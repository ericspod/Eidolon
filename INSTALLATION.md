# Installation Requirements

These are the instructions for installing the necessary components to run Eidolon from a git checkout.
Eidolon works currently in Windows (7 definitely, maybe 8 and 10) and Linux (Ubuntu 12.\*, 14.\*), and OS X 10.8+. For these platforms you should not need to compile since shared objects are included in the repository.

For all platforms it requires:
 * Python 2.7
 * PyQt 4.10.4+ (earlier 4.\* versions may work, 5 will not for now)
 * Numpy 1.8.0+ (earlier 1.7 versions may work, 1.6 does not)
 * SciPy 0.13.3+ (earlier versions may work)
 * Cg (Linux only, Windows/OSX included with EidolonLibs)
 
----

## Windows

Install Python either by downloading the Anaconda package or installing the components manually.

### Anaconda

Install the Anaconda Python 2.7 64bit Graphical installer: http://continuum.io/downloads

The more recent versions of Anaconda come with PyQt5 so we'll have to swap these out (or choose Anaconda 4.1).
Go into the **Anaconda Navigator**, select **Environments** and type **pyqt** into the search box on the right
Clicking on the checkbox next to **pyqt** gives you the option to swap versions, select the most recent 4 version.
Alternatively an older version of Anaconda, such as 4.1, works and would be easier.

### Manual Python Install

If you don't want to use Anaconda then you'll need to install the following:

 * Python 2.7 64bit: http://www.python.org/download/
 * Numpy: http://sourceforge.net/projects/numpy/files/
 * SciPy: http://www.scipy.org/install.html (comes with Numpy, get a 64bit version)
 * PyQt 4: http://www.riverbankcomputing.com/software/pyqt/download

----

## OS X

Follow the instructions above for Windows, installing Anaconda or a manual Python install. (NOTE: Anaconda may have issues on OSX with multiprocessing, using the prebuilt app or installing manually may be necessary)

Installing Python manually is easiest with MacPorts (https://www.macports.org/):

    sudo port install python27 py27-numpy py27-scipy py27-pyqt4

A few other things may need to be installed if packages are missing:

    sudo port install py27-pip py27-appdirs py27-nose py27-pip
    sudo pip install nose-cprof packaging

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

The built-in version of Python with 12.* is not compatible anymore so a manual install isn't feasible. Follow the instructions below for installing Anaconda after installing the above packages. If you don't want to use Anaconda you'll have to compile new versions of Python 2.7.11, Numpy, SciPy, PyQt, etc. then recompile Eidolon. Not fun.

#### Anaconda

With Ubuntu 12.04 there's a number of issues with older software now, so the easiest solution is to download the 64-bit Python 2.7 Anaconda distribution from here: https://www.continuum.io/downloads

Install the package with the following command (or something similar):

    bash Anaconda2-4.1.0-Linux-x86_64.sh

This will by default put Anaconda in your home directory, so you need to put **$HOME/Anaconda2/bin** in your **PATH** variable, or modify whatever aliases you're using to prioritize that Python over your system Python. A useful thing to add to your **.bashrc** file is a function which sets the PATH variable in this way just for opening Eidolon:

    function eidolon {
      PATH="$HOME/anaconda2/bin:$PATH" $HOME/Eidolon/run.sh $*
    }

(This assumes the Eidolon directory is in your home directory and Anaconda was installed to the default place)

### Ubuntu 14.*

Install Python, Ogre3D, and the packages listed above with a package manager (ie. Synaptic) or **apt-get**:

    sudo apt-get install python2.7 python-numpy python-scipy python-qt4 libcq libogre-1.9.0

Do not use Anaconda unless you want to recompile Eidolon, the included binaries were compiled against the default system Python. There's various issues between platforms in general in regards to how Numpy was compiled, any weird Numpy related exceptions at startup has probably got something to do with this sort of conflict.

Sometimes there's a missing package **dateutil.tz**, this can be installed with:

    sudo pip install python-dateutil --upgrade

