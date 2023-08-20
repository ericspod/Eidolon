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
"""
Eidolon is the experimental medical imaging visualization framework.
"""


__appname__ = "Eidolon Biomedical Framework"
__version_info__ = (0, 6, 99)  # global version, major/minor/patch, patch value 99 means development code from repo
__version__ = "%i.%i.%i" % __version_info__
__author__ = "Eric Kerfoot"
__copyright__ = "Copyright (c) 2016-20 Eric Kerfoot, King's College London, all rights reserved. Licensed under the GPL (see LICENSE.txt)."
__website__ = "https://ericspod.github.io/Eidolon"
__verurl__ = "https://api.github.com/repos/ericspod/Eidolon/releases"

if __name__ == "__main__":
    print("Eidolon version:", __version__)
