

import importlib.resources as pkg_resources
import sys

def _get_module(submodule=None):
    mname=__name__+("" if submodule is None else f".{submodule}")
    __import__(mname)
    return sys.modules[mname]

def read_text(filename,submodule=None):
    current_module=_get_module(submodule)
    return pkg_resources.read_text(current_module, filename)
