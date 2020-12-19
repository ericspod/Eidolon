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

import itertools
import functools
from typing import Tuple

import numpy as np

from .compile_support import jit


def tri_1NL(xi0: float, xi1: float, xi2: float) -> Tuple[float, float, float]:
    """
    Triangle linear nodal lagrange basis function. Returned values correspond to coefficients for (xi0, xi1, xi2) at
    coordinates (0,0,0), (1,0,0), and (0,1,0). Note @jit not applied as it doesn't help for so simple a function.
    """
    return 1 - xi0 - xi1, xi0, xi1


@jit
def quad_1NL(xi0: float, xi1: float, xi2: float) -> Tuple[float, float, float, float]:
    """
    Quadrilateral linear nodal lagrange basis function. Returned values correspond to coefficients for (xi0, xi1, xi2)
    at coordinates (0,0,0), (1,0,0), (0,1,0), and (1,1,0).
    """
    xi01: float = xi0 * xi1
    return 1 - xi0 - xi1 + xi01, xi0 - xi01, xi1 - xi01, xi01


@jit
def tet_1NL(xi0: float, xi1: float, xi2: float) -> Tuple[float, float, float, float]:
    """
    Tetrahedal linear nodal lagrange basis function. Returned values correspond to coefficients for (xi0, xi1, xi2) at
    coordinates (0,0,0), (1,0,0), (0,1,0), and (0,0,1).
    """
    return 1.0 - xi0 - xi1 - xi2, xi0, xi1, xi2


@jit
def hex_1NL(xi0: float, xi1: float, xi2: float) -> Tuple[float, float, float, float, float, float, float, float]:
    """
    Hexahedal linear nodal lagrange basis function. Returned values correspond to coefficients for (xi0, xi1, xi2) at
    coordinates (0,0,0), (1,0,0), (0,1,0), (1,1,0), (0,0,1), (1,0,1), (0,1,1), and (1,1,1)."""
    xi012: float = xi0 * xi1 * xi2
    xi12: float = xi1 * xi2
    xi01: float = xi0 * xi1
    xi02: float = xi0 * xi2

    return 1.0 - xi0 - xi1 - xi2 + xi01 + xi02 + xi12 - xi012, xi0 - xi01 - xi02 + xi012, xi1 - xi01 - xi12 + xi012, \
           xi01 - xi012, xi2 - xi02 - xi12 + xi012, xi02 - xi012, xi12 - xi012, xi012


@jit
def tri_2nl(xi0: float, xi1: float, xi2: float) -> Tuple[float, float, float, float, float, float]:
    return (2.0 * xi0 ** 2 + 4.0 * xi0 * xi1 - 3.0 * xi0 + 2.0 * xi1 ** 2 - 3.0 * xi1 + 1, 2.0 * xi0 ** 2 - 1.0 * xi0,
            2.0 * xi1 ** 2 - 1.0 * xi1, -4.0 * xi0 ** 2 - 4.0 * xi0 * xi1 + 4.0 * xi0,
            -4.0 * xi0 * xi1 - 4.0 * xi1 ** 2 + 4.0 * xi1, 4.0 * xi0 * xi1)


@jit
def quad_2nl(xi0: float, xi1: float, xi2: float) -> Tuple[float, float, float, float, float, float, float, float, float]:
    return (
    4.0 * xi0 ** 2 * xi1 ** 2 - 6.0 * xi0 ** 2 * xi1 + 2.0 * xi0 ** 2 - 6.0 * xi0 * xi1 ** 2 + 9.0 * xi0 * xi1 - 3.0 * xi0 + 2.0 * xi1 ** 2 - 3.0 * xi1 + 1,
    4.0 * xi0 ** 2 * xi1 ** 2 - 6.0 * xi0 ** 2 * xi1 + 2.0 * xi0 ** 2 - 2.0 * xi0 * xi1 ** 2 + 3.0 * xi0 * xi1 - 1.0 * xi0,
    4.0 * xi0 ** 2 * xi1 ** 2 - 2.0 * xi0 ** 2 * xi1 - 6.0 * xi0 * xi1 ** 2 + 3.0 * xi0 * xi1 + 2.0 * xi1 ** 2 - 1.0 * xi1,
    4.0 * xi0 ** 2 * xi1 ** 2 - 2.0 * xi0 ** 2 * xi1 - 2.0 * xi0 * xi1 ** 2 + xi0 * xi1,
    -8.0 * xi0 ** 2 * xi1 ** 2 + 12.0 * xi0 ** 2 * xi1 - 4.0 * xi0 ** 2 + 8.0 * xi0 * xi1 ** 2 - 12.0 * xi0 * xi1 + 4.0 * xi0,
    -8.0 * xi0 ** 2 * xi1 ** 2 + 8.0 * xi0 ** 2 * xi1 + 12.0 * xi0 * xi1 ** 2 - 12.0 * xi0 * xi1 - 4.0 * xi1 ** 2 + 4.0 * xi1,
    16.0 * xi0 ** 2 * xi1 ** 2 - 16.0 * xi0 ** 2 * xi1 - 16.0 * xi0 * xi1 ** 2 + 16.0 * xi0 * xi1,
    -8.0 * xi0 ** 2 * xi1 ** 2 + 8.0 * xi0 ** 2 * xi1 + 4.0 * xi0 * xi1 ** 2 - 4.0 * xi0 * xi1,
    -8.0 * xi0 ** 2 * xi1 ** 2 + 4.0 * xi0 ** 2 * xi1 + 8.0 * xi0 * xi1 ** 2 - 4.0 * xi0 * xi1)


@jit
def tet_2nl(xi0: float, xi1: float, xi2: float) -> Tuple[float, float, float, float, float, float, float, float, float, float]:
    return (
    2.0 * xi0 ** 2 + 4.0 * xi0 * xi1 + 4.0 * xi0 * xi2 - 3.0 * xi0 + 2.0 * xi1 ** 2 + 4.0 * xi1 * xi2 - 3.0 * xi1 + 2.0 * xi2 ** 2 - 3.0 * xi2 + 1,
    2.0 * xi1 ** 2 - 1.0 * xi1, 2.0 * xi0 ** 2 - 1.0 * xi0, 2.0 * xi2 ** 2 - 1.0 * xi2,
    -4.0 * xi0 * xi1 - 4.0 * xi1 ** 2 - 4.0 * xi1 * xi2 + 4.0 * xi1,
    -4.0 * xi0 ** 2 - 4.0 * xi0 * xi1 - 4.0 * xi0 * xi2 + 4.0 * xi0, 4.0 * xi0 * xi1,
    -4.0 * xi0 * xi2 - 4.0 * xi1 * xi2 - 4.0 * xi2 ** 2 + 4.0 * xi2, 4.0 * xi1 * xi2, 4.0 * xi0 * xi2)


@njit
def hex_2nl(xi0: float, xi1: float, xi2: float) -> Tuple[float, ...]:
    return (
    8.0 * xi0 ** 2 * xi1 ** 2 * xi2 ** 2 - 12.0 * xi0 ** 2 * xi1 ** 2 * xi2 + 4.0 * xi0 ** 2 * xi1 ** 2 - 12.0 * xi0 ** 2 * xi1 * xi2 ** 2 + 18.0 * xi0 ** 2 * xi1 * xi2 - 6.0 * xi0 ** 2 * xi1 + 4.0 * xi0 ** 2 * xi2 ** 2 - 6.0 * xi0 ** 2 * xi2 + 2.0 * xi0 ** 2 - 12.0 * xi0 * xi1 ** 2 * xi2 ** 2 + 18.0 * xi0 * xi1 ** 2 * xi2 - 6.0 * xi0 * xi1 ** 2 + 18.0 * xi0 * xi1 * xi2 ** 2 - 27.0 * xi0 * xi1 * xi2 + 9.0 * xi0 * xi1 - 6.0 * xi0 * xi2 ** 2 + 9.0 * xi0 * xi2 - 3.0 * xi0 + 4.0 * xi1 ** 2 * xi2 ** 2 - 6.0 * xi1 ** 2 * xi2 + 2.0 * xi1 ** 2 - 6.0 * xi1 * xi2 ** 2 + 9.0 * xi1 * xi2 - 3.0 * xi1 + 2.0 * xi2 ** 2 - 3.0 * xi2 + 1,
    8.0 * xi0 ** 2 * xi1 ** 2 * xi2 ** 2 - 12.0 * xi0 ** 2 * xi1 ** 2 * xi2 + 4.0 * xi0 ** 2 * xi1 ** 2 - 4.0 * xi0 ** 2 * xi1 * xi2 ** 2 + 6.0 * xi0 ** 2 * xi1 * xi2 - 2.0 * xi0 ** 2 * xi1 - 12.0 * xi0 * xi1 ** 2 * xi2 ** 2 + 18.0 * xi0 * xi1 ** 2 * xi2 - 6.0 * xi0 * xi1 ** 2 + 6.0 * xi0 * xi1 * xi2 ** 2 - 9.0 * xi0 * xi1 * xi2 + 3.0 * xi0 * xi1 + 4.0 * xi1 ** 2 * xi2 ** 2 - 6.0 * xi1 ** 2 * xi2 + 2.0 * xi1 ** 2 - 2.0 * xi1 * xi2 ** 2 + 3.0 * xi1 * xi2 - 1.0 * xi1,
    8.0 * xi0 ** 2 * xi1 ** 2 * xi2 ** 2 - 12.0 * xi0 ** 2 * xi1 ** 2 * xi2 + 4.0 * xi0 ** 2 * xi1 ** 2 - 12.0 * xi0 ** 2 * xi1 * xi2 ** 2 + 18.0 * xi0 ** 2 * xi1 * xi2 - 6.0 * xi0 ** 2 * xi1 + 4.0 * xi0 ** 2 * xi2 ** 2 - 6.0 * xi0 ** 2 * xi2 + 2.0 * xi0 ** 2 - 4.0 * xi0 * xi1 ** 2 * xi2 ** 2 + 6.0 * xi0 * xi1 ** 2 * xi2 - 2.0 * xi0 * xi1 ** 2 + 6.0 * xi0 * xi1 * xi2 ** 2 - 9.0 * xi0 * xi1 * xi2 + 3.0 * xi0 * xi1 - 2.0 * xi0 * xi2 ** 2 + 3.0 * xi0 * xi2 - 1.0 * xi0,
    8.0 * xi0 ** 2 * xi1 ** 2 * xi2 ** 2 - 12.0 * xi0 ** 2 * xi1 ** 2 * xi2 + 4.0 * xi0 ** 2 * xi1 ** 2 - 4.0 * xi0 ** 2 * xi1 * xi2 ** 2 + 6.0 * xi0 ** 2 * xi1 * xi2 - 2.0 * xi0 ** 2 * xi1 - 4.0 * xi0 * xi1 ** 2 * xi2 ** 2 + 6.0 * xi0 * xi1 ** 2 * xi2 - 2.0 * xi0 * xi1 ** 2 + 2.0 * xi0 * xi1 * xi2 ** 2 - 3.0 * xi0 * xi1 * xi2 + xi0 * xi1,
    8.0 * xi0 ** 2 * xi1 ** 2 * xi2 ** 2 - 4.0 * xi0 ** 2 * xi1 ** 2 * xi2 - 12.0 * xi0 ** 2 * xi1 * xi2 ** 2 + 6.0 * xi0 ** 2 * xi1 * xi2 + 4.0 * xi0 ** 2 * xi2 ** 2 - 2.0 * xi0 ** 2 * xi2 - 12.0 * xi0 * xi1 ** 2 * xi2 ** 2 + 6.0 * xi0 * xi1 ** 2 * xi2 + 18.0 * xi0 * xi1 * xi2 ** 2 - 9.0 * xi0 * xi1 * xi2 - 6.0 * xi0 * xi2 ** 2 + 3.0 * xi0 * xi2 + 4.0 * xi1 ** 2 * xi2 ** 2 - 2.0 * xi1 ** 2 * xi2 - 6.0 * xi1 * xi2 ** 2 + 3.0 * xi1 * xi2 + 2.0 * xi2 ** 2 - 1.0 * xi2,
    8.0 * xi0 ** 2 * xi1 ** 2 * xi2 ** 2 - 4.0 * xi0 ** 2 * xi1 ** 2 * xi2 - 4.0 * xi0 ** 2 * xi1 * xi2 ** 2 + 2.0 * xi0 ** 2 * xi1 * xi2 - 12.0 * xi0 * xi1 ** 2 * xi2 ** 2 + 6.0 * xi0 * xi1 ** 2 * xi2 + 6.0 * xi0 * xi1 * xi2 ** 2 - 3.0 * xi0 * xi1 * xi2 + 4.0 * xi1 ** 2 * xi2 ** 2 - 2.0 * xi1 ** 2 * xi2 - 2.0 * xi1 * xi2 ** 2 + xi1 * xi2,
    8.0 * xi0 ** 2 * xi1 ** 2 * xi2 ** 2 - 4.0 * xi0 ** 2 * xi1 ** 2 * xi2 - 12.0 * xi0 ** 2 * xi1 * xi2 ** 2 + 6.0 * xi0 ** 2 * xi1 * xi2 + 4.0 * xi0 ** 2 * xi2 ** 2 - 2.0 * xi0 ** 2 * xi2 - 4.0 * xi0 * xi1 ** 2 * xi2 ** 2 + 2.0 * xi0 * xi1 ** 2 * xi2 + 6.0 * xi0 * xi1 * xi2 ** 2 - 3.0 * xi0 * xi1 * xi2 - 2.0 * xi0 * xi2 ** 2 + xi0 * xi2,
    8.0 * xi0 ** 2 * xi1 ** 2 * xi2 ** 2 - 4.0 * xi0 ** 2 * xi1 ** 2 * xi2 - 4.0 * xi0 ** 2 * xi1 * xi2 ** 2 + 2.0 * xi0 ** 2 * xi1 * xi2 - 4.0 * xi0 * xi1 ** 2 * xi2 ** 2 + 2.0 * xi0 * xi1 ** 2 * xi2 + 2.0 * xi0 * xi1 * xi2 ** 2 - 1.0 * xi0 * xi1 * xi2,
    -16.0 * xi0 ** 2 * xi1 ** 2 * xi2 ** 2 + 24.0 * xi0 ** 2 * xi1 ** 2 * xi2 - 8.0 * xi0 ** 2 * xi1 ** 2 + 16.0 * xi0 ** 2 * xi1 * xi2 ** 2 - 24.0 * xi0 ** 2 * xi1 * xi2 + 8.0 * xi0 ** 2 * xi1 + 24.0 * xi0 * xi1 ** 2 * xi2 ** 2 - 36.0 * xi0 * xi1 ** 2 * xi2 + 12.0 * xi0 * xi1 ** 2 - 24.0 * xi0 * xi1 * xi2 ** 2 + 36.0 * xi0 * xi1 * xi2 - 12.0 * xi0 * xi1 - 8.0 * xi1 ** 2 * xi2 ** 2 + 12.0 * xi1 ** 2 * xi2 - 4.0 * xi1 ** 2 + 8.0 * xi1 * xi2 ** 2 - 12.0 * xi1 * xi2 + 4.0 * xi1,
    -16.0 * xi0 ** 2 * xi1 ** 2 * xi2 ** 2 + 24.0 * xi0 ** 2 * xi1 ** 2 * xi2 - 8.0 * xi0 ** 2 * xi1 ** 2 + 24.0 * xi0 ** 2 * xi1 * xi2 ** 2 - 36.0 * xi0 ** 2 * xi1 * xi2 + 12.0 * xi0 ** 2 * xi1 - 8.0 * xi0 ** 2 * xi2 ** 2 + 12.0 * xi0 ** 2 * xi2 - 4.0 * xi0 ** 2 + 16.0 * xi0 * xi1 ** 2 * xi2 ** 2 - 24.0 * xi0 * xi1 ** 2 * xi2 + 8.0 * xi0 * xi1 ** 2 - 24.0 * xi0 * xi1 * xi2 ** 2 + 36.0 * xi0 * xi1 * xi2 - 12.0 * xi0 * xi1 + 8.0 * xi0 * xi2 ** 2 - 12.0 * xi0 * xi2 + 4.0 * xi0,
    32.0 * xi0 ** 2 * xi1 ** 2 * xi2 ** 2 - 48.0 * xi0 ** 2 * xi1 ** 2 * xi2 + 16.0 * xi0 ** 2 * xi1 ** 2 - 32.0 * xi0 ** 2 * xi1 * xi2 ** 2 + 48.0 * xi0 ** 2 * xi1 * xi2 - 16.0 * xi0 ** 2 * xi1 - 32.0 * xi0 * xi1 ** 2 * xi2 ** 2 + 48.0 * xi0 * xi1 ** 2 * xi2 - 16.0 * xi0 * xi1 ** 2 + 32.0 * xi0 * xi1 * xi2 ** 2 - 48.0 * xi0 * xi1 * xi2 + 16.0 * xi0 * xi1,
    -16.0 * xi0 ** 2 * xi1 ** 2 * xi2 ** 2 + 24.0 * xi0 ** 2 * xi1 ** 2 * xi2 - 8.0 * xi0 ** 2 * xi1 ** 2 + 8.0 * xi0 ** 2 * xi1 * xi2 ** 2 - 12.0 * xi0 ** 2 * xi1 * xi2 + 4.0 * xi0 ** 2 * xi1 + 16.0 * xi0 * xi1 ** 2 * xi2 ** 2 - 24.0 * xi0 * xi1 ** 2 * xi2 + 8.0 * xi0 * xi1 ** 2 - 8.0 * xi0 * xi1 * xi2 ** 2 + 12.0 * xi0 * xi1 * xi2 - 4.0 * xi0 * xi1,
    -16.0 * xi0 ** 2 * xi1 ** 2 * xi2 ** 2 + 24.0 * xi0 ** 2 * xi1 ** 2 * xi2 - 8.0 * xi0 ** 2 * xi1 ** 2 + 16.0 * xi0 ** 2 * xi1 * xi2 ** 2 - 24.0 * xi0 ** 2 * xi1 * xi2 + 8.0 * xi0 ** 2 * xi1 + 8.0 * xi0 * xi1 ** 2 * xi2 ** 2 - 12.0 * xi0 * xi1 ** 2 * xi2 + 4.0 * xi0 * xi1 ** 2 - 8.0 * xi0 * xi1 * xi2 ** 2 + 12.0 * xi0 * xi1 * xi2 - 4.0 * xi0 * xi1,
    -16.0 * xi0 ** 2 * xi1 ** 2 * xi2 ** 2 + 16.0 * xi0 ** 2 * xi1 ** 2 * xi2 + 24.0 * xi0 ** 2 * xi1 * xi2 ** 2 - 24.0 * xi0 ** 2 * xi1 * xi2 - 8.0 * xi0 ** 2 * xi2 ** 2 + 8.0 * xi0 ** 2 * xi2 + 24.0 * xi0 * xi1 ** 2 * xi2 ** 2 - 24.0 * xi0 * xi1 ** 2 * xi2 - 36.0 * xi0 * xi1 * xi2 ** 2 + 36.0 * xi0 * xi1 * xi2 + 12.0 * xi0 * xi2 ** 2 - 12.0 * xi0 * xi2 - 8.0 * xi1 ** 2 * xi2 ** 2 + 8.0 * xi1 ** 2 * xi2 + 12.0 * xi1 * xi2 ** 2 - 12.0 * xi1 * xi2 - 4.0 * xi2 ** 2 + 4.0 * xi2,
    32.0 * xi0 ** 2 * xi1 ** 2 * xi2 ** 2 - 32.0 * xi0 ** 2 * xi1 ** 2 * xi2 - 32.0 * xi0 ** 2 * xi1 * xi2 ** 2 + 32.0 * xi0 ** 2 * xi1 * xi2 - 48.0 * xi0 * xi1 ** 2 * xi2 ** 2 + 48.0 * xi0 * xi1 ** 2 * xi2 + 48.0 * xi0 * xi1 * xi2 ** 2 - 48.0 * xi0 * xi1 * xi2 + 16.0 * xi1 ** 2 * xi2 ** 2 - 16.0 * xi1 ** 2 * xi2 - 16.0 * xi1 * xi2 ** 2 + 16.0 * xi1 * xi2,
    -16.0 * xi0 ** 2 * xi1 ** 2 * xi2 ** 2 + 16.0 * xi0 ** 2 * xi1 ** 2 * xi2 + 8.0 * xi0 ** 2 * xi1 * xi2 ** 2 - 8.0 * xi0 ** 2 * xi1 * xi2 + 24.0 * xi0 * xi1 ** 2 * xi2 ** 2 - 24.0 * xi0 * xi1 ** 2 * xi2 - 12.0 * xi0 * xi1 * xi2 ** 2 + 12.0 * xi0 * xi1 * xi2 - 8.0 * xi1 ** 2 * xi2 ** 2 + 8.0 * xi1 ** 2 * xi2 + 4.0 * xi1 * xi2 ** 2 - 4.0 * xi1 * xi2,
    32.0 * xi0 ** 2 * xi1 ** 2 * xi2 ** 2 - 32.0 * xi0 ** 2 * xi1 ** 2 * xi2 - 48.0 * xi0 ** 2 * xi1 * xi2 ** 2 + 48.0 * xi0 ** 2 * xi1 * xi2 + 16.0 * xi0 ** 2 * xi2 ** 2 - 16.0 * xi0 ** 2 * xi2 - 32.0 * xi0 * xi1 ** 2 * xi2 ** 2 + 32.0 * xi0 * xi1 ** 2 * xi2 + 48.0 * xi0 * xi1 * xi2 ** 2 - 48.0 * xi0 * xi1 * xi2 - 16.0 * xi0 * xi2 ** 2 + 16.0 * xi0 * xi2,
    -64.0 * xi0 ** 2 * xi1 ** 2 * xi2 ** 2 + 64.0 * xi0 ** 2 * xi1 ** 2 * xi2 + 64.0 * xi0 ** 2 * xi1 * xi2 ** 2 - 64.0 * xi0 ** 2 * xi1 * xi2 + 64.0 * xi0 * xi1 ** 2 * xi2 ** 2 - 64.0 * xi0 * xi1 ** 2 * xi2 - 64.0 * xi0 * xi1 * xi2 ** 2 + 64.0 * xi0 * xi1 * xi2,
    32.0 * xi0 ** 2 * xi1 ** 2 * xi2 ** 2 - 32.0 * xi0 ** 2 * xi1 ** 2 * xi2 - 16.0 * xi0 ** 2 * xi1 * xi2 ** 2 + 16.0 * xi0 ** 2 * xi1 * xi2 - 32.0 * xi0 * xi1 ** 2 * xi2 ** 2 + 32.0 * xi0 * xi1 ** 2 * xi2 + 16.0 * xi0 * xi1 * xi2 ** 2 - 16.0 * xi0 * xi1 * xi2,
    -16.0 * xi0 ** 2 * xi1 ** 2 * xi2 ** 2 + 16.0 * xi0 ** 2 * xi1 ** 2 * xi2 + 24.0 * xi0 ** 2 * xi1 * xi2 ** 2 - 24.0 * xi0 ** 2 * xi1 * xi2 - 8.0 * xi0 ** 2 * xi2 ** 2 + 8.0 * xi0 ** 2 * xi2 + 8.0 * xi0 * xi1 ** 2 * xi2 ** 2 - 8.0 * xi0 * xi1 ** 2 * xi2 - 12.0 * xi0 * xi1 * xi2 ** 2 + 12.0 * xi0 * xi1 * xi2 + 4.0 * xi0 * xi2 ** 2 - 4.0 * xi0 * xi2,
    32.0 * xi0 ** 2 * xi1 ** 2 * xi2 ** 2 - 32.0 * xi0 ** 2 * xi1 ** 2 * xi2 - 32.0 * xi0 ** 2 * xi1 * xi2 ** 2 + 32.0 * xi0 ** 2 * xi1 * xi2 - 16.0 * xi0 * xi1 ** 2 * xi2 ** 2 + 16.0 * xi0 * xi1 ** 2 * xi2 + 16.0 * xi0 * xi1 * xi2 ** 2 - 16.0 * xi0 * xi1 * xi2,
    -16.0 * xi0 ** 2 * xi1 ** 2 * xi2 ** 2 + 16.0 * xi0 ** 2 * xi1 ** 2 * xi2 + 8.0 * xi0 ** 2 * xi1 * xi2 ** 2 - 8.0 * xi0 ** 2 * xi1 * xi2 + 8.0 * xi0 * xi1 ** 2 * xi2 ** 2 - 8.0 * xi0 * xi1 ** 2 * xi2 - 4.0 * xi0 * xi1 * xi2 ** 2 + 4.0 * xi0 * xi1 * xi2,
    -16.0 * xi0 ** 2 * xi1 ** 2 * xi2 ** 2 + 8.0 * xi0 ** 2 * xi1 ** 2 * xi2 + 16.0 * xi0 ** 2 * xi1 * xi2 ** 2 - 8.0 * xi0 ** 2 * xi1 * xi2 + 24.0 * xi0 * xi1 ** 2 * xi2 ** 2 - 12.0 * xi0 * xi1 ** 2 * xi2 - 24.0 * xi0 * xi1 * xi2 ** 2 + 12.0 * xi0 * xi1 * xi2 - 8.0 * xi1 ** 2 * xi2 ** 2 + 4.0 * xi1 ** 2 * xi2 + 8.0 * xi1 * xi2 ** 2 - 4.0 * xi1 * xi2,
    -16.0 * xi0 ** 2 * xi1 ** 2 * xi2 ** 2 + 8.0 * xi0 ** 2 * xi1 ** 2 * xi2 + 24.0 * xi0 ** 2 * xi1 * xi2 ** 2 - 12.0 * xi0 ** 2 * xi1 * xi2 - 8.0 * xi0 ** 2 * xi2 ** 2 + 4.0 * xi0 ** 2 * xi2 + 16.0 * xi0 * xi1 ** 2 * xi2 ** 2 - 8.0 * xi0 * xi1 ** 2 * xi2 - 24.0 * xi0 * xi1 * xi2 ** 2 + 12.0 * xi0 * xi1 * xi2 + 8.0 * xi0 * xi2 ** 2 - 4.0 * xi0 * xi2,
    32.0 * xi0 ** 2 * xi1 ** 2 * xi2 ** 2 - 16.0 * xi0 ** 2 * xi1 ** 2 * xi2 - 32.0 * xi0 ** 2 * xi1 * xi2 ** 2 + 16.0 * xi0 ** 2 * xi1 * xi2 - 32.0 * xi0 * xi1 ** 2 * xi2 ** 2 + 16.0 * xi0 * xi1 ** 2 * xi2 + 32.0 * xi0 * xi1 * xi2 ** 2 - 16.0 * xi0 * xi1 * xi2,
    -16.0 * xi0 ** 2 * xi1 ** 2 * xi2 ** 2 + 8.0 * xi0 ** 2 * xi1 ** 2 * xi2 + 8.0 * xi0 ** 2 * xi1 * xi2 ** 2 - 4.0 * xi0 ** 2 * xi1 * xi2 + 16.0 * xi0 * xi1 ** 2 * xi2 ** 2 - 8.0 * xi0 * xi1 ** 2 * xi2 - 8.0 * xi0 * xi1 * xi2 ** 2 + 4.0 * xi0 * xi1 * xi2,
    -16.0 * xi0 ** 2 * xi1 ** 2 * xi2 ** 2 + 8.0 * xi0 ** 2 * xi1 ** 2 * xi2 + 16.0 * xi0 ** 2 * xi1 * xi2 ** 2 - 8.0 * xi0 ** 2 * xi1 * xi2 + 8.0 * xi0 * xi1 ** 2 * xi2 ** 2 - 4.0 * xi0 * xi1 ** 2 * xi2 - 8.0 * xi0 * xi1 * xi2 ** 2 + 4.0 * xi0 * xi1 * xi2)




def lagrange_beta(order, is_simplex, dim):
    """
    Calculate the beta matrix for a nodal lagrange basis function defining line, triangle, quad, hex, or tet elements.
    This adheres to CHeart node ordering. See Lee et al., "Multi-Physics Computational Modeling in CHeart", 2016
    """

    def sort_cheart(a, b):
        """Sort the columns of the beta matrix to enforce CHeart node ordering."""
        aorder = all(i == order or i == 0 for i in a)
        border = all(i == order or i == 0 for i in b)

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

        return 0

    # create the beta matrix by listing every `dim'-wide combination of the set [0,`order`]
    vals = list(v for v in itertools.product(range(order + 1), repeat=dim) if not is_simplex or sum(v) <= order)

    if dim > 1:  # 1D and points don't use CHeart node ordering apparently
        vals.sort(key=functools.cmp_to_key(sort_cheart))

    return np.swapaxes(vals, 0, 1)


def lagrange_alpha(beta, xi_coords):
    """
    Calculate an alpha matrix for a nodal lagrange basis function by applying the Vandermonde matrix method to a beta
    matrix and node xi coords. This adheres to CHeart node ordering.
    """

    k = len(xi_coords)
    d = len(xi_coords[0])
    a = np.zeros((k, k))

    for i, j in np.ndindex(k, k):
        a[i, j] = np.prod([xi_coords[i][k] ** beta[k][j] for k in range(d)])

    return np.linalg.inv(a).T


def xi_coords(order, beta):
    """Calculate xi coords for nodes from a beta matrix."""
    result = []
    for i in range(beta.shape[1]):
        result.append(tuple(beta[j][i] / order for j in range(beta.shape[0])))

    return np.array(result)


def lagrange_basis_eval(i, K, xi, alpha, beta):
    """Evaluate the i'th lagrange basis function using the input xi values and matrix definitions."""

    M = len(alpha[0])  # # of polynomials
    d = len(xi)  # spatial dimension

    result = 0
    for j in range(M):  # for each polynomial
        a = alpha[i][j]
        for k in range(d):  # for each xi component
            a *= xi[k] ** beta[k][j]

        result += a

    return result


def lagrange_basis_eval_str(i, K, d, alpha, beta):
    """
    Construct a string representing the i'th lagrange basis function with free variables xi0,xi1,xi2 storing the
    input xi values.
    """
    M = len(alpha[0])  # # of polynomials

    result = []
    for j in range(M):  # for each polynomial
        a = alpha[i][j]
        if a == 0:
            continue

        eq = ''
        is_first = True

        if a != 1:
            eq += str(a)
            is_first = False

        for k in range(d):  # for each xi component
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


def lagrange_basis_funcs(num_funcs, alpha, beta):
    """
    Create a sequence of lagrange basis functions, each of which accepts xi values and calculates the coefficient for
    its respective node.
    """
    funcs = []
    for i in range(num_funcs):
        funcs.append(lambda xi0, xi1, xi2, *_, **__: lagrange_basis_eval(i, num_funcs, (xi0, xi1, xi2), alpha, beta))

    return tuple(funcs)


def lagrange_basis(num_funcs, dim, alpha, beta):
    """Create a lagrange basis function which accepts xi values and calculates coefficients for each node."""

    s = '(' + ','.join(lagrange_basis_eval_str(i, num_funcs, dim, alpha, beta) for i in range(num_funcs)) + ')'
    c = compile(s, '<<basis>>', 'eval')

    return lambda xi0, xi1, xi2, *args, **kwargs: eval(c)


def lagrange_basis_exprs(order, is_simplex, dim):
    beta = lagrange_beta(order, is_simplex, dim)
    xis = xi_coords(order, beta)
    alpha = lagrange_alpha(beta, xis)
    k = xis.shape[0]
    return '(' + ','.join(lagrange_basis_eval_str(i, k, dim, alpha, beta) for i in range(k)) + ')'

