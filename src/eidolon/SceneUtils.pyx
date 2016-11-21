#cython: nonecheck=True

# Eidolon Biomedical Framework
# Copyright (C) 2016 Eric Kerfoot, King's College London, all rights reserved
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


'''This module defines utilities and algorithms that combine Python with the C++ RenderTypes, such as the mesh generation routines.'''

import math
import itertools
import atexit
import os
import glob
import compiler
import sip

import Renderer
cimport Renderer

from Renderer import vec3,transform,rotator,color,Vec3Matrix,RealMatrix,IndexMatrix,ColorMatrix,getSharedDir,unlinkShared,PyVertexBuffer,PyIndexBuffer
from Renderer cimport vec3,transform,rotator,color,Vec3Matrix,RealMatrix,IndexMatrix,ColorMatrix,getSharedDir,unlinkShared,PyVertexBuffer,PyIndexBuffer

import numpy as np
cimport numpy as np

from Utils import *
from Concurrency import *
from MathDef import GeomType,ElemType


# Types for additional index matrices: description, IndexMatrix name suffix, # of components
MatrixType=enum(
	('nodes','Node Matrix',' Nodes',3), # at least 3 components: position,normal,xi, followed possibly with uvw texture coords
	('external','External Face Index',' External',0), # 1 component per face, 1 if external, 0 if internal
	('lines','Line Indices',' Line',2), # 2 components: line start node index, line end node index
	('tris','Triangle Indices',' Triangle',3), # 3 components: 3 tri node indices
	('props','Node Properties',' Props',3), # node properies, 3 components: elem index, face index, index matrix number
	('extinds','Indices of External Elements',' ExtInds',1), # 1 component, index of external point/line/tri elements
	('adj','Face Adjacency Indices', ' AdjInds',0), # 2 components per face, first half states adjacent elem, second half adjacent face
	('filtind','Filter Element Indices',' Filter',1), # 1 component, index of selected element to be included in filter
	('octree','Octree Member Data',' Octree',1), # 1 component, octant member list of indices in an element matrix
)

# Defines standard properties that various matrices or datasets may have as metadata tags
StdProps=enum(
	# used to state the name of the topology the matrix or dataset uses as the spatial geometric topology
	('spatial','Spatial Topology Name'),
	# used to state which topology the data matrix uses for interpolation, same as 'spatial' if the topology is used for geometry and fields
	('topology', 'Related Topology (eg. field) Name'),
	# true if the matrix this is applied to is a spatial geometric (rather than data field) topology
	('isspatial','Spatial Topology Indicator (True/False)'),
	# if a dataset is cloned, this is the original's name
	('isdsclone','Dataset Clone\'s Original Name'),
	# if a matrix is loaded from a file with header info, this should be put here
	('header','Source File Header Data'),
	# this should be set for all matrices loaded from files
	('filename','Source Data Filename'),
	# should be set whenever a file has been moved
	('oldfilename','Source Data Filename'),
	# set to the glob name used to identify a group of matrices (usually per-timestep fields)
	('globname','Globbed Name Group'),
	# set to the length of a matrix before additional values are added as part of a filter
	('origlen','Original Matrix Length'),
	# | separated list of index names used by properties matrices which store what matrix from this list was used to calculate a node
	('indiceslist','Index Matrix Name List'),
	# True if the matrix stores a dataset of values per-element rather than per-node, False or absent otherwise
	('elemdata','Per-element dataset matrix (True/False)'),
	# True if the matrix stores a dataset of values per-element rather than per-node, False or absent otherwise
	('nodedata','Per-node dataset matrix independent of topologies, topology and spatial should not be set (True/False)'),
	# True if the data field is copied for each timestep, since it's the same it should be written only once when storing files
	('timecopy','Indicates a data field is copied for each timestep and so should not be duplicated when written (True/False)'),
	# data matrix value range
	('valrange','Mininum and maximum values separated by |'),
	# octree data for each octant (leaf), a tuple of (depth int, dimensions 3-tuple, center 3-tuple)
	('octreedata','Octree (depth, dimension tuple, center tuple) tuple'),
	# indices for rows of a sparse matrix stored as columns, eg. for a tuple t each row i starts at t[i] and ends on value before t[i+1]
	('sparsematrix','Indices list for the start of rows stored in single column format')
)


# Defines various render queues for drawing objects, these are necessary to ensure transparent objects and UI elements are drawn in correct order
RenderQueues=enum(
	('Default',50),
	('Transparent',60),
	('PlaneImg',58),
	('VolumeImg',59),
	('UI',100),
)

		
# divide a hex into 6 tets by choosing combinations of vertices, this ensures that adjacent hexes divide into tets with matching faces
hexTo6TetInds=( (1,0,2,4), (4,5,6,2), (2,1,4,5), (5,6,2,3), (1,2,3,5), (5,6,7,3) )
# hexes can be divided into 5 tets only, but these can't be used to subdivide a tet, or subdivide a hex and get matching faces
hexTo5TetInds=( (0,5,3,6), (0,3,2,6), (0,5,6,4), (5,3,6,7), (0,1,3,5) )


class PyDataSet(object):
	'''
	Python implementation of a dataset. This ensures that the ownership of matrices remains with Python for GC reasons.
	'''

	def __init__(self,name,nodes,indices=[],fields=[],assignMeta=True):
		'''
		Construct a dataset with the given nodes, indices, and fields data. The `nodes' argument can be a Vec3Matrix
		or a list of vec3 values which will be converted into a Vec3Matrix. The `indices' an `fields' iterables must
		be a dict mapping names to matrices, a list of matrices which will be converted into a dict mapping each of
		the matrices from its name to itself, or a iterable of triples of the form (name,type,data). In the third
		case, `name' will be the matrix name, `type' the matrix type, and `data' must be a list of values for a singe
		column matrix or a list of lists/tuples of values for multiple column matrix. The data or matrices for `indices'
		must be type int or long, and or `fields' must be float.
		'''
		self.name=name
		self.metamap={}
		self.nodes=nodes if isinstance(nodes,Vec3Matrix) else listToMatrix(nodes,'nodes')

		self.indices=dict()
		self.fields=dict()

		#  fill in indices
		if len(indices)>0:
			if isinstance(indices,dict):
				self.indices= dict(indices)
			elif all(isinstance(i,IndexMatrix) for i in indices):
				self.indices= dict((i.getName(),i) for i in indices)
			elif all(isinstance(i,tuple) and len(i) in (3,4) for i in indices):
				for i in indices:
					iname=i[0]
					itype=i[1]
					mat=i[2]
					if not isinstance(mat,IndexMatrix):
						mat=listToMatrix(mat,iname,itype,False,IndexMatrix)

					if len(i)>3:
						mat.meta(StdProps._isspatial,str(bool(i[3])))

					self.indices[iname]=mat

		# fill in fields
		if len(fields)>0:
			if isinstance(fields,dict):
				self.fields= dict(fields)
			elif all(isinstance(i,RealMatrix) for i in fields):
				self.fields= dict((i.getName(),i) for i in fields)
			elif all(isinstance(i,tuple) and len(i) in (2,3,4) for i in fields):
				for f in fields:
					fname=f[0]
					mat=f[1]
					if not isinstance(mat,RealMatrix):
						mat=listToMatrix(mat,fname,'',False,RealMatrix)

					if len(f)>2:
						mat.meta(StdProps._spatial,f[2])
					if len(f)>3:
						mat.meta(StdProps._topology,f[3])

					self.fields[fname]=mat

		# assign default metadata values
		if assignMeta:
			for i in self.indices.values():
				if i.getType() and not i.meta(StdProps._isspatial):
					i.meta(StdProps._isspatial,'True')

			map(self._setDefaultFieldMeta,self.fields.values())

	def _setDefaultFieldMeta(self,fieldmat):
		if fieldmat.meta(StdProps._nodedata) in ('','False'): # set meta values if this isn't already designated a per-node field
			if fieldmat.n()==self.nodes.n() and not fieldmat.meta(StdProps._spatial):
				# if this is a per-node field, mark it as such
				fieldmat.meta(StdProps._nodedata,'True')
			elif fieldmat.meta(StdProps._spatial) and not fieldmat.meta(StdProps._topology):
				# if there's a spatial topology but not a field topology, set the field topology to the spatial
				fieldmat.meta(StdProps._topology,fieldmat.meta(StdProps._spatial))
			else:
				# otherwise choose the first spatial topology
				toponame=first(i.getName() for i in self.indices.values() if i.meta(StdProps._isspatial))
				if toponame:
					if not fieldmat.meta(StdProps._topology):
						fieldmat.meta(StdProps._topology,toponame)

					if not fieldmat.meta(StdProps._spatial):
						fieldmat.meta(StdProps._spatial,toponame)

	def getName(self):
		return self.name

	def hasMetaKey(self,val):
		return val in self.metamap

	def getMetaKeys(self):
		return self.metamap.keys()

	def meta(self,key=None,val=None):
		if not key:
			return '\n'.join('{} = {}'.format(i) for i in self.metamap.items())
		elif not val:
			return self.metamap.get(key,'')
		else:
			self.metamap[key]=val

	def clone(self,name,cloneNodes=False,cloneIndices=False,cloneFields=False):
		oldname=self.getName()
		nodes=self.nodes
		indices=self.indices
		fields=self.fields

		if cloneNodes:
			nodes=nodes.clone()

		if cloneIndices:
			indices=[m.clone() for m in indices.values()]

		if cloneFields:
			fields=[m.clone() for m in fields.values()]

		ds=PyDataSet(name,nodes,indices,fields)
		ds.meta(StdProps._isdsclone,oldname)

		if any(n.startswith(oldname) for n in ds.getIndexNames()):
			ds.renameIndexSet(oldname,name)

		if any(n.startswith(oldname) for n in ds.getFieldNames()):
			ds.renameDataField(oldname,name)

		return ds

	def setNodes(self,nodes):
		self.nodes=nodes

	def getNodes(self):
		return self.nodes

	def getIndexSet(self,name):
		return self.indices.get(name,None)

	def hasIndexSet(self,name):
		return name in self.indices

	def getIndexNames(self):
		return self.indices.keys()

	def setIndexSet(self,mat):
		self.indices[mat.getName()]=mat

	def removeIndexSet(self,name):
		return self.indices.pop(name)

	def renameIndexSet(self,oldname,newname):
		cdef IndexMatrix ind
		cdef RealMatrix field
		cdef str k,f,n,nn
		cdef list names=[n for n in self.getIndexNames() if n.startswith(oldname)]

		#if not names:
		#	raise ValueError,'Unknown name/prefix %r in %r'%(oldname,self)

		for n in names:
			# rename each index set that began with `oldname'
			nn=n.replace(oldname,newname,1)
			ind=self.removeIndexSet(n)
			ind.setName(nn)
			self.setIndexSet(ind)

			# set each metadata field storing the oldname for ind to the new name
			for field in self.fields.values():
				for k in field.getMetaKeys():
					if field.meta(k)==n:
						field.meta(k,nn)

	def renameDataField(self,oldname,newname):
		cdef RealMatrix field
		cdef str n
		cdef list names=[n for n in self.getFieldNames() if n.startswith(oldname)]

		#if not names:
		#	raise ValueError,'Unknown name/prefix %r in %r'%(oldname,self)

		for n in names: # rename all fields
			field=self.getDataField(n)
			self.removeDataField(n)
			field.setName(n.replace(oldname,newname,1))
			self.setDataField(field)

	def enumIndexSets(self):
		return iter(self.indices.values())

	def getDataField(self,name):
		return self.fields.get(name,None)

	def hasDataField(self,name):
		return name in self.fields

	def getFieldNames(self):
		return self.fields.keys()

	def setDataField(self,mat,alias=None):
		self.fields[alias or mat.getName()]=mat
		self._setDefaultFieldMeta(mat)

	def removeDataField(self,name):
		if name in self.fields:
			mat=self.fields.pop(name)
			return mat

	def enumDataFields(self):
		return iter(self.fields.values())

	def findField(self,field,spatialName=None):
		'''
		Find the field in this dataset which has the same name as `field', which matches the glob pattern `field',
		or (if `field' is an iterable of matrices) which is the first matrix in `field' stored in this dataset.
		'''
		fnames=self.getFieldNames()
		name=None

		if spatialName: # retain only those fields which use the named spatial topology
			fnames=[f for f in fnames if self.getDataField(f).meta(StdProps._spatial)==spatialName]

		if isinstance(field,str): # if a string find the field in `dataset' with the same name or which matches the glob pattern
			name=findGlobMatch(field,fnames)
		elif isIterable(field): # choose the member of the field set which is stored in `dataset'
			name=first(f for f in field if f in fnames)
		elif isinstance(field,RealMatrix): # if the field matrix is given, use its name
			name=field.getName()

		return self.getDataField(name)

	def getFieldObject(self,field,spatialName=None):
		return FieldObject(self,self.findField(field,spatialName))

	def getIndexListFields(self,indlist,field):
		result=[]
		for ind in indlist:
			assert ind in self.indices.values()
			f=self.findField(field,ind.getName())
			if f!=None:
				result.append(FieldObject(self,f,ind))
			else:
				result.append(None)

		return result

	def validateDataSet(self):
		cdef int numnodes=self.nodes.n()
		cdef int mini,maxi
		cdef IndexMatrix ind
		cdef list errors=[]
		cdef str typename
		#cdef RealMatrix field

		for ind in self.indices.values():
			mini,maxi=Renderer.minmaxMatrixIndex(ind)
			if isSpatialIndex(ind) and (mini>=numnodes or mini<0 or maxi>=numnodes or maxi<0):
				errors.append('Invalid index %r value range: should be within [0,%i), is actually [%i,%i)'%(ind.getName(),numnodes,mini,maxi))

			typename=ind.getType()
			#if not typename:
			#	errors.append('Index %r has no stated element type'%ind.getName())
			#else:
			if typename:
				if typename not in ElemType:
					errors.append('Unknown element type %r for index %r'%(typename,ind.getName()))
				else:
					et=ElemType[typename]
					if ind.m()!=len(et.xis):
						errors.append('Index %r should have %i columns for element type %r but has %i'%(ind.getName(),len(et.xis),typename,ind.m()))

		assert errors==[],'\n'.join(errors)

	def __repr__(self):
		return 'DataSet<%s,%r,%r>'%(self.getName(),self.indices.keys(),self.fields.keys())

	def __str__(self):
		return getDatasetSummary(self)


def TriDataSet(name,nodes,inds=None,fields=[]):
	'''
	Generate a dataset for a triangle mesh defined by the given name, nodes, and indices. If indices is None, the node
	list is treated like a list of independent triangles with no shared vertices and an index set is generated for such.
	'''
	if inds==None:
		nlen=nodes.n() if isinstance(nodes,Vec3Matrix) else len(nodes)
		inds=[(i,i+1,i+2) for i in xrange(0,nlen,3)]

	return PyDataSet(name,nodes,[(name+MatrixType.tris[1],ElemType._Tri1NL,inds)],fields)


def LineDataSet(name,nodes,inds=None,fields=[]):
	'''
	Generate a dataset for a line mesh defined by the given name, nodes, and indices. If indices is None, the node
	list is treated like a list of independent lines with no shared vertices and an index set is generated for such.
	'''
	inds=inds or [(i,i+1) for i in xrange(0,len(nodes),2)]
	return PyDataSet(name,nodes,[(name+MatrixType.lines[1],ElemType._Line1NL,inds)],fields)


class FieldObject(object):
	def __init__(self,dataset,field,spatialtopo=None):
		self.dataset=dataset
		if isinstance(field,RealMatrix):
			self.field=field
		else:
			self.field=dataset.findField(field)

		assert isinstance(self.field,RealMatrix)
		self.fieldtopo=dataset.getIndexSet(self.field.meta(StdProps._topology))
		assert isinstance(self.fieldtopo,IndexMatrix)
		self.fieldtype=ElemType[self.fieldtopo.getType()]
		self.elemvals=None

		if spatialtopo!=None:
			self.spatialtopo=spatialtopo
		else:
			self.spatialtopo=dataset.getIndexSet(self.field.meta(StdProps._spatial))

		self.spatialtype=None
		if self.spatialtopo!=None:
			assert isinstance(self.spatialtopo,IndexMatrix)
			self.spatialtype=ElemType[self.spatialtopo.getType()]

	def selectElem(self,elem):
		self.elemvals=None
		if 0<=elem<self.fieldtopo.n():
			self.elemvals=[self.field.getRow(v) for v in self.fieldtopo.getRow(elem)]

	def coeffsAt(self,*xis,**basisArgs):
		for xi in xis:
			yield self.fieldtype.basis(*xi,**basisArgs)

	def applyCoeffs(self,*coeffs):
		if self.elemvals!=None:
			for c in coeffs:
				yield self.fieldtype.applyCoeffs(self.elemvals,c)

	def evalAt(self,*xis,**basisArgs):
		if self.elemvals!=None:
			for xi in xis:
				yield self.fieldtype.applyBasis(self.elemvals,*xi,**basisArgs)

	def setShared(self,shared):
		if shared:
			self.dataset=None
			self.elemvals=None
			self.field.setShared(True)
			self.fieldtopo.setShared(True)
			if self.spatialtopo!=None:
				self.spatialtopo.setShared(True)
				self.spatialtype=self.spatialtopo.getType() # convert the type back to string

			self.fieldtype=self.fieldtopo.getType() # convert the type back to string
		else: # convert the string type names back to their respective type objects (leave the matrices alone)
			if isinstance(self.fieldtype,str):
				self.fieldtype=ElemType[self.fieldtype]

			if isinstance(self.spatialtype,str):
				self.spatialtype=ElemType[self.spatialtype]

	def __repr__(self):
		return 'FieldObject<%s, Topo=%s>'%(self.field.getName(),self.fieldtopo.getName())


cdef class Face(object):
	cdef readonly tuple vertices
	cdef readonly int farid
	cdef readonly int faceid
	cdef readonly int elemid
	cdef long vhash

	def __init__(self,vertices,int farid,int faceid,int elemid):
		self.vertices=tuple(sorted(vertices))
		self.farid=farid
		self.faceid=faceid
		self.elemid=elemid
		self.vhash=hash(self.vertices)

	def __hash__(self):
		return self.vhash

	def __cmp__(self,Face other):
		return cmp(self.vertices,other.vertices)

	#def __eq__(self,other):
	#	return self.vertices == other.vertices

	def __richcmp__(Face self,v,int op):
			if v is None:
				return op==3

			if not isinstance(v,Face):
				return False

			if op in (1,2,5) and self.vertices==v.vertices:
				return True

			return False

	#def __getitem__(self,key):
	#	return (self.vertices+(self.far,)).__getitem__(key)

	@staticmethod
	def fromFaceDef(IndexMatrix ind,int elem,face,int facenum):
		return Face((ind.getAt(elem,f) for f in face[:-1]),ind.getAt(elem,face[-1]),facenum,elem)

	@staticmethod
	def fromElem(IndexMatrix ind,int elem,int facenum=-1,object elemtype=None):
		elemtype=elemtype or ElemType[ind.getType()]

		if facenum!=-1:
			face=elemtype.faces[facenum]
			return Face.fromFaceDef(ind,elem,face,facenum)
		else:
			faces=[]
			for i,face in enumerate(elemtype.faces):
				faces.append(Face.fromFaceDef(ind,elem,face,i))

			return faces


cdef class BoundBox(object):
	'''Defines an axis-aligned bound box by storing the minimal and maximal corners, center, and radius.'''
	cdef readonly vec3 maxv
	cdef readonly vec3 minv
	cdef readonly vec3 center
	cdef readonly float radius

	def __init__(self,vecs=None):
		if isinstance(vecs,Vec3Matrix):
			vecs=Renderer.calculateBoundBox(vecs)

		self.addVecIter(vecs or [vec3()])

	def _addMinMax(self,vec3 v):
		if not self.maxv:
			self.maxv=vec3(v)
			self.minv=vec3(v)

		self.minv.setMinVals(v)
		self.maxv.setMaxVals(v)

	def addVecIter(self,vecs):
		for v in vecs:
			self._addMinMax(v)

		self.addVec(self.minv) # triggert center and radius calculations

	def addVec(self,vec3 v):
		self._addMinMax(v)
		self.center=(self.maxv+self.minv)*0.5
		self.radius=self.maxv.distTo(self.center)

	def getDimensions(self):
		return self.maxv-self.minv

	def getCorners(self):
		'''Get the corners of the bound box in XYZ order (ie. the order expected by hex types).'''
		minx,miny,minz=self.minv
		maxx,maxy,maxz=self.maxv
		return [vec3(minx,miny,minz),vec3(maxx,miny,minz),vec3(minx,maxy,minz),vec3(maxx,maxy,minz),
			vec3(minx,miny,maxz),vec3(maxx,miny,maxz),vec3(minx,maxy,maxz),vec3(maxx,maxy,maxz)]

	def getExternalPoint(self):
		'''Returns an unspecified point guaranteed to be outside the box and coplanar if the box is 2D.'''
		return self.maxv+(self.maxv-self.minv).norm()

	def clampWithin(self,vec3 v):
		'''Return `v' clamped within the bound box, which isn't necessarily the closest point in the box to `v'.'''
		return v.clamp(self.minv,self.maxv)

	def __contains__(self,n):
		'''Returns true if vec3 `n' is in the bound box, or if all corners of BoundBox `n' are in the bound box.'''
		if isinstance(n,vec3):
			return n.inAABB(self.minv,self.maxv)
		else:
			return all(nn in self for nn in n.getCorners())

	def intersects(self,BoundBox n):
		'''Returns True if any corner of BoundBox `n' is within this bound box.'''
		return any(nn in self for nn in n.getCorners())

	def getInternalPlane(self,vec3 pt,vec3 norm):
		'''
		Returns a node within the bound box which is on the given plane and the radius of the spherical cap
		defined by the plane cutting through the bound sphere, or None,None if the node is not within the bound box.
		'''
		cdef list nodes=self.getCorners()
		cdef list heights=[n.planeDist(pt,norm) for n in nodes]
		cdef list intersects=[nodes[i].lerp(lerpval,nodes[j]) for i,j,lerpval in Renderer.calculateHexValueIntersects(0,*heights)]
		if intersects:
			center=avg(intersects,vec3())
			return center, math.sqrt(max(center.distToSq(i) for i in intersects))
		else:
			return None

	def isEmpty(self):
		'''Returns True if the distance between the minimal and maximal corners is infinitesimal.'''
		return self.minv.distTo(self.maxv)<epsilon

	#def __eq__(self,BoundBox other):
	#	'''Returns True if `other' is not None and represents the same BoundBox as `self' (ie. equal corners).'''
	#	return other!=None and self.minv==other.minv and self.maxv==other.maxv

	def __richcmp__(BoundBox self,v,int op):		
		#< 0, > 4, != 3, <= 1, == 2, >= 5
		
		if v is None or not isinstance(v,BoundBox):
			return op==3

		if v is self:
			return op in (1,2,5)
			
		if op==3:
			return self.minv!=v.minv or self.maxv!=v.maxv

		if op in (1,2,5):
			return self.minv==v.minv and self.maxv==v.maxv

		return False

	def __add__(self,BoundBox bb):
		'''Returns the BoundBox containing `self' and `bb'.'''
		return BoundBox([self.minv,self.maxv,bb.minv,bb.maxv])

	def __div__(self,BoundBox bb):
		'''Returns the BoundBox representing the intersection of `self' and the BoundBox `bb'.'''
		return BoundBox(c.clamp(bb.minv,bb.maxv) for c in self.getCorners())

	def __repr__(self):
		return 'BoundBox([%s,%s])' % (str(self.minv),str(self.maxv))

	def __str__(self):
		return '(%s) -> (%s) center=(%s) radius=%.4f' % (vec3SimpleStr(self.minv),vec3SimpleStr(self.maxv),vec3SimpleStr(self.center),self.radius)

	def transform(self,trans,vec3 scale=vec3(1),rot=(0,0,0)):
		'''
		Returns an BoundBox containing the corners of `self' transformed by the translation, scale, and rotation values.
		If `trans' is an instance of transform instead of vec3, then this used in place of transform(trans,scale,rot).
		'''
		if not isinstance(trans,transform):
			if not isinstance(rot,rotator):
				rot=rotator(*rot)

			trans=transform(trans,scale,rot)

		return BoundBox(trans*p for p in self.getCorners())

	@staticmethod
	def union(bbs):
		'''Returns the BoundBox containing all those not None in `bbs', defaulting to BoundBox() if none present.'''
		bbs=filter(bool,bbs)
		return sum(bbs,bbs[0] if bbs else BoundBox())


cdef class Octree(object):
	'''
	This implements a map between vectors an given values using a recursive octree data structure
	to optimize searching by partitioning space. Vectors are tested for equivalence using the '=='
	operator. Vectors are added to the tree which are assigned to their appropriate node as determined
	by spatial searching; if a vector is already present which is considered equivalent the stored
	one is returned.

	Octants:
		0 = (-,-,-)
		1 = (+,-,-)
		2 = (-,+,-)
		3 = (+,+,-)
		4 = (-,-,+)
		5 = (+,-,+)
		6 = (-,+,+)
		7 = (+,+,+)
		8 = (0,0,0) (root)
	'''

	cdef readonly Octree parent
	cdef readonly BoundBox aabb
	cdef readonly int depth
	cdef readonly int octant
	cdef readonly vec3 dim
	cdef readonly vec3 center
	cdef public dict nodes
	cdef public object leafdata
	cdef readonly object equalityFunc
	cdef readonly str name
	cdef readonly list subtrees

	def __init__(self,int depth,vec3 dim,vec3 parentcenter,equalityFunc=None,int octant=8,Octree parent=None):
		'''
		Initializes a new self-contained octree or an octant within one. When creating a new octree, `octant' and
		`parent' must be left with their default values, `depth' will define how many levels of sub-octants to create,
		`dim' is the total dimension of the AABB area covered by the tree, and `parentcenter' is the center of this
		area. The `equalityFunc' function is used to test equality between nodes added to the tree, operator.eq is used
		if None is given for this argument. When sub-octrees are being instantiated, the values for all arguments will
		be chosen by the instantiating parent.
		'''
		assert octant==8 or parent!=None

		self.parent=parent # parent octant
		self.depth=depth # depth==0 means this is a leaf node
		self.octant=octant # between 0 and 8 as described above
		self.dim=dim # dimensions of this octant
		dim2=self.dim*0.5

		self.center=parentcenter+(dim2*self.octantMul(self.octant)) # center of this octant
		self.aabb=BoundBox([self.center-dim2,self.center+dim2])

		self.nodes=dict()
		self.leafdata=[]
		self.equalityFunc=operator.eq if equalityFunc is None else equalityFunc

		self.name='Oc' if self.parent==None else self.parent.name+str(self.octant)
		self.subtrees=[] if depth==0 else [Octree(depth-1,dim2,self.center,self.equalityFunc,oc,self) for oc in range(8)]

	def getID(self):
		assert self.depth<=16, 'Cannot create unique IDs for octrees greater than 16 in depth.'
		pid=0 if self.parent==None else self.parent.getID()
		return long(pid<<4 | self.octant)

	def __repr__(self):
		return '%s(%i %i %r)' % (self.name, self.depth,self.octant,self.center)

	def getLeaves(self):
		'''Returns the Octree instances at the bottom of the tree in depth-first order (rather than spatial order).'''
		if self.depth==1:
			return self.subtrees
		else:
			return listSum(t.getLeaves() for t in self.subtrees)

	def addTree(self,Octree other,initfunc,mergefunc):
		'''Add the elements of `other' into this octree, using `initfunc' to initialize values and `mergefunc' to merge them.'''
		for leaf1,leaf2 in zip(self.getLeaves(),other.getLeaves()):
			for n2,vals2 in leaf2.nodes.items():
				n1,vals1=leaf1.addNode(n2,initfunc())
				mergefunc(vals1,vals2)

	def isInOctant(self,vec3 n):
		'''Returns true if the node 'n' is in the octant's axis-aligned cuboid space.'''
		return n.inAABB(self.aabb.minv,self.aabb.maxv)

	def intersectsPlane(self,vec3 planept,vec3 planenorm):
		'''Returns True if the plane defined by the point `planept' and normal `planenorm' passes through this octant.'''
		#return self.aabb.getInternalPlane(planept,planenorm)!=None
		return planeIntersectsElem(self.aabb.getCorners(),planept,planenorm)

	def getIntersectedLeaves(self,vec3 planept,vec3 planenorm):
		'''Returns the list of leaf octants which the plane defined by (planept,planenorm) intersects.'''
		if not self.intersectsPlane(planept,planenorm):
			return []
		elif self.depth==0:
			return [self]
		else:
			return listSum(l.getIntersectedLeaves(planept,planenorm) for l in self.subtrees)

	def octantMul(self,int octant):
		'''Returns a multiplicative vector corresponding to this octant's signs.'''
		if octant==8:
			return vec3()

		x=1 if octant%2==1 else -1
		y=1 if octant in (2,3,6,7) else -1
		z=1 if octant>3 else -1

		return vec3(x,y,z)

	def getOctant(self,vec3 n):
		'''Get the child octant within this octant which should contain `n'.'''
		cdef vec3 nn=n-self.center
		cdef int result=0
		if nn.z()>=0:
			result+=4
		if nn.y()>=0:
			result+=2
		if nn.x()>=0:
			result+=1

		return result

	def __contains__(self,vec3 n):
		'''Returns true if 'n' is in the octant and stored by an Octree node.'''
		return self.isInOctant(n) and (self._getEquivalentNode(n) is not None or any(n in t for t in self.subtrees))

	def numNodes(self):
		'''Returns the number of nodes stored in this tree.'''
		return sum(len(leaf.nodes) for leaf in self.getLeaves())

	def _getEquivalentNode(self,vec3 n):
		'''Returns the first key in `self.nodes' which is equal to `n' acccording the equality function.'''
		return first(nn for nn in self.nodes if self.equalityFunc(n,nn))

	def getLeaf(self,vec3 n):
		'''Find the Octree leaf object whose bound box contains `n', returning None if `n' is outside.'''
		if self.depth==0: # this is a leaf so must be it
			return self

		if self.octant==8 and not self.isInOctant(n): # if the root octant and `n' is not in our space, return None
			return None

		return self.subtrees[self.getOctant(n)].getLeaf(n) # find the child octant that contains `n'

	def getNode(self,vec3 n):
		'''Returns the value stored in the tree for 'n' or None if not found.'''
		leaf=self.getLeaf(n)
		return leaf and leaf.nodes.get(n,None)

	def __iter__(self):
		'''Iterates over all (node,value) pairs stored in this tree.'''
		if self.depth==0:
			for n in self.nodes.items():
				yield n
		else:
			for sb in self.subtrees:
				for n in sb:
					yield n

	def addNode(self,vec3 n,vals):
		'''
		Add the node 'n' into the tree. If an equivalent is not present, 'n' is added to the octree with 'vals' as its
		mapped value and both are returned as well as the leaf object. If an equivalent node is found this and its
		value is returned with the leaf object, ignoring 'vals' entirely.
		'''
		cdef object leaf=self.getLeaf(n)
		cdef vec3 nn

		if leaf:
			nn=leaf._getEquivalentNode(n)
			if nn is not None:
				return nn,leaf.nodes[nn],leaf
			else:
				leaf.nodes[n]=vals
				return n,vals,leaf
		else:
			return None,None,None

	def addLeafData(self,vec3 n,val):
		'''Find the leaf `n' belongs in and add `val' to its `treedata' field.'''
		leaf=self.getLeaf(n)
		if leaf:
			leaf.leafdata.append(val)


@atexit.register
def cleanupMatrices():
	'''
	Do cleanup of shared memory segments created for this process. On Linux this relies on
	the naming convention Matrix uses, which for now is to prepend __viz__ to the shared name.
	In OSX this uses the SHMDIRVAR directory in the global Config object which will store the names
	of open shared memory segments as file names.
	'''
	pid=os.getpid()
	shmdir=getSharedDir()
	if not shmdir:
		return

	if isLinux:
		for f in glob.glob(shmdir+'/__viz__*'):
			fs=filter(bool,f.split('_'))
			ppid=int(fs[2]) # PPID of process that created f
			fpid=int(fs[3]) # PID of process that created f

			# Remove f if this process created f or is the creator's parent, or if the creator doesn't exist.
			# pid==ppid if this process is the main process and f was created by an algorithm process
			# pid==fpid if this process (either main or algorithm) created f
			if pid in (ppid,fpid) or not processExists(fpid):
				os.remove(f)

	elif isDarwin:
		for f in glob.glob(shmdir+'/*'):
			#with f(f) as ff: # get the creator process ID from the file contents
			#	fpid=int(ff.read())
			fpid=int(open(f).read())
			# remove f if this process created it or the creator doesn't exist
			if fpid==pid or not processExists(fpid):
				unlinkShared(os.path.split(f)[1])
				os.remove(f)


def getDatasetSummary(ds):
	result='Dataset '+str(ds.getName())
	nodes=ds.getNodes()
	memtotal=nodes.memSize()
	result+='\n  Nodes: %i x %i (%s)' %(nodes.n(),nodes.m(),getUnitValue(memtotal))
	result+='\n  Indices:'

	for i in ds.getIndexNames():
		indmat=ds.getIndexSet(i)
		mem=indmat.memSize()
		memtotal+=mem
		result+='\n    %s: %i x %i (%s)' %(str(i),indmat.n(),indmat.m(),getUnitValue(mem))

	result+='\n  Fields:'

	for i in ds.getFieldNames():
		dmat=ds.getDataField(i)
		mem=dmat.memSize()
		memtotal+=mem
		result+='\n    %s: %i x %i (%s)' %(str(i),dmat.n(),dmat.m(),getUnitValue(mem))

	result+='\n  Mem Total: '+getUnitValue(memtotal)
	return result


def getDatasetSummaryTuples(*datasets):
	result=[]
	memtotalall=0.0

	for ds in datasets:
		nodes=ds.getNodes()
		memtotal=nodes.memSize()

		result.append( ('Dataset ',str(ds.getName())) )
		result.append( ('Nodes','%i x %i (%s)' %(nodes.n(),nodes.m(),getUnitValue(memtotal))) )

		for i in ds.getIndexNames():
			indmat=ds.getIndexSet(i)
			mem=indmat.memSize()
			memtotal+=mem
			result.append( ('Index','%s %i x %i (%s)' %(str(i),indmat.n(),indmat.m(),getUnitValue(mem))) )

		for i in ds.getFieldNames():
			dmat=ds.getDataField(i)
			mem=dmat.memSize()
			memtotal+=mem
			result.append( ( 'Field','%s: %i x %i (%s)' %(str(i),dmat.n(),dmat.m(),getUnitValue(mem))) )

		memtotalall+=memtotal

	result.append( ('Mem Total', getUnitValue(memtotalall)) )
	return result


def shareMatrices(*mats):
	'''
	For each matrix in `mats' which is not None and non-empty, make it shared and add it to the resulting tuple,
	otherwise add None to the tuple.
	'''
	result=[]
	for m in mats:
		if m!=None and m.n()>0:
			m.setShared(True)
			result.append(m)
		else:
			result.append(None)

	return tuple(result)


def unshareMatrices(*mats):
	'''Unshare all non-None members of `mats'.'''
	for m in filter(bool,mats):
		m.setShared(False)


def epsilonClamp(v,minv,maxv,mult=10):
	return clamp(v,minv+epsilon*mult,maxv-epsilon*mult)


def vec3SimpleStr(v):
	return '%.3f, %.3f, %.3f' % (v.x(),v.y(),v.z())


def matrixToStr(mat):
	return '%s %s %i %i\n%s'%(mat.getName(),mat.getType(),mat.n(),mat.m(),'\n'.join(map(repr,matrixToList(mat))))


def matrixToList(mat):
	assert mat!=None
	if mat.m()==1:
		return [mat.getAt(n) for n in xrange(mat.n())]
	else:
		return [mat.getRow(n) for n in xrange(mat.n())]


def listToMatrix(mat,name='mat',mtype='',isShared=False,objtype=None):
	try:
		width=max(len(i) for i in mat)
	except:
		width=1

	assert len(mat)>0
	assert width==1 or all(all(type(j)==type(mat[0][0]) for j in i) for i in mat), "Matrix `mat' must contain all the same type"
	assert width>1 or all(type(i)==type(mat[0]) for i in mat), "Matrix `mat' must contain all the same type"

	firstitem=mat[0][0] if width>1 else mat[0]

	if not objtype:
		if isinstance(firstitem,vec3):
			objtype=Vec3Matrix
		elif isinstance(firstitem,float):
			objtype=RealMatrix
		elif isinstance(firstitem,int):
			objtype=IndexMatrix
		elif isinstance(firstitem,color):
			objtype=ColorMatrix
		else:
			raise TypeError,'Cannot determine matrix type for lists of %s objects of max width %i'%(type(firstitem),width)

	m=objtype(name,mtype,len(mat),width,isShared)
	m.fromList(mat)
	return m


def matrixToArray(mat,dtype=None):
	'''Converts a RealMatrix or IndexMatrix `mat' to a Numpy array with type `dtype' or the matching type to `mat'.'''
	assert isinstance(mat,(RealMatrix,IndexMatrix))
	dtype=dtype or np.dtype(float if isinstance(mat,RealMatrix) else int)
	return np.asarray(mat).astype(dtype)


def arrayToMatrix(arr,mat):
	'''Fills the RealMatrix or IndexMatrix `mat' with the contents of Numpy array `arr' converted to the correct format.'''
	np.asarray(mat)[:,:]=arr


def storeMatrixToFile(filename,mat,metanames=[]):
	'''Store a matrix to a file in a format understood by readMatrixFromFile().'''
	strfunc=str
	mtype='index'

	if isinstance(mat,Vec3Matrix):
		strfunc=lambda v:'%f %f %f' % (v.x(),v.y(),v.z())
		mtype='vec3'
	elif isinstance(mat,ColorMatrix):
		strfunc=lambda c:'%f %f %f %f' %(c.r(),c.g(),c.b(),c.a())
		mtype='color'
	elif isinstance(mat,RealMatrix):
		mtype='real'

	o=None
	try: #with open(filename,'w') as o: # with block has problems with Cython
		o=open(filename,'w')
		lines=[mat.getName(),mtype,mat.getType(),'%i %i'%(mat.n(),mat.m())]

		for mn in metanames:
			lines.append('%s = %s'%(mn,mat.meta(mn)))

		o.write('\n'.join(lines)+'\n')

		for n in xrange(mat.n()):
			vals=mat.getRow(n)
			o.write(' '.join(map(strfunc,vals))+'\n')
	finally:
		o.close()


def readMatrixFromFile(filename):
	'''Read a matrix stored in a file by storeMatrixToFile().'''
	filename=os.path.abspath(filename)
	mat=None

	o=None
	try: #with open(filename,'w') as o: # with block has problems with Cython
		o=open(filename,'w')
		name=o.readline().strip()
		mtype=o.readline().strip()
		elemtype=o.readline().strip()
		n,m=map(int,o.readline().split())

		assert mtype in ('index','real','vec3','color'),mtype

		elemlen=1
		if mtype=='vec3':
			elemlen=3
			convfunc=lambda x,y,z:vec3(float(x),float(y),float(z))
			mattype=Vec3Matrix
		elif mtype=='color':
			elemlen=4
			convfunc=lambda r,g,b,a:color(float(r),float(g),float(b),float(a))
			mattype=ColorMatrix
		elif mtype=='real':
			convfunc=float
			mattype=RealMatrix
		else:
			convfunc=int
			mattype=IndexMatrix

		mat=mattype(name,elemtype,n,m)
		mat.meta(StdProps._filename,filename)

		line=o.readline()
		while '=' in line:
			name,value=line.split('=')
			mat.meta(name.strip(),value.strip())
			line=o.readline()

		index=0
		while line!='':
			vals=line.split()
			if elemlen==1:
				rvals=map(convfunc,vals)
			else:
				rvals=[convfunc(*vals[i:i+elemlen]) for i in range(0,len(vals),elemlen)]

			mat.setRow(index,*rvals)
			index+=1
			line=o.readline()
	finally:
		o.close()
	return mat


def matIterate(mat):
	'''Yields every (row,column) index of `mat' in column-row order.'''
	return trange(mat.n(),mat.m())


def validIndices(mat,n,m=0):
	'''Returns True if 0<=n<mat.n() and 0<=m<mat.m().'''
	return 0<=n<mat.n() and 0<=m<mat.m()


@concurrent
def applyMatOpRange(process,mat,opstring,localmap,minn,minm,maxm):
	'''Applies `opstring' to `mat' concurrently with `localmap' as added variables to the evaluating environment.'''

	matcomp=compiler.compile(opstring,'<<opstring>>','eval')

	def op(val,n,m):
		return eval(matcomp,globals(),locals())

	mat.applyCell(op,minn+process.startval,minm,minn+process.endval,maxm)

	process.setProgress(process.endval-process.startval+1)


def applyConcurrentMatOp(mats,opstring,minn=0,maxn=None,minm=0,maxm=None,task=None,**kwargs):
	'''
	Concurrently evaluates the expression `opstring' for every entry in each of `mats'. The argument `mats' must be
	a single matrix or a list/tuple thereof. The string `opstring' must be an expression returning the same type of
	value stored in any member of `mats'. Its environment consists of `val' containing the previous value, `n' and `m'
	indicating which row and column `val' was drawn from. The expression is only applied to rows from `minn' to `maxn'
	and columns from `minm' to `maxm'. A value of None for `maxn' or `maxm' represents the maximal row or column value.
	This all implies that the matrices of `mats' must be large enough for these bounds to make sense. The task object
	is used for progress reporting and is not necessary. Any additional keyword arguments are passed to the expression
	when called as global values; the values stored in these must all be pickable (ie. matrices must be shared).
	'''

	if not isIterable(mats):
		mats=[mats]

	for mat in mats:
		_maxn=maxn if maxn!=None else mat.n()
		_maxm=maxm if maxm!=None else mat.m()
		matrange=_maxn-minn

		proccount=chooseProcCount(matrange*(_maxm-minm),0,2000)
		mat.setShared(proccount!=1)
		applyMatOpRange(matrange,proccount,task,mat,opstring,kwargs,minn,minm,_maxm)


def planeIntersectsElem(nodes,vec3 planept,vec3 planenorm):
	'''Returns True if the plane defined by the given point and normal intersects the element defined by `nodes'.'''
	minh,maxh=minmax(n.planeDist(planept,planenorm) for n in nodes)
	return minh<=0<=maxh


def getSliceTriOrdering(float ab,float bc,float ca):
	'''
	Returns an node ordering for a triangle such that the vertex whose sign differs from the others is first. The values
	for the vertices are `ab', `bc', and `ca' which represent some scalar property which is used for ordering. Winding
	order is retained in the result, which is None if all arguments are positive or all are negative.
	'''
	cdef int numbelow=0,i

	if ab<0:
		numbelow+=1
	if bc<0:
		numbelow+=1
	if ca<0:
		numbelow+=1

	if numbelow==0 or numbelow==3:
		return None

	if numbelow==1: # only 1 node is below plane, rotate so that this one node is `a' then divide
		if bc<0:
			return 1,2,0
		elif ca<0:
			return 2,0,1
		else:
			return 0,1,2
	elif numbelow==2: # 2 nodes below plane, rotate so `a' is above and divide
		if ca>=0:
			return 2,0,1
		elif bc>=0:
			return 1,2,0
		else:
			return 0,1,2


def calculateTetIsosurf(fieldvals,fieldtype,elemtype,val,refine=0):
	'''
	Yields a series of xi coordinate triples defining a triangulation of the isosurface at the value `val' in the
	tet. The values `fieldvals' must be a list of float values, one for each node, representing the dataset to define
	the isosurface for. the `elemtype' value must define a tetrahedral element type, which will be divided into linear
	tets a number of times as defined by `refine' to produce a finer surface.
	'''

	refine=max(refine,elemtype.order-1)
	numpos=sum(1 if v>=val else 0 for v in fieldvals)
	if numpos in (0,len(fieldvals)): # tet not sliced, otherwise 1, 2, or 3 nodes are above `val'
		return

	if refine>0:
		for tet in divideTettoTet(1,refine):
			tnodes=[fieldtype.applyBasis(fieldvals,*xi) for xi in tet] # interpolate the node values for the embedded tet
			for sxi in calculateTetIsosurf(tnodes,ElemType.Tet1NL,ElemType.Tet1NL,val):
				yield tuple(ElemType.Tet1NL.applyBasis(tet,*xi) for xi in sxi) # convert each xi triple back to original tet xi space

		return

	elemtype=ElemType.Tet1NL # should be linear tet only by this point
	assert refine==0 # recursive call above should call this with no refinement value

	if len(fieldvals)!=len(elemtype.xis):
		nodevals=[fieldtype.applyBasis(fieldvals,*xi) for xi in elemtype.xis]
	else:
		nodevals=fieldvals

	sortindex=sorted(range(len(nodevals)),key=lambda i:val-nodevals[i])

	xis=[vec3(*elemtype.xis[i]) for i in sortindex]
	absvals=[abs(nodevals[i]-val) for i in sortindex]

	def lerpXiVal(v1,v2):
		'''Calculates the xi coordinate along the edge (v1,v2) of the tet.'''
		val1=absvals[v1]
		val2=val1+absvals[v2]
		xi1=xis[v1]
		xi2=xis[v2]
		return xi1 if val2==0 else xi1.lerp(val1/val2,xi2)

	if numpos in (1,3): # either 1 node is above the plane or 1 node is below, sliced area is thus triangular
		if numpos==3: # 1 node below plane, flip order so that the node below is the first node in the three lists
			xis.reverse()
			absvals.reverse()

		yield lerpXiVal(0,1),lerpXiVal(0,2),lerpXiVal(0,3)
	else: # 2 nodes above and 2 below, slice is thus rectangular
		xi1=lerpXiVal(0,2)
		xi2=lerpXiVal(0,3)
		xi3=lerpXiVal(1,2)
		xi4=lerpXiVal(1,3)

		yield xi1,xi2,xi3
		yield xi2,xi4,xi3


def calculateHexIsosurf(fieldvals,fieldtype,elemtype,val,refine=0):
	'''
	Yields a series of xi coordinate triples defining a triangulation of the isosurface at the value `val' in the
	hex. The values `fieldvals' must be a list of float values, one for each node of the field's type, representing
	the dataset to define the isosurface for. The `fieldtype' represents the type of the field topology. The `elemtype'
	value must define a hexahedral element type, which will be divided into linear hexes a number of times as defined
	by `refine' to produce a finer surface.
	'''
	refine=max(refine,elemtype.order-1)
	numpos=sum(1 if v>=val else 0 for v in fieldvals)
	if numpos in (0,len(fieldvals)): # hex not sliced, otherwise 1, 2, or 3 nodes are above `val'
		return

	if refine>0:
		for subhex in divideHextoHex(1,refine):
			tnodes=[fieldtype.applyBasis(fieldvals,*xi) for xi in subhex] # interpolate the node values for the embedded hex
			for sxi in calculateHexIsosurf(tnodes,ElemType.Hex1NL,ElemType.Hex1NL,val):
				yield tuple(ElemType.Hex1NL.applyBasis(subhex,*xi) for xi in sxi) # convert each xi triple back to original hex xi space

		return

	elemtype=ElemType.Hex1NL
	xis=[vec3(*xi) for xi in elemtype.xis]

	if len(fieldvals)!=len(xis):
		nodevals=[fieldtype.applyBasis(fieldvals,*xi) for x in xis]
	else:
		nodevals=fieldvals

	assert len(nodevals)==len(xis),str(len(nodevals))
	intersects=[xis[i].lerp(lerpval,xis[j]) for i,j,lerpval in Renderer.calculateHexValueIntersects(val,*nodevals)]

	if len(intersects)>0:
		invplane=rotator(intersects[0].planeNorm(intersects[1],intersects[2]),vec3(0,0,1))

		center=avg(intersects,vec3()) # determine the center of the intersect patch
		intersectangles=[]

		for n in intersects: # rotate the points (centered around `center') to be on the XY plane and store their polar x angles
			nn=invplane*(n-center)
			intersectangles.append((n,math.atan2(nn.y(),nn.x())))

		intersectangles.sort(key=lambda x:x[1]) # sort The points by their angles; this will yield a circular list of points

		xi0,a=intersectangles.pop(0)

		for i in xrange(len(intersectangles)-1):
			xi1,a=intersectangles[i]
			xi2,a=intersectangles[i+1]

			yield xi0,xi1,xi2


def calculateElemIsosurf(fieldvals,fieldtype,elemtype,val,refine=-1):
	assert elemtype.geom in (GeomType._Tet,GeomType._Hex)

	if refine==-1:
		refine=3+elemtype.order

	if elemtype.geom==GeomType._Tet:
		isofunc=calculateTetIsosurf
	else:
		isofunc=calculateHexIsosurf

	for tri in isofunc(fieldvals,fieldtype,elemtype,val,refine):
		yield tri


def sliceElementPlane(nodes,elemtype,pt,norm,refine=-1):
	'''
	Yields triples of xi values for triangles defining the surface within the given element coincident with the plane
	defined by the point `pt' and normal `norm'. The `elemtype' must define and tet or a hex, and `nodes' must be the
	control poitns for the element defined in the same coordinate space.
	'''
	assert elemtype.geom in (GeomType._Tet,GeomType._Hex)

	norm=norm.norm()
	heights=[n.planeDist(pt,norm) for n in nodes]

	for a,b,c in calculateElemIsosurf(heights,elemtype,elemtype,0,refine):
		n1=elemtype.applyBasis(nodes,*a)
		n2=elemtype.applyBasis(nodes,*b)
		n3=elemtype.applyBasis(nodes,*c)

		if n1.planeNorm(n2,n3)!=norm: # flip triangle if not facing same direction as plane
			b,c=c,b
			n2,n3=n3,n2

		yield n1,n2,n3,a,b,c


def isoIntersectElement(vals,inds):
	for i,j in inds:
		h1=vals[i]
		h2=vals[j]
		if (h1>=0 and h2<0) or (h1<0 and h2>=0):
			h1=abs(h1)
			h2=abs(h2)
			yield i,j,h1/float(h1+h2)


def calculateLinearTriIsoline(float ab, float bc,float ca):
	cdef tuple order=getSliceTriOrdering(ab,bc,ca)
	cdef list xis,av
	cdef int a,b,c
	cdef float lxi1,lxi2

	if not order:
		return None

	a,b,c=order
	av=[abs(ab),abs(bc),abs(ca)]
	xis=[vec3(0.0,0.0,0.0), vec3(1.0,0.0,0.0), vec3(0.0,1.0,0.0)]

	lxi1=av[a]/(av[a]+av[b])
	lxi2=av[a]/(av[a]+av[c])

	return xis[a].lerp(lxi1,xis[b]),xis[a].lerp(lxi2,xis[c])


def calculateTriIsoline(list nodevals,object elemtype,float val,int refine=0):
	cdef int numpos=sum(1 if v>=val else 0 for v in nodevals)
	cdef list vtri,tnodes

	if numpos==0 or numpos==len(nodevals): # tri not sliced
		return

	if refine>0:
		for tri in divideTritoTris(refine):
			vtri=[vec3(x,y,0) for x,y in tri]
			tnodes=[elemtype.applyBasis(nodevals,x,y,0) for x,y in tri] # interpolate the node values for the embedded tri
			for sxi in calculateTriIsoline(tnodes,ElemType.Tri1NL,val):
				yield tuple(ElemType.Tri1NL.applyBasis(vtri,*xi) for xi in sxi) # convert each xi pair back to original tri xi space

		return

	iso=calculateLinearTriIsoline(*[(v-val) for v in nodevals])
	if iso:
		yield iso


def calculateQuadIsoline(nodevals,elemtype,val,int refine=0):
	cdef int numpos=sum(1 if v>=val else 0 for v in nodevals)
	cdef list vquad,tnodes,xis,diffvals,inters

	if numpos in (0,len(nodevals)): # quad not sliced
		return

	if refine>0:
		for quad in divideQuadtoQuads(refine):
			vquad=[vec3(x,y,0) for x,y in quad]
			tnodes=[elemtype.applyBasis(nodevals,x,y,0) for x,y in quad] # interpolate the node values for the embedded quad
			for sxi in calculateQuadIsoline(tnodes,ElemType.Quad1NL,val):
				yield tuple(ElemType.Quad1NL.applyBasis(vquad,*xi) for xi in sxi) # convert each xi pair back to original quad xi space

		return

	elemtype=ElemType.Quad1NL
	assert refine==0 # recursive call above should call this with no refinement value

	xis=[vec3(x,y,0) for x,y in elemtype.xis]
	diffvals=[(v-val) for v in nodevals]
	inters=list(isoIntersectElement(diffvals,[(0,1),(0,2),(1,3),(2,3)]))

	for i in range(0,len(inters),2): #TODO: fix
		a,b,lxi1=inters[i]
		c,d,lxi2=inters[i+1]
		yield xis[a].lerp(lxi1,xis[b]),xis[c].lerp(lxi2,xis[d])


def calculateElemIsoline(nodevals,elemtype,val,int refine=-1):
	'''Yields pairs of 2D xi values defining the isoline across the given triangle or quad for the given value.'''
	assert elemtype.geom in (GeomType._Tri,GeomType._Quad)

	if refine==-1:
		refine=0 if elemtype.order==0 else 3+elemtype.order

	if elemtype.geom==GeomType._Tri:
		isofunc=calculateTriIsoline
	elif elemtype.geom==GeomType._Quad:
		isofunc=calculateQuadIsoline

	for line in isofunc(nodevals,elemtype,val,refine):
		yield line


def reindexMesh(list inds,list components):
	'''
	Reindex the mesh defined by the indices `inds' and list of nodes, norms, xis etc. in `components'. The indices in
	`inds' will be reordered to start from 0 and any members of `components' not indexed will not be present in the
	resulting mesh. The return value is the pair (newinds,newcomps) where `newinds' is the new list of indices and
	`newcomps' the new list of component lists which is indexed by `newinds'.
	'''
	cdef list newcomps=[list() for c in components]
	cdef list newinds=[]
	cdef dict nodemap={}
	cdef list newind

	assert len(components)>0

	for ind in inds:
		newind=[]
		for i in ind:
			# if the index is new, store it in nodemap and copy over the i'th value from each component to newcomps
			if i not in nodemap:
				nodemap[i]=len(newcomps[0])
				for j in xrange(len(newcomps)):
					newcomps[j].append(components[j][i])

			newind.append(nodemap[i]) # replace old index with new index

		newinds.append(tuple(newind))

	return newinds,newcomps


def generateCylinder(ctrls,radii,refine=0,indexoffset=0,endCaps=True,alignRings=True):
	'''
	Generate a cylinder using the given control points in `ctrls' to define each cross section. At every location of
	`ctrls' a cross section ring is define for the cylinder with a radius defined in `radii', and which is rotated to
	orient correctly in the direction the line is going. These two first parameters must have the same length.The
	argument `refine' is used to state the radial refinement level, 0 producing a triangular cylinder. If `encCaps'
	is true, two triangle fans are included defining beginning and end caps over the cylinder. If `alignRings' is true,
	each ring of points is rotated in its plane to orient on a common direction, this eliminates twisting of the
	cylinder at inflection points of the line (or in other situations).
	'''
	assert refine>=0
	assert len(ctrls)>=2
	assert len(ctrls)==len(radii)
	refine+=3
	alignRings=alignRings and len(ctrls)>=3

	# calculate the directional vectors as the differences between control points
	dirs=[(ctrls[1]-ctrls[0]).norm()]
	for n in xrange(1,len(ctrls)-1):
		d1=ctrls[n]-ctrls[n-1]
		d2=ctrls[n+1]-ctrls[n]
		dirs.append(((d1+d2)/2).norm())

	dirs.append((ctrls[-1]-ctrls[-2]).norm())

	ring=[vec3(-i*(math.pi*2),math.pi/2,1.0).fromPolar() for i in frange(0.0,1.0,1.0/refine)] # define a circular ring of points on the XY plane

	if alignRings: # calculate the control point barycenter
		barycenter=avg(ctrls,vec3())

	def makeRing(ctrlvec,dirvec,radius):
		'''Define a ring of nodes centered at `ctrlvec' with radius `radius' lying on the plane whose normal is `dirvec'.'''
		rot=rotator(vec3(0,0,1),dirvec)

		# rotate the ring in its plane so that the locally rotated X axis is at right angles with a vector towards the barycenter from the ring center
		if alignRings: # and dirvec.angleTo(alignplanes[ctrlvec])>0:
			rv=rot*vec3(1,0,0) # rotate X axis
			line=dirvec.cross((barycenter-ctrlvec).norm())
			rot=rotator(rv,line)*rot # rotate the ring in its plane so that the rotated X axis is at right angles with the barycenter

		return [ctrlvec+(rot*r*radius) for r in ring]

	nodes=makeRing(ctrls[0],dirs[0],radii[0]) # first ring
	indices=[]

	if endCaps:
		# start cap composed of triangle fan, starting index is the center of the fan, next indices are consecutive points
		# on the ring. The expression (i+1)%refine is used to index the next point on the ring from point i since the indices
		# have to loop back around to the beginning. Note also that all triangles use counter-clockwise winding.
		indices+=[(0,i+1,(i+1)%refine+1) for i in xrange(refine)]
		nodes=[ctrls[0]]+makeRing(ctrls[0],dirs[0],radii[0])+nodes # duplicate first ring

	# cylinder midsections and final ring with triangle indices
	for n in xrange(1,len(ctrls)):
		for i in xrange(refine): # fill in indices
			b=len(nodes)+i
			d=len(nodes)+(i+1)%refine
			a=b-refine
			c=d-refine
			indices+=[(a,b,c),(c,b,d)]

		nodes+=makeRing(ctrls[n],dirs[n],radii[n]) # midsection ring of nodes

	if endCaps: # the ending cap is defined in the same way as the start cap, ie. extra node ring and triangle fan
		ln=len(nodes)
		indices+=[(ln+refine,ln+(i+1)%refine,ln+i) for i in xrange(refine)]
		nodes+=makeRing(ctrls[-1],dirs[-1],radii[-1])+[ctrls[-1]]

	return nodes,[(i+indexoffset,j+indexoffset,k+indexoffset) for i,j,k in indices] # return nodes and offset indices


def generateArrow(refine=1,indexoffset=0):
	'''Generates a +Z pointing arrow centered at the origin occupying a 2*2*2 box using generateCylinder.'''

	nodes,indices=generateCylinder([vec3(0,0,-1),vec3(),vec3(0,0,1)],[0.5,0.5,1],refine,indexoffset)
	for i in xrange((3+refine)*2):
		nodes[-2-i]*=vec3(1,1,0) # make the arrow point by moving the last 2 wide rings down to the X-Y plane

	return nodes,indices


def generateSphere(refine=0,indexoffset=0):
	'''
	Generates a unit sphere (actually a buckyball) centered at the origin through recursive icosahedron refinement.
	This will produce a mesh with 20*(4**refine) triangles, indexing starting from `indexoffset'. Return value is the
	(nodes,indices) pair.
	'''

	gold=(1.0+math.sqrt(5.0))/2.0 # golden ratio

	# define the points of an icosahedron
	nodes=[
		vec3(0, 1, gold), vec3(0, -1, gold), vec3(0, 1, -gold), vec3(0, -1, -gold), # YZ-plane
		vec3(1, gold, 0), vec3(-1, gold, 0), vec3(1, -gold, 0), vec3(-1, -gold, 0), # XY-plane
		vec3(gold, 0, 1), vec3(-gold, 0, 1), vec3(gold, 0, -1), vec3(-gold, 0, -1)  # XZ-plane
	]

	# define the triangle indices of the icosahedron
	indices=[
		(0, 1, 8), (0, 9, 1), (0, 8, 4), (0, 4, 5), (0, 5, 9),
		(2, 3, 11), (2, 11, 5), (2, 5, 4), (2, 4, 10), (2, 10, 3),
		(1, 9, 7), (1, 7, 6), (1, 6, 8), (3, 10, 6), (3, 6, 7),
		(3, 7, 11), (4, 8, 10), (5, 11, 9), (6, 10, 8), (7, 9, 11)
	]

	# rotate the icosahedron so that a node of the YZ plane is up; when refined this
	# creates a figure with an 'equator' on the XY plane
	rot=rotator(vec3(1,0,0),nodes[0].angleTo(vec3(0,0,1)))
	nodes=[rot*n for n in nodes]

	# refine the icosahedron by dividing each triangle into 4, triforce-style
	for r in xrange(refine):
		medians={}
		nextindex=len(nodes)
		newindices=[]

		for i,j,k in indices:
			# reserve an index in 'nodes' for the new node which is the median node between a and b
			for a,b in itertools.combinations([i,j,k],2):
				if (a,b) not in medians:
					medians[(a,b)]=nextindex
					medians[(b,a)]=nextindex
					nextindex+=1

			# add new indices for the 4 new triangles
			newindices+=[
				(i,medians[(i,j)],medians[(i,k)]),
				(medians[(i,j)],j,medians[(j,k)]),
				(medians[(i,k)],medians[(j,k)],k),
				(medians[(i,j)],medians[(j,k)],medians[(i,k)])
			]

		indices=newindices
		nodes+=[None]*(nextindex-len(nodes))

		# calculate each median node
		for (i,j),n in medians.items():
			if not nodes[n]:
				nodes[n]=(nodes[i]+nodes[j])*0.5

	# normalizing the nodes creates a sphere rather than just a complex icosahedron
	return [n.norm() for n in nodes],[(i+indexoffset,j+indexoffset,k+indexoffset) for i,j,k in indices]


def generateHemisphere(refine=0,indexoffset=0):
	'''Generate a hemisphere as the top half of the mesh from generateSphere(refine+1,indexoffset).'''
	nodes,inds=generateSphere(refine+1,indexoffset)
	inds=[(i,j,k) for i,j,k in inds if nodes[i].z()>=-1e-10 and nodes[j].z()>=-1e-10 and nodes[k].z()>=-1e-10]
	inds,comps=reindexMesh(inds,[nodes])
	return comps[0],inds


def generateQuadFromLine(vec3 pt1,vec3 pt2,vec3 planenorm,float width):
	'''
	Generate the four nodes for a quad `width' wide with centerline `pt1' to `pt2' and face normal `planenorm'. The quad
	is on the plane defined by the pair (pt1,planenorm). The triangle indices are [(0,2,1),(1,2,3)].
	'''
	oblique=planenorm.cross(pt2-pt1).norm()*(width*0.5)
	return pt1-oblique,pt1+oblique,pt2-oblique,pt2+oblique


def generatePlane(int refine,int indexoffset=0):
	'''
	Generates a plane of triangles on the XY plane centered at the origin with edges length 1. The argument 'refine'
	states how many divisions to used in defining the plane, a value of 0 yields a plane defined by 2 triangles. The
	triangle winding order indicates the triangles face in the Z+ direction.
	'''
	refine+=1
	nl=1.0/refine
	indices=[]
	r2=(refine-1)/2.0

	pointindices=list(trange(refine+1,refine+1))

	nodes=[vec3(nl*i-0.5,nl*(refine-j)-0.5,0) for j,i in pointindices]
	xis=[vec3(nl*i,nl*j,0) for j,i in pointindices]

	for j,i in trange(refine,refine):
		a=indexoffset+pointindices.index((j,i))
		b=indexoffset+pointindices.index((j,i+1))
		c=indexoffset+pointindices.index((j+1,i))
		d=indexoffset+pointindices.index((j+1,i+1))

		# mirror quadrants of the plane so that long edges of triangles point toward the center
		if (j<r2 and i<r2) or (j>=r2 and i>=r2):
			indices+=[ (a,c,b),(b,c,d) ]
		else:
			indices+=[ (b,a,d),(a,c,d) ]

	return nodes,indices,xis


def generateCube(int refine,int indexoffset=0):
	'''Generates a unit cube centered at the origin using 'generatePlane', returns nodes, norms, indices, and xis.'''

	nodes=[]
	norms=[]
	inds=[]
	xis=[]

	pnodes,pinds,pxis=generatePlane(refine,indexoffset)

	# define each face as a rotation of the original plane after being translated by (0,0,0.5)
	faces=[rotator(vec3(1,0,0),0),rotator(vec3(1,0,0),math.pi),rotator(vec3(1,0,0),halfpi),rotator(vec3(1,0,0),-halfpi),rotator(vec3(0,1,0),halfpi),rotator(vec3(0,1,0),-halfpi)]

	for rot in faces:
		inds+=[(i+len(nodes),j+len(nodes),k+len(nodes)) for i,j,k in pinds]
		nodes+=[rot*(p+vec3(0,0,0.5)) for p in pnodes]
		norms+=[rot*vec3(0,0,1) for p in pnodes]
		xis+=pxis # FIXME

	return nodes,norms,inds,xis


def generateCircle(numSpokes,radius=1.0,indexoffset=0):
	'''
	Defines a circle of points in counter-clockwise order centered at the origin with a radius of `radius', followed by the
	center vector (0,0,0). The value `numSpokes' is the number of points in the circle, a value of 3 will be used instead
	if `numSpokes' is less than this. The return value is the list of points and the list of indices defining a triangle
	list for the circle.
	'''
	numSpokes=max(3,numSpokes)

	nodes=[vec3(i*2*math.pi,halfpi,radius).fromPolar()*vec3(1,1) for i in frange(0,1,1.0/numSpokes)]
	inds=[(indexoffset+numSpokes,indexoffset+(i+1)%numSpokes,indexoffset+i) for i in xrange(numSpokes)]
	return nodes+[vec3()],inds


def generateLineBox(box,useBB=False):
	'''
	Generate a box with 8 vertices and edge indices. If `box' is a list of eight vec3 values and `useBB' is false, those
	are the vertices for the box. If the number of points is not eight or `useBB' is true, a bound box is calculated
	from the points whose corners are then used as the vertices. If `box' is a BoundBox object then its corners are
	used as vertices. Result is vertices-indices pair.
	'''
	indices=[(0,1),(1,3),(3,2),(2,0),(4,5),(5,7),(7,6),(6,4),(0,4),(1,5),(2,6),(3,7)]

	if isinstance(box,(list,tuple)) and all(isinstance(b,vec3) for b in box) and (useBB or len(box)!=8):
		box=BoundBox(box)

	if isinstance(box,BoundBox):
		corners=box.getCorners()
	else:
		corners=list(box)

	return corners,list(indices)


def generateTriBox(box,useBB=False):
	indices=[(1, 0, 3), (0, 2, 3), (0, 1, 4), (1, 5, 4), (3, 2, 7), (2, 6, 7),
		(4, 5, 6), (5, 7, 6), (1, 3, 5), (3, 7, 5), (2, 0, 6), (0, 4, 6)]

	if isinstance(box,(list,tuple)) and all(isinstance(b,vec3) for b in box) and (useBB or len(box)!=8):
		box=BoundBox(box)

	if isinstance(box,BoundBox):
		corners=box.getCorners()
		center=box.center
	else:
		corners=list(box)
		center=avg(*corners)

	return corners,[(n-center).norm() for n in corners],list(indices)


def generateHexBox(dimx,dimy,dimz):
	dimx+=1
	dimy+=1
	dimz+=1
	dx=1.0/dimx
	dy=1.0/dimy
	dz=1.0/dimz

	nodes=[vec3(x,y,z) for z,y,x in trange((0.0,1.0+dz,dz),(0.0,1.0+dy,dy),(0.0,1.0+dx,dx))]

	dimx+=1
	dimy+=1
	dimz+=1
	dimxy=dimx*dimy
	ind=lambda i,j,k:i+j*dimx+k*dimxy

	hexes=[(ind(i,j,k),ind(i+1,j,k),ind(i,j+1,k),ind(i+1,j+1,k),ind(i,j,k+1),ind(i+1,j,k+1),ind(i,j+1,k+1),ind(i+1,j+1,k+1)) for k,j,i in trange(dimz-1,dimy-1,dimx-1)]

	return nodes,hexes


def generateTriNormals(list nodes,list indices,int indOffset=0):
	cdef list norms=[vec3() for i in nodes]

	for i,(a,b,c) in enumerate(indices):
		norm=nodes[a-indOffset].planeNorm(nodes[b-indOffset],nodes[c-indOffset])
		norms[a-indOffset]+=norm
		norms[b-indOffset]+=norm
		norms[c-indOffset]+=norm

	return [n.norm() for n in norms]


def linTriInterp(float x, float y, a,b,c):
	'''Linearly interpolate the triangle defined by (a,b,c) at xi coordinate (x,y).'''
	return (a*(1.0-x-y))+(b*x)+(c*y)


def calculateFaceNormal(list nodes,elemtype,int face):
	cdef listfindices=elemtype.faces[face]
	cdef vec3 far=nodes[findices[-1]]
	cdef vec3 n0=nodes[findices[0]]
	cdef vec3 n1=nodes[findices[1]]
	cdef vec3 n2=nodes[findices[2]]
	cdef vec3 norm=n0.planeNorm(n1,n2,far)

	if elemtype.numFaceVertices(face)>3:
		n0=nodes[findices[3]]
		norm=(norm+n0.planeNorm(n1,n2,far)).norm()

	return norm


def calculateFaceArea(list nodes,elemtype,int refine=0):
	cdef str geom=elemtype.geom
	cdef int order=elemtype.order
	cdef list tris=[]
	cdef list divtris
	refine+=order+1

	assert geom in (GeomType._Tri,GeomType._Quad)

	if order==1:
		tris=[nodes] if geom == GeomType._Tri else [nodes[:3],nodes[1:]]
	else:
		if geom == GeomType._Tri:
			divtris=divideTritoTris(refine)
		else:
			divtris=divideQuadtoTris(refine)

		for tri in divtris:
			tris.append([elemtype.applyBasis(nodes,x,y,0) for x,y in tri])

	return sum(a.triArea(b,c) for a,b,c in tris)


def chooseShiftFaceXi(float xi0,float xi1,float shift):
	'''Returns 2 points 'shift' away from (xi0,xi1), at right angles, in clockwise order, and on the unit square.'''
	cdef float nxi0=xi0+shift
	cdef float nxi1=xi1+shift

	if nxi0>1.0 and nxi1>1.0:
		return (xi0-shift,xi1),(xi0,xi1-shift)
	elif nxi0>1.0:
		return (xi0,nxi1),(xi0-shift,xi1)
	elif nxi1>1.0:
		return (xi0,xi1-shift),(nxi0,xi1)
	else:
		return (nxi0,xi1),(xi0,nxi1)


def calculatePointNormalCoeffs(elemtype,int face,float xi0,float xi1):
	'''
	Calculate two face xi cooefficient tuples for a xi point near (xi0,xi1) and at right angles to it, the cross
	product of the node at (xi0,xi1) and the nodes at the two new locations will yield the surface normal at (xi0,xi1).
	'''
	cdef tuple sxi1,sxi2,c1,c2
	sxi1,sxi2=chooseShiftFaceXi(xi0,xi1,0.0001)

	exi1=elemtype.faceXiToElemXi(face,*sxi1)
	exi2=elemtype.faceXiToElemXi(face,*sxi2)

	c1=elemtype.basis(*exi1)
	c2=elemtype.basis(*exi2)

	return c1,c2


def calculatePointNormalSurf(nodes,elemtype,n0,c1,c2,face,useFarVert=True):
	n1=elemtype.applyCoeffs(nodes,c1)
	n2=elemtype.applyCoeffs(nodes,c2)

	norm=n0.planeNorm(n1,n2)

	if not useFarVert or elemtype.dim<3:
		return norm
	else:
		farvert=nodes[elemtype.getFaceFarIndex(face)]
		return norm if norm.angleTo(farvert-n0)>=(math.pi*0.5) else -norm


def calculatePointNormal(nodes,elemtype,face,n0,xi0,xi1,useFarVert=True):
	'''
	Given an element of type `elemtype' with nodes `nodes', calculate the normal for the point `n0' on face `face'
	having face xi values (xi0,xi1). If `useFarVert' is true, then use the vertex "farthest" from the face to decide
	whether the element is inverted and the returned normal should also be inverted.
	'''
	c1,c2=calculatePointNormalCoeffs(elemtype,face,xi0,xi1)
	return calculatePointNormalSurf(nodes,elemtype,n0,c1,c2,face,useFarVert)


def equalPlanes(vec3 pt1,vec3 n1,vec3 pt2,vec3 n2):
	'''Returns True if the planes (pt1,n2) and (pt2,n2) are equivalent (although possibly facing opposite one another).'''
	return pt1.onPlane(pt2,n2) and not (epsilon<n1.angleTo(n2)<(math.pi-epsilon))


def isOutwardFace(elemtype,face,elemnodes):
	'''Returns true if the selected face is outward facing, false if it is inside-out (inward facing).'''

	if elemtype.dim<3:
		return True

	fxi0,fxi1=0.2,0.2
	exi0=elemtype.faceXiToElemXi(face,fxi0,fxi1) # TODO: where the sample is taken is important, find a better way
	n0=elemtype.applyBasis(elemnodes,*exi0)

	mnorm=calculatePointNormal(elemnodes,elemtype,face,n0,fxi0,fxi1,False)

	internalsub=elemtype.getInternalFaceXiSub(face)
	mxi=[(i-j) for i,j in zip(exi0,internalsub)]
	inorm=(n0-elemtype.applyBasis(elemnodes,*mxi)).norm()

	return mnorm.angleTo(inorm)<=halfpi


def isSpatialIndex(IndexMatrix ind,dim=None):
	'''
	Returns true if IndexMatrix `ind' defines a spatial topology, ie. represents geometry rather than a field or metadata.
	A matrix is a spatial topology if its type is a member of ElemType an its isspatial metadata tag is "True". If `dim'
	is not None it must be an integer, in which case the return value is True if additionally the spatial dimensions of
	the element type are greater or equal to this value.
	'''
	cdef str itype=ind.getType()
	return itype in ElemType and ind.meta(StdProps._isspatial)=='True' and (dim==None or ElemType[ind.getType()].dim>=dim)


def isPerNodeField(RealMatrix field,int numnodes):
	'''
	Returns True if `field' is a per-node field for a dataset with `numnodes' number of nodes. This checks the nodedata
	metadata value to check it says True, or if the length of `field' equals `numnodes' and that it designates no matrices
	in the spatial or topology metadata fields. If nodedata is True but the length of `field' is not `numnodes', ValueError
	is raised to indicate a mismatch of expectations.
	'''
	topo=field.meta(StdProps._spatial) or field.meta(StdProps._topology)
	isPerNode=bool(field.meta(StdProps._nodedata)) or (field.n()==numnodes and not topo)

	if isPerNode and field.n()!=numnodes:
		raise ValueError,'Field %r is designated to be per node for a node set of length %i, but has length %i'%(field.getName(),numnodes,field.n())

	return isPerNode


def findIndexSets(dataset,acceptFunc=isSpatialIndex):
	for i in dataset.getIndexNames():
		indmat=dataset.getIndexSet(i)
		if acceptFunc(indmat):
			ext=dataset.getIndexSet(i+MatrixType.external[1])
			adj=dataset.getIndexSet(i+MatrixType.adj[1])
			yield (indmat,ext,adj)


def fillCircleFigure(fig,radius,col,spokes=12):
	nodes,inds=generateCircle(spokes,radius)
	n=len(nodes)
	vbuf=PyVertexBuffer(nodes,[vec3(0,0,1)]*n,[col]*n)
	ibuf=PyIndexBuffer(inds+[(i,k,j) for i,j,k in inds])
	fig.fillData(vbuf,ibuf)


def fillPolyFigure(fig,nodes,col,isClosed=True):
	n=len(nodes)
	vbuf=PyVertexBuffer(nodes,[vec3(0,0,1)]*n,[col]*n)
	ibuf=PyIndexBuffer(list(successive(xrange(n),2,isClosed)))
	fig.fillData(vbuf,ibuf)


def fillSphereFigure(fig,radius,refine,col):
	nodes,inds=generateSphere(refine)
	norms=generateTriNormals(nodes,inds)
	n=len(nodes)
	vbuf=PyVertexBuffer([nn*radius for nn in nodes],norms,[col]*n)
	ibuf=PyIndexBuffer(inds+[(i,k,j) for i,j,k in inds])
	fig.fillData(vbuf,ibuf)


@memoized(tuple)
def divideTritoPoints(n):
	'''For refinement integer value `n'>=0, yield the face xi coordinates of evenly-spaced points on a triangle.'''
	n1=1.0/(n+1)

	for y in frange(0,1+n1,n1):
		for x in frange(0,1.0-y+n1,n1):
			yield (x,y)

@memoized(tuple)
def divideQuadtoPoints(n):
	'''For refinement integer value `n'>=0, yield the face xi coordinates of evenly-spaced points on a quad.'''
	n1=1.0/(n+1)

	for y,x in itertools.product(frange(0,1+n1,n1),repeat=2):
		yield (x,y)


@memoized(tuple)
def divideElemtoPoints(n,isSimplex):
	n1=1.0/(n+1)
	for z,y,x in itertools.product(frange(0,1+n1,n1),repeat=3):
		if not isSimplex or (x+y+z)<=1.0:
			yield x,y,z


@memoized(tuple)
def divideTritoLines(n):
	'''For refinement integer value `n'>=0, yield the face xi coordinates of lines on the edges of a triangle.'''
	n1=1.0/(n+1)
	yield tuple((y,0) for y in frange(0,1.0+n1,n1))
	yield tuple((0,y) for y in frange(0,1.0+n1,n1))
	yield tuple((1.0-y,y) for y in frange(0,1.0+n1,n1))


@memoized(tuple)
def divideQuadtoLines(n):
	'''For refinement integer value `n'>=0, yield the face xi coordinates of lines on the edges of a quad.'''
	n1=1.0/(n+1)
	yield tuple((y,0) for y in frange(0,1.0+n1,n1))
	yield tuple((0,y) for y in frange(0,1.0+n1,n1))
	yield tuple((1.0,y) for y in frange(0,1.0+n1,n1))
	yield tuple((y,1.0) for y in frange(0,1.0+n1,n1))


@memoized(tuple)
def divideTritoTris(n):
	'''For refinement integer value `n'>=0, yield the face xi coordinate triples of triangles dividing a triangle.'''
	n1=1.0/(n+1)

	for y in frange(0,1,n1):
		for x in frange(0,1-y-n1,n1):
			yield (x,y), (x+n1,y), (x,y+n1)
			yield (x,y+n1), (x+n1,y), (x+n1,y+n1)

		yield (1-y-n1,y), (1-y,y),(1-y-n1,y+n1)


@memoized(tuple)
def divideTritoTriMesh(int n):
	'''Returns 2D xis list and triangle index list for dividing a triangle into a triangle mesh with refinement `n'.'''
	cdef list xis=[],inds=[]
	cdef int i,j,start,nextr
	cdef float n1=1.0/(n+1)
	cdef float x,y

	for y in frange(0,1+n1,n1):
		for x in frange(0,1-y+n1,n1):
			xis.append((x,y))

#	for j in range(n):
#		for i in range(n-j):
#			start=j*(n+2)+i
#			nextr=(j+1)*(n+2)-j+i
#			inds+=[(start,start+1,nextr),(nextr,start+1,nextr+1)]
#
#		start=j*(n+2)+n-j
#		nextr=(j+1)*(n+2)-j+n-j
#		inds.append((start,start+1,nextr))
#
#	inds.append((len(xis)-3,len(xis)-2,len(xis)-1))

	nextr=0
	start=0
	for j in range(n+1):
		nextr+=n+2-j
		for i in range(n-j):
			inds+=[(start,start+1,nextr+i),(nextr+i,start+1,nextr+1+i)]
			start+=1

		inds+=[(start,start+1,nextr+n-j)]
		start=nextr

	return xis,inds


@memoized(tuple)
def divideQuadtoTriMesh(int n):
	'''Returns 2D xis list and triangle index list for dividing a quad into a triangle mesh with refinement `n'.'''
	cdef list xis=[],inds=[]
	cdef int i,j,start,nextr
	cdef float n1=1.0/(n+1)
	cdef float x,y

	for y in frange(0,1+n1,n1):
		for x in frange(0,1+n1,n1):
			xis.append((x,y))

	for j in range(n+1):
		for i in range(n+1):
			start=j*(n+2)+i
			nextr=(j+1)*(n+2)+i
			inds+=[(start,start+1,nextr),(nextr,start+1,nextr+1)]

	return xis,inds

@memoized(tuple)
def divideQuadtoTris(n):
	'''For refinement integer value `n'>=0, yield the face xi coordinate triples of triangles dividing a quad.'''
	n1=1.0/(n+1)

	for y,x in trange((0,1.0,n1),(0,1.0,n1)):
		if (y<0.5 and x>=0.5) or (y>=0.5 and x<0.5):
			yield (x,y), (x,y+n1),  (x+n1,y)
			yield (x,y+n1),(x+n1,y+n1),(x+n1,y)
		else:
			yield (x,y+n1), (x+n1,y+n1),  (x,y)
			yield (x,y),(x+n1,y+n1),(x+n1,y)


@memoized(tuple)
def divideQuadtoQuads(n):
	n1=1.0/(n+1)

	for y,x in trange((0.0,1.0,n1),(0.0,1.0,n1)):
		yield (x,y),(x+n1,y),(x,y+n1),(x+n1,y+n1)


@memoized(tuple)
def divideHextoHex(order,refine,expand=0.0):
	'''
	Divides the reference linear hex into `refine'**3 linear hexes. It yields each hex as a 8-tuple of xi points. The
	`expand' value is used to expand the size of each hex by the given multiple of the dimension, this overlapping is
	useful for point searching.
	'''
	div=1.0/(refine+1)
	exp1=div*(1.0+expand)
	exp2=0#div*-expand
	linhex=ElemType.Hex1NL
	orderhex=ElemType[ElemType.getTypeName(GeomType._Hex,'NL',order)]

	for x,y,z in trange((0,1.0,div),(0,1.0,div),(0,1.0,div)):
		hexxis=(
			(x+exp2,y+exp2,z+exp2),(x+exp1,y+exp2,z+exp2),(x+exp2,y+exp1,z+exp2),(x+exp1,y+exp1,z+exp2),
			(x+exp2,y+exp2,z+exp1),(x+exp1,y+exp2,z+exp1),(x+exp2,y+exp1,z+exp1),(x+exp1,y+exp1,z+exp1)
		)

		yield tuple(linhex.applyBasis(hexxis,*xi) for xi in orderhex.xis)
		

@memoized(tuple)
def divideHextoTet(order,refine=0, use5Tets=False):
	'''
	Divides reference linear hex into 6 (or 5 if use5Tets is true) tets of the given order when `refine'==0. For each
	of the tets, this yields a set of xi points in the hex element for each tet control point. The vertices of the
	tets are defined by the vertices of the hex element, thus the result for `order'==1 is 6 4-tuples of Hex1NL node xis.
	When `refine'>0, the hex is instead divided into 5 or 6 linear tets which are in turn divided themselves. The
	function then yields these subtets of the given order which are defined at tuples of xi points in the hex.
	'''
	if refine>0:
		for sb in divideHextoTet(1,0,use5Tets):
			for tet in divideTettoTet(order,refine):
				yield tuple(ElemType.Tet1NL.applyBasis(sb,*xi) for xi in tet)
	else:
		linearinds=hexTo5TetInds if use5Tets else hexTo6TetInds
		lintet=ElemType.Tet1NL
		linhex=ElemType.Hex1NL
		ordertet=ElemType[ElemType.getTypeName(GeomType._Tet,'NL',order)]

		# for each tet, determine the xi values for each control point by interpolating within a Tet1NL element with the Hex1NL xis as node values
		for tet in linearinds:
			hexxis=[linhex.xis[t] for t in tet]
			yield tuple(lintet.applyBasis(hexxis,*xi) for xi in ordertet.xis)


@memoized(tuple)
def divideTettoTet(order,refine,expand=0.0):
	'''Divides the reference linear tet evenly and yields smaller tets of the given order. The `refine' parameter determines how many.'''
	hextetxis=tuple(divideHextoTet(order))
	div=1.0/(refine+1)

	# divide xi-space into hexes, divide each of these into tets, and yield only the tets within the simplex xi-space (ie. sum(xi)<=1.0)
	for elem in divideHextoHex(1,refine):
		if all(sum(e)>=1.0 for e in elem): # skip hexes outside the simplex xi-space
			continue

		x,y,z=elem[0]
		for tet in hextetxis:
			tet=[(t0*div+x,t1*div+y,t2*div+z) for t0,t1,t2 in tet] # scale and move the tet into the current hex
			if all(isInEpsilonRange(sum(t),0.0,1.0) for t in tet): # yield the tet if it is in the simplex xi-space
				yield tet


def calculateLineXis(elemtype,refine,*args,**kwargs):
	xis=list(frange(0,1.0,1.0/(refine+1)))+[1.0]
	coeffs=[elemtype.basis(x,0.0,0.0,*args,**kwargs) for x in xis]
	return zip(xis,coeffs)


def calculateTriXis(elemtype,refine,divideFunc,*args,**kwargs):
	xis=divideFunc(refine)
	results=[]
	for a,b,c in xis:
		c1=elemtype.basis(a[0],a[1],0,*args,**kwargs)
		c2=elemtype.basis(b[0],b[1],0,*args,**kwargs)
		c3=elemtype.basis(c[0],c[1],0,*args,**kwargs)
		results.append((a,b,c,c1,c2,c3))

	return results


def calculateFaceXis(elemtype,refine,triRefineFunc,quadRefineFunc,*basisargs,**basiskwargs):
	'''
	Generates sets of face-xi/elem-xi/coefficient value sets for each face of an element. The return value is a list of
	lists, one list per face. For each face, either `triRefineFunc' or `quadRefineFunc' is called which must return a
	list of face xi coords (for individual points on the face) or a list of tuples of face xi coords (each member of the
	tuples being a vertex on a figure on the face such as a triangle).

	For each face, a list is constructed of the following elements, one for each value 'v' returned by the refine functions:
		* If 'v' single face xi coord (2-tuple of floats), a tuple is produced containing the face xi, the
		corresponding element xi, and the corresponding node coefficients.
		* If 'v' is a tuple of face xi coords, a tuple is produced containing the face xis of each
		xi value, followed by the element xis of each, and then the corresponding coefficients of each.

	The argument 'refine' determines the refinement level of the faces. 0 means no refinement, so 1 triangle will be
	defined for one triangular face. 1 means the first refinement level, so 4 triangles will be defined for one
	triangular face.

	For example, the arguments (ElemType.Tet1NL,0,divideTritoTris,None) produce a list of 4 lists, one per face, where
	each list contains 1 tuple defining one triangle representing the whole face. This one tuple contains 3 2D face xi
	values (one per triangle node), 3 3D element xi values, and 3 coefficient tuples with a coefficient for
	each node of the tet:

	[
		[(
			(0.0, 0.0), (0.0, 1.0), (1.0, 0.0),
			(0.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, 1.0, 0.0),
			(1.0, 0.0, 0.0, 0.0), (0.0, 1.0, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0)
		)],
		[...],
		[...],
		[...]
	]
	'''
	cdef list xis,result=[]
	cdef int face
	cdef tuple exi,c

	# for each face compute the face xi, element xi, and coefficients for each refined point or tuple of points
	for face in xrange(elemtype.numFaces()):
		# get the xis for the points or tuple of points of the refined face
		if elemtype.numFaceVertices(face)==3:
			refinexis=triRefineFunc(refine)
		else:
			refinexis=quadRefineFunc(refine)

		xis=[]
		for xi in refinexis:
			# for each face xi convert the value to element xi and compute the coefficients
			if not isinstance(xi[0],tuple): # xi is not a tuple of values (ie. a single face coord), make it a tuple of xis
				xi=(xi,)

			# xi is a tuple of xi values (eg. 3 for a triangle), compute the elem xi and coeffs for each
			exi=tuple(elemtype.faceXiToElemXi(face,*x) for x in xi)
			c=tuple(elemtype.basis(*(x+basisargs),**basiskwargs) for x in exi)
			xis.append(xi+exi+c) # tuple containing face xis, elem xis, coefficients

		result.append(xis)

	return result


#calculateFaceMeshes(ElemType.Tet1NL,0,divideTritoTriMesh,divideQuadtoTriMesh)
def calculateFaceMeshes(elemtype,refine,triRefineFunc,quadRefineFunc,*basisargs,**basiskwargs):
	cdef list results=[],fxis,inds
	cdef tuple exi, c0,c1,c2
	cdef int face,numfaces=elemtype.numFaces()
	cdef IndexMatrix indsmat
	cdef RealMatrix coeffs

	for face in range(numfaces):
		if elemtype.numFaceVertices(face)==3:
			fxis,inds=triRefineFunc(refine)
		else:
			fxis,inds=quadRefineFunc(refine)

		coeffs=RealMatrix('coeffs%i'%face,0,3+3*len(elemtype.xis))
		indsmat=listToMatrix(inds,'faceinds%i'%face) if inds else None
		results.append((coeffs,indsmat))

		for x,y in fxis:
			exi=elemtype.faceXiToElemXi(face,x,y)
			c0=elemtype.basis(*(exi+basisargs),**basiskwargs)
			c1,c2=calculatePointNormalCoeffs(elemtype,face,x,y)
			coeffs.append(*(exi+c0+c1+c2))

	return results


def calculateFaceMults(elemtype):
	'''
	Calculate the normal multiplier for each face. This assumes that the vertices of a face can be considered to be
	equivalent to the vertices of the linear element. The resulting list has an entry for each face which is 1 or -1
	depending on if the normal calculated through cross produce should be inverted or not. Essentially this determines
	if a face's vertices wind clockwise or counterclockwise. This relies on CHeart node ordering.
	'''
	mults=[]

	for n in range(elemtype.numFaces()):
		far=vec3(*elemtype.xis[elemtype.getFaceFarIndex(n)])

		v0=vec3(*elemtype.applyBasis(elemtype.xis,*elemtype.faceXiToElemXi(n,0.0,0.0)))
		v1=vec3(*elemtype.applyBasis(elemtype.xis,*elemtype.faceXiToElemXi(n,1.0,0.0)))
		v2=vec3(*elemtype.applyBasis(elemtype.xis,*elemtype.faceXiToElemXi(n,0.0,1.0)))

		norm=v0.planeNorm(v1,v2)
		mults.append(-1 if norm.angleTo(far-v0)<=halfpi else 1)

	return mults


def isValidXi(xis,isSimplex):
	'''Returns true if `xis' is in the unit cube and its components sum to no more than 1.0 if `isSimplex' is true.'''
	return all(isInEpsilonRange(x,0.0,1.0) for x in xis) and (not isSimplex or isInEpsilonRange(sum(xis),0.0,1.0))


@memoized(tuple)
def divideElemOrdered(refine, nearestxi, isSimplex):
	'''
	Produces a tet division list if `isSimplex' is true, or an hex division list otherwise. This list of embedded elements
	is sorted based on distance from the given xi value `nearestxi'.
	'''
	expand=0.05
	divs=divideTettoTet(1,refine,expand) if isSimplex else divideHextoHex(1,refine,expand) # create the dividing subelements
	nearpt=vec3(*nearestxi)
	dists=[nearpt.distToSq(avg((vec3(*v) for v in elem),vec3())) for elem in divs] # calculate the square distances from nearestxi to each subelement's centroid
	inds=sorted(range(len(dists)),key=lambda i:dists[i]) # sort an index list based on the distances
	return [divs[i] for i in inds] # use the sorted index list to produce a sorted list of subelements


def pointSearchElem(elemtype,elemnodes,pt,refine):
	'''
	Performs a point search within an element of type `elemtype' with control points `elemnodes'. It attempts to find
	the xi value corresponding to point `pt' within the element. A vec3 object is returned if found, None otherwise.
	The `refine' value is used to state how much to divide the element into sub-elements to search with.

	This routine works by dividing the element into embedded linear sub-elements and solving point search analytically
	for those. This requires a lot of searching if `refine' is high. For linear tets this routine will return a very
	accurate result if found, for linear hexes the return value will be equally exact if the faces are coplanar (since
	it relies on dividing the hex into linear tets). For higher order elements a high `refine' value ensures that
	curvy areas that will be outside linear elements is kept small, but interpolating within embedded linear elements
	will always be innaccurate to varying degrees.

	This algorithm assumes that the linear version of `elemtype' is equivalent to linear nodal lagrange since this is
	the basis function used in the underlying C++ code. When dividing higher order elements into linear elements, the
	basis function defined in `elemtype' is used to compute the vertices of the linear elements, thus if `elemtype'
	varies considerably from nodal langrange the linear elements will be poor approximations with their spaces. To
	get a better result in this case a high `refine' value is needed to use smaller linear elements which will then be
	better approximations.
	'''
	isSimplex=GeomType[elemtype.geom][2]
	pointSearchFunc=pointSearchLinTet if isSimplex else pointSearchLinHex
	divet=ElemType.Tet1NL if isSimplex else ElemType.Hex1NL

	if elemtype.order==1:
		return pointSearchFunc(pt,*elemnodes);

	if pt not in BoundBox(elemnodes):
		return None

	nearest=min(range(len(elemnodes)),key =lambda i:elemnodes[i].distToSq(pt)) # find the nearest control point to `pt'

	divs=divideElemOrdered(refine,tuple(elemtype.xis[nearest]),isSimplex) # divide the element, sorting sub-elements by distance from `nearest'

	# search through each sub-element of the original element
	for div in divs:
		divnodes=[elemtype.applyBasis(elemnodes,*node) for node in div] # calculate the world-space positions of the element's vertices

		xi=pointSearchFunc(pt,*divnodes) # attempt to find the position of `pt' in this element

		# if `pt' is in the element, apply the basis function to the embedded xi values of `div' to get the original element's xi value
		if isValidXi(xi,isSimplex):
			return vec3(*divet.applyBasis(div,*xi))

	return None


def collectFieldTopos(dataset,fields,indlist=[]):
	'''
	For each field matrix in in `fields'
	Collect with the topologies into a list of (field,topo) tuples. Matrices are made shared if `makeShared'.
	'''
	indlist=indlist or list(dataset.enumIndexSets())

	fieldtopolist=[]

	if len(fields)==1 and bool(fields[0].meta(StdProps._nodedata)):
		fieldtopolist=[(fields[0],ind) for ind in indlist]
	else:
		for field in fields:
			fname=field.getName()
			sname=field.meta(StdProps._spatial)
			tname=field.meta(StdProps._topology)

			fspatial=dataset.getIndexSet(sname)
			ftopo=dataset.getIndexSet(tname)

			if fspatial and fspatial not in indlist:
				raise ValueError,'Spatial topology %r is associated with field %r but not in use'%(sname,fname)

#			if ftopo and ftopo not in indlist:
#				raise ValueError,'Field topology %r is associated with field %r but not in use'%(tname,fname)

			if bool(field.meta(StdProps._nodedata)):
				raise ValueError,'Field %r is a per-node field and so has no topology'%fname

			if fspatial==None:
				raise ValueError, 'No spatial topology found for %r, name is given as %r'%(fname,sname)

			if ftopo==None and field.meta(StdProps._topology):
				raise ValueError, 'No field topology found for %r, name is given as %r'%(fname,tname)

	#		if field.n()!=fspatial.n() or field.m()!=fspatial.m():
	#			raise ValueError,'Field %r has dims (%i,%i), but associated spatial topology %r has dims (%i,%i)'%(fname,field.n(),field.m(),sname,fspatial.n(),fspatial.m())
	#
	#		if field.n()!=ftopo.n() or field.m()!=ftopo.m():
	#			raise ValueError,'Field %r has dims (%i,%i), but associated field topology %r has dims (%i,%i)'%(fname,field.n(),field.m(),fname,ftopo.n(),ftopo.m())

			ftopo=ftopo or fspatial # if no topology given but also no topology name given, use the spatial topology instead

			fieldtopolist.append((field,ftopo))

	return fieldtopolist

