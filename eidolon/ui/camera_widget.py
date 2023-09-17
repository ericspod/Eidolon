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

from PyQt5 import QtCore, QtGui, QtWidgets

from ..renderer.camera import OffscreenCamera
from ..renderer.render_base import RenderBase
from ..utils import EventDispatcher, Namespace, timing
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
    def __init__(
        self,
        camera: OffscreenCamera,
        parent: Optional[QtWidgets.QWidget] = None,
        events: Optional[EventDispatcher] = None,
    ):
        super().__init__(parent)

        self.camera: OffscreenCamera = camera
        self.rbase: RenderBase = camera.rbase

        self.painter: QtGui.QPainter = QtGui.QPainter()
        self._events: EventDispatcher = events or EventDispatcher()

        # creates a timed repaint event to redraw the widget after resizing in both dimensions at once
        self.redraw_timer: QtCore.QTimer = QtCore.QTimer()
        self.redraw_timer.setSingleShot(True)
        self.redraw_timer.timeout.connect(self.repaint_on_ready)

    def _trigger_event(self, name: str, evt=None):
        self.events.trigger_event(name, widget=self, event=evt)

    @property
    def events(self) -> EventDispatcher:
        return self._events

    @qtmainthread
    def repaint_on_ready(self):
        """
        Trigger a repainting of the scene, this requires updating the RenderBase object. If this isn't ready post an
        event to try again after other events have completed.
        """
        if self.rbase.is_ready():
            self.rbase.update()
            self.repaint()
        else:
            self.redraw_timer.start(1)

    def minimumSizeHint(self):
        return QtCore.QSize(400, 300)

    def paintEvent(self, evt: QtGui.QPaintEvent):
        self._trigger_event(CameraWidgetEvent._pre_paint)

        self.camera.resize(self.width(), self.height())
        texture = self.camera.texture

        if texture.might_have_ram_image():
            data = texture.get_ram_image().getData()
            img = QtGui.QImage(data, texture.getXSize(), texture.getYSize(), QtGui.QImage.Format_ARGB32).mirrored()

            self.painter.begin(self)
            self.painter.drawImage(0, 0, img)
            self.painter.end()

        self._trigger_event(CameraWidgetEvent._post_paint)

    def resizeEvent(self, evt: QtGui.QResizeEvent) -> None:
        self._trigger_event(CameraWidgetEvent._resized, evt)
        super().resizeEvent(evt)

        # need to trigger repaint event outside of this event, this allows self.rbase to update correctly when resized
        self.redraw_timer.start(1)  # FIXME: possible race condition with the rendering in paintEvent?

    def showEvent(self, evt: QtGui.QShowEvent) -> None:
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
