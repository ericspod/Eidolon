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

import os
import sys
import textwrap
import warnings
from typing import Any, Callable, Optional, List

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt

import eidolon
from eidolon.utils import Namespace, is_darwin

from eidolon.ui.console_widget import ConsoleWidget, JupyterWidget, jupyter_present
from eidolon.ui.loader import load_res_layout
from eidolon.ui.threadsafe_calls import qtmainthread
from eidolon.ui.ui_utils import center_window, choose_file_dialog, resize_screen_relative, create_menu

__all__ = ["IconName", "MainWindow"]

main_title = "%s v%s (FOR RESEARCH ONLY)"

Ui_MainWindow = load_res_layout("main_window.ui")


class IconName(Namespace):
    """Names of icons mapped to the filename in loaded resources."""

    default = "icons:document.png"
    mesh = "icons:cube.png"
    image = "icons:image.png"
    eye = "icons:eye.png"
    eyeclosed = "icons:eye-disabled.png"
    bars = "icons:stats-bars.png"
    help = "icons:help-circled.png"
    scissors = "icons:scissors.png"
    trash = "icons:trash-a.png"
    seg = "icons:seg.png"
    clipboard = "icons:clipboard.png"


class TreeItem:
    def __init__(self, obj, **named_values):
        self.obj = obj
        for k, v in named_values.items():
            setattr(self, k, v)

    def __eq__(self, value: object) -> bool:
        return self.obj == value


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, conf, width=1200, height=800):
        super().__init__()
        self.conf: dict = conf
        self.mgr = None
        self.working_dir: str = os.getcwd()

        self.setupUi(self)
        self.setWindowTitle(main_title % (eidolon.__appname__, eidolon.__version__))
        self.setDockOptions(QtWidgets.QMainWindow.AllowNestedDocks)
        self.setAcceptDrops(True)

        self.tree_model: QtGui.QStandardItemModel = QtGui.QStandardItemModel()
        self.treeView.setModel(self.tree_model)
        self.treeView.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.treeView.customContextMenuRequested.connect(self._menu_tree_view)

        self.action_About.triggered.connect(self._show_about)
        self.action_Scene_Elements.triggered.connect(
            lambda: self.interfaceDock.setVisible(not self.interfaceDock.isVisible())
        )
        self.action_Console.triggered.connect(lambda: self.consoleWidget.setVisible(not self.consoleWidget.isVisible()))
        self.action_Time.triggered.connect(lambda: self.timeWidget.setVisible(not self.timeWidget.isVisible()))
        self.actionScratch_Pad.triggered.connect(
            lambda: self.scratchWidget.setVisible(not self.scratchWidget.isVisible())
        )

        # self.execButton.clicked.connect(self._execute_scratch)
        # self.loadScratchButton.clicked.connect(self._load_scratch)
        # self.saveScratchButton.clicked.connect(self._save_scratch)

        self.status_progress_bar = QtWidgets.QProgressBar()
        self.status_progress_bar.setMaximumWidth(200)
        self.status_progress_bar.setRange(0, 1)
        self.status_progress_bar.setValue(1)
        self.status_progress_bar.setFormat("%p% (%v / %m)")
        self.status_progress_bar.setTextVisible(True)
        self.status_progress_bar.setVisible(False)
        self.status_text = QtWidgets.QLabel(self)
        self.statusBar.addWidget(self.status_progress_bar)
        self.statusBar.addWidget(self.status_text)
        self.set_status("Ready")

        if jupyter_present and conf.get("usejupyter", True):
            try:
                self.console = JupyterWidget(self, conf)
            except Exception as e:
                warnings.warn(f"Cannot create Jupyter console widget, defaulting to internal console:\n {e}")
                self.console = ConsoleWidget(self, conf)
        else:
            warn_suffix = "" if jupyter_present else ", Jupyter QtConsole not present or disabled"
            warnings.warn("Using internal console" + warn_suffix)
            self.console = ConsoleWidget(self, conf)

        self.consoleLayout.addWidget(self.console)

        self.consoleWidget.setVisible(False)  # hide the console by default

        self.timeWidget.setVisible(False)  # hide the time dialog by default
        self.scratchWidget.setVisible(False)  # hide the scratch pad by default

        # force a relayout
        self.resize(width, height + 1)
        self.show()
        # self.setRenderWinSize(width, height)

        self.raise_()  # bring window to front in OS X
        self.activateWindow()  # bring window to front in Windows (?)

        resize_screen_relative(self, 0.8, 0.8)
        center_window(self)

    # def _connect_components(self):
    #     self.removeObjectButton.clicked.connect(self._remove_button)

    def _show_about(self):
        """Show the about dialog box."""
        msg = f"""
            {eidolon.__appname__}
            {eidolon.__copyright__}
            
            Version: {eidolon.__version__}
            Python Version: {sys.version}
            Qt Version: {str(QtCore.qVersion())}
            PyQt Version: {QtCore.PYQT_VERSION_STR}
        """

        QtWidgets.QMessageBox.about(self, f"About {eidolon.__appname__}", textwrap.dedent(msg))

    # def _check_version(v1):
    #     """
    #     Check the application version against the repository API URL and show the results with the link to the site.
    #     """
    #     url = eidolon.__verurl__
    #     title = 'Checking Version'
    #
    #     try:
    #         cver, nver, isnew = Utils.getVersionsFromRepoURL(url)
    #         msg = '''Current Version: %s<br>
    #                Newest Version: %s<br><br>
    #                <a href="%s">Download latest release.</a>
    #             ''' % (cver, nver or '???', eidolon.__website__)
    #
    #         v1.showMsg(textwrap.dedent(msg), title)
    #     except Exception as e:
    #         QtWidgets.QMessageBox.about(v1, title, repr(e))

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_F11:
            self.toggle_fullscreen()
        elif e.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(e)

    def dragEnterEvent(self, e):
        if e.mimeData().hasText():
            e.accept()
        else:
            e.ignore()

    def dropEvent(self, e):
        pass

    def _menu_tree_view(self, point):
        index = self.treeView.indexAt(point)

        if not index.isValid():
            return

        item = self.tree_model.itemFromIndex(index)
        idata = item.data()
        if getattr(idata, "menu") is not None:
            menu = create_menu(idata.menu[0], idata.menu[1:], lambda i: idata.menu_func(idata.obj, i))
            menu.exec_(self.treeView.mapToGlobal(point))

    @qtmainthread
    def set_status(self, msg, progress=0, progressmax=0):
        if progressmax > 0 and is_darwin:
            msg = f"{(100.0 * progress) / progressmax:.0f} ({progress}/{progressmax} {msg}"

        self.status_text.setText(msg)
        self.status_progress_bar.setVisible(progressmax > 0)
        self.status_progress_bar.setRange(0, progressmax)
        self.status_progress_bar.setValue(progress)

    @qtmainthread
    def add_menu_item(self, menu_name, obj_name, text, func):
        """
        Add a menu item to the menu `menu_name', which must be one of ('File','Import','Export','Create','Project').
        The menu item is named `obj_name' with label `text', when clicked `callback' will be called with no arguments.
        """
        assert menu_name in ("File", "Import", "Export", "Create", "Project")

        action = QtWidgets.QAction(self)
        action.setObjectName(obj_name)
        action.setText(text)
        action.triggered.connect(func)

        if menu_name == "File":
            self.menuFile.insertAction(self.action_Quit, action)
        elif menu_name == "Import":
            self.menuImport.addAction(action)
        elif menu_name == "Export":
            self.menuExport.addAction(action)
        elif menu_name == "Create":
            self.menuCreate.addAction(action)
        elif menu_name == "Project":
            self.menu_New_Project.addAction(action)

        return action

    def choose_file_dialog(
        self,
        title,
        opendir=None,
        filterstr="",
        is_open=True,
        choose_multiple=False,
        confirm_overwrite=True,
        parent=None,
    ):
        parent = parent or self
        opendir = opendir or self.working_dir

        results = choose_file_dialog(title, parent, opendir, filterstr, is_open, choose_multiple, confirm_overwrite)

        if results:
            self.working_dir = os.path.dirname(os.path.abspath(results[0]))

        return results

    def toggle_fullscreen(self):
        pass

    # @qtmainthread
    # def show_msg(self, msg, title='Message', text=None, width=600, height=300):
    #     """
    #     Shows the string `msg' in a message dialog with the given title. If `text' is not None, this is displayed in
    #     a text box within a message dialog that recalls previous messages, otherwise a simple dialog is used.
    #     """
    #     if text is None:
    #         box = QtWidgets.QMessageBox(self)
    #         box.setText(msg)
    #         box.setWindowTitle(title)
    #         box.show()
    #     else:
    #         self.msgdialog.addMsg(title, msg, str(text), width, height)

    def find_tree_item(self, obj, search_list: Optional[list] = None):
        if search_list is None:
            search_list = self.tree_model.findItems(".*", Qt.MatchRegExp)

        for item in search_list:
            if item.data() == obj:
                return item
            elif item.hasChildren():
                child = self.find_tree_item(obj, [item.child(r, 0) for r in range(item.rowCount())])
                if child is not None:
                    return child

        return None

    def get_selected_tree_object(self):
        indices = self.treeView.selectedIndexes()

        if len(indices) > 0:
            item = self.tree_model.itemFromIndex(indices[0])
            return item.data().obj
        else:
            return None

    def set_object_icon(self, obj, icon_name: str):
        item = self.find_tree_item(obj)
        if item is not None:
            item.setIcon(QtGui.QIcon(icon_name))

    def add_tree_object(
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
            parent_item = self.find_tree_item(parent)

        parent_item.appendRow(item)
        self.treeView.expand(self.tree_model.indexFromItem(item))

        return item

    def remove_tree_object(self, obj):
        item = self.find_tree_item(obj)

        if item is None:
            raise ValueError(f"Object not found in tree view: {obj}")

        parent = item.parent() or self.tree_model
        parent.removeRow(item.row())

    # def _execute_scratch(self):
    #     """Execute the contents of the scratch pad line-by-line in the console, making it visible first."""
    #     self.consoleWidget.setVisible(True)
    #     text = str(self.scratchEdit.document().toPlainText())
    #     if text[-1] != "\n":
    #         text += "\n"

    #     self.console.send_input_block(text, False)

    # def _load_scratch(self):
    #     # scratch = v1.chooseFileDialog('Choose Load Scratch Filename', chooseMultiple=False, isOpen=True)
    #     scratch = choose_file_dialog("Choose Load Scratch Filename", self)
    #     if scratch:
    #         self.working_dir = os.path.dirname(scratch[0])
    #         with open(scratch[0]) as o:
    #             self.scratchEdit.document().setPlainText(o.read())

    # def _save_scratch(self):
    #     """Save the scratch pad contents to a chosen file."""
    #     # scratch = v1.chooseFileDialog('Choose Save Scratch Filename', chooseMultiple=False, isOpen=False)

    #     scratch = choose_file_dialog("Choose Save Scratch Filename", self, is_open=False)
    #     if scratch:
    #         self.working_dir = os.path.dirname(scratch[0])
    #         text = str(self.scratchEdit.document().toPlainText())
    #         if text[-1] != "\n":
    #             text += "\n"

    #         with open(scratch[0], "w") as ofile:
    #             ofile.write(text)

    # def _remove_button(self):
    #     obj = self.get_selected_tree_object()
