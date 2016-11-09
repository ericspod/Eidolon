# Eidolon
Eidolon biomedical visualization and analysis framework.

## Installation

See INSTALLATION.md for details on how to run Eidolon. The code includes precompiled libraries and executables so compilation shouldn't be necessary unless your platform is not supported. Eidolon itself does not need to be installed in any particular location nor require permissions.

To clone the included **EidolonLibs** submodule which contains shared libraries needed to run, use this command within the cloned Eidolon directory:

    git submodule update EidolonLibs
    
Eidolon releases will include pre-built application packages, see the release notes for details.

## Building

For building the Python bindings and Cython libraries, see BUILDING.md.
For building the EidolonLibs objects, see the README.md file in that submodule.

## Documentation

Doxygen Documentation:[![Documentation](https://codedocs.xyz/ericspod/Eidolon.svg)](https://codedocs.xyz/ericspod/Eidolon/)

The wiki https://github.com/ericspod/Eidolon/wiki is the main source of usage documentation. 
Online documentation at runtime for Python code can be seen through the console using the **help** command.

## Authors

Eidolon is developed and maintained by Eric Kerfoot <eric.kerfoot@kcl.ac.uk>.

## License

Copyright (C) 2016 Eric Kerfoot, King's College London, all rights reserved

This file is part of Eidolon.

Eidolon is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Eidolon is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program (LICENSE.txt).  If not, see <http://www.gnu.org/licenses/>

## Used/Included Library Copyrights

#### Python

Python is licensed under the Python Software Foundation License.
Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011,
2012, 2013, 2014, 2015, 2016 Python Software Foundation.  All rights reserved.

#### PyQt
PyQt is licensed under the GPL version 3.
PyQt is Copyright (C) 2011 Riverbank Computing Limited <info@riverbankcomputing.com>
                                            
#### Ogre

OGRE (www.ogre3d.org) is made available under the MIT License.
Copyright (c) 2000-2015 Torus Knot Software Ltd

#### Cython 

Cython is available under the open source Apache License v2.


