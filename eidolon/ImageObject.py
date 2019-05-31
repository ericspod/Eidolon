# Eidolon Biomedical Framework
# Copyright (C) 2016-8 Eric Kerfoot, King's College London, all rights reserved
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


from . import Utils
from . import renderer

from .renderer import vec3, transform, rotator, color, RealMatrix, ColorMatrix, TF_RGBA32, minmaxMatrixReal, getPlaneXi
from .Utils import trange, minmax, epsilon, avg, avgspan, clamp,first, indexList, isMainThread, radCircularConvert, listSum
from .Concurrency import concurrent
from .SceneUtils import BoundBox, RenderQueues, generatePlane
from .SceneObject import SceneObject, SceneObjectRepr,ReprType


#ImageType=enum(
#   ('Default','Default Image Type'),
#   ('CT','CT Image Series')
#)


def isImageVolume(images,err=1e-3):
    '''
    Returns True if the list of ShareImage objects `images' defines a single image volume, that is the positions of all
    the images fall on a single common line and the images have a common orientation. The margin of error for calculating
    these criteria is `err', which is a rather large value to account for Dicom inaccurracy.
    '''
    if len(images)==1:
        return True

    _,start,end=max((i.position.distTo(j.position),i.position,j.position) for i in images for j in images)
    diags=[i.center-i.position for i in images]

    sameaxis=all(0<=i.position.lineDist(start,end)<=err for i in images)
    samenorm=all(abs(i.norm.angleTo(start-end))<=err or abs(i.norm.angleTo(end-start))<=err for i in images)
    samediags=all(d.distTo(diags[0])<=err for d in diags)

    if not sameaxis and samenorm and samediags:
        #printFlush(images,sameaxis,samenorm,samediags)
        return False

    return True


def sortImageStack(images):
    '''Returns an indices list indexing the images in list `images' in bottom-up order.'''
    #assert isImageVolume(images)
    positions=[i.position for i in images]
    maxdist=max(i.distTo(j) for i in positions for j in positions)
    farpoint=positions[0]-images[0].norm*maxdist*2 # guaranteed to be a point below the stack
    return sorted(range(len(images)),key=lambda i:positions[i].distTo(farpoint))


@concurrent
def calculateStackClipSqRange(process,imgs,threshold):
    cols,rows=imgs[0].dimensions
    minx=cols-1
    miny=rows-1
    maxx=0
    maxy=0

    for i in process.prange():
        result=renderer.calculateBoundSquare(imgs[i].img,threshold)
        if result:
            minx=min(minx,result[0])
            miny=min(miny,result[1])
            maxx=max(maxx,result[2])
            maxy=max(maxy,result[3])

    return minx,miny,maxx,maxy


def calculateStackClipSq(imgs,threshold,margin=2,task=None):
    '''
    Calculates the (minx,miny,maxx,maxy) square in image space which encloses all values for the given images which
    are greater than or equal to `threshold'. The list `imgs' must contain only SharedImage objects.
    '''
    cols,rows=imgs[0].dimensions
    minx=cols-1
    miny=rows-1
    maxx=0
    maxy=0

    result=calculateStackClipSqRange(len(imgs),1,task,imgs,threshold)

    for minx1,miny1,maxx1,maxy1 in result.values():
        minx=min(minx,minx1)
        miny=min(miny,miny1)
        maxx=max(maxx,maxx1)
        maxy=max(maxy,maxy1)

    return max(minx-margin,0),max(miny-margin,0),min(maxx+margin,cols-1),min(maxy+margin,rows-1)


class SharedImage(object):
    '''Represents a loaded image with pixel data stored in a shared RealMatrix object.'''

    def __init__(self,filename,position,orientation,dimensions,spacing=(1.0,1.0),timestep=0,img=None,imgmin=0.0,imgmax=0.0):
        self.filename=filename
        self.position=position # top left corner, in mm
        self.orientation=orientation # rotation in the center, rotator
        self.dimensions=dimensions # (columns, rows) image dimensions, should match self.img dimensions
        self.spacing=spacing # (X,Y) pixel size in mm
        self.timestep=timestep # time in milliseconds
        self.img=img # image data, stored in transposed row-column or YX index order so self.img[Y,X] is the pixel at (X,Y) in the image
        self.imgmin=imgmin
        self.imgmax=imgmax
        self.calculateDimensions()

        if self.img!=None:
            assert (self.img.m(),self.img.n())==self.dimensions,'%r!=%r'%((self.img.m(),self.img.n()),self.dimensions)

    def calculateDimensions(self):
        '''
        Calculates `dimvec', `orientinv', `norm', and `center' from `position' and `orientation'. Call this after
        changing either of these members.
        '''
        # dimension vector, represents far corner of unrotated plane
        self.dimvec=vec3(self.dimensions[0]*self.spacing[0],-self.dimensions[1]*self.spacing[1])
        self.orientinv=self.orientation.inverse() # inverse of the orientation
        self.norm=self.orientation*vec3(0,0,1) # normal of plane
        self.center=self.position+self.orientation*(self.dimvec*0.5) # center of plane

    def setShared(self,isShared):
        if self.img!=None:
            self.img.setShared(isShared)

    def clone(self):
        img=self.img.clone(None,self.img.isShared()) if self.img else None
        return SharedImage(self.filename,self.position,self.orientation,self.dimensions,self.spacing,self.timestep,img,self.imgmin,self.imgmax)

    def crop(self,minx,miny,maxx,maxy):
        '''Crop the image from image index (minx,miny) to (maxx-1,maxy-1) inclusive.'''
        assert self.img

        xi=vec3(float(minx)/self.dimensions[0],float(miny)/self.dimensions[1])
        newpos=self.getPlanePos(xi)
        rows=maxy-miny
        cols=maxx-minx
        newimg=self.img.subMatrix(self.img.getName()+'crop',rows,cols,miny,minx,self.img.isShared())
        newmin,newmax=minmaxMatrixReal(newimg)
        return SharedImage(self.filename,newpos,self.orientation,(cols,rows),self.spacing,self.timestep,newimg,newmin,newmax)

    def resize(self,x,y,fillVal=0):
        '''
        Extend or contract the image by `x' pixels on the left and right and `y' pixels on the top and bottom. This
        will change the column count by x*2 and row count by y*2.
        '''
        newpos=self.getPlanePos(vec3(-x-0.5,-y-0.5),False)
        rows=2*y+self.dimensions[1]
        cols=2*x+self.dimensions[0]
        newimg=RealMatrix(self.img.getName()+'resize',rows,cols,self.img.isShared())

        for n,m in trange(rows,cols):
            ny=n-y
            mx=m-x
            if 0<=ny<self.img.n() and 0<=mx<self.img.m():
                newimg.setAt(self.img.getAt(ny,mx),n,m)
            else:
                newimg.setAt(fillVal,n,m)

        if x>0 or y>0:
            newmin,newmax=minmax(fillVal,self.imgmin,self.imgmax)
        else:
            newmin,newmax=minmaxMatrixReal(newimg)

        return SharedImage(self.filename,newpos,self.orientation,(cols,rows),self.spacing,self.timestep,newimg,newmin,newmax)

    def allocateImg(self,name,isShared=False):
        cols,rows=self.dimensions
        self.img=RealMatrix(name,'',rows,cols,isShared)

    def deallocateImg(self):
        if self.img!=None:
            self.img.clear()
            self.img=None
            self.imgmin=0.0
            self.imgmax=0.0
            
    def setArrayImg(self,arr):
        assert arr.shape==self.dimensions[::-1]
        self.setMinMaxValues(arr.min(),arr.max())
        self.img[:,:]=arr[:,:]

    def setMinMaxValues(self,minv,maxv):
        if self.img:
            self.img.meta('min',str(minv))
            self.img.meta('max',str(maxv))
        self.imgmin=minv
        self.imgmax=maxv

    def readMinMaxValues(self):
        if self.img:
            self.imgmin=float(self.img.meta('min') or 0)
            self.imgmax=float(self.img.meta('max') or 0)

    def memSize(self):
        return self.img.memSize() if self.img else 0

    def isParallel(self,otherimg,err=epsilon):
        '''Returns True if thsi image is parallel with the image `otherimg'.'''
        return self.norm.angleTo(otherimg.norm)<=err

    def isSameLocation(self,otherimg,err=epsilon):
        return self.isParallel(otherimg,err) and self.position.distTo(otherimg.position)<err

    def getDist(self,pos):
        return pos.planeDist(self.position,self.norm)

    def getPlaneXi(self,pos):
        '''
        Converts a vector `pos' into a xi value on the image plane with the result's z value being the distance
        from the plane, positive values above and negative below. Top left corner is (0,0,0), bottom right (1,1,0).
        '''
        return getPlaneXi(pos,self.position,self.orientinv,self.dimvec)

    def getPlaneDir(self,pos):
        '''Returns the directional vector `pos' as the equivalent direction in plane xi coordinates.'''
        return (self.orientinv*pos)*(self.dimvec+vec3(0,0,1))

    def getPlanePos(self,pos,isXiCoord=True,rotate=True):
        '''Converts a point (plane xi coord if isXiCoord is true, image matrix index otherwise) into a world position.'''
        if isXiCoord:
            pos*=self.dimvec
        else:
            pos=(pos+vec3(0.5,0.5))*vec3(self.spacing[0],-self.spacing[1])

        if rotate:
            pos=self.orientation*pos

        return self.position+pos

    def getPlanePosTransform(self,isXiCoord=True,rotate=True):
        return transform(self.position,self.dimvec if isXiCoord else vec3(self.spacing[0],-self.spacing[1]), self.orientation if rotate else rotator())

    def getCorners(self):
        pos=self.position
        o=self.orientation
        dx,dy,_=self.dimvec
        return [pos,pos+o*vec3(dx,0),pos+o*vec3(0,dy),pos+o*vec3(dx,dy)]

    def getRayIntersect(self,ray):
        '''Returns the image xi coordinates of where the ray intersects the image, or None if no intersection.'''
        inter=ray.intersectsPlane(self.center,self.norm)

        if 0<=inter<float('inf'):
            return self.getPlaneXi(ray.getPosition(inter))
        else:
            return None

    def getTransform(self):
        '''Get the transformation from unit quad to the image quad in world space.'''
        return transform(self.position,self.dimvec,self.orientation)

    def setTransform(self,trans):
        '''
        Apply the transform object `trans' to this image. The translation component is used as the new position, the
        voxel size is scaled by the scale component (ie. scale of (1,1,1) preserves voxel size), and the rotational
        component is used as the orientation.
        '''
        self.position=trans.getTranslation()
        self.orientation=trans.getRotation()
        space=trans.getScale()*vec3(*self.spacing)
        self.spacing=(space.x(),space.y())
        self.calculateDimensions()

    def __str__(self):
        return '<SharedImage %xi, Pos: %r, Orient: %r, Dims: %r, Spacing: %r, TS: %r>'%(id(self),self.position,self.orientation,self.dimensions,self.spacing,self.timestep)


class ImageSceneObject(SceneObject):
    def __init__(self,name,source,images,plugin=None,isTimeDependent=None,**kwargs):
        SceneObject.__init__(self,name,plugin,**kwargs)
        if isinstance(source,(list,tuple)):
            self.source=list(source)
        elif isinstance(source,dict):
            self.source=dict(source)
        else:
            self.source=source

        self.kwargs['source']=source

        assert len(images)>0,'Empty series: '+name

        self.images=list(images)
        self.alphamasks=None # list of RealMatrix images, one for each in self.images, used as alpha masks, or None to not use masks

        self.is2D=sum([self.images[0].position-i.position for i in self.images],vec3()).isZero()
        self.isTimeDependent=isTimeDependent
        self.maxrows=max(s.img.n() for s in images)
        self.maxcols=max(s.img.m() for s in images)
        self.imagerange=None # range of possible image values, should be pair (minval,maxval) or None
        self.aabb=None
        self.histogram=None

        if isTimeDependent==None:
            #self.isTimeDependent=len(images)>1 and any(images[0].isSameLocation(i) for i in images[1:])
            self.isTimeDependent=len(images)>1 and any(images[0].timestep!=i.timestep for i in images[1:])

        self.calculateAABB()

    def calculateAABB(self,overwrite=False):
        if overwrite or not self.aabb:
            self.aabb=BoundBox(Utils.matIter(s.getCorners() for s in self.images))
            
    def calculateImageRange(self):
        self.imagerange=None
        
        for i in self.images:
            i.setMinMaxValues(*minmaxMatrixReal(i.img))

    def clear(self):
        for i in self.images:
            i.deallocateImg()

    def setShared(self,isShared):
        for i in self.images:
            i.setShared(isShared)

    def getDataset(self):
        return list(self.images)

    def getImageRange(self):
        '''Returns the stored minimal and maximal values that would be expected in image data.'''
        if self.imagerange is None or self.imagerange[0]==self.imagerange[1]:
            self.imagerange=self.getRealImageRange()

        return self.imagerange

    def getRealImageRange(self):
        '''Get actual minimal and maximal image values as stored in the SharedImage objects themselves.'''
        return minmax(((i.imgmin,i.imgmax) for i in self.images),ranges=True)

    def getArrayDims(self):
        '''Get the 4 dimensions (columns, rows, height, time) for a 4D array containing the volume image data.'''
        inds=self.getTimestepIndices()
        return (self.maxcols,self.maxrows,len(inds[0][1]),len(inds))

    def getVoxelSize(self):
        '''Get the size of each voxel in the volume in world space units.'''
        stack=self.getVolumeStacks()
        if len(stack)==0:
            return vec3()

        stack0=stack[0][:2]
        img0=self.images[stack0[0]]
        img1=self.images[stack0[-1]] # either next in stack or same as img0
        return vec3(img0.spacing[0],img0.spacing[1],img0.position.distTo(img1.position))

    def getVolumeTransform(self,make2DVol=True):
        '''
        Get the transform from the unit cube to the hexahedron in world space defined by the image volume. if the image
        is 2D and `make2DVol', the transform defined a 3D volume as thick as the largest pixel spacing value instead of
        a 2D plane in space.
        '''
        stack=self.getVolumeStacks()
        if len(stack)==0:
            return transform()

        img0=self.images[stack[0][0]]
        img1=self.images[stack[0][-1]] # same as img0 if is2D
        
        pos=img0.position
        scale=img0.dimvec+vec3(0,0,img0.position.distTo(img1.position))
        
        if self.is2D and make2DVol: # define the 2D plane as a thin volume instead for mathematical reasons
            depth=max(abs(img0.spacing[0]),abs(img0.spacing[1]))*2 # fabricate a thickness value for the 2D plane
            pos-=img0.norm*(depth*0.5)
            scale+=vec3(0,0,depth)

        return transform(pos,scale,img0.orientation)
    
    def getTransform(self):
        '''Return the actual image transform, defining a 3D volume for 3D images and 2D plane for 2D images.'''
        return self.getVolumeTransform(False)

    def setTransform(self,trans):
        '''
        Apply the transform object `trans' to this object. If this is a 2D object, `trans' is applied to every image
        directly. If 3D, the translation component is used as the new origin, the voxel size is scaled by the scale
        component (ie. scale of (1,1,1) preserves voxel size), and the rotational component is used as the orientation.
        '''
        if self.is2D:
            for i in self.images:
                i.setTransform(trans)
        else:
            pos=trans.getTranslation()
            scale=trans.getScale()
            rot=trans.getRotation()
            dpos=rot*vec3(0,0,scale.z()*self.getVoxelSize().z())

            for inds in self.getVolumeStacks():
                for i,ind in enumerate(inds):
                    self.images[ind].setTransform(transform(pos+dpos*i,scale,rot))

        self.calculateAABB(True)

    def getVolumeCorners(self):
        '''Get the 8 corner vectors of the image volume.'''
        stack=self.getVolumeStacks()
        if len(stack)==0:
            return [vec3()]

        img0=self.images[stack[0][0]]
        img1=self.images[stack[0][-1]]

        return img0.getCorners()+img1.getCorners()

    def getTimestepList(self):
        '''Returns the list of timestep values for each step of this image.'''
        ts=[i[0] for i in self.getTimestepIndices()]
        if len(ts)%2==0 and all(ts[i]==ts[i-1] for i in range(1,len(ts),2)):
            return ts[::2] # if timesteps are duplicated (eg. magnitude+phase series) remove the duplicates
        else:
            return ts

    def setTimestepList(self,timesteps):
        '''Set the timestep values for the frames of this image, `timesteps' must be as long as there are frames.'''
        orientlists=list(self.getTimeOrientMap().values())
        #if not self.isTimeDependent or len(orientlists)==0:
        #   return

        assert len(orientlists[0])==len(timesteps),'%i != %i'%(len(orientlists[0]),len(timesteps))

        for i,ts in enumerate(timesteps):
            for olist in orientlists:
                self.images[olist[i]].timestep=ts

    def getOrientMap(self):
        '''
        Returns a map from rotators to lists of numbers indexing each image having that orientation. The ordering of
        the indices is dependent on the ordering of self.images.
        '''
        orientmap={}
        for i,img in enumerate(self.images):
            orient=first(o for o in orientmap.keys() if o==img.orientation)
            if orient:
                orientmap[orient].append(i)
            else:
                orientmap[rotator(img.orientation)]=[i]

        return orientmap

    def getTimeOrientMap(self):
        '''
        Returns a map from (vec3,rotator) pairs to the indices of all images (in temporal order) having that
        position and orientation. Each value in the map thus indexes the images defining a 2D slice in time. The
        ordering of the indices is depedent on the ordering of self.images if multiple colocated images have the 
        same timestep.
        '''
        timeorientmap={}
        for i,img in enumerate(self.images):
            key=first((im,o) for im,o in timeorientmap if im==img.position and o==img.orientation)
            if key!=None:
                timeorientmap[key].append(i)
            else:
                timeorientmap[(img.position,img.orientation)]=[i]

        for tom in timeorientmap.values():
            tom.sort(key=lambda i:self.images[i].timestep)

        return timeorientmap

    def getTimestepIndices(self):
        '''
        Returns a list of pairs containing the time for each timestep (ie. the average timing value of the images
        defining the timestep) and a list if image indices for those images at that time. If this image is not time-
        dependent, then each member of the list has the same time value but represents an independent image series
        which are differentiated by position and orientation. The indices are always sorted in stack order. If multiple 
        stacks define volumes at the same position and time they will be listed one after the other. The ordering of the 
        indices is dependent on the ordering of self.images. 2D image series are treated as single image stacks, so the 
        result will be a list of lists containing single indices.
        '''

        timesteps=[]
        if not self.isTimeDependent:
            ts=self.images[0].timestep
            for inds in self.getOrientMap().values():
                sortorder=sortImageStack(indexList(inds,self.images))
                timesteps.append((ts,indexList(sortorder,inds)))
        else:
            orientlists=list(self.getTimeOrientMap().values())

            if len(orientlists)>0:
                for ts in range(len(orientlists[0])): # ts is the index of a timestep,
                    #TODO: is this really needed? Can `inds' get by with differing lengths
                    # this ensures that all timesteps have the same number of images
                    #assert all(ts<len(olist) for olist in orientlists),'Not all orient lists have value for timestep %s\norient list lengths are: %r'%(ts,map(len,orientlists))

                    inds=[olist[ts] for olist in orientlists if ts<len(olist)] # indices of all images for this timestep
                    images=indexList(inds,self.images) # get the SharedImage objects
                    
                    sortorder=sortImageStack(images) # determine the ordering of the images by trying to sort into a bottom-up stack
                    avgstep=avg(i.timestep for i in images) # averaged timestep value for these images
                    timesteps.append((avgstep,indexList(sortorder,inds))) # add the sorted indices

        return timesteps

    def getVolumeStacks(self):
        '''
        Returns lists of index lists referring to the members of `images' which define volumes. Each member list indexes
        the images for a volume in bottom-up order. If this object is time-dependent then each member list of the
        returned list represents a stack for each timestep, and are given in temporal order. If the object is not
        time-dependent, then each member list represents an independent stack in the series of images differentiated
        by orientation and given in an arbitrary order. If multiple stacks define volumes at the same position and time
        they will be listed together, so a list of indices in the returned list may define multiple overlaying volumes.
        The ordering of the indices in the returned list depends on the order of images in self.images. 2D image series
        are treated as single image stacks, so the result will be a list of lists containing single indices.
        '''
        return [stack for _,stack in self.getTimestepIndices()]

    def getPropTuples(self):
        if len(self.proptuples)==0:
            ts=self.getTimestepList()
            if len(ts)>1:
                ts='%i, start: %.3f, step: %.3f'%(len(ts),ts[0],avgspan(ts))
            else:
                ts='Static at time %i'%self.images[0].timestep

            memtotal=sum(i.memSize() for i in self.images)

            self.proptuples= [
                ('Num Images',str(len(self.images))),
                ('Rows',str(self.maxrows)),
                ('Columns',str(self.maxcols)),
                ('Boundbox',str(self.aabb)),
                ('Timesteps',ts),
                ('Mem Total',Utils.getUnitValue(memtotal))
            ]

            if isinstance(self.source,dict):
                self.proptuples+=sorted((str(k),str(v).strip()) for k,v in self.source.items())

        return self.proptuples

    def getNearestTimestepIndices(self,timestep):
        return min( (abs(timestep-ts),ilist) for ts,ilist in self.getTimestepIndices() )[1]


class ImageSceneObjectRepr(SceneObjectRepr):
    def __init__(self,parent,reprtype,reprcount,imgmaterial,imgmatrices=[],texformat=TF_RGBA32,useSpecTex=True):
        '''
        Construct a representation of the ImageSceneObject `parent'. This has representation type `reprtype', is
        numbered `reprcount' in the list of representations for `parent', uses the material `imgmaterial' to generate
        texture data, and will generate texture data from the matrices `imgmatrices' which has one entry for each
        SharedImage element in parent.images. The textures are created with format `texformat' which is typically
        TF_RGBA32 or TF_ALPHALUM8. If `useSpecTex' is True then intenal materials will use spectrum textures to
        implement a color transfer function.
        '''
        assert imgmaterial!=None
        SceneObjectRepr.__init__(self,parent,reprtype,reprcount,imgmaterial.getName())
        self.position=vec3()
        self.scale=vec3(1,1,1)
        self.rotation=(0.0,0.0,0.0)
        self.aabb=self.parent.aabb
        self.imgmat=imgmaterial
        self.texformat=texformat
        self.useSpecTex=useSpecTex # True to use spectrum textures in materials
        self.mulAlpha=self.parent.alphamasks==None # True to multiple color alpha values by their magnitudes when filling in textures

        self.images=self.parent.images # image objects stored in parent
        # image matrix data to use, may be same as those in the SharedImage objects in parent or different if filtered
        self.imgmatrices=imgmatrices or [i.img for i in self.images] # one matrix for each image, may be ColorMatrix or RealMatrix

        assert len(self.images)==len(self.imgmatrices)
        assert all(type(self.imgmatrices[0])==type(m) for m in self.imgmatrices)

        self.timestep=0
        self.timestepIndex=0 # index in self.timesteplist corresponding to the current timestep
        self.timesteplist=[]

    def isTransparent(self):
        '''Returns True if any image is rendered with any transparency.'''
        return True

    def getTimestepList(self):
        return [t for t,l in self.timesteplist]

    def getTimestep(self):
        return self.timestep

    def getCurrentTimestepIndices(self):
        '''Get the image indices of the current timestep.'''
        return self.timesteplist[self.timestepIndex][1]

    def getCurrentTimestepMaterial(self,chosen=None):
        '''
        Get the material for the chose image component of the current timestep. The component is either an image plane
        in the stack of the current timestep, in which case the material is the one applied to that image's quad in the
        representation, or a vlume in the current timestep, in which case the material is the one applied to the volume
        object. If `chosen' is None, then an internal criteria can be use to select the component, ie. choose the first.
        '''
        pass

    def getDefinedTransform(self,chosen=None):
        '''
        Get the transform representing the chosen image component of the current timestep. The component is either an
        image plane in the stack of the current timestep, in which case the transform defines this plane in space, or
        a volume of the current timestep, in which case the transform defines this volume in space. If `chosen'
        is None, then an internal criteria can be use to select the component, ie. choose the first.
        '''
        pass

    def getNumStackSlices(self):
        return len(self.timesteplist[0][1])

    def useDepthCheck(self,val):
        for m in self.enumInternalMaterials():
            m.useDepthCheck(val)

    def useDepthWrite(self,val):
        for m in self.enumInternalMaterials():
            m.useDepthWrite(val)

    def useTexFiltering(self,val):
        for m in self.enumInternalMaterials():
            m.useTexFiltering(val)

    def usesDepthCheck(self):
        m=first(self.enumInternalMaterials())
        return m!=None and m.usesDepthCheck()

    def usesDepthWrite(self):
        m=first(self.enumInternalMaterials())
        return m!=None and m.usesDepthWrite()

    def usesTexFiltering(self):
        m=first(self.enumInternalMaterials())
        return m!=None and m.usesTexFiltering()

    def useLighting(self,useLight):
        for m in self.enumInternalMaterials():
            m.useLighting(useLight)

    def getPosition(self,isDerived=False):
        return self.position

    def getRotation(self,isDerived=False):
        return self.rotation

    def getScale(self,isDerived=False):
        return self.scale

    def _setFigureTransforms(self):
        pass

    def setPosition(self,pos):
        self.position=pos
        self._setFigureTransforms()

    def setRotation(self,yaw,pitch,roll):
        yaw=radCircularConvert(yaw)
        pitch=radCircularConvert(pitch)
        roll=radCircularConvert(roll)
        self.rotation=(yaw,pitch,roll)
        self._setFigureTransforms()

    def setScale(self,scale):
        self.scale=scale
        self._setFigureTransforms()


class ImageSeriesRepr(ImageSceneObjectRepr):
    def __init__(self,parent,reprtype,reprcount,imgmaterial, imgmatrices=[],texformat=TF_RGBA32,useSpecTex=True,**kwargs):
        ImageSceneObjectRepr.__init__(self,parent,reprtype,reprcount,imgmaterial,imgmatrices,texformat,useSpecTex)

        self.figs=[] # plane figures for each image
        self.figmats=[] # material for each figure
        self.figtextures=[] # texture for each figure

        self.chosenSlice=None # chosen slice to render exclusively, or None to render all images for a timestep

        self.timesteplist=self.parent.getTimestepIndices() # list of (timestep,indices) pairs, the indices refer to positions in self.images self.fig* and self.buffs

    def setTimestep(self,ts):
        if self.reprtype==ReprType._imgtimestack:
            self.timestep=clamp(ts,*self.getTimestepRange())
            tsdist,chosen,self.timestepIndex=min((abs(self.timestep-v),ilist,i) for i,(v,ilist) in enumerate(self.timesteplist))
            if self.chosenSlice!=None:
                chosen=[chosen[self.chosenSlice]]

            for i,f in enumerate(self.figs):
                f.setVisible(self._isVisible and i in chosen)

    def setChosenSlice(self,chosen):
        if isinstance(chosen,int):
            self.chosenSlice=clamp(chosen,0,self.getNumStackSlices())
        else:
            self.chosenSlice=None

        if self._isVisible and self.reprtype==ReprType._imgtimestack:
            self.setTimestep(self.timestep)
        else:
            for i,f in enumerate(self.figs):
                f.setVisible(self._isVisible and (chosen==None or i==chosen))

    def getCurrentTimestepMaterial(self,chosen=None):
        chosen=first(c for c in (chosen,self.chosenSlice,0) if c!=None)

        imgind=self.getCurrentTimestepIndices()[clamp(chosen,0,self.getNumStackSlices()-1)]
        return self.figmats[imgind]

    def getDefinedTransform(self,chosen=None):
        chosen=first(c for c in (chosen,self.chosenSlice,0) if c!=None)

        imgind=self.getCurrentTimestepIndices()[clamp(chosen,0,self.getNumStackSlices()-1)]
        img=self.images[imgind]

        rot=rotator(*self.rotation)
        slicetrans=transform(self.position+rot*(self.scale*img.center),self.scale*img.dimvec*vec3(1,-1,1),rot*img.orientation)

        return slicetrans

    def enumInternalMaterials(self):
        for m in self.figmats:
            yield m

    def isInScene(self):
        return len(self.figs)>0

    def getPropTuples(self):
        return [('#Images',str(len(self.imgmatrices))),('BoundBox',str(self.getAABB()))]

    def _getInteralFigures(self):
        return self.figs

    def setGPUParam(self, name,val, progtype, transformVec=False,rotateVec=False,**kwargs):
        if isinstance(val,vec3):
            trans=self.getTransform().inverse()
            tdir=trans.directional()

            for img,mat in zip(self.parent.images,self.figmats):
                if transformVec:
                    val1=img.getPlaneXi(trans*val)
                elif rotateVec:
                    val1=img.getPlaneDir(tdir*val)
                else:
                    val1=val

                mat.setGPUParamVec3(progtype,name,val1)
        else:
            kwargs['transformVec']=transformVec
            kwargs['rotatorVec']=rotateVec
            ImageSceneObjectRepr.setGPUParam(self, name,val, progtype,**kwargs)

    def removeFromScene(self,scene):
        self._isVisible=False
        for f in self.figs:
            f.setVisible(False)

        self.figs=[]
        self.figmats=[]
        self.figtextures=[]

        self.chosenSlice=None

    def setVisible(self,isVisible):
        if isVisible!=self._isVisible:
            self._isVisible=isVisible
            self.setChosenSlice(self.chosenSlice)

    def addToScene(self,scene):
        if not self.isInScene():
            fname=self.parent.getName().replace(' ','_')+str(self.reprcount)

            for i,matrix in enumerate(self.imgmatrices):
                tex=scene.createTexture(fname+'Tex'+str(i),matrix.m(),matrix.n(),0,self.texformat)
                tex.fillColor(color())

                mat=scene.createMaterial(fname+'Mat'+str(i))
                mat.useDepthCheck(True)
                mat.useDepthWrite(True)

                self.figmats.append(mat)
                self.figtextures.append(tex)

                fig=scene.createFigure(fname+' '+str(i),mat.getName(),renderer.FT_TRILIST)
                fig.setRenderQueue(RenderQueues.VolumeImg)
                self.figs.append(fig)

        self.setVisible(True)

    def _setFigureTransforms(self):
        rot=rotator(*self.rotation)

        for i,fig in enumerate(self.figs):
            fig.setPosition(self.position+rot*(self.scale*self.images[i].center))
            fig.setScale(self.scale)
            fig.setRotation(rot)

    def prepareBuffers(self):
        assert not isMainThread()

        pnodes,pindices,xis=generatePlane(0) # quad centered on origin

        pindices+=[(i,k,j) for i,j,k in pindices] # backside triangles
        ib=renderer.PyIndexBuffer(pindices)
        
        # use a spectrum material if that option is set and the image material is not present or uses a fragment program
        useSpecTex=self.useSpecTex and len(self.imgmat.getGPUProgram(renderer.PT_FRAGMENT))>0
        # multiply each pixel's alpha by the data value if that option is set and a spectrum material is not used
        mulAlpha=self.mulAlpha and not useSpecTex

        imgmin,imgmax=self.parent.getImageRange()

        for i in range(len(self.figs)):
            fig=self.figs[i]
            img=self.images[i]
            matrix=self.imgmatrices[i]
            tex=self.figtextures[i]
            mat=self.figmats[i]

            mask=self.parent.alphamasks[i] if self.parent.alphamasks else None

            orient=img.orientation
            dv=vec3(img.dimvec.x(),-img.dimvec.y(),1)# scale by absolute dimensions so that quad isn't flipped

            snodes=[orient*(n*dv) for n in pnodes]
            norms=[orient*vec3(0,0,1)]*len(snodes)

            vb=renderer.PyVertexBuffer(snodes,norms,None,xis)

            fig.fillData(vb,ib,True)
            
            self.imgmat.copyTo(mat,False,True,True) # copy details from self.imgmat to the internal material

            mat.setTexture(tex.getName())
            mat.useDepthCheck(self.usesDepthCheck())
            mat.useDepthWrite(self.usesDepthWrite())
            mat.useLighting(False)
            mat.clampTexAddress(True)
            mat.useSpectrumTexture(useSpecTex)

            colormat=None if useSpecTex else self.imgmat

            if isinstance(matrix,ColorMatrix):
                tex.fillColor(matrix,0)
            else:
                # The default values for self.useSpecTex and self.mulAlpha ensure data is filled into the
                # texture in a specific way: if useSpecTex is True then the color will be derived from a
                # spectrum texture using a fragment shader transfer function, so don't use the material to
                # assign color; if alpha mask matrices are provided then these are used for alpha values and
                # mulAlpha will be False, if no alpha masks and no spectrum texture then mulAlpha will be True
                # and the alpha value for each pixel is multipled by the pixel's data value. This ensures there
                # is some sort of alpha being stored regardless of settings and input
                tex.fillColor(matrix,0,imgmin,imgmax,colormat,mask,mulAlpha)
            

    def update(self,scene):
        assert isMainThread()
        self._setFigureTransforms()


class ImageVolumeRepr(ImageSceneObjectRepr):
    def __init__(self,parent,reprtype,reprcount,imgmaterial,imgmatrices=[],texformat=TF_RGBA32,useSpecTex=True,**kwargs):
        ImageSceneObjectRepr.__init__(self,parent,reprtype,reprcount,imgmaterial,imgmatrices,texformat,useSpecTex)
        self.numPlanes=600
        self.copySpec=imgmaterial.numSpectrumValues()>0 or imgmaterial.numAlphaCtrls()>0

        assert len(self.images)>1

        self.figs=[]
        self.figtexbb=[]
        self.figmats=[] # each figure has its own material with its own texture
        self.figtextures=[] # each figure has its own texture file
        self.figpositions=[] # figure position of min cornder
        self.figorients=[] # figure orientation
        self.figdims=[] # figure dimensions
        self.figinds=[] # list of indices of which images/matrices define the figure
        self.fighexes=[] # list of volume hexahedra represented by 6-tuples of vec3
        self.subalphas=[]

        self.timesteplist=self.parent.getTimestepIndices()

    def isInScene(self):
        return len(self.figs)>0

    def getParamDefs(self):
        return [Utils.ParamDef('numPlanes','Num Planes',Utils.ParamType._int,self.numPlanes,100,5000,100)]

    def getParam(self,name):
        if name=='numPlanes':
            return self.getNumPlanes()

    def setParam(self,name,value):
        if name=='numPlanes':
            self.setNumPlanes(value)

    def setTimestep(self,ts):
        ts=clamp(ts,*self.getTimestepRange())

        if self.reprtype==ReprType._imgtimevolume:
            tsdist,self.timestepIndex=min((abs(ts-v),i) for i,(v,l) in enumerate(self.timesteplist))
            self.timestep=ts
            for i,fig in enumerate(self.figs):
                fig.setVisible(self._isVisible and i==self.timestepIndex)

    def getCurrentTimestepMaterial(self,chosen=0):
        return self.figmats[self.timestepIndex] if self.timestepIndex<len(self.figmats) else None

    def getDefinedTransform(self,chosen=None):
        imgind=self.getCurrentTimestepIndices()[0]
        tsind=self.timestepIndex

        if imgind>=len(self.images) or tsind>=len(self.figs):
            return self.parent.getVolumeTransform()
        else:
            img=self.images[imgind]
            vdims=self.figdims[tsind]
            trans=self.figs[tsind].getPosition(True)-img.orientation*(vdims*vec3(0.5,-0.5,0))
            scale=self.figs[tsind].getScale(True)*(vdims*vec3(1,-1,1))
            rot=self.figs[tsind].getRotation(True)

            return transform(trans,scale,rot)

    def getPlaneIntersects(self,planept,planenorm,transformPlane=False,isXiPoint=False):
        if len(self.figs)<=self.timestepIndex:
            return []

        return self.figs[self.timestepIndex].getPlaneIntersects(planept,planenorm,transformPlane,isXiPoint)

    def getVolumeDims(self):
        return self.figdims[self.timestepIndex]

    def enumInternalMaterials(self):
        for m in self.figmats:
            yield m

    def _getInteralFigures(self):
        return self.figs

    def setGPUParam(self, name,val, progtype, transformVec=False,rotateVec=False,**kwargs):
        if isinstance(val,vec3):
            figmatmap=dict((ff.getMaterial(),ff) for ff in self.enumFigures())
            for m in self.enumInternalMaterials():
                mname=m.getName()
                if transformVec and mname in figmatmap:
                    val1=figmatmap[mname].getTexXiPos(val)
                elif rotateVec and mname in figmatmap:
                    val1=figmatmap[mname].getTexXiDir(val)
                else:
                    val1=val

                m.setGPUParamVec3(progtype,name,val1)
        else:
            kwargs['transformVec']=transformVec
            kwargs['rotatorVec']=rotateVec
            ImageSceneObjectRepr.setGPUParam(self, name,val, progtype,**kwargs)

    def getPropTuples(self):
        return [
            ('#Images',str(len(self.imgmatrices))),
            ('#Objects',str(len(self.figs))),
            ('Material',self.matname),
            ('BoundBox',str(self.getAABB()))
        ]

    def removeFromScene(self,scene):
        self.setVisible(False)
        self.figs=[]
        self.figtexbb=[]
        self.figmats=[]
        self.figtextures=[]
        self.figpositions=[]
        self.figorients=[]
        self.figdims=[]
        self.figinds=[]
        self.fighexes=[]
        self.subalphas=[]

    def setVisible(self,isVisible):
        if isVisible!=self._isVisible:
            self._isVisible=not self._isVisible
            if self._isVisible and self.reprtype==ReprType._imgtimevolume:
                self.setTimestep(self.timestep)
            else:
                for f in self.figs:
                    f.setVisible(self._isVisible)

    def addToScene(self,scene):
        assert isMainThread()

        if not self.isInScene():
            for ts,inds in self.timesteplist:
                num=str(len(self.figs)+1)
                fname=self.parent.getName().replace(' ','_')+str(self.reprcount)

                # extract the images and matrices associated with this orient set
                images=indexList(inds,self.images)
                matrices=indexList(inds,self.imgmatrices)

                # calculate the square bounding the regions containing data
                minx,miny,maxx,maxy=calculateStackClipSq(images,min(i.imgmin for i in images))
                cols,rows=images[0].dimensions
                minxi=vec3(minx/float(cols),miny/float(rows),0)
                maxxi=vec3(maxx/float(cols),maxy/float(rows),1)

                hexpts=[ # calculate the vertices for the hex defining this volume
                    images[0].getPlanePos(vec3(minxi.x(),minxi.y(),0)),
                    images[0].getPlanePos(vec3(maxxi.x(),minxi.y(),0)),
                    images[0].getPlanePos(vec3(minxi.x(),maxxi.y(),0)),
                    images[0].getPlanePos(vec3(maxxi.x(),maxxi.y(),0)),
                    images[-1].getPlanePos(vec3(minxi.x(),minxi.y(),0)),
                    images[-1].getPlanePos(vec3(maxxi.x(),minxi.y(),0)),
                    images[-1].getPlanePos(vec3(minxi.x(),maxxi.y(),0)),
                    images[-1].getPlanePos(vec3(maxxi.x(),maxxi.y(),0))
                ]

                tex=scene.createTexture(fname+'Tex'+num,maxx-minx,maxy-miny,len(matrices),self.texformat)
                tex.fillColor(color())

                mat=scene.createMaterial(fname+'Mat'+num)

                fig=scene.createFigure(fname+' '+num,mat.getName(),renderer.FT_TEXVOLUME)
                fig.setRenderQueue(RenderQueues.VolumeImg)
                fig.setNumPlanes(self.numPlanes)

                dimvec=vec3(images[0].dimvec.x(),-images[0].dimvec.y(),0)
                center=(images[0].getPlanePos(minxi)+images[0].getPlanePos(maxxi*vec3(1,1,0)))/2

                self.figs.append(fig)
                self.figtexbb.append((minx,miny,maxx,maxy))
                self.figorients.append(images[0].orientation)
                self.figpositions.append(center)
                self.figdims.append((maxxi-minxi)*dimvec+vec3(0,0,images[-1].position.distTo(images[0].position)))
                self.figtextures.append(tex)
                self.figmats.append(mat)
                self.figinds.append(inds)
                self.fighexes.append(hexpts)

            self.aabb=BoundBox(listSum(self.fighexes))

        self.setVisible(True)

    def prepareBuffers(self):
        # use a spectrum material if that option is set and the image material is not present or uses a fragment program
        useSpecTex=self.useSpecTex and (self.imgmat==None or len(self.imgmat.getGPUProgram(renderer.PT_FRAGMENT))>0)
        # multiply each pixel's alpha by the data value if that option is set and a spectrum material is not used
        mulAlpha=self.mulAlpha and not useSpecTex

        imgmin,imgmax=self.parent.getImageRange()

        for i in range(len(self.figs)):
            tex=self.figtextures[i]
            mat=self.figmats[i]
            
            if self.imgmat!=None:
                self.imgmat.copyTo(mat,False,self.copySpec,True)
    
            mat.setTexture(tex.getName())
            mat.useDepthCheck(self.usesDepthCheck())
            mat.useDepthWrite(self.usesDepthWrite())
            mat.useLighting(False)
            mat.clampTexAddress(True)
            mat.useSpectrumTexture(useSpecTex)
    
            colormat=None if useSpecTex else mat
        
            matrices=indexList(self.figinds[i],self.imgmatrices)
            alphas=indexList(self.figinds[i],self.parent.alphamasks) if self.parent.alphamasks else None

            minx,miny,maxx,maxy=self.figtexbb[i]

            for j,matrix in enumerate(matrices):
                matrix=matrix.subMatrix(matrix.getName()+'sub',maxy-miny,maxx-minx,miny,minx)
                
                if alphas:
                    alpha=alphas[j].subMatrix(alphas[j].getName()+'sub',maxy-miny,maxx-minx,miny,minx)
                else:
                    alpha=None
   
                if isinstance(matrix,ColorMatrix):
                    tex.fillColor(matrix,j)
                else:
                    # The default values for self.useSpecTex and self.mulAlpha ensure data is filled into the
                    # texture in a specific way: if useSpecTex is True then the color will be derived from a
                    # spectrum texture using a fragment shader transfer function, so don't use the material to
                    # assign color; if alpha mask matrices are provided then these are used for alpha values and
                    # mulAlpha will be False, if no alpha masks and no spectrum texture then mulAlpha will be True
                    # and the alpha value for each pixel is multipled by the pixel's data value. This ensures there
                    # is some sort of alpha being stored regardless of settings and input
                    tex.fillColor(matrix,j,imgmin,imgmax,colormat,alpha,mulAlpha)       

    def update(self,scene):
        assert isMainThread()
        self._setFigureTransforms()

    def getNumPlanes(self):
        return self.figs[0].getNumPlanes() if len(self.figs)>0 else 0

    def setNumPlanes(self,num):
        for fig in self.figs:
            fig.setNumPlanes(num)

    def _setFigureTransforms(self):
        rot=rotator(*self.rotation)
        for i,fig in enumerate(self.figs):
            fig.setPosition(self.position+rot*(self.scale*self.figpositions[i]))
            fig.setScale(self.scale)
            fig.setRotation(rot*self.figorients[i])
            fig.setAABB(self.figdims[i]*vec3(-0.5,0.5,0),self.figdims[i]*vec3(0.5,-0.5,1))
