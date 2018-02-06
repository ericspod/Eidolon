# Eidolon Biomedical Framework
# Copyright (C) 2016-7 Eric Kerfoot, King's College London, all rights reserved
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


import Cython.Compiler.Options
Cython.Compiler.Options.cimport_from_pyx = True

from Cython.Build.Dependencies import cythonize

from distutils.core import setup
from distutils.extension import Extension
from distutils import sysconfig

import platform,sys,os,shutil,glob
import numpy as np


scriptdir= os.path.dirname(os.path.abspath(__file__)) # path of the current file
libraries=[]
extra_compile_args=['-w','-O3']
compiledirs={}

if sys.version_info.major == 3:
    compiledirs['c_string_type']='unicode'
    compiledirs['c_string_encoding']='ascii'


# platform identifiers, exactly 1 should be true
isDarwin=platform.system().lower()=='darwin'
isWindows=platform.system().lower()=='windows'
isLinux=platform.system().lower()=='linux'

# ensure there's a value for CC, this is omitted sometimes but gcc is a valid substitute
sysconfig._config_vars['CC']=sysconfig.get_config_var('CC') or 'gcc'

if isDarwin:
    platdir='osx'
    extra_compile_args+=['-mmacosx-version-min=10.6.0'] # Ogre was compiled with an older version of OSX for compatibility reasons
elif isWindows:
    platdir='win64_mingw'
    sys.argv.append('--compiler=mingw32') # force the use of mingw, there must be a proper programmatic way
else:
    assert isLinux
    libraries+=['m']
    platdir='linux'

libdir=os.path.abspath(os.path.join(scriptdir,'..','..','EidolonLibs',platdir))
assert os.path.isdir(libdir),'%r not found'%libdir

# include file directories
includedirs=[scriptdir+'/../renderer',libdir+'/include',libdir+'/include/boost',libdir+'/include/OGRE',np.get_include()]

extensions=[]
for i in glob.glob('./*.pyx'):
    e=Extension(
        os.path.basename(i)[:-4],
        [i],
        define_macros=[('BOOST_SYSTEM_NO_DEPRECATED',None)],
        include_dirs=includedirs,
        libraries=libraries,
        extra_compile_args=extra_compile_args,
        compiler_directives=compiledirs,
        language='c++'
    )
    extensions.append(e)

ext=cythonize(extensions,include_path=['.','../renderer'])

# HORRIBLE KLUDGE: need to get around problem of Cython generating code which relies on CPython having been compiled with --with-fpectl
# The macros PyFTE_*_PROTECT invoke symbols which don't exist with Anaconda builds so they need to be removed which appears to be safe.
# See https://github.com/numpy/numpy/issues/8415 http://www.psf.upfronthosting.co.za/issue29137
for cppfile in glob.glob('*.cpp'):
	sys.stdout.write('Processing %s\n'%cppfile)
	sys.stdout.flush()
	cpplines=open(cppfile).readlines()
	with open(cppfile,'w') as o:
		for line in cpplines:
			if 'PyFPE_START_PROTECT' not in line and 'PyFPE_END_PROTECT' not in line: # remove the symbol lines from the source
				o.write(line)

setup(ext_modules=ext)

shutil.rmtree('build')

# copy the created .so file to the temporary filename in Eidolon directory, this will be symlinked by run.sh
if not isWindows:
    for i in glob.glob('./*.pyx'):
        i=os.path.splitext(i)[0]
        dest='%s.so.%s'%(i,platdir)
        sobj=glob.glob(i+'.*.so') # .so files get weird names so find the first one that matches
        sobj=sobj[0] if sobj else i+'.so'
        shutil.move(sobj,dest)
