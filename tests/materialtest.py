import numpy as np

from eidolon.renderer import Light, LightType, SimpleFigure, Material
from eidolon.ui import init_ui, SimpleApp
from eidolon.mathdef import vec3, rotator, Mesh, ElemType, generate_tri_normals, generate_sphere, HALFPI

app = init_ui()

win = SimpleApp(1200, 800)

# et = ElemType.Tet1NL
#
# nodes = np.zeros((et.num_nodes, 3), np.float32)
#
# for j, n in enumerate(et.xis):
#     nodes[j, :len(n)] = n
#
# inds = np.arange(et.num_nodes, dtype=np.int32)[None, :]
#
# mesh = Mesh(nodes, {"inds": (inds, et.name)})
#
# tri_mesh = calculate_tri_mesh(mesh, 5, "inds")

nodes, inds = generate_sphere(2)
norms = np.array(generate_tri_normals(nodes, inds))
nodes = np.array(list(map(tuple, nodes)), np.float32)

tri_mesh = Mesh(nodes, {"inds": (np.array(inds), "Tri1NL")})
tri_mesh.other_data["norms"] = norms

fig = SimpleFigure("mesh", tri_mesh.nodes, tri_mesh.topos["inds"][0], tri_mesh.other_data["norms"])
fig.attach(win.cam)
# fig.orientation = rotator.from_axis(vec3.X, HALFPI)

m = Material(
    "mat",
    diffuse=(1, 0, 0, 1),
    specular=(0, 1, 0, 1),
    shininess=20,
    refractive_index=1.5
)
fig.apply_material(m)

light = Light("dlight", LightType.DIRECTIONAL, (0.5, 0.5, 0.5, 1))
light.attach(win.cam, True)

amb = Light("amb", LightType.AMBIENT, (0.25, 0.25, 0.25, 1))
amb.attach(win.cam)

win.ctrl.move_see_all()
win.run()
