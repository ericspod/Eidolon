import sys
from PyQt5 import QtWidgets

import eidolon
import eidolon.renderer
import eidolon.ui

from eidolon.mathdef import vec3, generate_axes_arrows


def main():
    app = QtWidgets.QApplication(sys.argv)

    mgr = eidolon.renderer.Manager()
    cam = eidolon.renderer.OffscreenCamera(mgr, "test", 400, 400)

    light = eidolon.renderer.Light("dlight", eidolon.renderer.LightType.DIRECTIONAL, (1, 1, 1, 1))
    light.attach(cam)

    amb = eidolon.renderer.Light("amb", eidolon.renderer.LightType.AMBIENT, (0.25, 0.25, 0.25, 1))
    amb.attach(cam)

    camwidget = eidolon.ui.CameraWidget(mgr, cam)

    ctrl = eidolon.ui.CameraController(cam, vec3.zero, 0, 0, 50)
    ctrl.attach_events(camwidget.events)

    verts, inds, norms, colors = generate_axes_arrows(5, 10)

    mesh = eidolon.renderer.SimpleMesh("axes", verts, inds, norms, colors)
    mesh.attach(cam)

    appw = QtWidgets.QMainWindow()
    appw.resize(800, 600)
    appw.setCentralWidget(camwidget)
    appw.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
