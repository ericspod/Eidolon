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

from ..utils import Future

__all__ = ["qtthreadsafe", "delayedmethod"]


class ThreadsafeEvent(QtCore.QEvent):
    EVENT_TYPE = QtCore.QEvent.Type(QtCore.QEvent.registerEventType())

    def __init__(self):
        super().__init__(self.EVENT_TYPE)


class ThreadsafeCall(QtCore.QObject):
    def __init__(self, func, args, kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.result = Future()

    def event(self, event):
        print("event", event)
        event.accept()

        with self.result:
            res = self.func(*self.args, **self.kwargs)
            self.result.set_result(res)

        return True

    def post(self):
        QtCore.QCoreApplication.postEvent(self, ThreadsafeEvent(), Qt.HighEventPriority)
        return self.result


# class ThreadsafeEvent(QtCore.QEvent):
#     EVENT_TYPE = QtCore.QEvent.Type(QtCore.QEvent.registerEventType())
#
#     def __init__(self, func, args, kwargs,result):
#         super().__init__(self.EVENT_TYPE)
#         self.func=func
#         self.args=args
#         self.kwargs=kwargs
#         self.result=result
#
#
# class ThreadsafeCaller(QtCore.QObject):
#     def event(self,event):
#         event.accept()
#         with event.result:
#             res=event.func(*event.args,**event.kwargs)
#             event.result.set_result(res)
#
#         return True
#
#
# ts_caller=ThreadsafeCaller()
#
# def call_threadsafe(func,*args,**kwargs):
#     result=Future()
#     tse=ThreadsafeEvent(func,args,kwargs,result)
#     QtCore.QCoreApplication.postEvent(ThreadsafeCaller(),tse)
#     return result


def qtthreadsafe(func, timeout=10.0):
    name = func.__name__ + "__caller__"

    @wraps(func)
    def _wrapper(*args, **kwargs):
        # caller = getattr(self, name, None)
        # if caller is None:
        #     caller = ThreadsafeCall(meth, args, kwargs)
        #     setattr(self, name, caller)
        # else:
        #     caller.args = args
        #     caller.kwargs = kwargs
        #     caller.result.clear()

        caller = ThreadsafeCall(func, args, kwargs)
        result = caller.post()
        return result

    return _wrapper


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
    When applied to a function or method, delays the actual execution of the callable until the given time in
    milliseconds has elapsed. This is done using a QTimer object. If the same callable is invoked again the timeout is
    reset and the supplied arguments for the most recent call are used in place of previous ones. No value is returned.
    """

    def _deco(func):
        name = func.__name__ + "__delay__"

        @qtthreadsafe
        @wraps(func)
        def _meth(self, *args, **kwargs):
            if hasattr(self, name):
                dc = getattr(self, name)
            else:
                dc = DelayedCall(func, timeout)
                setattr(self, name, dc)

            dc.start(self, *args, **kwargs)

        return _meth

    return _deco
