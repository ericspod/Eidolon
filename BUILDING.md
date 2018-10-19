# Building Instructions

Eidolon needs Python to run as well as build so first follow the instructions for running it in INSTALLATION.md. 
Various additional components are needed to build for each platform. 
This assumes that the pre-built libraries are included.
For all platforms the following are required either separately, as included with the source, or as part of Anaconda:

 * Ogre3D Development Files (included)
 * Cython
 * g++/clang
 * make
 * git

The following are instructions for building with Anaconda/Miniconda as the base Python environment as setup in INSTALLATION.md. 
 
## Anaconda Setup

Install the necessary extra libraries using pip in a bash window (or Anaconda Prompt on Windows):

    conda install cython
    
#### Windows

Building Eidolon requires the use of a makefile which expects POSIX command line tools. The easiest way to get this is
to install Cygwin 64-bit (https://www.cygwin.com/) and then run commands from its bash console.

With Cygwin installed the **PATH** variable has to be set to include your Anaconda installed, for example:

    export PATH="$HOME/Miniconda3:$HOME/Miniconda3/Scripts:$HOME/Miniconda3/Library/mingw-w64/bin:$PATH"
    
This assumes you installed Miniconda in your home directory, change the `$HOME/Miniconda3` if not.

Install MinGW with the following in an Cygwin console:

    conda install libpython m2w64-toolchain
    
This will install the needed development tools with the **make** command in this setup is called **mingw32-make**. 
    
#### Linux (Ubuntu 14 and other Debians, other distros) 

Install **g++** and **make** (Debian-based):

    sudo apt-get install g++ make
    
#### OS X

OS X must be setup with Xcode and the necessary Python frameworks, follow the instructions for installing this from the App Store or wherever else.

## Building 

To build in any platform, simply use the **make** command without any arguments (or **mingw32-make** on Windows). 
This will first generate resource files from the Qt UI definition files, then builds with Cython to create the Python/C++ binding objects. 
This can be done with separate commands as follows:

    make ui 
    make renderer 
    make pyxlibs 

## Generating Applications With Pyinstaller

This program is used to generate standalone applications for Eidolon. On Windows this command must be run from a Cygwin terminal since it relies on 
command line programs.

First install it with pip:

    pip install pyinstaller
    
From a command line use **make** to generate the application:

    make app
    
On Windows or Linux this will create a .zip file containing the app, on OSX it will be a .dmg mountable filesystem.
