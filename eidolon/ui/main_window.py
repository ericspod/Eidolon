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

import sys
import textwrap
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt

from .loader import load_rc_layout

import eidolon

__all__=["MainWindow"]


main_title = '%s v%s (FOR RESEARCH ONLY)'

Ui_MainWindow = load_rc_layout("MainWindow")


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, width=1200, height=800):
        super().__init__()

        self.setupUi(self)
        self.setWindowTitle(main_title % (eidolon.__appname__, eidolon.__version__))
        self.setDockOptions(QtWidgets.QMainWindow.AllowNestedDocks)
        self.setAcceptDrops(True)

        self.action_About.triggered.connect(self._show_about)

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

    # def _check_version(self):
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
    #         self.showMsg(textwrap.dedent(msg), title)
    #     except Exception as e:
    #         QtWidgets.QMessageBox.about(self, title, repr(e))

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_F11:
            self.toggleFullscreen()
        elif e.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(e)
