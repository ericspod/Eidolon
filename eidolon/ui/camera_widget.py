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
from PyQt5.QtCore import Qt
from ..renderer.manager import Manager
from ..utils.event_dispatcher import EventDispatcher

__all__ = ["CameraWidget", "CameraWidgetEvents"]


class CameraWidgetEvents(Enum):
    KEY_PRESSED = 0, {"widget": QtWidgets.QWidget, "event": QtGui.QKeyEvent}
    KEY_RELEASED = 1, {"widget": QtWidgets.QWidget, "event": QtGui.QKeyEvent}
    MOUSE_PRESSED = 2, {"widget": QtWidgets.QWidget, "event": QtGui.QMouseEvent}
    MOUSE_DOUBLE_CLICKED = 3, {"widget": QtWidgets.QWidget, "event": QtGui.QMouseEvent}
    MOUSE_RELEASED = 4, {"widget": QtWidgets.QWidget, "event": QtGui.QMouseEvent}
    MOUSE_MOVED = 5, {"widget": QtWidgets.QWidget, "event": QtGui.QMouseEvent}
    MOUSE_WHEEL = 6, {"widget": QtWidgets.QWidget, "event": QtGui.QWheelEvent}
    SHOWN = 7, {"widget": QtWidgets.QWidget, "event": QtGui.QShowEvent}
    RESIZED = 8, {"widget": QtWidgets.QWidget, "event": QtGui.QResizeEvent}
    PRE_PAINT = 9, {"widget": QtWidgets.QWidget, "event": None}
    POST_PAINT = 10, {"widget": QtWidgets.QWidget, "event": None}


class CameraWidget(QtWidgets.QWidget):
    def __init__(self, mgr: Manager, camera, parent=None):
        super().__init__(parent)
        # self.setFocusPolicy(Qt.StrongFocus)
        # self.setAttribute(Qt.WA_PaintOnScreen, True)
        # self.setAttribute(Qt.WA_NoSystemBackground, True)
        # self.setAttribute(Qt.WA_OpaquePaintEvent, True)

        self.mgr: Manager = mgr
        self.camera = camera

        self.painter = QtGui.QPainter()
        self._events = EventDispatcher()

    @property
    def events(self):
        return self._events

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
            self._trigger_event(CameraWidgetEvents.PRE_PAINT)
            self.mgr.update()
            self.repaint()
            self._trigger_event(CameraWidgetEvents.POST_PAINT)

    def _resize(self, size: QtCore.QSize, do_update: bool):
        self.camera.resize(size.width(), size.height())
        if do_update:
            self.repaint_on_ready()

    def _trigger_event(self, name, evt=None):
        self.events.trigger_event(name, widget=self, event=evt)

    def resizeEvent(self, evt: QtGui.QResizeEvent) -> None:
        size_diff = evt.size() - evt.oldSize()
        # FIXME: why crash when changing both dimensions at once? Needed to avoid crashes when both dimensions change
        resize_1d = size_diff.width() == 0 or size_diff.height() == 0

        self._resize(evt.size(), resize_1d)
        self._trigger_event(CameraWidgetEvents.RESIZED, evt)
        super().resizeEvent(evt)

    def showEvent(self, evt: QtGui.QShowEvent) -> None:
        self._resize(self.size(), True)
        self._trigger_event(CameraWidgetEvents.SHOWN, evt)
        super().showEvent(evt)

    def mousePressEvent(self, evt: QtGui.QMouseEvent) -> None:
        self._trigger_event(CameraWidgetEvents.MOUSE_PRESSED, evt)
        super().mousePressEvent(evt)

    def mouseDoubleClickEvent(self, evt: QtGui.QMouseEvent) -> None:
        self._trigger_event(CameraWidgetEvents.MOUSE_DOUBLE_CLICKED, evt)
        super().mouseDoubleClickEvent(evt)

    def mouseReleaseEvent(self, evt: QtGui.QMouseEvent) -> None:
        self._trigger_event(CameraWidgetEvents.MOUSE_RELEASED, evt)
        super().mouseReleaseEvent(evt)

    def mouseMoveEvent(self, evt: QtGui.QMouseEvent) -> None:
        self._trigger_event(CameraWidgetEvents.MOUSE_MOVED, evt)
        super().mouseMoveEvent(evt)

    def wheelEvent(self, evt: QtGui.QWheelEvent) -> None:
        self._trigger_event(CameraWidgetEvents.MOUSE_WHEEL, evt)
        super().wheelEvent(evt)

    def keyPressEvent(self, evt: QtGui.QKeyEvent) -> None:
        self._trigger_event(CameraWidgetEvents.KEY_PRESSED, evt)
        super().keyPressEvent(evt)

    def keyReleaseEvent(self, evt: QtGui.QKeyEvent) -> None:
        self._trigger_event(CameraWidgetEvents.KEY_RELEASED, evt)
        super().keyReleaseEvent(evt)
