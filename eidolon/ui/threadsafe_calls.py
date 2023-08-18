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
import traceback
from functools import wraps

from PyQt5 import QtCore
from PyQt5.QtCore import Qt

from ..utils import Future, is_main_thread

__all__ = ["qtmainthread", "delayedmethod"]


class MainThreadEvent(QtCore.QEvent):
    EVENT_TYPE = QtCore.QEvent.Type(QtCore.QEvent.registerEventType())

    def __init__(self, func, args, kwargs, result):
        super().__init__(self.EVENT_TYPE)
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.result = result


class MainThreadCaller(QtCore.QObject):
    def event(self, event):
        event.accept()
        with event.result:
            res = event.func(*event.args, **event.kwargs)
            event.result.set_result(res)

        return True


# global persistent instance created in the mainthread
_mt_caller = MainThreadCaller()


def call_mainthread(func, *args, **kwargs):
    if is_main_thread():
        return func(*args, **kwargs)
    else:
        result = Future()
        evt = MainThreadEvent(func, args, kwargs, result)
        QtCore.QCoreApplication.postEvent(_mt_caller, evt)
        return result


def qtmainthread(func):
    """
    Executes the decorated function/method in the main thread using Qt's event system.
    """

    @wraps(func)
    def _wrapper(*args, **kwargs):
        return call_mainthread(func, *args, **kwargs)

    return _wrapper


def connect(signal, func):
    """
    Connects the callable `func` to the given signal in the main thread.
    """
    call_mainthread(signal.connect, func)


class DelayedCall:
    def __init__(self, func, timeout):
        self.func = func
        self.timeout = timeout
        self.args = None
        self.kwargs = None

        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._call)

    def _call(self):
        try:
            self.func(*self.args, **self.kwargs)
        except:
            print(traceback.format_exc(), file=sys.stderr, flush=True)

    def start(self, *args, **kwargs):
        if self.timer.isActive():
            self.timer.stop()

        self.args = args
        self.kwargs = kwargs
        self.timer.start(self.timeout)


def delayedmethod(timeout):
    """
    When applied to a method, delays the actual execution of the callable until the given time in milliseconds has
    elapsed. This is done using a QTimer object. If the same callable is invoked again the timeout is reset and the
    supplied arguments for the most recent call are used in place of previous ones. No value is returned.
    """

    def _deco(func):
        name = func.__name__ + "__delay__"

        @qtmainthread
        @wraps(func)
        def _meth(self, *args, **kwargs):
            dc = getattr(self, name, None)
            if dc is None:
                dc = DelayedCall(func, timeout)
                setattr(self, name, dc)

            dc.start(self, *args, **kwargs)

        return _meth

    return _deco
