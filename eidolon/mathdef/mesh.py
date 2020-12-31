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
from ..utils import Namespace

__all__ = ["Mesh", "MeshDataType"]


class MeshDataType(Namespace):
    node = "Nodes"
    line = "Lines Indices"
    tri = "Triangles Indices"
    spatial = "Spatial Topology"
    field = "Data Field"
    octree = "Octree Data"
    ext_adj = "Array of Adjacent Elements/Faces"
    ext_inds = "Indices of External Elements"


class Mesh:
    def __init__(self, nodes, topo_sets=[], field_sets=[], time_index=0, normals=None, colors=None, uvws=None):
        self.nodes = nodes
        self.topos = {}
        self.fields = {}
        self.normals = normals
        self.colors = colors
        self.uvws = uvws
        self.time_index = time_index

        self.properties = {}
        self.other_arrays = {}

        for t in topo_sets:
            if isinstance(t, (list, tuple)):
                self.set_topology(*t)
            else:
                raise ValueError(f"Unknown index {t}")

        for f in field_sets:
            if isinstance(f, (list, tuple)):
                self.set_field(*f)
            else:
                raise ValueError(f"Unknown field {f}")

    def set_topology(self, name, index_array, elem_type=None):
        self.topos[name] = (index_array, elem_type)

    def set_field(self, name, data_array, spatial_topology, field_topology=None):
        self.fields[name] = (data_array, spatial_topology, field_topology)
