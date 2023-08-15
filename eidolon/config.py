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
from pathlib import Path
from io import StringIO
from typing import Optional
from collections.abc import Mapping
import yaml

from .utils import PlatformName, Namespace

__all__ = ["load_config", "load_config_file", "save_config_file", "ConfigVarNames"]

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


class ConfigVarNames(Namespace):
    vsync = (True, "Vertical screen sync, possible values: True (default), False")
    logfile = ("eidolon.log", "Log file name in Eidolon's users data directory, default is eidolon.log")
    maxprocs = (8, "Maximum number of processors to use when computing datasets/representations")
    winsize = ([1200, 800], "Default window size at start-up (actual size may be larger to fit UI components)")
    uistyle = ("plastique", "Qt style to base the UI look-and-feel on")
    stylesheet = ("DefaultUIStyle.css", "UI stylesheet, must be path to external file or name of resource file")
    camerazlock = (True, "Sets the initial state of the camera's Z-axis locking: True (default), False")
    preloadscripts = ("", "Comma-separated list of scripts to load at runtime before any specified on the command line")
    userappdir = ("~/.eidolon", "Location of the per-user data directory to create at startup if it doesn't exist")
    consolelogfile = ("console.log", "Console log filename, to be stored in userappdir")
    consoleloglen = (10000, "How many lines of console logs to store in the log file")
    usejupyter = (True, "Try to use Jupyter console widget instead of built-in console widget: True (default), False")


DEFAULT_CONFIG = "all:\n" + "".join([f"  # {v[1]}\n  {k}: {v[0]}\n" for k,v in ConfigVarNames])


def update_dict(orig, updates):
    orig = dict(orig)
    for k, v in updates.items():
        if isinstance(v, Mapping):
            orig[k] = update_dict(orig.get(k, {}), v)
        else:
            orig[k] = v

    return orig


def load_config(configfile: Optional[str] = None) -> dict:
    conf = yaml.safe_load(StringIO(DEFAULT_CONFIG))
    datadir = None

    # raise an error if `configfile` is given but not a file, otherwise `configfile` is set to that in the app data dir
    if configfile is not None:
        if not Path(configfile).is_file():
            raise ValueError(f"Cannot load file '{configfile}'")
    else:
        datadir = Path(APPDATADIR).expanduser()
        configfile = datadir / CONFIGFILE

    # if the config file is present load it and replace the current values with whatever is loaded
    if configfile.is_file():
        saved_conf = load_config_file(str(configfile))
        conf = update_dict(conf, saved_conf)
    else:  # create the config file and app data dir if necessary
        create_appdata_dir(datadir)

    # select the "all" section from the config
    all_conf = dict(conf.get("all", {}))

    # replace values in config with those specific to the current platform
    for pn in PlatformName:
        platform_name, is_platform = pn.value
        if is_platform:
            all_conf = update_dict(all_conf, conf.get(platform_name, {}))

    return all_conf


def load_config_file(filename):
    with open(filename) as o:
        return yaml.safe_load(o)


def save_config_file(conf, filename):
    with open(filename, "w") as o:
        yaml.safe_dump(conf, o)


def create_appdata_dir(dirname):
    p = Path(dirname).expanduser()
    p.mkdir(parents=True, exist_ok=True)
    conf = p / CONFIGFILE

    if not conf.is_file():
        with open(conf, "w") as o:
            o.write(DEFAULT_CONFIG)
