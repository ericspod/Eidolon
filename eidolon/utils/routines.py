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

import os
import operator
import itertools
from functools import reduce
from .platform import is_windows

__all__ = ["process_exists", "get_win_drives", "get_username", "add_path_variable", "fcomp", "first", "last",
           "list_sum", "zip_with", "mulsum", "successive", "group"]


def process_exists(pid):
    """
    Returns true if the process identified by `pid' is running and active, false if it doesn't exist or has crashed.
    """
    if is_windows:  # adapted from http://www.madebuild.org/blog/?p=30
        _PROCESS_QUERY_INFORMATION = 1024  # OpenProcess requires this access rights specifier
        _STILL_ACTIVE = 259  # GetExitCodeProcess uses a special exit code to indicate the process is still running

        import ctypes
        import ctypes.wintypes
        kernel32 = ctypes.windll.kernel32

        handle = kernel32.OpenProcess(_PROCESS_QUERY_INFORMATION, 0, pid)
        if handle == 0:
            return False

        # If the process exited recently, a handle may still exist for the pid. So, check if we can get the exit code.
        exitcode = ctypes.wintypes.DWORD()
        result = kernel32.GetExitCodeProcess(handle, ctypes.byref(exitcode))  # returns 0 if failed
        kernel32.CloseHandle(handle)

        # See if we couldn't get the exit code or the exit code indicates that the process is still running.
        return result != 0 and exitcode.value == _STILL_ACTIVE
    else:  # non-Windows platforms, kill is supported in Windows but doesn't detect crashed processes correctly
        try:
            os.kill(pid, 0)  # signal 0 does nothing but still raises an exception if the process doesn't exist
            return True
        except OSError:
            return False


def get_win_drives():
    """Returns available Windows drive letters."""
    import win32api
    d = win32api.GetLogicalDriveStrings()
    return [dd[0] for dd in d.split('\x00') if dd]


def get_username():
    """Returns the username in a portable and secure way which works with 'su' and non-terminal processes."""
    if is_windows:
        import win32api
        import win32con
        hostuname = win32api.GetUserNameEx(win32con.NameSamCompatible)
        return str(hostuname.split('\\')[-1])
    else:
        import pwd
        return pwd.getpwuid(os.getuid()).pw_name


def add_path_variable(varname, path, append=True):
    """
    Add the string `path' to the environment variable `varname' by appending (if `append` is True) or prepending `path'
    using os.pathsep as the separator. This assumes `varname' is a path variable like PATH. Blank paths present in the
    original variable are moved to the end to prevent consecutive os.pathsep characters appearing in the variable. If
    `varname' does not name a variable with text it will be set to `path'.
    """
    var = os.environ.get(varname, '').strip()

    if var:  # if the variable exists and has text
        paths = [p.strip() for p in var.split(os.pathsep)]  # split by the separator and strip whitespace just in case
        paths.insert(len(paths) if append else 0, path)  # append or prepend `path'
        if '' in paths:  # need to move the blank path to the end to prevent :: from appearing in the variable
            paths = list(filter(bool, paths)) + ['']
    else:
        paths = [path]  # variable is new so only text is `path'

    os.environ[varname] = os.pathsep.join(paths)


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
