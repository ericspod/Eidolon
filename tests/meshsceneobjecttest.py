import os

import numpy as np

from eidolon.mathdef import ElemType, Mesh
from eidolon.mathdef.math_utils import iter_to_np
from eidolon.mathdef.mesh import MeshDataValue
from eidolon.mathdef.mesh_utils import generate_axes_arrows, generate_separate_tri_mesh, generate_sphere, generate_tri_normals
from eidolon.scene import MeshSceneObject,ReprType
from eidolon.ui import task_entry_point

def _task(mgr):
    verts, inds, norms, colors = generate_axes_arrows(5, 10)
    mesh = Mesh(verts, {"inds": (inds, ElemType._Tri1NL)})
    mesh.other_data[MeshDataValue._norms]=iter_to_np(norms)
    mesh.other_data[MeshDataValue._colors]=iter_to_np(colors)

    obj = MeshSceneObject("arrows", [mesh])
    mgr.add_scene_object(obj)

    repr = obj.plugin.create_repr(obj, ReprType._surface)
    mgr.add_scene_object_repr(repr)

    verts, inds = generate_sphere(3)
    verts, inds = generate_separate_tri_mesh(verts, inds)
    norms = generate_tri_normals(verts, inds)
    msphere = Mesh(verts, {"inds": (inds, ElemType._Tri1NL)})
    msphere.other_data[MeshDataValue._norms]=iter_to_np(norms)

    sobj = MeshSceneObject("arrows", [msphere])
    mgr.add_scene_object(sobj)

    srepr = sobj.plugin.create_repr(sobj, ReprType._surface)
    mgr.add_scene_object_repr(srepr)

    srepr.position=(5,5,5)

    mgr.set_camera_see_all()

if __name__ == "__main__":
    task_entry_point(_task)
