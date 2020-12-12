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
from typing import Optional

from PyQt5 import QtWidgets

from ..utils import is_interactive

__all__ = ["qtrunner"]


def qtrunner(app: QtWidgets.QApplication, do_exit: Optional[bool] = None):
    status = app.exec_()

    if do_exit is True or (do_exit is None and not is_interactive()):
        sys.exit(status)
