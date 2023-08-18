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

import sys
from contextlib import contextmanager
from functools import wraps
from time import perf_counter

__all__ = ["timing", "timing_block", "cached_property"]


@contextmanager
def timing_block(name: str, stream=sys.stdout):
    """Prints `name` when the context enters, and context runtime with the name when it exits, to `stream`."""
    print(name, flush=True, file=stream)
    start = perf_counter()
    yield
    end = perf_counter()
    print(name, "dT (s) =", end - start, flush=True, file=stream)


def timing(func, name: str = None, stream=sys.stdout):
    """Prints the runtime for each call to the decorated callable `func` to `stream`."""
    name = name or func.__name__

    @wraps(func)
    def _wrapper(*args, **kwargs):
        with timing_block(name, stream):
            return func(*args, **kwargs)

    return _wrapper


def cached_property(meth):
    """Caching version of the property decorator for methods only, stores returned value as a member of self."""
    cache_name = meth.__name__ + "__cache__"

    @property
    @wraps(meth)
    def _cached_property(self, *args, **kwargs):
        if not hasattr(self, cache_name):
            value = meth(self, *args, **kwargs)
            setattr(self, cache_name, value)

        return getattr(self, cache_name)

    return _cached_property
