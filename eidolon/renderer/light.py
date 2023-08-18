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
from typing import Optional, Tuple, Union

from panda3d.core import AmbientLight, DirectionalLight, NodePath, PointLight, Spotlight, VBase4F

from ..mathdef import vec3
from .camera import OffscreenCamera

__all__ = ["LightType", "Light"]


class LightType(Enum):
    AMBIENT = 1
    DIRECTIONAL = 2
    SPOTLIGHT = 3
    POINT = 4


class Light:
    def __init__(self, name: str, ltype: LightType, color: Union[VBase4F, Tuple[float, ...]], attenuation=(1, 0, 1)):
        self.ltype = ltype

        if ltype == LightType.AMBIENT:
            self._light = AmbientLight(name)
        elif ltype == LightType.DIRECTIONAL:
            self._light = DirectionalLight(name)
        elif ltype == LightType.SPOTLIGHT:
            self._light = Spotlight(name)
            self._light.attenuation = attenuation
        elif ltype == LightType.POINT:
            self._light = PointLight(name)
            self._light.attenuation = attenuation

        self._light.set_color(VBase4F(*color))
        self.nodepath = NodePath(self._light)
        self._node_attached = False

    def attach(self, camera: OffscreenCamera, attach_node=False):
        self._node_attached = attach_node
        if self._node_attached:
            self.nodepath.reparent_to(camera.camera)

        camera.nodepath.set_light(self.nodepath)

    def detach(self, camera: OffscreenCamera):
        if self._node_attached:
            self.nodepath.detach_node()

        camera.nodepath.clear_light(self.nodepath)
