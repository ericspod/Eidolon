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


try:
    from numba import jit as _jit, prange, set_num_threads
    from functools import partial

    jit = partial(_jit, nopython=True, cache=True, nogil=True)
    has_numba = True

except ImportError:
    import warnings

    warnings.warn("Numba not found, code will not be compiled")


    def jit(func=None,*_,**__):
        if func is not None and callable(func):
            return func
        else:
            return lambda f:f


    def set_num_threads(n):
        pass


    prange = range
    has_numba = False

__all__ = ["has_numba", "jit", "prange", "set_num_threads"]
