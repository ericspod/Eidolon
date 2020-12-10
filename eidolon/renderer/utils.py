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

import numpy as np

from ..mathdef.mathtypes import vec3, transform

__all__ = ["create_simple_geom", "create_texture_np"]

from panda3d.core import (
    Geom,
    GeomVertexFormat,
    GeomVertexData,
    GeomVertexWriter,
    LVector3,
    GeomTriangles,
    Texture
)


def create_simple_geom(vertices, indices, norms=None, colors=None, uvcoords=None):
    norms = norms or [vec3.Z] * len(vertices)
    colors = colors or [(1, 1, 1, 1)] * len(vertices)
    uvcoords = uvcoords or [(0, 0)] * len(vertices)

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


def create_texture_np(array, is_3d=False, t_format=None, f_format=None):
    tex = Texture()
    shape = array.shape
    components = 1

    # if the array has multiple components
    if (is_3d and array.ndim == 4) or (not is_3d and array.ndim == 3):
        *shape, components = array.shape

    h,w,*d=shape

    if t_format is None:
        if array.dtype == np.uint8:
            t_format = Texture.T_unsigned_byte
        elif array.dtype == np.float32:
            t_format = Texture.T_float
        elif array.dtype == np.int32:
            t_format = Texture.T_int

    if f_format is None:
        if components == 1:
            f_format = Texture.F_luminance
        elif components == 2:
            f_format = Texture.F_luminance_alpha
        elif components == 3:
            f_format = Texture.F_rgb
        elif components == 4:
            f_format = Texture.F_rgba

    if is_3d:
        tex.setup_3d_texture(w,h,*d, t_format, f_format)
        tex.setWrapW(Texture.WM_clamp)
    else:
        tex.setup_2d_texture(w,h,*d, t_format, f_format)

    tex.setWrapU(Texture.WM_clamp)
    tex.setWrapV(Texture.WM_clamp)
    tex.set_ram_image(array.tobytes())

    return tex
