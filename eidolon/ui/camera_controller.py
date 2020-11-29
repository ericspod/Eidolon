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

from PyQt5 import QtGui, QtCore

from .camera_widget import CameraWidget, CameraWidgetEvents
from ..mathdef.mathtypes import vec3, rotator, transform
from ..mathdef.mathtypes import rad_clamp, rad_circular_convert

__all__=["CameraController"]

class CameraController:
    def __init__(self, camera, position, theta, phi, dist):
        self.camera = camera
        self.position = position
        self.theta = theta
        self.phi = phi
        self.dist = dist
        self.last_pos = None
        self.free_rotator = None
        self._is_z_locked = True
        self.phisub = 1e-5
        self.rscale = 5e-1

    def attach_events(self, events):
        pass

    def detach_events(self, events):
        pass

    def _mouse_pressed(self, widget: CameraWidget, evt: QtGui.QMouseEvent):
        self.last_pos = (evt.x(), evt.y())

    def _mouse_moved(self, widget: CameraWidget, evt: QtGui.QMouseEvent):
        if evt.button() == QtCore.Qt.LeftButton:
            self.drag_rotate_to(evt.x(), evt.y())

    @property
    def z_lock(self) -> bool:
        return self._is_z_locked

    @z_lock.setter
    def z_lock(self, is_locked):
        if is_locked:
            self._is_z_locked = True
            self.free_rotator = None
        else:
            self.free_rotator = self.get_rotator()
            self._is_z_locked = False

    def get_rotator(self):
        """
        Get the rotator for the camera based on self.theta and self.phi or self.freerotator. This represents the
        rotation applied to orient the camera to face the look at position and a given up direction from the initial
        position as defined by this controller.
        """
        if self._is_z_locked:
            rot = rotator.from_axis(vec3.Z, -self.theta)
            return rotator.from_axis(rot * vec3.X, -self.phi) * rot
        else:
            return self.free_rotator

    def set_rotation(self, theta_r, phi=0):
        """
        Sets rotational parameters. If z_lock is True, `theta_r' and  `phi' are polar rotation values, these are
        used to set self.theta and self.phi contrained within their respective ranges and tolerances. If z_lock
        is False then `theta_r' is a rotator which is assigned to self.freerotator.
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

        # self.set_camera_position()

    def rotate(self, dx_r, dy=0):
        """
        Rotate the camera using the given arguments. If the camera is Z-locked (z_lock is True), `dx_r' is a
        float value scaled by self.rScale*0.005 then added to self.theta and `dy' is also a float scaled by
        self.rScale*0.005 then added to self.phi. If the camera is not Z-locked, `dx_r' is a rotator applied to the
        camera's rotation.
        """
        if self._is_z_locked:
            self.set_rotation(self.theta + float(dx_r) * 0.005 * self.rscale,
                              self.phi + float(dy) * 0.005 * self.rscale)
        else:
            self.set_rotation(dx_r * self.free_rotator)

    def set_camera_position(self):
        rot = self.get_rotator()
        campos = (rot * vec3(0, -self.dist, 0)) + self.position

        self.camera.camera.set_pos(*campos)
        self.camera.camera.look_at(*self.position)

    def drag_rotate_to(self, dx, dy):
        if self.last_pos is not None:
            lx, ly = self.last_pos
            self.rotate(dx - lx, dy - ly)

        self.last_pos = (dx, dy)
        # self.set_camera_position()
