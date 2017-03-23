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



from SceneObject import *
from ImageObject import *
from ImageAlgorithms import *
from VisualizerUI import *

import StringIO
import weakref
import os 


AxesType=enum(
	('none','None'),
	('originarrows','Origin Arrows'),
	('cornerTL','Top Left Corner Arrows'),
	('cornerTR','Top Right Corner Arrows'),
	('cornerBL','Bottom Left Corner Arrows'),
	('cornerBR','Bottom Right Corner Arrows'),
)

CenterType=enum(
	('none','None'),
	('point','Point'),
	('centerarrows','Center Arrows'),
)

LightType=enum(
	('point','Point Light'),
	('dir','Directional Light'),
	('spot','Spot Light'),
	('cpoint','Camera-Oriented Point Light'),
	('cdir','Camera-Oriented Directional Light'),
	('cspot','Camera-Oriented Spot Light'),
	doc='Defines the three types of light (point, directional, spot) and their camera-relative versions.'
)

class SceneLight(object):
	def __init__(self,light,lighttype,name,position=vec3(),direction=vec3(1,0,0)):
		self.light=light
		self.name=name
		self.theta=0.0
		self.phi=0.0
		self.lighttype=lighttype

		self.setPosition(position)
		self.setDirection(direction)
		self.setColor(color())
		self.setVisible(True)
		self.setSpotValues(0.2)
		self.setAttenuation(1000.0,0.0,1.0,0.0)
		self.setLightType(lighttype)

	def getName(self):
		return self.name

	def setLightType(self,lighttype):
		assert self.light
		assert lighttype in LightType
		self.lighttype=lighttype

		if lighttype in (LightType._spot,LightType._cspot):
			self.light.setSpotlight(0.0,self.spotangle,self.falloff)
		elif lighttype in (LightType._point,LightType._cpoint):
			self.light.setPoint()
		elif lighttype in (LightType._dir,LightType._cdir):
			self.light.setDirectional()

	def setVisible(self,isViz):
		self.isVisible=isViz
		self.light.setVisible(isViz)

	def setCameraAngles(self,theta,phi):
		self.theta=theta
		self.phi=phi

	def setSpotValues(self,spotangle,falloff=1.0):
		self.spotangle=spotangle
		self.falloff=falloff
		if self.lighttype in (LightType._spot,LightType._cspot):
			self.light.setSpotlight(0.0,self.spotangle,self.falloff)

	def setAttenuation(self,lrange,const,linear,quad):
		self.lrange=lrange
		self.const=const
		self.linear=linear
		self.quad=quad
		self.light.setAttenuation(self.lrange,self.const,self.linear,self.quad)

	def setPosition(self,pos):
		self.light.setPosition(pos)
		self.position=pos

	def setDirection(self,dirv):
		self.light.setDirection(dirv)
		self.direction=dirv

	def setColor(self,col):
		self.color=col
		self.light.setDiffuse(col)
		self.light.setSpecular(col)


class Handle(object):
	'''
	Base class for handles, which are UI elements in the render window or 2D windows used to manipulate scene objects
	or represent some other form of data (ig. points of interest, clip boxes). A handle has 3 different state values:
	 - isVisible()  -- True iff the handle is visible on screen, manipulable subcomponents may not be visible
	 - isActive()   -- True iff the handle can be manipulated/selected and all its subcomponents are visible
	 - isSelected() -- True iff the handle has been selected by mouse click and is being manipulated
		
	A handle can only be selected if its visible. Clicking on an inactive handle makes it both selected and active. The
	checks to determine if it's been selected are done with checkSelected(). A handle can be active and not selected if
	it was previously selected but then checkSelected() subsequently returned False. In this case the subcomponents are 
	visible but the user is not current interacting with the handle. If the handle is selected then the mouse has been 
	clicked on the handle and held down, so the handle will only then receive mouse inputs. A handle can be invisible 
	but active, meaning the subcomponents will still be visible once the handle becomes visible again.
	'''

	handleMatName='Handle'

	@staticmethod
	def _defaultMaterial(mgr):
		return mgr.getMaterial(Handle.handleMatName)

	def __init__(self):
		self._isVisible=False # handle visibility state
		self.figs=[] # list of figures used to represent the handle in 3D and 2D

	def isVisible(self):
		'''Returns True if the handle is visible.'''
		return self._isVisible

	def setVisible(self,isVisible):
		'''Set the visibility of the handle. The handle can still be active if invisible, but cannot be manipulated.'''
		self._isVisible=isVisible

		for f in self.figs:
			f.setVisible(isVisible)
			
	def isSelected(self):
		'''Returns True if this handle is selected as determined by checkSelected().'''
		return False
		
	def setSelected(self,isSelected):
		'''Set the selection state of the handle.'''
		pass

	def checkSelected(self,selectObj):
		'''
		Check whether this object is selected given the input `selectObj'. The input will vary depending on context,
		for a handle selected from a 3D window this should be a ray and so the handle should do a ray intersection
		test. For a 2D handle this may be the screen coordinates. This method should return True if the selection
		criteria is met, and isSelected() should then return the same until checkSelected() is called again. This
		method should return False if isVisible() is False. If it returns True it should also make the handle active.
		'''
		pass

	def isActive(self):
		'''Returns True if this handle is active.'''
		return True

	def setActive(self,isActive):
		'''Set the active state of the handle. The handle can still be inactive if visible, but cannot be manipulated.'''
		pass

	def addToScene(self,mgr,scene):
		pass

	def removeFromScene(self,mgr,scene):
		'''Remove the handle from the scene, this makes the figures invisible and clears self.figs.'''
		assert isMainThread()
		for f in self.figs:
			f.setVisible(False)
		del self.figs[:] 

	def mousePress(self,camera,e):
		pass

	def mouseRelease(self,e):
		pass

	def mouseMove(self,e):
		pass

	def mouseDrag(self,e,dragvec):
		pass

	def setPosition(self,pos):
		pass

	def setScale(self,scale):
		pass

	def setRotation(self,yaw,pitch,roll):
		pass


class Handle2D(Handle):
	'''
	This represents a handle in a BaseCamera2DWidget rendering widget. It has representation in 2D widget and optionally
	have representation in the main 3D view. 
	'''
	
	defaultPlaneMargin=1e-3 # margin for measuring if a handle is on a plane in 3D space, a handle this far from a plane is considered on it
	
	def __init__(self,widg2D,col,selectRadius=None):
		'''
		Initialize the handle with the BaseCamera2DWidget instance `widg2D', color `col' applied to the figures of the
		handle, and `selectRadius' float indicating the selectable radius in screen units around selectable figures.
		'''
		Handle.__init__(self)
		self.widg2D=widg2D
		self.planeMargin=Handle2D.defaultPlaneMargin
		self.selectRadius=abs(selectRadius or 5.0)
		self.selectedNodeInd=-1
		self._isActive=True # set to True if is manipulable by user input
		self._isChanged=False # set to True if structure is changed, not when repositioned
		self._isVisible3D=False # True if this handle makes visible any sort of representation it might have in the 3D view
		self.col=col

	def isVisible3D(self):
		return self._isVisible3D

	def setVisible3D(self,isVisible):
		self._isChanged=isVisible!=self._isVisible3D
		self._isVisible3D=isVisible

	def isActive(self):
		return self._isActive

	def setActive(self,isActive):
		self._isActive=isActive
		self.setVisible(self.isVisible()) # sets control point visibility

	def setColor(self,col):
		self.col=col
		self._isChanged=True

	def numNodes(self):
		return 0

	def getNodes(self):
		'''Returns the world coordinates of the data nodes representing this handle.'''
		return []

	def setNode(self,i,n):
		pass

	def enumPlaneNodes(self,viewtrans):
		invtrans=viewtrans.inverse()
		invtrans.setScale(vec3(1))
		for n in self.getNodes():
			yield invtrans*n

	def setPlaneVisible(self,viewtrans):
		self.setVisible(all(abs(n.z())<self.planeMargin for n in self.enumPlaneNodes(viewtrans)))

	def isSelected(self):
		return self.selectedNodeInd!=-1
		
	def setSelected(self,isSelected):
		self.selectedNodeInd= 0 if isSelected else -1

	def checkSelected(self,screenpos):
		assert isinstance(screenpos,vec3)
		
		self.selectedNodeInd=-1
		if self.isVisible():# and self.isActive():
			for i,n in enumerate(self.getNodes()):
				n=self.widg2D.getScreenPosition(n)
				if n.distTo(screenpos)<=(self.selectRadius+1):
					self.selectedNodeInd=i
					self.setActive(True)
					break

		return self.selectedNodeInd!=-1

	def updateHandle(self):
		'''Called by the 2D widget to cause handles to update their representations, positions, etc.'''
		if self._isChanged:
			self.updateRepr()

		self.updatePositions()
		self._isChanged=False

	def updatePositions(self):
		'''Called whenever a handle needs to update its positions for its representation figures.'''
		pass

	def mouseDrag(self,e,dragvec):
		if self.widg2D:
			node=self.widg2D.getWorldPosition(e.x(),e.y())
		else:
			node=vec3(e.x(),e.y())

		self.setNode(self.selectedNodeInd,node)

	def addToScene(self,mgr,scene):
		self._isChanged=True
		self.updateRepr()

	def updateRepr(self):
		pass


class PointHandle2D(Handle2D):
	def __init__(self,widg2D,pt,col=color(1,0,0),radius=None):
		Handle2D.__init__(self,widg2D,col,radius)
		self.pt=pt

	def numNodes(self):
		return 1

	def getNodes(self):
		return [self.pt]

	def setNode(self,i,n):
		assert i==0
		self.pt=n

	def updatePositions(self):
		self.figs[0].setPosition(self.widg2D.getOrthoPosition(self.pt))
		self.figs[1].setPosition(self.pt)
		self.figs[1].setVisible(self.isVisible3D())

	def updateRepr(self):
		mat=Handle._defaultMaterial(self.widg2D.mgr)

		if len(self.figs)==0:
			fig=self.widg2D.createFigure('point',FT_TRILIST)
			fig.setMaterial(mat)
			fig.setOverlay(True)
			self.figs.append(fig)

			fig3D=self.widg2D.createFigure('point3d',FT_TRILIST,False)
			fig3D.setMaterial('Default')
			fig3D.setOverlay(False)
			fig3D.setVisible(False)
			self.figs.append(fig3D)

		fillCircleFigure(self.figs[0],self.selectRadius,self.col)
		fillSphereFigure(self.figs[1],self.selectRadius/5,2,self.col)


class RectHandle2D(Handle2D):
	def __init__(self,widg2D,pts,col=color(1,0,0,1),radius=None):
		Handle2D.__init__(self,widg2D,col,radius)
		self.pts=list(self._setRect(*pts))
		self.boxcol=color(1,1,1,1)

	def setVisible(self,isVisible):
		self._isVisible=isVisible
		for f in self.figs[:4]: # make the control points visible only when active
			f.setVisible(isVisible and self.isActive())

		self.figs[-1].setVisible(isVisible)

	def numNodes(self):
		return 4

	def getNodes(self):
		return list(self.pts)

	def getMinMax(self):
		minv=vec3(self.pts[0])
		maxv=vec3(self.pts[0])
		for p in self.pts[1:]:
			minv.setMinVals(p)
			maxv.setMaxVals(p)

		return minv,maxv

	def _setRect(self,p1,p2,p3,p4,n=None):
		'''
		returns a rectangle defined using the given values. The rectangle lies on the plane defined by the first three
		points, `n' is projected onto this plane and then new values for `p2' and `p3' are calculated to ensure the
		retangular shape. It's assumed that `p1' is the far corner opposite `p4' and that `p4' is the point being
		replaced with `n', which requires adjusting `p2' and `p3'. if `n' isn't provided, `p4' is assigned to it.
		'''
		norm=p1.planeNorm(p2,p3)
		n=n or p4
		n=n.planeProject(p1,norm)
		diag=(n-p1)
		angle=diag.angleTo(p2-p1)
		pp2=(p2-p1).norm()*(math.cos(angle)*diag.len())+p1
		pp3=(p3-p1).norm()*(math.sin(angle)*diag.len())+p1

		# don't allow `p4' to cross over the planes bounding the rectangle at the edges p1->p2 and p1->p3
		if n.planeDist(p1,norm.cross(p1-p2))>=0 or n.planeDist(p1,norm.cross(p3-p1))>=0:
			return p1,p2,p3,p4

		return p1,pp2,pp3,n

	def setNode(self,i,n):
		if any(n.distToSq(self.pts[j])<epsilon*100 for j in range(len(self.pts)) if j!=i):
			return

		p1,p2,p3,p4=self.pts
		if i==0:
			p4,p2,p3,p1=self._setRect(p4,p2,p3,p1,n)
		elif i==1:
			p3,p1,p4,p2=self._setRect(p3,p1,p4,p2,n)
		elif i==2:
			p2,p4,p1,p3=self._setRect(p2,p4,p1,p3,n)
		else:
			p1,p2,p3,p4=self._setRect(p1,p2,p3,p4,n)

		self.pts=[p1,p2,p3,p4]

	def updatePositions(self):
		pts2d=map(self.widg2D.getOrthoPosition,self.pts)

		fillPolyFigure(self.figs[-1],[pts2d[0],pts2d[1],pts2d[3],pts2d[2]],self.boxcol)

		for f,p in zip(self.figs,pts2d):
			f.setPosition(p)

	def updateRepr(self):
		mat=Handle._defaultMaterial(self.widg2D.mgr)
		if len(self.figs)==0:
			for i in range(len(self.pts)): # 4 corner figures
				fig=self.widg2D.createFigure('corner%i'%i,FT_TRILIST)
				fig.setMaterial(mat)
				fig.setOverlay(True)
				self.figs.append(fig)

			#rectangle figure
			fig=self.widg2D.createFigure('box',FT_LINELIST)
			fig.setMaterial(mat)
			fig.setOverlay(True)
			fillPolyFigure(fig,self.pts,self.boxcol)
			self.figs.append(fig)

		for i in range(len(self.pts)):
			fillCircleFigure(self.figs[i],self.selectRadius,self.col)


class PolyHandle2D(Handle2D):
	'''
	Represents a polygon figure defined by 2 or more control points. The figure is drawn by interpolating points along
	the line using the given element type. The lines for the handle are rendered into the given 2D widget and into the
	3D view if set to do so. The handles for the control points are rendered in 2D only.
	'''
	contourMatName='Contour'

	@staticmethod
	def _contourMaterial(mgr):
		return mgr.getMaterial(PolyHandle2D.contourMatName)

	def __init__(self,widg2D,pts,isClosed=False,col=color(1,0,0,1),etype=None,radius=None):
		Handle2D.__init__(self,widg2D,col,radius)
		self.pts=list(pts)
		self.isClosed=isClosed
		self.etype=etype or ElemType.Line1NL
		self.linecol=color(1.0,1.0,0)
		self.mat=None
		self.coeffs=[]
		self.numlines=6
		self.line2D=None
		self.line3D=None
		self._calculateCoeffs()

	def _calculateCoeffs(self):
		'''Precalculates and stores the coefficients for the contour line.'''
		n=self.numNodes()
		numpts=n*self.numlines+1
		if len(self.coeffs)!=numpts:
			step=1.0/(len(self.pts)*self.numlines)
			lim=[(0,-1)] if self.isClosed else [(0,0)]
			self.coeffs=[self.etype.basis(i,0,0,n,limits=lim,circular=[self.isClosed]) for i in frange(0,1+step,step)]
			assert len(self.coeffs)==numpts,'%i %i'%(len(self.coeffs),numpts)
		
	def checkSelected(self,screenpos):
		if Handle2D.checkSelected(self,screenpos):
			return True
			
		if self.isVisible():# and self.isActive():
			isLinear=(self.etype==ElemType.Line1NL)
			pts2d=map(self.widg2D.getScreenPosition,self.pts)
			linepts=pts2d if isLinear else [self.etype.applyCoeffs(pts2d,c) for c in self.coeffs]
			lines=successive(linepts,cyclic=True)
			ind= first(i for i,pp in enumerate(lines) if 0<=screenpos.lineDist(*pp)<=self.selectRadius)
			if ind is not None:
				# choose the closest point index to the line segment that was clicked
				linexi=float(ind)/len(linepts)
				nodeind=int(round(linexi*len(pts2d)))
				self.selectedNodeInd=nodeind%len(pts2d)
				self.setActive(True)
			
		return self.selectedNodeInd!=-1

	def setVisible(self,isVisible):
		self._isVisible=isVisible
		for f in self.figs:
			f.setVisible(self.isActive() and isVisible) # hide the control points only if not active

		self.line2D.setVisible(isVisible)
		self.line3D.setVisible(self.isVisible3D())

	def numNodes(self):
		return len(self.pts)

	def setNumNodes(self,n):
		assert n>1
		if n!=len(self.pts):
			step=1.0/n
			lim=[(0,-1)] if self.isClosed else [(0,0)]
			self.pts=[self.etype.applyBasis(self.pts,i,0,0,len(self.pts),limits=lim,circular=(self.isClosed,)) for i in frange(0,1,step)]
			self._isChanged=True
			assert len(self.pts)==n

	def getNodes(self):
		return list(self.pts)

	def setNode(self,i,n):
		self._isChanged=True
		self.pts[i]=n

	def updatePositions(self):
		isLinear=(self.etype==ElemType.Line1NL)
		n=self.numNodes()
		assert n>1

		pts2d=map(self.widg2D.getOrthoPosition,self.pts)
		for f,p in zip(self.figs,pts2d): # set the positions of the node figs, which should be before any others so that zip works
			f.setPosition(p)

		if not isLinear and (self.isVisible() or self.isVisible3D()):
			self._calculateCoeffs()

		if self.isVisible():
			if isLinear:
				linepts=pts2d
			else:
				linepts=[self.etype.applyCoeffs(pts2d,c) for c in self.coeffs]

			fillPolyFigure(self.line2D,linepts,self.linecol,self.isClosed and isLinear) 

		if self.isVisible3D() and self._isChanged:
			if isLinear:
				linepts=self.pts
			else:
				linepts=[self.etype.applyCoeffs(self.pts,c) for c in self.coeffs]

			fillPolyFigure(self.line3D,linepts,self.linecol,self.isClosed and isLinear) 

	def updateRepr(self):
		self.mat=Handle._defaultMaterial(self.widg2D.mgr)

		if not self.line2D:
			mat=PolyHandle2D._contourMaterial(self.widg2D.mgr)

			#line figure
			self.line2D=self.widg2D.createFigure('line',FT_LINELIST)
			self.line2D.setMaterial(mat)
			self.line2D.setOverlay(True)
			self.line2D.setVisible(True)

			self.line3D=self.widg2D.createFigure('line3d',FT_LINELIST,False)
			self.line3D.setMaterial(mat)
			self.line3D.setVisible(False)

		n=self.numNodes()
		assert n>1

		del self.figs[:]

		# add needed figures
		for i in range(len(self.pts)):
			fig=self.widg2D.createFigure('node%i'%i,FT_TRILIST)
			fig.setMaterial(self.mat)
			fig.setOverlay(True)
			fillCircleFigure(fig,self.selectRadius,self.col)
			self.figs.append(fig)
			
		self.figs+=[self.line2D,self.line3D] # add the extra figs to the end
		self.setVisible(self._isVisible)

class Handle3D(Handle):
	'''
	This represents a manipulable handle in the 3D view only. It represents an object the user can interact with using
	the mouse rather than the indicator for a manipulable object in another view.
	'''
	def __init__(self):
		Handle.__init__(self)
		self.figscale=1.0
		self.prevX=0
		self.prevY=0
		self.buttons=None
		self.pressedCamera=None

	def mousePress(self,camera,e):
		if self.isSelected():
			self.prevX=e.x()
			self.prevY=e.y()
			self.buttons=e.buttons()
			self.pressedCamera=camera

	def mouseRelease(self,e):
		self.prevX=0
		self.prevY=0
		self.buttons=None
		self.pressedCamera=None

	def mouseMove(self,e):
		if self.isSelected():
			dragvec=vec3(e.x()-self.prevX,e.y()-self.prevY,0)
			self.prevX=e.x()
			self.prevY=e.y()
			self.mouseDrag(e,dragvec)

	def getDragDistance(self,axis,dragvec,startpos,isPerpendicular=False):
		'''
		Calculates the distance a mouse drag represents in relation to a given axis. The drag is represented by the
		position delta `dragvec', ie. vec3(b.x()-a.x(),b.y()-a.y(),0) if the mouse was dragged from screen position a to b.
		The argument `startpos' is where the attached object was when the button was first pressed.
		The returned value is proportional to how parallel (or perpendiculat if `isPerpendicular' is true) to the screen
		axis the drag is: in the direction of `axis' yields values up to 1, directly away from yields values down to -1.
		'''
		if not self.pressedCamera:
			return 0

		screenpos=self.pressedCamera.getScreenPosition(startpos)
		axispos=self.pressedCamera.getScreenPosition(startpos+axis)
		axisdir=(axispos-screenpos) # direction along tested axis
		if isPerpendicular: # if a perpendicular check is requested, make direction perpendicular to axis
			axisdir=vec3(axisdir.y(),-axisdir.x(),0)

		dragamount=1.0-(axisdir.angleTo(dragvec)/halfpi) # [-1,1]
		return dragvec.len()*dragamount

	def getDragVector(self,dragvec,curpos):
		prevpos=curpos-dragvec
		screenpos=self.pressedCamera.getProjectedRay(curpos.x(),curpos.y()).getPosition()
		startpos=self.pressedCamera.getProjectedRay(prevpos.x(),prevpos.y()).getPosition()
		return screenpos-startpos

	def setPosition(self,pos):
		for f in self.figs:
			f.setPosition(pos)

	def setScale(self,scale):
		self.figscale=scale
		for f in self.figs:
			f.setScale(scale)

	def setRotation(self,yaw,pitch,roll):
		rot=rotator(yaw,pitch,roll)
		for f in self.figs:
			f.setRotation(rot)


#class NodeHandle(Handle3D):
#	spherenodes=None
#	sphereinds=None
#
#	def __init__(self,rep,nodes,nodeind,col):
#		Handle.__init__(self)
#		self.rep=rep
#		self.nodes=nodes
#		self.nodeind=nodeind
#		self.col=col
#		self.lastIntersect=None
#
#		if NodeHandle.spherenodes==None:
#			NodeHandle.spherenodes,NodeHandle.sphereinds=generateSphere(2)
#
#	def isSelected(self):
#		return self.lastIntersect!=None


class TransformHandle(Handle3D):
	'''Handle used to manipulate the affine transformations of SceneObjectRepr objects.'''

	arrowinds=None
	xnodes=None
	ynodes=None
	xnodse=None

	def __init__(self,rep):
		Handle3D.__init__(self)
		self.rep=rep
		self.lastIntersect=None
		self.repRadius=0
		self._generatefigureValues()

	def _generatefigureValues(self):
		if TransformHandle.arrowinds!=None:
			return

		refine=5
		nodes,TransformHandle.arrowinds=generateArrow(refine)
		nodes[-1]*=0.5
		nodes=[n*vec3(0,0,1) for n in nodes[:2*(3+refine)+1]]+nodes[2*(3+refine)+1:]

		TransformHandle.znodes=[(n*vec3(0.35,0.35,1))+vec3(0,0,1) for n in nodes] # shrink and move Z-aligned arrow
		TransformHandle.xnodes=[rotator(vec3(0,1,0),halfpi)*n for n in TransformHandle.znodes]
		TransformHandle.ynodes=[rotator(vec3(1,0,0),-halfpi)*n for n in TransformHandle.znodes]

	def isSelected(self):
		return self.lastIntersect!=None
		
	def setSelected(self,isSelected):
		if isSelected:
			self.lastIntersect=(TransformHandle.xnodes,TransformHandle.arrowinds,0,self.rep.getPosition(True))
		else:
			self.lastIntersect=None

	def checkSelected(self,ray):
		assert isinstance(ray,Ray)
		self.lastIntersect=None
		if self.isVisible():# and self.isActive():
			pos=self.rep.getPosition(True)

			for nodes in (TransformHandle.xnodes,TransformHandle.ynodes,TransformHandle.znodes):
				for i,tri in enumerate(TransformHandle.arrowinds):
					tnodes=[(nodes[t]*self.figscale)+pos for t in tri]
					result=ray.intersectsTri(*tnodes)
					if len(result)>0:
						self.lastIntersect=(nodes,TransformHandle.arrowinds,i,pos)
						return True

		return False

	def mousePress(self,camera,e):
		Handle3D.mousePress(self,camera,e)
		self.repRadius=self.rep.getAABB(True).radius
		self.rot=0

	def mouseDrag(self,e,dragvec):
		nodes,inds,i,startpos=self.lastIntersect

		if nodes is TransformHandle.xnodes:
			axis=vec3(1,0,0)
		elif nodes is TransformHandle.ynodes:
			axis=vec3(0,1,0)
		else:
			axis=vec3(0,0,1)

		dragdist=self.getDragDistance(axis,dragvec,startpos,self.buttons==Qt.RightButton)

		if self.buttons==Qt.LeftButton: # translate
			multiplier=0.005*self.repRadius
			v=axis*(dragdist*multiplier)
			self.rep.setPosition(self.rep.getPosition()+v)

		elif self.buttons==Qt.RightButton: # rotate
			multiplier=-0.005
			rot=rotator(axis,dragdist*multiplier)*rotator(*self.rep.getRotation())
			yaw,pitch,roll=rot.getEulers()
			self.rep.setRotation(yaw,pitch,roll)

		elif self.buttons==Qt.MiddleButton: # scale
			multiplier=0.005
			v=axis*(dragdist*multiplier)
			scale=self.rep.getScale()
			self.rep.setScale(scale+v)

		elif self.buttons==Qt.LeftButton|Qt.RightButton: # translate relative to camera
			v=self.getDragVector(dragvec,vec3(e.x(),e.y()))*10000
			self.rep.setPosition(self.rep.getPosition()+v)

	def addToScene(self,mgr,scene):
		assert isMainThread()

		nameprefix=self.rep.getName()
		mat=Handle._defaultMaterial(mgr)
		matname=mat.getName()

		def createFigure(name,nodes,inds,col):
			norms=generateTriNormals(nodes,inds)
			vbuf=PyVertexBuffer(nodes,norms,[col]*len(nodes))
			ibuf=PyIndexBuffer(inds)

			fig=scene.createFigure(name,matname,FT_TRILIST)
			fig.fillData(vbuf,ibuf)
			return fig

		def createLine(name,n1,n2,col):
			vbuf=PyVertexBuffer([n1,n2],[vec3(1,0,0)]*2,[col]*2)
			ibuf=PyIndexBuffer([(0,1)])

			fig=scene.createFigure(name,matname,FT_LINELIST)
			fig.fillData(vbuf,ibuf)
			return fig

		self.figs=[
			createFigure(nameprefix+'HaxesZ',TransformHandle.znodes,TransformHandle.arrowinds,color(0,0,1,0.5)),
			createFigure(nameprefix+'HaxesX',TransformHandle.xnodes,TransformHandle.arrowinds,color(1,0,0,0.5)),
			createFigure(nameprefix+'HaxesY',TransformHandle.ynodes,TransformHandle.arrowinds,color(0,1,0,0.5)),
			createLine(nameprefix+'HlinesZ',vec3(0,0,5),vec3(0,0,-2.5),color(0,0,1,0.5)),
			createLine(nameprefix+'HlinesX',vec3(5,0,0),vec3(-2.5,0,0),color(1,0,0,0.5)),
			createLine(nameprefix+'HlinesY',vec3(0,5,0),vec3(0,-2.5,0),color(0,1,0,0.5)),
		]

		for f in self.figs:
			f.setOverlay(True)

	def setRotation(self,yaw,pitch,roll):
		rot=rotator(yaw,pitch,roll)
		for f in self.figs[3:]: # axes lines only, don't rotate arrows
			f.setRotation(rot)


class SpectrumWidget(BaseSpectrumWidget):
	'''This displays and manipulates the spectrum of a list of attached Material object.'''
	def __init__(self,matsrc,mgr,parent=None):
		'''Associate this widget with the list of materials `matsrc'.'''
		BaseSpectrumWidget.__init__(self,parent)
		self.matsrc=matsrc
		self.mgr=mgr

	def getValues(self):
		mat=first(self.matsrc())
		if mat==None:
			return

		assert isinstance(mat,Spectrum),str(mat)
		self.isLinearAlpha=mat.isLinearAlpha()

		self.colors=[]
		self.colorpos=[]
		for i in range(mat.numSpectrumValues()):
			self.colors.append(tuple(mat.getSpectrumValue(i)))
			self.colorpos.append(mat.getSpectrumPos(i))

		self.alphactrls=[]
		for i in range(mat.numAlphaCtrls()):
			self.alphactrls.append(tuple(mat.getAlphaCtrl(i)))

	def setLinearAlpha(self,linear):
		self.isLinearAlpha=linear
		for mat in self.matsrc():
			mat.setLinearAlpha(linear)

	def setValues(self,colorIndex=None,alphaIndex=None):
		for mat in self.matsrc():
			if colorIndex!=None:
				mat.setSpectrumValue(colorIndex,self.colorpos[colorIndex],color(*self.colors[colorIndex]))
			elif alphaIndex!=None:
				mat.setAlphaCtrl(vec3(*self.alphactrls[alphaIndex]),alphaIndex)
			else:
				nsv=mat.numSpectrumValues()
				nac=mat.numAlphaCtrls()

				for i in range(nsv):
					mat.removeSpectrumValue(0)

				for i in range(len(self.colors)):
					mat.addSpectrumValue(self.colorpos[i],color(*self.colors[i]))

				for i in range(nac):
						mat.removeAlphaCtrl(0)

				self.alphactrls.sort(key=operator.itemgetter(0))

				for i in range(len(self.alphactrls)):
						mat.addAlphaCtrl(vec3(*self.alphactrls[i]))

		if self.mgr!=None:
			self.mgr.repaint()

	def interpolateColor(self,t):
		mat=first(self.matsrc())
		return mat.interpolateColor(t)


class MaterialController(object):
	def __init__(self,mgr,win):
		self.mgr=mgr
		self.win=win

	def createMaterial(self,mat):
		'''
		Accepts a Material object instance and has the opportunity to modify it or return a proxied version. The
		default behaviour is to just return the same object.
		'''
		return mat

	def addMaterial(self,mat):
		'''Sets up the material property box and other operations for the new or cloned material. Executed in UI thread.'''
		assert isMainThread()
		if not self.win:
			return

		self.win.addMaterial(mat,self.updatePropBox)
		propbox=self.win.findPropBox(mat)

		propbox.textureList.currentIndexChanged.connect(lambda i:self._chooseTexture(i,mat,propbox))

		propbox.fragList.currentIndexChanged.connect(lambda i:self._chooseGPUProgram(i,mat,propbox.fragList,PT_FRAGMENT))
		propbox.vertList.currentIndexChanged.connect(lambda i:self._chooseGPUProgram(i,mat,propbox.vertList,PT_VERTEX))

		# color boxes
		propbox.chooseAmbient.clicked.connect(lambda:self._chooseColor(mat.getAmbient(),mat.setAmbient,mat,propbox))
		propbox.chooseDiffuse.clicked.connect(lambda:self._chooseColor(mat.getDiffuse(),mat.setDiffuse,mat,propbox))
		propbox.chooseEmissive.clicked.connect(lambda:self._chooseColor(mat.getEmissive(),mat.setEmissive,mat,propbox))
		propbox.chooseSpecular.clicked.connect(lambda:self._chooseColor(mat.getSpecular(),mat.setSpecular,mat,propbox))

		propbox.shininessBox.valueChanged.connect(lambda i: mat.setShininess(i) or self.mgr.repaint())
		propbox.alphaBox.valueChanged.connect(lambda i: mat.setAlpha(i) or self.mgr.repaint())

		# point size boxes
		propbox.minSizeBox.valueChanged.connect(lambda i: mat.setPointSize(i,mat.getPointSizeMax()) or self.mgr.repaint())
		propbox.maxSizeBox.valueChanged.connect(lambda i: mat.setPointSize(mat.getPointSizeMin(),i) or self.mgr.repaint())
		propbox.absSizeBox.valueChanged.connect(lambda i: mat.setPointSizeAbs(i) or self.mgr.repaint())
		propbox.absoluteRadio.clicked.connect(lambda b: mat.setPointAttenuation(False) or self.mgr.repaint())
		propbox.relativeRadio.clicked.connect(lambda b: mat.setPointAttenuation(True) or self.mgr.repaint())

		# properties check boxes
		propbox.useLightingCheck.clicked.connect(lambda i: mat.useLighting(not mat.usesLighting()) or self.mgr.repaint())
		propbox.flatShadingCheck.clicked.connect(lambda i: mat.useFlatShading(not mat.usesFlatShading()) or self.mgr.repaint())
		propbox.useVertexCheck.clicked.connect(lambda i: mat.useVertexColor(not mat.usesVertexColor()) or self.mgr.repaint())
		propbox.useSpritesCheck.clicked.connect(lambda i: mat.usePointSprites(not mat.usesPointSprites()) or self.mgr.repaint())
		propbox.cullBackfacesCheck.clicked.connect(lambda i: mat.cullBackfaces(not mat.isCullBackfaces()) or self.mgr.repaint())
		propbox.depthCheck.clicked.connect(lambda i: mat.useDepthCheck(not mat.usesDepthCheck()) or self.mgr.repaint())
		propbox.depthWriteCheck.clicked.connect(lambda i: mat.useDepthWrite(not mat.usesDepthWrite()) or self.mgr.repaint())
		propbox.texFilterCheck.clicked.connect(lambda i: mat.useTexFiltering(not mat.usesTexFiltering()) or self.mgr.repaint())

		propbox.spectrum=SpectrumWidget(lambda:[mat],None,propbox)
		propbox.gridLayout.addWidget(propbox.spectrum, 1, 0, 1, 1)

		propbox.applyButton.clicked.connect(lambda:self.mgr.applyMaterial(mat))
		
		propbox.setSpecButton.clicked.connect(lambda:self._setSpectrum(mat,propbox))

	def removeMaterial(self,mat):
		pass

	def updatePropBox(self,mat,propbox):
		propbox.update()
		setColorButton(mat.getAmbient(),propbox.chooseAmbient)
		setColorButton(mat.getSpecular(),propbox.chooseSpecular)
		setColorButton(mat.getEmissive(),propbox.chooseEmissive)
		setColorButton(mat.getDiffuse(),propbox.chooseDiffuse)

		propbox.shininessBox.setValue(mat.getShininess())
		propbox.alphaBox.setValue(mat.getAlpha())

		propbox.minSizeBox.setValue(mat.getPointSizeMin())
		propbox.maxSizeBox.setValue(mat.getPointSizeMax())
		propbox.absSizeBox.setValue(mat.getPointSizeAbs())
		propbox.setPointRelativeChecked(mat.usesPointAttenuation())

		setChecked(mat.usesLighting(),propbox.useLightingCheck)
		setChecked(mat.usesFlatShading(),propbox.flatShadingCheck)
		setChecked(mat.usesVertexColor(),propbox.useVertexCheck)
		setChecked(mat.usesPointSprites(),propbox.useSpritesCheck)
		setChecked(mat.isCullBackfaces(),propbox.cullBackfacesCheck)
		setChecked(mat.usesDepthCheck(),propbox.depthCheck)
		setChecked(mat.usesDepthWrite(),propbox.depthWriteCheck)
		setChecked(mat.usesTexFiltering(),propbox.texFilterCheck)

		fillList(propbox.spectrumList,self.mgr.listSpectrumNames())

		propbox.fillTextureList(self.mgr.listTextureNames(),mat.getTexture())
		propbox.fillFragmentList(self.mgr.listGPUProgramNames(PT_FRAGMENT),mat.getGPUProgram(PT_FRAGMENT))
		propbox.fillVertexList(self.mgr.listGPUProgramNames(PT_VERTEX),mat.getGPUProgram(PT_VERTEX))
		propbox.fillGeomList(self.mgr.listGPUProgramNames(PT_GEOMETRY),mat.getGPUProgram(PT_GEOMETRY))

	def _chooseColor(self,origcolor,callback,mat,propbox):
		self.win.chooseRGBColorDialog(origcolor,lambda c:callback(color(*c)))
		self.updatePropBox(mat,propbox)
		self.mgr.repaint()

	def _chooseTexture(self,i,mat,propbox):
		mat.setTexture('' if i==0 else str(propbox.textureList.currentText()))
		self.mgr.repaint()

	def _chooseGPUProgram(self,i,mat,listbox,ptype):
		mat.setGPUProgram('' if i==0 else str(listbox.currentText()),ptype)
		self.mgr.repaint()
		
	def _setSpectrum(self,mat,propbox):
		spec=self.mgr.getSpectrum(propbox.spectrumList.currentText())
		mat.copySpectrumFrom(spec)
		propbox.repaint()

	def getScriptCode(self,mat,**kwargs):
		namemap=kwargs.get('namemap',{mat:'mat'})
		varname=namemap[mat]
		code=''

		args={
			'varname':varname,
			'getAmbient':mat.getAmbient(),
			'getDiffuse':mat.getDiffuse(),
			'getAmbient':mat.getAmbient(),
			'getDiffuse':mat.getDiffuse(),
			'getSpecular':mat.getSpecular(),
			'getEmissive':mat.getEmissive(),
			'getShininess':mat.getShininess(),
			'getPointSizeMin':mat.getPointSizeMin(),
			'getPointSizeMax':mat.getPointSizeMax(),
			'getPointSizeAbs':mat.getPointSizeAbs(),
			'usesPointAttenuation':mat.usesPointAttenuation(),
			'usesVertexColor':mat.usesVertexColor(),
			'usesDepthCheck':mat.usesDepthCheck(),
			'usesDepthWrite':mat.usesDepthWrite(),
			'usesTexFiltering':mat.usesTexFiltering(),
			'isClampTexAddress':mat.isClampTexAddress(),
			'usesFlatShading':mat.usesFlatShading(),
			'usesLighting':mat.usesLighting(),
			'isCullBackfaces':mat.isCullBackfaces(),
			'usesPointSprites':mat.usesPointSprites(),
			'getAlpha':mat.getAlpha(),
			'usesInternalAlpha':mat.usesInternalAlpha(),
		}

		if kwargs.get('createCode',True):
			code+='%(varname)s=mgr.createMaterial("%(varname)s")'

		code+='''
			%(varname)s.setAmbient(%(getAmbient)r)
			%(varname)s.setDiffuse(%(getDiffuse)r)
			%(varname)s.setSpecular(%(getSpecular)r)
			%(varname)s.setEmissive(%(getEmissive)r)
			%(varname)s.setShininess(%(getShininess)r)
			%(varname)s.setPointSize(%(getPointSizeMin)r,%(getPointSizeMax)r)
			%(varname)s.setPointSizeAbs(%(getPointSizeAbs)r)
			%(varname)s.setPointAttenuation(%(usesPointAttenuation)r)
			%(varname)s.useVertexColor(%(usesVertexColor)r)
			%(varname)s.useDepthCheck(%(usesDepthCheck)r)
			%(varname)s.useDepthWrite(%(usesDepthWrite)r)
			%(varname)s.useTexFiltering(%(usesTexFiltering)r)
			%(varname)s.clampTexAddress(%(isClampTexAddress)r)
			%(varname)s.useFlatShading(%(usesFlatShading)r)
			%(varname)s.useLighting(%(usesLighting)r)
			%(varname)s.cullBackfaces(%(isCullBackfaces)r)
			%(varname)s.usePointSprites(%(usesPointSprites)r)
			%(varname)s.setAlpha(%(getAlpha)r)
			%(varname)s.useInternalAlpha(%(usesInternalAlpha)r)
		'''

		code=setStrIndent(code % args).strip()+'\n'

		tex=mat.getTexture()
		if len(tex)>0:
			code+='%s.setTexture(%r)\n' %(varname,tex)

		vert=mat.getGPUProgram(PT_VERTEX)
		if len(vert)>0:
			code+='%s.setGPUProgram(%r,PT_VERTEX)\n'%(varname,vert)

		frag=mat.getGPUProgram(PT_FRAGMENT)
		if len(frag)>0:
			code+='%s.setGPUProgram(%r,PT_FRAGMENT)\n'%(varname,frag)

		geom=mat.getGPUProgram(PT_GEOMETRY)
		if len(geom)>0:
			code+='%s.setGPUProgram(%r,PT_GEOMETRY)\n'%(varname,geom)

		for i in xrange(mat.numSpectrumValues()):
			code+='%s.addSpectrumValue(%r,%r)\n' %(varname,mat.getSpectrumPos(i),mat.getSpectrumValue(i))

		for i in xrange(mat.numAlphaCtrls()):
			code+='%s.addAlphaCtrl(%r)\n' %(varname,mat.getAlphaCtrl(i))

		return code


class LightController(object):
	def __init__(self,mgr,win):
		self.mgr=mgr
		self.win=win

	def addLight(self,light):
		assert isMainThread()
		if not self.win:
			return

		self.win.addLight(light,self._updateLightPropBox)
		prop=self.win.findPropBox(light)

		prop.visibleBox.clicked.connect(lambda i: light.setVisible(not light.isVisible) or self.mgr.repaint())

		prop.spotRadio.clicked.connect(lambda b:self.setLightType(light,LightType._spot))
		prop.pointRadio.clicked.connect(lambda b:self.setLightType(light,LightType._point))
		prop.dirRadio.clicked.connect(lambda b:self.setLightType(light,LightType._dir))

		def setColor(col):
			col=color(*col)
			#setColorSelector(col,prop.camlightBox,prop.camlightText)
			setColorButton(col,prop.chooseCamlight)
			light.setColor(col)
			self.mgr.repaint()

		prop.chooseCamlight.clicked.connect(lambda:self.win.chooseRGBColorDialog(light.color,setColor))

		prop.orientedBox.clicked.connect(lambda i: self.toggleCameraOriented(light,prop))
		prop.theta.valueChanged.connect(lambda i: light.setCameraAngles(i,light.phi) or self.mgr.repaint())
		prop.phi.valueChanged.connect(lambda i: light.setCameraAngles(light.theta,i) or self.mgr.repaint())

		prop.posx.valueChanged.connect(lambda:self.setPosition(light,prop))
		prop.posy.valueChanged.connect(lambda:self.setPosition(light,prop))
		prop.posz.valueChanged.connect(lambda:self.setPosition(light,prop))
		prop.dirx.valueChanged.connect(lambda:self.setDirection(light,prop))
		prop.diry.valueChanged.connect(lambda:self.setDirection(light,prop))
		prop.dirz.valueChanged.connect(lambda:self.setDirection(light,prop))

		prop.lrange.valueChanged.connect(lambda:self.setAttenuation(light,prop))
		prop.lconst.valueChanged.connect(lambda:self.setAttenuation(light,prop))
		prop.linear.valueChanged.connect(lambda:self.setAttenuation(light,prop))
		prop.quad.valueChanged.connect(lambda:self.setAttenuation(light,prop))

		prop.spotangle.valueChanged.connect(lambda:self.setSpotValues(light,prop))
		prop.falloff.valueChanged.connect(lambda:self.setSpotValues(light,prop))

	def removeLight(self,light):
		pass

	def toggleCameraOriented(self,sl,prop):
		lt=sl.lighttype
		if lt==LightType._dir:
			sl.setLightType(LightType._cdir)
		elif lt==LightType._cdir:
			sl.setLightType(LightType._dir)
		elif lt==LightType._cpoint:
			sl.setLightType(LightType._point)
		elif lt==LightType._point:
			sl.setLightType(LightType._cpoint)
		elif lt==LightType._cspot:
			sl.setLightType(LightType._spot)
		elif lt==LightType._spot:
			sl.setLightType(LightType._cspot)

		self._updateLightPropBox(sl,prop)
		self.mgr.repaint()

	def setLightType(self,sl,lt):
		isCamOriented=sl.lighttype in (LightType._cdir,LightType._cspot,LightType._cpoint)

		if lt==LightType._dir:
			sl.setLightType(LightType._cdir if isCamOriented else LightType._dir)
		elif lt==LightType._point:
			sl.setLightType(LightType._cpoint if isCamOriented else LightType._point)
		elif lt==LightType._spot:
			sl.setLightType(LightType._cspot if isCamOriented else LightType._spot)

		self.mgr.repaint()

	def setPosition(self,sl,prop):
		sl.setPosition(vec3(*prop.getPosition()))
		self.mgr.repaint()

	def setDirection(self,sl,prop):
		sl.setDirection(vec3(*prop.getDirection()))
		self.mgr.repaint()

	def setAttenuation(self,sl,prop):
		vals=mapWidgetValues(prop)
		sl.setAttenuation(vals['lrange'],vals['lconst'],vals['linear'],vals['quad'])
		self.mgr.repaint()

	def setSpotValues(self,sl,prop):
		vals=mapWidgetValues(prop)
		sl.setSpotValues(vals['spotangle'],vals['falloff'])
		self.mgr.repaint()

	def _updateLightPropBox(self,light,propbox):
		isCamOriented=light.lighttype in (LightType._cdir,LightType._cpoint,LightType._cspot)

		props={
			'theta':light.theta,
			'phi':light.phi,
			'lrange':light.lrange,
			'lconst':light.const,
			'linear':light.linear,
			'quad':light.quad,
			'visibleBox':light.isVisible,
			'orientedBox':isCamOriented,
			'spotangle':light.spotangle,
			'falloff':light.falloff,
		}

		if isCamOriented:
			props.update({
				'posx':0.0,'posy':0.0,'posz':0.0,
				'dirx':0.0,'diry':0.0,'dirz':0.0
			})
		else:
			lpos=light.position
			ldir=light.direction

			props.update({
				'posx':lpos.x(), 'posy':lpos.y(), 'posz':lpos.z(),
				'dirx':ldir.x(), 'diry':ldir.y(), 'dirz':ldir.z()
			})

		if light.lighttype in (LightType._cpoint,LightType._point):
			props['pointRadio']=True
		elif light.lighttype in (LightType._cdir,LightType._dir):
			props['dirRadio']=True
		elif light.lighttype in (LightType._cspot,LightType._spot):
			props['spotRadio']=True

		#setColorSelector(light.color,propbox.camlightBox,propbox.camlightText)
		setColorButton(light.color,propbox.chooseCamlight)
		setWidgetValues(propbox,props)


class GPUProgramController(object):
	def __init__(self,mgr,win):
		self.mgr=mgr
		self.win=win

	def addProgram(self,prog):
		assert isMainThread()
		if not self.win:
			return

		self.win.addGPUProgram(prog,self._updateProgPropBox)
		prop=self.win.findPropBox(prog)

		prop.setSrcButton.clicked.connect(lambda: self._setSourceCode(prog,prop))
		prop.undoButton.clicked.connect(lambda: prop.setSourceCode(prog.getSourceCode(),True))
		prop.applyButton.clicked.connect(lambda: self._applySettingChanges(prog,prop))

	def removeProgram(self,prog):
		pass

	def _updateProgPropBox(self,prog,propbox):
		propbox.setSourceCode(prog.getSourceCode())
		propbox.langEdit.setText(prog.getLanguage())
		propbox.entryEdit.setText(prog.getEntryPoint())
		propbox.profEdit.setText(prog.getProfiles())

		ptype=prog.getType()
		if ptype==PT_VERTEX:
			propbox.typeBox.setCurrentIndex(0)
		elif ptype==PT_FRAGMENT:
			propbox.typeBox.setCurrentIndex(1)
		elif ptype==PT_GEOMETRY:
			propbox.typeBox.setCurrentIndex(2)

	def _setSourceCode(self,prog,propbox):
		prog.setSourceCode(str(propbox.getSourceCode()))
		propbox.setSrcStatus(not prog.hasError())
		self.mgr.repaint()

	def _applySettingChanges(self,prog,propbox):
		ind=propbox.typeBox.currentIndex()
		#ptypetext=str(propbox.typeBox.currentText())

		ptype=PT_VERTEX
		if ind==1:
			ptype=PT_FRAGMENT
		elif ind==2:
			ptype=PT_GEOMETRY

		#lang=str(propbox.langEdit.text()).strip()
		entry=str(propbox.entryEdit.text()).strip()
		prof=str(propbox.profEdit.text()).strip()
		isChanged=False

		if prog.getEntryPoint().strip()!=entry:
			isChanged=True
			prog.setEntryPoint(entry)

		if prog.getProfiles().strip()!=prof:
			isChanged=True
			prog.setProfiles(prof)

		if prog.getType()!=ptype:
			isChanged=True
			prog.setType(ptype)

		#if prog.getLanguage().strip()!=lang:
		#	isChanged=True
		#	prog.setLanguage(lang)

		if isChanged:
			prog.setSourceCode(prog.getSourceCode())
			self.mgr.repaint()


class SingleCameraController(object):
	'''
	Implements a Z-locked camera controller, where Z is always up on screen. This means that the scene
	must first be rotated from the default orientation with Z pointing towards the camera, this is done
	by adding pi/2 to phi when constructing the Y-axis rotator.
	'''
	def __init__(self,camera,dist,zScale=1.0,tScale=1.0,rScale=1.0):
		self.camera=camera
		self.dist=dist
		self.zScale=zScale # zoom values scaled by this 
		self.rScale=rScale # rotational angle values scaled by this
		self.tScale=tScale # translation values scaled by this
		self.radiusPower=0 # the closest power of 10 encompassing the scene, used to scale various parameters by scene size

		self.prevX=-1 # screen coordinates when mouse pressed/moved
		self.prevY=-1

		self.pos=vec3(0,0,0) # position of controller, the look-at location
		self.campos=vec3(0,0,0) # position of camera, set by _setCamera

		self._isZLocked=True # True if Z-axis is always up, otherwise permit free rotation

		self.freerotator=rotator() # rotator representing a free rotation, only meaningful if isZLocked() is False

		# rotational values for determining placement and rotation when isZLocked() is True
		self.theta=0.0 # rotational angle
		self.phi=0.0 # elevation angle
		self.rho=0.0 # roll angle

		self.phisub=0.0005 # value to reduce phi angle by to prevent flipping when aligned with the Z axis

		self._setCamera()

	def start(self,mgr):
		mgr.addEventHandler(EventType._widgetResize,self._resizeCB)
		mgr.addEventHandler(EventType._mousePress,self._mousePressCB)
		mgr.addEventHandler(EventType._mouseMove,self._mouseMoveCB)
		mgr.addEventHandler(EventType._mouseWheel,self._mouseWheelCB)

	def stop(self,mgr):
		mgr.removeEventHandler(self._resizeCB)
		mgr.removeEventHandler(self._mousePressCB)
		mgr.removeEventHandler(self._mouseMoveCB)
		mgr.removeEventHandler(self._mouseWheelCB)

	def reset(self):
		self.freerotator=rotator()
		self.theta=0.0
		self.phi=0.0
		self.rho=0.0
		self._setCamera()

	def _resizeCB(self,w,h):
		self.setAspectRatio(1 if h==0 else (float(w)/float(h)))

	def _mousePressCB(self,e):
		self.prevX=e.x()
		self.prevY=e.y()

	def _mouseMoveCB(self,e):
		dx=e.x()-self.prevX
		dy=e.y()-self.prevY

		if e.buttons()==Qt.LeftButton:
			if self._isZLocked:
				if e.modifiers()==Qt.ShiftModifier:
					self.rho+=dx*0.01
					self._setCamera()
				else:
					self.rotate(dx,dy)
			else:
				rot=self.getRotator()
				if e.modifiers()==Qt.ShiftModifier:
					dr=rotator(rot*vec3(0,1,0),dx*0.01)
				else:
					dr=rotator(rot*vec3(1,0,0),-dy*0.01)*rotator(rot*vec3(0,0,1),-dx*0.01)

				self.rotate(dr)

		elif e.buttons()==Qt.MiddleButton:
			self.zoom(dy)
		elif e.buttons()==Qt.RightButton:
			self.translate(-dx,0,dy)
		elif e.buttons()==Qt.LeftButton|Qt.RightButton:
			self.translate(0,-dy,0)

		self.prevX=e.x()
		self.prevY=e.y()

	def _mouseWheelCB(self,e):
		self.zoom(e.delta()/-2)

	def getPropTuples(self):
		return [
			('Type','Single'),
			('rot',u'%.4f (%.4f\u03c0)'%(self.theta,self.theta/math.pi)),
			('elev',u'%.4f (%.4f\u03c0)'%(self.phi,self.phi/math.pi)),
			('Lookat Pos',vec3SimpleStr(self.pos)),
			('Zoom','%.4f'%(self.dist,)),
			('Camera Pos',vec3SimpleStr(self.campos)),
		]

	def setZLocked(self,zlock):
		self.freerotator=self.getRotator()
		self._isZLocked=zlock
		self._setCamera()

	def isZLocked(self):
		return self._isZLocked

	def setSeeAllBoundBox(self,bb):
		radius=max(0.0001,bb.radius)
		self.pos=bb.center
		self.dist=(radius*0.5)/math.tan(self.camera.getVertFOV()*0.5)+radius*1.5
		self.zScale=radius*0.005
		self.tScale=radius*0.00125
		self.radiusPower=getClosestPower(radius)-1

		self.camera.setNearClip(clamp(radius*0.05,epsilon*100,1.0))
		self.camera.setFarClip(clamp(self.dist*10,2000.0,10000000.0))

		self._setCamera()

	def setVertFOV(self,fov):
		self.camera.setVertFOV(fov)

	def setNearClip(self,clip):
		self.camera.setNearClip(clip)

	def setFarClip(self,clip):
		self.camera.setFarClip(clip)

	def getVertFOV(self):
		return self.camera.getVertFOV()

	def getNearClip(self):
		return self.camera.getNearClip()

	def getFarClip(self):
		return self.camera.getFarClip()

	def setOrtho(self,ortho):
		self.camera.setOrtho(ortho)

	def setWireframe(self,wire):
		self.camera.setWireframe(wire)

	def setAspectRatio(self,aspect):
		self.camera.setAspectRatio(aspect)
		self.camera.setViewport()

	def _setCamera(self):
		rot=self.getRotator()
		self.campos=(rot*vec3(0,-self.dist,0))+self.pos
		self._orientCamera(self.camera,self.campos,self.pos,rot)

	def _orientCamera(self,cam,pos,lookat,rot):
		cam.setPosition(pos+vec3(0.0001,0.0,0.0)) # (?) having to add topos to get over some numerical problem with double==real
		cam.setLookAt(lookat)
		if self._isZLocked:
			cam.setZUp()
			cam.rotate(rotator(rot*vec3(0,1,0),self.rho))
		else:
			cam.setRotation(rot*rotator(vec3(1,0,0),halfpi))

	def setCameraLight(self,light):
		if light.lighttype==LightType._cdir:
			ld=self.getRotator()*vec3(light.theta+halfpi,light.phi+halfpi,1).fromPolar()

			light.setPosition(self.campos)
			light.setDirection(ld)
		elif light.lighttype in (LightType._cspot, LightType._cpoint):
			ld=self.getRotator()*vec3(light.theta+halfpi,light.phi+halfpi,1).fromPolar()

			light.setPosition(self.campos)
			light.setDirection(ld)
		else:
			pass

	def translate(self,dx,dy,dz):
		'''Translate relative to the initial orientation (Y-forward, Z-up) rotated by the camera's rotator.'''
		rot=self.getRotator()
		self.setPosition(self.pos+(rot*vec3(dx*self.tScale,dy*self.tScale,dz*self.tScale)))

	def rotate(self,dx_r,dy=0):
		'''Rotate the camera using the given arguments. If the camera is Z-locked (isZLocked() is True), `dx_r' is a
		float value scaled by self.rScale*0.005 then added to self.theta and `dy' is also a float scaled by
		self.rScale*0.005 then added to self.phi. If the camera is not Z-locked, `dx_r' is a rotator applied to the
		camera's rotation.
		'''
		if self._isZLocked:
			self.setRotation(self.theta+float(dx_r)*0.005*self.rScale,self.phi+float(dy)*0.005*self.rScale)
		else:
			self.setRotation(dx_r*self.freerotator)

	def zoom(self,dist):
		'''Add `dist`*self.zScale to the view distance.'''
		self.setZoom(max(5*self.zScale,(dist*self.zScale)+self.dist))

	def setPosition(self,pos):
		'''Sets the look-at position to `pos'.'''
		self.pos=pos
		self._setCamera()

	def setRotation(self,theta_r,phi=0):
		'''
		Sets rotational parameters. If isZLocked() is True, `theta_r' and  `phi' are polar rotation values, these are
		used to set self.theta and self.phi contrained within their respective ranges and tolerances. If isZLocked()
		is False then `theta_r' is a rotator which is assigned to self.freerotator.
		'''
		if self._isZLocked:
			self.theta=radCircularConvert(theta_r)
			self.phi=radClamp(phi)
			self.phi+=self.phisub*(-1 if self.phi>0 else 1)
		else:
			if isinstance(theta_r,rotator):
				self.freerotator=theta_r
			else:
				self.freerotator=rotator(vec3(0,0,1),theta_r)
		self._setCamera()

	def setZoom(self,dist):
		'''Sets the distance from the look-at position to max(0,001,`dist').'''
		self.dist=max(0.0001,dist)
		self._setCamera()

	def getPosition(self):
		'''Returns the look-at position.'''
		return self.pos

	def getCameraPosition(self):
		'''Returns the camera's position.'''
		return self.campos

	def getZoom(self):
		'''Returns the zoom distance.'''
		return self.dist

	def getRotator(self):
		'''
		Get the rotator for the camera based on self.theta and self.phi or self.freerotator. This represents the
		rotation applied to orient the camera to face the look at position and a given up direction from the initial
		position as defined by this controller.
		'''
		if self._isZLocked:
			rot=rotator(vec3(0,0,1),-self.theta)
			return rotator(rot*vec3(1,0,0),-self.phi)*rot
		else:
			return self.freerotator

	def getCameraRotation(self):
		'''Returns the rotation applied to the camera.'''
		return self.camera.getRotation()


class AxesCameraController(SingleCameraController):
	'''Derived controller with figures for axes and center markers.'''

	def __init__(self,camera,dist,zScale=1.0,tScale=1.0,rScale=1.0):
		self.axesFigs=[]
		self.axestype=None
		self.axesMat=None
		self.axesCam=None

		self.centerFigs=[]
		self.centerMat=None

		SingleCameraController.__init__(self,camera,dist,zScale,tScale,rScale)

	def getPropTuples(self):
		tuples=SingleCameraController.getPropTuples(self)
		tuples+=[
			('Axes Len',str(10**self.radiusPower)),
			#('Axes Len',str(20*self.zScale))
		]

		return tuples

	def setCenterType(self,scene,centertype,dims=None):
		assert scene
		assert not centertype or centertype in CenterType, 'Unknown center type '+str(centertype)

		if not centertype:
			centertype=CenterType._none

		if not self.centerMat:
			self.centerMat=scene.createMaterial('CenterMat')

		self.centerMat.useLighting(True)
		self.centerMat.useInternalAlpha(False)
		self.centerMat.setDiffuse(color(1.0,1.0,1.0,0.5))
		self.centerMat.setAmbient(color(1.0,1.0,1.0,0.5))
		self.centerMat.useVertexColor(True)

		del self.centerFigs[:]

		if centertype==CenterType._point:
			self.centerFigs=[self._generateSphereFig(scene)]
		elif centertype==CenterType._centerarrows:
			self.centerFigs=self._generateAxesArrows(scene,'CenterMat','Center',True)

		return self.centerFigs

	def setAxesType(self,scene,axestype,dims=None):
		assert scene
		assert not axestype or axestype in AxesType, 'Unknown axes type '+str(axestype)

		if not axestype:
			axestype=AxesType._none

		self.axestype=axestype

		self.axesCam=None
		self.axesFigs=[]

		if not self.axesMat:
			self.axesMat=scene.createMaterial('AxesMat')

		self.axesMat.useLighting(True)
		self.axesMat.useVertexColor(True)
		#self.axesMat.useDepthWrite(False)

		if axestype == AxesType._originarrows:
			self.axesFigs=self._generateAxesArrows(scene,'AxesMat',makeoffset=True)
		elif axestype!=AxesType._none:
			left=0 if axestype in (AxesType._cornerTL,AxesType._cornerBL) else 0.8
			top=0 if axestype in (AxesType._cornerTL,AxesType._cornerTR) else 0.8

			self.axesFigs=self._generateAxesArrows(scene,'AxesMat')

			self.axesCam=scene.createCamera('AxesCam',left,top,0.2,0.2)
			self.axesCam.setBGColor(color(0,0,0,0))
			self.axesCam.setSecondaryCamera(True)
			self.axesCam.setAspectRatio(self.camera.getAspectRatio())

			self.axesMat.useLighting(False)

			for f in self.axesFigs:
				f.setCameraVisibility(None,False)
				f.setCameraVisibility(self.axesCam,True)

		return self.axesFigs

	def _generateAxesArrows(self,scene,matname,nameprefix='',makeoffset=False):
		offsetvec=vec3(0,0,1) if makeoffset else vec3()
		nodesz,indices=generateArrow(5)
		nodesz=[(n*vec3(0.25,0.25,1))+offsetvec for n in nodesz] # shrink and move Z-aligned arrow
		nodesx=[rotator(vec3(0,1,0),halfpi)*n for n in nodesz]
		nodesy=[rotator(vec3(1,0,0),-halfpi)*n for n in nodesz]

		normsz=generateTriNormals(nodesz,indices)
		normsx=generateTriNormals(nodesx,indices)
		normsy=generateTriNormals(nodesy,indices)

		vbufz=PyVertexBuffer(nodesz,normsz,[color(0,0,1,0.5)]*len(nodesz))
		vbufx=PyVertexBuffer(nodesx,normsx,[color(1,0,0,0.5)]*len(nodesx))
		vbufy=PyVertexBuffer(nodesy,normsy,[color(0,1,0,0.5)]*len(nodesy))

		axesFigs=[
			scene.createFigure(nameprefix+'axesZ',matname,FT_TRILIST),
			scene.createFigure(nameprefix+'axesX',matname,FT_TRILIST),
			scene.createFigure(nameprefix+'axesY',matname,FT_TRILIST)
		]

		ibuf=PyIndexBuffer(indices)

		axesFigs[0].setOverlay(True)
		axesFigs[1].setOverlay(True)
		axesFigs[2].setOverlay(True)

		axesFigs[0].fillData(vbufz,ibuf)
		axesFigs[1].fillData(vbufx,ibuf)
		axesFigs[2].fillData(vbufy,ibuf)

		if not makeoffset:
			axesFigs[0].setPosition(vec3(0,0,1))
			axesFigs[1].setPosition(vec3(1,0,0))
			axesFigs[2].setPosition(vec3(0,1,0))

		return axesFigs

	def _generateSphereFig(self,scene):
		nodes,indices=generateSphere(1)
		norms=generateTriNormals(nodes,indices)
		fig=scene.createFigure('CenterSphere','CenterMat',FT_TRILIST)
		fig.setOverlay(True)
		fig.fillData(PyVertexBuffer(nodes,norms,None),PyIndexBuffer(indices))
		return fig

	def setAspectRatio(self,aspect):
		SingleCameraController.setAspectRatio(self,aspect)
		if self.axesCam:
			self.axesCam.setAspectRatio(aspect)

	def _setCamera(self):
		SingleCameraController._setCamera(self)
		rot=self.getRotator()

		if self.axesCam: # move the axis camera to match the real camera
			self._orientCamera(self.axesCam,(rot*vec3(0,-5,0)),vec3(),rot)
		else: # if there's no axis camera then origin arrows are used, scale these accordingly
			for f in self.axesFigs:
				f.setScale(vec3(0.5* 10**self.radiusPower))

		for f in self.centerFigs:
			f.setPosition(self.pos)
			f.setScale(vec3(0.5* 10**self.radiusPower))


class ScriptWriter(object):
	'''
	This class generates Python code to recreate the current scene as defined by the SceneManager object passed to it.
	This relies on plugins implementing getScriptCode() correctly to generate plugin-specific loading and setup code 
	when requested by this type. 
	'''
	
	def __init__(self,target=None,scriptdir=None):
		'''
		Initialize the writer with `target' being the file-like object to write text into, or an instance of StringIO
		if this isn't provided. The `scriptdir' path is directory the script file being written will be in, this is
		None if writing non-script code. If `scriptdir' is present then all paths should be written relative to it.
		'''
		self.scriptHeader='from eidolon import *\n'
		self.writeComments=True
		self.namemap={}
		self.includedObjs=None
		self.scriptdir=os.path.abspath(scriptdir) if scriptdir else None 
		self.target=target or StringIO.StringIO()

	def addVar(self,name,val):
		self.namemap[val]=name
		
	def convertPath(self,path):
		if not path:
			return '""'

		path=os.path.abspath(path)
		if self.scriptdir and path.startswith(self.scriptdir):
			return 'scriptdir+%r'%os.path.relpath(path,self.scriptdir)
		else:
			return '%r'%path

	def writeLine(self,line=''):
		self.target.write(str(line)+'\n')

	def writeObjectComment(self,label,obj):
		self.writeLine('##%s %s %s %s'%(label,self.namemap[obj],obj.getLabel(),str(type(obj))))

	def writeCreateObject(self,obj):
		isRepr=isinstance(obj,SceneObjectRepr)
		code=obj.plugin.getScriptCode(obj,scriptdir=self.scriptdir,convertPath=self.convertPath,namemap=self.namemap)
		self.writeObjectComment('CR' if isRepr else 'CO',obj)
		if len(code)>0:
			self.writeLine(code.rstrip())
			func='addSceneObjectRepr' if isRepr else 'addSceneObject'
			self.writeLine('mgr.%s(%s)'%(func,self.namemap[obj]))

		self.writeLine()

	def writeSetupObject(self,obj):
		code=obj.plugin.getScriptCode(obj,scriptdir=self.scriptdir,convertPath=self.convertPath,namemap=self.namemap,configSection=True)
		self.writeObjectComment('SR' if isinstance(obj,SceneObjectRepr) else 'SO',obj)
		if len(code)>0:
			self.writeLine(code.rstrip())

		self.writeLine()

	def writeMaterial(self,mgr,mat):
		self.writeLine(mgr.matcontrol.getScriptCode(mat,namemap=self.namemap))

	def writeObjects(self,mgr,objs):
		# create all scene objects
		for o in objs:
			if isinstance(o,SceneObject):
				self.writeCreateObject(o)

		# configure all scene objects
		for o in objs:
			if isinstance(o,SceneObject):
				self.writeSetupObject(o)

		# create all representations
		for o in objs:
			if isinstance(o,SceneObjectRepr):
				self.writeCreateObject(o)

		# configure all representations
		for o in objs:
			if isinstance(o,SceneObjectRepr):
				self.writeSetupObject(o)

	def writeScene(self,mgr):
		if self.includedObjs==None:
			self.includedObjs=list(mgr.enumSceneObjects())+list(mgr.enumSceneObjectReprs())

		usedmats=[]

		for rep in mgr.enumSceneObjectReprs():
			matname=rep.getMaterialName()
			mat=mgr.getMaterial(matname)
			if mat!=None and mat not in self.namemap and rep in self.includedObjs:
				self.namemap[mat]=uniqueStr('mat',self.namemap.values(),'')
				self.namemap[matname]=self.namemap[mat]
				usedmats.append(mat)

		for o in self.includedObjs:
			if o not in self.namemap:
				prefix='obj' if isinstance(o,SceneObject) else 'rep'
				self.namemap[o]=uniqueStr(prefix,self.namemap.values(),'')

		self.writeLine('## Header')
		self.writeLine(self.scriptHeader)

		self.writeLine('## Material Setup')
		for mat in usedmats:
			self.writeMaterial(mgr,mat)

		self.writeObjects(mgr,self.includedObjs)

		self.writeLine('## Scene Setup')
		if mgr.controller==mgr.singleController:
			self.writeLine('mgr.setSingleFreeCamera()')

		self.writeLine('mgr.setCameraOrtho(%r)' % mgr.win.orthoCheck.isChecked())
		self.writeLine('mgr.setBackgroundColor(%r)' % mgr.backgroundColor)
		self.writeLine('mgr.setAmbientLight(%r)' % mgr.ambientColor)

		for tex in mgr.textures:
			name=tex.getFilename()
			if os.path.isfile(name):
				self.writeLine('mgr.loadTextureFile(%r)' % name)

		if mgr.timestepMax>mgr.timestepMin:
			self.writeLine('mgr.setTimeFPS(%s)' % mgr.timeFPS)
			self.writeLine('mgr.setTimeStepsPerSec(%s)'% mgr.timeStepsPerSec)

		self.writeLine()
		self.writeLine('mgr.setCameraSeeAll()')



