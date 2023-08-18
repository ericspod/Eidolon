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
from pathlib import Path

from eidolon.mathdef import vec3
from eidolon.renderer import Light, LightType, OffscreenCamera
from eidolon.resources import has_resource, read_text
from eidolon.ui import CameraWidget, MainWindow, add_search_path, exec_ui, init_ui

__all__ = ["create_default_app", "default_entry_point"]


def create_default_app(argv=None):
    from eidolon.scene import QtCameraController, SceneManager
    from eidolon.utils.config import ConfigVarNames, load_config

    conf = load_config()

    app = init_ui()

    app.setStyle(conf.get(ConfigVarNames._uistyle, ConfigVarNames.uistyle[0]))
    sheet = ""
    sheet_value = conf.get(ConfigVarNames._stylesheet, ConfigVarNames.stylesheet[0])
    if Path(sheet_value).is_file():
        with open(str(sheet_value)) as o:
            sheet = o.read()
    elif has_resource(sheet_value):
        sheet = read_text(sheet_value)

    app.setStyleSheet(sheet)

    add_search_path("icons", "icons")

    win = MainWindow(conf)

    cam = OffscreenCamera("test", 400, 400)

    camwidget = CameraWidget(cam)

    ctrl = QtCameraController(cam, vec3.zero, 0, 0, 50)
    ctrl.attach_events(camwidget.events)

    win.setCentralWidget(camwidget)

    mgr = SceneManager(conf, win)
    mgr.cameras.append(cam)
    mgr.controller = ctrl

    amb = Light("amb", LightType.AMBIENT, (0.3, 0.3, 0.3, 1))
    amb.attach(cam)
    mgr.lights.append(amb)

    return app, mgr


def default_entry_point(argv=None):
    if argv is None:
        argv = sys.argv

    app, mgr = create_default_app(argv)

    mgr.win.show()

    exec_ui(app)
