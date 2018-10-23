# Installation Requirements

These are the instructions for installing the necessary components to run Eidolon from a git checkout or zip package.
Eidolon works currently in Windows (7 definitely, 8 and 10 seem fine) and Linux (14.\*, Mint 18+, etc., and up), and OS X 10.8+. 
For these platforms you should not need to compile since shared objects are included in the repository.

For all platforms it requires:
 * Python 3.6 (version 2.7 is technically supported but untested)
 * PyQt 4.10.4+ or 5.*
 * Numpy 1.8.0+
 * SciPy 0.13.3+ 
 * ImageIO (optional)
 * Pandas (optional)
 * coverage (optional)
 * six (if not already present)

The following will explain how to setup a Python environment with Anaconda/Miniconda. 
To install using another Python distribution involves following the installation instructions for the base Python interpreter
and then for the above libraries. These can be acquired from:

 * Python 2.7 64bit: http://www.python.org/download/
 * Numpy/SciPy: http://www.scipy.org/install.html 
 * PyQt 4/5: http://www.riverbankcomputing.com/software/pyqt/download
 
or using the package manager of your system (apt-get or port).  
It is however strongly advised to use Anaconda for running Eidolon, it's simply easier to use, install or uninstall, and not
prone to installation or versioning issues that arise with a built-in Python interpreter.
 
----

## Anaconda
 
**The easiest way to get all these for any platform is through Anaconda: https://www.anaconda.com/download**
The following instructions are for setting up Anaconda for any platform. 
Miniconda (https://conda.io/miniconda.html) can alternatively be installed which includes fewer libraries but is much smaller to download and install.

#### Windows

Download the 64-bit Anaconda/Miniconda executable and install by running it. Once installed this should become the default Python. 

From the Start Menu open an **Anaconda Prompt** window and run the following:

    conda install python=3.6.3 numpy scipy pyqt six
    
This will install the bare necessities for Anaconda or Miniconda, the extras can be installed by including `imageio pandas`
in the command.

Once this is installed Eidolon can be run by double-clicking `run.bat` or running it from a terminal window.
In a Cygwin terminal, either `run.bat` or `run.sh` can be use to run Eidolon. 

#### Linux and OSX

Download the 64-bit .sh file for Anaconda/Miniconda for your platform. Follow instructions for running the .sh file to install. 

Both Linux and OSX versions of Anaconda will include a version of Numpy which uses Intel's Math Kernel Library (MKL). 
Unfortunately this is not compatible with multi-process concurrency for some reason and so the non-MKL versions of libraries
must be used instead. The easiest way to do this is to create a new environment called **nomkl** and run Eidolon from that.
Open a terminal and with the new installation in your PATH run the following:

    conda create -n nomkl python=3.6.3 nomkl numpy scipy pyqt six

Adding `imageio pandas` will install the optional libraries.
Once this is done the command `source activate nomkl` will activate this environment, then Eidolon can be run by executing `run.sh`.
