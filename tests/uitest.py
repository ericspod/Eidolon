import sys
import threading
import traceback

from PyQt5 import QtCore, QtGui

import eidolon
from eidolon.mathdef import generate_axes_arrows, vec3
from eidolon.renderer import OffscreenCamera, SimpleFigure
from eidolon.scene import QtCamera3DController
from eidolon.ui import CameraWidget, MainWindow, exec_ui, init_ui
from eidolon.utils import Future, config

conf = config.load_config()

app = init_ui()

app.setStyle("plastique")
# sheet = load_rc_file("DefaultUIStyle", ":/css").decode('utf-8')
sheet = eidolon.resources.read_text("DefaultUIStyle.css")
app.setStyleSheet(sheet)

win = MainWindow(conf)

cam = OffscreenCamera("test", 400, 400)

camwidget = CameraWidget(cam)

ctrl = QtCamera3DController(cam, vec3.zero, 0, 0, 50)
ctrl.attach_events(camwidget.events)

win.setCentralWidget(camwidget)

verts, inds, norms, colors = generate_axes_arrows(5, 10)

mesh = SimpleFigure("axes", verts, inds, norms, colors)
mesh.attach(cam)

model = win.treeView.model()

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
