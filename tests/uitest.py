import sys
import traceback
import threading
from PyQt5 import QtCore, QtGui

import eidolon
from eidolon.mathdef import vec3, generate_axes_arrows
from eidolon.scene import QtCameraController
from eidolon.ui import MainWindow, exec_ui, init_ui, CameraWidget
from eidolon.renderer import OffscreenCamera, SimpleFigure
from eidolon import config
from eidolon.utils import Future


conf = config.load_config()

app = init_ui()

app.setStyle("plastique")
# sheet = load_rc_file("DefaultUIStyle", ":/css").decode('utf-8')
sheet = eidolon.resources.read_text("DefaultUIStyle.css")
app.setStyleSheet(sheet)

win = MainWindow(conf)

cam = OffscreenCamera("test", 400, 400)

camwidget = CameraWidget(cam)

ctrl = QtCameraController(cam, vec3.zero, 0, 0, 50)
ctrl.attach_events(camwidget.events)

win.setCentralWidget(camwidget)

verts, inds, norms, colors = generate_axes_arrows(5, 10)

mesh = SimpleFigure("axes", verts, inds, norms, colors)
mesh.attach(cam)

model=win.treeView.model()

# item=QtGui.QStandardItem(QtGui.QIcon(':/icons/document.png'),"foo")
# item.setData("bar")
#
# model.appendRow(item)
#
# item1=QtGui.QStandardItem(QtGui.QIcon(':/icons/eye.png'),"thunk")
# item1.setData("baz")
# item.appendRow(item1)
#
# win.treeView.expand(model.indexFromItem(item))



win.show()

exec_ui(app)
