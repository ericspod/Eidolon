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


from eidolon import *
from eidolon.VisualizerUI import addCustomUIRow

from ui.SliceObjProp import Ui_SliceObjProp

sliceObjMatName='SliceObj'


BoxModes=enum('Inside','Outside')

PlaneModes=enum('Below Plane','Above Plane','On Plane','Orthogonal Planes')

ParamNames=enum('planept','planenorm','planeright','planemode','v0','v1','v2','v3','v4','v7','boxmode')


def sliceTriangle(slicevals,verts,indices,cols,startindex):
	'''
	Given a triangle defined by the given 3 vertices (tuples of vec3 values, first being the coordinate) in list `verts'
	whose distances from the slice plane are given in list `slicevals', whose indices in a topology are `indices' and
	whose colours are `cols', this yields 2 new vertices followed by 2 new colours and finally a list of index triples
	defining new triangles. The indices start from `startindex' and go up, thus they can be added to a topology whose
	largest index is `startindex'-1.
	'''
	a,b,c=getSliceTriOrdering(*slicevals)
	numbelow=sum(1 if s<0 else 0 for s in slicevals)

	# sort the vertices so that the first is the lone vertex above or below the plane, then transpose so each element is the collected vertex components
	verts=transpose([verts[i] for i in (a,b,c)])

	if numbelow==1: # first vertex below the plane
		coeffs1=(1.0+slicevals[a],-slicevals[a],0)
		coeffs2=(slicevals[c],0,1.0-slicevals[c])

		vert1=[mulsum(v,coeffs1) for v in verts]
		vert2=[mulsum(v,coeffs2) for v in verts]

		col1=cols[a].interpolate(-slicevals[a],cols[b])
		col2=cols[a].interpolate(1.0-slicevals[c],cols[c])

		newindices=[(indices[a],startindex,startindex+1)]
	else: # first vertex above plane
		coeffs1=(-slicevals[c],0,1.0+slicevals[c])
		coeffs2=(1.0-slicevals[a],slicevals[a],0)

		vert1=[mulsum(v,coeffs1) for v in verts]
		vert2=[mulsum(v,coeffs2) for v in verts]

		col1=cols[c].interpolate(-slicevals[c],cols[a])
		col2=cols[b].interpolate(1.0-slicevals[a],cols[a])

		newindices=[(indices[c],startindex,startindex+1),(indices[c],startindex+1,indices[b])]

	return vert1,vert2,col1,col2,newindices


@concurrent
def planeSliceFilterRange(process,origtrans,planept,planenorm, nodes,nodeprops, nodecolors,indices,extinds,reprtype):
	'''
	Filter out elements in `indices' above the plane (planept,planenorm). For lines and triangles, generate new indices
	and nodes for the bisection of those elements sliced by the plane.
	'''

	def iterateElemsExt(values,indextable):
		if indextable!=None:
			for i in xrange(process.index,indextable.n(),process.total):
				yield indextable.getAt(i)
		else:
			for i in xrange(process.index,values.n(),process.total):
				yield i

	selectedindices=IndexMatrix(nodes.getName()+'selectedindices'+str(process.index),0,1)
	newnodes=Vec3Matrix(nodes.getName()+'newnodes'+str(process.index),0,nodes.m())
	newnodecols=ColorMatrix(nodes.getName()+'newnodecols'+str(process.index),0,1)
	newnodeprops=IndexMatrix(nodes.getName()+'newnodeprops'+str(process.index),0,3)

	newtriindices=None
	newlineindices=None
	count=0
	planenorm=planenorm.norm()

	if reprtype[3]: # point type
		for i in iterateElemsExt(nodes,extinds):

			node=origtrans*nodes.getAt(i)
			if node.planeDist(planept,planenorm)<=0:
				selectedindices.append(i)

			count+=1
			process.setProgress(count)
	elif not reprtype[3] and not reprtype[4]: # 1D lines only, cylinders treated like polygons
		newlineindices=IndexMatrix(nodes.getName()+'newlineindices'+str(process.index),0,2)

		for i in iterateElemsExt(indices,extinds):
			inds=indices.getRow(i)
			iverts=[nodes.getRow(ii) for ii in inds]
			cols=[nodecolors.getAt(ii) for ii in inds]
			pts=[iv[0] for iv in iverts]
			proprow=nodeprops.getRow(inds[0])

			slicevals=[(origtrans*p).planeDist(planept,planenorm) for p in pts] # transform each point into world space


			if all(sv<=0 for sv in slicevals): # entirely below plane, add
				selectedindices.append(i)
			elif not all(sv>0 for sv in slicevals): # bisected by plane
				distsums=sum(abs(s) for s in slicevals)
				coeff=abs(slicevals[1])/distsums


				vert=[v1*coeff+v2*(1.0-coeff) for v1,v2 in zip(iverts[0],iverts[1])]
				col=cols[0].interpolate(coeff,cols[1])

				newlineindices.append(inds[0] if slicevals[0]<0 else inds[1],nodes.n()+newnodes.n())
				newnodes.append(*vert)
				newnodeprops.append(*proprow)
				newnodecols.append(col)
	else:
		newtriindices=IndexMatrix(nodes.getName()+'newtriindices'+str(process.index),0,3)

		for i in iterateElemsExt(indices,extinds):
			inds=indices.getRow(i)
			iverts=[nodes.getRow(ii) for ii in inds]
			proprow=nodeprops.getRow(inds[0])

			cols=nodecolors.mapIndexRow(indices,i)
			pts=[(origtrans*iv[0]) for iv in iverts] # transform points into world space

			barydist=avg(pts,vec3()).planeDist(planept,planenorm)

			slicevals=calculateTriPlaneSlice(planept,planenorm,*pts)

			if all(sv==0 for sv in slicevals) and barydist>0: # entirely above, ignore
				continue
			if all(sv<=0 for sv in slicevals): # entirely below plane, add
				selectedindices.append(i)
			elif not all(sv>0 for sv in slicevals): # bisected by plane
				v1,v2,c1,c2,newindices=sliceTriangle(slicevals,iverts,inds,cols,nodes.n()+newnodes.n())

				newnodes.append(*v1)
				newnodes.append(*v2)

				newnodeprops.append(*proprow)
				newnodeprops.append(*proprow)

				assert c1,repr((v1,v2,c1,c2))
				assert c2
				newnodecols.append(c1)
				newnodecols.append(c2)

				for ni in newindices:
					newtriindices.append(*ni)

			count+=1
			process.setProgress(count)

	if selectedindices.n()>0:
		selectedindices.setShared(True)
	else:
		selectedindices=None

	if newnodes.n()>0:
		return shareMatrices(selectedindices,newnodes,newnodeprops,newnodecols,newtriindices,newlineindices)
	else:
		return selectedindices,None,None,None,None,None


class PlaneSliceFilter(ModifierBase):
	'''
	Slices geometry on a defined plane, replacing elements with their slice equivalents where the intersect the plane
	and removing those entirely above it.
	'''
	def __init__(self,planept,planenorm):
		self.planept=planept
		self.planenorm=planenorm

	def _transformPlane(self,trans):
		r=trans*Ray(self.planept,self.planenorm)
		return r.getPosition(),r.getDirection()

	def applyMeshMod(self,nodes,norms,inds,colors,uvws,trans):
		width=len(inds[0]) if inds!=None else 0

		planept,planenorm=self._transformPlane(trans)

		newindices=[] # keep the new indices list separate so that the modifier is not applied to them

		if width==3: # triangles
			ind=0
			while ind<len(inds):
				tri=inds[ind]
				trinodes=[nodes[i] for i in tri]

				slicevals=calculateTriPlaneSlice(planept,planenorm,*trinodes)

				barydist=avg(trinodes,vec3()).planeDist(planept,planenorm)

				if all(sv==0 for sv in slicevals) and barydist>0:
					inds.pop(ind) # remove triangle, above slice plane
					ind-=1

				elif any(sv<=0 for sv in slicevals) and any(sv>0 for sv in slicevals):
					tricols=[colors[i] for i in tri] if colors else [color()]*3
					trinorms=[norms[i] for i in tri] if norms else [vec3(0,0,1)]*3
					triuvws=[uvws[i] for i in tri] if uvws else [vec3()]*3

					verts=transpose([trinodes,trinorms,triuvws])

					v1,v2,c1,c2,newinds=sliceTriangle(slicevals,verts,tri,tricols,len(nodes))

					inds[ind]=newinds[0] # replace this triangle with a sliced one

					if len(newinds)>1: # if a second triangle is needed to define the slice, add this one to the new indices list
						newindices.append(newinds[1])

					# 2 new nodes are created for each sliced triangle, add these to the node list
					nodes+=[v1[0],v2[0]]
					if norms!=None:
						norms+=[v1[1],v2[1]]

					if uvws!=None:
						uvws+=[v1[2],v2[2]]

					if colors!=None:
						colors+=[c1,c2]

				ind+=1

		else:
			pass # TODO: other geometries

		return nodes,norms,inds+newindices,colors,uvws

	@timing
	def applyDatasetMod(self,rep,dataset,nodecolors,indices,selectedinds, reprtype,modinds):
		planept,planenorm=self.planept,self.planenorm  #self._transformPlane(rep.getTransform(True).inverse())
		nodes=dataset.getNodes()
		nodeprops=dataset.getIndexSet(dataset.getName()+MatrixType.props[1])

		if selectedinds!=None:
			elemcount=selectedinds.n()
		elif indices!=None:
			elemcount=indices.n()
		else:
			elemcount=nodes.n()

		proccount=chooseProcCount(elemcount,1,1000)

		if proccount!=1:
			shareMatrices(nodes,nodeprops,nodecolors,indices,selectedinds)

		result= planeSliceFilterRange(elemcount,proccount,None,rep.getTransform(True),planept,planenorm,nodes,nodeprops,nodecolors,indices,selectedinds,reprtype)

		unshareMatrices(nodes,nodeprops,nodecolors,indices,selectedinds)

		oldnoden=nodes.n()
		newnodecount=0

		for selectedindices,newnodes,newnodeprops,newnodecols,newtriindices,newlineindices in result.values():
			if selectedindices!=None:
				modinds.append(selectedindices)

			indlen=indices.n() if indices!=None else 0

			if newnodes!=None:
				if newtriindices!=None:
					for n in xrange(newtriindices.n()):
						modinds.append(n+indlen)

						a,b,c=newtriindices.getRow(n)
						if a>=oldnoden:
							a+=newnodecount
						if b>=oldnoden:
							b+=newnodecount
						if c>=oldnoden:
							c+=newnodecount

						if indices!=None:
							indices.append(a,b,c)

				elif newlineindices!=None:
					for n in xrange(newlineindices.n()):
						modinds.append(n+indlen)

						a,b=newlineindices.getRow(n)
						if a>=oldnoden:
							a+=newnodecount
						if b>=oldnoden:
							b+=newnodecount

						if indices!=None:
							indices.append(a,b)

				nodes.append(newnodes)
				nodeprops.append(newnodeprops)

				newnodecount+=newnodes.n()
				nodecolors.append(newnodecols)


class IsoplaneModifier(ModifierBase):
	'''
	Generates an isoplane where a mesh intersects the defined plane.
	'''
	def __init__(self,planept,planenorm):
		self.planept=planept
		self.planenorm=planenorm

	def _transformPlane(self,trans):
		r=trans*Ray(self.planept,self.planenorm)
		return r.getPosition(),r.getDirection()

	@timing
	def applyDatasetMod(self,rep,dataset,nodecolors,indices,selectedinds, reprtype,modinds):
		ModifierBase.applyDatasetMod(self,rep,dataset,nodecolors,indices,selectedinds, reprtype,modinds)
		if not isinstance(rep,MeshSceneObjectRepr) or rep.tris==None or rep.parentdataset==None:
			return

		rot=rotator(*rep.getRotation(True)).inverse()
		pos=rep.getPosition(True)

		planeds,selindices=generateIsoplaneDataSet(rep.parentdataset,rep.getName()+'DS',rep.refine,self.planept-pos,rot*self.planenorm)

		newnodes=planeds.getNodes()
		inds=planeds.getIndexSet(planeds.getName()+MatrixType.tris[1])

		if newnodes!=None and newnodes.n()>0 and inds!=None:
			nodes=dataset.getNodes()
			nodeprops=dataset.getIndexSet(dataset.getName()+MatrixType.props[1])
			unshareMatrices(nodes,nodeprops,indices,nodecolors)

			for n in xrange(inds.n()):
				modinds.append(indices.n()+n)

			newnodeprops=planeds.getIndexSet(planeds.getName()+MatrixType.props[1])

			inds.add(nodes.n())
			indices.append(inds)

			#printFlush(nodes,nodeprops,newnodes,newnodeprops)
			nodes.append(newnodes)
			nodeprops.append(newnodeprops)

			# create a proxy representation used to generate the colouration for the isoplane
			fakerep=MeshSceneObjectRepr(rep.parent,ReprType._volume,0,rep.refine,(planeds,selindices),rep.parentdataset,True,True,rep.matname)
			fakerep.setDataFuncs(**rep.getDataFuncMap())
			fakerep.applyMaterial(rep.matname,field=rep.getDataField(),minfield=rep.selminfield,maxfield=rep.selmaxfield)
			nodecolors.append(fakerep.nodecolors)


class SlicePropertyWidget(QtGui.QWidget,Ui_SliceObjProp):
	def __init__(self, parent=None):
		QtGui.QWidget.__init__(self,parent)
		self.setupUi(self)


class SliceObject(SceneObject):
	def __init__(self,name,mgr,plugin):
		SceneObject.__init__(self,name,plugin)
		self.mgr=mgr
		self.slicedReprs=[] # list of names of SceneObjectRepr objects this plane slices through
		self.slicepos=vec3()
		self.slicerot=(0,0,0)

	def getPropTuples(self):
		return []

	def isSlicingRepr(self,rep):
		return rep.getName() in self.slicedReprs

	def getSlicedReprNames(self):
		return list(self.slicedReprs)

	def setApplyToRepr(self,rep,doApply=True):
		pass

	def update(self):
		pass

	def getAABB(self,isTransformed=False,isDerived=True):
		aabbs=[]
		for r in self.mgr.enumSceneObjectReprs():
			if r.getName() in self.slicedReprs:
				aabbs.append(r.getAABB(isTransformed,isDerived))

		if len(aabbs)==0:
			for r in self.mgr.enumSceneObjectReprs():
				if r.parent is not self and not isinstance(r.parent,SliceObject):
					aabbs.append(r.getAABB(isTransformed,isDerived))

		return BoundBox.union(aabbs)

	def setPosition(self,pos):
		self.slicepos=pos

	def getPosition(self):
		return self.slicepos

	def setRotation(self,yaw,pitch,roll):
		self.slicerot=(yaw,pitch,roll)

	def getRotation(self):
		return self.slicerot

	def removeRepr(self,rep):
		SceneObject.removeRepr(self,rep)

		# if we're removing the last repr (ie. when removing this object), un-apply the slicing to all repr objects
		if len(self.reprs)==0:
			sliced=self.getSlicedReprNames()
			for r in self.mgr.enumSceneObjectReprs():
				if r!=rep and r.getName() in sliced:
					self.setApplyToRepr(r,False)


class SliceRepr(SceneObjectRepr):
	def __init__(self,parent,reprtype,reprcount,matname):
		SceneObjectRepr.__init__(self,parent,reprtype,reprcount,matname)

	def getPropTuples(self):
		return []

	def setPosition(self,pos):
		self.parent.setPosition(pos)

	def getPosition(self,isDerived=False):
		return self.parent.getPosition()

	def setRotation(self,yaw,pitch,roll):
		yaw=radCircularConvert(yaw)
		pitch=radCircularConvert(pitch)
		roll=radCircularConvert(roll)
		self.parent.setRotation(yaw,pitch,roll)

	def getRotation(self,isDerived=False):
		return self.parent.getRotation()

	def getScale(self,isDerived=False):
		return vec3(1)

	def setTransforms(self):
		pass


class SliceBox(SliceObject):
	def __init__(self,name,mgr,plugin,center,dim,rot):
		SliceObject.__init__(self,name,mgr,plugin)
		self.label='SliceBox <'+name+'>'
		self.slicepos=center
		self.slicescale=vec3(1)
		self.initslicedim=dim
		self.slicerot=rot
		self.isInside=True

	def getPropTuples(self):
		return [
			('Center',str(self.slicepos)),
			('dimx',str(self.slicescale.x())),
			('dimy',str(self.slicescale.y())),
			('dimz',str(self.slicescale.z())),
		]

	def getReprTypes(self):
		return [ReprType._line]

	def isSlicingRepr(self,rep):
		return rep.getName() in self.slicedReprs

	@timing
	def setApplyToRepr(self,rep,doApply=True):
		name=rep.getName()

		if doApply:
			if name not in self.slicedReprs:
				self.slicedReprs.append(name)

			if(self.initslicedim.len()==0):
				aabb=self.plugin.mgr.getSceneAABB()
				self.initslicedim=(aabb.maxv-aabb.center).abs()*0.5
				self.initslicedim.setMaxVals(vec3(0.1))
		else:
			if name in self.slicedReprs:
				self.slicedReprs.remove(name)

		self.updateGPUParams(rep,not doApply)

	def getSlicedReprNames(self):
		return list(self.slicedReprs)

	@timing
	def update(self):
		self.updateReprList()
		self.updateBoxes()

	def updateBoxes(self):
		for rep in self.reprs:
			rep.setTransforms()

		for r in self.mgr.enumSceneObjectReprs():
			if r.getName() in self.slicedReprs:
				self.updateGPUParams(r)

	def updateGPUParams(self,rep,resetVals=False):
		if hasattr(rep,'setGPUParam'):
			if resetVals:
				v0=vec3()
				v1=vec3()
				v2=vec3()
				v3=vec3()
				v4=vec3()
				v7=vec3()
			else:
				pos=self.slicepos
				rot=rotator(*self.getRotation())
				scale=self.slicescale*self.initslicedim
				v0=pos+rot*(scale*vec3(-1,-1,-1))
				v1=pos+rot*(scale*vec3(1,-1,-1))
				v2=pos+rot*(scale*vec3(-1,1,-1))
				v3=pos+rot*(scale*vec3(1,1,-1))
				v4=pos+rot*(scale*vec3(-1,-1,1))
				v7=pos+rot*(scale*vec3(1,1,1))

			rep.setGPUParam(ParamNames.v0,v0,PT_FRAGMENT,transformVec=not resetVals)
			rep.setGPUParam(ParamNames.v1,v1,PT_FRAGMENT,transformVec=not resetVals)
			rep.setGPUParam(ParamNames.v2,v2,PT_FRAGMENT,transformVec=not resetVals)
			rep.setGPUParam(ParamNames.v3,v3,PT_FRAGMENT,transformVec=not resetVals)
			rep.setGPUParam(ParamNames.v4,v4,PT_FRAGMENT,transformVec=not resetVals)
			rep.setGPUParam(ParamNames.v7,v7,PT_FRAGMENT,transformVec=not resetVals)
			rep.setGPUParam(ParamNames.boxmode,0.0 if self.isInside else 1.0,PT_FRAGMENT)

	def updateReprList(self):
		existingreprs=[r.getName() for r in self.mgr.enumSceneObjectReprs()]

		for name in self.getSlicedReprNames():
			if name not in existingreprs:
				self.slicedReprs.remove(name)

	def getAABB(self,isTransformed=False,isDerived=True):
		aabbs=[]
		for r in self.mgr.enumSceneObjectReprs():
			if r.getName() in self.slicedReprs:
				aabbs.append(r.getAABB(isTransformed,isDerived))

		return BoundBox.union(aabbs)
		
	def setInside(self,isInside):
		self.isInside=isInside
		self.updateBoxes()

	def setPosition(self,pos):
		self.slicepos=pos
		self.updateBoxes()

	def setRotation(self,yaw,pitch,roll):
		self.slicerot=(yaw,pitch,roll)
		self.updateBoxes()

	def setScale(self,slicescale):
		self.slicescale=slicescale
		self.updateBoxes()

	def getScale(self):
		return self.slicescale


class SliceBoxRepr(SliceRepr):
	def __init__(self,parent,reprtype,reprcount,matname=sliceObjMatName):
		SliceRepr.__init__(self,parent,reprtype,reprcount,matname)
		self.name='Box'+str(reprcount)
		self.label=self.name

		self.boxFig=None
		self.vbuff=None
		self.ibuff=None

	def isInScene(self):
		return self.boxFig!=None

	def getAABB(self,isTransformed=False,isDerived=True):
		return self.parent.getAABB(isTransformed,isDerived)

	def enumFigures(self):
		yield self.boxFig

	def removeFromScene(self,scene):
		self.setVisible(False)

	def applyMaterial(self,mat,**kwargs):
		self.setMaterialName(mat.getName())

	def setMaterialName(self,matname):
		if self.boxFig!=None:
			self.boxFig.setMaterial(matname)

	def setVisible(self,isVisible):
		self._isVisible=isVisible
		if self.boxFig!=None:
			self.boxFig.setVisible(isVisible)

	def setTransparent(self,isTrans):
		if self.boxFig!=None:
			self.boxFig.setTransparent(isTrans)

	def isTransparent(self):
		return self.boxFig!=None and self.boxFig.isTransparent()

	def addToScene(self,scene):
		self.boxFig=scene.createFigure(self.name+'BoxFig',self.matname,FT_LINELIST)
		self.setVisible(True)
		self.setTransparent(True)

	def prepareBuffers(self):
		nodes,inds=generateLineBox([vec3(-1),vec3(1)])
		cols=[color()]*len(nodes)
		norms=[vec3(0,0,1)]*len(nodes)
		self.vbuff=PyVertexBuffer(nodes,norms,cols)
		self.ibuff=PyIndexBuffer(inds)

	def update(self,scene):
		self.boxFig.fillData(self.vbuff,self.ibuff)
		self.setTransforms()

	def getScale(self,isDerived=False):
		return self.parent.getScale()

	def setScale(self,scale):
		minv=vec3(0.0001)
		minv.setMaxVals(scale)
		self.parent.setScale(minv)

	def setTransforms(self):
		self.boxFig.setPosition(self.parent.slicepos)
		self.boxFig.setRotation(rotator(*self.parent.getRotation()))
		self.boxFig.setScale(self.parent.getScale()*self.parent.initslicedim)


class SlicePlane(SliceObject):
	def __init__(self,name,mgr,plugin,slicepos,planenorm,planepitch,planeyaw):
		SliceObject.__init__(self,name,mgr,plugin)

		if planenorm!=None:
			planenorm=planenorm.toPolar()
			planepitch=planenorm.y()
			planeyaw=planenorm.x()+halfpi

		self.psfilter=PlaneSliceFilter(slicepos,vec3(0,0,1))
		self.isofilter=IsoplaneModifier(slicepos,vec3(0,0,1))

		self.planeShift=0.00001 # amount to move the plane point by so that sliced meshes are not exactly on the plane
		self.planeFig=None
		self.planeMat='BoundBoxes'
		self.slicepos=slicepos
		self.slicerot=(planeyaw,planepitch,0)
		self.planemode=0
		self.setPlane()

	def getLabel(self):
		return 'SlicePlane <'+self.name+'>'

	def getPropTuples(self):
		return [
			('Center',str(self.slicepos)),
			('Norm',str(self.planenorm)),
			('Yaw',str(self.slicerot[0])),
			('Pitch',str(self.slicerot[1])),
			('Roll',str(self.slicerot[2])),
		]

	def getReprTypes(self):
		return [ReprType._line]

	def setPlane(self):
		self.planenorm=(self.getPlaneRotator()*vec3.Z()).norm()
		self.planeright=(self.getPlaneRotator()*vec3.X()).norm()
		self.psfilter.planept=self.slicepos+self.planenorm*self.planeShift
		self.psfilter.planenorm=self.planenorm
		self.isofilter.planept=self.slicepos+self.planenorm*self.planeShift
		self.isofilter.planenorm=self.planenorm
		self.updatePlanes()

	def setPosition(self,pos):
		self.slicepos=pos
		self.setPlane()

	def setRotation(self,yaw,pitch,roll):
		self.slicerot=(yaw,pitch,roll)
		self.setPlane()

	def getPlaneRotator(self):
		return rotator(*self.slicerot)

	def setApplyToRepr(self,rep,doApply=True):
		name=rep.getName()
		result=None

		if doApply:
			if name not in self.slicedReprs:
				self.slicedReprs.append(name)
				self.updatePlanes()
				self.updateGPUParams(rep)
				rep.addModifier(self.psfilter)
				rep.addModifier(self.isofilter)
		else:
			if name in self.slicedReprs:
				self.slicedReprs.remove(name)
				#self.updateRepr(rep)
				self.updateGPUParams(rep,True)
				rep.removeModifier(self.psfilter)
				rep.removeModifier(self.isofilter)

		if not isinstance(rep,ImageVolumeRepr):
			self.updateRepr(rep)

		self.mgr.repaint()

		return result

	@timing
	def updateRepr(self,rep):
		self.mgr.addFuncTask(lambda:self.mgr.updateSceneObjectRepr(rep))

	@timing
	def update(self):
		self.updateReprList()
		self.updatePlanes()

		for rep in self.mgr.enumSceneObjectReprs():
			if rep.getName() in self.slicedReprs:
				self.updateRepr(rep)

	def updatePlanes(self):
		for rep in self.reprs:
			rep.setTransforms()

		for r in self.mgr.enumSceneObjectReprs():
			if r.getName() in self.slicedReprs:
				self.updateGPUParams(r)

	def updateGPUParams(self,rep,resetVals=False):
		if hasattr(rep,'setGPUParam'):
			rep.setGPUParam(ParamNames.planept,vec3() if resetVals else self.slicepos,PT_FRAGMENT,transformVec=True)
			rep.setGPUParam(ParamNames.planenorm,vec3() if resetVals else self.planenorm,PT_FRAGMENT,rotateVec=True)
			rep.setGPUParam(ParamNames.planeright,vec3() if resetVals else self.planeright,PT_FRAGMENT,rotateVec=True)
			rep.setGPUParam(ParamNames.planemode,float(self.planemode),PT_FRAGMENT)

	def updateReprList(self):
		existingreprs=[r.getName() for r in self.mgr.enumSceneObjectReprs()]

		for name in self.getSlicedReprNames():
			if name not in existingreprs:
				self.slicedReprs.remove(name)
				
	def setPlaneMode(self,planemode):
		self.planemode=clamp(planemode,0,len(PlaneModes)-1)
		self.setPlane()
		

class SlicePlaneRepr(SliceRepr):
	def __init__(self,parent,reprtype,reprcount,matname=sliceObjMatName):
		SliceRepr.__init__(self,parent,reprtype,reprcount,matname)

		self.name='Plane'+str(reprcount)
		self.label=self.name

		self.planeFig=None
		self.vbuff=None
		self.ibuff=None
		self.planescale=vec3(1)
		self.planedim=1.0

	def isInScene(self):
		return self.planeFig!=None

	def getPropTuples(self):
		return [ ('Norm',str(self.parent.planenorm)) ]

	def getAABB(self,isTransformed=False,isDerived=True):
		return self.parent.getAABB(isTransformed,isDerived)

	def enumFigures(self):
		yield self.planeFig

	def removeFromScene(self,scene):
		self.setVisible(False)

	def applyMaterial(self,mat,**kwargs):
		self.setMaterialName(mat.getName())

	def setMaterialName(self,matname):
		if self.planeFig!=None:
			self.planeFig.setMaterial(matname)

	def setVisible(self,isVisible):
		self._isVisible=isVisible
		if self.planeFig!=None:
			self.planeFig.setVisible(isVisible)

	def setTransparent(self,isTrans):
		if self.planeFig!=None:
			self.planeFig.setTransparent(isTrans)

	def isTransparent(self):
		return self.planeFig!=None and self.planeFig.isTransparent()

	def addToScene(self,scene):
		figtype=FT_LINELIST if self.reprtype==ReprType._line else FT_TRILIST
		self.planeFig=scene.createFigure(self.name+'PlaneFig',self.matname,figtype)
		self.setVisible(True)
		self.setTransparent(True)

	def prepareBuffers(self):
		nodes=[vec3(1,1,0),vec3(-1,1,0),vec3(-1,-1,0),vec3(1,-1,0)]
		norms=[vec3(0,0,1)]*len(nodes)

		if self.reprtype==ReprType._line:
			inds=[(0,1),(1,2),(2,3),(3,0)]
			cols=[color()]*len(nodes)
		else:
			inds=[(0,1,2),(0,2,3)]
			cols=[color(1,1,1,0.5)]*len(nodes)

		self.vbuff=PyVertexBuffer(nodes,norms,cols)
		self.ibuff=PyIndexBuffer(inds)

	def update(self,scene):
		self.planeFig.fillData(self.vbuff,self.ibuff)
		self.setTransforms()

	def setTransforms(self):
		aabb=self.getAABB(True)
		internalplane=None

		if not aabb.isEmpty():
			internalplane=aabb.getInternalPlane(self.parent.slicepos,self.parent.planenorm)

		if internalplane!=None:
			proj,self.planedim=internalplane

		self.planescale=vec3(self.planedim,self.planedim,0)

		self.planeFig.setPosition(self.parent.slicepos)
		self.planeFig.setRotation(self.parent.getPlaneRotator())
		self.planeFig.setScale(self.planescale)


class SlicePlugin(ScenePlugin):
	def __init__(self):
		ScenePlugin.__init__(self,'SlicePlugin')
		self.objcount=0
		self.checkboxMap={} # relates QTableWidgetItem objects to (SliceObject,SceneObjectRepr) pairs

	def init(self,plugid,win,mgr):
		ScenePlugin.init(self,plugid,win,mgr)
		if win:
			win.addMenuItem('Create','NewPlane'+str(plugid),'New Slice &Plane',self._createSlicePlaneMenu)
			win.addMenuItem('Create','NewBox'+str(plugid),'New Slice &Box',self._createSliceBoxMenu)

	def getIcon(self,obj):
		return IconName.Scissors

	def _createSliceBoxMenu(self):
		@taskroutine('Creating new slice box')
		def createSliceBoxTask(task):
			box=self.createSliceBox()
			self.mgr.addSceneObject(box)
			brep=box.createRepr(ReprType._line)
			self.mgr.addSceneObjectRepr(brep)
			self.mgr.showHandle(brep)

		self.mgr.runTasks([createSliceBoxTask()])

	def _createSlicePlaneMenu(self):
		@taskroutine('Creating new slice plane')
		def createSlicePlaneTask(task):
			plane=self.createSlicePlane()
			self.mgr.addSceneObject(plane)
			prep=plane.createRepr(ReprType._line)
			self.mgr.addSceneObjectRepr(prep)
			self.mgr.showHandle(prep)

		self.mgr.runTasks([createSlicePlaneTask()])

	def createSliceBox(self,center=None,dim=None,rot=(0,0,0)):
		if center==None or dim==None:
			aabb=self.mgr.getSceneAABB()
			center=aabb.center
			dim=(aabb.maxv-center).abs()*0.5
			dim.setMaxVals(vec3(0.1))

		self.objcount+=1
		return SliceBox('SliceBox'+str(self.objcount),self.mgr,self,center,dim,rot)

	def createSlicePlane(self,slicepos=None,planenorm=None,planepitch=0.0,planeyaw=0.0):
		if slicepos==None:
			slicepos=self.mgr.getSceneAABB().center
		self.objcount+=1
		return SlicePlane('SlicePlane'+str(self.objcount),self.mgr,self,slicepos,planenorm,planepitch,planeyaw)

	def _setApplyToReprCheck(self,item):
		if item in self.checkboxMap:
			obj,rep=self.checkboxMap[item]
			obj.setApplyToRepr(rep,item.checkState()==QtCore.Qt.Checked)
			self.mgr.repaint()

	def _alignToObj(self,obj,prop):
		alignobj=self.mgr.findObject(str(prop.alignObjBox.currentText()))
		if alignobj:
			if isinstance(alignobj,ImageSceneObjectRepr):
				t=alignobj.getDefinedTransform()
			else:
				t=alignobj.getTransform()


			obj.setPosition(t.getTranslation())
			rot=t.getRotation()
			if prop.reverseBox.isChecked():
				rot=rotator(rot*vec3(1,0,0),math.pi)*rot # flip around the rotated X axis
			obj.setRotation(*rot.getEulers())
			self.mgr.repaint()

	def updateObjPropBox(self,obj,prop):
		ScenePlugin.updateObjPropBox(self,obj,prop)

		reprs=[]
		for r in self.mgr.enumSceneObjectReprs():
			if isinstance(r,(TDMeshSceneObjectRepr,MeshSceneObjectRepr,ImageSeriesRepr,ImageVolumeRepr)):
				reprs.append(r)

		fillList(prop.alignObjBox,[r.getName() for r in reprs],prop.alignObjBox.currentIndex())

		table=prop.selTable

		for i in xrange(table.rowCount()):
			item=table.item(i,0)
			if item in self.checkboxMap:
				self.checkboxMap.pop(item)

		table.clearContents()
		table.setRowCount(len(reprs))

		table.verticalHeader().setCascadingSectionResizes(True)
		table.horizontalHeader().setCascadingSectionResizes(True)
		table.verticalHeader().setDefaultAlignment(QtCore.Qt.AlignLeft) # why doesn't this stick in the designer?
		table.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignLeft)

		for i,r in enumerate(reprs):
			chkBoxItem = QtGui.QTableWidgetItem()
			chkBoxItem.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
			chkBoxItem.setCheckState(QtCore.Qt.Checked if obj.isSlicingRepr(r) else QtCore.Qt.Unchecked)

			self.checkboxMap[chkBoxItem]=(obj,r)

			label=QtGui.QTableWidgetItem(r.getLabel())
			label.setFlags((label.flags() & ~Qt.ItemIsEditable)|Qt.ItemIsSelectable)

			table.setItem(i,0,chkBoxItem)
			table.setItem(i,1,label)

		table.resizeColumnsToContents()
		table.resizeRowsToContents()

	def createObjPropBox(self,obj):
		prop=SlicePropertyWidget()

		prop.createButton.clicked.connect(lambda:self._createReprButton(obj,prop))
		prop.updateButton.clicked.connect(lambda:self.mgr.addFuncTask(obj.update))
		prop.selTable.itemClicked.connect(self._setApplyToReprCheck)

		prop.alignObjButton.clicked.connect(lambda:self._alignToObj(obj,prop))
		
		if isinstance(obj,SliceBox):
			fillList(prop.modeBox,first(zip(*BoxModes)))
			prop.modeBox.currentIndexChanged.connect(lambda i:obj.setInside(i==0))
		else:
			fillList(prop.modeBox,first(zip(*PlaneModes)))
			prop.modeBox.currentIndexChanged.connect(obj.setPlaneMode)

		return prop

	def createReprPropBox(self,rep):
		prop=ScenePlugin.createReprPropBox(self,rep)

		updatebox = QtGui.QGroupBox(prop)
		updatebox.setTitle('ObjReprProp')
		prop.verticalLayout.insertWidget(2,updatebox)
		formLayout = QtGui.QFormLayout(updatebox)

		label,button=addCustomUIRow(formLayout,0,CustomUIType._button,'updateButton','Update')
		
		button.clicked.connect(lambda:self.mgr.addFuncTask(rep.parent.update))

		return prop

	def createRepr(self,obj,reprtype,refine=0,**kwargs):
		assert reprtype in (ReprType._line,ReprType._surface)

		slicemat=self.mgr.getMaterial(sliceObjMatName)
		if slicemat==None:
			slicemat=self.mgr.createMaterial(sliceObjMatName)
			slicemat.cullBackfaces(False)
			slicemat.useLighting(False)
			slicemat.useVertexColor(True)

		if isinstance(obj,SlicePlane):
			obj.reprcount+=1
			rep=SlicePlaneRepr(obj,reprtype,obj.reprcount)
			obj.reprs.append(rep)
			return rep
		elif isinstance(obj,SliceBox):
			obj.reprcount+=1
			rep=SliceBoxRepr(obj,reprtype,obj.reprcount)
			obj.reprs.append(rep)
			return rep

	def applyMaterial(self,rep,mat,**kwargs):
		useSpectrum=kwargs.get('useSpectrum',True)

		slicedrepr=rep.getReprObj()

		if isinstance(slicedrepr,TDMeshSceneObjectRepr):
			slicedrepr=slicedrepr.getTimestepRepr()

		rep.setMaterialName(mat.getName())

		@taskroutine('Apply Material')
		@timing
		def applyMaterialTask(task):
			nodes=rep.nodes
			nodeprops=rep.nodeprops
			nodecolors=rep.nodecolors
			origindices=rep.sliceselindices

			valfunc=slicedrepr.getDataFunc('valfunc',ValueFunc)
			alphafunc=slicedrepr.getDataFunc('alphafunc',UnitFunc)

			parentdataset=slicedrepr.parentdataset
			field=slicedrepr.getDataField()
			fields=[field]*len(origindices)
			minv,maxv=slicedrepr.getSelectedFieldRange()

			if field!=None and mat.numSpectrumValues()>0 and useSpectrum:
				calculateDataColoration(mat,parentdataset,nodecolors,nodes,nodeprops,origindices,fields,minv,maxv,valfunc,alphafunc,task)
			else:
				col=mat.getDiffuse()
				if mat.usesInternalAlpha():
					col=color(col.r(),col.g(),col.b(),mat.getAlpha())

				nodecolors.fill(col)

			rep.setTransparent(mat.isTransparentColor() or any(nodecolors.getAt(i).a()<1.0 for i in xrange(nodecolors.n())))

		if slicedrepr!=None and rep.nodes!=None:
			self.mgr.runTasks([applyMaterialTask()])

	def getScriptCode(self,obj,**kwargs):
		code=''
		configSection=kwargs.get('configSection',False)
		namemap=kwargs.get('namemap',{})
		varname=namemap[obj]
		pname=None if isinstance(obj,SceneObject) else namemap.get(obj.parent,"<<ERROR>>")

#		if isinstance(obj,SliceObject):
#			if configSection:
#				for i in obj.slicedReprs:
#					code+='%s.setApplyToRepr(%s)\n' %(varname,namemap.get(i,"<<ERROR>>"))

		if isinstance(obj,SliceBox):
			if configSection:
				code+='%s.setPosition(%r)\n%s.setRotation(*%r)\n%s.setScale(%r)\n'% (varname,obj.getPosition(),varname,obj.getRotation(),varname,obj.getScale())
			else:
				code+='%s = SlicePlugin.createSliceBox(%r,%r,%r)\n' %(varname,obj.getPosition(),obj.initslicedim,obj.getRotation())

		elif isinstance(obj,SliceBoxRepr):
			if not configSection:
				code+='%s = %s.createRepr(ReprType._line)\n' %(varname,pname)
			else:
				for i in obj.parent.slicedReprs:
					code+='%s.setApplyToRepr(%s)\n' %(pname,namemap.get(self.mgr.findObject(i),"<<ERROR>>"))

		elif isinstance(obj,SlicePlane):
			if configSection:
				code+='%s.setPosition(%r)\n%s.setRotation(*%r)\n'% (varname,obj.getPosition(),varname,obj.getRotation())
			else:
				code+='%s = SlicePlugin.createSlicePlane(%r,%r)\n' %(varname,obj.getPosition(),obj.planenorm)

		elif isinstance(obj,SlicePlaneRepr):
			if not configSection:
				code+='%s = %s.createRepr(ReprType._line)\n' %(varname,pname)
			else:
				for i in obj.parent.slicedReprs:
					code+='%s.setApplyToRepr(%s)\n' %(pname,namemap.get(self.mgr.findObject(i),"<<ERROR>>"))

		return code

addPlugin(SlicePlugin())

