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

from typing import Any, Callable, List, NamedTuple, Optional, Tuple, Union

from eidolon.mathdef import (
    ElemType,
    Mesh,
    MeshDataValue,
    calculate_tri_mesh,
    calculate_surface_mesh,
    calculate_inverted_tri_mesh,
)
from eidolon.renderer import OffscreenCamera, SimpleFigure
from eidolon.renderer.material import Material
from eidolon.ui import IconName, ObjectProp, ReprProp
from eidolon.ui.property_panels import PropPanelEvent
from eidolon.ui.threadsafe_calls import qtmainthread
from eidolon.utils import Namespace, first, split_path_ext, task_method

from eidolon.scene.mesh_scene_object import MeshSceneObject, MeshSceneObjectRepr
from eidolon.scene.scene_object import ReprType, SceneObject, SceneObjectRepr
from eidolon.utils.event_dispatcher import EventDispatcher
from eidolon.utils.types import color

__all__ = ["MeshAlgorithmDesc", "ReprMeshAlgorithm", "ScenePlugin", "MeshScenePlugin", "ImageScenePlugin"]


class MeshAlgorithmDesc(NamedTuple):
    repr_type: str = ""
    calc_func: Callable = None
    min_dim: int = 0


class ReprMeshAlgorithm(Namespace):
    surfmesh = MeshAlgorithmDesc(ReprType._surface, calculate_surface_mesh, 2)
    trimesh = MeshAlgorithmDesc(ReprType._volume, calculate_tri_mesh, 3)


class ScenePlugin:
    """
    Class for managing interaction and integration for scene objects and extensions to the framework. Plugins should be
    responsible for data IO, managing behaviour of custom object types, handling UI events for these objects, and any
    other controller behaviour which doesn't belong in the SceneManager itself.
    """

    def __init__(self, name: str):
        self.plugid: int = -1
        self.name: str = name
        self.mgr = None
        self.win = None
        self.file_exts: List[str] = []
        self.evt_dispatch = EventDispatcher()

        self.evt_dispatch.add_handler(PropPanelEvent._color_changed, self._repr_color_change)
        self.evt_dispatch.add_handler(PropPanelEvent._alpha_changed, self._repr_alpha_change)

    def init(self, plugid: int, mgr):
        """Called when the manager is being initialized."""
        self.plugid = plugid
        self.win = mgr.win
        self.mgr = mgr

    def cleanup(self):
        """Called when shutting down, use this to clear and close resources."""
        pass

    def update_post_change(self):
        """Update the UI and repaint after a change has occurred in an object."""
        self.mgr.update_ui()
        self.mgr.repaint()


    def get_icon(self, obj) -> str:
        """Returns the icon name for `obj` (which will likely be a member of IconName), or None for the default."""
        return IconName.default

    @qtmainthread
    def get_properties_panel(self, obj: Union[SceneObject, SceneObjectRepr]) -> Optional[Any]:
        """Returns the properties panel if there is any for the given object."""
        if isinstance(obj, SceneObject):
            return ObjectProp(obj, self.evt_dispatch)
        else:
            return ReprProp(obj, self.evt_dispatch)

    def get_help(self) -> str:
        """Return a help text block."""
        return ""

    def get_menu(self, obj) -> Tuple[List[str], Callable]:
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

    def _repr_color_change(self, repr: SceneObjectRepr, component: str, value: Union[float, color]):
        mat = repr.get_material()
        mat.update_colors(**{component: value})
        repr.set_material(mat)
        self.update_post_change()

    def _repr_alpha_change(self, repr: SceneObjectRepr, value: float):
        mat:Material = repr.get_material()
        mat.set_alpha(value)

        repr.set_material(mat)
        self.update_post_change()

    def get_repr_types(self, obj: SceneObject) -> List[str]:
        """Return the ReprType identifiers for the valid representations of this object."""
        return []

    def accept_path(self, loadpath: str) -> bool:
        """Returns True if this plugin can load or save to the given file."""
        ext = split_path_ext(loadpath, True)[2]
        return ext in self.file_exts

    def load_object(self, filename: str, name: str = None, **kwargs) -> SceneObject:
        pass

    def save_object(
        self, obj: SceneObject, filename: str, overwrite: bool = False, set_filename: bool = True, **kwargs
    ):
        pass

    def remove_object(self, obj: SceneObject):
        """This should be called if another plugin takes responsibility for `obj' away from the current one."""
        assert obj.plugin == self

    def get_repr_params(self, obj: SceneObject, reprtype: str):
        """Returns the list of ParamDef objects defining the parameters for the given given representation type."""
        return []

    def create_repr(self, obj: SceneObject, reprtype: str, **kwargs):
        """Create a representation of `obj` of the type `reprtype`."""
        pass

    def attach_repr(self, rep: SceneObjectRepr, camera: OffscreenCamera):
        for fig in rep.figures:
            if not fig.attached_to_camera(camera):
                fig.attach(camera)

        rep.visible = True

    def detach_repr(self, rep: SceneObjectRepr, camera: OffscreenCamera):
        for fig in rep.figures:
            fig.detach(camera)


class MeshScenePlugin(ScenePlugin):
    def get_icon(self, obj) -> str:
        return IconName.mesh

    def get_repr_types(self, obj: MeshSceneObject) -> List[str]:
        spatial_topos = obj.meshes[0].get_spatial_topos()
        min_dim = min(ElemType[t.elem_type].dim for t in spatial_topos.values())

        reprs = [ReprType._vertex, ReprType._point]

        if min_dim > 1:
            reprs.append(ReprType._line)
        if min_dim > 2:
            reprs.append(ReprType._volume)

        return reprs

    def get_menu(self, obj):
        if not isinstance(obj, SceneObject):
            return None, None

        menu = [obj.name]
        if obj.get_max_dimensions() > 1:
            menu += [ReprType.surface, ReprType.volume]

        return menu, self._object_menu_item

    def _object_menu_item(self, obj: Union[SceneObject, SceneObjectRepr], item: str):
        repr: Optional[SceneObjectRepr] = None

        if item == ReprType.surface:
            repr = self.create_repr(obj, ReprType._surface, make_two_side=True)
        elif item == ReprType.volume:
            repr = self.create_repr(obj, ReprType._volume)

        if repr is not None:
            self.mgr.add_scene_object_repr(repr)

    def create_repr(self, obj: MeshSceneObject, repr_type: str, make_two_side=False, **kwargs):
        spatial_topos = obj.meshes[0].get_spatial_topos()
        min_dim = min(ElemType[t.elem_type].dim for t in spatial_topos.values())

        calc_func = first(
            d.calc_func for _, d in ReprMeshAlgorithm if d.repr_type == repr_type and d.min_dim >= min_dim
        )

        mesh0: Mesh = calc_func(obj.meshes[0], **kwargs)
        meshes = [mesh0]
        figures = []

        for m in obj.meshes[1:]:
            mesh0.share_other_data(m)
            meshm = calc_func(m, **kwargs)
            meshes.append(meshm)

        if make_two_side:
            meshes += [calculate_inverted_tri_mesh(m) for m in meshes]

        for m in meshes:
            inds = first(m.topos.values()).data
            norms = m.other_data.get(MeshDataValue._norms, None)
            colors = m.other_data.get(MeshDataValue._colors, None)
            uvwcoords = m.other_data.get(MeshDataValue._uvwcoords, None)

            fig = SimpleFigure(f"Fig{m.timestep}", m.nodes, inds, norms, colors, uvwcoords)
            fig.timestep = m.timestep
            figures.append(fig)

        repr = MeshSceneObjectRepr(obj, figures, meshes, repr_type, obj.reprcount)
        obj.add_repr(repr)

        return repr


class ImageScenePlugin(ScenePlugin):
    def get_icon(self, obj) -> str:
        return IconName.image
