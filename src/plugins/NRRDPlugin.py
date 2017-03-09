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


from eidolon import *

addLibraryFile('pynrrd-0.1-py2.7')

import nrrd


HeaderNames=enum('dimension','spacings','units','kinds','space origin','space','space directions','space origin','space units','space dimension')

class NRRDPlugin(ImageScenePlugin):				
	def __init__(self):
		ImageScenePlugin.__init__(self,'NRRD')
		
	def init(self,plugid,win,mgr):
		ImageScenePlugin.init(self,plugid,win,mgr)
		if win:
			win.addMenuItem('Import','NRRDLoad'+str(plugid),'&NRRD File',self._openFileDialog)
			win.addMenuItem('Export','NRRDExport'+str(plugid),'&NRRD File',self._exportMenuItem)
		
		# read command line argument, loading files as requested, note these tasks are queued at module load time
		if mgr.conf.hasValue('args','--nrrd'):
			loadvals=mgr.conf.get('args','--nrrd').split(',')
			filereprs=[]
			for m in loadvals:
				if m in ReprType and len(filereprs)>0:
					filereprs[-1][1]=m
				else:
					filereprs.append([m,None])
					
			@taskroutine('Loading NRRD File(s)')
			def _loadTask(filereprs,task=None):
				for m,reprtype in filereprs:
					obj=self.loadImage(m)
					self.mgr.addSceneObject(obj)
					
					if reprtype!=None:
						rep=obj.createRepr(reprtype)
						self.mgr.addSceneObjectRepr(rep)
						self.mgr.setCameraSeeAll()
			
			self.mgr.runTasks([_loadTask(filereprs)])
			
	def getHelp(self):
		return '\nUsage: --nrrd=file-path[,representation-type][,...]'
		
	def getObjFiles(self,obj):
		filename=obj.source['filename']
		if 'data file' in obj.source:
			return [filename,os.path.join(os.path.dirname(filename),obj.source['data file'])]
		else:
			return [filename]
			
	def copyObjFiles(self,obj,sdir,overwrite=False):
		files=self.getObjFiles(obj)
		filename=os.path.join(sdir,os.path.basename(files[0]))
		copyfileSafe(files[0],filename,overwrite)
		obj.source['filename']=filename
		if len(files)==2:
			copyfileSafe(files[1],os.path.join(sdir,os.path.basename(files[1])),overwrite)	
		
	def loadObject(self,filename,name=None,setpos=None,setrot=None,settrans=None,toffset=0,setinterval=None,**kwargs):
		'''
		Loads a NRRD image object from the file `filename'. If `name' is None then a name for the returned 
		ImageSceneObject is chosen from `filename', otherwise `name' is used.
		'''
		f=Future()

		@taskroutine('Loading NRRD File')
		def _loadFile(filename,name,setpos,setrot,setspacing,toffset,setinterval,task):
			with f:
				filename=Future.get(filename)
				basename=name or splitPathExt(filename)[1]
				name=uniqueStr(basename,[o.getName() for o in self.mgr.enumSceneObjects()]) # choose object name based on file name
				
				dat,hdr=nrrd.read(filename)				
				
				space=hdr.get(HeaderNames.space,0)
				spacedim=hdr.get(HeaderNames.space_dimension,0)
				dimension=hdr.get(HeaderNames.dimension,1)
				spacedir=hdr.get(HeaderNames.space_directions,[[1,0,0],[0,1,0],[0,0,1],'none'])
				position=vec3(*hdr.get(HeaderNames.space_origin,[0,0,0]))
				spacings=hdr.get(HeaderNames.spacings,[1]*dimension)
				
				assert dimension in (2,3,4), 'Can only understand NRRD images representing 2D images, 3D volumes, or 4D volumes'	
				
				movetimeaxis=spacedim==3 or space in ("right-anterior-superior", "RAS","left-anterior-superior","LAS","left-posterior-superior","LPS","scanner-xyz")		
				
				# calculate a rotation from the dimension vectors
				spacedir1=vec3(*spacedir[1 if movetimeaxis else 0])				
				spacedir2=vec3(*spacedir[2 if movetimeaxis else 1])
				rot=rotator(spacedir1,spacedir2,vec3(1,0,0),vec3(0,1,0))
				
				if movetimeaxis:
					dat=np.rollaxis(dat,0,len(dat.shape)) # move the time axis to the end
					spacing=vec3(*spacings[1:4])
				else:
					spacing=vec3(*spacings[:3])
					
				if dimension==4 and len(spacings)==dimension:
					interval=spacings[0 if movetimeaxis else 3] # if there's as many space values as dimensions, is the first or last the time interval?
				else:
					interval=1
					
				position-=rot*(spacing*0.5) # move position from center to top-left corner of image
				
				if setinterval!=None:
					interval=setinterval
				
				obj=self.createObjectFromArray(name,dat,interval,toffset,setpos or position,setrot or rot,setspacing or spacing,task=task)
				obj.source=hdr
				hdr['filename']=filename
				f.setObject(obj)
		
		return self.mgr.runTasks([_loadFile(filename,name,setpos,setrot,settrans,toffset,setinterval)],f)
	
#	def saveObject(self,obj,path,overwrite=False,setFilenames=False,**kwargs):
#		'''
#		'''
#		f=Future()
#
#		@taskroutine('Saving NRRD File')
#		def _saveFile(obj,path,kwargs,task):
#			with f:
#				pass
#		
#		return self.mgr.runTasks([_saveFile(obj,path,kwargs)],f)
		
	def _openFileDialog(self):
		filename=self.mgr.win.chooseFileDialog('Choose NRRD filename',filterstr='NRRD Files (*.nrrd  *.nhdr)')
		if filename!='':
			self.mgr.addFuncTask(lambda:self.mgr.addSceneObject(self.loadObject(filename)),'Importing NRRD file')
			
	def _exportMenuItem(self):
		obj=self.win.getSelectedObject()
		if not isinstance(obj,(ImageSceneObject,ImageSceneObjectRepr)):
			self.mgr.showMsg('Error: Must select image data object to export','NRRD Export')
		else:
			if isinstance(obj,ImageSceneObjectRepr):
				obj=obj.parent
				
			filename=self.mgr.win.chooseFileDialog('Choose NRRD filename',filterstr='NRRD Files (*.nrrd)',isOpen=False)
			if filename!='':
				self.saveObject(obj,filename)
				
#	def getScriptCode(self,obj,**kwargs):
#		configSection=kwargs.get('configSection',False)
#		namemap=kwargs.get('namemap',{})
#		scriptdir=kwargs['scriptdir']
#		varname=namemap[obj]
#		script=''
#		args={}
#		
#		if not configSection and isinstance(obj,ImageSceneObject):
#			filename=os.path.abspath(obj.source['filename'])
#			if scriptdir and filename.startswith(scriptdir):
#				filename='scriptdir+%r'%os.path.relpath(filename,scriptdir)
#			else:
#				filename='%r'%filename
#			
#			args={
#				'varname':varname,
#				'objname':obj.name,
#				'filename':filename
#			}
#					
#			script+='%(varname)s = MetaImg.loadImage(%(filename)s,%(objname)r)\n'
#			
#		elif isinstance(obj,ImageSceneObjectRepr):
#			args={
#				'varname':varname,
#				'pname':namemap[obj.parent],
#				'reprtype':obj.reprtype,
#				'matname':namemap.get(obj.getMaterialName(),'Greyscale')
#			}
#			
#			if configSection:
#				script= ImageScenePlugin.getScriptCode(self,obj,setMaterial=False,**kwargs)
#			else:
#				script= "%(varname)s=%(pname)s.createRepr(ReprType._%(reprtype)s,imgmat=%(matname)s)\n"
#			
#		return setStrIndent(script % args).strip()+'\n'

				
addPlugin(NRRDPlugin())