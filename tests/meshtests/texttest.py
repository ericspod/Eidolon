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

from eidolon import FT_TEXT, H_CENTER

@mgr.callThreadSafe
def _fig():
    fig=mgr.scene.createFigure('text','Default',FT_TEXT)
    fig.setText('If you can read this, the test passes')
    fig.setHAlign(H_CENTER)
    fig.setVisible(True)
    return fig # need to return fig so that it's stored as _fig, otherwise it will get collected
    
   
mgr.controller.setZoom(15)
mgr.repaint()
