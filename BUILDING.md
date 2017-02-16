# Building Instructions

Eidolon needs Python to run as well as build so first follow the instructions for running it. 
Various additional components are needed to build for each platform. 
This assumes that the pre-built libraries are included.
For all platforms the following are required either separately, as included with the source, or as part of Anaconda:

 * Ogre3D Development Files
 * PyQt Development Tools
 * Cython (specifically 0.24.1 for now)
 * g++/clang
 * make
 * git

## Setup

### Linux (Ubuntu 12/14) 

**Ubuntu 12.*** doesn't require anything extra if Anaconda is installed, so this is the easiest way to get started with development.

**Ubuntu 14.*** version of Eidolon uses the system Ogre3D package so the development components for that must be installed plus the Qt development tools and Cython:

    sudo apt-get install libogre-1.9-dev pyqt4-dev-tools qt4-dev-tools cython

Additionally for either platform, **g++** and **make** are needed to build the libraries, you should have these already. 

### OS X

OS X must be setup with Xcode and the necessary Python frameworks, follow the instructions for installing on OSX using MacPorts and pip then the following:

    sudo pip install Cython

You will otherwise have to download and install the following:

 1. Download and install Python2.7: http://www.python.org/download/ (most recent 2.* 64bit version)
 2. Download and build PyQt: http://www.riverbankcomputing.co.uk/software/pyqt/download (source release)
 3. Download and install Numpy and Scipy: http://www.scipy.org/install.html
 4. Download and build Cython: http://cython.org/#download


### Windows

Compiling in Windows requires Anaconda with its associated **MinGW** distribution and GNU Make.

 1. Install Cygwin from http://www.cygwin.org first, making sure to include **make** with the installation. Modify your config files to ensure the Anaconda executables are topmost in your **PATH**. 
 
 **OR**
 
 Use the Windows shell or PowerShell to invoke the commands in the next 2 steps, and then calling **mingw32-make.exe** when building instead of **make**. Cygwin isn't necessary but is really handy.

 2. Next pip must be installed, go to https://pip.pypa.io/en/latest/installing.html to get the get-pip.py script and run it in your Cygwin terminal. 

 3. Install MinGW with the following:

        pip install -i https://pypi.anaconda.org/carlkl/simple mingwpy


## Building 

To build in any platform, simply use the **make** command without any arguments (or **mingw32-make.exe** if not using Cygwin). 
This will first run pyuic to generate Python from the Qt UI definition files, then builds with Cython to create the Python/C++ binding objects. 
This can be done with separate commands as follows:

    make ui 
    make renderer 
    make pyxlibs 

Building in Windows is the same as the above using **Cygwin** as the environment in which you run make, and using the **MinGW** distribution installed with Anaconda.

### Building Ogre with MinGW 64-bit Supplied with Anaconda

Building Ogre with the MinGW specified above may require a few code tweaks.
Read the following, the first is a step guide and the second is the changes to Ogre code necessary to get MinGW to work:
 * http://www.ogre3d.org/tikiwiki/tiki-index.php?page=Building+Ogre+with+boost+1.50+upwards+and+MinGW
 * http://www.ogre3d.org/tikiwiki/tiki-index.php?page=TDM+MinGW64+build+guide
