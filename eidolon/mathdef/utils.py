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

from .compile_support import jit

__all__ = [
    "FEPSILON", "len3", "lensq3", "fequals_eps", "finv", "fsign", "fclamp", "rad_clamp", "rad_circular_convert",
    "rotator_yaw", "rotator_roll", "rotator_pitch","frange"
]

FEPSILON: float = 1e-10


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
