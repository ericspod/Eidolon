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


import os.path
import shutil
from struct import unpack

from eidolon import *

from ..ui import Ui_ObjDialog, Ui_DataDialog, Ui_TDDialog


CheartKeywords=enum(
    ('loadargs','Argument values for loading mesh data','(.X filename list,.T filename,ElemType of topology,load sequential or not,# of copies for timesteps,filename of base .X file)'),
    ('datafieldargs','List of argument value for loading fields','(.D filename list,.T file,.D file dimensions,Elemtype of topology,name of spatial topology,load sequential or not)')
)

def readDataSet(xfile,tfile,typename, isBinary=False):
    assert typename in MathDef.ElemType, 'Unknown typename '+typename

    xdata,xheader=readXFile(open(xfile),splitPathExt(xfile)[1],isBinary)
    tdata,theader=readTFile(open(tfile),typename,splitPathExt(tfile)[1],isBinary)

    return PyDataSet(splitPathExt(xfile)[1],xdata,[tdata])


def readXFile(data,buffname, isBinary=False,buff=None,task=None):
    return readCheartBuffer(data,vec3, 1,2,isBinary,buff,buffname,task)


def readTFile(data, typename,buffname,isBinary=False,buff=None,task=None):
    tdata,theader= readCheartBuffer(data,int, MathDef.ElemType[typename].numNodes(),2,isBinary,buff,buffname,task,True)
    tdata.setType(typename)
    return tdata,theader


def readDFile(data, dim,buffname,isBinary=False,buff=None,task=None):
    return readCheartBuffer(data,float, dim,2,isBinary,buff,buffname,task)


readXFileTask=taskroutine(taskLabel="Read Node File")(readXFile)
readTFileTask=taskroutine(taskLabel="Read Topology File")(readTFile)
readDFileTask=taskroutine(taskLabel="Read Data File")(readDFile)


def readCheartBuffer(data, pydatatype, dim,numHeaders,isBinary=False,buff=None,buffname=None,task=None,isIndex=False):
    if not buff: # create an appropriate matrix if there isn't one provided
        if not buffname:
            buffname='CheartBuffer'

        if pydatatype==vec3:
            buff=Vec3Matrix(buffname,0,dim)
        elif pydatatype==int:
            buff=IndexMatrix(buffname,0,dim)
        elif pydatatype==float:
            buff=RealMatrix(buffname,0,dim)

    if pydatatype==vec3: # replace the data type for vec3 with a pseudo-constructor that takes 1-3 numbers and returns a vec3
        def readVec3(*vals):
            if len(vals)==2:
                return vec3(vals[0],vals[1],0)
            elif len(vals)==1:
                return vec3(vals[0],0,0)

            return vec3(vals[0],vals[1],vals[2])

        pydatatype=readVec3


    elemsize=3 if pydatatype==vec3 else 1
    doClose=False

    if isinstance(data,str):
        doClose=True
        data=open(data,'rb' if isBinary else 'r')

    isFileSrc=hasattr(data,'name') and os.path.isfile(data.name)

    if isFileSrc:
        buff.meta(StdProps._filename,os.path.abspath(data.name))

    try:
        if isBinary:
            header=[unpack('i',data.read(4))[0] for i in range(numHeaders)]
        else:
            header=list(map(int,data.readline().replace(',',' ').split()))

        buff.meta(StdProps._header,' '.join(map(str,header)))
        buff.addRows(header[0]-buff.n())

        if header[1]==2 and elemsize==3:
            elemsize=2

        if task:
            task.setMaxProgress(header[0])

        if isFileSrc: # read from file
            if isBinary:
                buff.readBinaryFile(os.path.abspath(data.name),numHeaders*4)
            else:
                buff.readTextFile(os.path.abspath(data.name),numHeaders)

            if task:
                task.setProgress(header[0])
        elif isBinary: # read binary stream data
            done=False
            numlines=0

            while not done:
                for j in range(dim):
                    comps=[]
                    for i in range(elemsize):
                        d=data.read(4 if pydatatype==int else 8)
                        if d!='':
                            comps.append(unpack('i' if pydatatype==int else 'd',d)[0])
                        else:
                            done=True
                            break

                    if not done:
                        buff.setAt(pydatatype(*comps),numlines,j)

                if task:
                    task.setProgress(numlines)

                numlines+=1
        else: # read text stream data
            i=0
            line=data.readline()
            mapfunc=int if pydatatype==int else float

            while line!='':
                if line.strip()!='':
                    if i==buff.n():
                        buff.addRows(1)

                    comps=list(map(mapfunc, line.replace(',',' ').split()))

                    if task:
                        task.setProgress(i)

                    for j in range(dim):
                        buff.setAt(pydatatype(*comps[j*elemsize:(j+1)*elemsize]),i,j)

                i+=1
                line=data.readline()

        return buff,tuple(header)
    finally:
        if doClose:
            data.close()


def writeCheartBuffer(outfile,header,data,addVal=None):
    if isinstance(data,Vec3Matrix):
        getRow=lambda n:tuple(data.getAt(n))
    else:
        getRow=lambda n:data.getRow(n)

    if addVal!=None:
        getRow1=getRow
        getRow=lambda n:[v+addVal for v in getRow1(n)]

    with open(outfile,'w') as o:
        o.write(' '.join(map(str,header))+'\n')
        for n in range(data.n()):
            line=getRow(n)
            o.write(' '.join(map(str,line))+'\n')


def guessTopologyType(tfile):
    '''Returns a guess of the (geom,order,basis) values for a given text topology file.'''
    geom,order,basis=GeomType._Tet,1,BasisGenFuncs._NL # default if `tfile' is not text, has 4 values on the first line, or is otherwise bogus

    if os.path.isfile(tfile) and splitPathExt(tfile)[2]=='.T':
        with open(tfile) as o:
            o.readline() # skip header
            line=first(l for l in o if l.strip()) # skip empty lines

        linelen=len(line.split())
        if linelen==2:
            geom,order=GeomType._Line,1
        elif linelen==3:
            geom,order=GeomType._Tri,1
        elif linelen==6:
            geom,order=GeomType._Tri,2
        elif linelen==8:
            geom,order=GeomType._Hex,1
        elif linelen==9:
            geom,order=GeomType._Quad,2
        elif linelen==10:
            geom,order=GeomType._Tet,2
        elif linelen==27:
            geom,order=GeomType._Hex,2

    return geom,order,basis


@Concurrency.concurrent
def loadFileSequenceRange(process,files,typename,dim):
    start=process.startval
    end=process.endval

    results=[]
    count=0

    for f in files[start:end]:
        buffname=splitPathExt(f)[1]
        isBinary=f[-1].lower()=='b'

        try:
            if typename!=None:
                buff,header=readTFile(f,typename,buffname,isBinary)
            elif dim!=None:
                buff,header=readDFile(f,dim,buffname,isBinary)
            else:
                buff,header=readXFile(f,buffname,isBinary)

            buff.setShared(True)
            results.append((buff,header))
        except Exception as e:
            printFlush(e)
            traceback.print_exc()
            results.append((None,None))

        count+=1
        process.setProgress(count)

    return results


def loadFileSequence(files,typename=None,dim=None,task=None):
    files=list(map(os.path.abspath,files))

    for f in files:
        assert os.path.isfile(f),'File not found:'+f

    proccount=chooseProcCount(len(files),0,10)
    result=loadFileSequenceRange(len(files),proccount,task,files,typename,dim)

    filemap={}

    for buff,header in listSum(result.values()):
        filename=buff.meta(StdProps._filename)
        filemap[filename]=(buff,header)

    return [filemap.get(f) for f in files]


class BaseLoadDialog(QtWidgets.QDialog):
    def __init__(self,mgr,parent=None):
        QtWidgets.QDialog.__init__(self,parent)
        self.setupUi(self)
        self.mgr=mgr
        self.lastdir=self.tr('.')

    def accept(self):
        self.done(1)

    def reject(self):
        self.done(0)

    def _chooseFile(self,title,filterstr,filebox,chooseMultiple=False):
        result = self.mgr.win.chooseFileDialog(title,self.lastdir,filterstr,parent=self,chooseMultiple=chooseMultiple)
        if not chooseMultiple and filebox!=None and result.strip()!='':
            filebox.setText(result)
            self.lastdir=os.path.dirname(os.path.abspath(result))

        return result

    def _updateTable(self,table,newitems=[]):
        itemlist=[str(table.item(n,1).text()) for n in range(table.rowCount())]+newitems
        itemlist=[i for i in itemlist if i.strip()!='']
        fillEnumTable(itemlist,table)
        return itemlist

    def _guessTopology(self,tfile,geomBox,basisBox,orderBox):
        geom,order,basis=guessTopologyType(tfile)
        geomBox.setCurrentIndex(geomBox.findText(GeomType[geom][0]))
        basisBox.setCurrentIndex(basisBox.findText(BasisGenFuncs[basis][0]))
        orderBox.setValue(order)

    def _fillGeomBasisBoxes(self,geomBox,basisBox):
        fillList(geomBox,[nf for n,nf,dim,simp in GeomType])
        fillList(basisBox,[desc for n,desc,gen in BasisGenFuncs])

    def _getElemType(self,geomBox,basisBox,orderBox):
        geomtype=GeomType[geomBox.currentIndex()][0]
        basistype=BasisGenFuncs[basisBox.currentIndex()][0]
        return ElemType.getTypeName(geomtype,basistype,orderBox.value())

    def getParams(self):
        pass


class LoadDialog(Ui_ObjDialog,BaseLoadDialog):
    def __init__(self,mgr,parent=None):
        BaseLoadDialog.__init__(self,mgr,parent)
        self._fillGeomBasisBoxes(self.geomBox,self.basisBox)

        self.xchoose.clicked.connect(self.choose_x)
        self.tchoose.clicked.connect(lambda:self._chooseFile("Choose Topology .T File",".T Files (*.T *.Tb)",self.tfile))
        self.tfile.textChanged.connect(lambda:self._guessTopology(str(self.tfile.text()),self.geomBox,self.basisBox,self.orderBox))

    def choose_x(self):
        fname = self._chooseFile("Choose Node .X File",".X .D Files (*.X *.Xb *.D *.Db)",self.xfile)
        if fname:
            fnameext=os.path.splitext(fname)
            if os.path.isfile(fnameext[0]+'.T') and fnameext[1] in ('.X','.D'):
                self.tfile.setText(fnameext[0]+'.T')
            elif os.path.isfile(fnameext[0]+'.Tb') and fnameext[1] in ('.Xb','Db'):
                self.tfile.setText(fnameext[0]+'.Tb')

    def getParams(self):
        result=self.exec_()
        if result!=1:
            return None

        xfile=str(self.xfile.text()).strip()
        tfile=str(self.tfile.text()).strip()
        elemtype=self._getElemType(self.geomBox,self.basisBox,self.orderBox)

        return xfile,tfile,elemtype

class LoadDataDialog(Ui_DataDialog,BaseLoadDialog):
    def __init__(self,mgr,parent=None):
        BaseLoadDialog.__init__(self,mgr,parent)
        self._fillGeomBasisBoxes(self.geomBox,self.basisBox)
        self.dfiles=[]

        self.tchoose.clicked.connect(lambda:self._chooseFile("Choose Topology .T File",".T Files (*.T *.Tb)",self.tfile))
        self.dchoose.clicked.connect(self.addFields)
        self.tfile.textChanged.connect(lambda:self._guessTopology(str(self.tfile.text()),self.geomBox,self.basisBox,self.orderBox))

    def _updateDTable(self,newitems=[]):
        self.dfiles=self._updateTable(self.dfileTable,newitems)

    def addFields(self):
        fnames = self._chooseFile("Choose Field Files",".D Files (*.D *.Db)",None,True)
        self._updateDTable(fnames)

    def getParams(self):
        result=self.exec_()
        if result!=1:
            return None

        elemtype=self._getElemType(self.geomBox,self.basisBox,self.orderBox)
        tfile=str(self.tfile.text()).strip()
        return self.dfiles,self.dimBox.value(), tfile,elemtype


class LoadTDDialog(Ui_TDDialog,BaseLoadDialog):
    def __init__(self,mgr,parent=None):
        BaseLoadDialog.__init__(self,mgr,parent)
        self._fillGeomBasisBoxes(self.geomBox,self.basisBox)
        self._fillGeomBasisBoxes(self.fgeomBox,self.fbasisBox)

        self.xchoose.clicked.connect(lambda:self._chooseFile("Choose Node .X .D File",".X .D Files (*.X *.Xb *.D *.Db)",self.xfile))
        self.tchoose.clicked.connect(lambda:self._chooseFile("Choose Topology .T File",".T Files (*.T *.Tb)",self.tfile))
        self.ftchoose.clicked.connect(lambda:self._chooseFile("Choose Topology .T File",".T Files (*.T *.Tb)",self.ftfile))
        self.tfile.textChanged.connect(lambda:self._guessTopology(str(self.tfile.text()),self.geomBox,self.basisBox,self.orderBox))
        self.ftfile.textChanged.connect(lambda:self._guessTopology(str(self.tfile.text()),self.fgeomBox,self.fbasisBox,self.forderBox))

        self.absoluteRadio.clicked.connect(self._absoluteCheck)
        self.displaceRadio.clicked.connect(self._absoluteCheck)

        self.addNodesButton.clicked.connect(self.addNodes)
        self.addFieldsButton.clicked.connect(self.addFields)

        self.xkeyframes=[]
        self.dkeyframes=[]

        self.xfileTable.verticalHeader().setMovable(True)
        self.dfileTable.verticalHeader().setMovable(True)

        self.xfileTable.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.dfileTable.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)

        self.xfileTable.itemChanged.connect(lambda i:self._moveRow(i.row(),self.xkeyframes,self.xfileTable))
        setattr(self.xfileTable,'keyPressEvent',lambda e:self._delRow(e,self.xkeyframes,self.xfileTable))

        self.dfileTable.itemChanged.connect(lambda i:self._moveRow(i.row(),self.dkeyframes,self.dfileTable))
        setattr(self.dfileTable,'keyPressEvent',lambda e:self._delRow(e,self.dkeyframes,self.dfileTable))

    def _absoluteCheck(self):
        isabs=self.absoluteRadio.isChecked()
        if isabs:
            self.xfile.setText('')
        self.xchoose.setEnabled(not isabs)
        self.xfile.setEnabled(not isabs)

    def _delRow(self,event,itemlist,table):
        index=first(i.row() for i in table.selectedIndexes()) or -1
        if event.key() in (Qt.Key_Delete,Qt.Key_Backspace) and 0<=index<len(itemlist):
            itemlist.pop(index)
            fillEnumTable(itemlist,table)

        QtWidgets.QTableWidget.keyPressEvent(table,event)

    def _moveRow(self,j,itemlist,table):
        index=first(i.row() for i in table.selectedIndexes()) or -1
        if j>index:
            j+=1
        if 0<=index<len(itemlist) and j>=0:
            itemlist.insert(j,itemlist.pop(index))
            fillEnumTable(itemlist,table)

    def addNodes(self):
        fnames = self._chooseFile("Choose Keyframe Node Files",".X .D Files (*.X *.Xb *.D *.Db)",None,True)
        if fnames:
            self.xkeyframes=self._updateTable(self.xfileTable,fnames)

    def addFields(self):
        fnames = self._chooseFile("Choose Keyframe Field Files",".D Files (*.D *.Db)",None,True)
        if fnames:
            self.dkeyframes=self._updateTable(self.dfileTable,fnames)

    def getParams(self):
        result=self.exec_()
        if result!=1:
            return None

        xfile=str(self.xfile.text()).strip()
        tfile=str(self.tfile.text()).strip()
        ftfile=str(self.ftfile.text()).strip()
        isAbsolute=self.absoluteRadio.isChecked()
        datadim=self.dimBox.value()
        starttime=self.startTimeBox.value()
        interval=self.intervalBox.value()

        elemtype=self._getElemType(self.geomBox,self.basisBox,self.orderBox)
        felemtype=self._getElemType(self.fgeomBox,self.fbasisBox,self.forderBox)

        return xfile,tfile,ftfile,isAbsolute,datadim,elemtype,felemtype,starttime,interval,self.xkeyframes,self.dkeyframes


class CheartPlugin(MeshScenePlugin):
    def __init__(self):
        ScenePlugin.__init__(self,'CHeart')

    def init(self,plugid,win,mgr):
        ScenePlugin.init(self,plugid,win,mgr)
        if win:
            win.addMenuItem('Import','CHeartObjLoad'+str(plugid),'&CHeart Object',self._openLoadDialog)
            win.addMenuItem('Import','CHeartDataLoad'+str(plugid),'CHeart &Field',self._openLoadDataDialog)
            win.addMenuItem('Import','CHeartDataLoad'+str(plugid),'CHeart &Time Series',self._openLoadTDDialog)
            win.addMenuItem('Export','CHeartExport'+str(plugid),'&CHeart File(s)',self._openSaveDialog)

        conf=mgr.conf

        cheartload=conf.get('args','--cheartload').split(',')
        cheartfield=conf.get('args','--cheartfield').split(',')
        reprload=conf.get('args','--cheartrepr').split(',')

        # If the arguments are present and in the right format, load an object, a field, and/or produce a simple representation
        if len(cheartload)==3:
            obj=self.loadSceneObject(cheartload[0], cheartload[1],cheartload[2])
            self.mgr.addFuncTask(lambda:self.mgr.addSceneObject(obj()))

            # if the field argument is present and correct, load the field with the optional field topology
            if conf.hasValue('args','--cheartfield') and len(cheartfield)>1:
                dfile=cheartfield[0]
                dim=int(cheartfield[1])
                tfile=cheartfield[2] if len(cheartfield)==4 else None
                typename=cheartfield[3] if len(cheartfield)==4 else None
                self.loadDataField(obj,dfile,dim,tfile,typename)

            #if the representation argument is present and correct, generate a representation using the default material
            if conf.hasValue('args','--cheartrepr') and len(reprload)>0:
                reprtype=reprload[0]
                refine=int(reprload[1]) if len(reprload)>1 else 0
                externalOnly=bool(reprload[2]) if len(reprload)>2 else True
                rep=Future()
                self.mgr.addFuncTask(lambda:rep.setObject(obj().createRepr(reprtype,refine,externalOnly=externalOnly)))
                self.mgr.addFuncTask(lambda:self.mgr.addSceneObjectRepr(rep()))
                self.mgr.addFuncTask(mgr.setCameraSeeAll)

    def getHelp(self):
        return '''
Usage: --cheartload=XFILE,TFILE,BASIS [--cheartfield=DFILE,DIM[,TFILE,BASIS]]
                   [--cheartrepr=TYPE[,REFINE[,EXTERNONLY]]]

  Where:
    XFILE, TFILE, DFILE  Data file paths
    BASIS                Basis type identifier (eg Tet1NL)
    DIM, REFINE          Positive integers
    EXTERNONLY           'true' or 'false'.'''

    def getObjFiles(self,obj):
        xfiles,tfile,_,_,_,initXfile=obj.kwargs.get(CheartKeywords._loadargs,([],None,None,None,None,None))

        files=list(toIterable(xfiles))

        if tfile:
            files.append(tfile)

        if initXfile:
            files.append(initXfile)

        for dfiles,tfile,_,_,_,_ in obj.kwargs.get(CheartKeywords._datafieldargs,[]):
            files+=list(toIterable(dfiles))

            if tfile:
                files.append(tfile)

        return list(map(os.path.abspath,files))
        
    def checkFileOverwrite(self,obj,dirpath,name=None):
        oldname=obj.getName()
        newname=name or oldname
        prefixpath=os.path.join(dirpath,newname)
        
        inds=max(filter(isSpatialIndex,obj.datasets[0].indices.values()),key=len)
        indsname=inds.getName()
        
        result=[prefixpath+'.T']
        
        if len(obj.datasets)==1:
            result.append(prefixpath+'.X')
        else:
            result+=['%s%.4i.X'%(prefixpath,i) for i in range(len(obj.datasets))]
            
        for fieldname in obj.getFieldNames():
            dfs=toIterable(obj.getDataField(fieldname))
            spatial=dfs[0].meta(StdProps._spatial)

            # write out topology if needed
            topo=dfs[0].meta(StdProps._topology)
            if topo and topo!=indsname:
                topo=obj.datasets[0].getIndexSet(topo)
                result.append(prefixpath+getValidFilename(os.path.splitext(topo.getName())[0])+'_topo.T')


            isTimeCopy=dfs[0].meta(StdProps._timecopy)=='True' # true if the field has been copied to each timestep, so only write it out once
            if isTimeCopy: # if this is a time copy, reduce the list to one field and ensure the name doesn't get numbered
                dfs=[dfs[0]]

            for i,df in enumerate(dfs):
                dfname=getValidFilename(os.path.splitext(df.getName())[0])
                if dfname.startswith(newname):
                    dfprefix=os.path.join(prefixdir,dfname)
                else:
                    dfprefix=prefixpath+'_'+dfname

                if not isTimeCopy and len(dfs)>1: # number the filenames to ensure uniqueness and order
                    dfprefix='%s%.4i'%(dfprefix,i)

                result.append(dfprefix+'.D')
                
        return list(filter(os.path.exists,result))

    def renameObjFiles(self,obj,oldname,overwrite=False):
        if not isinstance(obj,SceneObject) or obj.getName()==oldname:
            return

        newname=obj.getName()
        indexnames={} # maps the old names of topologies to their new names
        xfiles,tfile,typename,loadSeq,loadTS,initXfile=obj.kwargs[CheartKeywords._loadargs]
        fields=list(obj.kwargs.get(CheartKeywords._datafieldargs,[]))
        
        def _moveFile(f):
            if f==None or not os.path.isfile(f):
                return None # if there's no filename or actual file, return None which indicates a file isn't used for a particular purpose
            else:
                newbasename=splitPathExt(f)[1]
                if oldname in newbasename:
                    newbasename=newbasename.replace(oldname,newname,1)
                else:
                    newbasename='%s_%s'%(newname,newbasename)
                    
                return renameFile(f,newbasename,overwriteFile=overwrite)

        # if a topology's name has `oldname' in it, store the mapping between names in indexnames
        for ds in obj.datasets:
            for ind in ds.enumIndexSets():
                oldindname=ind.getName()
                if oldname in oldindname:
                    newindname=oldindname.replace(oldname,newname,1)
                    indexnames[oldindname]=newindname

            ds.renameIndexSet(oldname,newname)
            ds.renameDataField(oldname,newname)

        # move .X files
        if isinstance(xfiles,str):
            xfiles=_moveFile(xfiles) # single file for static mesh
        else:
            xfiles=list(map(_moveFile,xfiles)) # multiple files for time-dependent mesh

        # rename .T file, initial .X file (for displacement series), and change the kwargs for the object
        tfile=_moveFile(tfile)
        initXfile=_moveFile(initXfile)
        obj.kwargs[CheartKeywords._loadargs]=(xfiles,tfile,typename,loadSeq,loadTS,initXfile)

        # rename fields and their topologies as necessary
        for i in range(len(fields)):
            dfiles,tfile,dim,typename,spatialName,loadSeq=fields[i]

            if isinstance(dfiles,str):
                dfiles=_moveFile(dfiles)
            else:
                dfiles=list(map(_moveFile,dfiles))

            spatialName=indexnames.get(spatialName,spatialName) # associate this field with the changed spatial name

            tfile=_moveFile(tfile)
            fields[i]=(dfiles,tfile,dim,typename,spatialName,loadSeq)

        # apply renaming to the field info stored in the object's kwargs
        if fields:
            obj.kwargs[CheartKeywords._datafieldargs]=tuple(fields)

    def copyObjFiles(self,obj,sdir,overwrite=False):
        xfiles,tfile,typename,loadSeq,loadTS,initXfile=obj.kwargs[CheartKeywords._loadargs]

        if isinstance(xfiles,str):
            filename=os.path.join(sdir,os.path.basename(xfiles))
            copyfileSafe(xfiles,filename,overwrite)
            xfiles=filename
        else:
            xfiles=list(xfiles)
            for i,x in enumerate(xfiles):
                xfiles[i]=os.path.join(sdir,os.path.basename(x))
                copyfileSafe(x,xfiles[i],overwrite)

        if tfile:
            filename=os.path.join(sdir,os.path.basename(tfile))
            copyfileSafe(tfile,filename,overwrite)
            tfile=filename

        if initXfile:
            filename=os.path.join(sdir,os.path.basename(initXfile))
            copyfileSafe(initXfile,filename,overwrite)
            initXfile=filename

        obj.kwargs[CheartKeywords._loadargs]=(xfiles,tfile,typename,loadSeq,loadTS,initXfile)

        if CheartKeywords._datafieldargs in obj.kwargs:
            newfields=[]
            for i,args in enumerate(obj.kwargs[CheartKeywords._datafieldargs]):
                dfiles,tfile,dim,typename,spatialName,loadSeq=args
                if isinstance(dfiles,str):
                    filename=os.path.join(sdir,os.path.basename(dfiles))
                    copyfileSafe(dfiles,filename,overwrite)
                    dfiles=filename
                else:
                    dfiles=list(dfiles)
                    for i,x in enumerate(dfiles):
                        dfiles[i]=os.path.join(sdir,os.path.basename(x))
                        copyfileSafe(x,dfiles[i],overwrite)

                if tfile:
                    filename=os.path.join(sdir,os.path.basename(tfile))
                    copyfileSafe(tfile,filename,overwrite)
                    tfile=filename

                newfields.append((dfiles,tfile,dim,typename,spatialName,loadSeq))

            obj.kwargs[CheartKeywords._datafieldargs]=newfields

    def getScriptCode(self,obj,**kwargs):
        configSection=kwargs.get('configSection',False)
        namemap=kwargs.get('namemap',{})
        varname=namemap[obj]
        scriptdir=kwargs['scriptdir']
        convertpath=kwargs['convertPath']

        if isinstance(obj,MeshSceneObject):
            script=''
            args={}

            if not configSection:
                xfiles,tfile,typename,loadSeq,loadTS,initXfile=obj.kwargs[CheartKeywords._loadargs]

                if isinstance(xfiles,str):
                    xfiles=[xfiles]

                tfile=convertpath(tfile)
                initXfile=convertpath(initXfile)

                if len(xfiles)>1:
                    xfiles=('['+','.join(map(convertpath,xfiles))+']')
                else:
                    xfiles=convertpath(xfiles[0])

                args={
                    'varname':varname,
                    'xfiles':xfiles,
                    'tfile':tfile,
                    'elemtype':('ElemType._'+typename if typename and tfile else '""'),
                    'loadSeq':loadSeq,
                    'loadTS':loadTS,
                    'initXfile':initXfile,
                    'objname':obj.getName()
                }
                script+='%(varname)s=CHeart.loadSceneObject(%(xfiles)s,%(tfile)s,%(elemtype)s,%(loadSeq)r,%(loadTS)r,%(initXfile)s,%(objname)r)'
            else:
                for args in obj.kwargs.get(CheartKeywords._datafieldargs,[]):
                    dfiles,tfile,dim,typename,spatialName,loadSeq=args
                    if isinstance(dfiles,str):
                        dfiles=[dfiles]

                    tfile=convertpath(tfile)

                    if len(dfiles)>1:
                        dfiles=('['+','.join(map(convertpath,dfiles))+']')
                    else:
                        dfiles=convertpath(dfiles[0])

                    args={
                        'varname':varname,
                        'dfiles':dfiles,
                        'tfile':tfile,
                        'dim':dim,
                        'spatialName':spatialName,
                        'loadSeq':loadSeq,
                        'elemtype':('ElemType._'+typename if typename and tfile else '""')
                    }

                    script+='%(varname)s.loadDataField(%(dfiles)s,%(dim)r,%(tfile)s,%(elemtype)s,%(spatialName)r,%(loadSeq)r)\n'%args

                args={'varname':varname,'timesteps':obj.getTimestepList()}
                script+='%(varname)s.setTimestepList(%(timesteps)r)\n'

            return setStrIndent(script % args).strip()+'\n'
        else:
            return MeshScenePlugin.getScriptCode(self,obj,**kwargs)

    def _openLoadDialog(self):
        d=LoadDialog(self)
        params=d.getParams()
        if params:
            xfile,tfile,elemtype=params
            if xfile=='':
                self.mgr.showMsg("Invalid X file '"+xfile+"'")
            elif tfile=='':
                self.mgr.showMsg("Invalid T file '"+tfile+"'")
            else:
                obj=self.loadSceneObject(xfile,tfile,elemtype)
                self.mgr.addFuncTask(lambda:self.mgr.addSceneObject(obj()))

    def _openLoadDataDialog(self):
        obj=self.win.getSelectedObject()

        if not obj or not isinstance(obj,MeshSceneObject):
            self.mgr.showMsg('A mesh object must be selected before data fields can be loaded for it','No scene object')
        else:
            d=LoadDataDialog(self)
            params=d.getParams()
            if params:
                dfiles,dim,tfile,elemtype=params
                self.loadDataField(obj,dfiles,dim,tfile,elemtype)

    def _openLoadTDDialog(self):
        d=LoadTDDialog(self)
        params=d.getParams()
        if params:
            xfile,tfile,ftfile,isAbsolute,datadim,elemtype,felemtype,starttime,interval,xkeyframes,dkeyframes=params

            lx=len(xkeyframes)
            ld=len(dkeyframes)
            
            # if one x file is specified copy this multiple times to produce a time series to match the time field
            if lx==1 and lx<ld:
                xkeyframes=[xkeyframes[0]]*ld
                lx=ld

            assert lx!=0 or ld!=0, 'Spatial or field keyframes must be provided.'
            assert lx==0 or ld==0 or lx==ld, 'Spatial and field keyframes must have the same number of both provided.'

            assert (lx>0 and isAbsolute) or len(xfile)>0

            timesteps=max(lx,ld)

            initialXFile=None if isAbsolute else xfile

            #if lx==0:
            #    xkeyframes=xfile

            obj=self.loadSceneObject(xkeyframes, tfile,elemtype,loadTimesteps=timesteps,initialXFile=initialXFile)

            if len(dkeyframes)>0:
                self.loadDataField(obj,dkeyframes,datadim,ftfile if ftfile!='' else None,felemtype)

            @self.mgr.addFuncTask
            def _add():
                o=Future.get(obj)
                o.setTimestepScheme(starttime,interval)
                self.mgr.addSceneObject(o)

    def _openSaveDialog(self):
        obj=self.win.getSelectedObject()
        if isinstance(obj,SceneObjectRepr):
            obj=obj.parent

        if not isinstance(obj,MeshSceneObject):
            self.mgr.showMsg('Error: Must select mesh data object to export','Cheart Export')
        else:
            filename=self.mgr.win.chooseFileDialog('Choose Cheart .T filename',filterstr='.T Files (*.T)',isOpen=False)
            if filename!='':
                self.saveSceneObject(filename,obj)

    def loadObject(self,filename,name=None,**kwargs):
        xfile=ensureExt(filename,'.X',True) # guess X filename based on T filename
        if not os.path.isfile(xfile):
            raise IOError('Cannot find X file to match %r'%filename)
            
        ttype=guessTopologyType(filename)
        return self.loadSceneObject(xfile,filename,'%s%i%s'%ttype)
        
    def saveObject(self,obj,path,overwrite=False,setFilenames=False,**kwargs):
        return self.saveSceneObject(path,obj,kwargs.get('indsname',None),setFilenames,overwrite)
        
    def loadSceneObject(self,xfiles,tfile,typename,loadSequential=False,loadTimesteps=0,initialXFile=None,objname=None):
        f=Future()
        @taskroutine('Loading CHeart Mesh')
        def _load(xfiles,tfile,typename,loadSequential,loadTimesteps,initialXFile,objname,task):
            with f:
                loadargs=(xfiles,tfile,typename,loadSequential,loadTimesteps,initialXFile)
                spatialName=splitPathExt(tfile)[1] if tfile else None
                elems=[]
                datasets=[]

                if isinstance(xfiles,str): # single node file, make into a list
                    xfiles=[xfiles]
                elif initialXFile: # initial node position file, all subsequent node files are displacement values
                    xfiles=[initialXFile]+xfiles

                if not objname:
                    basenames=list(map(os.path.basename,xfiles))
                    if tfile:
                        basenames.append(os.path.basename(tfile))
                    common=getStrListCommonality(basenames)
                    if common>3:
                        if basenames[0][common-1]=='.':
                            common-=1

                        objname=basenames[0][:common]
                    else:
                        objname='CheartObj'

                xfiles=loadFileSequence(xfiles,task=task)

                if not all(xfiles):
                    raise IOError('Unable to read CHeart data from files')

                initialXMat,header=xfiles.pop(0) if initialXFile else (None,None)

                if tfile:
                    topo,header=readTFile(tfile,typename,spatialName,tfile[-1].lower()=='b')
                    topo.sub(1) # 0-based indexing, the only sensible way
                    topo.meta(StdProps._isspatial,'True') # indicate that this is a spatial topology
                    elems.append(topo)

                for nodes,nheader in xfiles:
                    if initialXMat: # add initial position to displacement values
                        nodes.add(initialXMat)

                    name=splitPathExt(nodes.meta(StdProps._filename))[1]
                    datasets.append(PyDataSet(name,nodes,[e.clone() for e in elems]))

                # if a scene object with multiple timesteps is requested but the node data is static, clone the first dataset
                if loadTimesteps>0 and len(datasets)==1:
                    datasets=[datasets[0].clone('%s %i'%(datasets[0].getName(),i+1)) for i in range(loadTimesteps)]

                f.setObject(MeshSceneObject(objname,datasets,self,loadargs=loadargs))

        return self.mgr.runTasks(_load(xfiles,tfile,typename,loadSequential,loadTimesteps,initialXFile,objname),f,loadSequential)

    def saveSceneObject(self,prefixpath,obj,indsname=None,setObjArgs=False,overwrite=False):
        f=Future()
        @taskroutine('Saving CHeart Mesh')
        def _save(prefixpath,obj,indsname,setObjArgs,overwrite,task):
            with f:
                # these will be stored in the object's kwargs member to reflect the arguments to be passed to loadSceneObject() and loadDataField()
                loadargs=[[],None,None,False,0,None] # new arguments for loading the object
                datafieldargs=[] # new arguments for loading the fields

                prefixpath=os.path.splitext(prefixpath)[0] 
                if os.path.isdir(prefixpath):
                    prefixdir=prefixpath
                    prefixname=obj.getName()
                else:
                    prefixdir,prefixname=os.path.split(prefixpath)

                dds=obj.datasets
                inds=None

                if len(dds)==1:
                    dslist=[(prefixpath,dds[0])]
                else:
                    dslist=[('%s%.4i'%(prefixpath,i),ds) for i,ds in enumerate(dds)]
                
                # get the spatial topology, this either the topology named by `indsname' or the largest one stored in dds[0]
                if indsname:
                    inds=obj.getIndexSet(indsname) # choose the named index
                    
                if not inds:
                    # choose the largest spatial index, this is a kludge and obviously can cause problems
                    inds=max(filter(isSpatialIndex,dds[0].indices.values()),key=len)
                    indsname=inds.getName()

                # names of topologies and the files they get stored in must match so change the topology names in each of dds
#               for ds in dds:
#                   if not any(n.startswith(prefixname) for n in ds.getIndexNames()):
#                       ds.renameIndexSet(indsname,prefixname)

                indsname=inds.getName()
                loadargs[1]=prefixpath+'.T'
                loadargs[2]=inds.getType()

                # write out topology
                writeCheartBuffer(prefixpath+'.T',[inds.n(),dds[0].getNodes().n()],inds,1) # 1-based

                # write out .X files
                for prefix,ds in dslist:
                    nodes=ds.getNodes()
                    writeCheartBuffer(prefix+'.X',[nodes.n(),3],nodes)
                    loadargs[0].append(prefix+'.X')

                # write out fields with their topologies if needed
                for fieldname in obj.getFieldNames():
                    dfs=toIterable(obj.getDataField(fieldname))
                    spatial=dfs[0].meta(StdProps._spatial)
                    if spatial!=inds.getName():
                        continue

                    fieldarg=[[],None,1,None,splitPathExt(loadargs[1])[1],False]
                    datafieldargs.append(fieldarg)

                    # write out topology if needed
                    topo=dfs[0].meta(StdProps._topology)
                    if topo and topo!=indsname:
                        topo=dds[0].getIndexSet(topo)
                        toponame=prefixpath+getValidFilename(os.path.splitext(topo.getName())[0])+'_topo.T'
                        if not os.path.exists(toponame):
                            writeCheartBuffer(toponame,[topo.n(),dds[0].getNodes().n()],inds,1) # 1-based

                        fieldarg[1]=toponame
                        fieldarg[3]=topo.getType()

                    isTimeCopy=dfs[0].meta(StdProps._timecopy)=='True' # true if the field has been copied to each timestep, so only write it out once
                    if isTimeCopy: # if this is a time copy, reduce the list to one field and ensure the name doesn't get numbered
                        dfs=[dfs[0]]

                    # write out field matrices for this field
                    for i,df in enumerate(dfs):
                        dfname=getValidFilename(os.path.splitext(df.getName())[0])
                        if prefixname and dfname.startswith(prefixname):
                            dfprefix=os.path.join(prefixdir,dfname)
                        else:
                            dfprefix=prefixpath+'_'+dfname

                        if not isTimeCopy and len(dfs)>1: # number the filenames to ensure uniqueness and order
                            dfprefix='%s%.4i'%(dfprefix,i)

                        writeCheartBuffer(dfprefix+'.D',[df.n(),df.m()],df)

                        fieldarg[0].append(dfprefix+'.D')
                        fieldarg[2]=df.m()

                loadargs=tuple(loadargs)
                datafieldargs=tuple(map(tuple,datafieldargs))
                if setObjArgs:
                    if obj.plugin:
                        obj.plugin.removeObject(obj)
                    obj.plugin=self
                    obj.kwargs[CheartKeywords._loadargs]=loadargs
                    obj.kwargs[CheartKeywords._datafieldargs]=datafieldargs

                f.setObject((loadargs,datafieldargs))

        return self.mgr.runTasks(_save(prefixpath,obj,indsname,setObjArgs,overwrite),f)

    def loadDataField(self,obj,dfiles,dim,tfile=None,typename=None,spatialName=None,loadSequential=False,*args,**kwargs):
        f=Future()
        @taskroutine('Loading CHeart Field')
        def _load(obj,dfiles,dim,tfile,typename,spatialName,loadSequential,task):
            with f:
                dfiles=toIterable(dfiles)
                obj=Future.get(obj)
                datafieldargs=(dfiles,tfile,dim,typename,spatialName,loadSequential)

                if isinstance(obj,MeshSceneObject):
                    objname=obj.getName()
                    ds=obj.datasets[0]
                    obj.kwargs.setdefault(CheartKeywords._datafieldargs,[]).append(datafieldargs)
                else:
                    ds=obj
                    objname=''

                # if no data topology name given, choose the first spatial topology for this field
                spatialName=spatialName or first(i.getName() for i in ds.enumIndexSets() if isSpatialIndex(i))
                toponame=splitPathExt(tfile)[1] if tfile else spatialName
                ind=ds.getIndexSet(toponame)

                results=loadFileSequence(dfiles,None,dim,task)

                if not all(results):
                    raise IOError('Unable to read CHeart data field from files')

                if not ind and tfile: # if there's no topology by the given name and theres a tfile, load the tfile
                    ind,header=readTFile(tfile,typename,toponame,tfile[-1].lower()=='b')
                    ind.sub(1) # sensible 0-based indexing
                    ind.meta(StdProps._spatial,spatialName)

                datas=[]
                for buff,header in results:
                    bname=buff.getName()
                    if objname and bname.startswith(objname): # if the field names are prefixed with the object name, remove this prefixing
                        newname=bname[len(objname)+1:]
                        if newname[0] in ('_','-',' '):
                            newname=newname[1:]

                        buff.setName(newname)
                    buff.meta(StdProps._topology,toponame)
                    buff.meta(StdProps._spatial,spatialName)

                    if buff.n()!=ds.getNodes().n() and ind and buff.n()==ind.n():
                        buff.meta(StdProps._elemdata,'True')

                    datas.append(buff)

                # determine a field name from the commonality amongst the loaded field matrix names, used for time-dependent fields only
                names=[d.getName() for d in datas]
                fieldname=min(names,key=len)
                common=getStrListCommonality(names) or len(fieldname)
                fieldname=fieldname[:common].rstrip('0')

                for d in datas: # set each field matrix to have the same name
                    d.meta('oldname',d.getName())
                    d.setName(fieldname)

                if isinstance(obj,MeshSceneObject) and len(obj.datasets)>1:
                    # if there's only one matrix, make a list of the one matrix for each timestep, this shares the matrix between datasets
                    if len(datas)==1:
                        datas[0].meta(StdProps._timecopy,'True')
                        datas=datas*len(obj.datasets)

                    for d,ds1 in zip(datas,obj.datasets):
                        if not d.meta('oldname'): # recall the previous name of the matrix just in case
                            d.meta('oldname',d.getName())
                        d.setName(fieldname) # set the matrix name to the field name
                        ds1.setDataField(d)
                        if ind:
                            ds1.setIndexSet(ind)
                else:
                    for d in datas:
                        ds.setDataField(d)

                    if ind:
                        ds.setIndexSet(ind)

                f.setObject(datas if len(datas)>1 else datas[0])

        return self.mgr.runTasks(_load(obj,dfiles,dim,tfile,typename,spatialName,loadSequential),f)


addPlugin(CheartPlugin())

