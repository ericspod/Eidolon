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

from typing import List

from ..mathdef.mathtypes import vec3, transform
from panda3d.core import LQuaternionf

from panda3d.core import (
    NodePath,
    GeomNode,
    Geom,
    GeomVertexFormat,
    GeomVertexData,
    GeomVertexWriter,
    LVector3,
    GeomTriangles,
    TransparencyAttrib,
)

__all__ = ["create_simple_geom", "Mesh", "SimpleMesh"]


def create_simple_geom(vertices, norms, colors, indices, uvcoords):
    vformat = GeomVertexFormat.get_v3n3c4t2()
    vdata = GeomVertexData("square", vformat, Geom.UHDynamic)

    vertex = GeomVertexWriter(vdata, "vertex")
    normal = GeomVertexWriter(vdata, "normal")
    color = GeomVertexWriter(vdata, "color")
    texcoord = GeomVertexWriter(vdata, "texcoord")

    for i in range(len(vertices)):
        vertex.addData3f(*vertices[i])
        normal.addData3f(LVector3(*norms[i]).normalized())
        color.addData4f(*colors[i])
        texcoord.addData2f(*uvcoords[i])

    tris = GeomTriangles(Geom.UHDynamic)

    for i in range(len(indices)):
        tris.addVertices(*indices[i])

    geom = Geom(vdata)
    geom.addPrimitive(tris)
    return geom


class Mesh:
    def __init__(self, name: str, *geoms: Geom):
        self.name: str = name
        self.node: GeomNode = GeomNode(name + "_node")
        self.camnodes: List[NodePath] = []
        self._visible: bool = True
        self._transform: transform = transform()

        for geom in geoms:
            self.add_geom(geom)

    @property
    def position(self):
        return self._transform.trans

    @position.setter
    def position(self, pos):
        self._transform = transform(pos, self._transform.scale, self._transform.rot)
        for camnode in self.camnodes:
            camnode.set_pos(*pos)

    @property
    def orientation(self):
        return self._transform.rot

    @orientation.setter
    def orientation(self, rot):
        self._transform = transform(self._transform.trans, self._transform.scale, rot)
        x, y, z, w = rot
        rf = LQuaternionf(w, x, y, z)
        for camnode in self.camnodes:
            camnode.set_quat(rf)

    @property
    def scale(self):
        return self._transform.scale

    @scale.setter
    def scale(self, scale):
        self._transform = transform(self._transform.trans, scale, self._transform.rot)
        for camnode in self.camnodes:
            camnode.set_scale(*scale)

    def get_tranform(self):
        return self._transform

    def add_geom(self, geom):
        self.node.add_geom(geom)

    def attach(self, camera):
        cnode: NodePath = camera.nodepath.attach_new_node(self.node)
        cnode.set_transparency(TransparencyAttrib.M_alpha)
        self.camnodes.append(cnode)

    def detach(self, camera):
        for i in range(len(self.camnodes)):
            if self.camnodes[i] in camera.nodepath.children:
                self.camnodes[i].detach_node()
                del self.camnodes[i]
                break

    @property
    def visible(self):
        return self._visible

    @visible.setter
    def visible(self, visible):
        self._visible = visible

        for camnode in self.camnodes:
            if visible:
                camnode.show()
            else:
                camnode.hide()


class SimpleMesh(Mesh):
    def __init__(self, name: str, vertices, indices, norms=None, colors=None, uvcoords=None):
        norms = norms or [vec3.Z] * len(vertices)
        colors = colors or [(1, 1, 1, 1)] * len(vertices)
        uvcoords = uvcoords or [(0, 0)] * len(vertices)
        super().__init__(name, create_simple_geom(vertices, norms, colors, indices, uvcoords))
