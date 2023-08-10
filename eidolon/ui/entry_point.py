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

from pathlib import Path
import sys
from eidolon.resources import read_text, has_resource
from eidolon.mathdef import vec3
from eidolon.ui import MainWindow, exec_ui, init_ui, CameraWidget
from eidolon.renderer import OffscreenCamera


__all__ = ["create_default_app", "default_entry_point"]

def create_default_app(argv=None):
    from eidolon.scene import QtCameraController
    from eidolon import config

    conf = config.load_config()

    app = init_ui()

    app.setStyle("plastique")
    sheet=""
    sheet_path=Path(conf.get("stylesheet", "DefaultUIStyle.css"))
    if sheet_path.exists():
        with open(str(sheet_path)) as o:
            sheet=o.read()
    else:
        sheet_name=conf.get("stylesheet", "DefaultUIStyle.css")
        if has_resource(sheet_name+".css"):
            sheet_name+=".css"

        if has_resource(sheet_name):
            sheet=read_text(sheet)

    app.setStyleSheet(sheet)

    win = MainWindow(conf)

    cam = OffscreenCamera("test", 400, 400)

    camwidget = CameraWidget(cam)

    ctrl = QtCameraController(cam, vec3.zero, 0, 0, 50)
    ctrl.attach_events(camwidget.events)

    win.setCentralWidget(camwidget)

    return app, win, cam, ctrl


def default_entry_point(argv=None):
    if argv is None:
        argv=sys.argv

    app, win, _, _ = create_default_app(argv)

    win.show()

    exec_ui(app)


