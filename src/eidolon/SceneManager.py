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


'''
The SceneManager object is the focus of operations with Eidolon. It is used to control the scene, create new
objects, and handle user interaction. It wraps the RenderTypes.RenderScene object derived from Eidolon widget.
Plugins objectsare also defined which implement basic behaviour for scene objects, and for materials. These are extended
by plugin libraries to include new functionality into Eidolon.
'''

from SceneComponents import *
from ScenePlugin import *
from Camera2DView import *

import gc
import tempfile
import atexit
import shutil

globalMgr=None
globalPlugins=[]


ConfVars=enum(
	'shaders', 'resdir', 'shmdir', 'appdir', 'userappdir','logfile', 'preloadscripts', 'uistyle', 'stylesheet',
	'winsize', 'camerazlock', 'maxprocs', 'configfile', 'rtt_preferred_mode', 'vsync', 'rendersystem',
	desc='Variables in the Config object, these should be present and keyed to platformID group'
)


def createSceneMgr(win,conf=None):
	'''Create the global scene manager (if not already created) and return it.'''
	global globalMgr

	if globalMgr==None:
		globalMgr=SceneManager(win,conf)

		for i,plug in enumerate(globalPlugins):
			plug.init(i,win,globalMgr)

		atexit.register(cleanupPlugins)

	if win:
		win.updateGeometry()

	return globalMgr


def getSceneMgr():
	'''Returns the global scene manager.'''
	return globalMgr


def addPlugin(plug):
	'''
	Add a plugin to the plugins list, which will be loaded (by calling its init()) method when the global scene
	manager is creates. If a plugin of the same type as `plug' is already added, `plug' will not be added. Returns
	`plug' if added, or the plugin with the same type as `plug' if not.
	'''
	for p in globalPlugins:
		if type(p)==type(plug):
			return p

	globalPlugins.append(plug)
	return plug


def cleanupPlugins():
	'''Call cleanup() on all listed plugins.'''
	for p in globalPlugins:
		p.cleanup()


class Project(object):
	'''
	This is the base class for all projects in the syste. A project is a directory with a script file specifying how to
	load the project, a config file containing project metadata or whatever else, a log directory containing previous
	versions of these amongst other logs, and all of the data files needed by the project. This object is meant to act
	as the bridge between the UI and a plugin containing project-specific functionality, so the a lot of the code in a
	project is about driving the UI in its properties box (which it can add to through getPropBox()) and some file IO.
	The project's lifecycle is summarized here:
		1. Instantiated in SceneManager.createProjectObj()
		2. Project.create() is called
		3. Project.loadConfig() is called
		4. User interacts with the project
		5. Removed from the system by SceneManager.deleteProjectObj()
		6. Project.remove() is called

	'''
	def __init__(self,name,parentdir,mgr):
		self.name=name
		self.parentdir=os.path.abspath(parentdir)
		self.mgr=mgr
		self.memberObjs={} # maps objects part of this project to their variable names used to generate scripts
		self.configMap={'name':name}
		self.varcounter=1
		self.checkboxMap={} # maps QTableWidgetItem to scene object names
		self.prop=None
		self.header='\nif mgr.project==None:\n  mgr.createProjectObj(%r,%r,Project)\n' %(self.name,self.parentdir)
		self.backDir=self.getProjectFile('')

		assert os.path.isdir(self.parentdir)

	def addHandlers(self):
		'''Call this in the constructor to add event handlers to capture relevant events.'''
		self.mgr.addEventHandler(EventType._objectRenamed,self.renameObject)
		self.mgr.addEventHandler(EventType._objectRemoved,self.removeObject)
		self.mgr.addEventHandler(EventType._objectAdded,self.checkIncludeObject)

	def create(self):
		'''Creates the project directory and other init tasks if necessary.'''
		pdir=self.getProjectDir()
		if not os.path.exists(pdir):
			os.mkdir(pdir)
			self.save()

	def remove(self):
		'''Removes handlers and does other cleanup functions.'''
		self.mgr.removeEventHandler(self.renameObject)
		self.mgr.removeEventHandler(self.removeObject)
		self.mgr.removeEventHandler(self.checkIncludeObject)

	def getLabel(self):
		return '%s %s'%(type(self).__name__,self.name)

	def getProjectDir(self):
		'''Get the project's directory.'''
		return os.path.join(self.parentdir,self.name)

	def getProjectFile(self,filename):
		'''Get an absolute path to a file with name `filename' in the project's directory. This file need not exist.'''
		return os.path.join(self.parentdir,self.name,filename)

	def getScriptPath(self):
		'''Get the absolute path to the project's script file.'''
		return self.getProjectFile(self.name+'.py')

	def getConfigPath(self):
		'''Get the absolute path to the project's config file.'''
		return self.getProjectFile(self.name+'.ini')

	def getVarName(self,obj):
		'''Get the variable name associated with project member `obj' or None if `obj' is part of the project.'''
		return self.memberObjs.get(obj,None)

	def getProjectObj(self,name):
		'''Get the project object with the given name, or None if none has that name.'''
		return first(o for o in self.memberObjs if o.getName()==name)
		
	def hasFile(self,path):
		'''Returns True if `path' refers to a file/directory within the project's directory.'''
		return os.path.abspath(path).startswith(self.getProjectDir())

	def addObject(self,obj):
		'''Add an object to the project if not already there, if `obj' is a SceneObjectRepr its parent is also added.'''
		if isinstance(obj,SceneObjectRepr):
			self.addObject(obj.parent)

		if obj not in self.memberObjs:
			self.memberObjs[obj]='obj%i'%self.varcounter
			self.varcounter+=1

	def removeObject(self,obj):
		'''Remove an object from the project, if `obj' is a SceneObject its representations are first removed.'''
		if isinstance(obj,SceneObject):
			for r in obj.reprs:
				self.removeObject(r)
				
			files=obj.plugin.getObjFiles(obj)
			if files and self.mgr.win and obj in self.memberObjs and all(self.hasFile(f) for f in files):
				prompt='\n '.join(['Delete the following files?']+files)
				self.mgr.win.chooseYesNoDialog(prompt,'Confirm File Delete',lambda:map(os.remove,files))
				
		if obj in self.memberObjs:
			self.memberObjs.pop(obj)
			
	def hasObject(self,obj):
		return obj in self.memberObjs

	def renameObject(self,obj,oldname):
		'''Called when `obj' has been renamed from `oldname', giving the project the chance to rename files.'''
		pass

	def checkIncludeObject(self,obj):
		'''
		Called whenever a SceneObject or SceneObjectRepr `obj' is added to the scene. This allows a project to include
		the object into itself and do all the file copying needed, usually after the user is prompted to do so or not.
		'''
		pass

	def save(self):
		'''Save the project's script and config file.'''
		self.mgr.showStatusBarMsg('Saving Project '+self.name)

		projdir=self.getProjectDir()
		scriptpath=self.getScriptPath()

		timeBackupFile(scriptpath,self.backDir)

		with open(scriptpath,'w+') as ofile:
			writer=ScriptWriter(ofile)
			writer.namemap=dict(self.memberObjs)
			writer.includedObjs=[o for o in self.mgr.objs if o in self.memberObjs] # preserve object order
			writer.scriptHeader+=self.header
			writer.scriptdir=projdir+os.path.sep

			writer.writeScene(self.mgr)

			for n in self.memberObjs.values():
				writer.writeLine('mgr.project.addObject(%s)'%n)

		self.saveConfig()

	def loadConfig(self,filename=None):
		'''Load the config file (or `filename' if given) and update `self.configMap' with its contents.'''
		try:
			conf=readBasicConfig(filename or self.getConfigPath())
			self.configMap.update(conf)
		except Exception as e:
			self.mgr.showExcept(e)

	def saveConfig(self):
		'''Saves the config file from the values in `self.configMap'.'''
		filename=self.getConfigPath()
		timeBackupFile(filename,self.backDir)

		if len(self.configMap)>0:
			storeBasicConfig(filename,self.configMap)

	def getPropBox(self):
		assert isMainThread()
		if self.prop==None:
			self.prop=ProjectPropertyWidget()
			self.prop.saveButton.clicked.connect(self._saveButton)
			self.prop.dirButton.clicked.connect(self._dirButton)
			self.prop.selTable.itemClicked.connect(self._setApplyToObjCheck)

			setCollapsibleGroupbox(self.prop.selObjBox,True)
		return self.prop

	def _saveButton(self):
		self.name=str(self.prop.nameEdit.text())
		self.parentdir=os.path.abspath(str(self.prop.dirEdit.text()))
		self.create()
		self.save()

	def _dirButton(self):
		newdir=self.mgr.win.chooseDirDialog('Choose Project Root Directory')
		self.parentdir=os.path.abspath(newdir)
		self.prop.dirEdit.setText(self.parentdir)

	def _setApplyToObjCheck(self,item):
		if item in self.checkboxMap:
			obj=self.mgr.findObject(self.checkboxMap[item])
			if obj:
				if item.checkState()==QtCore.Qt.Checked:
					self.addObject(obj)
				else:
					self.removeObject(obj)

	def updatePropBox(self,proj,prop):
		prop.nameEdit.setText(self.name)
		prop.dirEdit.setText(self.parentdir)

		table=prop.selTable

		objs=list(self.mgr.enumSceneObjects())+list(self.mgr.enumSceneObjectReprs()) #listSum([o]+list(o.reprs) for o in self.mgr.enumSceneObjects())

		for i in xrange(table.rowCount()):
			item=table.item(i,0)
			if item in self.checkboxMap:
				self.checkboxMap.pop(item)

		table.clearContents()
		table.setRowCount(len(objs))

		setTableHeaders(table)

		for i,o in enumerate(objs):
			chkBoxItem = QtGui.QTableWidgetItem()
			chkBoxItem.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
			chkBoxItem.setCheckState(QtCore.Qt.Checked if o in self.memberObjs else QtCore.Qt.Unchecked)

			self.checkboxMap[chkBoxItem]=o.getName()

			label=QtGui.QTableWidgetItem(o.name)
			label.setFlags((label.flags() & ~Qt.ItemIsEditable)|Qt.ItemIsSelectable)

			table.setItem(i,0,chkBoxItem)
			table.setItem(i,1,label)

		table.resizeColumnsToContents()
		table.resizeRowsToContents()


class SceneManager(object):
	'''
	The manager object for scene objects, assets, and UI. It represents the link between the UI and the scene itself,
	containing the code to change the scene as directed by interaction with the UI, ie. part of the controller part of 
	MVC. Most of the functionality for performing operatiosn and calculating data is defined in plugins and controller
	objects instead which	include both UI and algorithm code. The purpose of the SceneManager is to be the central 
	point of interaction with the system without becoming a god object by including too much functionality. It also
	manages the task thread and the playing of time-dependent data.
	'''
	
	def __init__(self,win,conf):
		self.win=win
		self.conf=conf
		self.viz=None
		self.scene=None

		self.evtHandler=EventHandler()

		self.project=None # project object, only non-None when there's an existing project

		# camera controller
		self.controller=None # the camera controller
		self.singleController=None # same as self.controller if used, None if a multi-camera controller is used
		self.multiController=None # same as self.controller if used, None if a single-camera controller is used

		# scene assets and objects
		self.cameras=[] # list of Camera objects, cameras[0] is "main" 3D perspective camera
		self.objs=[] # members of the scene, instances of SceneObject
		self.specs=[] # Existing spectrums
		self.mats=[] # Existing materials
		self.textures=[] # Existing textures
		self.lights=[] # existing light objects
		self.programs=[] # existing Vertex/Fragment shader GPU programs

		self.ambientColor=color()
		self.backgroundColor=color()

		# secondary scene elements
		self.bbmap={} # maps representations to their bounding boxes
		self.handlemap={} # maps representations to their handles (Repr -> list<Handle>), only populated when handles are first requested

		# task related components
		self.tasklist=[] # list of queued Task objects
		self.finishedtasks=[] # list of completed Task objects
		self.tasklock=threading.RLock() # lock used for controlling access to task lists
		self.currentTask=None # the current running task, None if there is none
		self.taskthread=threading.Thread(target=self._processTasks) # thread in which tasks are executed, None if no tasks are being run
		self.taskthread.daemon=True

		# scene component controllers
		self.matcontrol=MaterialController(self,self.win) # the material controller responsible for all materials
		self.lightcontrol=LightController(self,self.win) # the light controller responsible for light UI
		self.progcontrol=GPUProgramController(self,self.win) # the shader GPU program controller responsible for the UI

		# time stepping components
		self.timestep=0
		self.timestepMin=0
		self.timestepMax=0
		self.timestepSpan=0
		#self.maxTimestep=0
		self.timeFPS=25
		self.timeStepsPerSec=1.0
		self.playerEvent=threading.Event()
		self.player=threading.Thread(target=self._playerThread)
		self.player.daemon=True
		self.player.start()
		
		def exception_hook(exctype, value, tb):
			msg='\n'.join(traceback.format_exception(exctype, value, tb))
			self.showExcept(msg,str(value),'Unhandled Exception')
		sys.excepthook = exception_hook

		self.meshplugin=MeshScenePlugin('MeshPlugin')
		self.imageplugin=ImageScenePlugin('ImgPlugin')

		global globalPlugins
		globalPlugins=[self.meshplugin,self.imageplugin]+globalPlugins

		# script local variables
		self.scriptlocals={'mgr':self} # local environment object scripts are executed with
		for p in globalPlugins: # add plugin variables to the script variable map
			self.scriptlocals[p.name.replace(' ','_')]=p

		if self.conf.hasValue('var','names'): # add command line variables to the script variable map
			names=self.conf.get('var','names').split('|')
			for n in names:
				self.scriptlocals[n]=self.conf.get('var',n)

		if self.win: # window setup
			self.win.mgr=self
			self.scene=self.win.scene
			self.viz=self.win.viz

			self.viz.evtHandler=self.evtHandler

			if self.win.console:
				self.win.console.updateLocals(self.scriptlocals)
				self.win.consoleWidget.setVisible(conf.hasValue('args','c'))

			self.callThreadSafe(self._windowConnect)
			
		#set config values
		if self.conf.get(platformID,'renderhighquality').lower()=='true':
			self.setAlwaysHighQual(True)

		self.addEventHandler(EventType._mouseMove,lambda e:self.repaint(False))
		self.addEventHandler(EventType._mouseWheel,lambda e:self.repaint(False))

		self.addEventHandler(EventType._widgetPreDraw,self._updateUI)
		self.addEventHandler(EventType._widgetPreDraw,self._updateManagedObjects)
		self.addEventHandler(EventType._widgetPostDraw,self._repaintHighQual)
		self.addEventHandler(EventType._mousePress,self._mousePressHandleCheck)
		self.addEventHandler(EventType._mouseMove,self._mouseMoveHandleCheck)
		self.addEventHandler(EventType._mouseRelease,self._mouseReleaseHandleCheck)

		self.taskthread.start() # start taskthread here

	def _windowConnect(self):
		'''Initializes all the UI control code, mostly connecting slots with action functions.'''

		self.win.addMenuItem('Create','Cam2DView','&2D View',lambda i:self.create2DView('2D View'))

		self.win.actionOpen_Project.triggered.connect(self._openProjectButton)
		self.win.action_Default_Project.triggered.connect(self._newProjectButton)
		self.win.actionSave_Project.triggered.connect(self._saveProjectButton)

		self.win.action_Open_Script.triggered.connect(self._openScriptButton)
		self.win.action_Save_Script.triggered.connect(self._saveScriptButton)
		self.win.actionTake_Screenshot.triggered.connect(self._saveScreenshotAction)
		self.win.action_Quit.triggered.connect(self.quit)

		self.win.actionShow_Log_Window.triggered.connect(lambda:self.win.showLogfileView(self.conf.get(platformID,'logfile')))
		self.win.actionShow_Scene_Code.triggered.connect(lambda:self.showTextBox('Current Scene Code:','Scene Code',self.getSceneCode(),700,800))

		self.win.actionEnable_Tracing.triggered.connect(setTrace)
		self.win.actionEnable_Logging.triggered.connect(self._saveLogFile)
		self.win.actionGC_Collect.triggered.connect(self._collect)

		self.win.removeObjectButton.clicked.connect(self._removeObjectButton)
		self.win.renameButton.clicked.connect(self._renameObjectButton)
		self.win.clearButton.clicked.connect(self._clearSceneButton)

		self.win.chooseAmbient.clicked.connect(lambda:self.win.chooseRGBColorDialog(self.ambientColor,self.setAmbientLight))
		self.win.chooseBackground.clicked.connect(lambda:self.win.chooseRGBColorDialog(self.backgroundColor,self.setBackgroundColor))

		self.win.seeAllButton.clicked.connect(self.setCameraSeeAll)
		self.win.highqualCheck.toggled.connect(self.setAlwaysHighQual)

		self.win.fovBox.editingFinished.connect(lambda:self.setCameraConfig(fov=self.win.fovBox.value()*math.pi))
		self.win.nearClipBox.editingFinished.connect(lambda:self.setCameraConfig(nearclip=self.win.nearClipBox.value()))
		self.win.farClipBox.editingFinished.connect(lambda:self.setCameraConfig(farclip=self.win.farClipBox.value()))

		self.win.newSpecButton.clicked.connect(self._newSpectrumButton)
		self.win.newMatButton.clicked.connect(self._newMaterialButton)
		self.win.newLightButton.clicked.connect(self._newLightButton)
		self.win.loadTextureButton.clicked.connect(self._loadTextureButton)
		self.win.loadShaderButton.clicked.connect(self._loadGPUScriptButton)

		self.win.cloneButton.clicked.connect(self._cloneAssetButton)
		self.win.removeAssetButton.clicked.connect(self._removeAssetButton)

		self.win.wireframeCheck.toggled.connect(self.setCameraWire)
		self.win.orthoCheck.toggled.connect(self.setCameraOrtho)
		self.win.zLockCheck.toggled.connect(self.setCameraZLocked)
		self.win.camResetButton.clicked.connect(self.resetCamera)

		self.win.timestepSlider.valueChanged.connect(lambda i:self.setTimestep(float(i)/self.win.timestepSliderMult))
		self.win.timestepBox.editingFinished.connect(lambda:self.setTimestep(self.win.timestepBox.value()))

		self.win.fpsBox.editingFinished.connect(lambda:self.setTimeFPS(self.win.fpsBox.value()))
		self.win.stepspersecBox.editingFinished.connect(lambda:self.setTimeStepsPerSec(self.win.stepspersecBox.value()))
		
		self.win.forwardButton.clicked.connect(self.play)
		self.win.stopButton.clicked.connect(self.stop)
		self.win.incTimeButton.clicked.connect(self.incTimestep)
		self.win.decTimeButton.clicked.connect(self.decTimestep)

		fillList(self.win.axestypeBox,[a[1] for a in AxesType])
		fillList(self.win.centertypeBox,[a[1] for a in CenterType])

		self.win.axestypeBox.currentIndexChanged.connect(lambda i:self.setAxesType(AxesType[i][0]))
		self.win.centertypeBox.currentIndexChanged.connect(lambda i:self.setCenterType(CenterType[i][0]))

		# replace the key press event handler method of the object tree widget so they can be captured and acted on
		oldKeyPressEvent=self.win.treeWidget.keyPressEvent
		def keyPressEvent(e):
			if e.key() in (Qt.Key_Delete,Qt.Key_Backspace):
				obj=self.win.getSelectedObject()
				if isinstance(obj,SceneObject):
					self.removeSceneObject(obj)
				elif isinstance(obj,SceneObjectRepr):
					self.removeSceneObjectRepr(obj)
			elif e.key() == Qt.Key_F2:
				self._renameObjectButton()
			else:
				oldKeyPressEvent(e)

		setattr(self.win.treeWidget,'keyPressEvent',keyPressEvent)

	def _updateUI(self):
		if self.controller:
			fillTable(self.controller.getPropTuples(),self.win.cameraProps)
			self.setCameraConfig()

	def _updateManagedObjects(self):
		'''Executed before each redraw, this is used to set scene objects/figures that are managed by this object.'''

		for sm in self.lights:
			if sm.lighttype in (LightType._cpoint,LightType._cdir,LightType._cspot):
				self.controller.setCameraLight(sm)

		for rep,(fig,matname) in self.bbmap.items(): # transform bound boxes
			aabb=rep.getAABB(True)
			fig.setPosition(aabb.center)
			fig.setScale(aabb.maxv-aabb.minv)

		for rep,handles in self.handlemap.items(): # transform handles
			for h in handles:
				if rep.isVisible():
					pos=rep.getPosition(True)
					h.setPosition(pos)
					h.setScale(vec3(pos.distTo(self.cameras[0].getPosition())*0.05)) # view distance kludge, should instead use overlayed ortho camera?
					h.setRotation(*rep.getRotation(True))
				else:
					h.setVisible(False)

	def _mousePressHandleCheck(self,e):
		'''
		Checks if a mouse click is on a handle, if so send the event to the handle and return true so no other
		events are processed. This assumes this function is the first event handler for clicks.
		'''
		x=e.x()
		y=e.y()

		cam=first(c for c in self.cameras if c.isPointInViewport(x,y) and not c.isSecondaryCamera())

		if cam!=None:
			ray=cam.getProjectedRay(x,y)
			campos=cam.getPosition()

			handles=[]
			for r,h in self.handlemap.items():
				rpos=r.getPosition()
				handles+=[(rpos.distTo(campos),hh) for hh in h]

			handles.sort(key=lambda i:i[0])

			for d,h in handles:
				if h.checkSelected(ray):
					h.mousePress(cam,e)
					return True # prevent other handlers from being triggered

		return False

	def _mouseMoveHandleCheck(self,e):
		'''
		Checks if a handle has been clicked on, sending it the event and returning true if so. This assumes this
		function is the first event handler for moves.
		'''
		handle=first(h for h in listSum(self.handlemap.values()) if h.isSelected())

		if handle!=None:
			handle.mouseMove(e)
			return True

		return False

	def _mouseReleaseHandleCheck(self,e):
		for h in listSum(self.handlemap.values()):
			h.mouseRelease(e)

	def _processTasks(self):
		'''
		Takes tasks from the queue and runs them. This is executed in a separate daemon thread and should not be called.
		'''
		assert threading.currentThread().daemon, 'Task thread must be a daemon'

		if self.conf.hasValue('args','t'):
			setTrace()

		if self.win: # wait for the window to appear
			while not self.win.isExec:
				time.sleep(0.01)

		def updateStatus():
			'''Status update action, this runs as a thread and continually updates the status bar.'''
			if self.conf.hasValue('args','t'):
				setTrace()

			while True:
				try:
					time.sleep(0.1)
					with self.tasklock:
						task=self.currentTask

					self.setTaskStatus(task or 'Ready')
				except: # ignores exceptions which are usually related to shutdown when UI objects get cleaned up before this thread stops
					pass

		updatethread=threading.Thread(target=updateStatus)
		updatethread.start() # also a daemon

		while True:
			try:
				# remove the first task, using tasklock to prevent interference while doing so
				with self.tasklock:
					if len(self.tasklist)>0:
						self.currentTask=self.tasklist.pop(0)
	
				# attempt to run the task by calling its start() method, on exception report and clear the queue
				try:
					if self.currentTask:
						self.currentTask.start()
						self.finishedtasks.append(self.currentTask)
					else:
						time.sleep(0.1)
				except FutureError as fe:
					exc=fe.exc_value
					while exc!=fe and isinstance(exc,FutureError):
						exc=exc.exc_value
						
					self.showExcept(fe,exc,'Exception from queued task '+self.currentTask.getLabel())
					self.currentTask.flushQueue=True # remove all waiting tasks; they may rely on 'task' completing correctly and deadlock
				except Exception as e:
					if self.currentTask: # if no current task then some non-task exception we don't care about has occurred
						self.showExcept(e,'Exception from queued task '+self.currentTask.getLabel())
						self.currentTask.flushQueue=True # remove all waiting tasks; they may rely on 'task' completing correctly and deadlock
				finally:
					# set the current task to None, using tasklock to prevent inconsistency with updatethread
					with self.tasklock:
						# clear the queue if there's a task and it wants to remove all current tasks
						if self.currentTask!=None and self.currentTask.flushQueue:
							self.tasklist=[]
	
						self.currentTask=None
			except:
				pass # ignore errors during shutdown 

	def getCurrentTask(self):
		'''Returns the current Task object if called within the task execution thread, None otherwise.'''
		return self.currentTask if threading.currentThread()==self.taskthread else None

	def addTasks(self,*tasks):
		'''Adds the given tasks to the task queue whether called in another task or not.'''
		assert all(isinstance(t,Task) for t in tasks)
		with self.tasklock:
			self.tasklist+=list(tasks)

	def addFuncTask(self,func,name=None):
		'''Creates a task object (named 'name' or the function name if None) to call the function when executed.'''
		self.addTasks(Task(name or func.__name__,func))

	def runTasks(self,tasks,resFuture=None,isSequential=False):
		'''
		Executes the given list of tasks if `isSequential' or if the call was made in the task execution thread. When
		all the tasks have been executed, the Future object 'resFuture' is queried for its value, which is returned.
		If neither condition is true the tasks are added to the task queue instead and `resFuture' is returned. The
		argument `resFuture' is expected to be a Future object which the tasks will provide an object for, or None.
		'''
		parentTask=self.getCurrentTask()

		tasks=toIterable(tasks)

		if isSequential or parentTask!=None: # run the tasks right here in this thread rather than putting them in the queue
			for t in tasks:
				t.parentTask=parentTask
				t.start()

			return Future.get(resFuture)
		else: # put the tasks in the queue and return the future object
			self.addTasks(*tasks)
			return resFuture

	def execScriptsTask(self,*scripts):
		'''
		Enqueues a task which will execute the given script files in sequence when run. If a directory is present in
		`scripts' containing a .py file of the same, the file is assumed to be a project script and is run instead.
		'''
		@taskroutine('Executing Scripts')
		def execScripts(scripts,task):
			for filename in scripts:
				updateLocals=True
				tryHard=False
				
				if os.path.isdir(filename): # if a directory, append to it the script file of the same name
					filename=os.path.join(filename,os.path.basename(os.path.abspath(filename))+'.py')
					updateLocals=False
					tryHard=True

				if os.path.isfile(filename):
					self.execScript(filename,updateLocals,tryHard)
				else:
					self.logError("Error: Cannot find script file '%s'"%str(filename))

		scripts=[s for s in scripts if len(s.strip())>0]
		if len(scripts)>0:
			self.addTasks(execScripts(scripts))
			
	def loadFilesTask(self,*files):
		'''
		Loads the given data files, script files, or directories. Each file in `files' is loaded in the order given.
		If the file is a Python script, this is executed. If a project directory (ie. a directory containing a Python
		script with the same name) the contained script file is executed. For any other file, the first plugin whose
		acceptFile() method returns true is tasked to load the file through its loadObject() method.
		'''
		@taskroutine('Loading Files')
		def _loadFiles(files,task):
			for filename in files:
				updateLocals=True
				tryHard=False
				
				if os.path.isdir(filename): # if a directory, append to it the script file of the same name (ie. load project)
					scriptfilename=os.path.join(filename,os.path.basename(os.path.abspath(filename))+'.py')
					if os.path.isfile(scriptfilename):
						filename=scriptfilename
						updateLocals=False # don't update locals with project's loading variables, these make a mess
						tryHard=True # ignore exceptions when exec'ing, this allows a project with missing data to load as much as possible

				if filename.endswith('.py'):
					if os.path.isfile(filename):
						self.execScript(filename,updateLocals,tryHard)
					else:
						self.logError("Error: Cannot find script file %r"%filename)
				else:
					p=first(p for p in globalPlugins if p.acceptFile(filename))
					if p:
						for o in toIterable(p.loadObject(filename)):
							self.addSceneObject(o)
					else:
						self.logError("Error: No plugin accepted file/directory %r"%filename)

		files=[f for f in files if len(f.strip())>0]
		if len(files)>0:
			self.addTasks(_loadFiles(files))

	def execBatchProgramTask(self,exefile,*exeargs,**kwargs):
		'''
		Executes the program `exefile' with the string arguments `exeargs'. This is done in a task so the result
		is a Future object which will contain a (returncode,output) pair if the program is run successfully, or an
		exception otherwise. The integer return code is taken from the program, in the usual case 0 indicating a
		correct execution and any other value indicating failure, and the output is a string of the merged stdout
		and stderr text. If the program requires input it will deadlock, this is a batch operation routine only. A
		keyword value `timeout' can be given indicating how long to wait for the program in seconds before killing
		it, otherwise the task will wait forever.
		'''
		logfile=kwargs.get('logfile',None) # log file path
		filename=os.path.split(exefile)[1]
		f=Future()

		@taskroutine('Executing program '+filename)
		def _exeTask(exefile,exeargs,logfile,kwargs,task):
			with f:
				rt,output=execBatchProgram(exefile,*exeargs,**kwargs)

				if logfile:
					timeBackupFile(logfile)
					with open(logfile,'w') as o:
						o.write(output)

				f.setObject((rt,output))

		return self.runTasks([_exeTask(exefile,exeargs,logfile,kwargs)],f,False)

	def listTasks(self):
		'''Returns a list of the labels of all queued tasks.'''
		with self.tasklock:
			return [t.getLabel() for t in self.tasklist]

	def setTaskStatus(self,msgOrTask,progress=0,progressmax=0):
		'''Sets the task status bar of the window if present, otherwise does nothing.'''
		if self.win:
			if isinstance(msgOrTask,str):
				self.win.setStatus(msgOrTask,progress,progressmax)
			else:
				stat='%s | %i tasks waiting' % (msgOrTask.getLabel(),len(self.tasklist))
				self.win.setStatus(stat,*msgOrTask.getProgress())

	def getPlugin(self,name):
		'''Returns the named plugin if found, None otherwise.'''
		return first(p for p in globalPlugins if p.name==name)

	def getPluginNames(self):
		'''Returns the names of loaded plugins.'''
		return [p.name for p in globalPlugins]

	def createProjectObj(self,name, rootdir,projconst):
		'''
		Creates a new Project object, saving the old one if it existed. The new project object is created by calling
		`projconst' with `name', `rootdir', and self as the arguments. This callable is expected to be a constructor
		that returns a Project type.
		'''
		if self.project!=None:
			self.project.save()
			self.deleteProjectObj()

		self.project=projconst(name,rootdir,self)
		self.project.create()
		self.project.loadConfig()

		if self.win:
			prop=self.callThreadSafe(self.project.getPropBox)
			self.win.addProjectObj(self.project,self.project.getLabel(),prop,self.project.updatePropBox)
			self.win.selectObject(self.project)

	def deleteProjectObj(self):
		if self.project!=None:
			self.project.remove()
			if self.win:
				self.win.removeObject(self.project)

		self.project=None

	@timing
	def execScript(self,filename,updateLocals=True,tryHard=False):
		'''Executes the given script file using internal environment, updates local/console variables if `updateLocals'.'''
		if not os.path.isfile(filename):
			raise IOError, "Cannot execute %r; not a file" % filename

		if not isTextFile(filename):
			raise IOError,'Cannot execute %r, not a text file'%filename

		self.scriptlocals['scriptdir']=os.path.split(os.path.abspath(filename))[0]+os.path.sep
		self.scriptlocals['task']=self.getCurrentTask()

		scriptlocals=self.scriptlocals
		if not updateLocals: # if we're not updating local variables, copy `scriptlocals' so the stored version isn't changed
			scriptlocals=dict(scriptlocals)

		if tryHard:
			excs=execfileExc(filename,scriptlocals)
			for e,format_exc in excs:
				self.showExcept(e,'Exception in script file %r'%filename,format_exc=format_exc)
		else:
			execfile(filename,scriptlocals,None)

		if self.win and updateLocals:
			self.win.console.updateLocals(self.scriptlocals)
			
	def getUserAppDir(self):
		'''Returns the per-user application directory as defined by ConfVars.userappdir in the config object.'''
		appdir= self.conf.get(platformID,ConfVars.userappdir)
		assert os.path.isdir(appdir)
		return appdir
		
	def getUserAppFile(self,filename):
		return os.path.join(self.getAppDir(),filename)
		
	def getUserTempDir(self,dirname):
		tempdir=tempfile.mkdtemp(prefix=dirname+'_',dir=self.getAppDir())
		atexit.register(shutil.rmtree,tempdir)
		return tempdir

	def quit(self):
		'''Quit the program after all tasks have completed. Ensures thread-safety with the UI thread.'''
		if self.win:
			self.addFuncTask(lambda: self.callThreadSafe(self.win.close)) # close() must be called in UI thread
		else:
			self.addFuncTask(sys.exit)

	def callThreadSafe(self,func,*args,**kwargs):
		'''
		Forces 'func' to be called by the main/UI thread, which is necessary for many graphics operations. The values
		'args' and 'kwargs' are used as the arguments, and the return value of the function is returned when the
		main thread has completed the call. If there is no window then the function is called directly in this thread.
		'''
		if self.win and not isMainThread():
			return self.win.callFuncUIThread(func,*args,**kwargs)
		else:
			return func(*args,**kwargs)

	def proxyThreadSafe(self,func):
		'''Returns a proxy function which calls `func' in the main thread when invoked. This method can be a decorator.'''
		return lambda *args,**kwargs : self.callThreadSafe(func,*args,**kwargs)
		
	def checkFutureResult(self,future):
		'''Checks the resulting value stored in Future `future', showing an exception if there is one.'''
		@self.addFuncTask
		def _check():
			try:
				Future.get(future)
			except FutureError as fe:
				exc=fe.exc_value
				while exc!=fe and isinstance(exc,FutureError):
					exc=exc.exc_value
					
				self.showExcept(fe,exc,'Exception from Future')

	def logMsg(self,*msgs,**kwargs):
		'''
		Writes a log entry composed of the string representations of the members of 'msgs' as well as to stdout.
		If 'nl' is present in 'kwargs' and is False, no newline appears at the end of the stdout write.
		'''
		printFlush(*msgs,**kwargs)

	def logError(self,*msgs,**kwargs):
		'''
		Writes a log entry composed of the string representations of the members of 'msgs' as well as to stderr.
		If 'nl' is present in 'kwargs' and is False, no newline appears at the end of the stderr write.
		'''
		kwargs['stream']=sys.stderr
		printFlush(*msgs,**kwargs)

	def showExcept(self,ex,msg='',title='Exception Caught',format_exc=None):
		'''Shows the given exception and writes information to the log file.'''
		format_exc=format_exc or traceback.format_exc()
		msg=str(msg or ex)

		if format_exc=='None\n':
			format_exc=str(ex)
			logmsg='%s\n%s'%(msg,format_exc)
		else:
			logmsg='%s\n%s\n%s'%(msg,str(ex),format_exc)

		self.logError(title+':',logmsg.strip())
		self.showMsg(msg,title,format_exc,False)

	def showMsg(self,msg,title='Message',text=None,doLog=True,width=600,height=300):
		'''Shows the given message in a message window if the UI is present, as writes it to the log file.'''
		if doLog:
			self.logMsg(title+':',msg,text)

		if self.win:
			self.win.showMsg(msg,title,text,width,height)

	def showTextBox(self,msg,title,text,width=600,height=300):
		if self.win:
			self.win.showTextBox(msg,title,text,width,height)

	def showStatusBarMsg(self,msg,timeout=1000):
		timeout=max(1000,timeout)
		if self.win:
			self.callThreadSafe(self.win.statusBar.showMessage,msg,timeout)
		else:
			self.logMsg(msg)

	def showTimeDialog(self,doShow=None,timestepMin=None,timestepMax=None,timestepSpan=None):
		'''
		Set the time dialog visibility and settings. If 'doShow' is None then a check is made to see if there are
		time-dependent representations. If 'doShow' is a boolean value, then visibility is set to that value. This
		also sets the `timestepMin' and `timestepMax' member.
		'''
		allreprs=filter(lambda r:len(r.getTimestepList())>1, self.enumSceneObjectReprs())
		doShow=doShow if doShow!=None else len(allreprs)>0

		if timestepMin!=None or timestepMax!=None or timestepSpan!=None:
			self.timestepMin,self.timestepMax,self.timestepSpan=timestepMin,timestepMax,timestepSpan
		elif len(allreprs)>0:
			self.timestepMin,self.timestepMax=minmax((r.getTimestepRange() for r in allreprs),ranges=True)
			self.timestepSpan=avg(avgspan(r.getTimestepList()) for r in allreprs)
			if any(isinstance(r,ImageSceneObjectRepr) for r in allreprs):
				self.setTimeStepsPerSec(500) # image data present, play at half real-time speed
			else:
				self.setTimeStepsPerSec(avg(r.getTimestepInterval() for r in allreprs))
		else:
			self.timestepMin,self.timestepMax,self.timestepSpan=0,0,0

		if self.win:
			self.win.showTimeDialog(doShow,self.timestepMin,self.timestepMax,self.timestepSpan)

	def isTimeDialogShown(self):
		return self.win and self.win.timeWidget.isVisible()

	def create2DView(self,name=None,constr=Camera2DView):
		return self.createDockWidget(lambda:constr(self,self.createCamera(name,True)),name or 'Cam2D%i'%len(self.cameras))

	def createDockWidget(self,constr,title,w=200,h=200):
		if self.win:
			widg=self.callThreadSafe(constr)
			self.win.createDock(title,widg,w,h)
			return widg

	def setTimestep(self,ts):
		'''Set the timestep `ts' for every representation clamped within the range [self.timestepMin,self.timestepMax].'''
		#assert ts>=0

		ts=clamp(ts,self.timestepMin,self.timestepMax)
		self.timestep=ts

		if self.win:
			self.win.setTimeDisplay(ts)

		# set the timestep for every visble representation, must be thread-safe since this affects the internals of interpolating figures
		for r in self.enumSceneObjectReprs():
			if len(r.getTimestepList())>1:
				self.callThreadSafe(r.setTimestep,ts)

		self.repaint()

	def incTimestep(self):
		newts=self.timestep+self.timestepSpan
		self.setTimestep(self.timestepMin if newts>self.timestepMax else newts)
		
	def decTimestep(self):
		newts=self.timestep-self.timestepSpan
		if newts<self.timestepMin:
			newts+=self.timestepMax-self.timestepMin
			
		self.setTimestep(newts)

	def setTimeFPS(self,fps):
		if fps>0:
			self.timeFPS=int(fps)
			if self.win:
				self.win.setTimeFPS(self.timeFPS)

	def setTimeStepsPerSec(self,sps):
		if sps>0:
			self.timeStepsPerSec=sps
			if self.win:
				self.win.setTimeStepsPerSec(self.timeStepsPerSec)

	def play(self):
		'''Play timestepping animation, do nothing if the steps/s is too large or frames/s is too small.'''
		if self.timestepMax>0 and ((self.timeStepsPerSec/self.timeFPS)/(self.timestepMax-self.timestepMin))<1.0:
			self.playerEvent.set()

	def stop(self):
		'''Stop animation.'''
		self.playerEvent.clear()

	def _playerThread(self):
		'''Thread implementing timestep animation, this must be executed in a daemon thread.'''
		assert threading.currentThread().daemon

		lasttime=time.time()
		while True:
			try:
				self.playerEvent.wait()
				timediff=time.time()-lasttime
				timeinterval=1.0/self.timeFPS
				timestepinc=self.timeStepsPerSec*timeinterval

				# sleep until the correct time interval has elapsed to maintain the stated FPS rate
				if timediff<timeinterval:
					time.sleep(timeinterval-timediff)

				newts=self.timestep+timestepinc

				# if the end of the animation has been reached, loop back to the beginning
				if newts>self.timestepMax:
					newts-=self.timestepMax-self.timestepMin

				self.setTimestep(newts)
				lasttime=time.time()

			except AttributeError as a: # for errors when trying to call methods of objects being cleaned up at exit
				self.showExcept(a,'<<Player Thread>>')
				self.stop()
			except ZeroDivisionError: # happens when deleting representations while playing
				self.stop()
			except Exception as e:
				self.showExcept(e,'<<Player Thread>>')
				self.stop()

	def addEventHandler(self,name,cb):
		self.evtHandler.addEventHandler(name,cb)

	def removeEventHandler(self,cb):
		self.evtHandler.removeEventHandler(cb)

	def _triggerEvent(self,name,*args):
		self.callThreadSafe(self.evtHandler._triggerEvent,name,*args)

	def createCamera(self,name=None,isSecondary=False):
		name=name or 'camera'
		if isSecondary:
			cam=self.scene.createCamera(name,0,0,0,0)
			cam.setSecondaryCamera(True)
		else:
			cam=self.scene.createCamera(name)

		self.cameras.append(cam)
		return cam

	def removeCamera(self,camera):
		self.cameras.remove(camera)

	def setSingleFreeCamera(self):
		'''
		Creates main camera if none exist, creates a AxesCameraController object which is assed to self.controller and
		self.singleController, and is then returned. This object is used to control the main camera as the single view.
		'''
		if self.cameras==[]:
			self.cameras.append(self.scene.createCamera("main")) # camera 0 is the main camera that is never deleted

		if not self.singleController:
			self.singleController=AxesCameraController(self.cameras[0],100)

		self.setCameraController(self.singleController)

		return self.singleController

	def setCameraController(self,controller):
		'''Sets the current camera controller to the given one, setting up cameras as needed must be done elsewhere.'''
		if self.controller:
			self.controller.stop(self)

		self.controller=controller
		self.controller.start(self)

	def setCameraOrtho(self,ortho):
		self.controller.setOrtho(ortho)
		if self.win:
			setChecked(ortho,self.win.orthoCheck)
		self.repaint()

	def setCameraWire(self,wire):
		self.controller.setWireframe(wire)
		if self.win:
			setChecked(wire,self.win.wireframeCheck)
		self.repaint()

	def setCameraZLocked(self,zlock):
		self.controller.setZLocked(zlock)
		if self.win:
			setChecked(zlock,self.win.zLockCheck)
		self.repaint()

	def setCameraConfig(self,fov=None,nearclip=None,farclip=None):
		c=self.controller
		if c!=None:
			if fov!=None:
				c.setVertFOV(fov)
			if nearclip!=None:
				c.setNearClip(nearclip)
			if farclip!=None:
				c.setFarClip(farclip)

			if fov!=None or nearclip!=None or farclip!=None:
				self.repaint()

			if self.win:
				self.win.setCameraValues(c.getVertFOV()/math.pi,c.getNearClip(),c.getFarClip())

	def setCameraSeeAll(self):
		'''Tells the current controller to reposition itself to see every visible object in the scene.'''
		if self.objs and self.controller:
			self.controller.setSeeAllBoundBox(self.getSceneAABB())
			self.repaint()

	def resetCamera(self):
		'''Resets the camera's rotational values but does not move its look-at position.'''
		self.controller.reset()
		self.repaint()

	def setAmbientLight(self,col):
		'''Sets the scene's ambient light value.'''
		col=color(*col)
		self.scene.setAmbientLight(col)
		self.ambientColor=col
		if self.win:
			self.win.callFuncUIThread(setColorButton,col,self.win.chooseAmbient)

		self.repaint()

	def setBackgroundColor(self,col):
		'''Sets the scene's background color value by calling setBGColor() on all primary cameras.'''
		col=color(*col)
		for c in self.cameras:
			if not c.isSecondaryCamera():
				c.setBGColor(col)

		self.callThreadSafe(self.scene.setBGObject,col,True)
		self.backgroundColor=col

		if self.win:
			self.win.callFuncUIThread(setColorButton,col,self.win.chooseBackground)

		self.repaint()

	def setAxesType(self,axestype):
		'''Sets the axes type and handles finalizing the necessary figures.'''
		assert axestype in AxesType

		if not hasattr(self.controller,'setAxesType'):
			return

		axesfigs=self.callThreadSafe(self.controller.setAxesType,self.scene,axestype)

		for f in axesfigs:
			f.setVisible(True)

		if self.win:
			selectBoxIndex(AxesType[axestype],self.win.axestypeBox)

		self.controller._setCamera()
		self.repaint()

	def setCenterType(self,centertype):
		'''Sets the center indicator type and handles finalizing the necessary figures.'''
		assert centertype in CenterType

		if not hasattr(self.controller,'setCenterType'):
			return

		centerFigs=self.callThreadSafe(self.controller.setCenterType,self.scene,centertype)

		for f in centerFigs:
			f.setVisible(True)

		if self.win:
			selectBoxIndex(CenterType[centertype],self.win.centertypeBox)

		self.controller._setCamera()
		self.repaint()

	def saveScreenshot(self,filename,camera_or_widget=None,width=0,height=0,stereoOffset=0):
		filename=filename.strip()
		camera_or_widget=camera_or_widget or self.cameras[0]

		if not filename or not camera_or_widget or not self.viz or not self.scene:
			return

		def takeshot():
			self.repaint(True)
			if isinstance(camera_or_widget,Camera):
				self.scene.saveScreenshot(filename,camera_or_widget,width,height,stereoOffset)
			else:
				screenshotWidget(camera_or_widget,filename)

		self.callThreadSafe(takeshot)

	def saveTimestepScreenshots(self,fileprefix,stepvalue=1.0,start=0.0,end=None,camera_or_widget=None,width=0,height=0,extension='.png'):
		if end==None:
			end=self.timestepMax+stepvalue

		for i,ts in enumerate(frange(start,end,stepvalue)):
			self.setTimestep(ts)
			self.saveScreenshot('%s%04d%s'%(fileprefix,i,extension),camera_or_widget,width,height)

	def getSceneCode(self):
		'''Returns the code representation of the current scene as can be constructed by plugins.'''
		writer=ScriptWriter()
		try:
			writer.writeScene(self)
		except Exception as e:
			self.showExcept(e)
		finally:
			return writer.target.getvalue()

	@locking
	def repaint(self,renderHighQual=True):
		'''Forces the scene to redraw. if `renderHighQual' is true a high quality render is done.'''

		self.scene.setRenderHighQuality(renderHighQual)

		if self.win:
			self.win.repaintScene()
			self.win.updateScrollAreas()
		else:
			self._updateManagedObjects()

	@delayedcall(0.25)
	def _repaintHighQual(self):
		self.repaint(True)

	def setAlwaysHighQual(self,val):
		self.scene.setAlwaysHighQuality(val)
		if self.win:
			setChecked(val,self.win.highqualCheck)

	def _collect(self):
		count=5
		collect=self.proxyThreadSafe(gc.collect)
		while collect() and count:
			count-=1

	def addSceneObject(self,obj,category=None):
		'''
		Adds the SceneObject instance to the scene. If `obj' has no plugin, the appropriate default is assigned. If
		the name of `obj' is not unique, it will be changed to a unique name by suffixing a number. 
		'''
		obj=Future.get(obj)
		assert isinstance(obj,SceneObject),'%r is type %r'%(obj,type(obj))
		assert obj not in self.objs

		obj.setName(self.getUniqueObjName(obj.getName()))

		self.objs.append(obj)

		# if this object has no plugin, give it the default one appropriate for its type
		if not obj.plugin:
			if isinstance(obj,MeshSceneObject):
				obj.plugin=self.meshplugin
			elif isinstance(obj,ImageSceneObject):
				obj.plugin=self.imageplugin
			else:
				obj.plugin=ScenePlugin('Default Plugin')

			obj.plugin.init(-1,self.win,self)

		prop,updateFunc=obj.plugin.addSceneObject(obj)

		if self.win and prop:
			icon=obj.plugin.getIcon(obj)
			menu,menuFunc=obj.plugin.getMenu(obj)
			self.win.addTreeObject(obj,obj.getLabel(),None,prop,updateFunc,None,menu,menuFunc,icon,category)
			self.win.updateScrollAreas()

		self._triggerEvent(EventType._objectAdded,obj)

	def addSceneObjectTask(self,obj,category=None):
		'''Adds a task to the task queue which adds `obj' to the scene.'''
		@taskroutine('Adding Scene Object')
		def _add(obj,category,task):
			self.addSceneObject(obj,category)

		return self.runTasks(_add(obj,category))

	@timing
	def addSceneObjectRepr(self,rep):
		'''Adds the SceneObjectRepr instance to the scene.'''
		rep=Future.get(rep)
		assert isinstance(rep,SceneObjectRepr),'%r is type %r'%(rep,type(rep))
		assert rep.parent in self.objs

		rep.setName(uniqueStr(rep.getName(),[r.getName() for r in self.enumSceneObjectReprs() if r!=rep],' '))

		self.callThreadSafe(rep.addToScene,self.scene)

		prop,updateFunc,dblClickFunc=rep.plugin.addSceneObjectRepr(rep)

		if self.win and prop:
			menu,menuFunc=rep.plugin.getMenu(rep)
			self.win.addTreeObject(rep,rep.getLabel(),rep.parent,prop,updateFunc,dblClickFunc,menu,menuFunc)
			self.win.setVisibilityIcon(rep,rep.isVisible())

		self.showTimeDialog()
		self._triggerEvent(EventType._objectAdded,rep)
		return self.updateSceneObjectRepr(rep)

	def enumSceneObjects(self):
		'''Yields each SceneObject added to the scene.'''
		for o in self.objs:
			yield o

	def enumSceneObjectReprs(self):
		'''Yields each SceneObjectRepr present in the scene.'''
		for o in self.objs:
			for r in o.reprs:
				yield r

	def enumAllObjects(self):
		'''Yields a SceneObject followed by each of its representations, then the same for every subsequent SceneObject.'''
		for o in self.objs:
			yield o
			for r in o.reprs:
				yield r

	def findObject(self,name_or_fn):
		'''Finds an object with the given name or which matches the given selector function.'''
		if not name_or_fn:
			return None

		if isinstance(name_or_fn,str):
			fn=lambda o:o.getName()==name_or_fn
		else:
			fn=name_or_fn

		return first(o for o in self.enumAllObjects() if fn(o))

	def getUniqueObjName(self,name,spacer='_'):
		return uniqueStr(name,[o.getName() for o in self.enumAllObjects()],spacer)

	def getSceneAABB(self):
		'''Returns the AABB containing all visible repr objects.'''
		return BoundBox.union(r.getAABB(True) for r in self.enumSceneObjectReprs() if r.isVisible())

	@timing
	def updateSceneObjectRepr(self,rep):
		'''
		Causes the SceneObjectRepr object to update its data through prepareBuffers() and update(). Updating occurs
		in a task which first calls rep.prepareBuffers() in its thread which expects `rep' to setup all data which is
		to be loaded into figures, then rep.update() is called in the main thread which is when `rep' is expected to
		create figures and load them with data. Once this is done the UI refreshes itself, the scene redraws, and the
		objectUpdated event is sent.
		'''
		f=Future()
		@taskroutine('Update Representation')
		def updateTask(task):
			with f:
				rep.prepareBuffers() # prepare data in a way that doesn't require operations in the main thread

				self.callThreadSafe(rep.update,self.scene) # update object in the main thread

				self.repaint()
				self._collect()
				self._triggerEvent(EventType._objectUpdated,rep)
				if self.win:
					self.win.relayoutViz()

				f.setObject(rep)

		return self.runTasks(updateTask(),f)

	def renameSceneObject(self,obj,newname):
		oldname=obj.getName()
		if not newname or oldname==newname:
			return oldname

		try:
			newname1=self.getUniqueObjName(newname)
			obj.setName(newname1)
			self._triggerEvent(EventType._objectRenamed,obj,oldname)

			if self.win:
				self.win.updateTreeObjects()

			return newname1
		except Exception as e:
			if self.win:
				self.showExcept(e,title='Cannot Rename Object')
			obj.setName(oldname)
			return oldname

	def showBoundBox(self,rep,doShow=True,matname='BoundBoxes'):
		'''
		Controls the drawing of bound boxes of representations. Given the representation object 'rep', a box using
		the given material is show if 'doShow' is true, if 'doShow' is false an existing boundbox is hidden or
		nothing is done if one wasn't already visible. This method is thread-safe
		'''
		if doShow and rep not in self.bbmap:
			@self.callThreadSafe
			def _createfigure():
				aabbnodes,indices=generateLineBox([vec3(-0.5),vec3(0.5)])
				vb=PyVertexBuffer(aabbnodes,[vec3(0,0,1)]*len(aabbnodes),[color()]*len(aabbnodes),None)
				ib=PyIndexBuffer(indices)

				fig=self.scene.createFigure(rep.getName()+' BoundBox',matname,FT_LINELIST)
				fig.fillData(vb,ib)
				self.bbmap[rep]=(fig,matname)

		if rep in self.bbmap:
			self.bbmap[rep][0].setVisible(doShow)

		self.repaint()

	def isBoundBoxShown(self,rep):
		'''Returns true if the bound box for 'rep' is visible.'''
		return rep in self.bbmap and self.bbmap[rep][0].isVisible()

	def showHandle(self,rep,doShow=True):
		'''
		Show or hide the control handle(s) for the representation `rep'. There may be just the one transform handle
		or multiple point handles (or other custom types) so this routine will show or hide all at once. This method
		is thread-safe.
		'''
		if rep not in self.handlemap:
			handles=rep.createHandles()

			for h in handles:
				self.callThreadSafe(h.addToScene,self,self.scene)

			self.handlemap[rep]=handles

		for h in self.handlemap[rep]:
			h.setVisible(doShow)

		self.repaint()

	def isHandleShown(self,rep):
		return rep in self.handlemap and self.handlemap[rep][0].isVisible()

	def setReprProps(self,rep,**props):
		'''
		Sets various properties of `rep' in a thread-safe way. If `parent' is present, set `rep' to have this object
		as its parent. If `trans' is present, set `rep' to have this transform. The purpose of this method is to
		provide a convenient thread-safe way of setting these properties, specifically in auto-generated scripts.
		'''
		def _setprops(rep,props):
			if 'parent' in props:
				rep.setParent(props['parent'])
			if 'trans' in props:
				rep.setTransform(props['trans'])

		self.callThreadSafe(_setprops,rep,props)

	def removeSceneObject(self,obj):
		'''Removes the SceneObject instance an its representations from the scene.'''
		for r in list(obj.reprs):
			self.removeSceneObjectRepr(r)

		self.objs.remove(obj)

		if self.win:
			self.win.removeObject(obj)
			self.win.selectObject(None)

		self._triggerEvent(EventType._objectRemoved,obj)
		obj=None
		self._collect()

	def removeSceneObjectRepr(self,rep):
		'''Removes the SceneObjectRepr instance from the scene.'''
		assert rep.parent in self.objs
		rep.parent.removeRepr(rep)

		if self.win:
			self.win.removeObject(rep)
			self.win.selectObject(rep.parent)

		if rep in self.bbmap:
			self.callThreadSafe(self.bbmap.pop,rep)

		if rep in self.handlemap:
			handles=self.handlemap.pop(rep)
			for h in handles:
				self.callThreadSafe(h.removeFromScene,self,self.scene)

		self.callThreadSafe(rep.removeFromScene,self.scene)

		self._triggerEvent(EventType._objectRemoved,rep)
		
		self.showTimeDialog()
		self.repaint()
		self._collect()
		
	def clearScene(self):
		'''Removes all any Project and all SceneObject objects from the scene.'''
		
		self.deleteProjectObj()
		
		for o in list(self.objs):
			self.removeSceneObject(o)
			
		self._collect()

	def loadTextureFile(self,filename):
		'''Loads the given texture file and adds it to the asset list in the UI.'''
		filename=os.path.abspath(filename)
		texture=self.getTexture(filename,True)

		if not texture:
			name=uniqueStr(os.path.split(filename)[1],self.listTextureNames())
			texture=self.callThreadSafe(self.scene.loadTextureFile,name,filename)
			self.textures.append(texture)
			if self.win:
				self.win.addTexture(texture)

		return texture

	def createTexture(self,name,width,height,depth,format):
		name=uniqueStr(name,self.listTextureNames())
		texture=self.scene.createTexture(name,width,height,depth,format)
		self.textures.append(texture)
		if self.win:
			self.win.addTexture(texture)

		return texture

	def getTexture(self,name,isFilename=False):
		'''
		Returns the first texture found with the given name, or filename if 'isFilename' is true. If no texture
		is found, returns None.
		'''
		if isFilename:
			name=os.path.abspath(name)
			return first(t for t in self.textures if t.getFilename()==name)
		else:
			return first(t for t in self.textures if t.getName()==name)

	def listTextureNames(self):
		'''Returns a list of all texture names.'''
		return [t.getName() for t in self.textures]

	def removeTexture(self,texture):
		'''Removes the given texture object from the scene and UI.'''
		self.textures.remove(texture)
		if self.win:
			self.win.removeObject(texture)

	def createLight(self,lighttype,name=None,position=vec3(),direction=vec3(1,0,0)):
		assert lighttype in LightType

		if name==None:
			name='Light'

		name=uniqueStr(name,[l.name for l in self.lights])
		sl=SceneLight(self.scene.createLight(),lighttype,name,position,direction)

		self.lights.append(sl)
		self.callThreadSafe(self.lightcontrol.addLight,sl)
		self.repaint()

		return sl

	def removeLight(self,light):
		assert light in self.lights
		self.lights.remove(light)

		self.lightcontrol.removeLight(light)

		if self.win:
			self.win.removeObject(light)

		light.setVisible(False) # light still exists but removed from scene

		self.repaint()

	def getLight(self,name):
		return first(l for l in self.lights if l.getName()==name)

	def loadGPUScriptFile(self,filename,progtype,name=None,profiles=None,lang=None,entry=None, ignoreError=False):
		try:
			assert os.path.isfile(filename)
			with open(filename) as o:
				src=o.read()

			names=os.path.splitext(os.path.split(filename)[1])
			if lang==None and names[1][1:].lower() in ('cg','hlsl','glsl'):
				lang=names[1][1:].lower()

			if name==None:
				name=names[0]

			return self.createGPUProgram(name,progtype,src,profiles,lang,entry)
		except Exception:
			if not ignoreError:
				raise

	def createGPUProgram(self,name,progtype,src=None,profiles=None,lang=None,entry=None):
		assert progtype in (PT_VERTEX,PT_FRAGMENT), 'Only vertex or fragment shaders are supported.'
		name=uniqueStr(name,self.listGPUProgramNames())

		def createProgram():
			prog=self.scene.createGPUProgram(name,progtype,lang)
			self.programs.append(prog)

			if profiles!=None:
				prog.setProfiles(profiles)

			if src!=None:
				prog.setSourceCode(src)

			if entry!=None:
				prog.setEntryPoint(entry)

			self.progcontrol.addProgram(prog)
			return prog

		return self.callThreadSafe(createProgram)

	def listGPUProgramNames(self, progtype=None):
		return [s.getName() for s in self.programs if progtype==None or s.getType()==progtype]

	def getGPUProgram(self,name):
		return first(s for s in self.programs if s.getName()==name)

	def createMaterial(self,matname):
		'''Creates a new material with the given name, which will be made unique amongst material names.'''

		matname=uniqueStr(matname,self.listMaterialNames())
		mat=self.matcontrol.createMaterial(self.scene.createMaterial(matname))
		self.mats.append(mat)
		self.callThreadSafe(self.matcontrol.addMaterial,mat)
		return mat

	def getMaterial(self,matname):
		'''Returns the material object with the given, or None if not found.'''
		return first(m for m in self.mats if m.getName()==matname)

	def listMaterialNames(self):
		'''Returns a list of all material names.'''
		return [m.getName() for m in self.mats]

	def removeMaterial(self,mat):
		'''Removes the material object from the scene and UI.'''
		if mat.getName()=='Default': # never allow removing the default material
			return

		self.mats.remove(mat)
		if self.win:
			self.win.removeObject(mat)

		self.matcontrol.removeMaterial(mat)

		self.repaint()

	def applyMaterial(self,mat):
		'''Applies the given material to any representation that uses it by invoking applyMaterial() on each.'''
		for rep in self.enumSceneObjectReprs():
			if rep.getMaterialName()==mat.getName():
				rep.applyMaterial(mat)

		self.repaint()

	def cloneMaterial(self,mat,name=None):
		'''
		Creates a new material with all the properties of the given material 'mat'. The new material's name is 'name'
		or a generated one if 'name' is None. The argument 'mat' may be a material object or a material's name.
		'''
		if isinstance(mat,str):
			mat=self.getMaterial(mat)

		assert mat!=None

		name=uniqueStr(name if name!=None else mat.getName(), self.listMaterialNames())
		mmat=mat.clone(name)

		self.mats.append(mmat)
		self.callThreadSafe(self.matcontrol.addMaterial,mmat)
		return mmat
		
	def createSpectrum(self,specname):
		specname=uniqueStr(specname,self.listSpectrumNames())
		spec=Spectrum(specname)
		self.specs.append(spec)
		
		if self.win:
			self.win.addSpectrum(spec)
			# add the spectrum widget to the spectrum's property box
			@self.callThreadSafe
			def _modProp():
				prop=self.win.findPropBox(spec)
				prop.spectrum=SpectrumWidget(lambda:[spec],None,prop)
				prop.gridLayout.addWidget(prop.spectrum, 1, 0, 1, 1)
		
		return spec
		
	def getSpectrum(self,specname):
		'''Returns the spectrum object with the given, or None if not found.'''
		return first(s for s in self.specs if s.getName()==specname)
		
	def listSpectrumNames(self):
		'''Returns a list of all material names.'''
		return [s.getName() for s in self.specs]

	def cloneSpectrum(self,spec,name=None):
		'''
		Creates a new spectrum from `spec' (either name or Spectrum object). The new spectrum's name is `name'
		or a generated one if `name' is None.
		'''
		if isinstance(spec,str):
			spec=self.getSpectrum(spec)

		assert spec!=None

		name=uniqueStr(name if name!=None else spec.getName(), self.listSpectrumNames())
		sspec=self.createSpectrum(name)
		sspec.copySpectrumFrom(spec)

		return sspec
		
	def removeSpectrum(self,spec):
		self.specs.remove(spec)
		if self.win:
			self.win.removeObject(spec)

	def _newProjectButton(self):
		def chooseProjDir(name):
			newdir=self.win.chooseDirDialog('Choose Project Root Directory')
			if len(newdir)>0:
				self.createProjectObj(name,newdir,Project)

		self.win.chooseStrDialog('Choose Project Name','Project',chooseProjDir)
		
	def _newSpectrumButton(self):
		'''Opens the UI dialog to choose a new spectrum name, and then creates a new spectrum.'''
		existing=self.listSpectrumNames()
		self.win.chooseStrDialog('Choose Material Name',uniqueStr('Spectrum', existing),self.createSpectrum)

	def _newMaterialButton(self):
		'''Opens the UI dialog to choose a new material name, and then creates a new material.'''
		existing=self.listMaterialNames()
		self.win.chooseStrDialog('Choose Material Name',uniqueStr('Material', existing),self.createMaterial)

	def _newLightButton(self):
		'''Opens the UI dialog to choose a new light name, and then creates a new light.'''
		existing=[l.name for l in self.lights]
		def createWithName(newname):
			self.createLight(LightType._point,newname)

		self.win.chooseStrDialog('Choose Light Name',uniqueStr('Light', existing),createWithName)

	def _removeObjectButton(self):
		obj=self.win.getSelectedObject()
		if isinstance(obj,Project):
			self.win.chooseYesNoDialog('Remove Project?','Confirm Remove',self.deleteProjectObj)
		elif isinstance(obj,SceneObjectRepr):
			self.win.chooseYesNoDialog('Remove Representation %s?'%obj.getName(),'Confirm Remove',lambda:self.removeSceneObjectRepr(obj))
		elif isinstance(obj,SceneObject):
			self.win.chooseYesNoDialog('Remove Scene Object %s?'%obj.getName(),'Confirm Remove',lambda:self.removeSceneObject(obj))

	def _renameObjectButton(self):
		obj=self.win.getSelectedObject()
		if isinstance(obj,(SceneObject,SceneObjectRepr)):
			self.win.chooseStrDialog('Choose New Object Name',obj.getName(),lambda i:self.renameSceneObject(obj,i))

	def _clearSceneButton(self):
		self.win.chooseYesNoDialog('Clear Scene (remove project and objects)?','Confirm Clear',self.clearScene)

	def _cloneAssetButton(self):
		'''Clones the selected asset.'''
		asset=self.win.getSelectedAsset()
		name=str(asset.getName())
		
		if isinstance(asset,Material):
			existing=self.listMaterialNames()

			def cloneWithName(newname):
				self.cloneMaterial(self.getMaterial(name),newname)

			self.win.chooseStrDialog('Choose Material Name',uniqueStr(name, existing),cloneWithName)
		elif isinstance(asset,Spectrum):
			existing=self.listSpectrumNames()

			def cloneWithName(newname):
				self.cloneSpectrum(self.getSpectrum(name),newname)

			self.win.chooseStrDialog('Choose Spectrum Name',uniqueStr(name, existing),cloneWithName)

	def _removeAssetButton(self):
		'''Removes the selected asset.'''
		asset=self.win.getSelectedAsset()

		if isinstance(asset,Material):
			self.removeMaterial(asset)
		elif isinstance(asset,Spectrum):
			self.removeSpectrum(asset)
		elif isinstance(asset,Texture):
			self.removeTexture(asset)
		elif isinstance(asset,SceneLight):
			self.removeLight(asset)

	def _openProjectButton(self):
		pdir=self.win.chooseDirDialog('Choose Project Root Directory')
		if pdir:
			self.execScriptsTask(pdir)

	def _openScriptButton(self):
		script=self.win.chooseFileDialog('Choose Open Script Filename',filterstr='Python Files (*.py)',chooseMultiple=False)
		if script:
			self.execScriptsTask(script)

	def _saveProjectButton(self):
		if self.project:
			self.project.save()
		else:
			self.showStatusBarMsg('No project to save!')

	def _saveScriptButton(self):
		script=self.win.chooseFileDialog('Choose Save Script Filename',filterstr='Python Files (*.py)',chooseMultiple=False,isOpen=False)
		if script:
			with open(script,'w') as ofile:
				writer=ScriptWriter(ofile,os.path.dirname(os.path.abspath(script)))
				writer.writeScene(self)

	def _loadTextureButton(self):
		'''Brings up the file choose dialog and then loads a texture.'''
		textures=self.win.chooseFileDialog('Choose Texture Files',chooseMultiple=True) #filterstr='Images (*.png *.jpg)'

		try:
			for t in textures:
				self.loadTextureFile(t)
		except Exception as e:
			self.showExcept(e)
			
	def _loadGPUScriptButton(self):
		script=self.win.chooseFileDialog('Choose Script Files')
		try:
			if script:
				self.loadGPUScriptFile(script,PT_FRAGMENT)
		except Exception as e:
			self.showExcept(e)

	def _saveScreenshotAction(self):
		@taskroutine('Saving Screenshot(s)')
		def _save(path,source,width,height,start,end,interval,task=None):
			if start==end:
				self.saveScreenshot(path,source,width,height)
			else:
				base,ext=os.path.splitext(path)
				self.saveTimestepScreenshots(base,interval,start,end,source,width,height,ext)

		sources=[
			('Main Camera',self.cameras[0],self.cameras[0].getWidth(),self.cameras[0].getHeight()),
			('Main Window',self.win,self.win.width(),self.win.height())
		]

		for d in self.win.dockWidgets: # for each dock, add its camera to the list if it has one, or itself plus any graph widgets
			if hasattr(d,'camera'):
				sources.append((d.parent().windowTitle(),d.camera,d.camera.getWidth(),d.camera.getHeight())) # add camera to list
			else:
				sources.append((d.parent().windowTitle(),d,d.width(),d.height())) # add widget to list

				def func(w):
					if isinstance(w,self.getPlugin('Plot').BasePlotWidget):
						sources.append((' +--> '+str(w.objectName()),w,w.width(),w.height()))
						return False
					return True

				traverseWidget(d,func) # add any pyqtgraph types to list

		self.win.chooseScreenshotDialog(self.timestepMin,self.timestepMax,self.timeFPS,self.timeStepsPerSec,sources,lambda *args:self.addTasks(_save(*args)))

	def _saveLogFile(self):
		'''Called when the user chooses a filename for a log file.'''
		savename=self.win.chooseFileDialog('Choose log filename',filterstr='Log files (*.log)',isOpen=False,confirmOverwrite=False)
		if savename!='':
			setLogging(savename)

