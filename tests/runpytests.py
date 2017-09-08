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

'''
Simple script to invoke pytest and run unit tests in the "unittest" directory as well as those in each plugin source file.
Run this script through the GUI through the menu "File -> Open Script" or on the command line: 
    
    ./run.sh tests/runpytests.py
    
This can be run in conjunction with coverage for even more testing information:
    
    ./tests/run_coverage.sh tests/runpytests.py
'''

# pylint cleanup stuff
mgr=mgr # pylint:disable=invalid-name,used-before-assignment
scriptdir=scriptdir # pylint:disable=invalid-name,used-before-assignment

import os
import sys
import pytest
import glob
import StringIO

try: # attempt to tweak terminal settings, this will fail on systems (win32) without terminal control
	import termios
	import struct
	import fcntl
	
	call = fcntl.ioctl(1,termios.TIOCGWINSZ,"\000"*8)
	row,col = struct.unpack( "hhhh", call ) [:2] # save the current terminal row and column values
	
	def setTerminalSize(fd, row, col):
		'''Set the terminal row and columns for the file descriptor `fd'.'''
		winsize = struct.pack("HHHH", row, col, 0, 0)
		fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)
except: # quietly do nothing since terminal control is aesthetic anyhow
	row,col=0,0
	def setTerminalSize(fd, row, col):pass

	
sys.path.append(scriptdir) # used by test scripts to import TestUtils

# collect unit test script files and plugin source files which may contain unit tests
srcfiles=glob.glob(os.path.join(scriptdir,'unittests','*.py'))+glob.glob(os.path.join(scriptdir,'..','src','plugins','*.py'))

sys.stdout=sys.stderr=out=StringIO.StringIO() # redirect stdout/stderr to the StringIO object out

setTerminalSize(sys.__stdout__.fileno(),10,50) # tweak the terminal size so that the separator lines aren't too large
pytest.main(['-p','no:cacheprovider']+srcfiles) # run with the cache provided disabled so no .cache directory is left behind
setTerminalSize(sys.__stdout__.fileno(),row,col) # restore terminal size

# restore streams
sys.stdout=sys.__stdout__
sys.stderr=sys.__stderr__

mgr.showTextBox('Pytest results:','Results',out.getvalue(),height=600)
