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

from enum import Enum
from typing import List, Tuple, Union

from ..utils import first
from .render_utils import create_simple_geom
from .camera import OffscreenCamera
from ..mathdef.math_types import vec3, rotator, transform, BoundBox, Transformable

from panda3d.core import (
    NodePath,
    GeomNode,
    Geom,
    TransparencyAttrib,
    Texture,
    BoundingBox,
    BoundingSphere,
    LQuaternionf,
    RenderModeAttrib
)

__all__ = ["Figure", "SimpleFigure", "RenderMode"]


class RenderMode(Enum):
    UNCHANGED = RenderModeAttrib.M_unchanged,
    FILLED = RenderModeAttrib.M_filled,
    WIREFRAME = RenderModeAttrib.M_wireframe,
    POINT = RenderModeAttrib.M_point,
    FILLED_FLAT = RenderModeAttrib.M_filled_flat,
    FILLED_WIREFRAME = RenderModeAttrib.M_filled_wireframe


class Figure(Transformable):
    def __init__(self, name: str, *geoms: Geom):
        super().__init__()
        self.name: str = name
        self.node: GeomNode = GeomNode(name + "_node")
        self.camnodes: List[NodePath] = []
        self._visible: bool = True

        for geom in geoms:
            self.add_geom(geom)

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

    def detach_all(self):
        for cm in self.camnodes:
            cm.detach_node()

        self.camnodes[:] = []

    @property
    def attached(self) -> bool:
        """Returns True if this figure is attached to any camera."""
        return len(self.camnodes) > 0

    def attached_to_camera(self, camera: OffscreenCamera) -> bool:
        """Returns True if this figure is attached to `camera`."""
        return any(cm in camera.nodepath.children for cm in self.camnodes)

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

    @property
    def render_mode(self) -> RenderMode:
        if self.camnodes:
            mode = first(self.camnodes).get_render_mode()
            return first(m for m in RenderMode if m.value == mode)

        return None

    def set_render_mode(self, mode: RenderMode, point_thickness: float = 1.0, wireframe_color=(1, 1, 1, 1)):
        if mode not in RenderMode:
            raise ValueError(f"Render mode {mode} not valid, must be in RenderMode")

        for camnode in self.camnodes:
            if mode == RenderMode.FILLED_WIREFRAME:
                camnode.set_render_mode_filled_wireframe(wireframe_color)
            else:
                camnode.set_render_mode(mode.value[0], point_thickness)

    def set_texture(self, tex: Texture):
        for camnode in self.camnodes:
            camnode.set_texture(tex)

    def aabb(self) -> BoundBox:
        bb = None

        for geom in self.node.get_geoms():
            bounds = geom.get_bounds()

            if isinstance(bounds, BoundingBox):
                vmin = vec3(*bounds.get_min())
                vmax = vec3(*bounds.get_max())
            elif isinstance(bounds, BoundingSphere):
                center = vec3(*bounds.get_center())
                rad = bounds.get_radius()
                diag = vec3.one * rad
                vmin = center - diag
                vmax = center + diag
            else:
                raise ValueError(f"Unknown bounds object {bounds}")

            newbb = BoundBox(vmin, vmax)
            bb = newbb if bb is None else (bb + newbb)

        return bb * self.get_transform()


class SimpleFigure(Figure):
    def __init__(self, name: str, vertices, indices=None, norms=None, colors=None, uvcoords=None):
        super().__init__(name, create_simple_geom(vertices, indices, norms, colors, uvcoords))
