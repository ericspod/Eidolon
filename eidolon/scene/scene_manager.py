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

import threading
import time
from typing import Union, List, Optional
from .scene_object import SceneObject, SceneObjectRepr
from .scene_plugin import ScenePlugin, MeshScenePlugin
from .camera_controller import CameraController
from ..utils import Namespace, TaskQueue, EventDispatcher, first
from ..ui import IconName, qtmainthread

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
        self.controller: Optional[CameraController] = None  # the camera controller

        # scene assets and objects
        self.cameras = []  # list of Camera objects, cameras[0] is "main" 3D perspective camera
        self.objects = []  # members of the scene, instances of SceneObject
        self.specs = []  # Existing spectrums
        self.mats = []  # Existing materials
        self.textures = []  # Existing textures
        self.lights = []  # existing light objects
        self.programs = []  # existing Vertex/Fragment shader GPU programs

        self.ambient_color = (1, 1, 1, 1)
        self.background_color = (1, 1, 1, 1)

        # # secondary scene elements
        # self.bbmap = {}  # maps representations to their bounding boxes
        # self.handlemap = {}  # maps representations to their handles (Repr -> list<Handle>), only populated when handles are first requested

        # task related components
        # thread in which tasks are executed, None if no tasks are being run
        self.taskthread = threading.Thread(target=self._process_tasks)
        self.taskthread.daemon = True
        self.updatethread = None

        # # scene component controllers
        # self.matcontrol = SceneComponents.MaterialController(self,
        #                                                      self.win)  # the material controller responsible for all materials
        # self.lightcontrol = SceneComponents.LightController(self,
        #                                                     self.win)  # the light controller responsible for light UI
        # self.progcontrol = SceneComponents.GPUProgramController(self,
        #                                                         self.win)  # the shader GPU program controller responsible for the UI

        # time stepping components
        self.timestep = 0
        self.timestepMin = 0
        self.timestepMax = 0
        self.timestepSpan = 0
        self.timeFPS = 25
        self.timeStepsPerSec = 1.0
        self.playerEvent = threading.Event()
        self.player = threading.Thread(target=self._player_thread)
        self.player.daemon = True
        self.player.start()

        # script local variables
        self.scriptlocals = {'mgr': self}  # local environment object scripts are executed with
        self.lastScript = ''  # name of last executed script file

        # if self.conf.hasValue('var', 'names'):  # add command line variables to the script variable map
        #     names = self.conf.get('var', 'names').split('|')
        #     for n in names:
        #         self.scriptlocals[n] = self.conf.get('var', n)

        # def exceptionHook(exctype, value, tb):
        #     msg = '\n'.join(traceback.format_exception(exctype, value, tb))
        #     self.showExcept(value, str(value), 'Unhandled Exception', msg)
        #
        # sys.excepthook = exceptionHook

        # # create default plugins for meshes and images added to the manager without one provided
        # self.meshplugin = ScenePlugin.MeshScenePlugin('MeshPlugin')
        # self.imageplugin = ScenePlugin.ImageScenePlugin('ImgPlugin')
        #
        # self.meshplugin.init(0, self.win, self)
        # self.imageplugin.init(1, self.win, self)

        # global globalPlugins
        # globalPlugins = [self.meshplugin, self.imageplugin] + globalPlugins
        #
        # for plug in globalPlugins:
        #     self.scriptlocals[plug.name.replace(' ', '_')] = plug

        if self.win is not None:  # window setup
            self.win.mgr = self
            # self.scene = self.win.scene
        #
        #     self.evtHandler = self.win.viz.evtHandler
        #
        #     if self.win.console:
        #         self.win.console.updateLocals(self.scriptlocals)
        #         self.win.consoleWidget.setVisible(conf.hasValue('args', 'c'))
        #
        #     self.callThreadSafe(self._windowConnect)

        # # set config values
        # if self.conf.get(platformID, 'renderhighquality').lower() == 'true':
        #     self.setAlwaysHighQual(True)
        #
        # # add the necessary repaint handlers to respond to mouse actions
        # self.addEventHandler(EventType._mousePress, lambda _: self.repaint(False), isPostEvent=True)
        # self.addEventHandler(EventType._mouseRelease, lambda _: self.repaint(False), isPostEvent=True)
        # self.addEventHandler(EventType._mouseMove, lambda _: self.repaint(False), isPostEvent=True)
        # self.addEventHandler(EventType._mouseWheel, lambda _: self.repaint(False), isPostEvent=True)
        #
        # self.addEventHandler(EventType._widgetPreDraw, self._updateUI)  # update UI when redrawing
        # self.addEventHandler(EventType._widgetPreDraw,
        #                      self._updateManagedObjects)  # update boxes and handles before drawing
        # self.addEventHandler(EventType._widgetPostDraw,
        #                      self._repaintHighQual)  # repaint again in high quality if the first paint was in low quality
        # self.addEventHandler(EventType._mousePress, self._mousePressHandleCheck)  # transmit mouse presses to handles
        # self.addEventHandler(EventType._mouseMove, self._mouseMoveHandleCheck)  # transmit mouse moves to handles
        # self.addEventHandler(EventType._mouseRelease,
        #                      self._mouseReleaseHandleCheck)  # transmit mouse release to handles
        # self.addEventHandler(EventType._keyPress, self._keyPressEvent)

        self.taskthread.start()  # start taskthread here

    @qtmainthread
    def ui_init(self):
        print("ui_init")
        self.win.seeAllButton.clicked.connect(self.set_camera_see_all)

    def get_plugin(self, name: str):
        return first(p for p in self.global_plugins if p.name == name)

    def _process_tasks(self):
        """
        Takes tasks from the queue and runs them. This is executed in a separate daemon thread and should not be called.
        """
        assert threading.currentThread().daemon, 'Task thread must be a daemon'

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

    def set_task_status(self, task_label, cur_progress, max_progress):
        pass

    def _player_thread(self):
        pass

    def set_camera_see_all(self):
        if self.controller is not None:
            self.controller.set_camera_see_all()

    def add_scene_object(self, obj: SceneObject):
        if obj in self.objects:
            raise ValueError("Object already in scene")

        self.objects.append(obj)
        plugin: ScenePlugin = obj.plugin

        if self.win is not None:
            icon = plugin.get_icon(obj) or IconName.default
            # menu=plugin.get_menu(obj)
            self.win.add_tree_object(obj, obj.label, icon)

    def add_scene_object_repr(self, rep: SceneObjectRepr):
        for cam in self.controller.cameras():
            rep.plugin.attach_repr(rep, cam)

        if self.win is not None:
            icon = IconName.eye
            self.win.add_tree_object(rep, rep.label, icon, rep.parent)

    def remove_object(self, obj: Union[SceneObject, SceneObjectRepr]):
        if isinstance(obj, SceneObject):
            if obj not in self.objects:
                raise ValueError("Object not in scene")

            for r in obj.reprs:
                self.remove_object(r)

            self.objects.remove(obj)
        elif isinstance(obj, SceneObjectRepr):
            for cam in self.controller.cameras():
                obj.plugin.dettach_repr(obj, cam)

            obj.visible = False
        else:
            raise ValueError("Unknown argument type, should be SceneObject/SceneObjectRepr")

        if self.win is not None:
            self.win.remove_tree_object(obj)