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


from __future__ import annotations
from typing import NamedTuple, Optional, Dict, Any, Tuple, Union
import numpy as np
from ..utils import Namespace, first

__all__ = ["Mesh", "MeshDataValue"]


class MeshDataValue(Namespace):
    """List of names and descriptions of known data objects that might appear in Mesh.other_data or Mesh.properties."""
    node = "Nodes"
    line = "Lines Indices"
    tri = "Triangles Indices"
    xis = "Node Xi Values"
    norms = "Node Normals"
    colors = "Node Colors"
    uvwcoords = "Texture Coordinates"
    nodeprops = "Per-node Properties Array"
    spatial = "Spatial Topology"
    field = "Data Field"
    octree = "Octree Data"
    ext_adj = "Array of Adjacent Elements/Faces"
    ext_inds = "Indices of External Elements"


class Topology(NamedTuple):
    data: np.ndarray = None
    elem_type: Optional[str] = ""
    is_field_topo: bool = False


class Field(NamedTuple):
    data: np.ndarray = None
    spatial_topo: str = ""
    field_topo: Optional[str] = None
    is_per_elem: bool = False


class Mesh:
    def __init__(self, nodes, topo_sets={}, field_sets={}, timestep=0, parent=None):
        self.nodes: np.ndarray = np.asarray(nodes)
        self.topos: Dict[str, Topology] = {}
        self.fields: Dict[str, Field] = {}
        self.timestep: float = timestep
        self.parent: Mesh = parent

        self.properties: Dict[Union[str, Tuple[str, str]], Any] = {}
        self.other_data: Dict[Union[str, Tuple[str, str]], Any] = {}

        for name, vals in topo_sets.items():
            self.set_topology(name, *vals)

        for name, vals in field_sets.items():
            self.set_field(name, *vals)

    def set_topology(self, name, index_array, elem_type=None, is_field_topo=False):
        self.topos[name] = Topology(np.asarray(index_array), elem_type, is_field_topo)

    def set_field(self, name, data_array, spatial_topology, field_topology=None, is_per_elem=False):
        field_topology = field_topology or spatial_topology
        self.fields[name] = Field(np.asarray(data_array), spatial_topology, field_topology, is_per_elem)

    def get_spatial_topos(self) -> Dict[str, Topology]:
        return {n: t for n, t in self.topos.items() if not t.is_field_topo}

    def share_other_data(self, other: Mesh):
        """
        Share members of `other_data` with `other`, adding key-value entries if they are not in `other.other_data`. This
        does not copy arrays so data does become shared, this is assumed to be normal, octree, or adjecency data that
        applies to the same topologies in `other` as are present here. If a key in `other_data` is a pair containing a
        value name and topology/field name, the entry is added to `other` only if that member is present.
        """
        for k, v in self.other_data.items():
            if k not in other.other_data:
                if isinstance(k, tuple):
                    _, array_name = k
                    if array_name in other.topos or array_name in other.fields:
                        other.other_data[k] = v
                else:
                    other.other_data[k] = v
