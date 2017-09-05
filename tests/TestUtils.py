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

'''Test utility routines used by scripts in the included test subdirectories.'''

import math
import random
import eidolon
from eidolon import vec3,timing, ElemType, GeomType, frange, listToMatrix


epsilon=1e-10 # separate value that can be tweaked for tests only
halfpi=math.pi/2
quartpi=math.pi/4


def eq_(a,b,msg=None):
    assert a==b, msg or '%r != %r' % (a, b)

def neq_(a,b,msg=None):
    assert a!=b, msg or '%r == %r' % (a, b)
    

def eqa_(a,b,msg=None):
    assert abs(a-b)<=epsilon, msg or '%r != %r' % (a, b)


def eqas_(a,b,msg=None):
    assert all(abs(i-j)<=epsilon for i,j in zip(a,b)), msg or '%r != %r' % (a, b)


def randnums(num,minv,maxv):
    return tuple(random.triangular(minv,maxv) for _ in xrange(num))
    
    
def randangle():
    return random.triangular(-math.pi*2,math.pi*2)


@timing
def generateTestMeshDS(etname,refine,pt=vec3(0.25)):
    et=ElemType[etname]

    if et.geom in (GeomType._Hex, GeomType._Tet):
        dividefunc=eidolon.divideHextoTet if et.geom==GeomType._Tet else eidolon.divideHextoHex
        nodes=eidolon.listSum(dividefunc(et.order,refine))
        inds=list(eidolon.group(range(len(nodes)),len(et.xis)))

        nodes,ninds,_=eidolon.reduceMesh(listToMatrix([vec3(*n) for n in nodes],'nodes'),[listToMatrix(inds,'inds',etname)])
        dist=[nodes.getAt(n).distTo(pt) for n in xrange(len(nodes))]
        diff=[tuple(nodes.getAt(n)-pt) for n in xrange(len(nodes))]

    elif et.geom == GeomType._Tri:
        nodes,inds=eidolon.generateSphere(refine)
        dist=[n.distTo(pt) for n in nodes]
        diff=[tuple(n-pt) for n in nodes]
        ninds=[('inds',ElemType._Tri1NL,inds)]

    ds=eidolon.PyDataSet('TestDS',nodes,ninds,[('dist',dist,'inds'),('diff',diff,'inds')])
    ds.validateDataSet()
    return ds


def generateTimeSphereImages(step,dim=50):
    images=[]
    steps=frange(0,1.0+step,step)
    for i in steps:
        ii=math.sin(i*math.pi*2)
        stepimgs=eidolon.generateSphereImageStack(dim,dim,dim,vec3(0.5,0.5,0.5),vec3(0.25+0.2*ii,0.25,0.25))
        for s in stepimgs:
            s.timestep=i*500

        images+=stepimgs

    return images


def generateTimeSphereMeshes(step,dim=50):
    dds=[]
    steps=list(frange(0,1.0+step,step))
    for i in steps:
        i=math.sin(i*math.pi*2)
        ds=generateTestMeshDS(ElemType._Tri1NL,5)
        nodes=ds.getNodes()
        nodes.mul(vec3(0.25+0.2*i,0.25,0.25))
        nodes.mul(dim)
        nodes.add(vec3(dim+1)*vec3(0.5,-0.5,0.5))

        dist=ds.getDataField('dist')
        for n in xrange(dist.n()):
            dist.setAt(nodes.getAt(n).distTo(vec3(0.25)*dim),n)

        dds.append(ds)

    return dds,[s*500 for s in steps]
    