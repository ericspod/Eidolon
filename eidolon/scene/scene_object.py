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

from ..utils import cached_property
from ..utils import Namespace

__all__ = ["ReprTypes", "SceneObject"]


class ReprTypes(Namespace):
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
        use self._prop_tuples as a cache for efficiency, so the method fills in self._prop_tuples if this attribute is
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
        pass

    def set_timestep_list(self, tslist):
        """
        Sets the timesteps values for this object. The ascending list of values `tslist` stores a time for each step.
        """
        pass

    def set_timestep_scheme(self, starttime, interval):
        """
        Set the first timestep to `starttime` and each subsequent step is `interval` forward in time.
        """
        tslen = len(self.get_timestep_list())
        self.set_timestep_list([starttime + interval * i for i in range(tslen)])

    def get_timestep_list(self):
        """Returns the timestep values for each timestep of the object, or just [0] if it's not time-dependent."""
        return [0]

    def get_timestep_scheme(self):
        ts = self.getTimestepList()
        starttime = ts[0]
        interval = np.diff(ts).mean() if len(ts) > 1 else 0
        return starttime, interval

    def __repr__(self):
        return f"{self.__class__.__name__}<'{self.name}' @ {id(self):.16x}>"
