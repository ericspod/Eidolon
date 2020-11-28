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

from PyQt5 import QtGui, QtCore, QtWidgets

from ..renderer.manager import Manager


class CameraWidget(QtWidgets.QWidget):
    def __init__(self, mgr: Manager, camera, controller, parent=None):
        super().__init__(parent)
        self.mgr: Manager = mgr
        self.camera = camera
        self.controller = controller

        self.painter = QtGui.QPainter()

    def minimumSizeHint(self):
        return QtCore.QSize(400, 300)

    def paintEvent(self, evt: QtGui.QPaintEvent):
        texture = self.camera.texture

        if texture.might_have_ram_image():
            data = texture.get_ram_image().getData()
            img = QtGui.QImage(data, texture.getXSize(), texture.getYSize(), QtGui.QImage.Format_ARGB32).mirrored()

            self.painter.begin(self)
            self.painter.drawImage(0, 0, img)
            self.painter.end()

    def repaint_on_ready(self):
        if self.mgr.is_ready():
            self.mgr.update()
            self.repaint()

    def _resize(self, size: QtCore.QSize, do_update: bool):
        self.camera.resize(size.width(), size.height())
        if do_update:
            self.mgr.update()

    def resizeEvent(self, evt: QtGui.QResizeEvent):
        self._resize(evt.size(), True)

    def showEvent(self, evt: QtGui.QShowEvent):
        self._resize(self.size(), True)

    def mousePressEvent(self, a0: QtGui.QMouseEvent) -> None:
        self.controller.last_pos = None
        self.repaint()

    def mouseMoveEvent(self, a0: QtGui.QMouseEvent) -> None:
        self.controller.drag(a0.x(), a0.y())
        self.controller.set_camera_position()
        self.repaint_on_ready()
