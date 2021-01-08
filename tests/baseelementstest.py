import numpy as np

from eidolon.renderer import Light, LightType, SimpleFigure
from eidolon.ui import init_ui, SimpleApp
from eidolon.mathdef import vec3, rotator, Mesh, ElemType, calculate_tri_mesh, HALFPI

app = init_ui()

win = SimpleApp(1200, 800)

elemtypes = [ElemType.Tri1NL, ElemType.Quad1NL, ElemType.Tet1NL, ElemType.Hex1NL]

figures = []

for i, et in enumerate(elemtypes):

    nodes = np.zeros((et.num_nodes, 3), np.float32)

    for j, n in enumerate(et.xis):
        nodes[j, :len(n)] = n

    inds = np.arange(et.num_nodes, dtype=np.int32)[None, :]

    mesh = Mesh(nodes, {"inds": (inds, et.name)})

    print(et.name, mesh.nodes.shape, mesh.topos["inds"][0].shape)

    tri_mesh = calculate_tri_mesh(mesh, 5, "inds")

    fig = SimpleFigure(et.name + "_trimesh", tri_mesh.nodes, tri_mesh.topos["inds"][0], tri_mesh.other_data["norms"])
    fig.attach(win.cam)
    fig.position = vec3(i * 2, 0, 0)
    fig.orientation = rotator.from_axis(vec3.X, HALFPI)

    # fig.camnodes[-1].set_render_mode_wireframe()

light = Light("dlight", LightType.DIRECTIONAL, (0.5, 0.5, 0.5, 1))
light.attach(win.cam, True)

amb = Light("amb", LightType.AMBIENT, (0.25, 0.25, 0.25, 1))
amb.attach(win.cam)

win.ctrl.move_see_all()
win.run()
