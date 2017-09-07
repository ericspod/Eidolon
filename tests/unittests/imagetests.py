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
    sys.path.append(scriptdir+'..')
except:
    pass # the script is run 2nd time by nose which doesn't have scriptdir in its namespace, this can safely fail silently

import nose
from TestUtils import *
from eidolon import vec3,rotator, SharedImage, getPlaneXi
import numpy as np


def testXis1():
    '''Test the xi values of points on the plane of a SharedImage, calls SharedImage.getPlaneXi().'''
    si=SharedImage('',vec3(),rotator(),(10,10))
    eq_(vec3(),si.getPlaneXi(vec3()))
    eq_(vec3(1,1),si.getPlaneXi(vec3(10,-10)))
    eq_(vec3(0.5,0.5),si.getPlaneXi(vec3(5,-5)))
    eq_(vec3(0.5,0.5),si.getPlaneXi(vec3(5,-5)))
    

def testXis2():
    '''Test the xi values of corners of a SharedImage, calls getPlaneXi().'''
    si=SharedImage('',vec3(1,-2,3),rotator(0.1,-0.2,0.3),(10,10),(0.678,0.789))
    corners=si.getCorners()
    eq_(vec3(),si.getPlaneXi(corners[0]))
    eq_(vec3(1,1),si.getPlaneXi(corners[-1]))
    eq_(vec3(0.5,0.5),si.getPlaneXi(si.center))
    
    
def testXis3():
    '''Test the xi values of points on the plane of a SharedImage, calls SharedImage.getPlaneXi().'''
    pos=vec3(5,-6,7)
    si=SharedImage('',pos,rotator(),(10,10))
    eq_(vec3(),si.getPlaneXi(pos))
    eq_(vec3(1,1),si.getPlaneXi(pos+vec3(10,-10)))
    eq_(vec3(0.5,0.5,5),si.getPlaneXi(pos+vec3(5,-5,5)))
    

def testXis4():
    '''Test the xi values of points on the plane of a SharedImage, calls SharedImage.getPlaneXi().'''
    pos=vec3(5,-6,7)
    dim=(0.678,0.789)
    si=SharedImage('',pos,rotator(),(10,10),dim)
    eq_(vec3(),si.getPlaneXi(pos))
    eq_(vec3(1,1),si.getPlaneXi(pos+vec3(10*dim[0],-10*dim[1])))
    eq_(vec3(0.5,0.5,5),si.getPlaneXi(pos+vec3(5*dim[0],-5*dim[1],5)))
    

def testRot1():
    '''Tests the creation of a SharedImage with the default vec3 and rotator value, calls SharedImage.getPlaneXi().'''
    si=SharedImage('',vec3(),rotator(),(1,1))
    
    eq_(vec3(1),si.getPlaneXi(vec3(1,-1,1)))
    

def testPlaneXiFunc():
    '''Tests the getPlaneXi function directly.'''
    v=vec3(*randnums(3,-5,5))
    r=rotator(*randnums(4,-1,1))
    eq_(vec3(0),getPlaneXi(v,v,r,vec3(1)))
    
#nose.runmodule()    
