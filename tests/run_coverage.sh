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

if [ "$(uname -o 2>/dev/null)" == "Cygwin" ]
then
#	$APPDIR/run.bat $@
#	exit 0
	APPDIR=$(cygpath -w $APPDIR)
	export PATH="$APPDIR\\EidolonLibs\\win64_mingw\\bin;$PATH"
	export PYTHONPATH="$APPDIR\\src"
elif [ "$(uname)" == "Darwin" ]
then
	# symlink each compiled library for OSX to the correct name
	for i in $APPDIR/src/*/*.so.osx; do ln -fs $i ${i%.so.osx}.so;done
	
	export DYLD_FRAMEWORK_PATH=$LIBSDIR/osx/bin
else
	# symlink every compiled library for this platform to the correct name
	for i in $APPDIR/src/*/*.so.linux; do ln -fs $i ${i%.so.linux}.so;done
	
	export LD_LIBRARY_PATH=$LIBSDIR/linux/bin:$LIBSDIR/IRTK:$LD_LIBRARY_PATH
fi


coverage run --branch --source=$APPDIR/src/eidolon --omit=$APPDIR/src/*/setup.py $APPDIR/main.py --help

covcmd="coverage run -a --branch --source=$APPDIR/src/eidolon --omit=$APPDIR/src/*/setup.py $APPDIR/main.py"
#$covcmd ./meshtests/*.py
#$covcmd ./imagetests/*.py
$covcmd "$@"
coverage report

