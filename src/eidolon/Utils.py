# Eidolon Biomedical Framework
# Copyright (C) 2016-7 Eric Kerfoot, King's College London, all rights reserved
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

'''
These are utility functions and classes defined in pure Python. They do not use libraries like Numpy or the renderer.
Routines are provided for file handling, file path manipulation, process handling and execution, routine utilities,
task handling, and a large number of mathematical utilities.

The class enum is used throughout the framework to define enumerations sort of like Java. These consist of list/dict
hybrid types where a tuple of values is associated with a string name, for example:

    vertices=enum(
        ('line',2,'1D'),
        ('triangle',3,'2D'),
        ('tet',4,'3D')
    )

This associates 'line' with the tuple (2,'1D') which can be queries from `vertices` by name or index, so `vertices.line`
and `vertices[0]` both return (2,'1D'). See the enum docs for further details of their use.

The class Future is the implementation of the future/promise/delay/etc. pattern. It is a container for a value which will
be provided eventually by some asynchronous operation. Typically a method is called which launches an asynchronous
operation and returns the Future instance the result will be placed in. The caller then queries the object to determine
if the result is present and then to get it directly. For example:

    f=someAsyncOp() #  f is the Future
    print f() # wait 10 seconds by default for f to be given its value

If a value is returned or passed as an argument which is either a Future or the object itself, the function Future.get()
can be used to get the object regardless:

    print Future.get(f)

The Future type can be used as the object in a with-block to automatically catch exceptions or ensure that a value was
eventually given. This is done in the asynchronous operation itself to ensure correct communication with its client. If
an exception is raised, it becomes the stored object, which is then raised by the client when the value is queried:

    def someAsyncOp(f)
        with f:
            ...
            raise SomeError()
    ...
    print f() # raises SomeError here

Asynchronous operations are often defined as tasks represented by the Task type. Instances of this type store a callable
and variables indicating progress and current state. The callable is what defines the actual behaviour, the Task object's
role is to represent the operation's current status and interface with the TaskQueue object responsible for running the
tasks. For example, a simple task printing a string to stdout:

    func=lambda:printFlush('I am a test task')
    q=TaskQueue()
    q.addTasks(Task('test 1',func))
    q.processTaskQueue() # note this never returns, should be a separate thread

Decorating a function with @taskroutine creates a wrapped version which returns a Task object when called, this object
will execute the function's body when used in a TaskQueue. Decorating a method with @taskmethod produces a method which
will enqueue a Task executing its body on the TaskQueue the receiver refers to in a member variable, by default called
`mgr'. Such a method when called will try to run the task immediately and return a Future object for the result.
'''

import math
import random
import sys
import time
import os
import traceback
import weakref
import itertools
import operator
import logging
import pickle
import re
import platform
import threading
import shutil
import subprocess
import atexit
import contextlib
import ast
import string
import inspect

from codeop import compile_command
from functools import wraps
from threading import Thread, RLock, Event,currentThread,_MainThread

try: # Python 2/3 fix
    import ConfigParser as configparser
except:
    import configparser


halfpi=math.pi/2.0

epsilon=1.0e-8

logFilename=None

isDarwin=platform.system().lower()=='darwin'
isWindows=platform.system().lower()=='windows'
isLinux=platform.system().lower()=='linux'

assert isDarwin or isWindows or isLinux # only allow one of these platforms for now


class enum(object):
    '''
    Simulate a Java-like enum type. An instance is initialized with a list of tuples, the first value of each is
    the enum member name, the following are the values that name stores. If instead a list of strings is given those
    strings are used as the name and value, similarly if a list of singleton tuples is given the names are used as
    values. An entry can be accessed as a member of the object using the given name if the name with spaces replaced
    with _ is a valid Python identifier.

    A second member with the same name prepended with _ returns the name itself. The [] operator can query
    values by index or by name. Containment (in/not in) is defined as name membership in the enum.
    The members of the enum are also iterable in the given order, each element being a tuple of the name+values.

    The constructor accepts keyword arguments to define secondary properties of the enum: "doc" should contain a
    documentation string describing the members of the enum, and "valtype" should be a tuple stating the type for each
    value in the entries, which assumes all entries have values of the same type.

    Eg. given e=enum( ('foo',1,2), ('bar',3,4), ('baz thunk', 5), ('plonk',) )
        'foo' in e   -> True
        e.foo        -> (1,2)
        e._foo       -> 'foo'
        e[1]         -> ('bar',3,4)
        e['bar']     -> (3,4)
        e.baz_thunk  -> 5
        e.plonk      -> 'plonk'
    '''
    def __init__(self,*vals,**kwargs):
        if vals and isinstance(vals[0],enum):
            kwargs['doc']=kwargs.get('doc',vals[0].doc)
            kwargs['valtype']=kwargs.get('valtype',vals[0].valtype)
            vals=list(vals[0])

        if all(isinstance(v,str) for v in vals):
            vals=[(v,) for v in vals]

        assert all(isinstance(v,tuple) for v in vals)
        object.__setattr__(self,'valdict',{})
        object.__setattr__(self,'vals',[])
        object.__setattr__(self,'doc',kwargs.get('doc',None))
        object.__setattr__(self,'valtype',kwargs.get('valtype',None))

        for v in vals:
            self.append(*v)

    def append(self,name,*comps):
        name=str(name)
        if len(comps)==0:
            val=name # if only the name is given, name is also the value
        elif len(comps)==1:
            val=comps[0] # if a single value is given, it is the value rather than a tuple containing only it
            assert self.valtype==None or val==None or isinstance(val,self.valtype)
        else:
            val=comps # otherwise the values minus the name becomes the value tuple
            assert self.valtype==None or (len(val)==len(self.valtype) and all(v==None or isinstance(v,vt) for v,vt in zip(val,self.valtype))),'%r %r'%(self.valtype,val)

        dname=name.replace(' ','_')
        self.valdict[dname]=val
        self.valdict['_'+dname]=name
        self.vals.append((name,)+comps)

    def findName(self,item):
        return first(n for n,i in self.valdict.items() if i==item)

    def indexOf(self,name):
        return first(i for i,v in enumerate(self.vals) if v[0]==name)

    def _getVal(self,i):
        if isinstance(i,int):
            return self.vals[i]
        else:
            return self.valdict[i]

    def __str__(self):
        res='Enum:\n Members: '+', '.join(n[0] for n in self.vals)
        if self.doc:
            res+='\n Doc: '+self.doc

        return res

    def __len__(self):
        return len(self.vals)

    def __iter__(self):
        return iter(self.vals)

    def __contains__(self,i):
        try:
            self._getVal(i)
            return True
        except:
            return False

    def __getitem__(self,i):
        return self._getVal(i)

    def __getattr__(self,i):
        try:
            return self._getVal(i)
        except KeyError:
            return self.__getattribute__(i)

    def __setattr__(self, name, value):  # this makes it read-only except for append()
        raise NotImplementedError('Enum values are read-only')


class FutureError(Exception):
    def __init__(self,f,exc_type, exc_value, tb):
        self.future=f
        self.exc_type=exc_type
        self.exc_value=exc_value
        self.tb=tb
        msg=''
        if exc_value:
            msg='Future object left control block with exception:\n'+'\n'.join(traceback.format_exception(exc_type, exc_value, tb))
        else:
            msg='Future object left control block without a value'

        Exception.__init__(self,msg)


class Future(object):
    '''
    An implementation of the Future Object design pattern. This acts as a proxy for a result from some concurrent task
    which can be given to clients. When the task completes the result is given to the object, which can be retrieved
    through the 'getObjectWait' function of the call () operator. If the result hasn't arrived yet then the caller will
    block until it does, or when the optional timout period has elapsed. These objects work only for threads and not
    between processes.

    Futures can be used in a 'with' control block, such that they will send the client an exception if the block is
    left without a result being sent or if an exception is thrown. This is useful in preventing client deadlock when
    errors occur.
    '''
    def __init__(self):
        self.obj=None
        self.event=Event()

    def setObject(self,obj):
        '''Set the internal stored object to `obj' and set the event.'''
        self.obj=obj
        self.event.set()

    def clear(self):
        '''Remove the internal object and clear the event.'''
        self.obj=None
        self.event.clear()

    def isSet(self):
        '''Returns True if the event has been set, ie. a result is stored.'''
        return self.event.isSet()

    def isEmpty(self):
        '''Returns True if there is no result and the event is not set.'''
        return self.obj is None and not self.event.isSet()

    def getObjectWait(self,timeout=10.0):
        '''
        Return the stored object, waiting `timeout' seconds for the object to be set, returning None if this doesn't
        occur in this time. If the object is present and is an exception, this is raised instead. The `timeout'
        value therefore must be a positive float or None to indicate indefinite waiting. If a timeout value is given
        and the return result is None, the timeout time was reached if isSet() returns False at this point, otherwise
        None was the set value.
        '''
        res=self.event.wait(timeout)

        if timeout!=None and not res: # if we timed out waiting, return None
            return None

        # if an exception was raised instead of setting a value, raise it
        if isinstance(self.obj,FutureError) and self.obj.exc_value:
            if hasattr(self.obj,'with_traceback'): # Python3 compatibility
                raise self.obj.exc_type(self.obj.exc_value).with_traceback(self.obj.tb)
            else:
                raise self.obj.exc_type,self.obj.exc_value,self.obj.tb

        elif isinstance(self.obj,Exception):
            raise self.obj

        # return the stored value, or if the value is a Future get the stored value from it
        return Future.get(self.obj,timeout)

    def __call__(self,timeout=10.0):
        '''Same as getObjectWait().'''
        return self.getObjectWait(timeout)

    def __enter__(self):
        '''
        Used to define with-blocks in which the Future must be given a value. If the block exits without a value set,
        __exit__ will set the object to a FutureError indicating this. This also includes the case where the block
        exits because of a raised exception, the details of which will be stored in the FutureError object.
        '''
        return self

    def __exit__(self,exc_type, exc_value, tb):
        '''Sets the stored object to a FutureError if block exits without a value or because of a raised exception.'''
        if exc_value or self.isEmpty(): # if there's no value or an exception was raised, store a FutureError
            self.setObject(FutureError(self,exc_type, exc_value, tb))

        return True

    @staticmethod
    def get(obj,timeout=10.0):
        '''
        Retrieve the object from `obj' if it's a Future, otherwise return `obj' itself. This is useful for methods which
        may want to accept a Future containing an object or the object itself, depending on whether the use context is
        concurrent or not. The `timeout' value is only used if `obj' is a Future, and must then be a positive float.
        '''
        if isinstance(obj,Future):
            return obj(timeout)
        else:
            return obj


ConfVars=enum(
    'all','shaders', 'resdir', 'shmdir', 'appdir', 'userappdir','logfile', 'preloadscripts', 'uistyle', 'stylesheet',
    'winsize', 'camerazlock', 'maxprocs', 'configfile', 'rtt_preferred_mode', 'vsync', 'rendersystem',
    'consolelogfile','consoleloglen',
    desc='Variables in the Config object loaded from config files, these should be present and keyed to platformID group'
)


ParamType=enum(
    ('int','Integer'),
    ('real','Real'),
    ('bool','Boolean'),
    ('vec3','3D Vector'),
    ('field','Field Name'),
    ('str','String'),
    ('strlist','String List'),
#   ('choice','Choice Option'),
    ('valuefunc','Value Function'),
    ('vecfunc','Vector Function'),
    ('unitfunc','Unit Function'),
    doc='Types of parameters the ParamDef class can represent.',
    valtype=(str,)
)


class ParamDef(object):
    '''
    Definition of a parameter for various uses, eg. representation object settings, UI definitions. Parameters consist
    of a name, description (for use in tooltips), a value type such as str or int, default value, value range, value
    step, and whether None is accepted as a value. A ParamDef represents a named value of some sort defined within these
    parameters, this can be used to define a generic interface for parameters into objects and to automatically define
    GUI elements for inputting these values.
    '''
    def __init__(self,name,desc,ptype,default=None,minv=None,maxv=None,step=None,notNone=False):
        assert ptype in ParamType
        self.name=name
        self.desc=desc
        self.ptype=ptype
        self.default=default
        self.minv=minv
        self.maxv=maxv
        self.step=step
        self.notNone=notNone

    def getErrorStr(self,val):
        errstr="Incorrect value for '%s' (%s): " %(self.desc,self.name)
        if val==None and self.notNone:
            return errstr + 'A value must be provided (not None)'

        if isIterable(self.minv):
            ival=val if isIterable(val) else (val,)

            if val!=None and self.minv!=None and all(v<mv for v,mv in zip(ival,self.minv)):
                return errstr + "Parameter is below minimum value of '%s' (value: %s)"%(str(self.minv),str(val))

            if val!=None and self.maxv!=None and all(v>mv for v,mv in zip(ival,self.maxv)):
                return errstr + "Parameter is above maximum value of '%s' (value: %s)"%(str(self.maxv),str(val))
        else:
            if val!=None and self.minv!=None and val<self.minv:
                return errstr + "Parameter is below minimum value of '%s' (value: %s)"%(str(self.minv),str(val))

            if val!=None and self.maxv!=None and val>self.maxv:
                return errstr + "Parameter is above maximum value of '%s' (value: %s)"%(str(self.maxv),str(val))

        return None

    def __repr__(self):
        s='ParamDef(name=%s,desc="%s",type=%s' %(self.name,self.desc,self.ptype)
        if self.default!=None:
            s+=',default='+str(self.default)
        if self.minv!=None:
            s+=',range=[%s,%s]' %(str(self.minv),str(self.maxv))
        if self.step!=None:
            s+=',step='+str(self.step)
        if self.notNone:
            s+=',Not None'

        return s+')'

    @staticmethod
    def validateArgMap(params,argmap):
        errlist=[]
        for p in params:
            result=p.getErrorStr(argmap.get(p.name,None))
            if result!=None:
                errlist.append(result)

        return errlist


EventType=enum(
    ('mousePress','Mouse Button Pressed'),
    ('mouseRelease','Mouse Button Released'),
    ('mouseDoubleClick','Mouse Button Double Clicked'),
    ('mouseMove','Mouse Moved With Key Pressed'),
    ('mouseWheel','Mouse Wheel Moved'),
    ('keyPress','Keyboard Key Pressed'),
    ('keyRelease','Keyboard Key Released'),
    ('widgetResize','Widget Resized/Shown'),
    ('widgetPreDraw','Widget to drawn'),
    ('widgetPostDraw','Widget Redrawn'),
    ('objectAdded','Object Added to Scene'),
    ('objectRemoved','Object Removed from Scene'),
    ('objectUpdated','Object Updated in Scene'),
    ('objectSelected','Object Selected in Scene'),
    ('objectRenamed','Object Renamed'),
    doc='Event types triggered by the rendering widget, used to signal draw events, input operations, etc'
)


class EventHandler(object):
    '''
    An event broadcast class which invokes callable objects when an EventType event occurs. For every named event, this
    maintains a list of callback callable objects which accept a set of parameters specific for each event type. When
    _triggerEvent() is called, each callback associated with the given event name is called with the given arguments
    passed in.
    '''
    def __init__(self):
        self.eventHandlers=dict((i,[]) for i,j in EventType)
        self.handleLock=threading.Lock()
        self.suppressedEvents=set()

    def _triggerEvent(self,name,*args):
        '''
        Broadcast event to handler callback functions, stopping for any callback that returns True. For every callback
        associated with event `name', call it expanding `args' as the arguments.
        '''
        assert isMainThread()
        discards=set()

        with self.handleLock:
            if name in self.suppressedEvents:
                return

            self.suppressedEvents.add(name)

        try:
            for cb in self.eventHandlers[name]:
                try:
                    result=cb(*args)
                    if result==True:
                        break
                except RuntimeError:
                    discards.add(cb)
        finally:
            for d in discards:
                self.eventHandlers[name].remove(d)

            with self.handleLock:
                self.suppressedEvents.remove(name)

    def addEventHandler(self,name,cb):
        '''Add the callback callable `cb' for event named `name'.'''
        assert name in EventType
        self.eventHandlers[name].append(cb)

    def removeEventHandler(self,cb):
        '''Remove the callback `cb' from wherever it occurs.'''
        for cblist in self.eventHandlers.values():
            if cb in cblist:
                cblist.remove(cb)


class ObjectLocker(object):
    '''
    This maintains a dictionary relating weak references to threading.RLock objects. This allows a lock to be associated
    uniquely with any provided object compatible with the weakref interface. The method getLock() returns the lock for
    the provided object, creating one if needed. When the object is removed the associated lock is also removed from
    the dictonary. The global instance `globalLocker` is created to provide a global default lock for the decorators
    which rely on this type.
    '''
    globalLocker=None

    def __init__(self):
        self.objLocks={} # map of objects to locks used to store unique locks for every requested object
        self.thisLock=RLock() # a lock for this object

    def getLock(self,obj):
        '''
        Get a threading.RLock object uniquely associated with `obj'. If this method is subsequently called with the
        same object, the same lock is returned. When `obj' is removed by the collector, the lock will also be removed.
        '''
        with self.thisLock:
            lock=first(self.objLocks[w] for w in self.objLocks if id(w())==id(obj))

            if not lock:
                w=weakref.ref(obj,self._removeLock)
                lock=RLock()
                self.objLocks[w]=lock

            return lock

    def _removeLock(self,obj):
        with self.thisLock:
            self.objLocks.pop(obj)

    @staticmethod
    def getGlobalLocker():
        '''Returns the global locker object, instantiating it if necessary.'''
        if ObjectLocker.globalLocker is None:
            ObjectLocker.globalLocker=ObjectLocker()

        return ObjectLocker.globalLocker


def lockobj(obj,locker=None):
    '''
    Returns a lock object which is be globally unique per input object. This lock can be used to synchronize access
    to any arbitrary object. It uses weak references to ensure previously locked objects can be collected.
    This function is thread-safe.
    '''
    locker=locker or ObjectLocker.getGlobalLocker()
    return locker.getLock(obj)


def locking(func,locker=None):
    '''
    This is a locking method decorator which uses 'lockobj' to synchronize access to the current object. This ensures
    that calls to decorated methods are restricted to one thread at a time, which doesn't necessarily ensure exclusive
    access to the all of the receiving object's members. A calling thread having a lock to the receiver already through
    'lockobj' will be able to call decorated methods as well.
    '''
    @wraps(func)
    def funcwrap(self,*args,**kwargs):
        with lockobj(self,locker):
            return func(self,*args,**kwargs)

    return funcwrap


def trylocking(func,locker=None):
    '''
    Same as 'locking' except it only attempts to acquire the lock without blocking, and does nothing if the acquire fails.
    '''
    @wraps(func)
    def funcwrap(self,*args,**kwargs):
        lock=lockobj(self,locker)
        if lock.acquire(False):
            try:
                return func(self,*args,**kwargs)
            finally:
                lock.release()

    return funcwrap


class Task(object):
    '''
    This class represents the abstract notion of a task, with a 'curprogress' value to indicate progress in relation to
    a 'maxprogress' value. Tasks may have their own threads or be executed by their containers. Normally tasks are
    executed by a TaskQueue object. The actual action of the Task object should be implemented by the supplied `func'
    argument, which must be a callable accepting the positional and keyword arguments given by `args' and `kwargs'.
    When a Task object is executed, it's start() method is called which will call self.func either in the calling thread
    or a new one, depending on the `useThread' argument. A Task object can have a parent Task, which occurs when the body
    of one task invokes an operation that normally adds a task to a queue. When this occurs the progress and label
    methods call into the parent Task object.
    '''
    @staticmethod
    def Null():
        return Task('NullTask')

    def __init__(self,label,func=None,args=(),kwargs={},selfName=None,parentTask=None):
        self.curprogress=0
        self.maxprogress=0
        self.result=None
        self.completed=False
        self.started=False
        self.flushQueue=False # set to true if the queue is to be task flushed when this task finishes
        self.parentTask=parentTask # if this task is being run within another task, call that task's methods instead so that it is used to indicate status

        kwargs=dict(kwargs)
        if selfName:
            kwargs[selfName]=self

        self.func=func
        self.args=args
        self.kwargs=kwargs
        self.thread=None
        self.setLabel(label)

    def _callFunc(self):
        '''Call self.func with arguments self.args and self.kwargs, storing the result in self.result.'''
        self.result=self.func(*self.args,**self.kwargs)

    def start(self,useThread=False):
        '''
        Perform the execution of the task. This will set the label, set self.started to True, and then if useThread is
        True create a thread which will _callFunc(), otherwise _callFunc() is called directly. Finally self.completed
        is set to True once this is done.
        '''
        oldlabel=self.getLabel()
        self.setLabel(self.label)
        self.started=True
        try:
            if useThread:
                self.thread=Thread(target=self._callFunc,name=self.label)
                self.thread.start()
            else:
                self._callFunc()
            self.completed=True
        finally:
            if oldlabel and self.parentTask:
                self.parentTask.setLabel(oldlabel) # restore the old label of the parent task if present

    def isDone(self):
        '''Returns True if the task has started and the thread is no longer alive or self.complete is True.'''
        return self.started and (not self.thread.isAlive() if self.thread else self.completed)

    def setLabel(self,label):
        '''Set the task's label (or that of the parent if present), this will be used by UI to indicate current task.'''
        if self.parentTask:
            self.parentTask.setLabel(label)
        else:
            self.label=label
            if self.thread:
                self.thread.label=label

    def getLabel(self):
        '''Get the task's label, or that of the parent if present.'''
        if self.parentTask:
            return self.parentTask.getLabel()
        else:
            return self.label

    def setProgress(self,curprogress):
        '''Set the progress of this or the parent task to the integer value `curprogress'.'''
        if self.parentTask:
            self.parentTask.setProgress(curprogress)
        else:
            self.curprogress=curprogress

    def setMaxProgress(self,maxprogress):
        '''Set the max progress value of this or the parent task to the integer value `maxprogress'.'''
        if self.parentTask:
            self.parentTask.setMaxProgress(maxprogress)
        else:
            self.maxprogress=maxprogress
            self.curprogress=min(self.curprogress,self.maxprogress)

    def getProgress(self):
        '''Returns the current progress value and maximum value, or that of the parent if present, or (0,0) if unknown.'''
        if self.parentTask:
            return self.parentTask.getProgress()
        else:
            return self.curprogress,self.maxprogress

    def __repr__(self):
        return 'Task<%s>' %self.label


class TaskQueue(object):
    '''
    This represents a queue of tasks waiting to be executed and the algorithm to do so. The processTaskQueue() method
    handles executing each task in sequence and handling any exceptions that occur. The expected use case is that this
    class will be mixed in with another responsible for maintaining tasks and other system-level facilities.
    '''
    def __init__(self):
        self.tasklist=[] # list of queued Task objects
        self.finishedtasks=[] # list of completed Task objects
        self.currentTask=None # the current running task, None if there is none
        self.doProcess=True # loop condition in processTaskQueue

    def processTaskQueue(self):
        '''
        Process the tasks in the queue, looping so long as self.doProcess is True. This method will not return so long
        as this condition is True and so should be executed in its own thread. Tasks are popped from the top of the
        queue and their start() methods are called. Exceptions from this method are handled through taskExcept().
        '''
        while self.doProcess:
            try:
                # remove the first task, using the self lock to prevent interference while doing so
                with lockobj(self):
                    if len(self.tasklist)>0:
                        self.currentTask=self.tasklist.pop(0)

                # attempt to run the task by calling its start() method, on exception report and clear the queue
                try:
                    if self.currentTask:
                        self.currentTask.start() # run the task's operation
                        self.finishedtasks.append(self.currentTask)
                    else:
                        time.sleep(0.1)
                except FutureError as fe:
                    exc=fe.exc_value
                    while exc!=fe and isinstance(exc,FutureError):
                        exc=exc.exc_value

                    self.taskExcept(fe,exc,'Exception from queued task '+self.currentTask.getLabel())
                    self.currentTask.flushQueue=True # remove all waiting tasks; they may rely on 'task' completing correctly and deadlock
                except Exception as e:
                    if self.currentTask: # if no current task then some non-task exception we don't care about has occurred
                        self.taskExcept(e,'','Exception from queued task '+self.currentTask.getLabel())
                        self.currentTask.flushQueue=True # remove all waiting tasks; they may rely on 'task' completing correctly and deadlock
                finally:
                    # set the current task to None, using self lock to prevent inconsistency with updatethread
                    with lockobj(self):
                        # clear the queue if there's a task and it wants to remove all current tasks
                        if self.currentTask!=None and self.currentTask.flushQueue:
                            del self.tasklist[:]

                        self.currentTask=None
            except:
                pass # ignore errors during shutdown

    @locking
    def addTasks(self,*tasks):
        '''Adds the given tasks to the task queue whether called in another task or not.'''
        assert all(isinstance(t,Task) for t in tasks)
        self.tasklist+=list(tasks)

    def addFuncTask(self,func,name=None):
        '''Creates a task object (named 'name' or the function name if None) to call the function when executed.'''
        self.addTasks(Task(name or func.__name__,func))

    @locking
    def listTasks(self):
        '''Returns a list of the labels of all queued tasks.'''
        return [t.getLabel() for t in self.tasklist]

    @locking
    def getNumTasks(self):
        '''Returns the number of queued tasks.'''
        return len(self.tasklist)

    def taskExcept(self,ex,msg,title):
        '''Called when the task queue encounters exception `ex' with message `msg' and report window title `title'.'''
        pass


class DelayThread(Thread):
    '''
    Calls a target callable with the given args after a delay time has elapsed, which is reset to the full time if
    subsequent call request come before the call occurs. This ensures that a single call to the target happens even
    if multiple requests come in during the delay period, allowing for example update tasks to be scheduled when UI
    elements are manipulated and then deferred if further operations are performed soon after.
    '''

    globalDelayMap={}

    def __init__(self,delay,target):
        Thread.__init__(self)
        self.target=target
        self.args=()
        self.kwargs={}
        self.delay=float(delay)
        self.decDelayVal=0.05
        self.currentDelay=0.0
        self.evt=Event()
        self.daemon=True

    def stop(self):
        self.delay=-1
        self.evt.set()

    @locking
    def callTargetDelayed(self,args,kwargs):
        self.currentDelay=self.delay
        self.args=args
        self.kwargs=kwargs
        self.evt.set()

    @locking
    def getCurrentDelay(self):
        return self.currentDelay

    @locking
    def decCurrentDelay(self):
        self.currentDelay-=self.decDelayVal

    def run(self):
        while True:
            self.evt.wait()
            if self.delay<0:
                break

            while self.getCurrentDelay()>0:
                self.decCurrentDelay()
                time.sleep(self.decDelayVal)

            try:
                self.target(*self.args, **self.kwargs)
                self.args=None
                self.kwargs=None
            except:
                t=first(t for t,d in DelayThread.globalDelayMap.items() if d==self)
                del DelayThread.globalDelayMap[t]
                return

            self.evt.clear()

    @staticmethod
    def callGlobalTarget(delay,target,args,kwargs):
        if target not in DelayThread.globalDelayMap:
            DelayThread.globalDelayMap[target]=DelayThread(delay,target)
            DelayThread.globalDelayMap[target].start()

        DelayThread.globalDelayMap[target].callTargetDelayed(args,kwargs)

    @staticmethod
    def removeGlobalTarget(target):
        for d in DelayThread.globalDelayMap:
            if d.target==target:
                del DelayThread.globalDelayMap[d]
                break


def wrapper(func):
    '''
    This decorator is applied to functions to simplify the definitions of decorators. A function this is applied to
    becomes a decorator itself. It's first three arguments must be the function to wrap, the list of positional arguments,
    and the dictionary of keyword arguments. The remaining arguments are those provided by the decorator call itself.
    The body of the function is responsible for replacing or augmenting the behaviour of the provided function just like
    any other decorator. This results in a decorator function which expects the arguments after the first three to be
    provided, and so must always be called with (), but which doesn't require the definition of nested functions.

    For example, the following decorator prints the function and a message provided through the decorator before calling
    the wrapped function and returning the result:

        @wrapper
        def printdeco(func,args,kwargs,msg='No Message'):
            print 'Calling',func,msg
            return func(*args,**kwargs)

    This is equivalent to:

        def printdeco(msg='No Message'):
            def _outer(func):
                @wraps(func)
                def _wrapper(*args,**kwargs):
                    print 'Calling',func,msg
                    return func(*args,**kwargs)

    This is used as such:

        @printdeco('Ni!')
        def spam(x):
            print 'Spam and',x

    Calling this function with "Eggs" as the argument prints the following:

        Calling <function tostr at 0x7f91d747a1b8> Ni!
        Spam and Eggs
    '''
    @wraps(func)
    def _newdecorator(*args,**kwargs):
        '''This defines the new argument decorator which replaces `func'.'''
        def _outer(func1):
            '''This is the argumentless decorator around the wrapper produced by the replaced version of `func'.'''
            @wraps(func1)
            def _wrapper(*wargs,**wkwargs):
                '''This is the actual wrapper function which calls `func' passing in the decorator and call arguments.'''
                return func(func1,wargs,wkwargs,*args,**kwargs)

            return _wrapper

        return _outer

    return _newdecorator


#def delayedcall(delay):
#   '''
#   Wrapper for defining a delayed call function. When the function is called, up to `delay' seconds elapses before
#   the call actually occurs. Subsequent calls to the function before this time elapses resets the counter but will
#   not induce multiple calls. The most recent arguments passed to the wrapped function are the ones used when the
#   call does occur; there is never a return value.
#   '''
#   def funcwrap(func):
#       @wraps(func)
#       def delayCall(*args,**kwargs):
#           DelayThread.callGlobalTarget(delay,func,args,kwargs)
#
#       return delayCall
#
#   return funcwrap


@wrapper
def delayedcall(func,args,kwargs,delay):
    DelayThread.callGlobalTarget(delay,func,args,kwargs)


def delayedMethodWeak(obj,methname,delay=0):
    '''
    Replaces the method named `methname' of object `obj' with an equivalent delayed call with a delay value of `delay'.
    The new method assigned to `obj' replaces `methname' but keeps only a weak reference to `obj'. Once `obj' has been
    collected an exception will be thrown when attempting to call this method, this will cause the delay thread to be
    removed from the DelayThread global list. This allows objects to be assigned individual delay threads for their
    methods, otherwise using delayedcall() directly means a thread is assigned to a method which is shared amongst all
    instances. Using the weak reference prevents the delay mechanism from affecting collection behaviour.
    '''
    wself=weakref.ref(obj)
    meth=getattr(type(obj),methname)

    @delayedcall(delay)
    def newmeth(*args,**kwargs):
        meth(wself(),*args,**kwargs)

    setattr(obj,methname,newmeth)


@wrapper
def taskroutine(func,args,kwargs,taskLabel=None,selfName='task'):
    '''
    Routine decorator which produces a wrapper function returning a task that will execute the original function when
    processedby the task queue. The first argument indicates the name of the variable used to pass the Task instance
    to the function call or is None if no passing is wanted. If the task argument is present it must be the last and
    when the function is called no value for it must be provided, thus it must have a default value (usually None).
    The optional second argument defines whether the task is a threaded one or not (default is False).
    '''
    return Task(taskLabel or func.__name__,func=func,args=args,kwargs=kwargs,selfName=selfName)


@wrapper
def taskmethod(meth,args,kwargs,taskLabel=None,selfName='task',mgrName='mgr'):
    '''
    Wraps a given method such that it will execute the method's body in a task and store the result in a returned
    Future object. This assumes the method's receiver has a member called `mgrName' which references a TaskQueue
    object. This will also add the keywod argument named `selfName' which will refer to the Task object when called.
    The string `taskLabel' is used to identify the task, typically in a status bar, ie. the same as in @taskroutine.

    For example, the method:

        def meth(self,*args,**kwargs):
            f=Future()
            @taskroutine('msg')
            def _func(task):
                with f:
                    f.setObject(doSomething())

            return self.mgr.runTasks(_func(),f)

    is equivalent to:

        @taskmethod('msg')
        def meth(self,*args,**kwargs):
            return doSomething()
    '''
    self,args=args[0],args[1:]
    mgr=getattr(self,mgrName)
    f=Future()

    def _task(task=None): # task proxy function, calls `meth' storing results/exceptions in f
        with f:
            kwargs[selfName]=task
            f.setObject(meth(self,*args,**kwargs))

    return mgr.runTasks(Task(taskLabel or meth.__name__,func=_task,selfName=selfName),f)


def readBasicConfig(filename):
    '''
    Read the config (.ini) file `filename' into a map of name/value pairs. The values must be acceptable inputs to
    ast.literal_eval(), ie. literals. This is for security since eval() on untrusted input can do interesting things.
    '''
    cparser=configparser.RawConfigParser()
    cparser.optionxform=str
    results=cparser.read(filename)

    if len(results)!=1:
        raise IOError('Cannot parse config file %r' %filename)

    sections=list(cparser.sections())+[configparser.DEFAULTSECT]
    results={}
    for s in sections:
        for n,v in cparser.items(s):
            results[n]=ast.literal_eval(v)

    return results


def storeBasicConfig(filename,values):
    '''
    Store the name/value map `values' into file `filename' as a config (.ini) file. The keys of `values' must be
    strings and the values must be literal types. All values go into the DEFAULT section of the file.
    '''
    cparser=configparser.RawConfigParser()
    cparser.optionxform=str
    for k,v in sorted(values.items()):
        cparser.set(None,str(k),repr(v))

    with open(filename,'w+') as o:
        cparser.write(o)


def setTrace():
    '''Enables tracing for the calling thread. This behaviour is unreliable and spews to logs or stdout.'''
    def trace(frame, event, arg):
        try:
            filename=frame.f_code.co_filename
            threadname=currentThread().getName()

            if 'threading' in filename: # ignore thread code tracing
                return None

            if logging.getLogger().getEffectiveLevel()==logging.DEBUG:
                logging.debug("%s:%s:%d: %s",threadname,filename, frame.f_lineno,event)
            else:
                printFlush("%s:%s:%d: %s"%(threadname,filename, frame.f_lineno,event))
        except:
            pass # modules get nullified at shutdown so suppress that exception

        return trace

    sys.settrace(trace)


def getAppDir():
    '''Returns the application's directory as stored in the APPDIRVAR environment variable.'''
    import __init__
    return os.path.abspath(os.getenv(__init__.APPDIRVAR,'./'))


def setLogging(logfile='eidolon.log',filemode='a'):
    '''Enables logging to the given file (by default same file as the renderer writes to) with the given filemode.'''

    if os.path.split(logfile)[0].strip()=='': # if the logfile is a relative path, put it in Eidolon directory
        logfile=os.path.join(getAppDir(),logfile)

    global logFilename

    logFilename=logfile

    logging.basicConfig(
        format='%(asctime)s %(message)s',
        filename=logfile,
        filemode=filemode,
        level=logging.DEBUG,
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logging.getLogger().setLevel(logging.DEBUG)
    logging.info('Start log')
    logging.raiseExceptions=False # stop exception prints about the log file being closed when writing traces


def addLibraryFile(lib):
    '''Add the nominated egg/wheel file to the end of the system path, assuming this is in ${APPDIR}/Libs/python.'''
    import __init__
    lib=os.path.join(getAppDir(),__init__.LIBSDIR,'python',lib)
    egg=ensureExt(lib,'.egg')
    whl=ensureExt(lib,'.whl')

    if os.path.exists(egg):
        sys.path.append(egg)
    elif os.path.exists(whl):
        sys.path.append(whl)
    else:
        raise ValueError('Library file %s.egg/.whl does not exist'%lib)


def processExists(pid):
    '''Returns true if the process identified by `pid' is running and active, false if it doesn't exist or has crashed.'''
    if isWindows: # adapted from http://www.madebuild.org/blog/?p=30
        _PROCESS_QUERY_INFORMATION=1024 # OpenProcess requires this access rights specifier
        _STILL_ACTIVE = 259 # GetExitCodeProcess uses a special exit code to indicate that the process is still running.

        import ctypes
        import ctypes.wintypes
        kernel32 = ctypes.windll.kernel32

        handle = kernel32.OpenProcess(_PROCESS_QUERY_INFORMATION, 0, pid)
        if handle == 0:
            return False

        # If the process exited recently, a handle may still exist for the pid. So, check if we can get the exit code.
        exitcode = ctypes.wintypes.DWORD()
        result = kernel32.GetExitCodeProcess(handle, ctypes.byref(exitcode)) # returns 0 if failed
        kernel32.CloseHandle(handle)

        # See if we couldn't get the exit code or the exit code indicates that the process is still running.
        return result!=0 and exitcode.value == _STILL_ACTIVE
    else: # non-Windows platforms, kill is supported in Windows as of 2.7 but doesn't detect crashed processes correctly
        try:
            os.kill(pid, 0) # signal 0 does nothing but still raises an exception if the process doesn't exist
            return True
        except OSError:
            return False


def getWinDrives():
    '''Returns available Windows drive letters.'''
    import win32api
    d=win32api.GetLogicalDriveStrings()
    return [dd[0] for dd in d.split('\x00') if dd]


def getUsername():
    '''Returns the username in a portable and secure way which works with 'su' and non-terminal processes.'''
    if isWindows:
        import win32api,win32con
        hostuname=win32api.GetUserNameEx(win32con.NameSamCompatible)
        return str(hostuname.split('\\')[-1])
    else:
        import pwd
        return pwd.getpwuid(os.getuid()).pw_name


def addPathVariable(varname,path,append=True):
    '''
    Add the string `path' to the environment variable `varname' by appending (if `append` is True) or prepending `path'
    using os.pathsep as the separator. This assumes `varname' is a path variable like PATH. Blank paths present in the
    original variable are moved to the end to prevent consecutive os.pathsep characters appearing in the variable. If
    `varname' does not name a variable with text it will be set to `path'.
    '''
    var=os.environ.get(varname,'').strip()

    if var: # if the variable exists and has text
        paths=[p.strip() for p in var.split(os.pathsep)] # split by the separator and strip whitespace just in case
        paths.insert(len(paths) if append else 0,path) # append or prepend `path'
        if '' in paths: # need to move the blank path to the end to prevent :: from appearing in the variable
            paths=filter(bool,paths)+['']
    else:
        paths=[path] # variable is new so only text is `path'

    os.environ[varname]=os.pathsep.join(paths)


def execfileExc(file_or_path,localvars,storeExcepts=True,streams=None):
    '''
    Executes the file or file path `file_or_path' in the same manner as execfile() with `localvars' as the local variable
    environment. If `storeExcepts' is True, whenever the code encounters an exception it is added to a list and this
    routine will then attempt to continue interpreting the code. The list of raised exceptions is then returned by the
    routine. If `storeExcepts' is False execution stops on the first exception which is raised. If `streams' is given,
    it must be a triple of objects suitable to substitute for the streams (sys.stdin, sys.stdout, sys.stderr) which are
    temporarily reassigned for the duration of execution.
    '''
    exclist=[]
    linebuffer=[]
    lastindent=0
    templine=None
    openedfile=False
    filename='<script>'
    count=1

    if isinstance(file_or_path,str): # open the file
        openedfile=True
        filename=file_or_path
        file_or_path=open(file_or_path)

    if streams: # substitute the IO streams
        sys.stdin,sys.stdout,sys.stderr=streams

    try:
        line=file_or_path.readline()
        while line:
            line=line.rstrip() # strip right side empty space including the trailing newline

            indent=first(i for i,c in enumerate(line) if c not in string.whitespace) if line else 0

            if indent==0 and lastindent>0 and line: # complete an indented block if this line of code has indentation
                templine=line # the current line shouldn't be executed with the finished block, save for next loop
                lastindent=0
            elif line: # otherwise if the line isn't empty add it to the buffer of lines
                linebuffer.append(line)
                lastindent=indent

            try:
                if indent==0 and line: # only attempt to execute whole code blocks
                    lineadd=['']*(count-len(linebuffer)) # add blank lines before the code to ensure line numbers of stack traces are correct
                    c=compile_command('\n'.join(lineadd+linebuffer)+'\n',filename,'exec') # raises syntax exceptions
                    if c:
                        linebuffer=[]
                        # TODO: definitely not Py3 compatible
                        exec c in localvars # raises execution exceptions (Note: exec tuple syntax encounters parser bug on python versions below 2.7.9)

            except Exception as e:
                linebuffer=[] # any exception means the stored code is possibly bogus so reject
                if storeExcepts: # store the whole stack trace
                    format_exc=traceback.format_exc()
                    exclist.append((e,format_exc))
                else:
                    raise

            # line becomes templine if it's present (ie. execute the code that ended a block next time around)
            if templine!=None:
                line=templine
                templine=None
            else: # otherwise line becomes the next line in the file
                line=file_or_path.readline()
                count+=1
                if not line and linebuffer: # ensure the last code line/block is executed
                    line='\n'

        return exclist
    finally:
        if streams: # replace the original IO streams
            sys.stdin,sys.stdout,sys.stderr=sys.__stdin__,sys.__stdout__,sys.__stderr__

        if openedfile: # close the file only if we've opened it
            file_or_path.close()


def execBatchProgram(exefile,*exeargs,**kwargs):
    '''
    Executes the program `exefile' with the string arguments `exeargs' as a batch process. The return result is a return
    code and output string pair. The integer return code is taken from the program, in the usual case 0 indicating a
    correct execution and any other value indicating failure, and the output is a string of the merged stdout
    and stderr text. If the program requires input it will deadlock, this is a batch operation routine only. A
    keyword value `timeout' can be given indicating how long to wait for the program in seconds before killing it,
    otherwise the routine will wait forever. If the keyword `logcmd' is True then the command line to be executed is
    printed to stdout before being run. If a log file path is given in keyword `logfile', the output from the program
    will be piped to that file.
    '''
    timeout=kwargs.get('timeout',None) # timeout time value in seconds
    cwd=kwargs.get('cwd',None)
    exefile=os.path.abspath(exefile)
    output=''
    errcode=0

    if isWindows:
        exefile=ensureExt(exefile,'.exe')

    if kwargs.pop('logcmd',False):
        printFlush(exefile,exeargs,kwargs)

    if not os.path.isfile(exefile):
        raise IOError('Cannot find program %r' %exefile)

    # if log file given, open it to receive output, otherwise send output to pipe
    if 'logfile' in kwargs:
        stdout=open(kwargs['logfile'],'w+')
    else:
        stdout=subprocess.PIPE

    proc=subprocess.Popen([exefile]+list(exeargs),stderr = subprocess.STDOUT, stdout = stdout,cwd=cwd)

    # if timeout is present, kill the process and throw an exception if the program doesn't finish beforehand
    if timeout!=None and timeout>0:
        tm=float(timeout)
        lasttime=time.time()
        while proc.poll()==None and tm>0:
            curtime=time.time()
            tm-=curtime-lasttime
            lasttime=curtime
            time.sleep(0.01)

        if tm<=0:
            proc.kill()
            output='Process %r failed to complete after %.3f seconds\n' %(exefile,timeout)
            errcode=1

    out,_ = proc.communicate()
    returncode= errcode if errcode!=0 and proc.returncode==0 else proc.returncode # choose errcode if the process was killed

    # if a log file was specified, read it into `out' since it will be empty in this case
    if 'logfile' in kwargs:
        stdout.seek(0)
        out=stdout.read()
        stdout.close()

    return (returncode,output+(out or ''))


def enumAllFiles(rootdir):
    '''Yields all absolute path regular files in the given directory.'''
    for root, dirs, files in os.walk(rootdir):
        for f in sorted(files):
            yield os.path.join(root,f)


def checkValidPath(path):
    '''
    Returns values to indicate if `path' is a valid pathname and if not why. This will return 0 if `path' exists or
    otherwise is a valid path, 1 if not accessible, 2 if the filename component contains invalid characters, and 3 if
    the extension contains invalid characters.
    '''
    pdir,basename,ext=splitPathExt(path)
    invalidchars='\\/:;*?!<>|"\'\0'

    if os.path.exists(path):
        return 0
    elif not os.access(pdir, os.W_OK):
        return 1
    elif any(i in basename for i in invalidchars):
        return 2
    elif any(i in ext for i in invalidchars):
        return 3

    return 0


def getValidFilename(name):
    '''Replaces all invalid filename characters with underscore.'''
    return re.sub('[\.\s\<\>?:;!*/\|%\'\"]', '_', name)


def ensureExt(path,ext,replaceExt=False):
    '''
    Ensures the returned path ends with extension `ext'. If the path doesn't have `ext' as its extension, this returns
    `path' with `ext' appended, replacing any existing extension if `replaceExt' is True. Eg. ensureExt('foo','.bar')
    returns 'foo.bar' as does ensureExt('foo.baz','.bar',True), but ensureExt('foo.baz','.bar') returns 'foo.baz.bar'.
    '''
    namepart,extpart=os.path.splitext(path)
    if namepart and extpart!=ext:
        path=(namepart if replaceExt else path)+ext

    return path


def splitPathExt(path,fullExt=False):
    '''
    For the given path, return the containing directory, filename without extension, and extension. If `fullExt' is
    True, consider everything to the right of the first period as the extension rather than from the last. For example,
    splitPathExt('foo.bar.baz')[2] produces '.baz' whereas splitPathExt('foo.bar.baz',True)[2] produces '.bar.baz'.
    '''
    path,basename=os.path.split(path)

    if fullExt and '.' in basename:
        basename,ext=basename.split('.',1) # consider everything to the right of the first . as the extension
        ext='.'+ext
    else:
        basename,ext=os.path.splitext(basename) # consider everything to the right of the last . as the extension

    return path,basename,ext


def timeBackupFile(filename,backDir=None):
    '''
    Copies `filename' if it exists to the same directory (or `backDir' if not None) with the system time and ".old"
    appended to the name. The new base filename is returned if this was done, otherwise None.
    '''
    if os.path.exists(filename):
        root,name=os.path.split(filename)
        backDir=backDir or root
        timefile='%s.%s.old' %(name,time.time())
        shutil.copyfile(filename,os.path.join(backDir,timefile))
        return timefile


def sortFilenameList(names,sortIndex,regex=None):
    '''
    Sort the list of filenames `names' based on a common numerical component. This assumes the files have a sequential
    numbering scheme which may not prefix numbers with zeros and so the alphabetical ordering is not the same as numerical.
    This function parses out the numerical component of each name and sorts using these as integer values.
    '''
    sortorder=getStrSortIndices([os.path.split(n)[1] for n in names],sortIndex,regex)
    return indexList(sortorder,names)


def isSameFile(src,dst):
    '''Returns True if the files `src' and `dst' refer to the same extant file.'''
    if not os.path.exists(src) or not os.path.exists(dst):
        return False

    if hasattr(os.path, 'samefile') and os.path.samefile(src, dst):
        return True

    if os.path.normcase(os.path.abspath(src)) == os.path.normcase(os.path.abspath(dst)):
        return True

    return False


def isTextFile(filename,bufferlen=512):
    '''Checks the first `bufferlen' characters in `filename' to assess whether the file is a text file or not.'''
    buf=open(filename).read(bufferlen)
    return '\0' not in buf # maybe something a bit more involved than just checking for null characters?


def copyfileSafe(src,dst,overwriteFile=False):
    '''
    Copy file from path `src' to path `dst' only if they are not the same file. If `overwriteFile' is True, raise an
    IOError if `dst' already exists.
    '''
    if not isSameFile(src,dst):
        if not overwriteFile and os.path.exists(dst):
            raise IOError('File already exists: %r'%dst)

        shutil.copyfile(src,dst)


def renameFile(oldpath,newname,moveFile=True,overwriteFile=False):
    '''
    Replace the basename without extension in `oldpath' with `newname' and keeping the old extension. If `moveFile' is
    True, copy the old file to the new location and overwrite existing file if `overwriteFile' is True; IOError
    is thrown if this isn't possible or if the file exists and `overwriteFile' is False. Setting `moveFile' to False
    allows a "dry run" where the checks are performed but the file isn't moved. Returns the new path.
    Eg. renameFile('/foo/bar.baz.plonk','thunk') -> '/foo/thunk.baz.plonk'
    '''
    olddir,oldname,ext=splitPathExt(oldpath,True)
    newpath=os.path.join(olddir,newname+ext)

    if not os.path.exists(oldpath):
        raise IOError('Cannot move %r to %r, source file does not exist'%(oldpath,newpath))
    elif os.path.exists(newpath) and not overwriteFile:
        raise IOError('Cannot move %r to %r, destination file already exists'%(oldpath,newpath))
    elif isSameFile(oldpath,newpath):
        raise IOError('File names %r and %r refer to the same file'%(oldpath,newpath))
    elif moveFile:
        shutil.move(oldpath,newpath)

    return newpath


cumulativeTimes={}

def addCumulativeTime(name,val):
    global cumulativeTimes
    if len(cumulativeTimes)==0:
        atexit.register(printCumulativeTimes)

    cumulativeTimes[name]=val+cumulativeTimes.get(name,0.0)


def printCumulativeTimes():
    '''Print the cumulative times to the stdout.'''
    global cumulativeTimes
    printFlush('Total Global dT (s):')
    for i in cumulativeTimes.items():
        printFlush(' %s = %f'% i)


def timing(func):
    '''
    This simple timing function decorator prints to stdout/logfile (it uses printFlush) how many seconds a call to the
    original function took to execute, as well as the name before and after the call.
    '''
    @wraps(func)
    def timingwrap(*args,**kwargs):
        printFlush(func.__name__)
        start=time.time()
        res=func(*args,**kwargs)
        end=time.time()
        printFlush(func.__name__, 'dT (s) =',(end-start))
        return res

    return timingwrap


def cumulativeTime(func):
    '''Add the time taken to execute `func' to a stored cumulative time counter for that function.'''
    @wraps(func)
    def timingwrap(*args,**kwargs):
        start=time.time()
        res=func(*args,**kwargs)
        end=time.time()
        addCumulativeTime(func.__name__,end-start)
        return res

    return timingwrap


@contextlib.contextmanager
def timingBlock(name,printEntry=True,addCumulative=False):
    '''
    Provides a timing facility for 'with' code blocks. Argument `name' is printed when entering if `printEntry', and
    always printed when exiting. If `addCumulative' is True then add the value to the cumulative time counter.
    The yielded value is the starting time of the block.
    '''
    if printEntry:
        printFlush('>',name)
    start=time.time()
    yield start  # execute code in 'with' block
    end=time.time()
    printFlush('<',name,'dT (s) =',(end-start))
    if addCumulative:
        addCumulativeTime(name,end-start)


def argtiming(func):
    '''This decorator is the same as timing() except it will additionally print the arguments and return value.'''
    @wraps(func)
    def _wrap(*args,**kwargs):
        printFlush(func.__name__,'(',args,kwargs,')')
        start=time.time()
        res=func(*args,**kwargs)
        end=time.time()
        printFlush(func.__name__, 'dT (s) =',(end-start),res)
        return res

    return _wrap


def tracing(func):
    '''This decorator prints a stack trace when the wrapped function is called.'''
    @wraps(func)
    def _wrap(*args,**kwargs):
        trace=inspect.stack()
        lastfile=None
        for _,filename,line,routine,_,_ in trace[1:]:
            filename=os.path.basename(filename)
            if filename!=lastfile:
                printFlush(filename)
                lastfile=filename

            printFlush(' %i: %s'%(line,routine))

        printFlush(args,kwargs)
        return func(*args,**kwargs)

    return _wrap


def traverseObj(obj,func,visited=()):
    '''
    Attempt to visit every member of `obj' and every member of members etc. recursively. The callable `func' is applied
    to `obj' to determine when to stop traversing, returning False if a stop is requested. The set `visited' is the
    recursive accumulated list of visited objects used to prevent cycles.
    '''
    result=func(obj)
    visited=set(visited)
    visited.add(obj)

    if result!=False:
        for d in dir(obj):
            at=getattr(obj,d)
            if not d.startswith('__') and at not in visited:
                traverseObj(at,func,visited)


def isPicklable(obj):
    '''Returns True if `obj' can be pickled.'''
    try:
        pickle.dumps(obj)
        return True
    except:
        return False


def isIterable(obj):
    '''Returns True if `obj' is iterable type, ie. list, tuple, dict.'''
#   try:
#       return iter(obj) is not None
#   except:
#       return False
    return isinstance(obj, (list,tuple,dict))


def toIterable(obj):
    '''Returns an iterable of objects, which is `obj' if it's not a string and iterable, otherwise (obj,).'''
    return obj if not isinstance(obj,str) and isIterable(obj) else (obj,)


def memoized(converter=lambda i:i,initialmemo={}):
    '''
    Produces a memoized version of the applied function. This is only useful for functions which always return the
    same result for given arguments. When the function is called, the memo dictionary is checked to see if there's a
    result keyed to the given arguments. If so this is returned, otherwise the original function is called and the
    result is stored and returned. The `converter' argument is used to convert the results from the original
    function into a storable form (eg. use `tuple' to store results from generators). All arguments must be hashable.
    The dictionary `initialmemo' can be used to initialize the stored memo with given arg-result value pairs.
    '''
    def funcwrap(func):
        memo=dict(initialmemo) # distinct instance of this is created for each function and is bound in its scope

        @wraps(func)
        def memoizedfunc(*args,**kwargs):
            memokey=args+tuple(kwargs.values())
            if memokey not in memo:
                memo[memokey]=converter(func(*args,**kwargs))

            return memo[memokey]

        return memoizedfunc

    return funcwrap


def isMainThread():
    '''Returns true if the call thread is the main thread. This relies on checking against the type _MainThread.'''
    return isinstance(currentThread(),_MainThread)


def asyncfunc(func):
    '''
    Wraps the function `func' with a asynchronous version which executes the function's body in a daemon thread. The
    return value is the threading.Thread object executing the function, which an extra member `result' containing the
    Future object which will eventually store the return value or raised exception from calling `func'.
    '''
    @wraps(func)
    def funcwrap(*args,**kwargs):
        f=Future()
        def _call():
            with f:
                f.setObject(func(*args,**kwargs))

        t=threading.Thread(target=_call)
        t.daemon=True
        t.result=f
        t.start()
        return t

    return funcwrap


def partitionSequence(maxval,part,numparts):
    '''
    Calculate the begin and end indices in the sequence [0,maxval) for partition `part' out of `numparts' total
    partitions. This is used to equally divide a sequence of numbers (eg. matrix rows or array indices) so that they
    may be assigned to multiple procs/threads. The result `start,end' defines a sequence [start,end) of numbers.
    '''
    partsize=maxval/float(numparts)
    start=math.floor(part*partsize)
    end=math.floor((part+1)*partsize)
    if (maxval-end)<partsize:
        end=maxval

    return long(start),long(end)


def createShortName(*comps,**kwargs):
    '''Creates a string by joining components `comps' with _, shortening each component to max length `complen' or 10.'''
    complen=kwargs.get('complen',10)
    return '_'.join(n[:complen] if len(n)>complen else n for n in comps)


def uniqueStr(name,namelist,spacer='_'):
    '''
    Derive a string from `name' guaranteed to not be in `namelist'. If `name' isn't in `namelist', it will be returned
    unmodified, otherwise the created name will be `name' followed by `spacer' and a number which makes it unique.
    '''
    count=1
    newname=name

    while newname in namelist:
        newname='%s%s%.2i'%(name,spacer,count)
        count+=1

    return newname


def getStrSortIndices(strs,sortIndex,regex=None):
    '''
    Determine the sort order of iterable `strs' based on the component indexed by `sortIndex'. Each string is split
    using `regex' as the regular expression to use with re.split (by default it splits names by _-\. | characters),
    then the component at position `sortIndex' is used to determine the sort order either by casting to an integer or
    through string comparison if it isn't a number. The result is the index list specifying the sorted ordering, or is
    the empty list if `strs' is an empty sequence.
    '''
    strcomps=[re.split(regex or '\||_|-|\.|\ ',n) for n in strs]
    if not strcomps:
        return []

    minlen=min(len(n) for n in strcomps)
    if sortIndex>=minlen or sortIndex<-minlen:
        raise IndexError("`sortIndex' value %i is outside possible range [%i,%i]"%(sortIndex,-minlen,minlen-1))

    def convertFunc(n):
        try:
            return int(n[sortIndex])
        except:
            return n[sortIndex]

    return sortIndices(map(convertFunc,strcomps))


def getStrCommonality(str1,str2):
    '''
    Returns the maximal length initial substring that the two arguments strings have in common and the percentage of
    the minimal length this value represents. A result of (0,0.0) indicates the two strings have nothing in common. A
    value of (X,1.0) indicates that the shorter of the two strings is the prefix of the longer which has length X.
    Eg. getStrCommonality('foo','foul') = (2,0.6666666) indicating that the first 2 letters of 'foo' are common and
    represent 2/3rds of its length.
    '''
    minlen=min(len(str1),len(str2))
    index=first(i for i in xrange(minlen) if str1[i]!=str2[i])
    if index==None:
        index=minlen

    return index,index/float(minlen)


def getStrListCommonality(strs):
    '''Returns the index of the first character which is not common in all the strings of the list `strs'.'''
    sets=itertools.imap(set,itertools.izip(*strs))
    return first(i for i,s in enumerate(sets) if len(s)>1)


def findGlobMatch(globname,names):
    '''
    If `globname' is a globulated name (that is one ending with *) then return the first string in `names' which
    begins with `globname' minus the *, or None if there is no match. If `globname' doesn't end with * it is returned.
    This does NOT do regex matching using `globname', it only works with names created with globulateStrList().
    '''
    if globname in names:
        return globname
    elif globname[-1]=='*':
        gn=globname[:-1]
        return first(n for n in names if n.startswith(gn))
    else:
        return None


def printFlush(*args,**kwargs):
    '''
    Converts each element of 'args' into a string and prints them to a stream separated by spaces. The same string is
    also printed to the log. The keyword argument `end' is used to specify the end string, the default is '\n'. If the
    keyword argument `stream' is omitted the string is printed to sys.stdout, otherwise this argument can be used to
    supply a different object with write() and flush() methods.
    '''
    msg=' '.join(map(str,args))
    stream=kwargs.get('stream',sys.stdout)
    stream.write(msg+kwargs.get('end','\n'))
    stream.flush()
    logging.info(msg)


def setStrIndent(s,indent=0,useTab=False):
    '''
    Remove the indentation from the code string `s' and set the leading indentation to be `indent' number of characters,
    spaces if `useTab' is False, tabs otherwise.
    '''
    ss=[l.strip()+'\n' for l in s.split('\n')]
    spacer=('\t' if useTab else ' ')*indent

    return spacer.join(['']+ss).rstrip()


def getUnitValue(val):
    '''
    Given a size `val' in bytes, returns a string with the size rounded to the nearest base 2 unit (B, kB, MB, etc.)
    with the appropriate unit suffix addded to the end.
    '''
    suffixes=['B','kB','MB','GB','TB','PB']
    power=0

    while val>1000 and (power+1)<len(suffixes):
        val/=1024.0
        power+=1

    return '%.2f%s' % (val,suffixes[power])


def getPaddedNum(val,maxval):
    '''Return the string form of `val' with enough pad zeros for as many digits as `maxval'.'''
    power=len(str(int(maxval)))
    result='%0*i'%(power,int(val))

    if isinstance(val,float):
        power=len(str(maxval).split('.')[-1])
        result+='%0.*f'%(power,val-int(val))

    return result


def parseSequenceSpec(spec,maxval):
    '''
    Creates a list of integer values based on the sequence string specification. The specifier string `spec' is a
    comma-separated list of specifiers, which are either a integer number, an integer range N-M for integers N and M-1
    or N-* where * is taken to be `maxval'-1, or an integer range N-S-M or N-S-* where S is the skip interval.
    For example: "1,6-8,9-2-14,16-*" yields [1, 6, 7, 9, 11, 13, 16, 17, 18, 19] for a `maxval' of 20. The resulting
    list is sorted with duplicates removed.
    '''
    selected=set()

    for part in spec.split(','):
        try:
            ipart=int(part)
            selected.add(ipart)
        except:
            rpart=part.split('-')

            if len(rpart) not in (2,3):
                raise ValueError("Bad sequence specifier '"+part+"'")

            if rpart[-1]=='*':
                rpart[-1]=maxval

            if len(rpart)==2:
                rpart.append(1)
            else:
                rpart[1],rpart[2]=rpart[2],rpart[1]

            rpart=map(int,rpart)

            if rpart[0]>rpart[1]:
                raise ValueError("Bad sequence specifier '"+part+"'")

            selected.update(xrange(*rpart))

    selected=sorted(list(selected))

    if selected[0]<0 or selected[-1]>=maxval:
        raise ValueError('Values must be in range 0 to '+str(maxval))

    return selected


def epsilonZero(val):
    '''Return 0.0 if `val' is within 'epsilon' of 0.0, otherwise return 'val' converted to a float value.'''
    val=float(val)
    return 0.0 if abs(val)<epsilon else val


def isInEpsilonRange(val,minv,maxv):
    '''Returns true if `val' is in the range [minv,maxv] expanded in both directions by 'epsilon'.'''
    return (minv-epsilon)<=val<=(maxv+epsilon)


def checkNan(val):
    '''Asserts that `val' is not NaN and then returns it.'''
    assert not math.isnan(val)
    return val


def indexList(indices,lst):
    '''Returns a list containing `lst'[i] for each index i in `indices'. '''
    assert all(0<=i<len(lst) for i in indices)
    return [lst[i] for i in indices]


def rotateIndices(start,numinds):
    '''Produces the indices for a list `numinds' long rotated so that index `start' is the new first index.'''
    return [(i+start)%numinds for i in xrange(numinds)]


def sortIndices(lst):
    '''Returns a list of indices into iterable `lst' which index the members of `lst' in sorted order.'''
    return sorted(range(len(lst)),key=lambda i:lst[i])


def sortedInsert(lst,val):
    '''Given a sorted list `lst', insert `val' in the first position in `lst' which maintains the ordering.'''
    i=first(i for i,v in enumerate(lst) if v>=val)
    if i!=None:
        lst[i:i]=[val]
    else:
        lst.append(val)


def minmaxIndices(lst):
    '''Returns the lowest indices of the minimal and maximal values in iterable `lst'.'''
    it=iter(lst)
    minind=0
    maxind=0
    minval=next(it)
    maxval=minval

    for i,v in enumerate(it):
        if v<minval:
            minval=v
            minind=i+1
        elif v>maxval:
            maxval=v
            maxind=i+1

    return minind,maxind


def fcomp(*funcs):
    '''Functional composition operator, fcomp(f0,f1,...,fn) is equivalent to lambda i:f0(f1(...fn(i)...)).'''
    return lambda i:reduce(lambda v,f:f(v),reversed(funcs),i)


def first(iterable,default=None):
    '''Returns the first item in the given iterable, meaningful mostly with 'for' expressions.'''
    for i in iterable:
        return i
    return default


def last(iterable,default=None):
    '''Returns the last item in the given iterable, meaningful mostly with 'for' expressions.'''
    result=default
    for i in iterable:
        result=i
    return result


def prod(i,initial=1):
    '''Returns the product of the given iterable, starting with the given initial value.'''
    return reduce(operator.mul,i,initial)


def listSum(lists):
    '''Sums the iterable of lists into one long list.'''
    return sum(itertools.imap(list,lists),[])


def zipWith(op,*vals):
    '''Starmap `op' to each tuple derived from zipping (izip) the iterables in `vals'.'''
    return itertools.starmap(op,itertools.izip(*vals))


def mulsum(ls,rs):
    '''Returns the sum of each element of `ls' multiplied by the equivalent element in `rs'.'''
    muls=zipWith(operator.mul,ls,rs)
    return sum(muls,next(muls)) # need to choose an initial value if the first member of muls cannot be added to 0


def successive(iterable,width=2,cyclic=False):
    '''
    Yields tuples of `width' values in order from `iterable' starting from the first value, then from the second value,
    etc. If `cyclic' is True then `iterable' is treated as a cycle of values and the last `width' tuples will have
    values starting from the end of the sequence then looping back to the beginning.
    Eg. successive(range(5))        -> (0, 1), (1, 2), (2, 3), (3, 4)
        successive(range(5),3,True) -> (0, 1, 2), (1, 2, 3), (2, 3, 4), (3, 4, 0), (4, 0, 1)
    '''
    assert width>1
    it=iter(iterable)
    val=tuple(next(it) for i in xrange(width)) # get the first `width' values

    if cyclic: # if cyclic, make `it' into a chain that effectively sticks `val' (minus its last value) onto the end
        it=itertools.chain(it,iter(val[:-1]))

    while True: # The Pythonic Way?
        yield val
        val=val[1:]+(next(it),) # eventually next() will raise an exception if `iterable' is finite and the loop will exit


def group(iterable,width=2):
    '''
    Groups successive items from `iterable' into `width' size tuples and yields each sequentially. If the number of items
    in `iterable' isn't a multiple of `width', the last shortened group is discarded. Eg. group(range(5)) -> (0,1), (2,3)
    '''
    assert width>0
    it=iter(iterable)
    rng=range(width)

    p=tuple(next(it) for i in rng) # get `width' values
    while len(p)==width: # loops so long as `iterable' has enough values, needed since exception from next() is suppressed by tuple()
        yield p
        p=tuple(next(it) for i in rng) # get the next `width' values


def matIter(mat):
    '''Iterate over each element of each iterable yielded by `mat' (ie. a list of lists).'''
    for m in mat:
        for mm in m:
            yield mm


def matIndices(mat,start=0):
    '''Returns a matrix with the same dimensions as `mat' with ascending value entries starting from `start'.'''
    result=[]
    count=start
    for m in mat:
        result.append(range(count,count+len(m)))
        count+=len(m)

    return result


def arrayIndex(inds,dims,circular):
    '''
    For an array of dimensions `dims' flattened into a 1D list, get the index in that list corresponding to array
    indices `inds'. All arguments must be lists/tuples of the same length. For each i in `inds' with corresponding
    dimension d in `dims', the value used for calculation is i%d if the corresponding value in `circular' is True,
    which allows for negative values and circular indexing. If the value in `circular' is False, the value is
    clamp(i,0,d-1) which keeps the resulting index in range.

    For example, for an array of dimensions (4,4,4) flattened into a 1D array of length 64, the index in the 1D array
    for position (1,2,3) in the 3D array is given by arrayIndex((1,2,3),(4,4,4),[False]*3) which is 57.
    '''
    #clampfunc=lambda i,d:clamp(i,0,d-1)
    #funcs=[(operator.mod if circular[ind] else clampfunc) for ind in range(len(inds))]
    #return sum(funcs[ind](i,d)*prod(dims[:ind]) for ind,(i,d) in enumerate(zip(inds,dims)))

    def _clampfunc(ind,dim,circ):
        return ind%dim if circ else clamp(ind,0,dim-1)

    return sum(_clampfunc(i,d,c)*prod(dims[:ind]) for ind,(i,d,c) in enumerate(zip(inds,dims,circular)))


def xisToPiecewiseXis(xis,dims,limits=None):
    '''
    Given a set of xi values `xis' and assumming a piecewise basis function on an grid of control points with dimensions
    `dim', calculate the xi values for the local element to apply to the basis function, and the indices for the control
    point of that element at xi=0. The unit values in `xis' represent a position in the xi space covering the whole
    object defined by the control point grid, the resuting xi values represent the equivalent position within one element
    within this control point grid. The returned indices denote which control point in the grid is this element's control
    point at the xi space origin. The xi coordinates of the other control points are assumed to be integers, so one can
    figure out what the other control point indices in the grid are by adding the element's control point xis to this
    index. The list `limits' must contain pairs of integers for each dimension of `dims' and state how many indices
    from the faces of the grid are control points. If `limits' is None the the value [(1,1)]*len(dims) is used. This
    implies that the first and last values in the grid in every dimension are control points.
    '''
    limits=limits or [(1,1)]*len(dims)
    pxis=[]
    indices=[]
    for x,d,(lmin,lmax) in zip(xis,dims,limits):
        xx=x*(d-lmax-lmin-1)
        ixx=int(xx)
        pxis.append(xx-ixx)
        indices.append(ixx+lmin)

    return pxis,indices


def frange(start,stop=None,step=None):
    '''Same as 'xrange', just with floats.'''
    if not stop:
        stop=start
        start=0.0

    if not step:
        step=1.0

    start=epsilonZero(start)
    stop=epsilonZero(stop)
    step=epsilonZero(step)

    if abs(stop-start)<=epsilon:
        return

    if step<=0:
        raise ValueError('Step must be positive and non-zero (step=%s)' % (str(step),))

    if stop<0 or start<0:
        raise ValueError('All arguments must be positive (start=%s, stop=%s)' % (str(start),str(stop)))

    if stop<start:
        raise ValueError('Stop value must be greater than start value (start=%s, stop=%s)' % (str(start),str(stop)))

    # Kahan algorithm (W. Kahan. 1965. Pracniques: further remarks on reducing truncation errors. Commun. ACM 8)

    comp=0.0 # compensation value for low order bits
    total=start # running total

    while total < stop-epsilon:
        yield total
        y = step - comp
        temp = total + y
        comp = (temp - total) - y
        total = temp


def trange(*vals):
    '''
    Produces a sequence of cartesian product tuples derived from multiple sequences as defined by the given arguments.
    An integer argument 'a' corresponds to  'xrange(a)', a float argument corresponds to 'frange(a)'. Tuple arguments
    are either pairs or triples of ints or floats which correspond to the start,stop,step set of values for xrange or
    frange. If 'a' is otherwise iterable it is used directly to derive values.

    Eg. list(trange((0,6,2),(0.0,0.6,0.2))) yields
       [(0, 0.0), (0, 0.2), (0, 0.4), (2, 0.0), (2, 0.2), (2, 0.4), (4, 0.0), (4, 0.2), (4, 0.4)]
    '''
    ranges=[]
    for v in vals:
        if isinstance(v,tuple) and len(v) in (2,3):
            if any(isinstance(vv,float) for vv in v):
                ranges.append(frange(*v))
            else:
                ranges.append(xrange(*v))
        elif isIterable(v):
            ranges.append(v)
        elif isinstance(v,float):
            ranges.append(frange(v))
        else:
            ranges.append(xrange(v))

    return itertools.product(*ranges)


def binom(n,k):
    '''
    Calculates the binomial coefficient (n choose k) using the multiplicative formula.
    This is equivalent to the expression n!/(k!(n-k)!) but faster.
    '''
    result=1

    for i in xrange(1,k+1):
        result=(result*(n-(k-i)))/i

    return result


def bern(n,i,u):
    '''Bernstein coefficient, (n choose i)*(u**i)*((1-u)**(n-i))'''
    return binom(n,i)*(u**i)*((1-u)**(n-i))


def clamp(val,minv,maxv):
    '''Returns minv if val<minv, maxv if val>maxv, otherwise val.'''
    if val>maxv:
        return maxv
    if val<minv:
        return minv
    return val


def lerp(val,v1,v2):
    '''Linearly interpolate between `v1' and `v2', val==0 results in `v1'.'''
    return v1+(v2-v1)*val


def lerpXi(val,minv,maxv):
    '''
    Calculates the linear interpolation xi value corresponding to `val' if interpolated over the range [minv,maxv],
    ie. if lerpXi(V,A,B)==X then lerp(X,A,B)==V assuming A<B. If minv>=maxv then `val' is returned.
    '''
    return val if minv>=maxv else float(val-minv)/float(maxv-minv)


def avg(vals,initial=0.0):
    '''Returns the average of the values derived from the iterable `vals', or `initial' if there are none.'''
    l=0.0
    sumv=initial
    for v in vals:
        sumv=v+sumv # if v overrides + this allows it to be used to accumulate the sumv value, instead of "sumv+=v" which does not
        l+=1.0

    return initial if l==0.0 else sumv/l


def mag(vals):
    '''Return the magnitude of the n-dimensional vector `vals'.'''
    return math.sqrt(sum(x*x for x in vals))


def stddev(vals,initial=0.0):
    '''Returns the standard deviation of the values derived from the iterable `vals', or `initial' if there are fewer than 2.'''
    a=avg(vals,initial)
    sumv=initial
    l=0.0
    for v in vals:
        sumv=((v-a)**2)+sumv
        l+=1.0

    return math.sqrt(sumv/(l-1)) if l>1 else initial


def avgspan(vals):
    '''Returns the average difference between successive values derived from the given iterable.'''
    return avg(b-a for a,b in successive(vals))


def minmaxval(minv,maxv,val):
    '''Returns min(val,minv),max(val,maxv) or val,val if either `minv' or `maxv' is None.'''
    if minv is None or maxv is None:
        return val,val
    else:
        return min(val,minv),max(val,maxv)


def minmax(*items,**kwargs):
    '''
    Returns the minimum and maximum values, like a combined min and max. If the keyword argument `ranges' is True then
    the members of `items' are treated as (min value, max value) pairs and the result is the minimal of the min values
    and the maximal of the max values.
    '''
    minv=None
    maxv=None
    mink=None
    maxk=None

    key=kwargs.get('key',lambda i:i)
    ranges=kwargs.get('ranges',False)

    if len(items)==1:
        items=items[0]

    if ranges:
        for i in items:
            ki=key(i)
            if i==None or ki==None:
                continue

            if minv==None:
                minv=i[0]
                maxv=i[1]
            else:
                if ki[0]<mink:
                    minv=i[0]
                if ki[1]>maxk:
                    maxv=i[1]

            mink=key(minv)
            maxk=key(maxv)
    else:
        for i in items:
            ki=key(i)
            if i==None or ki==None:
                continue

            if minv==None:
                minv=i
                maxv=i
            elif ki<mink:
                minv=i
            elif ki>maxk:
                maxv=i

            mink=key(minv)
            maxk=key(maxv)

    return minv,maxv


def radCircularConvert(rad):
    '''Converts the given rad angle value to the equivalent angle on the interval [-pi,pi].'''
    while rad>math.pi:
        rad-=math.pi*2

    while rad<-math.pi:
        rad+=math.pi*2

    return rad


def radClamp(rad):
    '''Clamps the given value between pi*0.5 and pi*-0.5.'''
    return clamp(rad,-halfpi,halfpi)


def getClosestPower(val):
    '''returns the power of 10 closest to the absolute value of `val'.'''
    val=abs(val)

    if val>=1:
        p=0
        val1=val
        while val1>1.0:
            p+=1
            val1/=10.0

        return p if val>(10**p)*0.5 else (p-1)
    else:
        p=0
        val1=val
        while val1<1.0:
            p-=1
            val1*=10.0

        return p if val<(10**(p+1))*0.5 else (p+1)


# try http://www.cs.ubc.ca/~rbridson/docs/bridson-siggraph07-poissondisk.pdf for better http://bost.ocks.org/mike/algorithms/
def generatePoisson2D(width,height,ptscount,mindist=None,startpt=None):
    '''
    Generates a randomly distributed set of 2D points across the rectangle defined by `width' and `height'. The
    `mindist' distance is the closest any two points can be and `ptscount' value is the maximum number of points
    returned, thus if `mindist' is too large fewer points are returned owing to too little space on the rectangle. If
    no `mindist' value is given, one is chosen which tends to distribute points evenly across the whole rectangle and
    return almost exactly 'ptscount' points. If `startpt' is provided the generation process begins at that point in
    the rectangle, otherwise a random point is chosen. This value and the returned points are all float pairs.
    '''

    if ptscount==0:
        return []

    if mindist==None:
        # this value seems to distribute `ptscount' points evenly over the whole rectangle
        mindist=math.sqrt((width*height)/ptscount)/(math.pi/math.e)

    assert width>0
    assert height>0
    assert mindist>0
    assert ptscount>0

    random.seed(ptscount)

    cellsize=mindist/math.sqrt(2)

    gw=int(math.ceil(width/cellsize))
    gh=int(math.ceil(height/cellsize))

    grid=arrayV(None,gw,gh)

    processlist=[]
    samplepts=[]

    def toGrid(x,y):
        return int(x/cellsize),int(y/cellsize)

    def generatePtAround(x,y):
        radius=mindist*(random.random()+1)
        angle=2*math.pi*random.random()
        return x+(radius*math.cos(angle)),y+(radius*math.sin(angle))

    def addPoint(pt):
        processlist.append(pt)
        samplepts.append(pt)
        i,j=toGrid(*pt)
        grid[i][j]=pt

    def inNeighbourhood(x,y):
        gpt=toGrid(x,y)

        for i,j in trange((gpt[0]-1,gpt[0]+2),(gpt[1]-1,gpt[1]+2)):
            if 0<=i<gw and 0<=j<gh:
                g=grid[i][j]
                if g!=None and math.sqrt((g[0]-x)**2+(g[1]-y)**2)<mindist:
                    return True

        return False

    if startpt!=None:
        addPoint(startpt)
    else:
        addPoint((random.randint(0,width-1),random.randint(0,height-1)))

    if ptscount>1:
        while len(processlist)>0 and len(samplepts)<ptscount:
            pos=random.randint(0,len(processlist)-1)
            pt=processlist.pop(pos)
            for i in range(ptscount):
                nx,ny=generatePtAround(*pt)
                if 0<=nx<=width and 0<=ny<=height and not inNeighbourhood(nx,ny):
                    addPoint((nx,ny))
                    if len(samplepts)==ptscount:
                        return samplepts

    return samplepts


def generatePoisson3D(width,height,depth,ptscount,mindist=None,startpt=None):
    '''
    Generates a randomly distributed set of 3D points across the rectangle defined by `width', `height', and `depth'.
    The other arguments and general behaviour of this algorithm are the same as that for generatePoisson2D() except
    return values and `startpt' are float triples.
    '''

    if ptscount==0:
        return []

    if mindist==None:
        # this value seems to distribute `ptscount' points evenly over the whole rectangle
        mindist=math.sqrt((width*height*depth)/ptscount)/(math.pi/math.e)

    assert width>0
    assert height>0
    assert depth>0
    assert mindist>0
    assert ptscount>0

    random.seed(ptscount)

    cellsize=mindist/math.sqrt(2)

    gw=int(math.ceil(width/cellsize))
    gh=int(math.ceil(height/cellsize))
    gd=int(math.ceil(depth/cellsize))

    grid=arrayV(None,gw,gh,gd)
    processlist=[]
    samplepts=[]

    def toGrid(x,y,z):
        return int(x/cellsize),int(y/cellsize),int(z/cellsize)

    def generatePtAround(x,y,z):
        radius=mindist*(random.random()+1)
        angle1=2*math.pi*random.random()
        angle2=2*math.pi*random.random()
        sin2=math.sin(angle2)
        return x+(radius*math.cos(angle1)*sin2),y+(radius*math.sin(angle1)*sin2),z+(radius*math.cos(angle2))

    def addPoint(pt):
        processlist.append(pt)
        samplepts.append(pt)
        i,j,k=toGrid(*pt)
        grid[i][j][k]=pt

    def inNeighbourhood(x,y,z):
        gpt=toGrid(x,y,z)

        for i,j,k in trange((gpt[0]-1,gpt[0]+2),(gpt[1]-1,gpt[1]+2),(gpt[2]-1,gpt[2]+2)):
            if 0<=i<gw and 0<=j<gh and 0<=k<gd:
                g=grid[i][j]
                if g!=None and math.sqrt((g[0]-x)**2+(g[1]-y)**2+(g[2]-z)**2)<mindist:
                    return True

        return False

    if startpt!=None:
        addPoint(startpt)
    else:
        addPoint((random.randint(0,width-1),random.randint(0,height-1),random.randint(0,depth-1)))

    if ptscount>1:
        while len(processlist)>0 and len(samplepts)<ptscount:
            pos=random.randint(0,len(processlist)-1)
            pt=processlist.pop(pos)
            for i in range(ptscount):
                nx,ny,nz=generatePtAround(*pt)
                if 0<=nx<=width and 0<=ny<=height and 0<=nz<=depth and not inNeighbourhood(nx,ny,nz):
                    addPoint((nx,ny,nz))
                    if len(samplepts)==ptscount:
                        return samplepts

    return samplepts


def unitWave2RGB(vis_range):
    '''
    Returns the colour value corresponding to the position in the visible spectrum designated by the unit value
    'vis_range'. If vis_range==0.0 then the colour is equivalent to 380nm, if vis_range==1.0 the colour is 780nm.
    '''
    return wave2RGB(380+400*clamp(vis_range,0.0,1.0))


def wave2RGB(wavelength):
    '''Converts a wavelength value between 380nm and 780nm into a RGB color tuple. Requires 380 <= wavelength <= 780.'''
    w = int(wavelength)
    R=0.0
    G=0.0
    B=0.0

    # colour
    if w >= 380 and w < 440:
        R = -(w - 440.) / (440. - 380.)
        B = 1.0
    elif w >= 440 and w < 490:
        G = (w - 440.) / (490. - 440.)
        B = 1.0
    elif w >= 490 and w < 510:
        G = 1.0
        B = -(w - 510.) / (510. - 490.)
    elif w >= 510 and w < 580:
        R = (w - 510.) / (580. - 510.)
        G = 1.0
    elif w >= 580 and w < 645:
        R = 1.0
        G = -(w - 645.) / (645. - 580.)
    elif w >= 645 and w <= 780:
        R = 1.0

    # intensity correction
    if w >= 380 and w < 420:
        SSS = 0.3 + 0.7*(w - 350) / (420 - 350)
    elif w >= 420 and w <= 700:
        SSS = 1.0
    elif w > 700 and w <= 780:
        SSS = 0.3 + 0.7*(780 - w) / (780 - 700)
    else:
        SSS = 0.0

    return (R*SSS,G*SSS,B*SSS)


def matZero(n,m):
    '''Return a list of lists with the given dimensions containing zeros.'''
    return [[0]*m for i in xrange(n)]


def matIdent(n):
    '''Return a list of lists defining the identity matrix of rank `n'.'''
    mat=matZero(n,n)
    for nn in range(n):
        mat[nn][nn]=1.0

    return mat


def assertMatDim(mat,n,m):
    '''Assert that `mat' has dimensions (n,m).'''
    assert len(mat)==n
    assert all(len(row)==m for row in mat)


def arrayV(val,*dims):
    '''Return an array composed of lists containing copies of `val' of dimensions `dims'.'''
    if len(dims)==0:
        return val

    return [arrayV(val,*dims[1:]) for i in xrange(dims[0])]


def transpose(mat):
    '''Return the transpose of list of list `mat'.'''
    n=len(mat)
    m=len(mat[0])

    result=matZero(m,n)

    for i,j in trange(n,m):
        result[j][i]=mat[i][j]

    return result

