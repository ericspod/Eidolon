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


'''This module represents almost all of the interface code for Eidolon, defining window classes and helper functions.'''

import sys
import threading
import traceback
import time
import os
import collections
import contextlib
import signal
import codeop
import textwrap
    
import sip

import eidolon
import eidolon.Utils as Utils
from eidolon.Utils import EventType, ParamType, ConfVars

from renderer import getRenderAdapter,RenderParamGroup,platformID

from ui import Qt, QtCore, QtGui, QtWidgets, QtVersion
from ui import Ui_MainWindow, Ui_ProjProp, Ui_ObjReprProp, Ui_ObjProp, Ui_matProp, Ui_LightProp, Ui_gpuProp,\
        Ui_Draw2DView, Ui_ScreenshotForm, Ui_ShowMsg #,loadGPUScript


globalApp=None # Global QApplication object, there must only be one of these
globalWin=None # Global VisualizerWindow instance, there should really only be one of these but that could be changed


CustomUIType=Utils.enum(
    ('label','Text Label'),
    ('int','Integer Spin Box'),
    ('real','Real Spin Box'),
    ('str','String box'),
    ('strlist','String List Combo Box'),
    ('checkbox','Checkbox'),
    ('button','Button'),
    ('hslider','Horizontal Slider'),
    ('radio','Radio Button'),
    doc='Types of UI elements that can be made using custom UI generation routines'
)

AssetType=Utils.enum(
    ('mat','Materials','3D Object Materials'),
    ('spec','Spectrums','Material Spectrums'),
    ('light','Lights','Scene Lights'),
    ('gpuprog','GPU Program','GPU Programs (Vertex/Fragment Shaders)'),
    ('tex','Textures','Texture Files'),
#   ('eqn','Equations','Python Equations'),
    doc='Types of scene assets (objects/concepts other than data) stored by the system and represented in the UI'
)

IconName=Utils.enum(
    ('Default',':/icons/document.png'),
    ('Mesh',':/icons/cube.png'),
    ('Image',':/icons/image.png'),
    ('Eye',':/icons/eye.png'),
    ('EyeClosed',':/icons/eye-disabled.png'),
    ('Bars',':/icons/stats-bars.png'),
    ('Help',':/icons/help-circled.png'),
    ('Scissors',':/icons/scissors.png'),
    ('Trash',':/icons/trash-a.png'),
    ('Seg',':/icons/seg.png'),
    ('Clipboard',':/icons/clipboard.png'),
    doc='Icon names for the UI, the names refer to resource paths in loaded Qt resource objects'
)


mainTitleString='%s v%s (FOR RESEARCH ONLY)'


def initUI(args=None):
    '''Initialize the UI framework.'''
    global globalApp

    if globalApp==None:
        globalApp = QtWidgets.QApplication(sys.argv if args==None else args)
        globalApp.setAttribute(Qt.AA_DontUseNativeMenuBar) # in OSX, forces menubar to be in window

    return globalApp


def getUIApp():
    return globalApp


def execUI(doExit=True):
    '''
    Run the event loop and wait until all windows are closed. If doExit is true then exit is called
    with the result, otherwise the result is returned by this function.
    '''
    global globalWin

    if globalWin:
        globalWin.isExec=True

    # ensure the keyboard interrupt signal causes a forced unclean exit
    if doExit:
        signal.signal(signal.SIGINT, signal.SIG_DFL)

    execval=globalApp.exec_()

    if doExit:
        sys.exit(execval)

    return execval


def createVizWin(conf,width,height):
    '''Create a visualization window and return it. This also initializes the global scene manager.'''
    global globalWin

    if not globalWin:
        globalWin=VisualizerWindow(conf,width,height)

    return globalWin


def getVizWin():
    '''get the visualization window after it has been created.'''
    return globalWin


def cppdel(obj):
    '''Delete the Qt object; this is sip specific so would have be changed to use PySide.'''
    if obj!=None:
        try:
            obj.deleteLater()
        except:
            try:
                sip.delete(obj)
            except:
                pass


def toQtColor(c):
    '''Converts an iterable object yielding color channel unit float values to a QColor.'''
    if isinstance(c,QtGui.QColor):
        return c
    else:
        c=list(c)
        c+=[1.0]*(4-len(c))
        return QtGui.QColor(c[0]*255, c[1]*255, c[2]*255,c[3]*255)


def traverseWidget(widg, func=lambda i:True):
    found=set([widg])
    widgstack=[widg]

    while widgstack:
        w=widgstack.pop()
        found.add(w)
        for d in dir(w):
            obj=getattr(w,d)
            try:
                if obj not in found and isinstance(obj,QtWidgets.QWidget) and func(obj):
                    widgstack.push(obj)
            except:
                pass


@contextlib.contextmanager
def signalBlocker(*objs):
    '''This context manager blocks signals going to the given argument objects within the scope of a 'with' code block.'''
    origvals=[o.blockSignals(True) for o in objs]
    yield # execute code in 'with' block
    for o,v in zip(objs,origvals):
        o.blockSignals(v)


def getWheelXY(qwheelevent):
    '''PyQt4/5 compatibility wrapper around the QWheelEvent wheel scroll angle, returns the (X,Y) scroll values.'''
    if QtVersion==4:
        #sign=-1 if qwheelevent.orientation()==Qt.Horizontal else 1
        #return qwheelevent.delta()*sign
        delta=qwheelevent.delta()
        if qwheelevent.orientation()==Qt.Horizontal:
            return delta,0
        else:
            return 0,delta
    else:
        delta=qwheelevent.angleDelta()
        return delta.x(),delta.y()
    

def getWheelDelta(qwheelevent):
    '''Returns a wheel scroll delta value combining the X and Y axes.'''
    x,y=getWheelXY(qwheelevent)
    return y or x*-1


def validQVariant(qvar):
    '''Returns True if the value `qvar' is a valid QVariant object in PyQt4 or if it is not None in PyQt5.'''
    if QtVersion==4:
        return qvar is not None and qvar.isValid()
    else:
        return qvar is not None
    

def validQVariantStr(qvar):
    '''
    In PyQt4 returns the string contents of the QVariant `qvar' if valid. In PyQt5 returns the string representation of
    `qvar' (which can be anything) or empty string if it is None.
    '''
    if QtVersion==4 and validQVariant(qvar):
        return qvar.toString()
    elif QtVersion==5 and qvar is not None:
        return str(qvar)
    else:
        return ''
    

def selectBoxIndex(val,box):
    '''Set the current index in `box' to be the first item whose text is `val', returning True if this was done.'''
    with signalBlocker(box):
        for i in range(box.count()):
            if str(box.itemText(i))==val:
                box.setCurrentIndex(i)
                return True

    return False


def setCollapsibleGroupbox(box,isVisible=True):
    '''
    Transforms the QGroupBox `box' into a collapsible one, which will have a check box that collapses its contents if
    unchecked. The box will be initially collapsed if `isVisible' is False.
    '''
    w=QtWidgets.QWidget()
    w.setLayout(box.layout())
    w.setContentsMargins(0,0,0,0)
    w.setStyleSheet('.QWidget{background-color:0x00000000;}')
    box.setStyleSheet('.QGroupBox::title { padding-left:-1px; }')
    layout = QtWidgets.QVBoxLayout(box)
    layout.addWidget(w)
    layout.setContentsMargins(0,0,0,0)
    box.setCheckable(True)
    box.setChecked(isVisible)
    w.setVisible(isVisible)
    box.clicked.connect(w.setVisible)


def setWarningStylesheet(widg):
    '''Set the stylesheet for `widg' to show a black+yellow striped background indicating advanced/dangerous features.'''
    sheet='''QGroupBox{
border: 2px solid black;
background-color: qlineargradient(spread:reflect, x1:0, y1:0, x2:0.037, y2:0.006, stop:0.475271 rgba(50, 50, 50, 255), stop:0.497948 rgba(150, 150, 0, 255));
}
QGroupBox::indicator { background-color:rgba(0,0,0,150.0); border:0;}
QGroupBox::title { background-color:rgba(0,0,0,150.0); }
QLabel { background-color:rgba(0,0,0,150.0); padding:1px;}'''
    widg.setStyleSheet(sheet)


def centerWindow(wind):
    '''Centers the window `wind' on the desktop by moving it only.'''
    geom = wind.geometry()
    geom.moveCenter(QtWidgets.QDesktopWidget().availableGeometry().center())
    wind.move(geom.topLeft())


def resizeScreenRelative(wind,w,h):
    geom = wind.geometry()
    desk=QtWidgets.QDesktopWidget().availableGeometry()
    nw=geom.width()
    nh=geom.height()

    if nw>desk.width():
        nw=int(desk.width()*w)

    if nh>desk.height():
        nh=int(desk.height()*h)

    wind.resize(nw,nh)


def screenshotWidget(w,filename):
    '''Save a screenshot of the widget `w' to the file `filename'.'''
    p=QtGui.QPixmap.grabWidget(w)
    p.save(filename)


def setChecked(isChecked,checkbox):
    '''Set the checkable widget `checkbox' to the boolean status `isChecked'.'''
    with signalBlocker(checkbox):
        checkbox.setChecked(isChecked)


def setColorButton(col,button):
    '''Set the colour of left hand border of `button' to color object `col'.'''
    button.setStyleSheet('border-left: 5px solid ' + str(toQtColor(col).name()))


def setSpinBox(box,minval=None,maxval=None,stepval=None,decimals=None):
    with signalBlocker(box):
        if minval!=None:
            box.setMinimum(minval)
        if maxval!=None:
            box.setMaximum(maxval)
        if decimals!=None:
            box.setDecimals(decimals)
        if stepval!=None:
            box.setSingleStep(stepval)


def currentIndexDataStr(obj):
    '''Returns the string form of the QVariant object at the current index in `obj', or the current text if that isn't valid.'''
    qvar=obj.itemData(obj.currentIndex())
    vstr=validQVariantStr(qvar)
    return str(vstr or obj.currentText())


def fillEnumTable(vals,table,numsSelectable=False):
    fillTable([(str(i+1),j) for i,j in enumerate(vals)],table)

    if not numsSelectable: # remove the selectable flag for each number item
        with signalBlocker(table):
            for n in range(table.rowCount()):
                item=table.item(n,0)
                item.setFlags(item.flags() & ~Qt.ItemIsSelectable)


def setTableHeaders(table):
    # NOTE: the critical property the table must have is the cascading resize settings must be set to true for both dimensions
    # The designer properties for these are horizontalHeaderCascadingSectionResizes and verticalHeaderCascadingSectionResizes
    table.verticalHeader().setCascadingSectionResizes(True)
    table.horizontalHeader().setCascadingSectionResizes(True)
    table.verticalHeader().setDefaultAlignment(Qt.AlignLeft) # why doesn't this stick in the designer?
    table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)
    table.horizontalHeader().setStretchLastSection(True)


def fillTable(vals,table):
    with signalBlocker(table):
        if table.rowCount()!=len(vals):
            table.clearContents()
            table.setRowCount(len(vals))
            table.setColumnCount(2)
            table.verticalHeader().setVisible(False)

        for i,(n,v) in enumerate(vals):
            item=QtWidgets.QTableWidgetItem(n)
            item.setFlags((item.flags() & ~Qt.ItemIsEditable)|Qt.ItemIsSelectable)
            table.setItem(i,0,item)
            item=QtWidgets.QTableWidgetItem(v)
            item.setFlags((item.flags() & ~Qt.ItemIsEditable)|Qt.ItemIsSelectable)
            table.setItem(i,1,item)

        table.resizeColumnToContents(0)
        table.resizeRowsToContents()

        setTableHeaders(table)


def fillList(listobj,items,curitem=-1,defaultitem=None,checkChanges=False):
    '''
    Fills the object `listobj' with the list `items'. The object `listobj' must be a QComboBox or QListWidget. Values
    in `items' may be single strings or (item,value) string pairs; when adding each item to a QComboBox, the string is
    used as the `userData' value in addItem in the first case but the given value part of the pair in the second case.
    If `curitem' is left as -1, the QComboBox object's current item will not be changed if it's present in the new list
    of items. If `curitem' is a string then the current index for either object type is set to select that member of the
    list, if a valid index value then that index is instead selected, otherwise no item is selected. if `defaultitem'
    is a non-empty string, this is added as the first member of the list. If `checkChanges' is True, the contents of
    `listobj' are compared to `items' and is only refilled if they differ; the expense of this operation versus refilling
    the list are up to the caller to determine.
    '''
    assert isinstance(listobj,(QtWidgets.QComboBox,QtWidgets.QListWidget))

    # define simple interface functions for interacting with `listobj'
    if isinstance(listobj,QtWidgets.QComboBox):
        getItem=lambda i: (str(listobj.itemText(i)),listobj.itemData(i))
        addItem=listobj.addItem
        setCurrentIndex=listobj.setCurrentIndex
        if curitem==-1:
            curitem=str(listobj.currentText())
    else:
        getItem=lambda i:(str(listobj.item(i).text()),)*2
        addItem=lambda i,v: listobj.addItem(i)
        setCurrentIndex=listobj.setCurrentRow #lambda i:listobj.setCurrentIndex(listobj.model().index(i,0))

    newitems=[(str(defaultitem),defaultitem)] if defaultitem!=None else [] # start the list with the default item if given

    # construct the list of (item,value) pairs from `items', if each entry i is a pair then i is stored, otherwise (i,i) is stored
    for item in items:
        if isinstance(item,str): # treat strings specially to avoid splitting up 2-character strings
            item,value=item,item
        else:
            try:
                item,value=item # attempt to split item
            except:
                item,value=item,item # otherwise just pair item with itself

        newitems.append((str(item),value))

    # if not checking for changes or the lists of values differ in contents, refill `listobj'
    if not checkChanges or listobj.count()!=len(newitems) or any(getItem(i)!=v for i,v in enumerate(newitems)):
        with signalBlocker(listobj):
            listobj.clear()
            for i,(item,value) in enumerate(newitems):
                addItem(item,value)
                
                if curitem!=-1 and (item==curitem or i==curitem):
                    setCurrentIndex(i)


def createSplitWidget(parent,widg1,widg2,isVertical=True):
    '''Create a splitter widget within `parent' with `widg1' and `widg2' as its two halves, vertical if `isVertical.'''
    split=QtWidgets.QSplitter(parent)
    split.setOrientation(Qt.Vertical if isVertical else Qt.Horizontal)
    split.setChildrenCollapsible(False)
    widg1.setParent(split)
    widg2.setParent(split)
    return split


def createMenu(title,values,defaultFunc=lambda v:None,parent=None):
    '''
    Construct a menu widget from the given values. The list `values' must contain strings, pairs containing strings
    and a callback function, '---' for a separator, or further lists thereof. When a item is selected, the given callback
    function is called with the string passed as an argument, if only a string is given then `defaultFunc' is called
    instead with that string as argument.
    '''
    menu=QtWidgets.QMenu(parent)
    if title:
        #menu.setTitle(title)
        menu.addAction(title,lambda:None)
        menu.addSeparator()

    def _callFunc(v,func): # needed to ensure v and func are fresh
        return lambda:func(v)

    for val in values:
        if val=='---':
            menu.addSeparator()
        elif isinstance(val,list):
            menu.addMenu(createMenu('',val,defaultFunc,menu))
        else:
            if isinstance(val,str):
                func=defaultFunc
            else:
                assert isinstance(val,tuple) and len(val)==2
                val,func=val

            menu.addAction(val,_callFunc(val,func))

    return menu


def mapWidgetValues(widget):
    results={}

    for d in dir(widget):
        at=getattr(widget,d)
        if isinstance(at,(QtWidgets.QCheckBox,QtWidgets.QRadioButton)):
            results[d]=at.isChecked()
        elif isinstance(at,(QtWidgets.QSpinBox,QtWidgets.QDoubleSpinBox)):
            results[d]=at.value()
        elif isinstance(at,QtWidgets.QComboBox):
            results[d]=(at.currentIndex(),str(at.currentText()))
        elif isinstance(at,QtWidgets.QLineEdit):
            results[d]=str(at.text())

    return results


def setWidgetValues(widget,vals):
    for k,v in vals.items():
        at=getattr(widget,k,None)
        if at:
            with signalBlocker(at):
                if isinstance(at,(QtWidgets.QCheckBox,QtWidgets.QRadioButton)):
                    at.setChecked(v)
                elif isinstance(at,(QtWidgets.QSpinBox,QtWidgets.QDoubleSpinBox)):
                    at.setValue(v)
                elif isinstance(at,QtWidgets.QComboBox):
                    at.setCurrentIndex(v)
                elif isinstance(at,QtWidgets.QLineEdit):
                    at.setText(v)


def addCustomUIRow(layout,index,uitype,name,labelText,minval=0,maxval=0,stepval=1,decimals=6):
    assert uitype in CustomUIType

    usesLabel=True

    if uitype==CustomUIType._label:
        opt= QtWidgets.QLabel()
        opt.setText(labelText)
        usesLabel=False
    elif uitype==CustomUIType._int:
        opt=QtWidgets.QSpinBox()
        setSpinBox(opt,minval,maxval,stepval)
    elif uitype==CustomUIType._real:
        opt=QtWidgets.QDoubleSpinBox()
        setSpinBox(opt,minval,maxval,stepval,decimals)
    elif uitype==CustomUIType._str:
        opt=QtWidgets.QLineEdit()
    elif uitype==CustomUIType._strlist:
        opt=QtWidgets.QComboBox()
    elif uitype==CustomUIType._checkbox:
        opt=QtWidgets.QCheckBox()
        opt.setText(labelText)
        usesLabel=False
    elif uitype==CustomUIType._button:
        opt=QtWidgets.QPushButton()
        opt.setText(labelText)
        usesLabel=False
    elif uitype==CustomUIType._hslider:
        opt=QtWidgets.QSlider(Qt.Horizontal)
        opt.setRange(int(minval),int(maxval))
        opt.setSingleStep(int(stepval))
        opt.setTickPosition(QtWidgets.QSlider.TicksBelow)
    elif uitype==CustomUIType._radio:
        opt=QtWidgets.QRadioButton()
        opt.setText(labelText)
        usesLabel=False

    if usesLabel:
        label= QtWidgets.QLabel()
        label.setText(labelText)
    else:
        label=None

    if isinstance(layout,QtWidgets.QFormLayout):
        layout.insertRow(index,label,opt)
    elif isinstance(layout,QtWidgets.QGridLayout):
        if not usesLabel:
            layout.addWidget(opt,index,0,1,1)
        else:
            form=QtWidgets.QFormLayout()
            form.insertRow(0,label,opt)
            form.setAlignment(Qt.AlignLeft)
            layout.addLayout(form,index,0,1,1)
    elif not usesLabel:
        layout.insertWidget(index,opt)
    else:
        form=QtWidgets.QFormLayout()
        form.insertRow(0,label,opt)
        form.setAlignment(Qt.AlignLeft)
        layout.insertLayout(index,form)

    return label,opt


class ParamPanel(QtWidgets.QWidget):
    '''
    This widget generates custom UI forms from a list of ParamDef objects. This can be used to create custom and dynamic
    parameter input UI elements, for example choosing representation object parameters.
    '''
    def __init__(self,params,parent=None):
        QtWidgets.QWidget.__init__(self,parent)
        self.layout=QtWidgets.QFormLayout(self)
        self.layout.setContentsMargins(0,0,0,0)
        self.params=list(params)
        self.uimap={}
        self.isFirstUpdate=True

        index=0
        for p in self.params:
            index+=self.addParamUI(p,index)

    def addParamUI(self,param,index):
        '''Add a UI element for the ParamDef `param' to the form at position `index'.'''
        pt=param.ptype
        name=param.name
        desc=param.desc

        if pt==ParamType._int:
            minv=0 if param.minv==None else param.minv
            maxv=99 if param.maxv==None else param.maxv
            step=1 if param.step==None else param.step
            label,ui=addCustomUIRow(self.layout,index,CustomUIType._int,name,desc,minv,maxv,step)
            if param.default!=None:
                ui.setValue(param.default)

        elif pt==ParamType._real:
            minv=0.0 if param.minv==None else param.minv
            maxv=99.0 if param.maxv==None else param.maxv
            step=1.0 if param.step==None else param.step
            label,ui=addCustomUIRow(self.layout,index,CustomUIType._real,name,desc,minv,maxv,step)
            if param.default!=None:
                ui.setValue(param.default)

        elif pt==ParamType._bool:
            label,ui=addCustomUIRow(self.layout,index,CustomUIType._checkbox,name,desc)
            ui.setChecked(param.default==True)

        elif pt==ParamType._vec3:
            minv=(0.0,0.0,0.0) if param.minv==None else param.minv
            maxv=(99.0,99.0,99.0) if param.maxv==None else param.maxv
            step=(1.0,1.0,1.0) if param.step==None else param.step

            _,label=addCustomUIRow(self.layout,index,CustomUIType._label,name,desc)
            label,x=addCustomUIRow(self.layout,index+1,CustomUIType._real,name+'_x','X',minv[0],maxv[0],step[0])
            label,y=addCustomUIRow(self.layout,index+2,CustomUIType._real,name+'_y','Y',minv[1],maxv[1],step[1])
            label,z=addCustomUIRow(self.layout,index+3,CustomUIType._real,name+'_z','Z',minv[2],maxv[2],step[2])
            ui=(x,y,z)
            if param.default!=None:
                x.setValue(param.default[0])
                y.setValue(param.default[1])
                z.setValue(param.default[2])

        elif pt==ParamType._str:
            label,ui=addCustomUIRow(self.layout,index,CustomUIType._str,name,desc)
            if param.default!=None:
                ui.setText(str(param.default))

        elif pt in (ParamType._strlist,ParamType._field,ParamType._valuefunc,ParamType._vecfunc,ParamType._unitfunc):
            label,ui=addCustomUIRow(self.layout,index,CustomUIType._strlist,name,desc)
            if Utils.isIterable(param.default):
                fillList(ui,param.default,None,None if param.notNone else 'None')

        self.uimap[param]=ui
        return 4 if pt==ParamType._vec3 else 1

    def setParamChangeFunc(self,basefunc):
        def func(name,value):
            '''Converts QString values (in PyQt4) to normal strings before calling `basefunc'.'''
            if QtVersion==4 and isinstance(value,QtCore.QString):
                value=str(value)

            basefunc(name,value)

        def _disconnect(signal):
            try:
                signal.disconnect()
            except:
                pass

        def _connect(pt,name,ui):
            '''For the UI element `ui' with name `name' and ParamType `pt', associate its change signal with func.'''
            if pt==ParamType._vec3:
                x,y,z=ui
                vecfunc=lambda:func(name,(x.value(),y.value(),z.value()))

                _disconnect(x.valueChanged)
                _disconnect(y.valueChanged)
                _disconnect(z.valueChanged)
                x.valueChanged.connect(vecfunc)
                y.valueChanged.connect(vecfunc)
                z.valueChanged.connect(vecfunc)
            if pt in (ParamType._int,ParamType._real):
                _disconnect(ui.valueChanged)
                ui.valueChanged.connect(lambda:func(name,ui.value()))
            elif pt==ParamType._bool:
                _disconnect(ui.toggled)
                ui.toggled.connect(lambda i:func(name,i))
            elif pt in (ParamType._strlist,ParamType._field,ParamType._valuefunc,ParamType._vecfunc,ParamType._unitfunc):
                _disconnect(ui.currentIndexChanged)
                ui.currentIndexChanged.connect(lambda i:func(name,ui.currentText()))

        for param,ui in self.uimap.items():
            _connect(param.ptype,param.name,ui) # need to do this to ensure fresh variable names are created

    def hasParam(self,name):
        return any(p.name==name for p in self.params)

    def getParamUI(self,name):
        param=Utils.first(p for p in self.params if p.name==name)
        if param:
            return self.uimap[param]

    def fillStrList(self,strlist,ptype,defaultitem=None):
        assert ptype in (ParamType._field,ParamType._valuefunc,ParamType._vecfunc,ParamType._unitfunc)

        for param,ui in self.uimap.items():
            if param.ptype==ptype:
                fillList(ui,strlist,str(ui.currentText()),None if param.notNone else defaultitem)

    def setParam(self,name,val):
        param=Utils.first(p for p in self.params if p.name==name)
        if param:
            pt=param.ptype
            assert pt in (ParamType._int,ParamType._real,ParamType._vec3, ParamType._bool)

            if pt==ParamType._vec3:
                x,y,z=self.uimap[param]
                with signalBlocker(x,y,z):
                    x.setValue(val[0])
                    y.setValue(val[1])
                    z.setValue(val[2])
            else:
                ui=self.uimap[param]
                with signalBlocker(ui):
                    if pt in (ParamType._int,ParamType._real):
                        ui.setValue(val)
                    else:
                        ui.setChecked(val==True)

    def _paramValue(self,param):
        pt=param.ptype
        ui=self.uimap[param]

        if pt==ParamType._vec3:
            x,y,z=ui
            return x.value(),y.value(),z.value()
        elif pt in (ParamType._int,ParamType._real):
            return ui.value()
        elif pt==ParamType._bool:
            return ui.isChecked()
        elif pt==ParamType._str:
            return str(ui.text())
        elif pt in (ParamType._strlist,ParamType._field,ParamType._valuefunc,ParamType._unitfunc,ParamType._vecfunc):
            if ui.count()==0:
                return None

            result=currentIndexDataStr(ui)
            if result=='None':
                return None

            return result

    def getParam(self,name):
        param=Utils.first(p for p in self.params if p.name==name)
        if param:
            return self._paramValue(param)

    def getParamMap(self):
        return dict((p.name,self._paramValue(p)) for p in self.params)


def signalmethod(meth):
    '''Method decorator for turning a method into a signal proxy. This causes the method to become asynchronous.'''
    def signalproxy(self,*args,**kwargs):
        self.method_signal.emit(meth.__name__,args,kwargs)

    return 'signalproxy',meth,signalproxy


def signalclass(cls):
    '''
    Class decorator for implementing the method signal proxy interface. It collects all the methods annotated with @signalmethod
    and stores them in a map keyed to their names, and sets the member to the proxy method which sends the corresponding signal.
    Whenever a signal with the name of the method is received, the original method annotated with @signalmethod is called.
    For example, a method 'foo' with the annotation will be replaces with a proxy emiting a signal with the name 'foo' to the
    self.method_signal member, which is connected to a method that will extract 'foo' from self.method_signalmap and call it.
    The purpose of this is to cause methods of UI classes to be executed within the main UI thread when called from other threads.
    The caller does not block waiting for a result from the call.
    '''
    funclist={}

    # iterate over every member of the class, those which are tuples containing the string 'signalproxy' and two methods were created
    # by the method decorator, unpack those and set the member to the generated proxy method and store the original in funclist.
    for name,val in cls.__dict__.items():
        if isinstance(val,tuple) and len(val)==3 and val[0]=='signalproxy':
            setattr(cls,name,val[2]) # set the member to be the proxy method
            funclist[name]=val[1] # store the original method in the dict keyed to the name

    # override __init__ to initialize the method map object used to associate method names with method objects
    old__init__=cls.__init__
    def new__init__(self,*args,**kwargs):
        old__init__(self,*args,**kwargs)
        self.method_signalmap=funclist # dict of original methods keyed to their names
        self.method_signal.connect(self.methodslot) # the one and only slot which invokes the original methods when called

    # provide a slot which invokes the stored method when called
    def methodslot(self,name,args,kwargs):
        self.method_signalmap[str(name)](self,*args,**kwargs)

    setattr(cls,'__init__',new__init__)
    setattr(cls,'methodslot',methodslot)

    return cls


class LogFileView(QtWidgets.QWidget):
    def __init__(self,filename,win,dimensions=(800,800)):
        QtWidgets.QWidget.__init__(self,None)

        self.setWindowTitle('Log File View')
        self.setAttribute(Qt.WA_QuitOnClose,False) # don't wait for this window to close when exiting the application

        self.filename=filename
        self.win=win
        self.readtime=0
        self.readsize=0

        self.gridLayout = QtWidgets.QGridLayout(self)
        self.logEdit = QtWidgets.QPlainTextEdit(self)
        self.logEdit.setReadOnly(True)
        self.gridLayout.addWidget(self.logEdit, 0, 0, 1, 1)

        # set window size and center on screen
        self.resize(*dimensions)
        centerWindow(self)

        self.updateThread=threading.Thread(target=self._readLogText)
        self.updateThread.daemon=True
        self.updateThread.start()

    def keyPressEvent(self,e):
        if e.key() == Qt.Key_Escape:
            self.close()
        else:
            QtWidgets.QWidget.keyPressEvent(self,e)

    def _setText(self,text):
        def setTextWin():
            self.logEdit.setPlainText(text)
            cursor=self.logEdit.textCursor()
            cursor.setPosition(len(text))
            self.logEdit.setTextCursor(cursor)
            self.logEdit.ensureCursorVisible()

        self.win.callFuncUIThread(setTextWin)

    def _readLogText(self):
        while True:
            try:
                size=os.path.getsize(self.filename)
                if os.path.getmtime(self.filename)>self.readtime or size>self.readsize:
                    self.readtime=time.time()
                    self.readsize=size

                    with open(self.filename) as o:
                        self._setText(o.read().strip())
            except Exception as e:
                self._setText("Cannot read log file '%s':\n%s" % (self.filename,str(e)))

            time.sleep(1)


class TextBoxDialog(QtWidgets.QDialog):
    def __init__(self,title,msg,text,parent,width=600,height=300):
        QtWidgets.QDialog.__init__(self,parent)
        self.setWindowTitle(title)
        self.resize(width, height)
        centerWindow(self)

        self.msgLabel = QtWidgets.QLabel(self)
        self.msgLabel.setWordWrap(True)
        self.msgLabel.setText(msg)

        self.textEdit = QtWidgets.QPlainTextEdit(self)
        self.textEdit.setReadOnly(True)
        self.textEdit.setPlainText(text)

        self.buttonBox = QtWidgets.QDialogButtonBox(self)
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Ok)

        self.verticalLayout = QtWidgets.QVBoxLayout(self)
        self.verticalLayout.addWidget(self.msgLabel)
        self.verticalLayout.addWidget(self.textEdit)
        self.verticalLayout.addWidget(self.buttonBox)

        self.buttonBox.accepted.connect(self.close)


class ShowMessageDialog(QtWidgets.QDialog,Ui_ShowMsg):
    def __init__(self,parent):
        QtWidgets.QDialog.__init__(self,parent)
        self.setupUi(self)
        self.msgs=[]
        self.curMsg=0
        centerWindow(self)
        self.textEdit.setReadOnly(True)
        self.setVisible(False)

        self.closeButton.clicked.connect(lambda:self.setVisible(False))
        self.prevButton.clicked.connect(lambda:self.setMsg(self.curMsg-1))
        self.nextButton.clicked.connect(lambda:self.setMsg(self.curMsg+1))

    def addMsg(self,title,msg,text,width=0,height=0):
        item=(title,msg,text)
        if not self.isVisible() or not self.msgs or item!=self.msgs[-1]:
            self.msgs.append(item)
            self.setMsg(len(self.msgs)-1)

            if width and height and (width,height)!=(self.width(),self.height()):
                self.resize(width,height)
                centerWindow(self)

    def setMsg(self,index):
        self.curMsg=Utils.clamp(index,0,len(self.msgs)-1)
        self.countLabel.setText('Message %i / %i'%(self.curMsg+1,len(self.msgs)))
        title,msg,text=self.msgs[self.curMsg]
        self.setWindowTitle(title)
        self.msgLabel.setText(msg)
        self.textEdit.setPlainText(text)
        self.setVisible(True)


class ObjectPropertyWidget(QtWidgets.QWidget,Ui_ObjProp):
    def __init__(self,parent=None):
        QtWidgets.QWidget.__init__(self,parent)
        self.setupUi(self)
        setCollapsibleGroupbox(self.propertiesBox,False)

    def addReprOption(self,name,labelText,uitype,minval=0,maxval=0,stepval=1,decimals=6):
        layout=self.createReprBox.layout()
        rows=layout.count()

        label,opt=addCustomUIRow(layout,rows-2,uitype,name,labelText,minval,maxval,stepval,decimals)

        setattr(self,name+'_label',label)
        setattr(self,name,opt)

        return label,opt

    def getParamPanel(self):
        if self.paramLayout.count()>0:
            return self.paramLayout.itemAt(0).widget()
        return None

    def setParamPanel(self,panel):
        oldpanel=self.getParamPanel()
        if oldpanel and oldpanel!=panel:
            self.paramLayout.removeWidget(oldpanel)
            oldpanel.setParent(None)

        if panel:
            self.paramLayout.addWidget(panel)


class ObjectReprPropertyWidget(QtWidgets.QWidget,Ui_ObjReprProp):
    def __init__(self,parent=None):
        QtWidgets.QWidget.__init__(self,parent)
        self.setupUi(self)
        setCollapsibleGroupbox(self.propertiesBox,False)

        self.yaw.valueChanged.connect(self._clampRotation)
        self.pitch.valueChanged.connect(self._clampRotation)
        self.roll.valueChanged.connect(self._clampRotation)
        self.paramPanel=None

    def addProperty(self,name,labelText,uitype,minval=0,maxval=0,stepval=1,decimals=6):
        layout=self.propertyLayout.layout()
        rows=layout.count()

        label,opt=addCustomUIRow(layout,rows-(1 if self.paramPanel else 0),uitype,name,labelText,minval,maxval,stepval,decimals)

        setattr(self,name+'_label',label)
        setattr(self,name,opt)

        return label,opt

    def setParamPanel(self,panel):
        self.paramPanel=panel
        self.propertyLayout.layout().addWidget(panel)

    def addMaterialOption(self,name,labelText,uitype,minval=0,maxval=0,stepval=1,decimals=6):
        layout=self.materialBox.layout()
        rows=layout.rowCount()

        label,opt=addCustomUIRow(layout,rows-1,uitype,name,labelText,minval,maxval,stepval,decimals)

        setattr(self,name+'_label',label)
        setattr(self,name,opt)

        return label,opt

    def getPosition(self):
        return (self.transx.value(),self.transy.value(),self.transz.value())

    def getScale(self):
        return (self.scalex.value(),self.scaley.value(),self.scalez.value())

    def getRotation(self):
        return (self.yaw.value(),self.pitch.value(),self.roll.value())

    def setPosition(self,x,y,z):
        with signalBlocker(self.transx,self.transy,self.transz):
            self.transx.setValue(x)
            self.transy.setValue(y)
            self.transz.setValue(z)

    def setScale(self,x,y,z):
        with signalBlocker(self.scalex,self.scaley,self.scalez):
            self.scalex.setValue(x)
            self.scaley.setValue(y)
            self.scalez.setValue(z)

    def setRotation(self,yaw,pitch,roll):
        with signalBlocker(self.yaw,self.pitch,self.roll):
            self.yaw.setValue(yaw)
            self.pitch.setValue(pitch)
            self.roll.setValue(roll)

    def _clampRotation(self):
        with signalBlocker(self.yaw,self.pitch,self.roll):
            self.yaw.setValue(Utils.radCircularConvert(self.yaw.value()))
            self.pitch.setValue(Utils.radCircularConvert(self.pitch.value()))
            self.roll.setValue(Utils.radCircularConvert(self.roll.value()))


class ProjectPropertyWidget(QtWidgets.QWidget,Ui_ProjProp):
    def __init__(self,parent=None):
        QtWidgets.QWidget.__init__(self,parent)
        self.setupUi(self)


class MaterialPropertyWidget(QtWidgets.QWidget,Ui_matProp):
    def __init__(self,parent=None):
        QtWidgets.QWidget.__init__(self,parent)
        self.setupUi(self)
        self.geomBox.setVisible(False)
        self.geomList.setVisible(False)

    def setPointRelativeChecked(self,val):
        with signalBlocker(self.relativeRadio,self.absoluteRadio):
            self.relativeRadio.setChecked(val)

    def fillTextureList(self,textures,curtex):
        fillList(self.textureList,textures,curtex,'None')

    def fillFragmentList(self,fragments,curfrag):
        fillList(self.fragList,fragments,curfrag,'None')

    def fillVertexList(self,vertexs,curvert):
        fillList(self.vertList,vertexs,curvert,'None')

    def fillGeomList(self,geoms,curgeom):
        fillList(self.geomList,geoms,curgeom,'None')


class LightPropertyWidget(QtWidgets.QWidget,Ui_LightProp):
    def __init__(self,parent=None):
        QtWidgets.QWidget.__init__(self,parent)
        self.setupUi(self)

    def getPosition(self):
        return self.posx.value(),self.posy.value(),self.posz.value()

    def getDirection(self):
        return self.dirx.value(),self.diry.value(),self.dirz.value()


class GPUProgramPropertyWidget(QtWidgets.QWidget,Ui_gpuProp):
    def __init__(self,parent=None):
        QtWidgets.QWidget.__init__(self,parent)
        self.setupUi(self)
        self.srcEdit.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)

    def setSourceCode(self,src,force=False):
        if self.srcEdit.toPlainText()=='' or force:
            self.srcEdit.setPlainText(src)

    def getSourceCode(self):
        return self.srcEdit.toPlainText()

    def setSrcStatus(self,isCorrect):
        palette = QtGui.QPalette(self.setSrcButton.palette()) # make a copy of the palette
        palette.setColor(QtGui.QPalette.ButtonText, QtGui.QColor('black' if isCorrect else 'red'))
        self.setSrcButton.setText('Set Source'+('' if isCorrect else ' (ERROR: see log file)'))
        self.setSrcButton.setPalette(palette)


class Base2DWidget(QtWidgets.QWidget):
    '''
    Defines the base class for 2D views, handling the redraw cycle and mouse and key input callback methods. The method
    modifyDrawWidget() modifies its argument widget by replacing the paintEvent, wheelEvent, and mouse*Event, and
    key*Event methods. The new paintEvent() method first calls updateView(), creates a QImage to cover the screen, calls
    fillImage() with that QImage object as the argument, and then draws the QImage to screen. The update cycle expects
    updateView() to setup scene and UI values then fillImage() draws whatever's necessary to the QImage object. This
    class therefore represents the boundary between the UI and 2D rendering subsystems. The methods of this class
    except modifyDrawWidget(), getDrawDims(), and getBoxFitScale() must be overridden to implement behaviour.
    '''
    def __init__(self,parent=None):
        QtWidgets.QWidget.__init__(self,parent)
        self.setFocusPolicy(Qt.StrongFocus)
        self.imgFormat=QtGui.QImage.Format_RGB32
        self.img=None
        self.prevX=0
        self.prevY=0

    def modifyDrawWidget(self,drawWidget):
        '''
        Modify the given object (assumed to be the widget the 2D view is drawn in) to send its events to the parent
        and repaint itself using an internal image object.
        '''
        def _paintWidget(e):
            self.updateView()
            w,h=self.getDrawDims()
            with QtGui.QPainter(drawWidget) as p:
                if self.img==None or (self.img.width(),self.img.height(),self.img.format())!=(w,h,self.imgFormat):
                    self.img=QtGui.QImage(w,h,self.imgFormat)

                self.fillImage(self.img)
                p.drawImage(0,0,self.img)

        def _mousePress(e):
            self.prevX=e.x()
            self.prevY=e.y()
            self.mousePress(e)

        def _mouseMove(e):
            self.mouseDrag(e,e.x()-self.prevX,e.y()-self.prevY)
            self.prevX=e.x()
            self.prevY=e.y()

        setattr(drawWidget,'paintEvent',_paintWidget)
        setattr(drawWidget,'mousePressEvent',_mousePress)
        setattr(drawWidget,'mouseMoveEvent',_mouseMove)
        setattr(drawWidget,'mouseReleaseEvent',self.mouseRelease)
        setattr(drawWidget,'mouseDoubleClickEvent',self.mouseDoubleClick)
        setattr(drawWidget,'wheelEvent',self.mouseWheelMove)
        setattr(drawWidget,'keyPressEvent',self.keyPress)
        setattr(drawWidget,'keyReleaseEvent',self.keyRelease)

    def updateView(self):
        '''Called before `fillImage()', used to update the scene and UI before draw.'''
        pass

    def fillImage(self,img):
        '''Called by the widget acting as the drawing target, the QImage `img' is filled with data here, then drawn.'''
        pass

    def mousePress(self,e):
        pass

    def mouseRelease(self,e):
        pass

    def mouseDrag(self,e,dx,dy):
        '''
        Called when the mouse is moved with a button pressed, `e' is the MouseEvent from mouseMoveEvent() calls,
        and (dx,dy) is the distance the mouse was moved since the last event.
        '''
        pass

    def mouseWheelMove(self,e):
        pass

    def mouseDoubleClick(self,e):
        pass

    def keyPress(self,e):
        '''By default passes the event `e' to QtWidgets.QWidget.keyPressEvent.'''
        QtWidgets.QWidget.keyPressEvent(self,e)

    def keyRelease(self,e):
        '''By default passes the event `e' to QtWidgets.QWidget.keyReleaseEvent.'''
        QtWidgets.QWidget.keyReleaseEvent(self,e)

    def parentClosed(self,e):
        '''
        Called if this widget is inside a parent container and that container is closed. It is up to the parent
        to call this, Qt doesn't do it automatically.
        '''
        pass

    def getDrawDims(self):
        '''Get the draw area (width,height) pair.'''
        return self.drawWidget.width(),self.drawWidget.height()

    def getBoxFitScale(self,w,h):
        '''Returns the scale factor needed to fit a rectangle of dimensions `w' x `h' in the drawing area.'''
        if w==0 or h==0:
            return 1

        dw,dh=self.getDrawDims()
        bscale=dw/abs(w)
        if abs(h)*bscale>dh:
            bscale=dh/abs(h)

        return bscale


class Draw2DView(Ui_Draw2DView):
    '''
    UI class derived from the generated form, it defines callbacks for UI operations and connects appropriate sockets.
    This class implements UI behaviour only and is meant to be used with Base2DWidget in a subtype which inherits both.
    The methods setSourceName() and setPlaneName() must be overriddent.
    '''
    def __init__(self,parent=None):
        self.setupUi(self)

        self.secondsSelected=set() # set of selected secondary representation names or labels
        self.secondsMenu=QtWidgets.QMenu(self)
        self.secondsButton.setMenu(self.secondsMenu)
        self.secondsButton.setPopupMode(QtWidgets.QToolButton.InstantPopup)

        self.setImageStackMax(10)
        self.vsplit.setCollapsible(1,False) # right side is not collapsible
        self.setLeftSideVisible(False) # hide the left side panel initially

        self.imageBox.valueChanged.connect(self.setImageStackPosition)
        self.imageSlider.valueChanged.connect(self.setImageStackPosition)
        self.sliceWidthBox.valueChanged.connect(self.setSliceWidth)
        self.lineWidthBox.valueChanged.connect(self.setLineWidth)
        self.sourceBox.currentIndexChanged.connect(lambda:self.setSourceName(currentIndexDataStr(self.sourceBox)))
        self.planeBox.currentIndexChanged.connect(lambda:self.setPlaneName(currentIndexDataStr(self.planeBox)))

    def fillSecondsMenu(self,seconds):
        '''Fill the selection menu with the list of named secondary objects `seconds.'''

        def _addAction(label,name):
            '''Use a subroutine to ensure `label' and `name' are fresh variables for each call to connect().'''
            action=self.secondsMenu.addAction(label)
            action.setCheckable(True)
            action.setChecked(name in self.secondsSelected)
            action.toggled.connect(lambda b:self.setSecondary(name,b))

        if seconds and not isinstance(seconds[0],str):
            labels,names=list(zip(*seconds)) # assume `seconds' is a list of label-name pairs and separate them out into lists of each
        else:
            labels=seconds # use names as labels
            names=seconds

        self.secondsSelected.intersection_update(set(names))
        self.secondsMenu.clear()

        for label,name in zip(labels,names):
            _addAction(label,name)

    def mouseWheelMove(self,e):
        '''Move through the image stack when the mouse wheel moves with the cursor over the 2D drawing widget.'''
        #delta=1 if getWheelDelta(e)>0 else -1
        delta=getWheelDelta(e)
        delta=delta/abs(delta) if delta else 0
#        if e.orientation()==Qt.Horizontal: # horizontal scrolling in the widget is opposite to the slider
#            delta*=-1

        pos=self.getImageStackPosition()+delta
        self.setImageStackPosition(pos)

    def setSourceName(self,name):
        '''
        Called when the source object's name has been set to `name', in which case the source data should be changed.
        This can be called by clients of this object or through user action by changing the index of self.sourceBox.
        '''
        pass

    def setPlaneName(self,plane):
        '''
        Called when the view plane's name has been set to `plane', in which case the view should be moved. This can
        be called by clients of this object or through user action by changing the index of self.planeBox.
        '''
        pass

    def setSliceWidth(self,width):
        '''Set the width of slices viewed at oblique angles, callable by clients or through the UI.'''
        assert Utils.isMainThread()
        with signalBlocker(self.sliceWidthBox):
            self.sliceWidthBox.setValue(width)

    def setLineWidth(self,width):
        '''Set the width of drawn lines representing sliced geometry, callable by clients or through the UI.'''
        assert Utils.isMainThread()
        with signalBlocker(self.lineWidthBox):
            self.lineWidthBox.setValue(width)

    def setSecondary(self,name,isVisible):
        '''
        Set the visibility of the secondary object named by `name' to `isVisible'. This can be called by clients of the
        object or through user action by changing the selections in self.secondsMenu.
        '''
        if isVisible:
            self.secondsSelected.add(name)
        elif name in self.secondsSelected:
            self.secondsSelected.remove(name)

    def setImageStackMax(self,maxval):
        '''Set the maximum stack index to `maxval' and update the UI, passing a value of 0 hides the image slider UI.'''
        maxval=max(int(maxval),0)
        self.imageSlider.setRange(0,maxval)
        self.imageSlider.setSingleStep(1)
        self.imageBox.setMaximum(maxval)
        self.imageSlider.setVisible(maxval>0)
        self.imageBox.setVisible(maxval>0)
        self.sliceLabel.setVisible(maxval>0)

    def setPlaneBoxVisible(self,vis):
        '''Set the visibility of the plane indicator UI.'''
        self.planeLabel.setVisible(vis)
        self.planeBox.setVisible(vis)

    def setImageStackPosition(self,val):
        '''
        Set the position index within the image stack of the source object to `val', callable by clients or through
        the UI but must be called in the main thread.
        '''
        assert Utils.isMainThread()
        val=Utils.clamp(val,0,self.getImageStackMax())
        with signalBlocker(self.imageBox,self.imageSlider):
            self.imageBox.setValue(val);
            self.imageSlider.setSliderPosition(val)

        self.drawWidget.repaint()

    def getImageStackPosition(self):
        '''Get the index in the image stack of the source object.'''
        return self.imageSlider.sliderPosition()

    def getImageStackMax(self):
        '''Get the maximum stack index.'''
        return self.imageSlider.maximum()

    def setLeftSideVisible(self,isVisible):
        self.vsplit.moveSplitter(100 if isVisible else 0,1)
        self.vsplit.widget(0).setVisible(isVisible)

    def isLeftSideVisible(self):
        return self.vsplit.isEnabled()


class RenderWidget(QtWidgets.QWidget):
    '''
    This class is used for the actual rendering window. It acquires a RenderAdapter object from the C++ renderer in its
    constructor and associates it with the `conf' argument. After the object is constructed and placed in a layout,
    initViz() is called to create the rendering window. If the `evtHandler' object is a EventHandler object, this will
    receive the events from this widget triggered by rendering, mouse or keyboard input, and resizing. After the widget
    is added and initViz() called, the host window must call show() to become visible, ONLY then can getRenderScene()
    be called to create the RenderScene object necessary to interface with the renderer.
    '''
    def __init__(self,conf,parent=None):
        QtWidgets.QWidget.__init__(self,parent)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAttribute(Qt.WA_PaintOnScreen,True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        
        self.conf=conf
        self.scene=None
        self.evtHandler=None
        self.eventTriggered=False # True if the next event was triggered by internal method calls rather than user input
        self.wid=None

        # create the adapter from the C++ renderer, associating self.conf with it from which config info will be taken
        self.adapt=getRenderAdapter(self.conf)

    def _getWinHandle(self):
        '''Returns the string window handle for this widget (or its parent as appropriate).'''
        if Utils.isWindows:
            return str(int(self.winId()))
        elif Utils.isDarwin:
            return str(int(self.winId()))
        else:
            if QtVersion==4:
                info=self.x11Info()
                return '%i:%i:%i'%(sip.unwrapinstance(info.display()),info.screen(),self.winId())
            else:
                return '0:0:%i'%self.winId() # TODO: correct for PyQt5?

    def initViz(self):
        '''
        Initialize the renderer component. This involves setting the window handle in self.conf to the appropriate
        parameter name, synching the widget in X11 if applicable, and then creating the render window. This will set
        self.wid to the created window's ID.
        '''
        # set the window handle parameter
        paramname='externalWindowHandle' if Utils.isDarwin else 'parentWindowHandle'
        self.conf.set(RenderParamGroup,paramname,self._getWinHandle()) # set the config parameter createWindow needs

        if Utils.isLinux: # call XSync to ensure the handle for the window referred to in `paramname' is valid
            if QtVersion==4:
                import ctypes,ctypes.util
                x11=ctypes.CDLL(ctypes.util.find_library('X11'))
                x11.XSync(sip.unwrapinstance(self.x11Info().display()),False)
            else:
                globalApp.sync() # TODO: is this the correct equivalent for Qt5?

        self.wid=self.adapt.createWindow(self.width(),self.height())

    def getRenderScene(self):
        '''Creates (if necessary) and returns the RenderScene object associated with the internal RenderAdapter object.'''
        assert self.wid is not None
        self.scene=self.scene or self.adapt.getRenderScene()
        return self.scene

    def _triggerEvent(self,name,*args):
        '''
        Calls self.evtHandler._triggerEvent with the given arguments if self.evtHandler isn't None. If the event is
        widgetPostDraw, only send if the scene is set to render in low quality mode; since this event is used to
        trigger a render in high quality after rendering in low quality, this prevents endless rendering loops.
        '''
        if self.evtHandler!=None and (name!=EventType._widgetPostDraw or not self.getRenderScene().getRenderHighQuality()):
            self.evtHandler._triggerEvent(name,*args)

    def paintEngine(self):
        '''Override method returning None to clue in Qt that we're handling painting ourselves.'''
        return None

    def resizeEvent(self,e):
        '''
        Triggered when the widget resizes, this handles sending the correct resize information to the adapter which
        must keep track of size in platform-specific ways. This triggers the widgetResize event and calls repaint().
        '''
        QtWidgets.QWidget.resizeEvent(self,e)

        r=self.geometry() if not Utils.isDarwin else QtCore.QRect()
        self.adapt.resize(*r.getRect())

        self._triggerEvent(EventType._widgetResize,self.width(),self.height())
        self.repaint()

    def update(self):
        self.eventTriggered=True
        self._triggerEvent(EventType._widgetPreDraw)
        QtWidgets.QWidget.update(self)
        self._triggerEvent(EventType._widgetPostDraw)

    def repaint(self,*q):
        self.eventTriggered=True
        QtWidgets.QWidget.repaint(self,*q)
        
    def mousePressEvent(self,e):
        self._triggerEvent(EventType._mousePress,e)

    def mouseReleaseEvent(self,e):
        self._triggerEvent(EventType._mouseRelease,e)

    def mouseDoubleClickEvent(self,e):
        self._triggerEvent(EventType._mouseDoubleClick,e)

    def wheelEvent(self,e):
        self._triggerEvent(EventType._mouseWheel,e)
        
    def mouseMoveEvent(self,e):
        self._triggerEvent(EventType._mouseMove,e)

    def keyPressEvent(self,e):
        self._triggerEvent(EventType._keyPress,e)
        QtWidgets.QWidget.keyPressEvent(self,e)

    def keyReleaseEvent(self,e):
        self._triggerEvent(EventType._keyRelease,e)
        QtWidgets.QWidget.keyReleaseEvent(self,e)

    def paintEvent(self,e):
        '''
        Triggered when repainting the widget, this calls self.adapt.paint() if self.scene is not None, which prevents
        attempting to repaint before the window this widget is in is reading for rendering. For this to function, the
        host window must call show() for itself before calling self.getRenderScene() to create the RenderScene object.
        If self.eventTriggered if False then the rendering is done in high quality mode, and self.eventTriggered is
        always set to False afterwards.
        '''
        if not self.eventTriggered:
            self.getRenderScene().setRenderHighQuality(True)
        self.eventTriggered=False

        # do not render until after the RenderScene has been created, ie. after show() in VisualizerWindow.__init__()
        if self.scene!=None:
            self.adapt.paint()


class ConsoleWidget(QtWidgets.QTextEdit):
    '''
    Simulates a Python terminal in a QTextEdit widget. This is similar to code.InteractiveConsole in how it executes
    individual lines of source. It includes a basic session history feature.
    '''

    def __init__(self,win,conf,parent=None):
        QtWidgets.QTextEdit.__init__(self,parent)
        self.setFont(QtGui.QFont('Courier', 10))

        self.win=win
        self.logfile=''
        self.locals={'win':self.win}
        self.comp=codeop.CommandCompiler()
        self.inputlines=['']
        self.linebuffer=[]
        self.history=[]
        self.historypos=0
        self.curline=''
        self.isExecuting=False
        self.initCmds=['from __future__ import print_function, division','from eidolon import *']

        self.inputevent=threading.Event()
        self.inputevent.set()

        self.isMetaDown=False # is a meta (shift/ctrl/alt/win/cmd) down?
        self.metakeys=(Qt.Key_Control,Qt.Key_Shift,Qt.Key_Alt,Qt.Key_AltGr,Qt.Key_Meta)
        self.metadown=0

        self.orig_stdout=sys.stdout
        self.orig_stderr=sys.stderr

        try:
            self.ps1=sys.ps1
        except:
            self.ps1='>>> '

        try:
            self.ps2=sys.ps2
        except:
            self.ps2='... '

        self.currentPrompt=self.ps1

        # try to read the setting for number of log file lines, default to 10000 if not present or the value is not a number
        try:
            self.loglines=int(conf.get(platformID,ConfVars.consoleloglen))
        except:
            self.loglines=10000

        # try to set the log filename, if there's no user directory this won't be set so no logging will occur
        if os.path.isdir(conf.get(platformID,ConfVars.userappdir)):
            self.logfile=os.path.join(conf.get(platformID,ConfVars.userappdir),conf.get(platformID,ConfVars.consolelogfile))

        # read the log file
        if os.path.isfile(self.logfile):
            try:
                with open(self.logfile) as o:
                    log=[s.rstrip() for s in o.readlines()]

                self.history=log[-self.loglines:] # add no more than self.loglines values to the history
            except Exception as e:
                self.write('Cannot open console log file %r:\n%r\n'%(self.logfile,e))

        self.thread=threading.Thread(target=self._interpretThread)
        self.thread.daemon=True
        self.thread.start()
        
    def _interpretThread(self):
        '''
        Daemon thread method which prints the appropriate prompt and reads commands given through sendInputLine().
        These are then executed with execute().
        '''

        while not self.win.isExec:
            time.sleep(0.01) # wait for window to appear

        for cmd in self.initCmds:
            self.execute(cmd) # execute initialization commands

        multiline=False # indicates if following lines are expected to be part of a indented block
        while True:
            self.inputevent.wait() # wait for an input line to come in
            self.inputevent.clear()

            line=self._getInputLine()
            while line!=None:
                multiline=self.execute(line)
                line=self._getInputLine()

                if line==None:
                    self.currentPrompt=self.ps2 if multiline else self.ps1

                    if len(self.getCurrentLine())>0: # ensure prompt goes onto a new line
                        self.write('\n')

                    self.write(self.currentPrompt)

    @Utils.locking
    def sendInputLine(self,line,historyAppend=True):
        '''Send the given line to the interpreter's line queue.'''

        # skip the usual console exiting commands, these don't make sense for a persistent console
        if line in ('exit','exit()','quit','quit()'):
            self.inputlines.append('') # do nothing, forces clean prompt printing
        else:
            # execute command and append to history
            self.inputlines.append(line)
            self.historypos=0

            # append only if not a duplicate of previous entry
            if historyAppend and len(line.strip())>0 and (len(self.history)==0 or self.history[-1]!=line):
                self.history.append(line)

                # write to log file if present
                if self.logfile:
                    try:
                        with open(self.logfile,'a') as o:
                            o.write('%s\n'%line)
                    except Exception as e:
                        self.write('Cannot write to console log file %r:\n%r\n'%(self.logfile,e))

        self.inputevent.set()

    def sendInputBlock(self,block,printBlock=True):
        '''Send a block of code lines `block' to be interpreted, printing the block to the console if `printBlock'.'''
        block=str(block)
        lines=block.split('\n')

        if len(lines)==1: # if there's only one line, print it and wait for user interaction
            self.write(lines[0])
        elif len(lines)>1:
            if printBlock: # set the cursor and print out the code block into the console
                self._setCursor(endline=True)
                self.write(block+'\n')

            lastindent=0 # last line's indent distance
            for line in lines:
                if line.strip(): # skip empty lines
                    indent=Utils.first(i for i in range(len(line)) if not line[i].isspace()) # get line's indent
                    # if this line is not indented but last one was, send an empty line to end a multi-line input block
                    if indent==0 and lastindent>0:
                        self.sendInputLine('\n')

                    lastindent=indent
                    self.sendInputLine(line)

            self.sendInputLine('\n')

    @Utils.locking
    def _getInputLine(self):
        return self.inputlines.pop(0) if len(self.inputlines)>0 else None

    def updateLocals(self,localvals):
        '''Override the local variable dictionary with the given dictionary.'''
        self.locals.update(localvals)

    def execute(self,line):
        '''
        Compile and interpret the given Python statement. Returns true if more statements are expected to fill an
        indented block, false otherwise.
        '''

        try:
            # If compiling an indented block (eg. an if statement) all the lines of the block must be submitted at
            # once followed by a blank line. Only then will the compile happen, otherwise a None object is returned
            # indicating more lines are needed. To do this statements accumulate in the buffer until compilation.
            self.linebuffer.append(line)
            comp = self.comp('\n'.join(self.linebuffer), '<console>')

            if comp is None: # expecting more statements to fill in an indented block, return true to indicate this
                return True

            sys.stdout=self # reroute stdout/stderr to print to the widget
            sys.stderr=self
            self.linebuffer=[]

            self.isExecuting=True
            exec(comp, self.locals) # execute the statement(s) in the context of the local symbol table
        except SyntaxError:
            sys.last_type, sys.last_value, sys.last_traceback = sys.exc_info()

            try:
                msg, (dummy_filename, lineno, offset, line) = sys.last_value
                value = SyntaxError(msg, ('<console>', lineno, offset, line))
                sys.last_value = value
            except:
                value=None

            self.linebuffer=[]
            self.write('\n'.join(traceback.format_exception_only(SyntaxError, value)))
        except Exception as e:
            self.linebuffer=[]
            self.write(str(e)+'\n')
            self.write(traceback.format_exc())
        finally:
            sys.stdout=self.orig_stdout # always restore stdout/stderr
            sys.stderr=self.orig_stderr
            self.isExecuting=False

        return False # no more statements expected

    def write(self, line):
        '''Write a line of text to the text window.'''

        def writeLine():
            self.insertPlainText(line)
            self.ensureCursorVisible()

        self.win.callFuncUIThread(writeLine)

    def flush(self):
        '''Stream compatibility, does nothing.'''
        pass

    def _setCursor(self,startline=False,endline=False):
        '''
        Set the cursor to the appropriate position, ensuring it is on the last line, after the prompt. If 'startline'
        is true or the cursor is somewhere not after the last prompt, the cursor is placed just after the last prompt.
        If 'endline' is true then the cursor goes at the end of the last line.
        '''

        doc=self.document()
        cursor=self.textCursor()
        doclen=len(doc.toPlainText())
        blocklen=len(doc.lastBlock().text())
        promptlen=len(self.currentPrompt)
        startlinepos=doclen-blocklen+promptlen

        if endline:
            cursor.setPosition(doclen)
        elif startline or cursor.position()<startlinepos:
            cursor.setPosition(min(doclen,startlinepos))

        self.setTextCursor(cursor)

    def getCurrentLine(self):
        '''Get the current statement being entered, minus the prompt'''

        promptlen=len(self.currentPrompt)
        return str(self.document().lastBlock().text())[promptlen:]

    def clearCurrentLine(self):
        '''Remove the current statement, leaving only the prompt'''

        self._setCursor(endline=True)

        for i in self.getCurrentLine():
            self.textCursor().deletePreviousChar()

    def focusOutEvent(self,event):
        self.isMetaDown=False
        self.metadown=0
        QtWidgets.QTextEdit.focusOutEvent(self,event)

    def keyReleaseEvent(self, event):
        if event.key() in self.metakeys:
            self.isMetaDown=False
            self.metadown ^= event.key()

        QtWidgets.QTextEdit.keyReleaseEvent(self,event)

    def insertFromMimeData(self,src):
        '''Triggered when pasting text, print out then interpret this line-by-line'''
        self.sendInputBlock(src.text())

    def keyPressEvent(self, event):
        '''
        Interpret key presses and move the cursor as necessary. If enter/return is pressed, the current statement is
        sent to be interpreted. Up and down cycle through the statement history. Usually the method of the superclass
        is called but this is omitted when preserving correct cursor position for some keys (eg. backspace).
        '''

        key=event.key()
        callSuper=key not in (Qt.Key_Up, Qt.Key_Down)

        if key in self.metakeys:
            self.isMetaDown=True
            self.metadown |= key

        if key in (Qt.Key_Return, Qt.Key_Enter): # execute the current line
            self._setCursor(endline=True) # move the cursor to the end so that the new line is done correctly
            self.sendInputLine(self.getCurrentLine())
        elif not self.isMetaDown:
            self._setCursor() # ensure cursor is correctly positioned, don't move it if doing meta commands eg. ctrl+c

        if key == Qt.Key_Up: # previous history item
            if len(self.history)>0 and self.historypos>-len(self.history):
                if self.historypos==0:
                    self.curline=self.getCurrentLine()

                self.historypos-=1
                self.clearCurrentLine()
                self.write(self.history[self.historypos])

        if key == Qt.Key_Down: # next history item
            if len(self.history)>0 and self.historypos<0:
                self.historypos+=1
                self.clearCurrentLine()
                if self.historypos==0:
                    self.write(self.curline)
                    self.curline=''
                else:
                    self.write(self.history[self.historypos])

        # prevent backspacing over the prompt
        if key == Qt.Key_Backspace and self.textCursor().positionInBlock() <= len(self.currentPrompt):
            callSuper=False

        if callSuper:
            QtWidgets.QTextEdit.keyPressEvent(self,event)

        # don't move the cursor if a meta key combination (such as ctrl+c) is pressed
        if not self.isMetaDown and key not in (Qt.Key_Return, Qt.Key_Enter):
            self._setCursor()

        # restore the prompt if undo has removed it
        if self.isMetaDown and key==Qt.Key_Z and not str(self.document().lastBlock().text()).strip():
            self.write(self.currentPrompt)
            self._setCursor(endline=True)

        # disallow OS X specific key combo of Cmd+Left or Ctrl+a to go past the prompt
        if Utils.isDarwin:
            if ((self.metadown & Qt.Key_Control) and key==Qt.Key_Left) or ((self.metadown & Qt.Key_Meta) and key==Qt.Key_A):
                self._setCursor()


class BaseSpectrumWidget(QtWidgets.QWidget):
    '''
    This widget implements a generic color spectrum with an alpha curve. The interface is defined a number of template
    methods that are used to pass data between instances of this widget and an associated spectrum object. It stores
    colors, positions, and alpha values, but does not define interpolation, this is left to the associated object.
    '''
    class SmallButton(object):
        '''A simple class implementing a small button drawn as a rectangle with a text label in the center.'''
        def __init__(self,x,y,w,h,text,parent):
            self.x=x
            self.y=y
            self.w=w
            self.h=h
            self.text=text
            self.parent=parent

        def pos(self):
            dx=int(self.x if self.x>=0 else (self.parent.width()+self.x))
            dy=int(self.y+self.parent.height()-self.parent.bottomheight)
            return dx,dy

        def isClicked(self,x,y):
            dx,dy=self.pos()
            return dx<=x<=(dx+self.w) and dy<=y<=(dy+self.h)

        def draw(self,p):
            dx,dy=self.pos()
            p.setPen(QtGui.QPen(Qt.GlobalColor(Qt.black)))
            p.setBrush(QtGui.QBrush(Qt.GlobalColor(Qt.white)))
            p.setFont(QtGui.QFont('Courier', 10 if Utils.isDarwin else 8))

            if QtVersion==5:
                p.drawRoundedRect(dx,dy,self.w,self.h,25,25,Qt.RelativeSize) # TODO: ugly, fix
            else:
                p.drawRoundRect(dx,dy,self.w,self.h)
            p.drawText(dx+3,dy+10,self.text)

    UPARROW=u'\u25b2'
    DOWNARROW=u'\u25bc'

    def __init__(self,parent=None,minheight=240):
        QtWidgets.QWidget.__init__(self,parent)
        self.setMinimumSize(QtCore.QSize(10, minheight))
        self.setMaximumSize(QtCore.QSize(5000, 800))
        self.setFocusPolicy(Qt.StrongFocus)

        self.minheight=minheight
        self.isDblHeight=False
        self.bg=QtGui.QBrush(Qt.GlobalColor(Qt.white))
        self.bar=QtGui.QBrush(Qt.GlobalColor(Qt.lightGray))

        self.colors=[] # spectrum colors
        self.colorpos=[] # positions of elements in self.colors

        self.alphactrls=[] # list of (x,y,z) triples defining the alpha curve

        self.bottomheight=28 # height of bottome blank bar
        self.margin=4 # margin around spectrum
        # color marker dimensions
        self.markerheight=20
        self.markerwidth=20
        self.markerangle=45
        self.ctrlradius=8 # radius of the alpha curve control point

        self.isLinearAlpha=False
        self.colorselected=None
        self.alphaselected=None

        self.delMarker=BaseSpectrumWidget.SmallButton(self.margin,15,12,12,'-',self)
        self.expandMarker=BaseSpectrumWidget.SmallButton(self.margin+12,15,12,12,BaseSpectrumWidget.DOWNARROW,self)
        self.linMarker=BaseSpectrumWidget.SmallButton(-48-self.margin,15,46,12,'Linear',self)

    def getValues(self):
        '''Copy values from the spectrum object into members `colors', `colorpos', `alphactrls', and `isLinearAlpha'.'''
        pass

    def setValues(self,colorIndex=None,alphaIndex=None):
        '''Set the values in the spectrum object. If `colorIndex' is not None, the color value from `color' and
        `colorpos' is set to that index in the object. If `alphaIndex' is not None, the alpha value from `alphactrls'
        is set to that index. If both are None, all the values from `color', `colorpos', and `alphactrls' are set in
        the spectrum object.
        '''
        pass

    def interpolateColor(self,t):
        '''Get the interpolated color in the spectrum at unit position `t'.'''
        pass

    def setLinearAlpha(self,linear):
        '''Set the alpha curve to be linear if `linear' is True, otherwise it's a cubic curve.'''
        pass

    def setDoubleHeight(self,dblHeight):
        self.setMinimumSize(QtCore.QSize(0, self.minheight*(2 if dblHeight else 1)))
        self.isDblHeight=dblHeight

    def getSpectrumDim(self):
        '''Get the dimensions of the spectrum area.'''
        return self.width()-self.margin*2,self.height()-self.bottomheight-self.margin*2

    def _markerRect(self,i):
        '''Get the dimensions of the rectangular marker area.'''
        x=int(self.colorpos[i]*(self.width()-self.margin*2))+self.margin
        return (x-self.markerwidth/2,self.height()-self.bottomheight,self.markerwidth,self.markerheight)

    def _getMarkerIndex(self,x,y):
        x-=self.margin
        w,h=self.getSpectrumDim()
        h+=self.margin*2
        if h<=y<=(h+self.markerheight/2):
            for i,p in enumerate(self.colorpos):
                if abs(x-int(p*w))<=self.markerwidth/2:
                    return i

        return None

    def _getCtrlIndex(self,x,y):
        x-=self.margin
        y-=self.margin
        w,h=self.getSpectrumDim()
        rsq=self.ctrlradius**2

        for i,c in enumerate(self.alphactrls):
            distsq=(x-c[0]*w)**2+(y-(1.0-c[1])*h)**2 # squared distance from (x,y) to this control point
            if distsq<=rsq:
                return i

        return None

    def _chooseColor(self):
        if self.colorselected!=None:
            origcolor=toQtColor(self.colors[self.colorselected])

            c = QtWidgets.QColorDialog.getColor(origcolor, self)
            if validQVariant(c):
                r,g,b,a=c.getRgbF()
                a=self.colors[self.colorselected][3]
                self.colors[self.colorselected]=(r,g,b,a)
                self.setValues()

    def _setSelectedColorPos(self,pos):
        if self.colorselected!=None:
            minv=0.0
            maxv=1.0
            if len(self.colorpos)>1:
                if self.colorselected!=0:
                    self.minv=self.colorpos[self.colorselected-1]+0.0001
                if self.colorselected!=len(self.colorpos)-1:
                    self.maxv=self.colorpos[self.colorselected+1]-0.0001

            self.colorpos[self.colorselected]=Utils.clamp(pos,minv,maxv)
            self.setValues(colorIndex=self.colorselected)
            self.update()

    def _setSelectedAlphaPos(self,x,y):
        if self.alphaselected!=None:
            minx=0.0
            maxx=1.0
            if len(self.alphactrls)>1:
                if self.alphaselected!=0:
                    self.minx=self.alphactrls[self.alphaselected-1][0]+0.0001
                if self.alphaselected!=len(self.alphactrls)-1:
                    self.maxx=self.alphactrls[self.alphaselected+1][0]-0.0001

            self.alphactrls[self.alphaselected]=(Utils.clamp(x,minx,maxx),Utils.clamp(y,0.0,1.0),0)
            self.setValues(alphaIndex=self.alphaselected)
            self.update()

    def _remove(self):
        if self.colorselected!=None:
            self.colors.pop(self.colorselected)
            self.colorpos.pop(self.colorselected)
            if len(self.colors)==0:
                self.colorselected=None
            elif self.colorselected==len(self.colors):
                self.colorselected-=1
        elif self.alphaselected!=None:
            if len(self.alphactrls)==2:
                self.alphactrls=[]
                self.alphaselected=None
            else:
                self.alphactrls.pop(self.alphaselected)
                if len(self.alphactrls)==0:
                    self.alphaselected=None
                elif self.alphaselected==len(self.alphactrls):
                    self.alphaselected-=1

        self.setValues()

    def _setMouseToolTip(self,x,y):
        w,h=self.getSpectrumDim()
        self.setToolTip('%i %i'%(w,h))

    def mousePressEvent(self,e):
        QtWidgets.QWidget.mousePressEvent(self,e)
        pt=(e.x(),e.y())

        if self.delMarker.isClicked(*pt):
            self._remove()
        elif self.expandMarker.isClicked(*pt):
            self.setDoubleHeight(not self.isDblHeight)
        elif self.linMarker.isClicked(*pt):
            self.setLinearAlpha(not self.isLinearAlpha)
        else:
            self.colorselected=self._getMarkerIndex(*pt)

            if self.colorselected==None:
                self.alphaselected=self._getCtrlIndex(*pt)
            else:
                self.alphaselected=None

        self.update()

    def mouseDoubleClickEvent(self,e):
        w,h=self.getSpectrumDim()
        x=e.x()-self.margin
        y=e.y()-self.margin

        self.colorselected=self._getMarkerIndex(e.x(),e.y())
        if self.colorselected!=None:
            self._chooseColor()
        elif 0<=x<=w and 0<=y<=h:
            newpos=(float(e.x()-self.margin)/w,1.0-float(e.y()-self.margin)/h,0)

            if len(self.alphactrls)==0:
                self.alphactrls=[(0,newpos[1],0),newpos]
            else:
                self.alphactrls.append(newpos)

            self.setValues()
        elif 0<=x<=w and (h+self.margin*2)<=e.y()<=(h+self.markerheight/2+self.margin*2):
            x=float(x)/w
            r,g,b,a=self.interpolateColor(x)

            ind=Utils.first(i-1 for i,p in enumerate(self.colorpos) if p>x)
            if ind==None:
                self.colorpos.append(x)
                self.colors.append((r,g,b,a))
            else:
                self.colorpos.insert(ind,x)
                self.colors.insert(ind,(r,g,b,a))

            self.setValues()

        self.update()

    def wheelEvent(self,e):
        if self.colorselected!=None:
            delta=getWheelDelta(e)
            delta=delta/abs(delta) if delta else 0
            self._setSelectedColorPos(self.colorpos[self.colorselected]+delta*0.0001)

    def mouseMoveEvent(self,e):
        w,h=self.getSpectrumDim()
        dx=Utils.clamp(float(e.x()-self.margin)/w,0,1)
        dy=Utils.clamp(1.0-float(e.y()-self.margin)/h,0,1)

        if self.colorselected!=None:
            self._setSelectedColorPos(dx)

            t=self.colorpos[self.colorselected]
            QtWidgets.QToolTip.showText(e.globalPos(),'T: %.3f'%t)
        elif self.alphaselected!=None:
            self._setSelectedAlphaPos(dx,dy)

            x,y,z=self.alphactrls[self.alphaselected]
            QtWidgets.QToolTip.showText(e.globalPos(),'T: %.3f A: %.3f'%(x,y))

    def keyPressEvent(self,e):
        if e.key() in (Qt.Key_Backspace,Qt.Key_Delete):
            self._remove()
            self.update()
        else:
            QtWidgets.QWidget.keyPressEvent(self,e)

    def paintEvent(self,e):
        self.getValues()

        w,h=self.getSpectrumDim()
        prevcurve=None
        p=QtGui.QPainter(self)

        p.fillRect(0,0,self.width(),self.height(),self.bg)
        p.fillRect(0+self.margin,h+self.margin*2,w,self.markerheight/2+3,self.bar)

        # buttons
        self.delMarker.draw(p)
        self.expandMarker.text=BaseSpectrumWidget.UPARROW if self.isDblHeight else BaseSpectrumWidget.DOWNARROW
        self.expandMarker.draw(p)
        self.linMarker.text='Cubic' if self.isLinearAlpha else 'Linear'
        self.linMarker.draw(p)

        # spectrum colors and alpha control curve lines
        for x in range(w):
            r,g,b,a=self.interpolateColor(float(x)/w)
            x+=self.margin
            p.fillRect(x,self.margin,1,h,toQtColor((r,g,b,1.0)))
            y=int(Utils.clamp(1.0-a,0.0,1.0)*h)+self.margin
            if prevcurve==None:
                prevcurve=(x,y-1)

            p.setPen(QtGui.QPen(Qt.GlobalColor(Qt.white)))
            p.drawLine(prevcurve[0],prevcurve[1]-1,x,y-1)
            #p.drawLine(prevcurve[0],prevcurve[1]+1,x,y+1)
            p.setPen(QtGui.QPen(Qt.GlobalColor(Qt.black)))
            p.drawLine(prevcurve[0],prevcurve[1],x,y)
            prevcurve=(x,y)

        # alpha curve control points
        for i,c in enumerate(self.alphactrls):
            rad=self.ctrlradius+(2 if i==self.alphaselected else 0)
            x=int(c[0]*w)+self.margin
            y=int((1.0-c[1])*h)+self.margin
            p.setBrush(QtGui.QBrush(toQtColor((0,0,0,1.0))))
            p.drawEllipse(x-rad/2,y-rad/2,rad,rad)
            p.setBrush(QtGui.QBrush(toQtColor((1.0,0,0,1.0))))
            p.drawEllipse(x-rad/2+1,y-rad/2+1,rad-2,rad-2)

        # spectrum markers
        for i in range(len(self.colors)):
            r,g,b,a=self.colors[i]
            x,y,mw,mh=self._markerRect(i)

            if i==self.colorselected:
                p.setBrush(QtGui.QBrush(toQtColor((0,0,0,1.0))))
                p.drawPie(x-3,y-self.markerheight/2-4,mw+6,mh+6,-16*self.markerangle,-16*(180-self.markerangle*2))

            p.setBrush(QtGui.QBrush(toQtColor((r,g,b,1.0))))
            p.drawPie(x,y-self.markerheight/2+1,mw,mh,-16*self.markerangle,-16*(180-self.markerangle*2))

        p.end()


class ScreenshotDialog(QtWidgets.QDialog,Ui_ScreenshotForm):
    def __init__(self,win,start,end,fps,steps,cameras):
        QtWidgets.QDialog.__init__(self,win)
        self.setupUi(self)
        self.win=win
        self.cameras=cameras
        self.currentCamera=cameras[0][0]

        fillList(self.srcBox,[c[0] for c in cameras])

        self.pathButton.clicked.connect(self._choosePath)
        self.srcBox.currentIndexChanged.connect(self._chooseSource)
        self.singleRadio.clicked.connect(self._setEnabled)
        self.multipleRadio.clicked.connect(self._setEnabled)
        self.startBox.valueChanged.connect(self._updateCount)
        self.endBox.valueChanged.connect(self._updateCount)
        self.fpsBox.valueChanged.connect(self._updateCount)
        self.stepsBox.valueChanged.connect(self._updateCount)
        self.saveButton.clicked.connect(self._save)
        self.cancelButton.clicked.connect(self.close)
        self.result=None
        self._setEnabled(False)

        self.setTimestepValues(start,end,fps,steps)
        self._chooseSource(0)
        self._choosePath()

    def setDimensionValues(self,width,height):
        self.widthBox.setValue(width)
        self.heightBox.setValue(height)

    def setTimestepValues(self,start,end,fps,steps):
        self.startBox.setValue(start)
        self.endBox.setValue(end)
        self.startBox.setValue(start)
        self.endBox.setValue(end)
        self.fpsBox.setValue(fps)
        self.stepsBox.setValue(steps)
        self.multipleRadio.setEnabled(end>start)

    def getTimestepValues(self):
        return self.startBox.value(),self.endBox.value(),self.fpsBox.value(),self.stepsBox.value()

    def _choosePath(self):
        savename=self.win.chooseFileDialog('Choose Screenshot filename',filterstr='Image Files (*.png *.jpg)',isOpen=False)
        if savename!='':
            self.pathBox.setText(savename)

    def _setEnabled(self,b=None):
        enable=b if b!=None else self.multipleRadio.isChecked()
        self.startBox.setEnabled(enable)
        self.endBox.setEnabled(enable)
        self.fpsBox.setEnabled(enable)
        self.stepsBox.setEnabled(enable)
        self._updateCount()

    def _updateCount(self,*b):
        start,end,fps,steps=self.getTimestepValues()
        numframes=max(0,int(((end-start)*fps)/steps) if steps!=0 else 0)+1
        self.totalLabel.setText('Total # of Images: %i'%numframes)

    def _chooseSource(self,i):
        _,self.currentCamera,w,h=self.cameras[i]
        self.setDimensionValues(w,h)

    def _save(self):
        path=str(self.pathBox.text())
        self.result=None

        if Utils.checkValidPath(path)!=0:
            self.win.showMsg('Cannot save screenshot(s) using the specified file','Invalid File Path')
        else:
            self.result=[path,self.currentCamera,self.widthBox.value(),self.heightBox.value(),0,0,0,self.transBox.isChecked()]
            if self.multipleRadio.isChecked():
                start,end,fps,steps=self.getTimestepValues()
                interval=steps/fps if fps!=0 else 0
                self.result[4:7]=[start,end,interval]

            self.close()


@signalclass
class VisualizerWindow(QtWidgets.QMainWindow,Ui_MainWindow):
    '''
    The main window of the application. This contains the render widget, scene panel, console panel, scratch pad panel,
    and whatever dock windows are created. The code defined in this class is meant only to actuate the UI, fill lists
    and other widgets with values, create input or notification windows, and perform other functions which don't delve
    into the model or controller layer.
    '''

    method_signal=QtCore.pyqtSignal(str,tuple,dict) # must be static for reasons, and no way of adding it as part of signalclass

    # named tuple type used to map UI elements to stored objects, data, and routines
    ObjMapTuple=collections.namedtuple('ObjMapTuple','obj propbox assettype updateFunc dblClickFunc menu menuFunc')

    def __init__(self,conf,width=1200,height=600):
        super(VisualizerWindow, self).__init__()

        self.setupUi(self)
        self.setWindowTitle(mainTitleString%(eidolon.__appname__,eidolon.__version__))
        self.setDockOptions(QtWidgets.QMainWindow.AllowNestedDocks)

        self.objMap=Utils.MutableDict() # maps UI items to ObjMapTuple instances
        self.mgr=None # scene manager object, set later
        self.dockWidgets=[] # list of docked widget objects
        self.isExec=False # set to True when the event loop is started
        self.timestepSliderMult=1.0 # number of ticks to divide timesteps by in the timestep slider
        self.assetRootMap={} # maps asset types to the root tree item for each type in the asset tree widget
        self.logfileView=None

        self.msgdialog=ShowMessageDialog(self)

        self.dialogDir=os.getcwd() # stored directory for open/save dialogs
        if '.app' in self.dialogDir:
            self.dialogDir=os.path.expanduser('~')

        # connect list signals
        self.treeWidget.currentItemChanged.connect(lambda:self._clickedTree(self.propScrollArea,self.treeWidget.currentItem()))
        self.treeWidget.itemClicked.connect(lambda:self._clickedTree(self.propScrollArea,self.treeWidget.currentItem()))
        self.treeWidget.itemDoubleClicked.connect(lambda:self._doubleClickedTree(self.propScrollArea,self.treeWidget.currentItem()))
        self.assetList.itemSelectionChanged.connect(lambda :self._clickedTree(self.assetScrollArea,self.assetList.currentItem()))
        self.treeWidget.customContextMenuRequested.connect(lambda p:self._menuClickedTree(self.treeWidget,p))

        # connect actions
        self.action_Scene_Elements.triggered.connect(lambda:self.interfaceDock.setVisible(not self.interfaceDock.isVisible()))
        self.action_Console.triggered.connect(lambda:self.consoleWidget.setVisible(not self.consoleWidget.isVisible()))
        self.action_Time.triggered.connect(lambda:self.timeWidget.setVisible(not self.timeWidget.isVisible()))
        self.actionScratch_Pad.triggered.connect(lambda:self.scratchWidget.setVisible(not self.scratchWidget.isVisible()))
        self.action_About.triggered.connect(self._showAbout)
        self.action_Check_Version.triggered.connect(self._checkVersion)

        self.execButton.clicked.connect(self._executeScratch)
        self.loadScratchButton.clicked.connect(self._loadScratch)
        self.saveScratchButton.clicked.connect(self._saveScratch)

        setCollapsibleGroupbox(self.treeGroup)

        # add the progress bar and text box to the status bar
        self.statusProgressBar=QtWidgets.QProgressBar()
        self.statusProgressBar.setMaximumWidth(200)
        self.statusProgressBar.setRange(0,1)
        self.statusProgressBar.setValue(1)
        self.statusProgressBar.setFormat('%p% (%v / %m)')
        self.statusProgressBar.setTextVisible(True)
        self.statusProgressBar.setVisible(False)
        self.statusText=QtWidgets.QLabel(self)
        self.statusBar.addWidget(self.statusProgressBar)
        self.statusBar.addWidget(self.statusText)
        self.setStatus('Ready')

        for key,name,desc in AssetType:
            self.assetRootMap[key]=QtWidgets.QTreeWidgetItem(self.assetList)
            self.assetRootMap[key].setText(0,name)
            self.assetRootMap[key].setToolTip(0,desc)

        self.console=ConsoleWidget(self,conf)
        self.consoleLayout.addWidget(self.console)
        self.consoleWidget.setVisible(False) # hide the console by default

        self.timeWidget.setVisible(False) # hide the time dialog by default
        self.scratchWidget.setVisible(False) # hide the scratch pad by default

        # replace the key press handler for the scratch pad so that the code is executed when Ctrl/Meta+Enter is pressed
        @Utils.setmethod(self.scratchWidget,'keyPressEvent')
        def _keyPressEvent(e):
            if e.key() in (Qt.Key_Return, Qt.Key_Enter) and e.modifiers()&(Qt.ControlModifier|Qt.MetaModifier):
                self._executeScratch()
            else:
                getattr(self.scratchWidget,'__old__keyPressEvent')(e) # TODO: why do I need to use getattr?

        # reset self.viz to use Eidolon renderer widget
        self.mainLayout.removeWidget(self.viz)
        self.viz1=self.viz
        self.viz=RenderWidget(conf,self)
        self.mainLayout.addWidget(self.viz)
        self.viz.initViz()

        # force a relayout
        self.resize(width, height+1)
        self.show()
        self.setRenderWinSize(width, height)

        self.scene=self.viz.getRenderScene() # must be after show() since rendering is prevented until the RenderScene is created

        self.scene.logMessage('Eidolon Version: '+eidolon.__version__)
        self.scene.logMessage('Qt Version: '+str(QtCore.qVersion()))
        self.scene.logMessage('Python Version: '+sys.version)
        self.scene.logMessage('Python exe: '+sys.executable)
        self.scene.logMessage('Python path: '+str(sys.path))

        self.raise_() # bring window to front in OS X
        self.activateWindow() # bring window to front in Windows (?)

        resizeScreenRelative(self,0.8,0.8)
        centerWindow(self)

    def _showAbout(self):
        '''Show the about dialog box.'''
        vals=(eidolon.__appname__,eidolon.__copyright__,eidolon.__version__,sys.version,str(QtCore.qVersion()),QtCore.PYQT_VERSION_STR)
        msg='%s\n%s\n\nVersion: %s\nPython Version: %s\nQt Version: %s\nPyQt Version: %s'%vals
        QtWidgets.QMessageBox.about(self,'About %s'%eidolon.__appname__,msg)
        
    def _checkVersion(self):
        '''Check the application version against the repository API URL and show the results with the link to the site.'''
        url=eidolon.__verurl__
        title='Checking Version'
        
        try:
            cver,nver,isnew=Utils.getVersionsFromRepoURL(url)
            msg='''Current Version: %s<br>
                   Newest Version: %s<br><br>
                   <a href="%s">Download latest release.</a>
                '''%(cver,nver or '???',eidolon.__website__)
                
            self.showMsg(textwrap.dedent(msg),title)
        except Exception as e:
            QtWidgets.QMessageBox.about(self,title,repr(e))

    @signalmethod
    def setRenderWinSize(self,w,h):
        '''Resize the window so that the rendering widget's draw area has dimensions (w,h).'''
        self.resize(self.width()+w-self.viz.width(),self.height()+h-self.viz.height())

    @signalmethod
    def relayoutViz(self):
        '''Cause the 3D visualization widget to redo its layout.'''
        s=self.viz.size()
        self.viz.resize(s.width(),s.height()+1)
        self.viz.resize(s.width(),s.height())

    def keyPressEvent(self,e):
        if e.key() == Qt.Key_F11:
            self.toggleFullscreen()
        elif e.key() == Qt.Key_Escape:
            self.close()
        else:
            QtWidgets.QMainWindow.keyPressEvent(self,e)

    def callFuncUIThread(self,func,*args,**kwargs):
        '''
        Call the given function with the given arguments in the UI (main) thread. This allows operations needing to be
        done by the UI thread to be defined in arbitrary functions and despatched from any thread. This assumes that
        whatever `func' does is thread-safe and won't wait on another event from the UI thread, otherwise it will
        deadlock since the call to callFuncUIThread() will wait indefinitely for a result from `func'. This method
        can be safely called from the UI thread however, assuming these properties of `func'.
        '''
        future=Utils.Future()
        self._callFuncAsSignal(func,future,args,kwargs)
        return future(None)

    @signalmethod
    def _callFuncAsSignal(self,func,future,args,kwargs):
        '''Call the function `func' with the given arguments, and storing the result (or thrown exception) in `future'.'''
        with future:
            v=func(*args,**kwargs)
            future.setObject(v)

    def sync(self):
        '''Cause the calling thread to wait until all slot operations prior to this one have completed.'''
        self.callFuncUIThread(lambda:None)

    @signalmethod
    def repaintScene(self):
        self.viz.update()

    @signalmethod
    def captureWidget(self,widg,filename):
        widg.update()
        p=QtGui.QPixmap.grabWindow(widg.winId())
        p.save(filename)

    @signalmethod
    def setStatus(self,msg,progress=0,progressmax=0):
        if progressmax>0 and Utils.isDarwin:
            msg='%.0f%% (%i/%i) '%((100.0*progress)/progressmax,progress,progressmax) +msg

        self.statusText.setText(msg)
        self.statusProgressBar.setVisible(progressmax>0)
        self.statusProgressBar.setRange(0,progressmax)
        self.statusProgressBar.setValue(progress)

    @signalmethod
    def showMessage(self,msg,msTime=0):
        self.statusBar.showMessage(msg if msg!=None and len(msg.strip())>0 else '',int(msTime))

    @signalmethod
    def showTimeDialog(self,doShow,start,end,step):
        self.timeWidget.setVisible(doShow)
        self.timestepBox.setRange(float(start),float(end))
        self.timestepSliderMult=100.0 if (end-start)<=100 else 1.0
        self.timestepSlider.setRange(int(start*self.timestepSliderMult),int(end*self.timestepSliderMult))
        self.timestepSlider.setTickInterval(step)

    @signalmethod
    def setTimeDisplay(self,ts):
        with signalBlocker(self.timestepSlider,self.timestepBox):
            self.timestepSlider.setValue(int(ts*self.timestepSliderMult))
            self.timestepBox.setValue(ts)

    @signalmethod
    def setTimeFPS(self,fps):
        with signalBlocker(self.fpsBox):
            self.fpsBox.setValue(fps)

    @signalmethod
    def setTimeStepsPerSec(self,sps):
        with signalBlocker(self.stepspersecBox):
            self.stepspersecBox.setValue(sps)

    @signalmethod
    def showScratchPad(self,doShow):
        self.scratchWidget.setVisible(doShow)
        
    @signalmethod
    def toggleFullscreen(self):
        isWindowed=self.windowState()!=Qt.WindowFullScreen
        self.setWindowState(Qt.WindowFullScreen if isWindowed else Qt.WindowNoState)

    def _executeScratch(self):
        '''Execute the contents of the scratch pad line-by-line in the console, making it visible first.'''
        self.consoleWidget.setVisible(True)
        text=str(self.scratchEdit.document().toPlainText())
        if text[-1]!='\n':
            text+='\n'

        self.console.sendInputBlock(text,False)

    def _loadScratch(self):
        scratch=self.chooseFileDialog('Choose Load Scratch Filename',chooseMultiple=False,isOpen=True)
        if scratch:
            with open(scratch) as o:
                self.scratchEdit.document().setPlainText(o.read())

    def _saveScratch(self):
        '''Save the scratch pad contents to a chosen file.'''
        scratch=self.chooseFileDialog('Choose Save Scratch Filename',chooseMultiple=False,isOpen=False)
        if scratch:
            text=str(self.scratchEdit.document().toPlainText())
            if text[-1]!='\n':
                text+='\n'

            with open(scratch,'w') as ofile:
                ofile.write(text)

    def _clickedTree(self,tree,item):
        if item in self.objMap:
            v=self.objMap[item]
            widg=tree.widget()

            if v.propbox!=widg:
                tree.takeWidget()
                tree.setWidget(v.propbox)

            if v.updateFunc:
                v.updateFunc(v.obj,v.propbox)

    def _doubleClickedTree(self,tree,item):
        if item in self.objMap:
            v=self.objMap[item]
            if v.dblClickFunc:
                v.dblClickFunc(v.obj)

            if v.updateFunc:
                v.updateFunc(v.obj,v.propbox)

    def _menuClickedTree(self,tree,p):
        item=tree.currentItem()
        if item in self.objMap:
            obj=self.objMap[item].obj
            menu=self.objMap[item].menu
            menuFunc=self.objMap[item].menuFunc
            if menu:
                qmenu=createMenu(menu[0],menu[1:],lambda i:menuFunc(obj,i))
                qmenu.exec_(tree.mapToGlobal(p))

    @signalmethod
    def selectObject(self,obj):
        '''
        Select an object in the scene object tree view. This will set the selection in the tree and replace the
        properties box with the correct one for that object. Passing None as the argument will clear the selection.
        '''
        if not obj:
            self.propScrollArea.takeWidget()
            for i in self.treeWidget.selectedItems():
                i.setSelected(False)
        else:
            item=self.findWidgetItem(obj)
            if not item.isSelected():
                self.selectObject(None)
                item.setSelected(True)
            self._clickedTree(self.propScrollArea,item)

    @Utils.delayedcall(0.1)
    def updateScrollAreas(self):
        '''Updates the possibly visible property boxes when a change occurs. This delays for 0.1s before executing.'''
        self._updateScrollAreasSig()

    @signalmethod
    def _updateScrollAreasSig(self):
        '''Updates the possibly visible property boxes when a change occurs. This executes as a signal.'''
        def updateObj(widg):
            if widg and widg.isVisible():
                result=Utils.first((v.obj,v.updateFunc) for v in self.objMap.values() if v.propbox==widg)
                if result:
                    obj,func=result
                    if func is not None:
                        func(obj,widg)

        updateObj(self.propScrollArea.widget())
        updateObj(self.assetScrollArea.widget())

    @signalmethod
    def setCameraValues(self,fov,nearclip,farclip):
        '''Set the field-of-view, near and far clipping distance UI elements.'''
        with signalBlocker(self.fovBox,self.nearClipBox,self.farClipBox):
            self.fovBox.setValue(fov)
            self.nearClipBox.setValue(nearclip)
            self.farClipBox.setValue(farclip)

    @signalmethod
    def addMenuItem(self,menuName,objName,text,callback):
        '''
        Add a menu item to the menu `menuName', which must be one of ('File','Import','Export','Create','Project').
        The menu item is named `objName' with label `text', when clicked `callback' will be called with no arguments.
        '''
        assert menuName in ('File','Import','Export','Create','Project')

        action= QtWidgets.QAction(self)
        action.setObjectName(objName)
        action.setText(text)
        action.triggered.connect(callback)

        if menuName=='File':
            self.menuFile.insertAction(self.action_Quit,action)
        elif menuName=='Import':
            self.menuImport.addAction(action)
        elif menuName=='Export':
            self.menuExport.addAction(action)
        elif menuName=='Create':
            self.menuCreate.addAction(action)
        elif menuName=='Project':
            self.menu_New_Project.addAction(action)

        return action

    @signalmethod
    def addInterfaceTab(self,name,tab):
        '''Add the widget `tab' to the tab panel in the Scene Elements dock.'''
        tab.setParent(self)
        self.interfaceTab.insertTab(0,tab, '')
        ind=self.interfaceTab.indexOf(tab)
        self.interfaceTab.setTabText(ind, name)

    @signalmethod
    def createDock(self,name,widg,minw=200,minh=200):
        '''Add the widget `widg' to the interface in its own docked subwindow with minimum dimensions (minw,minh).'''
        d = QtWidgets.QDockWidget(self)
        d.setFloating(False)
        d.setWindowTitle(Utils.uniqueStr(name,[w.parent().windowTitle() for w in self.dockWidgets],' '))
        d.setWidget(widg)
        d.setMinimumWidth(minw*2) # initialize the minimum width to twice given so that the dock starts out larger
        d.setMinimumHeight(minh)
        d.setAttribute(Qt.WA_DeleteOnClose, True)

        def closeEvent(e):
            if hasattr(widg,'parentClosed'):
                widg.parentClosed(e)
            self.dockWidgets.remove(widg)
            self.removeDockWidget(d)

        def showEvent(e): # set the minimum size to what's actually wanted when the dock is shown
            d.setMinimumWidth(minw)

        setattr(d,'closeEvent',closeEvent)
        setattr(d,'showEvent',showEvent)

        self.addDockWidget(Qt.DockWidgetArea(2), d)
        self.dockWidgets.append(widg)

    def findWidgetItem(self,obj):
        return Utils.first(t for t,v in self.objMap.items() if v.obj==obj)

    def findPropBox(self,obj):
        return Utils.first(v.propbox for v in self.objMap.values() if v.obj==obj)

    @signalmethod
    def connect(self,signal,slot):
        '''Performs signal connections which must be done within the main UI thread.'''
        signal.connect(slot)

    @signalmethod
    def chooseRGBColorDialog(self,origcolor,callback):
        '''
        Opens a color pick dialog initialized with `origcolor' (RGBA tuple or color object). If Ok is pressed, the
        callable `callback' is invoked with the RGBA color tuple passed as the single argument, otherwise does nothing.
        This is threadsafe and non-blocking.
        '''
        c = QtWidgets.QColorDialog.getColor(toQtColor(origcolor), self)
        #if validQVariantStr(c):
        callback(c.getRgbF())

    @signalmethod
    def chooseYesNoDialog(self,msg,title,callback):
        '''
        Opens a Yes/No dialog box with message string `msg' and title string `title'. If Yes is selected, the callable
        `callback' is called with no arguments. This is threadsafe and non-blocking.
        '''
        reply=QtWidgets.QMessageBox.question(self, title, msg, QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)
        if reply==QtWidgets.QMessageBox.Yes:
            callback()

    @signalmethod
    def getYesNoDialogValue(self,msg,title,future):
        '''
        Opens a Yes/No dialog box with message string `msg' and title string `title'. If Yes is selected, the Future
        object `future' is set to True, otherwise False. This is threadsafe and non-blocking.
        '''
        with future:
            reply=QtWidgets.QMessageBox.question(self, title, msg, QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)
            future.setObject(reply==QtWidgets.QMessageBox.Yes)

    @signalmethod
    def chooseStrDialog(self,title,defaultval,callback):
        '''
        Opens a dialog box asking for an input string with title string `title' and default string value `defaultval'.
        When the dialog closes, the callable `callback' is called with the given string value as the only argument.
        This is threadsafe and non-blocking.
        '''
        text, ok = QtWidgets.QInputDialog.getText(self, 'Input String',title,text=defaultval)
        if ok:
            callback(str(text))

    @signalmethod
    def chooseListItemsDialog(self,title,msg,items,callback,selected=[],multiSelect=False):
        selectmode=QtWidgets.QAbstractItemView.MultiSelection if multiSelect else QtWidgets.QAbstractItemView.SingleSelection 

        d=QtWidgets.QDialog(self)
        d.setWindowTitle(title)
        d.resize(400, Utils.clamp(len(items)*10,200,800))
        d.verticalLayout = QtWidgets.QVBoxLayout(d)
        d.label = QtWidgets.QLabel(d)
        d.label.setText(msg)
        d.verticalLayout.addWidget(d.label)
        d.listWidget = QtWidgets.QListWidget(d)
        d.listWidget.setSelectionMode(selectmode)
        d.listWidget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        d.verticalLayout.addWidget(d.listWidget)

        fillList(d.listWidget,map(str,items))

        for s in selected:
            d.listWidget.item(s).setSelected(True)

        def _getSelected():
            selinds=[]
            for i in d.listWidget.selectedItems():
                selinds.append(d.listWidget.indexFromItem(i).row())

            selinds.sort()
            callback(selinds)
            d.close()

        d.buttonBox = QtWidgets.QDialogButtonBox(d)
        d.buttonBox.setOrientation(Qt.Horizontal)
        d.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Ok)
        d.buttonBox.setCenterButtons(False)
        d.buttonBox.accepted.connect(_getSelected)
        d.verticalLayout.addWidget(d.buttonBox)
        d.exec_()

    @signalmethod
    def chooseScreenshotDialog(self,start,end,fps,steps,sources,callback):
        '''
        Shows the dialog for choosing screenshot parameters and calls `callback' with the results if OK is chosen. The
        first 4 arguments specify the timestep start, end, frames per second, and steps per second. The `sources' value
        is a list of (name,source,width,height) tuples specifying what cameras or widgets are acceptable as sources, the given
        name from each tuple will be the source comboboxentry and (width,height) will be set as the default values for those
        fields. The result arguments for `callback' are: file path, sources, width, height, start time, end time, interval.
        '''
        d=ScreenshotDialog(self,start,end,fps,steps,sources or [('Main Camera',None,self.viz.width(),self.viz.height())])
        d.exec_()
        if d.result:
            callback(*d.result)

    def chooseFileDialog(self,title,opendir=None,filterstr='',isOpen=True,chooseMultiple=False,confirmOverwrite=True,parent=None):
        assert Utils.isMainThread()
        parent=parent or self
        opendir=opendir or self.dialogDir

        if isOpen:
            if chooseMultiple:
                fnames=QtWidgets.QFileDialog.getOpenFileNames(parent, title,opendir, filterstr)
                if QtVersion==5:
                    fnames=fnames[0]
                    
                names=[os.path.abspath(str(f)) for f in fnames]
                if len(names)>0:
                    self.dialogDir=os.path.split(names[0])[0]
                return names
            else:
                fname=QtWidgets.QFileDialog.getOpenFileName(parent, title,opendir, filterstr)
        else:
            options=QtWidgets.QFileDialog.Options()
            if not confirmOverwrite:
                options|=QtWidgets.QFileDialog.DontConfirmOverwrite

            fname=QtWidgets.QFileDialog.getSaveFileName(parent, title,opendir, filterstr,None,options)

        if fname and QtVersion==5: # throw out the filter part that's returned in PyQt5
            fname=fname[0]
            
        name=str(fname)
        if name:
            self.dialogDir=os.path.dirname(os.path.abspath(name))

        return name

    def chooseDirDialog(self,title,opendir=None):
        assert Utils.isMainThread()

        opendir=opendir or self.dialogDir

        dirname=str(QtWidgets.QFileDialog.getExistingDirectory(self,title,opendir))
        if dirname:
            dirname=os.path.abspath(dirname)
            self.dialogDir=os.path.split(dirname)[0]

        return dirname

    @signalmethod
    def showLogfileView(self,logfile):
        self.logfileView=self.logfileView or LogFileView(logfile,self)
        self.logfileView.show()

    @signalmethod
    def showMsg(self,msg,title='Message',text=None,width=600,height=300):
        '''
        Shows the string `msg' in a message dialog with the given title. If `text' is not None, this is displayed in
        a text box within a message dialog that recalls previous messages, otherwise a simple dialog is used.
        '''
        if text==None:
            box=QtWidgets.QMessageBox(self)
            box.setText(msg)
            box.setWindowTitle(title)
            box.show()
        else:
            self.msgdialog.addMsg(title,msg,str(text),width,height)

    @signalmethod
    def showTextBox(self,msg,title,text,width=600,height=300):
        '''Shows a box with the given title displaying the mssage `msg' with text content `text'.'''
        box=TextBoxDialog(title,msg,text,self,width,height)
        box.show()

    def _addUIObj(self,treeItem,*args,**kwargs):
        args=list(args)+[None]*(len(self.ObjMapTuple._fields)-len(args)) # substitute None for any missing arguments
        self.objMap[treeItem]=self.ObjMapTuple(*args,**kwargs)

    @signalmethod
    def addTreeObject(self,obj,label,parentObj,prop,updateFunc,dblClickFunc=None,menu=None,menuFunc=None,icon=None,parentName=None):
        icon=icon or IconName.Default

        if parentObj:
            parentItem=self.findWidgetItem(parentObj)
            parentItem.setExpanded(True)
        elif parentName:
            parentItem=Utils.first(self.treeWidget.findItems(parentName,Qt.MatchExactly|Qt.MatchRecursive))
            if not parentItem:
                parentItem=QtWidgets.QTreeWidgetItem(self.treeWidget)
                parentItem.setText(0,parentName)
                parentItem.setExpanded(True)
        else:
            parentItem=self.treeWidget

        treeItem= QtWidgets.QTreeWidgetItem(parentItem)
        treeItem.setText(0,label)
        treeItem.setIcon(0,QtGui.QIcon(icon))

        self._addUIObj(treeItem,obj,prop,None,updateFunc,dblClickFunc,menu,menuFunc)

    @signalmethod
    def updateTreeObjects(self):
        for item,omt in self.objMap.items():
            obj=omt.obj
            try: # TODO: fix this, don't update things that don't have names or labels
                try:
                    text=obj.getLabel()
                except:
                    text=obj.getName()

                item.setText(0,text)
            except:
                pass

    @signalmethod
    def addProjectObj(self,proj,name,prop,updateFunc):
        treeItem= QtWidgets.QTreeWidgetItem(None)
        treeItem.setText(0,name)
        self._addUIObj(treeItem,proj,prop,None,updateFunc)

        self.treeWidget.insertTopLevelItem(0,treeItem)

    @signalmethod
    def addAsset(self,asset,text,assettype,propbox=None,updateFunc=None):
        li=QtWidgets.QTreeWidgetItem(self.assetRootMap[assettype])
        li.setText(0,text)
        self.assetRootMap[assettype].setExpanded(True)
        self._addUIObj(li,asset,propbox,assettype,updateFunc)

    @signalmethod
    def addMaterial(self,mat,updateFunc):
        self.addAsset(mat,mat.getName(),AssetType._mat,MaterialPropertyWidget(),updateFunc)

    @signalmethod
    def addSpectrum(self,spec):
#       prop=QtWidgets.QWidget()
#       prop.groupBox=QtWidgets.QGroupBox(prop)
#       prop.groupBox.setTitle('Spectrum')
#       prop.groupBox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
#       prop.gridLayout = QtWidgets.QGridLayout(prop.groupBox)

        prop=QtWidgets.QGroupBox()
        prop.setTitle('Spectrum')
        prop.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
        prop.gridLayout = QtWidgets.QGridLayout(prop)

        self.addAsset(spec,spec.getName(),AssetType._spec,prop)

    @signalmethod
    def addTexture(self,tex):
        self.addAsset(tex,tex.getName(),AssetType._tex)

    @signalmethod
    def addLight(self,light,updateFunc):
        self.addAsset(light,light.getName(),AssetType._light,LightPropertyWidget(),updateFunc)

    @signalmethod
    def addGPUProgram(self,prog,updateFunc):
        self.addAsset(prog,prog.getName(),AssetType._gpuprog,GPUProgramPropertyWidget(),updateFunc)

    @signalmethod
    def fillTextureList(self,textures):
        self.texList.clear()
        for tex in textures:
            li=QtWidgets.QListWidgetItem(self.texList)
            li.setText(tex)

    def getSelectedObject(self):
        item=self.treeWidget.currentItem()
        return self.objMap.get(item,[None])[0]

    def getSelectedAsset(self):
        item=self.assetList.currentItem()
        return self.objMap.get(item,[None])[0]

    @signalmethod
    def removeObject(self,obj):
        item=self.findWidgetItem(obj)
        if item:
            maptuple=self.objMap.pop(item)

            if self.assetList.currentItem()==item:
                self.assetScrollArea.takeWidget()
                self.assetList.setCurrentItem(item.parent())

            cppdel(item)
            cppdel(maptuple.propbox)

    @signalmethod
    def setVisibilityIcon(self,obj,val):
        item=self.findWidgetItem(obj)
        item.setIcon(0,QtGui.QIcon(IconName.Eye if val else IconName.EyeClosed))

