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

import contextlib
import re
from io import StringIO

from PyQt5 import QtCore, uic

from eidolon import resources

__all__ = ["load_ui", "load_res_layout", "add_search_path", "rename_ui_paths"]

# restag = re.compile("<resources>.*</resources>", flags=re.DOTALL)  # matches the resource tags in the ui files

UI_REPLACE_PATTERNS = [
    ("<resources>.*</resources>", ""),  # remove the resources section from the XML
    (">\\:/([^/]+)/([^<]+)<", ">\\1:\\2<"),  # replace every ':/path/filename.ext' with 'path:filename.ext' in XML
    ("\(\\:/([^/]+)/([^)]+)\)", "(\\1:\\2)")  # replace every ':/path/filename.ext' with 'path:filename.ext' in CSS
]


def rename_ui_paths(uistr):
    for p, r in UI_REPLACE_PATTERNS:
        uistr = re.sub(p, r, uistr, flags=re.DOTALL)

    return uistr

def load_ui(xmlstr,from_imports=False,import_from='.'):
    """Loads the given XML ui file data and returns the created type."""
    # s = re.sub(restag, "", xmlstr)  # get rid of the resources section in the XML
    xmlstr=rename_ui_paths(xmlstr)

    # create a local type definition
    uiclass, _ = uic.loadUiType(StringIO(xmlstr),from_imports=from_imports,import_from=import_from)
    return uiclass


def load_res_layout(filename,from_imports=False,import_from='.'):
    if not resources.has_resource(filename, "ui"):
        raise ValueError(f"Cannot find UI layout with name {filename}")

    return load_ui(resources.read_text(filename, "ui"),from_imports=from_imports,import_from=import_from)


def add_search_path(name, submodule):
    QtCore.QDir.addSearchPath(name, resources.get_resource_path(submodule))
