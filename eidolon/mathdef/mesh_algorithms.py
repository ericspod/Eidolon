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

from .utils import FEPSILON, HALFPI
from .math_types import vec3
from .elem_type import ElemType, ElemTypeDef, get_xi_elem_directions
from .octree import Octree
from ..utils import first, timing
from .mesh import Mesh, MeshDataType
from .compile_support import jit, prange, has_numba
from .mesh_utils import divide_quad_to_tri_mesh, divide_tri_to_tri_mesh

import numpy as np

__all__ = ["calculate_mesh_octree", "calculate_shared_nodes", "calculate_mesh_ext_adj", "calculate_tri_mesh"]


@timing
def calculate_mesh_octree(mesh: Mesh, topo_name=None, depth=3):
    topo_name = topo_name or first(mesh.topos)
    topo_array, *_ = mesh.topos[topo_name]

    other_key = (topo_name, MeshDataType._octree)

    oc = mesh.other_data.get(other_key, None)

    if oc is None:
        nodes = [vec3(*v) for v in mesh.nodes]
        oc = Octree.from_mesh(depth, nodes, topo_array)
        mesh.other_data[other_key] = oc

    return oc


if has_numba:
    from numba.typed import List
    from numba.core import types


    @jit
    def int_list():
        return List.empty_list(item_type=types.int64)
else:
    def int_list():
        return list()


@jit
def calculate_shared_nodes(topo_array: np.array, leaf: np.array):
    result = dict()

    for idx in range(leaf.shape[0]):
        elem_idx = leaf[idx]

        for node_idx in range(topo_array.shape[1]):
            node = topo_array[elem_idx, node_idx]
            if node not in result:
                result[node] = int_list()

            result[node].append(idx)

    return result


@jit(parallel=True)
def calculate_expanded_face_inds(expanded_face_inds: np.array, topo_array: np.array, leaf: np.array,
                                 face_inds: np.array):
    num_faces: int = face_inds.shape[0]
    face_size: int = face_inds.shape[1]

    for idx in prange(leaf.shape[0]):
        elem_idx: int = leaf[idx]

        for face_idx in range(num_faces):
            for felem_idx in range(face_size):
                expanded_face_inds[idx, face_idx, felem_idx] = topo_array[elem_idx, face_inds[face_idx, felem_idx]]


@timing
def calculate_mesh_ext_adj(mesh: Mesh, topo_name=None, octree_threshold=1000, octree_depth=3):
    topo_name = topo_name or first(t for t in mesh.topos if mesh.topos[t][2])
    ext_adj_key = (topo_name, MeshDataType._ext_adj)

    topo_ext_adj = mesh.other_data.get(ext_adj_key, None)

    if topo_ext_adj is None:
        topo_array, et_name, _ = mesh.topos[topo_name]
        et: ElemTypeDef = ElemType[et_name]

        if topo_array.shape[0] < octree_threshold:
            leaf_inds = [np.arange(topo_array.shape[0])]
        else:
            octree = calculate_mesh_octree(mesh, topo_name, octree_depth)
            leaf_inds = [leaf.leafdata for leaf in octree.leaves if len(leaf.leafdata) > 0]

        face_inds = np.array(et.faces)[:, :-1]  # remove far node index

        topo_ext_adj = -np.ones((topo_array.shape[0], et.num_faces * 2), dtype=int)

        for leafdata in leaf_inds:
            leafdata = np.array(leafdata)
            num_faces = face_inds.shape[0]
            face_size = face_inds.shape[1]

            expanded_face_inds = np.zeros((leafdata.shape[0], num_faces, face_size), dtype=int)
            calculate_expanded_face_inds(expanded_face_inds, topo_array, leafdata, face_inds)
            expanded_face_inds = np.sort(expanded_face_inds, axis=2)

            _calculate_leaf_ext_adj(expanded_face_inds, topo_array, leafdata, face_inds, topo_ext_adj)

        mesh.other_data[ext_adj_key] = topo_ext_adj

    return topo_ext_adj


@jit(parallel=True)
def _calculate_leaf_ext_adj(expanded_face_inds: np.array, topo_array: np.array, leaf: np.array,
                            face_inds: np.array, topo_ext_adj: np.array):
    shared_nodes = calculate_shared_nodes(topo_array, leaf)

    num_elems = leaf.shape[0]
    num_faces = face_inds.shape[0]

    for idx in prange(num_elems):
        elem_idx = leaf[idx]

        for face_idx in range(num_faces):
            if topo_ext_adj[elem_idx, face_idx] > -1:
                continue

            face = expanded_face_inds[idx, face_idx]
            other_elems = set()

            for face_elem_idx in range(face.shape[0]):
                other_elems.update(shared_nodes[face[face_elem_idx]])

            for other_idx in other_elems:
                if other_idx == idx:
                    continue

                for other_face_idx in range(num_faces):
                    if np.array_equal(expanded_face_inds[other_idx, other_face_idx], face):
                        other_elem = leaf[other_idx]

                        topo_ext_adj[elem_idx, face_idx] = other_elem
                        topo_ext_adj[elem_idx, face_idx + num_faces] = other_face_idx
                        topo_ext_adj[other_elem, other_face_idx] = elem_idx
                        topo_ext_adj[other_elem, other_face_idx + num_faces] = face_idx


@timing
def calculate_tri_elem_face_meshes(et: ElemTypeDef, refine=0):
    fet: ElemTypeDef = et.face_type
    num_faces: int = et.num_faces

    if fet.is_simplex:
        nodes, tri_inds = divide_tri_to_tri_mesh(refine)
    else:
        nodes, tri_inds = divide_quad_to_tri_mesh(refine)

    xis = np.zeros((num_faces, len(nodes), 3))
    coeffs = np.zeros((num_faces, len(nodes), et.num_nodes))
    inds = np.zeros((num_faces, len(tri_inds), 3), dtype=np.int32)

    for face_idx in range(num_faces):
        for i, (xi0, xi1) in enumerate(nodes):
            xi = et.face_xi_to_elem_xi(face_idx, xi0, xi1)
            xis[face_idx, i] = xi
            coeffs[face_idx, i] = et.basis(*xi)

        inds[face_idx, :] = tri_inds

        # calculate the normal of the first triangle in xi space
        a, b, c = tri_inds[0]
        verta = vec3(*xis[face_idx, a])
        vertb = vec3(*xis[face_idx, b])
        vertc = vec3(*xis[face_idx, c])
        xi_norm = verta.plane_norm(vertb, vertc)

        # calculate a vector point from the face surface towards the inside of the element in xi space
        vertex_idx = et.get_face_vertex_indices(face_idx)[0]
        vert_xi = vec3(*et.xis[vertex_idx])
        vert_inner_sub = vec3(*et.face_xi_norms[face_idx])
        xi_inner = (vert_xi - vert_inner_sub).norm

        if xi_norm.angle_to(vert_inner_sub) <= FEPSILON:
            tmp = inds[face_idx, :, 2].copy()
            inds[face_idx, :, 2] = inds[face_idx, :, 1]
            inds[face_idx, :, 1] = tmp

    return xis, coeffs, inds


@jit
def apply_coeffs_elem(nodes, inds, ind_idx, coeffs):
    """
    Interpolate the node values given by `nodes` of the element at `ind_idx` in the index matrix `inds`. The `coeffs`
    array of coefficients provides the multiplication values for each node value. The result is equivalent to:
        np.sum([coeffs[i] * nodes[inds[ind_idx, i]] for i in range(inds.shape[1])],axis=0)
    """
    result = coeffs[0] * nodes[inds[ind_idx, 0]]

    for i in range(1, inds.shape[1]):
        result += coeffs[i] * nodes[inds[ind_idx, i]]

    return result


@timing
def calculate_tri_mesh(mesh: Mesh, refine=0, topo_name=None, external_only=True, octree_depth=3):
    topo_name = topo_name or first(t for t in mesh.topos if mesh.topos[t][2])
    nodes = mesh.nodes
    topo_array, et_name, _ = mesh.topos[topo_name]
    et: ElemTypeDef = ElemType[et_name]

    ext_adj = calculate_mesh_ext_adj(mesh, topo_name, octree_depth=octree_depth)
    face_xis, coeffs, face_tris = calculate_tri_elem_face_meshes(et, refine)

    num_elems = topo_array.shape[0]

    if external_only:
        ext_faces = ext_adj[:, :et.num_faces] < 0
        num_ext_faces = np.sum(ext_faces)
        start_elem_idx = np.cumsum(np.sum(ext_faces, axis=1))
        start_elem_idx[1:] = start_elem_idx[:-1]
        start_elem_idx[0] = 0
    else:
        ext_faces = np.ones_like(ext_adj[:, :et.num_faces], dtype=np.bool)
        num_ext_faces = et.num_faces * num_elems
        start_elem_idx = np.arange(num_elems) * et.num_faces

    num_face_nodes = face_xis.shape[1]
    num_face_tris = face_tris.shape[1]
    num_nodes = num_face_nodes * num_ext_faces
    num_inds = num_face_tris * num_ext_faces

    out_nodes = np.zeros((num_nodes, nodes.shape[1]), dtype=nodes.dtype)
    out_xis = np.zeros((num_nodes, 3), dtype=np.float32)
    out_inds = np.zeros((num_inds, 3), dtype=np.int32)
    out_props = np.zeros((num_nodes, 2), dtype=np.int32)

    # for elem_idx in range(num_elems):
    #     node_idx = start_elem_idx[elem_idx] * num_face_nodes
    #     inds_idx = start_elem_idx[elem_idx] * num_face_tris
    #
    #     for face_idx in range(ext_faces.shape[1]):
    #         if ext_faces[elem_idx, face_idx]:
    #             out_inds[inds_idx:inds_idx + num_face_tris] = face_tris[face_idx] + node_idx
    #             out_xis[node_idx:node_idx + num_face_nodes] = face_xis[face_idx]
    #             out_props[node_idx:node_idx + num_face_nodes, 0] = elem_idx
    #             out_props[node_idx:node_idx + num_face_nodes, 1] = face_idx
    #
    #             for nidx in range(num_face_nodes):
    #                 out_nodes[node_idx] = apply_coeffs_elem(nodes, topo_array, elem_idx, coeffs[face_idx, nidx])
    #                 node_idx += 1
    #
    #             inds_idx += num_face_tris

    _calculate_tri_mesh_main(num_elems, num_face_nodes, num_face_tris,
                             nodes, topo_array,
                             ext_faces, start_elem_idx, face_tris, face_xis,
                             coeffs, out_nodes, out_inds, out_xis, out_props)

    if et.dim == 3:
        linet: ElemTypeDef = ElemType.get_linear_type(et)

        elem_dirs = get_xi_elem_directions(linet.xis)
        elem_dirs = np.array(elem_dirs)

        for elem_idx in range(num_elems):
            elem_inds = topo_array[elem_idx]
            elem_nodes = [vec3(*nodes[elem_inds[v]]) for v in range(linet.num_nodes)]
            is_inverted = False

            for a, b, c, d in elem_dirs:
                v0 = elem_nodes[a]
                v1 = elem_nodes[b]
                v2 = elem_nodes[c]
                v3 = elem_nodes[d]

                if v0.plane_norm(v1, v2).angle_to(v3 - v0) > HALFPI:
                    is_inverted = True
                    break

            if is_inverted:
                start_idx = start_elem_idx[elem_idx] * num_face_tris
                if (elem_idx + 1) < start_elem_idx.shape[0]:
                    end_idx = start_elem_idx[elem_idx + 1] * num_face_tris
                else:
                    end_idx = out_inds.shape[0]

                out_inds[start_idx:end_idx, :] = out_inds[start_idx:end_idx, (0, 2, 1)]

    out_mesh = Mesh(out_nodes, {"inds": (out_inds, ElemType._Tri1NL)})
    out_mesh.other_data["xis"] = out_xis
    out_mesh.other_data["parent"] = mesh

    return out_mesh


@jit(parallel=True)
def _calculate_tri_mesh_main(
        num_elems: int,
        num_face_nodes: int,
        num_face_tris: int,
        nodes: np.ndarray,
        topo_array: np.ndarray,
        ext_faces: np.ndarray,
        start_elem_idx: np.ndarray,
        face_tris: np.ndarray,
        face_xis: np.ndarray,
        coeffs: np.ndarray,
        out_nodes: np.ndarray,
        out_inds: np.ndarray,
        out_xis: np.ndarray,
        out_props: np.ndarray
):
    for elem_idx in prange(num_elems):
        node_idx = start_elem_idx[elem_idx] * num_face_nodes
        inds_idx = start_elem_idx[elem_idx] * num_face_tris

        for face_idx in range(ext_faces.shape[1]):
            if ext_faces[elem_idx, face_idx]:
                out_inds[inds_idx:inds_idx + num_face_tris] = face_tris[face_idx] + node_idx
                out_xis[node_idx:node_idx + num_face_nodes] = face_xis[face_idx]
                out_props[node_idx:node_idx + num_face_nodes, 0] = elem_idx
                out_props[node_idx:node_idx + num_face_nodes, 1] = face_idx

                for nidx in range(num_face_nodes):
                    out_nodes[node_idx] = apply_coeffs_elem(nodes, topo_array, elem_idx, coeffs[face_idx, nidx])
                    node_idx += 1

                inds_idx += num_face_tris
