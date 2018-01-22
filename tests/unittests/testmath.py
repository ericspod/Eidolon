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


import unittest
from TestUtils import eq_,eqa_
from eidolon import ElemType, GeomType


class TestMath(unittest.TestCase):
	def testLine1NL(self):
		'''Test linear line element type.'''
		et=ElemType.Line1NL
		eqa_(0,et.xis[0][0])
		eqa_(1,et.xis[1][0])
		self.assertEqual(et.geom,GeomType._Line)
    
