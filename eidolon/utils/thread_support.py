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

from typing import Optional
import traceback
from threading import RLock, Event, ThreadError, current_thread
from functools import wraps

__all__ = ["is_main_thread", "Future", "get_object_lock", "locking", "trylocking"]


def is_main_thread() -> bool:
    """Returns True if the calling thread is the main thread of the program."""
    return current_thread().name == "MainThread"


class FutureError(Exception):
    def __init__(self, f, exc_type, exc_value, tb):
        self.future = f
        self.exc_type = exc_type
        self.exc_value = exc_value
        self.tb = tb
        msg = ''

        if exc_value:
            fexp = '\n'.join(traceback.format_exception(exc_type, exc_value, tb))
            msg = 'Future object left control block with exception:\n' + fexp
        else:
            msg = 'Future object left control block without a value'

        Exception.__init__(self, msg)


class Future(object):
    """
    An implementation of the Future Object design pattern. This acts as a proxy for a result from some concurrent task
    which can be given to clients. When the task completes the result is given to the object, which can be retrieved
    through the 'get_result_wait' function of the () operator. If the result hasn't arrived yet then the caller will
    block until it does, or when the optional timout period has elapsed. These objects work only for threads and not
    between processes.

    Futures can be used as context managers where they will send the client an exception if the block is left without a
    result being sent or if an exception is raised. This is useful in preventing client deadlock when errors occur.
    """

    def __init__(self):
        self.result = None
        self.event = Event()

    def set_result(self, obj):
        """Set the internal stored object to `result' and set the event."""
        self.result = obj
        self.event.set()

    def clear(self):
        """Remove the internal object and clear the event."""
        self.result = None
        self.event.clear()

    def is_set(self):
        """Returns True if the event has been set, ie. a result is stored."""
        return self.event.is_set()

    def is_empty(self):
        """Returns True if there is no result and the event is not set."""
        return self.result is None and not self.event.is_set()

    def get_result_wait(self, timeout: Optional[float] = 10.0):
        """
        Return the stored object, waiting `timeout` seconds for the object to be set, returning None if this doesn't
        occur in this time. If the object is present and is an exception, this is raised instead. The `timeout`
        value therefore must be a positive float or None to indicate indefinite waiting. If a timeout value is given
        and the return result is None, the timeout time was reached if is_set() returns False at this point, otherwise
        None was the set value.
        """
        res = self.event.wait(timeout)

        if timeout is not None and not res:  # if we timed out waiting, return None
            raise ThreadError(f"Future timed out without receiving result (timeout = {timeout})")

        # if an exception was raised instead of setting a value, raise it
        if isinstance(self.result, FutureError) and self.result.exc_value:
            raise self.result.exc_type(self.result.exc_value).with_traceback(self.result.tb)
        elif isinstance(self.result, Exception):
            raise self.result

        # return the stored value, or if the value is a Future get the stored value from it
        return Future.get(self.result, timeout)

    def __call__(self, timeout=10.0):
        """Same as get_result_wait()."""
        return self.get_result_wait(timeout)

    def __enter__(self):
        """
        Used to define with-blocks in which the Future must be given a value. If the block exits without a value set,
        __exit__ will set the object to a FutureError indicating this. This also includes the case where the block
        exits because of a raised exception, the details of which will be stored in the FutureError object.
        """
        return self

    def __exit__(self, exc_type, exc_value, tb):
        """Sets the stored object to a FutureError if block exits without a value or because of a raised exception."""
        if exc_value or self.is_empty():  # if there's no value or an exception was raised, store a FutureError
            self.set_result(FutureError(self, exc_type, exc_value, tb))

        return True

    @staticmethod
    def get(obj, timeout: Optional[float] = 10.0):
        """
        Retrieve the object from `result` if it's a Future, otherwise return `result` itself. This is useful for
        routines wanting to accept a Future containing an object or the object itself, depending on whether the use case
        is concurrent or not. The `timeout` value is only used if `result` is a Future, and must be a positive float.
        """
        if isinstance(obj, Future):
            return obj(timeout)
        else:
            return obj


def get_object_lock(obj, lock_type=RLock):
    """
    Returns a lock object stored as the member `__lock__` of `obj`, creating it if such a member doesn't exist. The
    given type is used to create the lock object, by default this is RLock allowing recursive access to locked objects.
    """

    lock = getattr(obj, "__lock__", None)

    if lock is None:
        lock = lock_type()
        setattr(obj, "__lock__", lock)

    return lock


def locking(meth, lock_type=RLock):
    """
    This method decorator synchronizes access to the current object using its stored lock object. This ensures that
    calls to decorated methods are restricted to one thread at a time, which doesn't necessarily ensure exclusive access
    to the all of the receiving object's members.
    """

    @wraps(meth)
    def methwrap(self, *args, **kwargs):
        with get_object_lock(self, lock_type):
            return meth(self, *args, **kwargs)

    return methwrap


def trylocking(meth, lock_type=RLock):
    """
    Same as 'locking' except it only attempts to acquire the lock without blocking, doing nothing if the acquire fails.
    """

    @wraps(meth)
    def methwrap(self, *args, **kwargs):
        lock = get_object_lock(self, lock_type)
        if lock.acquire(False):
            try:
                return meth(self, *args, **kwargs)
            finally:
                lock.release()

    return methwrap
