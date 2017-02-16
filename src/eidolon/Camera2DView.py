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


from .SceneComponents import *
from .ImageObject import *
from .ImageAlgorithms import *
from .VisualizerUI import *


class BaseCamera2DWidget(Base2DWidget):
	'''
	This is the base class for all 2D drawing widgets using a camera from the renderer. It handles the update cycle of
	the camera rendering to a stream which is then fed into the image object for the widget. It provides createFigure()
	which will create Figure objects only visible to the internal camera. This class has no UI components and relies on
	inheriting subtypes calling modifyDrawWidget() to perform the correct association between the widget to draw into
	and the fillImage() method which updates the camera and copies its data over.
	'''

	defaultQuad=(
		(vec3(-0.5,0.5), vec3(0.5,0.5), vec3(-0.5,-0.5), vec3(0.5,-0.5)), # vertices
		((0, 2, 1), (1, 2, 3)), # triangle indices
		(vec3(0,0), vec3(1,0), vec3(0,1), vec3(1,1)) # xi values
	)

	standardPlanes=('XY','XZ','YZ')

	def __init__(self,mgr,camera,parent=None):
		Base2DWidget.__init__(self,parent)
		self.mgr=mgr
		self.camera=camera
		self.camera.setOrtho(True)
		self.camera.setSecondaryCamera(True)

		self.camera.setPosition(vec3(0,0,0))
		self.camera.setLookAt(vec3(0,0,-1))
		self.camera.setNearClip(epsilon*100)
		self.camera.setFarClip(100.0) # ensure the skybox is clipped out

		self.sourceName=None
		self.planeName=None
		
		self.scroll=vec3()
		self.zoom=1.0
		self.viewplane=transform() # the plane in world space corresponding to the current 2D view

		self.objFigMap={} # maps representation names to (planetrans,figs) pairs

		self.handles=[] # list of handles in this view

		self.slicewidth=0.2 # width in world units of 2D slices
		self.linewidth=1.0 # width in world units of mesh lines
		self.planeShift=0.00005 # amount to move slice position down by in world units so that slice planes don't cut out the image where we want to see it

		self.sceneBB=BoundBox(BaseCamera2DWidget.defaultQuad[0])

		self.indicatorMaterial=self.mgr.getMaterial('Indicator') or self.mgr.createMaterial('Indicator')
		self.indicatorMaterial.setDiffuse(color(1,1,1,1))
		self.indicatorMaterial.useLighting(False)

		self.indicatorTrans=transform()
		self.indicatorPlane=self.createFigure('PlaneIndicator%i'%id(self),FT_TRILIST,False)
		self.indicatorPlane.setMaterial(self.indicatorMaterial)
		self.indicatorPlane.setTransparent(True)
		self.indicatorPlane.setVisible(False)
		
		self.indicatorVisible=True

		# construct a quad with a cylinder rim for the indicator plane
		q=BaseCamera2DWidget.defaultQuad[0]
		mq=(q[0]+q[1])*0.5
		cnodes,cinds=generateCylinder([mq,q[1],q[3],q[2],q[0],mq],[0.0025]*6,1,4,False)
		nodes=list(BaseCamera2DWidget.defaultQuad[0])+cnodes
		inds=list(BaseCamera2DWidget.defaultQuad[1])+cinds
		self.indicatorPlane.fillData(PyVertexBuffer(nodes,[vec3(0,0,1)]*len(nodes),[color(1,1,1,0.5)]*len(nodes)),PyIndexBuffer(inds),False,True)
		
		delayedMethodWeak(self,'_repaintDelay') #delay method for repainting allows safe calling multiple times and from task threads

		mgr.addEventHandler(EventType._widgetPreDraw,self._repaintDelay)
		
	def _repaintDelay(self):
		self.mgr.callThreadSafe(self.repaint)

	@delayedcall(0.5) # only need/want 1 delay thread for repainting the 3D scene, don't want to do this often
	def _repaint3DDelay(self):
		self.mgr.callThreadSafe(self.mgr.repaint)
	
	def getImageStackPosition(self):
		'''Get the index in the image stack of the source object.'''
		return 0
	
	def getImageStackMax(self):
		'''Get the maximum stack index.'''
		return 0
		
	def getSecondaryNames(self):
		return []
		
	def getObjectNames(self):
		return [self.sourceName]+list(self.getSecondaryNames())
	
	def getImageXiPosition(self):
		'''Get the xi value on the unit interval representing Z position within the stack the current view represents.'''
		maxv=self.getImageStackMax()
		return 0 if maxv==0 else self.getImageStackPosition()/float(maxv)

	def mousePress(self,e):
		# check for handle selection
		if e.buttons()==Qt.LeftButton:
			selected=None
			for h in self.handles:
				if h.checkSelected(vec3(e.x(),e.y())):
					selected=selected or h
					
			# if a handle was selected, call the notice method and set all other handles to be inactive
			if selected:
				self.handleSelected(selected)
				for h in self.handles:
					h.setActive(h==selected)
					
				self._repaintDelay()
		else:
			for h in self.handles:
				h.setSelected(False)

		# reset view
		if e.buttons()==Qt.MiddleButton:
			self.scroll=vec3()
			self.zoom=1.0
			self._repaintDelay()

	def mouseDrag(self,e,dx,dy):
		h=first(h for h in self.handles if h.isSelected())
		if h:
			h.mouseDrag(e,vec3(dx,dy))
		elif e.buttons()==Qt.LeftButton:
			self.scroll+=vec3(dx,-dy,0)
		elif e.buttons()==Qt.RightButton:
			self.zoom=max(0.01,self.zoom-dy*0.01)

		self._repaintDelay()
		
	def mouseRelease(self,e):
		for h in self.handles:
			h.setSelected(False)

	def parentClosed(self,e):
		self.removeHandles()
		self.mgr.removeEventHandler(self._repaintDelay)
		self.mgr.removeCamera(self.camera)
		self.camera=None
		self.indicatorPlane.setVisible(False)

	def fillImage(self,img):
		assert isMainThread()
		w,h=self.getDrawDims()
		if w>0 and h>0:
			self.camera.setAspectRatio(float(w)/h)
			self.camera.renderToStream(img.bits(),w,h,TF_ARGB32)

	def isStdPlaneName(self,name):
		'''Returns True if `name' is the name of a standard plane (ie. XY, YZ, XZ).'''
		return name in BaseCamera2DWidget.standardPlanes

	def calculateViewPlane(self,reptrans,planename=None,imgxi=0):
		'''
		Return the transform object representing the plane in space named by `planename' or by `reptrans' alone if
		this isn't provided. If `planename' names a representation object then its transform is used to define the
		plane, specifically if its a ImageSceneObjectRepr then getDefinedTransform() is called to get this transform.
		If `planename' is one of the standard plane names (XY, YZ, or XZ) then the transform is defined to represent
		this plane at image xi value `imgxi' in the direction normal to the plane (ie. this is Z axis xi value for 
		plane XY). The `reptrans' transform represents the transformation from xi space to world of the object the
		plane bisects, thus if the object is a volume this is the transformation from texture coordinates to world
		coordinates. This used to transform the standard plane definitions to world coordinates, and to define the
		resulting transform if `planename' names neither a representation object nor a standard plane. The return
		value is a transform in world space with a (1,1,1) scale component.
		'''
		planerep=self.mgr.findObject(planename)

		if planerep!=None:
			if isinstance(planerep,ImageSceneObjectRepr):
				planetrans=planerep.getDefinedTransform()
				planetrans.setScale(vec3(1))
			else:
				planept=planerep.getPosition(True)
				planerot=rotator(*planerep.getRotation(True))
				planetrans=transform(planept-(planerot*vec3(0,0,self.planeShift)),vec3(1),planerot)
		elif self.isStdPlaneName(planename):
			xi=clamp(imgxi,epsilon*100,1.0-epsilon*100)

			# choose xi values in the volume representing the plane's center, normal, and right-hand direction
			if planename=='XY':
				xipos=vec3(0.5,0.5,xi)
				xinorm=xipos+vec3(0,0,1)
				xiright=xipos+vec3(1,0,0)
			elif planename=='YZ':
				xipos=vec3(xi,0.5,0.5)
				xinorm=xipos+vec3(1,0,0)
				xiright=xipos+vec3(0,1,0)
			else: # XZ
				xipos=vec3(0.5,xi,0.5)
				xinorm=xipos+vec3(0,1,0)
				xiright=xipos+vec3(1,0,0)

			# calculate a world position and rotation by applying the transform to the xi values
			planept=reptrans*xipos
			planerot=rotator((reptrans*xiright)-planept,(reptrans*xinorm)-planept,vec3(1,0,0),vec3(0,0,1))
			planetrans=transform(planept,vec3(1),planerot)
		else:
			planetrans=transform(reptrans.getTranslation(),vec3(1),reptrans.getRotation())

		return planetrans

	def createFigure(self,name,ftype=FT_TRILIST,is2DOnly=True):
		'''
		Helper method for creating a figure with name `name' and type `ftype'. If `is2DOnly' is True then the returned
		figure is visible to this widget's camera only, otherwise it's default behaviour is unchanged.
		'''
		fig=self.mgr.scene.createFigure(name,'',ftype)
		fig.fillData(PyVertexBuffer([]),PyIndexBuffer([]))
		fig.setVisible(True)

		if is2DOnly: # visible to this widget's 2D camera only
			fig.setCameraVisibility(None,False)
			fig.setCameraVisibility(self.camera,True)

		return fig

	def createMaterial(self,name,useLighting=False,useVertexColor=True):
		'''Helper method for creating a blank material which bypasses the UI.'''
		mat=self.mgr.scene.createMaterial(name)
		mat.useLighting(useLighting)
		mat.useVertexColor(useVertexColor)
		return mat

	def createTexture(self,name,width,height,format):
		'''Helper method for creating a texture which bypasses the UI.'''
		return self.mgr.scene.createTexture(name,width,height,0,format)

	def addHandle(self,handle):
		'''Add the handle to the view and to self.handles.'''
		handle.addToScene(self.mgr,self.mgr.scene)
		self.handles.append(handle)
		self._repaintDelay()

	def removeHandle(self,index):
		'''Remove the handle at position `index' in self.handles to the view.'''
		h=self.handles.pop(index)
		h.removeFromScene(self.mgr,self.mgr.scene)
		self._repaintDelay()

	def removeHandles(self):
		'''Remove all handles from the view.'''
		while len(self.handles)>0:
			self.removeHandle(0)

		self.handles=[]
		self._repaintDelay()
		
	def getHandle(self,index):
		'''Return handle at position `index' in the list of handles.'''
		return self.handles[index]
		
	def handleSelected(self,handle):
		'''Called when the given handle object is selected by mouse click.'''
		pass

	def getObjFigures(self,name,numfigs=1,ftype=FT_TRILIST):
		'''Get the Figure objects for the object `name', or create `numfigs' objects of type `ftype' if none found.'''
		if name not in self.objFigMap:
			self.objFigMap[name]=(transform(),[])

		trans,figs=self.objFigMap[name]
		lfigs=len(figs)
		if lfigs<numfigs:
			for i in xrange(numfigs-lfigs):
				figs.append(self.createFigure('%s_2DFig%i'%(name,i+lfigs),ftype))

		for i,f in enumerate(figs):
			f.setVisible(i<numfigs)

		return trans,figs

	def retainObjFigures(self,names):
		'''Keep only the figures for those objects named in the iterable `names.'''
		notfound=set(self.objFigMap.keys()).difference(set(names))
		for nf in notfound:
			figs=self.objFigMap.pop(nf)[1]
			for f in figs:
				f.setVisible(False)

	def setObjPlane(self,name,planetrans):
		'''Set the view plane for the object named by `name' in self.objFigMap, retaining the figure list.'''
		self.objFigMap[name]=(planetrans,self.objFigMap[name][1])

	def setFigsVisible(self,name,vis):
		'''Set the visibility of the figures to `vis' for object named by `name'.'''
		if name in self.objFigMap:
			for fig in self.objFigMap[name][1]:
				fig.setVisible(vis)

	def setPlaneIndicator(self,obj,planetrans):
		'''Set the plane indicator in the 3D view for object `obj' to be at transform `planetrans'.'''
		if isinstance(obj.parent,ImageSceneObject) and obj.parent.is2D:
			self.indicatorPlane.setVisible(False)
			self.indicatorTrans=transform()
		else:
			bb=obj.getAABB()
			trans=transform(planetrans.getTranslation(),planetrans.getScale()*vec3(bb.radius*1.5),planetrans.getRotation())
			
			# needed to prevent update loops with _repaintDelay and _repaint3DDelay
			if trans!=self.indicatorTrans or self.indicatorPlane.isVisible()!=self.indicatorVisible:
				self.indicatorTrans=trans
				self.indicatorPlane.setTransform(trans)
				self.indicatorPlane.setVisible(self.indicatorVisible)
				self._repaint3DDelay()
				
	def setIndicatorVisible(self,visible):
		self.indicatorVisible=visible
		self._repaintDelay()

	def getBBTransform(self):
		'''
		Returns the transform which adjusts the figures to fit inside the selected viewing area based on the scene
		bound box, scroll, and zoom parameters.
		'''
		bbw,bbh,bbd=self.sceneBB.getDimensions()
		bscale=self.getBoxFitScale(bbw,bbh)
		return transform(self.scroll-self.sceneBB.center*bscale,vec3(self.zoom*bscale,self.zoom*bscale))

	def _planeToWorldTransform(self):
		'''Returns the transform from plane-relative coordinates to world coordinates.'''
		return self.viewplane*self.getBBTransform().inverse()

	def getWorldPosition(self,x,y,isAbsolute=True):
		'''
		Returns the world position of the screen coordinate (x,y) if `isAbsolute' is True, or screen proportionate
		coordinates otherwise (ie. (0,0) is top-left corner of screen and (1,1) is bottom-right).
		'''
		return self._planeToWorldTransform()*self.camera.getWorldPosition(x,y,isAbsolute)

	def getScreenPosition(self,pos):
		'''Returns the screen coordinate of the world vector `pos'.'''
		return self.camera.getScreenPosition(self.getOrthoPosition(pos))

	def getOrthoPosition(self,pos):
		'''
		Returns the orthographic camera coordinate of the world vector `pos'. In orthographic coordinates, the screen
		center is (0,0) and bottom-right is (1,1).
		'''
		return (self._planeToWorldTransform()/pos)*vec3(1,1)

	def setFigTransforms(self):
		'''Set the transforms for all figures to fit them in the viewing area and translate/scale as inputed by user.'''
		bbt=self.getBBTransform()
		for _,figs in self.objFigMap.values():
			for fig in figs:
				fig.setTransform(bbt)

	def _updatePlaneFig(self,fig,rep,planetrans,stackpos=0):
		'''
		Updates `fig' to contain data for plane cut through `rep' at plane `planetrans' or image stack position `stackpos'.
		'''
		assert rep!=None, 'Cannot find representation for 2D view'

		nodes,indices,xis=calculateReprIsoplaneMesh(rep,planetrans,stackpos,self.slicewidth)

		invtrans=planetrans.inverse()
		invtrans.setScale(vec3(1,1))
		nodes=[invtrans*v for v in nodes]

		vb=PyVertexBuffer(nodes,[vec3(0,0,1)]*len(nodes),None,xis)
		ib=PyIndexBuffer(indices)
		fig.fillData(vb,ib)

		return BoundBox(nodes)

	@delayedcall(0.15)
	def _updateMeshPlanecutFigs(self,repfigspairs,planetrans):
		'''Updates the figures containing mesh slice data for each secondary mesh object.'''
		@taskroutine('Generating Mesh Planecut')
		@timing
		def _generatecut(task):
			for rep,figs in repfigspairs:
				tslen=len(rep.getTimestepList())
				planept=planetrans.getTranslation()
				planerot=planetrans.getRotation()
				planenorm=planerot*vec3(0,0,1)
				
				assert tslen==len(figs)
				task.setMaxProgress(tslen)

				for i,tsrep in enumerate(rep.enumSubreprs()):
					task.setProgress(i+1)

					snodes,sinds,scols=generateMeshPlanecut(tsrep.dataset,'slicemesh%i'%i,planept,planenorm,self.linewidth,nodecolors=tsrep.nodecolors)
					vb=None
					ib=None

					if snodes:
						# transform the isolines to orthographic camera space
						snodes.sub(planept,0,0,snodes.n(),1)
						snodes.mul(planerot.inverse())
						snodes.mul(vec3(1,1),0,0,snodes.n(),1)

						vb=MatrixVertexBuffer(snodes,scols)
						ib=MatrixIndexBuffer(sinds)

					self.mgr.callThreadSafe(figs[i].fillData,vb,ib)

			self._repaintDelay()

		return self.mgr.runTasks(_generatecut())

	def updateView(self):
		'''
		Update the visible data for the current view's position. This will update the quad for the main image, secondary
		images, and refill the isoline meshes for the secondary meshes. The plane in world space the 2D view currently
		shows will be set to self.viewplane. Handles will also be updated as necessary, and all figures will be transformed
		to fit into the current viewing position. If this method is overridden, the override should call this one to 
		perform these operations after updating subtype-specific state, ie. as the last statement in the method. 
		'''
		assert isMainThread()
		rep=self.mgr.findObject(self.sourceName) # get the main object, this is None if it's been deleted since the last update
		if rep==None:
			return

		imgstackpos=self.getImageStackPosition()
		
		self.retainObjFigures([r.getName() for r in self.mgr.enumSceneObjectReprs()]) # remove reprs that don't exist anymore

		# calculate the plane in space this view is located at		
		self.viewplane=self.calculateViewPlane(rep.getDefinedTransform(imgstackpos),self.planeName,self.getImageXiPosition())

		self.setPlaneIndicator(rep,self.viewplane)

		# update handle visibility/activity
		for h in self.handles:
			h.setPlaneVisible(self.viewplane)
			h.updateHandle()

		_,mainfig=self.getObjFigures(self.sourceName) # get the main object's figure

		# update the main figure's plane figure and set it's material to the representation's currently used one
		self.sceneBB=self._updatePlaneFig(mainfig[0],rep,self.viewplane,imgstackpos)
		mainfig[0].setOverlay(False)
		mat=rep.getCurrentTimestepMaterial(imgstackpos)
		if mat:
			mainfig[0].setMaterial(mat)

		repfigspairs=[]

		# update each secondary representation, either image or mesh types
		for s in self.getSecondaryNames():
			s=s.split('<',1)[0].strip()
			srep=self.mgr.findObject(s) # split the label by <, assuming there's no < in the repr or object names
			assert srep,'Cannot find %r'%s
			
			# image repr, 1 plane for volumes since they slice through at the view plane, 1 plane per slice of image series since they're 2D
			if isinstance(srep,ImageSceneObjectRepr):
				numslices=srep.getNumStackSlices() if isinstance(srep,ImageSeriesRepr) else 1
				_,sfig=self.getObjFigures(s,numslices)

				for sslice in xrange(numslices):
					self.sceneBB+=self._updatePlaneFig(sfig[sslice],srep,self.viewplane,sslice)
					sfig[sslice].setMaterial(srep.getCurrentTimestepMaterial(sslice))
					sfig[sslice].setOverlay(True)
			else:
				# mesh repr, find the closest timestep to "now"
				timesteps=srep.getTimestepList()
				tsrepr=srep.getTimestepRepr()
				matname=tsrepr.getMaterialName()
				nearestTS,_=minmaxIndices(abs(self.mgr.timestep-v) for v in timesteps)

				#strans,sfigs=self.getObjFigures(s,len(timesteps),FT_LINELIST) # get the view plane and figures for this repr
				strans,sfigs=self.getObjFigures(s,len(timesteps)) # get the view plane and figures for this repr

				self.setObjPlane(s,self.viewplane) # set the repr's view plane

				# calculate the repr's isolines where it intersects the viewing plane if the current view plane
				# differs from the one the previous isolines were calculated for, this ensure the calculation is
				# only done if the view plane has moved.
				if isinstance(tsrepr,MeshSceneObjectRepr) and (tsrepr.tris!=None or tsrepr.lines!=None) and self.viewplane!=strans:
					repfigspairs.append((srep,sfigs))

				# set figure properties, making only the current timestep's figure visible
				for i,f in enumerate(sfigs):
					f.setOverlay(True)
					f.setMaterial(matname)
					f.setVisible(i==nearestTS) # True only for the figure at the current timestep

		if repfigspairs:
			self._updateMeshPlanecutFigs(repfigspairs,self.viewplane)

		self.setFigTransforms()


class Camera2DView(Draw2DView,BaseCamera2DWidget):
	'''
	The default 2D view widget. It primarily provides the code for linking the UI in Draw2DView to the actual rendering
	code in BaseCamera2DWidget. It calls modifyDrawWidget() to associate the drawing logic with the UI logic. This widget
	should be the base for any other 2D drawing widgets using or extending the base UI element, otherwise inherit from
	BaseCamera2DWidget and define a different UI which has a widget modifyDrawWidget() can be called with.
	'''
	def __init__(self,mgr,camera,parent=None):
		BaseCamera2DWidget.__init__(self,mgr,camera,parent)
		Draw2DView.__init__(self)
		
		delayedMethodWeak(self,'_updateUIDelay')
		
		mgr.addEventHandler(EventType._objectAdded,self.updateUI)
		mgr.addEventHandler(EventType._objectRemoved,self.updateUI)

		self.modifyDrawWidget(self.drawWidget)
		self.numVolSteps=10

		self.indicatorBox.clicked.connect(self.setIndicatorVisible)
		setCollapsibleGroupbox(self.dataGroup)
		self._updateUIDelay()
		
	def _updateUIDelay(self):
		self.mgr.callThreadSafe(self.updateUI)
		
	def parentClosed(self,e):
		self.mgr.removeEventHandler(self.updateUI)
		BaseCamera2DWidget.parentClosed(self,e)
		
	def getSecondaryNames(self):
		return self.secondsSelected
		
	def setSourceName(self,name):
		if name!=self.sourceName:
			self.setFigsVisible(self.sourceName,False)
			self.sourceName=name
			self.setFigsVisible(self.sourceName,True)
			self._updateUIDelay()

	def setPlaneName(self,plane):
		if plane!=self.planeName:
			self.planeName=plane
			self._updateUIDelay()

	def setSliceWidth(self,width):
		if width!=self.slicewidth:
			self.slicewidth=width
			Draw2DView.setSliceWidth(self,width)
			self._repaintDelay()

	def setLineWidth(self,width):
		if width!=self.linewidth:
			self.linewidth=width
			Draw2DView.setLineWidth(self,width)
			self._repaintDelay()

	def setImageStackPosition(self,val):
		Draw2DView.setImageStackPosition(self,val)

	def setSecondary(self,name,isVisible):
		Draw2DView.setSecondary(self,name,isVisible)
		self.setFigsVisible(name,isVisible)
		self._updateUIDelay()
		
	def updateUI(self,_=None):
		stdPlanes=list(BaseCamera2DWidget.standardPlanes)
		reprs=sorted(self.mgr.enumSceneObjectReprs())
		imgreprs=[o for o in reprs if isinstance(o,ImageSceneObjectRepr)]

		names=[o.getName() for o in imgreprs]

		if len(names)>0 and self.sourceName not in names:
			self.sourceName=names[0]

		notsource=[o for o in reprs if o.getName()!=self.sourceName]
		seconds=[o for o in notsource if isinstance(o,(ImageSceneObjectRepr,MeshSceneObjectRepr,TDMeshSceneObjectRepr)) ]
		
		planes=stdPlanes+[o.getName() for o in notsource]

		if self.planeName not in planes:
			self.planeName=planes[0]

		rep=self.mgr.findObject(self.sourceName)
		if isinstance(rep,ImageSeriesRepr):
			self.planeName=None

		stackmax=0
		if isinstance(rep,ImageSeriesRepr):
			stackmax=rep.getNumStackSlices()-1
		elif isinstance(rep,ImageVolumeRepr) and self.isStdPlaneName(self.planeName):
			stackmax=(rep.getNumStackSlices()-1)*self.numVolSteps

		# construct namelabels as a list of pairs associating each object's label to its name
		namelabels=zip([o.getLabel() for o in imgreprs],names)
		# construct planelabels similarly as a list of label-name pairs		
		planelabels=zip(stdPlanes+[o.getLabel() for o in notsource],planes)
		
		# set the list, choosing the label associated with the object named in self.sourceName
		fillList(self.sourceBox,namelabels,first(l for l,n in namelabels if n==self.sourceName))
		# similarly fill the list and choose default by label
		fillList(self.planeBox,planelabels,first(l for l,n in planelabels if n==self.planeName))
		
		self.fillSecondsMenu([(s.getLabel(),s.getName()) for s in seconds])
		
		self.setPlaneBoxVisible(isinstance(rep,ImageVolumeRepr))
		self.indicatorBox.setVisible(not rep or not rep.parent.is2D)
		self.setImageStackMax(stackmax)
		self._repaintDelay()

	def mouseDoubleClick(self,e):
		pt=self.getWorldPosition(e.x(),e.y())
		timestep=self.mgr.timestep
		rep=self.mgr.findObject(self.sourceName)
		results='World Position: %r\n'%pt

		if rep:
			results+='%r = %r\n'%(self.sourceName,sampleImageVolume(rep.parent,pt,timestep))

		for sec in self.secondsSelected:
			rep=self.mgr.findObject(sec)
			if rep and isinstance(rep,ImageSceneObject):
				results+='%r = %r\n'%(sec,sampleImageVolume(rep.parent,pt,timestep))

		self.mgr.showMsg('Output:','Samples',results,False)

	def mouseWheelMove(self,e):
		'''Need to override mouseWheelMove() since it's inherited twice and the one from Draw2DView is what should be called.'''
		Draw2DView.mouseWheelMove(self,e)
		
	def keyPress(self,e):
		if e.key() in (QtCore.Qt.Key_Left, QtCore.Qt.Key_Right):
			rep=self.mgr.findObject(self.sourceName)
			if rep:
				timesteps=rep.getTimestepList()
				nearest,_=minmaxIndices(abs(self.mgr.timestep-v) for v in timesteps)# index of the nearest timestep to the current time
				nearest=clamp(nearest+(1 if e.key()==QtCore.Qt.Key_Right else -1),0,len(timesteps)-1)
				self.mgr.setTimestep(timesteps[nearest])
		else:
			QtGui.QWidget.keyPressEvent(self,e)


class PointChooseMixin(object):
	'''
	Mixin for adding the functionality to choose a fixed number of named points on an image within a 2D window. Mix this 
	with a type implementing _repaintDelay(), getWorldPosition(), and addHandle() as expected in BaseCamera2DWidget.
	'''
	def __init__(self,layout,showBox=False,grouplabel='Landmark Points'):
		'''
		Initialize the mixin with `layout' being the layout object the UI for the points is added to with addWidget().
		The `showBox' boolean indicates whether the box containing the UI is initially visible or not. The UI box will
		have title `grouplabel'.
		'''
		self.pointMap={} # maps positionable point names to the (handle,label,button,edit)  tuple
		self.ptBox = QtGui.QGroupBox(grouplabel,self) # UI box containing controls for the points
		self.gridLayout = QtGui.QGridLayout(self.ptBox)
		layout.addWidget(self.ptBox)
		setCollapsibleGroupbox(self.ptBox,showBox)

	def addPoint(self,name,text,col):
		'''
		Add a positionable point called `name' with description `text' and color `col'. This will produce a quadruple
		(handle,label,button,edit) containing the PointHandle2D, QLable, QPushButton, and QLineEdit used to represent
		this point, storing it in self.pointMap keyed to name as well as returning it.
		'''
		handle=PointHandle2D(self,vec3(),col)
		label=QtGui.QLabel(text)
		button=QtGui.QPushButton('Set Plane')
		edit=QtGui.QLineEdit()

		self.gridLayout.addWidget(label,len(self.pointMap),0)
		self.gridLayout.addWidget(button,len(self.pointMap),1)
		self.gridLayout.addWidget(edit,len(self.pointMap),2)

		label.setStyleSheet('background-color: %s;'%str(toQtColor(col).name()))
		edit.setReadOnly(True)

		def _setfunc():
			handle.setNode(0,self.getWorldPosition(0.5,0.5,False))
			self._repaintDelay()

		button.clicked.connect(_setfunc)

		handle.setVisible(True)
		handle.setVisible3D(False)

		self.addHandle(handle)
		self.pointMap[name]=(handle,label,button,edit)
		return (handle,label,button,edit)

	def setPointsVisible(self,isVisible):
		for h,_,_,_ in self.pointMap.values():
			h.setVisible(isVisible)

	def setPointsVisible3D(self,isVisible):
		for h,_,_,_ in self.pointMap.values():
			h.setVisible3D(isVisible)

	def setPointMargin(self,margin):
		for h,_,_,_ in self.pointMap.values():
			h.planeMargin=margin

	def updateView(self):
		for h,_,_,e in self.pointMap.values():
			e.setText('%.3f, %.3f, %.3f'%tuple(h.pt))
			
	def getPoint(self,name):
		return self.pointMap[name][0].pt
		
	def setPoint(self,name,pt):
		self.pointMap[name][0].pt=pt


class DrawContourMixin(object):
	'''
	Mixin representing the UI for drawing a contour in the 2D window. It relies on the mixed subtype calling drawMouse*
	methods when mouse events are caught and reacting appropriately when drawing occurs (ie. when those methods return
	True). When drawing is done the final contour is in self.contour and can then be accessed by the mixed subtype.
	The method fillContourFig() must be called whenever the view is updated (ie. updateView() as in BaseCamera2DWidget).
	'''
	def __init__(self,numNodes,matname='newContour',drawcolor=color(1,0,0)):
		self.numNodes=numNodes
		self.drawingContour=False
		self.contour=[]
		self.drawcolor=drawcolor
		
		self.contourMat=self.mgr.getMaterial(matname) or self.mgr.createMaterial(matname)
		self.contourMat.useLighting(False)
		self.contourMat.useVertexColor(True)
		self.contourMat.useDepthCheck(False)
		self.contourFig=self.createFigure('newContourFig',FT_LINELIST)
		self.contourFig.setVisible(False)
		self.contourFig.setOverlay(True)
		self.contourFig.setMaterial(self.contourMat)
		
	def startContourDraw(self):
		self.drawingContour=True
	
	def fillContourFig(self):
		'''Fills the figure representing the drawn contour with lines so that it is visible on screen while drawing.'''
		if self.drawingContour:
			orthot=self._planeToWorldTransform().inverse()
			contour=self.contour[::10] if len(self.contour)>200 else self.contour # simplify contour if a lot of points are present
			nodes=[(orthot*n)*vec3(1,1) for n in contour] # convert contour to 2D coordinates
			num=len(nodes)
			vbuf=PyVertexBuffer(nodes,[vec3(0,0,1)]*num,[self.drawcolor]*num)
			ibuf=PyIndexBuffer([(i,i+1) for i in range(num-1)])
			self.contourFig.fillData(vbuf,ibuf)

	def drawMousePress(self,e):
		'''Start drawing the contour, returns True if drawing was enabled and the contour started, False otherwise.'''
		if e.buttons()!=Qt.LeftButton or not self.drawingContour:
			return False
			
		pt=self.getWorldPosition(e.x(),e.y())
		self.contour=[pt,pt]
		self.contourFig.setVisible(True)
		return True
		
	def drawMouseDrag(self,e,dx,dy):
		'''
		Add points to the contour when the mouse is dragged with position delta (dx,dy). This will interpolate over
		large distances to (mostly) ensure a uniform distribution of points along the drawn contour. Returns True
		if the contour was drawn, False otherwise.
		'''
		if not self.drawingContour:
			return False
			
		p=self.getWorldPosition(e.x(),e.y())
		dlen=int(vec3(dx,dy).len())
		
		if dlen: # if the mouse was moved relatively fast, add uniformly-spaced points along the drag path
			self.contour+=[lerp(i/dlen,self.contour[-1],p) for i in frange(dlen)]
		else:
			self.contour.append(p)

		return True

	def drawMouseRelease(self,e):
		'''
		Finish drawing the contour, returns True if the drawing was enabled and enough contour points were present
		to form a correct contour, False otherwise. The resulting contour is stored in self.contour if True is returned.
		'''
		if not self.drawingContour:
			return False
			
		self.drawingContour=False
		self.contourFig.setVisible(False)
		
		if len(self.contour)>self.numNodes:
			# select evenly spaced values from self.contour and store these back into self.contour
			inds=[partitionSequence(len(self.contour),i,self.numNodes)[0] for i in range(self.numNodes)]
			self.contour=indexList(inds,self.contour)
			return True
		else:
			return False


class DrawLineMixin(object):
	'''
	Mixin representing the UI for drawing a line in the 2D window. It relies on the mixed subtype calling drawMouse*
	methods when mouse events are caught and reacting appropriately when drawing occurs (ie. when those methods return
	True). When drawing is done the final line is self.start to self.end and can then be accessed by the mixed subtype.
	The method fillLineFig() must be called whenever the view is updated (ie. updateView() as in BaseCamera2DWidget).
	'''
	def __init__(self,matname='newLine',drawcolor=color(1,0,0)):
		self.drawingLine=False
		self.lineStart=None
		self.lineEnd=None
		self.drawcolor=drawcolor
		
		self.lineMat=self.mgr.getMaterial(matname) or self.mgr.createMaterial(matname)
		self.lineMat.useLighting(False)
		self.lineMat.useVertexColor(True)
		self.lineMat.useDepthCheck(False)
		self.lineFig=self.createFigure('newLineFig',FT_LINELIST)
		self.lineFig.setVisible(False)
		self.lineFig.setOverlay(True)
		self.lineFig.setMaterial(self.lineMat)
		
	def startLineDraw(self):
		self.drawingLine=True
	
	def fillLineFig(self):
		'''Fills the figure representing the drawn line so that it is visible on screen while drawing.'''
		if self.drawingLine:
			orthot=self._planeToWorldTransform().inverse()
			vbuf=PyVertexBuffer([(orthot*self.lineStart)*vec3(1,1),(orthot*self.lineEnd)*vec3(1,1)],[vec3(0,0,1)]*2,[self.drawcolor]*2)
			ibuf=PyIndexBuffer([(0,1)])
			self.lineFig.fillData(vbuf,ibuf)

	def drawMousePress(self,e):
		'''Start drawing the line, returns True if drawing was enabled and the line started, False otherwise.'''
		if e.buttons()!=Qt.LeftButton or not self.drawingLine:
			return False
			
		self.lineStart=self.lineEnd=self.getWorldPosition(e.x(),e.y())
		self.lineFig.setVisible(True)
		return True
		
	def drawMouseDrag(self,e,dx,dy):
		'''Move the end point to the position in `e'. Returns True if the line was moved, False otherwise.'''
		if not self.drawingLine:
			return False
			
		self.lineEnd=self.getWorldPosition(e.x(),e.y())
		return True

	def drawMouseRelease(self,e):
		'''Finish drawing the line, returns True if the drawing was enabled, False otherwise.'''
		if not self.drawingLine:
			return False
			
		self.drawingLine=False
		self.lineFig.setVisible(False)
		
		return True
			
			