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

__all__ = ["Namespace", "NamespaceMeta"]


class NamespaceMeta(type):
    def __new__(mcs, cls, bases, classdict):
        ns_dict = {}

        for k, v in list(classdict.items()):
            if k[0] != "_" and not inspect.ismethod(v) and not isinstance(v, classmethod):
                ns_dict[k] = v
                classdict["_" + k] = k

        ns_class = super().__new__(mcs, cls, bases, classdict)

        # need a work-around to do ns_class.ns_dict = ns_dict
        type.__setattr__(ns_class, "ns_dict", ns_dict)

        return ns_class

    def __contains__(cls, member):
        return member in cls.ns_dict

    def __iter__(cls):
        yield from cls.ns_dict.items()

    def __len__(cls):
        return len(cls.ns_dict)

    # def __setattr__(cls, key, value):
    #     if hasattr(cls, key) and not hasattr(cls, "_" + key):  # not a namespace member, use inherited setattr
    #         type.__setattr__(cls, key, value)
    #     elif key[0] == "_":
    #         raise ValueError("Cannot add namespace member starting with _")
    #     else:
    #         cls.ns_dict[key] = value
    #         type.__setattr__(cls, key, value)
    #         type.__setattr__(cls, "_" + key, key)

    __getitem__ = type.__getattribute__
    # __setitem__ = __setattr__

    # def append(cls, key, value):
    #     if key in cls.ns_dict:
    #         raise ValueError(f"Key '{key}' already present in namespace")
    #
    #     # NamespaceMeta.__setattr__(cls, key, value)
    #     cls.ns_dict[key] = value
    #     type.__setattr__(cls, key, value)
    #     type.__setattr__(cls, "_" + key, key)

    def __setitem__(cls, key, value):
        if key[0] == "_":
            raise ValueError("Cannot add namespace member starting with _")
        elif key in cls.__dict__ and key not in cls.ns_dict:
            raise ValueError(f"Member {key} already defined")
        else:
            cls.ns_dict[key] = value
            type.__setattr__(cls, key, value)
            type.__setattr__(cls, "_" + key, key)



class Namespace(metaclass=NamespaceMeta):
    """
    A Namespace is a multable sequence of identifiers defined by static class members. Like Enum, a class inheriting
    from Namespace defines a new sequence variables which can be accessed as members, as items with [] syntax, and
    iterated over. Additionally the name of each variable is stored as a separate member with the same name prepended
    with underscore. Namespace classes are meant to be mutable and represent stored resources which plugins or other
    extensions can add to or modify to change system behaviour. To define a set of static constants with a separate type
    definition, use Enum instead.
    """
    pass
