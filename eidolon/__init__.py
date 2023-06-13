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
"""
Eidolon is the experimental medical imaging visualization framework.
"""

import os
import sys
# import glob
# import ctypes

# from .utils.platform import is_windows, is_linux, add_path_variable

from ._version import __version__

_scriptdir = os.path.dirname(os.path.abspath(__file__))

# the application directory is given by pyinstaller in _MEIPASS, if not present use the directory one level up
__appdir__ = getattr(sys, '_MEIPASS', os.path.abspath(_scriptdir + '/..'))

# environment variable names
APPDIRVAR = "APPDIR"  # path to the application's directory, default __appdir__
APPDATADIRVAR = "APPDATADIR"  # path to app data directory, default ~/.eidolon
CONFIGFILEVAR = "CONFIGFILE"  # path to config file, default config.yaml
LOGFILEVAR = "LOGFILE" # path to log file, default eidolon.log

# LIBSDIR = "EidolonLibs"  # directory name containing the application's libraries
APPDIR = os.environ.get(APPDIRVAR, __appdir__)
APPDATADIR = os.environ.get(APPDATADIRVAR, "~/.eidolon")
CONFIGFILE = os.environ.get(CONFIGFILEVAR, "config.yaml")  # config file name
LOGFILE = os.environ.get(LOGFILEVAR, "eidolon.log")  # config file name

# _scriptdir = os.path.dirname(os.path.abspath(__file__))
#
# # the application directory is given by pyinstaller in _MEIPASS, if not present use the directory one level up
# __appdir__ = getattr(sys, '_MEIPASS', os.path.abspath(_scriptdir + '/..'))
#
# # library directory
# __libdir__ = os.path.join(__appdir__, 'eidolon', LIBSDIR)

# if is_windows:
#     # add the library directory to PATH so that DLLs can be loaded when the renderer is imported
#     add_path_variable('PATH', os.path.abspath(os.path.join(__libdir__, 'win64_mingw', 'bin')))
# elif is_linux:
#     # load all linux libraries so that LD_LIBRARY_PATH doesn't need to be set
#     for lib in glob.glob(os.path.join(__libdir__, 'linux', 'lib', '*.so*')):  # will attempt to load libraries twice
#         try:
#             _ = ctypes.cdll.LoadLibrary(lib)
#         except OSError:
#             pass
