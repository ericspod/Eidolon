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

import itertools
import operator
from functools import reduce
from typing import Iterable

__all__ = ["is_iterable_notstr", "fcomp", "first", "last", "list_sum", "zip_with", "mulsum", "successive", "group"]


def is_iterable_notstr(val) -> bool:
    """Returns True if `val` is an iterable but not a string type (str or bytes)."""
    return isinstance(val, Iterable) and not isinstance(val, (str, bytes))


def fcomp(*funcs):
    """Functional composition operator, fcomp(f0,f1,...,fn) is equivalent to lambda i:f0(f1(...fn(i)...))."""
    return lambda i: reduce(lambda v, f: f(v), reversed(funcs), i)


def first(iterable, default=None):
    """Returns the first item in the given iterable, meaningful mostly with 'for' expressions."""
    for i in iterable:
        return i
    return default


def last(iterable, default=None):
    """Returns the last item in the given iterable, meaningful mostly with 'for' expressions."""
    result = default
    for i in iterable:
        result = i
    return result


def list_sum(lists):
    """Sums the iterable of lists into one long list."""
    return sum(map(list, lists), [])


def zip_with(op, *vals):
    """Starmap `op' to each tuple derived from zipping the iterables in `vals'."""
    return itertools.starmap(op, zip(*vals))


def mulsum(ls, rs):
    """Returns the sum of each element of `ls' multiplied by the equivalent element in `rs'."""
    muls = zip_with(operator.mul, ls, rs)
    return sum(muls, next(muls))  # need to choose an initial value if the first member of muls cannot be added to 0


def successive(iterable, width=2, cyclic=False):
    """
    Yields tuples of `width' values in order from `iterable' starting from the first value, then from the second value,
    etc. If `cyclic' is True then `iterable' is treated as a cycle of values and the last `width' tuples will have
    values starting from the end of the sequence then looping back to the beginning.
    Eg. successive(range(5))        -> (0, 1), (1, 2), (2, 3), (3, 4)
        successive(range(5),3,True) -> (0, 1, 2), (1, 2, 3), (2, 3, 4), (3, 4, 0), (4, 0, 1)
        successive([],2)            -> nil
    """
    assert width > 1

    can_continue = True
    it = iter(iterable)

    try:
        val = [next(it) for _ in range(width)]  # get the first `width' values
    except StopIteration:
        pass  # yield nothing if `iterable' has fewer than `width' values
    else:
        if cyclic:  # if cyclic, make `it' into a chain that sticks `val' (minus its last value) onto the end
            it = itertools.chain(it, iter(val[:-1]))

        while can_continue:
            yield tuple(val)
            try:
                # eventually next() will raise StopIteration if `iterable' is finite and the loop will exit
                val = val[1:] + [next(it)]
            except StopIteration:
                can_continue = False


def group(iterable, width=2):
    """
    Groups successive items from `iterable' into `width' size tuples and yields each sequentially. If the number of
    items in `iterable' isn't a multiple of `width', the last shortened group is discarded.
    Eg. group(range(5))    -> (0,1), (2,3)
        group(range(10))   -> (0, 1), (2, 3), (4, 5), (6, 7), (8, 9)
        group(range(10),3) -> (0, 1, 2), (3, 4, 5), (6, 7, 8)
        group(range(2),3)  -> nil
    """
    assert width > 1

    can_continue = True
    it = iter(iterable)
    rng = tuple(range(width))

    # loops so long as `iterable' has enough values
    while can_continue:
        try:  # try to extract `width' number of values from it, stop if fewer or none are available
            p = [next(it) for _ in rng]  # will raise StopIteration and not hide it behind RuntimeError like tuple()
            yield tuple(p)
        except StopIteration:
            can_continue = False
