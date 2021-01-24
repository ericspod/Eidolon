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

import math
from typing import Union

from PyQt5 import QtGui, QtCore

from .camera_widget import CameraWidget, CameraWidgetEvent
from ..renderer import OffscreenCamera
from ..mathdef.math_types import vec3, rotator
from ..mathdef.math_utils import rad_clamp, rad_circular_convert

from ..utils import timing

__all__ = ["CameraController"]


class CameraController:
    def __init__(self, camera: OffscreenCamera, position: vec3, theta: float, phi: float, dist: float):
        self.camera: OffscreenCamera = camera
        self._position: vec3 = position
        self.theta: float = theta
        self.phi: float = phi
        self._dist: float = dist
        self.last_pos = None
        self.free_rotator = None
        self._is_z_locked = True
        self.phisub: float = 1e-5
        self.rscale: float = 5e-3
        self.tscale: float = 1e-1
        self.zscale: float = 1e-1

        self.apply_camera_position()

    def attach_events(self, events):
        events.add_handler(CameraWidgetEvent._mouse_pressed, self._mouse_pressed)
        events.add_handler(CameraWidgetEvent._mouse_moved, self._mouse_moved)
        events.add_handler(CameraWidgetEvent._mouse_wheel, self._mouse_wheel)

    def detach_events(self, events):
        events.remove_handler(self._mouse_pressed)
        events.remove_handler(self._mouse_moved)
        events.remove_handler(self._mouse_wheel)

    def _mouse_pressed(self, widget: CameraWidget, event: QtGui.QMouseEvent):
        self.last_pos = (event.x(), event.y())

    def _mouse_moved(self, widget: CameraWidget, event: QtGui.QMouseEvent):
        dx = event.x() - self.last_pos[0]
        dy = event.y() - self.last_pos[1]

        if event.buttons() == QtCore.Qt.LeftButton:
            self.rotate(dx, dy)
        elif event.buttons() == QtCore.Qt.RightButton:
            self.translate_camera_relative(-dx, 0, dy)
        elif event.buttons() == QtCore.Qt.MiddleButton:
            self.zoom(dy)
        elif event.buttons() == (QtCore.Qt.LeftButton | QtCore.Qt.RightButton):
            self.translate_camera_relative(0, -dy, 0)

        self.apply_camera_position()
        widget.repaint_on_ready()
        self.last_pos = (event.x(), event.y())

    def _mouse_wheel(self, widget: CameraWidget, event: QtGui.QWheelEvent):
        self.zoom(-event.angleDelta().y())
        self.apply_camera_position()
        widget.repaint_on_ready()

    @property
    def z_lock(self) -> bool:
        return self._is_z_locked

    @z_lock.setter
    def z_lock(self, is_locked):
        if is_locked:
            self._is_z_locked = True
            self.free_rotator = None
        else:
            self.free_rotator = self.get_rotation()
            self._is_z_locked = False

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, value):
        self._position = value
        # self.apply_camera_position()

    @property
    def dist(self):
        return self._dist

    @dist.setter
    def dist(self, value):
        self._dist = max(5 * self.zscale, value)

    def get_rotation(self):
        """
        Get the rotator for the camera based on v1.theta and v1.phi or v1.freerotator. This represents the
        rotation applied to orient the camera to face the look at position and a given up direction from the initial
        position as defined by this controller.
        """
        if self._is_z_locked:
            rot = rotator.from_axis(vec3.Z, -self.theta)
            return rotator.from_axis(rot * vec3.X, -self.phi) * rot
        else:
            return self.free_rotator

    def set_rotation(self, theta_r: float, phi: float = 0):
        """
        Sets rotational parameters. If z_lock is True, `theta_r' and  `phi' are polar rotation values, these are
        used to set v1.theta and v1.phi contrained within their respective ranges and tolerances. If z_lock
        is False then `theta_r' is a rotator which is assigned to v1.freerotator.
        """
        if self._is_z_locked:
            self.theta = rad_circular_convert(theta_r)
            self.phi = rad_clamp(phi)
            self.phi += self.phisub * (-1 if self.phi > 0 else 1)
        else:
            if isinstance(theta_r, rotator):
                self.free_rotator = theta_r
            else:
                self.free_rotator = rotator.from_axis(vec3.Z, theta_r)

    def rotate(self, dx_r: Union[float, rotator], dy: float = 0):
        """
        Rotate the camera using the given arguments. If the camera is Z-locked (z_lock is True), `dx_r' is a
        float value scaled by v1.rScale*0.005 then added to v1.theta and `dy' is also a float scaled by
        v1.rScale*0.005 then added to v1.phi. If the camera is not Z-locked, `dx_r' is a rotator applied to the
        camera's rotation.
        """
        if self._is_z_locked:
            self.set_rotation(self.theta + dx_r * self.rscale, self.phi + dy * self.rscale)
        else:
            self.set_rotation(dx_r * self.free_rotator)

    def translate(self, trans: vec3):
        self.position += trans

    def translate_camera_relative(self, dx, dy, dz):
        """Translate relative to the orientation (Y-forward, Z-up) defined by the camera's rotator."""
        rot = self.get_rotation()
        self.translate(rot * (vec3(dx, dy, dz) * self.tscale))

    def zoom(self, dz: float):
        self.dist += dz * self.zscale

    def move_see_all(self):
        aabb = self.camera.scene_aabb
        radius = max(0.0001, aabb.radius)
        fov = max(self.camera.fov)

        self.position = aabb.center
        self.dist = (radius * 0.5) / math.tan(fov * 0.5) + radius * 1.5
        self.zscale = radius * 0.005
        self.tscale = radius * 0.00125
        # self.radiusPower = Utils.getClosestPower(radius) - 1

        self.apply_camera_position()

    def apply_camera_position(self):
        rot = self.get_rotation()
        campos = (rot * vec3(0, -self.dist, 0)) + self.position
        up = rot * vec3.Z

        self.camera.set_camera_lookat(campos, self.position, up)
