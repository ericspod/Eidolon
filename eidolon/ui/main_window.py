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
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt

from .loader import load_rc_layout

import eidolon
from ..utils.platform import is_darwin
from .ui_utils import resize_screen_relative, center_window, choose_file_dialog
from .console_widget import jupyter_present, JupyterWidget, ConsoleWidget
from .threadsafe_calls import qtmainthread
import threading

__all__ = ["MainWindow"]

main_title = '%s v%s (FOR RESEARCH ONLY)'

Ui_MainWindow = load_rc_layout("MainWindow")


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, conf, width=1200, height=800):
        super().__init__()
        self.conf = conf
        self.working_dir = os.getcwd()

        self.setupUi(self)
        self.setWindowTitle(main_title % (eidolon.__appname__, eidolon.__version__))
        self.setDockOptions(QtWidgets.QMainWindow.AllowNestedDocks)
        self.setAcceptDrops(True)

        self.action_About.triggered.connect(self._show_about)
        self.action_Scene_Elements.triggered.connect(
            lambda: self.interfaceDock.setVisible(not self.interfaceDock.isVisible()))
        self.action_Console.triggered.connect(lambda: self.consoleWidget.setVisible(not self.consoleWidget.isVisible()))
        self.action_Time.triggered.connect(lambda: self.timeWidget.setVisible(not self.timeWidget.isVisible()))
        self.actionScratch_Pad.triggered.connect(
            lambda: self.scratchWidget.setVisible(not self.scratchWidget.isVisible()))

        self.execButton.clicked.connect(self._execute_scratch)
        self.loadScratchButton.clicked.connect(self._load_scratch)
        self.saveScratchButton.clicked.connect(self._save_scratch)

        self.status_progress_bar = QtWidgets.QProgressBar()
        self.status_progress_bar.setMaximumWidth(200)
        self.status_progress_bar.setRange(0, 1)
        self.status_progress_bar.setValue(1)
        self.status_progress_bar.setFormat('%p% (%v / %m)')
        self.status_progress_bar.setTextVisible(True)
        self.status_progress_bar.setVisible(False)
        self.status_text = QtWidgets.QLabel(self)
        self.statusBar.addWidget(self.status_progress_bar)
        self.statusBar.addWidget(self.status_text)
        self.set_status('Ready')

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
        # v1.setRenderWinSize(width, height)

        self.raise_()  # bring window to front in OS X
        self.activateWindow()  # bring window to front in Windows (?)

        resize_screen_relative(self, 0.8, 0.8)
        center_window(self)

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
            self.toggleFullscreen()
        elif e.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(e)

    @qtmainthread
    def set_status(self, msg, progress=0, progressmax=0):
        if progressmax > 0 and is_darwin:
            msg = f"{(100.0 * progress) / progressmax:.0f} ({progress}/{progressmax} {msg}"

        self.status_text.setText(msg)
        self.status_progress_bar.setVisible(progressmax > 0)
        self.status_progress_bar.setRange(0, progressmax)
        self.status_progress_bar.setValue(progress)

    def _execute_scratch(self):
        """Execute the contents of the scratch pad line-by-line in the console, making it visible first."""
        self.consoleWidget.setVisible(True)
        text = str(self.scratchEdit.document().toPlainText())
        if text[-1] != '\n':
            text += '\n'

        self.console.send_input_block(text, False)

    def _load_scratch(self):
        # scratch = v1.chooseFileDialog('Choose Load Scratch Filename', chooseMultiple=False, isOpen=True)
        scratch = choose_file_dialog('Choose Load Scratch Filename', self)
        if scratch:
            self.working_dir = os.path.dirname(scratch[0])
            with open(scratch[0]) as o:
                self.scratchEdit.document().setPlainText(o.read())

    def _save_scratch(self):
        """Save the scratch pad contents to a chosen file."""
        # scratch = v1.chooseFileDialog('Choose Save Scratch Filename', chooseMultiple=False, isOpen=False)

        scratch = choose_file_dialog('Choose Save Scratch Filename', self, is_open=False)
        if scratch:
            self.working_dir = os.path.dirname(scratch[0])
            text = str(self.scratchEdit.document().toPlainText())
            if text[-1] != '\n':
                text += '\n'

            with open(scratch[0], 'w') as ofile:
                ofile.write(text)
