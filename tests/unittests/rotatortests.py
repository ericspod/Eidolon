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


import math
from TestUtils import eq_, eqas_, randnums, randangle
from eidolon import vec3, rotator, listSum, halfpi
import numpy as np


def testIdent1():
    '''Test the default rotator which should represent the identity transformation.'''
    for i in range(100):
        x,y,z=randnums(3,-5,5)
        v=vec3(x,y,z)
        r=rotator()
        eq_(r*v,v)
        

def testIdent2():
    '''Test a rotator specified as the angle around the zero vector is an identity transformation.'''
    r=rotator(vec3(),randangle())
    eq_(r,rotator())
    

def testPlaneDef1():
    r=rotator(vec3(1,0,0),vec3(0,1,0),vec3(1,0,0),vec3(0,1,0))
    eqas_(r.getEulers(),(0,0,0))
    
    
def testPlaneDef2():
    r=rotator(vec3(0,1,0),vec3(-1,0,0),vec3(1,0,0),vec3(0,1,0))
    eqas_(r.getEulers(),(halfpi,0,0))


def testPlaneDef3():
    r=rotator(vec3(1,0,0),vec3(0,0,1),vec3(1,0,0),vec3(0,1,0))
    eqas_(r.getEulers(),(0,halfpi,0))


def testAxis1():
    r=rotator(vec3(0,0,1),halfpi)
    eqas_(r.getEulers(),(halfpi,0,0))

    
def testAxis2():
    r=rotator(vec3(0,0,-1),halfpi)
    eqas_(r.getEulers(),(-halfpi,0,0))


def testFromTo1():
    r=rotator(vec3(1,0,0),vec3(0,1,0))
    eq_(r,rotator(vec3(0,0,1),halfpi))
    
    
def testFromTo2():
    for i in range(100):
        x,y,z=randnums(3,-5,5)
        v=vec3(x,y,z)   
        r=rotator(v,-v)
        eq_(r,rotator(vec3(1,0,0).cross(v),0)) # TODO: wanted to actually test 180 degree rotators
        #eq_(r,rotator(vec3(1,0,0).cross(v),math.pi))
        #eq_(r*v,-v)
    
    
def testEulers1():
    for i in range(100):
        y,p,r=randnums(3,-math.pi*2,math.pi*2)
        r1=rotator(y,p,r)
        eq_(r1,rotator(*r1.getEulers()))


def testEulers2():
    for i in range(100):
        y,p,r=randnums(3,-math.pi*2,math.pi*2)
        r1=rotator(y,p,r)
        eq_(r1,rotator(0,0,r)*rotator(y,0,0)*rotator(0,p,0))


def testEulers3():
    for i in range(100):
        a=randangle()
        eq_(rotator(a,0,0),rotator(vec3(0,0,1),a))
    

def testEulers4():
    for i in range(100):
        a=randangle()
        eq_(rotator(0,a,0),rotator(vec3(1,0,0),a))


def testEulers5():
    for i in range(100):
        a=randangle()
        eq_(rotator(0,0,a),rotator(vec3(0,1,0),a))


def testFullCircle1():
    r=rotator(vec3(1,0,0),math.pi*2)
    eq_(r,rotator())
    

def testMatrix1():
    for i in range(100):
        a=randangle()
        m=[math.cos(a),0,math.sin(a),0,1,0,-math.sin(a),0,math.cos(a)]
        r=rotator(*m)
        eq_(r,rotator(vec3(0,1,0),a))


def testMatrix2():
    for i in range(100):
        a=randangle()
        r=rotator(vec3(1,0,0),a)
        eqas_(listSum(r.toMatrix()),(1,0,0,0,0,math.cos(a),-math.sin(a),0,0,math.sin(a),math.cos(a),0,0,0,0,1))


def testMatrix3():
    for i in range(100):
        y,p,r=randnums(3,-math.pi*2,math.pi*2)
        r1=rotator(y,p,r)
        y,p,r=randnums(3,-math.pi*2,math.pi*2)
        r2=rotator(y,p,r)
        m1=r1.toMatrix()
        m2=r2.toMatrix()
        m=np.asarray(m1).dot(np.asarray(m2)).flat
        eqas_(listSum((r1*r2).toMatrix()),m)
        

def testInv1():
    for i in range(100):
        x,y,z=randnums(3,-5,5)
        v=vec3(x,y,z)
        y,p,r=randnums(3,-math.pi*2,math.pi*2)
        r1=rotator(y,p,r)
        eq_(r1*(r1/v),v)

