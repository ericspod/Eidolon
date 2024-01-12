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


from typing import Any, Callable, List, Optional
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt

from eidolon.ui.threadsafe_calls import qtmainthread
from eidolon.ui.ui_utils import create_menu
from eidolon.utils import first


__all__ = ["SceneObjectTree"]


class TreeItem:
    def __init__(self, obj, **named_values):
        self.obj = obj
        for k, v in named_values.items():
            setattr(self, k, v)

    def __eq__(self, value: object) -> bool:
        return self.obj == value


class SceneObjectTree(QtWidgets.QTreeView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tree_model: QtGui.QStandardItemModel = QtGui.QStandardItemModel()
        self.setModel(self.tree_model)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)
        self.evt_dispatch = None

        self.clicked.connect(self._click)
        self.doubleClicked.connect(self._dblclick)

    def _click(self, index):
        if self.evt_dispatch is not None:
            from eidolon.ui import MainWindowEvent

            obj = self.get_selected_object()
            self.evt_dispatch.trigger_event(MainWindowEvent._tree_clicked, obj=obj)

    def _dblclick(self, index):
        if self.evt_dispatch is not None:
            from eidolon.ui import MainWindowEvent

            obj = self.get_selected_object()
            self.evt_dispatch.trigger_event(MainWindowEvent._tree_dbl_clicked, obj=obj)

    def _menu(self, point):
        index = self.indexAt(point)

        if not index.isValid():
            return

        item = self.tree_model.itemFromIndex(index)
        idata = item.data()

        if getattr(idata, "menu") is not None:
            menu = create_menu(idata.menu[0], idata.menu[1:], lambda i: idata.menu_func(idata.obj, i))
            menu.exec_(self.mapToGlobal(point))

    def enum_all_items(self):
        def _enum(items):
            for item in items:
                yield item
                if item.hasChildren():
                    children = [item.child(r, 0) for r in range(item.rowCount())]
                    yield from _enum(children)

        yield from _enum(self.tree_model.findItems(".*", Qt.MatchRegExp))

    def update_icons(self):
        from eidolon.ui import IconName

        for item in self.enum_all_items():
            obj = item.data().obj
            is_visible = getattr(obj, "visible", None)
            if is_visible is not None:
                iname = IconName.eye if is_visible else IconName.eyeclosed
                item.setIcon(QtGui.QIcon(iname))

    def find_item(self, obj, search_list: Optional[list] = None) -> Optional[QtGui.QStandardItem]:
        return first(item for item in self.enum_all_items() if item.data() == obj)

    def get_selected_item(self) -> Optional[QtGui.QStandardItem]:
        indices = self.selectedIndexes()

        if len(indices) > 0:
            return self.tree_model.itemFromIndex(indices[0])

        return None

    def get_selected_object(self):
        item = self.get_selected_item()
        return item.data().obj if item is not None else None

    @qtmainthread
    def add_object(
        self,
        obj,
        text: str,
        icon: str,
        menu: Optional[List[str]],
        menu_func: Optional[Callable],
        prop: Optional[QtWidgets.QWidget],
        parent: Optional[Any],
    ) -> QtGui.QStandardItem:
        item = QtGui.QStandardItem(QtGui.QIcon(icon), text)
        item.setData(TreeItem(obj, menu=menu, menu_func=menu_func, prop=prop))
        parent_item = self.tree_model

        if parent is not None:
            parent_item = self.find_item(parent)

        parent_item.appendRow(item)
        self.expand(self.tree_model.indexFromItem(item))

        return item

    def remove_object(self, obj):
        item = self.find_item(obj)

        if item is None:
            raise ValueError(f"Object not found in tree view: {obj}")

        parent = item.parent() or self.tree_model
        parent.removeRow(item.row())
