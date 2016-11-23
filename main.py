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


import eidolon
import multiprocessing

# necessary for now to include plugins here for multiprocessing
import plugins.CheartPlugin
import plugins.DicomPlugin
import plugins.NiftiPlugin
import plugins.MetaImagePlugin
import plugins.VTKPlugin
import plugins.MeditPlugin
import plugins.STLPlugin
import plugins.NRRDPlugin
import plugins.ParRecPlugin
import plugins.ImageStackPlugin
import plugins.SlicePlugin
import plugins.PlotPlugin
import plugins.SegmentPlugin
import plugins.ReportCardPlugin
import plugins.MeasurementPlugin
import plugins.CardiacMotionPlugin
import plugins.ImageAlignPlugin

if __name__ == '__main__': # needed for Windows multiprocessing (unless you want fork bombs)
	multiprocessing.freeze_support()
	eidolon.defaultMain()

