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


import subprocess
import glob
import os

from __init__ import QtVersion

def generateResFile():
    '''Generates the resource file from the resources in ../../res and stores it in a PyQt version specific file.'''
    cmd='pyrcc%(ver)i ../../res/Resources.qrc > Resources_rc%(ver)i.py'
    subprocess.check_call(cmd%{'ver':QtVersion}, shell=True)


def generateUIFile():
    '''Generate a PyQt version specific resource file containing the .ui layout files.'''
    uifiles=glob.glob(os.path.join(os.path.dirname(__file__),'*.ui'))
    if uifiles:
        # write out a temporary resource spec file
        with open('ui.qrc','w') as o:
            o.write('<RCC>\n<qresource prefix="layout">\n')
            for ui in uifiles:
                o.write('<file>%s</file>'%os.path.basename(ui))
            o.write('</qresource>\n</RCC>\n')
            
        cmd='pyrcc%(ver)i ui.qrc > UI_rc%(ver)i.py'
        subprocess.check_call(cmd%{'ver':QtVersion}, shell=True)
        os.remove('ui.qrc')
    
    
if __name__=='__main__':
    print('Generating Resource Module')
    generateResFile()
    print('Generating UI Module')
    generateUIFile()
    