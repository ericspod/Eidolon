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


import os
import math

from eidolon import (
        enum, color, vec3, rotator, avg, timing, first, halfpi, clamp, frange, group, successive,indexList,listSum, taskroutine,
        BoundBox, Ray, Camera2DView, PointChooseMixin, ElemType, ImageSceneObject, SceneObject, ScenePlugin, printFlush
)
import eidolon

from ui import QtWidgets, Qt, Ui_Seg2DView, Ui_SegObjProp

import itertools

import numpy as np
from scipy.spatial import ConvexHull, Delaunay
from scipy.ndimage import binary_erosion,binary_fill_holes, label,sum as ndsum


DatafileParams=enum('name','title','type','srcimage')
SegmentTypes=enum('LVPool','LV')

segExt='.seg'

defaultNumNodes=16 # default number of contour nodes

SegViewPoints=enum(
    ('rvAttach','RV Anterior Attachment',color(1,0,1)),
    ('ch2Apex','2 Chamber Long Axis Apex',color(1,0,0)),
    ('ch3Apex','3 Chamber Long Axis Apex',color(0,0.75,0)),
    ('ch4Apex','4 Chamber Long Axis Apex',color(0,0,1))
)


class SegPropertyWidget(QtWidgets.QWidget,Ui_SegObjProp):
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self,parent)
        self.setupUi(self)


class Seg2DWidget(QtWidgets.QWidget,Ui_Seg2DView):
    def __init__(self,parent=None):
        QtWidgets.QWidget.__init__(self,parent)
        self.setupUi(self)


def getContourPlane(contour):
    '''
    Returns the plane definition for the contour points `contour'. The (center,normal) pair is the barycenter of the
    points in `contour' and the normal is calculated as the 3 point normal with `center', the first point in `contour',
    and a second point farther from the first point than the average distance between successive points. This routine
    assumes the points of `contour' are in circular order, actually do lie on a common plane, and are not colinear.
    '''
    assert len(contour)>2
    center=avg(contour,vec3()) # contour barycenter
    avgdist=avg(c1.distTo(c2) for c1,c2 in successive(contour)) # average distance between successive values in the contour

    # choose a point at least as far from contour[0] as the average distance between points, or the next point in the contour
    farpt=first(c for c in contour if c.distTo(contour[0])>=avgdist) or contour[1]

    norm=center.planeNorm(contour[0],farpt) # calculate the norm from the far point

    assert (contour[0]-center).angleTo(farpt-center)<math.pi, 'Chose points on a common line, is this contour valid?'
    #assert all(c.onPlane(center,norm) for c in contour), 'Not all contour points on a common plane'

    return center,norm


def contourOnPlane(contour,center,norm):
    '''Returns True if the points of `contour' are on the plane (center,norm).'''
    return all(c.onPlane(center,norm) for c in contour)


def contoursCoplanar(con1,con2):
    '''Returns True if the plane normals of `con1' and `con2' match and the barycenter of `con2' is on the plane of `con1'.'''
    c1,n1=getContourPlane(con1)
    c2,n2=getContourPlane(con2)
    return eidolon.equalPlanes(c1,n1,c2,n2)


def yieldContourIntersects(ray,contour):
    '''Yield each position in space where `ray' intersects a line segment between successive points in `contour'.'''
    for c1,c2 in successive(contour,2,True):
        t=ray.intersectsLineSeg(c1,c2)
        p=ray.getPosition(t)
        if t>=0:# and p!=c1 and p!=c2:
            yield p


def pointInContour(pt,contour,plane=None,bb=None,center=None):
    '''Returns True if `pt' is within `contour', which is on plane `plane' if given and has BoundBox `bb' if given.'''
    bb=bb or BoundBox(contour)
    if pt not in bb: # if the point isn't in the contour's boundbox then it isn't even close to being in the contour
        return False

    plane=plane or getContourPlane(contour)

    if not contourOnPlane(contour,*plane): # if contour isn't on a plane then the point can't be in the contour
        return False

    if not pt.onPlane(*plane): # if the point isn't on the plane then it can't be in the contour
        return False

    center=center or avg(contour,vec3())
    
    if center==pt:
        return True
    else:
        ray=Ray(pt,center-pt) # project a ray from `pt' to the center point
        intersects=list(yieldContourIntersects(ray,contour)) # list the intersection points with the contour
        return len(intersects)%2==1 # `pt' is in the contour if the ray intersects the contour an odd number of times


def reinterpolateContour(contour,elemtype,refine,numnodes):
    '''
    Reinterpolate `contour' with basis `elemtype' to produce a new one with `numnodes' control nodes. A polygon of
    refine*len(contour) vertices is first calculated by interpolating at even-spaced xi distances along the contour.
    The algorithm then chooses `numnodes' nodes from this polygon that are roughly evenly spaced apart and returns them.
    '''
    center,norm=getContourPlane(contour)
    step=1.0/(len(contour)*refine)
    pts=[elemtype.applyBasis(contour,i,0,0,len(contour),limits=[(0,-1)],circular=(True,)) for i in frange(0,1,step)]
    newcontour=[]
    nodelen=0
    # total length of the contour divided by the number of nodes we want to return, ie. distance between returned nodes
    steplen=sum(a.distTo(b) for a,b in successive(pts,2,True))/numnodes

    for a,b in successive(pts,2,True):
        nodelen+=a.distTo(b)
        if nodelen>steplen:
            newcontour.append(b)
            nodelen-=steplen

    return newcontour


def reinterpolateCircularContour(contour,elemtype,startdir,refine,numnodes):
    '''
    Reinterpolate `contour' with basis `elemtype' to produce a new one with `numnodes' control nodes. A polygon of
    refine*len(contour) vertices is first calculated by interpolating at even-spaced xi distances along the contour
    (which assumes it's circular). A ray is then cast from the center of the polygon at regular angle intervals starting
    from the direction of `startdir'. The intersection points of these rays with the polygon are used as the control
    points for the resulting contour. The result is guaranteed to have coplanar points which are uniformly distributed
    in space, but is only an approximation of the shape defined by `contour'. This approximation becomes closer with
    increasing values of both `refine' and `numnodes' (only one being large won't accomplish much).
    '''
    center,norm=getContourPlane(contour)
    step=1.0/(len(contour)*refine)
    pts1=[elemtype.applyBasis(contour,i,0,0,len(contour),limits=[(0,-1)],circular=(True,)) for i in frange(0,1,step)]
    pts=[p.planeProject(center,norm) for p in pts1] # ensure the points lie on the plane for numerical accuracy reasons
    newcontour=[]

    assert eidolon.equalsEpsilon(startdir.angleTo(norm),halfpi),'Start vector for contour reinterpolation not on contour plane'

    for i in frange(0,1,1.0/numnodes):
        rdir=rotator(norm,i*2*math.pi)*startdir
        try:
            ray=Ray(center,rdir)
        except:
            printFlush(center,norm,startdir,rdir)
            raise
            
        newpt=first(yieldContourIntersects(ray,pts))
        assert newpt!=None,'Did not find an intersect when interpolating contour at regular rotational intervals, is this contour coplanar?'
        newcontour.append(newpt)

    assert len(newcontour)==numnodes,'%i != %i'%(len(newcontour),numnodes)
    return newcontour


def getContourRelativeDir(contours,pos):
    '''
    Given a list of unsorted contours `contours' and a position `pos', returns a direction in plane with the largest
    contour which points from the contour center to `pos'.
    '''
    con=max(contours,key=lambda c:BoundBox(c).radius) # get largest contour

    # ensure pos is on the plane of con
    if pos.isZero():
        pos=con[0]
    else:
        pc,pn=getContourPlane(con)
        pos=pos.planeProject(pc,pn)

    return (pos-avg(con)).norm() # vector pointing in the rightwards direction


def sortContours(contours,startdir=None):
    '''
    Accepts a 2D matrix of contour vec3 points `contours' plus a vector `startdir' pointing in the, direction considered
    to be to the right of the contour stack and sorts the contours in order from top to bottom. The `startdir' value is
    used to reorder the points of each contour so that the first point is on the ray pointing from the center of the
    contour in the direction of `startdir'. If this argument isn't given then this sorting isn't done. The resulting
    contour 2D matrix contains vec3 objects.
    '''
    #assert len(contours)>1, 'Must have more than 1 contour'

    downvec=None
    sortorder=None
    ctrls=[]
    # convert each contour and rotate the node ordering so the first node is closest in angle to `startdir'
    for nodes in contours:
        center=avg(nodes,vec3())
        downvec=downvec or center.planeNorm(nodes[0],nodes[1])

        # reorder the points so that the first values in nodes is closest to the center->rightvec ray
        if startdir:
            #rightvec1=rightvec.planeProject(center,downvec)-center
            firstind=min((startdir.angleTo(v-center),i) for i,v in enumerate(nodes))[1]
            nodes=indexList(eidolon.rotateIndices(firstind,len(nodes)),nodes)

        # ensures all contours are in the same circular order
        if sortorder==None:
            sortorder=center.planeOrder(downvec,nodes[0],nodes[1])
        elif center.planeOrder(downvec,nodes[0],nodes[1])!=sortorder:
            nodes=[nodes[0]]+nodes[1:][::-1]

        ctrls.append((center,nodes))

    # sort contours in order along the plane normal
    maxdist=max(c1[0].distTo(c2[0]) for c1 in ctrls for c2 in ctrls)
    farpoint=ctrls[0][0]-downvec*maxdist*2
    sortinds=eidolon.sortIndices([c[0].distTo(farpoint) for c in ctrls])
    ctrls=[ctrls[i][1] for i in sortinds]

    # ensure contours are in top-down order, if the boundbox of the top contour is smaller than the bottom invert order
    if BoundBox(ctrls[0]).radius<BoundBox(ctrls[-1]).radius:
        ctrls=ctrls[::-1]

    return ctrls


def triangulateContour(contour,skipErrors=False):
    '''
    Returns a list of index triples for a triangulation of `contour', assuming it doesn't overlap itself. This uses the
    triangulation by ear reduction algorithm. If `skipErrors' is True, any time an ear can't be found a guess is made,
    this ensures the algorithm works if `contour' overlaps itself but will likely produce an overlapping triangulation.
    '''
    results=[]
    plane=getContourPlane(contour)
    cinds=[(i,c.planeProject(*plane)) for i,c in enumerate(contour)] # list of (index,node) pairs

    while len(cinds)>2:
        found=None
        currentcontour=[c[1] for c in cinds] # get the nodes of the current reduced contour
        for a,b,c in successive(cinds,3,True): # iterate over each possible ear triple
            mid=(a[1]+c[1])*0.5 # midpoint of triangle edge possibly inside the current contour
            if pointInContour(mid,currentcontour,plane): # if the midpoint of bc is in the contour, then abc is an ear
                results.append((a[0],b[0],c[0])) # add the ear's indices to the results
                found=b
                break

        if skipErrors and not found:
            found=cinds[1]
            results.append((cinds[0][0],cinds[1][0],cinds[2][0]))

        assert found, 'Could not find ear to reduce for triangulation: '+str(currentcontour)

        cinds.remove(found) # remove the outside vertex of the ear
        if len(cinds)==3:
            a,b,c=cinds
            results.append((a[0],b[0],c[0]))
            del cinds[:]

    return results


def estimateHemiThickness(contours):
    '''
    Estimate the thickness of the hemisphere defined by sorted contour list `contours' by averaging the difference in
    bound box radii of coplanar contours. If `contours' defines a surface, 0 is returned.
    '''

    # surface contour only, so thickness of 0
    if not contoursCoplanar(contours[0],contours[1]):
        return 0

    radii=[]
    for c1,c2 in group(contours):
        r1=BoundBox(c1).radius
        r2=BoundBox(c2).radius
        radii.append(abs(r1-r2))

    return avg(radii)


def getHemiAxis(contours):
    '''For the given sorted hemisphere contours, returns the normal of the shape pointing from top to apex.'''
    _,norm=getContourPlane(contours[0])
    realaxis=(avg(contours[-1])-avg(contours[0])).norm() # vector pointing from middle of top contour to middle of bottom
    return norm if norm.angleTo(realaxis)<halfpi else -norm


def getHemisphereControls(contours,inner=True):
    '''
    Get the control points from the contour list `contours' defining a hemisphere surface, assuming `contours' defines
    a volume hemisphere segmentation. If `inner' is True then the inner segmentation is chosen, the outer otherwise.
    '''
    contours=list(contours)
    ctrls=[]

    # choose a compare function based on whether the inner or outer contour was requested
    if inner:
        bbcmp=lambda c1,c2:BoundBox(c1).radius<BoundBox(c2).radius
    else:
        bbcmp=lambda c1,c2:BoundBox(c1).radius>BoundBox(c2).radius

    while contours:
        c1=contours.pop(0)
        c2=contours.pop(0) if contours else None
        if c2 and contoursCoplanar(c1,c2):
            ctrls.append(c1 if bbcmp(c1,c2) else c2)
        else:
            ctrls.append(c1)
            if c2:
                contours.insert(0,c2)

    #assert all(len(c)==len(ctrls[0]) for c in ctrls),'Contour lengths do not match, sorting failure?'
    return ctrls


def mapContoursToPlanes(contours):
    '''
    Returns a map relating (center,normal) pairs to a list of contours lying on that plane. The `contours' list should
    contains tuples of the form (nodes,name,timestep) storing the nodes in world space as 3-tuples, contour name, and
    contour timestep respective. Each value in the returned map will be sorted in temporal order.
    '''
    contourMap={}
    for con in contours:
        c,n=getContourPlane([vec3(*n) for n in con[0]])
        p=first((c1,n1) for c1,n1 in contourMap if eidolon.equalPlanes(c,n,c1,n1))
        if p!=None:
            contourMap[p].append(con)
        else:
            contourMap[(c,n)]=[con]

    for v in contourMap.values():
        v.sort(key=lambda i:i[2])

    return contourMap


@timing
def generateContoursFromMask(images,numctrls,innerSeg=True,minSegSize=100,refine=2,task=None):
    '''
    Generate contours for the masks given in the list of ShareImage objects `images'. This returns a list of 
    (timestep,nodes list) pairs of contours with `numctrls' number of nodes are in world space coordinates. An outer
    contour for each non-blank image is first created, if the area of this is greater than `minSegSize' then it is added
    to the result list. If `innerSeg' is True then there is expected to be an inner region which is then also converted 
    to a contour. The `refine' value sets the refinement of the contour interpolation function used when reducing contours.
    '''
    result=[]
    
    def _addContour(img,region,hull):
        pts=[vec3(region[h,0],region[h,1]) for h in hull.vertices] # get image coordinates of polygon
        
        # reduce the contour down to the requested number of control points
        ctrls=reinterpolateCircularContour(pts,ElemType.Line1PCR,vec3.X(),refine,numctrls)
        assert len(ctrls)==numctrls,'%r != %r'%(len(ctrls),numctrls)
        
        result.append((img.timestep,[img.getPlanePos(c,False) for c in ctrls])) # add the contour in world space coords
        
    if task:
        task.setMaxProgress(len(images))
        

    for i,img in enumerate(images):
        if task:
            task.setProgress(i)
            
        if img.imgmin>=img.imgmax: # skip blank images
            continue

        nparr=np.asarray(img.img).T # convert the image to numpy
        region = np.argwhere(nparr==nparr.max()) # find the pixels which are equal to the max value

        try:                    
            hull = ConvexHull(region) # convex hull of whole segmentation
            de=Delaunay(region[hull.vertices]) # triangulation of that hull
        except: 
            continue # ignore errors with Qhull, there's nothing to be done to fix these anyway
            
        # mask over whole convex hull
        simplexpts=de.find_simplex(np.argwhere(nparr==nparr))
        mask=(simplexpts.reshape(nparr.shape)!=-1).astype(int)
        mask=binary_erosion(mask).astype(np.float32)
        
        if np.sum(mask)>minSegSize: # if mask is too small this indicates a bad segmentation
            # isolate segmentation and fill in holes, this should be the same as the mask if the image was a contour but different if malformed
            outer= binary_fill_holes(mask*(nparr==nparr.max())).astype(np.float32)
            
            if ndsum(np.abs(mask-outer))<(minSegSize/10): # too much difference between mask and filled outer indicates a non-contour
                _addContour(img,region,hull)
                
                if innerSeg: # if an inner segmentation is present, attempt to isolate it and add a contour
                    inner=mask*(nparr!=nparr.max()) # mask of inner portion of mask
                    labeled,numfeatures=label(inner) 
                    
                    # keep only the largest piece in the inner segmentation region
                    sums=ndsum(inner,labeled,np.arange(numfeatures+1))
                    maxfeature=np.where(sums==np.max(sums)) # choose the maximum sum whose index will be the label number
                    inner=inner*(labeled==maxfeature)
                    
                    if np.sum(inner)>0:
                        try:
                            iregion = np.argwhere(inner==inner.max()) 
                            ihull = ConvexHull(iregion)
                        except:
                            continue # ignore errors with Qhull, there's nothing to be done to fix these anyway
                        
                        _addContour(img,iregion,ihull)

    return result


def generateApexContours(contours,scale=0.5,givenapex=None):
    '''
    Given contours for a hemisphere in top-to-bottom sorted order, define extra contours and an apex point which will
    close off the bottom of the hemisphere and maintain continuity. Return the final apex and a list of contour lists
    containing the mid ring, a contour entirely composed of final apex points, and the inverted mid ring needed for
    continuity when interpolating up to the apex.
    '''
    c1=contours[-1]
    c2=contours[-2]
    clen=len(c1)
    p1,_=getContourPlane(c1)
    p2,_=getContourPlane(c2)
    planedist=p1.distTo(p2)
    planeshift=getHemiAxis(contours)*(planedist*0.2)

    # if no apex point given calculate one
    if givenapex==None:
        # define an initial apex point by interpolating between the last 2 contours as defined by `scale'
        initialapex=avg(i+(i-j)*scale for i,j in zip(c1,c2))
        finalapex=initialapex+planeshift # define a final apex point
    else:
        finalapex=initialapex=givenapex # define the initial and final apex points as the given one

    # define a middle ring of control points as the median between the initial apex point and the last contour
    midring=[eidolon.lerp(0.5,i,initialapex)+planeshift for i in c1]
    # define an inverted or crossed-over ring segment to allow interpolation to cross over the xi_2=1 boundary
    invertring=[midring[(clen/2+i)%clen] for i in range(clen)]

    return finalapex,[midring,[finalapex]*clen,invertring]


@timing
def calculateAHAField(nodes,xis,inds,topcenter,norm,apex,startpos,include17):
    '''
    Calculates an AHA field for the hemisphere defined by (nodes,inds,xis). The plane defined by (topcenter,norm) should be
    the top of the hemisphere aligned with the center axis. The `apex' node should be node at the bottom of the inside
    surface. The `startpos' vector is a point in space which marks the plane the regions should start from, so if this is
    below `topcenter' then nodes above that plane will be put in region 18. If `include17' is True then region 17 at
    the apex is defined, otherwise regions 13-16 extend to the bottom (eg. for pool meshes). Vector `norm' should be
    the long axis normal pointing from top to apex. The return value is a RealMatrix defining a per-element field which
    assigns each element to a AHA region or 18 if below `startpos'.
    '''
    # AHA regions given in xi order since xi=(0,0,0) is at the top of the rim along the ray from the center to a "rightwards" direction
    aharegions=([2,3,4,5,6,1],[8,9,10,11,12,7],[13,14,15,16],[17],[18])
    ahaheights=(1/3.0,2/3.0,1.0) # bottom heights of each region

    aha=eidolon.RealMatrix('AHA',len(inds))
    aha.meta(eidolon.StdProps._elemdata,'True')

    nodeheights=[nodes[n].planeDist(topcenter,norm) for n in range(len(nodes))] # heights of each node from the top plane
    maxheight=max(nodeheights) # node farthest from top plane, should be in apex
    minheight=max(0,startpos.planeDist(topcenter,norm)) # starting position for assign regions, everything between here and the top plane becomes region 18

    apexdist=apex.planeDist(topcenter,norm) # distance from top plane to inner apex point
    apexheight=eidolon.lerpXi(apexdist,minheight,maxheight) if include17 else 1.0 # height of apex relative to (minheight,maxheight) range
    thresholds=[apexheight*h for h in ahaheights] # thresholds for each layer of regions

    # choose X and Y values to determine which region an element belongs to
    xvals=[]
    yvals=[]
    for i in range(len(inds)):
        ind=inds[i]
        theights=indexList(ind,nodeheights)
        txis=indexList(ind,xis)
        xvals.append(min(n.x() for n in txis if not 0<n.z()<1)) # use the minimal x values since triangles straddling the seam won't have adjacent xi values
        yvals.append(eidolon.lerpXi(max(theights),minheight,maxheight)) # calculate height relative to the (minheight,maxheight) range

    # fill in the field aha to assign a region to each element
    for i in range(len(inds)):
        ind=inds[i]
        avgy=yvals[i]
        minx=xvals[i]

        if avgy<0: # negative values are above where the regions start, so region 18
            row=4
            sector=0
        elif avgy<thresholds[0]: # regions 1-6
            sector=clamp(int(minx*6),0,5)
            row=0
        elif avgy<thresholds[1]: # regions 7-12
            sector=clamp(int(minx*6),0,5)
            row=1
        elif avgy<thresholds[2] or not include17: # regions 13-16
            sub=(1.0/4+1.0/6)/2 # rotate the quarter sections by half the angle difference between them and sixth sections
            sector=int((minx+sub)*4)%4
            row=2
        else: # region 17 (apex)
            row=3
            sector=0

        aha.setAt(aharegions[row][sector],i)

    return aha


@timing
def calculateCavityField(xis,inds):
    '''
    Calculates a pseudo-AHA field for a cavity mesh. This is done base entirely on radial direction.
    '''
    # AHA regions given in xi order since xi=(0,0,0) is at the top of the rim along the ray from the center to a "rightwards" direction
    aharegions=(18,19,20,21,22,23)

    aha=eidolon.RealMatrix('AHA',len(inds))
    aha.meta(eidolon.StdProps._elemdata,'True')

    # fill in the field aha to assign a region to each element
    for i in range(len(inds)):
        ind=inds[i]
        txis=indexList(ind,xis)
        minx=min(n.x() for n in txis if n.z() in (0.0,1.0)) # use the minimal x values since triangles straddling the seam won't have adjacent xi values
        aha.setAt(aharegions[clamp(int(minx*len(aharegions)),0,5)],i)

    return aha


def cartToPolarXi(n):
    '''
    Converts a cartesian coordinate `n' on the unit sphere to a xi coordinate in a hemisphere space with xi_2=0. The
    process is to convert `n' to polar space then convert that coordinate to xi space where xi_0 is the circumferential
    angle around the whole hemisphere, xi_1 is the height value from the rim to the apex, and xi_2 is the depth value
    from the inner to outer surface (always 0 with this function). All xi values range over the unit interval.
    '''
    theta,phi,_=(n*vec3(1,1,-1)).toPolar()

    xi0=theta/(math.pi*2.0)
    if xi0<0:
        xi0+=1.0

    xi1=((phi/math.pi)-0.5)*2

    return vec3(xi0,xi1)


def generatePCRTriHemisphere(ctrls,refine,task=None):
    assert all(len(c)==len(ctrls[0]) for c in ctrls)

    hnodes,inds=eidolon.generateHemisphere(refine+1) # get the nodes for a hemisphere
    nodes=eidolon.listToMatrix(list(map(cartToPolarXi,hnodes)),'nodes') # convert to xi coordinates
    xis=nodes.clone() # clone the xi values since entries in nodes are going to be overridden

    # apply the basis function to the list of xi values, this will convert each xi coordinate to a world coordinate
    args=(len(ctrls[0]),len(ctrls))
    kwargs=dict(limits=[(0,-1),(0,1)],circular=(True,False))
    eidolon.applyBasisConcurrent(nodes,listSum(ctrls),nodes,ElemType._Quad2PCR,args,kwargs,task)

    return nodes,inds,xis


@timing
def generatePCRTetHemisphere(ctrls,refine,task=None):
    '''
    Generate a hemispherical tet mesh from the control point lattice `ctrls' with refinement value `refine'. The number
    of total tets is 140*(4**(`refine'+1)). The `ctrls' lattice is expected to be indexed in ZYX order, len(ctrls)==2.
    '''
    assert all(len(c)==len(ctrls[0]) for c in ctrls)
    assert all(all(len(cc)==len(ctrls[0][0]) for cc in c) for c in ctrls)

    # indices of the tets within the prisms defined below
    tetinds=[
        (0,8,6,12),(6,7,1,13),(7,8,2,14),(6,8,7,14),(12,6,13,14),(12,8,6,14),(13,6,7,14), # first half
        (3,9,11,12),(9,4,10,13),(10,5,11,14),(9,10,11,14),(12,13,9,14),(12,9,11,14),(13,10,9,14) # second half
    ]

    # generate the xi values and indices for a hemisphere triangle mesh, this will be turned into a prism then a tet mesh below
    hnodes,inds=eidolon.generateHemisphere(refine) # get the nodes for a hemisphere
    nodes=[]

    # The process of generating a tet mesh from this point on is to first generate a prism mesh then break this into tets.
    # Prisms are defined as being projections of the triangles in `inds'. Each triangle is treated as the face of the
    # prism at xi_2=0 and xi_2=1 but broken into 4 triangles triforce style, so median nodes must be calculated for these.
    # The triangle is also used as a middle triangle at xi_2=0.5. Tets are generated by combining the face triangles with
    # the middle triangle to divide the prism into 14 elements.

    for i,j,k in inds:
        m1=hnodes[i]
        m2=hnodes[j]
        m3=hnodes[k]
        # these median nodes divide the face into triangles so that the prism can be divided into tets in face symmetric way
        m4=((m1+m2)*0.5).norm()
        m5=((m2+m3)*0.5).norm()
        m6=((m3+m1)*0.5).norm()

        m1,m2,m3,m4,m5,m6=map(cartToPolarXi,(m1,m2,m3,m4,m5,m6)) # convert to xi coordinates

        nodes+=[m1,m2,m3] # inner triangle
        nodes+=[n+vec3(0,0,1.0) for n in (m1,m2,m3)] # outer triangle
        nodes+=[m4,m5,m6] # inner triangle midpoints
        nodes+=[n+vec3(0,0,1.0) for n in (m4,m5,m6)] # outer triangle midpoints
        nodes+=[n+vec3(0,0,0.5) for n in (m1,m2,m3)] # mid triangle

    # reduce the mesh to remove duplicate xi nodes and join up the prism topology which will produce a joined tet topology
    prisms=list(group(range(len(nodes)),15)) # prisms have 15 elements: 6*2 for triangle faces plus 3 for median nodes
    nodes,indlist,_=eidolon.reduceMesh(eidolon.listToMatrix(nodes,'nodes'),[eidolon.listToMatrix(prisms,'prisms','')])
    xis=nodes.clone()

    # apply the basis function to the list of xi values, this will convert each xi coordinate to a world coordinate
    args=(len(ctrls[0][0]),len(ctrls[0]),len(ctrls)) # XYZ dimensions
    kwargs=dict(limits=[(0,-1),(0,1),(0,0)],circular=(True,False,False)) # directional overlap limits for the PCR basis function
    eidolon.applyBasisConcurrent(nodes,listSum(ctrls[0])+listSum(ctrls[1]),nodes,ElemType._Hex3PCR,args,kwargs,task)

    inds=eidolon.IndexMatrix('tets',ElemType._Tet1NL,0,4)
    # fill inds with indices for tets which divide the prisms into symmetric shapes
    for i in range(len(indlist[0])):
        prism=indlist[0].getRow(i)
        for tet in tetinds:
            inds.append(*indexList(tet,prism))

    return nodes,inds,xis


def generateDefaultHemisphereMesh(refine,center,scale,outerrad,innerrad,numctrls=36,numrings=12):
    '''
    Generates a uniform hemisphere with the top center at `center', scaled by vector `scale', with an outer radius of
    `outerrad' and inner radius of `innerad' (the thickness of the hemisphere will uniformly be outerrad-innerrad). The
    values `numctrls' and `numrings' control how many control points are created for the control point matrix.
    '''
    pstep=1.0/numrings
    tstep=1.0/numctrls
    innerv=vec3(innerrad,0,0)
    outerv=vec3(outerrad,0,0)

    ctrls=[]
    for phi in frange(0,1+pstep,pstep):
        inner=[]
        outer=[]
        vrot=rotator(vec3(0,1,0),phi*halfpi)
        for theta in frange(0,1,tstep):
            rot=rotator(vec3(0,0,1),2*math.pi*theta)*vrot
            outer.append(center+(rot*outerv)*scale)
            inner.append(center+(rot*innerv)*scale)

        ctrls+=[[inner,outer]]

    ctrls=list(map(list,zip(*ctrls)))

    _,apexctrls1=generateApexContours(ctrls[0],0.25)
    _,apexctrls2=generateApexContours(ctrls[1],0.5)
    ctrls[0]+=apexctrls1[:1]
    ctrls[1]+=apexctrls2[:1]

    return generatePCRTetHemisphere(ctrls,refine)


@timing
def generateHemisphereSurface(name,contours,refine, startpos, apex=None, reinterpolateVal=0,calcAHA=False,elemtype=None,innerSurface=True,task=None):
    '''
    Create a hemisphere triangle mesh for the contour set `contours' which are expected to define a tube for which an
    apex will be added. The contours will be sorted in order along a common axis with the largest topmost since this
    routine is expecting a hemispherical shape. The `startdir' direction is used to sort the control points of each
    contour to align them, as best as possible, on an axis from the contour's center in the direction of `startdir'
    so that there's minimal twisting in the mesh. The contours are expected to use a continuous basis `elemtype'
    such that node ordering doesn't affect shape (eg. Line1PCR).

    If `reinterpolateVal' is a value greater than 0, each contour with N control points is reinterpolated to have that
    many times N new control points, the first will be on the ray from each contour's center and pointing in the
    direction `startdir'. This will almost certainly change the mesh's shape but a large `reinterpolateVal' value
    (such as 20) will minimize this.

    The resulting contour control points are amalgamated into the control points for a Quad2PCR surface. Xi values for
    a geodesic hemisphere (a buckydome) are calculated on this surface to produce the hemisphere. This routine will
    produce a mesh with 10*(4**(refine+1)) triangles. A field defining which regions of the AHA division scheme each
    element belongs to is also generated, assuming that `startdir' points towards the center of the RV.
    '''
    startdir=getContourRelativeDir(contours,startpos)
    contours=sortContours(contours,startdir)

    # extract into ctrls only the contours for the cavity, if there's 2 contours per plane select the smallest if innerSurface==True
    ctrls=getHemisphereControls(contours,innerSurface)

    if reinterpolateVal: # reinterpolate contours starting from `startdir'
        elemtype=elemtype or ElemType.Line1PCR
        maxlen=max(len(cc) for cc in ctrls)
        ctrls=[reinterpolateCircularContour(cc,elemtype,startdir,reinterpolateVal,maxlen) for cc in ctrls]

    # if this is for the inner surface, move the supplied apex up an amount proportionate to the average thickness
    if innerSurface and apex:
        thickness=estimateHemiThickness(contours)
        axis=getHemiAxis(contours)
        apex-=axis*thickness*0.5

    apex,apexctrls=generateApexContours(ctrls,0.25 if innerSurface else 0.5,apex) # generate apex contour(s)
    ctrls+=apexctrls

    assert all(len(c)==len(ctrls[0]) for c in ctrls),'Contour lengths do not match, sorting failure?'

    nodes,inds,xis=generatePCRTriHemisphere(ctrls,refine,task)
    fields=[]

    # calculate the AHA region for each triangle based on the average or minimal xi value of its vertices
    if calcAHA:
        #topcenter,norm=getContourPlane(ctrls[0])
        topcenter=avg(ctrls[0])
        norm=getHemiAxis(ctrls)
        fields.append(calculateAHAField(nodes,xis,inds,topcenter,norm,apex,startpos,not innerSurface))

    return eidolon.TriDataSet(name+'DS',nodes,inds,fields)


@timing
def generateHemisphereVolume(name,contours,refine, startpos, apex=None,reinterpolateVal=0,calcAHA=False,elemtype=None,innerOnly=True,task=None):
    '''
    Create a hemisphere tetrahedral mesh for the contour set `contours' which are expected to define a tube for which an
    apex will be added. The contours will be sorted in order along a common axis with the largest topmost since this
    routine is expecting a hemispherical shape. The `startdir' direction is used to sort the control points of each
    contour to align them, as best as possible, on an axis from the contour's center in the direction of `startdir'
    so that there's minimal twisting in the mesh. The contours are expected to use a continuous basis `elemtype'
    such that node ordering doesn't affect shape (eg. Line1PCR).

    If `reinterpolateVal' is a value greater than 0, each contour with N control points is reinterpolated to have that
    many times N new control points, the first will be on the ray from each contour's center and pointing in the
    direction `startdir'. This will almost certainly change the mesh's shape but a large `reinterpolateVal' value
    (such as 20) will minimize this.

    The resulting contour control points are amalgamated into the control points for a Hex3PCR volume. Xi values for
    a geodesic hemisphere (a buckydome) are calculated on the xi_2=0 and xi_2=1 surfaces of this volume to produce a
    mesh composed of prism elements, these are decomposed into tetrahedrons in a way that allows adjacent elements to
    have adjacent faces. If `innerOnly' is True then a mesh within the inner contours is produced, if False then the
    contour set is expected to have 2 contours per plane defining and inner and outer boundary for which a hollow
    hemispherical mesh will be produced.
    '''
    elemtype=elemtype or ElemType.Line1PCR
    startdir=getContourRelativeDir(contours,startpos)
    contours=sortContours(contours,startdir) # sort contours from the top of the hemisphere down

    # extract into ctrls only the contours for the cavity, if there's 2 contours per plane select the smallest
    ctrls=getHemisphereControls(contours)

    if reinterpolateVal: # reinterpolate contours starting from `startdir'
        maxlen=max(len(cc) for cc in ctrls)
        ctrls=[reinterpolateCircularContour(cc,elemtype,startdir,reinterpolateVal,maxlen) for cc in ctrls]

    # if present, move the supplied apex up an amount proportionate to the average thickness
    if apex:
        thickness=estimateHemiThickness(contours)
        axis=getHemiAxis(contours)
        innerapex=apex-axis*thickness*0.5
    else:
        innerapex=None

    innerapex,apexctrls=generateApexContours(ctrls,0.25,innerapex) # generate apex contour(s)
    ctrls+=apexctrls

    assert all(len(c)==len(ctrls[0]) for c in ctrls),'Contour lengths do not match, sorting failure?'

    # if innerOnly, a volume for the inner area of the hemisphere is created, otherwise a volume from the outer to inner contours is created
    if innerOnly:
        # add the control points along the central axis of the hemisphere which, for a hexahedral object, would normally define the xi_2=1 surface
        ctrls=[ctrls,[[avg(c,vec3())]*len(c) for c in ctrls]] # ctrls is now a 3D structure index in ZYX order
    else:
        # choose the outer contours
        outerctrls=getHemisphereControls(contours,False)

        if reinterpolateVal: # reinterpolate contours starting from `startdir'
            maxlen=max(len(cc) for cc in outerctrls)
            outerctrls=[reinterpolateCircularContour(cc,elemtype,startdir,reinterpolateVal,maxlen) for cc in outerctrls]

        assert all(len(c)==len(ctrls[0]) for c in outerctrls),'Contour lengths do not match, sorting failure?'

        _,apexctrls=generateApexContours(outerctrls,0.5,apex) # generate apex contour(s)
        outerctrls+=apexctrls
        ctrls=[outerctrls,ctrls] # ctrls is now a 3D structure index in ZYX order

    nodes,inds,xis=generatePCRTetHemisphere(ctrls,refine+(1 if innerOnly else 0),task)
    fields=[]

    if calcAHA:
#       if innerOnly:
#           fields.append(calculateCavityField(xis,inds))
#       else:
#           topcenter,norm=getContourPlane(ctrls[0][0])
#           fields.append(calculateAHAField(nodes,xis,inds,topcenter,norm,innerapex,True))
        #topcenter,norm=getContourPlane(ctrls[0][0])

        topcenter=avg(ctrls[0][0])
        norm=getHemiAxis(listSum(ctrls))
        fields.append(calculateAHAField(nodes,xis,inds,topcenter,norm,innerapex,startpos,not innerOnly))

    return eidolon.PyDataSet(name+'DS',nodes,[inds],fields)


@eidolon.concurrent
def generateImageMaskRange(process,contours,contourtimes,planes,images,labelfunc):
    comp=compile(labelfunc,'labelfunc','eval')
    func=lambda pt,img,contours:float(eval(comp))

    for i in process.prange():
        img=images[i]
        img.img.fill(0)
        trans=img.getTransform().inverse()

        # collect the contours that are on this image and transform them to the image reference space
        imgcontours=[]
        for con,ctime,plane in zip(contours,contourtimes,planes):
            if eidolon.equalsEpsilon(ctime,img.timestep) and contourOnPlane(con,img.position,img.norm):
#            angle=plane[1].angleTo(img.norm)
#            if (angle<eidolon.epsilon or angle>(math.pi-eidolon.epsilon)) and abs(img.getDist(plane[0]))<=eidolon.Handle2D.defaultPlaneMargin:
                transcon=[(trans*c)*vec3(1,1) for c in con]
                box=BoundBox(transcon)
                box=BoundBox([box.minv-vec3(0,0,1),box.maxv+vec3(0,0,1)])
                imgcontours.append((transcon,box,avg(transcon)))

        if len(imgcontours)==0:
            continue

        # iterate over every pixel in the image and set to the value specified by `labelfunc', this clearly could be optimized
        for n,m in eidolon.matIterate(img.img):
            pt=vec3(float(m)/img.img.m(),float(n)/img.img.n())
            incontours=[c for c,bb,ce in imgcontours if pointInContour(pt,c,(vec3(),vec3(0,0,1)),bb,ce)]
            if incontours:
                val=func(pt,img,incontours)
                img.img.setAt(val,n,m)


def generateImageMask(name,contours,contourtimes,template,labelfunc='1',task=None):
    '''
    Generate a mask image from the given contour segmentation `contours'. The image `template' is used as the spatial
    definition of the resulting image, the contours are expected to be coplanar with the planes of this image. The
    expression `labelfunc' determines what the mask value should be for each pixel found within at least one contour.
    It will have available to it the point `pt' in image coordinate space corresponding to the current pixel, the
    SharedImage `img' currently being filled, and `contours' list of contour objects in image coordinate space which
    `pt' falls within. The default expression will set any pixel within a contour to 1, ie. a binary mask. The `contours'
    list should contain lists of vec3 nodes in world space coordinates, and `contourtimes' a timestep value for each 
    contour to align each correctly in time. 
    '''
    #contours=sortContours(contours)
    planes=list(map(getContourPlane,contours))

    if len(set(contourtimes))==1:
        mask=template.plugin.extractTimesteps(template,name,indices=[0]) # static mask
    else:
        mask=template.plugin.clone(template,name) # timed mask
        
    mask.setShared(True)
    proccount=eidolon.chooseProcCount(len(mask.images),0,10)

    generateImageMaskRange(len(mask.images),proccount,task,contours,contourtimes,planes,mask.images,labelfunc)
    mask.setShared(False)

    for i in mask.images:
        i.imgmin,i.imgmax=eidolon.minmaxMatrixReal(i.img)

    return mask


class LVSeg2DMixin(eidolon.DrawContourMixin):
    '''
    This mixin implements the interface for defining contour segmentations in the 2D view. Contours can be drawn around
    features in images using closed line handles defined with a set number of control points and 1D piecewise Catmull-
    Rom basis type.
    '''
    def __init__(self,layout,numNodes=defaultNumNodes):
        eidolon.DrawContourMixin.__init__(self,numNodes)
        self.uiobj=Seg2DWidget()
        self.uiobj.segBox.setParent(None)
        layout.addWidget(self.uiobj.segBox)
        self.contourNames={} # index -> (name,timestep) for each index in self.handles which is a contour handle (not all handles are contour handles)
        self.segobj=None
        self.handlecol=color(1,0,0)
        self.handleradius=5.0
        self.planeMargin=eidolon.Handle2D.defaultPlaneMargin

        self.uiobj.numCtrlBox.setValue(self.numNodes)
        self.uiobj.numCtrlBox.valueChanged.connect(self.setNumNodes)
        self.uiobj.addButton.clicked.connect(self._addButton)
        self.uiobj.delButton.clicked.connect(self._deleteActive)
        self.uiobj.saveButton.clicked.connect(self.save)
        self.uiobj.setPlaneButton.clicked.connect(self._setContourPlane)
        self.uiobj.setTSButton.clicked.connect(self._setContourTS)
        self.uiobj.cloneButton.clicked.connect(self._cloneContour)
        self.uiobj.showContoursBox.clicked.connect(lambda:self.setContoursVisible(self.isContoursVisible()))

        self.uiobj.contourList.itemSelectionChanged.connect(self._selectContour)

        eidolon.setCollapsibleGroupbox(self.uiobj.segBox)

    def setSegObject(self,segobj):
        self.segobj=segobj
        for i,ind in enumerate(sorted(self.contourNames)): # remove contours only, leave other handles alone
            self.removeHandle(ind-i)

        self.contourNames={}

        numnodes=0
        for contour in self.segobj.enumContours():
            numnodes=numnodes or len(contour)
            self.addContour(*contour)

        self.setNumNodes(numnodes)

    def save(self):
        if self.segobj:
            if not os.path.isfile(self.segobj.filename):
                self.segobj.filename=self.segobj.plugin.getSegFilename(False)

            self.segobj.clearContours()
            for i,(name,ts) in self.contourNames.items():
                nodes=self.handles[i].getNodes()
                name=self.segobj.addContour(nodes,name,ts) # names may need changing to be acceptable in the stored file
                self.contourNames[i]=(name,ts)

            self.segobj.save()

    def setNumNodes(self,n):
        if n>=4:
            self.numNodes=n
            with eidolon.signalBlocker(self.uiobj.numCtrlBox):
                self.uiobj.numCtrlBox.setValue(n)

            i=self.getActiveIndex()
            if i is not None: # change only the active contour
                self.handles[i].setNumNodes(n)

        self._repaintDelay()

    def addContourOnPlane(self):
        angles=frange(0,2*math.pi,(2*math.pi)/self.numNodes)
        wnodes=[self.getWorldPosition(0.5+math.cos(i)*0.25,0.5+math.sin(i)*0.25,False) for i in angles]
        self.addContour(wnodes)

    def addContour(self,nodes,name=None,timestep=None):
        name=eidolon.uniqueStr(name or 'contour',['contour']+[n for n,_ in self.contourNames.values()])

        timestep=self.mgr.timestep if timestep==None else timestep
        h=eidolon.PolyHandle2D(self,[vec3(*n) for n in nodes],True,self.handlecol,ElemType.Line1PCR,self.handleradius)
        self.addHandle(h)
        self.contourNames[len(self.handles)-1]=(name,timestep)
        h.setVisible3D(self.isContoursVisible())
        self.setActiveContour(name)
        return name

    def removeContour(self,name):
        self.removeHandle(first(i for i,(n,_) in self.contourNames.items() if n==name))

    def removeHandle(self,index):
        if index!=None:
            for i in sorted(self.contourNames.keys()):
                if i==index: # remove the entry for this handle
                    self.contourNames.pop(index)
                elif i>index: # move entries indexed above this handle down 1
                    self.contourNames[i-1]=self.contourNames.pop(i)

            Camera2DView.removeHandle(self,index)

    def removeHandles(self):
        Camera2DView.removeHandles(self)
        self.contourNames={}

    def setActiveContour(self,name):
        for i,(n,ts) in self.contourNames.items():
            self.handles[i].setActive(n==name)
            if n==name:
                self.setNumNodes(self.handles[i].numNodes())

        listitem=first(self.uiobj.contourList.findItems(name+' @ ',Qt.MatchStartsWith))
        if listitem:
            with eidolon.signalBlocker(self.uiobj.contourList):
                self.uiobj.contourList.setCurrentItem(listitem)

        self._repaintDelay()

    def handleSelected(self,handle):
        index=self.handles.index(handle)
        if index in self.contourNames:
            namets=self.contourNames[index]
            self.setActiveContour(namets[0])

    def getActiveIndex(self):
        return first(i for i in self.contourNames if i<len(self.handles) and self.handles[i].isActive())

    def isContoursVisible(self):
        return self.uiobj.showContoursBox.isChecked()

    def setContoursVisible(self,isVisible):
        eidolon.setChecked(isVisible,self.uiobj.showContoursBox)

        for i in self.contourNames:
            self.handles[i].setVisible3D(isVisible)

        self.mgr.repaint(False)

    def updateView(self):
        # fill the handles list, selecting the active handle
        handles=list(self.contourNames.items())
        contours=['%s @ %.3f'%hn for i,hn in handles]
        selected=self.getActiveIndex()
        eidolon.fillList(self.uiobj.contourList,contours,selected if selected!=None else -1,None,True)

        curtime=self.mgr.timestep
        rep=self.mgr.findObject(self.sourceName)
        tslist=rep.getTimestepList() if rep else []
        mintimeind=eidolon.minmaxIndices(abs(ts-curtime) for ts in tslist)[0] if rep else -1

        # only handles for the current timestep should be visible
        for i,(n,ts) in self.contourNames.items():
            curtimeind=eidolon.minmaxIndices(abs(ts1-ts) for ts1 in tslist)[0] if rep else -2
            self.handles[i].setVisible(self.handles[i].isVisible() and curtimeind==mintimeind)
            self.handles[i].setVisible3D(self.isContoursVisible() and curtimeind==mintimeind)

        self.fillContourFig()

    def mousePress(self,e):
        if not self.drawMousePress(e):
            Camera2DView.mousePress(self,e)

    def mouseRelease(self,e):
        if self.drawMouseRelease(e):
            self.addContour(self.contour)
        else:
            Camera2DView.mouseRelease(self,e)

        self.uiobj.addButton.setStyleSheet('')

        if self.isContoursVisible():
            self.mgr.repaint()

    def mouseDrag(self,e,dx,dy):
        if self.drawMouseDrag(e,dx,dy):
            self._repaintDelay()
        else:
            Camera2DView.mouseDrag(self,e,dx,dy)

    def _addButton(self):
        self.startContourDraw()
        self.uiobj.addButton.setStyleSheet('border: 1px solid rgb(255,0,0);')

    def _selectContour(self):
        text=str(self.uiobj.contourList.currentItem().text())
        self.setActiveContour(text.split('@')[0].strip())

    def _deleteActive(self):
        self.removeHandle(self.getActiveIndex())

    def _setContourPlane(self):
        i=self.getActiveIndex()
        if i!=None:
            h=self.handles[i]
            nodes=h.getNodes()
            for n in range(len(nodes)):
                x,y,_=self.getScreenPosition(nodes[n])
                h.setNode(n,self.getWorldPosition(x,y))

            self._repaintDelay()

    def _setContourTS(self):
        i=self.getActiveIndex()
        if i!=None:
            self.contourNames[i]=(self.contourNames[i][0],self.mgr.timestep)
            self._repaintDelay()

    def _cloneContour(self):
        i=self.getActiveIndex()
        if i!=None:
            h=self.handles[i]
            nodes=h.getNodes()
            for n in range(len(nodes)):
                x,y,_=self.getScreenPosition(nodes[n])
                nodes[n]=self.getWorldPosition(x,y)

            self.addContour(nodes,None,self.contourNames[i][1])


class LVSegView(LVSeg2DMixin,PointChooseMixin,Camera2DView):

    def __init__(self,mgr,camera,numNodes=defaultNumNodes):
        Camera2DView.__init__(self,mgr,camera)
        LVSeg2DMixin.__init__(self,self.mainLayout,numNodes)
        PointChooseMixin.__init__(self,self.mainLayout)

        for p in SegViewPoints:
            self.addPoint(*p)

    def updateView(self):
        self.setPointMargin(self.planeMargin)
        Camera2DView.updateView(self)
        LVSeg2DMixin.updateView(self)
        PointChooseMixin.updateView(self)

        if self.segobj:
            for p in SegViewPoints:
                self.segobj.set(p[0],tuple(self.getPoint(p[0])))

    def setSegObject(self,segobj):
        LVSeg2DMixin.setSegObject(self,segobj)

        for p in SegViewPoints:
            pt=self.segobj.get(p[0]) or (0,0,0)
            self.pointMap[p[0]][0].pt=vec3(*pt)

    def setContoursVisible(self,isVisible):
        self.setPointsVisible3D(isVisible)
        LVSeg2DMixin.setContoursVisible(self,isVisible)


class SegSceneObject(SceneObject):
    '''
    This represents a segmentation object containing the contours defining the segmentation's shapes. It loads and stores
    data from a basic config file which can have any sort of key-value pairs, however each contour's name must start with
    "contour_" and be unique.
    '''
    def __init__(self,name,filename,plugin,**kwargs):
        SceneObject.__init__(self,name,plugin,**kwargs)
        self.filename=eidolon.ensureExt(filename,segExt)
        self.datamap={DatafileParams.name:name,DatafileParams.title:name}
        self._updatePropTuples()

    def _updatePropTuples(self):
        self.proptuples=[('Filename',str(self.filename))]
        if self.datamap:
            self.proptuples+=sorted((k,str(v)) for k,v in self.datamap.items() if not k.startswith('contour_'))

    def getPropTuples(self):
        return self.proptuples

    def getWidget(self):
        '''Get the docked widget for this segmentation, or None if the user hasn't created one.'''
        return self.plugin.getSegObjectWidget(self)

    def get(self,name,default=None):
        return self.datamap.get(name,default)

    def set(self,name,value):
        result=self.get(name)
        self.datamap[name]=value
        self._updatePropTuples()
        return result

    def enumContours(self):
        '''Yields (nodes,name,timestep) tuples for each contour in name order.'''
        names=self.getContourNames()
        sortind=eidolon.getStrSortIndices(names,-1)
        for i in sortind:
            k=names[i]
            ts,n=self.datamap[k]
            yield (n,k,ts)

    def numContours(self):
        return len(self.getContourNames())

    def getContourNames(self):
        return [k for k in self.datamap if k.startswith('contour_')]

    def addContour(self,nodes,name=None,timestep=0):
        assert len(nodes)
        if not name:
            name='contour' # this will get replaced with contour_N below
        elif not name.startswith('contour_'):
                name='contour_'+name

        name=eidolon.uniqueStr(name,['contour']+self.getContourNames())

        self.datamap[name]=(timestep,list(map(tuple,nodes)))
        return name

    def setContour(self,name,timestep,nodes):
        if name not in self.datamap:
            raise ValueError('Cannot find contour with name %s'%name)

        oldval=self.datamap[name]
        self.datamap[name]=(timestep,nodes)
        return oldval

    def removeContour(self,name):
        if name not in self.datamap:
            raise ValueError('Cannot find contour with name %s'%name)

        return self.datamap.pop(name)

    def clearContours(self):
        for n in list(self.datamap):
            if n.startswith('contour_'):
                self.datamap.pop(n)

    def load(self):
        if self.filename:
            self.datamap=eidolon.readBasicConfig(self.filename)
            self._updatePropTuples()

    def save(self):
        if self.filename:
            eidolon.storeBasicConfig(self.filename,self.datamap)


class SegmentPlugin(ScenePlugin):
    def __init__(self):
        ScenePlugin.__init__(self,'Segment')
        self.objcount=0
        self.SegmentTypes=SegmentTypes
        self.dockmap={}

    def init(self,plugid,win,mgr):
        ScenePlugin.init(self,plugid,win,mgr)
        if win:
            win.addMenuItem('Create','NewSeg'+str(plugid),'&Segmentation Object',self._createSeg)
            win.addMenuItem('Import','ImportSeg'+str(plugid),'&Segmentation',self._importSeg)

        if mgr.conf.hasValue('args','--seg'):
            @taskroutine('Loading Seg File(s)')
            def _loadTask(filenames,task=None):
                for f in filenames:
                    obj=self.loadObject(f)
                    self.mgr.addSceneObject(obj)

            self.mgr.runTasks(_loadTask(mgr.conf.get('args','--seg').split(',')))

    def _importSeg(self):
        filename=self.getSegFilename()
        if filename:
            obj=self.loadObject(filename)
            self.mgr.addSceneObject(obj)

    def _createSeg(self):
        obj=self.createSegmentObject('',self.mgr.getUniqueObjName('Segment'),SegmentTypes._LV)
        self.mgr.addSceneObject(obj)

    def getIcon(self,obj):
        return eidolon.IconName.Seg

    def getMenu(self,obj):
        return [obj.getName(),'Show Segmentation View'],self.objectMenuItem

    def getSegFilename(self,isOpen=True):
        return self.mgr.win.chooseFileDialog('Choose Segmentation filename',filterstr='Segment Files (*.seg)',isOpen=isOpen)

    def getSegObjectWidget(self,obj):
        return first(w for w in self.win.dockWidgets if id(w)==self.dockmap.get(obj.getName(),-1))

#   def getReprTypes(self,obj):
#       return []

    def objectMenuItem(self,obj,item):
        if item=='Show Segmentation View':
            self.mgr.addFuncTask(lambda:obj.createRepr(None))

    def createObjPropBox(self,obj):
        prop=SegPropertyWidget()

        prop.ctrlsBox.setValue(defaultNumNodes)
        
        prop.showButton.clicked.connect(lambda:self.mgr.addFuncTask(lambda:obj.createRepr(None)))
        prop.srcBox.activated.connect(lambda i:obj.set(DatafileParams.srcimage,str(prop.srcBox.itemText(i))))

        prop.createContButton.clicked.connect(lambda:self._createContoursButton(prop,obj))
        prop.genMeshButton.clicked.connect(lambda:self._generateMeshButton(prop,obj))
        prop.genMaskButton.clicked.connect(lambda:self._generateMaskButton(prop,obj))
        prop.cropButton.clicked.connect(lambda:self._cropImageButton(prop,obj))

        return prop

    def updateObjPropBox(self,obj,prop):
        if not prop.isVisible():
            return

        imgnames=[o.getName() for o in self.mgr.objs if isinstance(o,ImageSceneObject)]

        eidolon.fillTable(obj.getPropTuples(),prop.propTable)
        eidolon.fillList(prop.srcBox,imgnames,obj.get(DatafileParams.srcimage))
        eidolon.fillList(prop.cropBox,imgnames)
        eidolon.fillList(prop.cropBox,imgnames)
        eidolon.fillList(prop.maskImgBox,imgnames)
        
        # if not source object has been selected, select the first one
        if not obj.get(DatafileParams.srcimage) and len(imgnames)>0:
            prop.srcBox.activated.emit(0)

    def acceptFile(self,filename):
        return eidolon.splitPathExt(filename)[2].lower() == segExt

    def checkFileOverwrite(self,obj,dirpath,name=None):
        outfile=os.path.join(dirpath,name or obj.getName())+segExt
        if os.path.exists(outfile):
            return [outfile]
        else:
            return []

    def renameObjFiles(self,obj,oldname,overwrite=False):
        assert isinstance(obj,SceneObject) and obj.plugin==self
        if os.path.isfile(obj.filename):
            obj.filename=eidolon.renameFile(obj.filename,obj.getName(),overwriteFile=overwrite)

    def getObjFiles(self,obj):
        return [obj.filename] if obj.filename else []

    def copyObjFiles(self,obj,sdir,overwrite=False):
        assert os.path.isfile(obj.filename),'Nonexistent filename: %r'%obj.filename

        newfilename=os.path.join(sdir,os.path.basename(obj.filename))
        if not overwrite and os.path.exists(newfilename):
            raise IOError('File already exists: %r'%newfilename)

        obj.filename=newfilename
        obj.save()

    def getScriptCode(self,obj,**kwargs):
        configSection=kwargs.get('configSection',False)
        namemap=kwargs.get('namemap',{})
        convertpath=kwargs['convertPath']
        script=''
        args={'varname':namemap[obj], 'objname':obj.name}

        if not configSection:
            args['filename']=convertpath(obj.filename)
            script+='%(varname)s = Segment.loadObject(%(filename)s,%(objname)r)\n'

        return eidolon.setStrIndent(script % args).strip()+'\n'

    def createSegmentObject(self,filename,name,stype):
        obj=SegSceneObject(name,filename,self)
        obj.datamap[DatafileParams.type]=stype
        return obj

    def createRepr(self,obj,reprtype,refine=0,**kwargs):
        f=eidolon.Future()
        @taskroutine('Creating Segmentation View')
        def _create(task):
            with f:
                res=[]
                sobj=self.mgr.findObject(obj.get(DatafileParams._srcimage))

                # make a representation of the source object visible if one doesn't already exist
                if isinstance(sobj,ImageSceneObject) and not len(sobj.reprs):
                    isEmpty=first(self.mgr.enumSceneObjectReprs())==None
                    r=sobj.createRepr(eidolon.ReprType._imgtimestack if sobj.isTimeDependent else eidolon.ReprType._imgstack)
                    self.mgr.addSceneObjectRepr(r)
                    if isEmpty:
                        self.mgr.setCameraSeeAll()
                        self.mgr.repaint()
                    self.win.sync() # need to do this to prevent crashing when the dock is created, why?
                    res.append(r)

                res.append(self.getSegObjectDock(obj))
                f.setObject(res)

        return self.mgr.runTasks(_create(),f)

    def getSegObjectDock(self,obj,w=400,h=400):
        @self.mgr.proxyThreadSafe
        def createWidget():
            widg=self.mgr.create2DView(obj.get(DatafileParams.name),LVSegView)
            self.dockmap[obj.getName()]=id(widg)
            widg.setSegObject(obj)
            return widg

        if self.win:
            widg=first(d for d in self.win.dockWidgets if id(d)==self.dockmap.get(obj.getName(),-1))
            return widg or createWidget()

    def loadSegObject(self,filename,name=None):
        '''Deprecated, for compatibility only.'''
        return self.loadObject(filename,name)

    def loadObject(self,filename,name=None,**kwargs):
        name=name or eidolon.splitPathExt(filename)[1]
        obj=SegSceneObject(name,filename,self)
        obj.load()

        if not obj.get(DatafileParams.srcimage):
            fstimg=first(o.getName() for o in self.mgr.objs if isinstance(o,ImageSceneObject))
            obj.set(DatafileParams.srcimage,fstimg)

        return obj

    def saveObject(self,obj,path,overwrite=False,setFilenames=False,**kwargs):
        if not isinstance(obj,SegSceneObject) or not isinstance(obj.plugin,SegmentPlugin):
            raise ValueError('Can only save segment objects with SegmentPlugin')

        if os.path.isdir(path):
            path=os.path.join(path,eidolon.getValidFilename(obj.getName()))

        path=eidolon.ensureExt(path,segExt)
        oldpath=obj.filename
        obj.filename=path
        obj.save()

        if not setFilenames: # set the filename back to the original if we're not supposed to change it
            obj.filename=oldpath

        return path

    def createHemisphereMesh(self,segobj,name,refine,reinterpolateVal=20,calcAHA=False,isVolume=False,inner=True,plugin=None):
        f=eidolon.Future()
        @taskroutine('Creating Hemisphere Mesh')
        def _create(segobj,name,refine,reinterpolateVal,calcAHA,isVolume,inner,task):
            with f:
                if not segobj.get(SegViewPoints._rvAttach):
                    raise ValueError('Segmentation does not define RV attachment point')

                #if not segobj.get(SegViewPoints._ch2Apex) or not segobj.get(SegViewPoints._ch3Apex) or not segobj.get(SegViewPoints._ch4Apex):
                #   raise ValueError('Segmentation provides no apex points')

                genfunc=generateHemisphereVolume if isVolume else generateHemisphereSurface
                ch2=vec3(*segobj.get(SegViewPoints._ch2Apex,(0,0,0)))
                ch3=vec3(*segobj.get(SegViewPoints._ch3Apex,(0,0,0)))
                ch4=vec3(*segobj.get(SegViewPoints._ch4Apex,(0,0,0)))
                rightpos=vec3(*segobj.get(SegViewPoints._rvAttach,(0,0,0))) # position in the rightwards direction
                apex=None

                contours=zip(*segobj.enumContours())[0]
                contours=[list(itertools.starmap(vec3,c)) for c in contours] # convert to vec3

                for c in contours:
                    plane=getContourPlane(c)
                    if not contourOnPlane(c,*plane):
                        raise ValueError('Contours are not all defined on planes (ie. they are not flat)')

#               con=max(contours,key=lambda c:BoundBox(c).radius) # get largest contour
#
#               # ensure rightpos is on the plane of con
#               if rightpos.isZero():
#                   rightpos=con[0]
#               else:
#                   pc,pn=getContourPlane(con)
#                   rightpos=rightpos.planeProject(pc,pn)
#
#               rightvec=(rightpos-avg(con)).norm() # vector pointing in the rightwards direction

                # choose the apex position by averaging any provided values, or None if none are given
                if any(not c.isZero() for c in [ch2,ch3,ch4]):
                    apex=avg(c for c in [ch2,ch3,ch4] if not c.isZero())
                    if apex.isZero():
                        apex=None

                ds=genfunc(name+'DS',contours,refine,rightpos,apex,reinterpolateVal,calcAHA,None,inner,task)
                f.setObject(eidolon.MeshSceneObject(name,ds,plugin))

        return self.mgr.runTasks(_create(segobj,name,refine,reinterpolateVal,calcAHA,isVolume,inner),f)

    @eidolon.taskmethod('Creating Segmentation Mask')
    def createImageMask(self,segobj,name,template,labelfunc='1',refine=1,elemtype=None,task=None):
        '''Create a mask image object from `segobj'. See generateImageMask() for description.'''
        name=name or (segobj.getName()+'Mask')
        contours,_,times=zip(*segobj.enumContours())
        contours=[list(itertools.starmap(vec3,c)) for c in contours] # convert to vec3

        if refine>1:
            elemtype=elemtype or ElemType.Line1PCR
            contours=[reinterpolateCircularContour(c,elemtype,vec3.X(),refine,len(c)*refine) for c in contours]
        
        mask=generateImageMask(name,contours,times,template,labelfunc,task)
        mask.source=None
        mask.plugin=None
        return mask
    
    @eidolon.taskmethod('Cropping Image Using Segmentation as Boundbox')
    def cropImageBySegment(self,obj,segobj,margin,task=None):
        mask=self.createImageMask(segobj,'tempmask',obj)
        mask.plugin=obj.plugin
        cmask=eidolon.cropObjectEmptySpace(mask,'tempcrop',20,False)
        return eidolon.cropRefImage(obj,cmask,obj.getName()+'_Crop',margin,margin)

    @eidolon.taskmethod('Creating contours from mask image')
    def createSegObjectFromMask(self,name,stype,mask,numctrls,innerseg,minSegSize=100,maskindex=0,task=None):
        '''
        Given a mask image `mask', calculate a segmentation with each contour having `numctrls' control points. The
        name of the resulting object will be `name' or a modified form thereof acceptable as a filename. The `stype'
        parameter is a member of SegmentTypes and specifies what type of segmentation this should be, if it equals LV
        then each plane should have 2 contours for an inner and outer surface, otherwise one for the inner surface.
        '''
        assert isinstance(mask,ImageSceneObject)
        assert stype in SegmentTypes

        name=eidolon.getValidFilename(name)
        obj=SegSceneObject(name,name,self)
        obj.datamap[DatafileParams.type]=stype
        obj.datamap[DatafileParams.srcimage]=mask.getName()

        contours=generateContoursFromMask(mask.images,numctrls,innerseg,minSegSize,2,task)
        for ts,nodes in contours:
            obj.addContour(nodes,timestep=ts)
            
        return obj
    
    def _createContoursButton(self,prop,obj):
        maskname=str(prop.maskImgBox.currentText())
        numctrls=prop.ctrlsBox.value()
        innerseg=prop.innerContBox.isChecked()
        mask=self.findObject(maskname)
        
        newobj=self.createSegObjectFromMask('',SegmentTypes._LV,mask,numctrls,innerseg)

        @taskroutine('Replacing contours')    
        def _replace(task):
            obj.clearContours()
            
            for c in newobj().enumContours():
                obj.addContour(*c)
                
            widg=obj.getWidget()
            if widg:
                self.mgr.callThreadSafe(widg.setSegObject,obj)
        
        self.mgr.runTasks(_replace())

    def _generateMeshButton(self,prop,obj):
        conmap=mapContoursToPlanes(obj.enumContours())
        lens=list(map(len,conmap.values()))
        msg=None

        if len(conmap)==0:
            msg='Contour object is empty.'
        elif any(l not in (1,2) for l in lens):
            msg='All planes with contours must have 1 or 2 contours only.'
        elif any(l!=lens[0] for l in lens):
            msg='All planes with contours must have the same number of contours.'
        elif lens[0]==1 and prop.hemButton.isChecked():
            msg='Cannot generate hemisphere if only 1 contour defined per plane.'

        if msg:
            self.mgr.showMsg(msg,'Cannot Generate Mesh')
        else:
            volume=prop.hemButton.isChecked() or prop.cavButton.isChecked()
            inner=prop.cavButton.isChecked() or prop.innerButton.isChecked()
            refine=prop.refineBox.value()
            reinterp=prop.reinterpBox.value()
            aha=prop.ahaBox.isChecked()

            f=self.createHemisphereMesh(obj,obj.getName()+'Mesh',refine,reinterp,aha,volume,inner)
            self.mgr.checkFutureResult(f)
            self.mgr.addSceneObjectTask(f)

    def _generateMaskButton(self,prop,obj):
        w=obj.getWidget()
        if w:
            w.save()
            
        refine=prop.refineMaskBox.value()

        conmap=mapContoursToPlanes(obj.enumContours())
        
        for k,v in conmap.items(): # keep only the contours for the first timestep stored for each plane
            conmap[k]=[vv for vv in v if vv[2]==v[0][2]]
        
        lens=list(map(len,conmap.values()))
        msg=None
        imgobj=self.mgr.findObject(obj.get(DatafileParams.srcimage))
        
        if not imgobj:
            msg='Cannot find source image object %r'%obj.get(DatafileParams.srcimage)
        elif len(conmap)==0:
            msg='Contour object is empty.'
        elif any(l not in (0,1,2) for l in lens):
            msg='All planes with contours must have 1 or 2 contours only.'
        elif any(l not in (0,lens[0]) for l in lens):
            msg='All planes with contours must have the same number of contours.'
        elif lens[0]==1 and not prop.cavMaskButton.isChecked():
            msg='Can only generate cavity mask if only 1 contour defined per plane.'

        if msg:
            self.mgr.showMsg(msg,'Cannot Generate Mask')
        else:
            if prop.hemMaskButton.isChecked():
                maskfunc='1 if len(contours)==1 else 0' # hemisphere mask, only put down a pixel if within 1 contour only
            elif prop.cavMaskButton.isChecked():
                maskfunc='1 if len(contours)==%i else 0'%lens[0] # cavity mask, only put down a pixel if within all contours at once
            elif prop.hemcavButton.isChecked():
                maskfunc='1'  # hemisphere+cavity mask, only put down a pixel if within any contours
            else:
                maskfunc='2 if len(contours)>1 else 3' # 2-label mask, put down 2 for hemisphere and 1 for cavity

            f=self.createImageMask(obj,obj.getName()+'_Mask',imgobj,maskfunc,refine)
            self.mgr.checkFutureResult(f)
            self.mgr.addSceneObjectTask(f)
            
    def _cropImageButton(self,prop,obj):
        imgname=str(prop.cropBox.currentText())
        margin=prop.marginBox.value()
        imgobj=self.mgr.findObject(imgname)
        
        f=self.cropImageBySegment(imgobj,obj,margin)
        self.mgr.checkFutureResult(f)
        self.mgr.addSceneObjectTask(f)


eidolon.addPlugin(SegmentPlugin())
