
from visualizer import *
from plugins.IRTKPlugin import IRTKPluginMixin
from plugins.VTKPlugin import DatasetTypes,VTKProps
from plugins.SegmentPlugin import SegmentTypes,SegSceneObject,DatafileParams
from ui.CTMotionProp import Ui_CTMotionProp


class CTmotionProjPropWidget(QtGui.QWidget,Ui_CTMotionProp):
	def __init__(self,parent=None):
		QtGui.QWidget.__init__(self,parent)
		self.setupUi(self)
		

# names of config values to store in the project's .ini file		
#ConfigNames=enum('ctImageStack','paramfile','lvtop','apex','rvtop','rvAtop','rvPtop','resampleStack')
ConfigNames=enum('paramfile')

class CTMotionTrackProject(Project):
	def __init__(self,name,parentdir,mgr):
		Project.__init__(self,name,parentdir,mgr)
		self.addHandlers()
		self.CTMotion=mgr.getPlugin('CTMotion')
		self.Dicom=mgr.getPlugin('Dicom')
		self.CTMotion.project=self
		self.header='\nCTMotion.createProject(%r,scriptdir+"/..")\n' %(self.name)
		self.logdir=self.getProjectFile('logs')
		self.backDir=self.logdir
		
#		for n in ConfigNames:
#			self.configMap[n[0]]=''
#			
#		self.configMap[ConfigNames._ctImageStack]=None
		self.configMap[ConfigNames._paramfile]='' #self.CTMotion.tsffd
#		self.configMap[ConfigNames._lvtop]=(0,0,0)
#		self.configMap[ConfigNames._apex]=(0,0,0)
##		self.configMap[ConfigNames._rvtop]=(0,0,0)
#		self.configMap[ConfigNames._rvAtop]=(0,0,0)
#		self.configMap[ConfigNames._rvPtop]=(0,0,0)
			
	def getPropBox(self):
		prop=Project.getPropBox(self)
		
		# remove the UI for changing the project location
		cppdel(prop.chooseLocLayout)
		cppdel(prop.dirButton)
		cppdel(prop.chooseLocLabel)
		
		self.ctprop=CTmotionProjPropWidget()
#		setCollapsibleGroupbox(self.ctprop.meshMaskGenGroup,False)
		prop.verticalLayout.insertWidget(prop.verticalLayout.count()-1,self.ctprop)
		
		self.ctprop.ctDicomButton.clicked.connect(self._loadCTButton)
		self.ctprop.niftiButton.clicked.connect(self._loadNiftiButton)
#		self.ctprop.resampleButton.clicked.connect(self._resampleButton)
#		self.ctprop.genMeshButton.clicked.connect(self._generateMeshButton)
		self.ctprop.chooseParamButton.clicked.connect(self._chooseParamFile)
		self.ctprop.trackButton.clicked.connect(self._trackButton)
#		self.ctprop.show3ptButton.clicked.connect(self._show3ptPanel)
#		self.ctprop.resample3ptButton.clicked.connect(self._resample3ptImage)
#		self.ctprop.createSegButton.clicked.connect(self._createSegObject)
#		self.ctprop.genMeshSegButton.clicked.connect(self._genSegMesh)
		self.ctprop.applyTrackButton.clicked.connect(self._applyTrack)
#		self.ctprop.squeezeButton.clicked.connect(self._calcSqueeze)
		
#		self.ctprop.resampleImgBox.activated.connect(self._setSourceVoxelDims)
#		self.ctprop.isotropicBox.stateChanged.connect(lambda:self._checkVoxelBoxes(float(self.ctprop.voxXBox.value())))
#		self.ctprop.voxXBox.valueChanged.connect(self._checkVoxelBoxes)
#		self.ctprop.voxYBox.valueChanged.connect(self._checkVoxelBoxes)
#		self.ctprop.voxZBox.valueChanged.connect(self._checkVoxelBoxes)
		
		self.ctprop.paramEdit.textChanged.connect(self.updateConfigFromProp)
		
		if not os.path.isdir(self.logdir):
			os.mkdir(self.logdir)
		
		return prop
		
	def updateConfigFromProp(self,*args):
		param=str(self.ctprop.paramEdit.text())
#		if not param:
#			param=self.CTMotion.tsffd
#			self.ctprop.paramEdit.setText(self.CTMotion.tsffd)
			
		if os.path.isfile(param):
			self.configMap[ConfigNames._paramfile]=param
		
	def updatePropBox(self,proj,prop):
		Project.updatePropBox(self,proj,prop)
		
		self.ctprop.paramEdit.setText(self.configMap[ConfigNames._paramfile])
#		
		sceneimgs=filter(lambda o:isinstance(o,ImageSceneObject),self.memberObjs)
#		scenesegs=filter(lambda o:isinstance(o,SegSceneObject),self.memberObjs)
		scenemeshes=filter(lambda o:isinstance(o,MeshSceneObject),self.memberObjs)
#
		names=sorted(o.getName() for o in sceneimgs)
#		fillList(self.ctprop.resampleImgBox,names)
#		fillList(self.ctprop.meshMaskBox,names)
		fillList(self.ctprop.trackImgBox,names)
		fillList(self.ctprop.trackMaskBox,names,defaultitem='None')
#		fillList(self.ctprop.choose3ptImgBox,names)
#		
#		names=sorted(o.getName() for o in scenesegs)
#		fillList(self.ctprop.genMeshSegBox,names)
#		
		names=sorted(o.getName() for o in scenemeshes)
		fillList(self.ctprop.trackObjBox,names)
#		
#		names=sorted(o.getName() for o in scenemeshes if len(o.datasets)>1)
#		fillList(self.ctprop.meshSqueezeBox,names)
#
#		trackdirs=set()
#		for d in glob.glob(self.getProjectFile('*/*.dof.gz')):
#			trackdirs.add(os.path.basename(os.path.dirname(d)))
				
		trackdirs=map(os.path.basename,self.CTMotion.getTrackingDirs())
		fillList(self.ctprop.trackDataBox,sorted(trackdirs))
#		
#		self._setSourceVoxelDims()
		
	def renameObject(self,obj,oldname):
		newname=getValidFilename(obj.getName())
		obj.setName(newname)
		
		conflicts=obj.plugin.checkFileOverwrite(obj,self.getProjectDir())
		if conflicts:
			raise IOError,'Renaming object would overwrite the following project files: '+', '.join(map(os.path.basename,conflicts))
			
		obj.plugin.renameObjFiles(obj,oldname)
			
		for n,v in self.checkboxMap.items():
			if v==oldname:
				self.checkboxMap[n]=newname
				
		for n,v in self.configMap.items():
			if v==oldname:
				self.configMap[n]=newname
		
		self.save()
		
	def _loadCTButton(self):
		@taskroutine('Loading Objects')
		def _loadObj(f,task):
			obj=Future.get(f)
			if obj:
				filenames=self.CTMotion.saveToNifti([obj])
				self.CTMotion.loadNiftiFiles(filenames)
			
		series=self.Dicom.openChooseSeriesDialog(subject='CT Series')
		
		if len(series)>0:
			f=self.Dicom.showTimeMultiSeriesDialog(series)
			self.mgr.runTasks(_loadObj(f))
			
	def _loadNiftiButton(self):
		filenames=self.mgr.win.chooseFileDialog('Choose NIfTI filename',filterstr='NIfTI Files (*.nii *.nii.gz)',chooseMultiple=True)
		if len(filenames)>0:
			self.CTMotion.loadNiftiFiles(filenames)
			
#	def _checkVoxelBoxes(self,val=0.0):
#		if self.ctprop.isotropicBox.isChecked():
#			with signalBlocker(self.ctprop.voxXBox,self.ctprop.voxYBox,self.ctprop.voxZBox):
#				self.ctprop.voxXBox.setValue(val)
#				self.ctprop.voxYBox.setValue(val)
#				self.ctprop.voxZBox.setValue(val)
#				
#	def _setSourceVoxelDims(self,i=None):
#		name=str(self.ctprop.resampleImgBox.currentText())
#		obj=self.CTMotion.findObject(name,False)
#		if obj:
#			self.ctprop.srcVoxelLabel.setText('Source Voxel Size: %.3f, %.3f, %.3f'%tuple(obj.getVoxelSize()))
#			
#	def _resampleButton(self):
#		name=str(self.ctprop.resampleImgBox.currentText())
#		x=float(self.ctprop.voxXBox.value())
#		y=float(self.ctprop.voxYBox.value())
#		z=float(self.ctprop.voxZBox.value())
#		self.CTMotion.resampleImage(name,vec3(x,y,z))
#		
#	def _generateMeshButton(self):
#		name=str(self.ctprop.meshMaskBox.currentText())
#		threshold=float(self.ctprop.thresholdBox.value())
#		smooth=int(self.ctprop.smoothBox.value())
#		resample=self.ctprop.resampleCheck.isChecked()
#		decimate=self.ctprop.decimateCheck.isChecked()
#		closed=self.ctprop.closedCheck.isChecked()
#		self.CTMotion.generateMesh(name,threshold,smooth,resample,decimate,closed)
		
	def _chooseParamFile(self):					
		filename=self.mgr.win.chooseFileDialog('Choose Parameter file')
		if filename:
			if not os.path.isfile(filename):
				self.mgr.showMsg('Cannot find file %r'%filename,'No Parameter File')
			else:
				self.ctprop.paramEdit.setText(filename)
				self.configMap[ConfigNames._paramfile]=filename
				self.saveConfig()
	
	def _trackButton(self):
		name=str(self.ctprop.trackImgBox.currentText())
		mask=str(self.ctprop.trackMaskBox.currentText())
		paramfile=str(self.ctprop.paramEdit.text())
		self.CTMotion.startMotionTrack(name,mask,paramfile)
#		
#	def _show3ptPanel(self):
#		name=str(self.ctprop.choose3ptImgBox.currentText())
#		if not name:
#			self.mgr.showMsg('Must select image series to choose points for','No Image Series Selected')
#			return
#			
#		c=self.mgr.callThreadSafe(self.mgr.create2DView,constr=Camera3PointView)
#		obj=self.mgr.findObject(name)
#		rep=first(obj.reprs)
#		
#		if rep:
#			c.setSourceName(rep.getName())
#		else:
#			rep=obj.createRepr(ReprType._imgtimevolume)
#			self.mgr.addFuncTask(lambda:self.mgr.addSceneObjectRepr(rep))
#			self.mgr.addFuncTask(lambda:c.setSourceName(rep().getName()))
#		
#	def _resample3ptImage(self):
#		name=str(self.ctprop.choose3ptImgBox.currentText())
#		lvtop=vec3(*self.configMap[ConfigNames._lvtop])
#		apex=vec3(*self.configMap[ConfigNames._apex])
#		#rvtop=vec3(*self.configMap[ConfigNames._rvtop])
#		rvAtop=vec3(*self.configMap[ConfigNames._rvAtop])
#		rvPtop=vec3(*self.configMap[ConfigNames._rvPtop])
#		
#		# choose the rvtop position based on the midpoint between corner nodes and their distance from the lvtop
#		rvtop=(lerp(0.5,rvAtop,rvPtop)-lvtop).norm()*(1.2*max(rvAtop.distTo(lvtop),rvPtop.distTo(lvtop)))+lvtop
##		rvtop=vec3(*self.configMap[ConfigNames._rvtop])
#		
#		if not name:
#			self.mgr.showMsg('Must select image series to resample','No Image Series Selected')
#		elif lvtop.distTo(apex)<epsilon or lvtop.distTo(rvtop)<epsilon or rvtop.distTo(apex)<epsilon:
#			self.mgr.showMsg('Image 3-points not chosen yet, open point picker first','No Points Selected')
#		else:
#			self.CTMotion.resample3ptImage(name,lvtop,apex,rvtop)
#			
#	def _createSegObject(self):
#		self.CTMotion.createSegObject(self.configMap[ConfigNames._resampleStack],SegmentTypes.LVPool)
#	
#	def _genSegMesh(self):
#		name=str(self.ctprop.genMeshSegBox.currentText())
#		refine=self.ctprop.genMeshRefineBox.value()
#		self.CTMotion.generateSegMesh(name,refine)
		
	def _applyTrack(self):
		name=str(self.ctprop.trackObjBox.currentText())
		trackname=str(self.ctprop.trackDataBox.currentText())
		srcname=first(o.getName() for o in self.memberObjs if isinstance(o,ImageSceneObject))
		f=self.CTMotion.applyTrackingToMesh(name,srcname,trackname)
		self.mgr.checkFutureResult(f)
	

class CTMotionTrackPlugin(ImageScenePlugin,IRTKPluginMixin):
	def __init__(self):
		ImageScenePlugin.__init__(self,'CTMotion')
		self.project=None
		
	def init(self,plugid,win,mgr):
		ImageScenePlugin.init(self,plugid,win,mgr)
		IRTKPluginMixin.init(self,plugid,win,mgr)
		
		self.Segment=self.mgr.getPlugin('Segment')
		
		if self.win!=None:
			self.win.addMenuItem('Project','CTMotionTrackProj'+str(plugid),'&CT Motion Track Project',self._newProjDialog)
		
	def createProject(self,name,parentdir):
		if self.mgr.project==None:
			self.mgr.createProjectObj(name,parentdir,CTMotionTrackProject)
				
	def _newProjDialog(self):
		def chooseProjDir(name):
			newdir=self.win.chooseDirDialog('Choose Project Root Directory')
			if len(newdir)>0:
				self.mgr.createProjectObj(name,newdir,CTMotionTrackProject)
				
		self.win.chooseStrDialog('Choose Project Name','Project',chooseProjDir)
		
	def getCWD(self):
		return self.project.getProjectDir()
	
	def getLogFile(self,filename):
		return os.path.join(self.project.logdir,ensureExt(filename,'.log'))
		
	def getLocalFile(self,name):
		return self.project.getProjectFile(name)
		
	def addObject(self,obj):
		if obj not in self.mgr.objs:
			self.mgr.addSceneObject(obj)
		self.project.addObject(obj)
		self.project.save()
		
	def loadNiftiFiles(self,filenames):
		f=Future()
		@taskroutine('Loading NIfTI Files')
		def _loadNifti(filenames,task):
			with f:
				isEmpty=len(self.project.memberObjs)==0
				filenames=Future.get(filenames)
				objs=[]
				for filename in filenames:
					filename=os.path.abspath(filename)
					if not filename.startswith(self.getCWD()):
						if filename.endswith('.nii.gz'): # unzip file, compression accomplishes almost nothing for nifti anyway
							newfilename=self.getUniqueLocalFile(splitPathExt(filename)[1])+'.nii'
							with gzip.open(filename) as gf:
								with open(newfilename,'wb') as ff:
									ff.write(gf.read())
						else:
							newfilename=self.getUniqueLocalFile(filename)
							copyfileSafe(filename,newfilename,True)
						filename=newfilename

					nobj=self.Nifti.loadObject(filename)
					self.addObject(nobj)
					objs.append(nobj)

				if isEmpty:
					self.mgr.callThreadSafe(self.project.updateConfigFromProp)
					self.project.save()

				f.setObject(objs)
				
		return self.mgr.runTasks(_loadNifti(filenames),f)
		
	def startMotionTrack(self,objname,maskname,paramfile):
		pass
		
	def applyTrackingToMesh(self,objname,srcname,trackname):
		f=Future()
		@taskroutine('Applying Tracking to Mesh')
		def _apply(objname,srcname,trackname,task):	
			with f:
				obj=self.findObject(objname)
				srcobj=self.findObject(srcname)
				trackdir=self.getLocalFile(trackname)
				trackfile=first(glob.glob(os.path.join(trackdir,'*.dof.gz')))
				resultname=self.getUniqueShortName(obj.getName(),'Tracked',trackname)
								
				assert isinstance(obj,MeshSceneObject)
				assert isinstance(srcobj,ImageSceneObject)
				assert os.path.isfile(trackfile)
				
				timesteps=srcobj.getTimestepList()
				outfiles=['out%.4i.vtk'%i for i in xrange(1,len(timesteps))]
				outfilepaths=[os.path.join(trackdir,o) for o in outfiles]
					
				vecfunc=lambda v:(-v.x(),-v.y(),v.z())
				self.VTK.saveLegacyFile(os.path.join(trackdir,'in.vtk'),obj,datasettype=DatasetTypes._POLYDATA,writeFields=False,vecfunc=vecfunc)
					
				task.setLabel('Applying tracking')
				task.setMaxProgress(len(outfiles))
				for i,o in enumerate(outfiles):
					task.setProgress(i)
					ttime=float(i+1)/len(outfiles)
					raise NotImplemented,'Choose a different transformation program'
					#execBatchProgram(self.ptransformation,'in.vtk',o,'-dofin',trackfile,'-time',str(ttime),cwd=trackdir)
					
				objds=obj.datasets[0]
				dss=[objds.clone(objds.getName()+'clone',True)]+map(self.readIRTKPolydata,outfilepaths)
				
				fields=[]
				for df in objds.fields.values():
					df=df.clone()
					df.meta(StdProps._timecopy,'True')
					fields.append(df)
					
				for ds in dss:
					if ds!=dss[0]: # don't fix the first dataset since it's the original
						ds.getNodes().mul(vec3(-1,-1,1)) 
						
					for i in objds.indices.values():
						ds.setIndexSet(i.clone())
					
					for df in fields:
						ds.setDataField(df)		
						
				nobj=MeshSceneObject(resultname,dss,filenames=outfilepaths)
				nobj.setTimestepList(timesteps)
				self.CHeart.saveSceneObject(self.getLocalFile(resultname),nobj,setObjArgs=True)
				self.addObject(nobj)
				f.setObject(nobj)
				self.win.selectObject(self.project)

		return self.mgr.runTasks(_apply(objname,srcname,trackname),f)
	
addPlugin(CTMotionTrackPlugin())
