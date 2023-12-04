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


from setuptools import setup,Extension
from distutils import sysconfig

from Cython.Build import cythonize
import platform
import sys,os,shutil,numpy,glob

def generateMatrix(prefix,ttype,ptype=None,tofunc='',fromfunc=''):
    '''
    Generate pyx files for each of the matrix types. The file MatrixT.pyxT is a pseudo-template definition containing patterns
    for replacing type names for each of the matrix types as well as type specific methods. This allows templating essentially
    so that the matrix Cython interface only has to be written once. The generated files do need to be included in the correct
    place in Renderer.pyx.
    '''
    ptype=ptype or ttype
    infile='MatrixT.pyxT'
    outfile='{}Matrix.pyx'.format(prefix)

    if os.path.exists(outfile) and os.path.getmtime(outfile)>os.path.getmtime(infile):
        sys.stdout.write('Skipping generation of %s\n'%outfile)
        sys.stdout.flush()
        return

    matrixT=open(infile).readlines()
    extras=[i for i,l in enumerate(matrixT) if l.startswith('##Extras')]

    if len(extras)==0:
        text=matrixT
    else:
        text=matrixT[:extras[0]]

        for i,e in enumerate(extras):
            if matrixT[e].split()[1]==prefix:
                if i+1<len(extras):
                    text+=matrixT[e:extras[i+1]]
                else:
                    text+=matrixT[e:]
                break

    with open(outfile,'w') as o:
        o.write(''.join(text).format(T=ttype,N=prefix,P=ptype,_To=tofunc,_From=fromfunc))


# generate code for RealMatrix, IndexMatrix, Vec3Matrix, ColorMatrix
generateMatrix('Real','real')
generateMatrix('Index','indexval')
generateMatrix('Vec3','ivec3','vec3','vec3._new','vec3._get')
generateMatrix('Color','icolor','color','color._new','color._get')

# platform identifiers, exactly 1 should be true
isDarwin=platform.system().lower()=='darwin'
isWindows=platform.system().lower()=='windows'
isLinux=platform.system().lower()=='linux'

# ensure there's a value for CC, this is omitted sometimes but gcc is a valid substitute
sysconfig._config_vars['CC']=sysconfig.get_config_var('CC') or 'gcc'

scriptdir= os.path.dirname(os.path.abspath(__file__)) # path of the current file
libsuffix='' # "" (for release builds) or "Debug" to choose which libraries to link with
srcfiles=['Renderer.pyx','RenderTypes.cpp','OgreRenderTypes.cpp']
libraries=['OgreMain','OgreOverlay']
extra_compile_args=['-w','-O3']
extra_link_args=[]
define_macros=[('BOOST_SYSTEM_NO_DEPRECATED',None),('USEOGRE',None)]
destfile='./Renderer.'

#compiledirs={}
#
#if sys.version_info.major == 3:
#    compiledirs['c_string_type']='unicode'
#    compiledirs['c_string_encoding']='ascii'

cpptime=max(map(os.path.getmtime,glob.glob('*.cpp')))
htime=max(map(os.path.getmtime,glob.glob('*.h')))

# touch a cpp file it any header files were changed after the most recently changed cpp file
if htime>cpptime:
    os.utime(glob.glob('*.cpp')[0],None)

if isDarwin:
    platdir='osx'
    #destfile+='dylib'
    destfile+='so.%s'%platdir
    libraries=[] # linking with frameworks and not libraries

    # add frameworks to link with
    extra_link_args+=['-stdlib=libc++', '-mmacosx-version-min=10.9','-framework', 'Ogre', '-framework','OgreOverlay']
    extra_compile_args+=['-std=c++11','-mmacosx-version-min=10.9'] # Ogre was compiled with an older version of OSX for compatibility reasons

elif isWindows:
    platdir='win64_mingw'
    sys.argv.append('--compiler=mingw32') # force the use of mingw
    define_macros+=[('RENDER_EXPORT',None)]
    destfile+='pyd'
    
else:
    assert isLinux
    libraries+=['m','rt']
    platdir='linux'
    destfile+='so.%s'%platdir
    
    # force the use of GCC 4.9 for now
    #os.environ["CC"] = "gcc-4.9" 
    #os.environ["CXX"] = "g++-4.9"

# root directory for the current platform's libraries
libdir=os.path.abspath(os.path.join(scriptdir,'..','EidolonLibs',platdir))
assert os.path.isdir(libdir),'%r not found'%libdir

# directory containing shared objects or frameworks
shared_dir=libdir+'/bin/'+libsuffix
library_dir=libdir+'/lib/'+libsuffix

# include file directories
includedirs=['.',libdir+'/include/OgreOverlay',libdir+'/include/Ogre']

# add numpy include directory, this will vary by platform
includedirs.append(numpy.get_include())

if isDarwin: # add the directory to search for frameworks in
    extra_link_args+=['-F'+shared_dir] 

extension=Extension(
    'Renderer',
    srcfiles,
    define_macros=define_macros,
    include_dirs=includedirs,
    library_dirs=[library_dir],
    libraries=libraries,
    extra_compile_args=extra_compile_args,
    extra_link_args=extra_link_args,
#    compiler_directives=compiledirs,
    language='c++'
)

ext=cythonize(extension)

# HORRIBLE KLUDGE: need to get around problem of Cython generating code which relies on CPython having been compiled with --with-fpectl
# The macros PyFTE_*_PROTECT invoke symbols which don't exist with Anaconda builds so they need to be removed which appears to be safe.
# See https://github.com/numpy/numpy/issues/8415 http://www.psf.upfronthosting.co.za/issue29137
cpplines=open('Renderer.cpp').readlines()
with open('Renderer.cpp','w') as o:
    for line in cpplines:
        if 'PyFPE_START_PROTECT' not in line and 'PyFPE_END_PROTECT' not in line: # remove the symbol lines from the source
            o.write(line)

setup(ext_modules=ext)

os.remove('Renderer.cpp')
shutil.rmtree('build')

# tweak the stupid framework linking stuff
if isDarwin:
    for so in glob.glob('Renderer.cpython-*-darwin.so'):    
        os.system('install_name_tool -change @executable_path/../Frameworks/Ogre.framework/Versions/1.10.0/Ogre @loader_path/../EidolonLibs/osx/bin/Ogre.framework/Ogre '+so)
        os.system('install_name_tool -change @executable_path/../Frameworks/OgreOverlay.framework/Versions/1.10.0/OgreOverlay @loader_path/../EidolonLibs/osx/bin/OgreOverlay.framework/OgreOverlay '+so)

## copy the created .so file to the temporary filename in Eidolon directory, this will be symlinked by run.sh
#if not isWindows:
#    sobj=glob.glob('Renderer.*.so') # .so files get weird names so find the first one that matches or the default
#    sobj=sobj[0] if sobj else 'Renderer.so'
#    shutil.move(sobj,destfile)

