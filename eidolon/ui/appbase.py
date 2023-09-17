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


import signal
import sys
from typing import Optional

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

from eidolon.mathdef import vec3
from eidolon.utils import is_interactive

from .camera_widget import CameraWidget

__all__ = ["init_ui", "exec_ui", "SimpleApp"]

global_app = None


def init_ui(args=None) -> QtWidgets.QApplication:
    """Initialize the UI framework."""
    global global_app

    if global_app is None:
        global_app = QtWidgets.QApplication(sys.argv if args is None else args)
        global_app.setAttribute(Qt.AA_DontUseNativeMenuBar)  # in macOS, forces menubar to be in window

    return global_app


def exec_ui(app: QtWidgets.QApplication, do_exit: Optional[bool] = None):
    do_exit = do_exit is True or (do_exit is None and not is_interactive())  # exit only if requested or not interactive
    app = app or global_app

    if do_exit:
        signal.signal(signal.SIGINT, signal.SIG_DFL)  # ensure keyboard interrupt signal causes a forced unclean exit

    status = app.exec_()

    if do_exit:
        sys.exit(status)


class SimpleApp(QtWidgets.QMainWindow):
    def __init__(self, width: int, height: int, parent=None):
        # imported here to avoid dependency issues
        from eidolon.renderer import OffscreenCamera
        from eidolon.scene import QtCamera3DController

        self.app = init_ui(sys.argv)
        super().__init__(parent)
        self.cam = OffscreenCamera("cam")

        self.camwidget = CameraWidget(self.cam)

        self.ctrl = QtCamera3DController(self.cam, vec3.zero, 0, 0, 50, self.camwidget.repaint_on_ready)
        self.ctrl.attach_events(self.camwidget.events)

        self.resize(width, height)
        self.setCentralWidget(self.camwidget)

    def keyPressEvent(self, evt):
        if evt.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(evt)

    def exec(self, do_exit: Optional[bool] = None):
        self.show()
        exec_ui(self.app, do_exit)
