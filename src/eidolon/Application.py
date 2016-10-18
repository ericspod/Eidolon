# Eidolon Biomedical Framework
# Copyright (C) 2016 Eric Kerfoot, King's College London, all rights reserved
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


'''This defines the default application setup by setting configuration values, creating default materials, and creating the manager and UI.'''

from Renderer import vec3,color,initSharedDir,Config,platformID,PT_FRAGMENT,PT_VERTEX

import sys
import os
import argparse
import ConfigParser

import SceneManager
import VisualizerUI
import Utils
import Concurrency
from SceneUtils import cleanupMatrices
from ImageAlgorithms import hounsfieldToUnit

from __init__ import __version__


def readConfig(configfile,conf):
	'''Read configuration ini file `configfile' and store values in Config object `conf'.'''
	conf.set(platformID,'configfile',configfile)
	cparser=ConfigParser.SafeConfigParser()
	cparser.optionxform=str
	results=cparser.read(configfile)

	if not results:
		raise IOError,'Unable to read config file %r\n'%configfile

	# read all values into the conf object, using the section names from the config file as the group names
	for s in cparser.sections():
		for n,v in cparser.items(s):
			conf.set(s,n,v)

	if cparser.has_section('Shaders'):
		conf.set(platformID,'shaders',','.join(str(n) for n,_ in cparser.items('Shaders')))

	# copy values from the 'All' section into the platform-specific section which haven't already been set
	if 'All' in cparser.sections():
		for n,v in cparser.items('All'):
			if not conf.hasValue(platformID,n):
				conf.set(platformID,n,v)


def generateConfig(inargs):
	'''Setup and return a Config object based on the environment and provided command line arguments `inargs'.'''
	vizdir=Utils.getVizDir()
	prog='run.bat' if platformID=='Windows' else 'run.sh'
	conf=Config()
	configfile=''

	# set configuration default values for the current platform, these are overridden below when the config file is read
	conf.set(platformID,Utils.VIZDIRVAR,vizdir) # store Eidolon's root directory, this is './' if the global variable isn't present
	conf.set(platformID,Utils.RESDIRVAR,vizdir+'/res/') # store the resource directory
	conf.set(platformID,Utils.SHMDIRVAR,'/dev/shm' if platformID=='Linux' else vizdir+'/.shm/') # store shared memory segment ref count file directory
	conf.set(platformID,'rtt_preferred_mode','FBO') # PBO, PBuffer, Copy
	conf.set(platformID,'vsync','true')
	conf.set(platformID,'rendersystem','OpenGL') # OpenGL, D3D9, D3D10, D3D11

	# define a help action that prints the normal help plus the help texts from loaded plugins
	class HelpAction(argparse.Action):
		def __call__(self, parser, namespace, values, option_string=None):
			parser.print_help()

			# print the help info from each plugin if supplied
			for g in SceneManager.globalPlugins:
				helpstr=g.getHelp()
				if len(helpstr)>0:
					helplines=helpstr.strip().split('\n')
					helpstr='\n   '.join(helplines)
					print('\nPlugin %r:\n   %s' % (g.name,helpstr))

			sys.exit(0)

	# define the parser for the fixed arguments, this will parse those stated below and leave others for plugins to pick up later
	parser=argparse.ArgumentParser(prog=prog,description='Eidolon',add_help=False)
	parser.add_argument('--version', action='version', version=str(__version__))
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
	if os.path.isfile(os.path.join(vizdir,'config.ini')):
		configfile=os.path.join(vizdir,'config.ini')
		readConfig(configfile,conf)

	# read the config file specified on the command line, or if not given read ~/.viz/config.ini if present
	if args.config:
		configfile=args.config
		readConfig(configfile,conf)
	elif os.path.isfile(os.path.expanduser('~/.viz/config.ini')):
		configfile=os.path.expanduser('~/.viz/config.ini')
		readConfig(configfile,conf)

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

		conf.set('var','names',','.join(names))

	# load parsed argument values into the group 'args', joining the lists with '|' characters
	for n,v in args.__dict__.items():
		if v:
			conf.set('args',n,v if isinstance(v,str) else '|'.join(map(str,v)))

	# split --foo=bar into name-value pairs and store in group 'args', --foo alone gets stored as itself
	for i in unknown:
		ii=i.split('=',1)
		conf.set('args',ii[0],ii[-1])

	# if the logfile is present and is just the filename, put it in the eidolon directory
	logfile=os.path.split(conf.get(platformID,'logfile'))
	if len(logfile)>0 and logfile[0].strip()=='':
		conf.set(platformID,'logfile',os.path.join(vizdir,logfile[1]))

	# if "preloadscripts" is specified in the config file, prepend the given values to the config value for command line files
	if conf.get(platformID,'preloadscripts'):
		preloadscripts=conf.get(platformID,'preloadscripts').split(',')
		for i,p in enumerate(preloadscripts):
			if p.startswith('./') and configfile:
				preloadscripts[i]=os.path.join(os.path.dirname(configfile),p)

		if conf.hasValue('args','files'): # add existing files to the end of the files list
			preloadscripts.append(conf.get('args','files'))

		conf.set('args','files','|'.join(preloadscripts))

	return conf


def initDefault(conf):
	'''
	Initialize the default components of Eidolon. This sets up tracing, concurrency, inits the UI, sets the
	style sheet, creates the main window, and finally creates the SceneManager. Returns the main window and manager.
	'''
	if conf.hasValue('args','l'):
		Utils.setLogging(conf.get(platformID,'logfile'))

	if conf.hasValue('args','t'):
		Utils.setTrace()

	# cleanup matrices in shared memory to make sure we've got enough room in Linux
	cleanupMatrices()

	# nominate shared memory directory to store ref count files
	initSharedDir(conf.get(platformID,Utils.SHMDIRVAR))

	# initialize the singleton instance of the ProcessServer type using the specified CPU count or the actual count if not present
	Concurrency.ProcessServer.createGlobalServer(int(conf.get(platformID,'maxprocs') or Concurrency.cpu_count()))

	# initialize the UI, for Qt this is creating the QApplication object
	app=VisualizerUI.initUI()

	if conf.hasValue(platformID,'uistyle'):
		app.setStyle(conf.get(platformID,'uistyle'))

	# If a stylesheet is specified, try to find it relative to the VIZDIR directory if it isn't an absolute path,
	# either way use it as the application-wide stylesheet.
	if conf.hasValue(platformID,'stylesheet'):
		sheet=conf.get(platformID,'stylesheet')
		try:
			if not os.path.isabs(sheet):
				sheet=os.path.join(conf.get(platformID,Utils.VIZDIRVAR),sheet)

			with open(sheet) as s:
				app.setStyleSheet(s.read())
		except:
			pass

	# attempt to set the window size based on config values, default to 1200x800 if the format is wrong
	try:
		size=conf.get(platformID,'winsize').split()
		width=int(size[0])
		height=int(size[1])
	except:
		width=1200
		height=800

	# create the main window and the manager object
	win=VisualizerUI.createVizWin(conf,width,height)
	mgr=SceneManager.createSceneMgr(win,conf)

	return win,mgr


def initDefaultAssets(mgr):
	'''Initializes scene colors and lights, loads GPU scripts, and creates materials.'''

	# set the scene's default camera to a single camera, ambient light, and background color to match the UI color scheme
	mgr.setSingleFreeCamera()
	mgr.setAmbientLight(color(0.5,0.5,0.5))
	mgr.setBackgroundColor(color(0.3515625,0.3515625,0.3515625))

	if mgr.conf.get(platformID,'camerazlock').lower()=='false':
		mgr.setCameraZLocked(False)

	# create a default directional light that follows the camera
	cl=mgr.createLight(SceneManager.LightType._cdir,'Camera Light')
	cl.setColor(color(0.25,0.25,0.25))

	res=mgr.conf.get(platformID,Utils.RESDIRVAR)
	
	mgr.scene.addResourceDir(res)
	mgr.scene.initializeResources()

	# load shaders/fragment programs
	for s in mgr.conf.get(platformID,'shaders').split(','):
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

	offset=hounsfieldToUnit(0)
	ctspec=[color(0,0,0),color(1,0,0),color(0.85,0.85,0.5),color(1,1,1)]
	ctspecpos=[offset+hounsfieldToUnit(-150),offset+hounsfieldToUnit(200),offset+hounsfieldToUnit(400),offset+hounsfieldToUnit(550)]
	ctalpha=[vec3(offset+hounsfieldToUnit(-425),0),vec3(offset+hounsfieldToUnit(300),0.25),vec3(offset+hounsfieldToUnit(550),1.0),
										vec3(offset+hounsfieldToUnit(1050),1.0),vec3(offset+hounsfieldToUnit(2000),0.0)]
										
	s8=mgr.createSpectrum('CardiacCT')
	s8.setSpectrumData(ctspec,ctspecpos,ctalpha)
	
	s9=mgr.createSpectrum('CardiacCT2D')
	s9.setSpectrumData(ctspec,ctspecpos,[vec3(offset+hounsfieldToUnit(-150),0),vec3(offset+hounsfieldToUnit(-100),1.0)])
	
	# create materials

	m=mgr.createMaterial('Default')

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

	m=mgr.createMaterial('Rainbow')
	m.copySpectrumFrom(s1)

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

	m=mgr.createMaterial('Contour')
	m.useLighting(False)


def defaultMain(args=None):
	'''Default entry point for the application, calls the standard sequence of init steps and then starts the UI.'''
	conf=generateConfig(args if args else sys.argv[1:])
	win,mgr=initDefault(conf)
	initDefaultAssets(mgr)
	mgr.loadFilesTask(*conf.get('args','files').split('|'))
	VisualizerUI.execUI()

