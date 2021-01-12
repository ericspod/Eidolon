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

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt

from .threadsafe_calls import qtmainthread


class DictTableModel(QtCore.QAbstractTableModel):
    def __init__(self, data, header=None):
        super().__init__()
        self._data = data
        self._header = header

    def rowCount(self, parent=None) -> int:
        return len(self._data)

    def columnCount(self, parent=None) -> int:
        return 2

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...):
        if self._header is not None and role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._header[section]

    def data(self, index: QtCore.QModelIndex, role: int = ...):
        if index.isValid() and role == QtCore.Qt.DisplayRole:
            kv = list(self._data.items())[index.row()]
            return kv[index.column()]


class ComboBoxModel(QtCore.QAbstractListModel):
    """
    Model for managing the contents of QComboBox objects. This contains a list of objects or a list of object tuples,
    the first member of tuples being used to determine the string values to fill the combo box with. The model can be
    updated with the replace() method to fulling replace the internal list, this will trigger the combo box to be
    refilled and retain the currently selected value if it's in the new list. The model should be associated with the
    box with attach() to ensure signals are connected as well as setting model.
    """

    def __init__(self):
        super().__init__()
        self._data = []
        self._combo: QtWidgets.QComboBox = None
        self._selected = None

    def attach(self, combo: QtWidgets.QComboBox):
        self._combo = combo
        combo.setModel(self)
        combo.currentIndexChanged.connect(self._current_index_changed)

    def detach(self):
        self._combo.setModel(None)
        self._combo.currentIndexChanged.disconnect(self._current_index_changed)
        self._combo = None

    def _current_index_changed(self, index):
        if index >= 0:
            self._selected = self._data[index]
            if isinstance(self._selected, tuple):
                self._selected = self._selected[0]

    @property
    def selected_index(self):
        for idx, item in enumerate(self._data):
            if isinstance(item, tuple):
                item = item[0]

            if item == self._selected:
                return idx

        return 0

    @property
    def selected_value(self):
        return self._data[self.selected_index]

    @qtmainthread
    def set_to_selected_item(self):
        if self._combo is not None:
            self._combo.setCurrentIndex(self.selected_index)

    @qtmainthread
    def fill(self, data):
        self.beginResetModel()
        self._data[:] = data
        self.endResetModel()
        self.set_to_selected_item()

    def rowCount(self, parent: QtCore.QModelIndex = ...) -> int:
        return len(self._data)

    def data(self, index: QtCore.QModelIndex, role: int = ...):
        if index.isValid() and role == QtCore.Qt.DisplayRole:
            item = self._data[index.row()]

            if isinstance(item, tuple):
                return str(item[0])
            else:
                return str(item)
