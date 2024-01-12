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
import datetime
import threading
import time
from typing import List, Optional, Union

from PIL import Image

from eidolon.scene.camera_controller import Camera3DController
from eidolon.scene.mesh_scene_object import MeshSceneObject
from eidolon.scene.scene_object import SceneObject, SceneObjectRepr
from eidolon.scene.scene_plugin import ImageScenePlugin, MeshScenePlugin, ScenePlugin
from eidolon.ui import IconName, qtmainthread, MainWindowEvent
from eidolon.ui.threadsafe_calls import connect
from eidolon.ui.ui_utils import choose_file_dialog
from eidolon.utils import EventDispatcher, Namespace, TaskQueue, first
from eidolon.utils.path_utils import is_text_file
from eidolon.utils.thread_support import Future
from eidolon.utils.types import color

__all__ = ["SceneManager"]


class ManagerEvent(Namespace):
    object_added = Union[SceneObject, SceneObjectRepr]
    object_removed = Union[SceneObject, SceneObjectRepr]


class SceneManager(TaskQueue):
    global_instance = None
    global_plugins: List[ScenePlugin] = []

    @staticmethod
    def instance():
        return SceneManager.global_instance

    @staticmethod
    def add_plugin(plugin: ScenePlugin):
        SceneManager.global_plugins.append(plugin)

    @staticmethod
    def init(conf, win):
        if SceneManager.global_instance is None:
            SceneManager.global_instance = SceneManager(conf, win)

            # add default plugins
            SceneManager.global_plugins.insert(0, ImageScenePlugin("Image"))
            SceneManager.global_plugins.insert(0, MeshScenePlugin("Mesh"))

            for i, p in enumerate(SceneManager.global_plugins):
                p.init(i, SceneManager.global_instance)

            if win is not None:
                SceneManager.global_instance.ui_init()

        return SceneManager.global_instance

    def __init__(self, conf, win):
        super().__init__()
        self.conf = conf
        self.win = win

        self.evt_dispatch = EventDispatcher()

        # camera controller
        self.controller: Optional[Camera3DController] = None  # the camera controller

        # scene assets and objects
        self.cameras = []  # list of Camera objects, cameras[0] is "main" 3D perspective camera
        self.objects = []  # members of the scene, instances of SceneObject
        self.specs = []  # Existing spectrums
        self.mats = []  # Existing materials
        self.textures = []  # Existing textures
        self.lights = []  # existing light objects
        self.programs = []  # existing shader GPU program names

        # task related components
        # thread in which tasks are executed, None if no tasks are being run
        self.taskthread = threading.Thread(target=self._process_tasks)
        self.taskthread.daemon = True
        self.updatethread = None

        # time stepping components
        self.timestep = 0
        self.timestep_range = (0, 0)
        self.timestep_span = 0
        self.time_fps = 25
        self.timesteps_persec = 1.0
        self.playerEvent = threading.Event()
        self.player = threading.Thread(target=self._player_thread)
        self.player.daemon = True
        self.player.start()

        # script local variables
        self.scriptlocals = {"mgr": self}  # local environment object scripts are executed with
        self.lastScript = ""  # name of last executed script file

        self.cur_dir: str = os.getcwd()  # current directory

        self.taskthread.start()  # start taskthread here

    @qtmainthread
    def ui_init(self):
        w = self.win
        w.mgr=self

        w.treeView.evt_dispatch=self.evt_dispatch

        def _click(widg, func):
            widg.clicked.connect(func)

        _click(w.seeAllButton, self.set_camera_see_all)
        _click(w.clearButton, self.clear_scene)
        _click(w.removeObjectButton, self._remove_tree_object)

        self.evt_dispatch.add_handler(MainWindowEvent._tree_clicked,self.win.select_object)
        self.evt_dispatch.add_handler(MainWindowEvent._tree_dbl_clicked,self._tree_object_dblclick)

        w.actionTake_Screenshot.triggered.connect(lambda *_: self.take_screenshot())

        w.action_Open_Script.triggered.connect(self._load_script)

    def _process_tasks(self):
        """
        Takes tasks from the queue and runs them. This is executed in a separate daemon thread and should not be called.
        """
        assert threading.current_thread().daemon, "Task thread must be a daemon"

        # if self.conf.hasValue('args', 't'):
        #     setTrace()

        # if self.win is not None:  # wait for the window to appear
        #     while not self.win.isExec:
        #         time.sleep(0.01)

        def _update_status():
            """Status update action, this runs as a thread and continually updates the status bar."""
            # if self.conf.hasValue('args', 't'):
            #     setTrace()

            while True:
                try:
                    time.sleep(0.1)
                    self.set_task_status(*self.task_status())
                # ignores exceptions related to shutdown when UI objects get cleaned up before thread stops
                except:
                    pass

        self.updatethread = threading.Thread(target=_update_status)
        self.updatethread.start()  # also a daemon

        self.process_queue()  # process the queue

    def _player_thread(self):
        pass

    def task_except(self, ex, msg, title):
        print(ex, msg, title, flush=True)  # TODO: change to use GUI to show exception

    def get_plugin(self, name: str):
        return first(p for p in self.global_plugins if p.name == name)

    def set_task_status(self, task_label, cur_progress, max_progress):
        super().set_task_status(task_label, cur_progress, max_progress)

        if self.win:
            if task_label:
                self.win.set_status(task_label, cur_progress, max_progress)
            else:
                self.win.set_status("Ready", 0, 0)

    def exec_scripts_task(self, *filenames):
        def _exec_scripts():
            for idx, fn in enumerate(filenames):
                fn = os.path.abspath(fn)
                self.set_task_status(f"Executing {fn}", idx, len(filenames))
                self.exec_script(fn)

        self.add_func_task(_exec_scripts, "Execute scripts")

    def exec_script(self, filename, update_locals=True):
        """Executes the given script file using internal environment, updates local/console variables if `update_locals'."""
        if not os.path.isfile(filename):
            raise IOError(f"Cannot execute {filename} (not a file)")

        if not is_text_file(filename):
            raise IOError(f"Cannot execute {filename} (not a script file)")

        self.last_script = (filename, update_locals)  # save the path of the last script to run it again

        self.scriptlocals["scriptdir"] = os.path.split(os.path.abspath(filename))[0] + os.path.sep
        self.scriptlocals["task"] = self.current_task

        scriptlocals = self.scriptlocals
        if not update_locals:  # if not updating local variables, copy so stored version isn't changed
            scriptlocals = dict(scriptlocals)

        comp = compile(open(filename).read(), os.path.abspath(filename), "exec")
        exec(comp, scriptlocals, None)

        # if self.win and update_locals:
        # self.win.console.updateLocals(self.scriptlocals)

    def set_camera_see_all(self):
        """Move the camera to see all visible objects in the scene."""
        if self.controller is not None:
            self.controller.set_camera_see_all()

    def repaint(self):
        """Repaint the scene."""
        if self.controller is not None:
            self.controller.repaint()

    def update_ui(self):
        """Update UI elements to display correctly when state changes. This will do nothing if there's no UI."""
        if self.win:
            self.win.update_ui()

    def try_load_path(self, loadpath: str):
        """
        Attempt to find a plugin to load the file/directory at location `loadpath`, returning the loaded object or 
        None if nothing loaded because an acceptable plugin wasn't found.
        """
        for p in self.global_plugins:
            if p.accept_path(loadpath):
                obj = p.load_object(loadpath)
                self.add_scene_object(obj)
                return obj

        return None

    def add_scene_object(self, obj: SceneObject):
        if obj in self.objects:
            raise ValueError(f"Object already in scene: {obj}")

        if obj.plugin is None:
            if isinstance(obj, MeshSceneObject):
                obj.plugin = self.get_plugin("Mesh")
            # elif isinstance(obj, ImageSceneObject):
            # obj.plugin=self.get_plugin("Image")

        self.objects.append(obj)
        plugin: ScenePlugin = obj.plugin

        if self.win is not None:
            icon = plugin.get_icon(obj) or IconName.default
            menu, menu_func = plugin.get_menu(obj)
            prop = Future.get(plugin.get_properties_panel(obj))
            self.win.add_tree_object(
                obj=obj, text=obj.label, icon=icon, menu=menu, menu_func=menu_func, prop=prop, parent=None
            )

    def add_scene_object_repr(self, repr: SceneObjectRepr):
        if repr.parent not in self.objects:
            raise ValueError(f"Repr is not for an object in the scene: {repr}")

        for cam in self.controller.cameras():
            repr.plugin.attach_repr(repr, cam)

        if self.win is not None:
            prop = Future.get(repr.plugin.get_properties_panel(repr))

            # def _set_visible():
            #     self.set_visible(repr, prop.visibleCheckbox.isChecked())
            #     prop.show()

            # connect(prop.visibleCheckbox.stateChanged, _set_visible)

            item = self.win.add_tree_object(
                obj=repr, text=repr.label, icon=IconName.eye, menu=None, menu_func=None, prop=prop, parent=repr.parent
            )

        self.repaint()

    def add_object(self, obj: Union[SceneObject, SceneObjectRepr]):
        if isinstance(obj, SceneObject):
            self.add_scene_object(obj)
        else:
            self.add_scene_object_repr(obj)

    def remove_object(self, obj: Union[SceneObject, SceneObjectRepr]):
        if isinstance(obj, SceneObject):
            if obj not in self.objects:
                raise ValueError(f"Object not in scene: {obj}")

            for r in obj.reprs:
                self.remove_object(r)

            self.objects.remove(obj)
        elif isinstance(obj, SceneObjectRepr):
            for cam in self.controller.cameras():
                obj.plugin.detach_repr(obj, cam)

            obj.parent.remove_repr(obj)
        else:
            raise ValueError("Unknown argument type, should be SceneObject/SceneObjectRepr")

        if self.win is not None:
            self.win.remove_tree_object(obj)

        self.repaint()

    def clear_scene(self):
        for obj in list(self.objects):
            self.remove_object(obj)

    def take_screenshot(self, filename=None, camera=None):
        print(filename, camera)
        try:
            if filename is None:
                filename = datetime.datetime.now().strftime(os.path.join(self.cur_dir, "screenshot_%y%m%d_%H%M%S.png"))

            if camera is None:
                camera = self.cameras[0]

            @qtmainthread
            def _take_shot():
                cim = camera.get_memory_image()
                Image.fromarray(cim).save(filename)
                print(filename)

            self.repaint()
            _take_shot()
        except Exception as e:
            print(e)
            raise

    def _remove_tree_object(self):
        obj = self.win.get_selected_tree_object()
        if obj is not None:
            self.remove_object(obj)

    def _tree_object_dblclick(self, obj):
        if isinstance(obj, SceneObjectRepr):
            obj.visible=not obj.visible
            self.update_ui()
            self.repaint()

    def _load_script(self):
        filenames=self.win.choose_file_dialog("Select script file")
        if filenames:
            self.exec_scripts_task(os.path.abspath(filenames[0]))
            

