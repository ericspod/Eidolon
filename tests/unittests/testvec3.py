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
import math
from eidolon import vec3, halfpi
from TestUtils import epsilon, randnums


class TestVec3(unittest.TestCase):
	def assertAlmostEqual(self,first, second, places=7, msg=None,delta=None):
		return unittest.TestCase.assertAlmostEqual(self,first, second, places, msg, epsilon or delta)
		
	def testMembers(self):
		'''Test members assigned to a vec3 are returned correctly.'''
		x,y,z=randnums(3,-5,5)
		v=vec3(x,y,z)
		
		self.assertEqual(v.x(),x)
		self.assertEqual(v.y(),y)
		self.assertEqual(v.z(),z)
		self.assertAlmostEqual(v.len(),math.sqrt(x*x+y*y+z*z))
		
	def testNan(self):
		'''Test NaN as a vector component value.'''
		v=vec3(float('nan'))
		self.assertNotEqual(v.len(), v.len()) # NaN is never equal to itself
		
	def testInf(self):
		'''Test +inf and -inf as vector component values.'''
		v=vec3(float('+inf'),float('-inf')) 
		
		self.assertEqual(v.x(),float('+inf'))
		self.assertEqual(v.y(),float('-inf'))
		self.assertEqual(-v.x(),float('-inf'))
		self.assertEqual(-v.y(),float('+inf'))
		self.assertEqual(v.x(),1e400)
		self.assertEqual(v.y(),-1e400)
		self.assertEqual(v.len(),float('+inf'))
		
	def testAngle1(self):
		self.assertAlmostEqual(vec3.X().angleTo(vec3.Y()),halfpi) 
		
	def testAngle2(self):
		self.assertAlmostEqual(vec3.X().angleTo(vec3.X()),0)  
	
	def testPolar(self):
		x,y,z=randnums(3,-5,5)
		v=vec3(x,y,z)
		self.assertEqual(v.toPolar().fromPolar(),v)
		
	def testCylindrical(self):
		x,y,z=randnums(3,-5,5)
		v=vec3(x,y,z)
		self.assertEqual(v.toCylindrical().fromCylindrical(),v)
		
	def testArea(self):
		self.assertAlmostEqual(vec3().triArea(vec3.X(),vec3.Y()),0.5)
		
	def testLineDist(self):
		x,y=randnums(2,-5,5)
		v=vec3(x,y,0.5)
		self.assertAlmostEqual(v.lineDist(vec3(),vec3.Z()),(v*vec3(1,1,0)).len())
		