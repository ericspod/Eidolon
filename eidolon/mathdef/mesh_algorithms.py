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

from .math_types import vec3, rotator
from .elem_type import ElemType, ElemTypeDef
from .octree import Octree
from ..utils import first
from .mesh import Mesh, MeshDataType
from .compile_support import jit, prange

import numpy as np

__all__ = ["calculate_mesh_octree", "calculate_shared_nodes", "calculate_mesh_ext_adj"]


def calculate_mesh_octree(mesh: Mesh, topo_name=None, depth=3):
    topo_name = topo_name or first(mesh.topos)
    topo_array, _ = mesh.topos[topo_name]

    other_key = (topo_name, MeshDataType.octree)

    nodes = [vec3(*v) for v in mesh.nodes]

    if other_key not in mesh.other_arrays:
        oc = Octree.from_mesh(depth, nodes, topo_array)
        mesh.other_arrays[other_key] = oc


# from numba.typed import Dict,List
# from numba.core import types

# int_array = types.int64[:]

@jit
def calculate_shared_nodes(topo_array: np.array, leaf: np.array):
    # result = Dict.empty(
    #     key_type=types.int64,
    #     value_type=int_array,
    # )

    result = dict()

    for idx in range(leaf.shape[0]):
        elem_idx = leaf[idx]

        for node_idx in range(topo_array.shape[1]):
            node = topo_array[elem_idx, node_idx]
            if node not in result:
                result[node] = np.array([idx])
            else:
                result[node] = np.append(result[node], idx)

    return result


def calculate_mesh_ext_adj(mesh: Mesh, topo_name=None):
    topo_name = topo_name or first(mesh.topos)
    topo_array, et_name = mesh.topos[topo_name]
    et: ElemTypeDef = ElemType[et_name]
    octree = mesh.other_arrays[(topo_name, MeshDataType.octree)]

    face_inds = np.array(et.faces)[:, :-1]  # remove far node index

    topo_ext_adj = -np.ones((topo_array.shape[0], et.num_faces * 2), dtype=int)

    for leaf in octree.leaves:
        if len(leaf.leafdata):
            leafdata = np.array(leaf.leafdata)
            num_faces = face_inds.shape[0]
            face_size = face_inds.shape[1]

            expanded_face_inds = np.zeros((leafdata.shape[0], num_faces, face_size), dtype=int)
            calculate_expanded_face_inds(expanded_face_inds, topo_array, leafdata, face_inds)
            expanded_face_inds = np.sort(expanded_face_inds, axis=2)

            calculate_leaf_ext_adj(expanded_face_inds, topo_array, leafdata, face_inds, topo_ext_adj)

    mesh.other_arrays[(topo_name, MeshDataType.ext_adj)] = topo_ext_adj

    return topo_ext_adj


@jit
def calculate_expanded_face_inds(expanded_face_inds: np.array, topo_array: np.array, leaf: np.array,
                                 face_inds: np.array):
    num_faces = face_inds.shape[0]
    face_size = face_inds.shape[1]

    for idx in range(leaf.shape[0]):
        elem_idx = leaf[idx]
        elem = topo_array[elem_idx]
        for face_idx in range(num_faces):
            for felem_idx in range(face_size):
                expanded_face_inds[idx, face_idx, felem_idx] = elem[face_inds[face_idx, felem_idx]]


@jit
def calculate_leaf_ext_adj(expanded_face_inds: np.array, topo_array: np.array, leaf: np.array,
                           face_inds: np.array, topo_ext_adj: np.array):
    # shared_nodes = calculate_shared_nodes(topo_array, leaf)
    num_faces = face_inds.shape[0]
    face_size = face_inds.shape[1]

    # expanded_face_inds = np.zeros((leaf.shape[0], num_faces, face_size), dtype=int)

    # for idx in range(leaf.shape[0]):
    #     elem_idx = leaf[idx]
    #     elem = topo_array[elem_idx]
    #     for face_idx in range(num_faces):
    #         for felem_idx in range(face_size):
    #             expanded_face_inds[idx, face_idx, felem_idx] = elem[face_inds[face_idx, felem_idx]]
    #
    # expanded_face_inds = np.sort(expanded_face_inds, axis=2)

    for idx in range(leaf.shape[0]):
        # elem_idx = leaf[idx]
        # elem = topo_array[elem_idx]
        for face_idx in range(num_faces):
            # face = [elem[face_inds[face_idx, i]] for i in range(face_inds.shape[1])]
            # face = set(face)
            face = expanded_face_inds[idx, face_idx]

            for other_idx in range(leaf.shape[0]):
                if other_idx == idx:
                    continue

                for other_face_idx in range(num_faces):
                    if np.array_equal(expanded_face_inds[other_idx, other_face_idx], face):
                        elem_idx = leaf[idx]
                        other_elem = leaf[other_idx]

                        topo_ext_adj[elem_idx, face_idx] = other_elem
                        topo_ext_adj[elem_idx, face_idx + num_faces] = other_face_idx
                        topo_ext_adj[other_elem, other_face_idx] = elem_idx
                        topo_ext_adj[other_elem, other_face_idx + num_faces] = face_idx

# # @jit
# def calculate_leaf_ext_adj(topo_array: np.array, leaf: np.array, face_inds: np.array, topo_ext_adj: np.array):
#     faces: dict = dict()
#     num_faces = topo_ext_adj.shape[1] // 2
#
#     for idx in range(leaf.shape[0]):
#         elem_idx = leaf[idx]
#         elem = topo_array[elem_idx]
#
#         for face_idx in range(face_inds.shape[0]):
#             face = [elem[face_inds[face_idx, i]] for i in range(face_inds.shape[1])]
#             face = set(face)
#             face = tuple(face)
#
#             if face in faces:
#                 other = faces[face]
#                 other_elem = other[0]
#                 other_face = other[1]
#
#                 topo_ext_adj[elem_idx, face_idx] = other_elem
#                 topo_ext_adj[elem_idx, face_idx + num_faces] = other_face
#                 topo_ext_adj[other_elem, other_face] = elem_idx
#                 topo_ext_adj[other_elem, other_face + num_faces] = face_idx
#             else:
#                 faces[face] = (elem_idx, face_idx)
