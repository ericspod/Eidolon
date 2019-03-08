# Eidolon Biomedical Framework
# Copyright (C) 2016-8 Eric Kerfoot, King's College London, all rights reserved
# 
# This file is part of Eidolon.
#
# Eidolon is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# Eidolon is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along
# with this program (LICENSE.txt).  If not, see <http://www.gnu.org/licenses/>

'''
This module defines the default application setup by setting configuration values, creating default materials, and 
creating the manager and UI. The function defaultMain() is typically called as the entry point, which in turn calls
generateConfig(), initDefault(), initDefaultAssets(), loads command line filenames, then calls VisualizerUI.execUI().
These components can be swapped around as needed in some other sort of application packaging, but initDefault() is the
critical routine responsible for doing a lot of the bookkeeping and creating the SceneManager and main window objects.
'''
from .renderer import vec3,color,initSharedDir,Config,platformID,PT_FRAGMENT,PT_VERTEX

import sys
import os
import shutil
import argparse
from . import VisualizerUI
from . import Utils
from . import Concurrency  
from .SceneUtils import cleanupMatrices
from .ImageAlgorithms import hounsfieldToUnit
from .Utils import ConfVars,py3

if py3:
	from . import SceneManager, LightType, globalPlugins, createSceneMgr
else:
	from SceneManager import SceneManager, LightType, globalPlugins, createSceneMgr

from .__init__ import __version__, CONFIGFILE
            

def readConfig(configfile,conf):
    '''
    Read configuration ini file `configfile' and store values in Config object `conf'. Each section will also have a
    value with the name of the section in lower case containing the comma-separated list of value names.
    '''
    conf.set(platformID,ConfVars.configfile,configfile)
    cparser=Utils.configparser.SafeConfigParser()
    cparser.optionxform=str
    results=cparser.read(configfile)

    if not results:
        raise IOError('Unable to read config file %r\n'%configfile)

    # read all values into the conf object, using the section names from the config file as the group names
    for s in cparser.sections():
        for n,v in cparser.items(s):
            conf.set(s,n,v)

    # for each section, set a value named for the section in lower case containing a comma-separated list of names in the section
    for sec in cparser.sections():
        oldnames=filter(bool,conf.get(sec,sec.lower()).split(','))
        names=list(oldnames)+[str(n) for n,_ in cparser.items(sec)]
        conf.set(sec,sec.lower(),','.join(set(names)))


def generateConfig(inargs):
    '''
    Setup and return a Config object based on the environment and provided command line arguments `inargs'. This will
    parse the values in `inargs' according to the in-built command line argument specification, and store the results
    in the "args" group of the returned Config object. The configuration file in the Eidolon directory (defined by
    the environment variable named by APPDIRVAR) is the loaded and its values are inserted into the Config object. If 
    a configuration file is specified on the command line or otherwise there is one in the app directory, this is loaded 
    and its values override those already loaded. Any arguments defined on the command line are then inserted into the 
    object, and the "var" argument if present is then parsed and its values inserted.
    '''
    
    appdir=Utils.getAppDir()
    prog='run.bat' if platformID=='Windows' else 'run.sh'
    conf=Config()
    configfile=''
    
    # set configuration default values for the current platform, these are overridden below when the config file is read
    conf.set(platformID,ConfVars.resdir,appdir+'/res/') # store the resource directory
    conf.set(platformID,ConfVars.shmdir,'/dev/shm' if platformID=='Linux' else appdir+'/.shm/') # store shared memory segment ref count file directory
    conf.set(platformID,ConfVars.rtt_preferred_mode,'FBO') # PBO, PBuffer, Copy
    conf.set(platformID,ConfVars.vsync,'true')
    conf.set(platformID,ConfVars.rendersystem,'OpenGL') # OpenGL, D3D9, D3D10, D3D11

    # define a help action that prints the normal help plus the help texts from loaded plugins
    class HelpAction(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            parser.print_help()
            
            print('\nPython Version:',sys.version)
            
            try:
                from .ui import QtCore
                print('Qt Version:',str(QtCore.qVersion()))
                print('PyQt Version',QtCore.PYQT_VERSION_STR)
            except:
                pass

            # print the help info from each plugin if supplied
            for g in globalPlugins:
                helpstr=g.getHelp()
                if len(helpstr)>0:
                    helplines=helpstr.strip().split('\n')
                    helpstr='\n   '.join(helplines)
                    Utils.printFlush('\nPlugin %r:\n   %s' % (g.name,helpstr))

            sys.exit(0)

    # define the parser for the fixed arguments, this will parse those stated below and leave others for plugins to pick up later
    parser=argparse.ArgumentParser(prog=prog,description='Eidolon v%s'%__version__,add_help=False)
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument('--config',help='Specify configuration file',dest='config',metavar='FILE',nargs=1)
    parser.add_argument('--var',help='Provide script string variables',dest='var',metavar='NAME,VAL,...',nargs=1,action='append')
    parser.add_argument('--setting',help='Override a config setting value',dest='setting',metavar='VAL',nargs=2,action='append')
    parser.add_argument('-t',help='Enable line tracing in stdout or log file',action='store_const',const='trace')
    parser.add_argument('-l',help='Enable logging to file',action='store_const',const='log')
    parser.add_argument('-c',help='Display the console at startup',action='store_const',const='console')
    parser.add_argument('files',help='Python Script Files, Project Directories, or Data Files',nargs='*')
    parser.add_argument('--help','-h',nargs=0,action=HelpAction,help='Display this help text and exit')

    args,unknown=parser.parse_known_args(inargs) # parse arguments after setting up config in case we quit (ie. --help) and cleanupMatrices gets called
    
    # load the config file in the Eidolon's directory if it exists
    if os.path.isfile(os.path.join(appdir,CONFIGFILE)):
        configfile=os.path.join(appdir,CONFIGFILE)
        readConfig(configfile,conf)

    # get the user application directory from either the platformID or All section in the config file and then set it for platformID
    userappdir=os.path.expanduser(conf.get(platformID,ConfVars.userappdir) or conf.get('All',ConfVars.userappdir))
    conf.set(platformID,ConfVars.userappdir,userappdir)
    conf.set(platformID,ConfVars.userplugindir,os.path.join(userappdir,'plugins'))
    
    # read the config file specified on the command line, or if not given read userappdir/config.ini if present, and override current values in conf with these
    if args.config:
        configfile=args.config
        readConfig(configfile,conf)
    elif userappdir and os.path.isfile(os.path.join(userappdir,CONFIGFILE)):
        configfile=os.path.join(userappdir,CONFIGFILE)
        readConfig(configfile,conf)
        
    # copy every value in the "All" section to the platformID section if not already present
    for name in conf.get('All',ConfVars.all).split(','):
        if not conf.hasValue(platformID,name):
            conf.set(platformID,name,conf.get('All',name))

    # override loaded settings with those specified on the command line
    if args.setting:
        for arg in args.setting:
            conf.set(platformID,arg[0],arg[1])

    # add variables added through --var
    if args.var:
        names=[]
        for arg in args.var:
            arg=arg[0].split(',',1)
            conf.set('var',arg[0],arg[1])
            names.append(arg[0])

        conf.set('var','names','|'.join(names))

    # load parsed argument values into the group 'args', joining the lists with '|' characters
    for n,v in args.__dict__.items():
        if v:
            conf.set('args',n,v if isinstance(v,str) else '|'.join(map(str,v)))

    # split --foo=bar into name-value pairs and store in group 'args', --foo alone gets stored as itself
    for i in unknown:
        ii=i.split('=',1)
        conf.set('args',ii[0],ii[-1])

    # if the logfile is present and is just the filename, put it in the user data directory
    logfile=os.path.split(conf.get(platformID,ConfVars.logfile))
    if len(logfile)>0 and logfile[0].strip()=='':
        conf.set(platformID,ConfVars.logfile,os.path.join(userappdir,logfile[1]))

    # if "preloadscripts" is specified in the config file, prepend the given values to the config value for command line files
    if conf.get(platformID,ConfVars.preloadscripts):
        preloadscripts=conf.get(platformID,ConfVars.preloadscripts).split(',')
        for i,p in enumerate(preloadscripts):
            if p.startswith('./') and configfile:
                preloadscripts[i]=os.path.join(os.path.dirname(configfile),p)

        if conf.hasValue('args','files'): # add existing files to the end of the files list
            preloadscripts.append(conf.get('args','files'))

        conf.set('args','files','|'.join(preloadscripts))

    return conf


def initDefault(conf,initGui=True):
    '''
    Initialize the default components of Eidolon. This sets up tracing, concurrency, inits the UI, sets the
    style sheet, creates the main window, and finally creates the SceneManager. Returns the main window and manager.
    '''
    userappdir=conf.get(platformID,ConfVars.userappdir)
    appdir=Utils.getAppDir() #conf.get(platformID,APPDIRVAR)
    
    if userappdir and not os.path.exists(userappdir):
        Utils.printFlush('Creating user directory %r'%userappdir)
        os.mkdir(userappdir,0o700)
        shutil.copy(os.path.join(appdir,CONFIGFILE),os.path.join(userappdir,CONFIGFILE))
        
    if conf.hasValue('args','l'):
        Utils.setLogging(conf.get(platformID,ConfVars.logfile))

    if conf.hasValue('args','t'):
        Utils.setTrace()

    # cleanup matrices in shared memory to make sure we've got enough room in Linux
    cleanupMatrices()

    # change the shm directory location to be the per-user application data directory
    if platformID!='Linux':
        conf.set(platformID,ConfVars.shmdir,userappdir+'/shm/') 

    # nominate shared memory directory to store ref count files
    initSharedDir(conf.get(platformID,ConfVars.shmdir))

    # initialize the singleton instance of the ProcessServer type using the specified CPU count or the actual count if not present
    Concurrency.ProcessServer.createGlobalServer(int(conf.get(platformID,ConfVars.maxprocs) or Concurrency.cpu_count()))

    if initGui:
        # initialize the UI, for Qt this is creating the QApplication object
        app=VisualizerUI.initUI()
    
        if conf.hasValue(platformID,ConfVars.uistyle):
            app.setStyle(conf.get(platformID,ConfVars.uistyle))
    
        # If a stylesheet is specified, try to find it relative to the APPDIR directory if it isn't an absolute path,
        # either way use it as the application-wide stylesheet.
        if conf.hasValue(platformID,ConfVars.stylesheet):
            sheet=conf.get(platformID,ConfVars.stylesheet)
            try:
                if not os.path.isabs(sheet):
                    sheet=os.path.join(appdir,sheet)
    
                with open(sheet) as s:
                    app.setStyleSheet(s.read())
            except:
                pass
    
        # attempt to set the window size based on config values, default to 1200x800 if the format is wrong
        try:
            size=conf.get(platformID,ConfVars.winsize).split()
            width=int(size[0])
            height=int(size[1])
        except:
            width=1200
            height=800
            
        # create the main window and the manager object
        win=VisualizerUI.createVizWin(conf,width,height)
    else:
        win=None # no GUI, every other part of Eidolon should expect this to be None in this case
        
    mgr=createSceneMgr(win,conf)

    return win,mgr


def initDefaultAssets(mgr):
    '''Initializes scene colors and lights, loads GPU scripts, and creates materials.'''

    # set the scene's default camera to a single camera, ambient light, and background color to match the UI color scheme
    mgr.setSingleFreeCamera()
    mgr.setAmbientLight(color(0.5,0.5,0.5))
    mgr.setBackgroundColor(color(0.3515625,0.3515625,0.3515625))

    if mgr.conf.get(platformID,ConfVars.camerazlock).lower()=='false':
        mgr.setCameraZLocked(False)

    # create a default directional light that follows the camera
    cl=mgr.createLight(LightType._cdir,'Camera Light')
    cl.setColor(color(0.25,0.25,0.25))

    res=mgr.conf.get(platformID,ConfVars.resdir)
    
    mgr.scene.addResourceDir(res)
    mgr.scene.initializeResources()

    # load shaders/fragment programs
    for s in mgr.conf.get('Shaders',ConfVars.shaders).split(','):
        spec=mgr.conf.get('Shaders',s).split(',')
        ptype=PT_FRAGMENT if spec[0]=='fragment' else PT_VERTEX
        profiles=spec[1] if len(spec)>1 else None
        mgr.loadGPUScriptFile(res+s,ptype,profiles=profiles,ignoreError=True)

    # create spectrums

    s2=mgr.createSpectrum('BW')
    s2.setSpectrumData([color(0,0,0),color()])

    s3=mgr.createSpectrum('BWAlpha')
    s3.setSpectrumData([color(0,0,0),color()],[0,1],[vec3(0,0),vec3(1,1)])
    
    s1=mgr.createSpectrum('Rainbow')
    s1.setSpectrumData([color(0.0,0.0,1.0),color(0.0,1.0,1.0),color(0.0,1.0,0.0),color(1.0,1.0,0.0),color(1.0,0.0,0.0)])
    
    s4=mgr.createSpectrum('RedBlue')
    s4.setSpectrumData([color(1.0,0.0,0.0),color(0.0,0.0,1.0)])
    
    s5=mgr.createSpectrum('BlackGreenWhite')
    s5.setSpectrumData([color(0.0,0.0,0.0),color(0,1.0,0),color(1.0,1.0,1.0)])

    s6=mgr.createSpectrum('BlueWhiteRed')
    s6.setSpectrumData([color(0.0,0.0,1.0),color(1.0,1.0,1.0),color(1.0,0.0,0.0)])
    
    s7=mgr.createSpectrum('EMSpectrum')
    s7.setSpectrumData([color(0.6,0.0,0.6),color(0.0,1.0,1.0),color(0.0,1.0,0.0),color(1.0,1.0,0.0),color(1.0,0.0,0.0),color(0.3,0.0,0.0)])

    ctspec=[color(0,0,0),color(1,0,0),color(0.85,0.85,0.5),color(1,1,1)]
    ctspecpos=[hounsfieldToUnit(-150),hounsfieldToUnit(200),hounsfieldToUnit(400),hounsfieldToUnit(550)]
    ctalpha=[vec3(hounsfieldToUnit(-425),0),vec3(hounsfieldToUnit(300),0.25),vec3(hounsfieldToUnit(550),1.0),
                                        vec3(hounsfieldToUnit(1050),1.0),vec3(hounsfieldToUnit(2000),0.0)]
                                        
    s8=mgr.createSpectrum('CardiacCT')
    s8.setSpectrumData(ctspec,ctspecpos,ctalpha)
    
    s9=mgr.createSpectrum('CardiacCT2D')
    s9.setSpectrumData(ctspec,ctspecpos,[vec3(hounsfieldToUnit(-150),0),vec3(hounsfieldToUnit(-100),1.0)])
    
    s10=mgr.createSpectrum('Thermal')
    s10.setSpectrumData([color(0.105,0.047,0.253), color(0.291,0.046,0.419), color(0.472,0.111,0.428),
                         color(0.646,0.174,0.378), color(0.807,0.263,0.279), color(0.930,0.411,0.145),
                         color(0.985,0.601,0.024), color(0.971,0.813,0.228), color(0.988,0.998,0.645)])
    
    # create materials

    m=mgr.createMaterial('Default')
    
    m=mgr.createMaterial('BlueWhiteRed')
    m.copySpectrumFrom(s6)

    m=mgr.createMaterial('Rainbow')
    m.copySpectrumFrom(s1)

    # prime color materials
    m=mgr.createMaterial('Red')
    m.setDiffuse(color(1,0,0))
    m=mgr.createMaterial('Green')
    m.setDiffuse(color(0,1,0))
    m=mgr.createMaterial('Blue')
    m.setDiffuse(color(0,0,1))
    m=mgr.createMaterial('Yellow')
    m.setDiffuse(color(1,1,0))
    m=mgr.createMaterial('Magenta')
    m.setDiffuse(color(1,0,1))
    m=mgr.createMaterial('Cyan')
    m.setDiffuse(color(0,1,1))

    m=mgr.createMaterial('BaseImage')
    m.useVertexColor(False)
    m.setGPUProgram('BaseImage',PT_FRAGMENT)
    m.copySpectrumFrom(s3)

    m=mgr.createMaterial('BaseImage2D')
    m.useVertexColor(False)
    m.setGPUProgram('BaseImage',PT_FRAGMENT)
    m.copySpectrumFrom(s2)

    m=mgr.createMaterial('BoundBoxes')
    m.useLighting(False)

    m=mgr.createMaterial('CtrlNode')
    m.useVertexColor(False)
    m.setPointSizeAbs(5.0)
    m.useLighting(False)
    m.setDiffuse(color(0.75,0,0))

    m=mgr.createMaterial('Handle')
    m.useLighting(False)
    m.useDepthCheck(False)
    
    m=mgr.createMaterial('Node')

    m=mgr.createMaterial('Contour')
    m.useLighting(False)


def defaultMain(args=None):
    '''Default entry point for the application, calls the standard sequence of init steps and then starts the UI.'''
    conf=generateConfig(args or sys.argv[1:])
    win,mgr=initDefault(conf)
    initDefaultAssets(mgr)
    mgr.loadFilesTask(*conf.get('args','files').split('|'))
    VisualizerUI.execUI()
    

def noGuiMain(args=[]):
    '''Default entry point for the application, calls the standard sequence of init steps and then starts the UI.'''
    conf=generateConfig(args)
    _,mgr=initDefault(conf,False)
    initDefaultAssets(mgr)
    mgr.loadFilesTask(*conf.get('args','files').split('|'))
