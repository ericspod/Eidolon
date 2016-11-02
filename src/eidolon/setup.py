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

# platform identifiers, exactly 1 should be true
isDarwin=platform.system().lower()=='darwin'
isWindows=platform.system().lower()=='windows'
isLinux=platform.system().lower()=='linux'

# ensure there's a value for CC, this is omitted sometimes but gcc is a valid substitute
sysconfig._config_vars['CC']=sysconfig.get_config_var('CC') or 'gcc'

if isDarwin:
	platdir='osx'
elif isWindows:
	platdir='win64_mingw'
	sys.argv.append('--compiler=mingw32') # force the use of mingw, there must be a proper programmatic way
else:
	assert isLinux
	libraries+=['m']

	with open('/etc/lsb-release') as o:
		lsb=dict(l.strip().split('=') for l in o.readlines() if l.strip())

	if lsb['DISTRIB_RELEASE'].startswith('12'):
		platdir='ubuntu12'
	elif lsb['DISTRIB_RELEASE'].startswith('14'):
		platdir='ubuntu14'
	else:
		raise ValueError,'Cannot compile with platform %r (%r)'%(lsb['DISTRIB_RELEASE'],lsb)


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
		language='c++'
	)
	extensions.append(e)

setup(ext_modules=cythonize(extensions,include_path=['.','../renderer']))

# copy the created .so file to the temporary filename in Eidolon directory, this will be symlinked by run.sh
if not isWindows:
	for i in glob.glob('./*.pyx'):
		i=os.path.splitext(i)[0]
		dest='%s.so.%s'%(i,platdir) if isLinux else i+'.dylib'
		shutil.move(i+'.so',dest)
