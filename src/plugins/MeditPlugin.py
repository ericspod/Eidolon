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

class MeditPlugin(MeshScenePlugin):
	def __init__(self):
		ScenePlugin.__init__(self,'Medit')
		self.objcount=0

	def init(self,plugid,win,mgr):
		MeshScenePlugin.init(self,plugid,win,mgr)
		
		if win:
			win.addMenuItem('Import','MeditLoad'+str(plugid),'&Medit .mesh File',self._openFileDialog)
			win.addMenuItem('Import','MeditSol'+str(plugid),'&Medit .bb File',self._openSolutionDialog)
			
		meditload=mgr.conf.get('args','--medit').split(',')
		
		if len(meditload) in (1,2) and meditload[0].strip():
			obj=self.loadFile(meditload[0])
			self.mgr.addFuncTask(lambda:self.mgr.addSceneObject(obj()))
			
			if len(meditload)==2:
				self.loadSolution(meditload[1],obj)

	def getHelp(self):
		return '\nUsage: --medit=mesh-file-path[,solution-file-path]'

	def getObjFiles(self,obj):
		filenames=[obj.kwargs['filename']]
		# solution files?
		return filenames
		
	def renameObjFiles(self,obj,oldname,overwrite=False):
		assert isinstance(obj,SceneObject) and obj.plugin==self
		obj.kwargs['filename']=renameFile(obj.kwargs['filename'],obj.getName(),overwriteFile=overwrite)
		
	def copyObjFiles(self,obj,sdir,overwrite=False):
		filename=os.path.join(sdir,os.path.basename(obj.kwargs['filename']))
		copyfileSafe(obj.kwargs['filename'],filename,overwrite)
		obj.kwargs['filename']=filename

	def _openFileDialog(self):
		filename=self.mgr.win.chooseFileDialog('Choose Medit filename',filterstr='Medit Mesh File (*.mesh)')
		if filename!='':
			self.mgr.addFuncTask(lambda:self.mgr.addSceneObject(self.loadObject(filename)),'Importing Medit file')
			
	def _openSolutionDialog(self):
		obj=self.win.getSelectedObject()
		
		if not obj or not isinstance(obj,MeshSceneObject):
			self.mgr.showMsg('A mesh object must be selected before data fields can be loaded for it.','No scene object')
		else:
			filename=self.mgr.win.chooseFileDialog('Choose Medit filename',filterstr='Medit Solution File (*.bb)')
			if filename!='':
				self.loadSolution(filename,obj)
			
	def loadObject(self,filename,name=None,**kwargs):
		widths={'triangles':3,'quadrilaterals':4,'tetrahedra':4,'hexaedra':8,'edges':2}
		types={'triangles':'Tri1NL','quadrilaterals':'Quad1NL','tetrahedra':'Tet1NL', 'hexaedra':'Hex1NL','edges':'Line1NL'}
		f=Future()
		
		@taskroutine('Loading Medit File')
		def _loadFile(filename,name,task):
			name=self.mgr.getUniqueObjName(name or splitPathExt(filename)[1])
			nodes=None
			indices=[]
			fields=[]
			
			with open(filename) as o:
				header=[o.readline(),o.readline(),o.readline()]
				assert header[0].strip()=='MeshVersionFormatted 1'
				assert header[1].strip()=='Dimension'
				assert header[2].strip()=='3'
				
				section=o.readline().strip().lower()
				while section and section!='end':
					numlines=int(o.readline())
					if section=='vertices': # special case for vertices
						nodes=Vec3Matrix('nodes',numlines)
						vertexrefs=RealMatrix('vertexrefs',numlines)
						vertexrefs.meta(StdProps._nodedata,'True')
						fields.append(vertexrefs)
						
						for n in xrange(numlines):
							line=map(float,o.readline().split())
							nodes.setAt(vec3(*line[:-1]),n)
							vertexrefs.setAt(line[-1],n)
					else: # read the index sets
						inds=IndexMatrix(section,types[section],numlines,widths[section])
						refs=RealMatrix(section+'refs',numlines)
						refs.meta(StdProps._spatial,section)
						refs.meta(StdProps._topology,section)
						
						for n in xrange(numlines):
							line=map(int,o.readline().split())
							inds.setRow(n,*line[:-1])
							refs.setAt(float(line[-1]),n)
							
						inds.sub(1)
						indices.append(inds)
						fields.append(refs)
						
					section=o.readline().strip().lower()
				
			f.setObject(MeshSceneObject(name,PyDataSet('meditDS',nodes,indices,fields),self,filename=filename))
			
		return self.mgr.runTasks(_loadFile(filename,name),f)
		
	def loadSolution(self,filename,obj,name=None):
		f=Future()
		@taskroutine('Loading Medit Solution File')
		def _loadFile(filename,name,obj,task):
			with open(filename) as o:
				obj=Future.get(obj)
				dds=obj.datasets
				dim,width,numvals,stype=map(int,o.readline().split())
				numlines=int(numvals/width)
				
				firstspatial=first(filter(isSpatialIndex,dds[0].indices.values())) # get the first spatial index
				
				sol=RealMatrix(name or splitPathExt(filename)[1],numlines,width)
				sol.meta(StdProps._topology,firstspatial.getName())
				sol.meta(StdProps._spatial,firstspatial.getName())
				sol.meta(StdProps._filename,filename)
				
				for n in xrange(numlines):
					sol.setRow(n,*map(float,o.readline().split()))
					
				for ds in dds:
					ds.setDataField(sol)
					
				f.setObject(sol)
		
		return self.mgr.runTasks(_loadFile(filename,name,obj),f)
			
	def getScriptCode(self,obj,**kwargs):
		if isinstance(obj,MeshSceneObject):
			configSection=kwargs.get('configSection',False)
			namemap=kwargs.get('namemap',{})
			convertpath=kwargs['convertPath']
			script=''
			args={'varname':namemap[obj],'objname':obj.name}
			
			if 'filename' in obj.kwargs:
				args['filename']=convertpath(obj.kwargs['filename'])

			if not configSection:
				if 'filename' in args:
					script+='%(varname)s=Medit.loadObject(%(filename)s,%(objname)r)\n'
			else:
				for i,field in enumerate(obj.datasets[0].enumDataFields()):
					ffilename=field.meta(StdProps._filename)
					if ffilename:
						args['ffilename'+str(i)]=convertpath(ffilename)
						script+='Medit.loadSolution(%(ffilename'+str(i)+')s,%(varname)s)\n'
			
			return setStrIndent(script % args).strip()+'\n'
		else:
			return MeshScenePlugin.getScriptCode(self,obj,**kwargs)		
			
		
addPlugin(MeditPlugin())