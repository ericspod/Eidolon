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


import cython
from cpython cimport Py_buffer
from cython.operator cimport dereference as deref

# import array library and Cython declarations
import array
from cpython cimport array

# import the regular Numpy library and Cython declarations
import numpy as np
cimport numpy as np

from libc.string cimport memcpy

# C++ type declarations
from libcpp.vector cimport vector
from libcpp.pair cimport pair

# import RenderTypes declarations, aliasing class types by prepending i to the names
cimport RenderTypes
from RenderTypes cimport FigureType,BlendMode,TextureFormat,ProgramType,VAlignType, HAlignType
from RenderTypes cimport real,rgba,sval,indexval,i32, u64, realpair, realtriple,indexpair,indextriple,intersect
from RenderTypes cimport vec3 as ivec3, color as icolor, rotator as irotator, transform as itransform, Ray as iRay
from RenderTypes cimport Matrix as iMatrix, Vec3Matrix as iVec3Matrix, RealMatrix as iRealMatrix,IndexMatrix as iIndexMatrix, ColorMatrix as iColorMatrix
from RenderTypes cimport Config as iConfig
from RenderTypes cimport VertexBuffer as iVertexBuffer, IndexBuffer as iIndexBuffer, MatrixVertexBuffer as iMatrixVertexBuffer,MatrixIndexBuffer as iMatrixIndexBuffer
from RenderTypes cimport CallbackVertexBuffer as iCallbackVertexBuffer, CallbackIndexBuffer as iCallbackIndexBuffer
from RenderTypes cimport Vec3Curve as iVec3Curve, Spectrum as iSpectrum, Material as iMaterial, GPUProgram as iGPUProgram
from RenderTypes cimport Light as iLight, Camera as iCamera, Texture as iTexture, Image as iImage
from RenderTypes cimport Figure as iFigure, BBSetFigure as iBBSetFigure, TextureVolumeFigure as iTextureVolumeFigure, GlyphFigure as iGlyphFigure,RibbonFigure as iRibbonFigure, TextFigure as iTextFigure
from RenderTypes cimport RenderScene as iRenderScene, RenderAdapter as iRenderAdapter


platformID       = RenderTypes.platformID
RenderParamGroup = RenderTypes.RenderParamGroup

FT_LINELIST      = RenderTypes.FT_LINELIST
FT_POINTLIST     = RenderTypes.FT_POINTLIST
FT_TRILIST       = RenderTypes.FT_TRILIST
FT_TRISTRIP      = RenderTypes.FT_TRISTRIP
FT_BB_POINT      = RenderTypes.FT_BB_POINT
FT_BB_FIXED_PAR  = RenderTypes.FT_BB_FIXED_PAR
FT_BB_FIXED_PERP = RenderTypes.FT_BB_FIXED_PERP
FT_GLYPH         = RenderTypes.FT_GLYPH
FT_RIBBON        = RenderTypes.FT_RIBBON
FT_TEXVOLUME     = RenderTypes.FT_TEXVOLUME
FT_TEXT          = RenderTypes.FT_TEXT

BM_ALPHA   = RenderTypes.BM_ALPHA
BM_COLOR   = RenderTypes.BM_COLOR
BM_ADD     = RenderTypes.BM_ADD
BM_MOD     = RenderTypes.BM_MOD
BM_REPLACE = RenderTypes.BM_REPLACE

TF_UNKNOWN   = RenderTypes.TF_UNKNOWN
TF_RGB24     = RenderTypes.TF_RGB24
TF_RGBA32    = RenderTypes.TF_RGBA32
TF_ARGB32    = RenderTypes.TF_ARGB32
TF_LUM8      = RenderTypes.TF_LUM8
TF_LUM16     = RenderTypes.TF_LUM16
TF_ALPHA8    = RenderTypes.TF_ALPHA8
TF_ALPHALUM8 = RenderTypes.TF_ALPHALUM8

PT_VERTEX   = RenderTypes.PT_VERTEX
PT_FRAGMENT = RenderTypes.PT_FRAGMENT
PT_GEOMETRY = RenderTypes.PT_GEOMETRY

H_LEFT      = RenderTypes.H_LEFT
H_RIGHT     = RenderTypes.H_RIGHT
H_CENTER    = RenderTypes.H_CENTER
V_TOP       = RenderTypes.V_TOP
V_BOTTOM    = RenderTypes.V_BOTTOM
V_CENTER    = RenderTypes.V_CENTER


def equalsEpsilon(real v1, real v2):
	return RenderTypes.equalsEpsilon(v1,v2)

def initSharedDir(path):
	RenderTypes.initSharedDir(path)

def getSharedDir():
	return RenderTypes.getSharedDir()

def unlinkShared(name):
	RenderTypes.unlinkShared(name)


cdef class color:
	cdef icolor val

	def __init__(self,real r=1.0,real g=1.0,real b=1.0,real a=1.0):
		if isinstance(r,color):
			self.val=icolor((<color>r).val)
#		elif isinstance(r,(int,long)):
#			self.val=icolor(<rgba>r)
		else:
			self.val=icolor(float(r),g,b,a)

	@staticmethod
	def fromRGBA(rgba val):
		return color._new(icolor(val))

	@staticmethod
	cdef color _new(icolor val):
		cdef color r=color()
		r.val=val
		return r

	@staticmethod
	cdef icolor _get(color v): # needed for matrix templating
		return v.val

	def __repr__(self):
		return 'color({:.15},{:.15},{:.15},{:.15})'.format(self.val.r(),self.val.g(),self.val.b(),self.val.a())

	def __iter__(self):
		return iter([self.val.r(),self.val.g(),self.val.b(),self.val.a()])

	def __reduce__(self):
		return color,(self.val.r(),self.val.g(),self.val.b(),self.val.a())

	def __copy__(self):
		return color._new(self.val)

	def r(self):
		return self.val.r()

	def g(self):
		return self.val.g()

	def b(self):
		return self.val.b()

	def a(self):
		return self.val.a()

	def __richcmp__(color self,v,int op):
		cdef icolor vv

		if v is None:
			return op==3

		if v is self:
			return op in (1,2,5)

		if isinstance(v,color):
			vv=(<color>v).val
			if op==0: #<
				return self.val<vv
			elif op==1: #<=
				return self.val<vv or self.val==vv
			elif op==2: #==
				return self.val==vv
			elif op==3: #!=
				return self.val!=vv
			elif op==4: #>
				return self.val>vv
			elif op==5: #>=
				return self.val>vv or self.val==vv

		if op==2: # objects are not equal to objects of other types
			return False

		if op==3: # objects are unequal to objects of other types
			return True

		raise ValueError,'Cannot compare color to %r'%type(v)

	def interpolate(self,real val, color col):
		return color._new(self.val.interpolate(val,col.val))

	def __add__(color self,v):
		return color._new(self.val+(<color>v).val if isinstance(v,color) else self.val+<real>v)

	def __sub__(color self,v):
		return color._new(self.val-(<color>v).val if isinstance(v,color) else self.val-<real>v)

	def __mul__(color self,v):
		return color._new(self.val*(<color>v).val if isinstance(v,color) else self.val*<real>v)


cdef class vec3:
	cdef ivec3 val

	def __init__(self,*args):
		try:
			largs=len(args)
			if largs==0:
				self.val=ivec3()
			elif largs==1:
				if isinstance(args[0],vec3):
					self.val=(<vec3?>args[0]).val
				else:
					self.val=ivec3(args[0])
			elif largs==2:
				self.val=ivec3(args[0],args[1],0)
			elif largs==3:
				self.val=ivec3(args[0],args[1],args[2])
			else:
				raise TypeError
		except TypeError:
			raise ValueError,'vec3() expects 0 to 3 arguments of type real, or 1 of type vec3'

	@staticmethod
	cdef vec3 _new(ivec3 val):
		cdef vec3 r=vec3()
		r.val=val
		return r

	@staticmethod
	cdef ivec3 _get(vec3 v): # needed for matrix templating
		return v.val

	def __repr__(self):
		return 'vec3({:.15},{:.15},{:.15})'.format(self.x(),self.y(),self.z())

	def __iter__(self):
		return iter((self.val.x(),self.val.y(),self.val.z()))

	def __reduce__(self):
		return vec3,(self.val.x(),self.val.y(),self.val.z())

	def __copy__(self):
		return vec3._new(self.val)

	def __hash__(self):
		return self.val.hash()

	def x(self):
		return self.val.x()

	def y(self):
		return self.val.y()

	def z(self):
		return self.val.z()

	def __add__(vec3 self,v):
		return vec3._new(self.val+(<vec3>v).val if isinstance(v,vec3) else self.val+<real>v)

	def __sub__(vec3 self,v):
		return vec3._new(self.val-(<vec3>v).val if isinstance(v,vec3) else self.val-<real>v)

	def __mul__(vec3 self,v):
		return vec3._new(self.val*(<vec3>v).val if isinstance(v,vec3) else self.val*<real>v)

	def __div__(vec3 self,v):
		if v in (0,0.0) or (isinstance(v,vec3) and v.isZero()):
			raise ValueError,'Divide by zero'

		return vec3._new(self.val/(<vec3>v).val if isinstance(v,vec3) else self.val/<real>v)

	def __neg__(vec3 self):
		return vec3._new(-self.val)

	def abs(self):
		return vec3._new(self.val.abs())

	def inv(self):
		return vec3._new(self.val.inv())

	def sign(self):
		return vec3._new(self.val.sign())

	def cross(self,vec3 v):
		return vec3._new(self.val.cross(v.val))

	def dot(self,vec3 v):
		return self.val.dot(v.val)

	def len(self):
		return self.val.len()

	def lenSq(self):
		return self.val.lenSq()

	def norm(self):
		return vec3._new(self.val.norm())

	def distTo(self,vec3 v):
		return self.val.distTo(v.val)

	def distToSq(self,vec3 v):
		return self.val.distToSq(v.val)

	def clamp(self,vec3 v1, vec3 v2):
		return  vec3._new(self.val.clamp(v1.val,v2.val))

	def setMinVals(self,vec3 v):
		self.val.setMinVals(v.val)

	def setMaxVals(self,vec3 v):
		self.val.setMaxVals(v.val)

	def normThis(self):
		self.val.normThis()

	def angleTo(self,vec3 v):
		return self.val.angleTo(v.val)

	def toPolar(self):
		return vec3._new(self.val.toPolar())

	def fromPolar(self):
		return vec3._new(self.val.fromPolar())

	def toCylindrical(self):
		return vec3._new(self.val.toCylindrical())

	def fromCylindrical(self):
		return vec3._new(self.val.fromCylindrical())

	def isZero(self):
		return self.val.isZero()

	def __richcmp__(vec3 self,v,int op):
		cdef ivec3 vv

		if v is None:
			return op==3 # objects are not equal to None

		if v is self:
			return op in (1,2,5) # objects are == <= >= to themselves

		if isinstance(v,vec3):
			vv=(<vec3>v).val
			if op==0: #<
				return self.val<vv
			elif op==1: #<=
				return self.val<vv or self.val==vv
			elif op==2: #==
				return self.val==vv
			elif op==3: #!=
				return self.val!=vv
			elif op==4: #>
				return self.val>vv
			elif op==5: #>=
				return self.val>vv or self.val==vv

		if op==2: # objects are not equal to objects of other types
			return False

		if op==3: # objects are unequal to objects of other types
			return True

		raise ValueError,'Cannot compare vec3 to %r'%type(v)

	def inAABB(self,vec3 minv,vec3 maxv):
		return self.val.inAABB(minv.val,maxv.val)

	def inOBB(self,vec3 minv,vec3 hx, vec3 hy, vec3 hz):
		return self.val.inOBB(minv.val,hx.val,hy.val,hz.val)

	def onPlane(self,vec3 planept,vec3 planenorm):
		return self.val.onPlane(planept.val,planenorm.val)

	def inSphere(self,vec3 center, real radius):
		return self.val.inSphere(center.val,radius)

	def isInUnitCube(self,real margin=0.0):
		return self.val.isInUnitCube(margin)
		
	def isColinear(self,vec3 other):
		return self.val.isColinear(other.val)

	def planeNorm(self,vec3 v2, vec3 v3):
		return vec3._new(self.val.planeNorm(v2.val,v3.val))

	def planeNorm(self,vec3 v2, vec3 v3,vec3 farv):
		return vec3._new(self.val.planeNorm(v2.val,v3.val,farv.val))

	def planeDist(self,vec3 planept,vec3 planenorm):
		return self.val.planeDist(planept.val,planenorm.val)

	def planeProject(self,vec3 planept, vec3 planenorm):
		return vec3._new(self.val.planeProject(planept.val,planenorm.val))

	def planeOrder(self,vec3 planenorm,vec3 v1, vec3 v2):
		return self.val.planeOrder(planenorm.val,v1.val,v2.val)

	def lineDist(self,vec3 v1, vec3 v2):
		return self.val.lineDist(v1.val,v2.val)

	def triArea(self,vec3 b, vec3 c):
		return self.val.triArea(b.val,c.val)

	def lerp(self,real val,vec3 v):
		return vec3._new(self.val.lerp(val,v.val))
		
	@staticmethod
	def X():
		return vec3._new(ivec3.X())
		
	@staticmethod
	def Y():
		return vec3._new(ivec3.Y())
		
	@staticmethod
	def Z():
		return vec3._new(ivec3.Z())


cdef class rotator:
	cdef irotator val
	def __init__(self,*args):
		try:
			largs=len(args)
			if largs==0:
				self.val=irotator()
			elif largs==1:
				if isinstance(args[0],rotator):
					self.val=irotator((<rotator?>args[0]).val)
				else:
					raise TypeError
			elif largs==2:
				if isinstance(args[1],vec3):
					self.val=irotator((<vec3?>args[0]).val,(<vec3?>args[1]).val)
				else:
					self.val=irotator((<vec3?>args[0]).val,<real>args[1])
			elif largs==3:
				self.val=irotator(args[0],args[1],args[2])
			elif largs==4:
				if isinstance(args[0],vec3):
					self.val=irotator((<vec3?>args[0]).val,(<vec3?>args[1]).val,(<vec3?>args[2]).val,(<vec3?>args[3]).val)
				else:
					self.val=irotator(<real>args[0],<real>args[1],<real>args[2],<real>args[3])
			elif largs==9:
				a,b,c,d,e,f,g,h,i=args
				self.val=irotator(a,b,c,d,e,f,g,h,i)
			else:
				raise TypeError
		except TypeError as e:
			raise TypeError,'Unexpected arguments for rotator constructor'

	@staticmethod
	cdef rotator _new(irotator val):
		cdef rotator r=rotator()
		r.val=val
		return r

	def __repr__(self):
		return 'rotator({:.15},{:.15},{:.15},{:.15})'.format(self.val.x(),self.val.y(),self.val.z(),self.val.w())

	def __iter__(self):
		return iter((self.val.x(),self.val.y(),self.val.z(),self.val.w()))

	def __reduce__(self):
		return rotator,(self.val.x(),self.val.y(),self.val.z(),self.val.w())

	def __copy__(self):
		return rotator._new(self.val)

	def __hash__(self):
		return self.val.hash()

	def x(self):
		return self.val.x()

	def y(self):
		return self.val.y()

	def z(self):
		return self.val.z()

	def w(self):
		return self.val.w()

	def getYaw(self):
		return self.val.getYaw()

	def getPitch(self):
		return self.val.getPitch()

	def getRoll(self):
		return self.val.getRoll()

	def getEulers(self):
		return self.val.getYaw(),self.val.getPitch(),self.val.getRoll()

	def __mul__(rotator self,v):
		if isinstance(v,vec3):
			return vec3._new(self.val*(<vec3>v).val)
		elif isinstance(v,rotator):
			return rotator._new(self.val*(<rotator>v).val)
		else:
			raise TypeError,'A rotator can be multiplied with vec3 or rotator instance only'

	def __div__(rotator self,v):
		return vec3._new(self.val/(<vec3>v).val)

	def inverse(self):
		return rotator._new(self.val.inverse())

	def norm(self):
		return rotator._new(self.val.norm())

	def normThis(self):
		self.val.normThis()
		
	def __richcmp__(rotator self,v,int op):
		cdef irotator vv

		if v is None:
			return op==3

		if v is self:
			return op in (1,2,5)

		if isinstance(v,rotator):
			vv=(<rotator>v).val
			if op==2:
				return self.val==vv
			elif op==3:
				return self.val!=vv
			else:
				raise ValueError,'Unsupported operator'

		if op==2: # objects are not equal to objects of other types
			return False

		if op==3: # objects are unequal to objects of other types
			return True

		raise ValueError,'Cannot compare rotator to %r'%type(v)

	def toMatrix(self):
		cdef real m[16]
		self.val.toMatrix(m)
		return (m[0],m[1],m[2],m[3]),(m[4],m[5],m[6],m[7]),(m[8],m[9],m[10],m[11]),(m[12],m[13],m[14],m[15])


cdef class Ray:
	cdef iRay val

	def __init__(self,vec3 pos, vec3 rdir):
		self.val=iRay(pos.val,rdir.val)

	@staticmethod
	cdef Ray _new(iRay val):
		cdef Ray r=Ray(vec3(),vec3(1))
		r.val=val
		return r

	def __repr__(self):
		return 'Ray({},{})'.format(self.getPosition(),self.getDirection())

	def getPosition(self,real len=0):
		return vec3._new(self.val.getPosition(len))

	def getDirection(self):
		return vec3._new(self.val.getDirection())

	def setPosition(self,vec3 v):
		self.val.setPosition(v.val)

	def setDirection(self,vec3 v):
		self.val.setDirection(v.val)

	def distTo(self,vec3 v):
		return self.val.distTo(v.val)

	def intersectsAABB(self,vec3 minv, vec3 maxv):
		cdef realpair r=self.val.intersectsAABB(minv.val,maxv.val)
		if r.first>=0 and r.second>=0:
			return r.first,r.second
		else:
			return tuple()

	def intersectsSphere(self,vec3 center, real rad):
		cdef realpair r=self.val.intersectsSphere(center.val,rad)
		return r.first,r.second

	def intersectsRay(self,Ray ray):
		cdef realpair r=self.val.intersectsRay(ray.val)
		return r.first,r.second

	def intersectsLineSeg(self,vec3 v1, vec3 v2):
		return self.val.intersectsLineSeg(v1.val,v2.val)

	def intersectsPlane(self,vec3 v1, vec3 v2):
		return self.val.intersectsPlane(v1.val,v2.val)

	def intersectsTri(self,vec3 v0, vec3 v1, vec3 v2):
		cdef realtriple r=self.val.intersectsTri(v0.val,v1.val,v2.val)
		if r.first>=0:
			return r.first,r.second,r.third
		else:
			return tuple()

	def intersectsTriMesh(self, Vec3Matrix nodes, IndexMatrix inds, Vec3Matrix centers, RealMatrix radii2,sval numResults=-1,sval excludeInd=-1):
		cdef vector[indextriple] triples=self.val.intersectsTriMesh(nodes.mat,inds.mat,centers.mat,radii2.mat,numResults,excludeInd)
		cdef indextriple rp
		cdef list result=[]

		for i in range(triples.size()):
			rp=triples[i]
			result.append((rp.first,rp.second.first,rp.second.second,rp.second.third))

		return result


cdef class transform:
	cdef itransform val

	def __init__(self,*args):
		try:
			largs=len(args)
			if largs==0:
				self.val=itransform()
			elif largs==1 and isinstance(args[0],transform):
				self.val=(<transform?>args[0]).val
			elif largs in (1,2,3,4) and isinstance(args[0],vec3):
				self.val=itransform((<vec3?>args[0]).val,(<vec3?>args[1]).val if largs>1 else ivec3(),(<rotator?>args[2]).val if largs>2 else irotator(),largs==4 and bool(args[3]))
			elif largs in (9,10):
				self.val=itransform(<real>args[0],<real>args[1],<real>args[2],<real>args[3],<real>args[4],<real>args[5],<real>args[6],<real>args[7],<real>args[8],largs==10 and bool(args[9]))
			else:
				raise TypeError
		except TypeError as e:
			raise TypeError,'Unexpected arguments for transform constructor'

	@staticmethod
	cdef transform _new(itransform val):
		cdef transform r=transform()
		r.val=val
		return r

	def __repr__(self):
		return 'transform({:.15},{:.15},{:.15},{:.15},{:.15},{:.15},{:.15},{:.15},{:.15},{})'.format(*self)

	def __iter__(self):
		cdef ivec3 t=self.val.getTranslation()
		cdef ivec3 s=self.val.getScale()
		cdef irotator r=self.val.getRotation()
		return iter((t.x(),t.y(),t.z(),s.x(),s.y(),s.z(),r.getYaw(),r.getPitch(),r.getRoll(),self.val.isInverse()))

	def __reduce__(self):
		return transform,tuple(self)

	def __copy__(self):
		return transform._new(self.val)

	def __richcmp__(transform self,v,int op):
		cdef itransform vv

		if v is None:
			return op==3

		if v is self:
			return op in (1,2,5)

		if isinstance(v,transform):
			vv=(<transform>v).val
			if op==2:
				return self.val==vv
			elif op==3:
				return not(self.val==vv)
			else:
				raise ValueError,'Unsupported operator'

		if op==2: # objects are not equal to objects of other types
			return False

		if op==3: # objects are unequal to objects of other types
			return True

		raise ValueError,'Cannot compare transform to %r'%type(v)

	def __mul__(transform self, v):
		if isinstance(v,transform):
			return transform._new(self.val*(<transform?>v).val)
		elif isinstance(v,Ray):
			return Ray._new(self.val*(<Ray?>v).val)
		else:
			return vec3._new(self.val*(<vec3?>v).val)

	def __div__(transform self,vec3 v):
		return vec3._new(self.val/v.val)

	def getTranslation(self):
		return vec3._new(self.val.getTranslation())

	def getScale(self):
		return vec3._new(self.val.getScale())

	def getRotation(self):
		return rotator._new(self.val.getRotation())

	def setTranslation(self,vec3 t):
		self.val.setTranslation(t.val)

	def setScale(self,vec3 s):
		self.val.setScale(s.val)

	def setRotation(self,rotator r):
		self.val.setRotation(r.val)

	def isInverse(self):
		return self.val.isInverse()

	def inverse(self):
		return transform._new(self.val.inverse())

	def directional(self):
		return transform._new(self.val.directional())

	def toMatrix(self):
		cdef real m[16]
		self.val.toMatrix(m)
		return (m[0],m[1],m[2],m[3]),(m[4],m[5],m[6],m[7]),(m[8],m[9],m[10],m[11]),(m[12],m[13],m[14],m[15])


# used to get around a declaration bug
_MemoryError=MemoryError
_IndexError=IndexError

include "IndexMatrix.pyx"
include "RealMatrix.pyx"
include "Vec3Matrix.pyx"
include "ColorMatrix.pyx"


cdef class Config:
	cdef iConfig val

	def set(self,str group_name,str name_value, str value_none=None):
		if value_none==None:
			self.val.set(group_name,name_value)
		else:
			self.val.set(group_name,name_value,value_none)

	def get(self,str group_name,str name_none=None):
		if name_none==None:
			return self.val.get(group_name)
		else:
			return self.val.get(group_name,name_none)

	def hasValue(self,str group, str name):
		return self.val.hasValue(group,name)

	def __repr__(self):
		return self.val.toString()


cdef class VertexBuffer:

	cdef iVertexBuffer* _get(self): # overridden in subtypes
		pass

	def getVertex(self,int i):
		pass

	def getNormal(self,int i):
		pass

	def getColor(self, int i):
		pass

	def getUVWCoord(self,int i):
		pass

	def numVertices(self):
		pass

	def hasNormal(self):
		pass

	def hasColor(self):
		pass

	def hasUVWCoord(self):
		pass


cdef class IndexBuffer:
	cdef iIndexBuffer* _get(self): # overridden in subtypes
		pass

	def numIndices(self):
		pass

	def indexWidth(self,int i):
		pass

	def getIndex(self, int i, int w):
		pass


cdef class MatrixVertexBuffer(VertexBuffer):
	cdef iMatrixVertexBuffer *val

	def __init__(self,Vec3Matrix vecs,ColorMatrix cols=None,IndexMatrix extinds=None):
		self.val=new iMatrixVertexBuffer(vecs.mat,ColorMatrix._getNone(cols),IndexMatrix._getNone(extinds))

	def __dealloc__(MatrixIndexBuffer self):
		del self.val

	cdef iVertexBuffer* _get(self):
		return self.val

	def getVertex(self,int i):
		return vec3._new(self.val.getVertex(i))

	def getNormal(self,int i):
		return vec3._new(self.val.getNormal(i))

	def getColor(self, int i):
		return color._new(self.val.getColor(i))

	def getUVWCoord(self,int i):
		return vec3._new(self.val.getUVWCoord(i))

	def numVertices(self):
		return self.val.numVertices()

	def hasNormal(self):
		return self.val.hasNormal()

	def hasColor(self):
		return self.val.hasColor()

	def hasUVWCoord(self):
		return self.val.hasUVWCoord()


cdef class MatrixIndexBuffer(IndexBuffer):
	cdef iMatrixIndexBuffer* val

	def __init__(self,IndexMatrix indices, IndexMatrix extinds=None):
		self.val=new iMatrixIndexBuffer(indices.mat,IndexMatrix._getNone(extinds))

	def __dealloc__(MatrixIndexBuffer self):
		del self.val

	cdef iIndexBuffer* _get(self):
		return self.val

	def numIndices(self):
		return self.val.numIndices()

	def indexWidth(self,int i):
		return self.val.indexWidth(i)

	def getIndex(self, int i, int w):
		return self.val.getIndex(i,w)


cdef ivec3 vertexFunc(void* context,int i) with gil:
	cdef CallbackVertexBuffer c
	try:
		c=<CallbackVertexBuffer>context
		return (<vec3?>c.getVertex(i)).val
	except:
		return ivec3()

cdef ivec3 normalFunc(void* context,int i) with gil:
	cdef CallbackVertexBuffer c
	try:
		c=<CallbackVertexBuffer>context
		return (<vec3?>c.getNormal(i)).val
	except:
		return ivec3()

cdef icolor colorFunc(void* context,int i) with gil:
	cdef CallbackVertexBuffer c
	try:
		c=<CallbackVertexBuffer>context
		return (<color?>c.getColor(i)).val
	except:
		return icolor()

cdef ivec3 uvwFunc(void* context,int i) with gil:
	cdef CallbackVertexBuffer c
	try:
		c=<CallbackVertexBuffer>context
		return (<vec3?>c.getUVWCoord(i)).val
	except:
		return ivec3()


cdef sval widthFunc(void* context,int i) with gil:
	cdef CallbackIndexBuffer c
	try:
		c=<CallbackIndexBuffer>context
		return c.indexWidth(i)
	except:
		return 0

cdef sval indexFunc(void* context,int i,int w) with gil:
	cdef CallbackIndexBuffer c
	try:
		c=<CallbackIndexBuffer>context
		return c.getIndex(i,w)
	except:
		return 0


cdef class CallbackVertexBuffer(VertexBuffer):
	'''
	Defines the basic skeleton for a buffer with Cython/Python method bodies callable in C++. This class should be
	subtyped and method bodies implemented to interface Python data into the renderer through fillData().
	'''
	cdef iCallbackVertexBuffer[void*]* val

	def __init__(self,sval numvertices,bint hasNormal,bint hasColor,bint hasUVWCoord):
		cdef ivec3 (*normf)(void*,int)
		cdef ivec3 (*uvwf)(void*,int)
		cdef icolor (*colorf)(void*,int)

		if hasNormal:
			normf=normalFunc
		else:
			normf=NULL

		if hasColor:
			colorf=colorFunc
		else:
			colorf=NULL

		if hasUVWCoord:
			uvwf=uvwFunc
		else:
			uvwf=NULL

		self.val=new iCallbackVertexBuffer[void*](<void*>self,numvertices,vertexFunc,normf,colorf,uvwf)

	def __dealloc__(MatrixIndexBuffer self):
		del self.val

	cdef iVertexBuffer* _get(self):
		return self.val

	def getVertex(self,int i):
		return vec3()

	def getNormal(self,int i):
		return vec3()

	def getColor(self, int i):
		return color()

	def getUVWCoord(self,int i):
		return vec3()

	def numVertices(self):
		return self.val.numVertices()

	def hasNormal(self):
		return self.val.hasNormal()

	def hasColor(self):
		return self.val.hasColor()

	def hasUVWCoord(self):
		return self.val.hasUVWCoord()


cdef class CallbackIndexBuffer(IndexBuffer):
	'''
	Defines the basic skeleton for a buffer with Cython/Python method bodies callable in C++. This class should be
	subtyped and method bodies implemented to interface Python data into the renderer through fillData().
	'''
	cdef iCallbackIndexBuffer[void*]* val

	def __init__(self,sval numindices):
		self.val=new iCallbackIndexBuffer[void*](<void*>self,numindices,widthFunc,indexFunc)

	def __dealloc__(MatrixIndexBuffer self):
		del self.val

	cdef iIndexBuffer* _get(self):
		return self.val

	def numIndices(self):
		return self.val.numIndices()

	def indexWidth(self,int i):
		return 0

	def getIndex(self, int i, int w):
		return 0


cdef class PyVertexBuffer(CallbackVertexBuffer):
	'''
	Stores a list of vertices and their associated normals and colors. The vertices and normals are instances of
	vec3 and the colors are instances of color.
	'''
	cdef object vecs
	cdef object norms
	cdef object cols
	cdef object uvws
	def __init__(self,vecs,norms=None,cols=None,uvws=None):
		CallbackVertexBuffer.__init__(self,len(vecs),bool(norms),bool(cols),bool(uvws))

		self.vecs=vecs
		self.norms=norms
		self.cols=cols
		self.uvws=uvws

		assert all(isinstance(v,vec3) for v in vecs)
		assert norms==None or all(isinstance(v,vec3) for v in norms)
		assert cols==None or all(isinstance(c,color) for c in cols)
		assert uvws==None or all(isinstance(v,vec3) for v in uvws)

#	def numVertices(self):
#		return len(self.vecs)

	def getVertex(self,int i):
		return self.vecs[i]

	def getColor(self,int i):
		return self.cols[i]

	def getNormal(self,int i):
		return self.norms[i]

	def getUVWCoord(self,int i):
		return self.uvws[i]


cdef class PyIndexBuffer(CallbackIndexBuffer):
	'''
	Stores a list of indices, which are enumerable objects containing the indices of vertices defining the figure as
	stored in a vertex buffer.
	'''
	cdef object indices
	def __init__(self,indices):
		CallbackIndexBuffer.__init__(self,len(indices))
		self.indices=indices

	def numIndices(self):
		return len(self.indices)

	def indexWidth(self,int i):
		return len(self.indices[i])

	def getIndex(self,int i,int j):
		return self.indices[i][j]


cdef class Vec3Curve:
	cdef iVec3Curve* val

	def Vec3Curve(self,bint isXFunc):
		self.val=new iVec3Curve(isXFunc)

	def __dealloc__(self):
		del self.val

	def addCtrlPoint(self,vec3 t):
		self.val.addCtrlPoint(t.val)

	def setCtrlPoint(self,vec3 t,indexval index):
		self.val.setCtrlPoint(t.val,index)

	def removeCtrlPoint(self,indexval index):
		self.val.removeCtrlPoint(index)

	def numPoints(self):
		return self.val.numPoints()

	def getCtrlPoint(self, indexval index):
		return vec3._new(self.val.getCtrlPoint(index))

	def at(self,real tt):
		return vec3._new(self.val.at(tt))

	def atX(self,real x, real threshold=0.001):
		return self.val.atX(x,threshold)


cdef class Spectrum:
	cdef iSpectrum* val

	def __init__(self,str name='',):
		self.val=new iSpectrum(name)
		
	@staticmethod
	cdef _new(iSpectrum* val):
		cdef Spectrum m=Spectrum()
		m.val=val
		return m
		
	def __dealloc__(self):
		if self.val:
			del self.val

	def getName(self):
		return self.val.getName()
		
	def setSpectrumData(self,colors,colorpos=None,alphactrls=None):
		self.val.clearSpectrum()
		colorpos=colorpos or np.linspace(0,1.0,len(colors))
		for c,p in zip(colors,colorpos):
			self.addSpectrumValue(p,c)
				
		if alphactrls:
			for a in alphactrls:
				self.addAlphaCtrl(a)
		
	def copySpectrumFrom(self,Spectrum s):
		self.val.copySpectrumFrom(s.val)

	def addSpectrumValue(self,real pos,color value):
		self.val.addSpectrumValue(pos,value.val)

	def numSpectrumValues(self):
		return self.val.numSpectrumValues()

	def getSpectrumIndex(self,real pos,color value):
		return self.val.getSpectrumIndex(pos,value.val)

	def interpolateColor(self,real pos):
		return color._new(self.val.interpolateColor(pos))

	def removeSpectrumValue(self,int index):
		self.val.removeSpectrumValue(index)

	def getSpectrumPos(self,int index):
		return self.val.getSpectrumPos(index)

	def getSpectrumValue(self,int index):
		return color._new(self.val.getSpectrumValue(index))

	def setSpectrumValue(self,sval index, real pos,color value):
		self.val.setSpectrumValue(index,pos,value.val)

	def numAlphaCtrls(self):
		return self.val.numAlphaCtrls()

	def getAlphaCtrl(self,indexval index):
		return vec3._new(self.val.getAlphaCtrl(index))

	def addAlphaCtrl(self,vec3 v):
		self.val.addAlphaCtrl(v.val)

	def removeAlphaCtrl(self,indexval index):
		self.val.removeAlphaCtrl(index)

	def setAlphaCtrl(self,vec3 v, indexval index):
		self.val.setAlphaCtrl(v.val,index)

	def setLinearAlpha(self,bint b):
		self.val.setLinearAlpha(b)

	def isLinearAlpha(self):
		return self.val.isLinearAlpha()

	def fillColorMatrix(self,ColorMatrix col, RealMatrix mat,bint useValAsAlpha=False):
		self.val.fillColorMatrix(col.mat,mat.mat,useValAsAlpha)


cdef class Material(Spectrum):
	cdef iMaterial* mval

	@staticmethod
	cdef _new(iMaterial* val):
		cdef Material m=Material()
		del m.val
		m.mval=val
		m.val=val
		return m

	def __dealloc__(self):
		self.val=NULL
		del self.mval

	def copyTo(self,Material mat,bint copyTex,bint copySpec,bint copyProgs):
		self.mval.copyTo(mat.mval,copyTex,copySpec,copyProgs)

	def clone(self,str name):
		return Material._new(self.mval.clone(name))
		
	def getAlpha(self):
		return self.mval.getAlpha()

	def setAlpha(self,real alpha):
		self.mval.setAlpha(alpha)

	def usesInternalAlpha(self):
		return self.mval.usesInternalAlpha()

	def useInternalAlpha(self,bint v):
		self.mval.useInternalAlpha(v)

	def getAmbient(self):
		return color._new(self.mval.getAmbient())

	def getDiffuse(self):
		return color._new(self.mval.getDiffuse())

	def getSpecular(self):
		return color._new(self.mval.getSpecular())

	def getEmissive(self):
		return color._new(self.mval.getEmissive())

	def getShininess(self):
		return self.mval.getShininess()

	def getPointSizeMin(self):
		return self.mval.getPointSizeMin()

	def getPointSizeMax(self):
		return self.mval.getPointSizeMax()

	def getPointSizeAbs(self):
		return self.mval.getPointSizeAbs()

	def usesPointAttenuation(self):
		return self.mval.usesPointAttenuation()

	def getBlendMode(self):
		return self.mval.getBlendMode()

	def usesVertexColor(self):
		return self.mval.usesVertexColor()

	def usesLighting(self):
		return self.mval.usesLighting()

	def usesFlatShading(self):
		return self.mval.usesFlatShading()

	def usesDepthCheck(self):
		return self.mval.usesDepthCheck()

	def usesDepthWrite(self):
		return self.mval.usesDepthWrite()

	def usesTexFiltering(self):
		return self.mval.usesTexFiltering()

	def isClampTexAddress(self):
		return self.mval.isClampTexAddress()

	def isCullBackfaces(self):
		return self.mval.isCullBackfaces()

	def usesPointSprites(self):
		return self.mval.usesPointSprites()

	def getTexture(self):
		return self.mval.getTexture()

	def getGPUProgram(self,ProgramType pt):
		return self.mval.getGPUProgram(pt)

	def isTransparentColor(self):
		return self.mval.isTransparentColor()

	def setAmbient(self,color c):
		self.mval.setAmbient(c.val)

	def setDiffuse(self,color c) :
		self.mval.setDiffuse(c.val)

	def setSpecular(self,color c):
		self.mval.setSpecular(c.val)

	def setEmissive(self,color c):
		self.mval.setEmissive(c.val)

	def setShininess(self,real c):
		self.mval.setShininess(c)

	def setPointSize(self,real min,real max) :
		self.mval.setPointSize(min,max)

	def setPointSizeAbs(self,real size):
		self.mval.setPointSizeAbs(size)

	def setPointAttenuation(self,bint enabled,real constant=0.0,real linear=1.0, real quad=0.0):
		self.mval.setPointAttenuation(enabled,constant,linear,quad)

	def setBlendMode(self,BlendMode bm):
		self.mval.setBlendMode(bm)

	def useVertexColor(self,bint use):
		self.mval.useVertexColor(use)

	def useLighting(self,bint use):
		self.mval.useLighting(use)

	def useFlatShading(self,bint use):
		self.mval.useFlatShading(use)

	def useDepthCheck(self,bint use):
		self.mval.useDepthCheck(use)

	def useDepthWrite(self,bint use):
		self.mval.useDepthWrite(use)

	def useTexFiltering(self,bint use):
		self.mval.useTexFiltering(use)

	def clampTexAddress(self,bint use):
		self.mval.clampTexAddress(use)

	def cullBackfaces(self,bint cull):
		self.mval.cullBackfaces(cull)

	def usePointSprites(self,bint useSprites):
		self.mval.usePointSprites(useSprites)

	def useSpectrumTexture(self,bint use):
		self.mval.useSpectrumTexture(use)

	def setGPUProgram(self, name_prog, ProgramType pt=PT_FRAGMENT):
		if isinstance(name_prog,str):
			self.mval.setGPUProgram(str(name_prog),pt)
		else:
			self.mval.setGPUProgram((<GPUProgram?>name_prog).val)

	def setTexture(self, tex):
		if isinstance(tex,str):
			self.mval.setTexture(str(tex))
		else:
			self.mval.setTexture((<Texture?>tex).getName())

	def setGPUParamInt(self,ProgramType pt,str name, int i):
		return self.mval.setGPUParamInt(pt,name,i)

	def setGPUParamReal(self,ProgramType pt,str name, real r):
		return self.mval.setGPUParamReal(pt,name,r)

	def setGPUParamVec3(self,ProgramType pt,str name, vec3 v):
		return self.mval.setGPUParamVec3(pt,name,v.val)

	def setGPUParamColor(self,ProgramType pt,str name, color c):
		return self.mval.setGPUParamColor(pt,name,c.val)

#	def addSpectrumValue(self,real pos,color value):
#		self.val.addSpectrumValue(pos,value.val)
#
#	def numSpectrumValues(self):
#		return self.val.numSpectrumValues()
#
#	def getSpectrumIndex(self,real pos,color value):
#		return self.val.getSpectrumIndex(pos,value.val)
#
#	def interpolateColor(self,real pos):
#		return color._new(self.val.interpolateColor(pos))
#
#	def removeSpectrumValue(self,int index):
#		self.val.removeSpectrumValue(index)
#
#	def getSpectrumPos(self,int index):
#		return self.val.getSpectrumPos(index)
#
#	def getSpectrumValue(self,int index):
#		return color._new(self.val.getSpectrumValue(index))
#
#	def setSpectrumValue(self,sval index, real pos,color value):
#		self.val.setSpectrumValue(index,pos,value.val)
#
#	def numAlphaCtrls(self):
#		return self.val.numAlphaCtrls()
#
#	def getAlphaCtrl(self,indexval index):
#		return vec3._new(self.val.getAlphaCtrl(index))
#
#	def addAlphaCtrl(self,vec3 v):
#		self.val.addAlphaCtrl(v.val)
#
#	def removeAlphaCtrl(self,indexval index):
#		self.val.removeAlphaCtrl(index)
#
#	def setAlphaCtrl(self,vec3 v, indexval index):
#		self.val.setAlphaCtrl(v.val,index)
#
#	def setLinearAlpha(self,bint b):
#		self.val.setLinearAlpha(b)
#
#	def isLinearAlpha(self):
#		return self.val.isLinearAlpha()
#
#	def fillColorMatrix(self,ColorMatrix col, RealMatrix mat,bint useValAsAlpha=False):
#		self.val.fillColorMatrix(col.mat,mat.mat,useValAsAlpha)


cdef class Light:
	cdef iLight* val

	@staticmethod
	cdef _new(iLight* val):
		cdef Light l=Light()
		l.val=val
		return l

	def __dealloc__(self):
		del self.val

	def setPosition(self,vec3 v):
		self.val.setPosition(v.val)

	def setDirection(self,vec3 v):
		self.val.setDirection(v.val)

	def setDiffuse(self,color c):
		self.val.setDiffuse(c.val)

	def setSpecular(self,color c):
		self.val.setSpecular(c.val)

	def setDirectional(self):
		self.val.setDirectional()

	def setPoint(self):
		self.val.setPoint()

	def setSpotlight(self,real radsInner, real radsOuter, real falloff=1.0):
		self.val.setSpotlight(radsInner, radsOuter,falloff)

	def setAttenuation(self,real rrange, real constant=0.0,real linear=1.0, real quad=0.0):
		self.val.setAttenuation(rrange,constant,linear,quad)

	def setVisible(self,bint isVisible):
		self.val.setVisible(isVisible)

	def isVisible(self):
		return self.val.isVisible()


cdef class Image:
	cdef iImage* val

	@staticmethod
	cdef _new(iImage* val):
		cdef Image v=Image()
		v.val=val
		return v

	def __dealloc__(self):
		del self.val

	def getFormat(self):
		return self.val.getFormat()

	def getWidth(self):
		return self.val.getWidth()

	def getHeight(self):
		return self.val.getHeight()

	def getDepth(self):
		return self.val.getDepth()
		
	def getData(self):
		cdef RenderTypes.u8* p=self.val.getData()
		return <bytes>p[:self.val.getDataSize()]
		
	def encode(self,format='png'):
		return self.val.encode(format)

	def fillRealMatrix(self,RealMatrix mat):
		self.val.fillRealMatrix(mat.mat)

	def fillColorMatrix(self,ColorMatrix mat):
		self.val.fillColorMatrix(mat.mat)


cdef class Camera:
	cdef iCamera* val

	@staticmethod
	cdef _new(iCamera* val):
		cdef Camera c=Camera()
		c.val=val
		return c

	def __dealloc__(self):
		if self.val:
			del self.val

	def deleteObj(self):
		if self.val:
			del self.val
			self.val=NULL

	def _checkObjectNull(self):
		if self.val==NULL:
			raise RuntimeError,'Internal C++ object deleted'

	def getName(self):
		self._checkObjectNull()
		return self.val.getName()

	def getAspectRatio(self):
		self._checkObjectNull()
		return self.val.getAspectRatio()

	def getProjectedRay(self,real x, real y, bint isAbsolute=True):
		self._checkObjectNull()
		cdef Ray r=Ray(vec3(),vec3(1,0,0))
		r.val=deref(self.val.getProjectedRay(x,y,isAbsolute))
		return r

	def getPosition(self):
		self._checkObjectNull()
		return vec3._new(self.val.getPosition())

	def getLookAt(self):
		self._checkObjectNull()
		return vec3._new(self.val.getLookAt())
		
	def getRotation(self):
		self._checkObjectNull()
		return rotator._new(self.val.getRotation())

	def getScreenPosition(self,vec3 pos):
		self._checkObjectNull()
		return vec3._new(self.val.getScreenPosition(pos.val))

	def getWorldPosition(self,real x, real y, bint isAbsolute=True):
		self._checkObjectNull()
		return vec3._new(self.val.getWorldPosition(x,y,isAbsolute))

	def getVertFOV(self):
		self._checkObjectNull()
		return self.val.getVertFOV()

	def getNearClip(self):
		self._checkObjectNull()
		return self.val.getNearClip()

	def getFarClip(self):
		self._checkObjectNull()
		return self.val.getFarClip()

	def getWidth(self):
		self._checkObjectNull()
		return self.val.getWidth()

	def getHeight(self):
		self._checkObjectNull()
		return self.val.getHeight()

	def isSecondaryCamera(self):
		self._checkObjectNull()
		return self.val.isSecondaryCamera()

	def isPointInViewport(self,int x, int y):
		self._checkObjectNull()
		return self.val.isPointInViewport(x,y)

	def setPosition(self,vec3 v):
		self._checkObjectNull()
		self.val.setPosition(v.val)

	def setLookAt(self,vec3 v):
		self._checkObjectNull()
		self.val.setLookAt(v.val)

	def setUp(self,vec3 v):
		self._checkObjectNull()
		self.val.setUp(v.val)

	def setZUp(self):
		self._checkObjectNull()
		self.val.setZUp()

	def rotate(self,rotator r):
		self._checkObjectNull()
		self.val.rotate(r.val)

	def setRotation(self,rotator r):
		self._checkObjectNull()
		self.val.setRotation(r.val)

	def setNearClip(self,real dist):
		self._checkObjectNull()
		self.val.setNearClip(dist)

	def setFarClip(self,real dist):
		self._checkObjectNull()
		self.val.setFarClip(dist)

	def setVertFOV(self,real rads):
		self._checkObjectNull()
		self.val.setVertFOV(rads)

	def setBGColor(self,color c):
		self._checkObjectNull()
		self.val.setBGColor(c.val)

	def setAspectRatio(self,real rat):
		self._checkObjectNull()
		self.val.setAspectRatio(rat)

	def setViewport(self,real left=0.0,real top=0.0,real width=1.0,real height=1.0):
		self._checkObjectNull()
		self.val.setViewport(left,top,width,height)

	def setOrtho(self,bint isOrtho):
		self._checkObjectNull()
		self.val.setOrtho(isOrtho)

	def setWireframe(self,bint isWireframe):
		self._checkObjectNull()
		self.val.setWireframe(isWireframe)

	def setSecondaryCamera(self,bint secondary):
		self._checkObjectNull()
		self.val.setSecondaryCamera(secondary)

	def renderToFile(self,str filename,sval width,sval height, TextureFormat tformat=TF_RGB24,real stereoOffset=0.0):
		self._checkObjectNull()
		self.val.renderToFile(filename,width,height,tformat,stereoOffset)

	def renderToStream(self,u64 stream,sval width,sval height, TextureFormat tformat=TF_RGB24,real stereoOffset=0.0):
		self._checkObjectNull()
		self.val.renderToStream(<void*>stream,width,height,tformat,stereoOffset)

	def renderToImage(self,sval width,sval height, TextureFormat tformat=TF_RGB24,real stereoOffset=0.0):
		self._checkObjectNull()
		return Image._new(self.val.renderToImage(width,height,tformat,stereoOffset))

		
cdef class Figure:
	cdef iFigure* val

	@staticmethod
	cdef _new(iFigure* val):
		cdef Figure v=Figure()
		v.val=val
		return v

	def __dealloc__(self):
		del self.val

	def getName(self):
		return self.val.getName()

	def setPosition(self,vec3 v):
		self.val.setPosition(v.val)

	def setRotation(self,rotator r):
		self.val.setRotation(r.val)

	def setScale(self,vec3 v):
		self.val.setScale(v.val)

	def setTransform(self,object trans,vec3 scale=vec3(1), rotator rot=rotator()):
		if isinstance(trans,transform):
			self.val.setTransform((<transform>trans).val)
		else:
			self.val.setTransform((<vec3?>trans).val,scale.val,rot.val)

	def setMaterial(self,mat):
		if isinstance(mat,str):
			self.val.setMaterial(str(mat))
		else:
			self.val.setMaterial((<Material?>mat).getName())

	def getMaterial(self):
		return self.val.getMaterial()
		
	def getAABB(self):
		cdef pair[ivec3,ivec3] aabb=self.val.getAABB()
		return (vec3._new(aabb.first),vec3._new(aabb.second))

	def fillData(self,VertexBuffer vb, IndexBuffer ib,bint deferFill=False,bint doubleSided=False):
		cdef iVertexBuffer* vbuf=NULL
		cdef iIndexBuffer* ibuf=NULL
		if vb:
			vbuf=vb._get()

		if ib:
			ibuf=ib._get()

		self.val.fillData(vbuf,ibuf,deferFill,doubleSided)

	def setVisible(self,bint isVisible):
		self.val.setVisible(isVisible)

	def isVisible(self):
		return self.val.isVisible()

	def isTransparent(self):
		return self.val.isTransparent()

	def isOverlay(self):
		return self.val.isOverlay()

	def getRenderQueue(self):
		return self.val.getRenderQueue()

	def setTransparent(self,bint isTrans):
		self.val.setTransparent(isTrans)

	def setOverlay(self,bint isOverlay):
		self.val.setOverlay(isOverlay)

	def setRenderQueue(self,sval queue):
		self.val.setRenderQueue(queue)

	def setCameraVisibility(self,Camera cam, bint isVisible):
		self.val.setCameraVisibility(cam.val if cam else NULL,isVisible)

	def setParent(self,Figure fig):
		self.val.setParent(fig.val if fig else NULL)

	def getPosition(self,bint isDerived=False):
		return vec3._new(self.val.getPosition(isDerived))

	def getScale(self,bint isDerived=False):
		return vec3._new(self.val.getScale(isDerived))

	def getRotation(self,bint isDerived=False):
		return rotator._new(self.val.getRotation(isDerived))

	def getTransform(self,bint isDerived=False):
		return transform._new(self.val.getTransform(isDerived))


cdef class BBSetFigure(Figure):
	cdef iBBSetFigure* bbval

	@staticmethod
	cdef _new(iBBSetFigure* val):
		cdef BBSetFigure v=BBSetFigure()
		v.val=val
		v.bbval=val
		return v

	def setDimension(self,real width, real height):
		self.bbval.setDimension(width,height)

	def getWidth(self):
		return self.bbval.getWidth()

	def getHeight(self):
		return self.bbval.getHeight()

	def setUpVector(self,vec3 v):
		self.bbval.setUpVector(v.val)

	def numBillboards(self):
		return self.bbval.numBillboards()

	def setBillboardPos(self,indexval index, vec3 pos):
		self.bbval.setBillboardPos(index,pos.val)

	def setBillboardDir(self,indexval index, vec3 bdir):
		self.bbval.setBillboardDir(index,bdir.val)

	def setBillboardColor(self,indexval index, color col):
		self.bbval.setBillboardColor(index,col.val)


cdef class TextureVolumeFigure(Figure):
	cdef iTextureVolumeFigure* texval

	@staticmethod
	cdef _new(iTextureVolumeFigure* val):
		cdef TextureVolumeFigure v=TextureVolumeFigure()
		v.val=val
		v.texval=val
		return v

	def setNumPlanes(self,sval num):
		self.texval.setNumPlanes(num)

	def getNumPlanes(self):
		return self.texval.getNumPlanes()

	def setAlpha(self,real a):
		self.texval.setAlpha(a)

	def getAlpha(self):
		return self.texval.getAlpha()

	def setTexAABB(self,vec3 minv, vec3 maxv):
		self.texval.setTexAABB(minv.val,maxv.val)

	def setAABB(self,vec3 minv, vec3 maxv):
		self.texval.setAABB(minv.val,maxv.val)

	def getTexXiPos(self,vec3 pos):
		return vec3._new(self.texval.getTexXiPos(pos.val))

	def getTexXiDir(self,vec3 pos):
		return vec3._new(self.texval.getTexXiDir(pos.val))

	def getPlaneIntersects(self,vec3 planept, vec3 planenorm,bint transformPlane=False,bint isXiPoint=False):
		cdef ivec3 vbuffer[6][2]
		cdef sval result=self.texval.getPlaneIntersects(planept.val,planenorm.val,vbuffer,transformPlane,isXiPoint)
		return [(vec3._new(vbuffer[i][0]),vec3._new(vbuffer[i][1])) for i in range(result)]


cdef class GlyphFigure(Figure):
	cdef iGlyphFigure* gval

	@staticmethod
	cdef _new(iGlyphFigure* val):
		cdef GlyphFigure v=GlyphFigure()
		v.val=val
		v.gval=val
		return v

	def setGlyphScale(self,vec3 v):
		self.gval.setGlyphScale(v.val)

	def getGlyphScale(self):
		return vec3._new(self.gval.getGlyphScale())

	def setGlyphName(self,str name):
		self.gval.setGlyphName(name)

	def getGlyphName(self):
		return self.gval.getGlyphName()

	def addGlyphMesh(self,str name,Vec3Matrix nodes,Vec3Matrix norms, IndexMatrix inds):
		self.gval.addGlyphMesh(name,nodes.mat,norms.mat,inds.mat)
		
		
cdef class RibbonFigure(Figure):
	cdef iRibbonFigure* rval

	@staticmethod
	cdef _new(iRibbonFigure* val):
		cdef RibbonFigure v=RibbonFigure()
		v.val=val
		v.rval=val
		return v
		
	def setOrientation(self,vec3 orient):
		self.rval.setOrientation(orient.val)
		
	def isCameraOriented(self):
		return self.rval.isCameraOriented()
		
	def getOrientation(self):
		return vec3._new(self.rval.getOrientation()) 
	
	def setNumRibbons(self,sval num):
		self.rval.setNumRibbons(num)
		
	def numRibbons(self):
		return self.rval.numRibbons()
		
	def numNodes(self,sval ribbon):
		return self.rval.numNodes(ribbon)
		
	def setMaxNodes(self,sval num):
		self.rval.setMaxNodes(num)
		
	def getMaxNodes(self):
		return self.rval.getMaxNodes()
				
	def clearRibbons(self):
		self.rval.clearRibbons()
		
	def removeRibbon(self,sval ribbon):
		self.rval.removeRibbon(ribbon)
		
	def removeNode(self,sval ribbon):
		self.rval.removeNode(ribbon)
		
	def addNode(self,sval ribbon,vec3 pos,color col,real width,rotator rot=rotator(),real tex=0.0):
		self.rval.addNode(ribbon,pos.val,col.val,width,rot.val,tex)
		
	def setNode(self,sval ribbon,sval node,vec3 pos,color col,real width,rotator rot=rotator(), real tex=0.0):
		self.rval.setNode(ribbon,node,pos.val,col.val,width,rot.val,tex)
		
	def getNode(self,sval ribbon,sval node):
		return vec3._new(self.rval.getNode(ribbon,node))
		
	def getNodeProps(self,sval ribbon,sval node):
		cdef RenderTypes.quadruple[icolor,real,irotator,real] r=self.rval.getNodeProps(ribbon,node)
		return (color._new(r.first),r.second,rotator._new(r.third),r.fourth)


cdef class TextFigure(Figure):
	cdef iTextFigure* tval
	
	@staticmethod
	cdef _new(iTextFigure* val):
		cdef TextFigure v=TextFigure()
		v.val=val
		v.tval=val
		return v
		
	def setText(self,str text):
		self.tval.setText(text)
		
	def setFont(self,str fontname):
		self.tval.setFont(fontname)
		
	def setColor(self, color col):
		self.tval.setColor(col.val)
	
	def setVAlign(self,VAlignType align):
		self.tval.setVAlign(align)
		
	def setHAlign(self,HAlignType align):
		self.tval.setHAlign(align)
		
	def setTextHeight(self,float height):
		self.tval.setTextHeight(height)
		
	def setSpaceWidth(self,float width):
		self.tval.setSpaceWidth(width)
	
	def getText(self):
		return self.tval.getText()
		
	def getFont(self):
		return self.tval.getFont()
		
	def getColor(self):
		return color._new(self.tval.getColor())
	
	def getVAlign(self):
		return self.tval.getVAlign()
		
	def getHAlign(self):
		return self.tval.getHAlign()
		
	def getTextHeight(self):
		return self.tval.getTextHeight()
		
	def getSpaceWidth(self):
		return self.tval.getSpaceWidth()
		

cdef class Texture:
	cdef iTexture* val

	@staticmethod
	cdef _new(iTexture* val):
		cdef Texture v=Texture()
		v.val=val
		return v

	def __dealloc__(self):
		del self.val

	def getName(self):
		return self.val.getName()

	def getFilename(self):
		return self.val.getFilename()

	def getWidth(self):
		return self.val.getWidth()

	def getHeight(self):
		return self.val.getHeight()

	def getDepth(self):
		return self.val.getDepth()

	def hasAlpha(self):
		return self.val.hasAlpha()

	def getFormat(self):
		return self.val.getFormat()

	def fillBlack(self):
		self.val.fillBlack()

	def fillColor(self,col_mat,indexval depth=0,real minval=0.0,real maxval=1.0, Material colormat=None, RealMatrix alphamat=None,bint mulAlpha=True):
		if isinstance(col_mat,color):
			self.val.fillColor((<color>col_mat).val)
		elif isinstance(col_mat,ColorMatrix):
			self.val.fillColor((<ColorMatrix>col_mat).mat,depth)
		else:
			self.val.fillColor((<RealMatrix>col_mat).mat,depth,minval,maxval,colormat.mval if colormat!=None else <iMaterial*>NULL,alphamat.mat if alphamat!=None else <iRealMatrix*>NULL,mulAlpha)


cdef class GPUProgram:
	cdef iGPUProgram* val

	@staticmethod
	cdef _new(iGPUProgram* val):
		cdef GPUProgram v=GPUProgram()
		v.val=val
		return v

	def __dealloc__(self):
		del self.val

	def getName(self):
		return self.val.getName()

	def setType(self,ProgramType pt):
		self.val.setType(pt)

	def getType(self):
		return self.val.getType()

	def getLanguage(self):
		return self.val.getLanguage()

	def setLanguage(self,str lang):
		self.val.setLanguage(lang)

	def setSourceCode(self,str code):
		self.val.setSourceCode(code)

	def hasError(self):
		return self.val.hasError()

	def getSourceCode(self):
		return self.val.getSourceCode()

	def setParameter(self,str param, str val):
		self.val.setParameter(param,val)

	def getParameter(self,str param):
		return self.val.getParameter(param)

	def getEntryPoint(self):
		return self.val.getEntryPoint()

	def getProfiles(self):
		return self.val.getProfiles()

	def getParameterNames(self):
		return self.val.getParameterNames()

	def setEntryPoint(self,str main):
		self.val.setEntryPoint(main)

	def setProfiles(self,str profiles):
		self.val.setProfiles(profiles)


cdef class RenderScene:
	cdef iRenderScene* val

	def __dealloc__(self):
		del self.val

	def createCamera(self,str name,real left=0.0,real top=0.0,real width=1.0,real height=1.0):
		return Camera._new(self.val.createCamera(name,left,top,width,height))

	def setAmbientLight(self,color c):
		self.val.setAmbientLight(c.val)

	def addResourceDir(self,str rdir):
		self.val.addResourceDir(rdir)
		
	def initializeResources(self):
		self.val.initializeResources()

	def createMaterial(self,str name):
		return Material._new(self.val.createMaterial(name))

	def createFigure(self,str name, str mat,FigureType ftype):
		cdef iFigure* f=self.val.createFigure(name,mat,ftype)
		if ftype in (FT_BB_POINT,FT_BB_FIXED_PAR,FT_BB_FIXED_PERP):
			return BBSetFigure._new(<iBBSetFigure*>f)
		elif ftype==FT_GLYPH:
			return GlyphFigure._new(<iGlyphFigure*>f)
		elif ftype==FT_RIBBON:
			return RibbonFigure._new(<iRibbonFigure*>f)
		elif ftype==FT_TEXVOLUME:
			return TextureVolumeFigure._new(<iTextureVolumeFigure*>f)
		elif ftype==FT_TEXT:
			return TextFigure._new(<iTextFigure*>f)
		else:
			return Figure._new(f)

	def createLight(self):
		return Light._new(self.val.createLight())

	def loadImageFile(self,str filename):
		return Image._new(self.val.loadImageFile(filename))

	def loadTextureFile(self,str name,str absFilename):
		return Texture._new(self.val.loadTextureFile(name,absFilename))

	def createTexture(self,str name,sval width, sval height, sval depth, TextureFormat tformat):
		return Texture._new(self.val.createTexture(name,width,height,depth,tformat))

	def createGPUProgram(self,str name,ProgramType ptype,str language):
		return GPUProgram._new(self.val.createGPUProgram(name,ptype,language))

	def saveScreenshot(self,str filename,Camera c=None,int width=0,int height=0,real stereoOffset=0.0,TextureFormat tf=TF_RGB24):
		self.val.saveScreenshot(filename,c.val,width,height,stereoOffset,tf)

	def getConfig(self):
		cdef Config c=Config()
		c.val=deref(self.val.getConfig())
		return c

	def logMessage(self,str msg):
		self.val.logMessage(msg)

	def setBGObject(self,color col,bint enabled):
		self.val.setBGObject(col.val,enabled)

	def setRenderHighQuality(self,bint val):
		self.val.setRenderHighQuality(val)

	def getRenderHighQuality(self):
		return self.val.getRenderHighQuality()

	def setAlwaysHighQuality(self,bint val):
		self.val.setAlwaysHighQuality(val)

	def getAlwaysHighQuality(self):
		return self.val.getAlwaysHighQuality()


cdef class RenderAdapter:
	cdef iRenderAdapter* val

	def __dealloc__(self):
		del self.val

	def createWindow(self,int width, int height):
		return self.val.createWindow(width,height)

	def paint(self):
		self.val.paint()

	def resize(self,int x, int y,int width, int height):
		self.val.resize(x,y,width,height)

	def getRenderScene(self):
		cdef RenderScene r=RenderScene()
		r.val=self.val.getRenderScene()
		return r


def getRenderAdapter(Config config):
	cdef RenderAdapter r=RenderAdapter()
	r.val=RenderTypes.getRenderAdapter(&config.val)
	return r


def basis_Tet1NL(real xi0, real xi1, real xi2):
	cdef real coeffs[4]
	RenderTypes.basis_Tet1NL(xi0,xi1,xi2,coeffs)
	return tuple(coeffs[i] for i in range(4))


def basis_Hex1NL(real xi0, real xi1, real xi2):
	cdef real coeffs[8]
	RenderTypes.basis_Hex1NL(xi0,xi1,xi2,coeffs)
	return tuple(coeffs[i] for i in range(8))


def basis_n_NURBS(sval ctrlpt,sval degree, real xi, RealMatrix knots):
	return RenderTypes.basis_n_NURBS(ctrlpt,degree,xi,knots.mat)


def basis_NURBS_default(real u, real v, real w,sval ul, sval vl, sval wl, sval udegree, sval vdegree, sval wdegree):
	cdef sval clen=ul*vl*wl
	cdef array.array coeffs=array.array('d',[0]*clen)
	RenderTypes.basis_NURBS_default(u,v,w,ul,vl,wl,udegree,vdegree,wdegree,coeffs.data.as_doubles)
	return coeffs.tolist()


def pointInTet(vec3 pt, vec3 n1, vec3 n2, vec3 n3, vec3 n4):
	return RenderTypes.pointInTet(pt.val,n1.val,n2.val,n3.val,n4.val)


def pointInHex(vec3 pt, vec3 n1, vec3 n2, vec3 n3, vec3 n4, vec3 n5, vec3 n6, vec3 n7, vec3 n8):
	return RenderTypes.pointInHex(pt.val,n1.val,n2.val,n3.val,n4.val,n5.val,n6.val,n7.val,n8.val)


def pointSearchLinTet(vec3 pt, vec3 n1, vec3 n2, vec3 n3, vec3 n4):
	return vec3._new(RenderTypes.pointSearchLinTet(pt.val,n1.val,n2.val,n3.val,n4.val))


def pointSearchLinHex(vec3 pt, vec3 n1, vec3 n2, vec3 n3, vec3 n4, vec3 n5, vec3 n6, vec3 n7, vec3 n8):
	return vec3._new(RenderTypes.pointSearchLinHex(pt.val,n1.val,n2.val,n3.val,n4.val,n5.val,n6.val,n7.val,n8.val))


def calculateTetVolume(vec3 a, vec3 b, vec3 c, vec3 d):
	return RenderTypes.calculateTetVolume(a.val,b.val,c.val,d.val)


def calculateBoundBox(Vec3Matrix mat):
	cdef pair[ivec3,ivec3] r=RenderTypes.calculateBoundBox(mat.mat)
	return (vec3._new(r.first),vec3._new(r.second))


def calculateBoundSquare(object mat, real threshold):
	cdef RenderTypes.quadruple[int,int,int,int] result

	if isinstance(mat,RealMatrix):
		result=RenderTypes.calculateBoundSquare((<RealMatrix>mat).mat,threshold)
	elif isinstance(mat,IndexMatrix):
		result=RenderTypes.calculateBoundSquare((<IndexMatrix>mat).mat,<indexval>threshold)
	else:
		raise ValueError,"Argument `mat' must be RealMatrix or IndexMatrix"

	if result.first<0:
		return None
	else:
		return (result.first,result.second,result.third,result.fourth)


def findBoundaryPoints(RealMatrix mat, real threshold):
	cdef vector[ivec3] r= RenderTypes.findBoundaryPoints[real](mat.mat,threshold)
	return [vec3._new(r[i]) for i in range(r.size())]


def countValuesInRange(RealMatrix mat, real minv, real maxv):
	return RenderTypes.countValuesInRange(mat.mat,minv,maxv)


def sumMatrix(RealMatrix mat):
	return RenderTypes.sumMatrix(mat.mat)


def minmaxMatrixReal(RealMatrix mat):
	return RenderTypes.minmaxMatrix[real](mat.mat)

def minmaxMatrixIndex(IndexMatrix mat):
	return RenderTypes.minmaxMatrix[indexval](mat.mat)


def trilerpMatrices(RealMatrix mat1, RealMatrix mat2, vec3 v1, vec3 v2):
	return RenderTypes.trilerpMatrices(mat1.mat,mat2.mat,v1.val,v2.val)


def getPlaneXi(vec3 pos, vec3 planepos, rotator orientinv, vec3 dimvec):
	return vec3._new(RenderTypes.getPlaneXi(pos.val,planepos.val,orientinv.val,dimvec.val))


def interpolateImageStack(list stack,transform stacktransinv,RealMatrix out,transform outtrans):
	cdef vector[iRealMatrix*] cstack
	for i in stack:
		cstack.push_back((<RealMatrix?>i).mat)

	RenderTypes.interpolateImageStack(cstack,stacktransinv.val,out.mat,outtrans.val)


def getImageStackValue(list stack,vec3 pos):
	cdef vector[iRealMatrix*] cstack
	for i in stack:
		cstack.push_back((<RealMatrix?>i).mat)

	return RenderTypes.getImageStackValue(cstack,pos.val)


def calculateImageHistogram(RealMatrix img, RealMatrix hist, i32 minv):
	return RenderTypes.calculateImageHistogram(img.mat,hist.mat,minv)


def calculateTriPlaneSlice(vec3 planept, vec3 planenorm, vec3 a, vec3 b, vec3 c):
	cdef realtriple rp=RenderTypes.calculateTriPlaneSlice(planept.val,planenorm.val,a.val,b.val,c.val)
	return (rp.first,rp.second,rp.third)


def calculateLinePlaneSlice(vec3 planept, vec3 planenorm, vec3 a, vec3 b):
	return RenderTypes.calculateLinePlaneSlice(planept.val,planenorm.val,a.val,b.val)


def calculateTetValueIntersects(real val, real a, real b, real c, real d):
	cdef real vals[6]
	RenderTypes.calculateTetValueIntersects(val,a,b,c,d,vals)
	return tuple(vals[i] for i in range(6))


def calculateHexValueIntersects(real val,real a, real b, real c, real d, real e, real f,real g,real h):
	cdef real vals[8]
	vals[0]=a
	vals[1]=b
	vals[2]=c
	vals[3]=d
	vals[4]=e
	vals[5]=f
	vals[6]=g
	vals[7]=h

	cdef intersect intersects[6]
	cdef sval result=RenderTypes.calculateHexValueIntersects(val,vals,intersects)
	return tuple((intersects[i].first,intersects[i].second,intersects[i].third) for i in range(result))

