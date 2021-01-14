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

from typing import Iterable, List
from .scene_object import SceneObject, SceneObjectRepr
from ..mathdef import Mesh


class MeshSceneObject(SceneObject):
    def __init__(self, name, meshes: Iterable[Mesh], plugin=None, **other_values):
        super().__init__(name, plugin, **other_values)
        self.meshes: List[Mesh] = meshes

        starttime, interval = self.get_timestep_scheme()
        self._prop_tuples = [
            ("Name", self.name),
            ("# Meshes", len(self.meshes)),
            ("Start Time", starttime),
            ("Interval", interval),
            ("# Nodes", len(self.meshes[0].nodes))
        ]

        for iname, ind in self.meshes[0].topos.items():
            self._prop_tuples.append(("Index", f"{iname}, shape: {ind[0].shape}"))

        for fname, field in self.meshes[0].fields.items():
            self._prop_tuples.append(("Field", f"{fname}, shape: {field[0].shape}"))

    def get_dataset(self):
        return list(self.meshes)

    def get_timestep_list(self):
        return sorted(set(m.timestep for m in self.meshes))

    def set_timestep_list(self, tslist):
        oldts = self.get_timestep_list()

        if len(oldts) != len(tslist):
            raise ValueError(f"Timestep list must have exactly {len(oldts)} values")

        for oldval, newval in zip(oldts, tslist):
            for m in self.meshes:
                if m.timestep == oldval:
                    m.timestep = newval


class MeshSceneObjectRepr(SceneObjectRepr):
    pass
