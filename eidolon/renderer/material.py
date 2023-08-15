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

from typing import Optional, Tuple, List


from panda3d.core import Texture, TextureStage, Shader, Material as PMaterial

__all__ = ["Material", "MAIN_TEX_NAME", "SPECTRUM_TEX_NAME"]

color = Tuple[float, float, float, float]

MAIN_TEX_NAME = "tex"
SPECTRUM_TEX_NAME = "spec"


class Material:
    def __init__(
        self,
        name: str,
        texture: Optional[Texture] = None,
        shader: Optional[Shader] = None,
        diffuse: color = (1, 1, 1, 1),
        emissive: color = (0, 0, 0, 0),
        specular: color = (0, 0, 0, 0),
        # refractive_index: float = 1,
        shininess: float = 0.0,
    ):
        self._name: str = name
        self.texture: Optional[Texture] = texture
        self.shader: Optional[Shader] = shader
        self.diffuse: color = diffuse
        self.emissive: color = emissive
        self.specular: color = specular
        # self.refractive_index: float = refractive_index
        self.shininess: float = shininess

        # self._alpha_curve: List[Tuple[float, float]] = []
        # self._spectrum: List[color] = []
        # self._spectrum_tex: Optional[Texture] = None

        self.pmaterial = PMaterial()

    @property
    def name(self):
        return self._name

    def get_material_obj(self) -> PMaterial:
        self.pmaterial.set_diffuse(self.diffuse)
        self.pmaterial.set_specular(self.specular)
        self.pmaterial.set_emission(self.emissive)
        # self.pmaterial.set_refractive_index(self.refractive_index)
        self.pmaterial.set_shininess(self.shininess)
        return self.pmaterial

    # def get_texture_stages(self):
    #     stages = []

    #     if self.texture is not None:
    #         ts = TextureStage(MAIN_TEX_NAME)
    #         ts.set_sort(0)
    #         stages.append((ts, self.texture))

    #     if self._spectrum_tex is not None:
    #         ts = TextureStage(SPECTRUM_TEX_NAME)
    #         ts.set_sort(1)
    #         stages.append((ts, self._spectrum_tex))

    #     return stages
