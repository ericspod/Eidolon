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


import eidolon
import multiprocessing

#eidolon.configEnviron() # configure environment variables before attempting to load plugins

# necessary for now to include plugins here for multiprocessing
import eidolon.plugins.X4DFPlugin
import eidolon.plugins.CheartPlugin
import eidolon.plugins.DicomPlugin
import eidolon.plugins.NiftiPlugin
import eidolon.plugins.MetaImagePlugin
import eidolon.plugins.VTKPlugin
import eidolon.plugins.MeditPlugin
import eidolon.plugins.STLPlugin
import eidolon.plugins.NRRDPlugin
import eidolon.plugins.ParRecPlugin
import eidolon.plugins.ImageStackPlugin
import eidolon.plugins.SlicePlugin
import eidolon.plugins.PlotPlugin
import eidolon.plugins.SegmentPlugin
import eidolon.plugins.ReportCardPlugin
import eidolon.plugins.MeasurementPlugin
import eidolon.plugins.CardiacMotionPlugin
import eidolon.plugins.ImageAlignPlugin
#import eidolon.plugins.CTMotionTrackPlugin
import eidolon.plugins.DeformPlugin

if __name__ == '__main__': # needed for Windows multiprocessing (unless you want fork bombs)
    multiprocessing.freeze_support()
    eidolon.defaultMain()

