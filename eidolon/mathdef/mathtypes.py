from __future__ import annotations

import numpy as np
from numba import njit
from math import sin, cos, acos, asin, atan2, sqrt, pi, inf
from typing import Union, Optional

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


class vec3:

    def __init__(self, x: float, y: float, z: float = 0):
        self._x: float = x
        self._y: float = y
        self._z: float = z

    @property
    def x(self) -> float:
        return self._x

    @property
    def y(self) -> float:
        return self._y

    @property
    def z(self) -> float:
        return self._z

    def __repr__(self):
        return f"vec3({self._x}, {self._y}, {self._z})"

    def __copy__(self) -> vec3:
        return vec3(self._x, self._y, self._z)

    def __iter__(self):
        return iter((self._x, self._y, self._z))

    def __pos__(self) -> vec3:
        return vec3(self._x, self._y, self._z)

    def __neg__(self) -> vec3:
        return vec3(-self._x, -self._y, -self._z)

    def __abs__(self) -> vec3:
        return vec3(abs(self._x), abs(self._y), abs(self._z))

    def __add__(self, other: Union[vec3, float]) -> vec3:
        if isinstance(other, vec3):
            return vec3(self._x + other.x, self._y + other.y, self._z + other.z)
        else:
            return vec3(self._x + other, self._y + other, self._z + other)

    def __radd__(self, other: Union[vec3, float]) -> vec3:
        return self + other

    def __sub__(self, other: Union[vec3, float]) -> vec3:
        return self + (-other)

    def __rsub__(self, other: Union[vec3, float]) -> vec3:
        return other + (-self)

    def __mul__(self, other: Union[vec3, float]) -> vec3:
        if isinstance(other, vec3):
            return vec3(self._x * other.x, self._y * other.y, self._z * other.z)
        else:
            return vec3(self._x * other, self._y * other, self._z * other)

    def __rmul__(self, other: Union[vec3, float]) -> vec3:
        return self * other

    def __floordiv__(self, other: Union[vec3, float]) -> vec3:
        if isinstance(other, vec3):
            return vec3(self._x // other.x, self._y // other.y, self._z // other.z)
        else:
            return vec3(self._x // other, self._y // other, self._z // other)

    def __truediv__(self, other: Union[vec3, float]) -> vec3:
        if isinstance(other, vec3):
            return vec3(self._x / other.x, self._y / other.y, self._z / other.z)
        else:
            return vec3(self._x / other, self._y / other, self._z / other)

    def __eq__(self, other) -> bool:
        return fequals_eps(self._x, other.x) and fequals_eps(self._y, other.y) and fequals_eps(self._z, other.z)

    def __lt__(self, other: vec3) -> bool:
        return self._x < other.x and self._y < other.y and self._z < other.z

    def __gt__(self, other: vec3) -> bool:
        return self._x > other.x and self._y > other.y and self._z > other.z

    def __le__(self, other: vec3) -> bool:
        return self == other or self < other

    def __ge__(self, other: vec3) -> bool:
        return self == other or self > other

    def len(self) -> float:
        return len3(self._x, self._y, self._z)

    def len_sq(self) -> float:
        return lensq3(self._x, self._y, self._z)

    def abs(self) -> vec3:
        return vec3(abs(self._x), abs(self._y), abs(self._z))

    def inv(self) -> vec3:
        return vec3(finv(self._x), finv(self._y), finv(self._z))

    def sign(self) -> vec3:
        return vec3(fsign(self._x), fsign(self._y), fsign(self._z))

    def cross(self, other: vec3) -> vec3:
        return vec3(self._y * other.z - self._z * other.y, self._z * other.x - self._x * other.z,
                    self._x * other.y - self._y * other.x)

    def dot(self, other: vec3) -> float:
        return self._x * other.x + self._y * other.y + self._z * other.z

    def norm(self) -> vec3:
        length = self.len()
        return self / length if length > 0 else vec3.zero

    def dist_to(self, other: vec3) -> float:
        return (self - other).len()

    def dist_to_sq(self, other: vec3) -> float:
        return (self - other).len_sq()

    def clamp(self, vmin: vec3, vmax: vec3) -> vec3:
        return vec3(fclamp(self._x, vmin.x, vmax.x), fclamp(self._y, vmin.y, vmax.y), fclamp(self._z, vmin.z, vmax.z))

    def to_polar(self) -> vec3:
        length = self.len()
        if length == 0:
            return vec3.zero

        return vec3(atan2(self._y, self._x), acos(self._z / length), length)

    def to_cylindrical(self) -> vec3:
        return vec3(atan2(self._y, self._x), self._z, sqrt(self._y ** 2 + self._x ** 2))

    def from_polar(self) -> vec3:
        return vec3(
            cos(self._x) * sin(self._y) * self._z,
            sin(self._y) * sin(self._x) * self._z,
            cos(self._y) * self._z
        )

    def from_cylindrical(self) -> vec3:
        return vec3(cos(self._x) * self._z, sin(self._x) * self._z, self._y)

    def is_zero(self):
        return fequals_eps(self._x, 0) and fequals_eps(self._y, 0) and fequals_eps(self._z, 0)

    def in_aabb(self, vmin: vec3, vmax: vec3) -> bool:
        return vmin <= self <= vmax

    def in_obb(self, center: vec3, hx: vec3, hy: vec3, hz: vec3):
        diff: vec3 = self - center
        return abs(hx.dot(diff)) <= hx.len_sq() and abs(hy.dot(diff)) <= hy.len_sq() and abs(
            hz.dot(diff)) <= hz.len_sq()

    def in_sphere(self, center: vec3, radius: float) -> bool:
        return self.dist_to_sq(center) <= (radius ** 2 + FEPSILON)

    def on_plane(self, planept: vec3, planenorm: vec3) -> bool:
        return fequals_eps(self.plane_dist(planept, planenorm), 0)

    def is_parallel(self, other: vec3) -> bool:
        return self.cross(other).is_zero()

    def angle_to(self, other: vec3) -> float:
        length: float = sqrt(self.len_sq() * other.len_sq())

        if length < FEPSILON:
            return 0.0

        vl: float = self.dot(other) / length

        if vl >= (1.0 - FEPSILON):
            return 0.0

        if vl <= (FEPSILON - 1.0):
            return pi

        return acos(vl)

    def plane_norm(self, v2: vec3, v3: vec3, vfar: Optional[vec3] = None) -> vec3:
        pnorm = (v2 - self).cross(v3 - self).norm()

        if vfar is not None and pnorm.angle_to(vfar - self) < (pi * 0.5):
            return -pnorm

        return pnorm

    def plane_dist(self, planept: vec3, planenorm: vec3) -> float:
        return planenorm.dot(self - planept)

    def plane_project(self, planept: vec3, planenorm: vec3) -> vec3:
        return self - (planenorm * self.plane_dist(planept, planenorm))

    def tri_area(self, v2: vec3, v3: vec3) -> float:
        bb: vec3 = v2 - self
        cc: vec3 = v3 - self

        return bb.len() * cc.len() * sin(bb.angle_to(cc)) * 0.5

    def line_dist(self, v1: vec3, v2: vec3) -> float:
        axis: vec3 = v2 - v1
        al: float = axis.len()

        if al < FEPSILON:  # v1==v2 so no line
            return -1

        # self is below or above the cylinder
        if self.plane_dist(v1, axis) < 0 or self.plane_dist(v2, -axis) < 0:
            return -1

        return axis.cross(v1 - self).len() / al


# set unit axes and other global values
vec3.X = vec3(1, 0, 0)
vec3.Y = vec3(0, 1, 0)
vec3.Z = vec3(0, 0, 1)
vec3.zero = vec3(0, 0, 0)
vec3.one = vec3(1, 1, 1)
vec3.pos_inf = vec3(inf, inf, inf)
vec3.neg_inf = vec3(-inf, -inf, -inf)


class rotator:

    @staticmethod
    def from_axis(axis: vec3, rads: float) -> rotator:
        if fequals_eps(rads, 0) or axis.is_zero():  # no rotation or bad axis
            return rotator()

        na: vec3 = axis.norm()
        srads: float = sin(rads / 2)
        return rotator(na.x * srads, na.y * srads, na.z * srads, cos(rads / 2.0))

    @staticmethod
    def between_vecs(vfrom: vec3, vto: vec3) -> rotator:
        if vfrom == vto:
            return rotator

        return rotator.from_axis(vfrom.cross(vto), vfrom.angle_to(vto))

    @staticmethod
    def from_ypr(yaw: float, pitch: float, roll: float):
        c1: float = cos(0.5 * roll)
        s1: float = sin(0.5 * roll)
        c2: float = cos(0.5 * yaw)
        s2: float = sin(0.5 * yaw)
        c3: float = cos(0.5 * pitch)
        s3: float = sin(0.5 * pitch)
        c1c2: float = c1 * c2
        s1s2: float = s1 * s2
        c1s2: float = c1 * s2
        s1c2: float = s1 * c2

        _w: float = c1c2 * c3 - s1s2 * s3
        _x: float = c1c2 * s3 + s1s2 * c3
        _y: float = s1c2 * c3 + c1s2 * s3
        _z: float = c1s2 * c3 - s1c2 * s3

        return rotator(_x, _y, _z, _w)

    @staticmethod
    def from_mat3x3(m00: float, m01: float, m02: float, m10: float, m11: float, m12: float, m20: float, m21: float,
                    m22: float) -> rotator:
        tr: float = m00 + m11 + m22

        if tr > 0:
            s: float = sqrt(tr + 1.0) * 2  # s=4*qw
            _w: float = 0.25 * s
            _x: float = (m21 - m12) / s
            _y: float = (m02 - m20) / s
            _z: float = (m10 - m01) / s
        elif m00 > m11 and m00 > m22:
            s: float = sqrt(1.0 + m00 - m11 - m22) * 2  # s=4*qx
            _w: float = (m21 - m12) / s
            _x: float = 0.25 * s
            _y: float = (m01 + m10) / s
            _z: float = (m02 + m20) / s
        elif m11 > m22:
            s: float = sqrt(1.0 + m11 - m00 - m22) * 2  # s=4*qy
            _w: float = (m02 - m20) / s
            _x: float = (m01 + m10) / s
            _y: float = 0.25 * s
            _z: float = (m12 + m21) / s
        else:
            s: float = sqrt(1.0 + m22 - m00 - m11) * 2  # s=4*qz
            _w: float = (m10 - m01) / s
            _x: float = (m02 + m20) / s
            _y: float = (m12 + m21) / s
            _z: float = 0.25 * s

        return rotator(_x, _y, _z, _w)

    @staticmethod
    def between_planes(row1: vec3, col1: vec3, row2: vec3, col2: vec3) -> rotator:
        """
        Defines a rotation to transform a plane defined with row/column vectors (row2,col2) to plane (row1,col1).
        This implies a rotation between plane normals and a rotation to transform the right-facing vector to the
        row vector. All args are assumed normalized.
        """
        norm1: vec3 = col1.cross(row1).norm()
        norm2: vec3 = col2.cross(row2).norm()

        if norm1 == -norm2:
            rot: rotator = rotator(row1, pi)
        else:
            rot: rotator = rotator.between_vecs(norm2, norm1)

        return rotator.between_vecs(rot * row2, row1) * rot

    def __init__(self, x: float = 0, y: float = 0, z: float = 0, w: float = 1):
        self._x: float = x
        self._y: float = y
        self._z: float = z
        self._w: float = w

    @property
    def x(self) -> float:
        return self._x

    @property
    def y(self) -> float:
        return self._y

    @property
    def z(self) -> float:
        return self._z

    @property
    def w(self) -> float:
        return self._w

    def yaw(self) -> float:
        return rotator_yaw(self._x, self._y, self._z, self._w)

    def pitch(self) -> float:
        return rotator_pitch(self._x, self._y, self._z, self._w)

    def roll(self) -> float:
        return rotator_roll(self._x, self._y, self._z, self._w)

    def __repr__(self):
        return f"rotator({self._x}, {self._y}, {self._z}, {self._w})"

    def __copy__(self) -> rotator:
        return rotator(self._x, self._y, self._z, self._w)

    def __iter__(self):
        return iter((self._x, self._y, self._z, self._w))

    def __mul__(self, other: Union[vec3, rotator]) -> Union[vec3, rotator]:
        if isinstance(other, vec3):
            axis: vec3 = vec3(self._x, self._y, self._z)
            vc: vec3 = axis.cross(other)
            vcc: vec3 = axis.cross(vc)

            return (vc * (2.0 * self._w)) + (vcc * 2.0) + other
        else:
            x = self._w * other._x + self._x * other._w + self._y * other._z - self._z * other._y
            y = self._w * other._y + self._y * other._w + self._z * other._x - self._x * other._z
            z = self._w * other._z + self._z * other._w + self._x * other._y - self._y * other._x
            w = self._w * other._w - self._x * other._x - self._y * other._y - self._z * other._z

            return rotator(x, y, z, w)

    def __rmul__(self, other: Union[vec3, rotator]) -> Union[vec3, rotator]:
        return self * other

    def __truediv__(self, other: Union[vec3, rotator]) -> Union[vec3, rotator]:
        return ~self * other

    def __rtruediv__(self, other: Union[vec3, rotator]) -> Union[vec3, rotator]:
        return ~self * other

    def __invert__(self) -> rotator:
        return self.conjugate().norm()

    def __eq__(self, other: rotator) -> bool:
        return fequals_eps(self._x, other.x) and fequals_eps(self._y, other.y) and \
               fequals_eps(self._z, other.z) and fequals_eps(self._w, other.w)

    def conjugate(self):
        return rotator(-self._x, -self._y, -self._z, self._w)

    def len(self) -> float:
        return sqrt(self._x ** 2 + self._y ** 2 + self._z ** 2 + self._w ** 2)

    def dot(self, rot: rotator) -> float:
        return self._x * rot.x + self._y * rot.y + self._z * rot.z + self._w * rot.w

    def norm(self) -> rotator:
        length: float = self.len()
        return rotator(self._x / length, self._y / length, self._z / length, self._w / length)

    def interpolate(self, val: float, rot: rotator) -> rotator:
        if val >= 1:
            return rot
        elif val <= 0:
            return self

        mult: float = -1 if self.dot(rot) < 0 else 1
        components: list = [s + (mult * r - s) * val for s, r in zip(self, rot)]

        return rotator(*components).norm()

    def to_matrix(self) -> np.ndarray:
        out: np.ndarray = np.eye(4)
        rnorm: rotator = self.norm()
        x2: float = rnorm.x * rnorm.x
        y2: float = rnorm.y * rnorm.y
        z2: float = rnorm.z * rnorm.z
        xy: float = rnorm.x * rnorm.y
        xz: float = rnorm.x * rnorm.z
        yz: float = rnorm.y * rnorm.z
        wz: float = rnorm.w * rnorm.z
        wx: float = rnorm.w * rnorm.x
        wy: float = rnorm.w * rnorm.y

        out[0] = 1.0 - 2.0 * (y2 + z2), 2.0 * (xy - wz), 2.0 * (xz + wy), 0
        out[1] = 2.0 * (xy + wz), 1.0 - 2.0 * (x2 + z2), 2.0 * (yz - wx), 0
        out[2] = 2.0 * (xz - wy), 2.0 * (yz + wx), 1.0 - 2.0 * (x2 + y2), 0

        return out


class ray:
    def __init__(self, pos: vec3, vdir: vec3):
        self._pos: vec3 = pos
        self._vdir: vec3 = vdir.norm()
        self._invdir: vec3 = vdir.inv()
        self._signx: bool = self.invdir.x < 0
        self._signy: bool = self.invdir.y < 0
        self._signz: bool = self.invdir.z < 0

    @property
    def pos(self) -> vec3:
        return self._pos

    @property
    def vdir(self) -> vec3:
        return self._vdir

    def get_position(self, dist: float) -> vec3:
        return self._pos + self._vdir * dist

    def dist_to(self, otherpos: vec3) -> float:
        return self._vdir.dot(otherpos)

    def on_plane(self, planept: vec3, planenorm: vec3) -> bool:
        return self._pos.on_plane(planept, planenorm) and (self._pos + self._vdir).on_plane(planept, planenorm)

    def intersects_plane(self, planept: vec3, planenorm: vec3) -> float:
        return planenorm.dot(planept - self._pos) / planenorm.dot(self._vdir)


class transform:
    @staticmethod
    def from_values(tx: float = 0, ty: float = 0, tz: float = 0, sx: float = 0, sy: float = 0, sz: float = 0,
                    rx: float = 0, ry: float = 0, rz: float = 0, rw: float = 1, is_inverse: bool = False) -> transform:

        return transform(vec3(tx, ty, tz), vec3(sx, sy, sz), rotator(rx, ry, rz, rw), is_inverse)

    def __init__(self, trans: Optional[vec3] = None, scale: Optional[vec3] = None,
                 rot: Optional[rotator] = None, is_inverse: bool = False):
        self._trans = trans or vec3.zero
        self._scale = scale or vec3.one
        self._rot = rot or rotator()
        self._is_inverse = is_inverse

    @property
    def trans(self):
        return self._trans

    @property
    def scale(self):
        return self._scale

    @property
    def rot(self):
        return self._rot

    @property
    def is_inverse(self):
        return self._is_inverse

    def __mul__(self, other: Union[vec3, ray, transform]) -> Union[vec3, ray, transform]:
        if isinstance(other, vec3):
            if self._is_inverse:
                return self._scale * (self._rot * (other + self._trans))
            else:
                return self._trans + (self._rot * (other * self._scale))
        elif isinstance(other, ray):
            return ray(self * other.pos, self.directional() * other.vdir)
        else:
            mincorner: vec3 = self * (other * vec3())
            maxcorner: vec3 = self * (other * vec3.one)
            xcorner: vec3 = self * (other * vec3.X)
            ycorner: vec3 = self * (other * vec3.Y)

            rot: rotator = rotator.between_planes((xcorner - mincorner).norm(), (ycorner - mincorner).norm(), vec3.X,
                                                  vec3.Y)
            scale: vec3 = rot / (maxcorner - mincorner)

            return transform(mincorner, scale, rot)

    def __rmul__(self, other: Union[vec3, ray, transform]) -> Union[vec3, ray, transform]:
        return self * other

    def __truediv__(self, other: Union[vec3, ray, transform]) -> Union[vec3, ray, transform]:
        return ~self * other

    def __rtruediv__(self, other: Union[vec3, ray, transform]) -> Union[vec3, ray, transform]:
        return self / other

    def __invert__(self) -> transform:
        return transform(self._trans * -1, self._scale.inv(), ~self._rot, not self._is_inverse)

    def __eq__(self, other: transform) -> bool:
        return self._trans == other.trans and self._scale == other.scale and \
               self._rot == other.rot and self._is_inverse == other.is_inverse

    def __repr__(self):
        return f"transform({self._rot}, {self._scale}, {self._rot}, {self._is_inverse})"

    def directional(self) -> transform:
        return transform(vec3(), self._scale, self._rot, self._is_inverse)

    def to_matrix(self) -> np.ndarray:
        out = self._rot.to_matrix()

        if self._is_inverse:
            out[:3, 0] *= self._scale.x
            out[:3, 1] *= self._scale.y
            out[:3, 2] *= self._scale.z
            out[0, 3] = self._trans.dot(vec3(*out[0, :3]))
            out[1, 3] = self._trans.dot(vec3(*out[1, :3]))
            out[2, 3] = self._trans.dot(vec3(*out[2, :3]))
        else:
            out[0, :3] *= self._scale.x
            out[1, :3] *= self._scale.y
            out[2, :3] *= self._scale.z
            out[:3, 3] = tuple(self._trans)

        return out


if __name__ == "__main__":
    v = vec3(1, -2, 3)
    print(v, v.inv(), v.cross(vec3(1, -2, 0)))
    print(abs(v))
    print(2.1 * (v + 1))
    print(list(v))
    print((v + 1) == vec3(2, -1, 4), (v + 1) > v)

    print(vec3(0, 0, 0).in_aabb(vec3(-1, -1, -1), vec3(1, 1, 1)))
    print(vec3.X)

    print(~rotator(1, 0, 1, 1))
    print(rotator(1, 0, 1, 1).yaw())

    print(rotator.from_axis(vec3.X, 0.5).to_matrix())

    print(transform(vec3(1, 2, 3), vec3(1, 2, 3), rotator.from_axis(vec3.one, 0.5)).to_matrix())

    t1 = transform(vec3(1, 2, -3), vec3(1.1, 1.2, 1.3), rotator.from_axis(vec3.one, 0.5))

    m1 = t1.to_matrix()
    m2 = (~t1).to_matrix()

    print(m1)
    print(m2)
    print(np.matmul(m1, m2))
