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


'''
This defines the SceneObject and SceneObjectRepr objects and derivatives. These represent scene data and visual
representations of that data respectively.
'''

import functools
import inspect

from renderer import vec3, color, rotator, transform, FT_POINTLIST, FT_LINELIST, FT_TRILIST, FT_GLYPH, \
        IndexMatrix, ColorMatrix,MatrixIndexBuffer, MatrixVertexBuffer, PyIndexBuffer, PyVertexBuffer
from .Utils import enum, avgspan, first, toIterable, listSum, minmax, clamp,radCircularConvert, isMainThread
from .SceneUtils import StdProps, MatrixType, getDatasetSummaryTuples, BoundBox

from . import MeshAlgorithms, MathDef, Utils
    

# Known representation types: description, generator function, FigureType, is Point type, is Polygon type
ReprType=enum(
    # Mesh types
    ('node','Element Nodes',MeshAlgorithms.generateNodeDataSet,FT_POINTLIST,True,False),
    ('point','Points',MeshAlgorithms.generatePointDataSet,FT_POINTLIST,True,False),
    ('line', 'Lines',MeshAlgorithms.generateLineDataSet,FT_LINELIST,False,False),
    ('volume','Mesh Volumes',MeshAlgorithms.generateTriDataSet,FT_TRILIST,False,True),
    ('surface','Mesh Surfaces',MeshAlgorithms.generateTriDataSet,FT_TRILIST,False,True),
    ('cylinder','Cylinders',MeshAlgorithms.generateCylinderDataSet,FT_TRILIST,False,True),
    ('isosurf','Isosurfaces',MeshAlgorithms.generateIsosurfaceDataSet,FT_TRILIST,False,True),
    ('isoline','Isolines',MeshAlgorithms.generateIsolineDataSet,FT_TRILIST,False,True),
    ('glyph','Glyphs',MeshAlgorithms.generateGlyphDataSet,FT_GLYPH,True,False),
#   ('ribbon','Ribbons',generateRibbonDataSet,FT_RIBBON,False,False),
#   ('bbpoint','Billboard Points',generateBillboardDataSet,FT_BB_POINT,True,False),
#   ('bbline','Billboard Lines',generateBillboardDataSet,FT_BB_FIXED_PAR,True,False),
#   ('bbplane','Billboard Planes',generateBillboardDataSet,FT_BB_FIXED_PERP,True,False),
    # image types
    ('imgstack','Image Stack',None,None,False,False),
    ('imgtimestack','Timed Image Stack',None,None,False,False),
    ('imgvolume','Image Stack Volume',None,None,False,False),
    ('imgtimevolume','Timed Image Stack Volume',None,None,False,False),
    doc='Stores known representation types, their generating function, figure type, and if they are a point type.',
    #valtype=(str,type(lambda:None),FigureType,bool,bool),
)


class SceneObject(object):
    '''
    A SceneObject represents the data of a single notional object, for example the data for a model or all of the
    imaging slices for an image set. These are loaded from data sources by plugins or can be instantiated within
    scripts. In either case they must be added to the scene with SceneManager.addSceneObject() before they can be used
    for creating a representation. Once they have been added, they can produce instances of SceneObjectRepr to visually
    represent the data store. The representations are stored as children of the originating SceneObject.
    '''
    def __init__(self,name,plugin=None,**kwargs):
        assert name!=None

        self.name=name # object name
        self.reprs=[] # list of current representations
        self.reprcount=0 # number of representations created, used to ensure unique names
        self.plugin=plugin # plugin used to link interface and create representations
        self.kwargs=dict(kwargs) # keyword arguments passed in through the constructor
        self.reprtypes=[] # list of possible representation types
        self.proptuples=[] # list of cached property tuples, filled in by getPropTuples()
        
    def __getattr__(self,name):
        try:
            return self.__getattribute__(name)
        except AttributeError:
            # Search the base types of self.plugin for a method called `name', if found to be a 
            # delegated method in any of the types return the wrapped instance from self.plugin.
            for cls in inspect.getmro(type(self.plugin)):
                meth=getattr(cls,name,None)
                if getattr(meth,'__isdelegatedmethod__',False):
                    meth=getattr(self.plugin,name) # get meth again which will be different if overridden
                    return functools.partial(meth,self)
                
            raise # if no plugin method found, raise the exception

    def getLabel(self):
        '''Returns the UI label.'''
        return self.getName()

    def getPropTuples(self):
        '''
        Returns a list of name/value pairs listing the properties to display for this scene object in the UI. This can
        use self.proptuples as a cache for efficiency, so the method fills in self.proptuples if this attribute is
        empty and returns it thereafter.
        '''
        return []

    def getName(self):
        '''Returns the name of the object.'''
        return self.name

    def setName(self,name):
        '''Sets the name of the object.'''
        self.name=name

    def getReprTypes(self):
        '''Returns an iterable of ReprType names identifying valid representations of this object.'''
        self.reprtypes=self.reprtypes or self.plugin.getReprTypes(self)
        return self.reprtypes

    def removeRepr(self,rep):
        assert rep in self.reprs
        self.reprs.remove(rep)
        # store old representations for later?

    def getDataset(self):
        '''Returns the underlying data structures defining this object.'''
        pass

    def setTimestepList(self,tslist):
        '''Sets the timesteps for this object. The arguments `tslist' must have ascending values, one for each frame of data.'''
        pass

    def setTimestepScheme(self, starttime, interval):
        '''Set timestepping such that the first timestep is `starttime' and each subsequent step is `interval' forward in time.'''
        tslen=len(self.getTimestepList())
        self.setTimestepList([starttime+interval*i for i in range(tslen)])

    def getTimestepList(self):
        '''Returns the timestep values for each timestep of the object, or just [0] if it's not time-dependent.'''
        return [0]

    def getTimestepScheme(self):
        ts=self.getTimestepList()
        return ts[0],avgspan(ts) if len(ts)>1 else 0

    def __repr__(self):
        return '%s<%r @ 0x%.16x>'%(self.__class__.__name__,self.getName(),id(self))


class DatafileSceneObject(SceneObject):
    def __init__(self,name,filename,datamap,plugin,**kwargs):
        SceneObject.__init__(self,name,plugin,**kwargs)
        self.filename=filename
        self.datamap=datamap
        self._updatePropTuples()

    def _updatePropTuples(self):
        self.proptuples=[('Filename',str(self.filename))]
        if self.datamap:
            self.proptuples+=sorted((k,str(v)) for k,v in self.datamap.items())

    def getPropTuples(self):
        return self.proptuples

    def get(self,name,default=None):
        return self.datamap.get(name,default)

    def set(self,name,value):
        result=self.datamap[name]=value
        self._updatePropTuples()
        return result

    def load(self):
        if self.filename:
            self.datamap=Utils.readBasicConfig(self.filename)
            self._updatePropTuples()

    def save(self):
        if self.filename:
            Utils.storeBasicConfig(self.filename,self.datamap)
            

class SceneObjectRepr(object):
    '''
    A SceneObjectRepr encapsulates a single method of representing a SceneObject visually in the scene. It contains the
    information generated from the SceneObject's data which is sent to the renderer for drawing, and has the facilities
    controlling how it appears in the scene such as the use of materials. A representation can be a range of renderable
    concepts, such as a point list represented using points or billboards, line lists used to draw the outlines of
    figures, triangle meshes for rendering solid objects, texture planes for representing imaging data, and so forth.
    '''
    def __init__(self,parent,reprtype,reprcount,matname='Default'):
        self.parent=parent # parent SceneObject instance
        self.plugin=self.parent.plugin
        self.name=ReprType[reprtype][0]#+str(reprcount)
        self.matname=matname
        self.reprcount=reprcount
        self.reprtype=reprtype
        self._isVisible=False
        self.aabb=None # cached AABB object, set to None to force recalc

        self.rparent=None # parent SceneObjectRepr instance
        self.children=set()
        
    def __getattr__(self,name):
        try:
            return self.__getattribute__(name)
        except AttributeError:
            # Search the base types of self.plugin for a method called `name', if found to be a 
            # delegated method in any of the types return the wrapped instance from self.plugin.
            for cls in inspect.getmro(type(self.plugin)):
                meth=getattr(cls,name,None)
                if getattr(meth,'__isdelegatedmethod__',False):
                    meth=getattr(self.plugin,name) # get meth again which will be different if overridden
                    return functools.partial(meth,self)
                
            raise # if no plugin method found, raise the exception

    def isInScene(self):
        '''Returns true if this representation has been initialized and included into the scene, false otherwise.'''
        pass

    def getAABB(self,isTransformed=False,isDerived=True,recalculate=False):
        '''Returns the untransformed axis-aligned bound box enclosing the geometry of this representation.'''
        if recalculate or self.aabb==None:
            self.calculateAABB()

        if isTransformed and self.aabb:
            return self.aabb.transform(self.getTransform(isDerived))
        else:
            return self.aabb

    def calculateAABB(self):
        '''Recalculate the AABB after the data has changed.'''
        pass

    def getLabel(self):
        '''Returns the UI label, this may be different from the name and include additional information.'''
        return self.name+' <'+self.parent.name+'>'

    def getName(self):
        '''Returns the name of this representation.'''
        return self.name

    def setName(self,name):
        '''Sets the name of the object.'''
        self.name=name

    def getDataset(self):
        '''Returns the Dataset object for this representation, or whatever data object is used.'''
        return None

    def getMaterialName(self):
        '''Returns the applied material's name.'''
        return self.matname

    def setTimestep(self,ts):
        '''Set the current timestep to that which is nearest to `ts'.'''
        pass

    def getTimestep(self):
        '''Get the current timestep position.'''
        return 0

    def getTimestepList(self):
        '''Returns the list of timesteps, [0] for non-time-dependent objects.'''
        return [0]

    def getTimestepRange(self):
        '''Returns the timestep start and end values.'''
        ts=self.getTimestepList()
        return (ts[0],ts[-1])

    def getTimestepInterval(self):
        '''Returns the interval between timesteps.'''
        ts=self.getTimestepList()
        return (ts[-1]-ts[0])/len(ts)

    def getTimestepRepr(self,ts=0):
        '''
        Returns the subrepresentation at timestep `ts' or nearest if `ts' is non-integer. For non-time-dependent
        representations, this instead returns `self'.
        '''
        return self

    def setParent(self,prepr):
        '''
        Set this object's parent representation to `prepr'. This sets every internal figure to be a child of the
        first figure yielded by `prepr.enumFigures()'. This establishes a one-to-many relationship between objects
        such that an affine transformation performed on the parent is compounded with that applied to the child. In
        effect the child exists and is transformed in the local coordinates of its parent.

        If `prepr' is None then this representation will have no parent and its subfigures will be children of the
        root scene node only.
        '''

        if any(c==prepr for c in self.enumChildren(True)):
            raise Exception('Cannot set a parent which is a child of this representation.')

        p=self.getParent()
        while p!=None:
            if p==prepr:
                raise Exception('Cannot add a child which is a parent of this representation.')
            p=p.getParent()


        if self.rparent:
            self.rparent.removeChild(self)

        self.rparent=prepr

        if prepr:
            prepr.addChild(self)
            pfigure=first(prepr.enumFigures())
        else:
            pfigure=None

        for f in self.enumFigures():
            f.setParent(pfigure)

    def getParent(self):
        '''Returns the parent representation object.'''
        return self.rparent

    def enumChildren(self,allChildren=False):
        '''Yield every child of this object, descending depth first into the scene node tree if allChildren is true.'''
        for c in self.children:
            yield c
            if allChildren:
                for cc in c.enumChildren():
                    yield cc

    def addChild(self,child):
        '''Add a child to the internal children set, should only be called by setParent().'''
        self.children.add(child)

    def removeChild(self,child):
        '''Remove a child to the internal children set, should only be called by setParent().'''
        if child in self.children:
            self.children.remove(child)

    def enumSubreprs(self):
        '''
        Yield every internal sub-representation of this object excluding `self', or [`self'] if no internal
        representations are used in this type.
        '''
        return [self]

    def _getInteralFigures(self):
        return []

    def enumFigures(self):
        '''Yield every Figure object which comprises this representation.'''
        for f in self._getInteralFigures():
            yield f

        for r in self.enumSubreprs():
            if r==self:
                return
            for f in r.enumFigures():
                yield f

    def enumInternalMaterials(self):
        '''Yield every internal material (ie. created by this object) used to define this representation.'''
        return [] # default is to yield nothing, but don't return None or use 'pass'

    def addModifier(self,mod):
        pass

    def removeModifier(self,mod):
        pass

    def getParamDefs(self):
        '''Get the ParamDef objects describing the additional parameters to this representation.'''
        return []

    def getParam(self,name):
        '''Get the value of an additional parameter.'''
        rep=first(self.enumSubreprs())
        if rep and rep!=self:
            return rep.getParam(name)
        else:
            return None

    def setParam(self,name,value):
        '''Set the value of an additional parameter.'''
        for r in self.enumSubreprs():
            if r!=self:
                r.setParam(name,value)

    def setGPUParam(self, name,val, progtype,**kwargs):
        '''
        Sets the GPU program parameter `name' with value `val' for every internal material. The `progtype' value
        specifies which program type this is for. The value of `val' must be a vec3, real, int, long, or color.
        '''
        paramfunc=None
        if isinstance(val,vec3):
            paramfunc=lambda m,p,n,v:m.setGPUParamVec3(p,n,v)
        elif isinstance(val,color):
            paramfunc=lambda m,p,n,v:m.setGPUParamColor(p,n,v)
        elif isinstance(val,int):
            paramfunc=lambda m,p,n,v:m.setGPUParamInt(p,n,int(v))
        elif isinstance(val,float):
            paramfunc=lambda m,p,n,v:m.setGPUParamReal(p,n,v)

        for m in self.enumInternalMaterials():
            paramfunc(m,progtype,name,val)

        for f in self.enumSubreprs():
            if f==self: # prevent recursion
                return
            f.setGPUParam(name,val,progtype,**kwargs)

    def getRayIntersect(self,ray):
        '''Return the distance value where `ray' intersects this object, or None if not known or not intersected.'''
        return None

    def getPropTuples(self):
        '''Returns a list of name/value pairs listing the properties to display for this scene object in the UI.'''
        pass

    def removeFromScene(self,scene):
        '''Removes the representation from the scene, but may not destroy scene data (ie. just sets visibility).'''
        pass

    def applySpectrum(self,spec):
        '''Replaces the spectrum information for each internal material with that in `spec'.'''
        for m in self.enumInternalMaterials():
            m.copySpectrumFrom(spec)

    def createHandles(self,**kwargs):
        '''
        Returns either a single Handle object or a list thereof for this representation. The default code simply calls
        the same function of the plugin, which will create one TransformHandle by default. Handles are objects rendered
        in the scene which can be manipulated with the mouse in conjunction with the keyboard to perform some operation
        or transformation on the associated object (or its components). This method should be called only once per object
        otherwise multiple redundant handles are created.
        '''
        return self.plugin.createHandles(self,**kwargs)

    def setMaterialName(self,matname):
        '''Sets the material name of the representation's internal components.'''
        pass

    def setVisible(self,isVisible):
        '''Sets the visibility of the representation's geometry in the scene.'''
        pass

    def isVisible(self):
        '''Returns True if the object is in the scene and visible, False otherwise.'''
        return self._isVisible

    def setTransparent(self,isTrans):
        '''
        Sets the transparency properties of the scene data objects, this is necessary to get alpha compositing to
        look correct since transparent objects get rendered in a separate queue. This does not actually make the objects
        transparent, only allows transparent objects to be rendered correctly.
        '''
        pass

    def isTransparent(self):
        '''Returns whether the scene data objects have been set to be transparent or not.'''
        pass

    def addToScene(self,scene):
        '''Initialize the scene data objects and call 'update' to fill in their data.'''
        pass

    def prepareBuffers(self):
        '''Fill internal buffers with data before they are sent to the Figure objects in update().'''
        pass

    def update(self,scene):
        '''
        Fill or refill the scene data objects with their geometry information. This is called by SceneManager and
        probably should never be called by any other client.
        '''
        pass

    def setPosition(self,pos):
        '''Sets the vec3 position of the representation.'''
        pass

    def getPosition(self,isDerived=False):
        '''Returns the position vec3 object.'''
        pass

    def setRotation(self,yaw,pitch,roll):
        '''Sets the rotation in terms of Euler angles.'''
        pass

    def getRotation(self,isDerived=False):
        '''Returns a (yaw,pitch,roll) triple of Euler angles, each angle between -pi and +pi.'''
        pass

    def setScale(self,scale):
        '''Sets the scale in terms of a vec3 object to multiply the nodes of the representation by.'''
        pass

    def getScale(self,isDerived=False):
        '''Returns the scale vec3 object.'''
        pass

    def getTransform(self,isDerived=False):
        return transform(self.getPosition(isDerived),self.getScale(isDerived),rotator(*self.getRotation(isDerived)))

    def setTransform(self,trans):
        self.setRotation(*trans.getRotation().getEulers())
        self.setPosition(trans.getTranslation())
        self.setScale(trans.getScale())

    def __repr__(self):
        return '%s<%r @ 0x%.16x>'%(self.__class__.__name__,self.getName(),id(self))


class MeshSceneObject(SceneObject):
    '''Represents a data set which stores 3D model information, or anything else which is represented as a mesh.'''
    def __init__(self,name,datasets,plugin=None,**kwargs):
        SceneObject.__init__(self,name,plugin,**kwargs)
        assert datasets!=None
        self.datasets=list(toIterable(datasets)) # initial dataset or list of datasets
        self.timestepList=list(range(len(self.datasets))) # list of timestep values

    def createRepr(self,reprtype,refine=0,**kwargs):
        '''
        Create a representation for this dataset. 'reprType' is a member of ReprType, 'refine' is the refinement level,
        and any other named arguments can be passed to the SceneObjectRepr object. This method calls the plugin's
        method of the same name to implement its behaviour.
        '''
        kwargs['refine']=refine
        return self.plugin.createRepr(self,reprtype,**kwargs)

    def getPropTuples(self):
        if not self.proptuples:
            ts=self.getTimestepList()
            if len(ts)==1:
                self.proptuples=[('Num frames','1')]
            else:
                self.proptuples=[
                    ('Num frames',str(len(ts))),
                    ('Timesteps','%i, start: %i, step: %s'%(len(ts),ts[0],str(avgspan(ts))))
                ]

            self.proptuples+=getDatasetSummaryTuples(self.datasets[0])

        return self.proptuples

    def elemTypes(self):
        typelist=set()
        for ds in self.datasets:
            for ename in ds.getIndexNames():
                etype=ds.getIndexSet(ename).getType()
                if etype in MathDef.ElemType:
                    typelist.add(etype)

        return list(typelist)

    def getDataset(self):
        return list(self.datasets)

    def getFieldNames(self):
        '''Returns the names of data fields in the dataset.'''
        names=set(self.datasets[0].getFieldNames())
        for ds in self.datasets[1:]:
            names.intersection_update(ds.getFieldNames())
        return list(names)

    def getDataField(self,name):
        '''
        Returns the RealMatrix object for the field of the given name, a list of such if the object is time-
        dependent, or None if no field with this name is present.
        '''
        if name not in self.getFieldNames():
            return None
        elif len(self.datasets)==1:
            return self.datasets[0].getDataField(name)
        else:
            return [ds.getDataField(name) for ds in self.datasets]

        #globnames=self.getFieldNames()
        #names=globnames.get(name,[])
                #
        #if len(names)==0:
        #   return None
        #elif len(names)==1:
        #   return self.datasets[0].getDataField(names[0])
        #else:
        #   return [ds.getDataField(n) for ds,n in zip(self.datasets,names)]

    def getFieldObject(self,name):
        #globnames=self.getFieldNames()
        #names=globnames.get(name,[])
                #
        #if len(names)==0:
        #   return None
        #elif len(names)==1:
        #   return self.datasets[0].getFieldObject(names[0])
        #else:
        #   return [ds.getFieldObject(n) for ds,n in zip(self.datasets,names)]
        if name not in self.getFieldNames():
            return None
        elif len(self.datasets[0])==1:
            return self.datasets[0].getFieldObject(name)
        else:
            return [ds.getFieldObject(name) for ds in self.datasets]

    def loadDataField(self,*args,**kwargs):
        return self.plugin.loadDataField(self,*args,**kwargs)

    def setTimestepList(self,tslist):
        assert len(tslist)==len(self.datasets)
        self.timestepList=list(tslist)

    def getTimestepList(self):
        return list(self.timestepList)

    def transformNodes(self,trans):
        '''Transform the nodes for each dataset by the transform object `trans'.'''
        for ds in self.datasets:
            ds.getNodes().mul(trans)


class ModifierBufferGenerator(object):
    def __init__(self,*mods):
        self.mods=list(mods)

    def addModifier(self,mod):
        if mod not in self.mods:
            self.mods.append(mod)

    def removeModifier(self,mod):
        if mod in self.mods:
            self.mods.remove(mod)

    def applyMeshMod(self,nodes,norms,inds,colors,uvs,trans=transform()):
        '''
        Applies modifiers to the mesh defined by the supplied vec3or index tuple lists and transform. This method is
        for meshes not defined in datasets. The lists `nodes', `norms', `colors', and `uvs' define the components of
        each node for this mesh while `inds' defines the topology as a list of element index tuples. The method
        `applyMeshMod' is called on each modifier with arguments (nodes,norms,inds,colors,uvs,trans). The method must
        return a tuple containing (nodes,norms,inds,colors,uvs) which may be the same lists modified or new ones. Once
        all modifiers have been applied a vertex and an index buffer are created from the lists and returned.
        '''
        for mod in self.mods:
            nodes,norms,inds,colors,uvs=mod.applyMeshMod(nodes,norms,inds,colors,uvs,trans)

        vbuff=PyVertexBuffer(nodes,norms,colors,uvs)
        ibuff=PyIndexBuffer(inds)

        return vbuff,ibuff

    def applyDatasetMod(self,rep,dataset,nodecolors,indices,extinds, reprtype):
        def resetMatLen(mat):
            if mat:
                mat.setShared(False)
                # record the original length of `mat'
                origlen=mat.meta(StdProps._origlen)

                if len(origlen)==0:
                    mat.meta(StdProps._origlen,str(mat.n()))
                    origlen=mat.n()
                else:
                    origlen=int(origlen)

                mat.setN(origlen) # reset to the original length

        nodes=dataset.getNodes()
        modinds=dataset.getIndexSet(dataset.getName()+MatrixType.filtind[1])

        if modinds==None:
            modinds=IndexMatrix(dataset.getName()+MatrixType.filtind[1],0,1)
            dataset.setIndexSet(modinds)
        else:
            modinds.setShared(False)
            modinds.setN(0)

        resetMatLen(indices)
        resetMatLen(nodes)
        resetMatLen(nodecolors)

        # `selectedinds' is the selected indices matrix currently in use, initially use the provided external elements matrix
        selectedinds=extinds

        tempmodinds=IndexMatrix(dataset.getName()+' mod1',0,1) # modifiers will fill in this temp matrix that gets copied to `modinds'

        for mod in self.mods:
            mod.applyDatasetMod(rep,dataset,nodecolors,indices,selectedinds,ReprType[reprtype],tempmodinds)

            # for all subsequent modifiers after the first, `modinds' is used for determining visible/external elements
            selectedinds=modinds

            # replace the older modified/filtered indices with those generated by `mod' then clear the temp matrix
            modinds.setN(0)
            modinds.append(tempmodinds)
            tempmodinds.setN(0)

        # if not modifiers were applied then use the original external indices matrix in the vertex buffer
        if len(self.mods)==0:
                modinds=extinds

        if ReprType[reprtype][3]: # point type
            vbuff=MatrixVertexBuffer(nodes,nodecolors,modinds)
            ibuff=PyIndexBuffer([])
        else:
            vbuff=MatrixVertexBuffer(nodes,nodecolors,None)
            ibuff=MatrixIndexBuffer(indices,modinds)

        return vbuff,ibuff


class ModifierBase(object):
    '''A default modifier object for ModifierBufferGenerator generator objects which does not change its input data.'''

    def applyMeshMod(self,nodes,norms,inds,colors,uvs,trans=None):
        '''
        Given the argument lists which define a mesh, modify the mesh by changing the list values or appending to the
        lists. The return value must be the tuple (nodes,norms,inds,colors,uvs), in other words return a modified mesh.
        '''
        return nodes,norms,inds,colors,uvs

    def applyDatasetMod(self,rep,dataset,nodecolors,indices,selectedinds, reprtype,modinds):
        '''
        Modify a mesh by appending new nodes, node colors, and indices to the given matrices and dataset object. The
        mesh belongs to the SceneObjectRepr object `rep' which contains the dataset object `dataset'. The matrix
        `selectedinds' stores the indices of elements selected for visibility (which will initially be the external
        indices matrix) and only these should be considered for modification. The output matrix `modinds' contains all
        the indices for elements this modifier has chosen for visibility, so by default `selectedinds' is copied into it.
        If `selectedinds' is None then all elements are visible.
        '''
        if selectedinds!=None:
            modinds.append(selectedinds)


class MeshSceneObjectRepr(SceneObjectRepr):
    '''These representations use meshes and other 3D primitives to represent MeshSceneObject data.'''

    def __init__(self,parent,reprtype,reprcount,refine,reprdata,parentdataset=None,drawInternal=False,externalOnly=False,matname='Default',aabb=None,**kwargs):
        SceneObjectRepr.__init__(self,parent,reprtype,reprcount,matname)
        self.refine=refine
        self.drawInternal=drawInternal
        self.externalOnly=externalOnly
        self.figs=[] #list of figures, one for each index set

        self.kwargs=dict(kwargs)

        self.position=vec3()
        self.scale=vec3(1,1,1)
        self.rotation=(0.0,0.0,0.0)

        self.datafuncs={} # map from names to functional expressions for tranforming data to material information
        self.datafuncs['valfunc']=MeshAlgorithms.ValueFunc._Average # data-to-unitvalue function
        self.datafuncs['alphafunc']=MeshAlgorithms.UnitFunc._One # unitvalue-to-unitvalue alpha function

        self.dataset,self.origindices=reprdata
        self.parentdataset=parentdataset
        self.nodes=self.dataset.getNodes()
        self.lines=self.dataset.getIndexSet(self.dataset.getName()+MatrixType.lines[1])
        self.tris=self.dataset.getIndexSet(self.dataset.getName()+MatrixType.tris[1])
        self.nodeprops=self.dataset.getIndexSet(self.dataset.getName()+MatrixType.props[1])
        self.extinds=self.dataset.getIndexSet(self.dataset.getName()+MatrixType.extinds[1])

        self.datafield=None
        #self.minfield=None
        #self.maxfield=None
        self.selminfield=None
        self.selmaxfield=None

        self.aabb=aabb

        self.bufferGen=ModifierBufferGenerator()

        self.nodecolors=ColorMatrix('Colors',self.nodes.n())
        self.nodecolors.fill(color(1.0,1.0,1.0,1.0))

    def calculateAABB(self):
        nodes=listSum(f.getAABB() for f in self.figs) or self.nodes
        self.aabb=BoundBox(nodes)

    def getDataset(self):
        return self.dataset

    def __getattr__(self,name):
        attrs=[getattr(a,name) for a in self.figs if hasattr(a,name)]

        if attrs==[]:
            return SceneObjectRepr.__getattr__(self,name)

        return lambda *args,**kwargs:[a(*args,**kwargs) for a in attrs]

    def isInScene(self):
        return len(self.figs)>0

# TODO: not used at all?

#   def getParamDefs(self):
#       params=[]
#       if self.reprtype in (ReprType._bbline,ReprType._bbpoint,ReprType._bbplane):
#           rad=self.aabb.radius
#           if self.isInScene():
#               w=self.figs[0].getWidth()
#               h=self.figs[0].getHeight()
#           else:
#               w=rad*0.001
#               h=rad*0.001
#
#           params+=[
#               ParamDef('width','Width',ParamType._real,w,0,rad*2,rad*0.01),
#               ParamDef('height','Height',ParamType._real,h,0,rad*2,rad*0.01)
#           ]
#
#       return params
#
    def getParam(self,name):
        if self.isInScene():
            if name=='width':
                return self.figs[0].getWidth()
            elif name=='height':
                return self.figs[0].getHeight()
            elif name=='glyphscale':
                return self.figs[0].getGlyphScale()
            elif name=='glyphname':
                return self.figs[0].getGlyphName()

    def setParam(self,name,value):
        assert self.isInScene(), 'Cannot set parameters until representation is added to the scene'
        for fig in self.figs:
            if name=='width':
                fig.setDimension(value,fig.getHeight())
            elif name=='height':
                fig.setDimension(fig.getWidth(),value)
            elif name=='glyphscale':
                fig.setGlyphScale(vec3(*toIterable(value)))
            elif name=='glyphname':
                fig.setGlyphName(value)

    def getPropTuples(self):
        return [('Type',self.reprtype),('Material',self.matname),('BoundBox',str(self.aabb))] + getDatasetSummaryTuples(self.dataset)

    def removeFromScene(self,scene):
        self.setVisible(False)
        self.figs=[]

    def getFieldNames(self):
        '''Returns a list of field names for this representation.'''
        return self.dataset.getFieldNames()

    def getSelectedFieldName(self):
        '''Returns the name of the selected data field.'''
        if self.datafield!=None:
            return self.datafield.getName()
        else:
            return None

    def getSelectedFieldRange(self):
        return (self.selminfield,self.selmaxfield)

    def setSelectedFieldRange(self,minv,maxv):
        if minv!=None:
            self.selminfield=minv
        if maxv!=None:
            self.selmaxfield=maxv

    def getDataField(self,name=None):
        '''Returns the field with the given name, or the current selected field if `name' is None.'''
        if name!=None:
            return self.dataset.getDataField(name) #self.datafield
        else:
            return self.datafield

    def setDataField(self,field,ts=None):
        '''
        Set the data field to use with materials; 'field' is either a single field name or RealMatrix instance
        or a list thereof. If this representation is time dependent, 'field' is assigned to each subrepresentation
        if it is a single value, otherwise 'field' must be a list at least as long as there are timesteps and each
        member is assigned to the corresponding timestep subrepresentation. If 'field' is a globbed name for a series
        of fields which is as long as there are subrepresentations, each member of that series is assigned to the
        corresponding subrepresentation.
        '''
        if isinstance(field,str):
            field=self.getDataField(field) #self.dataset.getDataField(field)

        if not field:
            self.datafield=None
            self.selminfield=None
            self.selmaxfield=None
            #self.minfield=None
            #self.maxfield=None
        elif field!=self.datafield:
            self.datafield=field

            #valfunc=self.getDataFunc('valfunc',ValueFunc)
            self.selminfield=None
            self.selmaxfield=None

            #self.minfield,self.maxfield=calculateFieldMinMax(self.datafield,valfunc)
            #self.selminfield=self.minfield
            #self.selmaxfield=self.maxfield

    def _getInteralFigures(self):
        return self.figs

    def addModifier(self,mod):
        self.bufferGen.addModifier(mod)

    def removeModifier(self,mod):
        self.bufferGen.removeModifier(mod)

    def setDataFuncs(self,**funcs):
        self.datafuncs.update(funcs)

    def getDataFunc(self,name,funcEnum=None):
        '''
        Get the data manipulation function with the given name. The stored value may be the name of an expression in
        an enum or the expression value itself. In the former case, if `funcEnum' is not none and the name is in
        the enum, the value from the enum is returned instead. In the latter case the value stored in this object is
        always returned. This allows repr objects to refer to functions stored in enums by name which is convenient
        for GUI interaction, but also be able to provide custom data functions.
        '''
        val=self.datafuncs.get(name,None)
        if isinstance(val,str) and funcEnum!=None and val.replace(' ','_') in funcEnum:
            return funcEnum[val.replace(' ','_')]
        else:
            return val

    def getDataFuncMap(self):
        return dict(self.datafuncs)

    def reorderMesh(self):
        self.plugin.reorderMesh(self)

    def reduceMesh(self):
        self.plugin.reduceMesh(self)

    def isDrawInternal(self):
        return self.drawInternal

    def setDrawInternal(self,drawInternal):
        self.drawInternal=drawInternal

    def setMaterialName(self,matname):
        self.matname=matname
        for fig in self.figs:
            fig.setMaterial(matname)

    def setVisible(self,isVisible):
        if isVisible!=self._isVisible:
            self._isVisible=not self._isVisible
            for fig in self.figs:
                fig.setVisible(self._isVisible)

    def setTransparent(self,isTrans):
        for f in self.figs:
            f.setTransparent(isTrans)

    def isTransparent(self):
        return len(self.figs)>0 and self.figs[0].isTransparent()

    def isExternalOnly(self):
        return self.externalOnly

    def addToScene(self,scene):
        assert isMainThread()

        if not self.isInScene():
            fname=self.name
            figtype=ReprType[self.reprtype][2]

            fig=scene.createFigure(fname,self.matname,figtype)
            self.figs.append(fig)

            for k,v in self.kwargs.items():
                self.setParam(k,v)

        self.setVisible(True)

    def prepareBuffers(self):
        assert not isMainThread()

        if len(self.figs)>0:
            extinds=None if self.drawInternal else self.extinds
            vbuff,ibuff=self.bufferGen.applyDatasetMod(self,self.dataset,self.nodecolors,self.lines or self.tris,extinds,self.reprtype)
            self.figs[0].fillData(vbuff,ibuff,True,self.kwargs.get('doubleSided',True))

    def update(self,scene):
        assert isMainThread()
        self.setPosition(self.position)
        self.setRotation(*self.rotation)
        self.setScale(self.scale)

    def setPosition(self,pos):
        self.position=pos
        for f in self.figs:
            f.setPosition(pos)

    def getPosition(self,isDerived=False):
        if self.getParent()==None or len(self.figs)==0:
            return self.position
        else:
            return self.figs[0].getPosition(isDerived)

    def setRotation(self,yaw,pitch,roll):
        yaw=radCircularConvert(yaw)
        pitch=radCircularConvert(pitch)
        roll=radCircularConvert(roll)
        self.rotation=(yaw,pitch,roll)

        rotq=rotator(yaw,pitch,roll)
        for f in self.figs:
            f.setRotation(rotq)

    def getRotation(self,isDerived=False):
        if self.getParent()==None or len(self.figs)==0:
            return self.rotation
        else:
            return self.figs[0].getRotation(isDerived).getEulers()

    def setScale(self,scale):
        self.scale=scale
        for f in self.figs:
            f.setScale(scale)

    def getScale(self,isDerived=False):
        if self.getParent()==None or len(self.figs)==0:
            return self.scale
        else:
            return self.figs[0].getScale(isDerived)


class TDMeshSceneObjectRepr(SceneObjectRepr):
    def __init__(self,subreprs,parent,reprtype,reprcount,matname='Default'):
        assert len(subreprs)>0
        self.subreprs=subreprs
        self.timestep=0
        self.timestepIndex=0
        self.datafieldname=None
        self.drawInternal=self.isDrawInternal()
        self.proptuples=[]

        if len(parent.timestepList)==len(subreprs):
            self.timestepList=parent.timestepList  
        else: 
            self.timestepList=list(range(len(subreprs)))

        SceneObjectRepr.__init__(self,parent,reprtype,reprcount,matname)
        self.calculateAABB()

    def isInScene(self):
        return all(r.isInScene() for r in self.subreprs)

    def calculateAABB(self):
        self.aabb=BoundBox.union(r.getAABB(False,False) for r in self.subreprs)

    def getTimestepList(self):
        return self.timestepList

    def setTimestep(self,ts):
        self.timestep=clamp(ts,*self.getTimestepRange())

        self.timestepIndex=min((abs(self.timestep-v),i) for i,v in enumerate(self.timestepList))[1]

        for i,r in enumerate(self.subreprs):
            r.setVisible(self._isVisible and i==self.timestepIndex)

    def getTimestep(self):
        return self.timestep

    def getDataset(self):
        return [r.getDataset() for r in self.enumSubreprs()] or None

    def getTimestepRepr(self,ts=0):
        diff,ind=min((abs(ts-v),i) for i,v in enumerate(self.timestepList))
        return self.subreprs[ind]

    def enumSubreprs(self):
        for r in self.subreprs:
            yield r

    def getPropTuples(self):
        if len(self.proptuples)==0:
            #self.proptuples=listSum(r.getPropTuples() for r in self.subreprs)
            self.proptuples=self.subreprs[0].getPropTuples()
        return self.proptuples

    #def getGlobFieldNames(self):
    #   return globulateStrList(listSum(r.getFieldNames() for r in self.subreprs))

    def getFieldNames(self):
        #return self.getGlobFieldNames().keys()
        names=set(self.subreprs[0].getFieldNames())
        for r in self.subreprs:
            names.intersection_update(r.getFieldNames())
        return names

    def getSelectedFieldName(self):
        '''Returns the name of the selected data field.'''
        return self.datafieldname

    def getDataField(self,name=None):
        '''Returns the fields with the given name, or the current selected fields if `name' is None.'''
        return [r.getDataField(name) for r in self.subreprs]
        #name=name or self.datafieldname
        #
        ##namemap=self.getGlobFieldNames()
        ##if name not in namemap:
        ##  return None
        ##else:
        ##  return [r.dataset.getDataField(n) for r,n in zip(self.subreprs,namemap[name])]
        #if name not in self.getFieldNames():
        #   return None
        #else:
        #   return [r.getDataField(name) for r in self.subreprs]

#   def getFieldRange(self):
#       return minmax(matIter(r.getFieldRange() for r in self.subreprs))

    def getSelectedFieldRange(self):
        return minmax((r.getSelectedFieldRange() for r in self.subreprs),ranges=True)

    def setSelectedFieldRange(self,minv,maxv):
        for r in self.subreprs:
            r.setSelectedFieldRange(minv,maxv)

    def removeFromScene(self,scene):
        self.setVisible(False)

        for r in self.subreprs:
            r.removeFromScene(scene)

    def isDrawInternal(self):
        return all(r.isDrawInternal() for r in self.subreprs)

    def setDrawInternal(self,drawInternal):
        self.drawInternal=drawInternal
        for r in self.subreprs:
            r.setDrawInternal(drawInternal)

    def addModifier(self,mod):
        for r in self.subreprs:
            r.addModifier(mod)

    def removeModifier(self,mod):
        for r in self.subreprs:
            r.removeModifier(mod)

    def setDataField(self,field,ts=None):
        if ts:
            self.getTimestepRepr(ts).setDataField(field)
        elif not field:
            self.datafieldname=None
            for r in self.subreprs:
                r.setDataField(None)
        elif isinstance(field,list):
            names=field if isinstance(field[0],str) else [field[0].getName()]
            common=Utils.getStrListCommonality(names)
            self.datafieldname=names[0][:common]
            #self.datafieldname=globulateStrList(field) if isinstance(field[0],str) else field[0].getName()
            for f,r in zip(field,self.subreprs):
                r.setDataField(f)
        elif isinstance(field,str):
            self.datafieldname=field
            for r in self.subreprs:
                r.setDataField(field)

            #globnames=self.getGlobFieldNames()
                        #
            #if len(globnames.get(field,[]))==len(self.subreprs):
            #   self.datafieldname=field
            #   for r,n in zip(self.subreprs,globnames[field]):
            #       r.setDataField(n)
            #else:
            #   self.datafieldname=field if isinstance(field,str) else field.getName()
            #   for r in self.subreprs:
            #       r.setDataField(field)

    def setDataFuncs(self,**funcs):
        for r in self.subreprs:
            r.setDataFuncs(**funcs)

    def getDataFunc(self,name,funcEnum=None):
        return self.subreprs[0].getDataFunc(name,funcEnum)

    def getDataFuncMap(self):
        return self.subreprs[0].getDataFuncMap()

    def setMaterialName(self,matname):
        self.matname=matname
        for r in self.subreprs:
            r.setMaterialName(matname)

    def setVisible(self,isVisible):
        self._isVisible=isVisible

        if isVisible:
            self.setTimestep(self.timestep)
        else:
            for r in self.subreprs:
                r.setVisible(False)

    def setTransparent(self,isTrans):
        for r in self.subreprs:
            r.setTransparent(isTrans)

    def isTransparent(self):
        return all(r.isTransparent() for r in self.subreprs)

    def isExternalOnly(self):
        return all(r.isExternalOnly() for r in self.subreprs)

    def addToScene(self,scene):
        for r in self.subreprs:
            r.addToScene(scene)

        self.setVisible(True)

    def prepareBuffers(self):
        for r in self.subreprs:
            r.prepareBuffers()

    def update(self,scene):
        for r in self.subreprs:
            r.update(scene)

    def setPosition(self,pos):
        for r in self.subreprs:
            r.setPosition(pos)

    def getPosition(self,isDerived=False):
        return self.subreprs[0].getPosition(isDerived)

    def setRotation(self,yaw,pitch,roll):
        for r in self.subreprs:
            r.setRotation(yaw,pitch,roll)

    def getRotation(self,isDerived=False):
        return self.subreprs[0].getRotation(isDerived)

    def setScale(self,scale):
        for r in self.subreprs:
            r.setScale(scale)

    def getScale(self,isDerived=False):
        return self.subreprs[0].getScale(isDerived)

    def reorderMesh(self):
        self.plugin.reorderMesh(self)

    def reduceMesh(self):
        self.plugin.reduceMesh(self)


