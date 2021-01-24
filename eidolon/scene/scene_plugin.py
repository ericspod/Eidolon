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

from typing import List, Union, NamedTuple, Callable

from .scene_object import ReprType, SceneObject, SceneObjectRepr
from ..utils import split_path_ext, Namespace
from ..ui import IconName
from ..mathdef import calculate_tri_mesh

class MeshAlgorithmDesc(NamedTuple):
    calc_func:Callable=None
    

class ReprMeshAlgorithm(Namespace):
    TriMesh=(calculate_tri_mesh,)


class ScenePlugin:
    def __init__(self, name: str):
        self.plugid: int = -1
        self.name: str = name
        self.mgr = None
        self.win = None
        self.file_exts: List[str] = []

    def init(self, plugid: int, mgr):
        """Called when the manager is being initialized."""
        self.plugid = plugid
        self.win = mgr.win
        self.mgr = mgr

    def cleanup(self):
        """Called when shutting down, use this to clear and close resources."""
        pass

    def get_icon(self, obj) -> str:
        """Returns the icon name for `obj` (which will likely be a member of IconName), or None for the default."""
        return IconName.Default

    def get_help(self) -> str:
        """Return a help text block."""
        return ""

    def get_menu(self, obj):
        """
        Returns the menu structure for `obj` and the callback for when an item is clicked, by default this is
        self._object_menu_item. The menu structure is a list whose first element is the menu title, followed by values
        satisfying create_menu(). The callback take two arguments, the object associated with the menu and the text of
        the menu item clicked.
        """
        return None, self._object_menu_item

    def _object_menu_item(self, obj: Union[SceneObject, SceneObjectRepr], item: str):
        """Callback to react to a menu item with value `item` being selected for object `obj`."""
        pass

    def get_repr_types(self, obj: SceneObject) -> List[str]:
        """Return the ReprType identifiers for the valid representations of this object."""
        return []

    def accept_file(self, filename: str) -> bool:
        """Returns True if this plugin can load or save to the given file."""
        ext = split_path_ext(filename, True)[2]
        return ext in self.file_exts

    def load_object(self, filename: str, name: str = None, **kwargs) -> SceneObject:
        pass

    def save_object(self, obj: SceneObject, filename: str, overwrite: bool = False, set_filename: bool = True,
                    **kwargs):
        pass

    def remove_object(self, obj: SceneObject):
        """This should be called if another plugin takes responsibility for `obj' away from the current one."""
        assert obj.plugin == self


class MeshScenePlugin(ScenePlugin):
    def get_icon(self, obj) -> str:
        return IconName.Mesh

class ImageScenePlugin(ScenePlugin):
    def get_icon(self, obj) -> str:
        return IconName.Image