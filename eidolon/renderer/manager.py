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

from threading import RLock

from panda3d.core import loadPrcFileData, Thread

from direct.showbase.ShowBase import ShowBase


class Manager(ShowBase):
    def __init__(self, width=800, height=600):
        loadPrcFileData("", f"win-size {width} {height}")
        loadPrcFileData("", "window-type offscreen")
        ShowBase.__init__(self)

        self.disableMouse()
        self.disable_all_audio()
        self.disable_particles()
        self.lock = RLock()

    def update(self):
        with self.lock:
            if self.is_ready():
                self.taskMgr.step()

    def is_ready(self):
        with self.lock:
            return Thread.getCurrentThread().getCurrentTask() is None
