#! /bin/bash

# This file is used to run Eidolon with code coverage enabled with Coverage.py. This must already be installed and 
# present on the command line. 


# Determine file directory (http://stackoverflow.com/a/246128)
function getFileDir() {
	src=$1
	while [ -h "$src" ]; do # resolve $src until the file is no longer a symlink
		dir="$( cd -P "$( dirname "$src" )" && pwd )"
		src="$(readlink "$src")"
		# if $src was a relative symlink, we need to resolve it relative to the path where the symlink file was located
		[[ $src != "/*" ]] && src="$dir/$src" 
	done
	dir="$( cd -P "$( dirname "$src" )" && pwd )"
	
	echo $dir
}

# parent directory of this script, assuming this is in the directory tests
export APPDIR=$(getFileDir "${BASH_SOURCE[0]}")/../

export LIBSDIR=$APPDIR/EidolonLibs
export PYTHONPATH=$APPDIR/src
export DYLD_FRAMEWORK_PATH=$LIBSDIR/osx/bin
export LD_LIBRARY_PATH=$LIBSDIR/linux/bin:$LIBSDIR/IRTK:$LD_LIBRARY_PATH

if [ "$(uname -o 2>/dev/null)" == "Cygwin" ]
then
	APPDIR=$(cygpath -w $APPDIR)
	export PATH="$APPDIR\\EidolonLibs\\win64_mingw\\bin;$PATH"
	export PYTHONPATH="$APPDIR\\src"
fi

# if the coverage file isn't present create it with a simple run of the program
if [ ! -f .coverage ]
then
    coverage run --branch $APPDIR/main.py --help
fi

# contribute to a current .coverage file, delete this file to start fresh
coverage run -a --branch $APPDIR/main.py "$@"
coverage report

