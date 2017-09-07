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
    pass

import nose
from TestUtils import *
from eidolon import vec3    

    
def testMembers():
    x,y,z=randnums(3,-5,5)
    v=vec3(x,y,z)
    
    eq_(v.x(),x)
    eq_(v.y(),y)
    eq_(v.z(),z)
    eqa_(v.len(),math.sqrt(x*x+y*y+z*z))
    
    
def testNan():
    v=vec3(float('nan'))
    neq_(v.len(), v.len()) # NaN is never equal to itself
    
    
def testInf():
    v=vec3(float('+inf'),float('-inf')) 
    
    eq_(v.x(),float('+inf'))
    eq_(v.y(),float('-inf'))
    eq_(-v.x(),float('-inf'))
    eq_(-v.y(),float('+inf'))
    eq_(v.x(),1e400)
    eq_(v.y(),-1e400)
    eq_(v.len(),float('+inf'))
    
    
def testAngle1():
    eqa_(vec3.X().angleTo(vec3.Y()),halfpi) 
    

def testAngle2():
    eqa_(vec3.X().angleTo(vec3.X()),0)  


def testPolar():
    x,y,z=randnums(3,-5,5)
    v=vec3(x,y,z)
    eq_(v.toPolar().fromPolar(),v)
    
    
def testCylindrical():
    x,y,z=randnums(3,-5,5)
    v=vec3(x,y,z)
    eq_(v.toCylindrical().fromCylindrical(),v)
    
    
def testArea():
    eqa_(vec3().triArea(vec3.X(),vec3.Y()),0.5)
    
    
def testLineDist():
    x,y=randnums(2,-5,5)
    v=vec3(x,y,0.5)
    eqa_(v.lineDist(vec3(),vec3.Z()),(v*vec3(1,1,0)).len())


    
    
#nose.runmodule()


