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

from math import asin, acos, atan2, sqrt, pi
from typing import Tuple

from .compile_support import jit

__all__ = [
    "FEPSILON", "HALFPI", "TAU", "len3", "lensq3", "fequals_eps", "finv", "fsign", "fclamp", "rad_clamp",
    "rad_circular_convert", "rotator_yaw", "rotator_roll", "rotator_pitch", "frange", "lerp", "lerp_xi",
    "angle_between", "plane_norm"
]

FEPSILON: float = 1e-10
HALFPI: float = pi / 2
TAU: float = pi * 2


def epsilon_zero(val):
    """Return 0.0 if `val' is within 'epsilon' of 0.0, otherwise return 'val' converted to a float value."""
    val = float(val)
    return 0.0 if abs(val) < FEPSILON else val


@jit
def len3(x: float, y: float, z: float) -> float:
    return sqrt(x ** 2 + y ** 2 + z ** 2)


@jit
def lensq3(x: float, y: float, z: float) -> float:
    return x ** 2 + y ** 2 + z ** 2


@jit
def fequals_eps(v1: float, v2: float) -> bool:
    return abs(v1 - v2) <= FEPSILON


@jit
def finv(v: float) -> float:
    return 1 / v if v != 0.0 else 0.0


@jit
def fsign(v: float) -> float:
    return 1.0 if v >= 0.0 else -1.0


@jit
def fclamp(v: float, vmin: float, vmax: float) -> float:
    if v > vmax:
        return vmax
    elif v < vmin:
        return vmin
    return v


@jit
def angle_between(x0, y0, z0, x1, y1, z1):
    """Returns the angle between vectors (x0, y0, z0) and (x1, y1, z1)."""
    length = sqrt(lensq3(x0, y0, z0) * lensq3(x1, y1, z1))

    if length < FEPSILON:
        return 0.0

    vl = (x0 * x1 + y0 * y1 + z0 * z1) / length

    if vl >= (1.0 - FEPSILON):
        return 0.0

    if vl <= (FEPSILON - 1.0):
        return pi

    return acos(vl)


@jit
def plane_norm(x0: float, y0: float, z0: float, x1: float, y1: float, z1: float, x2: float, y2: float, z2: float) -> \
        Tuple[float, float, float]:
    dx1 = x1 - x0
    dy1 = y1 - y0
    dz1 = z1 - z0
    dx2 = x2 - x0
    dy2 = y2 - y0
    dz2 = z2 - z0

    cx = dy1 * dz2 - dz1 * dy2
    cy = dz1 * dx2 - dx1 * dz2
    cz = dx1 * dy2 - dy1 * dx2

    ln = len3(cx, cy, cz)

    if ln == 0:
        return 0, 0, 0
    else:
        return cx / ln, cy / ln, cz / ln


@jit
def rad_circular_convert(rad: float) -> float:
    """Converts the given rad angle value to the equivalent angle on the interval [-pi,pi]."""
    # if rad > pi:
    #     rad -= pi * 2 * rad // (pi * 2)
    # elif rad < -pi:
    #     rad += pi * 2 * abs(rad) // (pi * 2)
    #
    # return rad

    while rad > pi:
        rad -= pi * 2

    while rad < -pi:
        rad += pi * 2

    return rad


@jit
def rad_clamp(rad: float) -> float:
    """Clamps the given value between pi*0.5 and pi*-0.5."""
    return fclamp(rad, -pi / 2, pi / 2)


@jit
def rotator_yaw(x: float, y: float, z: float, w: float) -> float:
    test: float = x * y + z * w
    if test > (0.5 - FEPSILON):
        return pi * 0.5

    if test < (-0.5 + FEPSILON):
        return pi * -0.5

    return asin(2 * test)


@jit
def rotator_pitch(x: float, y: float, z: float, w: float) -> float:
    test: float = x * y + z * w
    if test > (0.5 - FEPSILON):
        return 0

    if test < (-0.5 + FEPSILON):
        return 0

    y1: float = 2 * x * w - 2 * y * z
    x1: float = 1 - 2 * x ** 2 - 2 * z ** 2
    return atan2(y1, x1)


@jit
def rotator_roll(x: float, y: float, z: float, w: float) -> float:
    test: float = x * y + z * w
    if test > (0.5 - FEPSILON):
        return 2 * atan2(x, w)

    if test < (-0.5 + FEPSILON):
        return -2 * atan2(x, w)

    y1: float = 2 * y * w - 2 * x * z
    x1: float = 1 - 2 * y ** 2 - 2 * z ** 2
    return atan2(y1, x1)


def frange(start, stop=None, step=None):
    """Same as 'range', just with floats."""
    if not stop:
        stop = start
        start = 0.0

    if not step:
        step = 1.0

    start = epsilon_zero(start)
    stop = epsilon_zero(stop)
    step = epsilon_zero(step)

    if abs(stop - start) <= FEPSILON:
        return

    if step <= 0:
        raise ValueError('Step must be positive and non-zero (step=%s)' % (str(step),))

    if stop < 0 or start < 0:
        raise ValueError('All arguments must be positive (start=%s, stop=%s)' % (str(start), str(stop)))

    if stop < start:
        raise ValueError('Stop value must be greater than start value (start=%s, stop=%s)' % (str(start), str(stop)))

    # Kahan algorithm (W. Kahan. 1965. Pracniques: further remarks on reducing truncation errors. Commun. ACM 8)

    comp = 0.0  # compensation value for low order bits
    total = start  # running total

    while total < stop - FEPSILON:
        yield total
        y = step - comp
        temp = total + y
        comp = (temp - total) - y
        total = temp


def lerp(val, v1, v2):
    """Linearly interpolate between `v1' and `v2', val==0 results in `v1'."""
    return v1 + (v2 - v1) * val


def lerp_xi(val, minv, maxv):
    """
    Calculates the linear interpolation xi value corresponding to `val` if interpolated over the range [minv,maxv],
    ie. if lerp_xi(V,A,B)==X then lerp(X,A,B)==V assuming A<B. If minv>=maxv then `val` is returned.
    """
    return val if minv >= maxv else float(val - minv) / float(maxv - minv)
