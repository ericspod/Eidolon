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

# necessary for now to include plugins here for multiprocessing
import CheartPlugin
import DicomPlugin
import NiftiPlugin
import MetaImagePlugin
import VTKPlugin
import MeditPlugin
import STLPlugin
import NRRDPlugin
import ParRecPlugin
import ImageStackPlugin
import SlicePlugin
import PlotPlugin
import SegmentPlugin
import ReportCardPlugin
import MeasurementPlugin


if __name__ == '__main__': # needed for Windows multiprocessing (unless you want fork bombs)
	eidolon.defaultMain()

