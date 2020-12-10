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

from .event_dispatcher import *
# from .misc import *
from .platform import *

from time import perf_counter
from functools import wraps


def timing(func):
    """
    This simple timing function decorator prints to stdout/logfile (it uses printFlush) how many seconds a call to the
    original function took to execute, as well as the name before and after the call.
    """

    @wraps(func)
    def _wrapper(*args, **kwargs):
        print(func.__name__, flush=True)
        start = perf_counter()
        res = func(*args, **kwargs)
        end = perf_counter()
        print(func.__name__, 'dT (s) =', (end - start), flush=True)
        return res

    return _wrapper
