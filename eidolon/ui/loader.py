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

import re
import contextlib
from io import StringIO

from PyQt5 import QtCore, uic

from eidolon import resources

__all__ = ["load_ui", "load_res_layout"]

restag = re.compile('<resources>.*</resources>', flags=re.DOTALL)  # matches the resource tags in the ui files

layouts_section = ":/layouts"


def load_ui(xmlstr):
    """Loads the given XML ui file data and returns the created type."""
    s = re.sub(restag, '', xmlstr)  # get rid of the resources section in the XML
    uiclass, _ = uic.loadUiType(StringIO(s))  # create a local type definition
    return uiclass


def load_res_layout(filename):
    if not resources.has_resource(filename, "ui"):
      raise ValueError(f"Cannot find UI layout with name {filename}")

    return load_ui(resources.read_text(filename, "ui"))  

# def load_rc_layout(filename):
#     layout = load_rc_file(filename, layouts_section)

#     if layout:
#         return load_ui(layout.decode("utf-8"))

#     raise ValueError(f"Cannot find UI layout with name {filename}")


# def load_rc_file(filename, section):
#     it = QtCore.QDirIterator(section)

#     while it.hasNext():
#         name = it.next()
#         if filename in name:
#             with contextlib.closing(QtCore.QFile(name)) as qfile:
#                 if qfile.open(QtCore.QFile.ReadOnly):
#                     xfile = qfile.readAll()
#                     return bytes(xfile)
#                 else:
#                     raise ValueError(f"Unable to open {name}")

#     return None
