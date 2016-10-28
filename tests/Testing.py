'''Test utility routines used by scripts in the included test subdirectories.'''

from eidolon import *

@timing
def generateTestMeshDS(etname,refine):
	et=ElemType[etname]
	pt=vec3(0.25)

	if et.geom in (GeomType._Hex, GeomType._Tet):
		dividefunc=divideHextoTet if et.geom==GeomType._Tet else divideHextoHex
		nodes=listSum(dividefunc(et.order,refine))
		inds=list(group(range(len(nodes)),len(et.xis)))

		nodes,ninds,_=reduceMesh(listToMatrix([vec3(*n) for n in nodes],'nodes'),[listToMatrix(inds,'inds',etname)])
		dist=[nodes.getAt(n).distTo(pt) for n in xrange(nodes.n())]

	elif et.geom == GeomType._Tri:
		nodes,inds=generateSphere(refine)
		dist=[n.distTo(pt) for n in nodes]
		ninds=[('inds',ElemType._Tri1NL,inds)]

	ds=PyDataSet('TestDS',nodes,ninds,[('dist',dist,'inds')])
	ds.validateDataSet()
	return ds


def generateTimeSphereImages(step,dim=50):
	images=[]
	steps=frange(0,1.0+step,step)
	for i in steps:
		ii=math.sin(i*math.pi*2)
		stepimgs=generateSphereImageStack(dim,dim,dim,vec3(0.5,0.5,0.5),vec3(0.25+0.2*ii,0.25,0.25))
		for s in stepimgs:
			s.timestep=i*500

		images+=stepimgs

	return images


def generateTimeSphereMeshes(step,dim=50):
	dds=[]
	steps=list(frange(0,1.0+step,step))
	for i in steps:
		i=math.sin(i*math.pi*2)
		ds=generateTestMeshDS(ElemType._Tri1NL,5)
		nodes=ds.getNodes()
		nodes.mul(vec3(0.25+0.2*i,0.25,0.25))
		nodes.mul(dim)
		nodes.add(vec3(dim+1)*vec3(0.5,-0.5,0.5))

		dist=ds.getDataField('dist')
		for n in xrange(dist.n()):
			dist.setAt(nodes.getAt(n).distTo(vec3(0.25)*dim),n)

		dds.append(ds)

	return dds,[s*500 for s in steps]