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

"""
2D node ordering:

     2     2--3
y    |\    |  |
^    | \   |  |
|    0--1  0--1
+->x



"""
from __future__ import annotations
import itertools
import functools
import re
from typing import Optional, Callable

from ..utils import Namespace, NamespaceMeta, cached_property, is_iterable_notstr, mulsum
from .math_utils import lerp, lerp_xi, FEPSILON
from .basis_functions import lagrange_basis, ShapeType
from .math_types import vec3

__all__ = ["ElemType", "ElemTypeDef", "BasisGenFuncs","get_xi_elem_directions"]


class ElemTypeDef(object):
    """
    Defines a mesh element type, including the basis function and its face definition.
    """

    def __init__(self, shape_type: str, basis_name: str, desc: str, order: int, xis: list, vertices: list,
                 faces: list, edges: list, face_xi_norms: list, xi_elem_dirs: list, basis: Callable,
                 point_search: Optional[Callable], face_type: Optional[ElemTypeDef]):

        self.shape_type: str = shape_type  # geometry (tet, hex, etc)
        self.dim: int = ShapeType[shape_type][1]  # spatial dimensions
        self.is_simplex: bool = ShapeType[shape_type][2]  # whether the element is simplex (tri,tet) or not
        self.basis_name: str = basis_name  # basis function name (NL=nodal lagrange, etc)
        self.desc: str = desc  # plain language description
        self.order: int = order  # order (1=linear, 2=quadratic, etc)
        self.xis: list = list(xis)  # xi values for each node, [] if node count not fixed
        self.center_xi: tuple = (0.25 if self.is_simplex else 0.5,) * self.dim
        self.vertices: list = list(vertices)  # list of vertex topos, [] if node count not fixed
        self.faces: list = list(faces)  # list of face node topos, [] if node count not fixed
        self.xi_elem_dirs = list(xi_elem_dirs)  # list of xi element direction index quadruples

        # basis callable, maps xi values to node coefficients, must accept x, y, z coordinate
        # arguments plus any further positional and keyword args
        self.basis: Callable = basis

        self.point_search: Optional[Callable] = point_search  # callable which implements point search for this type
        self.face_xi_norms: list = list(face_xi_norms)  # per-face xi space normals
        self.edges: list = edges  # tuples of xi indices defining edges on 1D/2D elements, vertices first then midpoints

        # ElemTypeDef defining faces as 2D elements (assumes all faces same shape)
        self.face_type: ElemTypeDef = face_type or self

    @cached_property
    def name(self):
        return ElemType.get_elem_type_name(self.shape_type, self.basis_name, self.order)

    @cached_property
    def is_fixed_node_count(self):
        """Returns true if the basis function is defined for a fixed number of control nodes, eg. nodal lagrange."""
        return bool(self.xis)

    @cached_property
    def num_nodes(self):
        """Returns the number of nodes used to define this basis type, -1 if not fixed."""
        return len(self.xis) if self.is_fixed_node_count else -1

    @cached_property
    def num_vertices(self):
        """Returns the number of corner nodes, -1 if not fixed."""
        return len(self.vertices) if self.is_fixed_node_count else -1

    @cached_property
    def num_faces(self):
        """Returns the number of faces, -1 if not fixed."""
        return len(self.faces) if self.is_fixed_node_count else -1

    @cached_property
    def face_vertices(self):
        # vertex indices for each face
        return [len(set(self.get_face_indices(i)).intersection(self.vertices)) for i in range(len(self.faces))]

    def num_face_vertices(self, face=0):
        """Returns the number of vertices for a face, or -1 if not fixed."""
        return self.face_vertices[face] if face < len(self.face_vertices) else -1

    def get_face_indices(self, face):
        """Returns the topos for a face, or [] if not fixed."""
        # return v1.faces[face][:-1] if v1.is_fixed_node_count() else -1
        if face >= len(self.faces) or not self.is_fixed_node_count:
            return []
        elif self.dim < 3:
            return self.faces[face]
        else:
            return self.faces[face][:-1]

    def get_face_vertex_indices(self, face):
        numverts = self.num_face_vertices(face)
        if numverts <= 0:
            return []
        else:
            return self.get_face_indices(face)[:numverts]

    def get_face_type(self, face, as_linear=False):
        if is_iterable_notstr(self.face_type):
            facetype = self.face_type[face]
        else:
            facetype = self.face_type

        if as_linear:
            facetype = ElemType.get_linear_type(facetype)

        return facetype

    def get_face_far_index(self, face):
        """Returns the index of a vertex far from the given face, or -1 if not fixed or is not applicable."""
        if face < len(self.faces) and self.dim == 3 and self.is_fixed_node_count:
            return self.faces[face][-1]
        else:
            return -1

    def get_internal_face_xi_sub(self, face):
        """Returns the value to subtract from a xi on the given face to get an internal xi coordinate."""
        return self.internalxis[face]

    def apply_basis(self, vals, xi0, xi1, xi2, *args, **kwargs):
        """
        Evaluates the basis function at the xi point, multiplies the values by the coefficients, and sums the result.
        """
        assert len(self.xis) in (0, len(vals)), 'Number of values (%i) does not match control point count (%i)' % (
            len(vals), len(self.xis))
        return self.apply_coeffs(vals, self.basis(xi0, xi1, xi2, *args, **kwargs))

    def apply_coeffs(self, vals, coeffs):
        """Apply the given coefficients to the given values and return the summed result."""
        assert is_iterable_notstr(vals)
        assert is_iterable_notstr(coeffs)
        assert len(vals) == len(coeffs), '%i != %i' % (len(vals), len(coeffs))

        if isinstance(vals[0], (list, tuple)):
            result = [0] * len(vals[0])
            for c, val in zip(coeffs, vals):
                for j, v in enumerate(val):
                    result[j] += v * c

            return tuple(result)
        else:
            return mulsum(vals, coeffs)

    def face_xi_to_elem_xi(self, face, xi0, xi1):
        """
        Convert the xi value (xi0,xi1) on face number `face` to an element xi value for a 3D element. If self.dim
        is less than 3, the result is simply (xi0,xi1,0). This relies on face 0 being on the xi YZ plane at xi2=0.
        """
        if self.dim < 3:
            return xi0, xi1, 0

        result = [0, 0, 0]
        facetype = self.get_face_type(face, True)
        coeffs = facetype.basis(xi0, xi1, 0)  # coeffs within the xi space of this face
        finds = self.get_face_indices(face)  # topos for the nodes of the element defining this face

        # interpolate the xi coordinates of the nodes defining this face
        for c, f in zip(coeffs, finds):
            v = self.xis[f]
            result[0] += v[0] * c
            result[1] += v[1] * c
            result[2] += v[2] * c

        return tuple(result)

    def apply_point_search(self, elemnodes, pt, refine, *args, **kwargs):
        """
        Attempt to find the xi coordinate in an element defined by node values `elemnodes` of the spatial point `pt`.
        """
        if len(elemnodes) != self.num_nodes:
            raise ValueError(
                f"Must supply as many element node values as nodes for this element {len(elemnodes)}!={self.num_nodes}"
            )

        return self.point_search(self, elemnodes, pt, refine, *args, **kwargs)

    def __repr__(self):
        return f"{self.name}: {self.desc}"


def find_faces(xis, num_vertices, is_simplex):
    """
    Find the faces of an axis-aligned element (tet or hex) with unit xi coordinates. This adheres to CHeart node
    ordering. The first topos for each face will be the vertices, the last is the index for a node opposite the face.
    A more general face-finding operation would look for those nodes defining vertices and then the nodes between them
    to find faces, but life is easier with axis-aligned elements. Other geometry types other than tet or hex would
    require modification to this function. The first return value is a list of face index lists, the second is a list
    of xi values which when subtracted from a xi coordinate on the face will produce an internal xi coordinate.
    """
    faces = []
    face_xi_norms = []  # values to subtract from surface xis to get an internal xi coord
    xi_dim = len(xis[0])
    xi_range = (0.0,) if is_simplex else (0.0, 1.0)

    def farnode(_face, _xirange):
        # assumes vertices are indexed in the range [0,num_vertices], ie. CHeart node ordering
        vertices = [i for i in range(num_vertices) if i not in _face]
        return vertices[int(_xirange) - 1]

    # collect axis-aligned faces
    for dim, xirange in itertools.product(range(xi_dim), xi_range):
        # collect the topos of each xi value whose component 'dim' equals 'xirange' (which is 0 or 1)
        face = [n for n, xi in enumerate(xis) if xi[dim] == xirange]
        if len(face) > 0:
            far = farnode(face, xirange)
            faces.append(face + [far])

            xi_norm = [0.0] * xi_dim
            xi_norm[dim] = 1.0 if xirange == 1.0 else -1.0
            face_xi_norms.append(xi_norm)

    # collect tet far face passing through unit vectors
    if is_simplex:
        face = [n for n, xi in enumerate(xis) if sum(xi) == 1.0]
        if face != ():
            far = farnode(face, 0)
            faces.append(face + [far])
            face_xi_norms.append([1.0] * xi_dim)

    def _cmp(a, b):
        a = faces[a]
        b = faces[b]
        return (a > b) - (a < b)

    # topos=sorted(range(len(faces)),key=lambda i:faces[i])
    indices = sorted(range(len(faces)), key=functools.cmp_to_key(_cmp))

    return [faces[i] for i in indices], [face_xi_norms[i] for i in indices]


def find_edges(xis, num_vertices, is_simplex):
    def crosses_midpoint(a, b):
        """Returns True if the line from `a` to `b` crosses the midpoint of a face or element, ie. is diagonal."""
        return sum(abs(i * 0.5 + j * 0.5 - 0.5) < FEPSILON for i, j in zip(a, b)) in (2, 3)

    def within(v, a, b):
        """Returns True if `v' is within range [a,b], or [b,a] if b<=a."""
        return a <= v <= b if a <= b else b <= v <= a

    def is_line_point(p, xi, start, end):
        """Returns True if point `p' is at xi position `xi' on line `start'->`end'."""
        return all(abs(lerp(xi, j, k) - i) < FEPSILON for i, j, k in zip(p, start, end))

    def is_between(a, start, end):
        """Returns True if `a' lies on a line between `start' and `end'."""
        xi = max(lerp_xi(i, j, k) if j != k else 0 for i, j, k in zip(a, start, end))

        if not all(within(i, j, k) for i, j, k in zip(a, start, end)):
            return False

        return is_line_point(a, xi, start, end) or is_line_point(a, xi, end, start)

    found = []
    edges = []

    for v1, v2 in itertools.product(range(num_vertices), repeat=2):
        if v1 != v2 and (v1, v2) not in found:
            xi1 = xis[v1]
            xi2 = xis[v2]

            if is_simplex or not crosses_midpoint(xi1, xi2):
                # get the midpoints
                mids = [i for i in range(len(xis)) if i != v1 and i != v2 and is_between(xis[i], xi1, xi2)]

                edges.append(tuple([v1, v2] + mids))  # add the edge, vertices first
                found += [(v1, v2), (v2, v1)]

    return edges


def get_xi_elem_directions(xis):
    """
    Returns quadruples of node indices for the xi coordinates `xis` such that the normal of the plane defined by the
    first three nodes points in the direction of the fourth in xi space.
    """
    cross_prods = []

    for a, b, c, d in itertools.permutations(range(len(xis)), 4):
        v0 = vec3(*xis[a])
        v1 = vec3(*xis[b])
        v2 = vec3(*xis[c])
        v3 = vec3(*xis[d])
        if (a, b, c, d) not in cross_prods and v0.plane_norm(v1, v2).angle_to(v3 - v0) < FEPSILON:
            cross_prods.append((a, b, c, d))

    return cross_prods


def nodal_lagrange_type(shape, desc, order):
    """
    Generates the ElemTypeDef object which defines a nodal lagrange element type for the given type geometry,
    description, and order. This relies on CHeart node ordering where xi coordinates are sorted based on component
    values, where X is least significant and Z most, but with the vertices coming first before medial nodes.
    """

    point_search_elem = None  # FIXME: implement point search function
    _, dim, is_simplex = ShapeType[shape]

    basis, xis = lagrange_basis(shape, order)

    num_vertices = xis.shape[0]
    xis = xis.tolist()

    # determine faces and face basis function(s)
    faces = []
    face_norms = []
    vertices = list(range(num_vertices))
    face_type = None
    xi_elem_dirs = []
    edges = []

    if dim == 1:
        edges = [list(range(len(xis)))]  # whole line is an edge
    elif dim == 2:
        faces = [list(range(len(xis)))]
        edges = find_edges(xis, len(vertices), is_simplex)
    elif dim == 3:
        faces, face_norms = find_faces(xis, num_vertices, is_simplex)
        xi_elem_dirs = get_xi_elem_directions(xis)

        # TODO: this assumes all faces the same shape, change if this isn't true anymore (eg. prisms)
        shape_type = ShapeType._Tri if is_simplex else ShapeType._Quad
        face_name = ElemType.get_elem_type_name(shape_type, "NL", order)
        face_type = ElemType[face_name]

    return ElemTypeDef(
        shape, 'NL', desc, order, xis, vertices, faces, edges, face_norms, xi_elem_dirs, basis, point_search_elem,
        face_type
    )


class BasisGenFuncs(Namespace):
    """
    List of basis function types, stores the full name of the basis type and a function to generate an ElemTypeDef
    object containing all the properties of an element type using that basis. The functions must accept a shape name,
    description, and an order number (0=point, 1=linear, 2=quadratic, etc.). The key name is used as the element type
    name suffix, which is constructed as [shape][order][basis], eg. Tet1NL for linear nodal lagrange tetrahedra.

    The nodal lagrange function is thus stored under the key "NL" and contains ("Nodal Lagrange", nodal_lagrange_type).
    The function "nodal_lagrange_type" accepts the arguments (shape, desc, order) and returns a ElemTypeDef object.
    """
    NL = ("Nodal Lagrange", nodal_lagrange_type)


class ElemTypeMeta(NamespaceMeta):
    def __new__(mcs, cls, bases, classdict):
        return super().__new__(mcs, cls, bases, classdict)

    def _generate_elem_type(cls, name):
        """
        Generate an element type based on the type's name. The name is of the form [GEOM][ORDER][BASIS] where [GEOM]
        is a name in GeomType, [ORDER] is a number >=1, and [BASIS] is a name in BasisGenFuncs. For example, cubic
        nodal lagrange hexahedrons have the name Hex3NL.
        """
        nsplit = re.split("([a-zA-Z]+)(\d+)([a-zA-Z0-9]+)", name)

        assert len(nsplit) > 3, 'Bad name: ' + str(nsplit) + ' ' + str(name)

        shape = nsplit[1]
        order = int(nsplit[2])
        basistype = nsplit[3]

        if shape not in ShapeType:
            raise ValueError(f"Shape type '{shape}' not recognized")

        if order < 1:
            raise ValueError(f"Order value '{order}' must be an integer greater than 0")

        if basistype not in BasisGenFuncs:
            raise ValueError(f"Basis Function type '{basistype}' not recognized")

        ordernames = ['Linear', 'Quadratic', 'Cubic', 'Quartic']

        orderstr = ordernames[order - 1] if order <= len(ordernames) else f"Order {order}"

        desc = f"{ShapeType[shape][0]}, {orderstr} {BasisGenFuncs[basistype][0]}"

        basisobj = BasisGenFuncs[basistype][1](shape, desc, order)

        cls.append(name, basisobj)

        faces = basisobj.face_type
        if not is_iterable_notstr(faces):
            faces = [faces]

        for f in faces:
            if f is not None:
                name = cls.get_elem_type_name(f.shape_type, basistype, f.order)
                if name not in cls:
                    cls.append(name, f)

        return basisobj

    def get_elem_type_name(cls, shape_name, basis_name, order):
        """Produces the [GEOM][ORDER][BASIS] element type name from the given arguments."""

        if shape_name not in ShapeType:
            raise ValueError(f"Shape name '{shape_name}' not in ShapeType")
        if basis_name not in BasisGenFuncs:
            raise ValueError(f"Basis name '{basis_name}' not in BasisGenFuncs")
        if not isinstance(order, int) or order < 0:
            raise ValueError(f"Invalid order value {order}")

        if shape_name == ShapeType._Point:
            return cls._Point
        else:
            return f"{shape_name}{order}{basis_name}"

    def get_linear_type(cls, elemtype):
        key = cls.get_elem_type_name(elemtype.shape_type, elemtype.basis_name, 1)
        return cls.__getattr__(key)

    def __getattr__(cls, key):
        if key[0] == "_":
            try:
                cls._generate_elem_type(key[1:])
                return key[1:]
            except ValueError:
                pass

        try:
            return super().__getattr__(key)
        except AttributeError:
            return cls._generate_elem_type(key)


class ElemType(metaclass=ElemTypeMeta):
    """
    Stores the ElemTypeDef objects for requested element types. This initially only contains the trivial definition for
    Point elements, when other element definitions are requested by name these are generated using the function stored
    in BasisGenFuncs associated with the requested basis function type. The resulting ElemTypeDef is then stored in
    this type for later recall.

    For example, Tet1NL will cause the nodal lagrange (NL) basis generator function to be pulled from BasisGenFuncs and
    the values "Tet" and 1 passed as the shape and order values. The resulting object is keyed to Tet1NL internally.
    """
    Point = ElemTypeDef(ShapeType._Point, "NL", "Point", 0, [], [], [], [], [], [], None, None, None)
