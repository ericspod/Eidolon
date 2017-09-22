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


from eidolon import *
from ui import Ui_OpenImgStackDialog


class ChooseImgStackDialog(QtWidgets.QDialog,Ui_OpenImgStackDialog):
    def __init__(self, plugin,parent=None):
        QtWidgets.QDialog.__init__(self,parent)
        self.setupUi(self)
        self.plugin=plugin
        self.filenames=[]
        
        self.nameEdit.setText(uniqueStr('ImgStack',[o.name for o in self.plugin.mgr.objs]))

        self.chooseDirButton.clicked.connect(self._chooseDir)
        self.dirEdit.textChanged.connect(self._updateFileList)
        self.regexEdit.textChanged.connect(self._updateFileList)
        self.reverseCheck.clicked.connect(self._updateFileList)
        self.colBox.valueChanged.connect(self._updateFileList)
        
    def _chooseDir(self):
        dirpath=self.plugin.win.chooseDirDialog('Choose Image Stack Directory')
        if dirpath!='':
            self.dirEdit.setText(os.path.abspath(dirpath))
            
    def _updateFileList(self):
        dirtext=str(self.dirEdit.text()) or '.'
        globtext=str(self.regexEdit.text())     
        globpath=os.path.join(os.path.abspath(dirtext),globtext)
        
        self.filenames=glob.glob(globpath)
        
        sortednames=sortFilenameList(self.filenames,self.colBox.value())
        if sortednames:
            self.filenames=sortednames
        
        if self.reverseCheck.isChecked():
            self.filenames.reverse()
        
        fillList(self.fileList,[os.path.relpath(f,dirtext) for f in self.filenames])
        
        
class ImageStackPlugin(ImageScenePlugin):
    def __init__(self):
        ImageScenePlugin.__init__(self,'ImgStack')
        
    def init(self,plugid,win,mgr):
        ImageScenePlugin.init(self,plugid,win,mgr)
        if win:
            win.addMenuItem('Import','ImgStackLoad'+str(plugid),'&Image Stack Directory',self._openDirDialog)
            
    def loadObject(self,filename,name=None,**kwargs):
        filenames=kwargs.pop('filenames',[filename])
        name=name or splitPathExt(filename)[1]
        return self.loadImageStackObject(name,filenames,**kwargs)

    def loadImageStackObject(self,name,filenames,pos=vec3(),rot=rotator(),spacing=(1.0,1.0),imgsep=1.0,sortIndex=None,regex=None,reverse=False,task=None):
        '''
        Loads a stack of images (or a sequence of stacks), ordered bottom up, into a ImageSceneObject. If
        `sortIndex' is not None, this is the sorting index in the file names used to sort the stack. The start
        position `pos' is intepreted as the top left position of the bottom-most image. If `filenames' is a list
        of filenames only, the series is not timed, however if it's a list of lists of filenames then each sublist
        is (optionally) sorted and then loaded into a time series object.
        '''

        isTimed=isIterable(filenames[0]) and not isinstance(filenames[0],str)

        if isTimed:
            if sortIndex!=None:
                filenames=[sortFilenameList(fn,sortIndex,regex) for fn in filenames]

            if reverse:
                for f in filenames:
                    f.reverse()

            positions=[pos+(rot*vec3(0,0,imgsep*i)) for i in range(len(filenames[0]))]

            imagesteps=[loadImageStack(fn,self.mgr.scene.loadImageFile,positions,rot,spacing,task) for fn in filenames]

            for i,imgs in enumerate(imagesteps):
                for img in imgs:
                    img.timestep=i

            images=listSum(imagesteps)
            filenames=listSum(filenames)
        else:
            if sortIndex!=None:
                filenames=sortFilenameList(filenames,sortIndex,regex)

            if reverse:
                filenames.reverse()

            positions=[pos+(rot*vec3(0,0,imgsep*i)) for i in range(len(filenames))]

            images=loadImageStack(filenames,self.mgr.scene.loadImageFile,positions,rot,spacing,task)

        return self.createSceneObject(name,images,filenames,isTimed)
            
    def _openDirDialog(self):
        @taskroutine('Loading Image Stack')
        def _loadStack(name,filenames,task=None):
            obj=self.loadImageStackObject(name,filenames,task=task)
            centerImagesLocalSpace(obj)
            self.mgr.addSceneObject(obj)
        
        d=ChooseImgStackDialog(self,self.win)
        result=d.exec_()
        if result==1:
            name=uniqueStr(str(d.nameEdit.text()),[o.getName() for o in self.mgr.objs])
            self.mgr.runTasks([_loadStack(name,d.filenames)])
        
        
addPlugin(ImageStackPlugin())
