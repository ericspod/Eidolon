from eidolon.mathdef.mesh import Mesh
from eidolon.renderer.material import Material
from eidolon.scene import MeshSceneObject, SceneManager, ReprType
from eidolon.mathdef import generate_separate_tri_mesh, generate_sphere, generate_tri_normals

mgr: SceneManager

verts, inds = generate_sphere(3)
verts, inds = generate_separate_tri_mesh(verts, inds)
norms = generate_tri_normals(verts, inds)
colors = [(1, 1, 1, 1)] * len(verts)

mesh = Mesh.tri_mesh(verts, inds, norms, colors)

obj = MeshSceneObject("Sphere", [mesh])
mgr.add_scene_object(obj)

repr = obj.plugin.create_repr(obj, ReprType._surface)
mgr.add_scene_object_repr(repr)

mat = Material(
    "mat",
    diffuse=(1, 0, 0, 0.5),
    shininess=20
)

repr.set_material(mat)

mgr.set_camera_see_all()
