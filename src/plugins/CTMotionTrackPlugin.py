
from visualizer import *
from plugins.IRTKPlugin import IRTKPluginMixin
from plugins.VTKPlugin import DatasetTypes,VTKProps
from plugins.SegmentPlugin import SegmentTypes,SegSceneObject,DatafileParams
from ui import Ui_CTMotionProp


class CTmotionProjPropWidget(QtWidgets.QWidget,Ui_CTMotionProp):
    def __init__(self,parent=None):
        QtWidgets.QWidget.__init__(self,parent)
        self.setupUi(self)


# names of config values to store in the project's .ini file
#ConfigNames=enum('ctImageStack','paramfile','lvtop','apex','rvtop','rvAtop','rvPtop','resampleStack')
ConfigNames=enum('paramfile')

class CTMotionTrackProject(Project):
    def __init__(self,name,parentdir,mgr):
        Project.__init__(self,name,parentdir,mgr)
        self.addHandlers()
        self.Measure=mgr.getPlugin('Measure')
        self.CTMotion=mgr.getPlugin('CTMotion')
        self.Dicom=mgr.getPlugin('Dicom')
        self.CTMotion.project=self
        self.header='\nCTMotion.createProject(%r,scriptdir+"/..")\n' %(self.name)
        self.logdir=self.getProjectFile('logs')
        self.backDir=self.logdir

        for n in ConfigNames:
            self.configMap[n[0]]=''

    @taskmethod('Adding Object to Project')
    def checkIncludeObject(self,obj,task=None):

        # Only try to save objects that aren't already in the project and which are saveable
        # Important: this task method will be called after the project has loaded so won't ask to add things already in the project
        if not isinstance(obj,SceneObject) or obj in self.memberObjs or obj.plugin.getObjFiles(obj) is None:
            return

        def _copy():
            pdir=self.getProjectDir()
            files=map(os.path.abspath,obj.plugin.getObjFiles(obj) or [])

            if not files or any(not f.startswith(pdir) for f in files):
                newname=self.CTMotion.getUniqueObjName(obj.getName())
                self.mgr.renameSceneObject(obj,newname)
                filename=self.getProjectFile(obj.getName())

                if isinstance(obj,ImageSceneObject):
                    self.CTMotion.saveToNifti([obj],True)
                elif isinstance(obj,MeshSceneObject):
                    self.CTMotion.VTK.saveObject(obj,filename,setFilenames=True)
                else:
                    obj.plugin.saveObject(obj,filename,setFilenames=True)

            Project.addObject(self,obj)
            self.save()

        msg="Do you want to add %r to the project?\nThis requires saving/copying the object's file data into the project directory."%(obj.getName())
        self.mgr.win.chooseYesNoDialog(msg,'Adding Object',_copy)

    def getPropBox(self):
        prop=Project.getPropBox(self)

        # remove the UI for changing the project location
        cppdel(prop.chooseLocLayout)
        cppdel(prop.dirButton)
        cppdel(prop.chooseLocLabel)

        self.ctprop=CTmotionProjPropWidget()
        prop.verticalLayout.insertWidget(prop.verticalLayout.count()-1,self.ctprop)

        self.ctprop.ctDicomButton.clicked.connect(self._loadCTButton)
        self.ctprop.niftiButton.clicked.connect(self._loadNiftiButton)
        self.ctprop.chooseParamButton.clicked.connect(self._chooseParamFile)
        self.ctprop.trackButton.clicked.connect(self._trackButton)
        self.ctprop.applyTrackButton.clicked.connect(self._applyTrack)
        self.ctprop.isoCreateButton.clicked.connect(self._createIsoImage)

        self.ctprop.paramEdit.textChanged.connect(self.updateConfigFromProp)

        if not os.path.isdir(self.logdir):
            os.mkdir(self.logdir)

        return prop

    def updateConfigFromProp(self,*args):
        param=str(self.ctprop.paramEdit.text())
#       if not param:
#           param=self.CTMotion.tsffd
#           self.ctprop.paramEdit.setText(self.CTMotion.tsffd)

        if os.path.isfile(param):
            self.configMap[ConfigNames._paramfile]=param

    def updatePropBox(self,proj,prop):
        Project.updatePropBox(self,proj,prop)

        self.ctprop.paramEdit.setText(self.configMap[ConfigNames._paramfile])

        sceneimgs=filter(lambda o:isinstance(o,ImageSceneObject),self.memberObjs)
        scenemeshes=filter(lambda o:isinstance(o,MeshSceneObject),self.memberObjs)

        names=sorted(o.getName() for o in sceneimgs)
        fillList(self.ctprop.isoCreateBox,names)
        fillList(self.ctprop.trackImgBox,names)
        fillList(self.ctprop.trackMaskBox,names,defaultitem='None')

        names=sorted(o.getName() for o in scenemeshes)
        fillList(self.ctprop.trackObjBox,names)

        trackdirs=map(os.path.basename,self.CTMotion.getTrackingDirs())
        fillList(self.ctprop.trackDataBox,sorted(trackdirs))

        # refill the measurement plugin's known tracking sources
        self.Measure.removeTrackSource(self.CTMotion.applyMotionTrackPoints)
        for td in trackdirs:
            self.Measure.addTrackSource(td,self.CTMotion.applyMotionTrackPoints)

    def renameObject(self,obj,oldname):
        newname=getValidFilename(obj.getName())
        obj.setName(newname)

        conflicts=obj.plugin.checkFileOverwrite(obj,self.getProjectDir())
        if conflicts:
            raise IOError('Renaming object would overwrite the following project files: '+', '.join(map(os.path.basename,conflicts)))

        obj.plugin.renameObjFiles(obj,oldname)

        for n,v in self.checkboxMap.items():
            if v==oldname:
                self.checkboxMap[n]=newname

        for n,v in self.configMap.items():
            if v==oldname:
                self.configMap[n]=newname

        self.save()

    def _loadCTButton(self):
        @taskroutine('Loading Objects')
        def _loadObj(f,task):
            obj=Future.get(f)
            if obj:
                filenames=self.CTMotion.saveToNifti([obj])
                self.CTMotion.loadNiftiFiles(filenames)

        series=self.Dicom.showChooseSeriesDialog(subject='CT Series')
        if len(series)>0:
            f=self.Dicom.showTimeMultiSeriesDialog(series)
            self.mgr.checkFutureResult(f)
            self.mgr.runTasks(_loadObj(f))

    def _loadNiftiButton(self):
        filenames=self.mgr.win.chooseFileDialog('Choose NIfTI filename',filterstr='NIfTI Files (*.nii *.nii.gz)',chooseMultiple=True)
        if len(filenames)>0:
            self.CTMotion.loadNiftiFiles(filenames)

    def _chooseParamFile(self):
        filename=self.mgr.win.chooseFileDialog('Choose Parameter file')
        if filename:
            if not os.path.isfile(filename):
                self.mgr.showMsg('Cannot find file %r'%filename,'No Parameter File')
            else:
                self.ctprop.paramEdit.setText(filename)
                self.configMap[ConfigNames._paramfile]=filename
                self.saveConfig()

    def _trackButton(self):
        name=str(self.ctprop.trackImgBox.currentText())
        mask=str(self.ctprop.trackMaskBox.currentText())
        paramfile=str(self.ctprop.paramEdit.text())
        trackname=str(self.ctprop.trackName.text())
        onefile=self.ctprop.oneFileCheck.isChecked()

        f=self.CTMotion.startRegisterMotionTrack(name,mask,trackname,paramfile,None,onefile)
        self.mgr.checkFutureResult(f)

    def _applyTrack(self):
        name=str(self.ctprop.trackObjBox.currentText())
        trackname=str(self.ctprop.trackDataBox.currentText())
        f=self.CTMotion.applyMotionTrack(name,trackname)
        self.mgr.checkFutureResult(f)

    def _createIsoImage(self):
        name=str(self.ctprop.isoCreateBox.currentText())
        cropEmpty=self.ctprop.emptyCropBox.isChecked()
        f=self.CTMotion.createIsotropicObject(name,cropEmpty)
        self.mgr.checkFutureResult(f)


class CTMotionTrackPlugin(ImageScenePlugin,IRTKPluginMixin):
    def __init__(self):
        ImageScenePlugin.__init__(self,'CTMotion')
        self.project=None

    def init(self,plugid,win,mgr):
        ImageScenePlugin.init(self,plugid,win,mgr)
        IRTKPluginMixin.init(self,plugid,win,mgr)

        self.Segment=self.mgr.getPlugin('Segment')

        if self.win!=None:
            self.win.addMenuItem('Project','CTMotionTrackProj'+str(plugid),'&CT Motion Track Project',self._newProjDialog)

    def createProject(self,name,parentdir):
        if self.mgr.project==None:
            self.mgr.createProjectObj(name,parentdir,CTMotionTrackProject)

    def _newProjDialog(self):
        def chooseProjDir(name):
            newdir=self.win.chooseDirDialog('Choose Project Root Directory')
            if len(newdir)>0:
                self.mgr.createProjectObj(name,newdir,CTMotionTrackProject)

        self.win.chooseStrDialog('Choose Project Name','Project',chooseProjDir)

    def getCWD(self):
        return self.project.getProjectDir()

    def getLogFile(self,filename):
        return os.path.join(self.project.logdir,ensureExt(filename,'.log'))

    def getLocalFile(self,name):
        return self.project.getProjectFile(name)

    def addObject(self,obj):
        if obj not in self.mgr.objs:
            self.mgr.addSceneObject(obj)
        self.project.addObject(obj)
        self.project.save()

    @taskmethod('Load Nifti Files')
    def loadNiftiFiles(self,filenames,task=None):
        isEmpty=len(self.project.memberObjs)==0
        objs=IRTKPluginMixin.loadNiftiFiles(self,filenames)

        if isEmpty:
            self.mgr.callThreadSafe(self.project.updateConfigFromProp)
            self.project.save()

        return objs


addPlugin(CTMotionTrackPlugin())
