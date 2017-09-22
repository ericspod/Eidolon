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


import os, weakref
from eidolon import *


class ReportCardSceneObject(SceneObject):
    def __init__(self,name,filename,plugin,datamat=[],**kwargs):
        SceneObject.__init__(self,name,plugin,**kwargs)
        self.filename=filename
        self.datamat=list(datamat) # list of (object,name,value) triples
        
    def getPropTuples(self):
        proptuples=[('Filename',str(self.filename))]
        return proptuples
        
    def setValue(self,obj,name,value):
        objname=getattr(obj,'getName',lambda:str(obj))()
        index=first(i for i,(o,n,_) in enumerate(self.datamat) if (objname,name)==(o,n))
        
        if index!=None:
            self.datamat[index]=(objname,name,value)
        else:
            self.datamat.append((objname,name,value))
        
    def load(self):
        if self.filename:
            datamap=sorted(readBasicConfig(self.filename).items())
            self.datamat=[line for _,line in datamap]
        
    def save(self):
        if self.filename:
            datamap={}
            for i,line in enumerate(self.datamat):
                datamap['line%.4i'%i]=line
                
            storeBasicConfig(self.filename,datamap)
            
    def __repr__(self):
        return '<Report Card %r, %r>'%(self.name,self.filename)
            
            
class TagTableModel(QtCore.QAbstractTableModel):
    def __init__(self,report,parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        self.columns=('Source Object','Name','Value')
        self.report=weakref.ref(report)
#       self.sortCol=0
#       self.sortOrder=Qt.AscendingOrder
        
    def setReportCard(self,report):
        self.layoutAboutToBeChanged.emit()
        self.report=report
        self.layoutChanged.emit()
        
    def rowCount(self, parent):
        return len(self.report().datamat) if self.report() else 0
        
    def columnCount(self,parent):
        return len(self.columns)
        
#   def sort(self,column,order):
#       self.sortCol=column
#       self.sortOrder=order
#       self.resort()
#       
#   def resort(self):
#       self.layoutAboutToBeChanged.emit()
#       self.tagList.sort(key=itemgetter(self.sortCol),reverse=self.sortOrder==Qt.DescendingOrder)
#       self.layoutChanged.emit()
        
    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation==Qt.Horizontal:
            return self.columns[section]
            
    def data(self, index, role):
        if index.isValid() and role == Qt.DisplayRole:
            return str(self.report().datamat[index.row()][index.column()])
            
#   def flags(self,index):
#       '''Allows editability.'''
#       return Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable
#       
#   def setData(self, index, value,role):
#       '''Allows a cell to be edited.'''
#       if index.isValid() and role == Qt.EditRole:
#           row=self.report().datamat[index.row()]          
#           value=str(value.toString())
#           
#           try:
#               value=eval(value) # attemp to evaluate the value, store as string if it's something weird
#           except:
#               pass
#           
#           self.report().datamat[index.row()]=tuple(r if i!=index.column() else value for i,r in enumerate(row))
#       
#       return True
            
            
class ReportCardPlugin(ScenePlugin):
    def __init__(self):
        ScenePlugin.__init__(self,'ReportCard')
        
    def init(self,plugid,win,mgr):
        ScenePlugin.init(self,plugid,win,mgr)
        
        if win:
            win.addMenuItem('Import','CardLoad'+str(plugid),'&Report Card File',self._openFileDialog)
            
        # read command line argument, loading files as requested, note these tasks are queued at module load time
        if mgr.conf.hasValue('args','--card'):
            @taskroutine('Loading Report Card File')
            def _loadTask(filenames,task=None):
                for f in filenames:
                    obj=self.loadObject(f)
                    self.mgr.addSceneObject(obj)
            
            self.mgr.runTasks(_loadTask(mgr.conf.get('args','--card').split(',')))
            
    def getIcon(self,obj):
        return IconName.Clipboard
        
    def getMenu(self,obj):
        return [obj.getName(),'Show Card'],self.objectMenuItem
        
    def objectMenuItem(self,obj,item):
        if item=='Show Card':
            self.mgr.showMsg('Not yet.')
            self.mgr.addFuncTask(lambda:obj.createRepr(None))
        
    def acceptFile(self,filename):
        return splitPathExt(filename)[2].lower() == '.report'
        
    def checkFileOverwrite(self,obj,dirpath,name=None):
        outfile=os.path.join(dirpath,name or obj.getName())+'.report'
        if os.path.exists(outfile):
            return [outfile]
        else:
            return []
            
    def renameObjFiles(self,obj,oldname,overwrite=False):
        assert isinstance(obj,SceneObject) and obj.plugin==self
        if os.path.isfile(obj.filename):
            obj.filename=renameFile(obj.filename,obj.getName(),overwriteFile=overwrite)
        
    def getObjFiles(self,obj):
        return [obj.filename] if obj.filename else []
        
    def copyObjFiles(self,obj,sdir,overwrite=False):
        newfilename=os.path.join(sdir,os.path.basename(obj.filename))
        if not overwrite and os.path.exists(newfilename):
            raise IOError('File already exists: %r'%newfilename)
            
        obj.filename=newfilename
        obj.save()
        
    def createObjPropBox(self,obj):
        prop=ScenePlugin.createObjPropBox(self,obj)
        
        prop.reportmodel=TagTableModel(obj)
        prop.reportview=QtGui.QTableView(prop)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(prop.reportview.sizePolicy().hasHeightForWidth())
        prop.reportview.setSizePolicy(sizePolicy)
        prop.reportview.setMinimumSize(QtCore.QSize(50, 0))
        prop.reportview.setSelectionMode(QtGui.QAbstractItemView.NoSelection)
        prop.reportview.setSelectionBehavior(QtGui.QAbstractItemView.SelectItems)
        prop.reportview.setShowGrid(False)
        prop.reportview.setSortingEnabled(False)
        prop.reportview.horizontalHeader().setCascadingSectionResizes(True)
        prop.reportview.horizontalHeader().setDefaultSectionSize(120)
        prop.reportview.horizontalHeader().setHighlightSections(False)
        prop.reportview.horizontalHeader().setSortIndicatorShown(False)
        prop.reportview.horizontalHeader().setStretchLastSection(True)
        prop.reportview.verticalHeader().setVisible(False)
        prop.reportview.verticalHeader().setCascadingSectionResizes(True)
        prop.reportview.verticalHeader().setHighlightSections(False)
        prop.reportview.setModel(prop.reportmodel)
        prop.verticalLayout.insertWidget(2,prop.reportview)
        prop.verticalLayout.removeItem(prop.verticalLayout.itemAt(3))
        
#       prop.saveButton=QtGui.QPushButton('Save Edits',prop)
#       prop.verticalLayout.insertWidget(3,prop.saveButton)
#       prop.saveButton.clicked.connect(obj.save)
        
        return prop
        
    def updateObjPropBox(self,obj,prop):
        ScenePlugin.updateObjPropBox(self,obj,prop)
        prop.reportmodel.layoutChanged.emit()
        
    def getScriptCode(self,obj,**kwargs):
        configSection=kwargs.get('configSection',False)
        namemap=kwargs.get('namemap',{})
        convertpath=kwargs['convertPath']
        script=''
        args={'varname':namemap[obj], 'objname':obj.name}
        
        if not configSection:
            args['filename']=convertpath(obj.filename)
            script+='%(varname)s = ReportCard.loadObject(%(filename)s,%(objname)r)\n'
            
        return setStrIndent(script % args).strip()+'\n'
        
    def createReportCard(self,name,filename,datamat=[]):
        name=self.mgr.getUniqueObjName(getValidFilename(name))
        
        return ReportCardSceneObject(name,ensureExt(filename,'.report',True),self,datamat)
        
    def loadObject(self,filename,name=None,**kwargs):
        name=name or os.path.splitext(os.path.basename(filename))[0]
        obj=ReportCardSceneObject(name,filename,self)
        obj.load()
        return obj
            
    def _openFileDialog(self):
        filename=self.mgr.win.chooseFileDialog('Choose Report Card filename',filterstr='Report Card Files (*.report)')
        if filename!='':
            self.mgr.addFuncTask(lambda:self.mgr.addSceneObject(self.loadObject(filename)),'Importing Report Card File')
        
        
addPlugin(ReportCardPlugin())
            