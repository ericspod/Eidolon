#cython: nonecheck=True

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
Defines algorithms for generating representations and manipulating mesh data. Each representation creation algorithm
must have the arguments '(dataset,name,refine,externalOnly=False,task=None,**kwargs)' and return a (DataSet,index list)
tuple.
'''

from codeop import CommandCompiler

from .Utils import *
from .Concurrency import concurrent,chooseProcCount,cpu_count,checkResultMap
from .MathDef import GeomType,ElemType

import cython
cimport cython

from renderer.Renderer import IndexMatrix,RealMatrix,Vec3Matrix,ColorMatrix,vec3,color
from renderer.Renderer cimport IndexMatrix,RealMatrix,Vec3Matrix,ColorMatrix,vec3,color

import SceneUtils
cimport SceneUtils

from .SceneUtils import PyDataSet,Octree,BoundBox,Face,StdProps,shareMatrices,isSpatialIndex,MatrixType,findIndexSets,listToMatrix,calculateLinePlaneIntersect
from .SceneUtils cimport PyDataSet,Octree,BoundBox,Face,StdProps,shareMatrices,isSpatialIndex,MatrixType,findIndexSets,listToMatrix,calculateLinePlaneIntersect


def unitfuncLin(x):
    return x

def unitfuncInv(x):
    return 1.0-x

def unitfuncOne(x):
    return 1.0

def unitfuncZero(x):
    return 0.0

def unitfuncSin(x):
    return math.sin(0.5*x*math.pi)

def unitfuncCos1(x):
    return 1-math.cos(0.5*x*math.pi)

def unitfuncCos2(x):
    return (1-math.cos(x*math.pi))/2

def valuefuncAvg(vals):
    return avg(vals)

def valuefuncMag(vals):
    return mag(vals)

def valuefuncCol0(vals):
    return vals[0]

def valuefuncCol1(vals):
    return vals[1]

def valuefuncCol2(vals):
    return vals[2]

def valuefuncCol3(vals):
    return vals[3]

def valuefuncCol4(vals):
    return vals[4]

def vecfuncZero(vals):
    return vec3()

def vecfuncLinear(vals):
    return vec3(*vals[:3])

def vecfuncMag(vals):
    return vec3(valuefuncMag(vals))

def vecfuncX(vals):
    return vec3(valuefuncMag(vals),1,1)

def vecfuncY(vals):
    return vec3(1,valuefuncMag(vals),1)

def vecfuncZ(vals):
    return vec3(1,1,valuefuncMag(vals))

#UnitFunc=enum(
#   ('Linear','x'),
#   ('InvLinear','1.0-x'),
#   ('One','1.0'),
#   ('Zero','0.0'),
#   ('sin(x*(pi/2))','math.sin(0.5*x*math.pi)'),
#   ('1-cos(x*(pi/2))','1-math.cos(0.5*x*math.pi)'),
#   ('(1-cos(x*pi))/2','(1-math.cos(x*math.pi))/2'),
#   doc='Functions for mapping one scalar unit value (0<=x<=1) to another, used for fitting data values to curves and alpha calculations.',
#   valtype=(str,),
#)

## Functions for fitting raw field values to a scalar value
#ValueFunc=enum(
#   ('Average','avg(vals)'),
#   ('Magnitude','mag(vals)'),
#   ('Column 1','vals[0]'),
#   ('Column 2','vals[1]'),
#   ('Column 3','vals[2]'),
#   ('Column 4','vals[3]'),
#   ('Column 5','vals[4]'),
#   valtype=(str,),
#)

#VecFunc=enum(
#   ('Zero','vec3()'),
#   ('Linear','vec3(*vals)'),
#   ('Magnitude','vec3(mag(vals))'),
#   ('XAxis','vec3(mag(vals),1,1)'),
#   ('YAxis','vec3(1,mag(vals),1)'),
#   ('ZAxis','vec3(1,1,mag(vals))'),
#   valtype=(str,),
#)

UnitFunc=enum(
    ('Linear',unitfuncLin),
    ('InvLinear',unitfuncInv),
    ('One',unitfuncOne),
    ('Zero',unitfuncZero),
    ('sin(x*(pi/2))',unitfuncSin),
    ('1-cos(x*(pi/2))',unitfuncCos1),
    ('(1-cos(x*pi))/2',unitfuncCos2),
    doc='Functions for mapping one scalar unit value (0<=x<=1) to another, used for fitting data values to curves and alpha calculations.',
    valtype=(object,),
)

# Functions for fitting raw field values to a scalar value
ValueFunc=enum(
    ('Average',valuefuncAvg),
    ('Magnitude',valuefuncMag),
    ('Column 1',valuefuncCol0),
    ('Column 2',valuefuncCol1),
    ('Column 3',valuefuncCol2),
    ('Column 4',valuefuncCol3),
    ('Column 5',valuefuncCol4),
    doc="Functions for mapping a field row `vals' to a scalar value.",
    valtype=(object,),
)

VecFunc=enum(
    ('Zero',vecfuncZero),
    ('Linear',vecfuncLinear),
    ('Magnitude',vecfuncMag),
    ('XAxis',vecfuncX),
    ('YAxis',vecfuncY),
    ('ZAxis',vecfuncZ),
    doc="Functions for mapping a field row `vals' to a vec3 value.",
    valtype=(object,),
)


def createUnitFunc(unitfunc,label):
    if not unitfunc:
        return unitfuncLin
    elif unitfunc in UnitFunc:
        return UnitFunc[unitfunc]
    elif not isinstance(unitfunc,str):
        return unitfunc
    else:
        c=CommandCompiler()
        comp=c(unitfunc,label,'eval')
        return lambda x:eval(comp,globals(),{'x':x})


def createValFunc(valfunc,label):
    if not valfunc:
        return avg
    elif valfunc in ValueFunc:
        return ValueFunc[valfunc]
    elif not isinstance(valfunc,str):
        return valfunc
    else:
        c=CommandCompiler()
        comp=c(valfunc,label,'eval')
        return lambda vals:eval(comp,globals(),{'vals':vals,'vec3':vec3})


def createVec3Func(vecfunc,label,dim):
    if not vecfunc:
        if dim<=0:
            vecfunc='vec3(1)'
        elif dim==1:
            vecfunc='vec3(vals[0])'
        elif dim==2:
            vecfunc='vec3(vals[0],vals[1],0)'
        else:
            vecfunc='vec3(vals[0],vals[1],vals[2])'
    elif vecfunc in VecFunc:
        return VecFunc[vecfunc]
    elif not isinstance(vecfunc,str):
        return vecfunc

    c=CommandCompiler()
    comp=c(vecfunc,label,'eval')
    return lambda vals: eval(comp,globals(),{'vals':vals,'vec3':vec3})


def applyCoeffsVec3(tuple vecs,tuple coeffs):
    cdef vec3 result=vec3(),v
    cdef int i
    cdef float c

    for i in range(len(vecs)):
        v=vecs[i]
        c=coeffs[i]
        result+=(v*c)

    return result


def applyCoeffsColor(tuple cols,tuple coeffs):
    cdef color result=color(0,0,0,0),v
    cdef int i
    cdef float c

    for i in range(len(cols)):
        v=vecs[i]
        c=coeffs[i]
        result+=(v*c)

    return result


def applyCoeffsReal(tuple vals,tuple coeffs):
    cdef float result=0.0,v,c
    cdef int i

    for i in range(len(vals)):
        v=vecs[i]
        c=coeffs[i]
        result+=(v*c)

    return result


def createDataMatrices(name,indextype,includeUVW=False):
    '''
    This returns 4 matrices for the expected data suitable as renderable input for MeshSceneObject instances. The `name'
    value is used to as the prefix for the matrix names, the suffices are standard names from MatrixType which the
    MeshSceneObject will understand. The `indextype' parameter is MatrixType.tri or MatrixType.line to choose whether to
    define triangle or line render objects, or None if no index matrix is to be created. The return values are:
        nodes -- Vec3Matrix with 4 columns (node, normal, xi, uvw) if `includeUVW' or 3 (node, normal, xi) if not
        props -- IndexMatrix with 3 columns (elem index, face index, index matrix number) storing node properties
        extindices -- IndexMatrix of 1 column listing the elements in the index matrix which are external, ie. on the surface
        indices -- IndexMatrix of however many columns are stated in `indextype'[2], or is None if `indextype' is None
    '''
    nodes=Vec3Matrix(name+MatrixType.nodes[1],0,4 if includeUVW else 3) # (node, normal, xi), or (node, normal, xi, uvw) if textures used
    props=IndexMatrix(name+MatrixType.props[1],0,3) #  elem index, face index, index matrix number
    extindices=IndexMatrix(name+MatrixType.extinds[1],0,1) # list of external elements
    indices=IndexMatrix(name+indextype[1],0,indextype[2]) if indextype!=None else None # element definitions

    if indices:
        indices.meta(StdProps._isspatial,'True')

    return nodes,props,indices,extindices


def collectResults(Vec3Matrix nodes,IndexMatrix props,IndexMatrix indices,IndexMatrix extindices,dict results):
    '''
    Given a dictionary of results from a concurrent algorithm run, mapping process number to
    (node,nodeprop,indices,extindices) tuples, append this result information to the given matrices. The elemen indices
    in the results are all assumed to be 0-based and so are incremented as appropriate before being appended to `indices'.
    All matrices in `results' are cleared once used.
    '''
    cdef Vec3Matrix outnodes
    cdef IndexMatrix outprops,outinds,outext

    for i in sorted(results):
        outnodes,outprops,outinds,outext=results[i]

        if outnodes!=None:
            if outinds!=None:
                outinds.add(nodes.n())
            if outext!=None:
                outext.add(indices.n() if indices else nodes.n())

            nodes.append(outnodes)

            if props!=None and outprops!=None:
                props.append(outprops)

            if outinds!=None and indices!=None:
                indices.append(outinds)

            if outext!=None and extindices!=None:
                extindices.append(outext)

            outnodes.clear()
            outprops.clear()
            if outinds!=None:
                outinds.clear()
            if outext!=None:
                outext.clear()


@concurrent
def makeMeshOctreeRange(process,Vec3Matrix nodes,IndexMatrix inds,int depth,vec3 dim,vec3 center):
    cdef Octree l,oc=Octree(depth,dim,center)
    cdef IndexMatrix result
    cdef list sparseindices,leaves
    cdef set leaf
    cdef int n,count,rlen

    # for each element `n', insert the index into each leaf which contains one of its nodes, elements can be in multiple leaves
    for n in process.nrange():
        for node in nodes.mapIndexRow(inds,n):
            oc.addLeafData(node,n)

    leaves=[set(l.leafdata) for l in oc.getLeaves()]
    rlen=sum(len(leaf) for leaf in leaves)

    result=IndexMatrix('%s%s%i'%(inds.getName(),MatrixType.octree[1],process.index),rlen,1,True)
    sparseindices=[0]
    count=0

    # construct a sparse row matrix by appending all the elements for each leaf, storing the index where each leaf starts
    for leaf in leaves:
        for i,v in enumerate(leaf):
            result.mat.ats(count+i,0,v)

        count+=len(leaf)
        sparseindices.append(count)

    result.meta(StdProps._sparsematrix,str(sparseindices))
    return result


def getDatasetOctrees(dataset,int depth=2,acceptFunc=isSpatialIndex,task=None):
    '''
    Returns the octree sparse row matrices for each index set in `dataset' satisfying the predicate `acceptFunc'. If no
    octree was found a matrix, one is generated with `depth' as its depth parameter. The octree matrices contain the
    octree paramers in their StdProps._octreedata metadata values and the sparse row indices in StdProps._sparsematrix.
    '''
    cdef Vec3Matrix nodes=dataset.getNodes()
    cdef IndexMatrix inds,ocmat,s
    cdef BoundBox aabb=BoundBox(nodes)
    cdef vec3 dim=aabb.getDimensions()
    cdef vec3 center=aabb.center
    cdef str ocname
    cdef int proccount,count,i
    cdef list ocmatinds,subinds
    cdef dict trees={}
    cdef object acceptedInds=list(filter(acceptFunc,dataset.enumIndexSets()))

    for inds in acceptedInds:
        ocname=inds.getName()+MatrixType.octree[1]
        ocmat=dataset.getIndexSet(ocname)

        if not ocmat:
            proccount=chooseProcCount(inds.n(),0,1000)
            if proccount!=1:
                shareMatrices(nodes,inds)

            result=makeMeshOctreeRange(inds.n(),proccount,task,nodes,inds,depth,dim,center)
            submats=result.values()
            subinds=[eval(s.meta(StdProps._sparsematrix)) for s in submats]

            ocmat=IndexMatrix(ocname,sum(s.n() for s in submats),1,True)
            count=0
            ocmatinds=[0]

            # construct a sparse row matrix by amalgamating those generated in the other processes
            for leaf in range(8**depth):
                for i,s in enumerate(submats):
                    start=subinds[i][0] # row start index
                    end=subinds[i][1] # row end index
                    subinds[i].pop(0) # remove the first index so that the next iteration of the outer loop goes to the next row

                    for j in xrange(start,end):
                        ocmat.mat.ats(count,0,s.mat.atc(j,0))
                        count+=1

                ocmatinds.append(count)

            ocmat.meta(StdProps._sparsematrix,str(ocmatinds))
            ocmat.meta(StdProps._octreedata,str((depth,tuple(dim),tuple(center))))
            dataset.setIndexSet(ocmat)

        trees[inds]=ocmat

    return trees


@concurrent
def calculateOctantExtAdjRange(process,IndexMatrix octree,IndexMatrix indmat,IndexMatrix adj,IndexMatrix ext):
    '''
    Calculate face normals, face adjacencies, and determine which elements have external (boundary) faces. Each octant
    will contain the index of each element that has at least one vertex in its bound box. This guarantees that any two
    elements with adjacent faces will be referenced by the same octant, but may also both appear in a neighbouring octant.
    '''
    cdef Face f,ff
    cdef int e,elem,start,end,face
    cdef dict uniques
    cdef object elemtype=ElemType[indmat.getType()]
    cdef int numfaces=elemtype.numFaces()
    cdef list sparseinds=eval(octree.meta(StdProps._sparsematrix))

    # traverse only certain rows of the octree matrix assigned to this process
    for leaf in process.prange():
        uniques={}
        start=sparseinds[leaf] # start of octree leaf row
        end=sparseinds[leaf+1] # end of octree leaf row

        # For each element in the leaf, create the Face object for each face. If this object is not in `uniques'
        # then add it. If it is already in `uniques' then the element's face is adjacent to a face of the element
        # the stored Face object refers to, thus the adjacency and external matrices can be filled in. The important
        # feature of the Face type is that equivalence only takes face indices into account, not element or face ID.
        for e in range(start,end):
            elem=octree.getAt(e)
            for face in range(numfaces):
                f=Face.fromElem(indmat,elem,face,elemtype)
                if f in uniques: # face encountered a second time so must be internal
                    ff=uniques.pop(f) # ff is not the same object as f but the face adjacent to it
                    adj.mat.ats(ff.elemid,ff.faceid,f.elemid) # the face ff.faceid of element ff.elemid is adjacent to element f.elemid
                    adj.mat.ats(ff.elemid,ff.faceid+numfaces,f.faceid) # the face ff.faceid of element ff.elemid is adjacent to face f.faceid
                    ext.mat.ats(ff.elemid,ff.faceid,0) # the face ff.faceid of element ff.elemid is internal
                    # this stores the same as the above, just for the current face
                    adj.mat.ats(elem,face,ff.elemid)
                    adj.mat.ats(elem,face+numfaces,ff.faceid)
                    ext.mat.ats(elem,face,0)
                else:
                    uniques[f]=f # newly encountered face, add it


@timing
def calculateElemExtAdj(dataset,object acceptIndex=lambda i:isSpatialIndex(i,3),int treedepth=2,task=None):
    '''
    For each index matrix which is acceptable according to 'acceptIndex', this generates an external face index
    and a normal index, and adds the normal vectors to the node list. Each new index's name is the original index's
    name plus the appropriate suffix in MatrixType. For each element in the original matrix, the normal matrix
    stores a line with a node index for each face in the same order, so eg. a tet will have a line with 4 indices.
    The external matrix stores 2 indices for each external face in the original matrix, the first value being the
    element index and the second the face number.
    '''

    cdef IndexMatrix indmat,octree, adj, ext
    cdef str adjname,extname
    cdef int proccount,depth
    cdef dict trees=getDatasetOctrees(dataset,treedepth,acceptIndex)

    for indmat,octree in trees.items():
        adjname=indmat.getName()+MatrixType.adj[1]
        extname=indmat.getName()+MatrixType.external[1]

        if not dataset.hasIndexSet(adjname):
            elemtype=ElemType[indmat.getType()]
            if not elemtype.faces: # no face information available, cannot perform adjacency determination
                continue

            proccount=chooseProcCount(indmat.n(),0,2000)

            adj=IndexMatrix(adjname,MatrixType._adj,indmat.n(),elemtype.numFaces()*2,proccount!=1)
            ext=IndexMatrix(extname,MatrixType._external,indmat.n(),elemtype.numFaces(),proccount!=1)
            ext.fill(1) # all faces are first assumed to be external until they are found to be adjacent to others

            dataset.setIndexSet(adj)
            dataset.setIndexSet(ext)

            depth=eval(octree.meta(StdProps._octreedata))[0]

            if proccount!=1:
                shareMatrices(octree,indmat)

            calculateOctantExtAdjRange(8**depth,proccount,task,octree,indmat,adj,ext)


@concurrent
def calculateTriRange(process,IndexMatrix ind,Vec3Matrix nodes,IndexMatrix ext,int refine,bint externalOnly,int indnum):
    cdef object elemtype=ElemType[ind.getType()]
    cdef str name='calculateTrisRange'
    cdef bint isExt,flatnormals=elemtype.order==1
    cdef Vec3Matrix outnodes
    cdef IndexMatrix outprops,outinds,outext
    cdef int i,facemult,nlen,face,numfaces=elemtype.numFaces()
    cdef tuple elemnodes,c,c0,c1,c2
    cdef vec3 n1,n2,norm,xi

    assert elemtype.geom in (GeomType._Tri,GeomType._Quad,GeomType._Hex, GeomType._Tet)
    assert not ext or numfaces<=ext.m()
    assert process.maxval<=ind.n()

    outnodes,outprops,outinds,outext=createDataMatrices(name+str(process.index),MatrixType.tris)

    facemeshes=SceneUtils.calculateFaceMeshes(elemtype,refine,SceneUtils.divideTritoTriMesh,SceneUtils.divideQuadtoTriMesh)

    count=0
    for elem in process.prange():
        elemnodes=nodes.mapIndexRow(ind,elem)
        nlen=len(elemnodes)

        for face in range(numfaces):
            isExt=(ext==None or ext.mat.atc(elem,face)==1)
            if not isExt and externalOnly: # skip internal faces if externalOnly is True
                continue

            coeffs,indmat=facemeshes[face]
            count+=indmat.n()
            norm=None

            if isExt: # if this face is external, add the indices for each triangle of the face
                for i in range(indmat.n()):
                    outext.append(outinds.n()+i)

            indmat.sub(indmat.getAt(0,0)) # reset the indexing from 0
            indmat.add(outnodes.n()) # shift the indexing forward to cover new nodes
            outinds.append(indmat) # add the indices

            # calculate each node of this face's triangle mesh from coefficients stored in coeffs
            for i in range(coeffs.n()):
                c=coeffs.getRow(i)
                xi=vec3(*c[:3])
                c0=c[3:3+nlen]
                c1=c[3+nlen:3+nlen*2]
                c2=c[3+nlen*2:]

                node=applyCoeffsVec3(elemnodes,c0)
                if not norm or not flatnormals:
                    n1=applyCoeffsVec3(elemnodes,c1)
                    n2=applyCoeffsVec3(elemnodes,c2)
                    norm=node.planeNorm(n1,n2)

                outnodes.append(node,norm,xi)
                outprops.append(elem,face,indnum)

    return shareMatrices(outnodes,outprops,outinds,outext)


@timing
def generateTriDataSet(dataset,str name,int refine,bint externalOnly=False,task=None,**kwargs):
    cdef Vec3Matrix nodes=dataset.getNodes(),outnodes
    cdef IndexMatrix ind,ext,adj,nodeprops,indices,extindices
    cdef int proccount
    cdef dict result
    cdef list indlist=[]

    outnodes,nodeprops,indices,extindices=createDataMatrices(name,MatrixType.tris)
    indices.setType(ElemType._Tri1NL)

    # generate data for each index set which is spatial and defines 2D or 3D elements
    for ind,ext,adj in findIndexSets(dataset,acceptFunc=lambda ind: isSpatialIndex(ind,2)):
        shareMatrices(nodes,ind,ext)
        proccount=chooseProcCount(ind.n()*ElemType[ind.getType()].order,refine,2000)

        result=calculateTriRange(ind.n(),proccount,task,ind,nodes,ext,refine,externalOnly,len(indlist))
        indlist.append(ind)

        collectResults(outnodes,nodeprops,indices,extindices,result)

#    if indices.n()==0:
#        raise ValueError('Dataset contains no data suitable for triangle generation')

    ds=PyDataSet(name,outnodes,[nodeprops,extindices,indices],dataset.fields)
    ds.validateDataSet()
    return ds,indlist


@concurrent
def generateMeshPlanecutRange(process,str name,vec3 pt,vec3 norm,float width,Vec3Matrix innodes,ColorMatrix nodecolors,IndexMatrix inds,IndexMatrix octree,list slicedleaves):
    cdef tuple indextype=MatrixType.lines if width==0 else MatrixType.tris
    cdef Vec3Matrix nodes=Vec3Matrix(name+MatrixType.nodes[1],0,2)
    cdef IndexMatrix indices=IndexMatrix(name+indextype[1],0,indextype[2])
    cdef ColorMatrix colors=ColorMatrix(name+'cols',0,1)
    cdef object elemtype=ElemType.Tri1NL
    cdef int e,elem,n
    cdef tuple elemnodes,elemcols,elemxis
    cdef list elemdists
    cdef vec3 xi1,xi2,q1,q2,q3,q4,n1,n2,ee,e1,e2,e3
    cdef color c1,c2,ec1,ec2,ec3
    cdef bint isTri=inds.m()==3

    for p in process.prange():
        for e in range(*slicedleaves[p]):
            elem=octree.mat.atc(e,0)
            elemxis=None

            if isTri:
                e1,e2,e3=innodes.mapIndexRow(inds,elem)
                elemxis=SceneUtils.calculateLinearTriIsoline(e1.planeDist(pt,norm),e2.planeDist(pt,norm),e3.planeDist(pt,norm))

                if elemxis:
                    ec1,ec2,ec3=nodecolors.mapIndexRow(inds,elem)
                    xi1,xi2=elemxis

                    n1=SceneUtils.linTriInterp(xi1.x(),xi1.y(),e1,e2,e3)
                    n2=SceneUtils.linTriInterp(xi2.x(),xi2.y(),e1,e2,e3)
                    c1=SceneUtils.linTriInterp(xi1.x(),xi1.y(),ec1,ec2,ec3)
                    c2=SceneUtils.linTriInterp(xi2.x(),xi2.y(),ec1,ec2,ec3)
            else:
                e1,e2=innodes.mapIndexRow(inds,elem)
                elemxis=calculateLinePlaneIntersect(e1,e2,pt,norm)
                if elemxis:
                    ec1,ec2=nodecolors.mapIndexRow(inds,elem)
                    n1=e1.lerp(clamp(elemxis[1]-0.01,0,1),e2).planeProject(pt,norm)

                    if width>0: # make the line `width' long in the direction of the line's projection on the plane
                        n1=(n1-elemxis[0]).norm()*(width/2)
                        n2=elemxis[0]-n1
                        n1=elemxis[0]+n1
                    else:
                        n2=e1.lerp(clamp(elemxis[1]+0.01,0,1),e2).planeProject(pt,norm)

                    c1=ec1.interpolate(elemxis[1],ec2)
                    c2=ec2

            if elemxis:
                n=nodes.n()
                if width==0: # 1D line
                    indices.append(n,n+1)
                    nodes.append(n1,norm)
                    nodes.append(n2,norm)
                    colors.append(c1)
                    colors.append(c2)
                else: # 2D quad
                    q1,q2,q3,q4=SceneUtils.generateQuadFromLine(n1,n2,norm,width)

                    indices.append(n,n+2,n+1)
                    indices.append(n+1,n+2,n+3)
                    nodes.append(q1,norm)
                    nodes.append(q2,norm)
                    nodes.append(q3,norm)
                    nodes.append(q4,norm)
                    colors.append(c1)
                    colors.append(c1)
                    colors.append(c2)
                    colors.append(c2)

    return shareMatrices(nodes,indices,colors) if process.total>1 else (nodes,indices,colors)


def generateMeshPlanecut(dataset,str name,vec3 pt,vec3 norm,float width,int treedepth=3,ColorMatrix nodecolors=None,task=None,**kwargs):
    cdef object acceptIndex=lambda i:isSpatialIndex(i) and ElemType[i.getType()].geom in (GeomType._Tri,GeomType._Line)
    cdef dict trees=getDatasetOctrees(dataset,treedepth,acceptIndex)
    cdef Vec3Matrix nodes=None,dnodes,inodes
    cdef IndexMatrix indices=None,indmat=None,octree=None,iinds,
    cdef ColorMatrix cols=None,icols

    if trees:
        indmat,octree=first(trees.items()) # TODO: cut only the first topology for now
        dnodes=dataset.getNodes()

        depth,dim,center=eval(octree.meta(StdProps._octreedata))
        sparseinds=eval(octree.meta(StdProps._sparsematrix))
        oc=Octree(depth,vec3(*dim),vec3(*center))
        slicedleaves=[]

        # collect the indices of octants which intersect the plane
        for i,leaf in enumerate(oc.getLeaves()):
            if leaf.intersectsPlane(pt,norm):
                slicedleaves.append((sparseinds[i],sparseinds[i+1]))

        proccount=chooseProcCount(sum(j-i for i,j in slicedleaves),1,5000)

        if proccount!=1:
            shareMatrices(dnodes,nodecolors,indmat,octree)

        results=generateMeshPlanecutRange(len(slicedleaves),proccount,task,name,pt,norm,width,dnodes,nodecolors,indmat,octree,slicedleaves)

        for i in sorted(results):
            inodes,iinds,icols=results[i]
            if inodes: # even if the plane passes through a octant, it still might not pass through any triangles so None,None,None might still be the result
                if not nodes:
                    SceneUtils.unshareMatrices(inodes,iinds,icols)
                    nodes,indices,cols=inodes,iinds,icols
                else:
                    iinds.add(nodes.n())
                    nodes.append(inodes)
                    indices.append(iinds)
                    cols.append(icols)
                    inodes.clear()
                    iinds.clear()
                    icols.clear()

    return nodes,indices,cols


@concurrent
def calculateFieldMinMaxRange(process,list fields,valfunc):
    cdef RealMatrix field
    cdef object vallambda=createValFunc(valfunc,'<<valfunc>>')
    cdef tuple row=fields[0].getRow(process.startval)
    cdef float minv=vallambda(row)
    cdef float maxv=minv,val
    cdef int n

    for field in fields:
        for n in range(field.n()):
            row=field.getRow(n)
            val=vallambda(row)
            minv=min(minv,val)
            maxv=max(maxv,val)

    return minv,maxv


def calculateFieldMinMax(fields,valfunc=None,task=None):
    cdef int proccount
    cdef float minv,maxv
    cdef dict minmaxs
    if not fields or not all(fields):
        return 0.0,0.0

    proccount=chooseProcCount(fields[0].n(),0,1000000)
    if proccount!=1 or len(fields)>cpu_count():
        shareMatrices(*fields)

    # If there's fewer fields and CPUs, consecutively partition up each field between procs,
    # otherwise partition the field list between procs
    if len(fields)<=cpu_count():
        minmaxs=calculateFieldMinMaxRange(fields[0].n(),proccount,task,[fields[0]],valfunc)
        minv,maxv=minmax(minmaxs.values(),ranges=True)
        for f in fields[1:]:
            minmaxs=calculateFieldMinMaxRange(f.n(),proccount,task,[f],valfunc)
            minv,maxv=minmax([(minv,maxv)]+minmaxs.values(),ranges=True)
    else:
        proccount=chooseProcCount(len(fields),0,cpu_count()*10)
        minmaxs=calculateFieldMinMaxRange(len(fields),proccount,task,fields,valfunc)
        minv,maxv=minmax(minmaxs.values(),ranges=True)

    return minv,maxv


@concurrent
def calculateDataColorationRange(process,Vec3Matrix nodes,IndexMatrix nodeprops,indlist,fieldtopolist,valfunc,alphafunc,float minval,float maxval,vals):
    '''
    Calculate the color values as defined by 'valfunc' for the given nodes and fields. Arguments:
        process - process object
        nodes - matrix of nodes, nodes.n()==1 if point element type, nodes.n()==3 if nodes are calculated from other data type
        nodeprops - matrix of node properties, nodeprops.getAt(n,2) states which field in fieldtopolist node n is found on
        valfunc - function which maps a field entry to a scalar value
        minvallimit,maxvallimit - value range limits, can be None in which case they will be computed from `vals'
        vals - matrix of values to fill in, n x 2 RealMatrix
    '''
    cdef object valuelambda=createValFunc(valfunc,'<<valfunc>>')
    cdef object alphalambda=createUnitFunc(alphafunc,'<<alphafunc>>')
    cdef bint isTransparent=False # set to True if any color is not opaque
    cdef bint isPerElem
    cdef set emptyinds=set() # set of node indices for which no field data exists, these are then out-of-band as far as coloration is concerned
    cdef float emptysub=0 # amount to subtract from the minimum of the value range to make room for out-of-band values
    cdef dict fieldmap={} # map each index i in `indlist' to a field and associated values
    cdef int i,n,elem,index
    cdef float val,alpha
    cdef IndexMatrix ft,fieldtopo,t
    cdef RealMatrix field,f
    
    # Map each index i of `indlist' to (field,fieldtopo,isPerElem,fieldtype) if the field's spatial topology is indlist[i]
    # The value fieldtopo is that field's topology, isPerElem is True is it's a per-element field, and fieldtype is fieldtopo's ElemType
    for i,t in enumerate(indlist):
        fft=first((f,ft) for f,ft in fieldtopolist if f.meta(StdProps._spatial)==t.getName() or ft.getName()==t.getName())
        if fft:
            field,fieldtopo=fft
            isPerElem=field.meta(StdProps._elemdata).lower()=='true' or (field.n()!=nodes.n() and field.n()==fieldtopo.n())
            fieldtype=ElemType[fieldtopo.getType()]
            fieldmap[i]=(field,fieldtopo,isPerElem,fieldtype)

    for n in process.prange():
        xi=nodes.getAt(n,2)
        elem=nodeprops.getAt(n,0)
        index=nodeprops.getAt(n,2)

        if index not in fieldmap:
            emptyinds.add(n)
        else:
            field,fieldtopo,isPerElem,fieldtype=fieldmap[index]

            if isPerElem:
                value=field.getRow(elem)
            else:
                fieldvals=[field.getRow(v) for v in fieldtopo.getRow(elem)]
                value=fieldtype.applyBasis(fieldvals,*xi)

            valfunced=valuelambda(value)
            vals.setAt(valfunced,n)
            
    # if there are empty indices, substract a certain amount from the min of the value range to leave room for an out-of-band value
    process.sync()
    emptysub=(maxval-minval)*0.01 if len(emptyinds)>0 else 0
    emptysub=max([emptysub]+list(process.shareObject('minmaxvals',emptysub).values()))
    minval-=emptysub

    for n in process.nrange():
        val=0
        if n not in emptyinds:
            val=lerpXi(vals.getAt(n),minval,maxval)

        alpha=alphalambda(val)
        isTransparent=isTransparent or alpha<1.0

        vals.setAt(val,n)
        vals.setAt(alpha,n,1) # apply the alpha function to the value and save it

    return isTransparent


@concurrent
def calculatePerNodeColorationRange(process,RealMatrix field,valfunc,alphafunc,float minval,float maxval,RealMatrix vals):
    cdef object valuelambda=createValFunc(valfunc,'<<valfunc>>')
    cdef object alphalambda=createUnitFunc(alphafunc,'<<alphafunc>>')
    cdef float alpha,val
    cdef bint isTransparent=False # set to True if any color is not opaque
    cdef int n

    for n in process.prange():
        val=valuelambda(field.getRow(n))
        val=lerpXi(val,minval,maxval) # calculate a unit value from the field component
        alpha=alphalambda(val)
        isTransparent=isTransparent or alpha<1.0
        vals.setRow(n,val,alpha)

    return isTransparent


@timing
def calculateDataColoration(mat,parentds,ColorMatrix cols,Vec3Matrix nodes,IndexMatrix nodeprops,indlist,fields,float minval,float maxval,valfunc,alphafunc,task=None):
    '''
    Calculates colors for the nodes based on the given fields. Arguments:

       mat           - Material used to convert value to color
     parentds      - parent data set containing the mesh data `nodes' was derived from
     cols          - matrix of colors to fill, cols.n()==nodes.n()
     nodes         - matrix of nodes for the representation's mesh, nodes.m()>=3
     nodeprops     - node properties matrix, nodeprops.getAt(n,2) states which topology in `indlist' node n is found on
     indlist       - IndexMatrix list defining topologies `nodes' was computed from, all must be found in `parentds'
     fields        - list of field matrices to use for calculating, their "spatial" meta values must name a member of `indlist'
     minval,maxval - the value range over which color is determined, these must be float values such that minval<=maxval
     valfunc       - value function, calculates a scalar value from a field row
     alphafunc     - fits a scalar unit value to the alpha value for a color
     task          - task object

    The material defines what colors are to be chosen based on the data by interpolating within its spectrum, which will
    be filled into the per-node color table `cols'. The node properties matrix states in column 2 which index in `indlist'
    was used to calculate a particular node, each index in this table is associated with a field in `fields'. This allows
    a node set derived from multiple topologies to be colored with multiple fields simultaneously since one field can
    only be associated with one topology. Each field may have its own topology or use that in `indlist', in the former
    case the topology for the field must be found in  from `parentds'. A field may be "per-element", which is to say it
    provides one value for each element in its associated topology, otherwise it must have a value for each index in a
    topology.

    If only one field is given but multiple topologies are in `indlist', this field must be a "per-node" field for the
    nodes in `parentds', which is to say there is a value in the field for each of the original mesh's nodes thus a
    topology in `indlist' can index field values in the same way as nodes. If only one field is given having the same
    length as `nodes' and is associated with no topology, it is "per-node" in regards to the representation mesh rather
    than the original mesh in `parentds' and so a value for each node in `nodes' can be taken directly from the field
    without interpolation. A field can be interpreted as per-node if its "nodedata" meta value is "True" and it has no
    topology association in metadata.

    For each node in `nodes', a value is therefore derived from the fields by interpolation or directly. This value can
    be a scalar value or a row of values, these are converted to a scalar value by `valfunc'. This value is then
    converted into a unit value by scaling by the maximal and minimal vales. The `alphafunc' function maps the value to
    an alpha channel value which is a scalar unit value. Finally the material is used to convert these two unit values
    into colors in `cols'.

    If `nodeprops' is None then the field has to be treated like a per-node field since no information relating nodes
    to topologies is present.

    Returns True if any color is not opaque, False otherwise.
    '''
    cdef int proccount
    cdef bint isShared
    cdef RealMatrix vals

    assert cols.n()==nodes.n(), 'Color list must be same length as node list'
    assert nodes.m() in (3,4)
    assert minval<=maxval

    if nodeprops!=None:
        assert nodeprops.n()==nodes.n(),'nodeprops.n()==%i != nodes.n()==%i'%(nodeprops.n(),nodes.n())
    else:
        assert (len(fields)==1 and fields[0].n()==nodes.n())

    proccount=chooseProcCount(nodes.n(),0,1000)
    isShared=proccount!=1

    if task:
        task.maxprogress=nodes.n()
        task.curprogress=0

    vals=RealMatrix('vals','',nodes.n(),2,isShared)

    if len(fields)==1 and fields[0].n()==nodes.n() and (not nodeprops or SceneUtils.isPerNodeField(fields[0],nodes.n())): # per-node field for this topology
        if isShared:
            shareMatrices(nodes,fields[0])

        result=timing(calculatePerNodeColorationRange)(nodes.n(),proccount,task,fields[0],valfunc,alphafunc,minval,maxval,vals)
    else:
        fieldtopolist=SceneUtils.collectFieldTopos(parentds,fields) # collect the fields together with their assigned topologies

        if isShared:
            shareMatrices(nodes,nodeprops)
            shareMatrices(*indlist)
            shareMatrices(*sum(fieldtopolist,()))

        result=calculateDataColorationRange(nodes.n(),proccount,task,nodes,nodeprops,indlist,fieldtopolist,valfunc,alphafunc,minval,maxval,vals)

    mat.fillColorMatrix(cols,vals)

    return any(result.values())


@concurrent
def applyBasisConcurrentRange(process,Vec3Matrix xis,ctrls,output,str typename,tuple args,dict kwargs):
    cdef int i
    cdef float x,y,z
    et=ElemType[typename]
    for i in process.prange():
        x,y,z=xis.getAt(i)
        val=et.applyBasis(ctrls,x,y,z,*args,**kwargs)
        output.setAt(val,i)


@timing
def applyBasisConcurrent(Vec3Matrix xis,ctrls,output,str typename,tuple args,dict kwargs,task=None):
    '''
    For each xi value in `xis', apply the basis function named by `typename' using control values `ctrls' and parameters
    `args' and `kwargs', and store the result in `output'.
    '''
    cdef int proccount=chooseProcCount(xis.n(),1,100)
    assert xis.n()==output.n()
    if proccount!=1:
        shareMatrices(xis,output)

    applyBasisConcurrentRange(xis.n(),proccount,task,xis,ctrls,output,typename,args,kwargs)


@concurrent
def calculateLinearTriangulationRange(process,int numnodes,IndexMatrix ind,IndexMatrix ext,bint externalOnly,int indnum):
    cdef object elemtype=ElemType[ind.getType()]
    cdef str facegeom=elemtype.getFaceType(0).geom
    cdef list finds=[elemtype.getFaceIndices(i) for i in range(elemtype.numFaces())]
    cdef str name='calcLinTriRange'
    cdef Vec3Matrix outnodes
    cdef IndexMatrix outprops,outinds,outext
    cdef int elem,face
    cdef tuple einds
    cdef bint isExt
    cdef list curfaceinds

    assert facegeom in (GeomType._Tri,GeomType._Quad)

    outnodes,outprops,outinds,outext=createDataMatrices(name+str(process.index),MatrixType.tris)
    outprops.setN(numnodes)

    def addInd(list inds,int elem,int face,bint isExt):
        if isExt:
            outext.append(outinds.n())
        outinds.append(*inds)

        for i in inds:
            try:
                if outprops.getAt(i)==0:
                    outprops.setRow(i,elem,face,indnum)
            except:
                printFlush(i)
                raise

    for elem in process.prange():
        einds=ind.getRow(elem)

        for face in xrange(elemtype.numFaces()):
            isExt=ext==None or ext.getAt(elem,face)==1
            if not isExt and externalOnly:
                continue

            curfaceinds=indexList(finds[face],einds)

            addInd(curfaceinds[:3],elem,face,isExt)

            if facegeom==GeomType._Quad:
                addInd(curfaceinds[1:4],elem,face,isExt)

    return shareMatrices(outinds,outprops,outext)


def generateLinearTriangulation(dataset,str name,int refine,bint externalOnly=False,task=None,**kwargs):
    '''
    Generate a triangulation of triangle, quad, hex, and tet topologies in the Dataset object `dataset'. This will create
    1 or 2 triangles per face always using the vertices of the original element as triangle vertices, so `refine' is
    ignored. Returns a (dataset,indlist) pair where the node matrix and per-node fields of the dataset are the same as
    those for `dataset'.
    '''
    cdef Vec3Matrix nodes=dataset.getNodes()
    cdef list indlist=[]
    cdef Vec3Matrix outnodes
    cdef IndexMatrix outprops,outinds, outext,ind,ext,adj,oinds,oprops,oext
    cdef int proccount
    cdef dict result

    def acceptFunc(ind):
        if not isSpatialIndex(ind):
            return False

        et=ElemType[ind.getType()]
        return et.dim>1 and et.geom in (GeomType._Tri,GeomType._Quad,GeomType._Hex, GeomType._Tet)

    outnodes,outprops,outinds,outext=createDataMatrices(name,MatrixType.tris)
    outprops.setN(nodes.n())

    for ind,ext,adj in findIndexSets(dataset,acceptFunc=acceptFunc):
        proccount=chooseProcCount(ind.n(),0,2000)
        shareMatrices(ind,ext)
        result=calculateLinearTriangulationRange(ind.n(),proccount,task,nodes.n(),ind,ext,externalOnly,len(indlist))
        indlist.append(ind)

        for oinds,oprops,oext in result.values():
            if oinds!=None:
                outinds.append(oinds)
                oext.add(outinds.n())
                outext.append(oext)

                for prop in xrange(oprops.n()):
                    if outprops.getAt(prop)==0:
                        outprops.setRow(prop,*oprops.getRow(prop))

                oprops.clear()
                oinds.clear()
                oext.clear()

    ds=PyDataSet(name,nodes,[outprops,outext,outinds],[f for f in dataset.enumDataFields() if f.n()==nodes.n()])
    return ds,indlist


@concurrent
def calculatePointsRange(process,IndexMatrix ind,Vec3Matrix nodes,tuplenodebounds,IndexMatrix ext,int refine,bint externalOnly,bint includeUVW,int indnum):
    cdef object elemtype=ElemType[ind.getType()]
    cdef str geom=elemtype.geom
    cdef str name='calculatePointsRange'
    cdef Vec3Matrix outnodes
    cdef IndexMatrix outprops,outext
    cdef int elem
    cdef list xis=[],facexis=[],defaultextline=[1]*elemtype.numFaces()
    cdef facemap=dict() # map point xi coords to the faces they are members of

    outnodes,outprops,_,outext=createDataMatrices(name+str(process.index),None,includeUVW)

    def addNode(vec3 node,vec3 norm,vec3 xi,int elem,int face,bint isExt):
        outnodes.append(node,norm,xi)
        outprops.append(elem,face,indnum)
        if isExt:
            outext.append(outnodes.n()-1)

    def calculateNormal(tuple elemnodes,vec3 node,vec3 xi):
        if geom==GeomType._Line:
            norm=(elemnodes[0]+elemnodes[-1])*0.5-node
            return norm.norm() if norm.lenSq()>0 else vec3(0,0,1)
        else:
            return SceneUtils.calculatePointNormal(elemnodes,elemtype,0,node,xi.x(),xi.y(),0)

    if geom==GeomType._Point:
        for elem in process.prange():
            node=nodes.getAt(elem)
            addNode(node,node.norm(),vec3(),elem,0,True)

    elif geom in (GeomType._Line,GeomType._Tri,GeomType._Quad):
        if geom==GeomType._Line:
            xis=[(vec3(xi,0,0),c) for xi,c in SceneUtils.calculateLineXis(elemtype,refine)]
        else:
            xis=[(vec3(*exi),c) for _,exi,c in SceneUtils.calculateFaceXis(elemtype,refine,SceneUtils.divideTritoPoints,SceneUtils.divideQuadtoPoints)[0]]

        for elem in process.prange():
            elemnodes=nodes.mapIndexRow(ind,elem)

            for xi,c in xis:
                node=elemtype.applyCoeffs(elemnodes,c)
                norm=calculateNormal(elemnodes,node,xi)
                addNode(node,norm,xi,elem,0,True)

    elif geom in (GeomType._Hex, GeomType._Tet):
        # calculate face xi sets, so facexis[f] is the set of element xi points for face `f'
        for facexiset in SceneUtils.calculateFaceXis(elemtype,refine,SceneUtils.divideTritoPoints,SceneUtils.divideQuadtoPoints):
            facexis.append(set(vec3(*exi) for fxi,exi,c in facexiset))

        # calculate xis to be a (xi,coeffs) list of values and facemap to map `xi' to face indices or None if not on a face
        for p in SceneUtils.divideElemtoPoints(refine,geom==GeomType._Tet):
            n=vec3(*p)
            c=elemtype.basis(*p)
            xis.append((n,c))
            facemap[n]=[] #first(i for i,f in enumerate(facexis) if n in f)

            for i,f in enumerate(facexis):
                nn=first(nn for nn in f if n==nn)
                if nn!=None:
                    facemap[n].append(i)

        for elem in process.prange():
            extline=ext.getRow(elem) if ext!=None else defaultextline
            elemnodes=nodes.mapIndexRow(ind,elem)

            for xi,c in xis:
                face=facemap[xi]
                node=elemtype.applyCoeffs(elemnodes,c)
                if len(face)==0:
                    addNode(node,(xi-vec3(0.5)).norm(),xi,elem,elemtype.numFaces(),False)
                else:
                    norm=calculateNormal(elemnodes,node,xi)
                    i=first(i for i,f in enumerate(face) if extline[f]==1)
                    if i!=None: # prioritize generating points on external faces
                        addNode(node,norm,xi,elem,face[i],True)
                    else:
                        addNode(node,norm,xi,elem,face[0],False)

    return shareMatrices(outnodes,outprops,None,outext)


@concurrent
def calculatePoissonPointsRange(process,IndexMatrix ind,Vec3Matrix nodes,RealMatrix densityfield, float fmin, float fmax,startpos,IndexMatrix ext,int refine,bint externalOnly,bint includeUVW,int indnum):
    cdef object elemtype=ElemType[ind.getType()]
    cdef str geom=elemtype.geom
    cdef int elem,i,numpoints
    cdef str name
    cdef list elemnodes
    cdef Vec3Matrix outnodes
    cdef IndexMatrix outprops,outext
    cdef RealMatrix areas

    if startpos==None:
        startpos=[0.333333]*elemtype.dim
    else:
        startpos=tuple(startpos)

    refine=(refine+1)*(2 if elemtype.isSimplex else 1) # multiply by 2 for simplex types since half the generated points will be culled
    name='calculatePoissonPointsRange'+str(process.index)

    outnodes,outprops,_,outext=createDataMatrices(name,None,includeUVW)

    def addNode(vec3 node,vec3 norm,vec3 xi,int elem,int face,bint isExt):
        outnodes.append(node,norm,xi)
        outprops.append(elem,face,indnum)
        if isExt:
            outext.append(outnodes.n()-1)

    def calculateNormal(list elemnodes,vec3 node,vec3 xi):
        if geom==GeomType._Line:
            norm=(elemnodes[0]+elemnodes[-1])*0.5-node
            return norm.norm() if norm.lenSq()>0 else vec3(0,0,1)
        else:
            return SceneUtils.calculatePointNormal(elemnodes,elemtype,0,node,xi.x(),xi.y(),0)

    if geom in (GeomType._Tri,GeomType._Quad):
        areas=RealMatrix(name+'areas',process.endval-process.startval,1)
        amin=None
        amax=None

        # fill areas with the area of each element
        for i,elem in enumerate(process.nrange()):
            elemnodes=nodes.mapIndexRow(ind,elem)
            area=SceneUtils.calculateFaceArea(elemnodes,elemtype)
            areas.setAt(area,i)
            amin,amax=minmaxval(amin,amax,area)

        minmaxvals=process.shareObject('minmaxvals',(amin,amax))
        amin,amax=minmax([(amin,amax)]+minmaxvals,rangse=True)
        #amin=min([amin]+[v[0] for v in minmaxvals.values()])
        #amax=max([amax]+[v[1] for v in minmaxvals.values()])

        if amax>amin:
            areas.sub(amin)
            areas.div(amax-amin)

        for i,elem in enumerate(process.prange()):
            elemnodes=nodes.mapIndexRow(ind,elem)

            numpoints=refine*areas.getAt(i)
            if densityfield!=None:
                numpoints*=avg(densityfield.mapIndexRow(ind,elem))

            xis=generatePoisson2D(1.0,1.0,int(numpoints),None,(startpos[0],startpos[1]))
            xis=[vec3(xi[0],xi[1],0) for xi in xis if geom==GeomType._Quad or sum(xi)<=1.0]

            for xi in xis:
                node=elemtype.applyBasis(elemnodes,*xi)
                norm=calculateNormal(elemnodes,node,xi)
                addNode(node,norm,xi,elem,0,True)

    # TODO: volumetric geometries

    return shareMatrices(outnodes,outprops,None,outext)


@timing
def generateNodeDataSet(dataset,str name,int refine,bint externalOnly=False,task=None,**kwargs):
    '''Generate a dataset containing points for each node in `dataset'. This does no interpolation.'''
    cdef Vec3Matrix nodes=dataset.getNodes()
    cdef bint includeUVW=kwargs.get('includeUVW',False)
    cdef Vec3Matrix outnodes=Vec3Matrix(name+' Nodes',nodes.n(),4 if includeUVW else 3)

    outnodes.fill(vec3())
    outnodes.add(nodes)

    return PyDataSet(name,outnodes,{},dataset.fields),[]


@timing
def generatePointDataSet(dataset,str name,int refine,bint externalOnly=False,task=None,**kwargs):
    cdef Vec3Matrix nodes=dataset.getNodes()
    cdef bint includeUVW=kwargs.get('includeUVW',False)
    cdef bint usePoisson=kwargs.get('usePoisson',False)
    cdef object startpos=kwargs.get('startPos',None)
    cdef RealMatrix densityfield=kwargs.get('densityField',None)
    cdef BoundBox aabb=BoundBox(nodes)
    cdef str geom,valfunc=kwargs.get('valfunc','avg(vals)')
    cdef float fmin=0,fmax=0
    cdef dict result
    cdef Vec3Matrix outnodes
    cdef IndexMatrix nodeprops,extindices

    outnodes,nodeprops,_,extindices=createDataMatrices(name,None,includeUVW)
    indlist=[]

    if usePoisson:
        if densityfield!=None:
            densityfield,fmin,fmax=calculateFieldValues(densityfield,valfunc,task)

    for ind,ext,adj in findIndexSets(dataset):
        shareMatrices(nodes,ind,ext)
        proccount=chooseProcCount(ind.n(),refine,6000)
        geom=elemtype=ElemType[ind.getType()].geom

        if usePoisson and geom in (GeomType._Tri,GeomType._Quad): # TODO: (GeomType._Tet,GeomType._Hex)
            result=calculatePoissonPointsRange(ind.n(),proccount,task,ind,nodes,densityfield, fmin, fmax,startpos,ext,refine,externalOnly,includeUVW,len(indlist))
        else:
            result=calculatePointsRange(ind.n(),proccount,task,ind,nodes,(aabb.minv,aabb.maxv),ext,refine,externalOnly,includeUVW,len(indlist))

        indlist.append(ind)

        collectResults(outnodes,nodeprops,None,extindices,result)

    if outnodes.n()==0: # no indices found, add all points
        return generateNodeDataSet(dataset,name,refine,externalOnly,task,**kwargs)

    ds=PyDataSet(name,outnodes,[nodeprops,extindices],dataset.fields)
    return ds,indlist


def getUniqueEdges(process,Vec3Matrix nodes,IndexMatrix ind,IndexMatrix ext,list edges,bint externalOnly,bint calcRadius):
    cdef object elemtype=ElemType[ind.getType()]
    cdef set linepairs=set()
    cdef list linelengths=[],faceinds,fedges
    cdef tuple eleminds,elemnodes,edgeinds
    cdef float radius=0,dist,rad
    cdef int elem,face,e0,e1
    cdef bint isExt
    cdef dict otherpairs,otherrads

    # fill linelengths with indices for the start and end nodes of each edge
    for elem in process.nrange():
        eleminds=ind.getRow(elem)
        if calcRadius:
            elemnodes=nodes.mapIndexRow(ind,elem) #getElemNodes(elem,ind,nodes)

        for face in xrange(elemtype.numFaces()):
            isExt=ext==None or ext.getAt(elem,face)==1
            if not isExt and externalOnly:
                continue

            faceinds=elemtype.getFaceIndices(face)
            fedges=edges[face]

            for edge in range(len(fedges)):
                edgeinds=fedges[edge]
                e0=eleminds[faceinds[edgeinds[0]]] # start node index for this edge
                e1=eleminds[faceinds[edgeinds[1]]] # end node index for this edge

                linepairs.add((min(e0,e1),max(e0,e1)))

                # if no radius info is given, calculate a rough line length as the distance between the ends of this line
                if calcRadius:
                    dist=elemnodes[faceinds[edgeinds[0]]].distToSq(elemnodes[faceinds[edgeinds[1]]])
                    if dist>epsilon:
                        linelengths.append(dist)

    otherpairs=process.shareObject('linepairs',linepairs) # get the pair lists from the other procs
    # Subtract all pairs generated by procs of greater rank than this one, these subtracted pairs will corresponds to
    # the common edges between this proc and those above, thus the higher procs are responsible for generating them.
    for op in range(process.index+1,process.total):
        linepairs-=otherpairs[op]

    if calcRadius: # calculate a radius value by averaging rough line lengths between procs
        rad=math.sqrt(avg(linelengths))
        otherrads=process.shareObject('rad',rad)
        radius=max(0.0001,avg([rad]+otherrads.values())*0.01)

    return linepairs,radius


@concurrent
def calculateLineCylindersRange(process,IndexMatrix ind,IndexMatrix ext,Vec3Matrix nodes,int refine,int radrefine,RealMatrix radiusfield,bint isAreaField,radius,bint externalOnly,bint use1DLines,int indnum):
    cdef object elemtype=ElemType[ind.getType()]
    cdef str geom=elemtype.geom
    cdef str name='calculateCylindersRange'
    cdef bint endCaps=True
    cdef bint calcRadius=radius==None and radiusfield==None and not use1DLines
    cdef int ringSize=radrefine+3
    cdef int capSize=(ringSize+1) if endCaps else 0
    cdef int elem,edge,face,count,e0,e1
    cdef list defaultradii=None,edges,genCycles,allfaceinds,defaultextline,elemradii,edgepoints,edgeradii
    cdef set genpairs
    cdef object valfunc=lambda i:i# is radius field, use directly
    cdef Vec3Matrix outnodes
    cdef IndexMatrix outprops,outinds,outext
    cdef tuple eleminds,elemnodes,edgexis,coeffs

    if isAreaField:
        valfunc=lambda i:math.sqrt(i/math.pi) # convert area to radius

    outnodes,outprops,outinds,outext=createDataMatrices(name,MatrixType.lines if use1DLines else MatrixType.tris)

    if use1DLines:
        def addSegment(list pts,list radii,tuple xis,int elem,int face,bint isExt):
            cdef int i
            for i in xrange(len(pts)):
                outnodes.append(pts[i],vec3(0,0,1),vec3(*xis[i]))
                outprops.append(elem,face,indnum)
                if i>0:
                    if isExt:
                        outext.append(outinds.n())
                    outinds.append(outnodes.n()-2,outnodes.n()-1)
    else:
        def addSegment(list pts,list radii,tuple xis,int elem,int face,bint isExt):
            cdef int i
            cdef list cnodes,triinds,norms

            cnodes,triinds=SceneUtils.generateCylinder(pts,radii,radrefine,outnodes.n(),endCaps)
            norms=SceneUtils.generateTriNormals(cnodes,triinds,outnodes.n())
            xis=tuple(vec3(*xi) for xi in xis)

            for ind in triinds:
                if isExt:
                    outext.append(outinds.n())
                outinds.append(*ind)

            for i,n in enumerate(cnodes):
                if i<(capSize+ringSize):
                    xi=0
                elif i>=(capSize+ringSize*(len(xis)-2)):
                    xi=len(xis)-1
                else:
                    xi=(i-capSize)/ringSize

                outnodes.append(n,norms[i],xis[xi])
                outprops.append(elem,face,indnum)

    if geom==GeomType._Line:
        if calcRadius: # calculate a radius value by averaging rough line lengths between procs
            linelengths=[]

            for elem in process.nrange():
                elemnodes=nodes.mapIndexRow(ind,elem) #getElemNodes(elem,ind,nodes)
                linelengths.append(elemnodes[0].distToSq(elemnodes[-1]))

            # determine the rough minimal length from amongst the procs
            rad=math.sqrt(avg(linelengths))
            otherrads=process.shareObject('rad',rad)
            radius=max(0.0001,avg([rad]+otherrads.values())*0.01)

        xis=SceneUtils.calculateLineXis(elemtype,refine)

        if radius!=None:
            defaultradii=[float(radius)]*len(xis)

        for elem in process.prange():
            elemnodes=nodes.mapIndexRow(ind,elem)

            interppoints=[elemtype.applyCoeffs(elemnodes,c) for xi,c in xis]

            if radiusfield:
                elemradii=map(valfunc,radiusfield.mapIndexRow(ind,elem))
                interpradii=[elemtype.applyCoeffs(elemradii,c) for xi,c in xis]
            else:
                interpradii=defaultradii

            addSegment(interppoints,interpradii,tuple((xi,0,0) for xi,c in xis),elem,0,True)

    if geom in (GeomType._Tri,GeomType._Quad,GeomType._Hex, GeomType._Tet):
        edges=[elemtype.getFaceType(f).edges for f in range(elemtype.numFaces())]
        facexis=SceneUtils.calculateFaceXis(elemtype,refine,SceneUtils.divideTritoLines,SceneUtils.divideQuadtoLines) # TODO: assumes same node ordering as the basis function, find some way of sorting instead
        count=0
        genpairs=set()
        genCycles=[True] if externalOnly else [True,False]
        allfaceinds=[elemtype.getFaceIndices(face) for face in range(elemtype.numFaces())]
        defaultextline=[1]*elemtype.numFaces()

        linepairs,newradius=getUniqueEdges(process,nodes,ind,ext,edges,externalOnly,calcRadius)

        if calcRadius:
            radius=newradius

        if radius!=None:
            defaultradii=[float(radius)]*(len(facexis[0][0])/3)

        for doExtFirst in genCycles: # generate for external edges first, then internal edges (if not externalOnly)
            for elem in process.nrange():
                process.setProgress(count/2)
                count+=2 if externalOnly else 1

                if ext:
                    extline=ext.getRow(elem)
                else:
                    extline=defaultextline

                if doExtFirst and ext and sum(extline)==0: # skip entirely internal elements
                    continue

                eleminds=ind.getRow(elem)
                elemnodes=nodes.mapIndexRow(ind,elem)

                if radiusfield:
                    elemradii=map(valfunc,radiusfield.mapIndexRow(ind,elem))

                for face in xrange(elemtype.numFaces()):
                    isExt=extline[face]==1 #ext==None or ext.getAt(elem,face)==1
                    if isExt != doExtFirst or (not isExt and externalOnly):
                        continue

                    for edge in range(len(edges[face])):
                        edgeinds=edges[face][edge]
                        faceinds=allfaceinds[face]
                        e0=eleminds[faceinds[edgeinds[0]]] # start node index for this edge
                        e1=eleminds[faceinds[edgeinds[1]]] # end node index for this edge
                        line=(min(e0,e1),max(e0,e1))

                        # if a line from e0 to e1 is generated already or elsewhere, skip
                        if line not in linepairs or line in genpairs:
                            continue

                        genpairs.add(line)

                        edgexis=facexis[face][edge] # get the (face-xis + elem-xis + coeffs) tuple for this edge
                        coeffs=edgexis[(len(edgexis)/3)*2:]

                        edgepoints=[elemtype.applyCoeffs(elemnodes,c) for c in coeffs]

                        if radiusfield:
                            edgeradii=[elemtype.applyCoeffs(elemradii,c) for c in coeffs]
                        else:
                            edgeradii=defaultradii

                        addSegment(edgepoints,edgeradii,edgexis[(len(edgexis)/3):(len(edgexis)/3)*2],elem,face,isExt)

    return shareMatrices(outnodes,outprops,outinds,outext)


@timing
def generateLineDataSet(dataset,str name,int refine,bint externalOnly=False,task=None,**kwargs):
    kwargs['use1DLines']=True
    return generateCylinderDataSet(dataset,name,refine,externalOnly,task,**kwargs)


@timing
def generateCylinderDataSet(dataset,str name,int refine,bint externalOnly=False,task=None,**kwargs):
    field=kwargs.get('field',None)
    radius=kwargs.get('radius',None)
    isAreaField=kwargs.get('isAreaField',False)
    radrefine=int(kwargs.get('radrefine',1))
    use1DLines=kwargs.get('use1DLines',False)

    if radius!=None and radius<epsilon:
        radius=None

    nodes=dataset.getNodes()
    outnodes,nodeprops,indices,extindices=createDataMatrices(name,MatrixType.lines if use1DLines else MatrixType.tris)
    indices.setType(ElemType._Line1NL if use1DLines else ElemType._Tri1NL)
    indlist=[]

    field=dataset.findField(field)

    for ind,ext,adj in findIndexSets(dataset,acceptFunc=lambda ind: isSpatialIndex(ind) and ElemType[ind.getType()].dim>0):
        shareMatrices(nodes,ind,field,ext)
        proccount=chooseProcCount(ind.n(),refine,2000)

        result=calculateLineCylindersRange(ind.n(),proccount,task,ind,ext,nodes,refine,radrefine,field,isAreaField,radius,externalOnly,use1DLines,len(indlist))
        indlist.append(ind)

        checkResultMap(result)

        collectResults(outnodes,nodeprops,indices,extindices,result)

    if indices.n()==0:
        raise ValueError('Dataset contains no data suitable for line generation')

    ds=PyDataSet(name,outnodes,[nodeprops,extindices,indices],dataset.fields)
    return ds,indlist


@timing
def generateBillboardDataSet(dataset,name,refine,externalOnly=False,task=None,**kwargs):
    ds,indlist=generatePointDataSet(dataset,name,refine,externalOnly,task,**kwargs)

    field=kwargs.get('field',None)
    if field!=None:
        vecfunc=kwargs.get('vecfunc',vecfuncLinear)
        field=dataset.findField(field)
        nodes=ds.getNodes()
        nodeprops=ds.getIndexSet(ds.getName()+MatrixType.props[1])
        fields=[field]*len(indlist)

        calculateDataNormals(dataset,nodes,nodeprops,indlist,fields,vecfunc,task)

    return ds,indlist


@concurrent
def calculateGlyphScalesRange(process,Vec3Matrix nodes,IndexMatrix nodeprops,list fields,list fieldtopolist,vecfunc):
    cdef object veclambda=createVec3Func(vecfunc,'<<vecfunc>>',min(f.m() for f,t in fieldtopolist))
    cdef int n,elem,face,indnum
    cdef vec3 xi,vec
    cdef list fieldvals
    cdef RealMatrix field
    cdef IndexMatrix fieldtopo

    fieldtopolist=[(f,ft,ElemType[ft.getType()]) for f,ft in fieldtopolist]

    for n in process.nrange():
        process.setProgress(n-process.startval+1)

        xi=nodes.getAt(n,2)
        elem,face,indnum=nodeprops.getRow(n)
        field,fieldtopo,fieldtype=fieldtopolist[indnum]

        fieldvals=[field.getRow(v) for v in fieldtopo.getRow(elem)]

        value=fieldtype.applyBasis(fieldvals,*xi)
        vec=veclambda(value)
        nodes.setAt(vec,n,3) # set the scale value for the given node in the UVW field


@timing
def calculateGlyphScales(dataset,Vec3Matrix nodes,IndexMatrix nodeprops,list fields,vecfunc,task=None):
    '''Set column 3 of `nodes' to be the scaling vector for each glyph.'''
    proccount=chooseProcCount(nodes.n(),0,1000)
    fieldtopolist=SceneUtils.collectFieldTopos(dataset,fields)

    if len(fieldtopolist)>0:
        if proccount!=1:
            shareMatrices(nodes,nodeprops,*listSum(map(list,fieldtopolist)))
            shareMatrices(*fields)

        calculateGlyphScalesRange(nodes.n(),proccount,task,nodes,nodeprops,fields,fieldtopolist,vecfunc)


@timing
def generateGlyphDataSet(dataset,name,refine,externalOnly=False,task=None,**kwargs):
    dfield=kwargs.get('dfield',None)
    sfield=kwargs.get('sfield',None)

    ds,indlist=generatePointDataSet(dataset,name,refine,externalOnly,task,includeUVW=(sfield!=None),**kwargs)

    if dfield!=None:
        vecfunc=kwargs.get('vecfunc',None)
        field=dataset.findField(dfield)
        nodes=ds.getNodes()
        nodeprops=ds.getIndexSet(ds.getName()+MatrixType.props[1])
        fields=[field]*len(indlist)

        if len(indlist)>0:
            shareMatrices(nodes,nodeprops)
            calculateDataNormals(dataset,nodes,nodeprops,indlist,fields,vecfunc,task)
        else:
            for n in xrange(nodes.n()):
                nodes.setAt(vec3(*field.getRow(n)),n,1)

    if sfield!=None:
        scalefunc=kwargs.get('scalefunc',None)
        field=dataset.findField(sfield)
        nodes=ds.getNodes()
        nodeprops=ds.getIndexSet(ds.getName()+MatrixType.props[1])
        fields=[field]*len(indlist)

        if len(indlist)>0:
            shareMatrices(nodes,nodeprops)
            calculateGlyphScales(dataset,nodes,nodeprops,fields,scalefunc,task)
        else:
            veclambda=createVec3Func(scalefunc,'<<vecfunc>>',field.m())

            for n in xrange(nodes.n()):
                nodes.setAt(veclambda(field.getRow(n)),n,3)

    return ds,indlist


@timing
def generateRibbonDataSet(dataset,str name,int refine,bint externalOnly=False,task=None,**kwargs):
    rangeinds=kwargs.get('rangeinds',True)
    maxlen=kwargs.get('rangeinds',0.0)

    if rangeinds:
        nodes=dataset.getNodes()
        lineinds=first(i for i in dataset.enumIndexSets() if isSpatialIndex(i))

        outnodes,nodeprops,extindices,indices=createDataMatrices(name,MatrixType.lines,True)
        indices.append(lineinds)

        for ind in xrange(len(lineinds)):
            if n in xrange(*lineinds[ind]):
                outnodes.append(nodes[n],vec3(),vec3(),vec3())
                nodeprops.append(ind,0,0)
                extindices.append(len(extindices))

        ds=PyDataSet(name,outnodes,[nodeprops,extindices,indices],dataset.fields)
        return ds,[lineinds]


@concurrent
def reinterpolateVerticesRange(process,Vec3Matrix vertices,Vec3Matrix newnodes,Vec3Matrix oldnodes,IndexMatrix oldnodeprops,indlist):
    cdef int n,elem,indnum,ind
    cdef list elemnodes,elemtypelist=[ElemType[ind.getType()] for ind in indlist]
    cdef dict elemnodemap={}

    for n in process.prange():
        elem=oldnodeprops.getAt(n,0)
#       face=oldnodeprops.getAt(n,1)
        indnum=oldnodeprops.getAt(n,2)
        ind=indlist[indnum]
        elemtype=elemtypelist[indnum]

#       elemnodes=newnodes.mapIndexRow(ind,elem)

        if (elem,indnum) not in elemnodemap:
            elemnodemap[(elem,indnum)]=newnodes.mapIndexRow(ind,elem)

        elemnodes=elemnodemap[(elem,indnum)]

        vertxi=oldnodes.getAt(n,2)
        vert=elemtype.applyBasis(elemnodes,vertxi.x(),vertxi.y(),vertxi.z())
#       norm=calculateFaceNormal(elemnodes,elemtype,face)

        vertices.setRow(n,vert,oldnodes.getAt(n,1),vertxi)


@timing
def reinterpolateVertices(newname,origds,srcds,indlist,task=None,**kwargs):
    '''Recalculate mesh node positions from their stored xi/elem# values.'''

    oldname=origds.getName()
    oldnodes=origds.getNodes()
    oldnodeprops=origds.getIndexSet(oldname+MatrixType.props[1])

    newnodes=srcds.getNodes()

    vertices=Vec3Matrix(newname+' Nodes',oldnodes.n(),oldnodes.m(),True)
    newds=PyDataSet(newname,vertices)

    # populate new dataset with original's index sets with alias names, this eliminates the need to copy matrices
    for f in origds.getIndexNames():
        if f.startswith(oldname):
            newds.setIndexSet(f.replace(oldname,newname),origds.getIndexSet(f))

    # populate new dataset with original's fields with alias names, this eliminates the need to copy matrices
    for f in srcds.getFieldNames():
        df=srcds.getDataField(f)
        if f.startswith(oldname):
            newds.setDataField(f.replace(oldname,newname),df)
        else:
            newds.setDataField(df)

    proccount=chooseProcCount(oldnodes.n(),0,2000)
    if proccount!=1:
        shareMatrices(oldnodeprops,oldnodes,newnodes,*indlist)

    reinterpolateVerticesRange(oldnodes.n(),proccount,task,vertices,newnodes,oldnodes,oldnodeprops,indlist)

    return newds


def reduceMesh(nodes,indslist=[],fieldslist=[],depth=4,aabb=None,marginSq=None):
    '''
    Traverses the given nodes and eliminates duplicate. This will re-index all the index matrices in the list `indslist'
    and refill the per-node fields in the list `fieldslist' to correlate to the new node list. The result is the node
    matrix, list of new index matrices, and list of new field matrices. The value `depth' sets how deep to build an
    octree, and `aabb' is the bounding box for `nodes' if known otherwise it will be computed internally. `marginSq' is
    the margin of error expressed as the minimal squared distance nodes can be apart to be considered indentical.
    '''
    cdef Octree oc
    cdef dict nodemap={} # maps old indices to new indices
    cdef list fieldinds=[] # indices for the values to go into new per-node fields
    cdef Vec3Matrix newnodes=Vec3Matrix('newnodes',0)
    cdef list newindslist=[],newfieldslist=[],oldinds,newfield,newind
    cdef int i
    cdef IndexMatrix ind
    cdef RealMatrix field

    aabb=aabb or BoundBox(nodes)
    oc=Octree(depth,aabb.maxv-aabb.minv,aabb.center,None if marginSq==None else (lambda a,b:a.distToSq(b)<=marginSq))

    # associate each node with the indices of those nodes equivalent to it in `nodes'
    for i in xrange(len(nodes)):
        oc.addNode(nodes.getAt(i),list())[1].append(i)

    # fill nodemap to relate every old node index to the new one, put the new node in newnodes,
    # and put the first of the old indices into fieldinds
    for n,oldinds in oc:
        for i in oldinds:
            nodemap[i]=len(newnodes)
        newnodes.append(n)
        fieldinds.append(oldinds[0]) # assuming duplicate nodes have the same field value, store only the first index

    # for each index, replace the old indices with the new ones by applying each old index to nodemap
    for ind in indslist:
        newind=[]
        for i in xrange(len(ind)):
            newind.append([nodemap[r] for r in ind.getRow(i)])

        newindslist.append(listToMatrix(newind,ind.getName(),ind.getType()))

    # for each field, rebuild the matrix by pulling out those rows indexed in fieldinds only
    for field in fieldslist:
        # pull out each row from the old field which corresponds to a node that's been retained
        newfield=map(field.getRow if field.m()>1 else field.getAt, fieldinds)
        newfieldslist.append(listToMatrix(newfield,field.getName()))

    return newnodes,newindslist,newfieldslist





@concurrent
def selectElementsRange(process,nodes,indices,selectFunc):
    c=CommandCompiler()
    selcomp=c(selectFunc,'<<selectFunc>>','eval')
    sellambda=lambda cnodes,ind,ext,adj:eval(selcomp)

    selected=IndexMatrix(nodes.getName()+' Selected'+str(process.index),0,2)
    count=0
    progress=0

    for ind,ext,adj in indices:
        for n in xrange(process.index,ind.n(),process.total):
            progress+=1
            process.setProgress(progress)
            cnodes=nodes.mapIndexRow(ind,n)
            if sellambda(cnodes,ind,ext,adj):
                selected.append(count,n)

        count+=1

    if selected.n()>0:
        selected.setShared(True)
        return selected
    else:
        return None


def selectElements(dataset,selectFunc,indexAcceptFunc=None,task=None):
    nodes=dataset.getNodes()
    indexAcceptFunc=indexAcceptFunc or isSpatialIndex
    indices=list(findIndexSets(dataset,acceptFunc=indexAcceptFunc))

    selected=IndexMatrix(nodes.getName()+' Selected',0,2)

    if len(indices)>0:
        nodes.setShared(True)
        for ind,ext,adj in indices:
            ind.setShared(True)
            if ext:
                ext.setShared(True)
            if adj:
                adj.setShared(True)

        totalindices=sum(i[0].n() for i in indices)
        proccount=chooseProcCount(totalindices*ElemType[indices[0][0].getType()].order,1,1000)

        results=selectElementsRange(totalindices,proccount,task,nodes,indices,selectFunc)
        selected.reserveRows(sum(r.n() for r in results.values() if r!=None))

        for r in results.values():
            if r!=None:
                selected.append(r)
                r.clear()

    return selected,[i[0] for i in indices]


@concurrent
def selectPlaneElementsRange(process,nodes,inds,octree,planept,planenorm):
    results=set()
    depth,dim,center=eval(octree.meta(StdProps._octreedata))
    sparseinds=eval(octree.meta(StdProps._sparsematrix))

    oc=Octree(depth,vec3(*dim),vec3(*center))
    leaves=oc.getLeaves()

    for leaf in process.prange():
        if leaves[leaf].intersectsPlane(planept,planenorm):
            start=sparseinds[leaf]
            end=sparseinds[leaf+1]

            for e in xrange(start,end):
                elem=octree.getAt(e)
                if SceneUtils.planeIntersectsElem(nodes.mapIndexRow(inds,elem),planept,planenorm):
                    results.add(elem)
        #octant=octants[p-process.startval]
        #ocdata=octant.meta(StdProps._octreedata)

#       if ocdata:
#           loctant,ldepth,lcenter,ldim,depth,center,dim=eval(ocdata)
#           if not SceneUtils.planeIntersectsElem(BoundBox([lcenter-ldim*0.5,lcenter+ldim*0.5]).getCorners(),planept,planenorm):
#               continue
#
#       for e in xrange(octant.n()):
#           elem=octant.getAt(e)
#           if SceneUtils.planeIntersectsElem(nodes.mapIndexRow(inds,elem),planept,planenorm):
#               results.add(elem)

    return results


def selectPlaneElements(dataset,planept,planenorm,treedepth=2,indexAcceptFunc=None,task=None):
    nodes=dataset.getNodes()
    indices=list(filter(indexAcceptFunc or isSpatialIndex,dataset.enumIndexSets()))

    selected=IndexMatrix(nodes.getName()+' Selected',0,2) # (index #,element #) pairs

    trees=getDatasetOctrees(dataset,treedepth,indexAcceptFunc) if len(indices)>0 else None

    for indcount,ind in enumerate(indices):
        #octants=[l.leafdata for l in trees[ind].getLeaves() if l.leafdata]
        octree=trees[ind]
        depth,_,_=eval(octree.meta(StdProps._octreedata))
        proccount=chooseProcCount(ind.n()*ElemType[ind.getType()].order,1,1000)

        if proccount!=1:
            shareMatrices(nodes,ind,octree)

        results=selectPlaneElementsRange(8**depth,proccount,task,nodes,ind,octree,planept,planenorm)

        for i in set().union(*results.values()):
            selected.append(indcount,i)

    return selected,indices


@concurrent
def calculateIsoplaneRange(process,nodes,indices,selected,refine,pt,norm):
    outnodes=Vec3Matrix(nodes.getName()+' Nodes'+str(process.index),0,3)
    outprops=IndexMatrix(nodes.getName()+MatrixType.props[1]+str(process.index),0,3)
    outinds=IndexMatrix(nodes.getName()+MatrixType.tris[1]+str(process.index),0,3)

    typemap=dict((i[0],ElemType[i[0].getType()]) for i in indices)
    typemap=dict((i,e) for i,e in typemap.items() if e.geom in (GeomType._Tet,GeomType._Hex))

    for n in process.prange():
        indnum,elem=selected.getRow(n)
        index=indices[indnum][0]
        elemtype=typemap.get(index,None)

        if elemtype:
            elemnodes=nodes.mapIndexRow(index,elem)
            for n1,n2,n3,a,b,c in SceneUtils.sliceElementPlane(elemnodes,elemtype,pt,norm,refine):
                numnodes=outnodes.n()
                outinds.append(numnodes,numnodes+1,numnodes+2)

                outprops.append(elem,0,indnum)
                outprops.append(elem,0,indnum)
                outprops.append(elem,0,indnum)

                outnodes.append(n1,norm,vec3(*a))
                outnodes.append(n2,norm,vec3(*b))
                outnodes.append(n3,norm,vec3(*c))

    return shareMatrices(outnodes,outprops,outinds)


@timing
def generateIsoplaneDataSet(dataset,name,refine,pt,norm,indexAcceptFunc=None,task=None):

    indexAcceptFunc=indexAcceptFunc or isSpatialIndex
    norm=norm.norm()

    selected,selindices=selectPlaneElements(dataset,pt,norm,2,indexAcceptFunc,task)

    indices1=list(findIndexSets(dataset,acceptFunc=indexAcceptFunc))
    sortedindices=[]
    for i in selindices:
        sortedindices.append(first(ind1 for ind1 in indices1 if ind1[0]==i))

    nodes,nodeprops,indices,extindices=createDataMatrices(name,MatrixType.tris)

    if selected.n()>0:
        dnodes=dataset.getNodes()
        proccount=chooseProcCount(selected.n(),refine,500)

        if proccount!=1:
            selected.setShared(True)
            dnodes.setShared(True)

        result=calculateIsoplaneRange(selected.n(),proccount,task,dnodes,sortedindices,selected,refine,pt,norm)

        selected.clear()

        for outnodes,outprops,outinds in result.values():
            if outnodes!=None:
                outinds.add(nodes.n())
                indices.append(outinds)
                nodeprops.append(outprops)
                nodes.append(outnodes)

                outnodes.clear()
                outprops.clear()
                outinds.clear()

        extindices.setN(indices.n())
        for n in xrange(indices.n()):
            extindices.setAt(n,n)

    if indices.n()==0:
        raise ValueError('Dataset contains no data suitable for triangle generation')

    ds=PyDataSet(name,nodes,[nodeprops,extindices,indices])
    return ds,selindices


@concurrent
def calculateIsosurfaceRange(process,nodes,ind,refine,field,fieldtopo,minv,maxv,planevals,indnum):
    elemtype=ElemType[ind.getType()]
    fieldtype=ElemType[fieldtopo.getType()]
    name='calculateIsosurfaceRange'
    count=1

    outnodes=Vec3Matrix(name+' Nodes'+str(process.index),0,3)
    outprops=IndexMatrix(name+MatrixType.props[1]+str(process.index),0,3)
    outinds=IndexMatrix(name+MatrixType.tris[1]+str(process.index),0,3)

    def addNode(node,norm,xi,elem):
        outnodes.append(node,norm,vec3(*xi))
        outprops.append(elem,0,indnum)

    for elem in xrange(process.maxval):
        if elem%process.total!=process.index:
            continue

        elemnodes=nodes.mapIndexRow(ind,elem) #getElemNodes(elem,ind,nodes)
        fieldvals=field.mapIndexRow(fieldtopo,elem) #getElemNodes(elem,fieldtopo,field)
        process.setProgress(count)
        count+=1

        for val in planevals:
            for a,b,c in SceneUtils.calculateElemIsosurf(fieldvals,fieldtype,elemtype,val,refine):
                n1=elemtype.applyBasis(elemnodes,*a)
                n2=elemtype.applyBasis(elemnodes,*b)
                n3=elemtype.applyBasis(elemnodes,*c)

                norm=n1.planeNorm(n2,n3)

                nodeslen=outnodes.n()
                addNode(n1,norm,a,elem)
                addNode(n2,norm,b,elem)
                addNode(n3,norm,c,elem)

                addNode(n1,-norm,a,elem)
                addNode(n3,-norm,c,elem)
                addNode(n2,-norm,b,elem)

                outinds.append(nodeslen,nodeslen+1,nodeslen+2)
                outinds.append(nodeslen+3,nodeslen+4,nodeslen+5)

    if outnodes.n()>0:
        outnodes.setShared(True)
        outprops.setShared(True)
        outinds.setShared(True)
    else:
        outnodes=None
        outprops=None
        outinds=None

    return outnodes,outinds,outprops


@concurrent
def calculateIsolineRange(process,nodes,ind,ext,refine,field,fieldtopo,minv,maxv,radius,cylrefine,linevals,indnum):
    elemtype=ElemType[ind.getType()]
    fieldtype=ElemType[fieldtopo.getType()]
    geom=elemtype.geom
    name='calculateIsosurfaceRange'
    count=1

    endCaps=True
    ringSize=cylrefine+3
    capSize=(ringSize+1) if endCaps else 0

    assert len(elemtype.faces)>0

    outnodes=Vec3Matrix(name+' Nodes'+str(process.index),0,3)
    outprops=IndexMatrix(name+MatrixType.props[1]+str(process.index),0,3)
    outinds=IndexMatrix(name+MatrixType.tris[1]+str(process.index),0,3)

    lines=[list() for i in linevals]

    if geom in (GeomType._Hex, GeomType._Tet):
        for elem in xrange(process.maxval):
            if elem%process.total!=process.index:
                continue

            process.setProgress(count)
            count+=1

            extfaces=ext.getRow(elem) if ext else [1]*elemtype.numFaces()

            if sum(extfaces)==0:
                continue

            elemnodes=nodes.mapIndexRow(ind,elem) #getElemNodes(elem,ind,nodes)

            for face,isext in enumerate(extfaces):
                if isext==0:
                    continue

                faceinds=fieldtype.getFaceIndices(face)
                facetype=fieldtype.getFaceType(face)
                facexis=indexList(faceinds,fieldtype.xis)
                nodeinds=indexList(faceinds,fieldtopo.getRow(elem)) # indices of the face nodes/values

                facevals=[field.getAt(i) for i in nodeinds]

                for ln,val in enumerate(linevals):
                    for a,b in SceneUtils.calculateElemIsoline(facevals,facetype,val,refine):
                        xi0=facetype.applyBasis(facexis,*a)
                        xi1=facetype.applyBasis(facexis,*b)
                        p0=elemtype.applyBasis(elemnodes,*xi0)
                        p1=elemtype.applyBasis(elemnodes,*xi1)

                        lines[ln].append((p0,p1,xi0,xi1,elem))

    otherlines=process.shareObject('lines',lines) # communicate the collected line segments to all procs, though not every proc needs every segment

    for ln,val in enumerate(linevals):
        if ln%process.total!=process.index:
            continue

        segs=lines[ln]+listSum(ol[ln] for ol in otherlines.values())
        conjsegs=[]

        epsilondist=epsilon*10
        radsq=radius**2

        while len(segs)>0:
            orderseg=[]
            index=0

            while index!=None: # collect segments by joining up neighbouring segments
                p0,p1,xi0,xi1,elem=segs.pop(index)

                if len(orderseg)>0 and orderseg[-1][0].distToSq(p0)>epsilondist:
                    p0,p1=p1,p0
                    xi0,xi1=xi1,xi0

                if len(orderseg)==0:
                    orderseg+=[(p0,xi0,elem),(p1,xi1,elem)] # store the whole line segment
                else:
                    orderseg+=[(p1,xi1,elem)] # store the far end point of this segment

                # look for the next nearest line segment
                index=first(i for i,(np0,np1,nxi0,nxi1,nelem) in enumerate(segs) if min(p1.distToSq(np0),p1.distToSq(np1))<epsilondist)

            index=0
            while index<len(orderseg)-1: # remove line segments shorter than the radius
                p0,xi0,elem0=orderseg[index]
                p1,xi1,elem1=orderseg[index+1]
                if p0.distToSq(p1)<radsq:
                    orderseg[index]=(p0+p1)*0.5,xi0,elem0
                    orderseg.pop(index+1)

                index+=1

            if len(orderseg)>=2:
                conjsegs.append(orderseg)
                # if the line ends meet close enough, join them up
                p0,xi0,elem0=orderseg[0]
                p1,xi1,elem1=orderseg[-1]
                if p0.distToSq(p1)<radsq:
                    orderseg[0]=(p0+p1)*0.5,xi0,elem0
                    orderseg[-1]=(p0+p1)*0.5,xi1,elem1

        # generate each cylinder and add the triangles
        for seg in conjsegs:
            cnodes,cinds=SceneUtils.generateCylinder([s[0] for s in seg],[radius]*len(seg),cylrefine,outnodes.n(),endCaps) # TODO: want end caps
            norms=SceneUtils.generateTriNormals(cnodes,cinds,outnodes.n())

            for ind in cinds:
                outinds.append(*ind)

            for i,n in enumerate(cnodes):
                if i<=capSize:
                    sind=0
                elif (len(cnodes)-i)<=capSize:
                    sind=-1
                else:
                    sind=(i-capSize)/ringSize

                xi,elem=seg[sind][1:]

                outnodes.append(n,norms[i],vec3(*xi))
                outprops.append(elem,0,indnum)

    return shareMatrices(outnodes,outinds,outprops)


def generateIsoObjectDataSet(dataset,name,refine,externalOnly=False,task=None,**kwargs):
    numitervals=max(1,int(kwargs.get('numitervals',1)))
    vals=kwargs.get('vals',"")
    minv=kwargs.get('minv',None)
    maxv=kwargs.get('maxv',None)
    field=kwargs.get('field',None)
    radius=kwargs.get('radius',1.0) # line only
    cylrefine=kwargs.get('cylrefine',3) # line only
    objtype=kwargs.get('objtype','surface')
    nodes=dataset.getNodes()

    assert objtype in ('line','surface')

    valfunc=kwargs.get('valfunc','sum(vals)/len(vals)')

    outnodes=Vec3Matrix(name+' Nodes',0,3) # node, normal, xi, should be (node,normal,ui,xi) if textures used
    nodeprops=IndexMatrix(name+MatrixType.props[1],0,3) #  elem index, face index, index matrix number
    extindices=IndexMatrix(name+MatrixType.extinds[1],0,1) # list of external tris
    indices=IndexMatrix(name+MatrixType.tris[1],0,3)
    indlist=[]

    field=dataset.findField(field)
    fieldtopo=dataset.getIndexSet(field.meta(StdProps._topology))
    fieldvals,fmin,fmax=calculateFieldValues(field,valfunc,task)

    assert fieldtopo!=None

    if minv==None:
        minv=fmin
    if maxv==None:
        maxv=fmax

    minv=float(minv)
    maxv=float(maxv)

    if minv==maxv:
        numitervals=1
        vals=[minv]
    elif vals!=None and isinstance(vals,str) and len(vals)>0: # parse the string list of values
        vals=list(set(clamp(float(p),minv,maxv) for p in re.split(',|\ ',vals) if len(p)>0))
    else: # defined a list of evenly-separated values
        if numitervals==1:
            vals=[minv+(maxv-minv)*0.5]
        else:
            planeskip=(maxv-minv)/(numitervals-1)
            vals=[minv+planeskip*n for n in range(numitervals)]

    def acceptFunc(ind):
        if not isSpatialIndex(ind):
            return False

        elemtype=ElemType[ind.getType()]
        return elemtype.dim>2 and elemtype.geom in (GeomType._Tet,GeomType._Hex)

    for ind,ext,adj in findIndexSets(dataset,acceptFunc=acceptFunc):
        shareMatrices(nodes,ind,field,fieldtopo)

        if objtype=='surface':
            proccount=chooseProcCount(ind.n(),refine,2000)
            result=calculateIsosurfaceRange(ind.n(),proccount,task,nodes,ind,refine,field,fieldtopo,minv,maxv,vals,len(indlist))
        else:
            if ext:
                ext.setShared(True)
            numelems=ext.n() if ext else ind.n()
            proccount=chooseProcCount(ind.n(),refine,2000)
            result=calculateIsolineRange(numelems,proccount,task,nodes,ind,ext,refine,field,fieldtopo,minv,maxv,radius,cylrefine,vals,len(indlist))

        indlist.append(ind)

        for onodes,oinds,props in result.values():
            if onodes!=None:
                oinds.add(outnodes.n())

                indices.append(oinds)
                outnodes.append(onodes)
                nodeprops.append(props)
                oinds.clear()
                onodes.clear()
                props.clear()

    extindices.addRows(indices.n())
    for i in xrange(extindices.n()):
        extindices.setAt(i,i)

    #if indices.n()==0:
    #    raise ValueError('Dataset contains no data suitable for triangle generation')

    ds=PyDataSet(name,outnodes,[nodeprops,extindices,indices],dataset.fields)

    return ds,indlist


@timing
def generateIsosurfaceDataSet(dataset,name,refine,externalOnly=False,task=None,**kwargs):
    return generateIsoObjectDataSet(dataset,name,refine,externalOnly,task,objtype='surface',**kwargs)


@timing
def generateIsolineDataSet(dataset,name,refine,externalOnly=False,task=None,**kwargs):
    return generateIsoObjectDataSet(dataset,name,refine,externalOnly,task,objtype='line',**kwargs)


@concurrent
def calculateDataNormalsRange(process,Vec3Matrix nodes,IndexMatrix nodeprops,list fieldtopolist,vecfunc):
    cdef object veclambda=createVec3Func(vecfunc,'<<vecfunc>>',min(f.m() for f,t in fieldtopolist))
    cdef vec3 xi,vec
    cdef int n,elem
    cdef list fieldvals
    cdef RealMatrix field
    cdef IndexMatrix fieldtopo

    for n in process.prange():
        xi=nodes.getAt(n,2)
        elem=nodeprops.getAt(n,0)
        field,fieldtopo=fieldtopolist[nodeprops.getAt(n,2)]
        fieldtype=ElemType[fieldtopo.getType()]

        #topoinds=[fieldtopo.getAt(elem,m) for m in xrange(fieldtopo.m())] # get the indices of the topology element
        #fieldvals=[[field.getAt(v,w) for w in range(field.m())] for v in topoinds] # extract the field values for each index
        fieldvals=[field.getRow(v) for v in fieldtopo.getRow(elem)]

        value=fieldtype.applyBasis(fieldvals,*xi)
        vec=veclambda(value)
        nodes.setAt(vec,n,1) # set the normal value for the given node


@timing
def calculateDataNormals(dataset,nodes,nodeprops,indlist,fields,vecfunc,task=None):
    '''
    Calculates new normals for the nodes based on the given fields. These normals are used for billboard direction
    vectors rather than surface normals. Arguments:

        dataset - object data set
        nodes - matrix of nodes, nodes.n()==3
        nodeprops - matrix of node properties, nodeprops.getAt(n,2) states which topology in indlist node n is found on
        indlist - list of index matrices defining spatial topologies, len(indlist)==len(fields)
        fields - list of field matrices defining which field corresponds to which topology in indlist
        vecfunc - vector function, calculates a vector from a field entry
        task - task object
    '''

    proccount=chooseProcCount(nodes.n(),0,10000)
    fieldtopolist=SceneUtils.collectFieldTopos(dataset,fields,indlist)

    if proccount!=1:
        shareMatrices(nodes,nodeprops,*listSum(map(list,fieldtopolist)))

    calculateDataNormalsRange(nodes.n(),proccount,task,nodes,nodeprops,fieldtopolist,vecfunc)



@concurrent
def calculateFieldValuesRange(process,RealMatrix field,RealMatrix result,valfunc):
    cdef object vallambda=createValFunc(valfunc,'<<valfunc>>')
    cdef tuple row=field.getRow(process.startval)
    cdef float minv=vallambda(row)
    cdef float maxv=minv
    cdef float val
    cdef int n

    for n in process.prange():
        row=field.getRow(n)
        val=vallambda(row)
        result.setAt(val,n)
        minv=min(minv,val)
        maxv=max(maxv,val)

    return minv,maxv


def calculateFieldValues(RealMatrix field,valfunc=None,task=None):
    '''
    Creates a new one-dimensional RealMatrix object by applying `valfunc' to each member of `field', or returns `field'
    itself it it's one-dimensional and `valfunc' is None. The argument `valfunc' must be a string with a Python expression
    expecting a tuple called `vals' which will be each row of `field'. If `valfunc' is None then "avg(vals)" is used.
    '''
    cdef RealMatrix result
    cdef int proccount
    cdef dict results

    if field.m()==1 and valfunc==None:
        return field

    proccount=chooseProcCount(field.n(),0,10000)
    if proccount!=1:
        field.setShared(True)

    result=RealMatrix(field.getName()+'Val',field.n(),1,True)
    result.meta(StdProps._topology,field.meta(StdProps._topology))
    result.meta(StdProps._spatial,field.meta(StdProps._spatial))

    results=calculateFieldValuesRange(field.n(),proccount,task,field,result,valfunc)

    if isinstance(results[0],Exception):
        result.clear()
        raise results[0]

    return result,min(v[0] for v in results.values()),max(v[1] for v in results.values())


@timing
def calculateMeshSurfNormals(nodes,inds,ext):
    '''
    Returns a Vec3Matrix object containing the normals for each point in Vec3Matrix `nodes' given topology IndexMatrix
    `inds' with external IndexMatrix `ext' (or None if every index is external).
    '''
    results=Vec3Matrix('normals',nodes.n())
    elemtype=ElemType[inds.getType()]
    facerange=range(elemtype.numFaces())
    finds=[elemtype.getFaceIndices(face) for face in facerange]

    for elem in xrange(inds.n()): # calculate normals for each element
        elemnodes=nodes.mapIndexRow(inds,elem)

        for face in facerange: # calculate normals for each face of the current element
            if ext!=None and ext.getAt(elem,face)!=1: # skip internal faces
                continue

            # for each node of the face, calculate the normal at that node's xi position
            for v in finds[face]:
                xi=elemtype.xis[v]
                norm=SceneUtils.calculatePointNormal(elemnodes,elemtype,face,elemnodes[v],xi[0],xi[1])
                vind=inds.getAt(elem,v)
                results.setAt(results.getAt(vind)+norm,vind)

    for r in xrange(results.n()):
        v=results.getAt(r)
        if v.lenSq()>0:
            results.setAt(v.norm(),r)

    return results


