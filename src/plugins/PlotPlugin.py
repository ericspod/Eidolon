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


'''
This module defines a SceneObject type, widgets, and a plugin for displaying plottable data. The widgets available include
a basic graph type, an AHA region plot, and a pool region plot. The PlotSceneObject type stores named values to config
files and is relied upon by the widgets as the source of data. The enum DatafileParams lists the entry names that are used
by the plots. The important one is DatafileParams._matrix which defines the 2D data matrix the plots represent for time-
dependent plots, or a map from names to a list of data for plots that are not time-dependent. For time-dependent, each row
of the matrix represents the values for a named data object whose name is in the same index of the DatafileParams._labels
list of label strings. Each column in the matrix represents the value for each of the object's at that timestep index, the
specific timestep times for each column are given in the list DatafileParams._timesteps. All rows in the matrix  and
DatafileParams._timeteps must therefore be the same length. The entry DatafileParams._widgettype names the type of widget
to create to represent a plot object, this must correspond to the type of data stored.

A simple graph with two values can be added to the scene as such:

    p=Plot.createPlotObject('test.plot','test','Test Plot',{'foo':(1,2,3),'bar':(2,-1,5)},[],Plot.SimpleGraphWidget)
    mgr.addSceneObject(p)

A simple time graph plotting two values over time can be added to the scene as such:

    p=Plot.createPlotObject('test.plot','test','Test Plot',[(1,2,3),(2,-1,5)],[10,20,30],Plot.TimePlotWidget)
    mgr.addSceneObject(p)

'''

from eidolon import Qt, QtGui, QtCore, QtWidgets, SceneObject, ScenePlugin
from eidolon import enum,lerp, minmax, isIterable, toIterable, first, matIter, clamp, EventType, halfpi,splitPathExt
import eidolon

from ui import Ui_RegionGraphWidget

eidolon.addLibraryFile('pyqtgraph-0.10.0')

import pyqtgraph as pg
import numpy as np
import math
import os

DatafileParams=enum(
    'name',
    'title',
    'matrix',
    'timesteps',
    'widgettype',
    'srcobject',
    'labels',
    'ispercent',
    'istimed',
)

AHARegionNames=enum(
    'Basal Anterior',
    'Basal Anteseptal',
    'Basal Inferoseptal',
    'Basal Inferior',
    'Basal Inferolateral',
    'Basal Anterolateral',
    'Mid Anterior',
    'Mid Anteseptal',
    'Mid Inferoseptal',
    'Mid Inferior',
    'Mid Inferolateral',
    'Mid Anterolateral',
    'Apical Anterior',
    'Apical Septal',
    'Apical Inferior',
    'Apical Lateral,',
    'Apex'
)


class ColorBar(pg.GraphicsObject):
    '''
    Basic vertical color bar with labels ranging from a minimal to maximal value. The intent is for this to be embedded
    in a scene with another graph and share its color graph and height.
    '''
    def __init__(self, colormap, x,y,width, height, numticks):
        pg.GraphicsObject.__init__(self)

        self.colormap=colormap
        self.cx=x
        self.cy=y
        self.cwidth=width
        self.cheight=height
        self.minval=0.0
        self.maxval=1.0
        self.numticks=numticks
        self.pic = QtGui.QPicture()

        self.drawBar()
        self.translate(self.cx,self.cy)

    def drawBar(self):
        '''Redraw the bar into the self.pic value. This should be called after changing any stored value.'''
        stops, colors = self.colormap.getStops('float')

        with QtGui.QPainter(self.pic) as p:
            p.setPen(pg.mkPen('w'))
            grad = QtGui.QLinearGradient(self.cwidth/2.0, 0.0, self.cwidth/2.0, self.cheight*1.0)

            for stop, color in zip(stops, colors):
                grad.setColorAt(1.0 - stop, QtGui.QColor(*[255*c for c in color]))

            p.setBrush(QtGui.QBrush(grad))
            p.drawRect(QtCore.QRectF(0, 0, self.cwidth, self.cheight))

            for tick in range(self.numticks):
                tick/=float(self.numticks-1)
                y=(1-tick)*self.cheight
                p.drawLine(self.cwidth, y, self.cwidth+5.0, y)

                label='%.3f'%lerp(tick,self.minval,self.maxval)
                br = p.boundingRect(0, 0, 0, 0, Qt.AlignLeft, label)
                p.drawText(self.cwidth+8.0,y+br.height()/4,label)

    def paint(self, p, *args):
        p.setPen(QtGui.QColor(255, 255, 255, 0))
        p.setBrush(QtGui.QColor(255, 255, 255, 0))
        p.drawPicture(0, 0, self.pic)

    def boundingRect(self):
        return QtCore.QRectF(self.pic.boundingRect())

    def setValRange(self,minval,maxval):
        '''Set the bar's value range.'''
        self.minval=minval
        self.maxval=maxval
        self.drawBar()

    def setParentHeight(self,h):
        '''Set the height of the bar based on the containing parent's height `h'.'''
        self.cheight=h-self.cy*2
        self.drawBar()


class BasePlotWidget(pg.PlotWidget):
    def __init__(self,plugin,parent=None):
        assert eidolon.isMainThread()
        pg.PlotWidget.__init__(self,parent)
        self.plugin=plugin
        self.title=''
        self.updatedData=False
        self.legend=None

    def setTitle(self,title):
        '''Sets the title to the given string and calls setUpdated().'''
        self.title=title
        self.setUpdated()

    def setUpdated(self):
        self.updatedData=True
        self.update()

    def setShowLegend(self,show=True,update=True):
        '''Sets the legend visibility to `show' or updates it if already visible and `update' is True.'''
        if self.legend and (update or not show):
            self.legend.scene().removeItem(self.legend)
            self.legend=None

        if show and not self.legend:
            self.legend=self.addLegend()

    def paintEvent(self,e):
        if self.updatedData:
            self.updatedData=False
            self.updateGraph()

        pg.PlotWidget.paintEvent(self,e)

    def updateGraph(self):
        '''
        Called by paintEvent() to trigger the graph to update itself based on stored data that has changed. This will
        execute in the main thread.
        '''
        pass

    def setPlotObjectData(self,obj):
        '''
        Called when the data from the given PlotSceneObject should be passed to the graph widget.
        This should call setUpdated().
        '''
        pass

    def getDataTable(self):
        '''Return a list of column labels and a list of column data lists for data export, or (None,None).'''
        return None,None


class SimpleGraphWidget(BasePlotWidget):
    def __init__(self,plugin,parent=None):
        BasePlotWidget.__init__(self,plugin,parent)
        self.graphmap={}
        self.items=[]

    def updateGraph(self):
        self.clear()
        self.setShowLegend()
        self.plotItem.setTitle(self.title)

        for i,(name,values) in enumerate(self.graphmap.items()):
            if len(values)==2 and isIterable(values[0]) and isIterable(values[1]) and len(values[0])==len(values[1]):
                xdata,ydata=values
            else:
                xdata=list(range(len(values)))
                ydata=values

            plot=self.plot(xdata,ydata,name=name,pen=(i,len(self.graphmap)))
            self.items.append(plot)

    def updateGraphData(self,graphmap):
        self.graphmap.update(graphmap)
        self.setUpdated()

    def setPlotObjectData(self,obj):
        self.title=obj.get(DatafileParams._title)
        self.updateGraphData(obj.get(DatafileParams._matrix))

    def getDataTable(self):
        labels=sorted(self.graphmap.keys())
        cols=[self.graphmap[l] for l in labels]
        return labels,cols


class TimePlotWidget(BasePlotWidget):
    def __init__(self,plugin=None,parent=None):
        BasePlotWidget.__init__(self,plugin,parent)
        self.currentTime=0
        self.setData([[]],[],[])
        self.ylabel=''
        self.legendwidth=65.0
        self.lines={}
        self.timeplot=None
        self.updatedTime=False
        self.timepen={'color': '#dddddd', 'width': 0.5,'style':Qt.DashLine}

        if self.plugin:
            self.plugin.mgr.addEventHandler(EventType._widgetPreDraw,self.setCurrentTime)

    def parentClosed(self,e):
        self.plugin.mgr.removeEventHandler(self.setCurrentTime)

    def setCurrentTime(self,val=None):
        if val==None:
            val=self.plugin.mgr.timestep

        newtime=clamp(val,self.timeMin,self.timeMax)
        if newtime!=self.currentTime:
            self.currentTime=newtime
            self.updatedTime=True
            self.setUpdated()

    def updateGraph(self):
        if self.updatedTime:
            self.updatedTime=False
            timelabel='Time' #'Time @ %.3f'%(self.currentTime)
            timex=[self.currentTime]*2
            timey=self.dataRange

            if not self.timeplot:
                self.timeplot=self.plot(timex,timey,name=timelabel,pen=self.timepen)
                if self.legend:
                    self.legend.removeItem(timelabel)
            else:
                self.timeplot.setData(timex,timey,name=timelabel,pen=self.timepen)

        self.legend=self.legend or self.addLegend()
        self.showGrid(x=True,y=True)

        for name in self.lines.keys():
            if name not in self.labels:
                line=self.lines.pop(name)
                self.removeItem(line)
                self.legend.removeItem(name)

        for i,(data,timesteps,label) in enumerate(zip(self.dataseries,self.timesteps,self.labels)):
            if label not in self.lines:
                self.lines[label]=self.plot(timesteps,data,name=label,pen=(i,len(self.dataseries)))
            else:
                self.lines[label].setData(timesteps,data,name=label,pen=(i,len(self.dataseries)))

        self.plotItem.setTitle(self.title)
        if len(self.dataseries)>0:
            self.autoRange()

    def setPlotObjectData(self,obj):
        mat=obj.get(DatafileParams._matrix)
        if isinstance(mat,dict):
            labels,dataseries=zip(*[(k,list(v)) for k,v in mat.items()])
        else:
            dataseries=list(toIterable(obj.get(DatafileParams._matrix)))
            labels=obj.get(DatafileParams._labels) or list(map(str,range(1,len(dataseries)+1)))

        self.setData(dataseries,obj.get(DatafileParams._timesteps),labels)

    def setData(self,dataseries,timesteps,labels,timeMin=0,timeMax=0):
        #assert all(len(ds)==len(timesteps) for ds in dataseries),'%s != %s'%(dataseries[0],timesteps)
        if not isIterable(first(timesteps)):
            timesteps=[list(timesteps) for t in range(len(dataseries))]

        lens=[(len(ds),len(ts)) for ds,ts in zip(dataseries,timesteps)]
            
        if any(ds!=ts for ds,ts in lens):
            raise ValueError('Dataseries lengths do not match associated timesteps: %r != %r'%tuple(zip(*lens)))

        self.updatedData=True
        self.updatedTime=True
        self.dataseries=dataseries
        self.timesteps=timesteps

        self.labels=labels
        self.dataRange=minmax(matIter(self.dataseries)) if len(self.dataseries)>0 else (0,0)
        if timeMax==timeMin and isIterable(first(timesteps)) and len(self.timesteps[0])>0:
            self.timeMin,self.timeMax=minmax(matIter(self.timesteps))
        else:
            self.timeMax=timeMax
            self.timeMin=timeMin

    def getDataTable(self):
        return ['Timestep']+self.labels,self.timesteps,self.dataseries


class RegionPlotWidget(BasePlotWidget):
    def __init__(self,plugin,parent=None):
        BasePlotWidget.__init__(self,plugin,parent)
        self.setObjectName('Region Plot')
        self.plotarea=self.plot()
        self.hideAxis('left')
        self.hideAxis('bottom')
        self.setAspectLocked() # square aspect ratio
        self.setBackground(None) # transparent background

        # override how the graph is padded around the edges to remove most of the empty space
        setattr(self.getViewBox(),'suggestPadding',lambda axis:-0.05)

        self.regions=[] # stored QGraphicsEllipseItem objects for each region
        self.labels=[] # stored TextItem objects, should probably be 1 for every region
        self.timesteps=[] # timestep vector for the data
        self.matrix=[] # matrix of data, len(self.matrix)==len(self.timesteps)
        self.dataRange=(0,0) # range of values in self.matrix
        self.currentTime=0
        self.currentTimeIndex=0
        self.colormap=pg.ColorMap([0.0, 0.25, 0.5, 0.75, 1.0],[(0.0,0.0,1.0,1.0),(0.0,1.0,1.0,1.0),(0.0,1.0,0.0,1.0),(1.0,1.0,0.0,1.0),(1.0,0.0,0.0,1.0)])
        self.colorbar=ColorBar(self.colormap,10,10,20,200,5)

        self.scene().addItem(self.colorbar)

        if self.plugin:
            self.plugin.mgr.addEventHandler(EventType._widgetPreDraw,self.setCurrentTime)

    def paintEvent(self,e):
        self.colorbar.setParentHeight(self.height())
        BasePlotWidget.paintEvent(self,e)

    def parentClosed(self,e):
        self.plugin.mgr.removeEventHandler(self.setCurrentTime)

    def setCurrentTime(self,val=None):
        if val==None:
            val=self.plugin.mgr.timestep

        if len(self.timesteps)==0:
            return

        newtime=clamp(val,self.timesteps[0],self.timesteps[-1])
        if newtime!=self.currentTime:
            self.currentTime=newtime
            self.currentTimeIndex=min((abs(ts-self.currentTime),i) for i,ts in enumerate(self.timesteps))[1]
            self.setUpdated()

    def createRegion(self,x,y,rad,start,end,col):
        '''
        Create an ellipse centered at (x,y) with radius `rad' starting at radian angle `start' and ending at `end'
        with colour `col'. The center is defined as the center of the circle of which the ellipse is a slice. The
        ellipse is thus a full "pie slice" drawn over top of earlier defined slices.
        '''
        startd=math.degrees(start)*16
        endd=math.degrees(end)*16
        reg=QtWidgets.QGraphicsEllipseItem(x-rad,y-rad,rad*2,rad*2)
        reg.setStartAngle(-startd)
        reg.setSpanAngle(startd-endd)
        reg.setPen(pg.mkPen(0.5))
        reg.setBrush(pg.mkBrush(col))
        self.addItem(reg)
        self.regions.append(reg)

    def createLabel(self,x,y,rad,angle,text,color=0.0,font=QtGui.QFont("Arial",20)):
        '''Create a label centered at (x,y) and offset by the polar vector (rad,angle).'''
        label=pg.TextItem(text,anchor=(0.5,0.5),color=color)
        label.setPos(x+math.cos(-angle)*rad,y-math.sin(-angle)*rad)
        label.setFont(font)
        self.addItem(label)
        self.labels.append(label)

    def setRegionColor(self,reg,col):
        self.regions[reg].setBrush(pg.mkBrush(col))

    def setPlotObjectData(self,obj):
        self.matrix=obj.get(DatafileParams._matrix)
        self.timesteps=obj.get(DatafileParams._timesteps)
        self.dataRange=minmax(matIter(self.matrix))
        self.setTitle(obj.get(DatafileParams._title))
        self.colorbar.setValRange(*self.dataRange)

    def updateGraph(self):
        for i,data in enumerate(self.matrix[self.currentTimeIndex]):
            xi=clamp(eidolon.lerpXi(data,*self.dataRange),0.0,1.0)
            q=self.colormap.mapToQColor(xi)
            self.setRegionColor(i,q)


def AHAPlotWidget(plugin,parent=None):
    widg=RegionPlotWidget(plugin,parent)
    thirdpi=math.pi/3

    for i in range(6): # regions 1-6
        widg.createRegion(0,0,4,(i+1)*thirdpi,(i+2)*thirdpi,'w')
        widg.createLabel(0,0,3.5,(i+1.5)*thirdpi,str(i+1))

    for i in range(6): # regions 7-12
        widg.createRegion(0,0,3,(i+1)*thirdpi,(i+2)*thirdpi,'w')
        widg.createLabel(0,0,2.5,(i+1.5)*thirdpi,str(i+7))

    for i in range(4): # regions 13-16
        widg.createRegion(0,0,2,(i+0.5)*halfpi,(i+1.5)*halfpi,'w')
        widg.createLabel(0,0,1.5,(i+1)*halfpi,str(i+13))

    widg.createRegion(0,0,1,0,math.pi*2,'w') # region 17
    widg.createLabel(0,0,0,0,'17')


    return widg


def PoolRegionPlotWidget(plugin,parent=None):
    widg=RegionPlotWidget(plugin,parent)
    thirdpi=math.pi/3

    for i in range(6): # regions 1-6
        widg.createRegion(0,0,1,(i+1)*thirdpi,(i+2)*thirdpi,'w')
        widg.createLabel(0,0,0.5,(i+1.5)*thirdpi,str(i+1))

    return widg


class RegionGraphDockWidget(QtWidgets.QWidget,Ui_RegionGraphWidget):
    def __init__(self,plugin,numRegions,parent=None):
        QtWidgets.QWidget.__init__(self,parent)
        self.setupUi(self)

        self.plugin=plugin
        self.mgr=plugin.mgr
        self.region=None
        self.matrix=None
        self.timesteps=None
        self.currentTime=0
        self.numRegions=numRegions

        self.dataChecks=[]
        checkcols=9
        gridlayout=self.checkboxGroup.layout()
        for i in range(numRegions):
            check= QtWidgets.QCheckBox(self.checkboxGroup)
            check.setText(str(i+1))
            check.clicked.connect(self.updatePlot)
            self.dataChecks.append(check)
            gridlayout.addWidget(check, i/checkcols, i%checkcols, 1, 1)

        self.allcheck=QtWidgets.QCheckBox(self.checkboxGroup)
        self.allcheck.setText('All')
        self.allcheck.clicked.connect(self.selectAll)
        gridlayout.addWidget(self.allcheck, numRegions/checkcols, numRegions%checkcols, 1, 1)

        self.plot=TimePlotWidget(parent=self)
        self.plot.setObjectName('Region Graph')
        self.verticalLayout.addWidget(self.plot)

        self.setDataMatrix([list(range(numRegions))],[0])

        self.mgr.addEventHandler(EventType._widgetPreDraw,self._updateTime)

    def parentClosed(self,e):
        self.mgr.removeEventHandler(self._updateTime)

    def _updateTime(self):
        self.setTimestep(self.mgr.timestep)

    def setRegionWidget(self,region):
        self.region=region
        self.scrollAreaWidgetContents.layout().insertWidget(0,region)

    def setPlotObjectData(self,obj):
        self.setDataMatrix(obj.get(DatafileParams._matrix),obj.get(DatafileParams._timesteps))
        self.region.setPlotObjectData(obj)
#       self.region.isPercent=obj.get(DatafileParams._ispercent)

    def setDataMatrix(self,matrix,timesteps):
        assert len(matrix)==len(timesteps)
        assert all(len(d)==self.numRegions for d in matrix),'%i != %i'%(len(first(matrix)),self.numRegions)
        self.matrix=matrix
        self.timesteps=timesteps
        self._updateTime()

    def setTimestep(self,time):
        if time!=self.currentTime:
            self.currentTime=time
            if self.region:
                self.region.setCurrentTime(time)
            self.plot.setCurrentTime(time)
            self.updatePlot()

    def selectAll(self,isSelected=None):
        if isSelected==None:
            isSelected=self.allcheck.isChecked()

        with eidolon.signalBlocker(*([self.allcheck]+self.dataChecks)):
            self.allcheck.setChecked(isSelected)
            for check in self.dataChecks:
                check.setChecked(isSelected)

        self.updatePlot()

    def updatePlot(self):
        dataseries=[]
        labels=[]
        for i,check in enumerate(self.dataChecks):
            if check.isChecked():
                dataseries.append([a[i] for a in self.matrix])
                labels.append(str(i+1))

        self.plot.setData(dataseries,self.timesteps,labels)
        self.repaint()


def AHADockWidget(plugin,parent=None):
    widg=RegionGraphDockWidget(plugin,17,parent)
    widg.setRegionWidget(AHAPlotWidget(None,widg))
    return widg

def AHAPoolDockWidget(plugin,parent=None):
    widg=RegionGraphDockWidget(plugin,16,parent)
    widg.setRegionWidget(AHAPlotWidget(None,widg))
    return widg

def PoolDockWidget(plugin,parent=None):
    widg=RegionGraphDockWidget(plugin,6,parent)
    widg.setRegionWidget(PoolRegionPlotWidget(None,widg))
    return widg


class PlotSceneObject(SceneObject):
    def __init__(self,name,filename,datamap,plugin,**kwargs):
        SceneObject.__init__(self,name,plugin,**kwargs)
        self.filename=filename
        self.datamap=datamap
        self._updatePropTuples()

    def _updatePropTuples(self):
        self.proptuples=[('Filename',str(self.filename))]
        if self.datamap:
            self.proptuples+=sorted((k,str(v)) for k,v in self.datamap.items())

    def getPropTuples(self):
        return self.proptuples

    def getWidget(self):
        '''Get the docked widget for this plot, or None if the user hasn't created one.'''
        return self.plugin.getPlotObjectWidget(self)

    def getTimestepList(self):
        return self.datamap.get(DatafileParams._timesteps,[0])

    def get(self,name):
        return self.datamap.get(name,None)

    def set(self,name,value):
        result=self.datamap[name]=value
        self._updatePropTuples()
        return result

    def load(self):
        if self.filename:
            self.datamap=eidolon.readBasicConfig(self.filename)
            self._updatePropTuples()

    def save(self):
        if self.filename:
            eidolon.storeBasicConfig(self.filename,self.datamap)


class PlotPlugin(ScenePlugin):
    def __init__(self):
        ScenePlugin.__init__(self,'Plot')
        self.BasePlotWidget=BasePlotWidget
        self.SimpleGraphWidget=SimpleGraphWidget
        self.TimePlotWidget=TimePlotWidget
        self.RegionPlotWidget=RegionPlotWidget
        self.AHAPlotWidget=AHAPlotWidget
        self.AHAPoolDockWidget=AHAPoolDockWidget
        self.PoolRegionPlotWidget=PoolRegionPlotWidget
        self.AHADockWidget=AHADockWidget
        self.PoolDockWidget=PoolDockWidget
        self.dockmap={}

    def init(self,plugid,win,mgr):
        ScenePlugin.init(self,plugid,win,mgr)

        if win:
            win.addMenuItem('Import','PlotLoad'+str(plugid),'&Plot File',self._openFileDialog)

        # read command line argument, loading files as requested, note these tasks are queued at module load time
        if mgr.conf.hasValue('args','--plot'):
            @eidolon.taskroutine('Loading Plot File(s)')
            def _loadTask(filenames,task=None):
                for f in filenames:
                    obj=self.loadObject(f)
                    self.mgr.addSceneObject(obj)

            self.mgr.runTasks(_loadTask(mgr.conf.get('args','--plot').split(',')))

    def getIcon(self,obj):
        return eidolon.IconName.Bars

    def getMenu(self,obj):
        return [obj.getName(),'Show Plot'],self.objectMenuItem

    def acceptFile(self,filename):
        return splitPathExt(filename)[2].lower() == '.plot'

    def checkFileOverwrite(self,obj,dirpath,name=None):
        outfile=os.path.join(dirpath,name or obj.getName())+'.plot'
        if os.path.exists(outfile):
            return [outfile]
        else:
            return []

    def objectMenuItem(self,obj,item):
        if item=='Show Plot':
            self.mgr.addFuncTask(lambda:obj.createRepr(None))

    def renameObjFiles(self,obj,oldname,overwrite=False):
        assert isinstance(obj,SceneObject) and obj.plugin==self
        if os.path.isfile(obj.filename):
            obj.filename=eidolon.renameFile(obj.filename,obj.getName(),overwriteFile=overwrite)

    def getObjFiles(self,obj):
        return [obj.filename] if obj.filename else []

    def copyObjFiles(self,obj,sdir,overwrite=False):
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
        args={ 'varname':namemap[obj], 'objname':obj.name}

        if not configSection and isinstance(obj,PlotSceneObject):
            args['filename']=convertpath(obj.filename)
            script+='%(varname)s = Plot.loadObject(%(filename)s,%(objname)r)\n'

        return eidolon.setStrIndent(script % args).strip()+'\n'

    def createRepr(self,obj,reprtype,refine=0,**kwargs):
        self.createPlotObjectDock(obj)
        ts=obj.getTimestepList()
        if len(ts)>1 and not self.mgr.isTimeDialogShown():
            self.mgr.showTimeDialog(True,ts[0],ts[-1],ts[1]-ts[0])

    def createPlotObject(self,filename,name,title,matrix,timesteps,widgettype,srcobject=None,**kwargs):
        if not isinstance(widgettype,str):
            widgettype=widgettype.__name__

        if srcobject and not isinstance(srcobject,str):
            srcobject=srcobject.getName()

        name=name or splitPathExt(filename)[1]

        datamap={
            DatafileParams._name:name,
            DatafileParams._title:title,
            DatafileParams._matrix:matrix,
            DatafileParams._timesteps:timesteps,
            DatafileParams._widgettype:widgettype,
            DatafileParams._srcobject:srcobject or '',
            DatafileParams._istimed:len(timesteps)>1,
        }

        datamap.update(kwargs)

        return PlotSceneObject(name,filename,datamap,self)

    def plotSimpleGraph(self,title,values):
        '''
        Generate a simple line plot with title `title' and value list/tuple/dict `values'. If a list of values is
        provided, these are plotted on x-axis 0 to N for N values and given the name `title'. If a tuple is provided
        this should be (x-axis,y-axis) value lists which must have the same length. If a dict is provided this must
        map plot names to either list or tuple values as described.

        Example:
            p=Plot.plotSimpleGraph('X',{'x1':([0,1],[0,1]),'x2':([0,1],[1,0])})
        '''
        name=self.mgr.getUniqueObjName('plot')
        if not isinstance(values,dict):
            values={title:values}
        plot=self.createPlotObject(name,name,title,values,[],self.SimpleGraphWidget)
        self.mgr.addSceneObject(plot)
        plot.createRepr(None)
        return plot

    def plotMatrix(self,mat):
        '''
        Plot the RealMatrix `mat' as a graph with the first column containing plotted values. The metadata values
        "minx" and "maxx" are used to store integer start and end x-axis values applied as arguments to range() to
        produce the x-axis, if these are not present then range(mat.n()) is used instead.
        '''
        minx=mat.meta('minx')
        maxx=mat.meta('maxx')
        if minx and maxx:
            xvals=list(range(int(minx),int(maxx)))
            assert len(xvals)==mat.n()
        else:
            xvals=len(range(mat.n()))

        return self.plotSimpleGraph(mat.getName(),(xvals,eidolon.matrixToList(mat)))

    def createPlotObjectDock(self,obj,w=400,h=400):
        if self.win:
            widg=self.getPlotObjectWidget(obj)
            if not widg:
                constr=globals()[obj.get(DatafileParams._widgettype)]
                widg=self.mgr.createDockWidget(lambda:constr(self),obj.get(DatafileParams._title),w,h)
                self.dockmap[obj.getName()]=id(widg)

            widg.setPlotObjectData(obj)

    def getPlotObjectWidget(self,obj):
        return first(w for w in self.win.dockWidgets if id(w)==self.dockmap.get(obj.getName(),-1))

    def loadPlotObject(self,filename,name=None):
        '''Deprecated, for compatibility only.'''
        return self.loadObject(filename,name)

    def loadObject(self,filename,name=None,**kwargs):
        name=name or os.path.splitext(os.path.basename(filename))[0]
        obj=PlotSceneObject(name,filename,None,self)
        obj.load()
        return obj
    
    def plotImageMatrix(self,image,title='Image View',width=200,height=200,transpose=True):
        def createView():
            im=image
            if transpose:
                im=np.transpose(im,[-1]+list(range(im.ndim-1))) # move last dimension to first
                
            view=pg.ImageView()
            view.setImage(im,xvals=np.arange(im.shape[0]+1))
            return view
        
        return self.mgr.createDockWidget(createView,title,width,height)

    def _openFileDialog(self):
        filename=self.mgr.win.chooseFileDialog('Choose Plot filename',filterstr='Plot Files (*.plot)')
        if filename!='':
            self.mgr.addFuncTask(lambda:self.mgr.addSceneObject(self.loadObject(filename)),'Importing Plot File')


eidolon.addPlugin(PlotPlugin())
