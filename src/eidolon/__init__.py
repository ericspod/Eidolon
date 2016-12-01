# Eidolon Biomedical Framework
# Copyright (C) 2016 Eric Kerfoot, King's College London, all rights reserved
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
Eidolon is the experimental medical imaging visualization framework.
'''

from renderer.Renderer import *
from eidolon.VisualizerUI import *
from eidolon.Utils import *
from eidolon.Concurrency import *
from eidolon.SceneUtils import *
from eidolon.MeshAlgorithms import *
from eidolon.ImageObject import *
from eidolon.MathDef import *
from eidolon.SceneManager import *
from eidolon.SceneObject import *
from eidolon.ScenePlugin import *
from eidolon.Application import *

__appname__='Eidolon Biomedical Framework'
__version_info__=(0,1,99) # global application version, major/minor/patch
__version__='%i.%i.%i'%__version_info__
__author__='Eric Kerfoot'
__copyright__="Copyright (c) 2016 Eric Kerfoot, King's College London, all rights reserved. Licensed under the GPL (see LICENSE.txt)."
__website__="https://github.com/ericspod/Eidolon"

APPDIRVAR='APPDIR' # environment variable defining the application's directory, set by the start up script and is needed at init time
LIBSDIR='EidolonLibs' # directory name containing the application's libraries
CONFIGFILE='config.ini' # config file name

