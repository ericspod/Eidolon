from unittest import TestCase
from numpy.testing import assert_array_almost_equal

from eidolon.mathdef import ShapeType, ElemType


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
