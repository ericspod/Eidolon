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

import gzip
from glob import glob

from .IRTKPlugin import IRTKPluginMixin,ServerMsgs,applyMotionTrackTask
from .SegmentPlugin import SegSceneObject,SegmentTypes
from .VTKPlugin import DatasetTypes
from .CheartPlugin import LoadDialog
from .ReportCardPlugin import ReportCardSceneObject
from .DicomPlugin import readDicomHeartRate
from ui.CardiacMotionProp import Ui_CardiacMotionProp


def avgDevRange(vals,stddevDist=1.0):
	if not vals:
		return 0

	a=avg(vals)
	sd=stddev(vals)*stddevDist
	return avg(v for v in vals if abs(v-a)<=sd)


#@timing
#def calculateRadialField(ds,indmat):
#	'''
#	Calculate a field of radial vectors for the surface of the mesh defined by index matrix `indmat' using nodes and
#	other data from dataset `ds'.
#	'''
#	calculateElemExtAdj(ds)
#
#	result=calculateMeshSurfNormals(ds.getNodes(),indmat,ds.getIndexSet(indmat.getName()+MatrixType.external[1]))
#	radialf=RealMatrix('radial',0,3)
#	for i in xrange(result.n()):
#		radialf.append(*result.getAt(i))
#
#	radialf.meta(StdProps._topology,indmat.getName())
#	radialf.meta(StdProps._spatial,indmat.getName())
#	radialf.meta(StdProps._timecopy,'True')
#	ds.setDataField(radialf)
#	return radialf
#
#
#@timing
#def calculateLVDirectionalFields(ds,radialfield,longaxis,longname,circumname):
#	'''
#	Given the dataset `ds' and radial vector field `radialfield', calculate the logitudinal and circumferential fields
#	using LV centerline axis direction `longaxis'. The names of the returned matrices are `longname' and `circumname'.
#	'''
#	length=radialfield.n()
#	longmat=RealMatrix(longname,length,3)
#	circummat=RealMatrix(circumname,length,3)
#
#	for n in xrange(length):
#		longmat.setRow(n,*longaxis)
#		circummat.setRow(n,*longaxis.cross(vec3(*radialfield.getRow(n))))
#
#	longmat.meta(StdProps._topology,radialfield.meta(StdProps._topology))
#	longmat.meta(StdProps._spatial,radialfield.meta(StdProps._spatial))
#	longmat.meta(StdProps._timecopy,'True')
#	circummat.meta(StdProps._topology,radialfield.meta(StdProps._topology))
#	circummat.meta(StdProps._spatial,radialfield.meta(StdProps._spatial))
#	circummat.meta(StdProps._timecopy,'True')
#
#	return longmat,circummat
	
	
@timing
def calculateLVDirectionalFields(ds,longaxis,radialname,longname,circumname):
	
	spatialmats=filter(isSpatialIndex,ds.enumIndexSets())
	indmat=first(m for m in spatialmats if ElemType[m.getType()].dim==3) or first(spatialmats)
	indname=indmat.getName()
	
	nodes=ds.getNodes().clone()
	length=nodes.n()

	longmat=RealMatrix(longname,length,3)
	radialmat=RealMatrix(radialname,length,3)
	circummat=RealMatrix(circumname,length,3)

	orient=rotator(longaxis,vec3(0,0,1))
	nodes.mul(transform(-BoundBox(nodes).center,vec3(1),orient))  # transforms the mesh so that the centerline is Z axis
	
	# calculate the bound boxes of the nodes near the mitral plane and apex
	minz,maxz=minmax([n.z() for n in nodes]) # determine the min and max distance from the origin in the Z dimension, ie. height
	mitralaabb=BoundBox([n for n in nodes if n.z()<(minz+(maxz-minz)*0.1)])
	apexaabb=BoundBox([n for n in nodes if n.z()>(minz+(maxz-minz)*0.9)])
	
	# `longaxis' is pointing from apex to mitral so reverse it, this assumes apex is small which may be wrong
	if mitralaabb.radius<apexaabb.radius:
		longaxis=-longaxis
		mitralaabb,apexaabb=apexaabb,mitralaabb
		
	#nodes.sub(apexaabb.center*vec3(1,1,0)) # try to center on the apex
	
	apexray=Ray(mitralaabb.center,(apexaabb.center-mitralaabb.center))
	
	for n in xrange(length):
		node=nodes[n]
		d=apexray.distTo(node) #*0.9 # scale the distance along the ray so that apex directions are more rounded
		rad=orient/((node-apexray.getPosition(d))*vec3(1,1,0)).norm()
		#rad=orient/(node*vec3(1,1,0)).norm()
		
		radialmat.setRow(n,*rad)
		longmat.setRow(n,*longaxis)
		circummat.setRow(n,*(longaxis.cross(rad)))

	longmat.meta(StdProps._topology,indname)
	longmat.meta(StdProps._spatial,indname)
	longmat.meta(StdProps._timecopy,'True')
	circummat.meta(StdProps._topology,indname)
	circummat.meta(StdProps._spatial,indname)
	circummat.meta(StdProps._timecopy,'True')
	radialmat.meta(StdProps._topology,indname)
	radialmat.meta(StdProps._spatial,indname)
	radialmat.meta(StdProps._timecopy,'True')

	return radialmat,longmat,circummat


def createStrainGrid(nodes,toRefSpace,toImgSpace,h):
	'''
	Calculate the 6 point strain node set for each node of `nodes'. Each node from `nodes' is first transformed by
	`toRefSpace' to place it in reference space, then 6 vectors are calculated by shifting the node by `h' in along
	each axis in the positive and negative directions. All vectors are then transformed by `toImgSpace'. The result
	is a matrix with 7 columns, the transformed node and its 6 shifted vectors.
	'''
	result=Vec3Matrix('straingrid',0,7)
	result.reserveRows(len(nodes))

	dx=vec3(h,0,0)
	dy=vec3(0,h,0)
	dz=vec3(0,0,h)

	for n in xrange(len(nodes)):
		p=toRefSpace*nodes[n]
		result.append(p,p+dx,p-dx,p+dy,p-dy,p+dz,p-dz)

	result.mul(toImgSpace)

	return result


def createStrainField(nodes,radialfield,longfield,circumfield,h):
	'''
	Calculate a strain field by adding or subtracting the corresponding directional vectors to each node in `nodes'.
	'''
	numnodes=nodes.n()
	result=Vec3Matrix('strainfield',0,7)
	result.reserveRows(numnodes)

	for n in xrange(numnodes):
		p=nodes.getAt(n)
		rad=vec3(*radialfield.getRow(n)).norm()*h
		cir=vec3(*circumfield.getRow(n)).norm()*h
		lon=vec3(*longfield.getRow(n)).norm()*h
		result.append(p,p+rad,p-rad,p+cir,p-cir,p+lon,p-lon)

	return result


def strainTensor(px,mx,py,my,pz,mz,hh):
	'''
	Calculate the Green-Lagrange strain tensor for a point in space given the 6 deformed strain axes for that point.
	The vectors are assumed to have been calculated initially at a distance of `hh' from the node.
	'''
	hh2=1.0/(2.0*hh)

	# gradient matrix G
	a,b,c=(px-mx)*hh2
	d,e,f=(py-my)*hh2
	g,h,i=(pz-mz)*hh2

	# unrolled equivalent of 0.5*(F.T*F-np.eye(3)) where F=G+np.eye(3)
#	E1=0.5*(a**2 + 2.0*a + d**2 + g**2)
#	E2=0.5*(a*b + b + d*e + d + g*h)
#	E3=0.5*(a*c + c + d*f + g*i + g)
#	E5=0.5*(b**2 + e**2 + 2.0*e + h**2)
#	E6=0.5*(b*c + e*f + f + h*i + h)
#	E9=0.5*(c**2 + f**2 + i**2 + 2.0*i)
#	return E1,E2,E3,E2,E5,E6,E3,E6,E9

	#F=np.asarray([[a,b,c],[d,e,f],[g,h,i]],dtype=float)
	#T=0.5*(np.dot(F.T,F)-np.eye(3))
	#return T.flatten().tolist()

	x0 = 0.5*a
	x1 = 0.5*d
	x2 = 0.5*g
	x3 = b*x0 + e*x1 + h*x2
	x4 = c*x0 + f*x1 + i*x2
	x5 = 0.5*b*c + 0.5*e*f + 0.5*h*i
	
	return 0.5*a**2 + 0.5*d**2 + 0.5*g**2 - 0.5, x3, x4, x3, 0.5*b**2 + 0.5*e**2 + 0.5*h**2 - 0.5, x5, x4, x5, 0.5*c**2 + 0.5*f**2 + 0.5*i**2 - 0.5


def tensorMul(E,v):
	'''Returns Ev.v'''
	#return (E[0]*v[0]+E[1]*v[1]+E[2]*v[2]),(E[3]*v[0]+E[4]*v[1]+E[5]*v[2]),(E[6]*v[0]+E[7]*v[1]+E[8]*v[2])
	return (E[0]*v[0]+E[1]*v[1]+E[2]*v[2])*v[0]+(E[3]*v[0]+E[4]*v[1]+E[5]*v[2])*v[1]+(E[6]*v[0]+E[7]*v[1]+E[8]*v[2])*v[2]

@timing
def calculateStrainTensors(nodes_t,h):
	'''
	Calculate the tensors for each row of `nodes_t', which is the transformed node and its 6 transformed strain vectors.
	The result is a 9 column matrix where each row is a tensor matrix laid out in row-column order.
	'''
	result=RealMatrix('straintensors',0,9)
	result.reserveRows(nodes_t.n())

	for n in xrange(nodes_t.n()):
		p,px,mx,py,my,pz,mz=nodes_t.getRow(n)
		result.append(*strainTensor(px,mx,py,my,pz,mz,h))

	return result


@timing
def calculateTensorIndicatorEigen(tensors):
	'''Calculate the maximal and minimal eigenvalue for each tensor matrix in `tensors.'''
	maxeig=RealMatrix('maxstrain',0)
	maxeig.reserveRows(tensors.n())
	mineig=RealMatrix('maxstrain',0)
	mineig.reserveRows(tensors.n())

	for n in xrange(tensors.n()):
		E=np.matrix(tensors.getRow(n)).reshape(3,3)
		eigvals,reigvals=np.linalg.eig(E)
		maxeig.append(np.max(eigvals))
		mineig.append(np.min(eigvals))

	return maxeig,mineig


@timing
def calculateTensorMul(tensors,vecmat,name):
	assert tensors.n()==vecmat.n(),'%i != %i'%(tensors.n(),vecmat.n())
	result=RealMatrix(name,tensors.n())

	for n in xrange(tensors.n()):
		E=tensors.getRow(n)
		v=vecmat.getRow(n)
		result.setRow(n,tensorMul(E,v))

	return result


@concurrent
def divideTrisByElemValRange(process,tris,nodeprops,elemvals,choosevals):
	matrices=dict((cv,IndexMatrix('choose_%i_%r'%(process.index,cv),tris.getType(),0,tris.m())) for cv in choosevals)

	for n in xrange(tris.n()):
		process.setProgress((n+1)/process.total)
		nodeinds=tris.getRow(n) # node indices for this triangle
		origind=nodeprops.getAt(nodeinds[0]) # original element index
		val=elemvals.getAt(origind) # the value for the original element

		if val in matrices:
			matrices[val].append(*nodeinds)

	return shareMatrices(*matrices.values())


@timing
def divideMeshSurfaceByElemVal(dataset,elemvals,choosevals,task=None):
	calculateElemExtAdj(dataset,task=task)

	trids,indlist=generateLinearTriangulation(dataset,'dividetris',0,True,task)
	tris=trids.getIndexSet(trids.getName()+MatrixType.tris[1])
	nodeprops=trids.getIndexSet(trids.getName()+MatrixType.props[1])

	assert len(indlist)==1,'Multiple spatial topologies found in mesh, cannot determine element value field association'
	assert indlist[0].n()==elemvals.n(),'Element value field length (%i) does not match topology length (%i)'%(elemvals.n(),indlist[0].n())

	proccount=chooseProcCount(tris.n(),0,2000)
	shareMatrices(tris,nodeprops,elemvals)
	results= divideTrisByElemValRange(tris.n(),proccount,task,tris,nodeprops,elemvals,choosevals,partitionArgs=(choosevals,))

	matrices=listSum(map(list,results.values()))

	return trids,indlist,matrices


def divideMeshByElemFunc(datasets,oldinds,choosefunc):
	oldnodes=datasets[0].getNodes()

	nodes=Vec3Matrix('nodes',0,1)
	inds=IndexMatrix(oldinds.getName(),0,oldinds.m())
	inds.meta(StdProps._isspatial,'True')
	inds.setType(oldinds.getType())

	chosen=[]
	nodemap={}

	for n in xrange(oldinds.n()):
		if choosefunc(n):
			chosen.append(n)
			row=oldinds.getRow(n)
			for i in xrange(len(row)):
				if row[i] not in nodemap:
					nodes.append(oldnodes.getAt(row[i]))
					nodemap[row[i]]=nodes.n()-1

			inds.append(*[nodemap[r] for r in row])

	fields=[]
	for oldfield in datasets[0].enumDataFields():
		if oldfield.n()==oldinds.n():
			field=RealMatrix(oldfield.getName(),0,oldfield.m())
			fields.append(field)
			for ch in chosen:
				field.append(*oldfield.getRow(ch))
		elif oldfield.n()==oldnodes.n():
			field=RealMatrix(oldfield.getName(),nodes.n(),oldfield.m())
			fields.append(field)
			for oldind,newind in nodemap.items():
				field.setRow(newind,*oldfield.getRow(oldind))

	dsout=[PyDataSet(datasets[0].getName()+'Div',nodes,[inds],fields)]

	for ds in datasets[1:]:
		olddsnodes=ds.getNodes()
		dsnodes=Vec3Matrix('nodes',nodes.n(),1)
		for oldind,newind in nodemap.items():
			dsnodes.setAt(olddsnodes.getAt(oldind),newind)

		dsout.append(PyDataSet(ds.getName()+'Div',dsnodes,[inds],fields))

	return dsout,chosen,nodemap


#@concurrent
#def divideMeshElemsByElemValRange(process,inds,elemvals,choosevals):
#	matrices=dict((cv,IndexMatrix('choose_%i_%r'%(process.index,cv),inds.getType(),0,inds.m())) for cv in choosevals)
#
#	for n in process.prange():
#		matrices[elemvals.getAt(n)].append(inds.getRow(n))
#
#	return shareMatrices(*[matrices[cv] for cv in choosevals])
#
#
#def divideMeshElemsByElemVal(dataset,elemvals,choosevals,task=None):
#	inds=dataset.getIndexSet(elemvals.meta(StdProps._spatial)) or first(dataset.enumIndexSets())
#
#	assert inds
#	assert inds.n()==elemvals.n()
#
#	proccount=chooseProcCount(inds.n(),0,2000)
#	shareMatrices(inds,elemvals)
#	results=divideMeshElemsByElemValRange(inds.n(),proccount,task,inds,elemvals,choosevals)
#
#	results=[results[i] for i in sorted(results)]
#	unshareMatrices(*results[0])
#
#	for r in results[1:]:
#		for i in range(len(r)):
#			results[0][i].append(r[i])
#
#	return results[0]


@concurrent
def calculateRegionThicknessesRange(process,trinodes,stddevRange,triindlist):
	'''
	Returns the averaged thickness of each triangle mesh given in `triindlist'. It is assumed that the name of each
	such topology matrix is of the form "choose_X_Y" where X is the ID of the process in divideTrisByElemValRange()
	which created the matrix, and Y corresponds to the region number that mesh belongs to. The return value is a list
	of pairs, one for each member of `triindlist', containing Y and the computed average thickness.
	'''
	results=[]

	maxlen=max(triind.n() for triind in triindlist)
	centers=Vec3Matrix('centers',maxlen)
	norms=Vec3Matrix('norms',maxlen)
	radii2=RealMatrix('radii2',maxlen)

	for triind in triindlist:
		for n in xrange(triind.n()):
			nodes=trinodes.mapIndexRow(triind,n)#getElemNodes(n,triind,trinodes)
			center=(nodes[0]+nodes[1]+nodes[2])/3.0
			centers.setAt(center,n)
			norms.setAt(nodes[0].planeNorm(nodes[1],nodes[2]),n)
			radii2.setAt(max(center.distToSq(v) for v in nodes),n)

		lengths=[]

		for n in xrange(triind.n()):
			center=centers.getAt(n)
			norm=norms.getAt(n)
			ray=Ray(center,-norm)

			intres=ray.intersectsTriMesh(trinodes,triind,centers,radii2,1,n)

			if len(intres)>0:
				lengths.append(intres[0][1])

		avglen=avgDevRange(lengths,stddevRange)

		results.append((int(triind.getName().split('_')[2]),avglen))

	return results


@timing
def calculateRegionThicknesses(datasetlist,elemvals,choosevals,stddevRange=1.0,task=None):
	'''
	Computes the region thicknesses for each mesh defines by the list of datasets in `datasetlist'. The value list
	`choosevals' defines the region numbers of interest, and `elemvals' is a field which labels each element of the
	mesh with a number; each value of `choosevals' must be found in this set of labels. For each dataset, the resulting
	list will contain a list of thickness values, one for each label in `choosevals'. Assuming the datasets represent
	a moving mesh in time, the rows of the returned matrix represent thickness in time, and the columns represent the
	thicknesses for each region.
	'''
	results=[]
	regionmap=dict((v,i) for i,v in enumerate(choosevals)) # maps region # to index in `choosevals'

	trids,indlist,triindlist=divideMeshSurfaceByElemVal(datasetlist[0],elemvals,choosevals,None)

	if task:
		task.setMaxProgress(len(datasetlist))

	for count,dataset in enumerate(datasetlist):
		if task:
			task.setProgress(count+1)

		nodes=dataset.getNodes()
		sumlens=sum(tris.n() for tris in triindlist)
		proccount=chooseProcCount(sumlens,0,2000)
		shareMatrices(*(triindlist+[nodes]))
		thicknesses=calculateRegionThicknessesRange(sumlens,proccount,None,nodes,stddevRange,triindlist,partitionArgs=(triindlist,))

		thicknesslist=[v for i,v in sorted(listSum(thicknesses.values()))] # in same order as `choosevals'

		thicknessfield=RealMatrix('RegionThickness',elemvals.n())
		thicknessfield.meta(StdProps._spatial,elemvals.meta(StdProps._spatial))
		thicknessfield.meta(StdProps._topology,elemvals.meta(StdProps._topology))
		thicknessfield.meta(StdProps._elemdata,'True')
		thicknessfield.fill(0)

		for n in xrange(elemvals.n()):
			region=regionmap.get(int(elemvals.getAt(n)),-1)
			if region>=0:
				thicknessfield.setAt(thicknesslist[region],n)

		dataset.setDataField(thicknessfield)

		results.append(thicknesslist)

	return results


@concurrent
def calculateAvgDisplacementRange(process,orignodes,trinodes,stddevRange,triindlist):
	results=[]
	for triind in triindlist:
		allinds=set()

		for n in xrange(triind.n()):
			allinds.update(triind.getRow(n))

		lengths=[orignodes.getAt(i).distTo(trinodes.getAt(i)) for i in allinds]
		avglen=avgDevRange(lengths,stddevRange)

		results.append((int(triind.getName().split('_')[2]),avglen))

	return results


@timing
def calculateAvgDisplacement(datasetlist,elemvals,choosevals,stddevRange=1.0,task=None):
	results=[]
	orignodes=None
	trids,indlist,triindlist=divideMeshSurfaceByElemVal(datasetlist[0],elemvals,choosevals,None)

	regionmap=dict((v,i) for i,v in enumerate(choosevals)) # maps region # to index in `choosevals'

	if task:
		task.setMaxProgress(len(datasetlist))

	for count,dataset in enumerate(datasetlist):
		if task:
			task.setProgress(count+1)

		nodes=dataset.getNodes()
		orignodes=orignodes or nodes
		sumlens=sum(tris.n() for tris in triindlist)
		proccount=chooseProcCount(sumlens,0,2000)
		shareMatrices(*(triindlist+[nodes]))
		dists=calculateAvgDisplacementRange(sumlens,proccount,None,orignodes,nodes,stddevRange,triindlist,partitionArgs=(triindlist,))

		displist=[v for i,v in sorted(listSum(dists.values()))]

		dispfield=RealMatrix('RegionDisplacement',elemvals.n())
		dispfield.meta(StdProps._spatial,elemvals.meta(StdProps._spatial))
		dispfield.meta(StdProps._topology,elemvals.meta(StdProps._topology))
		dispfield.meta(StdProps._elemdata,'True')
		dispfield.fill(0)

		for n in xrange(elemvals.n()):
			region=regionmap.get(int(elemvals.getAt(n)),-1)
			if region>=0:
				dispfield.setAt(displist[region],n)

		dataset.setDataField(dispfield)

		results.append(displist)

	return results


@concurrent
def calculateLinTetVolumeRange(process,nodelist,fieldlist,inds,elemvals,choosevals):
	results=[]
	counter=1
	
	for nodes,volfield in zip(nodelist,fieldlist):
		process.setProgress(counter)
		counter+=1
		
		nodevols=dict((cv,0) for cv in choosevals)
		for n in xrange(inds.n()):
			val=elemvals.getAt(n)
			if val in nodevols:
				elemnodes=nodes.mapIndexRow(inds,n)
				vol=calculateTetVolume(*elemnodes)
				nodevols[val]+=abs(vol)
#				volfield.setAt(vol,n)

		results.append([nodevols[cv] for cv in choosevals])

		for n in xrange(inds.n()):
			volfield.setAt(nodevols.get(elemvals.getAt(n),0),n)

	return results


@timing
def calculateLinTetVolume(datasetlist,elemvals,choosevals,task=None):
	nodelist=[ds.getNodes() for ds in datasetlist]
	inds=datasetlist[0].getIndexSet(elemvals.meta(StdProps._spatial)) #or first(datasetlist[0].enumIndexSets())

	assert inds,'Cannot find index set with name %r'%elemvals.meta(StdProps._spatial)
	assert inds.n()>0
	shareMatrices(inds,elemvals)
	shareMatrices(*nodelist)

	fieldlist=[RealMatrix('volumes',inds.n(),1,True) for i in xrange(len(nodelist))]

	for ds,f in zip(datasetlist,fieldlist):
		ds.setDataField(f)
		f.meta(StdProps._topology,inds.getName())
		f.meta(StdProps._spatial,inds.getName())

	results=calculateLinTetVolumeRange(len(nodelist),0,task,nodelist,fieldlist,inds,elemvals,choosevals,partitionArgs=(nodelist,fieldlist))
	
	return listSum(results[p] for p in sorted(results))


class CardiacMotionPropWidget(QtGui.QWidget,Ui_CardiacMotionProp):
	def __init__(self,parent=None):
		QtGui.QWidget.__init__(self,parent)
		self.setupUi(self)
		tb=self.toolBox
		tb.setCurrentIndex(0)
		# make the toolbox large enough for the current pane
		tb.currentChanged.connect(lambda i:tb.setMinimumHeight(tb.currentWidget().height()+tb.count()*30))
		tb.currentChanged.emit(0)


ConfigNames=enum(
	'savecheart',
	'shortaxis','templateimg','saxseg','saxtimereg','regsubject','regintermed', # alignment/registration names
	'tagged3d','detagged3d', # 3D tag values
	'serveraddr','serverport','jobids','trackedimg','maskimg','adaptive','paramfile', # server values
	'heartrateBPM' # stored properties
)


class CardiacMotionProject(Project):
	def __init__(self,name,parentdir,mgr):
		Project.__init__(self,name,parentdir,mgr)
		self.addHandlers()
		self.CardiacMotion=mgr.getPlugin('CardiacMotion')
		self.ReportCard=mgr.getPlugin('ReportCard')
		self.CardiacMotion.project=self
		self.header='\nCardiacMotion.createProject(%r,scriptdir+"/..")\n' %(self.name)
		self.alignprop=None
		self.numUnknownJobs=0
		self.reportcard=None

		for n in ConfigNames:
			self.configMap[n[0]]=''

		self.configMap[ConfigNames._serverport]=15000
		self.configMap[ConfigNames._serveraddr]='localhost'
		self.configMap[ConfigNames._adaptive]=0.9
		self.configMap[ConfigNames._jobids]=[]
		self.configMap[ConfigNames._paramfile]=self.CardiacMotion.patient1e4

		for o in list(mgr.enumSceneObjects()):
			mgr.removeSceneObject(o)

		self.logdir=self.getProjectFile('logs')
		self.backDir=self.logdir
		
	def create(self):
		'''Task routine set to run after the project is loaded which does extra setup or config operations.'''
		Project.create(self)
		
		if not os.path.isdir(self.logdir):
			os.mkdir(self.logdir)

		reportcardfile=self.getProjectFile(self.name+'.report')
		if not os.path.exists(reportcardfile):
			self.reportcard=self.ReportCard.createReportCard(self.name,reportcardfile)
			self.reportcard.save()
			self.mgr.addSceneObjectTask(self.reportcard)
			self.addObject(self.reportcard)
			self.save()
		else:
			pass
		
	def getPropBox(self):
		prop=Project.getPropBox(self)

		# remove the UI for changing the project location
		cppdel(prop.chooseLocLayout)
		cppdel(prop.dirButton)
		cppdel(prop.chooseLocLabel)
		
		self.alignprop=CardiacMotionPropWidget()
		prop.verticalLayout.insertWidget(prop.verticalLayout.count()-1,self.alignprop)

		self.alignprop.loadCineButton.clicked.connect(self._loadCineSeries)
		self.alignprop.morphoButton.clicked.connect(self._loadMorphoSeries)
		self.alignprop.loadNiftiButton.clicked.connect(self._loadNiftiFile)
		self.alignprop.loadMetaButton.clicked.connect(self._loadMetaFile)
		self.alignprop.loadVTKMeshButton.clicked.connect(self._loadVTKFile)
		self.alignprop.loadCHeartButton.clicked.connect(self._loadCHeartFiles)
		self.alignprop.magphaseButton.clicked.connect(self._loadMagFlow)
		
		self.alignprop.saveCHeartCheck.clicked.connect(self.updateConfigFromProp)

#		self.alignprop.alignCheckButton.clicked.connect(lambda:self.CardiacMotion.checkLongAxisAlign(str(self.alignprop.alignCheckBox.currentText()),str(self.alignprop.checkTargetBox.currentText())))

		self.alignprop.shortAxisBox.activated.connect(self.updateConfigFromProp)
		self.alignprop.saxsegBox.activated.connect(self.updateConfigFromProp)
		self.alignprop.templateBox.activated.connect(self.updateConfigFromProp)
		self.alignprop.regSubBox.activated.connect(self.updateConfigFromProp)
		self.alignprop.regInterBox.activated.connect(self.updateConfigFromProp)
		self.alignprop.trackedBox.activated.connect(self.updateConfigFromProp)
		self.alignprop.maskBox.activated.connect(self.updateConfigFromProp)

		self.alignprop.svrAddrBox.textChanged.connect(self.updateConfigFromProp)
		#self.alignprop.paramEdit.textChanged.connect(self.updateConfigFromProp)

		self.alignprop.mCropButton.clicked.connect(self._cropSeries)
		self.alignprop.alignButton.clicked.connect(self._alignButton)
#		self.alignprop.createTimeRegButton.clicked.connect(self._createTimeRegButton)
		self.alignprop.createSegButton.clicked.connect(self._createSegButton)
		self.alignprop.regButton.clicked.connect(self._rigidRegButton)
		self.alignprop.loadTagButton.clicked.connect(self._load3DTagSeries)
		self.alignprop.chooseParamButton.clicked.connect(self._chooseParamFile)
		self.alignprop.chooseNRegParamButton.clicked.connect(self._chooseNRegParamFile)
		self.alignprop.startButton.clicked.connect(self._startMotionJob)
		self.alignprop.startNregButton.clicked.connect(self._startNregMotion)
		self.alignprop.checkButton.clicked.connect(lambda:self._checkMotionJob())
		self.alignprop.killButton.clicked.connect(self._killJob)
		self.alignprop.tsOrderButton.clicked.connect(self._invertOrder)
		self.alignprop.tsSetButton.clicked.connect(self._setTimestep)
		self.alignprop.addOffsetButton.clicked.connect(self._offsetTimestep)
		self.alignprop.reorderButton.clicked.connect(self._reorderMulticycle)
		self.alignprop.prospectButton.clicked.connect(self._prospTimestep)
		self.alignprop.applyTrackButton.clicked.connect(self._applyTrackButton)
		self.alignprop.gridButton.clicked.connect(self._createGridButton)
		self.alignprop.resampleButton.clicked.connect(self._resampleImage)
		self.alignprop.tsExtrButton.clicked.connect(self._extractTimesteps)
		self.alignprop.isoCreateButton.clicked.connect(self._createIsoImage)
		self.alignprop.bbCropButton.clicked.connect(self._cropBoundBox)
		self.alignprop.emptyCropButton.clicked.connect(self._cropEmpty)
		self.alignprop.thicknessButton.clicked.connect(self._calculateThicknessButton)
		self.alignprop.avgdispButton.clicked.connect(self._calculateAvgDispButton)
		self.alignprop.volButton.clicked.connect(self._calculateVolumeButton)
		self.alignprop.strainButton.clicked.connect(self._calculateStrainButton)
		self.alignprop.strainMeshButton.clicked.connect(self._calculateStrainMeshButton)

		self.alignprop.keCalcButton.clicked.connect(self._calculateKineticEnergyButton)

		self.alignprop.isTagCheck.stateChanged.connect(lambda i:self._tagCheckBox(self.alignprop.isTagCheck.isChecked()))

		def fillFieldBox(objbox,fieldbox,allowNone=False):
			def fillAction(*args):
				obj=self.getProjectObj(str(objbox.currentText()))
				fields=['None'] if allowNone else []
				fields+=sorted(obj.datasets[0].fields.keys()) if obj else ['None']
				fillList(fieldbox,fields)

			objbox.currentIndexChanged.connect(fillAction)

		fillFieldBox(self.alignprop.thickMeshBox,self.alignprop.thickFieldBox)
		fillFieldBox(self.alignprop.dispMeshBox,self.alignprop.dispFieldBox)
		fillFieldBox(self.alignprop.volMeshBox,self.alignprop.volFieldBox)

		fillFieldBox(self.alignprop.strainMeshBox,self.alignprop.strainMeshAHABox)

		#fillList(self.alignprop.interpTypeBox,['None']+[i.replace('_',' ') for i,j in InterpTypes])

		setCollapsibleGroupbox(self.alignprop.trackAdvBox,False)
		setWarningStylesheet(self.alignprop.trackAdvBox)

		def _fillTS(i=None):
			o=self.mgr.findObject(str(self.alignprop.tsExtrSrcBox.currentText()))
			if o:
				fillList(self.alignprop.tsExtrChooseBox,['Step %i @ Time %i'%its for its in enumerate(o.getTimestepList())])

		self.alignprop.tsExtrSrcBox.activated.connect(_fillTS)

		return prop

	def updatePropBox(self,proj,prop):
		Project.updatePropBox(self,proj,prop)
		
		setChecked(self.configMap[ConfigNames._savecheart].lower()=='true',self.alignprop.saveCHeartCheck)

		sceneimgs=filter(lambda o:isinstance(o,ImageSceneObject),self.memberObjs)
		scenemeshes=filter(lambda o:isinstance(o,MeshSceneObject),self.memberObjs)

		names=sorted(o.getName() for o in sceneimgs)
		fillList(self.alignprop.regList,names)
		fillList(self.alignprop.manipImgBox,names)
		fillList(self.alignprop.bbCropSrcBox,names)
		fillList(self.alignprop.bbCropRefBox,names)
		fillList(self.alignprop.emptyCropImgBox,names)
		fillList(self.alignprop.strainImgBox,names)
		fillList(self.alignprop.resampleSrcBox,names)
		fillList(self.alignprop.resampleTmpltBox,names)

		names=sorted(o.getName() for o in sceneimgs if o.isTimeDependent)
		fillList(self.alignprop.mCropSeriesBox,names)
		fillList(self.alignprop.trackSrcBox,names,defaultitem='None')
		fillList(self.alignprop.regInterBox,names,self.configMap[ConfigNames._regintermed],'None')
		fillList(self.alignprop.tsExtrSrcBox,names)

		names=sorted(o.getName() for o in sceneimgs if o.isTimeDependent and len(o.getTimestepList())==2)
		fillList(self.alignprop.reorderSrcBox,names)

#		names=sorted(o.getName() for o in sceneimgs if o.is2D)
#		fillList(self.alignprop.alignCheckBox,names)

		names=sorted(o.getName() for o in sceneimgs if not o.is2D)
		fillList(self.alignprop.shortAxisBox,names,self.configMap[ConfigNames._shortaxis])
		fillList(self.alignprop.templateBox,names,self.configMap[ConfigNames._templateimg],'None')
		fillList(self.alignprop.trackedBox,names,self.configMap[ConfigNames._trackedimg])
		fillList(self.alignprop.maskBox,names,self.configMap[ConfigNames._maskimg],'None')
		fillList(self.alignprop.regSubBox,names,self.configMap[ConfigNames._regsubject])
#		fillList(self.alignprop.checkTargetBox,names)
		fillList(self.alignprop.gridImgBox,names)
		fillList(self.alignprop.isoCreateBox,names)
		fillList(self.alignprop.strainROIBox,names)
		fillList(self.alignprop.trackedNregBox,names)
		fillList(self.alignprop.maskNregBox,names,defaultitem='None')
		fillList(self.alignprop.strainSrcBox,names,defaultitem='None')

		fillList(self.alignprop.keMaskBox,names)
		fillList(self.alignprop.phaseXBox,names)
		fillList(self.alignprop.phaseYBox,names)
		fillList(self.alignprop.phaseZBox,names)

		names+=sorted(o.getName() for o in self.memberObjs if isinstance(o,SegSceneObject) and o.numContours()>1)
		fillList(self.alignprop.saxsegBox,names,self.configMap[ConfigNames._saxseg])

		names=sorted(o.getName() for o in sceneimgs+scenemeshes)
		fillList(self.alignprop.trackObjBox,names)

		names=sorted(o.getName() for o in scenemeshes)
		fillList(self.alignprop.thickMeshBox,names)

		names=sorted(o.getName() for o in scenemeshes if len(o.datasets)>1)
		fillList(self.alignprop.strainMeshBox,names)
		fillList(self.alignprop.dispMeshBox,names)
		fillList(self.alignprop.volMeshBox,names)

		names=sorted(o.getName() for o in sceneimgs+scenemeshes if len(o.getTimestepList())>1)
		fillList(self.alignprop.tsSetObjBox,names)

		# make the field boxes repopulate themselves
		self.alignprop.thickMeshBox.currentIndexChanged.emit(self.alignprop.thickMeshBox.currentIndex())
		self.alignprop.dispMeshBox.currentIndexChanged.emit(self.alignprop.dispMeshBox.currentIndex())
		self.alignprop.volMeshBox.currentIndexChanged.emit(self.alignprop.volMeshBox.currentIndex())
		self.alignprop.strainMeshBox.currentIndexChanged.emit(self.alignprop.strainMeshBox.currentIndex())

		trackdirs=map(os.path.basename,self.CardiacMotion.getTrackingDirs())
		fillList(self.alignprop.trackDataBox,trackdirs)
		fillList(self.alignprop.strainTrackBox,trackdirs)
		fillList(self.alignprop.strainMeshTrackBox,trackdirs)
		
		heartrate=self.configMap[ConfigNames._heartrateBPM]
		if heartrate and self.alignprop.bpmBox.value()==0:
			self.alignprop.bpmBox.setValue(heartrate)

		# server box values
		with signalBlocker(self.alignprop.adaptBox,self.alignprop.svrAddrBox,self.alignprop.paramEdit):
			self.alignprop.adaptBox.setValue(self.configMap[ConfigNames._adaptive])
			self.alignprop.svrAddrBox.setText('%s:%i'%(self.configMap[ConfigNames._serveraddr],int(self.configMap[ConfigNames._serverport])))
			self.alignprop.paramEdit.setText(self.configMap[ConfigNames._paramfile])

		self.alignprop.tsExtrSrcBox.activated.emit(0)

	def updateConfigFromProp(self,*args):
		'''Read data into self.configMap from the UI.'''
		self.configMap[ConfigNames._shortaxis]=str(self.alignprop.shortAxisBox.currentText())
		self.configMap[ConfigNames._saxseg]=str(self.alignprop.saxsegBox.currentText())
		self.configMap[ConfigNames._templateimg]=str(self.alignprop.templateBox.currentText())
		self.configMap[ConfigNames._regsubject]=str(self.alignprop.regSubBox.currentText())
		self.configMap[ConfigNames._regintermed]=str(self.alignprop.regInterBox.currentText())
		self.configMap[ConfigNames._trackedimg]=str(self.alignprop.trackedBox.currentText())
		self.configMap[ConfigNames._maskimg]=str(self.alignprop.maskBox.currentText())
		self.configMap[ConfigNames._adaptive]=self.alignprop.adaptBox.value()
		self.configMap[ConfigNames._paramfile]=str(self.alignprop.paramEdit.text())
		self.configMap[ConfigNames._savecheart]=str(self.alignprop.saveCHeartCheck.isChecked())

		style=''
		try: # try to read the address and port correctly, any exceptions will be from bad formatting so change nothing in that case
			addr,port=str(self.alignprop.svrAddrBox.text()).split(':')
			port=int(port)
			addr=addr.strip()
			if port!=self.configMap[ConfigNames._serverport] or addr!=self.configMap[ConfigNames._serveraddr]:
				self.configMap[ConfigNames._serverport]=port
				self.configMap[ConfigNames._serveraddr]=addr
				self.saveConfig()
		except:
			style='color: rgb(255,0,0)'

		self.alignprop.svrAddrBox.setStyleSheet(style)
		
	def _readDicomHeartRate(self,series):
		heartrate=readDicomHeartRate(series)		
		if heartrate is not None and not self.configMap[ConfigNames._heartrateBPM]:
			self.configMap[ConfigNames._heartrateBPM]=int(heartrate)
			
			rc=self.getReportCard()
			if rc:
				rc.setValue(series.seriesID,'Heart Rate (bpm)',heartrate)

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
		
	def getReportCard(self):
		return first(obj for obj in self.memberObjs if obj.getName()==self.name and isinstance(obj,ReportCardSceneObject))

	def checkIncludeObject(self,obj):
		'''Check whether the given object should be added to the project or not.'''
		# if this isn't a scene object, ignore
		if not isinstance(obj,SceneObject) or obj in self.memberObjs:
			return

#		# ignore if this isn't a mesh or image and we can't save it to a file
#		if not isinstance(obj,(MeshSceneObject,ImageSceneObject)) and not obj.plugin.getObjFiles(obj):
#			return
			
		# ignore if this isn't a mesh or image
		if not isinstance(obj,(MeshSceneObject,ImageSceneObject)):
			return

		pdir=self.getProjectDir()
		files=map(os.path.abspath,obj.plugin.getObjFiles(obj) or [])

		@taskroutine('Adding Object to Project')
		def _copy(task=None):
			newname=getValidFilename(obj.getName())
			self.mgr.renameSceneObject(obj,newname)
			filename=self.getProjectFile(obj.getName())
			
			if isinstance(obj,ImageSceneObject):
				self.CardiacMotion.saveToNifti([obj],True)
			elif isinstance(obj,MeshSceneObject):
				savecheart=self.configMap[ConfigNames._savecheart].lower()=='true'
				if savecheart:
					self.CardiacMotion.CHeart.saveObject(obj,filename,setFilenames=True)
				else:
					self.CardiacMotion.VTK.saveObject(obj,filename,setFilenames=True)

			Project.addObject(self,obj)

			self.save()

		if not files or any(not f.startswith(pdir) for f in files):
			msg="Do you want to add %r to the project? This requires saving/copying the object's file data into the project directory."%(obj.getName())
			self.mgr.win.chooseYesNoDialog(msg,'Adding Object',lambda:self.mgr.addTasks(_copy()))
			
	def _checkTrackDirs(self):
		# all directories containing dof files
		dirs=[d for d in glob(self.getProjectFile('*/')) if glob(os.path.join(d,'*.dof.gz'))]

		sceneimgs=[o.getName() for o in self.memberObjs if isinstance(o,ImageSceneObject)]
		
		for d in dirs:
			jfile=os.path.join(d,'job.ini')
			if os.path.isfile(jfile):
				jdata=readBasicConfig(jfile)

	def _loadNiftiFile(self):
		filenames=self.mgr.win.chooseFileDialog('Choose NIfTI filename',filterstr='NIfTI Files (*.nii *.nii.gz)',chooseMultiple=True)
		if len(filenames)>0:
			self.CardiacMotion.loadNiftiFiles(filenames)

	def _loadMetaFile(self):
		filenames=self.mgr.win.chooseFileDialog('Choose MetaImage Header filename',filterstr='Header Files (*.mhd *.mha)',chooseMultiple=True)
		if len(filenames)>0:
			self.CardiacMotion.loadMetaFiles(filenames)

	def _alignButton(self):
		saxname=self.configMap[ConfigNames._shortaxis]
		segname=self.configMap[ConfigNames._saxseg]
		templatename=self.configMap[ConfigNames._templateimg]
#		timeregname=self.configMap[ConfigNames._saxtimereg]

		if templatename=='None':
			templatename=None

		if saxname=='':
			self.mgr.showMsg('A short axis stack must be loaded first.','Cannot Perform Alignment')
		elif segname=='':
			self.mgr.showMsg('A segmentation must be loaded first.','Cannot Perform Alignment')
		else:
			self.CardiacMotion.alignShortStack(saxname,segname,templatename)#,timeregname)

#	def _createTimeRegButton(self):
#		template=self.getProjectObj(self.configMap[ConfigNames._templateimg])
#		if not template or template=='None':
#			self.mgr.showMsg('No template image specified so nothing to time-register to.','Cannot Perform Operation')
#		else:
#			sax=self.getProjectObj(self.configMap[ConfigNames._shortaxis])
#			regobj=self.CardiacMotion.createTimeRegStack(template,sax)
#
#			self.mgr.addFuncTask(lambda:self.configMap.update({ConfigNames._saxtimereg:regobj().getName()}))

	def _createSegButton(self):
		saxname=self.configMap[ConfigNames._shortaxis]
#		timeregname=self.configMap[ConfigNames._saxtimereg]

		if not saxname: # and not timeregname:
			self.mgr.showMsg('A short axis stack must be loaded first.','Cannot Create Segmentation')
		else:
			self.CardiacMotion.createSegObject(saxname,SegmentTypes.LV)

	def _rigidRegButton(self):
		regnames=[str(i.text()) for i in self.alignprop.regList.selectedItems()]
		if len(regnames)>0:
			self.CardiacMotion.rigidRegisterStackList(self.configMap[ConfigNames._regsubject],self.configMap[ConfigNames._regintermed],regnames)

	def _cropSeries(self):
		seriesname=str(self.alignprop.mCropSeriesBox.currentText())
		threshold=self.alignprop.cropThresholdBox.value()
		self.CardiacMotion.motionCropObject(seriesname,threshold)

	def _cropBoundBox(self):
		srcname=str(self.alignprop.bbCropSrcBox.currentText())
		refname=str(self.alignprop.bbCropRefBox.currentText())
		mx=self.alignprop.bbXBox.value()
		my=self.alignprop.bbYBox.value()

		self.CardiacMotion.refImageCrop(srcname,refname,mx,my)

	def _cropEmpty(self):
		srcname=str(self.alignprop.emptyCropImgBox.currentText())
		self.CardiacMotion.emptyCropObject(srcname)

	def _loadCineSeries(self):
		series=self.CardiacMotion.Dicom.openChooseSeriesDialog(subject='CINE')
		if len(series)>0:
			objs=[self.CardiacMotion.Dicom.loadSeries(s) for s in series]
			self._readDicomHeartRate(series[0])
			filenames=self.CardiacMotion.saveToNifti(objs)
			self.CardiacMotion.loadNiftiFiles(filenames)

	def _loadMorphoSeries(self):
		param=ParamDef('tsOffset','Timestep Offset',ParamType._int,40,-300,300,10)
		results={}

		series=self.CardiacMotion.Dicom.openChooseSeriesDialog(allowMultiple=False,params=([param],lambda n,v:results.update({n:v})),subject='Morphology')
		if len(series)>0:
			ts=results.get('tsOffset',40)
			suffix='_offset%i'%ts

			sobj=self.CardiacMotion.Dicom.loadSeries(series[0])
			self._readDicomHeartRate(series[0])
			filenames=self.CardiacMotion.saveToNifti([sobj])
			obj=self.CardiacMotion.loadNiftiFiles(filenames)
			self.mgr.addFuncTask(lambda:self.CardiacMotion.offsetTimesteps(obj()[0],suffix,ts))

	def _load3DTagSeries(self):
		params=[
			ParamDef('makeProspective','Prospective Timing',ParamType._bool,True),
			ParamDef('makeDetag','Make Detagged Image',ParamType._bool,True),
			ParamDef('loadPlanes','Include Plane-aligned Images',ParamType._bool,False)
		]
		results={}
		series=self.CardiacMotion.Dicom.openChooseSeriesDialog(allowMultiple=False,params=(params,lambda n,v:results.update({n:v})),subject='3D Tag')

		if len(series)>0:
			obj=self.CardiacMotion.Dicom.loadSeries(series[0])
			self._readDicomHeartRate(series[0])
			makeProspective=results.get('makeProspective',True)
			loadPlanes=results.get('loadPlanes',False)
			makeDetag=results.get('makeDetag',True)

			f=self.CardiacMotion.load3DTagSeries(obj,makeProspective,loadPlanes,makeDetag)
			self.mgr.checkFutureResult(f)

	def _loadMagFlow(self):
		filename=self.mgr.win.chooseFileDialog('Choose Par filename',filterstr='Par Files (*.par *.PAR)',chooseMultiple=False)
		if filename:
			self.CardiacMotion.loadMagPhaseParRec(filename)

	def _loadVTKFile(self):
		filename=self.mgr.win.chooseFileDialog('Choose VTK Mesh filename',filterstr='VTK Files (*.vtk *.vtu)',chooseMultiple=False)
		if filename:
			f=self.CardiacMotion.loadVTKFile(filename)
			self.mgr.checkFutureResult(f)

	def _loadCHeartFiles(self):
		d=LoadDialog(self.mgr)
		params=d.getParams()

		if params:
			self.CardiacMotion.loadCHeartMesh(*params)
			
	def _setTimestep(self):
		objname=str(self.alignprop.tsSetObjBox.currentText())
		start=self.alignprop.tsStartBox.value()
		step=self.alignprop.tsStepBox.value()
		
		if objname:
			self.CardiacMotion.setObjectTimestep(objname,start,step)

	def _invertOrder(self):
		manipname=str(self.alignprop.manipImgBox.currentText())
		msg='This operation will invert the order of timesteps for this image, are you sure?'
		if manipname:
			self.mgr.win.chooseYesNoDialog(msg,'Timestep Ordering',lambda:self.CardiacMotion.invertTimesteps(manipname))

	def _offsetTimestep(self):
		offsetname=str(self.alignprop.manipImgBox.currentText())
		ts=self.alignprop.offsetBox.value()
		suffix='_offset%i'%ts
		msg='This operation will add the given value to the timesteps for this image, are you sure?'
		if offsetname:
			self.mgr.win.chooseYesNoDialog(msg,'Timestep Ordering',lambda:self.CardiacMotion.offsetTimesteps(offsetname,suffix,ts))

	def _prospTimestep(self):
		offsetname=str(self.alignprop.manipImgBox.currentText())
		msg='This operation will convert the timesteps for this image into prospective times, are you sure?'
		if offsetname:
			self.mgr.win.chooseYesNoDialog(msg,'Timestep Ordering',lambda:self.CardiacMotion.offsetTimesteps(offsetname,'_prospective',0,True))

	def _reorderMulticycle(self):
		name=str(self.alignprop.reorderSrcBox.currentText())
		self.CardiacMotion.reorderMulticycleImage(name,self.imgalignprop.reorderStartBox.value(),self.imgalignprop.reorderStepBox.value())

	def _chooseParamFile(self):
		filename=self.mgr.win.chooseFileDialog('Choose Parameter file')
		if filename:
			self.alignprop.paramEdit.setText(filename)
			self.configMap[ConfigNames._paramfile]=filename
			self.saveConfig()

	def _chooseNRegParamFile(self):
		filename=self.mgr.win.chooseFileDialog('Choose Parameter file')
		if filename:
			self.alignprop.paramNRegEdit.setText(filename)

	def _startMotionJob(self):
		self.updateConfigFromProp()
		trackimg=self.configMap[ConfigNames._trackedimg]
		maskimg=self.configMap[ConfigNames._maskimg]
		adaptive=self.configMap[ConfigNames._adaptive]
		paramfile=self.configMap[ConfigNames._paramfile]
		dirname=str(self.alignprop.trackDirEdit.text())
		isTagCheck=self.alignprop.isTagCheck.isChecked()

		if not os.path.isfile(paramfile):
			self.mgr.showMsg('Cannot file param file %r, using default file'%paramfile,'File Not Found')
			paramfile=self.CardiacMotion.patient1e6 if isTagCheck else self.CardiacMotion.patient1e4
			self.configMap[ConfigNames._paramfile]=paramfile

		if 'tagged' in trackimg and not isTagCheck:
			self.mgr.showMsg('Warning: IRTK will treat this image as tagged data since "tagged" is in the name, but the tagged image check is not selected','Warning')

		if maskimg in ('','None'):
			maskimg=None

		response=self.CardiacMotion.startMotionTrackJob(trackimg,maskimg,dirname,adaptive,paramfile)

		@taskroutine('Checking Motion Track Job')
		def _checkJob(task):
			name,msg=Future.get(response)

			assert name in (ServerMsgs._Except,ServerMsgs._RStart)

			if name==ServerMsgs._Except:
				self.mgr.showExcept(msg[1],'MotionTrackServer reported an exception when sending a job','Exception from Server')
			else:
				jid=msg[0]
				self.configMap[ConfigNames._jobids].append(jid)
				self.saveConfig()

		self.mgr.runTasks(_checkJob())
		self._checkMotionJob(False)

	def _checkMotionJob(self,checkActive=True):
		jids=self.configMap[ConfigNames._jobids]
		assert jids!=None

		if checkActive and not self.CardiacMotion.isServerAlive():
			self.mgr.callThreadSafe(fillList,self.alignprop.jobList,['MotionTrackServer not active.'])
			#self.mgr.showMsg('MotionTrackServer not active.','Server Check',False)
		else:
			@self.mgr.addFuncTask
			def _updateList():
				msgs,deadjobs=self.CardiacMotion.checkMotionTrackJobs(jids)
				self.mgr.callThreadSafe(fillList,self.alignprop.jobList,msgs)
				self.numUnknownJobs=len(deadjobs)
				for d in deadjobs:
					self.configMap[ConfigNames._jobids].remove(d)

				self.saveConfig()

	def _startNregMotion(self):
		imgname=str(self.alignprop.trackedNregBox.currentText())
		maskname=str(self.alignprop.maskNregBox.currentText())
		trackname=str(self.alignprop.trackingNregName.text())
		paramfile=str(self.alignprop.paramNRegEdit.text())
		f=self.CardiacMotion.startGPUNRegMotionTrack(imgname,maskname,trackname,paramfile)
		self.mgr.checkFutureResult(f)

	def _killJob(self):
		ind=self.alignprop.jobList.currentRow()
		if ind>=0 and self.CardiacMotion.isServerAlive():
			def _killSelected():
				jid=self.configMap[ConfigNames._jobids][ind-self.numUnknownJobs]
				name,msg=self.CardiacMotion.sendServerMsg(ServerMsgs._Kill,(jid,))
				self._checkMotionJob()

			self.mgr.win.chooseYesNoDialog('Kill the selected running motion tracking job?','Kill',_killSelected)

	def _applyTrackButton(self):
		objname=str(self.alignprop.trackObjBox.currentText())
		srcname=str(self.alignprop.trackSrcBox.currentText())
		trackname=str(self.alignprop.trackDataBox.currentText())
		isFrameByFrame=self.alignprop.framebyframeCheck.isChecked()

		if srcname=='None':
			srcname=None

		f=self.CardiacMotion.applyMotionTrack(objname,srcname,trackname,isFrameByFrame)
		self.mgr.checkFutureResult(f)

	def _resampleImage(self):
		objname=str(self.alignprop.resampleSrcBox.currentText())
		tmpltname=str(self.alignprop.resampleTmpltBox.currentText())
		isIso=self.alignprop.resampleIsoCheck.isChecked()
		f=self.CardiacMotion.resampleObject(objname,tmpltname,isIso)
		self.mgr.checkFutureResult(f)

	def _extractTimesteps(self):
		objname=str(self.alignprop.tsExtrSrcBox.currentText())
		self.CardiacMotion.extractTimestepsToObject(objname,[self.alignprop.tsExtrChooseBox.currentIndex()])

	def _createGridButton(self):
		name=str(self.alignprop.gridImgBox.currentText())
		self.CardiacMotion.createImageGrid(name,self.alignprop.gridW.value(),self.alignprop.gridH.value(),self.alignprop.gridD.value())

	def _createIsoImage(self):
		name=str(self.alignprop.isoCreateBox.currentText())
		#shapetype=str(self.alignprop.interpTypeBox.currentText())
		cropEmpty=self.alignprop.emptyCropBox.isChecked()

		#if cropEmpty:
		#	name=self.CardiacMotion.emptyCropObject(name,False)

		f=self.CardiacMotion.createIsotropicObject(name,cropEmpty)
		self.mgr.checkFutureResult(f)

	def _calculateThicknessButton(self):
		objname=str(self.alignprop.thickMeshBox.currentText())
		fieldname=str(self.alignprop.thickFieldBox.currentText())
		percentThickness=self.alignprop.percentThickBox.isChecked()
		self.CardiacMotion.calculateMeshRegionThickness(objname,fieldname,percentThickness)

	def _calculateAvgDispButton(self):
		objname=str(self.alignprop.dispMeshBox.currentText())
		fieldname=str(self.alignprop.dispFieldBox.currentText())
		self.CardiacMotion.calculateMeshRegionAvgDisp(objname,fieldname)

	def _calculateVolumeButton(self):
		objname=str(self.alignprop.volMeshBox.currentText())
		fieldname=str(self.alignprop.volFieldBox.currentText())
		heartrate=self.alignprop.bpmBox.value()
		f=self.CardiacMotion.calculateMeshRegionVolume(objname,fieldname,heartrate)
		self.mgr.checkFutureResult(f)

	def _calculateStrainButton(self):
		name=str(self.alignprop.strainROIBox.currentText())
		srcname=str(self.alignprop.strainSrcBox.currentText())
		spacing=self.alignprop.strainSpacingBox.value()
		trackname=str(self.alignprop.strainTrackBox.currentText())
		griddims=(self.alignprop.strainWBox.value(),self.alignprop.strainHBox.value(),self.alignprop.strainDBox.value())
		
		f=self.CardiacMotion.calculateImageStrainField(name,srcname,griddims,spacing,trackname)
		self.mgr.checkFutureResult(f)

	def _calculateStrainMeshButton(self):
		objname=str(self.alignprop.strainMeshBox.currentText())
		imgname=str(self.alignprop.strainImgBox.currentText())
		ahafieldname=str(self.alignprop.strainMeshAHABox.currentText())
		trackname=str(self.alignprop.strainMeshTrackBox.currentText())
		spacing=self.alignprop.strainSpacingMeshBox.value()
		
		f=self.CardiacMotion.calculateMeshStrainField(objname,imgname,ahafieldname,spacing,trackname)
		self.mgr.checkFutureResult(f)

	def _calculateKineticEnergyButton(self):
		maskname=str(self.alignprop.keMaskBox.currentText())
		phaseXname=str(self.alignprop.phaseXBox.currentText())
		phaseYname=str(self.alignprop.phaseYBox.currentText())
		phaseZname=str(self.alignprop.phaseZBox.currentText())
		self.CardiacMotion.calculatePhaseKineticEnergy(maskname,phaseXname,phaseYname,phaseZname)

	def _tagCheckBox(self,isChecked):
		paramfile=str(self.alignprop.paramEdit.text())
		p1e4=self.CardiacMotion.patient1e4
		p1e6=self.CardiacMotion.patient1e6
		if paramfile in (None,'','<<Use Default>>',p1e4,p1e6):
			paramfile=p1e6 if isChecked else p1e4
			self.alignprop.paramEdit.setText(paramfile)
			self.configMap[ConfigNames._paramfile]=paramfile
			self.saveConfig()



class CardiacMotionPlugin(ImageScenePlugin,IRTKPluginMixin):
	def __init__(self):
		ImageScenePlugin.__init__(self,'CardiacMotion')
		self.project=None

	def init(self,plugid,win,mgr):
		ImageScenePlugin.init(self,plugid,win,mgr)
		IRTKPluginMixin.init(self,plugid,win,mgr)
		self.ParRec=self.mgr.getPlugin('ParRec')
		if self.win!=None:
			self.win.addMenuItem('Project','CardMotionProj'+str(plugid),'&Cardiac Motion Project',self._newProjDialog)

	def createProject(self,name,parentdir):
		if self.mgr.project==None:
			self.mgr.createProjectObj(name,parentdir,CardiacMotionProject)

	def getCWD(self):
		return self.project.getProjectDir()

	def getLogFile(self,filename):
		return os.path.join(self.project.logdir,ensureExt(filename,'.log'))

	def getLocalFile(self,name):
		return self.project.getProjectFile(name)

	def addObject(self,obj):
		self.project.addObject(obj)
		if obj not in self.mgr.objs:
			self.mgr.addSceneObject(obj)
		self.project.save()

	def getServerAddrPort(self):
		addr=self.project.configMap[ConfigNames._serveraddr]
		port=self.project.configMap[ConfigNames._serverport]
		return addr,port

	def setServerAddrPort(self,addr,port):
		if addr!=None:
			self.project.configMap[ConfigNames._serveraddr]=addr
		if port!=None:
			self.project.configMap[ConfigNames._serverport]=port

		self.project.saveConfig()

	def _newProjDialog(self):
		def chooseProjDir(name):
			newdir=self.win.chooseDirDialog('Choose Project Root Directory')
			if len(newdir)>0:
				self.mgr.createProjectObj(name,newdir,CardiacMotionProject)

		self.win.chooseStrDialog('Choose Project Name','Project',chooseProjDir)

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
					if not filename.startswith(self.project.getProjectDir()):
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

				f.setObject(objs)

		return self.mgr.runTasks(_loadNifti(filenames),f)

	def loadMetaFiles(self,filenames):
		'''Same thing as loadNiftiFiles() just for MetaImage format.'''
		f=Future()
		@taskroutine('Loading Meta Files')
		def _loadMeta(filenames,task):
			with f:
				isEmpty=len(self.project.memberObjs)==0
				filenames=Future.get(filenames)
				objs=[]
				for filename in filenames:
					filename=os.path.abspath(filename)

					mobj=self.Meta.loadObject(filename)
					niftiname=self.getUniqueLocalFile(splitPathExt(filename)[1])+'.nii'
					self.Nifti.saveObject(mobj,niftiname)

					nobj=self.Nifti.loadObject(niftiname)
					self.project.addObject(nobj)
					self.mgr.addSceneObject(nobj)
					objs.append(nobj)

				if isEmpty:
					self.mgr.callThreadSafe(self.project.updateConfigFromProp)
					self.project.save()

				f.setObject(objs)

		return self.mgr.runTasks(_loadMeta(filenames),f)

	def loadCHeartMesh(self,xfile,tfile,elemtype):
		f=Future()
		@taskroutine('Loading CHeart Files')
		def _load(xfile,tfile,elemtype,task):
			with f:
				savecheart=self.project.configMap[ConfigNames._savecheart].lower()=='true'
				if savecheart:
					newxfile=self.project.getProjectFile(os.path.split(xfile)[1])
					copyfileSafe(xfile,newxfile,True)
					newtfile=self.project.getProjectFile(os.path.split(tfile)[1])
					copyfileSafe(tfile,newtfile,True)
		
					obj=self.CHeart.loadSceneObject(newxfile,newtfile,elemtype,objname=splitPathExt(xfile)[1])
				else:
					objname=splitPathExt(xfile)[1]
					obj=self.CHeart.loadSceneObject(xfile,tfile,elemtype,objname=objname)
					self.VTK.saveObject(obj,self.project.getProjectFile(objname),setFilenames=True)
					
				self.addObject(obj)
				f.setObject(obj)

		return self.mgr.runTasks(_load(xfile,tfile,elemtype),f)

	def loadVTKFile(self,filename,trans=transform()):
		f=Future()
		@taskroutine('Loading VTK')
		@timing
		def _load(filename,task):
			with f:
				basename=self.getUniqueObjName(splitPathExt(filename)[1])
				vobj=self.VTK.loadFile(filename)
				vobj.datasets[0].getNodes().mul(trans)
				
				savecheart=self.project.configMap[ConfigNames._savecheart].lower()=='true'
				
				if savecheart:
					self.CHeart.saveObject(vobj,self.getLocalFile(basename),setFilenames=True)
				else:
					vobj.plugin.copyObjFiles(vobj,self.getLocalFile('.'))
					
				self.addObject(vobj)
				f.setObject(vobj)

		return self.mgr.runTasks(_load(filename),f)

	def loadMagPhaseParRec(self,filename):
		f=Future()
		@taskroutine('Loading Meta Files')
		def _load(filename,task):
			with f:
				objs=self.ParRec.loadObject(filename)
				magname=self.getUniqueShortName('Mag',obj.getName())
				phasename=self.getUniqueShortName('Phase',obj.getName())
				
				if len(objs)!=2:
					raise IOError,'Loaded ParRec does not have 2 orientations, is this mag/phase?'
					
				self.Nifti.saveObject(objs[0],self.getNiftiFile(magname))
				self.Nifti.saveObject(objs[1],self.getNiftiFile(phasename))

				objs=self.loadNiftiFiles([self.getNiftiFile(magname),self.getNiftiFile(phasename)])
				f.setObject(objs)

		return self.mgr.runTasks(_load(filename),f)

	def calculateMeshRegionThickness(self,objname,regionfieldname,percentThickness):
		f=Future()
		@taskroutine('Calculating Thickness')
		def _calcThickness(objname,regionfieldname,task):
			with f:
				obj=self.findObject(objname)
				regionfield=obj.datasets[0].getDataField(regionfieldname)
				stddevRange=1.0

				#assert len(obj.getTimestepList())>1
				assert regionfield!=None

				results=calculateRegionThicknesses(obj.datasets,regionfield,range(1,18),stddevRange,task)

				obj.plugin.saveObject(obj,self.project.getProjectFile(obj.getName()),setFilenames=True)
				
				if percentThickness:
					for m in range(len(results[0])):
						val=results[0][m]/100.0
						for n in range(len(results)):
							results[n][m]/=val

				plotname=self.getUniqueObjName(objname+'_thickness')
				plottitle=objname+' Region Thickness'+(' (%% of initial)' if percentThickness else '')
				plotfilename=self.project.getProjectFile(plotname+'.plot')

				plot=self.Plot.createPlotObject(plotfilename,plotname,plottitle,results,obj.getTimestepList(),self.Plot.AHADockWidget,obj,isPercent=percentThickness)
				plot.save()
				
				rc=self.mgr.project.getReportCard()
				if rc:
					value='(%% of initial)' if percentThickness else 'mm'
					minthick,maxthick=minmax(listSum(results))
					rc.setValue(objname,'Min Thickness %s'%value, minthick)
					rc.setValue(objname,'Max Thickness %s'%value, maxthick)
					rc.save()
					
				self.mgr.addSceneObject(plot)
				self.project.addObject(plot)
				self.project.save()
				f.setObject(plot)

		return self.mgr.runTasks(_calcThickness(objname,regionfieldname),f)

	def calculateMeshRegionAvgDisp(self,objname,regionfieldname):
		f=Future()
		@taskroutine('Calculating Average Displacement')
		def _calcDisp(objname,regionfieldname,task):
			with f:
				obj=self.findObject(objname)
				regionfield=obj.datasets[0].getDataField(regionfieldname)
				stddevRange=1.0

				assert len(obj.getTimestepList())>1
				assert regionfield!=None

				results=calculateAvgDisplacement(obj.datasets,regionfield,range(1,18),stddevRange,task)

				obj.plugin.saveObject(obj,self.project.getProjectFile(obj.getName()),setFilenames=True)

				plotname=self.getUniqueObjName(objname+'_displace')
				plottitle=objname+' Region Average Displacement'
				plotfilename=self.project.getProjectFile(plotname+'.plot')

				plot=self.Plot.createPlotObject(plotfilename,plotname,plottitle,results,obj.getTimestepList(),self.Plot.AHADockWidget,obj)
				plot.save()
				
				rc=self.mgr.project.getReportCard()
				if rc:
					mindisp,maxdisp=minmax(listSum(results))
					rc.setValue(objname,'Min Avg Displacement', mindisp)
					rc.setValue(objname,'Max Avg Displacement', maxdisp)
					rc.save()

				self.mgr.addSceneObject(plot)
				self.project.addObject(plot)
				self.project.save()
				f.setObject(plot)

		return self.mgr.runTasks(_calcDisp(objname,regionfieldname),f)

	def calculateMeshRegionVolume(self,objname,regionfieldname,heartrate,regionrange=range(1,17)): #regionrange=range(18,24)
		f=Future()
		@taskroutine('Calculating Average Volume')
		def _calcVolume(objname,regionfieldname,heartrate,regionrange,task):
			with f:
				obj=self.findObject(objname)
				timesteps=obj.getTimestepList()
				heartrate=heartrate or (timesteps[-1]-timesteps[0]) # use given heart rate or image time length
				duration=60000.0/heartrate # 1 minute in ms over heart rate yields cycle duration in ms
				regionfield=obj.datasets[0].getDataField(regionfieldname)

				assert len(timesteps)>1
				assert regionfield!=None

				results=calculateLinTetVolume(obj.datasets,regionfield,regionrange,task) # results is indexed by timestep then region

				totals=[t/1000.0 for t in map(sum,results)] # total volume per timestep in mL
				minv,maxv=minmax(totals)
				assert minv<maxv,repr(totals)

				ejectfrac=(maxv-minv)*(100.0/maxv) # calculate ejection fraction percentage
				mincc=minv
				maxcc=maxv
				
				mintimes=[]
				for region in range(len(results[0])):
					regionvals=[results[i][region] for i in xrange(len(results))]
					mintimes.append(min(zip(regionvals,timesteps))[1])
					
				mintimestddev=stddev(mintimes)
				sdiperc=mintimestddev*(100.0/duration)

				resultItems=(
				# BPM
				# duration
					('Timestep Volumes (mL)',totals),
					('ESV Volume (mL)',mincc), 
					('EDV Volume (mL)',maxcc),
					('Stroke Volume (mL)',maxcc-mincc),
					('Ejection Fraction (%)',ejectfrac),
					#('Region Minimum Volume Times (ms)',mintimes),
					('SDI Time (ms)', mintimestddev),
					('SDI (%)',sdiperc)
				)

				otherDataItems=dict(resultItems)

				# create the plot for the region volumes
				plotname=self.getUniqueShortName(objname,regionfieldname,'volume',complen=15)
				plottitle=objname+' Blood Pool Region Volume'
				plotfilename=self.project.getProjectFile(plotname+'.plot')

				plot=self.Plot.createPlotObject(plotfilename,plotname,plottitle,results,timesteps,self.Plot.AHAPoolDockWidget,obj,**otherDataItems)
				plot.save()

				self.mgr.addSceneObject(plot)
				self.project.addObject(plot)

				# create another plot for the total volume
				plotname=self.getUniqueShortName(objname,regionfieldname,'totalvol',complen=15)
				plottitle=objname+' Blood Pool Total Volume'
				plotfilename=self.project.getProjectFile(plotname+'.plot')

				plot1=self.Plot.createPlotObject(plotfilename,plotname,plottitle,[totals],timesteps,self.Plot.TimePlotWidget,obj,**otherDataItems)
				plot1.save()

				self.mgr.addSceneObject(plot1)
				self.project.addObject(plot1)
				self.project.save()

				rc=self.mgr.project.getReportCard()
				if rc:
					for n,v in resultItems:
						rc.setValue(objname,n,v)
						
					rc.save()

				f.setObject([plot,plot1])

		return self.mgr.runTasks(_calcVolume(objname,regionfieldname,heartrate,regionrange),f)

	def calculateMeshStrainField(self,objname, imgname,ahafieldname,spacing,trackname):
		
		if not ahafieldname:
			raise ValueError,'Need to provide an AHA field name'''
			
		f=Future()
		fstrainnodes=Future()

		obj=self.findObject(objname)
		img=self.findObject(imgname)
		trackdir=self.project.getProjectFile(trackname)
		trackfiles=sorted(glob(os.path.join(trackdir,'*.dof.gz')))
		filelists=[('in.vtk','out%.4i.vtk'%i,dof,-1) for i,dof in enumerate(trackfiles)]
		infile=os.path.join(trackdir,'in.vtk')
		timesteps=obj.getTimestepList()

		assert len(timesteps)==(len(trackfiles)+1),'%i != %i'%(len(timesteps),(len(trackfiles)+1))

		ds=obj.datasets[0]
		nodes=ds.getNodes()
		aha=ds.getDataField(ahafieldname)
		spatialmats=filter(isSpatialIndex,ds.enumIndexSets())
		indmat=first(m for m in spatialmats if ElemType[m.getType()].dim==3) or first(spatialmats)

		ahaindices=dict((v,i) for i,v in enumerate(range(1,18))) # map regions to 0-based indices used to index in lists
		
		printFlush(ahaindices)

		# create a matrix assigning an AHA region to each node
		nodeaha=IndexMatrix('nodeaha',nodes.n(),1)
		nodeaha.fill(0) # assumes 0 is never used for a region number
		for n in xrange(indmat.n()):
			elemaha=int(aha.getAt(n)) # AHA region for element n
			# for each node of element n, assign it to region elemaha if it hasn't been already assigned
			for ind in indmat.getRow(n):
				nodeaha.setAt(nodeaha.getAt(ind) or elemaha,ind) # choose the first AHA region encountered for each node
			
		def _addFields(ds,*fields):
			'''Add the matrices `fields' as fields of `ds' with metadat values set.'''
			for f in fields:
				f.meta(StdProps._topology,indmat.getName())
				f.meta(StdProps._spatial,indmat.getName())
				f.meta(StdProps._timecopy,'False')
				ds.setDataField(f)
				
		def _makePlot(suffix,titlesuffix,values):
			'''Create a AHA Plot object for the given region values.'''
			plotname=self.mgr.getUniqueObjName(objname+suffix)
			plottitle=objname+titlesuffix
			plotfilename=self.project.getProjectFile(plotname+'.plot')
			plot=self.Plot.createPlotObject(plotfilename,plotname,plottitle,values,obj.getTimestepList(),self.Plot.AHADockWidget,obj)
			plot.save()
			self.mgr.addSceneObject(plot)
			self.project.addObject(plot)
			return plot

		@taskroutine('Calculating strain field')
		def _calcField(task):
			'''Calculates the 3 directional vector fields, then calculates the strain field and saves it to `infile'.'''
			with fstrainnodes:
				longaxis=img.getVolumeTransform().getRotation()*vec3(0,0,1)

				radialf,longf,circumf=calculateLVDirectionalFields(ds,longaxis,'radial','longitudinal','circumferential')

				for d in obj.datasets:
					d.setDataField(radialf)
					d.setDataField(longf)
					d.setDataField(circumf)

				strainnodes=createStrainField(nodes,radialf,longf,circumf,spacing)
				strainnodes.setM(1)

				self.writePolyNodes(infile,strainnodes)
				fstrainnodes.setObject(strainnodes)

		@taskroutine('Calculating Strains')
		@timing
		def _calcStrains(task):
			'''Calculates the strain fields for each timestep.'''
			with f:
				outfiles=[ff[1] for ff in filelists]
				firstnodes=fstrainnodes()
				task.setMaxProgress(len(outfiles))

				objds=obj.datasets[0]
				radialf=objds.getDataField('radial')
				longf=objds.getDataField('longitudinal')
				circumf=objds.getDataField('circumferential')

				# initial tensor field
				tensors0=listToMatrix([(1.0,0.0,0.0, 0.0,1.0,0.0, 0.0,0.0,1.0)]*nodes.n(),'tensors')
				# initial strain fields
				maxeig0=RealMatrix('maxstrain',nodes.n())
				mineig0=RealMatrix('minstrain',nodes.n())
				# initial direction strain fields are just the directional fields scaled by `spacing'
				radstrain0=RealMatrix('radstrain',nodes.n(),3) 
				longstrain0=RealMatrix('longstrain',nodes.n(),3) 
				circstrain0=RealMatrix('circstrain',nodes.n(),3)

				# scale the vectors to be as long as the spacing value, assuming they were unit length vectors initially
				maxeig0.fill(0)
				radstrain0.fill(0)
				longstrain0.fill(0)
				circstrain0.fill(0)
				
				_addFields(objds,tensors0,maxeig0,mineig0,radstrain0,longstrain0,circstrain0)

				# These matrices will contain one row per timestep, each row will have an averaged value for each
				# region, thus the matrices are indexed by timestep then region
				mavgstrains=[[0]*len(ahaindices)] # averages of maximal eigenvalue strain
				minavgstrains=[[0]*len(ahaindices)] # averages of minimal eigenvalue strain
				lavgstrains=[[0]*len(ahaindices)] # averages of longitudinal strain
				ravgstrains=[[0]*len(ahaindices)] # averages of radial strain
				cavgstrains=[[0]*len(ahaindices)] # averages of circumferential strain
				
				globalmavgstrains=[0]
				globalminavgstrains=[0]
				globallavgstrains=[0]
				globalravgstrains=[0]
				globalcavgstrains=[0]

				for i,o in enumerate(outfiles):
					objds=obj.datasets[i+1]
					inodes,_=self.readPolyNodes(os.path.join(trackdir,o))
					inodes.setM(7)

					tensors=calculateStrainTensors(inodes,spacing)
					maxeig,mineig=calculateTensorIndicatorEigen(tensors)
					longstrain=calculateTensorMul(tensors,longf,'longstrain')
					radstrain=calculateTensorMul(tensors,radialf,'radstrain')
					circstrain=calculateTensorMul(tensors,circumf,'circstrain')

					_addFields(objds,tensors,maxeig,mineig,radstrain,longstrain,circstrain)

					# create lists with one empty list for each region
					mavgstrain=[list() for x in xrange(len(ahaindices))]
					minavgstrain=[list() for x in xrange(len(ahaindices))]
					lavgstrain=[list() for x in xrange(len(ahaindices))]
					ravgstrain=[list() for x in xrange(len(ahaindices))]
					cavgstrain=[list() for x in xrange(len(ahaindices))]

					# Go through each value in the strain fields, if their associated nodes are in a region of interest
					# add the value to the appropriate sublist in the one the above list, otherwise zero the value out
					for n in xrange(maxeig.n()):
						region=nodeaha.getAt(n)
						if region in ahaindices: # if the node is in a region of interest, add its strain values to the lists
							index=ahaindices[region]
							mavgstrain[index].append(maxeig.getAt(n))
							minavgstrain[index].append(mineig.getAt(n))
							lavgstrain[index].append(longstrain.getAt(n))
							ravgstrain[index].append(radstrain.getAt(n))
							cavgstrain[index].append(circstrain.getAt(n))
						else: # otherwise zero out its entries so that strain outside the regions of interest are not stored
							printFlush(region)
							maxeig.setAt(0,n)
							mineig.setAt(0,n)
							longstrain.setRow(n,0,0,0)
							radstrain.setRow(n,0,0,0)
							circstrain.setRow(n,0,0,0)

					# store the averages of the per-region lists in the total average lists
					mavgstrains.append(map(avg,mavgstrain))
					minavgstrains.append(map(avg,minavgstrain))
					lavgstrains.append(map(avg,lavgstrain))
					ravgstrains.append(map(avg,ravgstrain))
					cavgstrains.append(map(avg,cavgstrain))
					
					# global average strains minus last region (17)
					globalmavgstrains.append(avg(matIter(mavgstrain[:-1]))) 
					globalminavgstrains.append(avg(matIter(minavgstrain[:-1])))
					globallavgstrains.append(avg(matIter(lavgstrain[:-1])))
					globalravgstrains.append(avg(matIter(ravgstrain[:-1])))
					globalcavgstrains.append(avg(matIter(cavgstrain[:-1])))

					task.setProgress(i+1)

				obj.plugin.saveObject(obj,self.project.getProjectFile(objname),setFilenames=True)

				p1=_makePlot('_maxstrain',' Region Average of Maximal Strain',mavgstrains)
				p2=_makePlot('_longstrain',' Region Average of Magnitude of Longitudinal Strain',lavgstrains)
				p3=_makePlot('_radstrain',' Region Average of Magnitude of Radial Strain',ravgstrains)
				p4=_makePlot('_circstrain',' Region Average of Magnitude of Circumferential Strain',cavgstrains)
				
				plotname=self.mgr.getUniqueObjName(objname+'_globalstrain')
				plottitle=objname+' Global Average Strain'
				plotfilename=self.project.getProjectFile(plotname+'.plot')
				results=(globalmavgstrains,globalminavgstrains,globallavgstrains,globalravgstrains,globalcavgstrains)
				labels=('Global Maximal Strain','Global Minimal Strain','Global Longitudinal Strain','Global Radial Strain','Global Circumferential Strain')
				gplot=self.Plot.createPlotObject(plotfilename,plotname,plottitle,results,timesteps,self.Plot.TimePlotWidget,obj,labels=labels)
				gplot.save()

				self.mgr.addSceneObject(gplot)
				self.project.addObject(gplot)
				
				rc=self.mgr.project.getReportCard()
				if rc:
					minm,maxm=minmax(matIter(mavgstrains))
					rc.setValue(objname,'Min Avg Strain', minm)
					rc.setValue(objname,'Max Avg Strain',maxm)
					minm,maxm=minmax(matIter(lavgstrains))
					rc.setValue(objname,'Min Avg Longitudinal Strain', minm)
					rc.setValue(objname,'Max Avg Longitudinal Strain',maxm)
					minm,maxm=minmax(matIter(ravgstrains))
					rc.setValue(objname,'Min Avg Radial Strain', minm)
					rc.setValue(objname,'Max Avg Radial Strain',maxm)
					minm,maxm=minmax(matIter(cavgstrains))
					rc.setValue(objname,'Min Avg Circumferential Strain', minm)
					rc.setValue(objname,'Max Avg Circumferential Strain',maxm)
					
					maxvt=max(zip(map(abs,globalmavgstrains),timesteps))
					rc.setValue(objname,'Maximal Global Strain Peak (value,time)', maxvt)
					minvt=max(zip(map(abs,globalminavgstrains),timesteps))
					rc.setValue(objname,'Minimal Global Strain Peak (value,time)', minvt)
					lvt=max(zip(map(abs,globallavgstrains),timesteps))
					rc.setValue(objname,'Minimal Longitudinal Strain Peak (value,time)', lvt)
					rvt=max(zip(map(abs,globalravgstrains),timesteps))
					rc.setValue(objname,'Minimal Radial Strain Peak (value,time)', rvt)
					cvt=max(zip(map(abs,globalcavgstrains),timesteps))
					rc.setValue(objname,'Minimal Circumferential Strain Peak (value,time)', cvt)
					
					rc.save()

				self.project.save()
				f.setObject((p1,p2,p3,p4,gplot))

		if ds.getDataField('Radial') is None:
			tasks=[_calcField()]
		else:
			tasks=[]
			
		tasks+=[applyMotionTrackTask(self.ptransformation,trackdir,False,filelists), _calcStrains()]
		return self.mgr.runTasks(tasks,f)

	def calculateImageStrainField(self,objname,srcname,griddims,spacing,trackname):
		obj=self.findObject(objname)
		srcobj=self.findObject(srcname)
		trackdir=self.project.getProjectFile(trackname)
		trackfiles=sorted(glob(os.path.join(trackdir,'*.dof.gz')))
		infile=os.path.join(trackdir,'in.vtk')
		timesteps=srcobj.getTimestepList() if srcobj else range(len(trackfiles))

		#dx,dy,dz=[max(2,int(d/float(spacing))) for d in obj.getVolumeDims()]
		trans=obj.getVolumeTransform()
		nodes,inds=generateHexBox(*griddims)

		indmat=listToMatrix(inds,'inds',ElemType._Hex1NL)
		indmat.meta(StdProps._isspatial,'True')

#		strain0=listToMatrix([0.0]*len(nodes),'strain0')
#		strain0.meta(StdProps._topology,indmat.getName())
#		strain0.meta(StdProps._spatial,indmat.getName())
		initds=PyDataSet('initds',[trans*n for n in nodes],[indmat],[('strain0','',[0.0]*len(nodes))])

		strainnodes=createStrainGrid(nodes,transform(),trans,spacing)
		strainnodes.setM(1)

		self.writePolyNodes(infile,strainnodes)
		
		filelists=[('in.vtk','out%.4i.vtk'%i,dof) for i,dof in enumerate(trackfiles)]
		self.mgr.runTasks(applyMotionTrackTask(self.ptransformation,trackdir,False,filelists))

		f=Future()
		@taskroutine('Calculating Strains')
		def _calcStrains(initds,outfiles,timesteps,spacing,obj,task):
			with f:
				indmat=initds.getIndexSet('inds')
				task.setMaxProgress(len(outfiles))
				dds=[initds]
				for i,o in enumerate(outfiles):
					#ds=self.readIRTKPolydata(os.path.join(trackdir,o))
					#nodes=ds.getNodes()
					nodes,_=self.VTK.loadPolydataNodes(os.path.join(trackdir,o))
					nodes.mul(vec3(-1,-1,1))
					nodes.setM(7)
					tensors=calculateStrainTensors(nodes,spacing)
					strain,_=calculateTensorIndicatorEigen(tensors)
					strain.meta(StdProps._topology,indmat.getName())
					strain.meta(StdProps._spatial,indmat.getName())

					ds=PyDataSet(o+'DS',nodes.subMatrix(nodes.getName(),nodes.n()),[indmat],[strain])
#					ds.setIndexSet(indmat)
#					ds.setDataField(strain)
#					ds.setNodes(nodes.subMatrix(nodes.getName(),nodes.n()))

					if i==0:
						dds[-1].setDataField(strain.clone('strain0'))

					dds.append(ds)
					task.setProgress(i+1)

				nobj=MeshSceneObject(self.mgr.getUniqueObjName(obj.getName()+'Strain'),dds)
				nobj.timestepList=timesteps
				self.mgr.addSceneObject(nobj)

				f.setObject(nobj)

		return self.mgr.runTasks(_calcStrains(initds,[ff[1] for ff in filelists],timesteps,spacing,obj),f)

	def calculatePhaseKineticEnergy(self,maskname,phaseXname,phaseYname,phaseZname,maskval=2):
		mask=self.findObject(maskname)
		phasex=self.findObject(phaseXname)
		phasey=self.findObject(phaseYname)
		phasez=self.findObject(phaseZname)

		f=Future()
		@taskroutine('Calculating Phase Kinetic Energy')
		def _calcEnergy(mask,phasex,phasey,phasez,maskval,task):
			with f:
				energy=cropObjectEmptySpace(mask,self.getUniqueObjName('EmptyMask'))
				thresholdImage(energy,maskval-epsilon,maskval+epsilon,task)
				binaryMaskImage(energy,maskval-epsilon)

				voxelw,voxelh=energy.images[0].spacing
				energycalcfunc='sum([(vals[0]*10)**2,(vals[1]*10)**2,(vals[2]*10)**2])*vals[3]*(%r)'%((voxelw**3)*0.5)

				mergeImages([phasex,phasey,phasez,energy],energy,energycalcfunc,task)

				energylist=[]
				for _,inds in energy.getTimestepIndices():
					energylist.append(sum(sumMatrix(energy.images[ii].img) for ii in inds))

				plotname=self.getUniqueShortName(mask.getName(),'Energy',complen=15)
				plottitle=mask.getName()+' Total Kinetic Energy'
				plotfilename=self.project.getProjectFile(plotname+'.plot')

				plot=self.Plot.createPlotObject(plotfilename,plotname,plottitle,[energylist],energy.getTimestepList(),self.Plot.TimePlotWidget,mask)
				plot.save()
				self.addObject(plot)

				self.saveToNifti([energy])
				self.addObject(energy)

		return self.mgr.runTasks(_calcEnergy(mask,phasex,phasey,phasez,maskval))


addPlugin(CardiacMotionPlugin())
