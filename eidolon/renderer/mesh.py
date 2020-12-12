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

from .utils import create_simple_geom
from .camera import OffscreenCamera
from ..mathdef.mathtypes import vec3, rotator, transform
from panda3d.core import LQuaternionf

from panda3d.core import (
    NodePath,
    GeomNode,
    Geom,
    TransparencyAttrib,
    Texture
)

__all__ = ["Mesh", "SimpleMesh"]


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
    def position(self, pos: vec3):
        self.set_transform(transform(pos, self._transform.scale, self._transform.rot))

    @property
    def orientation(self):
        return self._transform.rot

    @orientation.setter
    def orientation(self, rot: rotator):
        self.set_transform(transform(self._transform.trans, self._transform.scale, rot))

    @property
    def scale(self):
        return self._transform.scale

    @scale.setter
    def scale(self, scale: vec3):
        self.set_transform(transform(self._transform.trans, scale, self._transform.rot))

    def get_transform(self):
        return self._transform

    def set_transform(self, trans: transform):
        self._transform = trans
        x, y, z, w = trans.rot
        rf = LQuaternionf(w, x, y, z)

        for camnode in self.camnodes:
            camnode.set_pos(*trans.trans)
            camnode.set_quat(rf)
            camnode.set_scale(*trans.scale)

    def add_geom(self, geom: Geom):
        self.node.add_geom(geom)

    def attach(self, camera: OffscreenCamera):
        cnode: NodePath = camera.nodepath.attach_new_node(self.node)
        cnode.set_transparency(TransparencyAttrib.M_alpha)
        cnode.set_two_sided(True)

        self.camnodes.append(cnode)

    def detach(self, camera: OffscreenCamera):
        for i in range(len(self.camnodes)):
            if self.camnodes[i] in camera.nodepath.children:
                self.camnodes[i].detach_node()
                del self.camnodes[i]
                break

    @property
    def visible(self):
        return self._visible

    @visible.setter
    def visible(self, visible: bool):
        self._visible = visible

        for camnode in self.camnodes:
            if visible:
                camnode.show()
            else:
                camnode.hide()

    def set_texture(self, tex: Texture):
        for camnode in self.camnodes:
            camnode.set_texture(tex)


class SimpleMesh(Mesh):
    def __init__(self, name: str, vertices, indices, norms=None, colors=None, uvcoords=None):
        super().__init__(name, create_simple_geom(vertices, indices, norms, colors, uvcoords))
