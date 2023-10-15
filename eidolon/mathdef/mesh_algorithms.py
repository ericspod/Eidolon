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

from typing import Callable, Optional

import numpy as np

from eidolon.utils import first, timing
from .compile_support import has_numba, jit, prange
from .elem_type import ElemType, ElemTypeDef, get_xi_elem_directions
from .math_types import vec3
from .math_utils import FEPSILON, HALFPI, angle_between, len3, plane_norm
from .mesh import Mesh, MeshDataValue, Topology, Field
from .mesh_utils import divide_quad_to_tri_mesh, divide_tri_to_tri_mesh
from .octree import Octree

__all__ = [
    "calculate_mesh_octree",
    "calculate_shared_nodes",
    "calculate_mesh_ext_adj",
    "calculate_surface_mesh",
    "calculate_tri_mesh",
    "calculate_field",
    "calculate_field_colors",
    "calculate_trimesh_normals",
    "calculate_inverted_tri_mesh",
]


@timing
def calculate_mesh_octree(mesh: Mesh, topo_name=None, depth=3):
    topo_name = topo_name or first(mesh.topos)
    topo_array, *_ = mesh.topos[topo_name]

    other_key = (MeshDataValue._octree, topo_name)

    oc = mesh.other_data.get(other_key, None)

    if oc is None:
        nodes = [vec3(*v) for v in mesh.nodes]
        oc = Octree.from_mesh(depth, nodes, topo_array)
        mesh.other_data[other_key] = oc

    return oc


# calculate_shared_nodes() needs a generic way to create a Numba List object if present, or a Python list if not
if has_numba:
    from numba.core import types
    from numba.typed import List

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


@timing
@jit(parallel=True)
def calculate_trimesh_normals(nodes: np.ndarray, triinds: np.ndarray):
    normals = np.zeros_like(nodes)
    for tri_idx in prange(triinds.shape[0]):
        a, b, c = triinds[tri_idx, :3]
        nx, ny, nz = plane_norm(
            nodes[a, 0],
            nodes[a, 1],
            nodes[a, 2],
            nodes[b, 0],
            nodes[b, 1],
            nodes[b, 2],
            nodes[c, 0],
            nodes[c, 1],
            nodes[c, 2],
        )

        normals[a, 0] += nx
        normals[a, 1] += ny
        normals[a, 2] += nz
        normals[b, 0] += nx
        normals[b, 1] += ny
        normals[b, 2] += nz
        normals[c, 0] += nx
        normals[c, 1] += ny
        normals[c, 2] += nz

    for norm_idx in prange(normals.shape[0]):
        nl: float = len3(normals[norm_idx, 0], normals[norm_idx, 1], normals[norm_idx, 2])
        if nl != 0:
            normals[norm_idx] /= nl

    return normals


@jit(parallel=True)
def calculate_expanded_face_inds(
    expanded_face_inds: np.array, topo_array: np.array, leaf: np.array, face_inds: np.array
):
    num_faces: int = face_inds.shape[0]
    face_size: int = face_inds.shape[1]

    for idx in prange(leaf.shape[0]):
        elem_idx: int = leaf[idx]

        for face_idx in range(num_faces):
            for felem_idx in range(face_size):
                expanded_face_inds[idx, face_idx, felem_idx] = topo_array[elem_idx, face_inds[face_idx, felem_idx]]


@timing
def calculate_mesh_ext_adj(mesh: Mesh, topo_name=None, octree_threshold=100000, octree_depth=3):
    topo_name = topo_name or first(t for t in mesh.topos if mesh.topos[t].is_field_topo)
    ext_adj_key = (MeshDataValue._ext_adj, topo_name)

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
def _calculate_leaf_ext_adj(
    expanded_face_inds: np.array, topo_array: np.array, leaf: np.array, face_inds: np.array, topo_ext_adj: np.array
):
    shared_nodes = calculate_shared_nodes(topo_array, leaf)

    num_elems = leaf.shape[0]
    num_faces = face_inds.shape[0]

    for idx in prange(num_elems):
        elem_idx = leaf[idx]

        for face_idx in range(num_faces):
            if topo_ext_adj[elem_idx, face_idx] > -1:
                continue

            other_elems = set()
            face = expanded_face_inds[idx, face_idx]

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
def calculate_tri_elem_face_meshes(et: ElemTypeDef, refine: int = 0):
    """
    Calculate the triangle meshes for each of the faces of the given element type. An element of type `et` has
    `num_faces` number of faces and so there is a mesh for each with xi coordinates, basis function coefficients, and
    triangle indices. Each face will have `num_nodes` number of vertices to the mesh with `num_inds` number of
    triangles. This function assumes the faces of `et` are all the same shape, ie. prisms not represented.

    Arguments:
        et: element type to generate the face meshes for
        refine: refinement level for the meshes

    Returns:
        xis: (num_faces, num_nodes, 3) shape array with xi coordinates for each vertex for each face
        coeffs: (num_faces, num_nodes, et.num_nodes) shape array with coefficient weights for every mesh vertex
        inds: (num_faces, num_inds, 3) shape array with triangle indices for the mesh
    """
    fet: ElemTypeDef = et.face_type
    num_faces: int = et.num_faces

    if fet.is_simplex:
        nodes, tri_inds = divide_tri_to_tri_mesh(refine)
    else:
        nodes, tri_inds = divide_quad_to_tri_mesh(refine)

    xis = np.zeros((num_faces, len(nodes), 3))
    coeffs = np.zeros((num_faces, len(nodes), et.num_nodes))
    inds = np.zeros((num_faces, len(tri_inds), 3), dtype=np.int32)

    # for each face calculate the mesh with outward facing triangle windings
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

        # ensure the triangle winding order is facing outwards for 3D elements
        if len(et.face_xi_norms) > 0:
            # calculate a vector point from the face surface towards the inside of the element in xi space
            vert_inner_sub = vec3(*et.face_xi_norms[face_idx]).norm

            if xi_norm.angle_to(vert_inner_sub) > FEPSILON:
                inds[face_idx] = inds[face_idx, :][:, (0, 2, 1)]

    return xis, coeffs, inds


@jit
def apply_coeffs_elem(field, inds, ind_idx, coeffs):
    """
    Interpolate the node values given by `field` of the element at `ind_idx` in the index matrix `inds`. The `coeffs`
    array of coefficients provides the multiplication values for each node value. The result is equivalent to:
        np.sum([coeffs[i] * nodes[inds[ind_idx, i]] for i in range(inds.shape[1])],axis=0)
    """
    result = coeffs[0] * field[inds[ind_idx, 0]]

    for i in range(1, inds.shape[1]):
        result += coeffs[i] * field[inds[ind_idx, i]]

    return result


@jit
def is_elem_inverted(nodes: np.ndarray, elem: np.ndarray, elem_dirs: np.ndarray):
    """
    Returns True if the element defined by indices `elem` is inverted, that is at least one cross product of edge
    vectors as stored in `elem_dirs` differs in the reference xi space versus the space defined by 3D points `nodes`.
    """
    for idx in range(elem_dirs.shape[0]):
        ax, ay, az = nodes[elem[elem_dirs[idx, 0]], :3]
        bx, by, bz = nodes[elem[elem_dirs[idx, 1]], :3]
        cx, cy, cz = nodes[elem[elem_dirs[idx, 2]], :3]
        dx, dy, dz = nodes[elem[elem_dirs[idx, 3]], :3]

        nx, ny, nz = plane_norm(ax, ay, az, bx, by, bz, cx, cy, cz)

        if angle_between(nx, ny, nz, dx - ax, dy - ay, dz - az) > HALFPI:
            return True

    return False


@timing
def calculate_surface_mesh(mesh: Mesh, refine=0, topo_name=None):
    """
    Calculate a surface triangle mesh from the given 2D mesh. This requires the mesh to have 2D elements only. The
    `refine` value is ignored.
    """
    topo_name = topo_name or first(t for t in mesh.topos if not mesh.topos[t].is_field_topo)
    nodes = mesh.nodes
    topo_array, et_name, _ = mesh.topos[topo_name]
    et: ElemTypeDef = ElemType[et_name]
    num_nodes = nodes.shape[0]

    if et.dim != 2:
        raise ValueError("Only 2D meshes can be made into surfaces directly, 3D meshes must be volumes")

    if et.name != "Tri1NL":
        raise NotImplementedError("Only triangles meshes can be made into surfaces currently")

    out_nodes = nodes
    out_inds = topo_array
    out_norms = mesh.other_data.get(MeshDataValue._norms, None)

    if out_norms is None:
        out_norms = calculate_trimesh_normals(out_nodes, out_inds)

    out_mesh = Mesh(out_nodes, {"inds": (out_inds, ElemType._Tri1NL)}, {}, mesh.timestep, mesh)
    out_mesh.other_data.update(mesh.other_data)
    out_mesh.other_data[MeshDataValue._xis] = None
    out_mesh.other_data[MeshDataValue._norms] = out_norms
    out_mesh.other_data[MeshDataValue._nodeprops] = None

    return out_mesh


@timing
def calculate_tri_mesh(
    mesh: Mesh, refine=0, topo_name=None, external_only=True, octree_threshold=100000, octree_depth=3
):
    """
    Calculates a triangle mesh from the given Mesh object.
    """
    topo_name = topo_name or first(t for t in mesh.topos if not mesh.topos[t].is_field_topo)
    nodes = mesh.nodes
    topo_array, et_name, _ = mesh.topos[topo_name]
    et: ElemTypeDef = ElemType[et_name]

    face_xis, coeffs, face_tris = calculate_tri_elem_face_meshes(et, refine)
    num_elems = topo_array.shape[0]

    if et.dim < 2:
        raise ValueError(f"Triangles can only be generated for 2/3D element types, not {et_name}")
    elif et.dim == 2:
        ext_adj = -np.ones((num_elems, 1), dtype=int)  # don't need to do adjacency calculation
        external_only = False  # generate all faces since they're all external
    else:
        ext_adj = calculate_mesh_ext_adj(mesh, topo_name, octree_threshold, octree_depth)

    if external_only:
        ext_faces = ext_adj[:, : et.num_faces] < 0
        num_ext_faces = np.sum(ext_faces)
        start_elem_idx = np.cumsum(np.sum(ext_faces, axis=1))
        start_elem_idx[1:] = start_elem_idx[:-1]
        start_elem_idx[0] = 0
    else:
        ext_faces = np.ones_like(ext_adj[:, : et.num_faces], dtype=bool)
        num_ext_faces = et.num_faces * num_elems
        start_elem_idx = np.arange(num_elems) * et.num_faces

    num_face_nodes = face_xis.shape[1]
    num_face_tris = face_tris.shape[1]
    num_nodes = num_face_nodes * num_ext_faces
    num_inds = num_face_tris * num_ext_faces

    out_nodes = np.zeros((num_nodes, nodes.shape[1]), dtype=nodes.dtype)  # output nodes
    out_xis = np.zeros((num_nodes, 3), dtype=np.float32)  # xi coordinate of each node
    out_inds = np.zeros((num_inds, 3), dtype=np.int32)  # output triangle indices
    out_props = np.zeros((num_nodes, 2), dtype=np.int32)  # element and face indices for each node

    # if this is a 3D element compute the element edge direction matrix to detect inverted elements
    if et.dim == 3:
        linet: ElemTypeDef = ElemType.get_linear_type(et)

        elem_dirs = get_xi_elem_directions(linet.xis)
        elem_dirs = np.array(elem_dirs, np.int32)
    else:
        elem_dirs = np.array([(-1, -1, -1, -1)], np.int32)  # fake set of cross product indices for 2D elements

    _calculate_tri_mesh_main(
        num_elems,
        num_face_nodes,
        num_face_tris,
        nodes,
        topo_array,
        ext_faces,
        start_elem_idx,
        face_tris,
        face_xis,
        coeffs,
        elem_dirs,
        out_nodes,
        out_inds,
        out_xis,
        out_props,
    )

    out_norms = calculate_trimesh_normals(out_nodes, out_inds)

    out_mesh = Mesh(out_nodes, {"inds": (out_inds, ElemType._Tri1NL)}, {}, mesh.timestep, mesh)
    out_mesh.other_data[MeshDataValue._xis] = out_xis
    out_mesh.other_data[MeshDataValue._norms] = out_norms
    out_mesh.other_data[MeshDataValue._nodeprops] = out_props

    return out_mesh


@jit(parallel=True)
def _calculate_tri_mesh_main(
    num_elems: int,
    num_face_nodes: int,
    num_face_tris: int,
    nodes: np.ndarray,
    topo_array: np.ndarray,
    selected_faces: np.ndarray,
    start_elem_idx: np.ndarray,
    face_tris: np.ndarray,
    face_xis: np.ndarray,
    coeffs: np.ndarray,
    elem_dirs: np.ndarray,
    out_nodes: np.ndarray,
    out_inds: np.ndarray,
    out_xis: np.ndarray,
    out_props: np.ndarray,
):
    for elem_idx in prange(num_elems):
        node_idx: int = start_elem_idx[elem_idx] * num_face_nodes
        inds_idx: int = start_elem_idx[elem_idx] * num_face_tris
        cur_inds_idx: int = inds_idx

        # generate triangles for every selected face
        for face_idx in range(selected_faces.shape[1]):
            if selected_faces[elem_idx, face_idx]:
                out_inds[cur_inds_idx : cur_inds_idx + num_face_tris] = face_tris[face_idx] + node_idx
                out_xis[node_idx : node_idx + num_face_nodes] = face_xis[face_idx]
                out_props[node_idx : node_idx + num_face_nodes, 0] = elem_idx
                out_props[node_idx : node_idx + num_face_nodes, 1] = face_idx

                for nidx in range(num_face_nodes):
                    out_nodes[node_idx] = apply_coeffs_elem(nodes, topo_array, elem_idx, coeffs[face_idx, nidx])
                    node_idx += 1

                cur_inds_idx += num_face_tris

        # if the element is inverted, swap triangle winding order
        if elem_dirs[0, 0] >= 0 and is_elem_inverted(nodes, topo_array[elem_idx], elem_dirs):
            tmp = out_inds[inds_idx:cur_inds_idx, 1].copy()
            out_inds[inds_idx:cur_inds_idx, 1] = out_inds[inds_idx:cur_inds_idx, 2]
            out_inds[inds_idx:cur_inds_idx, 2] = tmp


@timing
def calculate_field(mesh: Mesh, field_name: str):
    field_array, _, field_topo_name, is_per_elem = mesh.parent.fields[field_name]
    field_topo, fet_name, _ = mesh.parent.topos[field_topo_name]

    fet = ElemType[fet_name]
    xis = mesh.other_data[MeshDataValue._xis]
    props = mesh.other_data[MeshDataValue._nodeprops]

    if field_array.ndim == 1:
        out_field_size = (mesh.nodes.shape[0],)
    else:
        out_field_size = (mesh.nodes.shape[0], field_array.shape[1])

    out_field = np.zeros(out_field_size, dtype=field_array.dtype)

    for node_idx in range(xis.shape[0]):
        elem_idx = props[node_idx, 0]

        if is_per_elem:
            out_field[node_idx] = field_array[elem_idx]
        else:
            coeffs = fet.basis(xis[node_idx, 0], xis[node_idx, 1], xis[node_idx, 2])
            out_field[node_idx] = apply_coeffs_elem(field_array, field_topo, elem_idx, coeffs)

    mesh.set_field(field_name, out_field, field_topo_name)

    return out_field


@timing
def calculate_field_colors(mesh: Mesh, field_name: str, color_func: Callable, convert: Optional[Callable] = None):
    field_array: np.ndarray = mesh.fields[field_name].data
    out_colors = np.zeros((field_array.shape[0], 4))

    if field_array.ndim > 1 and convert is not None:
        field_array = convert(field_array)

    field_array = (field_array - field_array.min()) / field_array.ptp()

    for field_idx in range(field_array.shape[0]):
        out_colors[field_idx] = color_func(field_array[field_idx])

    mesh.other_data[MeshDataValue._colors] = out_colors

    return out_colors


@timing
def calculate_inverted_tri_mesh(mesh: Mesh):
    """Calculate an inside-out mesh from the given triangle mesh"""
    out_topos = {}

    # invert triangle topologies
    for name, topo in mesh.topos.items():
        if not topo.is_field_topo and topo.elem_type == ElemType._Tri1NL:
            data = topo.data.copy()
            out_topos[name] = Topology(data[:, [0, 2, 1]], topo.elem_type, False)
        else:
            out_topos[name] = topo

    out_mesh = Mesh(mesh.nodes, out_topos, mesh.fields, mesh.timestep, mesh.parent)
    out_mesh.other_data = dict(mesh.other_data)
    out_mesh.properties = dict(mesh.properties)

    # invert norms
    norms = out_mesh.other_data.get(MeshDataValue._norms, None)
    if norms is not None:
        out_mesh.other_data[MeshDataValue._norms] = -norms

    return out_mesh
