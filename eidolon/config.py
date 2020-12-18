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

from pathlib import Path
from io import StringIO
from collections.abc import Mapping
import yaml

from . import CONFIGFILE, APPDATADIR

DEFAULT_CONFIG = """
all:
    # Vertical screen sync, possible values: true (default), false
    vsync: True
    # Log file name in Eidolon's users data directory, default is eidolon.log
    logfile: eidolon.log
    # Maximum number of processors to use when computing datasets/representations
    maxprocs: 8
    # Default window size at start-up (actual size may be larger if necesary to fit UI components)
    winsize: [1200, 800]
    # Qt style to base the UI look-and-feel on
    uistyle: plastique
    # Stylesheet used to define the interface look-and-feel, must be an absolute path or relative to the <app> directory 
    stylesheet: DefaultUIStyle
    # Sets the initial state of the camera's Z-axis locking: true (default), false
    camerazlock: True
    # Comma-separated list of scripts to load at runtime before any others specified on the command line (prefix with ./ to be relative to config file)
    preloadscripts: ""
    # render high quality for every frame by default
    renderhighquality: True
    # location of the per-user application data directory to create at startup if it doesn't exist, This file will be copied there and can be modified for per-user configuration
    userappdir: ~/.eidolon
    # console log filename, to be stored in userappdir
    consolelogfile: console.log
    # how many lines of console logs to store in the log file
    consoleloglen: 10000
    # try to use the Jupyter Qt console widget instead of the built-in console widget: true (default), false
    usejupyter: True
"""


def update_dict(orig, updates):
    orig = dict(orig)
    for k, v in updates.items():
        if isinstance(v, Mapping):
            orig[k] = update_dict(orig.get(k, {}), v)
        else:
            orig[k] = v

    return orig


# def load_config(filename, use_defaults=True):
#     conf = {}
#     if filename:
#         p = Path(filename).expanduser()
#         if p.is_file():
#             conf = load_config_file(str(p))
#
#     if use_defaults:
#         defaults = yaml.safe_load(StringIO(DEFAULT_CONFIG))
#         conf = update_dict(defaults, conf)
#
#     return conf


def load_config(configfile: str = None) -> dict:
    conf = yaml.safe_load(StringIO(DEFAULT_CONFIG))
    datadir = None

    if configfile is not None:
        if not Path(configfile).is_file():
            raise ValueError(f"Cannot load file '{configfile}'")
    else:
        datadir = Path(APPDATADIR).expanduser()
        configfile = datadir / CONFIGFILE

    if configfile.is_file():
        saved_conf = load_config_file(str(configfile))
        conf = update_dict(conf, saved_conf)
    else:
        create_appdata_dir(conf, datadir)

    return conf


def load_config_file(filename):
    with open(filename) as o:
        return yaml.safe_load(o)


def save_config_file(conf, filename):
    with open(filename, 'w') as o:
        yaml.safe_dump(conf, o)


def create_appdata_dir(conf, dirname):
    p = Path(dirname)
    p.mkdir(parents=True, exist_ok=True)
    save_config_file(conf, str(p / CONFIGFILE))
