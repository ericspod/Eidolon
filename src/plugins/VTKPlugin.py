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


from eidolon import *

addLibraryEgg('pyparsing-2.0.5-py2.7')

from pyparsing import *
import xml.etree.ElementTree as ET
import base64
import zlib
import StringIO
import contextlib

VTKProps=enum('header','desc','version','datasettype','griddims','attrtype','polyinds',desc='Metadata property names for storing VTK info in DataSet objects')
DatasetTypes=enum('STRUCTURED_GRID','UNSTRUCTURED_GRID','POLYDATA',desc='Understood VTK dataset types')
AttrTypes=enum('SCALARS','COLOR_SCALARS','LOOKUP_TABLE','VECTORS','NORMALS','TENSORS','TEXTURE_COORDINATES','FIELD',desc='Attribute section names')

CellTypes=enum(
	#('Vertex',1,'Point',(0,)),
	('Line',3,'Line1NL',(0,1)),
	('Triangle',5,'Tri1NL',(0,1,2)),
	('Poly',7,'Poly',(0,1)),
	('Quad',9,'Quad1NL',(0,1,3,2)),
	('Tet',10,'Tet1NL',(0,1,2,3)),
	('Hex',12,'Hex1NL',(0,1,3,2,4,5,7,6)),
	desc='Understood cell types, their IDs, equivalent ElemType names, and node orderings'
)


matrixCounter=0 # simple way of ensuring matrix name uniqueness
	
	
def toMatrix(mtype):
	def _split(s=None,l=None,t=None):
		if t==None or len(t)==0:
			return None
			
		global matrixCounter
		matrixCounter+=1
		
		if mtype: # if there's a matrix type, convert each element of t accordingly
			tokens=t[0].strip().split()
			if mtype==vec3:
				mat=[vec3(float(a),float(b),float(c)) for a,b,c in group(tokens,3)]
			else:
				mat=map(mtype,tokens)
		else: # otherwise assume the elements in t are converted already and just make a list of these
			mat=list(t)
			
		return listToMatrix(mat,'mat'+str(matrixCounter))
	
	return _split
	
	
def toTuple(s,l,t):
	return tuple(t)
	
	
ParserElement.setDefaultWhitespaceChars(' \t') # \n and \r are significant in this grammar

# regular expressions for integer and float, including sign and power components
intregex=r"[+-]?(([1-9]\d*)|0)"
floatregex=r"[+-]?((\d+(:?\.\d*)?)|(:?\.\d+))(:?[eE][+-]?\d+)?"

# base types
ident=Word(alphas+"_", alphanums+"_%$&*@#~") # no clear definition of an identifier, there may be other accepted characters
nls=Suppress(OneOrMore(lineEnd))
fnum=Regex(floatregex).setParseAction(lambda s,l,t:float(t[0]))
intnum=Regex(intregex).setParseAction(lambda s,l,t:int(t[0]))
vec=(fnum*3).setParseAction(lambda s,l,t:vec3(t[0],t[1],t[2]))

# base matrices
intnums=Regex(r"(%s[ \n\r\t]+)+"%intregex).setParseAction(toMatrix(int))
nums=Regex(r"(%s[ \n\r\t]+)+"%floatregex).setParseAction(toMatrix(float))
vecs=Regex(r"(%s[ \n\r\t]+)+"%floatregex).setParseAction(toMatrix(vec3))

# dataset
spatialvalue=(Keyword('DIMENSIONS')|Keyword('ORIGIN')|Keyword('SPACING')|Keyword('ASPECT_RATIO')) +vec+nls
spatialvalues=ZeroOrMore(spatialvalue).setParseAction(lambda s,l,t:dict((t[i],t[i+1]) for i in range(0,len(t),2)))

polyelems=(Keyword('VERTICES')|Keyword('LINES')|Keyword('POLYGONS')|Keyword('TRIANGLE_STRIPS'))+intnum+intnum+nls+intnums
polyelems.setParseAction(toTuple)

# cells and cell types, produces a list of tuples of varying length which is turned into a matrix with as many columns as the largest tuple
cellline=Regex(r"(%s[ \t]*)+"%intregex).setParseAction(lambda s,l,t:tuple(map(int,t[0].strip().split())))
cellnums=ZeroOrMore(cellline+nls).setParseAction(toMatrix(None))
cells=Suppress(Keyword('CELLS')+intnum+intnum)+nls+cellnums
celltypes=Suppress(Keyword('CELL_TYPES')+intnum)+nls+intnums

points=Suppress(Keyword('POINTS')+intnum+ident)+nls+vecs

strucpts=Keyword('STRUCTURED_POINTS')+nls+spatialvalues+Optional(points)
strucgrid=Keyword('STRUCTURED_GRID')+nls+Suppress(Keyword('DIMENSIONS'))+vec+nls+points
rectgrid=(Keyword('RECTILINEAR_GRID')+nls+Suppress(Keyword('DIMENSIONS'))+vec+nls+Suppress(Keyword('X_COORDINATES')+intnum)
		+ident+nums+Suppress(Keyword('Y_COORDINATES')+intnum)+ident+nums+Suppress(Keyword('Z_COORDINATES')+intnum)+ident+nums)
polydata=Keyword('POLYDATA')+nls+points+ZeroOrMore(polyelems)
unstrucgrid=Keyword('UNSTRUCTURED_GRID')+nls+points+cells+celltypes
dfield=Keyword('FIELD')+ident+nls+nums
dataset=Suppress(Keyword('DATASET'))+(strucpts|strucgrid|rectgrid|polydata|unstrucgrid|dfield).setParseAction(toTuple)

# attributes
fieldarray=(ident+intnum+intnum+ident+nls+nums).setParseAction(toTuple)

scalars=Keyword('SCALARS')+ident+ident+Optional(intnum)+nls+Optional(Keyword('LOOKUP_TABLE')+ident+nls)+nums
color_scalars=Keyword('COLOR_SCALARS')+ident+intnum+nls+nums
lookup=Keyword('LOOKUP_TABLE')+ident+intnum+nls+nums
vectors=Keyword('VECTORS')+ident+ident+nls+nums
normals=Keyword('NORMALS')+ident+ident+nls+nums
tensors=Keyword('TENSORS')+ident+ident+nls+nums
texcoords=Keyword('TEXTURE_COORDINATES')+ident+intnum+ident+nls+nums
field=Keyword('FIELD')+ident+intnum+nls+ZeroOrMore(fieldarray)
attrtypes=(scalars|color_scalars|lookup|vectors|normals|texcoords|tensors|field).setParseAction(toTuple)

attrs=((Keyword('POINT_DATA')|Keyword('CELL_DATA'))+intnum+nls+ZeroOrMore(attrtypes)).setParseAction(toTuple)

# header and file
header=Suppress(Keyword('#')+Keyword('vtk') + Keyword('DataFile') +Keyword('Version')) +fnum+nls + CharsNotIn('\r\n')+nls+Suppress(Keyword('ASCII'))+nls
vtkfile=header+dataset+ZeroOrMore(attrs)


@contextlib.contextmanager
def xmltag(out,name,**kwargs):
	if isinstance(out,tuple):
		indent,outstream=out
	else:
		indent,outstream=0,out
		
	values=' '.join('%s="%s"'%(str(k),str(v)) for k,v in kwargs.items())
	spacing=' '*indent
	outstream.write('%s<%s %s>\n'%(spacing,name,values))
	outstream.flush()
	yield (indent+1,outstream)
	outstream.write('%s</%s>\n'%(spacing,name))
	outstream.flush()
	

class VTKPlugin(MeshScenePlugin):
	def __init__(self):
		ScenePlugin.__init__(self,'VTK')
		self.objcount=0

	def init(self,plugid,win,mgr):
		MeshScenePlugin.init(self,plugid,win,mgr)
		
		if win:
			win.addMenuItem('Import','VTKLoad'+str(plugid),'&VTK Legacy/XML File',self._openFileDialog)
			win.addMenuItem('Import','VTKLoad'+str(plugid),'&VTK Legacy/XML Sequence',lambda:self._openFileDialog(True))
			win.addMenuItem('Export','VTKSave'+str(plugid),'&VTK XML File(s)',self._saveFileDialog)
			
		vtkload=filter(bool,mgr.conf.get('args','--vtk').split(','))
		
		if len(vtkload)>0:
			if len(vtkload)==1:
				obj=self.loadObject(vtkload[0])
			else:
				obj=self.loadSequence(vtkload)
			self.mgr.addFuncTask(lambda:self.mgr.addSceneObject(obj))
				
	def getHelp(self):
		return '\nUsage: --vtk=vtk-file-path[,vtk-file-path]*'
		
	def acceptFile(self,filename):
		return splitPathExt(filename)[2].lower() in ('.vtk','.vtu','.vtp')
		
	def checkFileOverwrite(self,obj,dirpath,name=None):
		if 'filename' in obj.kwargs:
			outfile=os.path.join(dirpath,name or obj.getName())+splitPathExt(obj.kwargs['filename'])[2]
			if os.path.isfile(outfile):
				return [outfile]
		elif 'filenames' in obj.kwargs:
			result=[]
			for filename in obj.kwargs['filenames']:
				outfile=os.path.join(dirpath,name or obj.getName())+splitPathExt(filename)[2]
				if os.path.isfile(outfile):
					result.append(outfile)
					
			return result
			
	def getObjFiles(self,obj):
		assert obj.plugin==self
		if 'filename' in obj.kwargs:
			return [obj.kwargs['filename']]
		else:
			return obj.kwargs.get('filenames',[])
		
	def copyObjFiles(self,obj,sdir,overwrite=False):
		filenames=self.getObjFiles(obj)
		assert filenames
		
		if len(filenames)==1:
			filename=os.path.join(sdir,os.path.basename(filenames[0]))
			copyfileSafe(obj.kwargs['filename'],filename,overwrite)
			obj.kwargs['filename']=filename
		else:
			newnames=[os.path.join(sdir,os.path.basename(f)) for f in filenames]
			for oldf,newf in zip(filenames,newnames):
				copyfileSafe(oldf,newf,overwrite)
			obj.kwargs['filenames']=newnames
		
	def renameObjFiles(self,obj,oldname,overwrite=False):
		assert isinstance(obj,SceneObject) and obj.plugin==self
		if 'filename' in obj.kwargs:
			obj.kwargs['filename']=renameFile(obj.kwargs['filename'],obj.getName(),overwriteFile=overwrite)
		elif 'filenames' in obj.kwargs:
			#obj.kwargs['filenames']=[renameFile(f,obj.getName()) for f in obj.kwargs['filenames']]
			newfiles=[]
			newname=obj.getName()
			
			for f in obj.kwargs['filenames']:
				newbasename=splitPathExt(f)[1].replace(oldname,newname,1)
				newfiles.append(renameFile(f,newbasename,overwriteFile=overwrite))
				
			obj.kwargs['filenames']=newfiles

	def parseString(self,strdata):
		return vtkfile.parseString(strdata.strip()+'\n').asList()
		
	def loadLegacyFile(self,filename,name=None,strdata=None):
		f=Future()
		@taskroutine('Loading VTK Legacy File')
		def _loadFile(filename,name,strdata,task):
			result=self.parseString(strdata or open(filename).read())
			
			basename=name or os.path.basename(filename).split('.')[0]
			name=uniqueStr(basename,[o.getName() for o in self.mgr.enumSceneObjects()])
	
			version,desc,data=result[:3]
			pointattrs=filter(lambda a:a[0]=='POINT_DATA',result[3:])
			cellattrs=filter(lambda a:a[0]=='CELL_DATA',result[3:])
			
			ds=None
			indmats=[]
			metamap={ VTKProps.desc:desc, VTKProps.version : str(version), VTKProps.datasettype : data[0] }
			
			# interpret dataset blocks
			if data[0]==DatasetTypes._UNSTRUCTURED_GRID:
				nodes,cells,celltypes=data[1:]
				
				# map cell types to the indices of members of `cells' of that type
				typeindices={}
				for i in xrange(celltypes.n()):
					typeindices.setdefault(celltypes.getAt(i),[]).append(i)	
				
				for ctype,inds in typeindices.items():
					tname,elemtypename,sortinds=first((n,e,s) for n,i,e,s in CellTypes if i==ctype) or (None,None,None)
					matname='' if tname==None else uniqueStr(tname,[i.getName() for i in indmats],'')
					if tname==CellTypes._Poly:
						mat=IndexMatrix(matname,elemtypename,0)
						polyinds=IndexMatrix(matname+'Inds',VTKProps._polyinds,0,2)
						mat.meta(VTKProps._polyinds,polyinds.getName())
						indmats.append(mat)
						indmats.append(polyinds)
						
						for ind in inds:
							row=cells.getRow(ind)
							length=row[0]
							polyinds.append(mat.n(),mat.n()+length)
							for r in row[1:length+1]:
								mat.append(r)
							
					elif tname!=None:
						elemtype=ElemType[elemtypename]
						mat=IndexMatrix(matname,elemtypename,0,elemtype.numNodes())
						indmats.append(mat)
						for ind in inds:
							sortedinds=indexList(sortinds,cells.getRow(ind)[1:])
							mat.append(*sortedinds)
							
			elif data[0]==DatasetTypes._STRUCTURED_GRID:
				dims,nodes=data[1:]
				dimx,dimy,dimz=map(int,dims)
	
				assert dimx>1			
				assert dimy>1			
				assert dimz>1			
				
				_,inds=generateHexBox(dimx-2,dimy-2,dimz-2)
				
				inds=listToMatrix(inds,'hexes')
				inds.setType(ElemType._Hex1NL)
				
				indmats=[inds]
				metamap[VTKProps._griddims]=repr((dimx,dimy,dimz))
				
			elif data[0]==DatasetTypes._POLYDATA:
				nodes=data[1]
				polyelems=data[2:]
				
				lines=IndexMatrix('lines',ElemType._Line1NL,0,2)
				tris=IndexMatrix('tris',ElemType._Tri1NL,0,3)
				quads=IndexMatrix('quads',ElemType._Quad1NL,0,4)
				
				for pname,numelems,numvals,ind in polyelems:
					n=0
					if pname=='POLYGONS':
						while n<ind.n():
							polylen=ind.getAt(n)
							if polylen==2:
								lines.append(ind.getAt(n+1),ind.getAt(n+2))
							elif polylen==3:
								tris.append(ind.getAt(n+1),ind.getAt(n+2),ind.getAt(n+3))
							elif polylen==4:
								quads.append(ind.getAt(n+1),ind.getAt(n+2),ind.getAt(n+4),ind.getAt(n+3))
							
							n+=polylen+1
							
				if len(tris)>0:
					indmats.append(tris)
				if len(quads)>0:
					indmats.append(quads)
				if len(lines)>0:
					indmats.append(lines)
			else:
				raise NotImplementedError,'Dataset type %s not understood yet'%str(data[0])
				
			ds=PyDataSet('vtk',nodes,indmats)
			for k,v in metamap.items():
				ds.meta(k,v)
				
			# read attributes into fields
			for attr in list(pointattrs)+list(cellattrs):
				for attrtype in attr[2:]:
					atype=str(attrtype[0])
					
					spatialname=first(ds.indices.keys()) # TODO: choose a better topology

					if atype == AttrTypes._FIELD:
						for fname,width,length,dtype,dat in attrtype[3:]:
							assert (width*length)==dat.n()
							assert length==nodes.n() or length==ds.indices[spatialname].n()							

							dat.setName(fname)
							dat.setM(width)
							dat.meta(StdProps._topology,spatialname)
							dat.meta(StdProps._spatial,spatialname)
							dat.meta(VTKProps._attrtype,atype)
							ds.setDataField(dat)
					else:
						dat=attrtype[-1]
						dat.setName(str(attrtype[1]))
						dat.meta(StdProps._topology,spatialname)
						dat.meta(StdProps._spatial,spatialname)
						dat.meta(VTKProps._attrtype,atype)
						ds.setDataField(dat)
							
						if atype in (AttrTypes._NORMALS,AttrTypes._VECTORS):
							dat.setM(3)
						elif atype == AttrTypes._LOOKUP_TABLE:
							dat.setM(4)
						elif atype == AttrTypes._TENSORS:
							dat.setM(9)
						elif atype in (AttrTypes._TEXTURE_COORDINATES,AttrTypes._COLOR_SCALARS):
							dat.setM(attrtype[2])
						elif atype == AttrTypes._SCALARS:
							if isinstance(attrtype[3],int):
								dat.setM(attrtype[3])
							if attrtype[3]==AttrTypes._LOOKUP_TABLE:
								dat.meta(AttrTypes._LOOKUP_TABLE,str(attrtype[4]))
							elif attrtype[4]==AttrTypes._LOOKUP_TABLE:
								dat.meta(AttrTypes._LOOKUP_TABLE,str(attrtype[5]))
				
			try:
				descdata=eval(desc) # if desc is a Python object (eg. timestep number) attempt to evaluate it
			except:
				descdata=desc # just a normal string
				
			f.setObject(MeshSceneObject(name,ds,self,filename=filename,descdata=descdata,result=result))
				
		return self.mgr.runTasks([_loadFile(filename,name,strdata)],f)

	def saveLegacyFile(self,filename,obj,**kwargs):
		dsindex=kwargs.get('dsindex',0)
		ds=obj.datasets[dsindex] if isinstance(obj,MeshSceneObject) else obj
		datasettype=kwargs.get('datasettype',ds.meta(VTKProps.datasettype)) or DatasetTypes._UNSTRUCTURED_GRID
		desc=kwargs.get('descStr',ds.meta(VTKProps._desc)).strip()
		writeFields=kwargs.get('writeFields',True)
		vecfunc=kwargs.get('vecfunc',tuple)
		version=3.0
		
		assert datasettype in DatasetTypes, 'Unsupported dataset type: %s'%datasettype
		
		if not desc:
			if isinstance(obj,MeshSceneObject):
				desc=repr({'desc':'Visualizer Output For '+obj.getName(),'timestep':obj.timestepList[dsindex]})
			else:
				desc='Visualizer Output For '+obj.getName()
			
		f=Future()
		@taskroutine('Saving VTK Legacy File')
		def _saveFile(filename,ds,datasettype,desc,version,task):
			with f:
				nodes=ds.getNodes()
				with open(filename,'w') as o:
					o.write('# vtk DataFile Version %.1f\n%s\nASCII\nDATASET %s'%(version,desc,datasettype))
					
					if datasettype == DatasetTypes._STRUCTURED_GRID:
						griddims=eval(ds.meta(VTKProps._griddims))
						o.write(' %i %i %i'%griddims)
					o.write('\n')
					
					# write out points
					o.write('POINTS %i double\n'%nodes.n())
					for n in xrange(nodes.n()):
						o.write('%f %f %f\n'%vecfunc(nodes.getAt(n)))
					
					# write out the extra components for unstructured grids
					if datasettype==DatasetTypes._UNSTRUCTURED_GRID:
						cells=[]
						celltypes=[]
						for inds in ds.indices.values():
							tname,cid,sortinds=first((n,i,s) for n,i,e,s in CellTypes if e==inds.getType()) or (None,None,None)
							
							if tname==CellTypes._Poly:
								polyinds=ds.getIndexSet(inds.meta(VTKProps._polyinds))
								celltypes+=[cid]*polyinds.n()
								
								for p in xrange(polyinds.n()):
									start,end=polyinds.getRow(p)
									poly=tuple(inds.getAt(i) for i in range(start,end))
									cells.append(poly)
							elif tname!=None:
								#unsortinds=list(reversed(indexList(sortinds,list(reversed(range(len(sortinds)))))))
								unsortinds=indexList(sortinds,range(len(sortinds)))
							
								celltypes+=[cid]*inds.n()
								for ind in xrange(inds.n()):
									cells.append(indexList(unsortinds,inds.getRow(ind)))
								
						if len(cells)>0:
							o.write('CELLS %i %i\n'%(len(cells),sum(len(c)+1 for c in cells)))
							for c in cells:
								o.write(' '.join(map(str,[len(c)]+list(c)))+'\n')
								
							o.write('CELL_TYPES %i\n'%len(celltypes))
							o.write('\n'.join(map(str,celltypes))+'\n')
							
					# write out fields as POINT_DATA, CELL_DATA is not supported
					fields=ds.fields.values() if writeFields else []
					if len(fields)>0:
						o.write('POINT_DATA %i\n'%nodes.n())
						
					for dat in fields:
						atype=dat.meta(VTKProps._attrtype) or AttrTypes._SCALARS
						name=dat.getName()
						
						if atype in (AttrTypes._SCALARS,AttrTypes._VECTORS,AttrTypes._NORMALS,AttrTypes._TENSORS):
							o.write('%s %s float\n'%(atype,name)) # scalars doesn't preserve any lookup table components
						elif atype in (AttrTypes._TEXTURE_COORDINATES,AttrTypes._COLOR_SCALARS):
							dtype=' float' if atype==AttrTypes._TEXTURE_COORDINATES else ''
							o.write('%s %s %i%s\n'%(atype,dat.m(),dtype))
						elif atype == AttrTypes._LOOKUP_TABLE:
							o.write('%s %i\n'%(atype,dat.n()))
						else:
							continue # skips field matrices if these get stored
						
						for n in xrange(dat.n()):
							o.write(' '.join(map(str,dat.getRow(n)))+'\n')
							
				f.setObject(filename)
						
		return self.mgr.runTasks([_saveFile(filename,ds,datasettype,desc,version)],f)
		
	def loadXMLFile(self,filename,name=None):
		def _get(elem,name):
			return elem.get(name) or elem.get(name.lower())
			
		def readArray(node,byteorder,compressor):
			dtype=np.dtype(_get(node,'type')).newbyteorder(byteorder)
			
			if _get(node,'format') and _get(node,'format').lower()=='binary':
				text=base64.decodestring(node.text)[8:] # skip 8 byte header?
				if compressor:
					raise NotImplementedError,"Haven't figured out compression yet"
					#text=zlib.decompress(text[:24]) # skip 24 byte header?
					
				return np.frombuffer(text,dtype=dtype)
			else:
				return np.loadtxt(StringIO.StringIO(node.text.replace('\n',' ')),dtype).flatten()
			
		def readNodes(nodearray,byteorder,compressor):
			assert _get(nodearray,'NumberOfComponents')=='3'					
			arr=readArray(nodearray,byteorder,compressor)
			nodes=Vec3Matrix('nodes',arr.shape[0]/3)
			np.asarray(nodes).flat[:]=arr
			del arr
			return nodes
				
		def readFields(celldata,pointdata,byteorder,compressor):
			fields=[]
			celldata=list(celldata)
			pointdata=list(pointdata)
			
			for array in (celldata+pointdata):
				fname=_get(array,'Name')
				width=int(_get(array,'NumberOfComponents') or 1)
				arr=readArray(array,byteorder,compressor)
				mat=RealMatrix(fname,arr.shape[0]/width,width)
				np.asarray(mat).flat[:]=arr
				del arr
					
				fields.append(mat)
				if array in celldata:
					mat.meta(StdProps._elemdata,'True')	
					
			return fields
				
		f=Future()
		@taskroutine('Loading VTK XML File')
		def _loadFile(filename,name,task):
			basename=name or os.path.basename(filename).split('.')[0]
			name=uniqueStr(basename,[o.getName() for o in self.mgr.enumSceneObjects()])
			ds=None
			
			tree=ET.parse(filename)
			root=tree.getroot()
			unstruc=root.find('UnstructuredGrid')
			poly=root.find('PolyData')
			#appended=root.find('AppendedData')
			compressor=_get(root,'compressor')
			byteorder='<' if root.get('byte_order')=='LittleEndian' else '>'
			
			if unstruc is not None:
				pieces=list(unstruc)
				
				points=pieces[0].find('Points')
				cells=pieces[0].find('Cells')
				celldata=pieces[0].find('CellData') 
				pointdata=pieces[0].find('PointData')
				nodearray=points.find('DataArray')
				
				if celldata is None:
					celldata=[]
				if pointdata is None:
					pointdata=[]
				
				nodes=readNodes(nodearray,byteorder,compressor)
				
				connectivity=first(i for i in cells if i.get('Name').lower()=='connectivity')
				types=first(i for i in cells if i.get('Name').lower()=='types')
				offsets=first(i for i in cells if i.get('Name').lower()=='offsets')
				
				indlist=readArray(connectivity,byteorder,compressor)
				celltypes=readArray(types,byteorder,compressor)
				offlist=readArray(offsets,byteorder,compressor)
				
				assert len(celltypes)==len(offlist)
				
				indmats=dict((i,(IndexMatrix(n+'Inds',e,0,len(s)),s,len(s))) for n,i,e,s in CellTypes)
				
				for i in xrange(len(celltypes)):
					celltype=celltypes[i]
					if celltype in indmats: # ignore cell types we don't understand (eg. vertex)
						indmat,sortinds,width=indmats[celltype]
						off=offlist[i]
						vals=indlist[off-width:off]
						indmat.append(*indexList(sortinds,vals))
					
				fields=readFields(celldata,pointdata,byteorder,compressor)
				
				ds=PyDataSet('vtk',nodes,[i for i,s,w in indmats.values() if i.n()>0],fields)
				
			elif poly is not None:
				pieces=list(poly)
				
				points=pieces[0].find('Points')
				celldata=pieces[0].find('CellData') 
				pointdata=pieces[0].find('PointData')
				nodearray=points.find('DataArray')
				
				poly=pieces[0].find('Polys')
				polyconnect=first(p for p in poly.findall('DataArray') if p.get('Name').lower()=='connectivity')
				
				nodes=readNodes(nodearray,byteorder,compressor)
				
				inds=[]
				
				if polyconnect is not None and len(polyconnect.text.strip())>0:
					ind=IndexMatrix('poly',ElemType._Tri1NL,0,3)
					for tri in group(polyconnect.text.split(),3):
						ind.append(*map(int,tri))
					inds.append(ind)
				
				fields=readFields(celldata,pointdata,byteorder,compressor)
				
				ds=PyDataSet('vtk',nodes,inds,fields)
			else:
				raise NotImplementedError,'Dataset not understood yet'
				
			f.setObject(MeshSceneObject(name,ds,self,filename=filename,isXML=True,descdata=''))
		
		return self.mgr.runTasks([_loadFile(filename,name)],f)

	def loadFile(self,filename,name=None):
		'''Deprecated, for compatibility only.'''
		return self.loadObject(filename,name)
		
	def loadObject(self,filename,name=None,**kwargs):
		if filename.endswith('.vtk'):
			return self.loadLegacyFile(filename,name)
		else:
			return self.loadXMLFile(filename,name)
			
	def saveObject(self,obj,path,overwrite=False,setFilenames=False,**kwargs):
		return self.saveXMLFile(path,obj,setObjArgs=setFilenames)
		
	def loadSequence(self,filenames,name=None):
		fileobjs=[self.loadObject(f) for f in filenames]
		f=Future()
		
		@taskroutine('Loading VTK File Sequence')
		def _loadSeq(filenames,fileobjs,name,task):
			with f:
				fileobjs=map(Future.get,fileobjs)
				name=name or fileobjs[0].getName()
				obj=MeshSceneObject(name,[o.datasets[0] for o in fileobjs],self,filenames=filenames)
				
				for i,o in enumerate(fileobjs):
					descdata=o.kwargs['descdata']
					if not isinstance(descdata,str) and 'timestep' in descdata:
						obj.timestepList[i]=int(descdata['timestep'])
						
				f.setObject(obj)
		
		return self.mgr.runTasks([_loadSeq(filenames,fileobjs,name)],f)
		
	def loadPolydataNodes(self,filename): 
		'''Fast load for node data from a polydata .vtk file, this ignores everything but the nodes.'''
		with open(filename) as o:
			header=[o.readline(),o.readline(),o.readline(),o.readline(),o.readline()]
			assert header[2].strip().lower()=='ascii',repr(header)
			assert header[3].strip().lower()=='dataset polydata',repr(header)
			
			nodes=Vec3Matrix('nodes',0)
			nodes.reserveRows(int(header[-1].split()[1])/3)
			vals=[]
			
			for line in o:
				vals+=line.split() # add numbers to accumulated list, this allows nodes to be split between lines safely
				while len(vals)>=3: # read a node if there's 3+ values, if the # of values isn't a multiple of 3 retain the last 1 or 2 in vals
					nodes.append(vec3(float(vals.pop(0)),float(vals.pop(0)),float(vals.pop(0))))
					
			return nodes,header
			
	def saveXMLFile(self,filenameprefix,obj,filetype='vtu',setObjArgs=False):
		def writeArray(xo,mat,**kwargs):
			with xmltag(xo,'DataArray',**kwargs) as xo1:
				o=xo1[1]
				o.write(' '*xo1[0])
				for n in xrange(mat.n()):
					for r in mat.getRow(n):
						o.write(' '+str(r))
				o.write('\n')
				
		def writeNodes(xo,nodes):
			with xmltag(xo,'Points') as xo1:
				with xmltag(xo1,'DataArray',type="Float32",NumberOfComponents="3",Format="ascii") as xo2:
					indents=' '*xo2[0]
					o=xo2[1]
					for n in xrange(nodes.n()):
						nn=nodes.getAt(n)
						o.write('%s%s %s %s\n'%(indents,nn.x(),nn.y(),nn.z()))
						
		def writeFields(xo,nodefields,cellfields):
			if nodefields:
				with xmltag(xo,'PointData') as xo1:
					for df in nodefields:
						writeArray(xo1,df, type="Float32", Name=df.getName(), Format="ascii")
						
			if cellfields:
				with xmltag(xo,'CellData') as xo1:
					for df in cellfields:
						writeArray(xo1,df, type="Float32", Name=df.getName(), Format="ascii")
		
		f=Future()
		@taskroutine('Saving VTK XML File')
		def _saveFile(obj,filenameprefix,filetype,setObjArgs,task):
			with f:
				assert filetype in ('vtu',) # TODO: other file types
				dds=obj.datasets
				filenameprefix=os.path.splitext(filenameprefix)[0]
				
				if os.path.isdir(filenameprefix):
					filenameprefix=os.path.join(filenameprefix,obj.getName())
				
				knowncelltypes={c[2]:c[1] for c in CellTypes}
				cellorders={c[2]:c[3] for c in CellTypes}
			
				if len(dds)==1:
					filenames=[filenameprefix+'.'+filetype]
				else:
					filenames=['%s_%.4i.%s'%(filenameprefix,i,filetype) for i in range(len(dds))]		
				
				for fn,ds in zip(filenames,dds):
					nodes=ds.getNodes()
					inds=filter(lambda i: i.getType() in knowncelltypes,ds.enumIndexSets())
					numcells=sum(i.n() for i in inds)
					numindices=sum(i.n()*i.m() for i in inds)
					
					cellfields=[df for df in ds.enumDataFields() if df.n()==numcells]
					nodefields=[df for df in ds.enumDataFields() if df.n()==nodes.n()]
					
					with open(fn,'w') as o:
						o.write('<?xml version="1.0"?>\n')
						if filetype=='vtu':
							with xmltag(o,'VTKFile',type="UnstructuredGrid", version="0.1", byte_order="BigEndian") as xo:
								with xmltag(xo,'UnstructuredGrid') as xo1:
									with xmltag(xo1,'Piece',NumberOfPoints=nodes.n(),NumberOfCells=numcells) as xo2:
										writeNodes(xo2,nodes)
													
										# calculate a new indices matrix by combining all those in inds and 
										# reordering the elements to match VTK ordering
										with xmltag(xo2,'Cells') as xo3:
											indices=IndexMatrix('indices',numindices)
											offsets=IndexMatrix('offsets',numcells)
											types=IndexMatrix('types',numcells)
											
											count=0
											pos=0
											ipos=0
											for ind in inds:
												typenum=knowncelltypes[ind.getType()]
												order=cellorders[ind.getType()]
												for n in xrange(ind.n()):
													count+=ind.m()
													offsets.setAt(count,pos) # add element offset
													types.setAt(typenum,pos) # add element type
													pos+=1
													
													# reorder the index values of this element to VTK ordering
													row=ind.getRow(n)
													for nn in order:
														indices.setAt(row[nn],ipos)
														ipos+=1
													
											writeArray(xo3,indices, type="Int32", Name="connectivity", Format="ascii")
											writeArray(xo3,offsets, type="Int32", Name="offsets", Format="ascii")
											writeArray(xo3,types, type="Int32", Name="types", Format="ascii")
											
										writeFields(xo2,nodefields,cellfields)
					
				if setObjArgs:
					if len(dds)==1:
						args={'filename':filenames[0]}
					else:
						args={'filenames':filenames}
					args['descdata']=''
					args['isXML']=True
					obj.plugin=self
					obj.kwargs=args
					
				f.setObject(filenames)
			
		return self.mgr.runTasks([_saveFile(obj,filenameprefix,filetype,setObjArgs)],f)				

	def _openFileDialog(self,chooseMultiple=False):
		filenames=self.mgr.win.chooseFileDialog('Choose VTK XML filename',filterstr='VTK Files (*.vtu *.vts *.vtp *.vtk)',chooseMultiple=chooseMultiple)
		if filenames:
			if chooseMultiple:
				obj=self.loadSequence(filenames)
			else:
				obj=self.loadObject(filenames)
				
			self.mgr.addFuncTask(lambda:self.mgr.addSceneObject(obj),'Importing VTK file(s)')
			
	def _saveFileDialog(self):
		obj=self.win.getSelectedObject()
		if isinstance(obj,SceneObjectRepr):
			obj=obj.parent

		if not isinstance(obj,MeshSceneObject):
			self.mgr.showMsg('Error: Must select mesh data object to export','VTK Export')
		else:
			filename=self.mgr.win.chooseFileDialog('Choose VTK filename',filterstr='VTK Files (*.vtu)',isOpen=False)
			if filename!='':
				self.saveXMLFile(filename,obj)

	def getScriptCode(self,obj,**kwargs):
		if isinstance(obj,MeshSceneObject):
			configSection=kwargs.get('configSection',False)
			namemap=kwargs.get('namemap',{})
			convertpath=kwargs['convertPath']
			script=''
			args={'varname':namemap[obj], 'objname':obj.name}

			if not configSection:
				if 'filename' in obj.kwargs:
					args['filename']=convertpath(obj.kwargs['filename'])
					script+='%(varname)s=VTK.loadObject(%(filename)s,%(objname)r)'
				elif 'filenames' in obj.kwargs:
					args['filenames']=('['+','.join(map(convertpath,obj.kwargs['filenames']))+']')
					script+='%(varname)s=VTK.loadSequence(%(filenames)s,%(objname)r)'
			
			return setStrIndent(script % args).strip()+'\n'
		else:
			return MeshScenePlugin.getScriptCode(self,obj,**kwargs)		
			
		
addPlugin(VTKPlugin())

