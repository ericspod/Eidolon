# Installation Requirements

These are the instructions for installing the necessary components to run Eidolon from a git checkout.
Eidolon works currently in Windows (7 definitely, 8 and 10 seem fine) and Linux (14.\*, Mint 18+, etc., and up), and OS X 10.8+. 
For these platforms you should not need to compile since shared objects are included in the repository.

For all platforms it requires:
 * Python 2.7
 * PyQt 4.10.4+ (earlier 4.\* versions may work) or 5.*
 * Numpy 1.8.0+ (earlier 1.7 versions may work, 1.6 does not)
 * SciPy 0.13.3+ (earlier versions may work)
 
Python 3 is not supported just yet, this is a TODO item.

The code coverage testing relies on **coverage**.

**The easiest way to get all these for any platform is through Anaconda: http://continuum.io/downloads**

----

## Windows

Install Python either by downloading the Anaconda package or installing the components manually.

### Anaconda

Install the Anaconda Python 2.7 64bit Graphical installer: http://continuum.io/downloads

### Manual Python Install

If you don't want to use Anaconda then you'll need to install the following:

 * Python 2.7 64bit: http://www.python.org/download/
 * Numpy: http://sourceforge.net/projects/numpy/files/
 * SciPy: http://www.scipy.org/install.html (comes with Numpy, get a 64bit version)
 * PyQt 4/5: http://www.riverbankcomputing.com/software/pyqt/download

----

## OS X

Follow the instructions above for Windows, installing Anaconda or a manual Python install. 

Installing Python manually is easiest with MacPorts (https://www.macports.org/):

    sudo port install python27 py27-numpy py27-scipy py27-pyqt4

A few other things may need to be installed if packages are missing:

    sudo port install py27-pip py27-appdirs py27-nose py27-pip
    sudo pip install nose-cprof packaging

----
## Linux

Eidolon has been compiled to work on Ubuntu 14.04+ but works on later version of Ubuntu and other distros using later kernels. 
Support for earlier versions of Ubuntu is now dropped.
The following packages are required:

 * BASH (a "recent" version)
 * python2.7
 * python-numpy
 * python-scipy
 * python-qt4 or python-qt5

You may also need the following packages:

 * libopenjpeg2 (OpenJpeg)
 * openexr (OpenExr)

Follow the instructions below for Anaconda or system installation.

#### Anaconda

An easy way to get started is to download the 64-bit Python 2.7 Anaconda distribution from here: https://www.continuum.io/downloads

Install the package with the following command (or something similar):

    bash Anaconda2-4.1.0-Linux-x86_64.sh

This will by default put Anaconda in your home directory, so you need to put **$HOME/Anaconda2/bin** in your **PATH** variable, or modify whatever aliases you're using to prioritize that Python over your system Python. A useful thing to add to your **.bashrc** file is a function which sets the PATH variable in this way just for opening Eidolon:

    function eidolon {
      PATH="$HOME/anaconda2/bin:$PATH" $HOME/Eidolon/run.sh $*
    }

(This assumes the Eidolon directory is in your home directory and Anaconda was installed to the default place)

### Ubuntu 14.* and Other Distros

Install Python and the packages listed above with a package manager (ie. Synaptic) or **apt-get**:

    sudo apt-get install python2.7 python-numpy python-scipy python-qt4 libcg

Sometimes there's a missing package **dateutil.tz**, this can be installed with:

    sudo pip install python-dateutil --upgrade

