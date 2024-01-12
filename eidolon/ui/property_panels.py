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

from typing import Callable, List, NamedTuple, Union
from functools import partial

from PyQt5 import QtWidgets
from eidolon.renderer.material import Material
from eidolon.scene.scene_object import SceneObjectRepr
from eidolon.ui import ColorButtonEvent, ColorButton
from eidolon.ui.ui_utils import fill_table, replace_widget, set_checked, set_color_button, signal_blocker, to_qt_color
from eidolon.ui.loader import load_res_layout
from eidolon.utils import color, EventDispatcher, Namespace

__all__ = ["ObjectProp", "ReprProp"]

Ui_ObjectProp = load_res_layout("object_property.ui")
Ui_ReprProp = load_res_layout("repr_property.ui")


class PropPanelEvent(Namespace):
    color_changed = (SceneObjectRepr, str, color)
    alpha_changed = (SceneObjectRepr, color)


class ObjectProp(QtWidgets.QWidget, Ui_ObjectProp):
    def __init__(self, obj, evt_dispatch: EventDispatcher, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        self.obj = obj
        self.evt_dispatch: EventDispatcher = evt_dispatch

    def _update_state(self):
        with signal_blocker(self.propTable):
            fill_table(self.obj.prop_tuples,self.propTable)

    def showEvent(self, evt):
        QtWidgets.QWidget.showEvent(self, evt)
        self._update_state()


class ReprProp(QtWidgets.QWidget, Ui_ReprProp):
    def __init__(self, repr, evt_dispatch: EventDispatcher, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        self.repr = repr
        self.evt_dispatch: EventDispatcher = evt_dispatch

        self.handleCheckbox.setVisible(False)
        self.bbCheckbox.setVisible(False)
        self.materialBox.setVisible(False)
        self.spectrumBox.setVisible(False)
        self.transformBox.setVisible(False)
        self.parentObjBox.setVisible(False)

        self.chooseAmbient.clicked.connect(partial(self._select_color, component="ambient"))
        self.chooseDiffuse.clicked.connect(partial(self._select_color, component="diffuse"))
        self.chooseEmissive.clicked.connect(partial(self._select_color, component="emissive"))
        self.chooseSpecular.clicked.connect(partial(self._select_color, component="specular"))

        self.shininessBox.valueChanged.connect(self._select_shininess)
        self.alphaBox.valueChanged.connect(self._select_alpha)
    
    def _update_state(self):
        mat:Material = self.repr.get_material()
        with signal_blocker(self.alphaBox,self.shininessBox,self.propTable):
            self.alphaBox.setValue(mat.diffuse[3])
            self.shininessBox.setValue(mat.shininess)

            fill_table(self.repr.prop_tuples,self.propTable)

            mat:Material = self.repr.get_material()
            set_color_button(mat.ambient,self.chooseAmbient)
            set_color_button(mat.diffuse,self.chooseDiffuse)
            set_color_button(mat.emissive,self.chooseEmissive)
            set_color_button(mat.specular,self.chooseSpecular)


    def showEvent(self, evt):
        QtWidgets.QWidget.showEvent(self, evt)
        self._update_state()

    def _select_shininess(self, value):
        self.evt_dispatch.trigger_event(
            PropPanelEvent._color_changed, repr=self.repr, component="shininess", value=value
        )

    def _select_alpha(self, value):
        self.evt_dispatch.trigger_event(PropPanelEvent._alpha_changed, repr=self.repr, value=value)

    def _select_color(self, component):
        mat:Material = self.repr.get_material()
        col = to_qt_color(getattr(mat, component))
        c = QtWidgets.QColorDialog.getColor(col, self)
        if c.isValid():
            col = tuple(c.getRgbF())
            col = col[:3] + (self.alphaBox.value(),)
            self.evt_dispatch.trigger_event(
                PropPanelEvent._color_changed, repr=self.repr, component=component, value=col
            )
