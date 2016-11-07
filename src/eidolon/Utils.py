# Eidolon Biomedical Framework
# Copyright (C) 2016 Eric Kerfoot, King's College London, all rights reserved
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


'''These are utility functions and classes defined in pure Python. They do not use libraries like Numpy or the renderer.'''

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
import ConfigParser
import atexit
import contextlib
import ast
import string
import inspect

from codeop import compile_command

from functools import wraps
from threading import Thread, RLock, Event,currentThread,_MainThread


halfpi=math.pi/2.0

epsilon=1.0e-8

logFilename=None

VIZDIRVAR='VIZDIR'
RESDIRVAR='RESDIR'
SHMDIRVAR='SHMDIR'
APPDIR='APPDIR'
LIBSDIR='EidolonLibs'

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
	values by index or by name. Containment is defined as whether the given name is a member of the enum or not.
	The members of the enum are also iterable in the given order, each element being a tuple of the name+values.

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
			kwargs['doc']=vals[0].doc
			kwargs['valtype']=vals[0].valtype
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
		self.obj=obj
		self.event.set()

	def clear(self):
		self.obj=None
		self.event.clear()

	def isSet(self):
		return self.event.isSet()
		
	def isEmpty(self):
		return not self.obj and not self.event.isSet()

	def getObjectWait(self,timeout=10.0):
		res=self.event.wait(timeout)

		if timeout!=None and not res: # if we timed out waiting, return None
			return None

		# if an exception was raised by raised instead of setting a value, raise it
		if isinstance(self.obj,FutureError) and self.obj.exc_value:
			raise self.obj.exc_type,self.obj.exc_value,self.obj.tb
		elif isinstance(self.obj,Exception):
			raise self.obj

		# return the stored value, or if the value is a Future get the stored value from it
		return Future.get(self.obj,timeout) 

	def __call__(self,timeout=10.0):
		return self.getObjectWait(timeout)

	def __enter__(self):
		return self

	def __exit__(self,exc_type, exc_value, tb):
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


ParamType=enum(
	('int','Integer'),
	('real','Real'),
	('bool','Boolean'),
	('vec3','3D Vector'),
	('field','Field Name'),
	('str','String'),
	('strlist','String List'),
#	('choice','Choice Option'),
	('valuefunc','Value Function'),
	('vecfunc','Vector Function'),
	('unitfunc','Unit Function'),
	doc='Types of parameters the ParamDef class can represent.',
	valtype=(str,)
)


class ParamDef(object):
	'''Definition of a parameter for various uses, eg. representation object settings.'''
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
	'''An event broadcast class which invokes callable objects when an EventType event occurs.'''
	def __init__(self):
		self.eventHandlers=dict((i,[]) for i,j in EventType)
		self.handleLock=threading.Lock()
		self.suppressedEvents=set()

	def _triggerEvent(self,name,*args):
		'''Broadcast event to handler callback functions, stopping for any callback that returns True.'''
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
		assert name in EventType
		self.eventHandlers[name].append(cb)

	def removeEventHandler(self,cb):
		for cblist in self.eventHandlers.values():
			if cb in cblist:
				cblist.remove(cb)


def readBasicConfig(filename):
	'''
	Read the config (.ini) file `filename' into a map of name/value pairs. The values must be acceptable inputs to
	ast.literal_eval(), ie. literals. This is for security since eval() on untrusted input can do interesting things.
	'''
	cparser=ConfigParser.RawConfigParser()
	cparser.optionxform=str
	results=cparser.read(filename)

	if len(results)!=1:
		raise IOError,'Cannot parse config file %r' %filename

	sections=list(cparser.sections())+[ConfigParser.DEFAULTSECT]
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
	cparser=ConfigParser.RawConfigParser()
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

			if 'threading' in filename:
				return None

			if logging.getLogger().getEffectiveLevel()==logging.DEBUG:
				logging.debug("%s:%s:%d: %s",threadname,filename, frame.f_lineno,event)
			else:
				printFlush("%s:%s:%d: %s"%(threadname,filename, frame.f_lineno,event))
		except:
			pass # Utils gets nullified at shutdown so suppress that exception

		return trace

	sys.settrace(trace)


def getVizDir():
	'''Returns the application's directory as stored in the VIZDIRVAR environment variable.'''
	return os.path.abspath(os.getenv(VIZDIRVAR,'./'))


def setLogging(logfile='eidolon.log',filemode='a'):
	'''Enables logging to the given file (by default same file as the renderer writes to) with the given filemode.'''

	if os.path.split(logfile)[0].strip()=='': # if the logfile is a relative path, put it in Eidolon directory
		logfile=os.path.join(getVizDir(),logfile)

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


def addLibraryEgg(egg):
	'''Add the nominated egg file to the front of the system path, assuming this is found in ${VIZDIR}/Libs/python.'''
	sys.path.insert(0,os.path.join(getVizDir(),LIBSDIR,'python',ensureExt(egg,'.egg')))


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

		# If the process exited recently, a pid may still exist for the handle. So, check if we can get the exit code.
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
	'''Gets the username in a portable and secure way which works with 'su' and non-terminal processes.'''
	if isWindows:
		import win32api,win32con
		hostuname=win32api.GetUserNameEx(win32con.NameSamCompatible)
		return str(hostuname.split('\\')[-1])
	else:
		import pwd
		return pwd.getpwuid(os.getuid()).pw_name


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
						exec c in localvars # raises execution exceptions

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
	keyword value `timeout' can be given indicating how long to wait for the program in seconds before killing
	it, otherwise the routine will wait forever.
	'''
	timeout=kwargs.get('timeout',None) # timeout time value in seconds
	cwd=kwargs.get('cwd',None)
	exefile=os.path.abspath(exefile)

	if isWindows:
		exefile=ensureExt(exefile,'.exe')

	if kwargs.pop('logcmd',False):
		printFlush(exefile,exeargs,kwargs)

	if not os.path.isfile(exefile):
		raise IOError,'Cannot find program %r' %exefile

	proc=subprocess.Popen([exefile]+list(exeargs),stderr = subprocess.STDOUT, stdout = subprocess.PIPE,cwd=cwd)
	output=''
	errcode=0

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

	(out,err) = proc.communicate()
	returncode= errcode if errcode!=0 and proc.returncode==0 else proc.returncode

	return (returncode,output+out)


def enumAllFiles(rootdir):
	'''Yields all absolute path regular files in the given directory.'''
	for root, dirs, files in os.walk(rootdir):
		for f in sorted(files):
			yield os.path.join(root,f)


def checkValidPath(path):
	pdir,basename,ext=splitPathExt(path)
	invalidchars='\\/:*?<>|"\0'

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
	'''Returns True if the files `src' and `dst' refer to the same file that exists.'''
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
			raise IOError,'File already exists: %r'%dst
			
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
		raise IOError,'Cannot move %r to %r, source file does not exist'%(oldpath,newpath)
	elif os.path.exists(newpath) and not overwriteFile:
		raise IOError,'Cannot move %r to %r, destination file already exists'%(oldpath,newpath)
	elif isSameFile(oldpath,newpath):
		raise IOError,'File names %r and %r refer to the same file'%(oldpath,newpath)
	elif moveFile:
		shutil.move(oldpath,newpath)

	return newpath


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


@contextlib.contextmanager
def timingBlock(name,printEntry=True):
	'''
	Provides a timing facility for 'with' code blocks. Argument `name' is printed when entering if `printEntry', and
	always printed when exiting. The returned value is the starting time of the block.
	'''
	if printEntry:
		printFlush('>',name)
	start=time.time()
	yield start  # execute code in 'with' block
	end=time.time()
	printFlush('<',name,'dT (s) =',(end-start))


cumulativeTimes={}

def printCumulativeTimes():
	global cumulativeTimes
	printFlush('Total Global dT (s):')
	for i in cumulativeTimes.items():
		printFlush(' %s = %f'% i)


def cumulativeTime(func):
	@wraps(func)
	def timingwrap(*args,**kwargs):
		start=time.time()
		res=func(*args,**kwargs)
		end=time.time()

		global cumulativeTimes
		if len(cumulativeTimes)==0:
			atexit.register(printCumulativeTimes)

		cumulativeTimes[func.__name__]=(end-start)+cumulativeTimes.get(func.__name__,0.0)
		return res

	return timingwrap


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
	

def traverseObj(obj,func,visited=[]):
	result=func(obj)
	visited=[obj]+visited

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
#	try:
#		return iter(obj) is not None
#	except:
#		return False
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
		memo=dict(initialmemo)

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


# This global map of objects to locks is used by 'lockobj' to store unique locks for every requested object
globalObjLocks={}
globalLocksLock=RLock() # a lock for the above object map


def _removeObjLock(obj):
	with globalLocksLock:
		globalObjLocks.pop(obj)


def lockobj(obj):
	'''
	Returns a lock object which is be globally unique per input object. This lock can be used to synchronize access
	to any arbitrary object. It uses weak references to ensure previously locked objects can be collected.
	This function is thread-safe.
	'''
	with globalLocksLock:
		lock=first(globalObjLocks[w] for w in globalObjLocks if id(w())==id(obj))

		if not lock:
			w=weakref.ref(obj,_removeObjLock)
			lock=RLock()
			globalObjLocks[w]=lock

		return lock


def locking(func):
	'''
	This is a locking method decorator which uses 'lockobj' to synchronize access to the current object. This ensures
	that calls to decorated methods are restricted to one thread at a time, which doesn't necessarily ensure exclusive
	access to the all of the receiving object's members. A calling thread having a lock to the receiver already through
	'lockobj' will be able to call decorated methods as well.
	'''
	@wraps(func)
	def funcwrap(self,*args,**kwargs):
		with lockobj(self):
			return func(self,*args,**kwargs)

	return funcwrap


def trylocking(func):
	'''
	Same as 'locking' except it only attempts to acquire the lock without blocking, and does nothing if the acquire fails.
	'''
	@wraps(func)
	def funcwrap(self,*args,**kwargs):
		lock=lockobj(self)
		if lock.acquire(False):
			try:
				return func(self,*args,**kwargs)
			finally:
				lock.release()

	return funcwrap


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


def delayedcall(delay):
	'''
	Wrapper for defining a delayed call function. When the function is called, up to `delay' seconds elapses before
	the call actually occurs. Subsequent calls to the function before this time elapses resets the counter but will
	not induce multiple calls. The most recent arguments passed to the wrapped function are the ones used when the
	call does occur; there is never a return value.
	'''
	def funcwrap(func):
		@wraps(func)
		def delayCall(*args,**kwargs):
			DelayThread.callGlobalTarget(delay,func,args,kwargs)

		return delayCall

	return funcwrap


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


class Task(object):
	'''
	This class represents the abstract notion of a task, with a 'curprogress' value to indicate progress in relation to
	a 'maxprogress' value. Tasks may have their own threads or be executed by their containers. Normally tasks are
	executed by the SceneManager object.
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
		self.result=self.func(*self.args,**self.kwargs)

	def start(self,useThread=False):
		self.setLabel(self.label)
		self.started=True
		if useThread:
			self.thread=Thread(target=self._callFunc,name=self.label)
			self.thread.start()
		else:
			self._callFunc()
		self.completed=True

	def isDone(self):
		return self.started and (not self.thread.isAlive() if self.thread else self.completed)

	def setLabel(self,label):
		if self.parentTask:
			self.parentTask.setLabel(label)
		else:
			self.label=label
			if self.thread:
				self.thread.label=label

	def getLabel(self):
		if self.parentTask:
			return self.parentTask.getLabel()
		else:
			return self.label

	def setProgress(self,curprogress):
		if self.parentTask:
			self.parentTask.setProgress(curprogress)
		else:
			self.curprogress=curprogress

	def setMaxProgress(self,maxprogress):
		if self.parentTask:
			self.parentTask.setMaxProgress(maxprogress)
		else:
			self.maxprogress=maxprogress
			self.curprogress=min(self.curprogress,self.maxprogress)

	def getProgress(self):
		'''Returns the current progress value and maximum value, or (0,0) if unknown.'''
		if self.parentTask:
			return self.parentTask.getProgress()
		else:
			return self.curprogress,self.maxprogress

	def __repr__(self):
		return 'Task<%s>' %self.label


def taskroutine(taskLabel=None,selfName='task'):
	'''
	Routine decorator which produces a wrapper function returning a task that will execute the original function when
	processedby the task queue. The first argument indicates the name of the variable used to pass the Task instance
	to the function call or is None if no passing is wanted. If the task argument is present it must be the last and
	when the function is called no value for it must be provided, thus it must have a default value (usually None).
	The optional second argument defines whether the task is a threaded one or not (default is False).
	'''
	def funcwrap(func):
		@wraps(func)
		def taskroutinefunc(*args,**kwargs):
			return Task(taskLabel if taskLabel else func.__name__,func=func,args=args,kwargs=kwargs,selfName=selfName)

		return taskroutinefunc

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
	Derive a string from `name' guaranteed to not be in `namelist', which will be `name' if it wasn't originally in list.
	The created name will otherwise be `name' followed by `spacer' and a number.
	'''
	count=1
	newname=name

	while newname in namelist:
		newname=name+spacer+str(count)
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
		raise IndexError,"`sortIndex' value %i is outside possible range [%i,%i]"%(sortIndex,-minlen,minlen-1)

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
	return first(i for i,s in enumerate(sets) if len(s)>1)# or min(map(len,strs))

#	minlen=min(map(len,strs))
#	def identChars(i):
#		return all(strs[0][i]==s[i] for s in strs[1:])
#
#	index=first(i for i in xrange(minlen) if not identChars(i))
#	return index if index!=None else minlen


def globulateStrList(striter,threshold=3):
	'''
	Converts a list of strings into a dict mapping regex-like patterns to strings in `striter' having at least `threshold'
	commonality with one another. The key value is the longest prefix all the strings have in common followed by *.
	If a string has no commonality of at least `threshold' with any other string, it is mapped to itself. If multiple
	identical strings are found, they are mapped to themselves with * appended in the key.

	Eg: globulateStrList(['fooggle','foogg','fottt','bazzol','bazzle','thunk','fool'])
	results in
	   {'thunk': ['thunk'], 'bazz*': ['bazzol', 'bazzle'], 'fo*': ['fooggle', 'foogg', 'fottt', 'fool']}.
	'''
	results={}
	initlist=list(striter)
	strlist=sorted(striter,key=lambda i:-len(i))

	for unique in set(strlist):
		found=[i for i in strlist if i==unique]
		if len(found)>1:
			results[unique]=found
			strlist=[i for i in strlist if i!=unique]

	matchlist=[(i,max(getStrCommonality(i,j)[0] for j in strlist if i!=j)) for i in strlist]

	while len(matchlist)>0:
		str1,maxmatch=matchlist.pop(0)
		nextmatch=first(i for _,i in matchlist if i!=maxmatch)

		matchvals=[]#[i for i,_ in matchlist if getStrCommonality(i,str1)[0]>nextmatch]
		maxcommon=0
		for i,_ in matchlist:
			common= getStrCommonality(i,str1)[0]
			if common>nextmatch:
				matchvals.append(i)
				maxcommon=max(maxcommon,common)

		if matchvals:
			results[str1[:maxcommon]]=[str1]+matchvals
			matchlist=[(i,j) for i,j in matchlist if i not in matchvals]
		else:
			results[str1]=[str1]

	resultlist=sorted(results.items()) # sort results by name, so shorter names first
	results={}

	# keep names that are a prefix for other names and add these other names's values to the prefix value list
	while resultlist:
		name,vals=resultlist.pop(0)
		suffixes=filter(lambda i:i[0].startswith(name),resultlist)
		if suffixes: # found names that start with the current name
			resultlist=filter(lambda i:i not in suffixes,resultlist)
			vals+=listSum(zip(*suffixes)[1])

		if len(set(vals))>1:
			name+='*'

		results[name]=sorted(vals,key=initlist.index)

	return results


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
		raise ValueError,'Step must be positive and non-zero (step=%s)' % (str(step),)

	if stop<0 or start<0:
		raise ValueError,'All arguments must be positive (start=%s, stop=%s)' % (str(start),str(stop))

	if stop<start:
		raise ValueError,'Stop value must be greater than start value (start=%s, stop=%s)' % (str(start),str(stop))

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
	return [[0]*m for i in xrange(n)]


def matIdent(n):
	mat=matZero(n,n)
	for nn in range(n):
		mat[nn][nn]=1.0

	return mat


def assertMatDim(mat,n,m):
	assert len(mat)==n
	assert all(len(row)==m for row in mat)


def arrayV(val,*dims):
	if len(dims)==0:
		return val

	return [arrayV(val,*dims[1:]) for i in xrange(dims[0])]


def vandermonde(vals,n):
	return [[v**(n-j-1) for j in xrange(n)] for v in vals]


def transpose(mat):
	n=len(mat)
	m=len(mat[0])

	result=matZero(m,n)

	for i,j in trange(n,m):
		result[j][i]=mat[i][j]

	return result


def mat2Det(a,b,c,d):
	return a*d-b*c


def mat3Det(a,b,c,d,e,f,g,h,i):
	return a*(e*i-f*h)+b*(f*g-i*d)+c*(d*h-e*g)


def mat4Det(a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p):
	return (l * o * b * e - k * p * b * e - l * n * c * e + j * p * c * e + k * n * d * e - j * o * d * e
		- a * l * o * f + a * k * p * f + l * m * c * f - k * m * d * f + a * l * n * g - a * j * p * g
		- l * m * b * g + j * m * d * g - a * k * n * h + a * j * o * h + k * m * b * h - j * m * c * h
		- p * c * f * i + o * d * f * i + p * b * g * i - n * d * g * i - o * b * h * i + n * c * h * i)


def mat2Inv(a,b,c,d):
	det=mat2Det(a,b,c,d)
	return ((d/det,-b/det),(-c/det,a/det))


def mat3Inv(a,b,c,d,e,f,g,h,i):
	det=mat3Det(a,b,c,d,e,f,g,h,i)
	A=e*i-f*h
	B=f*g-d*i
	C=d*h-e*g
	D=c*h-b*i
	E=a*i-c*g
	F=g*b-a*h
	G=b*f-c*e
	H=c*d-a*f
	I=a*e-b*d

	return ((A/det,D/det,G/det),(B/det,E/det,H/det),(C/det,F/det,I/det))


def mat4Inv(a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p):
	s0 = a * f - e * b
	s1 = a * g - e * c
	s2 = a * h - e * d
	s3 = b * g - f * c
	s4 = b * h - f * d
	s5 = c * h - g * d

	c5 = k * p - o * l
	c4 = j * p - n * l
	c3 = j * o - n * k
	c2 = i * p - m * l
	c1 = i * o - m * k
	c0 = i * n - m * j

	invdet = 1.0 / (s0 * c5 - s1 * c4 + s2 * c3 + s3 * c2 - s4 * c1 + s5 * c0)

	b00 = ( f * c5 - g * c4 + h * c3) * invdet
	b01 = (-b * c5 + c * c4 - d * c3) * invdet
	b02 = ( n * s5 - o * s4 + p * s3) * invdet
	b03 = (-j * s5 + k * s4 - l * s3) * invdet

	b10 = (-e * c5 + g * c2 - h * c1) * invdet
	b11 = ( a * c5 - c * c2 + d * c1) * invdet
	b12 = (-m * s5 + o * s2 - p * s1) * invdet
	b13 = ( i * s5 - k * s2 + l * s1) * invdet

	b20 = ( e * c4 - f * c2 + h * c0) * invdet
	b21 = (-a * c4 + b * c2 - d * c0) * invdet
	b22 = ( m * s4 - n * s2 + p * s0) * invdet
	b23 = (-i * s4 + j * s2 - l * s0) * invdet

	b30 = (-e * c3 + f * c1 - g * c0) * invdet
	b31 = ( a * c3 - b * c1 + c * c0) * invdet
	b32 = (-m * s3 + n * s1 - o * s0) * invdet
	b33 = ( i * s3 - j * s1 + k * s0) * invdet

	return ((b00,b01,b02,b03),(b10,b11,b12,b13),(b20,b21,b22,b23),(b30,b31,b32,b33))


def matDet(mat):
	n=len(mat)
	assert all(len(m)==n for m in mat)

	if n in (2,3,4):
		if n==2:
			det=mat2Det
		elif n==3:
			det=mat3Det
		else:
			det=mat4Det

		return det(*(mat[i][j] for i,j in itertools.product(range(n),repeat=2)))
	else:
		sign=1
		result=0
		for j in range(n):
			result+=sign*mat[0][j]*matDet(matCrossOut(mat,0,j))
			sign*=-1

		return result


def matCrossOut(mat,i,j):
	'''Returns matrix 'mat' with row 'i' and column 'j' crossed out.'''
	rows=[]
	for n in range(len(mat)):
		if n!=i:
			rows.append([mat[n][m] for m in xrange(len(mat)) if m!=j])

	return rows


def matCoFactors(mat):
	n=len(mat)
	cofactors=matZero(n,n)

	for i,j in trange(n,n):
		cofactors[i][j]=matDet(matCrossOut(mat,i,j))
		if (i+j)%2==1:
			cofactors[i][j]*=-1

	return cofactors


def matInv(mat):
	n=len(mat)
	assert all(len(m)==n for m in mat)

	if n in (2,3,4):
		if n==2:
			inv=mat2Inv
		elif n==3:
			inv=mat3Inv
		else:
			inv=mat4Inv

		return inv(*(mat[i][j] for i,j in itertools.product(range(n),repeat=2)))
	else:
		detinv=1.0/matDet(mat)
		comat=matCoFactors(mat)
		inv=matZero(n,n)

		for i,j in trange(n,n):
			inv[i][j]=comat[j][i]*detinv

	return inv


