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
import os
import glob
import re
import contextlib
from io import StringIO

from PyQt5 import QtGui, QtCore, QtWidgets, uic
from PyQt5.QtCore import Qt

# from . import Resources_rc5


module = sys.modules[__name__]  # this module
restag = re.compile('<resources>.*</resources>', flags=re.DOTALL)  # matches the resource tags in the ui files
# list all .ui files, if there are none then attempt to load from a resource script file
uifiles = glob.glob(os.path.join(os.path.dirname(__file__), '*.ui'))


def load_ui(xmlstr):
    """Load the given XML ui file data and store the created type as a member of this module."""
    s = re.sub(restag, '', xmlstr)  # get rid of the resources section in the XML
    uiclass, _ = uic.loadUiType(StringIO(s))  # create a local type definition
    setattr(module, uiclass.__name__, uiclass)  # store as module member


if len(uifiles) != 0:
    # load the class from each ui file and store it as a member of this module
    for ui in uifiles:
        load_ui(open(ui).read())
else:
    # load the resource module containing the .ui files
    from . import UI_rc5

    # iterate over every file in the layout section of the resources and load them into this module
    it = QtCore.QDirIterator(':/layout')
    while it.hasNext():
        with contextlib.closing(QtCore.QFile(it.next())) as layout:
            if layout.open(QtCore.QFile.ReadOnly):
                xfile = layout.readAll()
                load_ui(bytes(xfile).decode('utf-8'))
