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

from typing import Any, List, Optional, Union

import numpy as np

from eidolon.mathdef import BoundBox, Transformable, transform
from eidolon.renderer import Figure, Material, make_shader_from_prefix
from eidolon.utils import Namespace, cached_property

__all__ = ["ReprType", "SceneObject", "SceneObjectRepr"]


class ReprType(Namespace):
    """
    Stores the types of visual representations data can have.
    """

    # mesh types
    vertex = "Mesh Vertices"
    point = "Mesh Points"
    line = "Mesh Lines"
    surface = "Mesh Surfaces"
    volume = "Mesh Volumes"

    # image types
    imagestack = "Image Stack"
    imagevolume = "Image Volume"
    timedimagestack = "Time-dependent Image Stack"
    timedimagevolume = "Time-dependent Image Volume"


class SceneObject:
    """
    A SceneObject represents the data of a single notional object, for example the data for a model or all of the
    imaging slices for an image set. These are loaded from data sources by plugins or can be instantiated within
    scripts. In either case they must be added to the scene with SceneManager.addSceneObject() before they can be used
    for creating a representation. Once they have been added, they can produce instances of SceneObjectRepr to visually
    represent the data store. The representations are stored as children of the originating SceneObject.
    """

    def __init__(self, name: str, plugin=None, **other_values):
        self._name: str = name  # object name
        self.reprs: list = []  # list of current representations
        self.reprcount: int = 0  # number of representations created, used to ensure unique names
        self.plugin = plugin  # plugin used to link interface and create representations
        self.other_values: dict = other_values  # keyword arguments passed in through the constructor
        self._prop_tuples: list = []  # list of cached property tuples, filled in by getPropTuples()
        self.filename: str = None

    def __repr__(self):
        return f"{self.__class__.__name__}<'{self.name}' @ {id(self):x}>"

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
        rep.visible = False
        self.reprs.remove(rep)

    def get_dataset(self):
        """Returns the underlying data structures defining this object."""
        raise NotImplementedError()

    def set_timestep_list(self, tslist):
        """
        Sets the timesteps values for this object. The ascending list of values `tslist` stores a time for each step.
        """
        raise NotImplementedError()

    def get_timestep_list(self):
        """Returns the timestep values for each timestep of the object, or just [0] if it's not time-dependent."""
        raise NotImplementedError()

    def set_timestep_scheme(self, starttime, interval):
        """
        Set the first timestep to `starttime` and each subsequent step is `interval` forward in time.
        """
        tslen = len(self.get_timestep_list())
        self.set_timestep_list([starttime + interval * i for i in range(tslen)])

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

    def __init__(self, parent: SceneObject, repr_type: str, repr_count: int, matname: str = "Default"):
        super().__init__()

        self.parent: SceneObject = parent  # parent SceneObject instance
        self.plugin = self.parent.plugin
        self._name: str = ReprType[repr_type]  # +str(reprcount)
        self._matname: str = matname
        self.repr_count: int = repr_count
        self.repr_type: str = repr_type
        self._visible: bool = False
        self._aabb: Optional[BoundBox] = None  # cached AABB object, set to None to force recalc
        self._current_timestep: float = 0

        self.figures: List[Figure] = []
        self.secondary_figures: List[Figure] = []

    def __repr__(self):
        return f"{self.__class__.__name__}<{self.name} @ {id(self):x}>"

    @property
    def label(self):
        """Returns the UI label, this may be different from the name and include additional information."""
        return self._name + " <" + self.parent.name + ">"

    @property
    def name(self):
        """Returns the name of this representation."""
        return self._name

    @name.setter
    def name(self, name):
        """Sets the name of the object."""
        self._name = name

    @property
    def visible(self) -> bool:
        return self._visible

    @visible.setter
    def visible(self, visible: bool):
        self._visible = visible
        self.timestep = self._current_timestep  # sets visibility

    @property
    def timestep(self):
        return self._current_timestep

    @timestep.setter
    def timestep(self, timestep):
        tmin, tmax = self.timestep_range

        if not (tmin <= timestep <= tmax):
            raise ValueError(f"Timestep value {timestep} not in interval [{tmin}, {tmax}]")

        self._current_timestep = timestep

        for f in self.all_figures():
            f.visible = self.visible and f.timestep == timestep

    @property
    def is_in_scene(self) -> bool:
        """Returns True if this representation has been initialized and included into the scene, false otherwise."""
        return any(f.attached for f in self.figures)

    def aabb(self, recalculate: bool = False):
        """Returns the untransformed axis-aligned bound box enclosing the geometry of this representation."""
        if recalculate or self._aabb is None:
            self._calculate_aabb()

        return self._aabb

    def _calculate_aabb(self) -> BoundBox:
        """Recalculate the AABB after the data has changed."""
        boxes = [f.aabb() for f in self.figures if f.visible]
        return BoundBox.from_boxes(*boxes)

    def all_figures(self):
        yield from self.figures
        yield from self.secondary_figures

    def get_dataset(self):
        """Returns the underlying data structures defining this object."""
        return self.parent.get_dataset()

    @property
    def timestep_list(self):
        """Returns the list of timesteps, [0] for non-time-dependent objects."""
        return sorted(set(f.timestep for f in self.figures))

    @property
    def timestep_range(self):
        """Returns the timestep start and end values."""
        ts = self.timestep_list
        return ts[0], ts[-1]

    @property
    def timestep_interval(self):
        """Returns the interval between timesteps, which is the mean of differences between values."""
        return np.diff(self.timestep_list).mean()

    def set_transform(self, trans: transform):
        super().set_transform(trans)

        for f in self.all_figures():
            f.set_transform(trans)

    @property
    def material_name(self):
        """Returns the applied material's name."""
        return self._matname

    def set_material(self, mat: Material):
        self._matname = mat.name

        for fig in self.figures:
            fig.set_material(mat)

    def set_shader(self, shader: Union[str, Any], apply_to_seconds=False):
        figures = list(self.figures) + list(self.secondary_figures if apply_to_seconds else [])

        if isinstance(shader, str):
            shader = make_shader_from_prefix(shader)

        for fig in figures:
            fig.set_shader(shader)

    def set_shader_input(self, name: str, *args, apply_to_seconds=False):
        figures = list(self.figures) + list(self.secondary_figures if apply_to_seconds else [])

        for fig in figures:
            fig.set_shader_input(name,*args)
