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
    GeomVertexArrayFormat,
    GeomVertexData,
    GeomVertexWriter,
    LVector3,
    GeomTriangles,
    Texture
)

vaformat = GeomVertexArrayFormat()
vaformat.addColumn("vertex", 3, Geom.NTFloat32, Geom.C_point)
vaformat.addColumn("normal", 3, Geom.NTFloat32, Geom.C_normal)
vaformat.addColumn("color", 4, Geom.NTFloat32, Geom.C_color)
vaformat.addColumn("texcoord", 3, Geom.NTFloat32, Geom.C_texcoord)

default_vformat = GeomVertexFormat()
default_vformat.addArray(vaformat)
default_vformat = GeomVertexFormat.registerFormat(default_vformat)


def create_simple_geom(vertices, indices, norms=None, colors=None, uvwcoords=None, vformat=None):
    norms = norms or [vec3.Z] * len(vertices)
    colors = colors or [(1, 1, 1, 1)] * len(vertices)
    uvwcoords = uvwcoords or [(0, 0, 0)] * len(vertices)
    vformat = vformat or default_vformat

    vdata = GeomVertexData("square", vformat, Geom.UHDynamic)

    vertex = GeomVertexWriter(vdata, "vertex")
    normal = GeomVertexWriter(vdata, "normal")
    color = GeomVertexWriter(vdata, "color")
    texcoord = GeomVertexWriter(vdata, "texcoord")

    for i in range(len(vertices)):
        vertex.addData3f(*vertices[i])
        normal.addData3f(LVector3(*norms[i]).normalized())
        color.addData4f(*colors[i])
        texcoord.addData3f(*uvwcoords[i])

    tris = GeomTriangles(Geom.UHDynamic)

    for i in range(len(indices)):
        tris.addVertices(*indices[i])

    geom = Geom(vdata)
    geom.addPrimitive(tris)
    return geom


def create_texture_np(array, is_3d: bool = False, t_format=None, f_format=None):
    tex = Texture()
    shape = array.shape
    components = 1

    tex.setWrapU(Texture.WM_clamp)
    tex.setWrapV(Texture.WM_clamp)
    # tex.set_minfilter(Texture.FT_nearest)
    # tex.set_magfilter(Texture.FT_nearest)

    # if the array has multiple components
    if (is_3d and array.ndim == 4) or (not is_3d and array.ndim == 3):
        *shape, components = array.shape

    w, h, *d = shape

    if t_format is None:
        if array.dtype == np.uint8:
            t_format = Texture.T_unsigned_byte
        elif array.dtype == np.float32:
            t_format = Texture.T_float
        elif array.dtype == np.int32:
            t_format = Texture.T_int
        else:
            raise ValueError("Array format must be uint8, float32, or int32")

    if f_format is None:
        if components == 1:
            f_format = Texture.F_luminance
        elif components == 2:
            f_format = Texture.F_luminance_alpha
        elif components == 3:
            f_format = Texture.F_rgb
        elif components == 4:
            f_format = Texture.F_rgba
        else:
            raise ValueError("Array must have 2, 3, or 4 dimensions")

    if is_3d:
        tex.setup_3d_texture(w, h, d[0], t_format, f_format)
        tex.setWrapW(Texture.WM_clamp)
        trans_dims = [2, 1, 0] if array.ndim == 3 else [2, 1, 0, 3]
    else:
        tex.setup_2d_texture(w, h, t_format, f_format)
        trans_dims = [1, 0] if array.ndim == 2 else [1, 0, 2]

    array = array.transpose(*trans_dims)

    # convert to panda3d's channel order
    if components == 3:
        array = array[..., [2, 1, 0]]
    elif components == 4:
        array = array[..., [2, 1, 0, 3]]

    buffer = array.tobytes()

    # if components in (3, 4):  # RGB or RGBA images
    #     tex.set_ram_image_as(buffer, "RGBA" if components == 4 else "RGB")
    # else:
    #     tex.set_ram_image(buffer)

    tex.set_ram_image(buffer)

    return tex
