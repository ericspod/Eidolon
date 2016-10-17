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


from eidolon import vec3,rotator,ImageSceneObject,enum,ImageScenePlugin,ReprType,taskroutine,renameFile,SceneObject,printFlush
from eidolon import ensureExt,splitPathExt,Future,SharedImage,avgspan,ImageSceneObjectRepr,first,setStrIndent, addPlugin

import numpy as np

import os
import shutil
import math

genInfoFields=enum(
	('patientname','Patient name',str,0),
	('examname','Examination name',str,1),
	('protocol','Protocol name',str,2),
	('examdate','Examination date/time',str,3),
	('seriestype','Series Type',str,4),
	('acqnr','Acquisition nr',int,5),
	('reconnr','Reconstruction nr',int,6),
	('scandur','Scan Duration [sec]',float,7),
	('maxphase','Max. number of cardiac phases',int,8),
	('maxecho','Max. number of echoes',int,9),
	('maxloc','Max. number of slices/locations',int,10),
	('maxdyn','Max. number of dynamics',int,11),
	('maxmix','Max. number of mixes',int,12),
	('patientpos','Patient position',str,13),
	('prepdir','Preparation direction',str,14),
	('technique','Technique',str,15),
	('scanres','Scan resolution  (x, y)',int,16),
	('scanmode','Scan mode',str,17),
	('reptime','Repetition time [ms]',float,18),
	('fov','FOV (ap,fh,rl) [mm]',float,19),
	('water','Water Fat shift [pixels]',float,20),
	('angulation','Angulation midslice(ap,fh,rl)[degr]',float,21),
	('offcenter','Off Centre midslice(ap,fh,rl) [mm]',float,22),
	('flow','Flow compensation <0=no 1=yes> ?',int,23),
	('presat','Presaturation     <0=no 1=yes> ?',int,24),
	('phaseenc','Phase encoding velocity [cm/sec]',float,25),
	('mtc','MTC               <0=no 1=yes> ?',int,26),
	('spir','SPIR              <0=no 1=yes> ?',int,27),
	('epi','EPI factor        <0,1=no EPI>',int,28),
	('dynscan','Dynamic scan      <0=no 1=yes> ?',int,29),
	('diff','Diffusion         <0=no 1=yes> ?',int,30),
	('diffecho','Diffusion echo time [ms]',float,31),
	('maxdiff','Max. number of diffusion values',int,32),
	('maxgrad','Max. number of gradient orients',int,33),
	('numlabel','Number of label types   <0=no ASL>',int,34),
	doc='Values are (fullname, format, position)'
)

imgInfoFields=enum(
	('slicenum','slice number', int,1,0),
	('echonum','echo number', int,1,1),
	('dynnum','dynamic scan number', int,1,2),
	('phasenum','cardiac phase number', int,1,3),
	('imgtypemr','image_type_mr', int,1,4),
	('scanseq','scanning sequence', int,1,5),
	('indexrec','index in REC file', int,1,6),
	('imgpix','image pixel size', int,1,7),
	('scanper','scan percentage', int,1,8),
	('reconres','recon resolution', int, 2,9),
	('rescalein','rescale intercept', float,1,10),
	('rescalesl','rescale slope', float,1,11),
	('scalesl','scale slope', float,1,12),
	('wincen','window center', int,1,13),
	('winwid','window width', int,1,14),
	('imgang','image angulation', float, 3,15),
	('imgoff','image offcentre', float, 3,16),
	('sliceth','slice thickness', float,1,17),
	('slicega','slice gap', float,1,18),
	('imgdispo','image_display_orientation', int,1,19),
	('sliceori','slice orientation', int,1,20),
	('fmri','fmri_status_indication', int,1,21),
	('imgtype','image_type_ed_es', int,1,22),
	('pixspace','pixel spacing', float, 2,23),
	('echo','echo_time', float,1,24),
	('dynscan','dyn_scan_begin_time', float,1,25),
	('trigger','trigger_time', float,1,26),
	('diffbfac','diffusion_b_factor', float,1,27),
	('numavg','number of averages', int,1,28),
	('imgflip','image_flip_angle', float,1,29),
	('cardfreq','cardiac frequency', int,1,30),
	('minrr','minimum RR-interval', int,1,31),
	('maxrr','maximum RR-interval', int,1,32),
	('turbo','TURBO factor', int,1,33),
	('invdel','Inversion delay', float,1,34),
	('diffb','diffusion b value number', int,1,35),
	('gradori','gradient orientation number', int,1,36),
	('contrtype','contrast type', int,1,37),
	('diffani','diffusion anisotropy type', int,1,38),
	('diff','diffusion', float, 3,39),
	('labeltype','label type', int,1,40),
	doc='Values are (fullname, format, number of values, position)'
)

ImageTypes=enum(
	('Magnitude',0),
	('Phase',3)
)

SliceOrientations=enum(
	('Transverse',1),
	('Sagittal',2),
	('Coronal',3)
)


def parseParFile(filename):
	geninfo={}
	imginfo=[]
	numinfocols=sum(f[-2] for f in imgInfoFields)
	
	with open(filename) as o:
		lines=[l.strip() for l in o.readlines() if l.strip() and l.strip()[0]!='#']
		
	# parse the header values, this assumes the header values are always in the same order and does not check names
	for i in xrange(len(genInfoFields)):
		name,value=lines.pop(0).split(':',1)
		assert name[0]=='.'
		
		if genInfoFields[i][2]==str:
			value=value.strip()
		else:
			value=map(genInfoFields[i][2],value.split())
			
		geninfo[i]=value
		
	# parse the image info lines, this assumes the columns are always in the same order and does not check names as specified
	for line in lines:
		vals=map(float,line.split()) # convert to float now so that a column that's supposed to be int but is given as float will convert correctly
		assert len(vals)==numinfocols
		imgdef=[]
		
		for _,_,vtype,dim,_ in imgInfoFields:
			if dim==1:
				imgdef.append(vtype(vals.pop(0)))
			else:
				imgdef.append(tuple(vtype(vals.pop(0)) for i in range(dim)))
				
		imginfo.append(imgdef)
		
	return geninfo,imginfo


def getTransformFromInfo(offcenter,angulation,sliceorient,spacing,dimensions):
	'''
	Returns a (vec3,rotator) pair for the position and orientation of an image given the ParRec parameters for
	offcenter position, angulation in degrees, slice orientation value from SliceOrientations, pixel spacing, 
	and image dimensions.
	'''
	cy,cz,cx=offcenter
	theta,phi,rho=map(math.radians,angulation)
	refmat=np.array([[-1,0,0],[0,0,1],[0,-1,0]])
	AFRtoLPS=np.array([[0,0,1],[1,0,0],[0,1,0]])
	torient=np.eye(3)
	
	# get the slice orientation transform matrix
	if sliceorient==SliceOrientations.Transverse:
		torient=np.array([[0,1,0],[-1,0,0],[0,0,-1]])
	elif sliceorient==SliceOrientations.Sagittal:
		torient=np.array([[-1,0,0],[0,0,-1],[0,1,0]])
	elif sliceorient==SliceOrientations.Coronal:
		torient=np.array([[0,0,-1],[1,0,0],[0,1,0]])
	
	# convert angulation values to rotation matrices
	tap=np.array([[1,0,0],[0,math.cos(theta),-math.sin(theta)],[0,math.sin(theta),math.cos(theta)]])
	tfh=np.array([[math.cos(phi),0,math.sin(phi)],[0,1,0],[-math.sin(phi),0,math.cos(phi)]])
	trl=np.array([[math.cos(rho),-math.sin(rho),0],[math.sin(rho),math.cos(rho),0],[0,0,1]])
	
	# compose transformations and convert to a rotator object
	dirmat=AFRtoLPS.dot(trl).dot(tap).dot(tfh).dot(refmat).dot(torient)
	rot=rotator(*dirmat.flat)
	
	# Since rotation is defined at the center of the image, need to add a rotated mid vector to the 
	# position which is instead defined at the top left corner.
	midoffset=((spacing*vec3(1,-1,1))*(dimensions-vec3(1)))*0.5-spacing*vec3(0.5,-0.5,0)
	pos=vec3(cx,cy,cz)-(rot*midoffset)
	
	return pos,rot
		

class ParRecPlugin(ImageScenePlugin):
	def __init__(self):
		ImageScenePlugin.__init__(self,'ParRec')
		
	def init(self,plugid,win,mgr):
		ImageScenePlugin.init(self,plugid,win,mgr)
		if win:
			win.addMenuItem('Import','ParRecLoad'+str(plugid),'&Par File (Par-Rec)',self._openFileDialog)
		
		# read command line argument, loading files as requested, note these tasks are queued at module load time
		if mgr.conf.hasValue('args','--parrec'):
			loadvals=mgr.conf.get('args','--parrec').split(',')
			filereprs=[]
			for v in loadvals:
				if v in ReprType and len(filereprs)>0:
					filereprs[-1][1]=v
				else:
					filereprs.append([v,None])
					
			@taskroutine('Loading Par-Rec File(s)')
			def _loadTask(filereprs,task=None):
				for v,reprtype in filereprs:
					for obj in self.loadObject(v):
						self.mgr.addSceneObject(obj)
						
						if reprtype!=None:
							rep=obj.createRepr(reprtype)
							self.mgr.addSceneObjectRepr(rep)
							self.mgr.setCameraSeeAll()
			
			self.mgr.runTasks([_loadTask(filereprs)])
			
	def getHelp(self):
		return '\nUsage: --parrec=par-file-path[,representation-type][,...]'
		
	def acceptFile(self,filename):
		return splitPathExt(filename)[2].lower() == '.par'
		
	def checkFileOverwrite(self,obj,dirpath,name=None):
		outfile=os.path.join(dirpath,name or obj.getName())
		result=[]
		
		if os.path.exists(outfile+'.par'):
			result.append(outfile+'.par')
			
		if os.path.exists(outfile+'.rec'):
			result.append(outfile+'.rec')
		
		return result
		
	def getObjFiles(self,obj):
		filename=obj.source['filename']
		recfile=os.path.splitext(filename)[0]
		
		if os.path.exists(recfile+'.rec'):
			recfile=recfile+'.rec'
		elif os.path.exists(recfile+'.REC'):
			recfile=recfile+'.REC'
			
		return [filename,recfile]
		
	def copyObjFiles(self,obj,sdir,overwrite=False):
		par,rec=self.getObjFiles(obj)
		filename=os.path.join(sdir,os.path.basename(par))
		obj.source['filename']=filename
		copyfileSafe(par,filename,overwrite)
		copyfileSafe(rec,os.path.join(sdir,os.path.basename(rec)),overwrite)
		
	def renameObjFiles(self,obj,oldname,overwrite=False):
		assert isinstance(obj,SceneObject) and obj.plugin==self
		oldpath=obj.source['filename']
		recfile=ensureExt(oldpath,'.rec' if os.path.splitext(oldpath)[1]=='.par' else '.REC',True)
		renameFile(recfile,obj.getName(),overwriteFile=overwrite)
		obj.source['filename']=renameFile(oldpath,obj.getName(),overwriteFile=overwrite)
			
	def loadObject(self,filename,name=None,scalemethod=None,**kwargs):
		f=Future()
		@taskroutine('Loading ParRec Files')
		def _loadFile(filename,name,position=None,rot=None,toffset=None,interval=None,task=None):
			with f:
				filename=Future.get(filename)
				name=name or self.mgr.getUniqueObjName(splitPathExt(filename)[1])
				
				recfile=os.path.splitext(filename)[0]
				if os.path.exists(recfile+'.rec'):
					recfile=recfile+'.rec'
				elif os.path.exists(recfile+'.REC'):
					recfile=recfile+'.REC'
				else:
					raise IOError,"Cannot find rec file '%s.rec'"%recfile
					
				geninfo,imginfo=parseParFile(filename) # read par file
				rec=np.fromfile(recfile,np.uint8) # read rec file
				
#				numorients=geninfo[genInfoFields.maxgrad[2]][0]
#				numslices=geninfo[genInfoFields.maxloc[2]][0]
#				numsteps=geninfo[genInfoFields.maxphase[2]][0]
				
#				slicenum=imgInfoFields.slicenum[-1]
#				trigger=imgInfoFields.trigger[-1]
				
#				numslices=len(set(i[slicenum] for i in imginfo))
#				# count the number of times the slice number decreases one slice to the next, this indicates how many times the slice index loops back
#				numorients=1+sum(1 if imginfo[i][slicenum]>imginfo[i+1][slicenum] else 0 for i in range(len(imginfo)-1))
#				# count the number of times the trigger time decreases one slice to the next, this indicates when the images transition between volumes
#				numvols=1+sum(1 if imginfo[i][trigger]>imginfo[i+1][trigger] else 0 for i in range(len(imginfo)-1))/(numorients*numslices)
				
#				if len(imginfo)!=(numvols*numorients*numslices*numsteps):
#					raise IOError,'Mismatch between stated orient, slice, and step numbers and number of images (%r != %r*%r*%r*%r)'%(len(imginfo),numorients,numslices,numsteps,numvols)
				
#				orientsize=len(imginfo)/numorients
				datasize=0
				objs=[]
				rpos=0
				typemap={} # maps type ID to dict mapping dynamic ID to SharedImage lists
				
				for imgi in imginfo: # sum up the sizes of each image to compare against the actual size of the rec file
					w,h=imgi[imgInfoFields.reconres[-1]]
					pixelsize=imgi[imgInfoFields.imgpix[-1]]/8 # convert from bits to bytes
					datasize+=w*h*pixelsize
				
				if rec.shape[0]!=datasize:
					raise IOError,'Rec file incorrect size, should be %i but is %i'%(datasize,rec.shape[0])
					
				for imgi in imginfo:
					dynamic=imgi[imgInfoFields.dynnum[-1]]
					itype=imgi[imgInfoFields.imgtypemr[-1]]
					dims=imgi[imgInfoFields.reconres[-1]]
					trigger=imgi[imgInfoFields.trigger[-1]]
					orientation=imgi[imgInfoFields.sliceori[-1]]
					spacing=imgi[imgInfoFields.pixspace[-1]]
					offcenter=imgi[imgInfoFields.imgoff[-1]]
					angulation=imgi[imgInfoFields.imgang[-1]]
					pixelsize=imgi[imgInfoFields.imgpix[-1]]
					reslope=imgi[imgInfoFields.rescalesl[-1]]
					intercept=imgi[imgInfoFields.rescalein[-1]]
					
					if itype not in typemap:
						typemap[itype]=dict()
						
					if dynamic not in typemap[itype]:
						typemap[itype][dynamic]=[]
						
					images=typemap[itype][dynamic]
						
					dtype=np.dtype('uint'+str(pixelsize))
					
					pos,rot=getTransformFromInfo(offcenter,angulation,orientation,vec3(*spacing),vec3(*dims))

					imgsize=dims[0]*dims[1]*dtype.itemsize
					arr=rec[rpos:rpos+imgsize].view(dtype).reshape(dims)
					rpos+=imgsize
					
					if scalemethod in ('dv','DV'):
						arr=(arr.astype(float)*reslope)+intercept # DV scaling method							

					simg=SharedImage(recfile,pos,rot,dims,spacing,trigger)
					simg.allocateImg('%s_t%i_d%i_img%i'%(name,itype,dynamic,len(images)))
					simg.setArrayImg(arr)
						
					images.append(simg)	
				
				for itype in typemap:
					for dynamic,images in typemap[itype].items():
						vname='%s_t%i_d%i'%(name,itype,dynamic)
						source={'geninfo':geninfo,'imginfo':imginfo,'filename':filename,'scalemethod':scalemethod,'loadorder':len(objs)}
						obj=ImageSceneObject(vname,source,images,self)
						objs.append(obj)
				
#				for numo in xrange(numorients):
#					orientimgs=imginfo[numo*orientsize:(numo+1)*orientsize]
#					
#					for numv in xrange(numvols):
#						volsimgs=[img for i,img in enumerate(orientimgs) if i%numvols==numv]
#						images=[]
#						for imgi in volsimgs:
#							vname='%s_o%i_v%i'%(name,numo,numv)
#							dims=imgi[imgInfoFields.reconres[-1]]
#							trigger=imgi[imgInfoFields.trigger[-1]]
#							orientation=imgi[imgInfoFields.sliceori[-1]]
#							spacing=imgi[imgInfoFields.pixspace[-1]]
#							offcenter=imgi[imgInfoFields.imgoff[-1]]
#							angulation=imgi[imgInfoFields.imgang[-1]]
#							pixelsize=imgi[imgInfoFields.imgpix[-1]]
#							
#							reslope=imgi[imgInfoFields.rescalesl[-1]]
#							intercept=imgi[imgInfoFields.rescalein[-1]]
#							
#							dtype=np.dtype('uint'+str(pixelsize))
#							
#							pos,rot=self._getTransformFromInfo(offcenter,angulation,orientation,vec3(*spacing),vec3(*dims))
#		
#							imgsize=dims[0]*dims[1]*dtype.itemsize
#							arr=rec[rpos:rpos+imgsize].view(dtype).reshape(dims)
#							rpos+=imgsize
#							
#							if scalemethod in ('dv','DV'):
#								arr=(arr.astype(float)*reslope)+intercept # DV scaling method							
#	
#							simg=SharedImage(recfile,pos,rot,dims,spacing,trigger)
#							simg.allocateImg('%s_img%i'%(vname,len(images)))
#							simg.setArrayImg(arr)
#							images.append(simg)
#						
#						obj=ImageSceneObject(vname,{'geninfo':geninfo,'imginfo':imginfo,'filename':filename},images,self)
#						objs.append(obj)

				assert rpos==rec.shape[0],'%i != %i'%(rpos,rec.shape[0])
					
				f.setObject(objs)
					
		return self.mgr.runTasks([_loadFile(filename,name)],f)
			
	def _openFileDialog(self):
		filename=self.mgr.win.chooseFileDialog('Choose Par filename',filterstr='Par Files (*.par *.PAR)')
		if filename!='':
			self.mgr.addFuncTask(lambda:map(self.mgr.addSceneObject,self.loadObject(filename)),'Importing ParRec files')
			
	def getScriptCode(self,obj,**kwargs):
		configSection=kwargs.get('configSection',False)
		namemap=kwargs.get('namemap',{})
		convertpath=kwargs['convertPath']
		varname=namemap[obj]
		script=''
		args={}
		
		if not configSection and isinstance(obj,ImageSceneObject):
			filename=convertpath(obj.source['filename'])
			
			args={
				'varname':varname,
				'objname':obj.name,
				'filename':filename,
				'loadorder':obj.source['loadorder'],
				'scalemethod':obj.source['scalemethod'],
			}
					
			script+='%(varname)s = ParRec.loadObject(%(filename)s,%(objname)r,%(scalemethod)r)[%(loadorder)i]\n'
			
		elif isinstance(obj,ImageSceneObjectRepr):
			args={
				'varname':varname,
				'pname':namemap[obj.parent],
				'reprtype':obj.reprtype,
				'matname':namemap.get(obj.getMaterialName(),'Greyscale')
			}
			
			if configSection:
				script= ImageScenePlugin.getScriptCode(self,obj,setMaterial=False,**kwargs)
			else:
				script= "%(varname)s=%(pname)s.createRepr(ReprType._%(reprtype)s,imgmat=%(matname)s)\n"
			
		return setStrIndent(script % args).strip()+'\n'		
		
addPlugin(ParRecPlugin())
