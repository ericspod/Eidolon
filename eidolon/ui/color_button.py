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

from typing import Optional

from eidolon.utils import color, EventDispatcher, Namespace
from eidolon.ui import set_color_button, to_qt_color

from PyQt5 import QtCore, QtGui, QtWidgets


class ColorButtonEvent(Namespace):
    selected: (QtWidgets.QPushButton, color)


class ColorButton(QtWidgets.QPushButton):
    def __init__(self, col: color, parent: QtWidgets.QWidget, evt_dispatch: Optional[EventDispatcher] = None):
        super().__init__(parent=parent)
        self.button_color = color
        self._evt_dispatch = evt_dispatch

    @property
    def button_color(self) -> color:
        return self._button_color

    @button_color.setter
    def button_color(self, col: color):
        self._button_color = col
        set_color_button(col, self)

    def _pressed(self):
        c = QtWidgets.QColorDialog.getColor(to_qt_color(self.button_color), self)
        if c.isValid():
            self.button_color = c.getRgbF()
            if self._evt_dispatch is not None:
                self._evt_dispatch.trigger_event(ColorButtonEvent._selected, self, self.button_color)
