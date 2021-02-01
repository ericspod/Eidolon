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

from typing import NamedTuple, Optional
from PyQt5 import QtGui, QtCore, QtWidgets

from ..utils import Namespace, EventDispatcher, timing
from ..renderer.camera import OffscreenCamera
from ..renderer.render_base import RenderBase
from .threadsafe_calls import qtmainthread

__all__ = ["CameraWidget", "CameraWidgetEvent", "WidgetEventDesc"]


class WidgetEventDesc(NamedTuple):
    widget: QtWidgets.QWidget = None
    event: QtCore.QEvent = None


class CameraWidgetEvent(Namespace):
    key_pressed = WidgetEventDesc(OffscreenCamera, QtGui.QKeyEvent)
    key_released = WidgetEventDesc(OffscreenCamera, QtGui.QKeyEvent)
    mouse_pressed = WidgetEventDesc(OffscreenCamera, QtGui.QMouseEvent)
    mouse_double_clicked = WidgetEventDesc(OffscreenCamera, QtGui.QMouseEvent)
    mouse_released = WidgetEventDesc(OffscreenCamera, QtGui.QMouseEvent)
    mouse_moved = WidgetEventDesc(OffscreenCamera, QtGui.QMouseEvent)
    mouse_wheel = WidgetEventDesc(OffscreenCamera, QtGui.QWheelEvent)
    shown = WidgetEventDesc(OffscreenCamera, QtGui.QShowEvent)
    resized = WidgetEventDesc(OffscreenCamera, QtGui.QResizeEvent)
    pre_paint = WidgetEventDesc(OffscreenCamera, None)
    post_paint = WidgetEventDesc(OffscreenCamera, None)


class CameraWidget(QtWidgets.QWidget):
    def __init__(self, camera: OffscreenCamera,
                 parent: Optional[QtWidgets.QWidget] = None, events: Optional[EventDispatcher] = None):
        super().__init__(parent)

        self.camera: OffscreenCamera = camera
        self.rbase: RenderBase = camera.rbase

        self.painter: QtGui.QPainter = QtGui.QPainter()
        self._events: EventDispatcher = events or EventDispatcher()

        # creates a timed repaint event to redraw the widget after resizing in both dimensions at once
        self.redraw_timer: QtCore.QTimer = QtCore.QTimer()
        self.redraw_timer.setSingleShot(True)
        self.redraw_timer.timeout.connect(self.repaint_on_ready1)

    @property
    def events(self):
        return self._events

    def minimumSizeHint(self):
        return QtCore.QSize(400, 300)

    def paintEvent(self, evt: QtGui.QPaintEvent):
        size=self.size()
        self.camera.resize(size.width(), size.height())

        texture = self.camera.texture

        if texture.might_have_ram_image():
            data = texture.get_ram_image().getData()
            img = QtGui.QImage(data, texture.getXSize(), texture.getYSize(), QtGui.QImage.Format_ARGB32).mirrored()

            self.painter.begin(self)
            self.painter.drawImage(0, 0, img)
            self.painter.end()

    @qtmainthread
    def repaint_on_ready(self):
        if self.rbase.is_ready():
            self._trigger_event(CameraWidgetEvent._pre_paint)
            self.rbase.update()
            self.repaint()
            self._trigger_event(CameraWidgetEvent._post_paint)

    def _resize(self, size: QtCore.QSize, do_update: bool):
        self.camera.resize(size.width(), size.height())
        if do_update:
            self.repaint_on_ready()

        self.repaint()

    def _trigger_event(self, name, evt=None):
        self.events.trigger_event(name, widget=self, event=evt)


    @timing
    def resizeEvent(self, evt: QtGui.QResizeEvent) -> None:
        size_diff = evt.size() - evt.oldSize()
        # FIXME: why crash when changing both dimensions at once? Needed to avoid crashes when both dimensions change
        resize_1d = False  # size_diff.width() == 0 or size_diff.height() == 0

        # self._resize(evt.size(), resize_1d)
        self.repaint()

        self._trigger_event(CameraWidgetEvent._resized, evt)
        super().resizeEvent(evt)

        if not resize_1d:  # FIXME: this is the fix for the above issue, should be replaced with a proper solution
            self.redraw_timer.start(5)

    def showEvent(self, evt: QtGui.QShowEvent) -> None:
        # self._resize(self.size(), True)
        self._trigger_event(CameraWidgetEvent._shown, evt)
        super().showEvent(evt)

    def mousePressEvent(self, evt: QtGui.QMouseEvent) -> None:
        self._trigger_event(CameraWidgetEvent._mouse_pressed, evt)
        super().mousePressEvent(evt)

    def mouseDoubleClickEvent(self, evt: QtGui.QMouseEvent) -> None:
        self._trigger_event(CameraWidgetEvent._mouse_double_clicked, evt)
        super().mouseDoubleClickEvent(evt)

    def mouseReleaseEvent(self, evt: QtGui.QMouseEvent) -> None:
        self._trigger_event(CameraWidgetEvent._mouse_released, evt)
        super().mouseReleaseEvent(evt)

    def mouseMoveEvent(self, evt: QtGui.QMouseEvent) -> None:
        self._trigger_event(CameraWidgetEvent._mouse_moved, evt)
        super().mouseMoveEvent(evt)

    def wheelEvent(self, evt: QtGui.QWheelEvent) -> None:
        self._trigger_event(CameraWidgetEvent._mouse_wheel, evt)
        super().wheelEvent(evt)

    def keyPressEvent(self, evt: QtGui.QKeyEvent) -> None:
        self._trigger_event(CameraWidgetEvent._key_pressed, evt)
        super().keyPressEvent(evt)

    def keyReleaseEvent(self, evt: QtGui.QKeyEvent) -> None:
        self._trigger_event(CameraWidgetEvent._key_released, evt)
        super().keyReleaseEvent(evt)
