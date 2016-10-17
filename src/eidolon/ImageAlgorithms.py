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


from ImageObject import *

import scipy.ndimage
import scipy.signal

# Hounsfield value range
Hounsfield=enum(
	('air',-1000),
	('water',0),
	('muscle',10,40),
	('blood',40),
	('bone',1000),
	('min',-1000),
	('max',4000), # 4095?
	doc='Known Hounsfield unit values for various tissues, 1 or 2 values for a minimum and optional maximum range'
)


defaultImageQuad=(
	(vec3(-0.5,0.5), vec3(0.5,0.5), vec3(-0.5,-0.5), vec3(0.5,-0.5)), # vertices
	((0, 2, 1), (1, 2, 3)), # triangle indices
	(vec3(0,0), vec3(1,0), vec3(0,1), vec3(1,1)) # xi values
)


def hounsfieldToUnit(h):
	'''Converts a Hounsfield unit value `h' to a unit value, 0 if `h' is the minimal Hounsfield value to 1 if maximal.'''
	return clamp(lerpXi(h,Hounsfield.min,Hounsfield.max),0.0,1.0)


@timing
def checkNan(obj):
	for i,img in enumerate(obj.images):
		for n,m in matIterate(img.img):
			v=img.img.getAt(n,m)
			assert not math.isnan(v), 'Found NaN in object %s, image %i at %i,%i'%(obj.getName(),i,n,m)


def loadImageFile(filename,imgobj,pos=vec3(),rot=rotator(),spacing=(1.0,1.0)):
	#imgobj=imgobj or Image.loadImageFile(filename)

	w=imgobj.getWidth()
	h=imgobj.getHeight()

	si=SharedImage(filename,pos,rot,(w,h),spacing)
	si.allocateImg(os.path.split(filename)[1])
	imgobj.fillRealMatrix(si.img)
	si.readMinMaxValues()

	return si


@timing
def loadImageStack(files,imgLoadFunc,positions,rot=rotator(),spacing=(1.0,1.0),task=None):
	assert len(files)==len(positions)

	def createLoadImageThread(filenames,positions,imgq):
		def readImages():
			for f,p in zip(filenames,positions):
				try:
					i=imgLoadFunc(f)
					imgq.put((f,i,p))
				except Exception as e:
					printFlush(e)

		readthread=threading.Thread(target=readImages)
		readthread.start()

		return readthread

	imgq=Queue()
	numthreads=1
	threads=[]
	results=[]

	if task:
		task.setMaxProgress(len(files))

	for n in range(numthreads):
		start,end=partitionSequence(len(files),n,numthreads)
		threads.append(createLoadImageThread(files[start:end],positions[start:end],imgq))

	while any(t.isAlive() for t in threads) or not imgq.empty():
		try:
			filename,imgobj,position=imgq.get(True,0.01)
			results.append(loadImageFile(filename,imgobj,position,rot,spacing))
			del imgobj
		except Exception as e:
			printFlush(e)

		if task:
			task.setProgress(len(results))

	return results


def generateImageStack(width,height,slices,timesteps=1,pos=vec3(),rot=rotator(),spacing=vec3(1),name='img'):
		'''Create a blank image stack with each timestep ordered bottom-up with integer timesteps.'''
		assert width>0
		assert height>0
		assert slices>0
		assert spacing.x()>0
		assert spacing.y()>0
		assert timesteps>0

		images=[]
		positions=[pos+(rot*vec3(0,0,spacing.z()*s)) for s in range(slices)]
		for t,s in trange(timesteps,slices):
			siname='%s_%i_%i' %(name,s,t)
			si=SharedImage(siname,positions[s],rot,(width,height),(spacing.x(),spacing.y()),t)
			si.allocateImg(siname+'Img')
			si.img.fill(0)
			images.append(si)

		return images


def generateTestImageStack(width,height,slices,timesteps=1,pos=vec3(),rot=rotator(),spacing=vec3(1)):
	images=generateImageStack(width,height,slices,timesteps,pos,rot,spacing)
	
	for ind,im in enumerate(images):
			t=int(float(ind)/slices)
			i=ind%slices
			imax=0.0

			for n,m in trange(im.img.n(),im.img.m()):
				val=0.0
				
				if n==t and m==t:
					val=4.0
				elif n==(i+1) or m==(i+1):
					val=0.5
				elif n<20 and m<20:
					val=3.0
				elif m<15 and i<15:
					val=2.0
				elif n<10 and i<10:
					val=1.0

				im.img.setAt(val,n,m)
				imax=max(imax,val)

			im.imgmin=0.0
			im.imgmax=imax

	return images


def generateSphereImageStack(width,height,slices,center=vec3(0.5),scale=vec3(0.45),innerval=0.75,shellval=1.0):
	dim=vec3(width,height,slices)
	center=center*dim
	images=generateImageStack(width,height,slices)

	for i,im in enumerate(images):
		imax=0.0

		for n,m in matIterate(im.img):
			p=(vec3(m,n,i)-center)/(scale*dim)
			val=0
			plen=p.len() # plen is twice the distance from image stack center to p

			if plen<0.9: # inner part of circle
				val=innerval
			elif plen<1.0: # circle edge
				val=shellval
			else:
				continue

			im.img.setAt(val,n,m)
			imax=max(imax,val)

		im.imgmin=0.0
		im.imgmax=imax

	return images


@concurrent
def calculateImageStackHistogramRange(process,imgs,minv,maxv):
	hist=RealMatrix('histogram',int(maxv-minv),1,True)
	hist.fill(0)

	for i in process.prange():
		calculateImageHistogram(imgs[i-process.startval].img,hist,minv)

	return hist


def calculateImageStackHistogram(imgs,minv=None,maxv=None,task=None):
	if isinstance(imgs,ImageSceneObject):
		imgs=imgs.images

	#if minv==None or maxv==None:
	#	minv,maxv=minmax(((i.imgmin,i.imgmax) for i in imgs),ranges=True)

	imgmin,imgmax=minmax(((i.imgmin,i.imgmax) for i in imgs),ranges=True)
	if minv!=None:
		imgmin=min(imgmin,minv)
	if maxv!=None:
		imgmax=max(imgmax,maxv)

	results=calculateImageStackHistogramRange(len(imgs),0,task,imgs,int(imgmin),int(imgmax),partitionArgs=(imgs,))

	hists=results.values()
	hist=hists[0]
	for hh in hists[1:]:
		hist.add(hh)
		hh.clear()

	hist.meta('minx',str(imgmin))
	hist.meta('maxx',str(imgmax))

	return hist


def getHistogramExtremas(hist,thresholdFilter=True,thresholdfunc=None,sigma=3,order=5):
	'''
	Given a histogram matrix `hist', identify the maximal and minimal points in the histogram's curve. The histogram
	is first smoothed using a gaussian filter with the given `sigma' argument, and then argrelextrema() is applied to
	this with the given `order' argument
	'''
	hist=matrixToArray(hist)

	zeroind=first(i for i,v in enumerate(hist) if v>0)
	hist[zeroind]=0 # eliminate the empty space component

	smoothed=scipy.ndimage.gaussian_filter(hist,sigma) # compute a smoothed histogram curve

	# calculate curve maximal values
	maximi=[(i,hist[i]) for i in scipy.signal.argrelextrema(smoothed,np.greater,order=order)[0]]
	minimi=[(zeroind,0)]+[(i,hist[i]) for i in scipy.signal.argrelextrema(smoothed,np.less,order=order)[0]]

	if thresholdFilter:
		thresholdfunc=thresholdfunc or (lambda i:np.average(i)*0.5)
		threshold=thresholdfunc(hist)

		fmaximi=[]
		fminimi=set()

		for i,v in maximi:
			l=first(sorted((abs(j-i),(j,m)) for j,m in minimi if j<i))
			r=first(sorted((abs(j-i),(j,m)) for j,m in minimi if j>i))
			l=l[1] if l else None
			r=r[1] if r else None

			if (l and (v-l[1])>threshold) or (r and (r[1]-v)>threshold):
				fmaximi.append((i,v))
				fminimi.add(l)
				fminimi.add(r)

		maximi=fmaximi
		minimi=sorted(filter(bool,fminimi))

	return maximi,minimi


def isCTImageSeries(imgs=None,minv=None,maxv=None,hist=None):
	'''
	Returns True if the list of ShareImage objects `imgs' represents a volume of CT data. This is done by counting the
	number of maximi in the image histogram, if there's more than 3 this is a CT series. If `hist' is not None, this
	RealMatrix is used as the histogram, otherwise one is calculated from `imgs'.
	'''
	assert imgs or hist
#	'''
#	Returns True if the list of ShareImage objects `imgs' represents a volume of CT data. This is done by measuring
#	where in the image histogram half the values fall. If this point is 20% along the range from the minimal to maximal
#	position in the histogram, this is a CT image. If `hist' is not None, this RealMatrix is used as the histogram,
#	otherwise one is calculated from `imgs'.
#	'''
#	hist=matrixToList(hist or calculateImageStackHistogram(imgs,minv,maxv))
#
#	hmin,hmax=minmax(hist)
#	if hmin>=0 and hmax<20: # trivially small numbers
#		return False
#
#	hmin=first(i for i,v in enumerate(hist) if v>0)
#	hmax=last(i for i,v in enumerate(hist) if v>0)
#	hsum=sum(hist)
#
#	hist[hmin]=0
#	halfsum=0
#	halfind=0
#	for i in xrange(len(hist)):
#		halfsum+=hist[i]
#		if halfsum>hsum/2:
#			halfind=i
#			break
#
#	return lerpXi(halfind,hmin,hmax)>0.2

	maximi,minimi=getHistogramExtremas(hist or calculateImageStackHistogram(imgs,minv,maxv))
	return len(maximi)>3


def addMotionDiff(img1,img2,imgout):
	for n,m in matIterate(imgout):
		diff=abs(img2.getAt(n,m)-img1.getAt(n,m))+imgout.getAt(n,m)
		imgout.setAt(diff,n,m)


@concurrent
def calculateMotionMaskRange(process,diffimgs,vols,inimgs):
	maxval=0.0
	for ind in process.nrange():
		imgout=diffimgs[ind].img
		process.setProgress(ind-process.startval+1)
		for v in range(1,len(vols)):
			addMotionDiff(inimgs[vols[v-1][ind]].img,inimgs[vols[v][ind]].img,imgout)
#			img1=inimgs[vols[v-1][ind]].img
#			img2=inimgs[vols[v][ind]].img
#			for n,m in matIterate(imgout):
#				diff=abs(img2.getAt(n,m)-img1.getAt(n,m))+imgout.getAt(n,m)
#				imgout.setAt(diff,n,m)

		for n,m in matIterate(imgout):
			maxval=max(maxval,imgout.getAt(n,m))

	return maxval


@timing
def calculateMotionMask(imgobj,task=None):
	if not imgobj.isTimeDependent:
		raise ValueError,"ImageSceneObject `imgobj'must be time-dependent"

	for i in imgobj.images:
		i.img.setShared(True)

	diffimgs=[]
	if imgobj.is2D:
		img=imgobj.images[0].clone()
		diffimgs.append(img)
		inds=listSum(imgobj.getVolumeStacks())

		for ind1,ind2 in zip(inds,inds[1:]):
			addMotionDiff(imgobj.images[ind1].img,imgobj.images[ind2].img,img.img)
	else:
		vols=imgobj.getVolumeStacks()

		for ind in vols[0]:
			img=imgobj.images[ind].clone()
			img.img.fill(0)
			diffimgs.append(img)

		maxs=calculateMotionMaskRange(len(diffimgs),0,task,diffimgs,vols,imgobj.images)

		maxdiff=max(maxs.values())

		for i in diffimgs:
			i.img.div(maxdiff)
			i.imgmin=0.0
			i.imgmax=1.0

	return diffimgs


def applySlopeIntercept(imgobj,slope=None,inter=None):
	'''Apply the slope and intercept values to the image object `imgobj', each pixel i is replaced with i*slope+inter.'''
	slope=float(slope if slope is not None else 1.0)
	inter=float(inter if inter is not None else 0.0)
	if slope==1.0 and inter==0.0:
		return

	for i in imgobj.images:
		i.img.mul(slope)
		i.img.add(inter)
		i.setMinMaxValues(i.imgmin*slope+inter,i.imgmax*slope+inter)

	imgobj.imagerange=None


@timing
def applyVolumeMask(imgobj,mask,threshold,task=None):
	vols=imgobj.getVolumeStacks()
	if not imgobj.isTimeDependent or len(vols)==1:
		raise ValueError,"ImageSceneObject `imgobj' must be time-dependent"

	minx,miny,maxx,maxy=calculateStackClipSq(mask,threshold)
	outobj=imgobj.cropXY(imgobj.getName()+'VCrop',minx,miny,maxx,maxy)

#	for ind,ming in enumerate(mask):
#		ming=ming.img
#		for vol in vols:
#			outimg=outobj.images[vol[ind]].img
#			for n,m in trange((miny,maxy),(minx,maxx)):
#				if ming.getAt(n,m)<threshold:
#					outimg.setAt(0,n-miny,m-minx)

	return outobj


@timing
def cropObjectEmptySpace(obj,name,xymargins=0,zFilter=False):
	'''
	Crop the images of ImageSceneObject `obj' to exclude empty space, defined by being any pixel below the minimal value
	plus a small threshold. A new object is produced with name `name' having its own copy of the image data, even if the
	entirety of the original images is included (ie. not clipped). If `xymargins' is specified then the clipping square
	is expanded by that much. if `zFilter' is true then images whose maximal value is below the clipping threshold
	are excluded in their entirety.
	'''
	images=obj.images
	cols,rows=images[0].dimensions
	imgmin=min(i.imgmin for i in images)
	imgmax=max(i.imgmax for i in images)
	threshold=imgmin+(imgmax-imgmin)*0.001

	if zFilter:
		images=filter(lambda i:i.imgmax>=threshold,images)

	clipsq=calculateStackClipSq(images,threshold)
	newobj=ImageSceneObject(name,obj.source,images,obj.plugin,obj.isTimeDependent)
	if clipsq!=(0,0,cols-1,rows-1):
		minx,miny,maxx,maxy=clipsq
		minx=max(0,minx-xymargins/2)
		miny=max(0,miny-xymargins/2)
		maxx=min(cols-1,maxx+xymargins/2)
		maxy=min(rows-1,maxy+xymargins/2)
		newobj=newobj.cropXY(name,minx,miny,maxx,maxy)

	return newobj


def centerImagesLocalSpace(obj):
	for i in obj.images:
		i.position-=obj.getAABB().center
		i.calculateDimensions()

	obj.aabb=BoundBox(matIter(s.getCorners() for s in obj.images))


def sampleImageRay(img,start,samplevec,numsamples):
	'''Sample `numsamples' values from `img' starting from `start' in direction of `samplevec' (both in matrix coords).'''
	samples=[]
	for i in xrange(numsamples):
		pos=start+samplevec*(float(i+1)/numsamples)
		n=int(0.5+pos.y())
		m=int(0.5+pos.x())

		if not validIndices(img,n,m):
			break

		samples.append(img.getAt(n,m))

	return samples


@timing
def normalizeImageData(obj):
	imgmin,imgmax=minmax(((i.imgmin,i.imgmax) for i in obj.images),ranges=True)

	for i in obj.images:
		i.img.sub(imgmin)
		i.img.div(imgmax)
		i.setMinMaxValues(0.0,1.0)


@concurrent
def binaryMaskImageRange(process,imgs,threshold):
	def op(val,n,m):
		return 1.0 if val>=threshold else 0.0

	for i in process.prange():
		imgs[i-process.startval].applyCell(op)


@timing
def binaryMaskImage(obj,threshold,task=None):
	'''Fill `obj' with a binary mask, each value of each image replaced with 1.0 if >=`threshold', 0.0 otherwise.'''
	obj.setShared(True)
	imglist=[i.img for i in obj.images]
	binaryMaskImageRange(len(imglist),0,task,imglist,threshold,partitionArgs=(imglist,))

	for i in obj.images:
		i.setMinMaxValues(0.0,1.0)


@concurrent
def thresholdImageRange(process,imgs,minv,maxv):
	def op(val,n,m):
		return val if minv<=val<=maxv else 0.0

	for i in process.prange():
		imgs[i-process.startval].applyCell(op)


@timing
def thresholdImage(obj,minv,maxv,task=None):
	'''Fill `obj' with a 0 for all values outside the range [minv,maxv], any value within is untouched.'''
	obj.setShared(True)
	imglist=[i.img for i in obj.images]
	thresholdImageRange(len(imglist),0,task,imglist,minv,maxv,partitionArgs=(imglist,))

	for i in obj.images:
		i.setMinMaxValues(*minmaxMatrixReal(i.img))


#@contextlib.contextmanager
#def processImageNp(img,dtype=None):
#	'''
#	Yields a Numpy array from the SharedImage or RealMatrix `img' with type `dtype' when the context entures, then
#	copies data back into `img' when the context is left.
#	'''
#	if isinstance(img,SharedImage):
#		img=img.img
#	im=matrixToArray(img,dtype)
#	yield im
#	if im.size>0:
#		arrayToMatrix(im,img)
#
#
#@timing
#def sobelImage2D(obj):
#	for image in obj.images:
#		with processImageNp(image) as im:
#			sx = ndimage.sobel(im, axis=0, mode='constant')
#			sy = ndimage.sobel(im, axis=1, mode='constant')
#			im[:]=np.hypot(sx, sy)


def sampleImageVolume(obj,pt,timestep,transinv=None):
	'''
	Sample the image volume `obj' at the given point in world space and time, returning 0 if the point is outside the
	volume. The value `transinv' should be the inverse transform of the object's volume, if this is None then the
	transform is queried from `obj', therefore this is an optional optimization value only.
	'''
	transinv=transinv or obj.getVolumeTransform().inverse()
	inds=obj.getNearestTimestepIndices(timestep)
	images=[obj.images[i].img for i in inds]
	return getImageStackValue(images,transinv*pt)
	
	
def calculateReprIsoplaneMesh(rep,planetrans,stackpos,slicewidth):
	'''
	Calculates the mesh for image representation object `rep' at plane `planetrans' at the stack position `stackpos' 
	(which is meaningfor only for ImageSeriesRepr types). This will determine where `rep' is intersected by `planetrans' 
	and returns the triple (nodes,indices,xis) representing a mesh for that intersecting geometry. 2D images viewed at
	oblique angles produces slices which are `slicewidth' wide.
	'''
	assert isinstance(rep,(ImageSeriesRepr,ImageVolumeRepr))
	nodes,indices,xis=defaultImageQuad # default plane values

	# get a plane point and norm from the transform
	planept=planetrans.getTranslation()
	planenorm=planetrans.getRotation()*vec3(0,0,1)

	# calculate the plane mesh by transforming the default quad by the repr's defined transform,
	if isinstance(rep,ImageSeriesRepr):
		trans=rep.getDefinedTransform(stackpos)
		nodes=[trans*v for v in nodes]
		reppt=trans.getTranslation()
		repnorm=trans.getRotation()*vec3(0,0,1)

		# if this is being viewed at an oblique angle, determine where the image plane intersects the view plane and represent that as a 2D textured line
		if not equalPlanes(reppt,repnorm,planept,planenorm):
			et=ElemType.Quad1NL
			heights=[n.planeDist(planept,planenorm) for n in nodes] # determine distance from each node to the view plane
			xipair=first(calculateQuadIsoline(heights,et,0)) # calculate the isoline of intersection between the image plane and view plane

			if xipair: # if an isoline is found, calculate an isoline quad with a width of slicewidth
				xi1,xi2=xipair
				pt1=et.applyBasis(nodes,*xi1)
				pt2=et.applyBasis(nodes,*xi2)
				nodes=generateQuadFromLine(pt1,pt2,planenorm,slicewidth)
				xis=[xi1,xi1,xi2,xi2]
			else:
				nodes=[] # otherwise given no nodes, meaning nothing to see here

	# calculate the plane mesh by slicing through the volume at the plane defined by `planetrans'
	elif isinstance(rep,ImageVolumeRepr):
		inters=rep.getPlaneIntersects(planept,planenorm,True) # get the (node,xi) pairs for the intersecting polygon
		if len(inters):
			nodes,xis=zip(*inters) # divide nodes and xis into separate lists
			indices=[(0,i+1,i+2) for i in xrange(len(inters)-2)] # triangle fan indices

	return nodes,indices,xis


@timing
def resampleImage(srcobj,destobj):
	'''Resample the data from `srcobj' into `destobj', overwriting the latter's contents.'''

	srctrans=srcobj.getVolumeTransform().inverse()

	srcinds=srcobj.getTimestepIndices()
	destinds=destobj.getTimestepIndices()

	for ts,inds in destinds:
		tdiff,closest=min((abs(sts-ts),sinds) for sts,sinds in srcinds)

		srcstack=indexList(closest,srcobj.images)
		stackimgs=[s.img for s in srcstack]

		if srcobj.is2D:
			stackimgs+=stackimgs

		for ind in inds:
			img=destobj.images[ind]
			interpolateImageStack(stackimgs,srctrans, img.img, img.getTransform())
			img.readMinMaxValues()


@concurrent
def mergeColinearImagesRange(process,imglist,mergefunc):
	if isinstance(mergefunc,str):
		comp=compiler.compile(mergefunc,'mergefunc','eval')
		mergefunc=lambda vals:eval(comp)

	minmaxes=[]
	for p in process.prange():
		imgs=imglist[p-process.startval][:-1]
		imgo=imglist[p-process.startval][-1]

		imgmin=mergefunc([i.img.getAt(0,0) for i in imgs])
		imgmax=imgmin

		for n,m in matIterate(imgo.img):
			val=mergefunc([i.img.getAt(n,m) for i in imgs])
			imgo.img.setAt(val,n,m)

			imgmin=min(imgmin,val)
			imgmax=max(imgmax,val)

		minmaxes.append((imgmin,imgmax))

	return minmaxes


@timing
def mergeColinearImages(imgobjs,objout,mergefunc=None,task=None):
	'''
	Merge the images in `imgobjs' into `objout' using the function `mergefunc' which accepts a list of values `val' and
	expects a single float value in return. By default the built-in function max is used in `mergefunc' is None. The
	objects in `imgobjs' must be colinear with `objout', that is the topology of the image planes in these objects must
	be the same as those in `objout', so there must be as many images in each of these objects and each image plane is 
	located in the same time and space as the counterpart in `objout'. The order of planes as stored in the `images' 
	field of the objects must also be the same.
	'''
	mergefunc=mergefunc or max
	imgobjs=toIterable(imgobjs)

	for o in imgobjs:
		o.setShared(True)

	objout.setShared(True)

	imglist=[] # will contain lists of colinear images
	for ind in listSum(objout.getVolumeStacks()):
		imglist.append([o.images[ind] for o in imgobjs]+[objout.images[ind]])

	minmaxes=mergeColinearImagesRange(len(imglist),0,task,imglist,mergefunc,partitionArgs=(imglist,))

	minmaxes=listSum(indexList(xrange(len(minmaxes)),minmaxes.values()))

	for n in xrange(len(minmaxes)):
		imglist[n][-1].setMinMaxValues(*minmaxes[n])


@timing
def mergeImages(imgobjs,imgout,mergefunc=None,task=None):
	'''
	Merge the images of `imgobjs' into `imgout'. Each image in `imgobjs' is resampled into a clone of `imgout' which
	are then merged into `imgout' using `mergefunc', except if `imgout' is in `imgobjs', in which case it will be used
	directly in calculations. The object `mergefunc' is either a callable in the gloval namespace accepting a list of
	floats and returning a single float (by default the built-in max) or a string expression converting a list of 
	floats `vals' into a single float value. For example, "avg(vals)" produces an averaged image. 
	'''
	inters=[] # resample `imgobjs' into clones of `imgout' thus ensuring they are colinear with `imgout'
	for o in imgobjs:
		if o==imgout:
			inters.append(o)
		else:
			i=imgout.clone('resampleclone'+o.getName())
			resampleImage(o,i)
			inters.append(i)

	mergeColinearImages(inters,imgout,mergefunc,task) # merge the images using the merge function
	
	# delete temporary image data, be sure not to delete `imgout'
	for i in inters: 
		if i!=imgout:
			i.clear()


@timing
def createIsotropicVolume(obj,dims=None,dimmult=1.0):
	assert not obj.is2D
	
	dims=vec3(*dims) if dims else vec3(min(obj.getVoxelSize()))
	dims*=dimmult
	trans=obj.getVolumeTransform()
	w,h,d,t=obj.getMatrixDims()
	
	images=generateImageStack(w,h,int(trans.getScale().z()/dims[2]),t,trans.getTranslation(),trans.getRotation(),dims,obj.getName()+'_Iso')
	imgobj=ImageSceneObject(obj.getName()+'_Iso',obj.source,images,obj.plugin,obj.isTimeDependent)
	imgobj.setTimestepList(obj.getTimestepList())
	return imgobj
	
	
def dilateImageVolume(obj,size=(5,5,5)):
	inds=obj.getVolumeStacks()	
	
	for ind in inds:
		images=indexList(ind,obj.images)
		volume=np.asarray([np.asarray(i.img) for i in images])
		volume=np.transpose(volume,(1,2,0))
		result=scipy.ndimage.morphology.grey_dilation(volume,size)
		for i,img in enumerate(images):
			np.asarray(img.img)[:,:]=result[:,:,i]
			
			
	