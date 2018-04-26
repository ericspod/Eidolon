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


import math
import os
import contextlib
import threading

import numpy as np
import scipy.ndimage
import scipy.signal
import scipy.fftpack
import scipy.spatial

import renderer

from . import Utils
from . import MathDef
from . import SceneUtils

from renderer import vec3, rotator, RealMatrix, IndexMatrix
from .Utils import timing, clamp, lerpXi, printFlush, trange, listSum, indexList, first, minmax,queue
from .SceneUtils import matIterate, validIndices, BoundBox
from .Concurrency import concurrent, checkResultMap, sumResultMap
from .ImageObject import SharedImage, ImageSceneObject, ImageSeriesRepr, ImageVolumeRepr, calculateStackClipSq

from eidolon import * # because eval() is used its necessary to ensure everything is in the namespace for this module

# Hounsfield value range
Hounsfield=Utils.enum(
    ('air',-1000),
    ('water',0),
    ('muscle',10,40),
    ('blood',40),
    ('bone',1000),
    ('min',-1000),
    ('max',4000), # 4095?
    doc='Known Hounsfield unit values for various tissues, 1 or 2 values for a minimum and optional maximum range'
)


# coordinates, indices, and xi values for a 2-triangle square on the XY plane centered on the origin
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
    '''Assert that all values in the image object `obj' are not NaN.'''
    for i,img in enumerate(obj.images):
        for n,m in matIterate(img.img):
            v=img.img.getAt(n,m)
            assert not math.isnan(v), 'Found NaN in object %s, image %i at %i,%i'%(obj.getName(),i,n,m)
    

def rescaleArray(arr,minv=0.0,maxv=1.0,dtype=np.float32):
    '''Rescale the values of numpy array `arr' to be from `minv' to `maxv'.'''
    if dtype is not None:
        arr=arr.astype(dtype)
        
    mina=np.min(arr)
    maxa=np.max(arr)
    
    if mina==maxa:
        return arr*maxv
    
    norm=(arr-mina)/(maxa-mina) # normalize the array first
    return (norm*(maxv-minv))+minv # rescale by minv and maxv, which is the normalized array by default


@contextlib.contextmanager
def processImageNp(imgobj,writeBack=False,dtype=np.float):
    '''
    Given an ImageSceneObject instance `imgobj', this manager yields the 4D numpy array of type `dtype' containing the 
    image data in XYZT (column/row/depth/time) dimensional ordering. This allows the array to be modified which is then 
    written back into the object once the context exits if `writeBack' is True. The array is fresh thus can be retained 
    outside the context.
    '''
    shape=imgobj.getArrayDims()
    im=np.ndarray(shape,dtype)
    timeseqs=imgobj.getVolumeStacks()

    # read the image data from the SharedImage objects in `imgobj' in the correct spatial order
    for t,ts in enumerate(timeseqs): # each stack should represent a timestep which are given in temporal order
        for d,dd in enumerate(ts): # each stack is in bottom-up order so fill im with the data from the SharedImage matrix
            arr=np.asarray(imgobj.images[dd].img).astype(dtype).T # RealMatrix is stored in transposed order
            assert arr.shape==shape[:2]
            im[:,:,d,t]=arr
    
    yield im
    
    # is writeBack is True, write the image data in im back to the SharedImage objects in `imgobj'
    if writeBack:
        imgobj.imagerange=(im.min(),im.max()) # reset the stored image range
        for t,ts in enumerate(timeseqs):
            for d,dd in enumerate(ts):
                arr=im[:,:,d,t]
                img=imgobj.images[dd]
                img.setMinMaxValues(arr.min(),arr.max())
                np.asarray(img.img)[:,:]=arr.T


def transposeRowsColsNP(img):
    '''Return `img' with indices 0 and 1 transposed, sued for converting between row- or column-majored image volumes.'''
    #neworder=[1,0]+list(range(2,img.ndim))
    #return np.transpose(img,neworder)
    return np.swapaxes(img,0,1)


def reverseAxes(img):
    '''Reverse the axes of numpy array `img'.'''
    return np.transpose(img,list(reversed(range(img.ndim))))
	

def sampleImageRay(img,start,samplevec,numsamples):
    '''Sample `numsamples' values from `img' starting from `start' in direction of `samplevec' (both in matrix coords).'''
    samples=[]
    for i in range(numsamples):
        pos=start+samplevec*(float(i+1)/numsamples)
        n=int(0.5+pos.y())
        m=int(0.5+pos.x())

        if not validIndices(img,n,m):
            break

        samples.append(img.getAt(n,m))

    return samples


def loadImageFile(filename,imgobj,pos=vec3(),rot=rotator(),spacing=(1.0,1.0)):
    '''Returns a SharedImage object containing the image data from `imgobj' which must have a fillRealMatrix(mat) method.'''
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

    imgq=queue.Queue()
    numthreads=1
    threads=[]
    results=[]

    if task:
        task.setMaxProgress(len(files))

    for n in range(numthreads):
        start,end=Utils.partitionSequence(len(files),n,numthreads)
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
    '''Create a test pattern on an otherwise blank image stack made with generateImageStack().'''
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
    '''Create a sphere image on an otherwise blank image stack made with generateImageStack().'''
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
        renderer.calculateImageHistogram(imgs[i-process.startval].img,hist,minv)

    return hist


def calculateImageStackHistogram(imgs,minv=None,maxv=None,task=None):
    if isinstance(imgs,ImageSceneObject):
        imgs=imgs.images

    #if minv==None or maxv==None:
    #   minv,maxv=minmax(((i.imgmin,i.imgmax) for i in imgs),ranges=True)

    imgmin,imgmax=minmax(((i.imgmin,i.imgmax) for i in imgs),ranges=True)
    if minv!=None:
        imgmin=min(imgmin,minv)
    if maxv!=None:
        imgmax=max(imgmax,maxv)

    results=calculateImageStackHistogramRange(len(imgs),0,task,imgs,int(imgmin),int(imgmax),partitionArgs=(imgs,))

    hists=list(results.values())
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
    hist=np.asarray(hist)

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
#   '''
#   Returns True if the list of ShareImage objects `imgs' represents a volume of CT data. This is done by measuring
#   where in the image histogram half the values fall. If this point is 20% along the range from the minimal to maximal
#   position in the histogram, this is a CT image. If `hist' is not None, this RealMatrix is used as the histogram,
#   otherwise one is calculated from `imgs'.
#   '''
#   hist=matrixToList(hist or calculateImageStackHistogram(imgs,minv,maxv))
#
#   hmin,hmax=minmax(hist)
#   if hmin>=0 and hmax<20: # trivially small numbers
#       return False
#
#   hmin=first(i for i,v in enumerate(hist) if v>0)
#   hmax=last(i for i,v in enumerate(hist) if v>0)
#   hsum=sum(hist)
#
#   hist[hmin]=0
#   halfsum=0
#   halfind=0
#   for i in xrange(len(hist)):
#       halfsum+=hist[i]
#       if halfsum>hsum/2:
#           halfind=i
#           break
#
#   return lerpXi(halfind,hmin,hmax)>0.2

    maximi,minimi=getHistogramExtremas(hist or calculateImageStackHistogram(imgs,minv,maxv))
    return len(maximi)>3


def getLargestMaskObject(mask):
    '''Given a numpy array `mask' containing a binary mask, returns an equivalent array with only the largest mask object.'''
    labeled,numfeatures=scipy.ndimage.label(mask) # generate a feature label
    sums=scipy.ndimage.sum(mask,labeled,list(range(numfeatures+1))) # sum the pixels under each label
    maxfeature=np.where(sums==max(sums)) # choose the maximum sum whose index will be the label number
    return mask*(labeled==maxfeature)


@timing
def calculateMotionField(obj):
    '''Returns a motion field array from time-dependent image `obj'.'''
    if not obj.isTimeDependent:
        raise ValueError('Image object %r must be time-dependent for calculating motion ROI.'%obj.getName())
        
    with processImageNp(obj,False) as mat:
        return calculateMotionFFT(mat)


def calculateMotionFFT(imgmat):
    '''
    Given a 4D image array `imgmat', calculate the motion representation using fourier transforms to determine where 
    motion is present. The result is a 3D image with dimensions of `obj' with areas of motion having higher intensity.
    
    see: Lin et. al, "Automated Detection of Left Ventricle in 4D MR Images: Experience from a Large Study"
    '''
    assert imgmat.ndim==4
    assert imgmat.shape[3]>1
    out=np.zeros(imgmat.shape[:3],np.float32)
        
    for i in range(imgmat.shape[2]):
        ff=scipy.fftpack.fftn(imgmat[:,:,i,:].transpose(2,0,1))
        iff=np.absolute(scipy.fftpack.ifftn(ff[1:]))
        out[:,:,i]=np.sum(iff,axis=0)
        
    return out


def generateMotionMask(motion,percentile=90,filterSize=10):
    '''
    Given a 3D image `motion' containing the FFT motion representation, generate a mask image of the same dimensions
    containing the area of motion greater than the given percentile which is then filtered with maximum filter of size
    `filterSize'. A larger `percentile' keeps less motion while a larger `filterSize' increases the bounds around the 
    selected motion area of interest.
    '''
    result=np.zeros_like(motion)

    for i in range(motion.shape[-1]):
        m=motion[...,i]>np.percentile(motion[...,i],percentile)
        m=scipy.ndimage.binary_erosion(m,iterations=1)
        m=getLargestMaskObject(m)
        m=scipy.ndimage.maximum_filter(m, size=filterSize)
        m=generateMaskConvexHull(m)
        result[...,i]=m
    
    return result


def generateMaskConvexHull(mask):
    '''Returns a convex hull mask image covering the non-zero values in 2D/3D image `mask'.'''
    origshape=mask.shape
    mask=np.squeeze(mask) # if a 2D image is presented as a 3D image with depth 1 this must be compressed
    region=np.argwhere(mask>0) # select non-zero points on the mask image
    
    if region.shape[0]==0: # an empty mask produces an empty hull
        return np.zeros(origshape,mask.dtype)
    
    hull=scipy.spatial.ConvexHull(region) # define the convex hull
    de=scipy.spatial.Delaunay(region[hull.vertices]) # define a triangulation of the hull
    simplexpts=de.find_simplex(np.argwhere(mask==mask)) # do an inclusion test for every point of the mask
    
    # reshape the points to the original's shape and mask by valid values
    return (simplexpts.reshape(origshape)!=-1).astype(mask.dtype) 


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
def cropVolumeMask(imgobj,mask,threshold,task=None):
    '''
    Crop the image `imgobj' to the boundbox of voxels in `mask' greater than or equal to `threshold'. This assumes the 
    image objects are colinear (ie. same shape). Returns the cropped copy of `imgobj'.
    '''
    vols=imgobj.getVolumeStacks()
    if not imgobj.isTimeDependent or len(vols)==1:
        raise ValueError("ImageSceneObject `imgobj' must be time-dependent")

    minx,miny,maxx,maxy=calculateStackClipSq(mask,threshold)
    outobj=imgobj.plugin.cropXY(imgobj,imgobj.getName()+'VCrop',minx,miny,maxx,maxy)

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
        images=[i for i in images if i.imgmax>=threshold]

    clipsq=calculateStackClipSq(images,threshold)
    newobj=ImageSceneObject(name,obj.source,images,obj.plugin,obj.isTimeDependent)
    if clipsq!=(0,0,cols-1,rows-1):
        minx,miny,maxx,maxy=clipsq
        minx=max(0,minx-xymargins/2)
        miny=max(0,miny-xymargins/2)
        maxx=min(cols-1,maxx+xymargins/2)
        maxy=min(rows-1,maxy+xymargins/2)
        newobj=newobj.plugin.cropXY(newobj,name,minx,miny,maxx,maxy)

    return newobj
    
    
def cropRefImage(obj,ref,name,marginx=0,marginy=0):
    '''
    Crop the image `obj' to the spatial boundbox of `ref' with added (X,Y) margins `marginx' and `marginy'. 
    Returns the cropped image with name `name'.
    '''
    trans=obj.getVolumeTransform()
    tinv=trans.inverse()
    maxcols=obj.maxcols
    maxrows=obj.maxrows
    
    corners=listSum(i.getCorners() for i in ref.images)
    aabb=BoundBox([tinv*c for c in corners])
    
    minx=clamp(aabb.minv.x()*maxcols-marginx,0,maxcols-1)
    maxx=clamp(aabb.maxv.x()*maxcols+marginx,0,maxcols-1)
    miny=clamp(aabb.minv.y()*maxrows-marginy,0,maxrows-1)
    maxy=clamp(aabb.maxv.y()*maxrows+marginy,0,maxrows-1)
    
    return obj.plugin.cropXY(obj,name,int(minx),int(miny),int(maxx),int(maxy))


def cropMotionImage(obj,name,percentile=90,filterSize=10):
    '''Returns a copy of `obj' cropped in XY using motion info from calculateMotionField(obj).'''
    motion=calculateMotionField(obj)
    mask=generateMotionMask(motion,percentile,filterSize)
    inds=scipy.ndimage.find_objects(mask)[0]
    return obj.plugin.cropXY(obj,name,inds[0].start, inds[1].start, inds[0].stop, inds[1].stop)
  

def maskMotionImage(obj,name,percentile=90,filterSize=10):
    motion=calculateMotionField(obj)
    mask=generateMotionMask(motion,percentile,filterSize)
    
    out=obj.plugin.clone(obj,name)
    
    return out
    

def centerImagesLocalSpace(obj):
    '''Moves `obj' so that its boundbox center is at the origin.'''
    for i in obj.images:
        i.position-=obj.aabb.center
        i.calculateDimensions()

    obj.aabb=BoundBox(Utils.matIter(s.getCorners() for s in obj.images))


@timing
def normalizeImageData(obj):
    '''Rescales the image data of `obj' to be in the unit range.'''
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
        i.setMinMaxValues(*renderer.minmaxMatrixReal(i.img))


def sampleImageVolume(obj,pt,timestep,transinv=None):
    '''
    Sample the image volume `obj' at the given point in world space and time, returning 0 if the point is outside the
    volume. The value `transinv' should be the inverse transform of the object's volume, if this is None then the
    transform is queried from `obj', therefore this is an optional optimization value only.
    '''
    transinv=transinv or obj.getVolumeTransform().inverse()
    inds=obj.getNearestTimestepIndices(timestep)
    images=[obj.images[i].img for i in inds]
    return renderer.getImageStackValue(images,transinv*pt)
    
    
def calculateReprIsoplaneMesh(rep,planetrans,stackpos,slicewidth):
    '''
    Calculates the mesh for image representation object `rep' at plane `planetrans' and at the stack position `stackpos' 
    (which is meaningful only for ImageSeriesRepr types). This will determine where `rep' is intersected by `planetrans' 
    and returns the triple (nodes,indices,xis) representing a mesh for that intersecting geometry. 2D images viewed at
    oblique angles produces slices which are `slicewidth' wide. Returns a (nodes,indices,xis) triple where the nodes are
    in world space coordinates.
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
        if not SceneUtils.equalPlanes(reppt,repnorm,planept,planenorm):
            et=MathDef.ElemType.Quad1NL
            heights=[n.planeDist(planept,planenorm) for n in nodes] # determine distance from each node to the view plane
            xipair=first(SceneUtils.calculateQuadIsoline(heights,et,0)) # calculate the isoline of intersection between the image plane and view plane

            if xipair: # if an isoline is found, calculate an isoline quad with a width of slicewidth
                xi1,xi2=xipair
                pt1=et.applyBasis(nodes,*xi1)
                pt2=et.applyBasis(nodes,*xi2)
                nodes=SceneUtils.generateQuadFromLine(pt1,pt2,planenorm,slicewidth)
                xis=[xi1,xi1,xi2,xi2]
            else:
                nodes=[] # otherwise given no nodes, meaning nothing to see here

    # calculate the plane mesh by slicing through the volume at the plane defined by `planetrans'
    elif isinstance(rep,ImageVolumeRepr):
        inters=rep.getPlaneIntersects(planept,planenorm,True) # get the (node,xi) pairs for the intersecting polygon
        if len(inters):
            nodes,xis=list(zip(*inters)) # divide nodes and xis into separate lists
            indices=[(0,i+1,i+2) for i in range(len(inters)-2)] # triangle fan indices

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
            renderer.interpolateImageStack(stackimgs,srctrans, img.img, img.getTransform())
            img.readMinMaxValues()


@concurrent
def mergeColinearImagesRange(process,imglist,mergefunc):
    if isinstance(mergefunc,str):
        comp=compile(mergefunc,'mergefunc','eval')
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
    imgobjs=Utils.toIterable(imgobjs)

    for o in imgobjs:
        o.setShared(True)

    objout.setShared(True)

    imglist=[] # will contain lists of colinear images
    for ind in listSum(objout.getVolumeStacks()):
        imglist.append([o.images[ind] for o in imgobjs]+[objout.images[ind]])

    minmaxes=mergeColinearImagesRange(len(imglist),0,task,imglist,mergefunc,partitionArgs=(imglist,))
    checkResultMap(minmaxes)
    minmaxes=sumResultMap(minmaxes)
    
    for n in range(len(minmaxes)):
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
            i=imgout.plugin.clone(imgout,'resampleclone'+o.getName())
            resampleImage(o,i)
            inters.append(i)

    mergeColinearImages(inters,imgout,mergefunc,task) # merge the images using the merge function
    
    # delete temporary image data, be sure not to delete `imgout'
    for i in inters: 
        if i!=imgout:
            i.clear()
    
    
def dilateImageVolume(obj,size=(5,5,5)):
    '''Dilate the image `obj' by `size' using grey dilation. This overwrites the data in `obj'.'''
    with processImageNp(obj,True) as mat:
        for i in range(mat.shape[-1]):
            mat[...,i]=scipy.ndimage.grey_dilation(mat[...,i],size)
            

@concurrent
def extendImageRange(process,imglist,mx,my,fillVal):
    images=[]
    for p in process.prange():
        img=imglist[p-process.startval]
        images.append(img.resize(mx,my,fillVal))

    return images   
    
            
@timing
def extendImage(obj,name,mx,my,mz,fillVal=0,numProcs=0,task=None):
    '''
    Extends the image `obj' by the given margins (mx,my,mz) in each dimension. The extended regions are filled with the
    value `fillVall'. The `numProcs' value is used in determining how many processes to use (0 for all). The returned
    object has name `name' and represents the same spatial data as the original plus the added margins.
    '''
    if mx==0 and my==0:
        images=[i.clone() for i in obj.images]
    else:
        obj.setShared(True)
        result=extendImageRange(len(obj.images),numProcs,task,obj.images,mx,my,fillVal,partitionArgs=(obj.images,))
        checkResultMap(result)
        images=sumResultMap(result)
        
    dz=obj.getVolumeTransform().getRotation()*(obj.getVoxelSize()*vec3(0,0,1))
    if mz>0:
        for stack in obj.getVolumeStacks():
            for i in range(1,mz+1):
                img=images[stack[0]].clone()
                img.img.fill(fillVal)
                img.position-=dz*i
                img.calculateDimensions()
                images.append(img)
                
                img=images[stack[-1]].clone()
                img.img.fill(fillVal)
                img.position+=dz*i
                img.calculateDimensions()
                images.append(img)
            
    return obj.plugin.createSceneObject(name,images,obj.source,obj.isTimeDependent)
    
    
def createTemporalImage(obj,numImgsPerStep=None, stepMul=1):
    '''
    Apply a temporal scheme to the image object `obj', assuming that the members of obj.images are in spatial then 
    temporal order but have incorrect timestep information. If `numImgsPerStep' is provided then this is used as the 
    number of images each timestep is defined by. If not provided this can be determine for 2D planes or 3D volumes 
    by checking how many images after the first are present before another in the same location is encountered. Each 
    calculated timestep is multiplied by `stepMul' when set for each new image. Return value is a new time-dependent 
    scene object with the same image data but with timesteps set to calculated values.
    '''
    imgs=[i.clone() for i in obj.images]
    
    if not numImgsPerStep is None:
        numImgsPerStep=first(i for i in range(1,len(imgs)) if imgs[0].position==imgs[i].position)
        
    for i in range(len(imgs)):
        imgs[i].timestep= (i//numImgsPerStep)*stepMul
        
    return obj.plugin.createSceneObject(obj.name+'TS',imgs,obj.source,True)
    
    