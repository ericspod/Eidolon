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

from PyQt5 import QtWidgets
from eidolon.ui import ColorButtonEvent, ColorButton
from eidolon.ui.ui_utils import replace_widget, set_checked
from eidolon.ui.loader import load_res_layout
from eidolon.utils import color, EventDispatcher

__all__=["ObjectProp", "ReprProp"]

Ui_ObjectProp = load_res_layout("object_property.ui")
Ui_ReprProp = load_res_layout("repr_property.ui")


class ObjectProp(QtWidgets.QWidget, Ui_ObjectProp):
    def __init__(self,obj,parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        self.obj=obj


class ReprProp(QtWidgets.QWidget, Ui_ReprProp):
    def __init__(self,repr,parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        self.repr=repr
        # self.chooseAmbient=replace_widget(self.chooseAmbient,ColorButton("Ambient",(1,1,1,1),None))
        self.handleCheckbox.setVisible(False)
        self.bbCheckbox.setVisible(False)
        self.materialBox.setVisible(False)
        self.spectrumBox.setVisible(False)
        self.transformBox.setVisible(False)
        self.parentObjBox.setVisible(False)

    def _update_state(self):
        set_checked(self.repr.visible,self.visibleCheckbox)
    
    def showEvent(self, evt):
        QtWidgets.QWidget.showEvent(self,evt)
        self._update_state()
        
