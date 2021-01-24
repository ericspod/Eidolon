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

from __future__ import annotations
import time
from typing import Optional, List
import traceback
from threading import RLock, Event, ThreadError, current_thread
from functools import wraps

__all__ = ["is_main_thread", "Future", "get_object_lock", "locking", "trylocking", "Task", "task_method", "TaskQueue"]


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


class Task:
    """
    This class represents the abstract notion of a task, with a `cur_progress` value to indicate progress in relation to
    a `max_progress` value. Tasks are executed by a TaskQueue object. The actual action of the Task object should be
    implemented by the supplied `func` argument, which must be a callable accepting the positional and keyword arguments
    given by `args` and `kwargs`. When a Task object is executed, it's start() method is called which will call
    self.func in the calling thread. A Task object can have a parent Task, which occurs when the body of one task
    invokes an operation that normally adds a task to a queue. When this occurs the progress and label methods call into
    the parent Task object.
    """

    @staticmethod
    def null():
        return Task('NullTask', lambda *args, **kwargs: None)

    def __init__(self, label, func=None, args=(), kwargs={}, self_name: Optional[str] = None,
                 parent_task: Optional[Task] = None):
        self._cur_progress: int = 0
        self._max_progress: int = 0
        self._label: str = ""
        self.result = None
        self.completed: bool = False
        self.started: bool = False
        self.flush_queue: bool = False  # set to true if the queue is to be task flushed when this task finishes

        # if this task is being run within another task, call that task's methods instead so that it is used to
        # indicate status
        self.parent_task: Task = parent_task

        kwargs = dict(kwargs)
        if self_name is not None:
            kwargs[self_name] = self

        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.label = label

    def start(self):
        """
        Perform the execution of the task which sets the label, sets self.started to True, and then sets self.result to
        the result of calling self.func with self.args and self.kwargs as arguments. Finally self.complete is set to
        True once this is done.
        """
        oldlabel = self.label
        self.label = self.label
        self.started = True

        try:
            self.result = self.func(*self.args, **self.kwargs)
            self.completed = True
        finally:
            if oldlabel and self.parent_task is not None:
                self.parent_task.label = oldlabel  # restore the old label of the parent task if present

    @property
    def is_done(self):
        """Returns True if the task has started and self.complete is True."""
        return self.started and self.completed

    @property
    def label(self):
        """Get the task's label, or that of the parent if present."""
        if self.parent_task is not None:
            return self.parent_task.label
        else:
            return self._label

    @label.setter
    def label(self, label):
        """Set the task's label (or that of the parent if present), this will be used by UI to indicate current task."""
        if self.parent_task is not None:
            self.parent_task.label = label
        else:
            self._label = label

    @property
    def progress(self):
        """Returns the current progress value or that of the parent if present."""
        if self.parent_task is not None:
            return self.parent_task._cur_progress
        else:
            return self._cur_progress

    @progress.setter
    def progress(self, cur_progress):
        """Set the progress of this or the parent task to the integer value `curprogress`."""
        if self.parent_task is not None:
            self.parent_task.progress = cur_progress
        else:
            self._cur_progress = cur_progress

    @property
    def max_progress(self):
        """Returns the maximal progress value or that of the parent if present."""
        if self.parent_task is not None:
            return self.parent_task.max_progress
        else:
            return self._max_progress

    @max_progress.setter
    def max_progress(self, max_progress):
        """Set the max progress value of this or the parent task to the integer value `max_progress`."""
        if self.parent_task is not None:
            self.parent_task.max_progress = max_progress
        else:
            self._max_progress = max_progress
            self._cur_progress = min(self._cur_progress, self._max_progress)

    def __repr__(self):
        return f"Task<{self.label}>"


def task_method(meth, task_queue_name="mgr", task_arg_name="task", task_label=None):
    """
    Decorates a method to execute it's body as a Task. The method receiver must have a member named `task_queue_name`
    which is a TaskQueue instance (default "mgr" reflects using the SceneManager as this object). When the method is
    called a Task is added to this queue which executes the method body. If `task_arg_name` is not None the Task object
    is passed to the method through the named additional keyword argument. If `task_label` is not None this labels the
    Task instead of the method name. The returned value is a Future object which eventually stores the task's result.
    """
    @wraps(meth)
    def _wrapper(self, *args, **kwargs):
        tqueue = getattr(self, task_queue_name)
        result = Future()

        def _task(task=None):  # task proxy function, calls `meth` storing results/exceptions in result
            with result:
                if task_arg_name:
                    kwargs[task_arg_name] = task

                mresult = meth(self, *args, **kwargs)
                result.set_result(mresult)

        functask = Task(task_label or meth.__name__, func=_task, self_name="task")
        tqueue.add_tasks(functask)

        return result

    return _wrapper


class TaskQueue(object):
    """
    This represents a queue of tasks waiting to be executed and the algorithm to do so. The process_queue() method
    handles executing each task in sequence and handling any exceptions that occur. The expected use case is that this
    class will be mixed in with another responsible for maintaining tasks and other system-level facilities.
    """

    def __init__(self):
        self.task_list: List[Task] = []  # list of queued Task objects
        self.finished_tasks: List[Task] = []  # list of completed Task objects
        self.current_task: Optional[Task] = None  # the current running task, None if there is none
        self.do_process: bool = True  # loop condition in processTaskQueue

    def process_queue(self):
        """
        Process the tasks in the queue, looping so long as self.do_process is True. This method will not return so long
        as this condition is True and so should be executed in its own thread. Tasks are popped from the top of the
        queue and their start() methods are called. Exceptions from this method are handled through task_except().
        """
        while self.do_process:
            try:
                # remove the first task, using the self lock to prevent interference while doing so
                with get_object_lock(self):
                    if len(self.task_list) > 0:
                        self.current_task = self.task_list.pop(0)

                # attempt to run the task by calling its start() method, on exception report and clear the queue
                try:
                    if self.current_task:
                        self.current_task.start()  # run the task's operation
                        self.finished_tasks.append(self.current_task)
                    else:
                        time.sleep(0.1)
                except FutureError as fe:
                    exc = fe.exc_value
                    while exc != fe and isinstance(exc, FutureError):
                        exc = exc.exc_value

                    self.task_except(fe, exc, 'Exception from queued task ' + self.current_task.getLabel())
                    # remove all waiting tasks; they may rely on 'task' completing correctly and deadlock
                    self.current_task.flush_queue = True

                except Exception as e:
                    # if no current task then some non-task exception we don't care about has occurred
                    if self.current_task:
                        self.task_except(e, '', 'Exception from queued task ' + self.current_task.getLabel())
                        self.current_task.flush_queue = True  # remove waiting tasks
                finally:
                    # set the current task to None, using self lock to prevent inconsistency with updatethread
                    with get_object_lock(self):
                        # clear the queue if there's a task and it wants to remove all current tasks
                        if self.current_task is not None and self.current_task.flush_queue:
                            del self.task_list[:]

                        self.current_task = None
            except:
                pass  # ignore errors during shutdown

    @locking
    def add_tasks(self, *tasks: Task):
        """Adds the given tasks to the task queue whether called in another task or not."""
        if not all(isinstance(t, Task) for t in tasks):
            raise ValueError("Arguments must all be Task objects")

        self.task_list += list(tasks)

    def add_func_task(self, func, name=None):
        """Creates a task object (named 'name' or the function name if None) to call the function when executed."""
        self.add_tasks(Task(name or func.__name__, func))

    @locking
    def list_tasks(self):
        """Returns a list of the labels of all queued tasks."""
        return [t.label for t in self.task_list]

    @locking
    def get_num_tasks(self):
        """Returns the number of queued tasks."""
        return len(self.task_list)

    @locking
    def task_status(self):
        """Returns the current task lable, progress, and max progress, or ("",0,0) if no task running."""
        if self.current_task is not None:
            return self.current_task.label, self.current_task.progress, self.current_task.max_progress
        else:
            return "", 0, 0

    def task_except(self, ex, msg, title):
        """Called when the task queue encounters exception `ex` with message `msg` and report window title `title`."""
        pass
