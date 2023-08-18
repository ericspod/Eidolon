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

import numpy as np

from eidolon.mathdef import (
    Mesh,
    MeshDataValue,
    calculate_mesh_ext_adj,
    calculate_mesh_octree,
    calculate_shared_nodes,
    vec3,
)


class SimpleMeshTestCase(TestCase):
    def setUp(self) -> None:
        nodes = np.array([(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 1)])
        inds = np.array([(0, 1, 2, 3), (1, 2, 3, 4)])

        self.mesh = Mesh(nodes, {"inds": (inds, "Tet1NL")})


class TestCalculateOctree(SimpleMeshTestCase):
    def test_calculate_octree(self):
        calculate_mesh_octree(self.mesh, "inds")

        self.assertIn(("inds", MeshDataValue.octree), self.mesh.other_data)


class TestCalculateSharedNodes(SimpleMeshTestCase):
    def test_calculate_shared_nodes(self):
        result = calculate_shared_nodes(self.mesh.topos["inds"][0], np.array([0, 1]))

        self.assertEqual(len(result), 5)
        self.assertTupleEqual(tuple(result[0]), (0,))
        self.assertTupleEqual(tuple(result[1]), (0, 1))
        self.assertTupleEqual(tuple(result[2]), (0, 1))
        self.assertTupleEqual(tuple(result[3]), (0, 1))
        self.assertTupleEqual(tuple(result[4]), (1,))


class TestCalculateExtAdj(SimpleMeshTestCase):
    def test_calculate_extadj(self):
        calculate_mesh_octree(self.mesh, "inds")
        result = calculate_mesh_ext_adj(self.mesh, "inds")

        self.assertIn(("inds", MeshDataValue.ext_adj), self.mesh.other_data)

        expected = np.array([[-1, -1, -1, 1, -1, -1, -1, 0], [0, -1, -1, -1, 3, -1, -1, -1]])

        np.testing.assert_array_equal(expected, result)
