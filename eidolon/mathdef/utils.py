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

from math import asin, atan2, sqrt, pi

from .compile_support import njit

FEPSILON: float = 1e-10


@njit
def len3(x: float, y: float, z: float) -> float:
    return sqrt(x ** 2 + y ** 2 + z ** 2)


@njit
def lensq3(x: float, y: float, z: float) -> float:
    return x ** 2 + y ** 2 + z ** 2


@njit
def fequals_eps(v1: float, v2: float) -> bool:
    return abs(v1 - v2) <= FEPSILON


@njit
def finv(v: float) -> float:
    return 1 / v if v != 0.0 else 0.0


@njit
def fsign(v: float) -> float:
    return 1.0 if v >= 0.0 else -1.0


@njit
def fclamp(v: float, vmin: float, vmax: float) -> float:
    if v > vmax:
        return vmax
    elif v < vmin:
        return vmin
    return v


@njit
def rad_circular_convert(rad: float) -> float:
    """Converts the given rad angle value to the equivalent angle on the interval [-pi,pi]."""
    if rad > pi:
        rad -= pi * 2 * rad // (pi * 2)
    elif rad < -pi:
        rad += pi * 2 * abs(rad) // (pi * 2)

    return rad


@njit
def rad_clamp(rad: float) -> float:
    """Clamps the given value between pi*0.5 and pi*-0.5."""
    return fclamp(rad, -pi / 2, pi / 2)


@njit
def rotator_yaw(x: float, y: float, z: float, w: float) -> float:
    test: float = x * y + z * w
    if test > (0.5 - FEPSILON):
        return pi * 0.5

    if test < (-0.5 + FEPSILON):
        return pi * -0.5

    return asin(2 * test)


@njit
def rotator_pitch(x: float, y: float, z: float, w: float) -> float:
    test: float = x * y + z * w
    if test > (0.5 - FEPSILON):
        return 0

    if test < (-0.5 + FEPSILON):
        return 0

    y1: float = 2 * x * w - 2 * y * z
    x1: float = 1 - 2 * x ** 2 - 2 * z ** 2
    return atan2(y1, x1)


@njit
def rotator_roll(x: float, y: float, z: float, w: float) -> float:
    test: float = x * y + z * w
    if test > (0.5 - FEPSILON):
        return 2 * atan2(x, w)

    if test < (-0.5 + FEPSILON):
        return -2 * atan2(x, w)

    y1: float = 2 * y * w - 2 * x * z
    x1: float = 1 - 2 * y ** 2 - 2 * z ** 2
    return atan2(y1, x1)
