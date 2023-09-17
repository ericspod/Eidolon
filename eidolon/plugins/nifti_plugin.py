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

import nibabel as nib
from nibabel.nifti1 import unit_codes

from eidolon.mathdef import vec3, rotator

import numpy as np

__all__ = ["get_nifti_transform"]


def get_nifti_transform(img):
    hdr = img.header
    pixdim = hdr["pixdim"]
    xyzt_units = hdr["xyzt_units"]
    x = float(hdr["qoffset_x"])
    y = float(hdr["qoffset_y"])
    z = float(hdr["qoffset_z"])
    b = float(hdr["quatern_b"])
    c = float(hdr["quatern_c"])
    d = float(hdr["quatern_d"])
    toffset = float(hdr["toffset"])
    interval = float(pixdim[4])

    hdim = hdr["dim"]
    dims = hdim[1 : hdim[0] + 1]

    if interval == 0.0 and len(img.shape) >= 4 and img.shape[3] > 1:
        interval = 1.0

    qfac = float(pixdim[0]) or 1.0
    spacing = vec3(pixdim[1], pixdim[2], qfac * pixdim[3])

    if int(hdr["qform_code"]) > 0:
        position = vec3(x, y, z)
        rot = rotator(-c, b, np.sqrt(max(0, 1.0 - (b * b + c * c + d * d))), -d)
    else:
        affine = img.affine
        position = vec3(*affine[:3, 3])
        rmat = np.asarray(
            [
                affine[0, :3] / spacing.x,
                affine[1, :3] / spacing.y,
                affine[2, :3] / spacing.z,
            ]
        )
        rot = rotator.from_mat3x3(*rmat.flatten().tolist())

    # convert from nifti-space to real space
    # position = position * vec3(-1, -1, 1)
    # rot = rot * rotator.from_axis(vec3.Z, HALFPI)

    xyzunit = xyzt_units & 0x07  # isolate space units with a bitmask of 7
    tunit = xyzt_units & 0x38  # isolate time units with a bitmask of 56

    if tunit == 0:  # if no tunit provided, try to guess
        if interval < 1.0:
            tunit = unit_codes["sec"]
        elif interval > 1000.0:
            tunit = unit_codes["usec"]

    # convert to millimeters
    if xyzunit == unit_codes["meter"]:
        position *= 1000.0
        spacing *= 1000.0
    elif xyzunit == unit_codes["micron"]:
        position /= 1000.0
        spacing /= 1000.0

    # convert to milliseconds
    if tunit == unit_codes["sec"]:
        toffset *= 1000.0
        interval *= 1000.0
    elif tunit == unit_codes["usec"]:
        toffset /= 1000.0
        interval /= 1000.0

    return position, rot, spacing, toffset, interval, dims
