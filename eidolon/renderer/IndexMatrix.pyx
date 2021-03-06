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


# Template for generating matrices of various types, DO NOT INCLUDE THIS FILE DIRECTLY
# Use Python string formatting to create type-specific versions of this file and store
# these to separate .pyx files.
# Parameters:
#   N - Name prefix
#   T - C++ template typename
#   P - Python type a matrix contains, instances of P wrap instances of T or P==T
#   _To - function name to convert instances of T to P, empty string is default
#   _From - function name to convert instances of P to T, empty string is default


cdef indexval IndexMatrixCallback(void* func,indexval val, sval n, sval m) with gil:
    cdef object o
    o=<object?>func
    return (o((val),n,m))


cdef class IndexMatrix:
    cdef iMatrix[indexval]* mat
    cdef Py_ssize_t shape[2]
    cdef Py_ssize_t strides[2]
    cdef viewCount
    #cdef object __weakref__

    def __init__(self,str name,*args):
        cdef str mtype=''
        cdef str sharedname=''
        cdef str serialmeta=''
        cdef sval n=1,m=1
        cdef bint isShared=False
        self.viewCount=0

        args=list(args)
        if len(args):
            if isinstance(args[0],str):
                mtype=args.pop(0)

            if isinstance(args[0],str):
                sharedname=args.pop(0)
                serialmeta=args.pop(0)

            n=int(args.pop(0))
            isShared=False

            if len(args)>0 and not isinstance(args[0],bool):
                m=int(args.pop(0))

            if len(args)>0:
                isShared=bool(args[0])

        if len(sharedname)>0:
            self.mat=new iMatrix[indexval](name,mtype,sharedname,serialmeta,n,m)
        else:
            self.mat=new iMatrix[indexval](name,mtype,n,m,isShared)

    def __dealloc__(IndexMatrix self):
        del self.mat

    @staticmethod
    cdef IndexMatrix _new(iMatrix[indexval]* mat):
        m=IndexMatrix(mat.getName())
        m.mat=mat
        return m

    @staticmethod
    cdef iMatrix[indexval]* _getNone(IndexMatrix m):
        if m:
            return m.mat
        else:
            return NULL

    cdef checkViewCount(self):
        if self.viewCount>0:
            raise MemoryError('Cannot perform operation, external views of matrix exist')

    def subMatrix(self,str name,sval n, sval m=1,sval noff=0,sval moff=0,bint isShared=False):
        return IndexMatrix._new(self.mat.subMatrix(name,n,m,noff,moff,isShared))

    def reshape(self,str name,sval n, sval m,bint isShared=False):
        return IndexMatrix._new(self.mat.reshape(name,n,m,isShared))

    def applyCell(self,object func,sval minrow=0,sval mincol=0,sval maxrow=-1,sval maxcol=-1):
        maxcol=RenderTypes._min[sval](self.mat.m(),maxcol)
        maxrow=RenderTypes._min[sval](self.mat.n(),maxrow)
        for n in range(minrow,maxrow):
            for m in range(mincol,maxcol):
                self.mat.ats(n,m,(func((self.mat.at(n,m)),n,m)))

    def applyRow(self,object func,sval minrow=0,sval maxrow=-1):
        maxrow=RenderTypes._min[sval](self.mat.n(),maxrow)
        cdef object row
        for n in range(minrow,maxrow):
            row=tuple((self.mat.at(n,i)) for i in range(self.mat.m()))
            self.setRow(n,*func(row,n))

    def hasMetaKey(self,str key):
        return self.mat.hasMetaKey(key)

    def getMetaKeys(self):
        return self.mat.getMetaKeys()

    def meta(self,str key=None, str val=None):
        if not key:
            return self.mat.meta()
        elif not val:
            return self.mat.meta(key)
        else:
            self.mat.meta(key,val)

    def clone(self,str newname=None,bint isShared=False):
        if newname:
            return IndexMatrix._new(self.mat.clone(newname,isShared))
        else:
            return IndexMatrix._new(self.mat.clone(NULL,isShared))

    def __clone__(self):
        return self.clone()

    def __repr__(self):
        return 'IndexMatrix<%s, %i x %i, %r>'%(self.getName(),self.n(),self.m(),self.isShared())

    def __reduce__(self):
        if not self.isShared():
            raise MemoryError('Only shared memory matrices can be pickled')

        return IndexMatrix,(self.getName(),self.getType(),self.mat.getSharedName(),self.mat.serializeMeta(),self.n(),self.m())

    def clear(self):
        self.checkViewCount()
        self.mat.clear()

    def getName(self):
        return self.mat.getName()

    def getType(self):
        return self.mat.getType()

    def isShared(self):
        return self.mat.isShared()

    def n(self):
        return self.mat.n()

    def __len__(self):
        return self.mat.n()

    def m(self):
        return self.mat.m()

    def memSize(self):
        return self.mat.memSize()

    def setName(self,str name):
        self.mat.setName(name)

    def setType(self,str typen):
        self.mat.setType(typen)

    def setShared(self,bint val):
        self.checkViewCount()
        self.mat.setShared(val)

    def swapEndian(self):
        self.mat.swapEndian()

    def getAt(self,sval n,sval m=0):
        return (self.mat.getAt(n,m))

    def setAt(self,indexval v,sval n,sval m=0):
        self.mat.setAt((v),n,m)

    def fill(self,indexval v):
        self.mat.fill((v))

    def setN(self,sval newn):
        self.checkViewCount()
        self.mat.setN(newn)

    def setM(self,sval newm):
        self.checkViewCount()
        self.mat.setM(newm)

    def addRows(self,sval num):
        self.checkViewCount()
        self.mat.addRows(num)

    def reserveRows(self,sval num):
        self.checkViewCount()
        self.mat.reserveRows(num)

    def append(self,*args):
        cdef sval minlen=RenderTypes._min[sval](self.mat.m(),len(args))
        cdef sval n,i

        self.checkViewCount()

        if minlen==0:
            raise MemoryError('Cannot append empty row')

        #elif len(args) not in (1,self.mat.m()): # args is not a single value or a correct-width row of values
        #   raise MemoryError('Can only append matrix or row of correct width (m()=%i, len(args)=%i)'%(self.mat.m(),len(args)))

        if isinstance(args[0],IndexMatrix):
            self.mat.append(deref((<IndexMatrix>args[0]).mat))
        else:
            n=self.mat.n()
            self.mat.addRows(1)
            for i in range(minlen):
                self.mat.ats(n,i,(args[i]))

    def removeRow(self,sval n):
        self.checkViewCount()
        self.mat.removeRow(n)

    def getRow(self,sval n):
        cdef sval i
        if n>=self.mat.n():
            raise IndexError("Bad value %i for index 'n' (0<=n<%i)"%(n,self.mat.n()))
            
        return tuple((self.mat.at(n,i)) for i in range(self.mat.m()))

    def setRow(self,sval n,*vals):
        cdef sval i,minlen=RenderTypes._min[sval](self.mat.m(),len(vals))
        
        if n>=self.mat.n():
            raise IndexError("Bad value %i for index 'n' (0<=n<%i"%(n,self.n()))
            
        for i in range(minlen):
            self.mat.ats(n,i,(vals[i]))

    def mapIndexRow(self,IndexMatrix inds, sval row,int offset=0):
        if row>=inds.mat.n():
            raise IndexError('Parameter "row" not a valid row index for inds (%i>=%i)'%(row,inds.n()))

        return tuple(self.getAt(inds.mat.at(row,i)+offset) for i in range(inds.mat.m()))

    def indexOf(self,indexval p,sval aftern=0,sval afterm=0):
        r= self.mat.indexOf((p),aftern,afterm)
        if r.first==self.mat.n():
            return None
        else:
            return r.first,r.second
            
    def validIndices(self,int n,int m=0):
        return 0<=n<self.n() and 0<=m<self.m()
        
    def iterIndices(self):
        for n in range(self.n()):
            for m in range(self.m()):
                yield n,m
                
    def toList(self):
        if self.m()==1:
            return [(self.mat.atc(i,0)) for i in range(self.n())]
        else:
            return [self.getRow(i) for i in range(self.n())]

    def fromList(self,listmat):
        cdef object line
        cdef sval n=min(self.mat.n(),len(listmat))
        cdef sval m=self.mat.m()

        try:
            m=min(m,len(listmat[0]))
        except:
            m=1

        for i in range(n):
            if m==1:
                self.mat.ats(i,0,(listmat[i]))
            else:
                line=listmat[i]
                for j in range(min(m,len(line))):
                    self.mat.ats(i,j,(line[j]))

    def fromIterable(self,iterable):
        cdef object it=iter(iterable)
        self.setN(len(iterable))
        for i in range(len(iterable)):
            self.mat.ats(i,0,(next(it)))

    def readBinaryFile(self, str filename,size_t offset):
        self.mat.readBinaryFile(filename,offset)

    def readTextFile(self, str filename,sval numHeaders):
        self.mat.readTextFile(filename,numHeaders)

    def storeBinaryFile(self, str filename, list header):
        cdef array.array a=array.array('i',header)
        self.mat.storeBinaryFile(filename,a.data.as_ints,len(header))

    def __getitem__(self,index):
        origindex=index

        if isinstance(index,tuple):
            index=tuple(i for i in index if i!=Ellipsis)
            if len(index)==1:
                index=index[0]

        if isinstance(index,(int,long)):
            if index<0:
                index+=len(self)

            if self.mat.m()==1:
                return self.getAt(index)
            else:
                return self.getRow(index)
        elif isinstance(index,slice):
            if self.mat.m()==1:
                return [(self.mat.at(i,0)) for i in xrange(*index.indices(len(self)))]
            else:
                return [self.getRow(i) for i in xrange(*index.indices(len(self)))]
        elif isinstance(index,tuple) and len(index)==2:
            i,j=index
            if isinstance(i,(int,long)) and isinstance(j,(int,long)):
                return self.getAt(i,j)
            elif isinstance(i,(int,long)) and isinstance(j,slice):
                if i<0:
                    i+=len(self)
                if not (0<=i<len(self)):
                    raise IndexError('Row index value %r out of range'%(index[0],))

                return [(self.mat.at(i,jj)) for jj in xrange(*j.indices(self.m()))]
            elif isinstance(i,slice) and isinstance(j,(int,long)):
                if j<0:
                    i+=len(self)
                if not (0<=j<len(self)):
                    raise IndexError('Column index value %r out of range'%(index[1],))

                return [(self.mat.at(ii,j)) for ii in xrange(*i.indices(len(self)))]
            elif isinstance(i,slice) and isinstance(j,slice):
                minds=range(*j.indices(self.m()))
                return [tuple((self.mat.at(ii,jj)) for jj in minds) for ii in xrange(*i.indices(len(self)))]

        raise TypeError('Index %r is not supported'%(origindex,))

    def __setitem__(self,index,value):
        origindex=index

        if isinstance(index,tuple):
            index=tuple(i for i in index if i!=Ellipsis)
            if len(index)==1:
                index=index[0]

        if isinstance(index,(int,long)):
            if index<0:
                index+=len(self)

            if self.mat.m()==1:
                self.setAt(value,index)
            else:
                self.setRow(index,*value)
        elif isinstance(index,slice):
            if self.mat.m()==1:
                for i in xrange(*index.indices(len(self))):
                    self.mat.ats(i,0,(value[i]))
            else:
                for i in xrange(*index.indices(len(self))):
                    self.setRow(i,*value[i])
        elif isinstance(index,tuple) and len(index)==2:
            i,j=index
            if isinstance(i,(int,long)) and isinstance(j,(int,long)):
                self.setAt(value,i,j)
            elif isinstance(i,(int,long)) and isinstance(j,slice):
                if i<0:
                    i+=len(self)
                if not (0<=i<len(self)):
                    raise IndexError('Row index value %r out of range'%(index[0],))

                minds=range(*j.indices(self.m()))
                row=value[i]
                for jj in minds:
                    self.mat.ats(i,jj,(row[jj-minds[0]]))
            elif isinstance(i,slice) and isinstance(j,(int,long)):
                if j<0:
                    i+=len(self)
                if not (0<=j<len(self)):
                    raise IndexError('Column index value %r out of range'%(index[1],))


                ninds=range(*i.indices(len(self)))
                for ii in ninds:
                    self.mat.ats(ii,j,(value[ii-ninds[0]][j]))
            elif isinstance(i,slice) and isinstance(j,slice):
                ninds=range(*i.indices(len(self)))
                minds=range(*j.indices(self.m()))
                for ii in ninds:
                    row=value[ii-ninds[0]]
                    for jj in minds:
                        self.mat.ats(ii,jj,(row[jj-minds[0]]))
            else:
                raise TypeError('Index %r is not supported'%(origindex,))
        else:
            raise TypeError('Index %r is not supported'%(origindex,))


##Extras Index
# extra methods for IndexMatrix

    def __getbuffer__(self, Py_buffer *buffer, int flags):
        cdef Py_ssize_t itemsize = sizeof(indexval)

        self.shape[0] = self.mat.n()
        self.shape[1] = self.mat.m()

        self.strides[1] = itemsize
        self.strides[0] = self.mat.m()*itemsize

        buffer.buf = <char *>self.mat.dataPtr()
        buffer.format = 'I'
        buffer.internal = NULL
        buffer.itemsize = itemsize
        buffer.len = self.mat.memSize()
        buffer.ndim = 2
        buffer.obj = self
        buffer.readonly = 0
        buffer.shape = self.shape
        buffer.strides = self.strides
        buffer.suboffsets = NULL
        self.viewCount+=1

    def __releasebuffer__(self, Py_buffer *buffer):
        self.viewCount-=1

    def add(self,t,sval minrow=0,sval mincol=0,sval maxrow=-1,sval maxcol=-1):
        if isinstance(t,IndexMatrix):
            self.mat.addm[indexval](deref((<IndexMatrix>t).mat),minrow,mincol,maxrow,maxcol)
        else:
            self.mat.add[indexval](<indexval>t,minrow,mincol,maxrow,maxcol)

    def sub(self,t,sval minrow=0,sval mincol=0,sval maxrow=-1,sval maxcol=-1):
        if isinstance(t,IndexMatrix):
            self.mat.subm[indexval](deref((<IndexMatrix>t).mat),minrow,mincol,maxrow,maxcol)
        else:
            self.mat.sub[indexval](<indexval>t,minrow,mincol,maxrow,maxcol)

    def mul(self,t,sval minrow=0,sval mincol=0,sval maxrow=-1,sval maxcol=-1):
        if isinstance(t,IndexMatrix):
            self.mat.mulm[indexval](deref((<IndexMatrix>t).mat),minrow,mincol,maxrow,maxcol)
        else:
            self.mat.mul[indexval](<indexval>t,minrow,mincol,maxrow,maxcol)

    def div(self,t,sval minrow=0,sval mincol=0,sval maxrow=-1,sval maxcol=-1):
        if isinstance(t,IndexMatrix):
            self.mat.divm[indexval](deref((<IndexMatrix>t).mat),minrow,mincol,maxrow,maxcol)
        else:
            self.mat.div[indexval](<indexval>t,minrow,mincol,maxrow,maxcol)


