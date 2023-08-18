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

from unittest import TestCase

from numpy.testing import assert_array_almost_equal

from eidolon.mathdef import ElemType, ShapeType


class TestShapeType(TestCase):
    def test_membership(self):
        self.assertIn(ShapeType._Tri, ShapeType)

    def test_value(self):
        st = ShapeType.Tet

        self.assertIsInstance(st, tuple)
        self.assertEqual(len(st), 3)


class TestElemType(TestCase):
    def test_point(self):
        self.assertIn(ElemType._Point, ElemType, "'Point' should be in ElemType")
        self.assertIsNotNone(ElemType.Point, "No Point type definition")

    def test_1nl_type(self):
        self.assertIsNotNone(ElemType.Tet1NL, "Linear test basis type failed")

    def test_2nl_type(self):
        self.assertIsNotNone(ElemType.Tet2NL, "Linear test basis type failed")

    def test_tri_basis(self):
        et = ElemType.Tri1NL
        xi = (0, 0, 0)
        expected = (1, 0, 0)

        assert_array_almost_equal(et.basis(*xi), expected)

    def test_tet_basis(self):
        et = ElemType.Tet1NL
        xi = (1 / 3, 1 / 3, 1 / 3)  # middle of far face
        expected = (0, 0.3333333, 0.3333333, 0.3333333)

        assert_array_almost_equal(et.basis(*xi), expected)
