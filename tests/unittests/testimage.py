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

import unittest
from TestUtils import randnums
from eidolon import vec3,rotator, SharedImage, getPlaneXi


class TestImage(unittest.TestCase):
	def testXis1(self):
		'''Test the xi values of points on the plane of a SharedImage, calls SharedImage.getPlaneXi().'''
		si=SharedImage('',vec3(),rotator(),(10,10))
		self.assertEqual(vec3(),si.getPlaneXi(vec3()))
		self.assertEqual(vec3(1,1),si.getPlaneXi(vec3(10,-10)))
		self.assertEqual(vec3(0.5,0.5),si.getPlaneXi(vec3(5,-5)))
		self.assertEqual(vec3(0.5,0.5),si.getPlaneXi(vec3(5,-5)))
		
	def testXis2(self):
		'''Test the xi values of corners of a SharedImage, calls getPlaneXi().'''
		si=SharedImage('',vec3(1,-2,3),rotator(0.1,-0.2,0.3),(10,10),(0.678,0.789))
		corners=si.getCorners()
		self.assertEqual(vec3(),si.getPlaneXi(corners[0]))
		self.assertEqual(vec3(1,1),si.getPlaneXi(corners[-1]))
		self.assertEqual(vec3(0.5,0.5),si.getPlaneXi(si.center))
		
	def testXis3(self):
		'''Test the xi values of points on the plane of a SharedImage, calls SharedImage.getPlaneXi().'''
		pos=vec3(5,-6,7)
		si=SharedImage('',pos,rotator(),(10,10))
		self.assertEqual(vec3(),si.getPlaneXi(pos))
		self.assertEqual(vec3(1,1),si.getPlaneXi(pos+vec3(10,-10)))
		self.assertEqual(vec3(0.5,0.5,5),si.getPlaneXi(pos+vec3(5,-5,5)))
	
	def testXis4(self):
		'''Test the xi values of points on the plane of a SharedImage, calls SharedImage.getPlaneXi().'''
		pos=vec3(5,-6,7)
		dim=(0.678,0.789)
		si=SharedImage('',pos,rotator(),(10,10),dim)
		self.assertEqual(vec3(),si.getPlaneXi(pos))
		self.assertEqual(vec3(1,1),si.getPlaneXi(pos+vec3(10*dim[0],-10*dim[1])))
		self.assertEqual(vec3(0.5,0.5,5),si.getPlaneXi(pos+vec3(5*dim[0],-5*dim[1],5)))
	
	def testRot1(self):
		'''Tests the creation of a SharedImage with the default vec3 and rotator value, calls SharedImage.getPlaneXi().'''
		si=SharedImage('',vec3(),rotator(),(1,1))
		
		self.assertEqual(vec3(1),si.getPlaneXi(vec3(1,-1,1)))
		
	def testPlaneXiFunc(self):
		'''Tests the getPlaneXi function directly.'''
		v=vec3(*randnums(3,-5,5))
		r=rotator(*randnums(4,-1,1))
		self.assertEqual(vec3(0),getPlaneXi(v,v,r,vec3(1)))
		
