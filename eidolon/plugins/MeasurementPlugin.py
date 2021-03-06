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

import eidolon
from eidolon import vec3, color, enum, first, fillList, Camera2DView, DrawContourMixin, DrawLineMixin, PolyHandle2D

from ..ui import QtWidgets, QtCore, Qt, Ui_Measure2DView, Ui_MeasureObjProp
from .SegmentPlugin import triangulateContour, generateContoursFromMask
from .PlotPlugin import TimePlotWidget
import itertools


# names of parameters for the measurement data file
DatafileParams=enum('name','title','srcimage','tracksrc','trackdata')

# types of measurements
MeasureType=enum('point','line','contour')

# extension of measurement files
measureExt='.measure'

defaultNumNodes=16 # default number of contour nodes
defaultColor=color(1,0,0) # default handle colour

# default colours for points
PointColors=(color(1,0,0),color(0,1,0),color(0,0,1),color(1,1,0),color(1,0,1),color(0,1,1),color(1,1,1))


def calculateLength(measure,objs):
    return [v[0].distTo(v[1]) for v in measure.values]


def calculateDisplacement(measure,objs):
    return [measure.values[0][0].distTo(v[0]) for v in measure.values]
    
    
def calculateCircumference(measure,objs):
    results=[]
    for v in measure.values:
        results.append(sum(a.distTo(b) for a,b in eidolon.successive(v,cyclic=True)))
        
    return results

    
def calculateArea(measure,objs):
    results=[]
    for v in measure.values:
        triinds=triangulateContour(v,True)
        results.append(sum(v[a].triArea(v[b],v[c]) for a,b,c in triinds))
        
    return results
    

def calculateImageVolume(measure,objs):
    area=calculateArea(measure,objs)
    img=first(o for o in objs if isinstance(o,eidolon.ImageSceneObject))
    if img:
        area*=img.getVoxelSize().z()
        
    return area


# List of metric calculation functions to apply to specific measurement types, values are (description, MeasureType, function)
# The function should accept two arguments, a Measurement object and a list of objects representing the main image object followed 
# by secondary objects. The Measurement object is expected to be on one of the planes of the main image, and the secondary
# objects are assumed to be the secondary visible objects in a 2D view.
MetricFuncs=enum(
    ('length','Length',MeasureType._line,calculateLength),
    ('disp','Displacement',MeasureType._point,calculateDisplacement),
    ('circum','Circumference',MeasureType._contour,calculateCircumference),
    ('area','Area',MeasureType._contour,calculateArea),
    #('volume','Volume',MeasureType._contour,calculateImageVolume),
    doc='Types of metrics to apply to measurements over time'
)
    

class Measurement(object):
    def __init__(self,name,mtype,col=(1,1,1),timesteps=[],values=[]):
        self.name=name
        self.mtype=mtype
        self.col=color(*col)
        self.timesteps=list(timesteps)
        self.values=[list(itertools.starmap(vec3,v)) for v in values] # list of lists, store values as vec3
        
        assert len(self.values)==len(self.timesteps)
        assert all(len(v)==len(self.values[0]) for v in self.values)
        assert mtype in MeasureType
        
    def clone(self):
        return Measurement(self.name,self.mtype,self.col,self.timesteps,self.values)
        
    def setHandlePoints(self,handle,timestep,margin=0):
        curtimeind=eidolon.minmaxIndices(abs(ts-timestep) for ts in self.timesteps)[0]
        assert 0<=curtimeind<len(self.values)
        
        for i,n in enumerate(self.values[curtimeind]):
            handle.setNode(i,n)
            
        handle.col=self.col
        
    def setHandleVisible(self,handle,timestep,margin):
        handle.setVisible(handle.isVisible() and (not margin or min(abs(ts-timestep) for ts in self.timesteps)<=margin))
        
    def updateValue(self,handle,timestep):
        curtimeind=eidolon.minmaxIndices(abs(ts-timestep) for ts in self.timesteps)[0]
        assert 0<=curtimeind<len(self.values)
        nodes=handle.getNodes()
        
        if nodes!=self.values[curtimeind]: # if the nodes are changed, update
            self.values[curtimeind]=nodes
            return True
        else:
            return False
            
    def addTimestep(self,timestep,values):
        self.timesteps.append(timestep)
        self.values.append(list(values))
        
        # resort timestep and values
        sortinds=eidolon.sortIndices(self.timesteps)
        self.timesteps=eidolon.indexList(sortinds,self.timesteps)
        self.values=eidolon.indexList(sortinds,self.values)
        
    def setTimesteps(self,timesteps,copyFirstValues=True):
        self.timesteps=timesteps
        if copyFirstValues or len(timesteps)!=len(self.values):
            self.values=[list(self.values[0]) for ii in timesteps]
        
    def __repr__(self):
        col=tuple(self.col)
        values=[list(map(tuple,v)) for v in self.values]
        return repr((self.name,self.mtype,col,self.timesteps,values))
        
            
class MeasureSceneObject(eidolon.DatafileSceneObject):
    def __init__(self,name,filename,plugin,**kwargs):
        filename=eidolon.ensureExt(filename,measureExt)
        datamap={
            DatafileParams.name: name,
            DatafileParams.title: name,
            DatafileParams.srcimage:'',
            DatafileParams.tracksrc:'',
            DatafileParams.trackdata:''
        }
        
        eidolon.DatafileSceneObject.__init__(self,name,filename,datamap,plugin,**kwargs)

    def getWidget(self):
        '''Get the docked widget for this object, or None if the user hasn't created one.'''
        return self.plugin.getObjectWidget(self)
        
    def getObjectNames(self):
        return [n for n in self.datamap if n not in DatafileParams]
        
    def addObject(self,sceneobj):
        basename=sceneobj.name or sceneobj.mtype
        sceneobj.name=eidolon.uniqueStr(basename,[sceneobj.mtype]+self.getObjectNames())
        self.datamap[sceneobj.name]=sceneobj
        return sceneobj.name
        
    def enumObjects(self):
        for name,val in self.datamap.items():
            if name not in DatafileParams:
                yield val

    def clearObjects(self):
        for n in list(self.datamap):
            if n not in DatafileParams:
                self.datamap.pop(n)
        
        
class MeasurePropertyWidget(QtWidgets.QWidget,Ui_MeasureObjProp):
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self,parent)
        self.setupUi(self)
        

class Measure2DWidget(QtWidgets.QWidget,Ui_Measure2DView):
    def __init__(self,parent=None):
        QtWidgets.QWidget.__init__(self,parent)
        self.setupUi(self)
            
            
class LabelPolyHandle2D(PolyHandle2D):
    def __init__(self,widg2D,pts,isClosed=False,col=color(1,0,0,1),etype=None,radius=None):
        PolyHandle2D.__init__(self,widg2D,pts,isClosed,col,etype,radius)
        self.label=None
        
    def setVisible(self,isVisible):
        PolyHandle2D.setVisible(self,isVisible)
        if self.label:
            self.label.setVisible(isVisible and self.isActive())
        
    def updatePositions(self):
        PolyHandle2D.updatePositions(self)

        if self.isVisible():
            self.label.setPosition(self.widg2D.getOrthoPosition(eidolon.avg(self.pts)))
            
            if len(self.pts)==2:
                text='Len: %g'%self.pts[0].distTo(self.pts[1])
            else:
                circ=sum(a.distTo(b) for a,b in eidolon.successive(self.pts,cyclic=True))
                triinds=triangulateContour(self.pts,True)
                area=sum(self.pts[a].triArea(self.pts[b],self.pts[c]) for a,b,c in triinds)
                
                text='Circ: %g\nArea:%g'%(circ,area)
                self.label.setHAlign(eidolon.H_CENTER)
                self.label.setVAlign(eidolon.V_CENTER)
                
            self.label.setText(text)
            
    def updateRepr(self):
        PolyHandle2D.updateRepr(self)
        
        if not self.label:
            self.label=self.widg2D.createFigure('label',eidolon.FT_TEXT)
            self.label.setTextHeight(20)
            self.label.setOverlay(True)
            self.label.setVisible(False)

        self.figs.append(self.label)
        
            
class MeasurementView(DrawLineMixin,DrawContourMixin,Camera2DView):
    
    measurementChanged=QtCore.pyqtSignal(int)

    def __init__(self,mgr,camera,parent=None):
        Camera2DView.__init__(self,mgr,camera,parent)
        DrawLineMixin.__init__(self)
        DrawContourMixin.__init__(self,defaultNumNodes)
        
        self.plugin=self.mgr.getPlugin('Measure')
        self.handlecol=defaultColor
        self.handleradius=5.0
        self.planeMargin=eidolon.Handle2D.defaultPlaneMargin
        
        self.lastUpdateTime=-1.0
        
        self.sceneobj=None
        
        self.handleNames={} # index -> Measurement object for each index in self.handles which is a measuring handle (not all handles are such)
        
        self.uiobj=Measure2DWidget()
        self.uiobj.measureBox.setParent(None)
        self.mainLayout.addWidget(self.uiobj.measureBox)
        
        self.uiobj.numCtrlBox.setValue(self.numNodes)
        self.uiobj.numCtrlBox.valueChanged.connect(self.setNumNodes)
        
        self.uiobj.cloneButton.clicked.connect(self._cloneObject)
        self.uiobj.delButton.clicked.connect(self._deleteObject)
        self.uiobj.saveButton.clicked.connect(self.save)
        self.uiobj.setPlaneButton.clicked.connect(self._setObjectPlane)
        self.uiobj.setStartButton.clicked.connect(self._setStartTime)
        self.uiobj.copyStepsButton.clicked.connect(self._copySteps)
        self.uiobj.trackButton.clicked.connect(self._motionTrack)
        
        self.uiobj.addPointButton.clicked.connect(self._addPointButton)
        self.uiobj.addLineButton.clicked.connect(self._addLineButton)
        self.uiobj.addContourButton.clicked.connect(self._addContourButton)
        
        self.uiobj.show3DBox.clicked.connect(lambda:self.setVisible3D(self.isVisible3D()))
        
        self.uiobj.objectList.itemSelectionChanged.connect(self._selectObject)
        
        self.measurementChanged.connect(lambda i:self.updateSceneObject())
        
        eidolon.setCollapsibleGroupbox(self.uiobj.measureBox,True)
        
#       self.uiobj.trackGroup.setVisible(False) # TODO: hide the track box until figured out how to track without close coupling
        
    def setSceneObject(self,sceneobj):
        self.sceneobj=sceneobj
        
        for i,ind in enumerate(sorted(self.handleNames)): # remove objects only, leave other handles alone
            self.removeHandle(ind-i)

        self.handleNames={}

        for mobj in tuple(self.sceneobj.enumObjects()):
            if isinstance(mobj,tuple):
                mobj=Measurement(*mobj)
                
            self.addMeasurement(mobj)
            
        self.setActiveObject('') # select nothing
        
    def updateSceneObject(self):
        if self.sceneobj:
            self.sceneobj.clearObjects()
            for i,v in self.handleNames.items():
                self.sceneobj.addObject(v) 
                
    def save(self):
        if self.sceneobj:
            self.updateSceneObject() 

            if not os.path.isfile(self.sceneobj.filename):
                self.sceneobj.filename=eidolon.ensureExt(self.sceneobj.plugin.getFilename(False),measureExt)
            self.sceneobj.save()

    def setNumNodes(self,n):
        if n>=4:
            self.numNodes=n
            with eidolon.signalBlocker(self.uiobj.numCtrlBox):
                self.uiobj.numCtrlBox.setValue(n)

        self._repaintDelay()
        
    def addMeasurement(self,mobj):
        '''Add the Measurement object `mobj' to the list of measurements and create an appropriate handle.'''
        if mobj.mtype==MeasureType.point:
            h=eidolon.PointHandle2D(self,mobj.values[0][0],mobj.col)
        elif mobj.mtype==MeasureType.line:
            h=LabelPolyHandle2D(self,mobj.values[0][:2],False,mobj.col,eidolon.ElemType.Line1NL,self.handleradius)
        elif mobj.mtype==MeasureType.contour:
            h=LabelPolyHandle2D(self,mobj.values[0],True,mobj.col,eidolon.ElemType.Line1PCR,self.handleradius)
            
        i=len(self.handles)
        self.addHandle(h)
        self.handleNames[i]=mobj
        self.measurementChanged.emit(i)
        
    def createMeasurement(self,mtype,col,values,name=None,timesteps=None):
        '''Create and add a new Measurement object of type `mtype', color `col', with points `values'.'''
        
        existingnames=list(map(first,MeasureType))+[n.name for n in self.handleNames.values()] # ensures names are unique and always numbered
        name=eidolon.uniqueStr(name or mtype,existingnames) 
        timesteps=[self.mgr.timestep] if timesteps==None else timesteps
        col=col or self.handlecol
        if not isinstance(values[0],list):
            values=[values]

        mobj=Measurement(name,mtype,col,timesteps,values)
        self.addMeasurement(mobj)
        self.setActiveObject(mobj.name)
        
        return mobj
        
    def getMeasurement(self,i):
        return self.handleNames[i]
        
    def addPoint(self,point,col=None,name=None,timestep=None):
        return self.createMeasurement(MeasureType.point,col,[point],name,timestep)
        
    def addLine(self,start,end,col=None,name=None,timestep=None):
        return self.createMeasurement(MeasureType.line,col,[start,end],name,timestep)
        
    def addContour(self,nodes,col=None,name=None,timestep=None):
        return self.createMeasurement(MeasureType.contour,col,nodes,name,timestep)
        
    def setActiveObject(self,name):
        for i,v in self.handleNames.items():
            self.handles[i].setActive(v.name==name)

        listitem=first(self.uiobj.objectList.findItems(name+' @ ',Qt.MatchStartsWith))
        if listitem:
            with eidolon.signalBlocker(self.uiobj.objectList):
                self.uiobj.objectList.setCurrentItem(listitem)
                
        self._repaintDelay()

    def handleSelected(self,handle):
        self.setActiveObject(self.handleNames[self.handles.index(handle)].name)
        
    def getActiveIndex(self):
        return first(i for i in self.handleNames if i<len(self.handles) and self.handles[i].isActive())

    def removeHandle(self,index):
        if index!=None:
            for i in sorted(self.handleNames.keys()):
                if i==index: # remove the entry for this handle
                    self.handleNames.pop(index)
                elif i>index: # move entries indexed above this handle down 1
                    self.handleNames[i-1]=self.handleNames.pop(i)

            Camera2DView.removeHandle(self,index)

    def removeHandles(self):
        Camera2DView.removeHandles(self)
        self.handleNames={}
        
    def updateView(self):
        self.fillLineFig()
        self.fillContourFig()
        
        handles=sorted(self.handleNames.items())
        
        # fill the handles list, selecting the active handle
        objects=['%s @ %.2f->%.2f (%s)'%(mobj.name,mobj.timesteps[0],mobj.timesteps[-1],mobj.mtype) for i,mobj in handles]
        selected=self.getActiveIndex()
        fillList(self.uiobj.objectList,objects,selected if selected!=None else -1,None,True)

        curtime=self.mgr.timestep
        rep=self.mgr.findObject(self.sourceName)
        tslist=rep.getTimestepList() if rep else []
        tsmargin=eidolon.avgspan(tslist)/2 if len(tslist)>=2 else 0
        #mintimeind=minmaxIndices(abs(ts-curtime) for ts in tslist)[0] if rep else -1

        # set the handle for each measurement object to the data for the current timestep
        if curtime!=self.lastUpdateTime:
            self.lastUpdateTime=curtime
            for i,mobj in handles:
                mobj.setHandlePoints(self.handles[i],curtime,tsmargin)
            
        Camera2DView.updateView(self)   
        
        for i,mobj in handles:
            mobj.setHandleVisible(self.handles[i],curtime,tsmargin)
            
        fillList(self.uiobj.trackDataBox,sorted(list(self.plugin.trackSrcs)))
    
    def mousePress(self,e):
        if DrawLineMixin.drawMousePress(self,e) or DrawContourMixin.drawMousePress(self,e):
            return
        
        Camera2DView.mousePress(self,e)

    def mouseRelease(self,e):
        self.uiobj.addContourButton.setStyleSheet('')
        self.uiobj.addLineButton.setStyleSheet('')
        
        if DrawLineMixin.drawMouseRelease(self,e):
            self.addLine(self.lineStart,self.lineEnd)
            self._repaintDelay()
        elif DrawContourMixin.drawMouseRelease(self,e):
            self.addContour(self.contour)
            self._repaintDelay()
        else:
            i=self.getActiveIndex()
            if i!=None and self.handles[i].isVisible():
                if self.handleNames[i].updateValue(self.handles[i],self.mgr.timestep):
                    self.measurementChanged.emit(i)
            
            Camera2DView.mouseRelease(self,e)

    def mouseDrag(self,e,dx,dy):
        if DrawLineMixin.drawMouseDrag(self,e,dx,dy) or DrawContourMixin.drawMouseDrag(self,e,dx,dy):
            self._repaintDelay()
        else:
            Camera2DView.mouseDrag(self,e,dx,dy)
            
    def isVisible3D(self):
        return self.uiobj.show3DBox.isChecked()

    def setVisible3D(self,isVisible):
        eidolon.setChecked(isVisible,self.uiobj.show3DBox)

        for i in self.handleNames:
            self.handles[i].setVisible3D(isVisible)

        self.mgr.repaint(False)
            
    def _selectObject(self):
        if self.uiobj.objectList.currentItem():
            text=str(self.uiobj.objectList.currentItem().text())
            self.setActiveObject(text.split('@')[0].strip())
            
    def _addPointButton(self):
        p=self.getWorldPosition(0.5,0.5,False)
        self.addPoint(p,self.handlecol)
        
    def _addLineButton(self):
        if not self.drawingContour:
            self.startLineDraw()
            self.uiobj.addLineButton.setStyleSheet('border: 1px solid rgb(255,0,0);')
            
    def _addContourButton(self):
        if not self.drawingLine:
            self.startContourDraw()
            self.uiobj.addContourButton.setStyleSheet('border: 1px solid rgb(255,0,0);')
        
    def _deleteObject(self):
        self.removeHandle(self.getActiveIndex())
        
    def _setObjectPlane(self):
        i=self.getActiveIndex()
        if i!=None:
#           h=self.handles[i]
#           nodes=h.getNodes()
#           for n in range(len(nodes)):
#               x,y,_=self.getScreenPosition(nodes[n])
#               h.setNode(n,self.getWorldPosition(x,y))
#
#           if self.handleNames[i].updateValue(h,self.mgr.timestep):
#               self.measurementChanged.emit(i)
        
            m=self.handleNames[i]
            
            for ts in m.values:
                for j,n in enumerate(ts):
                    x,y,_=self.getScreenPosition(n)
                    ts[j]=self.getWorldPosition(x,y)
                
            self.measurementChanged.emit(i)
            self._repaintDelay()
    
    def _setStartTime(self):
        i=self.getActiveIndex()
        if i!=None:
            m=self.handleNames[i]
            m.timesteps=[self.mgr.timestep]
            m.values=[m.values[0]]
            self.measurementChanged.emit(i)
            
    def _cloneObject(self):
        i=self.getActiveIndex()
        if i!=None:
            #m=self.handleNames[i].clone()
            #m.name=uniqueStr(m.mtype,[n.name for n in self.handleNames.values()]) # ensure name uniqueness
            #self.addMeasurement(m)
            m=self.handleNames[i]
            self.createMeasurement(m.mtype,m.col,m.values,None,m.timesteps)
            
    def _copySteps(self):
        i=self.getActiveIndex()
        rep=self.mgr.findObject(self.sourceName)
        if i!=None and rep!=None:
            m=self.handleNames[i]
            m.setTimesteps(rep.getTimestepList())
            self.measurementChanged.emit(i)
        
    def _motionTrack(self):
        i=self.getActiveIndex()
        rep=self.mgr.findObject(self.sourceName)
        trackdata=str(self.uiobj.trackDataBox.currentText())
        
        if not trackdata:
            self.mgr.showMsg('No source for motion track data','No Track Data')
        elif i!=None and rep!=None:
            m=self.handleNames[i]
            m.timesteps=rep.getTimestepList()
            
            result=self.plugin.trackSrcs[trackdata](trackdata,m.values[0])
            m.values=[]
            
            for ts in m.timesteps:
                _,pts=min((abs(ts-t),p) for t,p in result.items())
                m.values.append(pts)
                
            self.measurementChanged.emit(i)
            
        
class MeasurementPlotWidget(TimePlotWidget):
    def __init__(self,plugin,parent=None):
        TimePlotWidget.__init__(self,plugin,parent)
        self.measureCache={} # maps (measurement name, metric name) to (is visible, timestep,line data) tuples
        self.setObjectName('Measurement Plot')
        
    def isLineVisible(self,measure,metric):
        k=(measure.name,metric)
        return k in self.measureCache and self.measureCache[k][0]
        
    def setLineVisible(self,measure,metric,isVisible):
        k=(measure.name,metric)
        if k in self.measureCache:
            self.measureCache[k]=(isVisible,measure.timesteps,self.measureCache[k][-1])
            self.updatePlot()
            
    def setMeasurement(self,measure,metric,data):
        self.measureCache[(measure.name,metric)]=(True,measure.timesteps,data)
        self.updatePlot()
    
    def updatePlot(self):
        @self.plugin.mgr.callThreadSafe
        def _update():
            data=[]
            timesteps=[]
            labels=[]
            
            for mname,metric in self.measureCache:
                isVis,timestep,linedata=self.measureCache[(mname,metric)]
                if isVis:
                    labels.append('%s (%s)'%(mname,MetricFuncs[metric][0]))
                    timesteps.append(timestep)
                    data.append(linedata)
                
            self.setData(data,timesteps,labels)
            self.repaint()
            
        
class MeasureSplitView(QtWidgets.QSplitter):
    def __init__(self,mgr,camera,parent=None):
        QtWidgets.QSplitter.__init__(self)
        self.mgr=mgr
        self.setOrientation(Qt.Horizontal)
        self.setChildrenCollapsible(True)
        self.measure=MeasurementView(mgr,camera,self)
        
        self.measure.measurementChanged.connect(self.updateMeasurement)
        
        self.plotwidg=QtWidgets.QWidget(self)
        self.plotLayout=QtWidgets.QVBoxLayout(self.plotwidg)

        self.plot=MeasurementPlotWidget(mgr.getPlugin('Plot'),self.plotwidg)
        
        self.plotctrls=QtWidgets.QGroupBox('Choose Plot Measurements',self.plotwidg)
        self.plotCtrlLayout=QtWidgets.QHBoxLayout(self.plotctrls)

        self.chooseMenu=QtWidgets.QMenu(self)       
        self.plotChooseButton=QtWidgets.QToolButton(self.plotctrls)
        self.plotChooseButton.setText('Choose Measurements')        
        self.plotChooseButton.setMenu(self.chooseMenu)
        self.plotChooseButton.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        
        self.plotCtrlLayout.addWidget(self.plotChooseButton)
        
        self.plotLayout.addWidget(self.plot)
        self.plotLayout.addWidget(self.plotctrls)
        
    def setSceneObject(self,sceneobj):
        self.measure.setSceneObject(sceneobj)
        
    def parentClosed(self,e):
        self.measure.parentClosed(e)
        self.plot.parentClosed(e)
        
    def fillChooseMenu(self):
        def _addAction(measure,metric):
            '''Use a subroutine to ensure `measure' and `metric' are fresh variables for each call to connect().'''
            action=self.chooseMenu.addAction('%s (%s)'%(measure.name,MetricFuncs[metric][0]))
            action.setCheckable(True)
            action.setChecked(self.plot.isLineVisible(measure,metric))
            action.toggled.connect(lambda b:self.setLineVisible(measure,metric,b))
    
        self.chooseMenu.clear()
        for m in self.measure.sceneobj.enumObjects():
            for mf in MetricFuncs:
                if mf[2]==m.mtype:
                    _addAction(m,mf[0])
            
    @eidolon.taskmethod('Calculating Plot')
    def setMeasurement(self,measure,metric,objs,task):
        linedata=MetricFuncs[metric][2](measure,objs)
        self.plot.setMeasurement(measure,metric,linedata)
        return linedata
                    
    def setLineVisible(self,measure,metric,isVisible):
        if isVisible and (measure.name,metric) not in self.plot.measureCache:
            objs=[self.mgr.findObject(n).parent for n in self.measure.getObjectNames() if n]
            f=self.setMeasurement(measure,metric,objs)
            #self.mgr.checkFutureResult(f)
        else:
            self.plot.setLineVisible(measure,metric,isVisible)
                    
    def updateMeasurement(self,i):
        self.fillChooseMenu()
        m=self.measure.getMeasurement(i)
        objs=[self.mgr.findObject(n).parent for n in self.measure.getObjectNames() if n]
        
        for k in list(self.plot.measureCache):
            if k[0]==m.name:
                if not self.plot.measureCache[k][0]:
                    self.plot.measureCache.pop(k)
                else:
                    self.setMeasurement(m,k[1],objs)
                

class MeasurePlugin(eidolon.ScenePlugin):
    def __init__(self):
        eidolon.ScenePlugin.__init__(self,'Measure')
        self.dockmap={}
        # maps source name/directory to function accepting (name, points list) and returns mapping from timesteps to list of points tracked to that time
        self.trackSrcs={} 
        
    def init(self,plugid,win,mgr):
        eidolon.ScenePlugin.init(self,plugid,win,mgr)
        if win:
            win.addMenuItem('Create','NewMeasure'+str(plugid),'&Measurement Object',self._createMeasure)
            win.addMenuItem('Import','ImportMeasure'+str(plugid),'&Measurements',self._importMeasure)

        if mgr.conf.hasValue('args','--measure'):
            @eidolon.taskroutine('Loading Measurement File(s)')
            def _loadTask(filenames,task=None):
                for f in filenames:
                    obj=self.loadObject(f)
                    self.mgr.addSceneObject(obj)

            self.mgr.runTasks(_loadTask(mgr.conf.get('args','--measure').split(',')))

    def _importMeasure(self):
        filename=self.getFilename()
        if filename:
            obj=self.loadObject(filename)
            self.mgr.addSceneObject(obj)

    def _createMeasure(self):
        obj=self.createMeasurementObject('','Measurement')
        self.mgr.addSceneObject(obj)

    def getMenu(self,obj):
        return [obj.getName(),'Show Measurement View'],self.objectMenuItem

    def getFilename(self,isOpen=True):
        return self.mgr.win.chooseFileDialog('Choose Measurement filename',filterstr='Measurement Files (*%s)'%measureExt,isOpen=isOpen)

    def getObjectWidget(self,obj):
        return first(w for w in self.win.dockWidgets if id(w)==self.dockmap.get(obj.getName(),-1))

    def objectMenuItem(self,obj,item):
        if item=='Show Measurement View':
            self.mgr.addFuncTask(lambda:obj.createRepr(None))

    def createObjPropBox(self,obj):
        prop=MeasurePropertyWidget()

        prop.createContButton.clicked.connect(lambda:self._createContoursButton(prop,obj))
        prop.showButton.clicked.connect(lambda:self.mgr.addFuncTask(lambda:obj.createRepr(None)))
        prop.srcBox.activated.connect(lambda i:obj.set(DatafileParams.srcimage,str(prop.srcBox.itemText(i))))

        return prop

    def updateObjPropBox(self,obj,prop):
        if not prop.isVisible():
            return
        
        prop.ctrlsBox.setValue(defaultNumNodes)

        imgnames=[o.getName() for o in self.mgr.objs if isinstance(o,eidolon.ImageSceneObject)]

        eidolon.fillTable(obj.getPropTuples(),prop.propTable)
        eidolon.fillList(prop.srcBox,imgnames,obj.get(DatafileParams.srcimage))
        
        eidolon.fillList(prop.maskImgBox,imgnames)
        
    def acceptFile(self,filename):
        return eidolon.splitPathExt(filename)[2].lower() == measureExt
        
    def checkFileOverwrite(self,obj,dirpath,name=None):
        outfile=os.path.join(dirpath,name or obj.getName())+measureExt
        if os.path.exists(outfile):
            return [outfile]
        else:
            return []

    def renameObjFiles(self,obj,oldname,overwrite=False):
        assert isinstance(obj,eidolon.SceneObject) and obj.plugin==self
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
            script+='%(varname)s = Measure.loadObject(%(filename)s,%(objname)r)\n'

        return eidolon.setStrIndent(script % args).strip()+'\n'

    def createMeasurementObject(self,filename,name):
        return MeasureSceneObject(name,filename,self)

    @eidolon.taskmethod('Creating Segmentation View')
    def createRepr(self,obj,reprtype,refine=0,task=None,**kwargs):
        sobj=self.mgr.findObject(obj.get(DatafileParams.srcimage))
        
        # make a representation of the source object visible if one doesn't already exist
        if isinstance(sobj,eidolon.ImageSceneObject) and not len(sobj.reprs):
            isEmpty=first(self.mgr.enumSceneObjectReprs())==None
            r=sobj.createRepr(eidolon.ReprType._imgtimestack if sobj.isTimeDependent else eidolon.ReprType._imgstack)
            self.mgr.addSceneObjectRepr(r)
            if isEmpty:
                self.mgr.setCameraSeeAll()
                self.mgr.repaint()

        return self.getMeasurementDock(obj)

    def getMeasurementDock(self,obj,w=400,h=400):
        @self.mgr.proxyThreadSafe
        def createWidget():
            widg=self.mgr.create2DView(obj.get(DatafileParams.name),MeasureSplitView)#MeasurementView)
            self.dockmap[obj.getName()]=id(widg)
            widg.setSceneObject(obj)
            return widg

        if self.win:
            self.win.sync()
            widg=first(d for d in self.win.dockWidgets if id(d)==self.dockmap.get(obj.getName(),-1))
            return widg or createWidget()

    def loadObject(self,filename,name=None,**kwargs):
        obj=self.createMeasurementObject(filename,name or eidolon.splitPathExt(filename)[1])
        obj.load()
        return obj
        
    def saveObject(self,obj,path,overwrite=False,setFilenames=False,**kwargs):
        if not isinstance(obj,MeasureSceneObject) or not isinstance(obj.plugin,MeasurePlugin):
            raise ValueError('Can only save measurement objects with MeasurePlugin')
            
        if os.path.isdir(path):
            path=os.path.join(path,eidolon.getValidFilename(obj.getName()))
            
        path=eidolon.ensureExt(path,measureExt)
        oldpath=obj.filename
        obj.filename=path
        obj.save()
        
        if not setFilenames: # set the filename back to the original if we're not supposed to change it
            obj.filename=oldpath
        
        return path
        
    def addTrackSource(self,name,func):
        '''
        Add the tracking source for the name/directory `name'. The `func' callable must accept 2 arguments, the name
        it was keyed to and a list of vec3 points, and return a dict mapping timesteps to the motion tracked data
        at that time.
        '''
        self.trackSrcs[name]=func
        
    def removeTrackSource(self,name_or_func):
        '''Remove all tracking sources using the given name or function.'''
        for n,f in list(self.trackSrcs.items()):
            if name_or_func in (n,f):
                del self.trackSrcs[n]
                
    @eidolon.taskmethod('Add segmentations from mask image')
    def addMaskSegmentations(self,obj,mask,numctrls,innerseg,minSegSize=100,refine=2,task=None):
        contours=generateContoursFromMask(mask.images,numctrls,innerseg,minSegSize,2,task)
        
        for ts,nodes in contours:
            mobj=Measurement('contour',MeasureType.contour,defaultColor,[ts],[nodes])
            obj.addObject(mobj)
            
        widg=obj.getWidget()
        if widg:
            self.mgr.callThreadSafe(widg.setSceneObject,obj)
        
    
    def _createContoursButton(self,prop,obj):
        maskname=str(prop.maskImgBox.currentText())
        numctrls=prop.ctrlsBox.value()
        innerseg=prop.innerContBox.isChecked()
        mask=self.findObject(maskname)
        
        f=self.addMaskSegmentations(obj,mask,numctrls,innerseg)
        self.mgr.checkFutureResult(f)
        
        
eidolon.addPlugin(MeasurePlugin())

