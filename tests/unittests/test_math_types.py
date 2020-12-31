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

from eidolon.mathdef import vec3, rotator, transform
from unittest import TestCase
from numpy.testing import assert_array_equal


class TestVec3(TestCase):
    def test_basic(self):
        v = vec3(1, -2, 3)

        assert_array_equal(tuple(v), (1, -2, 3))

    def test_mathops(self):
        v = vec3.one
        expr = v * vec3(1, 0, 2) + vec3(-2, 1, 3.5)
        expected = vec3(-1, 1, 5.5)

        assert_array_equal(expr, expected)

    def test_aabb(self):
        assert vec3(0, 0, 0).in_aabb(vec3(-1, -1, -1), vec3(1, 1, 1))


class TestRotator(TestCase):
    def test_basic(self):
        r = rotator()

        assert_array_equal(tuple(r), (0, 0, 0, 1))
        self.assertEqual(r.yaw, 0)
        self.assertEqual(r.pitch, 0)
        self.assertEqual(r.roll, 0)
