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

from enum import Enum
from PyQt5 import QtGui, QtCore, QtWidgets
from ..renderer.manager import Manager
from ..utils.event_dispatcher import EventDispatcher

__all__ = ["CameraWidget", "CameraWidgetEvents"]


class CameraWidgetEvents(Enum):
    KEY_PRESSED = {"widget": QtWidgets.QWidget, "event": QtGui.QKeyEvent}
    KEY_RELEASED = {"widget": QtWidgets.QWidget, "event": QtGui.QKeyEvent}
    MOUSE_PRESSED = {"widget": QtWidgets.QWidget, "event": QtGui.QMouseEvent}
    MOUSE_DOUBLE_CLICKED = {"widget": QtWidgets.QWidget, "event": QtGui.QMouseEvent}
    MOUSE_RELEASED = {"widget": QtWidgets.QWidget, "event": QtGui.QMouseEvent}
    MOUSE_MOVED = {"widget": QtWidgets.QWidget, "event": QtGui.QMouseEvent}
    SHOWN = {"widget": QtWidgets.QWidget, "event": QtGui.QShowEvent}
    RESIZED = {"widget": QtWidgets.QWidget, "event": QtGui.QResizeEvent}
    PRE_PAINT = {"widget": QtWidgets.QWidget, "event": QtGui.QPaintEvent}
    POST_PAINT = {"widget": QtWidgets.QWidget, "event": QtGui.QPaintEvent}


class CameraWidget(QtWidgets.QWidget):
    def __init__(self, mgr: Manager, camera, parent=None):
        super().__init__(parent)
        self.mgr: Manager = mgr
        self.camera = camera

        self.painter = QtGui.QPainter()
        self.events = EventDispatcher()

    def minimumSizeHint(self):
        return QtCore.QSize(400, 300)

    def paintEvent(self, evt: QtGui.QPaintEvent):
        self._trigger_event(CameraWidgetEvents.PRE_PAINT, evt)
        texture = self.camera.texture

        if texture.might_have_ram_image():
            data = texture.get_ram_image().getData()
            img = QtGui.QImage(data, texture.getXSize(), texture.getYSize(), QtGui.QImage.Format_ARGB32).mirrored()

            self.painter.begin(self)
            self.painter.drawImage(0, 0, img)
            self.painter.end()

        self._trigger_event(CameraWidgetEvents.POST_PAINT, evt)

    def repaint_on_ready(self):
        if self.mgr.is_ready():
            self.mgr.update()
            self.repaint()

    def _resize(self, size: QtCore.QSize, do_update: bool):
        self.camera.resize(size.width(), size.height())
        if do_update:
            self.mgr.update()

    def _trigger_event(self, name, evt):
        self.events.trigger_event(name, event=evt)

    def resizeEvent(self, evt: QtGui.QResizeEvent):
        self._resize(evt.size(), True)
        self._trigger_event(CameraWidgetEvents.RESIZED, evt)

    def showEvent(self, evt: QtGui.QShowEvent):
        self._resize(self.size(), True)
        self._trigger_event(CameraWidgetEvents.SHOWN, evt)

    def mousePressEvent(self, a0: QtGui.QMouseEvent) -> None:
        self._trigger_event(CameraWidgetEvents.MOUSE_PRESSED, a0)

    def mouseDoubleClickEvent(self, a0: QtGui.QMouseEvent) -> None:
        self._trigger_event(CameraWidgetEvents.MOUSE_DOUBLE_CLICKED, a0)

    def mouseReleaseEvent(self, a0: QtGui.QMouseEvent) -> None:
        self._trigger_event(CameraWidgetEvents.MOUSE_RELEASED, a0)

    def mouseMoveEvent(self, a0: QtGui.QMouseEvent) -> None:
        self._trigger_event(CameraWidgetEvents.MOUSE_MOVED, a0)
        self.repaint_on_ready()

    def keyPressEvent(self, a0: QtGui.QKeyEvent) -> None:
        self._trigger_event(CameraWidgetEvents.KEY_PRESSED, a0)

    def keyReleaseEvent(self, a0: QtGui.QKeyEvent) -> None:
        self._trigger_event(CameraWidgetEvents.KEY_RELEASED, a0)
