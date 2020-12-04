import sys
import math
from PyQt5 import QtGui, QtCore, QtWidgets

import eidolon
import eidolon.renderer
import eidolon.ui

from eidolon.mathdef import vec3,rotator, generate_axes_arrows


def main():
    app = QtWidgets.QApplication(sys.argv)

    mgr = eidolon.renderer.Manager()
    cam = eidolon.renderer.OffscreenCamera(mgr, "test", 400, 400)

    camwidget = eidolon.ui.CameraWidget(mgr, cam)

    ctrl = eidolon.ui.CameraController(cam, vec3.zero, 0, 0, 50)
    ctrl.attach_events(camwidget.events)

    verts, inds, norms, colors = generate_axes_arrows(5, 10)

    mesh = eidolon.renderer.SimpleMesh("quad", verts, inds, norms, colors)
    mesh.attach(cam)

    appw = QtWidgets.QMainWindow()
    appw.resize(800, 600)
    appw.setCentralWidget(camwidget)
    appw.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
