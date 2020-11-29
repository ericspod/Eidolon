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

__all__ = ["create_geom", "Mesh"]


def create_geom(vertices, norms, colors, indices, uvcoords):
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
    def __init__(self, name: str, vertices, norms, colors, uvcoods, indices):
        self.name: str = name
        self.geom: Geom = create_geom(vertices, norms, colors, indices, uvcoods)
        self.node: GeomNode = GeomNode(name + "_node")
        self.node.addGeom(self.geom)
        self.camnodes: List[NodePath] = []
        self._visible: bool = True
        self._transform: transform = transform()

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

    @property
    def scale(self):
        return self._transform.scale

    def get_tranform(self):
        return self._transform

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

        for cm in self.camnodes:
            if visible:
                cm.show()
            else:
                cm.hide()
