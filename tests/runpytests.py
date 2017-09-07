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
'''

import os
import sys
import pytest
import glob

sys.path.append(scriptdir) # used by test scripts to import TestUtils

srcfiles=glob.glob(os.path.join(scriptdir,'unittests','*.py'))+glob.glob(os.path.join(scriptdir,'..','src','plugins','*.py'))

pytest.main(srcfiles)
