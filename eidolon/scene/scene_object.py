# Eidolon Biomedical Framework
# Copyright (C) 2016-20 Eric Kerfoot, King's College London, all rights reserved
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

import numpy as np

from ..utils import cached_property,Namespace
from ..mathdef import Transformable

__all__ = ["ReprType", "SceneObject", "SceneObjectRepr"]


class ReprType(Namespace):
    """
    Stores the types of visual representations data can have.
    """
    Vertex = "Mesh Vertices"
    Point = "Mesh Points"
    Line = "Mesh Lines"
    Volume = "Mesh Volumes"
    Surface = "Mesh Surfaces"
    ImageStack = "Image Stack"
    TimedImageStack = "Time-dependent Image Stack"
    ImageVolume = "Image Volume"
    TimedImageVolume = "Time-dependent Image Volume"


class SceneObject:
    """
    A SceneObject represents the data of a single notional object, for example the data for a model or all of the
    imaging slices for an image set. These are loaded from data sources by plugins or can be instantiated within
    scripts. In either case they must be added to the scene with SceneManager.addSceneObject() before they can be used
    for creating a representation. Once they have been added, they can produce instances of SceneObjectRepr to visually
    represent the data store. The representations are stored as children of the originating SceneObject.
    """

    def __init__(self, name, plugin=None, **kwargs):
        self._name = name  # object name
        self.reprs = []  # list of current representations
        self.reprcount = 0  # number of representations created, used to ensure unique names
        self.plugin = plugin  # plugin used to link interface and create representations
        self.kwargs = kwargs  # keyword arguments passed in through the constructor
        self._prop_tuples = []  # list of cached property tuples, filled in by getPropTuples()

    def __repr__(self):
        return f"{self.__class__.__name__}<'{self.name}' @ {id(self):.16x}>"

    # def __getattr__(v1, name):
    #     try:
    #         return v1.__getattribute__(name)
    #     except AttributeError:
    #         # Search the base types of v1.plugin for a method called `name', if found to be a
    #         # delegated method in any of the types return the wrapped instance from v1.plugin.
    #         for cls in inspect.getmro(type(v1.plugin)):
    #             meth = getattr(cls, name, None)
    #             if getattr(meth, '__isdelegatedmethod__', False):
    #                 meth = getattr(v1.plugin, name)  # get meth again which will be different if overridden
    #                 return functools.partial(meth, v1)
    #
    #         raise  # if no plugin method found, raise the exception

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def label(self):
        return self.name

    @property
    def prop_tuples(self):
        """
        Returns a list of name/value pairs listing the properties to display for this scene object in the UI. This can
        use v1._prop_tuples as a cache for efficiency, so the method fills in v1._prop_tuples if this attribute is
        empty and returns it thereafter.
        """
        return tuple(self._prop_tuples)

    @cached_property
    def repr_types(self):
        """Returns an iterable of ReprType names identifying valid representations of this object."""
        return self.plugin.get_repr_types(self)

    def remove_repr(self, rep):
        self.reprs.remove(rep)

    def get_dataset(self):
        """Returns the underlying data structures defining this object."""
        raise NotImplementedError()

    def set_timestep_list(self, tslist):
        """
        Sets the timesteps values for this object. The ascending list of values `tslist` stores a time for each step.
        """
        raise NotImplementedError()

    def set_timestep_scheme(self, starttime, interval):
        """
        Set the first timestep to `starttime` and each subsequent step is `interval` forward in time.
        """
        tslen = len(self.get_timestep_list())
        self.set_timestep_list([starttime + interval * i for i in range(tslen)])

    def get_timestep_list(self):
        """Returns the timestep values for each timestep of the object, or just [0] if it's not time-dependent."""
        raise NotImplementedError()

    def get_timestep_scheme(self):
        ts = self.get_timestep_list()
        starttime = ts[0]
        interval = np.diff(ts).mean() if len(ts) > 1 else 0
        return starttime, interval


class SceneObjectRepr(Transformable):
    """
    A SceneObjectRepr encapsulates a single method of representing a SceneObject visually in the scene. It contains the
    information generated from the SceneObject's data which is sent to the renderer for drawing, and has the facilities
    controlling how it appears in the scene such as the use of materials. A representation can be a range of renderable
    concepts, such as a point list represented using points or billboards, line lists used to draw the outlines of
    figures, triangle meshes for rendering solid objects, texture planes for representing imaging data, and so forth.
    """

    def __init__(self, parent, reprtype, reprcount, matname='Default'):
        super().__init__()

        self.parent = parent  # parent SceneObject instance
        self.plugin = self.parent.plugin
        self._name = ReprType[reprtype]  # +str(reprcount)
        self.matname = matname
        self.reprcount = reprcount
        self.reprtype = reprtype
        self._isVisible = False
        self._aabb = None  # cached AABB object, set to None to force recalc

        # self.rparent = None  # parent SceneObjectRepr instance
        self.children = set()

    def __repr__(self):
        return f"{self.__class__.__name__}<{self.name} @ {id(self):.16x}>"

    # def __getattr__(self, name):
    #     try:
    #         return self.__getattribute__(name)
    #     except AttributeError:
    #         # Search the base types of self.plugin for a method called `name', if found to be a
    #         # delegated method in any of the types return the wrapped instance from self.plugin.
    #         for cls in inspect.getmro(type(self.plugin)):
    #             meth = getattr(cls, name, None)
    #             if getattr(meth, '__isdelegatedmethod__', False):
    #                 meth = getattr(self.plugin, name)  # get meth again which will be different if overridden
    #                 return functools.partial(meth, self)
    #
    #         raise  # if no plugin method found, raise the exception

    @property
    def is_in_scene(self) -> bool:
        """Returns True if this representation has been initialized and included into the scene, false otherwise."""
        pass

    def aabb(self, is_transformed=False, is_derived=True, recalculate=False):
        """Returns the untransformed axis-aligned bound box enclosing the geometry of this representation."""
        if recalculate or self._aabb is None:
            self.calculate_aabb()

        if is_transformed and self.aabb:
            return self._aabb * self.getTransform(is_derived)
        else:
            return self._aabb

    def calculate_aabb(self):
        """Recalculate the AABB after the data has changed."""
        pass

    @property
    def label(self):
        """Returns the UI label, this may be different from the name and include additional information."""
        return self._name + ' <' + self.parent.name + '>'

    @property
    def name(self):
        """Returns the name of this representation."""
        return self._name

    @name.setter
    def name(self, name):
        """Sets the name of the object."""
        self._name = name

    @property
    def timestep(self):
        raise NotImplementedError()

    @timestep.setter
    def timestep(self, timestep):
        raise NotImplementedError()

    def get_dataset(self):
        """Returns the underlying data structures defining this object."""
        raise NotImplementedError()

    def get_material_name(self):
        """Returns the applied material's name."""
        return self.matname

    def get_timestep_list(self):
        """Returns the list of timesteps, [0] for non-time-dependent objects."""
        raise NotImplementedError()

    def get_timestep_range(self):
        """Returns the timestep start and end values."""
        ts = self.get_timestep_list()
        return ts[0], ts[-1]

    def get_timestep_interval(self):
        """Returns the interval between timesteps."""
        return np.diff(self.get_timestep_list()).mean()

    # def getTimestepRepr(self, ts=0):
    #     '''
    #     Returns the subrepresentation at timestep `ts' or nearest if `ts' is non-integer. For non-time-dependent
    #     representations, this instead returns `self'.
    #     '''
    #     return self
    #
    # def setParent(self, prepr):
    #     '''
    #     Set this object's parent representation to `prepr'. This sets every internal figure to be a child of the
    #     first figure yielded by `prepr.enumFigures()'. This establishes a one-to-many relationship between objects
    #     such that an affine transformation performed on the parent is compounded with that applied to the child. In
    #     effect the child exists and is transformed in the local coordinates of its parent.
    #     If `prepr' is None then this representation will have no parent and its subfigures will be children of the
    #     root scene node only.
    #     '''
    #
    #     if any(c == prepr for c in self.enumChildren(True)):
    #         raise Exception('Cannot set a parent which is a child of this representation.')
    #
    #     p = self.getParent()
    #     while p != None:
    #         if p == prepr:
    #             raise Exception('Cannot add a child which is a parent of this representation.')
    #         p = p.getParent()
    #
    #     if self.rparent:
    #         self.rparent.removeChild(self)
    #
    #     self.rparent = prepr
    #
    #     if prepr:
    #         prepr.addChild(self)
    #         pfigure = first(prepr.enumFigures())
    #     else:
    #         pfigure = None
    #
    #     for f in self.enumFigures():
    #         f.setParent(pfigure)
    #
    # def getParent(self):
    #     '''Returns the parent representation object.'''
    #     return self.rparent
    #
    # def enumChildren(self, allChildren=False):
    #     '''Yield every child of this object, descending depth first into the scene node tree if allChildren is true.'''
    #     for c in self.children:
    #         yield c
    #         if allChildren:
    #             for cc in c.enumChildren():
    #                 yield cc
    #
    # def addChild(self, child):
    #     '''Add a child to the internal children set, should only be called by setParent().'''
    #     self.children.add(child)
    #
    # def removeChild(self, child):
    #     '''Remove a child to the internal children set, should only be called by setParent().'''
    #     if child in self.children:
    #         self.children.remove(child)
    #
    # def enumSubreprs(self):
    #     '''
    #     Yield every internal sub-representation of this object excluding `self', or [`self'] if no internal
    #     representations are used in this type.
    #     '''
    #     return [self]
    #
    # def _getInteralFigures(self):
    #     return []
    #
    # def enumFigures(self):
    #     '''Yield every Figure object which comprises this representation.'''
    #     for f in self._getInteralFigures():
    #         yield f
    #
    #     for r in self.enumSubreprs():
    #         if r == self:
    #             return
    #         for f in r.enumFigures():
    #             yield f
    #
    # def enumInternalMaterials(self):
    #     '''Yield every internal material (ie. created by this object) used to define this representation.'''
    #     return []  # default is to yield nothing, but don't return None or use 'pass'
    #
    # def addModifier(self, mod):
    #     pass
    #
    # def removeModifier(self, mod):
    #     pass
    #
    # def getParamDefs(self):
    #     '''Get the ParamDef objects describing the additional parameters to this representation.'''
    #     return []
    #
    # def getParam(self, name):
    #     '''Get the value of an additional parameter.'''
    #     rep = first(self.enumSubreprs())
    #     if rep and rep != self:
    #         return rep.getParam(name)
    #     else:
    #         return None
    #
    # def setParam(self, name, value):
    #     '''Set the value of an additional parameter.'''
    #     for r in self.enumSubreprs():
    #         if r != self:
    #             r.setParam(name, value)
    #
    # def setGPUParam(self, name, val, progtype, **kwargs):
    #     '''
    #     Sets the GPU program parameter `name' with value `val' for every internal material. The `progtype' value
    #     specifies which program type this is for. The value of `val' must be a vec3, real, int, long, or color.
    #     '''
    #     paramfunc = None
    #     if isinstance(val, vec3):
    #         paramfunc = lambda m, p, n, v: m.setGPUParamVec3(p, n, v)
    #     elif isinstance(val, color):
    #         paramfunc = lambda m, p, n, v: m.setGPUParamColor(p, n, v)
    #     elif isinstance(val, int):
    #         paramfunc = lambda m, p, n, v: m.setGPUParamInt(p, n, int(v))
    #     elif isinstance(val, float):
    #         paramfunc = lambda m, p, n, v: m.setGPUParamReal(p, n, v)
    #
    #     for m in self.enumInternalMaterials():
    #         paramfunc(m, progtype, name, val)
    #
    #     for f in self.enumSubreprs():
    #         if f == self:  # prevent recursion
    #             return
    #         f.setGPUParam(name, val, progtype, **kwargs)
    #
    # def getRayIntersect(self, ray):
    #     '''Return the distance value where `ray' intersects this object, or None if not known or not intersected.'''
    #     return None
    #
    # def getPropTuples(self):
    #     '''Returns a list of name/value pairs listing the properties to display for this scene object in the UI.'''
    #     pass
    #
    # def removeFromScene(self, scene):
    #     '''Removes the representation from the scene, but may not destroy scene data (ie. just sets visibility).'''
    #     pass
    #
    # def applySpectrum(self, spec):
    #     '''Replaces the spectrum information for each internal material with that in `spec'.'''
    #     for m in self.enumInternalMaterials():
    #         m.copySpectrumFrom(spec)
    #
    # def createHandles(self, **kwargs):
    #     '''
    #     Returns either a single Handle object or a list thereof for this representation. The default code simply calls
    #     the same function of the plugin, which will create one TransformHandle by default. Handles are objects rendered
    #     in the scene which can be manipulated with the mouse in conjunction with the keyboard to perform some operation
    #     or transformation on the associated object (or its components). This method should be called only once per object
    #     otherwise multiple redundant handles are created.
    #     '''
    #     return self.plugin.createHandles(self, **kwargs)
    #
    # def setMaterialName(self, matname):
    #     '''Sets the material name of the representation's internal components.'''
    #     pass
    #
    # def setTransparent(self, isTrans):
    #     '''
    #     Sets the transparency properties of the scene data objects, this is necessary to get alpha compositing to
    #     look correct since transparent objects get rendered in a separate queue. This does not actually make the objects
    #     transparent, only allows transparent objects to be rendered correctly.
    #     '''
    #     pass
    #
    # def isTransparent(self):
    #     '''Returns whether the scene data objects have been set to be transparent or not.'''
    #     pass
    #
    # def addToScene(self, scene):
    #     '''Initialize the scene data objects and call 'update' to fill in their data.'''
    #     pass
    #
    # def prepareBuffers(self):
    #     '''Fill internal buffers with data before they are sent to the Figure objects in update().'''
    #     pass
    #
    # def update(self, scene):
    #     '''
    #     Fill or refill the scene data objects with their geometry information. This is called by SceneManager and
    #     probably should never be called by any other client.
    #     '''
    #     pass

