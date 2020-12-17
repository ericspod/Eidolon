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
import numpy as np

from panda3d.core import Texture

from .figure import Figure
from .utils import create_simple_geom, create_texture_np
from ..mathdef import vec3, BoundBox, generate_plane, generate_cube
from .camera import OffscreenCamera

__all__ = ["ImagePlaneFigure", "ImageVolumeFigure"]


class ImagePlaneFigure(Figure):
    def __init__(self, name: str, image: np.ndarray, is_3d: bool = False, t_format=None, f_format=None):
        self.texture: Texture = create_texture_np(image, is_3d, t_format, f_format)
        self.width: int = image.shape[0]
        self.height: int = image.shape[1]
        self.depth: int = image.shape[2] if (image.ndim == 4 or is_3d) else 1
        self.selected_planes: List[bool] = [True] * self.depth

        geoms = self._create_planes()

        super().__init__(name, *geoms)

        self.set_texture(self.texture)

    def _create_planes(self):
        verts, inds, xis = generate_plane(1)
        verts = [v + vec3(0.5, 0.5, 0) for v in verts]

        geoms = []

        for d in range(self.depth):
            if self.selected_planes[d]:
                addxi = vec3(0, 0, d / (self.depth - 1) if self.depth > 1 else 0)
                planeverts = [v + addxi for v in verts]
                planexis = [x + addxi for x in xis]

                geom = create_simple_geom(planeverts, inds, uvwcoords=planexis)
                geoms.append(geom)

        return geoms

    def attach(self, camera: OffscreenCamera):
        super().attach(camera)
        self.set_texture(self.texture)

    def set_selected_planes(self, selected_planes: List[bool]):
        if len(selected_planes) == len(self.selected_planes):
            self.selected_planes = list(selected_planes)
            geoms = self._create_planes()
            self.node.remove_all_geoms()
            for geom in geoms:
                self.add_geom(geom)

            self.set_texture(self.texture)


class ImageVolumeFigure(Figure):
    def __init__(self, name: str, image: np.ndarray, num_planes: int = 100, t_format=None, f_format=None):
        self.texture: Texture = create_texture_np(image, True, t_format, f_format)
        self.width: int = image.shape[0]
        self.height: int = image.shape[1]
        self.depth: int = image.shape[2]
        self.num_planes: int = num_planes

        # verts, _, inds, xis = generate_cube(1)
        # verts = [v + vec3.one * 0.5 for v in verts]
        #
        # geom = create_simple_geom(verts, inds, uvwcoords=xis)

        geom = create_simple_geom([vec3.one * 0.5] * self.num_planes)

        super().__init__(name, geom)

        self.set_texture(self.texture)

    def attach(self, camera: OffscreenCamera):
        super().attach(camera)
        self.set_texture(self.texture)

    def aabb(self):
        return BoundBox(vec3.zero, vec3.one) * self.get_transform()

    def corners(self):
        t = self.get_transform()
        return vec3.zero * t, vec3.one * t
