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
import sys
import platform

__all__=["is_interactive"]

is_darwin = platform.system().lower() == 'darwin'
is_windows = platform.system().lower() == 'windows'
is_linux = platform.system().lower() == 'linux'


def is_interactive() -> bool:
    # try:
    #     import __main__
    #     return not hasattr(__main__, "__file__")
    # except ImportError:
    #     return False

    return hasattr(sys,"ps1")


def add_path_variable(varname: str, path: str, append=True):
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
