import importlib.resources as pkg_resources
import sys


def _get_module(submodule=None):
    mname = __name__ + ("" if submodule is None else f".{submodule}")
    return mname
    # __import__(mname)
    # return sys.modules[mname]


def list_resources(submodule=None):
    """List resources in the root or `submodule` module."""
    rmod = _get_module(submodule)
    return list(pkg_resources.contents(rmod))


def has_resource(filename, submodule=None):
    """Returns True if `filename` is a resource in the root or `submodule` module."""
    rmod = _get_module(submodule)
    return pkg_resources.is_resource(rmod, filename)


def read_text(filename, submodule=None):
    """Returns the text of `filename` in the root or `submodule` module."""
    rmod = _get_module(submodule)
    return pkg_resources.read_text(rmod, filename)


def read_binary(filename, submodule=None):
    """Returns the binary data of `filename` in the root or `submodule` module."""
    rmod = _get_module(submodule)
    return pkg_resources.read_binary(rmod, filename)
