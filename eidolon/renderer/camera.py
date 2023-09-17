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

from typing import Optional

import numpy as np
from panda3d.core import (
    Camera,
    FrameBufferProperties,
    GraphicsOutput,
    GraphicsPipe,
    Lens,
    LPoint2f,
    LPoint3f,
    NodePath,
    Texture,
    WindowProperties,
)

from eidolon.mathdef import BoundBox, ray, vec3
from eidolon.renderer.render_base import RenderBase
from eidolon.utils import color

__all__ = ["OffscreenCamera"]


class OffscreenCamera:
    def __init__(
        self,
        name: str,
        width: int = 400,
        height: int = 400,
        sort: int = -100,
        clear_color: color = (0.1, 0.1, 0.1, 1),
        rbase: Optional[RenderBase] = None,
    ):
        self.rbase: RenderBase = rbase or RenderBase.instance()
        self.name: str = name

        self.texture: Texture = Texture()
        self.texture.setMinfilter(Texture.FTLinear)
        self.texture.setFormat(Texture.FRgba32)
        self.texture.set_wrap_u(Texture.WM_clamp)
        self.texture.set_wrap_v(Texture.WM_clamp)

        winprops = WindowProperties()
        winprops.set_size(width, height)

        props = FrameBufferProperties()
        props.set_rgb_color(True)
        props.set_rgba_bits(8, 8, 8, 8)
        props.set_depth_bits(8)

        with self.rbase.lock:
            self.buffer = self.rbase.graphicsEngine.make_output(
                self.rbase.pipe,
                name,
                sort,
                props,
                winprops,
                GraphicsPipe.BF_resizeable,
                self.rbase.win.get_gsg(),
                self.rbase.win,
            )

            self.buffer.add_render_texture(self.texture, GraphicsOutput.RTMCopyRam)
            self.buffer.set_sort(sort)
            self.camera: NodePath = self.rbase.make_camera(self.buffer, camName=name)

            self.nodepath: NodePath = NodePath(name + "_nodepath")
            self.camera.reparent_to(self.nodepath)

            self.camera_node: Camera = self.camera.node()
            self.lens: Lens = self.camera_node.get_lens()

            self.set_clear_color(clear_color)

    def set_clear_color(self, clear_color: color):
        if clear_color is None:
            self.buffer.set_clear_active(GraphicsOutput.RTPColor, False)
        else:
            self.buffer.set_clear_color(clear_color)
            self.buffer.set_clear_active(GraphicsOutput.RTPColor, True)

    def get_clear_color(self):
        clear_active = self.buffer.get_clear_active(GraphicsOutput.RTPColor)
        return tuple(self.buffer.get_clear_color()) if clear_active else None

    def get_memory_image(self):
        if not self.texture.might_have_ram_image():
            raise MemoryError("Texture does not have RAM image")

        data = self.texture.get_ram_image_as("RGBA").getData()
        datanp = np.frombuffer(data, np.uint8)
        datanp = datanp.reshape((self.texture.getYSize(), self.texture.getXSize(), 4))

        return datanp[::-1]

    @property
    def size(self):
        return tuple(self.lens.get_film_size())

    def resize(self, width, height):
        self.lens.set_film_size(width, height)
        self.buffer.set_size(width, height)

    def set_camera_lookat(self, position: vec3, look_at: vec3, up: Optional[vec3] = None):
        self.camera.set_pos(*position)

        if up is None:
            self.camera.look_at(LPoint3f(*look_at))
        else:
            self.camera.look_at(LPoint3f(*look_at), LPoint3f(*up))

    @property
    def scene_aabb(self):
        bounds = self.nodepath.get_tight_bounds()
        vmin,vmax = bounds if bounds is not None else (vec3.zero, vec3.zero)
        
        return BoundBox(vec3(*vmin), vec3(*vmax))

    @property
    def fov(self):
        return np.deg2rad(self.lens.get_fov())

    def get_screen_ray(self, x: float = 0, y: float = 0) -> Optional[ray]:
        """Given a screen coordinate with (0,0) in center and (-1,-1) bottom left, return projected ray."""
        near = LPoint3f()
        far = LPoint3f()

        if self.lens.extrude(LPoint2f(x, y), near, far):
            return ray(vec3(*near), vec3(*(far - near)))
        else:
            return None

    def get_screen_position(self, pos: vec3) -> Optional[vec3]:
        """Given a position in space, return screen coordinate with (0,0) in center and (-1,-1) bottom left."""
        pt = LPoint2f()

        if self.lens.project(LPoint3f(*pos)):
            return vec3(*pt)
        else:
            return None
