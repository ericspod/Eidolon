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


import sys
from typing import Optional

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

from ..mathdef import vec3
from ..utils import is_interactive
from ..renderer import Manager, OffscreenCamera
from .camera_controller import CameraController
from .camera_widget import CameraWidget

__all__ = ["qtrunner", "SimpleApp"]


def qtrunner(app: QtWidgets.QApplication, do_exit: Optional[bool] = None):
    status = app.exec_()

    if do_exit is True or (do_exit is None and not is_interactive()):
        sys.exit(status)


class SimpleApp(QtWidgets.QMainWindow):
    def __init__(self, width: int, height: int, parent=None):
        self.app = QtWidgets.QApplication(sys.argv)
        super().__init__(parent)
        self.mgr = Manager()
        self.cam = OffscreenCamera(self.mgr, "test")

        self.camwidget = CameraWidget(self.mgr, self.cam)

        self.ctrl = CameraController(self.cam, vec3.zero, 0, 0, 50)
        self.ctrl.attach_events(self.camwidget.events)

        self.resize(width, height)
        self.setCentralWidget(self.camwidget)

    def keyPressEvent(self, evt):
        if evt.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(evt)

    def run(self, do_exit: Optional[bool] = None):
        self.show()
        qtrunner(self.app, do_exit)
