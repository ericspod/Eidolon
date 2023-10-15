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

from typing import Union
import os
from eidolon.scene import MeshScenePlugin, SceneObject, SceneObjectRepr, MeshSceneObject, SceneManager, ReprType
from eidolon.mathdef import ElemType, Mesh, MeshDataValue
from eidolon.ui import choose_file_dialog
import trimesh


__all__ = ["TriMeshPlugin"]


class TriMeshPlugin(MeshScenePlugin):
    def init(self, plugid: int, mgr):
        super().init(plugid, mgr)

        # more formats mentioned in trimesh.exchange.load.mesh_formats
        self.file_exts += [".obj", ".stl", ".ply", ".xyz", ".off"]

        if mgr.win is not None:
            mgr.win.add_menu_item("Import", "trimesh_import", "Trimesh-compatible File", self._import_menu)

    def load_object(self, filename: str, name: str = None, **kwargs) -> SceneObject:
        tmesh: trimesh.Trimesh = trimesh.load_mesh(filename)
        trimesh.repair.fix_inversion(tmesh)
        trimesh.repair.fix_winding(tmesh)

        mesh = Mesh(tmesh.vertices, {"inds": (tmesh.faces, ElemType._Tri1NL)})
        mesh.other_data.update(tmesh.metadata)

        if tmesh.vertex_normals is not None:
            mesh.other_data[MeshDataValue._norms] = tmesh.vertex_normals

        # TODO: other loaded values from trimesh compatible files like color
        
        if name is None:
            name = os.path.splitext(os.path.basename(filename))[0]

        obj = MeshSceneObject(name, [mesh], self)

        return obj

    def get_menu(self, obj):
        if not isinstance(obj, SceneObject):
            return None, None

        return [obj.name, "Surfaces", "Volumes"], self._object_menu_item

    def _object_menu_item(self, obj: Union[SceneObject, SceneObjectRepr], item: str):
        if item == "Volumes":
            repr = self.create_repr(obj, ReprType._volume)
            self.mgr.add_scene_object_repr(repr)

    def _import_menu(self):
        fname = self.mgr.win.choose_file_dialog("Choose Trimesh file")
        if fname:
            obj = self.load_object(fname[0])
            self.mgr.add_scene_object(obj)


SceneManager.add_plugin(TriMeshPlugin("TriMesh"))
