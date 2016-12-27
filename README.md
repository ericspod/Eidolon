# Eidolon
Eidolon is a biomedical visualization and analysis framework designed to render spatial biomedical data (images and meshes) and provide facilities for image reconstruction, analysis, and computation.

Features include:

 * Visualization environment providing the combined rendering of time-dependent mesh and image data in 2D and 3D views 
 * Concurrent algorithms for processing and generating data
 * Python-based framework with compiled code extensions for renderer, algorithms, and data structures
 * Interactive access to running application code through built-in Python console
 * Plugin-oriented architecture, script interface, and console allow easy user-extension to code 
 * Integration with Python scientific libraries including numpy and scipy
 * Multi-platform support, including Windows, OSX, Ubuntu 12/14
 * Project-oriented architecture helps organize data and extension features
 * Image processing, registration, and motion tracking provided through IRTK routines

## Installation

The most current release will include zip files containing the code as well as standalone applications for Windows and OSX. 
These apps do not require anything to be installed, however to run the application from the zip or a checkout, Python and the necessary components need to be installed.
See INSTALLATION.md for details on how to run Eidolon from a git checkout. 

To initialize the included **EidolonLibs** submodule which contains shared libraries needed to run, use the **--recursive** option when cloning:

    git clone --recursive https://github.com/ericspod/Eidolon.git

The submodule can otherwise be initialized within the cloned Eidolon directory with this command:

    git submodule update EidolonLibs
    
The code includes precompiled libraries and executables so compilation shouldn't be necessary unless your platform is not supported. 
Eidolon itself does not need to be installed in any particular location nor require permissions.
Releases include pre-built application packages, see the release notes for details.

## Building

For building the Python bindings and Cython libraries, see BUILDING.md.
For building the EidolonLibs objects, see the README.md file in that submodule.

## Documentation

Doxygen Documentation: [![Documentation](https://codedocs.xyz/ericspod/Eidolon.svg)](https://codedocs.xyz/ericspod/Eidolon/)

The wiki https://github.com/ericspod/Eidolon/wiki is the main source of usage documentation. 
Online documentation at runtime for Python code can be seen through the console using the **help** command.

## Notifications

Watch this repository to receive notifications for new releases, or subscribe to the Google Group for announcements: <eidolon-users+subscribe@googlegroups.com>

## Authors/Acknowledgements

Eidolon is developed and maintained by Eric Kerfoot, King's College London <eric.kerfoot@kcl.ac.uk> with the support of the National Institute for Health Research (NIHR) Biomedical Research Centre (BRC) at KCL.

If any publications are made with the help of Eidolon it would be appreciated if an acknowledgement is included recognizing the author, KCL, and BRC.

The main citation for Eidolon:

    @InProceedings{kerfoot2016miar,
      author =    {Kerfoot, E. and Fovargue, L. and Rivolo, S. and Shi, W. and Rueckert, D. and Nordsletten, D. and Lee, J. and Chabiniok, R. and Razavi, R.},
      title =     {Eidolon: Visualization and Computational Framework for Multi-Modal Biomedical Data Analysis},
      booktitle = {LNCS 9805, Medical Imaging and Augmented Reality 2016 (MIAR 2016)},
      year =      {2016},
      journal =   {Lecture Notes in Computer Science},
      volume =    {9805},
      doi =       {10.1007/978-3-319-43775-0},
      url =       {http://www.springer.com/gb/book/9783319437743},
      publisher = {Springer}
    }

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

## Used/Included Library Copyrights and Acknowledgements

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

#### IRTK

The Image Registration Toolkit was used under Licence from Ixico Ltd. 

The image registration software itself has been written by

Daniel Rueckert

Visual Information Processing Group Department of Computing Imperial College London London SW7 2BZ, United Kingdom

The image processing library used by the registration software has been written by

Daniel Rueckert Julia Schnabel

See the COPYRIGHT file in the IRTK repository at https://github.com/BioMedIA/IRTK for more information on the copyright and license agreement for the software.

#### GPU_Nreg

GPU_Nreg is provided by Dr Wenjia Bai, Imperial College London (http://wp.doc.ic.ac.uk/wbai/).


