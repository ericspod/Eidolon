from eidolon.mathdef.math_utils import iter_to_np
from eidolon.mathdef.mesh import MeshDataValue
from eidolon.mathdef.mesh_algorithms import calculate_trimesh_normals
from eidolon.renderer.figure import SimpleFigure
from eidolon.renderer.material import Material

from eidolon.scene import ReprType
from eidolon.scene.mesh_scene_object import MeshSceneObject
from eidolon.mathdef import generate_sphere
from eidolon.ui.entry_point import task_entry_point
from eidolon.utils import timing
from eidolon.mathdef.mesh_utils import generate_separate_tri_mesh, generate_sphere, generate_tri_normals
from eidolon.mathdef import  Mesh

import numpy as np

@timing
def setup(mgr):
    landmark =(0,0,0)
    verts, inds = generate_sphere(3)
    verts, inds = generate_separate_tri_mesh(verts, inds)
    norms = generate_tri_normals(verts, inds)
    msphere=Mesh.tri_mesh(verts,inds,norms)

    sobj = MeshSceneObject("outer_sphere", [msphere])
    mgr.add_scene_object(sobj)

    srepr = sobj.plugin.create_repr(sobj, ReprType._surface, make_two_side=True)
    mgr.add_scene_object_repr(srepr)

    srepr.set_shader("cone_cut")
    srepr.set_shader_input("angle",0.5)
    srepr.set_shader_input("landmark",*landmark)

    srepr.scale=(5,5,5)

    smat = Material(
        "smat",
        diffuse=(1, 0, 0, 1),
        shininess=20
    )

    sverts, sinds = generate_sphere(3)
    snorms = calculate_trimesh_normals(np.asarray(list(map(tuple, sverts))), np.asarray(sinds))

    sphere = SimpleFigure(f"sphere", sverts, sinds, snorms)
    sphere.attach(mgr.cameras[0])
    sphere.position=landmark
    sphere.apply_material(smat)
    sphere.two_sided = False
    sphere.camnodes[0].set_depth_test(False)
    sphere.camnodes[0].set_depth_write(False)
    sphere.camnodes[0].set_bin("fixed", 0)

    mgr.set_camera_see_all()


if __name__ == "__main__":
    task_entry_point(setup)
    