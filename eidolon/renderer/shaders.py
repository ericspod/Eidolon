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

from panda3d.core import Shader

import eidolon.resources as res

__all__ = ["make_shader_from_prefix", "get_default_image_volume"]


def read_shader(filename):
    if res.has_resource(filename, "shaders"):
        return res.read_text(filename, "shaders")

    return None


def make_shader_from_prefix(prefix):
    vert = read_shader(f"{prefix}.vert") or ""
    geom = read_shader(f"{prefix}.geom") or ""
    frag = read_shader(f"{prefix}.frag") or ""

    if not vert and not geom and not frag:
        raise ValueError(f"Shader with prefix {prefix} not found")

    return Shader.make(Shader.SL_GLSL, vert, frag, geom)


def get_default_image_volume():
    return make_shader_from_prefix("image_volume")
