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


import itertools
import functools
from typing import Tuple
from textwrap import dedent

import numpy as np

from ..utils import Namespace
from .compile_support import jit

__all__ = ["ShapeType", "lagrange_basis"]


class ShapeType(Namespace):
    """
    Stores the geometry types with their full names, dimensions, and if they are symplex or not
    """
    Point = ("Point", 0, False)
    Line = ("Line", 1, False)
    Tri = ('Triangle', 2, True)
    Quad = ('Quadrilateral', 2, False)
    Tet = ('Tetrahedron', 3, True)
    Hex = ('Hexahedron', 3, False)


def line_1nl(xi0: float, xi1: float, xi2: float) -> Tuple[float, float]:
    """
    Line linear nodal lagrange basis function. Returned values correspond to coefficients for (xi0, xi1, xi2) at
    coordinates (0,0,0) and (1,0,0). Note @jit not applied as it doesn't help for so simple a function.
    """
    return 1 - xi0, xi0


def tri_1nl(xi0: float, xi1: float, xi2: float) -> Tuple[float, float, float]:
    """
    Triangle linear nodal lagrange basis function. Returned values correspond to coefficients for (xi0, xi1, xi2) at
    coordinates (0,0,0), (1,0,0), and (0,1,0). Note @jit not applied as it doesn't help for so simple a function.
    """
    return 1 - xi0 - xi1, xi0, xi1


@jit
def quad_1nl(xi0: float, xi1: float, xi2: float) -> Tuple[float, float, float, float]:
    """
    Quadrilateral linear nodal lagrange basis function. Returned values correspond to coefficients for (xi0, xi1, xi2)
    at coordinates (0,0,0), (1,0,0), (0,1,0), and (1,1,0).
    """
    xi01: float = xi0 * xi1
    return 1 - xi0 - xi1 + xi01, xi0 - xi01, xi1 - xi01, xi01


@jit
def tet_1nl(xi0: float, xi1: float, xi2: float) -> Tuple[float, float, float, float]:
    """
    Tetrahedal linear nodal lagrange basis function. Returned values correspond to coefficients for (xi0, xi1, xi2) at
    coordinates (0,0,0), (1,0,0), (0,1,0), and (0,0,1).
    """
    return 1.0 - xi0 - xi1 - xi2, xi0, xi1, xi2


@jit
def hex_1nl(xi0: float, xi1: float, xi2: float) -> Tuple[float, float, float, float, float, float, float, float]:
    """
    Hexahedal linear nodal lagrange basis function. Returned values correspond to coefficients for (xi0, xi1, xi2) at
    coordinates (0,0,0), (1,0,0), (0,1,0), (1,1,0), (0,0,1), (1,0,1), (0,1,1), and (1,1,1)."""
    xi012: float = xi0 * xi1 * xi2
    xi12: float = xi1 * xi2
    xi01: float = xi0 * xi1
    xi02: float = xi0 * xi2

    return 1.0 - xi0 - xi1 - xi2 + xi01 + xi02 + xi12 - xi012, xi0 - xi01 - xi02 + xi012, xi1 - xi01 - xi12 + xi012, \
           xi01 - xi012, xi2 - xi02 - xi12 + xi012, xi02 - xi012, xi12 - xi012, xi012


def lagrange_beta(order: int, is_simplex: bool, dim: int):
    """
    Calculate the beta matrix for a nodal lagrange basis function defining line, triangle, quad, hex, or tet elements.
    This adheres to CHeart node ordering. See Lee et al., "Multi-Physics Computational Modeling in CHeart", 2016
    """

    def sort_cheart(a, b):
        """Sort the columns of the beta matrix to enforce CHeart node ordering."""
        aorder = all(int(i) in (0, order) for i in a)
        border = all(int(i) in (0, order) for i in b)

        # sort first by order (# of index components used by vertices), this makes vertices come first
        if aorder < border:
            return 1  # note reversed order
        elif aorder > border:
            return -1

        # sort by component
        for i, j in reversed(list(zip(a, b))):  # sort in Z, Y, X order
            if i < j:
                return -1
            elif i > j:
                return 1

        return 0

    # create the beta matrix by listing every `dim'-wide combination of the set [0,`order`]
    vals = list(v for v in itertools.product(range(order + 1), repeat=dim) if not is_simplex or sum(v) <= order)

    if dim > 1:  # 1D and points don't use CHeart node ordering apparently
        vals.sort(key=functools.cmp_to_key(sort_cheart))

    return np.swapaxes(vals, 0, 1)


def lagrange_alpha(beta: np.ndarray, xis: np.ndarray):
    """
    Calculate an alpha matrix for a nodal lagrange basis function by applying the Vandermonde matrix method to a beta
    matrix and node xi coords. This adheres to CHeart node ordering.
    """

    k = len(xis)
    d = len(xis[0])
    a = np.zeros((k, k))

    for i, j in np.ndindex(k, k):
        a[i, j] = np.prod([xis[i][k] ** beta[k][j] for k in range(d)])

    return np.linalg.inv(a).T


def xi_coords(order: int, beta: np.ndarray):
    """Calculate xi coords for nodes from a beta matrix."""
    result = []
    for i in range(beta.shape[1]):
        result.append(tuple(beta[j][i] / order for j in range(beta.shape[0])))

    return np.array(result)


def lagrange_basis_eval(i, xi, alpha, beta):
    """Evaluate the i'th lagrange basis function using the input xi values and matrix definitions."""

    result = 0
    for j in range(len(alpha)):  # for each polynomial
        a = alpha[i][j]
        for k in range(len(xi)):  # for each xi component
            a *= xi[k] ** beta[k][j]

        result += a

    return result


def lagrange_basis_funcs(num_funcs, alpha, beta):
    """
    Create a sequence of lagrange basis functions, each of which accepts xi values and calculates the coefficient for
    its respective node.
    """
    funcs = []
    for i in range(num_funcs):
        funcs.append(lambda xi0, xi1, xi2, *_, **__: lagrange_basis_eval(i, (xi0, xi1, xi2), alpha, beta))

    return tuple(funcs)


def lagrange_basis_eval_str(i, alpha, beta):
    """
    Construct a string representing the i'th lagrange basis function with free variables xi0,xi1,xi2 storing the
    input xi values.
    """

    result = []
    for j in range(alpha.shape[0]):  # for each polynomial
        a = alpha[i][j]
        if a == 0:
            continue

        eq = ''
        is_first = True

        if a != 1:
            eq += str(a)
            is_first = False

        for k in range(beta.shape[0]):  # for each xi component
            b = beta[k][j]
            if b == 0:
                continue

            if not is_first:
                eq += '*'

            is_first = False

            eq += 'xi' + str(k)
            if b != 1:
                eq += '**' + str(b)

        if eq == '':
            eq = '1'

        result.append('(' + eq + ')')

    return '+'.join(result)


def lagrange_basis(shape_type, order, prefix_code=""):
    """
    Creates a function to compute the coefficients for the nodes of a nodal lagrange element of type `shape_type` and
    order `order`. This is done by defining a function to compute the weights as generated Python code which is compiled
    with Numba if available. The `prefix_code` string is prepended to the code block to be compiled. The return value is
    this compiled callable accepting the three xi coordinate values and the matrix of xi coordinates for each node.
    Numba is invoked with caching disabled so the generated function should be kept by the called to avoid recompiling.
    """
    if shape_type not in ShapeType:
        raise ValueError(f"Unknown shape type '{shape_type}'")
    elif shape_type == ShapeType._Line:
        dim = 1
    elif shape_type in (ShapeType._Tri, ShapeType._Quad):
        dim = 2
    elif shape_type in (ShapeType._Tet, ShapeType._Hex):
        dim = 3
    else:
        raise ValueError(f"Lagrange basis function not known shape type '{shape_type}'")

    is_simplex = shape_type in (ShapeType._Tri, ShapeType._Tet)
    beta = lagrange_beta(order, is_simplex, dim)
    xis = xi_coords(order, beta)

    if order == 1:
        premade_funcs = {
            ShapeType._Line: line_1nl,
            ShapeType._Tri: tri_1nl,
            ShapeType._Quad: quad_1nl,
            ShapeType._Tet: tet_1nl,
            ShapeType._Hex: hex_1nl,
        }

        basis_func = premade_funcs[shape_type]
    else:
        basis_name = f"compute_{shape_type}{order}nl"
        alpha = lagrange_alpha(beta, xis)
        k = xis.shape[0]

        exprs = '(' + ','.join(lagrange_basis_eval_str(i, alpha, beta) for i in range(k)) + ')'

        basis_func = f"""
            {prefix_code}
            @jit(cache=False)  # cannot cache outside of a named module to store the result in
            def {basis_name}(xi0, xi1, xi2):
                '''Computes the Nodal Lagrange coefficients for the nodes of an {order} {shape_type} element.'''
                return {exprs}
        """

        exec(dedent(basis_func))  # compile the generated function with Numba if installed
        basis_func = locals()[basis_name]

    # if xis.shape[1] == 3:
    #     xis = xis[:, (1, 0, 2)]  # swap X and Y values

    return basis_func, xis
