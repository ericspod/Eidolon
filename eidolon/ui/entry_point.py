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

__all__ = ["create_default_app", "default_entry_point", "task_entry_point"]


def create_default_app(argv=None):
    """
    Configure and create the default application with manager and main window. The manager and QApplication is returned.
    """
    from eidolon.mathdef import vec3
    from eidolon.renderer import Light, LightType, OffscreenCamera
    from eidolon.resources import has_resource, read_text
    from eidolon.ui import CameraWidget, MainWindow, add_search_path, init_ui, rename_ui_paths
    from eidolon.scene import QtCamera3DController, SceneManager
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

    app.setStyleSheet(rename_ui_paths(sheet))

    add_search_path("icons", "icons")

    win = MainWindow(conf)

    cam = OffscreenCamera("test", 400, 400)
    camwidget = CameraWidget(cam)

    ctrl = QtCamera3DController(cam, vec3.zero, 0, 0, 50, camwidget.repaint_on_ready)
    ctrl.attach_events(camwidget.events)

    win.setCentralWidget(camwidget)

    mgr = SceneManager.init(conf, win)

    mgr.cameras.append(cam)
    mgr.controller = ctrl

    amb = Light("amb", LightType.AMBIENT, (0.3, 0.3, 0.3, 1))
    amb.attach(cam)

    dlight = Light("dlight", LightType.DIRECTIONAL, (0.5, 0.5, 0.5, 1))
    dlight.attach(cam, True)

    mgr.lights+=[amb, dlight]

    return app, mgr


def default_entry_point(argv=None):
    """
    Entry point which calls `create_default_app` and just execs the UI once the window is shown.
    """
    from eidolon.ui import exec_ui

    if argv is None:
        argv = sys.argv

    app, mgr = create_default_app(argv)

    mgr.win.show()

    exec_ui(app)


def task_entry_point(func_task, argv=None):
    """
    Entry point for program with `func_task` executed as a task item after the UI is shown.
    """
    from eidolon.ui import exec_ui

    if argv is None:
        argv = sys.argv

    app, mgr = create_default_app(argv)

    def _taskwrapper():
        mgr.set_task_status("Running task function", 0, 1)
        func_task(mgr) 

    mgr.win.show()

    mgr.add_func_task(_taskwrapper)

    exec_ui(app)
