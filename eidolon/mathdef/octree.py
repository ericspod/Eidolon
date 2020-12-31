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

from __future__ import annotations
import operator
from typing import Callable, Iterable

import numpy as np
from .math_types import vec3, BoundBox
from ..utils import list_sum, first


class Octree:
    """
    This implements a map between vectors an given values using a recursive octree data structure
    to optimize searching by partitioning space. Vectors are tested for equivalence using the '=='
    operator. Vectors are added to the tree which are assigned to their appropriate node as determined
    by spatial searching; if a vector is already present which is considered equivalent the stored
    one is returned.
    Octants:
        0 = (-,-,-)
        1 = (+,-,-)
        2 = (-,+,-)
        3 = (+,+,-)
        4 = (-,-,+)
        5 = (+,-,+)
        6 = (-,+,+)
        7 = (+,+,+)
        8 = (0,0,0) (root)
    """

    @staticmethod
    def octant_mul(octant: int):
        """Returns a multiplicative vector corresponding to this octant's signs."""
        if octant == 8:
            return vec3.zero

        x = 1 if octant % 2 == 1 else -1
        y = 1 if octant in (2, 3, 6, 7) else -1
        z = 1 if octant > 3 else -1

        return vec3(x, y, z)

    @staticmethod
    def from_mesh(depth: int, nodes: np.array, inds: np.array, margins: float = 0.05, eq_func: Callable = None):
        aabb = BoundBox.from_vertices(nodes)
        octree = Octree(depth, aabb.diag * (1.0 + margins), aabb.center, eq_func)
        octree.add_mesh(nodes, inds)
        return octree

    def __init__(self, depth: int, dim: vec3, parentcenter: vec3, eq_func: Callable = None, octant: int = 8,
                 parent: Octree = None):
        """
        Initializes a new self-contained octree or an octant within one. When creating a new octree, `octant' and
        `parent' must be left with their default values, `depth' will define how many levels of sub-octants to create,
        `dim' is the total dimension of the AABB area covered by the tree, and `parentcenter' is the center of this
        area. The `eq_func' function is used to test equality between nodes added to the tree, operator.eq is used
        if None is given for this argument. When sub-octrees are being instantiated, the values for all arguments will
        be chosen by the instantiating parent.
        """
        assert octant == 8 or parent is not None

        self.parent = parent  # parent octant
        self.depth = depth  # depth==0 means this is a leaf node
        self.octant = octant  # between 0 and 8 as described above
        self.dim = dim  # dimensions of this octant
        dim2 = self.dim * 0.5

        self.center = parentcenter + (dim2 * Octree.octant_mul(self.octant))  # center of this octant
        self.aabb = BoundBox(self.center - dim2, self.center + dim2)

        self.nodes = dict()
        self.leafdata = []
        self.eq_func = operator.eq if eq_func is None else eq_func

        self.name = 'Oc' if self.parent is None else self.parent.name + str(self.octant)
        self.subtrees = []

        if depth != 0:
            self.subtrees = [Octree(depth - 1, dim2, self.center, self.eq_func, oc, self) for oc in range(8)]

    @property
    def octant_id(self):
        assert self.depth <= 16, 'Cannot create unique IDs for octrees greater than 16 in depth.'
        pid = 0 if self.parent is None else self.parent.octant_id
        return pid << 4 | self.octant

    def __repr__(self):
        return f"{self.name}<{self.octant_id}, {self.depth}, {self.octant}, {self.center}>"

    @property
    def leaves(self):
        """Returns the Octree instances at the bottom of the tree in depth-first order (rather than spatial order)."""
        if self.depth == 1:
            return self.subtrees
        else:
            return list_sum(t.leaves for t in self.subtrees)

    def add_tree(self, other: Octree, init_func: Callable, merge_func: Callable):
        """
        Add the elements of `other` into self, using `init_func` to initialize values and `mergefunc` to merge them.
        """
        for leaf1, leaf2 in zip(self.leaves, other.leaves):
            for n2, vals2 in leaf2.nodes.items():
                n1, vals1 = leaf1.add_node(n2, init_func())
                merge_func(vals1, vals2)

    def __contains__(self, other: vec3):
        """Returns true if the node `other` is in the octant's axis-aligned cuboid space."""
        return other in self.aabb

    def plane_intersects(self, planept: vec3, planenorm: vec3):
        """
        Returns True if the plane defined by the point `planept` and normal `planenorm` passes through this octant.
        """
        # return self.aabb.getInternalPlane(planept,planenorm)!=None
        return self.aabb.plane_intersects(planept, planenorm)

    def get_intersected_leaves(self, planept: vec3, planenorm: vec3):
        """Returns the list of leaf octants which the plane defined by (planept,planenorm) intersects."""
        if not self.plane_intersects(planept, planenorm):
            return []
        elif self.depth == 0:
            return [self]
        else:
            return list_sum(l.get_intersected_leaves(planept, planenorm) for l in self.subtrees)

    def get_octant(self, n: vec3):
        """Get the child octant within this octant which should contain `n`."""

        nn = n - self.center
        result = 0

        if nn.z >= 0:
            result += 4
        if nn.y >= 0:
            result += 2
        if nn.x >= 0:
            result += 1

        return result

    def stores_node(self, n: vec3):
        """Returns true if 'n' is in the octant and stored by an Octree node."""
        return n in self and (self._get_equivalent_node(n) is not None or any(n in t for t in self.subtrees))

    @property
    def num_nodes(self):
        """Returns the number of nodes stored in this tree."""
        return sum(len(leaf.nodes) for leaf in self.leaves)

    def _get_equivalent_node(self, n: vec3):
        """Returns the first key in `self.nodes' which is equal to `n' acccording the equality function."""
        return first(nn for nn in self.nodes if self.eq_func(n, nn))

    def get_leaf(self, n: vec3):
        """Find the Octree leaf object whose bound box contains `n`, returning None if `n` is outside."""
        if self.depth == 0:  # this is a leaf so must be it
            return self

        if self.octant == 8 and n not in self:  # if the root octant and `n` is not in our space, return None
            return None

        return self.subtrees[self.get_octant(n)].get_leaf(n)  # find the child octant that contains `n`

    def get_node(self, n: vec3):
        """Returns the value stored in the tree for 'n' or None if not found."""
        leaf = self.get_leaf(n)
        return leaf and leaf.nodes.get(n, None)

    def __iter__(self):
        """Iterates over all (node,value) pairs stored in this tree."""
        if self.depth == 0:
            for n in self.nodes.items():
                yield n
        else:
            for sb in self.subtrees:
                for n in sb:
                    yield n

    def add_node(self, n: vec3, vals):
        """
        Add the node `n` into the tree. If an equivalent is not present, `n` is added to the octree with `vals` as its
        mapped value and both are returned as well as the leaf object. If an equivalent node is found this and its
        value is returned with the leaf object, ignoring `vals` entirely. Return value is the stored node, stored
        values, and leaf storing the node.
        """
        leaf = self.get_leaf(n)

        if leaf:
            nn = leaf._get_equivalent_node(n)
            if nn is not None:
                return nn, leaf.nodes[nn], leaf
            else:
                leaf.nodes[n] = vals
                return n, vals, leaf
        else:
            return None, None, None

    def add_leaf_data(self, n: vec3, val):
        """Find the leaf `n' belongs in and add `val' to its `leafdata' field."""
        leaf = self.get_leaf(n)
        if leaf:
            leaf.leafdata.append(val)

    def add_mesh(self, nodes: Iterable, inds: Iterable):
        """
        Add the nodes from `nodes` to the octree, mapping them to the element index they were referenced from, and
        storing the element index in each leaf an element occurs in.
        """
        for eidx, elem in enumerate(inds):
            for nidx in elem:
                _, _, leaf = self.add_node(vec3(*nodes[nidx]), eidx)  # store the node in the leaf
                leaf.leafdata.append(eidx)  # store the element ID in the leaf
