# Eidolon Biomedical Framework
# Copyright (C) 2016-20 Eric Kerfoot, King's College London, all rights reserved
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

from setuptools import setup, find_packages
import os
import sys

from PyQt5.pyrcc_main import processResourceFile

from eidolon import __appname__, __version__, __author__

scriptdir = os.path.dirname(os.path.abspath(__file__))  # path of the current file

long_description = """
Eidolon is the experimental medical imaging visualization framework.
"""

if "generate" in sys.argv:  # generate only, quit at this point before setup
    # generate resource file for PyQt4 or 5
    processResourceFile([scriptdir + "/res/Resources.qrc"], scriptdir + "/eidolon/ui/resources_rc.py", False)
else:
    setup(
        name=__appname__,
        version=__version__,
        packages=find_packages(exclude=("res", "tests")),
        author=__author__,
        author_email="eric.kerfoot@kcl.ac.uk",
        url="http://github.com/ericspod/Eidolon",
        license="GPLv3",
        description='Experimental medical imaging visualization framework.',
        keywords="dicom python medical imaging pydicom pyqtgraph nibabel visualisation",
        long_description=long_description.strip(),
        # entry_points={'console_scripts': ['DicomBrowser = DicomBrowser:mainargv']},
        # install_requires=['pyqtgraph', 'pydicom', 'pyqt']
    )
