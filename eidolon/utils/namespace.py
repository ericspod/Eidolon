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

import inspect
from types import MethodType

__all__ = ["Namespace","NamespaceMeta"]


class NamespaceMeta(type):
    def __new__(mcs, cls, bases, classdict):
        ns_dict = {}

        for k, v in list(classdict.items()):
            if k[0] != "_" and not inspect.ismethod(v) and not isinstance(v,classmethod):
                ns_dict[k] = v
                del classdict[k]

        ns_class = super().__new__(mcs, cls, bases, classdict)

        # need a work-around to do ns_class.ns_dict = ns_dict
        type.__setattr__(ns_class, "ns_dict", ns_dict)

        return ns_class

    def __contains__(cls, member):
        return member in cls.ns_dict

    def __getitem__(cls, name):
        if name in cls.ns_dict:
            return cls.__getattr__(name)
        else:
            raise ValueError(f"Value {name} not found in namespace")

    def __getattr__(cls, name):
        if name in cls.ns_dict:
            return cls.ns_dict[name]
        elif name[0] == '_' and name[1:] in cls.ns_dict:
            return name[1:]
        else:
            return super().__getattribute__(name)

    def __setattr__(cls, key, value):
        if key not in cls.ns_dict and hasattr(cls, key):
            super().__setattribute__(key, value)
        elif key[0] == "_":
            raise ValueError("Cannot add namespace member starting with _")

        cls.ns_dict[key] = value

    def __iter__(cls):
        yield from cls.ns_dict.items()

    def append(cls, key, value):
        if key in cls.ns_dict:
            raise ValueError(f"Key '{key}' already present in namespace")

        cls.ns_dict[key] = value

    def __len__(cls):
        return len(cls.ns_dict)


class Namespace(metaclass=NamespaceMeta):
    pass
