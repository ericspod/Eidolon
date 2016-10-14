# Installation Requirements 

Eidolon works currently in Windows (7 definitely, maybe 8 and 10) and Linux (Ubuntu 12.*, 14.*), and OS X 10.8+. iOS and Android are tentative possibilities.

For all platforms it requires:
 * Python 2.7
 * PyQt 4.10.4+ (earlier 4.* versions may work also)
 * Numpy 1.8.0+ (earlier 1.7 versions may work too, 1.6 does not for some features)
 * SciPy 0.13.3+ (earlier versions might also work)
 
----

## Windows 

Install Python either by downloading the Anaconda package or installing the components manually.

### Anaconda

Install the Anaconda Python 2.7 64bit Graphical installer: http://continuum.io/downloads

This should include PyQt4, but if not then you will need to install it manually. In a command window, navigate to the *Anaconda/Scripts* directory and execute the following to install PyQt4 (version 4.10.4 as of this writing):

    conda.exe install pyqt

### Manual Python Install

If you don't want to use Anaconda then you'll need to install the following:

 * Python 2.7 64bit: http://www.python.org/download/
 * Numpy: http://sourceforge.net/projects/numpy/files/
 * SciPy: http://www.scipy.org/install.html (comes with Numpy, get a 64bit version)
 * PyQt 4: http://www.riverbankcomputing.com/software/pyqt/download (may need to be 4.10 version exactly)

----

## Linux

Eidolon has only been compiled to work on Ubuntu 12.04 and 14.04 so these instructions are for these distros only. The Eidolon requires the following packages: 

 * BASH (a "recent" version)
 * python2.7
 * python-numpy 
 * python-scipy
 * python-qt4 
 * libcg
 * System-installed IRTK (Optional)

You may also need the following packages:

 * libopenjpeg2 (OpenJpeg)
 * openexr (OpenExr)

Follow the instructions below for your OS version before installing anything. 

### Ubuntu 12.* 

The built-in version of Python with 12.* is not compatible anymore so a manual install isn't feasible. Follow the instructions below for installing Anaconda then install libopenjpeg2, openexr, and libcg by running the following:

    sudo apt-get install libopenjpeg2 openexr libcg

Otherwise use a package manager (ie. Synaptic).

If you don't want to use Anaconda you'll have to compile new versions of Python 2.7.11, Numpy, SciPy, PyQt, etc. then recompile Eidolon. Not fun.

### Ubuntu 14.*

Install Python by following the manual install instructions below.

The Ogre3D library distributed with this version of Ubuntu is needed, so install the following:

 * libogre-1.9.0

For developers, also install:

 * libogre-1.9-dev

### NB: Anaconda

With Ubuntu 12.04 there's a number of issues with older software now, so the easiest solution is to download the 64-bit Python 2.7 Anaconda distribution from here: https://www.continuum.io/downloads

Install the package with the following command:

    bash Anaconda2-2.5.0-Linux-x86_64.sh

This will by default put Anaconda in your home directory, so you need to put **$HOME/Anaconda2/bin** in your **PATH** variable, or modify whatever aliases you're using to prioritize that Python over your system Python. A useful thing to add to your **.bashrc** file is a function which sets the PATH variable in this way just for opening Eidolon:

    function eidolon {
      PATH="$HOME/anaconda2/bin:$PATH" $HOME/Eidolon/run.sh $*
    }

(This assumes the Eidolon directory is in your home directory and Anaconda was installed to the default place)

### Manual Python Install

The simplest way to install these on is all together on the command line:

    sudo apt-get install python2.7 python-numpy python-scipy python-qt4 libcg

Otherwise use a package manager to install these individually.

### IRTK

Eidolon can also use system-installed IRTK executables. If these are present they will be used automatically, otherwise those packaged with Eidolon will be used. To install the IRTK onto your system using the provided PPA, run the following:

    sudo apt-add-repository ppa:ghisvail/irtk
    sudo apt-get update
    sudo apt-get install irtk

----
## OS X

There is a OS X application package provided containing a .app object. Download the .dmg from the main trac page, mount it and copy the .app package to wherever you want, then double click to start. Alternatively .tgz packages of development releases can be acquired by request. 

The tutorial material is within the .app directory, so you will have go into this with Finder and copy *Eidolon_?.?.?.app/Contents/Resources/tutorial* to some other location to be able to open the script files from within Eidolon. You get access to the contents of the .app directory by right-clicking on it and selecting **Show Package Contents**.
