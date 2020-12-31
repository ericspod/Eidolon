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

from eidolon.mathdef import vec3, Octree, generate_cylinder
from unittest import TestCase
from numpy.testing import assert_array_equal


class TestOctree(TestCase):
    def test_add_node(self):
        oc = Octree(1, vec3.one, vec3.one / 2)

        n, v, leaf = oc.add_node(vec3.zero, "zero")

        self.assertEqual(v, "zero")
        self.assertIsNotNone(leaf)

    def test_level1(self):
        oc = Octree(1, vec3.one, vec3.one / 2)

        self.assertEqual(len(oc.leaves), 8)

    def test_level2(self):
        oc = Octree(2, vec3.one, vec3.one / 2)

        self.assertEqual(len(oc.leaves), 64)

    def test_add_mesh1(self):
        oc = Octree(1, vec3.one * 1.05, vec3.one / 2)

        for v in [vec3.zero, vec3.X, vec3.Y, vec3.Z]:
            _, val, leaf = oc.add_node(v, 0)

            self.assertEqual(val, 0, f"Failed to add {v}")
            self.assertIsNotNone(leaf, f"Failed to add {v}")

    def test_add_mesh2(self):
        oc = Octree(1, vec3.one * 1.05, vec3.one / 2)
        oc.add_mesh([vec3.zero, vec3.X, vec3.Y, vec3.Z], [(0, 1, 2, 3)])
        leaves = oc.leaves

        self.assertEqual(sum(len(l.leafdata) > 0 for l in leaves), 4)

    def test_from_mesh(self):
        ctrls = [vec3.one * i for i in range(6)]
        radii = [0.75] * 6
        nodes, indices = generate_cylinder(ctrls, radii)

        oc = Octree.from_mesh(3, nodes, indices)

        leaves = oc.leaves
        all_indices = set()

        for leaf in leaves:
            all_indices.update(set(leaf.leafdata))

        self.assertSetEqual(all_indices, set(range(len(indices))))
