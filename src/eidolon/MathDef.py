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

'''
Math definitions for element types, basis functions, etc. These routines assume CHeart-like element definitions and node 
orders. Known element types as defined by basis functions and dimension parameters are stored in the 'ElemType' enum.

The shape of elements is defined by their basis functions and how many dimensions they are defined for. A linear nodal 
lagrange tetrahedron is defined in 3 dimensions with the restriction that xi values for any point in the element must 
sum to no more than 1. Thus linear Tet elements have 4 nodes:

    2---3
   /|  /
  / | /
 /  |/
0---1

Xi Values (node 0 is local origin, sum(xi_n)<=1):
    0,0,0
    1,0,0
    0,1,0
    0,0,1

Faces:
    Face 1: 0-2-1
    Face 2: 0-3-2
    Face 3: 0-3-1
    Face 4: 1-2-3

Quadratic Tet elements have 10 nodes, the first 4 defining the corners in the same way as linear tets:

2
|\
5 7    9
|  \   |\
0-4-1  6-8  3

Element type generation is defined by these objects and types:
    * GeomType: defines geometry types, eg. Line or Tet
    * ElemTypeDef: defines element types, including basis function and geometric description
    * BasisGenFuncs: enumerates ElemTypeDef generators, associating them with abbreviations of the type name
    * ElemType: defines a generative function which instantiates ElemTypeDef instances on request using BasisGenFuncs

Element types are defined by instances of ElemTypeDef. This class contains the above information, a basis function which
accepts xi coords and other arguments and returns control point coefficients, other methods for doing interpolation, and
other ancillary information. These objects are instantiated by generator functions accepting a geometry name as stored in
GeomType, a textual description, and an integer stating the order of the element type. 

The BasisGenFuncs enum relates abbreviated basis names to the generator functions. Adding new items to this list will
make new basis types available in the system.

The ElemType object uses the BasisGenFuncs enum to find a generator function then calls that for the given name being
requested. For example, ElemType.Line1NL will request the generator function for nodal lagrange from BasisGenFuncs then
pass arguments to it to generate a linear line ElemTypeDef object.
'''


import itertools
import functools
import re
import math


import numpy as np

from .Utils import (
    enum, transpose, prod, matZero, trange,xisToPiecewiseXis,arrayIndex,bern,binom,matIdent,isIterable,
    assertMatDim,mulsum,lerp,lerpXi,epsilon, matInv
)


GeomType=enum(
    ('Point','Point',0,False),
    ('Line','Line',1,False),
    ('Tri','Triangle',2,True),
    ('Quad','Quadrilateral',2,False),
    ('Tet','Tetrahedron',3,True),
    ('Hex','Hexahedron',3,False),
    ('Cyl','Cylinder',3,False),
    ('Hemi','Hemisphere',3,False),
    doc='This defines the element geometry types available, eg. point, line, tet, etc. Values are (Name,Dimension,isSimplex).'
)


class ElemTypeDef(object):
    ''' Defines an element type as its basis function. This includes geometry and face type information.'''

    def __init__(self,geom,basisname,desc,order,xis,vertices,faces,internalxis,basis,pointsearch,facetype):
        self.geom=geom # geometry (tet, hex, etc)
        self.dim=GeomType[geom][1]
        self.isSimplex=GeomType[geom][2]
        self.basisname=basisname # basis function name (NL=nodal lagrange, etc)
        self.desc=desc # plain language description
        self.order=order # order (1=linear, 2=quadratic, etc)
        self.xis=list(xis) # xi values for each node, [] if node count not fixed
        #self.dim=len(self.xis[0]) if len(self.xis)>0 else 0 # dimension, must be 1 (1D), 2 (2D), or 3 (3D)
        self.vertices=list(vertices) # list of vertex indices, [] if node count not fixed
        self.faces=list(faces) # list of face node indices, [] if node count not fixed
        self.basis=basis # basis callable, maps xi values to node coefficients, must accept x, y, z coordinate arguments plus any further positional and keyword args
        self.pointsearch=pointsearch # callable which implements point search for this type
        self.facetype=facetype if facetype else self# ElemTypeDef defining faces as 2D elements (assumes all faces same shape)
        self.internalxis=list(internalxis) # per-face xi sub values to convert a xi value on face to internal xi
        self.facevertices=[len(set(self.getFaceIndices(i)).intersection(self.vertices)) for i in range(len(self.faces))] # # of vertices per face
        self.edges=[] # tuples of xi indices defining edges on 1D/2D elements, vertices first followed by midpoints
        
        if self.dim==1:
            self.edges=[list(range(len(xis)))] # whole line is an edge
        elif self.dim==2:
            self.edges=findEdges(self.xis,len(self.vertices),self.isSimplex)
                    
    def isFixedNodeCount(self):
        '''Returns true if the basis function is defined for a fixed number of control nodes, eg. nodal lagrange.'''
        return bool(self.xis)

    def numNodes(self):
        '''Returns the number of nodes used to define this basis type, -1 if not fixed.'''
        return len(self.xis) if self.isFixedNodeCount() else -1

    def numVertices(self):
        '''Returns the number of corner nodes, -1 if not fixed.'''
        return len(self.vertices) if self.isFixedNodeCount() else -1

    def numFaces(self):
        '''Returns the number of faces, -1 if not fixed.'''
        return len(self.faces) if self.isFixedNodeCount() else -1

    def numFaceVertices(self,face=0):
        '''Returns the number of vertices for a face, or -1 if not fixed.'''
        return self.facevertices[face] if face<len(self.facevertices) else -1

    def getFaceIndices(self,face):
        '''Returns the indices for a face, or [] if not fixed.'''
        #return self.faces[face][:-1] if self.isFixedNodeCount() else -1
        if face>=len(self.faces) or not self.isFixedNodeCount():
            return []
        elif self.dim<3:
            return self.faces[face]
        else:
            return self.faces[face][:-1]
            
    def getFaceVertexIndices(self,face):
        numverts=self.numFaceVertices()
        if numverts<=0:
            return []
        else:
            return self.getFaceIndices(face)[:numverts]
        
    def getFaceType(self,face,asLinear=False):
        if isIterable(self.facetype):
            facetype=self.facetype[face]
        else:
            facetype=self.facetype
            
        if asLinear:
            facetype=ElemType.getLinearType(facetype)
            
        return facetype

    def getFaceFarIndex(self,face):
        '''Returns the index of a vertex far from the given face, or -1 if not fixed or is not applicable.'''
        if face<len(self.faces) and self.dim==3 and self.isFixedNodeCount():
            return self.faces[face][-1]
        else:
            return -1

    def getInternalFaceXiSub(self,face):
        '''Returns the value to subtract from a xi on the given face to get an internal xi.'''
        return self.internalxis[face]

    def applyBasis(self,vals,xi0,xi1,xi2,*args,**kwargs):
        '''Evaluates the basis function at the xi point, multiplies the values by the coefficients, and sums the result.'''
        assert len(self.xis) in (0,len(vals)), 'Number of values (%i) does not match control point count (%i)' %(len(vals),len(self.xis))
        return self.applyCoeffs(vals,self.basis(xi0,xi1,xi2,*args,**kwargs))

    def applyCoeffs(self,vals,coeffs):
        '''Apply the given coefficients to the given values and return the summed result.'''
        assert isIterable(vals)
        assert isIterable(coeffs)
        assert len(vals)==len(coeffs), '%i != %i' % (len(vals),len(coeffs))
        
        if isinstance(vals[0],(list,tuple)):
            result=[0]*len(vals[0])
            for c,val in zip(coeffs,vals):
                for j,v in enumerate(val):
                    result[j]+=v*c

            return tuple(result)
        else:
            return mulsum(vals,coeffs)

    def faceXiToElemXi(self,face,xi0,xi1):
        '''
        Convert the xi value (xi0,xi1) on face number `face' to an element xi value for a 3D element. If self.dim
        is less than 3, the result is simply (xi0,xi1,0). This relies on face 0 being on the xi YZ plane at xi0=0.
        '''
        if self.dim<3:
            return (xi0,xi1,0)
            
        result=[0,0,0]
        facetype=self.getFaceType(face,True)
        coeffs=facetype.basis(xi0,xi1,0) # coeffs within the xi space of this face
        finds=self.getFaceIndices(face) # indices for the nodes of the element defining this face
        
        # interpolate the xi coordinates of the nodes defining this face
        for c,f in zip(coeffs,finds):
            v=self.xis[f]
            result[0]+=v[0]*c
            result[1]+=v[1]*c
            result[2]+=v[2]*c

        return tuple(result)
        
    def applyPointSearch(self,elemnodes,pt,refine,*args,**kwargs):
        '''Attempt to find what xi coordinate in an element defined by node values `elemnodes' the point `pt' is found at.'''
        assert len(elemnodes)==self.numNodes()
        assert refine>=0
        return self.pointsearch(self,elemnodes,pt,refine,*args,**kwargs)
        
    def __repr__(self):
        return '%s: %s' % (ElemType.getTypeName(self.geom,self.basisname,self.order), self.desc)


def findFaces(xis,numVertices,isSimplex):
    '''
    Find the faces of an axis-aligned element (tet or hex) with unit xi coordinates. This adheres to CHeart node
    ordering. The first indices for each face will be the vertices, the last is the index for a node opposite the face.
    A more general face-finding operation would look for those nodes defining vertices and then the nodes between them
    to find faces, but life is easier with axis-aligned elements. Other geometry types other than tet or hex would
    require modification to this function. The first return value is a list of face index lists, the second is a list
    of xi values which when subtracted from a xi coordinate on the face will produce an internal xi coordinate.
    '''
    faces=[]
    subvalue=0.01
    internalxisub=[] # values to subtract from surface xis to get an internal xi coord
    xiDim=len(xis[0])
    xiRange=(0.0,) if isSimplex else (0.0,1.0)

    def farnode(face,xirange):
        # assumes vertices are indexed in the range [0,numVertices], ie. CHeart node ordering
        vertices=[i for i in range(numVertices) if i not in face]
        return vertices[int(xirange)-1]

    # collect axis-aligned faces
    for dim,xirange in itertools.product(range(xiDim),xiRange):
        # collect the indices of each xi value whose component 'dim' equals 'xirange' (which is 0 or 1)
        face=[n for n,xi in enumerate(xis) if xi[dim]==xirange]
        if len(face)>0:
            far=farnode(face,xirange)
            faces.append(face+[far])

            internalxis=[0.0]*xiDim
            internalxis[dim]=subvalue if xirange==1.0 else -subvalue
            internalxisub.append(internalxis)

    # collect tet far face passing through unit vectors
    if isSimplex:
        face=[n for n,xi in enumerate(xis) if sum(xi)==1.0]
        if face!=():
            far=farnode(face,0)
            faces.append(face+[far])
            internalxisub.append([subvalue]*xiDim)
            
    def _cmp(a,b):
        a=faces[a]
        b=faces[b]
        return ((a > b) - (a < b))

    #indices=sorted(range(len(faces)),key=lambda i:faces[i])
    indices=sorted(range(len(faces)),key=functools.cmp_to_key(_cmp))
    
    return [faces[i] for i in indices],[internalxisub[i] for i in indices]


def findEdges(xis,numVertices, isSimplex):
    def crossesMidpoint(a,b):
        return sum(1 if abs(i*0.5+j*0.5-0.5)<epsilon else 0 for i,j in zip(a,b)) in (2,3)
    
    
    def within(v,a,b):
        '''Returns True if `v' is within range [a,b], or [b,a] if b<=a.'''
        return a<=v<=b if a<=b else b<=v<=a
        
    
    def isLinePoint(p,xi,start,end):
        '''Returns True if point `p' is at xi position `xi' on line `start'->`end'.'''
        return all(abs(lerp(xi,j,k)-i)<epsilon for i,j,k in zip(p,start,end))
    
    
    def isBetween(a,start,end):
        '''Returns True if `a' lies on a line between `start' and `end'.'''
        xi=max(lerpXi(i,j,k) if j!=k else 0 for i,j,k in zip(a,start,end))
        
        if not all(within(i,j,k) for i,j,k in zip(a,start,end)):
            return False
        
        return isLinePoint(a,xi,start,end) or isLinePoint(a,xi,end,start)

    found=[]
    edges=[]
    
    for v1,v2 in itertools.product(range(numVertices),repeat=2):
        if v1!=v2 and  (v1,v2) not in found:
            xi1=xis[v1]
            xi2=xis[v2]
            
            if isSimplex or not crossesMidpoint(xi1,xi2):
                # get the midpoints
                mids=[i for i in range(len(xis)) if i!=v1 and i!=v2 and isBetween(xis[i],xi1,xi2)]    
                
                edges.append(tuple([v1,v2]+mids)) # add the edge, vertices first
                found+=[(v1,v2),(v2,v1)]
                
    return edges


def lagrangeBasisI(i,K,xi,alpha,beta):
    '''Evaluate the i'th lagrange basis function using the input xi values and matrix definitions.'''

    M=len(alpha[0]) # # of polynomials
    d=len(xi) # spatial dimension
    assert i>=0 and i<K # K is # of nodes/basis functions, i is current node/function
    assertMatDim(alpha,K,M)
    assertMatDim(beta,d,M)

    result=0
    for j in range(M): # for each polynomial
        a=alpha[i][j]
        for k in range(d): # for each xi component
            a*=xi[k]**beta[k][j]

        result+=a

    return result


def lagrangeBasisIStr(i,K,d,alpha,beta):
    '''
    Construct a string representing the i'th lagrange basis function with free variables xi0,xi1,xi2 storing the
    input xi values.
    '''
    M=len(alpha[0]) # # of polynomials
    assert i>=0 and i<K # K is # of nodes/basis functions, i is current node/function
    assertMatDim(alpha,K,M)
    assertMatDim(beta,d,M)

    result=[]
    for j in range(M): # for each polynomial
        a=alpha[i][j]
        if a==0:
            continue

        eq=''
        isFirst=True

        if a!=1:
            eq+=str(a)
            isFirst=False

        for k in range(d): # for each xi component
            b=beta[k][j]
            if b==0:
                continue

            if not isFirst:
                eq+='*'

            isFirst=False

            eq+='xi'+str(k)
            if b!=1:
                eq+='**'+str(b)

        if eq=='':
            eq='1'

        result.append('('+eq+')')

    return '+'.join(result)


def lagrangeBasisFuncs(K,alpha,beta):
    '''
    Create a sequence of lagrange basis functions, each of which accepts xi values and calculates the coefficient for
    its respective node.
    '''
    return tuple((lambda xi0,xi1,xi2,*args,**kwargs : lagrangeBasisI(i,K,(xi0,xi1,xi2),alpha,beta)) for i in range(K))


def lagrangeBasis(K,dim,alpha,beta):
    '''Create a lagrange basis function which accepts xi values and calculates coefficients for each node.'''

    s='('+','.join(lagrangeBasisIStr(i,K,dim,alpha,beta) for i in range(K))+')'
    c=compile(s,'<<basis>>','eval')
    
    return lambda xi0,xi1,xi2,*args,**kwargs : eval(c)


def lagrangeAlpha(beta,xicoords):
    '''
    Calculate an alpha matrix for a nodal lagrange basis function by applying the Vandermonde matrix method to a beta
    matrix and node xi coords. This adheres to CHeart node ordering.
    '''
    K=len(xicoords)
    d=len(xicoords[0])
    a=matZero(K,K)

    for i,j in trange(K,K):
        a[i][j]=prod(xicoords[i][k]**beta[k][j] for k in range(d))

    return np.linalg.inv(np.asarray(a)).T.tolist()
#    return transpose(matInv(a))


def lagrangeBeta(order,isSimplex,dim):
    '''
    Calculate the beta matrix for a nodal lagrange basis function defining hex or tet elements.
    This adheres to CHeart node ordering.
    '''
    def sortCHeart(a,b):
        '''This function is used to sort the columns of the beta matrix to enforce CHeart node ordering.'''
        aorder=all(i==order or i==0 for i in a)
        border=all(i==order or i==0 for i in b)
        #a0=sum(1 for i in a if i!=0)
        #b0=sum(1 for i in b if i!=0)

        # sort first by order (# of index components used by vertices), this makes vertices come first
        if aorder < border:
            return 1 # note reversed order
        elif aorder>border:
            return -1

        # sort by number of non-zero compoments for simplex types
        #if isSimplex and a0!=b0:
        #   return cmp(a0,b0)

        # sort by component
        for i,j in reversed(list(zip(a,b))): # sort in Z, Y, X order 
            if i<j:
                return -1
            elif i>j:
                return 1
            return 0

        return 0

    # create the beta matrix by listing every `dim'-wide combination of the set [0,`order'] 
    vals=list(v for v in itertools.product(range(order+1),repeat=dim) if not isSimplex or sum(v)<=order)

    if dim>1: # 1D and points don't use CHeart node ordering apparently
        vals.sort(key=functools.cmp_to_key(sortCHeart))

    return transpose(vals)


def xiCoords(order,beta):
    '''Calculate xi coords for nodes from a beta matrix.'''
    fo=float(order)
    result=[]
    for i in range(len(beta[0])):
        result.append(tuple(beta[j][i]/fo for j in range(len(beta))))

    return result


def nodalLagrangeType(geom,desc,order):
    '''
    Generate the ElemTypeDef object which defines a nodal lagrange element type for the given type geometry,
    description, and order. This relies on CHeart node ordering where xi coordinates are sorted based on component
    values, where X is least significant and Z most, but with the vertices coming first before medial nodes.
    '''
    
    from .SceneUtils import pointSearchElem # needed here to get around circular dependency issue with SceneUtils
    
    dim=GeomType[geom][1]
    isSimplex=GeomType[geom][2] 

    if dim==3:
        numVertices=4 if isSimplex else 8
    elif dim==2:
        numVertices=3 if isSimplex else 4
    else:
        numVertices=dim+1

    # construct the beta, xis, and alpha matrices, then construct the basis functions from these
    beta=lagrangeBeta(order,isSimplex,dim)
    xis=xiCoords(order,beta)
    alpha=lagrangeAlpha(beta,xis)
    basis=lagrangeBasis(len(xis),dim,alpha,beta)

    # determine faces and face basis function(s)
    faces=[]
    internalxis=[]
    
    if dim==3:
        faces,internalxis=findFaces(xis,numVertices,isSimplex)
    elif dim==2:
        faces=[list(range(len(xis)))]

    facetype=None
    if dim==3: # TODO: this assumes all faces the same shape, change if this isn't true anymore (eg. prisms)
        facetype=nodalLagrangeType(GeomType._Tri if isSimplex else GeomType._Quad,'Face type',order)

    return ElemTypeDef(geom,'NL',desc,order,xis,list(range(numVertices)),faces,internalxis,basis,pointSearchElem,facetype)


def jacobiPoly(n,a,b,x):
    '''Calculates the Jacobi polynomial for node `n' and xi value `x', with parameters `a' and `b'.'''
    result=0
    Ax=0.5*(x-1)
    Bx=0.5*(x+1)

    for s in range(n+1):
        Co=binom(n+a,s)*binom(n+b,n-s)
        result+=Co*(Ax**(n-s))*(Bx**s)

    return result


def modalPoly(n,N,x):
    '''Calculates the modal polynomial for node `n' out of `N' total nodes at xi value `x'.'''
    a = 0.5 * (1 - x)
    b = 0.5 * (1 + x)

    if n==0:
        return a
    elif n<N:
        return a * b * jacobiPoly(n-1,1,1,x)
    elif n==N:
        return b
    else:
        return 0


def modalPolyLineType(geom,desc,order):
    '''Generates the ElemTypeDef object which defines the modal poly line element type.'''
    assert geom==GeomType._Line,'Only 1D lines supported for now'

    def basis(xi0,xi1,xi2,*args,**kwargs):
        return tuple(modalPoly(n,order,xi0*2-1) for n in range(order+1))

    xis=[(float(i)/order,) for i in range(order+1)]
    nodeinds=range(order+1)

    return ElemTypeDef(geom,'MPL',desc,order,xis,nodeinds,[],[],basis,None,None)


def jacobiEvaluate(x,order,a,b):
    ab=a+b
    ab1=ab+1.0
    ab2=ab+2.0

    P=0.5*(a-b+ab2*x)
    P1=1.0
    P2=0

    for n in range(2,order):
        P2=P1
        P1=P

        n2=2.0*n
        n2ab=n2+ab
        n2ab1=n2+ab1
        n2ab2=n2+ab2

        a1 = 2.0*(n+1.0)*(n+ab1)*n2ab
        a2 = n2ab1*(a**2-b**2)
        a3 = n2ab*n2ab1*n2ab2
        a4 = 2.0*(n+a)*(n+b)*n2ab2
        P = ((a2+a3*x)*P1 - a4*P2)/a1

    b1 = (2.0*order+ab)*(1.0-x**2)
    b2 = order*(a-b-(2.0*order+ab)*x)
    b3 = 2.0*(order+a)*(order+b)

    Pprime = (b2*P + b3*P1)/b1

    return P,Pprime


def get1DSpectralCoords(order):
    '''Calculate the xi positions for the 1D spectral basis.'''

    tol=1e-12
    maxIters=100
    xi = [0.0]*order+[1.0]

    if order>1:
        a = 1.0
        b = 1.0  # alpha and beta
        x = [0.0]*(order+1)

        for k in range(((order-2)/2)+1):

            r = -math.cos(((2.0*k+1.0)/(2.0*order))*math.pi)

            if k>0:
                r = (r+x[k-1])/2.0

            for it in range(maxIters+1):
                s = sum(1.0/(r-x[i]) for i in range(k))

                P, Pprime = jacobiEvaluate(r,order,a,b)
                delta = -P/(Pprime - P*s)
                r += delta

                if abs(delta)<tol:
                    break

                if it==maxIters:
                    raise Exception('too many iterations xi=%g, delta=%g'%(r,delta))

            x[k] = r
            x[order-2-k] = -r

        for i in range(1,order):
            xi[i] = x[i-1]/2.0 + 0.5;

    return xi


def getSpectralTensorCoords(dim,order):
    xis=get1DSpectralCoords(order)

    result=[]
    dim0=order+1
    dim1=dim0 if dim>1 else 1
    dim2=dim0 if dim>2 else 1

    for k,j,i in trange(dim2,dim1,dim0):
        xi=[xis[i],xis[j],xis[k]]
        result.append(xi[:dim])

    return result


def spectralBasis1D(xi,powers,coeffs):
    xis=[[xi**p] for p in powers]
    return (coeffs*xis).tolist()


def evaluateSpectralBasis(xi0,xi1,xi2,powers,coeffs,order,dim):

    phii=spectralBasis1D(xi0,powers,coeffs)
    dim0=order+1

    if dim>1:
        dim1=order+1
        phij=spectralBasis1D(xi1,powers,coeffs)
    else:
        dim1=1
        phij=[1]*(order+1)

    if dim>2:
        dim2=order+1
        phik=spectralBasis1D(xi2,powers,coeffs)
    else:
        dim2=1
        phik=[1]*(order+1)

    result=[]
    for k,j,i in trange(dim2,dim1,dim0):
        val=phii[i]*phij[j]*phik[k]
        result.append(val[0])

    return result

def spectralBasisType(geom,desc,order):
    assert geom==GeomType._Line,'Only 1D lines supported for now'

    dim=GeomType[geom][1]
    numnodes=(order+1)**dim
    isSimplex=geom in (GeomType._Tri,GeomType._Tet)

    powers=list(reversed(list(range(order+1))))

    if isSimplex:
        coeffs=matIdent(dim+1)
        coeffs[0]=[1.0]+[-1.0]*dim
    else:
        xi=get1DSpectralCoords(order)

        v=np.vander(xi,len(xi))
        coeffs=np.linalg.solve(v,np.eye(order+1)).T

    def basis(xi0,xi1,xi2):
        return tuple(evaluateSpectralBasis(xi0,xi1,xi2,powers,coeffs,order,dim))

    return ElemTypeDef(geom,'SL',desc,order,[(x,) for x in xi],range(numnodes),[],[],basis,None,None)


def bezierLineType(geom,desc,order):
    '''
    Generates a bezier line type implemented with De Casteljau's algorithm. A line must have 1+order control points,
    order 1 is a linear line. The line passes through only the first and last control points.
    '''
    assert geom==GeomType._Line,'Only 1D lines supported for now'

    basis=lambda xi0,xi1,xi2: tuple(bern(order,i,xi0) for i in range(order+1))

    xis=[(float(i)/order,) for i in range(order+1)]
    nodeinds=list(range(order+1))

    return ElemTypeDef(geom,'BL',desc,order,xis,nodeinds,[],[],basis,None,None)
    
    
def cubicHermiteCoeffs1D(t,u=0,v=0):
    '''
    Defines 4 coefficients for interpolating over the unit interval `t', where the result values are for the function 
    values at t=0 and t=1, and the derivatives of those values at t=0 and t=1. Thus if two values p1 and p2 have 
    derivatives m1 and m2, (a,b,c,d)=cubicHermiteCoeffs1D(t) implies the value at t is (a*p1 + b*p2 + c*m1 + d*m2).
    '''
    t2=t*t
    t3=t2*t
    #return (2*t3-3*t2+1),(-2*t3+3*t2),(t3-2*t2+t),(t3-t2) # basis functions at xi=0,1,-1,2
    return (t3-2*t2+t),(2*t3-3*t2+1),(-2*t3+3*t2),(t3-t2) # basis functions at xi=-1,0,1,2


def cubicHermiteCoeffs2D(t,u,v=0):
    at,bt,ct,dt=cubicHermiteCoeffs1D(t)
    au,bu,cu,du=cubicHermiteCoeffs1D(u)
    
    return at*au,bt*au,ct*au,dt*au, at*bu,bt*bu,ct*bu,dt*bu, at*cu,bt*cu,ct*cu,dt*cu, at*du,bt*du,ct*du,dt*du
    

def cubicHermiteCoeffs3D(t,u,v):
    c2d=cubicHermiteCoeffs2D(t,u)
    av,bv,cv,dv=cubicHermiteCoeffs1D(v)
    
    return tuple(c*av for c in c2d)+tuple(c*bv for c in c2d)+tuple(c*cv for c in c2d)+tuple(c*dv for c in c2d)
        
    
def cubicHermiteType(geom,desc,order):
    assert geom in (GeomType._Line,GeomType._Quad, GeomType._Hex)
    faces=[]
    internalxis=[]
    pointsearch=None
    facetype=None
        
    if geom==GeomType._Line:
        order=1
        basis=cubicHermiteCoeffs1D
        xis=[-1,0,1,2]
        vertices=[1,2]
    elif geom==GeomType._Quad:
        order=2
        basis=cubicHermiteCoeffs2D
        vertices=[5,6,9,10]
        faces=[list(range(16))]
    elif geom==GeomType._Hex:
        order=3
        basis=cubicHermiteCoeffs3D
        vertices=[21, 22, 25, 26, 37, 38, 41, 42]
        internalxis=[(0.01, 0, 0), (0, 0.01, 0), (0, 0, 0.01),(-0.01, 0, 0), (0, -0.01, 0), (0, 0, -0.01)]
        facetype=cubicHermiteType(GeomType._Quad,'Cubic Hermite Quad Face',2)
        faces=[[16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31,42], 
            [4, 5, 6, 7, 20, 21, 22, 23, 36, 37, 38, 39, 52, 53, 54, 55,42], 
            [1, 5, 9, 13, 17, 21, 25, 29, 33, 37, 41, 45, 49, 53, 57, 61,42], 
            [32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47,21], 
            [8, 9, 10, 11, 24, 25, 26, 27, 40, 41, 42, 43, 56, 57, 58, 59,21], 
            [2, 6, 10, 14, 18, 22, 26, 30, 34, 38, 42, 46, 50, 54, 58, 62,21]]
    else:
        raise ValueError('Unsupported geometry: %r'%geom)

    xis=[tuple(reversed(xi)) for xi in itertools.product([-1.0,0.0,1.0,2.0],repeat=order)]

    return ElemTypeDef(geom,'CH',desc,order,xis,vertices,faces,internalxis,basis,pointsearch,facetype)


def catmullRomCoeffs1D(t,u=0,v=0):
    '''
    Defines 4 coefficients for interpolating over the unit interval `t', where the result values are for the function 
    values at t=-1, t=0, t=1, and t=2. This is used when the derivatives at t=0 and t=1 are not known and adjacent
    values at t=-1 and t=2 are used instead. This basis function is a Catmull Rom spline with tension value tau of 0.5.
    The result is equivalent to (t*t-t*0.5-t*t*t*0.5, t*t*t*1.5-2.5*t*t+1, 2*t*t+t*0.5-t*t*t*1.5, t*t*t*0.5-0.5*t*t).
    '''
    t2=t*t
    t3=t2*t
    t3_05=t3*0.5
    t3_15=t3*1.5
    t_05=t*0.5
    
    return t2-t_05-t3_05, t3_15-2.5*t2+1, 2*t2+t_05-t3_15, t3_05-0.5*t2
    
    
def catmullRomCoeffs2D(t,u,v=0):
    '''
    Defines the 16 coefficients for interpolating over the unit quadrilateral (t,u). Given two Catmull Rom splines 
    at,bt,ct,dt=catmullRomCoeffs1D(t) and au,bu,cu,du=catmullRomCoeffs1D(u), this is equivalent to 
        Matrix([au,bu,cu,du])*Matrix([at,bt,ct,dt]).T
    which if flattened is equivalent to 
        at*au,bt*au,ct*au,dt*au, at*bu,bt*bu,ct*bu,dt*bu, at*cu,bt*cu,ct*cu,dt*cu, at*du,bt*du,ct*du,dt*du
        
    The implementation is derived from Sympy using the routine cse(Matrix([au,bu,cu,du])*Matrix([at,bt,ct,dt]).T))
    to eliminate common subexpressions from the above matrix.
    '''
    x0=0.5*t
    x1=t**2
    x2=t**3
    x3=0.5*x2
    x4=-x0 + x1 - x3
    x5=0.5*u
    x6=u**2
    x7=u**3
    x8=0.5*x7
    x9=-x5 + x6 - x8
    x10=1.5*x2
    x11=-2.5*x1 + x10 + 1
    x12=x0 + 2*x1 - x10
    x13=-0.5*x1 + x3
    x14=1.5*x7
    x15=x14 - 2.5*x6 + 1
    x16=-x14 + x5 + 2*x6
    x17=-0.5*x6 + x8
    
    return x4*x9, x11*x9, x12*x9, x13*x9, x15*x4, x11*x15, x12*x15, x13*x15, x16*x4, x11*x16, x12*x16, x13*x16, x17*x4, x11*x17, x12*x17, x13*x17
    

def catmullRomCoeffs3D(t,u,v):
    '''
    Defines the 64 coefficients for interpolating over the unit cube (t,u,v). The code of this function is equivalent
    to this code:
        c2d=catmullRomCoeffs2D(t,u)
        av,bv,cv,dv=catmullRomCoeffs1D(v)
        return tuple(c*av for c in c2d)+tuple(c*bv for c in c2d)+tuple(c*cv for c in c2d)+tuple(c*dv for c in c2d)
        
    The implementation is derived from Sympy using the cse routine to eliminate common expressions.
    '''
    
    x0=0.5*v
    x1=v**2
    x2=v**3
    x3=0.5*x2
    x4=-x0 + x1 - x3
    x5=0.5*t
    x6=t**2
    x7=t**3
    x8=0.5*x7
    x9=-x5 + x6 - x8
    x10=0.5*u
    x11=u**2
    x12=u**3
    x13=0.5*x12
    x14=-x10 + x11 - x13
    x15=x14*x9
    x16=1.5*x7
    x17=x16 - 2.5*x6 + 1
    x18=x14*x17
    x19=-x16 + x5 + 2*x6
    x20=x14*x19
    x21=-0.5*x6 + x8
    x22=x14*x21
    x23=1.5*x12
    x24=-2.5*x11 + x23 + 1
    x25=x24*x9
    x26=x17*x24
    x27=x19*x24
    x28=x21*x24
    x29=x10 + 2*x11 - x23
    x30=x29*x9
    x31=x17*x29
    x32=x19*x29
    x33=x21*x29
    x34=-0.5*x11 + x13
    x35=x34*x9
    x36=x17*x34
    x37=x19*x34
    x38=x21*x34
    x39=1.5*x2
    x40=-2.5*x1 + x39 + 1
    x41=x0 + 2*x1 - x39
    x42=-0.5*x1 + x3
    x43=x42*x9
    x44=x17*x42
    x45=x19*x42
    x46=x21*x42
    x47=x34*x42
    
    return (x15*x4, x18*x4, x20*x4, x22*x4, x25*x4, x26*x4, x27*x4, x28*x4, x30*x4, x31*x4, x32*x4, x33*x4, x35*x4, x36*x4, x37*x4, x38*x4, 
        x15*x40, x18*x40, x20*x40, x22*x40, x25*x40, x26*x40, x27*x40, x28*x40, x30*x40, x31*x40, x32*x40, x33*x40, x35*x40, x36*x40, x37*x40, x38*x40, 
        x15*x41, x18*x41, x20*x41, x22*x41, x25*x41, x26*x41, x27*x41, x28*x41, x30*x41, x31*x41, x32*x41, x33*x41, x35*x41, x36*x41, x37*x41, x38*x41, 
        x14*x43, x14*x44, x14*x45, x14*x46, x24*x43, x24*x44, x24*x45, x24*x46, x29*x43, x29*x44, x29*x45, x29*x46, x47*x9, x17*x47, x19*x47, x38*x42)


def catmullRomType(geom,desc,order):
    '''Returns a Catmull Rom ElemTypeDef object for line, quad, or hex geometries. The `order' argument is ignored.'''
    assert geom in (GeomType._Line,GeomType._Quad, GeomType._Hex)
    faces=[]
    internalxis=[]
    pointsearch=None
    facetype=None
    
    if geom==GeomType._Line:
        order=1
        basis=catmullRomCoeffs1D
        vertices=[1,2]
    elif geom==GeomType._Quad:
        order=2
        basis=catmullRomCoeffs2D
        vertices=[5,6,9,10]
        faces=[list(range(16))]
    elif geom==GeomType._Hex:
        order=3
        basis=catmullRomCoeffs3D
        vertices=[21, 22, 25, 26, 37, 38, 41, 42]
        internalxis=[(0.01, 0, 0), (0, 0.01, 0), (0, 0, 0.01),(-0.01, 0, 0), (0, -0.01, 0), (0, 0, -0.01)]
        facetype=catmullRomType(GeomType._Quad,'Catmull Rom Quad Face',2)
        faces=[[16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31,42], 
            [4, 5, 6, 7, 20, 21, 22, 23, 36, 37, 38, 39, 52, 53, 54, 55,42], 
            [1, 5, 9, 13, 17, 21, 25, 29, 33, 37, 41, 45, 49, 53, 57, 61,42], 
            [32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47,21], 
            [8, 9, 10, 11, 24, 25, 26, 27, 40, 41, 42, 43, 56, 57, 58, 59,21], 
            [2, 6, 10, 14, 18, 22, 26, 30, 34, 38, 42, 46, 50, 54, 58, 62,21]]
    else:
        raise ValueError('Unsupported geometry: %r'%geom)
        
    xis=[tuple(reversed(xi)) for xi in itertools.product([-1.0,0.0,1.0,2.0],repeat=order)]
    
    return ElemTypeDef(geom,'CR',desc,order,xis,vertices,faces,internalxis,basis,pointsearch,facetype)


def piecewiseCatmullRomType(geom,desc,order):
    '''
    Defines the basis function for a piecewise Catmull Rom object. A piecewise object is composed of multiple sub-element
    which are treated as one large object with a continuous xi space. The basis function will, for a given xi coordinate,
    determine which element this xi coordinate falls into, what the local xi coordinate in that element is, and choose
    the indices of the control points for that element. 
    '''
    assert geom in (GeomType._Line,GeomType._Quad, GeomType._Hex)
    basetype=catmullRomType(geom,desc+' (base type)',order)
    order=basetype.order
    facetype=None if order<3 else piecewiseCatmullRomType(GeomType._Quad,'CR Face type',2)
    
    def _addInds(inds,xis):
        return tuple(int(i+x) for i,x in zip(inds,xis))
    
    def _basisPCR(u,v,w,ul,vl=1,wl=1,*args,**kwargs):
        dims=(ul,vl,wl) # vl==wl==1 for 1D, wl==1 for 2D
        limits=kwargs.get('limits',None)
        circular=kwargs.get('circular',[False]*3)
        pxis,indices=xisToPiecewiseXis((u,v,w),dims,limits) # calculate the xi value in the local element and its index
        coeffs=[0]*(ul*vl*wl)
        basecoeffs=basetype.basis(*pxis) # calculate the coefficients in the local element
        
        # calculate the indices in the coeffs grid by adding the xi coordinates of the local element to the base index
        ctrlinds=[arrayIndex(_addInds(indices,xis),dims,circular) for xis in basetype.xis]
        # for each control point for the local element in the grid, add the coefficient value
        for ind,c in zip(ctrlinds,basecoeffs):
            coeffs[ind]+=c
            
        return coeffs
            
    return ElemTypeDef(geom,'PCR',desc,order,[],[],[],[],_basisPCR,None,facetype)
        


BasisGenFuncs=enum(
    # name, description, generator function
    ('NL','Nodal Lagrange',nodalLagrangeType),
    ('MPL','Modal Poly Line',modalPolyLineType),
    ('SL','Spectral 1D Line',spectralBasisType),
    ('BL','Bezier 1D Line',bezierLineType),
    ('CH','Cubic Hermite',cubicHermiteType),
    ('CR','Catmull Rom',catmullRomType),
    ('PCR','Piecewise Catmull Rom',piecewiseCatmullRomType),
    doc='''Enumeration of functions generating ElemTypeDef objects for given basis functions. The elements of each enum
are the basis function abbreviation, full name, and a function which accepts as arguments a geometry name, a
description, and an order number, and returns an ElemTypeDef object implementing said basis function.'''
)


class ElemTypeMap(enum):
    '''
    Defines an enumeration of element type names paired with ElemTypeDef objects. The definition objects are only
    instantiated when the enum item is requested. The instantiation is done by the function given in BasisGenFuncs.
    '''

    def __init__(self):
        '''Initialize the type mape with the point type definition.'''
        enum.__init__(self,('Point',ElemTypeDef(GeomType._Point,'NL','Point',0,[],[],[],[],None,None,None)))

    def getTypeName(self,geomName,basisName,order):
        '''Produces the [GEOM][ORDER][BASIS] element type name from the given arguments.'''

        assert geomName in GeomType
        assert basisName in BasisGenFuncs
        assert isinstance(order,int) and order>0,'%r %r %r'%(geomName,basisName,order)

        if geomName==GeomType._Point:
            return self._Point
        else:
            return '%s%i%s' % (geomName,order,basisName)
            
    def getLinearType(self,elemtype):
        return ElemType[ElemType.getTypeName(elemtype.geom,elemtype.basisname,1)]

    def _generateElemType(self,name):
        '''
        Generate an element type based on the type's name. The name is of the form [GEOM][ORDER][BASIS] where [GEOM]
        is a name in GeomType, [ORDER] is a number >=1, and [BASIS] is a name in BasisGenFuncs. For example, cubic
        nodal lagrange hexahedrons have the name Hex3NL.
        '''
        if name not in self.valdict:
            nsplit=re.split('([a-zA-Z]+)(\d+)([a-zA-Z0-9]+)',name)

            assert len(nsplit)>3, 'Bad name: '+str(nsplit)+' '+str(name)

            geom=nsplit[1]
            order=int(nsplit[2])
            basistype=nsplit[3]

            if geom not in GeomType:
                raise TypeError("Element type '"+geom+"' not recognized")

            if basistype not in BasisGenFuncs:
                raise TypeError("Basis Function type '"+basistype+"' not recognized")

            ordernames=['Linear','Quadratic','Cubic','Quartic','Quintic','Hextic','Heptic','Octic','Nonic','Decic']
            orderstr=ordernames[order-1] if order<=10 else 'Order '+str(order)

            desc='%s, %s %s' %(GeomType[geom][0],orderstr,BasisGenFuncs[basistype][0])

            basisobj=BasisGenFuncs[basistype][1](geom,desc,order)

            self.append(name,basisobj)
            
            faces=basisobj.facetype
            if not isIterable(faces):
                faces=[faces]
                
            for f in faces:
                if f and self.findName(f)==None:
                    self.append(self.getTypeName(f.geom,basistype,f.order),f)

    def _getVal(self,name):
        self._generateElemType(name if name[0]!='_' else name[1:])
        return enum._getVal(self,name)


# The global enum of per-geometry basis functions which are initialized only on demand
ElemType=ElemTypeMap()

