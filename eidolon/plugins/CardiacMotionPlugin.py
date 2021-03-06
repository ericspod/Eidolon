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

import eidolon
from eidolon import (
    vec3, rotator, transform, BoundBox, Vec3Matrix, RealMatrix, IndexMatrix, Future, StdProps, ElemType, Project, 
    avg, stddev, first, minmax, fillList, taskroutine, taskmethod, timing, concurrent, listSum, matIter, shareMatrices,
    ParamType, ParamDef, splitPathExt
)

import numpy as np
from scipy.ndimage import binary_fill_holes

import os
import math
import textwrap
import unittest
from glob import glob

from .IRTKPlugin import IRTKPluginMixin,ServerMsgs,TrackTypes,JobMetaValues,trackconfname
from .SegmentPlugin import SegSceneObject,SegmentTypes
from .CheartPlugin import LoadDialog
from .ReportCardPlugin import ReportCardSceneObject
from .DicomPlugin import readDicomHeartRate
from ..ui import Ui_CardiacMotionProp


ConfigNames=eidolon.enum(
    'savecheart',
    'shortaxis','templateimg','saxseg','saxtimereg','regsubject','regintermed', # alignment/registration names
    'tagged3d','detagged3d', # 3D tag values
    'serveraddr','serverport','jobids','trackedimg','maskimg','adaptive','paramfile', # server values
    'heartrateBPM' # stored properties
)


def avgDevRange(vals,stddevDist=1.0):
    '''Calculate the average of values from `vals' which are within `stddevDist' standard deviations of the average.'''
    if not vals:
        return 0

    vals=list(vals)
    a=avg(vals)
    sd=stddev(vals)*stddevDist
    return avg(v for v in vals if abs(v-a)<=sd)


@timing
def calculateLVDirectionalFields(ds,longaxis,radialname,longname,circumname):

    spatialmats=list(filter(eidolon.isSpatialIndex,ds.enumIndexSets()))
    indmat=first(m for m in spatialmats if ElemType[m.getType()].dim==3) or first(spatialmats)
    indname=indmat.getName()

    nodes=ds.getNodes().clone()
    length=nodes.n()

    longmat=RealMatrix(longname,length,3)
    radialmat=RealMatrix(radialname,length,3)
    circummat=RealMatrix(circumname,length,3)

    orient=rotator(longaxis,vec3(0,0,1))
    nodes.mul(transform(-BoundBox(nodes).center,vec3(1),orient))  # transforms the mesh so that the centerline is Z axis

    # calculate the bound boxes of the nodes near the mitral plane and apex
    minz,maxz=minmax([n.z() for n in nodes]) # determine the min and max distance from the origin in the Z dimension, ie. height
    mitralaabb=BoundBox([n for n in nodes if n.z()<(minz+(maxz-minz)*0.1)])
    apexaabb=BoundBox([n for n in nodes if n.z()>(minz+(maxz-minz)*0.9)])

    # `longaxis' is pointing from apex to mitral so reverse it, this assumes apex is small which may be wrong
    if mitralaabb.radius<apexaabb.radius:
        longaxis=-longaxis
        mitralaabb,apexaabb=apexaabb,mitralaabb

    #nodes.sub(apexaabb.center*vec3(1,1,0)) # try to center on the apex

    apexray=eidolon.Ray(mitralaabb.center,(apexaabb.center-mitralaabb.center))

    for n in range(length):
        node=nodes[n]
        d=apexray.distTo(node) #*0.9 # scale the distance along the ray so that apex directions are more rounded
        rad=orient/((node-apexray.getPosition(d))*vec3(1,1,0)).norm()
        #rad=orient/(node*vec3(1,1,0)).norm()

        radialmat.setRow(n,*rad)
        longmat.setRow(n,*longaxis)
        circummat.setRow(n,*(longaxis.cross(rad)))

    longmat.meta(StdProps._topology,indname)
    longmat.meta(StdProps._spatial,indname)
    longmat.meta(StdProps._timecopy,'True')
    circummat.meta(StdProps._topology,indname)
    circummat.meta(StdProps._spatial,indname)
    circummat.meta(StdProps._timecopy,'True')
    radialmat.meta(StdProps._topology,indname)
    radialmat.meta(StdProps._spatial,indname)
    radialmat.meta(StdProps._timecopy,'True')

    return radialmat,longmat,circummat


def createStrainGrid(nodes,toRefSpace,toImgSpace,h):
    '''
    Calculate the 6 point strain node set for each node of `nodes'. Each node from `nodes' is first transformed by
    `toRefSpace' to place it in reference space, then 6 vectors are calculated by shifting the node by `h' along
    each axis in the positive and negative directions. All vectors are then transformed by `toImgSpace'. The result
    is a matrix with 7 columns, the transformed node and its 6 shifted vectors.
    '''
    result=Vec3Matrix('straingrid',0,7)
    result.reserveRows(len(nodes))

    rot=toImgSpace.getRotation()
    dx=rot*vec3(h,0,0)
    dy=rot*vec3(0,h,0)
    dz=rot*vec3(0,0,h)

    for n in range(len(nodes)):
        p=toImgSpace*(toRefSpace*nodes[n])
        result.append(p,p+dx,p-dx,p+dy,p-dy,p+dz,p-dz)

#   result.mul(toImgSpace)

    return result


def createStrainField(nodes,radialfield,longfield,circumfield,h):
    '''
    Calculate a strain field by adding or subtracting the corresponding directional vectors to each node in `nodes'.
    '''
    numnodes=nodes.n()
    result=Vec3Matrix('strainfield',0,7)
    result.reserveRows(numnodes)

    for n in range(numnodes):
        p=nodes.getAt(n)
        rad=vec3(*radialfield.getRow(n)).norm()*h
        cir=vec3(*circumfield.getRow(n)).norm()*h
        lon=vec3(*longfield.getRow(n)).norm()*h
        result.append(p,p+rad,p-rad,p+cir,p-cir,p+lon,p-lon)

    return result


def strainTensor(px,mx,py,my,pz,mz,hh):
    '''
    Calculate the Green-Lagrange strain tensor for a point in space given the 6 deformed strain axes for that point.
    The vectors are assumed to have been calculated initially at a distance of `hh' from the node.
    '''
    hh2=1.0/(2.0*hh)

    # gradient matrix G
    a,b,c=(px-mx)*hh2
    d,e,f=(py-my)*hh2
    g,h,i=(pz-mz)*hh2

    x0 = 0.5*a
    x1 = 0.5*d
    x2 = 0.5*g
    x3 = b*x0 + e*x1 + h*x2
    x4 = c*x0 + f*x1 + i*x2
    x5 = 0.5*b*c + 0.5*e*f + 0.5*h*i

    return 0.5*a**2 + 0.5*d**2 + 0.5*g**2 - 0.5, x3, x4, x3, 0.5*b**2 + 0.5*e**2 + 0.5*h**2 - 0.5, x5, x4, x5, 0.5*c**2 + 0.5*f**2 + 0.5*i**2 - 0.5


def tensorMul(E,v):
    '''Returns Ev.v'''
    return (E[0]*v[0]+E[1]*v[1]+E[2]*v[2])*v[0]+(E[3]*v[0]+E[4]*v[1]+E[5]*v[2])*v[1]+(E[6]*v[0]+E[7]*v[1]+E[8]*v[2])*v[2]

@timing
def calculateStrainTensors(nodes_t,h):
    '''
    Calculate the tensors for each row of `nodes_t', which is the transformed node and its 6 transformed strain vectors.
    The result is a 9 column matrix where each row is a tensor matrix laid out in row-column order.
    '''
    result=RealMatrix('straintensors',0,9)
    result.reserveRows(nodes_t.n())

    for n in range(nodes_t.n()):
        _,px,mx,py,my,pz,mz=nodes_t.getRow(n)
        result.append(*strainTensor(px,mx,py,my,pz,mz,h))

    return result


@timing
def calculateTensorIndicatorEigen(tensors):
    '''Calculate the maximal and minimal eigenvalue for each tensor matrix in `tensors.'''
    maxeig=RealMatrix('maxstrain',0)
    maxeig.reserveRows(tensors.n())
    mineig=RealMatrix('maxstrain',0)
    mineig.reserveRows(tensors.n())

    for n in range(tensors.n()):
        E=np.matrix(tensors.getRow(n)).reshape(3,3)
        eigvals,reigvals=np.linalg.eig(E)
        maxeig.append(np.max(eigvals))
        mineig.append(np.min(eigvals))

    return maxeig,mineig


@timing
def calculateTensorMul(tensors,vecmat,name):
    assert tensors.n()==vecmat.n(),'%i != %i'%(tensors.n(),vecmat.n())
    result=RealMatrix(name,tensors.n())

    for n in range(tensors.n()):
        E=tensors.getRow(n)
        v=vecmat.getRow(n)
        result.setRow(n,tensorMul(E,v))

    return result


@concurrent
def divideTrisByRegionRange(process,tris,nodeprops,regionfield,choosevals):
    '''
    Returns matrices containing the indices of the triangles belonging to the regions given in `choosevals' as defined
    by the region field `regionfield'. The matrix `tris' is the original triangle index matrix and `nodeprops' the
    associated node properties matrix, these are expected to have heen derived from generateLinearTriangulation() so
    are not from the original dataset whereas `regionfield' is. Return value is list of matrices for each chosen region
    in no particular order.
    '''
    matrices={cv:IndexMatrix('choose_%i_%r'%(process.index,cv),tris.getType(),0,tris.m()) for cv in choosevals}

    # For each triangle, determine what region the original element it was derived from was part of
    # and store the triangle's indices in the appropriate region matrix.
    for n in range(tris.n()):
        process.setProgress((n+1)/process.total)
        nodeinds=tris.getRow(n) # node indices for this triangle
        origind=nodeprops.getAt(nodeinds[0]) # original element index
        val=regionfield.getAt(origind) # the region value for the original element in the original dataset

        if val in matrices: # original element was part of one of the regions being selected so add the triangle indices
            matrices[val].append(*nodeinds)

    return shareMatrices(*matrices.values())


@timing
def divideMeshSurfaceByRegion(dataset,regionfield,choosevals,task=None):
    '''
    Define a triangle mesh surface for the topologies in `dataset' and divide them into the regions chosen in `choosevals'
    as drawn from the region field `regionfield'. Returns the triangle dataset, index list from `dataset', and list of
    matrices containing the triangle indices for each region selected in `choosevals'. Returns the triangulation dataset,
    index matrix list, and the list of per-region matrices in no particular order.
    '''
    eidolon.calculateElemExtAdj(dataset,task=task)

    # calculate the triangulation of the original dataset and extract the triangle index and node properties matrices
    trids,indlist=eidolon.generateLinearTriangulation(dataset,'dividetris',0,True,task)
    tris=trids.getIndexSet(trids.getName()+eidolon.MatrixType.tris[1])
    nodeprops=trids.getIndexSet(trids.getName()+eidolon.MatrixType.props[1])

    assert len(indlist)==1,'Multiple spatial topologies found in mesh, cannot determine element value field association'
    assert indlist[0].n()==regionfield.n(),'Element value field length (%i) does not match topology length (%i)'%(regionfield.n(),indlist[0].n())

    # calculate the region division matrices
    proccount=eidolon.chooseProcCount(tris.n(),0,2000)
    shareMatrices(tris,nodeprops,regionfield)
    results= divideTrisByRegionRange(tris.n(),proccount,task,tris,nodeprops,regionfield,choosevals,partitionArgs=(choosevals,))
    matrices=listSum(list(map(list,results.values())))

    return trids,indlist,matrices


@concurrent
def calculateRegionThicknessesRange(process,trinodes,stddevRange,triindlist):
    '''
    Returns the averaged thickness of each triangle mesh given in `triindlist'. It is assumed that the name of each
    such topology matrix is of the form "choose_X_Y" where X is the ID of the process in divideTrisByElemValRange()
    which created the matrix, and Y corresponds to the region number that mesh belongs to. The return value is a list
    of pairs, one for each member of `triindlist', containing Y and the computed average thickness.
    '''
    results=[]

    maxlen=max(triind.n() for triind in triindlist)
    centers=Vec3Matrix('centers',maxlen)
    norms=Vec3Matrix('norms',maxlen)
    radii2=RealMatrix('radii2',maxlen)

    for triind in triindlist:
        # for each triangle, store the center, norm, and radius in the above matrices
        for n in range(triind.n()):
            nodes=trinodes.mapIndexRow(triind,n) # triangle nodes
            center=(nodes[0]+nodes[1]+nodes[2])/3.0 # triangle center
            centers.setAt(center,n) # store center
            norms.setAt(nodes[0].planeNorm(nodes[1],nodes[2]),n) # store triangle norm
            radii2.setAt(max(center.distToSq(v) for v in nodes),n) # store triangle radius**2

        # for each triangle, project a ray inward and store in `lengths' the distance of the first intersection with the mesh
        lengths=[]
        for n in range(triind.n()):
            center=centers.getAt(n)
            norm=norms.getAt(n)
            ray=eidolon.Ray(center,-norm)

            intres=ray.intersectsTriMesh(trinodes,triind,centers,radii2,1,n)

            if len(intres)>0:
                lengths.append(intres[0][1])

        avglen=avgDevRange(lengths,stddevRange)
        region=int(triind.getName().split('_')[2])
        results.append((region,avglen))

    return results


@timing
def calculateRegionThicknesses(datasetlist,regionfield,choosevals,stddevRange=1.0,task=None):
    '''
    Computes the region thicknesses for each mesh defines by the list of datasets in `datasetlist'. The value list
    `choosevals' defines the region numbers of interest, and `regionfield' is a field which labels each element of the
    mesh with a number; each value of `choosevals' must be found in this set of labels. For each dataset, the resulting
    list will contain a list of thickness values, one for each label in `choosevals'. Assuming the datasets represent
    a moving mesh in time, the rows of the returned matrix represent thickness in time, and the columns represent the
    thicknesses for each region.
    '''
    results=[]
    regionmap={v:i for i,v in enumerate(choosevals)} # maps region # to index in `choosevals'

    _,_,triindlist=divideMeshSurfaceByRegion(datasetlist[0],regionfield,choosevals,None)

    if task:
        task.setMaxProgress(len(datasetlist))

    for count,dataset in enumerate(datasetlist):
        if task:
            task.setProgress(count+1)

        nodes=dataset.getNodes()
        sumlens=sum(tris.n() for tris in triindlist)
        proccount=eidolon.chooseProcCount(sumlens,0,2000)
        shareMatrices(*(triindlist+[nodes]))
        thicknesses=calculateRegionThicknessesRange(sumlens,proccount,None,nodes,stddevRange,triindlist,partitionArgs=(triindlist,))

        thicknesslist=[v for i,v in sorted(listSum(list(thicknesses.values())))] # in same order as `choosevals'

        # calculate the per-region thickness field
        thicknessfield=RealMatrix('RegionThickness',regionfield.n())
        thicknessfield.meta(StdProps._spatial,regionfield.meta(StdProps._spatial))
        thicknessfield.meta(StdProps._topology,regionfield.meta(StdProps._topology))
        thicknessfield.meta(StdProps._elemdata,'True')
        thicknessfield.fill(0)

        for n in range(regionfield.n()):
            region=regionmap.get(int(regionfield.getAt(n)),-1)
            if region>=0:
                thicknessfield.setAt(thicknesslist[region],n)

        dataset.setDataField(thicknessfield)

        results.append(thicknesslist)

    return results


@concurrent
def calculateAvgDisplacementRange(process,orignodes,trinodes,stddevRange,triindlist):
    results=[]
    for triind in triindlist:
        allinds=set()

        for n in range(triind.n()):
            allinds.update(triind.getRow(n))

        lengths=[orignodes.getAt(i).distTo(trinodes.getAt(i)) for i in allinds]
        avglen=avgDevRange(lengths,stddevRange)

        results.append((int(triind.getName().split('_')[2]),avglen))

    return results


@timing
def calculateAvgDisplacement(datasetlist,regionfield,choosevals,stddevRange=1.0,task=None):
    results=[]
    orignodes=None
    trids,indlist,triindlist=divideMeshSurfaceByRegion(datasetlist[0],regionfield,choosevals,None)

    regionmap=dict((v,i) for i,v in enumerate(choosevals)) # maps region # to index in `choosevals'

    if task:
        task.setMaxProgress(len(datasetlist))

    for count,dataset in enumerate(datasetlist):
        if task:
            task.setProgress(count+1)

        nodes=dataset.getNodes()
        orignodes=orignodes or nodes
        sumlens=sum(tris.n() for tris in triindlist)
        proccount=eidolon.chooseProcCount(sumlens,0,2000)
        shareMatrices(*(triindlist+[nodes]))
        dists=calculateAvgDisplacementRange(sumlens,proccount,None,orignodes,nodes,stddevRange,triindlist,partitionArgs=(triindlist,))

        displist=[v for i,v in sorted(listSum(list(dists.values())))]

        dispfield=RealMatrix('RegionDisplacement',regionfield.n())
        dispfield.meta(StdProps._spatial,regionfield.meta(StdProps._spatial))
        dispfield.meta(StdProps._topology,regionfield.meta(StdProps._topology))
        dispfield.meta(StdProps._elemdata,'True')
        dispfield.fill(0)

        for n in range(regionfield.n()):
            region=regionmap.get(int(regionfield.getAt(n)),-1)
            if region>=0:
                dispfield.setAt(displist[region],n)

        dataset.setDataField(dispfield)

        results.append(displist)

    return results


@concurrent
def calculateLinTetVolumeRange(process,nodelist,fieldlist,inds,regionfield,choosevals):
    results=[]
    counter=1

    for nodes,volfield in zip(nodelist,fieldlist):
        process.setProgress(counter)
        counter+=1

        nodevols=dict((cv,0) for cv in choosevals)
        for n in range(inds.n()):
            val=regionfield.getAt(n)
            if val in nodevols:
                elemnodes=nodes.mapIndexRow(inds,n)
                vol=eidolon.calculateTetVolume(*elemnodes)
                nodevols[val]+=abs(vol)
#               volfield.setAt(vol,n)

        results.append([nodevols[cv] for cv in choosevals])

        for n in range(inds.n()):
            volfield.setAt(nodevols.get(regionfield.getAt(n),0),n)

    return results


@timing
def calculateLinTetVolume(datasetlist,regionfield,choosevals,task=None):
    nodelist=[ds.getNodes() for ds in datasetlist]
    inds=datasetlist[0].getIndexSet(regionfield.meta(StdProps._spatial)) #or first(datasetlist[0].enumIndexSets())

    assert inds,'Cannot find index set with name %r'%regionfield.meta(StdProps._spatial)
    assert inds.n()>0
    shareMatrices(inds,regionfield)
    shareMatrices(*nodelist)

    fieldlist=[RealMatrix('volumes',inds.n(),1,True) for i in range(len(nodelist))]

    for ds,f in zip(datasetlist,fieldlist):
        ds.setDataField(f)
        f.meta(StdProps._topology,inds.getName())
        f.meta(StdProps._spatial,inds.getName())

    results=calculateLinTetVolumeRange(len(nodelist),0,task,nodelist,fieldlist,inds,regionfield,choosevals,partitionArgs=(nodelist,fieldlist))

    return eidolon.sumResultMap(results)


@timing
def calculateMaskVolume(imgobj,calculateInner=True):
    volumes=[]
    voxelvol=eidolon.prod(imgobj.getVoxelSize()) # voxel volume
    
    with eidolon.processImageNp(imgobj) as im:
        for t in range(im.shape[3]):
            volsum=0
            for s in range(im.shape[2]):
                img=im[:,:,s,t]
                if img.max()>img.min():
                    binimg=(img==img.max()).astype(int)
                    
                    # to calculate the sum of the inside of a mask, subtract the outer mask from the filled mask
                    if calculateInner:
                        outer= binary_fill_holes(binimg).astype(int)
                        if np.any(outer!=binimg):
                            binimg=outer-binimg
                            
                    volsum+=np.sum(binimg)
                  
            volumes.append(volsum*voxelvol)
            
    return volumes
    

@timing
def calculateTorsion(datasetlist,aha,choosevals):
    '''
    Calculate the torsion of the motion mesh defined by the PyDataSet list `datasetlist' with region field `aha' and
    selected regions `choosevals'. Result is list of per-node matrices of twist angles in degrees, list of average twist
    angles for the apex nodes, list of average twist angles for the base nodes, and the centerline axis length.
    '''
    nodes=[ds.getNodes().clone() for ds in datasetlist]
    nodes0=nodes[0]
    length=nodes0.n()
    inds=datasetlist[0].getIndexSet(aha.meta(StdProps._spatial))
    results=[]
    apextwists=[]
    basetwists=[]

    assert inds and inds.n()>0,'Cannot find index set with name %r'%aha.meta(StdProps._spatial)

    baseinds=set()
    apexinds=set()

    for i in range(len(inds)):
        region=aha[i]
        if region in range(1,7):
            for ind in inds[i]:
                baseinds.add(ind)
        elif region in range(13,17):
            for ind in inds[i]:
                apexinds.add(ind)

    basepos=avg(nodes0[i] for i in baseinds) or vec3()
    apexpos=avg(nodes0[i] for i in apexinds) or vec3()
    longaxis=apexpos-basepos

    orient=rotator(longaxis,-vec3.Z())
    trans=transform(-basepos,vec3(1,1),orient,True)

    for n in nodes:
        n.mul(trans)  # transforms the meshes so that the centerline is Z axis and points are projected onto the XY plane

    for n,ds in zip(nodes,datasetlist):
        twist=RealMatrix('PointTwist',length,1)
        twist.fill(0)
        twist.meta(StdProps._spatial,aha.meta(StdProps._spatial))
        twist.meta(StdProps._topology,aha.meta(StdProps._topology))
        ds.setDataField(twist)
        results.append(twist)

        for i in range(length):
            startnode=nodes0[i]
            stepnode=n[i]
            crossz=startnode.cross(stepnode).z()
            twist[i]=math.degrees(startnode.angleTo(stepnode)*(1 if crossz<0 else -1))

        apextwists.append(avg(twist[i] for i in apexinds))
        basetwists.append(avg(twist[i] for i in baseinds))

    return results,apextwists,basetwists,longaxis.len()


@concurrent
def calculateTriAreasRange(process,nodes,inds,result):
    for i in process.prange():
        a,b,c=nodes.mapIndexRow(inds,i)
        result.setAt(max(eidolon.epsilon*10,a.triArea(b,c)),i) # ensure no 0-area triangles just in case


def calculateTriAreas(nodes,inds,task=None):
    assert inds.getType()==ElemType._Tri1NL and inds.m()==3,'Not a triangle topology'
    result=RealMatrix('areas',inds.n(),1,True)
    result.meta(StdProps._topology,inds.getName())
    result.meta(StdProps._spatial,inds.getName())

    shareMatrices(nodes,inds)
    proccount=eidolon.chooseProcCount(inds.n(),1,5000)
    calculateTriAreasRange(inds.n(),proccount,task,nodes,inds,result)
    return result


def calculateRegionSumField(field,regionfield,choosevals):
    sumfield=field.clone(field.getName()+'_'+regionfield.getName())
    sumfield.fill(0)

    summap={r:0 for r in choosevals}

    for n in range(field.n()): # sum per-region values
        v=field.getAt(n)
        r=int(regionfield.getAt(n))
        if r in summap:
            summap[r]=summap[r]+v

    for n in range(field.n()): # fill sumfield with region summations
        r=int(regionfield.getAt(n))
        if r in summap:
            sumfield.setAt(summap[r],n)

    return summap,sumfield


class CardiacMotionPropWidget(eidolon.QtWidgets.QWidget,Ui_CardiacMotionProp):
    def __init__(self,parent=None):
        eidolon.QtWidgets.QWidget.__init__(self,parent)
        self.setupUi(self)
        tb=self.toolBox
        tb.setCurrentIndex(0)
        # make the toolbox large enough for the current pane
        tb.currentChanged.connect(lambda i:tb.setMinimumHeight(tb.currentWidget().height()+tb.count()*30))
        tb.currentChanged.emit(0)


class CardiacMotionProject(Project):
    def __init__(self,name,parentdir,mgr):
        Project.__init__(self,name,parentdir,mgr)
        self.addHandlers()
        self.Measure=mgr.getPlugin('Measure')
        self.CardiacMotion=mgr.getPlugin('CardiacMotion')
        self.ReportCard=mgr.getPlugin('ReportCard')
        self.CardiacMotion.project=self
        self.header='\nCardiacMotion.createProject(%r,scriptdir+"/..")\n' %(self.name)
        self.alignprop=None
        self.numUnknownJobs=0
        self.reportcard=None

        for n in ConfigNames:
            self.configMap[n[0]]=''

        self.configMap[ConfigNames._serverport]=15000
        self.configMap[ConfigNames._serveraddr]='localhost'
        self.configMap[ConfigNames._adaptive]=0.9
        self.configMap[ConfigNames._jobids]=[]
        self.configMap[ConfigNames._paramfile]=self.CardiacMotion.patient1e4

        for o in list(mgr.enumSceneObjects()):
            mgr.removeSceneObject(o)

        self.logDir=self.getProjectFile('logs')
        self.backDir=self.logDir

    def create(self):
        '''Task routine set to run after the project is loaded which does extra setup or config operations.'''
        Project.create(self)

        if not os.path.isdir(self.logDir):
            os.mkdir(self.logDir)

        reportcardfile=self.getProjectFile(self.name+'.report')
        if not os.path.exists(reportcardfile):
            self.reportcard=self.ReportCard.createReportCard(self.name,reportcardfile)
            self.reportcard.save()
            self.mgr.addSceneObjectTask(self.reportcard)
            self.addObject(self.reportcard)
            #self.save()
        else:
            pass

    def getPropBox(self):
        prop=Project.getPropBox(self)

        # remove the UI for changing the project location
        eidolon.cppdel(prop.chooseLocLayout)
        eidolon.cppdel(prop.dirButton)
        eidolon.cppdel(prop.chooseLocLabel)

        self.alignprop=CardiacMotionPropWidget()
        prop.verticalLayout.insertWidget(prop.verticalLayout.count()-1,self.alignprop)

        self.alignprop.loadCineButton.clicked.connect(self._loadCineSeries)
        self.alignprop.morphoButton.clicked.connect(self._loadMorphoSeries)
        self.alignprop.loadNiftiButton.clicked.connect(self._loadNiftiFile)
        self.alignprop.loadMetaButton.clicked.connect(self._loadMetaFile)
        self.alignprop.loadVTKMeshButton.clicked.connect(self._loadVTKFile)
        self.alignprop.loadCHeartButton.clicked.connect(self._loadCHeartFiles)
        self.alignprop.magphaseButton.clicked.connect(self._loadMagFlow)

        self.alignprop.saveCHeartCheck.clicked.connect(self.updateConfigFromProp)

#       self.alignprop.alignCheckButton.clicked.connect(lambda:self.CardiacMotion.checkLongAxisAlign(str(self.alignprop.alignCheckBox.currentText()),str(self.alignprop.checkTargetBox.currentText())))

        self.alignprop.shortAxisBox.activated.connect(self.updateConfigFromProp)
        self.alignprop.saxsegBox.activated.connect(self.updateConfigFromProp)
        self.alignprop.templateBox.activated.connect(self.updateConfigFromProp)
        self.alignprop.regSubBox.activated.connect(self.updateConfigFromProp)
        self.alignprop.regInterBox.activated.connect(self.updateConfigFromProp)
        self.alignprop.trackedBox.activated.connect(self.updateConfigFromProp)
        self.alignprop.maskBox.activated.connect(self.updateConfigFromProp)

        self.alignprop.svrAddrBox.textChanged.connect(self.updateConfigFromProp)
        #self.alignprop.paramEdit.textChanged.connect(self.updateConfigFromProp)

        self.alignprop.mCropButton.clicked.connect(self._motionCropSeries)
        self.alignprop.alignButton.clicked.connect(self._alignButton)
#       self.alignprop.createTimeRegButton.clicked.connect(self._createTimeRegButton)
        self.alignprop.createSegButton.clicked.connect(self._createSegButton)
        self.alignprop.regButton.clicked.connect(self._rigidRegButton)
        self.alignprop.loadTagButton.clicked.connect(self._load3DTagSeries)
        self.alignprop.chooseParamButton.clicked.connect(self._chooseParamFile)
        self.alignprop.chooseNRegParamButton.clicked.connect(self._chooseNRegParamFile)
        self.alignprop.startButton.clicked.connect(self._startMotionJob)
        self.alignprop.startNregButton.clicked.connect(self._startNregMotion)
        self.alignprop.checkButton.clicked.connect(lambda:self._checkMotionJob())
        self.alignprop.killButton.clicked.connect(self._killJob)
        self.alignprop.tsOrderButton.clicked.connect(self._invertOrder)
        self.alignprop.tsSetButton.clicked.connect(self._setTimestep)
        self.alignprop.addOffsetButton.clicked.connect(self._offsetTimestep)
        self.alignprop.reorderButton.clicked.connect(self._reorderMulticycle)
        self.alignprop.prospectButton.clicked.connect(self._prospTimestep)
        self.alignprop.applyTrackButton.clicked.connect(self._applyTrackButton)
        self.alignprop.gridButton.clicked.connect(self._createGridButton)
        self.alignprop.resampleButton.clicked.connect(self._resampleImage)
        self.alignprop.extendButton.clicked.connect(self._extendImage)
        self.alignprop.tsExtrButton.clicked.connect(self._extractTimesteps)
        self.alignprop.isoCreateButton.clicked.connect(self._createIsoImage)
        self.alignprop.bbCropButton.clicked.connect(self._cropBoundBox)
        self.alignprop.emptyCropButton.clicked.connect(self._cropEmpty)
        self.alignprop.thicknessButton.clicked.connect(self._calculateThicknessButton)
        self.alignprop.avgdispButton.clicked.connect(self._calculateAvgDispButton)
        self.alignprop.volButton.clicked.connect(self._calculateVolumeButton)
        self.alignprop.maskvolButton.clicked.connect(self._calculateImageMaskVolumeButton)
        self.alignprop.strainButton.clicked.connect(self._calculateStrainButton)
        self.alignprop.strainMeshButton.clicked.connect(self._calculateStrainMeshButton)
        self.alignprop.torsionButton.clicked.connect(self._calculateTorsionButton)
        self.alignprop.squeezeButton.clicked.connect(self._calculateSqueezeButton)

        self.alignprop.keCalcButton.clicked.connect(self._calculateKineticEnergyButton)

        self.alignprop.isTagCheck.stateChanged.connect(lambda i:self._tagCheckBox(self.alignprop.isTagCheck.isChecked()))

        def fillFieldBox(objbox,fieldbox,allowNone=False):
            @objbox.currentIndexChanged.connect
            def fillAction(*args):
                obj=self.getProjectObj(str(objbox.currentText()))
                fields=['None'] if allowNone else []
                fields+=sorted(obj.datasets[0].fields.keys()) if obj else ['None']
                fillList(fieldbox,fields)

        fillFieldBox(self.alignprop.thickMeshBox,self.alignprop.thickFieldBox)
        fillFieldBox(self.alignprop.dispMeshBox,self.alignprop.dispFieldBox)
        fillFieldBox(self.alignprop.volMeshBox,self.alignprop.volFieldBox)
        fillFieldBox(self.alignprop.torsionMeshBox,self.alignprop.torsionFieldBox)
        fillFieldBox(self.alignprop.squeezeMeshBox,self.alignprop.squeezeFieldBox)

        fillFieldBox(self.alignprop.strainMeshBox,self.alignprop.strainMeshAHABox)

        eidolon.setCollapsibleGroupbox(self.alignprop.trackAdvBox,False)
        eidolon.setCollapsibleGroupbox(self.alignprop.legacyBox,False)
        eidolon.setWarningStylesheet(self.alignprop.trackAdvBox)

        @self.alignprop.tsExtrSrcBox.activated.connect
        def _fillTS(i=None):
            o=self.mgr.findObject(str(self.alignprop.tsExtrSrcBox.currentText()))
            if o:
                fillList(self.alignprop.tsExtrChooseBox,['Step %i @ Time %i'%its for its in enumerate(o.getTimestepList())])

        self.mgr.addFuncTask(self._checkTrackDirs) # check directories after everything else has loaded
        
        # TODO: disable choosing how the volume analysis works, this needs work to allow calculating tissue volume in a well presented way
        self.alignprop.volImageMaskInnerBox.setVisible(False) 

        return prop

    @timing
    def updatePropBox(self,proj,prop):
        Project.updatePropBox(self,proj,prop)

        eidolon.setChecked(self.configMap[ConfigNames._savecheart].lower()=='true',self.alignprop.saveCHeartCheck)

        sceneimgs=[o for o in self.memberObjs if isinstance(o,eidolon.ImageSceneObject)]
        scenemeshes=[o for o in self.memberObjs if isinstance(o,eidolon.MeshSceneObject)]

        names=sorted(o.getName() for o in sceneimgs)
        fillList(self.alignprop.regList,names)
        fillList(self.alignprop.manipImgBox,names)
        fillList(self.alignprop.bbCropSrcBox,names)
        fillList(self.alignprop.bbCropRefBox,names)
        fillList(self.alignprop.emptyCropImgBox,names)
        fillList(self.alignprop.resampleSrcBox,names)
        fillList(self.alignprop.extendSrcBox,names)
        fillList(self.alignprop.resampleTmpltBox,names)

        names=sorted(o.getName() for o in sceneimgs if o.isTimeDependent)
        fillList(self.alignprop.mCropSeriesBox,names)
        fillList(self.alignprop.regInterBox,names,self.configMap[ConfigNames._regintermed],'None')
        fillList(self.alignprop.tsExtrSrcBox,names)
        fillList(self.alignprop.trackedNregBox,names)
        fillList(self.alignprop.reorderSrcBox,names)
        fillList(self.alignprop.volImageMaskBox,names)

        names=sorted(o.getName() for o in sceneimgs if not o.is2D)
        fillList(self.alignprop.shortAxisBox,names,self.configMap[ConfigNames._shortaxis])
        fillList(self.alignprop.templateBox,names,self.configMap[ConfigNames._templateimg],'None')
        fillList(self.alignprop.trackedBox,names,self.configMap[ConfigNames._trackedimg])
        fillList(self.alignprop.maskBox,names,self.configMap[ConfigNames._maskimg],'None')
        fillList(self.alignprop.regSubBox,names,self.configMap[ConfigNames._regsubject])
        fillList(self.alignprop.gridImgBox,names)
        fillList(self.alignprop.isoCreateBox,names)
        fillList(self.alignprop.strainROIBox,names,defaultitem='None')
        fillList(self.alignprop.maskNregBox,names,defaultitem='None')

        fillList(self.alignprop.keMaskBox,names)
        fillList(self.alignprop.phaseXBox,names)
        fillList(self.alignprop.phaseYBox,names)
        fillList(self.alignprop.phaseZBox,names)

        names+=sorted(o.getName() for o in self.memberObjs if isinstance(o,SegSceneObject) and o.numContours()>1)
        fillList(self.alignprop.saxsegBox,names,self.configMap[ConfigNames._saxseg])

        names=sorted(o.getName() for o in sceneimgs+scenemeshes)
        fillList(self.alignprop.trackObjBox,names)

        names=sorted(o.getName() for o in scenemeshes)
        fillList(self.alignprop.thickMeshBox,names)

        names=sorted(o.getName() for o in scenemeshes if len(o.datasets)>1)
        fillList(self.alignprop.strainMeshBox,names)
        fillList(self.alignprop.dispMeshBox,names)
        fillList(self.alignprop.volMeshBox,names)
        fillList(self.alignprop.torsionMeshBox,names)
        fillList(self.alignprop.squeezeMeshBox,names)

        names=sorted(o.getName() for o in sceneimgs+scenemeshes if len(o.getTimestepList())>1)
        fillList(self.alignprop.tsSetObjBox,names)

        # make the field boxes repopulate themselves
        self.alignprop.thickMeshBox.currentIndexChanged.emit(self.alignprop.thickMeshBox.currentIndex())
        self.alignprop.dispMeshBox.currentIndexChanged.emit(self.alignprop.dispMeshBox.currentIndex())
        self.alignprop.volMeshBox.currentIndexChanged.emit(self.alignprop.volMeshBox.currentIndex())
        self.alignprop.strainMeshBox.currentIndexChanged.emit(self.alignprop.strainMeshBox.currentIndex())
        self.alignprop.torsionMeshBox.currentIndexChanged.emit(self.alignprop.torsionMeshBox.currentIndex())
        self.alignprop.squeezeMeshBox.currentIndexChanged.emit(self.alignprop.squeezeMeshBox.currentIndex())

        # fill tracking dirs boxes with directory names
        trackdirs=list(map(os.path.basename,self.CardiacMotion.getTrackingDirs()))
        fillList(self.alignprop.trackDataBox,trackdirs)
        fillList(self.alignprop.strainTrackBox,trackdirs)
        fillList(self.alignprop.strainMeshTrackBox,trackdirs)

        # refill the measurement plugin's known tracking sources
        self.Measure.removeTrackSource(self.CardiacMotion.applyMotionTrackPoints)
        for td in trackdirs:
            self.Measure.addTrackSource(td,self.CardiacMotion.applyMotionTrackPoints)

        # set heart rate if stored in the config map
        heartrate=self.configMap[ConfigNames._heartrateBPM]
        if heartrate and self.alignprop.bpmBox.value()==0:
            self.alignprop.bpmBox.setValue(heartrate)

        # server box values
        with eidolon.signalBlocker(self.alignprop.adaptBox,self.alignprop.svrAddrBox,self.alignprop.paramEdit):
            self.alignprop.adaptBox.setValue(self.configMap[ConfigNames._adaptive])
            self.alignprop.svrAddrBox.setText('%s:%i'%(self.configMap[ConfigNames._serveraddr],int(self.configMap[ConfigNames._serverport])))
            self.alignprop.paramEdit.setText(self.configMap[ConfigNames._paramfile])

        self.alignprop.tsExtrSrcBox.activated.emit(0)

    def updateConfigFromProp(self,*args):
        '''Read data into self.configMap from the UI.'''
        self.configMap[ConfigNames._shortaxis]=str(self.alignprop.shortAxisBox.currentText())
        self.configMap[ConfigNames._saxseg]=str(self.alignprop.saxsegBox.currentText())
        self.configMap[ConfigNames._templateimg]=str(self.alignprop.templateBox.currentText())
        self.configMap[ConfigNames._regsubject]=str(self.alignprop.regSubBox.currentText())
        self.configMap[ConfigNames._regintermed]=str(self.alignprop.regInterBox.currentText())
        self.configMap[ConfigNames._trackedimg]=str(self.alignprop.trackedBox.currentText())
        self.configMap[ConfigNames._maskimg]=str(self.alignprop.maskBox.currentText())
        self.configMap[ConfigNames._adaptive]=self.alignprop.adaptBox.value()
        self.configMap[ConfigNames._paramfile]=str(self.alignprop.paramEdit.text())
        self.configMap[ConfigNames._savecheart]=str(self.alignprop.saveCHeartCheck.isChecked())

        style=''
        try: # try to read the address and port correctly, any exceptions will be from bad formatting so change nothing in that case
            addr,port=str(self.alignprop.svrAddrBox.text()).split(':')
            port=int(port)
            addr=addr.strip()
            if port!=self.configMap[ConfigNames._serverport] or addr!=self.configMap[ConfigNames._serveraddr]:
                self.configMap[ConfigNames._serverport]=port
                self.configMap[ConfigNames._serveraddr]=addr
                self.saveConfig()
        except:
            style='color: rgb(255,0,0)'

        self.alignprop.svrAddrBox.setStyleSheet(style)

    def _readDicomHeartRate(self,series):
        heartrate=readDicomHeartRate(series)
        if heartrate is not None and not self.configMap[ConfigNames._heartrateBPM]:
            self.configMap[ConfigNames._heartrateBPM]=int(heartrate)

            rc=self.getReportCard()
            if rc:
                rc.setValue(series.seriesID,'Heart Rate (bpm)',heartrate)

    def renameObject(self,obj,oldname):
        newname=eidolon.getValidFilename(obj.getName())
        obj.setName(newname)

        conflicts=obj.plugin.checkFileOverwrite(obj,self.getProjectDir())
        if conflicts:
            raise IOError('Renaming object would overwrite the following project files: '+', '.join(map(os.path.basename,conflicts)))

        obj.plugin.renameObjFiles(obj,oldname)

        for n,v in self.checkboxMap.items():
            if v==oldname:
                self.checkboxMap[n]=newname

        for n,v in self.configMap.items():
            if v==oldname:
                self.configMap[n]=newname

        self.save()

    def getReportCard(self):
        return first(obj for obj in self.memberObjs if obj.getName()==self.name and isinstance(obj,ReportCardSceneObject))

    @taskmethod('Adding Object to Project')
    def checkIncludeObject(self,obj,task):
        '''Check whether the given object should be added to the project or not.'''

        # Only try to save objects that aren't already in the project and which are saveable
        # Important: this task method will be called after the project has loaded so won't ask to add things already in the project
        if not isinstance(obj,eidolon.SceneObject) or obj in self.memberObjs or obj.plugin.getObjFiles(obj) is None:
            return

        def _copy():
            self.mgr.removeSceneObject(obj)
            newname=self.CardiacMotion.getUniqueObjName(obj.getName())
            #self.mgr.renameSceneObject(obj,newname)
            obj.setName(newname)
            filename=self.getProjectFile(obj.getName())
            savecheart=self.configMap[ConfigNames._savecheart].lower()=='true'

            if isinstance(obj,eidolon.ImageSceneObject):
                self.CardiacMotion.saveToNifti([obj],True)
            elif isinstance(obj,eidolon.MeshSceneObject):
                if savecheart: # force CHeart saving is selected
                    self.CardiacMotion.CHeart.saveObject(obj,filename,setFilenames=True)
                else:
                    self.CardiacMotion.VTK.saveObject(obj,filename,setFilenames=True)
            else:
                obj.plugin.saveObject(obj,filename,setFilenames=True)

            self.mgr.addSceneObject(obj)
            Project.addObject(self,obj)

            self.save()

        pdir=self.getProjectDir()
        files=list(map(os.path.abspath,obj.plugin.getObjFiles(obj) or []))

        if not files or any(not f.startswith(pdir) for f in files):
            msg="Do you want to add %r to the project? This requires saving/copying the object's file data into the project directory."%(obj.getName())
            self.mgr.win.chooseYesNoDialog(msg,'Adding Object',_copy)

    def _checkTrackDirs(self):
        '''
        Check tracking directories for a file named `trackconfname', this should appear in tracking directories made
        later and will contain more information than the original job.ini files. If the file is missing, create it
        based on the source image chosen by the user if there is a choice, guess otherwise.
        '''
        def _fixDir(sceneimgs,trackdir,index):
            index=index[0]
            jfile=os.path.join(trackdir,'job.ini')
            tfile=os.path.join(trackdir,trackconfname)
            jdata=eidolon.readBasicConfig(jfile) if os.path.isfile(jfile) else {}
            imgobj=self.mgr.findObject(sceneimgs[index])

            if imgobj:
                name=imgobj.getName()
                timesteps=imgobj.getTimestepList()
                trans=tuple(imgobj.getVolumeTransform())
                vox=tuple(imgobj.getVoxelSize())
            else:
                name='UNKNOWN'
                timesteps=list(range(len(glob(os.path.join(trackdir,'*.dof.gz')))+1))
                trans=(0,0,0,1,1,1,0,0,0,False)
                vox=(1,1,1)

            jdata.update({
                JobMetaValues._trackobj     :name,
                JobMetaValues._numtrackfiles:len(timesteps)-1,
                JobMetaValues._tracktype    :TrackTypes._motiontrackmultimage if jdata else TrackTypes._gpunreg,
                JobMetaValues._timesteps    :timesteps,
                JobMetaValues._transform    :trans,
                JobMetaValues._pixdim       :vox,
            })

            eidolon.printFlush('Writing %r with data from %r'%(tfile,name))
            eidolon.storeBasicConfig(tfile,jdata)

        def _chooseSource(sceneimgs,trackdir):
            msg='''
            Due to developer oversight, the source image of tracking directories wasn't saved.
            Please select which object was tracked in directory %r:
            '''%os.path.basename(trackdir)

            callback=lambda i:_fixDir(sceneimgs,trackdir,i)

            # important: this is called in a function so that `callback' binds with fresh variables
            self.mgr.win.chooseListItemsDialog('Choose Source Image',textwrap.dedent(msg).strip(),sceneimgs,callback)

        imgs=[o for o in self.memberObjs if isinstance(o,eidolon.ImageSceneObject)]

        for d in glob(self.getProjectFile('*/')): # check each directory `d' to see if it has dof files but no `trackconfname' file
            numdofs=len(glob(os.path.join(d,'*.dof.gz')))

            if not os.path.isfile(os.path.join(d,trackconfname)) and numdofs:
                trackdir=d[:-1] # remove trailing /

                # choose correct length images
                sceneimgs=[o.getName() for o in imgs if len(o.getTimestepList())==(numdofs+1)]+["Don't know"]

                if len(sceneimgs)<=2: # 0 or 1 possibilities, choose first option which will be "Don't know" if no suitable images found
                    _fixDir(sceneimgs,trackdir,[0])
                else:
                    _chooseSource(sceneimgs,trackdir) # otherwise ask user which one to choose

    def _loadNiftiFile(self):
        filenames=self.mgr.win.chooseFileDialog('Choose NIfTI filename',filterstr='NIfTI Files (*.nii *.nii.gz)',chooseMultiple=True)
        if len(filenames)>0:
            f=self.CardiacMotion.loadNiftiFiles(filenames)
            self.mgr.checkFutureResult(f)

    def _loadMetaFile(self):
        filenames=self.mgr.win.chooseFileDialog('Choose MetaImage Header filename',filterstr='Header Files (*.mhd *.mha)',chooseMultiple=True)
        if len(filenames)>0:
            self.CardiacMotion.loadMetaFiles(filenames)

    def _alignButton(self):
        saxname=self.configMap[ConfigNames._shortaxis]
        segname=self.configMap[ConfigNames._saxseg]
        templatename=self.configMap[ConfigNames._templateimg]
#       timeregname=self.configMap[ConfigNames._saxtimereg]

        if templatename=='None':
            templatename=None

        if saxname=='':
            self.mgr.showMsg('A short axis stack must be loaded first.','Cannot Perform Alignment')
        elif segname=='':
            self.mgr.showMsg('A segmentation must be loaded first.','Cannot Perform Alignment')
        else:
            self.CardiacMotion.alignShortStack(saxname,segname,templatename)#,timeregname)

#   def _createTimeRegButton(self):
#       template=self.getProjectObj(self.configMap[ConfigNames._templateimg])
#       if not template or template=='None':
#           self.mgr.showMsg('No template image specified so nothing to time-register to.','Cannot Perform Operation')
#       else:
#           sax=self.getProjectObj(self.configMap[ConfigNames._shortaxis])
#           regobj=self.CardiacMotion.createTimeRegStack(template,sax)
#
#           self.mgr.addFuncTask(lambda:self.configMap.update({ConfigNames._saxtimereg:regobj().getName()}))

    def _createSegButton(self):
        saxname=self.configMap[ConfigNames._shortaxis]
#       timeregname=self.configMap[ConfigNames._saxtimereg]

        if not saxname: # and not timeregname:
            self.mgr.showMsg('A short axis stack must be loaded first.','Cannot Create Segmentation')
        else:
            self.CardiacMotion.createSegObject(saxname,SegmentTypes.LV)

    def _rigidRegButton(self):
        self.updateConfigFromProp()
        regnames=[str(i.text()) for i in self.alignprop.regList.selectedItems()]
        if len(regnames)>0:
            self.CardiacMotion.rigidRegisterStackList(self.configMap[ConfigNames._regsubject],self.configMap[ConfigNames._regintermed],regnames)

    def _motionCropSeries(self):
        seriesname=str(self.alignprop.mCropSeriesBox.currentText())
        filtersize=self.alignprop.filterSizeBox.value()
        threshold=self.alignprop.cropThresholdBox.value()
        f=self.CardiacMotion.cropMotionObject(seriesname,threshold,filtersize)
        self.mgr.checkFutureResult(f)

    def _cropBoundBox(self):
        srcname=str(self.alignprop.bbCropSrcBox.currentText())
        refname=str(self.alignprop.bbCropRefBox.currentText())
        mx=self.alignprop.bbXBox.value()
        my=self.alignprop.bbYBox.value()

        self.CardiacMotion.refImageCrop(srcname,refname,mx,my)

    def _cropEmpty(self):
        srcname=str(self.alignprop.emptyCropImgBox.currentText())
        self.CardiacMotion.emptyCropObject(srcname)

    def _loadCineSeries(self):
        params=[
            #ParamDef('mergeMulti','Merge Selected Series Into One Object',ParamType._bool,False),
            ParamDef('showCrop','Show Multiseries/Crop Dialog',ParamType._bool,False)
        ]
        results={}

        series=self.CardiacMotion.Dicom.showChooseSeriesDialog(subject='CINE',params=(params,lambda n,v:results.update({n:v})))
        if len(series)>0:
            if results.get('showCrop',False):
                objs=[self.CardiacMotion.Dicom.showTimeMultiSeriesDialog(series)]
                self.mgr.checkFutureResult(objs[0])
            else:
                objs=[self.CardiacMotion.Dicom.loadSeries(s) for s in series]
#               if results.get('mergeMulti',False):
#                   images=listSum(o.images for o in objs)
#                   ind=getStrListCommonality(o.getName() for o in objs)
#                   name=objs[0].getName()
#                   if ind:
#                       name=name[:ind]
#
#                   objs=[objs[0].plugin.createSceneObject(name,objs[0].source,images,objs[0].plugin,objs[0].isTimeDependent)]

            self._readDicomHeartRate(series[0])
            filenames=self.CardiacMotion.saveToNifti(objs)
            f=self.CardiacMotion.loadNiftiFiles(filenames)
            self.mgr.checkFutureResult(f)

    def _loadMorphoSeries(self):
        param=ParamDef('tsOffset','Dicom Trigger Time Additive Value',ParamType._int,50,-300,300,10)
        results={}

        series=self.CardiacMotion.Dicom.showChooseSeriesDialog(allowMultiple=False,params=([param],lambda n,v:results.update({n:v})),subject='Morphology')
        if len(series)>0:
            ts=results.get('tsOffset',40)
            suffix='_offset%i'%ts

            sobj=self.CardiacMotion.Dicom.loadSeries(series[0])
            self._readDicomHeartRate(series[0])
            filenames=self.CardiacMotion.saveToNifti([sobj])
            obj=self.CardiacMotion.loadNiftiFiles(filenames)
            self.mgr.addFuncTask(lambda:self.CardiacMotion.offsetTimesteps(obj()[0],suffix,ts))

    def _load3DTagSeries(self):
        params=[
            ParamDef('makeProspective','Prospective Timing',ParamType._bool,True),
            ParamDef('makeDetag','Make Detagged Image',ParamType._bool,True),
            ParamDef('loadPlanes','Include Plane-aligned Images',ParamType._bool,False)
        ]
        results={}
        series=self.CardiacMotion.Dicom.showChooseSeriesDialog(allowMultiple=False,params=(params,lambda n,v:results.update({n:v})),subject='3D Tag')

        if len(series)>0:
            obj=self.CardiacMotion.Dicom.loadSeries(series[0])
            self._readDicomHeartRate(series[0])
            makeProspective=results.get('makeProspective',True)
            loadPlanes=results.get('loadPlanes',False)
            makeDetag=results.get('makeDetag',True)

            f=self.CardiacMotion.load3DTagSeries(obj,makeProspective,loadPlanes,makeDetag)
            self.mgr.checkFutureResult(f)

    def _loadMagFlow(self):
        filename=self.mgr.win.chooseFileDialog('Choose Par filename',filterstr='Par Files (*.par *.PAR)',chooseMultiple=False)
        if filename:
            f=self.CardiacMotion.loadMagPhaseParRec(filename)
            self.mgr.checkFutureResult(f)

    def _loadVTKFile(self):
        filename=self.mgr.win.chooseFileDialog('Choose VTK Mesh filename',filterstr='VTK Files (*.vtk *.vtu)',chooseMultiple=False)
        if filename:
            f=self.CardiacMotion.loadVTKFile(filename)
            self.mgr.checkFutureResult(f)

    def _loadCHeartFiles(self):
        d=LoadDialog(self.mgr)
        params=d.getParams()

        if params:
            f=self.CardiacMotion.loadCHeartMesh(*params)
            self.mgr.checkFutureResult(f)

    def _setTimestep(self):
        objname=str(self.alignprop.tsSetObjBox.currentText())
        start=self.alignprop.tsStartBox.value()
        step=self.alignprop.tsStepBox.value()

        if objname:
            self.CardiacMotion.setObjectTimestep(objname,start,step)

    def _invertOrder(self):
        manipname=str(self.alignprop.manipImgBox.currentText())
        msg='This operation will invert the order of timesteps for this image, are you sure?'
        if manipname:
            self.mgr.win.chooseYesNoDialog(msg,'Timestep Ordering',lambda:self.CardiacMotion.invertTimesteps(manipname))

    def _offsetTimestep(self):
        offsetname=str(self.alignprop.manipImgBox.currentText())
        ts=self.alignprop.offsetBox.value()
        suffix='_offset%i'%ts
        msg='This operation will add the given value to the timesteps for this image, are you sure?'
        if offsetname:
            self.mgr.win.chooseYesNoDialog(msg,'Timestep Ordering',lambda:self.CardiacMotion.offsetTimesteps(offsetname,suffix,ts))

    def _prospTimestep(self):
        offsetname=str(self.alignprop.manipImgBox.currentText())
        msg='This operation will convert the timesteps for this image into prospective times, are you sure?'
        if offsetname:
            self.mgr.win.chooseYesNoDialog(msg,'Timestep Ordering',lambda:self.CardiacMotion.offsetTimesteps(offsetname,'_prospective',0,True))

    def _reorderMulticycle(self):
        name=str(self.alignprop.reorderSrcBox.currentText())
        f=self.CardiacMotion.reorderMulticycleImage(name,self.alignprop.reorderStartBox.value(),self.alignprop.reorderStepBox.value())
        self.mgr.checkFutureResult(f)

    def _chooseParamFile(self):
        filename=self.mgr.win.chooseFileDialog('Choose Parameter file')
        if filename:
            self.alignprop.paramEdit.setText(filename)
            self.configMap[ConfigNames._paramfile]=filename
            self.saveConfig()

    def _chooseNRegParamFile(self):
        filename=self.mgr.win.chooseFileDialog('Choose Parameter file')
        if filename:
            self.alignprop.paramNRegEdit.setText(filename)

    def _startMotionJob(self):
        self.updateConfigFromProp()
        trackimg=self.configMap[ConfigNames._trackedimg]
        maskimg=self.configMap[ConfigNames._maskimg]
        adaptive=self.configMap[ConfigNames._adaptive]
        paramfile=self.configMap[ConfigNames._paramfile]
        dirname=str(self.alignprop.trackDirEdit.text())
        isTagCheck=self.alignprop.isTagCheck.isChecked()

        if not os.path.isfile(paramfile):
            self.mgr.showMsg('Cannot file param file %r, using default file'%paramfile,'File Not Found')
            paramfile=self.CardiacMotion.patient1e6 if isTagCheck else self.CardiacMotion.patient1e4
            self.configMap[ConfigNames._paramfile]=paramfile

        if 'tagged' in trackimg and not isTagCheck:
            self.mgr.showMsg('Warning: IRTK will treat this image as tagged data since "tagged" is in the name, but the tagged image check is not selected','Warning')

        if maskimg in ('','None'):
            maskimg=None

        response=self.CardiacMotion.startMotionTrackJob(trackimg,maskimg,dirname,adaptive,paramfile)

        @taskroutine('Checking Motion Track Job')
        def _checkJob(task):
            name,msg=Future.get(response)

            assert name in (ServerMsgs._Except,ServerMsgs._RStart)

            if name==ServerMsgs._Except:
                self.mgr.showExcept(msg[1],'MotionTrackServer reported an exception when sending a job','Exception from Server')
            else:
                jid=msg[0]
                self.configMap[ConfigNames._jobids].append(jid)
                self.saveConfig()

        self.mgr.runTasks(_checkJob())
        self._checkMotionJob(False)

    def _checkMotionJob(self,checkActive=True):
        jids=self.configMap[ConfigNames._jobids]
        assert jids!=None

        if checkActive and not self.CardiacMotion.isServerAlive():
            self.mgr.callThreadSafe(fillList,self.alignprop.jobList,['MotionTrackServer not active.'])
            #self.mgr.showMsg('MotionTrackServer not active.','Server Check',False)
        else:
            @self.mgr.addFuncTask
            def _updateList():
                msgs,deadjobs=self.CardiacMotion.checkMotionTrackJobs(jids)
                self.mgr.callThreadSafe(fillList,self.alignprop.jobList,msgs)
                self.numUnknownJobs=len(deadjobs)
                for d in deadjobs:
                    self.configMap[ConfigNames._jobids].remove(d)

                self.saveConfig()

    def _startNregMotion(self):
        imgname=str(self.alignprop.trackedNregBox.currentText())
        maskname=str(self.alignprop.maskNregBox.currentText())
        trackname=str(self.alignprop.trackingNregName.text())
        paramfile=str(self.alignprop.paramNRegEdit.text())
        onefile=self.alignprop.oneFileCheck.isChecked()

        if self.alignprop.gpuNregCheck.isChecked():
            f=self.CardiacMotion.startGPUNRegMotionTrack(imgname,maskname,trackname,paramfile)
        else:
            f=self.CardiacMotion.startRegisterMotionTrack(imgname,maskname,trackname,paramfile,None,onefile)

        self.mgr.checkFutureResult(f)
        self.mgr.addFuncTask(lambda:self.mgr.callThreadSafe(self.updatePropBox,self,self.prop))

    def _killJob(self):
        ind=self.alignprop.jobList.currentRow()
        if ind>=0 and self.CardiacMotion.isServerAlive():
            def _killSelected():
                jid=self.configMap[ConfigNames._jobids][ind-self.numUnknownJobs]
                name,msg=self.CardiacMotion.sendServerMsg(ServerMsgs._Kill,(jid,))
                self._checkMotionJob()

            self.mgr.win.chooseYesNoDialog('Kill the selected running motion tracking job?','Kill',_killSelected)

    def _applyTrackButton(self):
        objname=str(self.alignprop.trackObjBox.currentText())
        trackname=str(self.alignprop.trackDataBox.currentText())

        f=self.CardiacMotion.applyMotionTrack(objname,trackname)
        self.mgr.checkFutureResult(f)

    def _resampleImage(self):
        objname=str(self.alignprop.resampleSrcBox.currentText())
        tmpltname=str(self.alignprop.resampleTmpltBox.currentText())
        isIso=self.alignprop.resampleIsoCheck.isChecked()
        f=self.CardiacMotion.resampleObject(objname,tmpltname,isIso)
        self.mgr.checkFutureResult(f)

    def _extendImage(self):
        objname=str(self.alignprop.extendSrcBox.currentText())
        x=self.alignprop.extendXBox.value()
        y=self.alignprop.extendYBox.value()
        z=self.alignprop.extendZBox.value()
        f=self.CardiacMotion.extendImageObject(objname,x,y,z)
        self.mgr.checkFutureResult(f)

    def _extractTimesteps(self):
        objname=str(self.alignprop.tsExtrSrcBox.currentText())
        self.CardiacMotion.extractTimestepsToObject(objname,[self.alignprop.tsExtrChooseBox.currentIndex()])

    def _createGridButton(self):
        name=str(self.alignprop.gridImgBox.currentText())
        self.CardiacMotion.createImageGrid(name,self.alignprop.gridW.value(),self.alignprop.gridH.value(),self.alignprop.gridD.value())

    def _createIsoImage(self):
        name=str(self.alignprop.isoCreateBox.currentText())
        #shapetype=str(self.alignprop.interpTypeBox.currentText())
        cropEmpty=self.alignprop.emptyCropBox.isChecked()
        spacing=self.alignprop.isoSizeBox.value()

        #if cropEmpty:
        #   name=self.CardiacMotion.emptyCropObject(name,False)

        f=self.CardiacMotion.createIsotropicObject(name,cropEmpty,spacing)
        self.mgr.checkFutureResult(f)

    def _calculateThicknessButton(self):
        objname=str(self.alignprop.thickMeshBox.currentText())
        fieldname=str(self.alignprop.thickFieldBox.currentText())
        percentThickness=self.alignprop.percentThickBox.isChecked()
        f=self.CardiacMotion.calculateMeshRegionThickness(objname,fieldname,percentThickness)
        self.mgr.checkFutureResult(f)

    def _calculateAvgDispButton(self):
        objname=str(self.alignprop.dispMeshBox.currentText())
        fieldname=str(self.alignprop.dispFieldBox.currentText())
        f=self.CardiacMotion.calculateMeshRegionAvgDisp(objname,fieldname)
        self.mgr.checkFutureResult(f)

    def _calculateVolumeButton(self):
        objname=str(self.alignprop.volMeshBox.currentText())
        fieldname=str(self.alignprop.volFieldBox.currentText())
        heartrate=self.alignprop.bpmBox.value()
        f=self.CardiacMotion.calculateMeshRegionVolume(objname,fieldname,heartrate)
        self.mgr.checkFutureResult(f)

    def _calculateImageMaskVolumeButton(self):
        objname=str(self.alignprop.volImageMaskBox.currentText())
        calculateInner=self.alignprop.volImageMaskInnerBox.isChecked()
        
        f=self.CardiacMotion.calculateImageMaskVolume(objname,calculateInner)
        self.mgr.checkFutureResult(f)

    def _calculateStrainButton(self):
        name=str(self.alignprop.strainROIBox.currentText())
        spacing=self.alignprop.strainSpacingBox.value()
        trackname=str(self.alignprop.strainTrackBox.currentText())
        griddims=(self.alignprop.strainWBox.value(),self.alignprop.strainHBox.value(),self.alignprop.strainDBox.value())

        f=self.CardiacMotion.calculateImageStrainField(name,griddims,spacing,trackname)
        self.mgr.checkFutureResult(f)

    def _calculateStrainMeshButton(self):
        objname=str(self.alignprop.strainMeshBox.currentText())
        ahafieldname=str(self.alignprop.strainMeshAHABox.currentText())
        trackname=str(self.alignprop.strainMeshTrackBox.currentText())
        spacing=self.alignprop.strainSpacingMeshBox.value()

        f=self.CardiacMotion.calculateMeshStrainField(objname,ahafieldname,spacing,trackname)
        self.mgr.checkFutureResult(f)

    def _calculateTorsionButton(self):
        objname=str(self.alignprop.torsionMeshBox.currentText())
        ahafieldname=str(self.alignprop.torsionFieldBox.currentText())

        f=self.CardiacMotion.calculateTorsion(objname,ahafieldname)
        self.mgr.checkFutureResult(f)

    def _calculateSqueezeButton(self):
        objname=str(self.alignprop.squeezeMeshBox.currentText())
        ahafieldname=str(self.alignprop.squeezeFieldBox.currentText())

        f=self.CardiacMotion.calculateSqueeze(objname,ahafieldname)
        self.mgr.checkFutureResult(f)

    def _calculateKineticEnergyButton(self):
        maskname=str(self.alignprop.keMaskBox.currentText())
        phaseXname=str(self.alignprop.phaseXBox.currentText())
        phaseYname=str(self.alignprop.phaseYBox.currentText())
        phaseZname=str(self.alignprop.phaseZBox.currentText())
        f=self.CardiacMotion.calculatePhaseKineticEnergy(maskname,phaseXname,phaseYname,phaseZname)
        self.mgr.checkFutureResult(f)

    def _tagCheckBox(self,isChecked):
        paramfile=str(self.alignprop.paramEdit.text())
        p1e4=self.CardiacMotion.patient1e4
        p1e6=self.CardiacMotion.patient1e6
        if paramfile in (None,'','<<Use Default>>',p1e4,p1e6):
            paramfile=p1e6 if isChecked else p1e4
            self.alignprop.paramEdit.setText(paramfile)
            self.configMap[ConfigNames._paramfile]=paramfile
            self.saveConfig()



class CardiacMotionPlugin(eidolon.ImageScenePlugin,IRTKPluginMixin):
    def __init__(self):
        eidolon.ImageScenePlugin.__init__(self,'CardiacMotion')
        self.project=None

    def init(self,plugid,win,mgr):
        eidolon.ImageScenePlugin.init(self,plugid,win,mgr)
        IRTKPluginMixin.init(self,plugid,win,mgr)
        self.ParRec=self.mgr.getPlugin('ParRec')
        if self.win!=None:
            self.win.addMenuItem('Project','CardMotionProj'+str(plugid),'&Cardiac Motion Project',self._newProjDialog)

    def _newProjDialog(self):
        def chooseProjDir(name):
            newdir=self.win.chooseDirDialog('Choose Project Root Directory')
            if len(newdir)>0:
                self.mgr.createProjectObj(name,newdir,CardiacMotionProject)

        self.win.chooseStrDialog('Choose Project Name','Project',chooseProjDir)

    def createProject(self,name,parentdir):
        if self.mgr.project==None:
            self.mgr.createProjectObj(name,parentdir,CardiacMotionProject)

    def getCWD(self):
        return self.project.getProjectDir()

    def getLogFile(self,filename):
        return os.path.join(self.project.logDir,eidolon.ensureExt(filename,'.log'))

    def getLocalFile(self,name):
        return self.project.getProjectFile(name)
    
    def getUniqueObjName(self,name):
        return self.project.getUniqueObjName(name)

    def addObject(self,obj):
        self.project.addObject(obj)
        if obj not in self.mgr.objs:
            self.mgr.addSceneObject(obj)
        self.project.save()

    def getServerAddrPort(self):
        addr=self.project.configMap[ConfigNames._serveraddr]
        port=self.project.configMap[ConfigNames._serverport]
        return addr,port

    def setServerAddrPort(self,addr,port):
        if self.project:
            if addr!=None:
                self.project.configMap[ConfigNames._serveraddr]=addr
            if port!=None:
                self.project.configMap[ConfigNames._serverport]=port

            self.project.saveConfig()

    @taskmethod('Load Nifti Files')
    def loadNiftiFiles(self,filenames,task=None):
        isEmpty=len(self.project.memberObjs)==0
        objs=IRTKPluginMixin.loadNiftiFiles(self,filenames)

        if isEmpty:
            self.mgr.callThreadSafe(self.project.updateConfigFromProp)
            self.project.save()

        return objs

    def loadMetaFiles(self,filenames):
        '''Same thing as loadNiftiFiles() just for MetaImage format.'''
        f=Future()
        @taskroutine('Loading Meta Files')
        def _loadMeta(filenames,task):
            with f:
                isEmpty=len(self.project.memberObjs)==0
                filenames=Future.get(filenames)
                objs=[]
                for filename in filenames:
                    filename=os.path.abspath(filename)

                    mobj=self.Meta.loadObject(filename)
                    niftiname=self.getUniqueLocalFile(splitPathExt(filename)[1])+'.nii'
                    self.Nifti.saveObject(mobj,niftiname)

                    nobj=self.Nifti.loadObject(niftiname)
                    self.project.addObject(nobj)
                    self.mgr.addSceneObject(nobj)
                    objs.append(nobj)

                if isEmpty:
                    self.mgr.callThreadSafe(self.project.updateConfigFromProp)
                    self.project.save()

                f.setObject(objs)

        return self.mgr.runTasks(_loadMeta(filenames),f)

    def loadCHeartMesh(self,xfile,tfile,elemtype):
        f=Future()
        @taskroutine('Loading CHeart Files')
        def _load(xfile,tfile,elemtype,task):
            with f:
                savecheart=self.project.configMap[ConfigNames._savecheart].lower()=='true'
                if savecheart:
                    newxfile=self.project.getProjectFile(os.path.split(xfile)[1])
                    eidolon.copyfileSafe(xfile,newxfile,True)
                    newtfile=self.project.getProjectFile(os.path.split(tfile)[1])
                    eidolon.copyfileSafe(tfile,newtfile,True)

                    obj=self.CHeart.loadSceneObject(newxfile,newtfile,elemtype,objname=splitPathExt(xfile)[1])
                else:
                    objname=splitPathExt(xfile)[1]
                    obj=self.CHeart.loadSceneObject(xfile,tfile,elemtype,objname=objname)
                    self.VTK.saveObject(obj,self.project.getProjectFile(objname),setFilenames=True)

                self.addObject(obj)
                f.setObject(obj)

        return self.mgr.runTasks(_load(xfile,tfile,elemtype),f)

    def loadVTKFile(self,filename,trans=transform()):
        f=Future()
        @taskroutine('Loading VTK')
        def _load(filename,task):
            with f:
                basename=self.getUniqueObjName(splitPathExt(filename)[1])
                vobj=self.VTK.loadFile(filename)
                vobj.datasets[0].getNodes().mul(trans)

                savecheart=self.project.configMap[ConfigNames._savecheart].lower()=='true'

                if savecheart:
                    self.CHeart.saveObject(vobj,self.getLocalFile(basename),setFilenames=True)
                else:
                    vobj.plugin.copyObjFiles(vobj,self.getLocalFile('.'))

                self.addObject(vobj)
                f.setObject(vobj)

        return self.mgr.runTasks(_load(filename),f)

    def loadMagPhaseParRec(self,filename):
        f=Future()
        @taskroutine('Loading Meta Files')
        def _load(filename,task):
            with f:
                objs=self.ParRec.loadObject(filename)

                if len(objs)!=2:
                    raise IOError('Loaded ParRec does not have 2 orientations, is this mag/phase?')

                magname=self.getUniqueShortName('Mag',objs[0].getName())
                phasename=self.getUniqueShortName('Phase',objs[0].getName())
                self.Nifti.saveObject(objs[0],self.getNiftiFile(magname))
                self.Nifti.saveObject(objs[1],self.getNiftiFile(phasename))

                objs=self.loadNiftiFiles([self.getNiftiFile(magname),self.getNiftiFile(phasename)])
                f.setObject(objs)

        return self.mgr.runTasks(_load(filename),f)

    def calculateMeshRegionThickness(self,objname,regionfieldname,percentThickness):
        f=Future()
        @taskroutine('Calculating Thickness')
        def _calcThickness(objname,regionfieldname,task):
            with f:
                obj=self.findObject(objname)
                regionfield=obj.datasets[0].getDataField(regionfieldname)
                stddevRange=1.0

                #assert len(obj.getTimestepList())>1
                assert regionfield!=None

                results=calculateRegionThicknesses(obj.datasets,regionfield,list(range(1,18)),stddevRange,task)

                obj.plugin.saveObject(obj,self.project.getProjectFile(obj.getName()),setFilenames=True)

                if percentThickness:
                    for m in range(len(results[0])):
                        val=results[0][m]/100.0
                        for n in range(len(results)):
                            results[n][m]/=val

                plotname=self.getUniqueObjName(objname+'_thickness')
                plottitle=objname+' Region Thickness'+(' (%% of initial)' if percentThickness else '')
                plotfilename=self.project.getProjectFile(plotname+'.plot')

                plot=self.Plot.createPlotObject(plotfilename,plotname,plottitle,results,obj.getTimestepList(),self.Plot.AHADockWidget,obj,isPercent=percentThickness)
                plot.save()

                rc=self.mgr.project.getReportCard()
                if rc:
                    value='(%% of initial)' if percentThickness else 'mm'
                    minthick,maxthick=minmax(listSum(results))
                    rc.setValue(objname,'Min Thickness %s'%value, minthick)
                    rc.setValue(objname,'Max Thickness %s'%value, maxthick)
                    rc.save()

                self.mgr.addSceneObject(plot)
                self.project.addObject(plot)
                self.project.save()
                f.setObject(plot)

        return self.mgr.runTasks(_calcThickness(objname,regionfieldname),f)

    def calculateMeshRegionAvgDisp(self,objname,regionfieldname):
        f=Future()
        @taskroutine('Calculating Average Displacement')
        def _calcDisp(objname,regionfieldname,task):
            with f:
                obj=self.findObject(objname)
                regionfield=obj.datasets[0].getDataField(regionfieldname)
                stddevRange=1.0

                assert len(obj.getTimestepList())>1
                assert regionfield!=None

                results=calculateAvgDisplacement(obj.datasets,regionfield,list(range(1,18)),stddevRange,task)

                obj.plugin.saveObject(obj,self.project.getProjectFile(obj.getName()),setFilenames=True)

                plotname=self.getUniqueObjName(objname+'_displace')
                plottitle=objname+' Region Average Displacement'
                plotfilename=self.project.getProjectFile(plotname+'.plot')

                plot=self.Plot.createPlotObject(plotfilename,plotname,plottitle,results,obj.getTimestepList(),self.Plot.AHADockWidget,obj)
                plot.save()

                rc=self.mgr.project.getReportCard()
                if rc:
                    mindisp,maxdisp=minmax(listSum(results))
                    rc.setValue(objname,'Min Avg Displacement', mindisp)
                    rc.setValue(objname,'Max Avg Displacement', maxdisp)
                    rc.save()

                self.mgr.addSceneObject(plot)
                self.project.addObject(plot)
                self.project.save()
                f.setObject(plot)

        return self.mgr.runTasks(_calcDisp(objname,regionfieldname),f)

    def calculateMeshRegionVolume(self,objname,regionfieldname,heartrate,regionrange=list(range(1,17))): #regionrange=range(18,24)
        f=Future()
        @taskroutine('Calculating Average Volume')
        def _calcVolume(objname,regionfieldname,heartrate,regionrange,task):
            with f:
                obj=self.findObject(objname)
                timesteps=obj.getTimestepList()
                heartrate=heartrate or (timesteps[-1]-timesteps[0]) # use given heart rate or image time length
                duration=60000.0/heartrate # 1 minute in ms over heart rate yields cycle duration in ms
                regionfield=obj.datasets[0].getDataField(regionfieldname)

                assert len(timesteps)>1
                assert regionfield!=None

                results=calculateLinTetVolume(obj.datasets,regionfield,regionrange,task) # results is indexed by timestep then region

                totals=[t/1000.0 for t in map(sum,results)] # total volume per timestep in mL
                minv,maxv=minmax(totals)
                assert minv<maxv,repr(totals)

                ejectfrac=(maxv-minv)*(100.0/maxv) # calculate ejection fraction percentage
                mincc=minv
                maxcc=maxv

                mintimes=[]
                for region in range(len(results[0])):
                    regionvals=[results[i][region] for i in range(len(results))]
                    mintimes.append(min(list(zip(regionvals,timesteps)))[1])

                mintimestddev=stddev(mintimes)
                sdiperc=mintimestddev*(100.0/duration)

                resultItems=(
                # BPM
                # duration
                    ('Timestep Volumes (mL)',totals),
                    ('ESV Volume (mL)',mincc),
                    ('EDV Volume (mL)',maxcc),
                    ('Stroke Volume (mL)',maxcc-mincc),
                    ('Ejection Fraction (%)',ejectfrac),
                    #('Region Minimum Volume Times (ms)',mintimes),
                    ('SDI Time (ms)', mintimestddev),
                    ('SDI (%)',sdiperc)
                )

                otherDataItems=dict(resultItems)

                # create the plot for the region volumes
                plotname=self.getUniqueShortName(objname,regionfieldname,'volume',complen=15)
                plottitle=objname+' Blood Pool Region Volume'
                plotfilename=self.project.getProjectFile(plotname+'.plot')

                plot=self.Plot.createPlotObject(plotfilename,plotname,plottitle,results,timesteps,self.Plot.AHAPoolDockWidget,obj,**otherDataItems)
                plot.save()

                self.mgr.addSceneObject(plot)
                self.project.addObject(plot)

                # create another plot for the total volume
                plotname=self.getUniqueShortName(objname,regionfieldname,'totalvol',complen=15)
                plottitle=objname+' Blood Pool Total Volume'
                plotfilename=self.project.getProjectFile(plotname+'.plot')

                plot1=self.Plot.createPlotObject(plotfilename,plotname,plottitle,[totals],timesteps,self.Plot.TimePlotWidget,obj,**otherDataItems)
                plot1.save()

                self.mgr.addSceneObject(plot1)
                self.project.addObject(plot1)
                self.project.save()

                rc=self.mgr.project.getReportCard()
                if rc:
                    for n,v in resultItems:
                        rc.setValue(objname,n,v)

                    rc.save()

                f.setObject([plot,plot1])

        return self.mgr.runTasks(_calcVolume(objname,regionfieldname,heartrate,regionrange),f)
    
    @taskmethod('Calculating Mask Image Volume')
    def calculateImageMaskVolume(self,objname,calculateInner,task=None):
        obj=self.findObject(objname)
        volumes=calculateMaskVolume(obj,calculateInner)
        
        volumes_mL=[v/1000.0 for v in volumes] # convert to mL
        minv,maxv=minmax(volumes_mL)
        assert minv<maxv,repr(volumes_mL)

        ejectfrac=(maxv-minv)*(100.0/maxv) # calculate ejection fraction percentage
        
        resultItems=(
            ('Mask Timestep Volumes (mL)',volumes_mL),
            ('Mask ESV Volume (mL)',minv),
            ('Mask EDV Volume (mL)',maxv),
            ('Mask Stroke Volume (mL)',maxv-minv),
            ('Mask Ejection Fraction (%)',ejectfrac),
        )
        
        otherDataItems=dict(resultItems)
        
        plotname=self.getUniqueShortName(objname,'maskvolume',complen=15)
        plottitle=objname+' Blood Pool Volume (Mask)'
        plotfilename=self.project.getProjectFile(plotname+'.plot')

        plot=self.Plot.createPlotObject(plotfilename,plotname,plottitle,[volumes_mL],obj.getTimestepList(),self.Plot.TimePlotWidget,obj,**otherDataItems)
        plot.save()

        self.mgr.addSceneObject(plot)
        self.project.addObject(plot)
        self.project.save()

        rc=self.mgr.project.getReportCard()
        if rc:
            for n,v in resultItems:
                rc.setValue(objname,n,v)

            rc.save()

        return plot

    def calculateMeshStrainField(self,objname,ahafieldname,spacing,trackname):
        def _makePlot(suffix,titlesuffix,values,obj):
            '''Create a AHA Plot object for the given region values.'''
            plotname=self.mgr.getUniqueObjName(objname+suffix)
            plottitle=objname+titlesuffix
            plotfilename=self.project.getProjectFile(plotname+'.plot')
            plot=self.Plot.createPlotObject(plotfilename,plotname,plottitle,values,obj.getTimestepList(),self.Plot.AHADockWidget,obj)
            plot.save()
            self.mgr.addSceneObject(plot)
            self.project.addObject(plot)
            return plot


        obj=self.findObject(objname)
        timesteps=obj.getTimestepList()
        trackdir=self.project.getProjectFile(trackname)
        conf=eidolon.readBasicConfig(os.path.join(trackdir,trackconfname))

        if not ahafieldname:
            raise ValueError('Need to provide an AHA field name''')

        if len(conf[JobMetaValues._timesteps])!=len(timesteps):
            raise ValueError('Mesh object has %i timesteps but tracking data has %i'%(len(timesteps),len(conf[JobMetaValues._timesteps])))

        f=Future()
        @taskroutine('Calculating strains')
        def _calc(task):
            with f:
                ds=obj.datasets[0]
                nodes=ds.getNodes()
                aha=ds.getDataField(ahafieldname)
                aharegions=list(range(1,18))
                imgtrans=transform(*conf[JobMetaValues._transform])

                task.setMaxProgress(len(timesteps))

                # get the index matrix defining the topology the AHA field is defined for
                if ds.hasIndexSet(aha.meta(StdProps._spatial)):
                    indmat=ds.getIndexSet(aha.meta(StdProps._spatial))
                else:
                    spatialmats=list(filter(eidolon.isSpatialIndex,ds.enumIndexSets()))
                    indmat=first(m for m in spatialmats if ElemType[m.getType()].dim==3) or first(spatialmats)

                # create a matrix assigning an AHA region to each node
                nodeaha=IndexMatrix('nodeaha',nodes.n(),1)
                nodeaha.fill(0) # assumes 0 is never used for a region number
                for n in range(indmat.n()):
                    elemaha=int(aha.getAt(n)) # AHA region for element n
                    # for each node of element n, assign it to region elemaha if it hasn't been already assigned
                    for ind in indmat.getRow(n):
                        nodeaha.setAt(nodeaha.getAt(ind) or elemaha,ind) # choose the first AHA region encountered for each node

                # calculate directional fields if necessary
                if not ds.hasDataField('radial'):
                    longaxis=imgtrans.getRotation()*vec3.Z()
                    radialf,longf,circumf=calculateLVDirectionalFields(ds,longaxis,'radial','longitudinal','circumferential')

                    for d in obj.datasets:
                        d.setDataField(radialf)
                        d.setDataField(longf)
                        d.setDataField(circumf)
                else:
                    radialf=ds.getDataField('radial')
                    longf=ds.getDataField('longitudinal')
                    circumf=ds.getDataField('circumferential')

                strainnodes=createStrainField(nodes,radialf,longf,circumf,spacing)
                strainnodes.setM(1) # make the nodes one long column so that they will be tracked like regular nodes

                # apply motion tracking using a dummy scene object
                initobj=eidolon.MeshSceneObject(obj.getName()+'_Strains',eidolon.PyDataSet('initds',strainnodes,[indmat]))
                trackobj=self.applyMotionTrack(initobj,trackname,False)

                # These matrices will contain one row per timestep, each row will have an averaged value for each
                # region, thus the matrices are indexed by timestep then region
                mavgstrains=[] # averages of maximal eigenvalue strain
                minavgstrains=[] # averages of minimal eigenvalue strain
                lavgstrains=[] # averages of longitudinal strain
                ravgstrains=[] # averages of radial strain
                cavgstrains=[] # averages of circumferential strain

                globalmavgstrains=[]
                globalminavgstrains=[]
                globallavgstrains=[]
                globalravgstrains=[]
                globalcavgstrains=[]

                # for each pairing of a dataset from the original object and from the tracked strain object,
                # compute the strain from the tracked object's data, storing the results in the original's
                # dataset and in the arrays of results above from which plots shall be made
                for i,ods in enumerate(obj.datasets):
                    inodes=trackobj.datasets[i].getNodes()
                    inodes.setM(7)

                    tensors=calculateStrainTensors(inodes,spacing) # calculate tensor matrices from each set of 7 points
                    maxeig,mineig=calculateTensorIndicatorEigen(tensors) # maximal/minimal eigenvector values
                    # strain in each direction computed by multiplying tensors by directions
                    longstrain=calculateTensorMul(tensors,longf,'longstrain')
                    radstrain=calculateTensorMul(tensors,radialf,'radstrain')
                    circstrain=calculateTensorMul(tensors,circumf,'circstrain')

                    # add each of the fields to the dataset
                    for df in (tensors,maxeig,mineig,radstrain,longstrain,circstrain):
                        df.meta(StdProps._topology,indmat.getName())
                        df.meta(StdProps._spatial,indmat.getName())
                        df.meta(StdProps._timecopy,'False')
                        ods.setDataField(df)

                    # create lists with one empty list for each region
                    mavgstrain=[list() for x in range(len(aharegions))]
                    minavgstrain=[list() for x in range(len(aharegions))]
                    lavgstrain=[list() for x in range(len(aharegions))]
                    ravgstrain=[list() for x in range(len(aharegions))]
                    cavgstrain=[list() for x in range(len(aharegions))]

                    # Go through each value in the strain fields, if their associated nodes are in a region of interest
                    # add the value to the appropriate sublist in the one the above list, otherwise zero the value out
                    for n in range(maxeig.n()):
                        region=nodeaha.getAt(n)-1
                        if (region+1) in aharegions: # if the node is in a region of interest, add its strain values to the lists
                            mavgstrain[region].append(maxeig.getAt(n))
                            minavgstrain[region].append(mineig.getAt(n))
                            lavgstrain[region].append(longstrain.getAt(n))
                            ravgstrain[region].append(radstrain.getAt(n))
                            cavgstrain[region].append(circstrain.getAt(n))
                        else: # otherwise zero out its entries so that strain outside the regions of interest are not stored
                            maxeig.setAt(0,n)
                            mineig.setAt(0,n)
                            longstrain.setRow(n,0,0,0)
                            radstrain.setRow(n,0,0,0)
                            circstrain.setRow(n,0,0,0)

                    # store the averages of the per-region lists in the total average lists
                    mavgstrains.append(list(map(avg,mavgstrain)))
                    minavgstrains.append(list(map(avg,minavgstrain)))
                    lavgstrains.append(list(map(avg,lavgstrain)))
                    ravgstrains.append(list(map(avg,ravgstrain)))
                    cavgstrains.append(list(map(avg,cavgstrain)))     

                    # global average strains minus last region (17)
                    globalmavgstrains.append(avg(matIter(mavgstrain[:-1])))
                    globalminavgstrains.append(avg(matIter(minavgstrain[:-1])))
                    globallavgstrains.append(avg(matIter(lavgstrain[:-1])))
                    globalravgstrains.append(avg(matIter(ravgstrain[:-1])))
                    globalcavgstrains.append(avg(matIter(cavgstrain[:-1])))

                    task.setProgress(i+1)

                # resave the object using its plugin, which must work otherwise the object couldn't have been saved already
                obj.plugin.saveObject(obj,self.project.getProjectFile(objname),setFilenames=True)

                # make bullseye plots of max strain the 3 directional strains
                p1=_makePlot('_maxstrain',' Region Average of Maximal Strain',mavgstrains,obj)
                p2=_makePlot('_longstrain',' Region Average of Magnitude of Longitudinal Strain',lavgstrains,obj)
                p3=_makePlot('_radstrain',' Region Average of Magnitude of Radial Strain',ravgstrains,obj)
                p4=_makePlot('_circstrain',' Region Average of Magnitude of Circumferential Strain',cavgstrains,obj)

                # create a graph plot of the global average strain maxima, minima, and average strain in the three directions
                plotname=self.mgr.getUniqueObjName(objname+'_globalstrain')
                plottitle=objname+' Global Average Strain'
                plotfilename=self.project.getProjectFile(plotname+'.plot')
                results=(globalmavgstrains,globalminavgstrains,globallavgstrains,globalravgstrains,globalcavgstrains)
                labels=('Global Maximal Strain','Global Minimal Strain','Global Longitudinal Strain','Global Radial Strain','Global Circumferential Strain')
                gplot=self.Plot.createPlotObject(plotfilename,plotname,plottitle,results,timesteps,self.Plot.TimePlotWidget,obj,labels=labels)
                gplot.save()

                # add the plot this way to avoid saving the project multiple times
                self.mgr.addSceneObject(gplot)
                self.project.addObject(gplot)

                # fill in the report card
                rc=self.mgr.project.getReportCard()
                if rc:
                    minm,maxm=minmax(matIter(mavgstrains))
                    rc.setValue(objname,'Min Avg Strain', minm)
                    rc.setValue(objname,'Max Avg Strain',maxm)
                    minm,maxm=minmax(matIter(lavgstrains))
                    rc.setValue(objname,'Min Avg Longitudinal Strain', minm)
                    rc.setValue(objname,'Max Avg Longitudinal Strain',maxm)
                    minm,maxm=minmax(matIter(ravgstrains))
                    rc.setValue(objname,'Min Avg Radial Strain', minm)
                    rc.setValue(objname,'Max Avg Radial Strain',maxm)
                    minm,maxm=minmax(matIter(cavgstrains))
                    rc.setValue(objname,'Min Avg Circumferential Strain', minm)
                    rc.setValue(objname,'Max Avg Circumferential Strain',maxm)

                    maxvt=max(zip(map(abs,globalmavgstrains),timesteps))
                    rc.setValue(objname,'Maximal Global Strain Peak (value,time)', maxvt)
                    minvt=max(zip(map(abs,globalminavgstrains),timesteps))
                    rc.setValue(objname,'Minimal Global Strain Peak (value,time)', minvt)
                    lvt=max(zip(map(abs,globallavgstrains),timesteps))
                    rc.setValue(objname,'Minimal Longitudinal Strain Peak (value,time)', lvt)
                    rvt=max(zip(map(abs,globalravgstrains),timesteps))
                    rc.setValue(objname,'Minimal Radial Strain Peak (value,time)', rvt)
                    cvt=max(zip(map(abs,globalcavgstrains),timesteps))
                    rc.setValue(objname,'Minimal Circumferential Strain Peak (value,time)', cvt)

                    rc.save()

                self.project.save()
                f.setObject((p1,p2,p3,p4,gplot))

        return self.mgr.runTasks(_calc(),f)

    def calculateImageStrainField(self,objname,griddims,spacing,trackname):
        f=Future()
        @taskroutine('Calculating Strains')
        def _calcStrains(task):
            with f:
                indname='inds'
                obj=self.findObject(objname)

                nodes,inds=eidolon.generateHexBox(*griddims)
                strainnodes=createStrainGrid(nodes,transform(),obj.getVolumeTransform(),spacing)
                strainnodes.setM(1)
                gridDS=eidolon.PyDataSet('initds',strainnodes,[(indname,ElemType._Hex1NL,inds)])
                initobj=eidolon.MeshSceneObject(obj.getName()+'_Grid',gridDS)
                trackobj=self.applyMotionTrack(initobj,trackname,False)

                task.setMaxProgress(len(trackobj.datasets))

                for i,ds in enumerate(trackobj.datasets):
                    nodes=ds.getNodes()
                    nodes.setM(7)

                    tensors=calculateStrainTensors(nodes,spacing)
                    strain,_=calculateTensorIndicatorEigen(tensors)
                    strain.meta(StdProps._topology,indname)
                    strain.meta(StdProps._spatial,indname)
                    ds.setDataField(strain)
                    ds.setNodes(nodes.subMatrix(nodes.getName(),nodes.n()))

                    task.setProgress(i+1)

                self.VTK.saveObject(trackobj,self.getLocalFile(trackobj.getName()),setFilenames=True)
                self.addObject(trackobj)
                f.setObject(trackobj)

        return self.mgr.runTasks(_calcStrains(),f)

    def calculateTorsion(self,objname,fieldname):
        f=Future()
        @taskroutine('Calculating Torsion')
        def _calcTorsion(objname,fieldname,task):
            with f:
                obj=self.findObject(objname)
                timesteps=obj.getTimestepList()
                sectimesteps=[t/1000.0 for t in timesteps]
                field=obj.datasets[0].getDataField(fieldname)

                nodetwists,apextwists,basetwists,axislen=calculateTorsion(obj.datasets,field,list(range(1,18)))

                twists=[a-b for a,b in zip(apextwists,basetwists)]
                torsions=[t/axislen for t in twists]

                results={'Apex Rotation (Degrees)':apextwists,'Base Rotation (Degrees)':basetwists,'Twist (Degrees)':twists}

                plotname=self.mgr.getUniqueObjName(objname+'_torsion')
                plottitle=objname+' Average Torsion'
                plotfilename=self.project.getProjectFile(plotname+'.plot')
                gplot=self.Plot.createPlotObject(plotfilename,plotname,plottitle,results,timesteps,self.Plot.TimePlotWidget,obj)
                gplot.save()

                self.mgr.addSceneObject(gplot)
                self.project.addObject(gplot)

                rc=self.mgr.project.getReportCard()
                if rc:
                    maxtwist=max(zip(twists,sectimesteps))
                    rc.setValue(objname,'Max Twist (degrees) and Time (seconds)',maxtwist)

                    maxtorsion=max(zip(torsions,sectimesteps))
                    rc.setValue(objname,'Max Torsion (degrees/mm) and Time (seconds)',maxtorsion)

                    rc.save()

                obj.plugin.saveObject(obj,self.project.getProjectFile(objname),setFilenames=True)

                self.project.save()
                f.setObject((twists,gplot))

        return self.mgr.runTasks(_calcTorsion(objname,fieldname),f)

    @taskmethod('Calculating Mesh Squeeze')
    def calculateSqueeze(self,objname,regionfieldname=None,regionvals=None,task=None):
        obj=self.findObject(objname)
        regionfield=obj.datasets[0].getDataField(regionfieldname or 'AHA')
        regionvals=regionvals or list(range(1,18)) # AHA regions
        initareas=None
        initsums=None
        initsumlist=None
        results=[]
        dss=[]

        for ds in obj.datasets:
            nodes=ds.getNodes()
            inds=first(i for i in ds.enumIndexSets() if i.m()==3)
            areas=calculateTriAreas(nodes,inds,task)
            summap,sumareas=calculateRegionSumField(areas,regionfield,regionvals)
            sumlist=[summap[i] for i in summap]

            if initareas==None: # store the first results for scaling subsequent results
                initareas=areas
                initsums=sumareas
                initsumlist=sumlist
            else: # store the areas as proportions of the initial areas
                areas.div(initareas)
                sumareas.div(initsums)

            ds.setDataField(areas)
            ds.setDataField(sumareas)
            results.append([(a/b if b!=0 else 0) for a,b in zip(sumlist,initsumlist)])

            dss.append((ds,nodes,inds,sumareas))

        # set the initial areas to be proportions of themselves to match subsequent frames
        initareas.fill(1)
        initsums.fill(1)

        plotname=objname+'_squeeze'
        plottitle=objname+' Region Squeeze'
        plotfilename=self.project.getProjectFile(plotname+'.plot')

        plot=self.Plot.createPlotObject(plotfilename,plotname,plottitle,results,obj.getTimestepList(),self.Plot.AHADockWidget,obj)
        plot.save()
        self.addObject(plot)

        obj.plugin.saveObject(obj,self.project.getProjectFile(objname),setFilenames=True)

        return dss

    def calculatePhaseKineticEnergy(self,maskname,phaseXname,phaseYname,phaseZname,maskval=2):
        mask=self.findObject(maskname)
        phasex=self.findObject(phaseXname)
        phasey=self.findObject(phaseYname)
        phasez=self.findObject(phaseZname)

        f=Future()
        @taskroutine('Calculating Phase Kinetic Energy')
        def _calcEnergy(mask,phasex,phasey,phasez,maskval,task):
            with f:
                energy=eidolon.cropObjectEmptySpace(mask,self.getUniqueObjName('EmptyMask'))
                eidolon.thresholdImage(energy,maskval-eidolon.epsilon,maskval+eidolon.epsilon,task)
                eidolon.binaryMaskImage(energy,maskval-eidolon.epsilon)

                voxelw,voxelh=energy.images[0].spacing
                energycalcfunc='sum([(vals[0]*10)**2,(vals[1]*10)**2,(vals[2]*10)**2])*vals[3]*(%r)'%((voxelw**3)*0.5)

                eidolon.mergeImages([phasex,phasey,phasez,energy],energy,energycalcfunc,task)

                energylist=[]
                for _,inds in energy.getTimestepIndices():
                    energylist.append(sum(eidolon.sumMatrix(energy.images[ii].img) for ii in inds))

                plotname=self.getUniqueShortName(mask.getName(),'Energy',complen=15)
                plottitle=mask.getName()+' Total Kinetic Energy'
                plotfilename=self.project.getProjectFile(plotname+'.plot')

                plot=self.Plot.createPlotObject(plotfilename,plotname,plottitle,[energylist],energy.getTimestepList(),self.Plot.TimePlotWidget,mask)
                plot.save()
                self.addObject(plot)

                self.saveToNifti([energy])
                self.addObject(energy)

        return self.mgr.runTasks(_calcEnergy(mask,phasex,phasey,phasez,maskval))


### Add plugin to environment

eidolon.addPlugin(CardiacMotionPlugin())

### Unit tests

class TestCardiacMotionPlugin(unittest.TestCase):
    def setUp(self):
        pass
        
    def tearDown(self):
        pass
    
#    def testTestVolume(self):
#        et=ElemType.Tet1NL
#        sizes=(1.0,2.0,3.0)
#        
#        nodes=listSum(eidolon.divideHextoTet(1))
#        inds=list(eidolon.group(range(len(nodes)),et.numNodes()))
#        
#        regionfield=eidolon.listToMatrix([1]*len(inds),'regionfield')
#        dsinds=('inds',ElemType._Tet1NL,inds)
#        
#        dds=[]
#        for size in sizes:
#            snodes=[vec3(*n)*vec3(size,0,0) for n in nodes] # scale nodes
#            dds.append(eidolon.PyDataSet('TestDS',snodes,dsinds))
#            
#        vols=calculateLinTetVolume(dds,regionfield,[1])
        
        
