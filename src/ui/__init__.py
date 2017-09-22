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

#from .MainWindow import Ui_MainWindow
#from .ProjProp import Ui_ProjProp
#from .ObjReprProp import Ui_ObjReprProp
#from .ObjProp import Ui_ObjProp
#from .MatProp import Ui_matProp
#from .LightProp import Ui_LightProp
#from .GPUProp import Ui_gpuProp
#from .Draw2DView import Ui_Draw2DView
#from .ScreenshotForm import Ui_ScreenshotForm
#from .ShowMsg import Ui_ShowMsg
#from .Measure2DView import Ui_Measure2DView
#from .MeasureObjProp import Ui_MeasureObjProp
#from CardiacMotionProp import Ui_CardiacMotionProp
#from cheartload import Ui_ObjDialog
#from cheartdataload import Ui_DataDialog
#from chearttdload import Ui_TDDialog
#from CTMotionProp import Ui_CTMotionProp
#from SeriesProp import Ui_SeriesProp
#from ChooseSeries import Ui_ChooseSeriesDialog
#from Dicom2DView import Ui_Dicom2DView
#from ChooseImgStack import Ui_OpenImgStackDialog
#from mtServerForm import Ui_mtServerForm
#from RegionGraphWidget import Ui_RegionGraphWidget
#from Seg2DView import Ui_Seg2DView
#from SegObjProp import Ui_SegObjProp
#from SliceObjProp import Ui_SliceObjProp

import sys
import os
import glob
import re

import Resources_rc

module=sys.modules[__name__]

try:
    restag=re.compile('<resources>.*</resources>',flags=re.DOTALL)
    uifiles=glob.glob(os.path.join(os.path.dirname(__file__),'*.ui'))
    if len(uifiles)==0:
        raise IOError('No .ui files')
        
    try: # PyQt4 and 5 support
        from PyQt5 import uic
    except ImportError:
        from PyQt4 import uic
        
    try: # Python 2 and 3 support
        from StringIO import StringIO
    except ImportError:
        from io import StringIO
        
    for ui in uifiles:
        s=bytes(open(ui).read())#.decode('utf-8')
        s=re.sub(restag,'',s) # get rid of the resources section in the XML
        uiclass,_=uic.loadUiType(StringIO(s)) # create a local type definition
        setattr(module,uiclass.__name__,uiclass)
        
except Exception as e:
    raise

