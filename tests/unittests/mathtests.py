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

try:
    import sys
    sys.path.append(scriptdir)
except:
    pass # the script is run 2nd time by nose which doesn't have scriptdir in its namespace, this can safely fail silently

import nose
from TestUtils import *
from eidolon import ElemType, GeomType


def testLine1NL():
    '''Test linear line element type.'''
    et=ElemType.Line1NL
    assert eq_([(0.0,), (1.0,)],et.xis)
    assert et.geom==GeomType._Line
    

nose.runmodule()    
