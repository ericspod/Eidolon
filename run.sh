#! /bin/bash

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

# directory of this script
export APPDIR=$(getFileDir "${BASH_SOURCE[0]}")
export LIBSDIR=$APPDIR/EidolonLibs
export PYTHONPATH=$APPDIR/src

if [ "$(uname -o 2>/dev/null)" == "Cygwin" ]
then
	$APPDIR/run.bat $@
	exit 0
elif [ "$(uname)" == "Darwin" ]
then
	# symlink each compiled library for OSX to the correct name
	for i in $APPDIR/src/*/*.so.osx; do ln -fs $i ${i%.so.osx}.so;done
	
	export DYLD_FRAMEWORK_PATH=$LIBSDIR/osx/bin
else
	PLAT=ubuntu$(lsb_release -sr | head -c 2)
	# symlink every compiled library for this platform to the correct name
	for i in $APPDIR/src/*/*.so.$PLAT; do ln -fs $i ${i%.so.$PLAT}.so;done
	
	export LD_LIBRARY_PATH=$LIBSDIR/$PLAT/bin:$LIBSDIR/IRTK:$LD_LIBRARY_PATH
fi

python2.7 $APPDIR/main.py "$@"

