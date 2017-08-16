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
export LIBSDIR="$APPDIR/EidolonLibs"

if [ -z "$PYTHONPATH" ]
then
	export PYTHONPATH="$APPDIR/src"
else
	export PYTHONPATH="$PYTHONPATH:$APPDIR/src"
fi	

if [ -f "$APPDIR/Eidolon" ] # generated executable, run this instead of the script
then
	LD_LIBRARY_PATH="$APPDIR:$LD_LIBRARY_PATH" "$APPDIR/Eidolon" "$@"
	exit $?
elif [ "$(uname -o 2>/dev/null)" == "Cygwin" ] || [ "$(uname -o 2>/dev/null)" == "Msys" ] # Windows Cygwin or Msys shell
then
	"$APPDIR/run.bat" $@
	exit $?
elif [ "$(uname)" == "Darwin" ] # OSX
then
	# symlink each compiled library for OSX to the correct name
	for i in "$APPDIR"/src/*/*.so.osx; do ln -fs "$i" "${i%.so.osx}.so";done
	
	export DYLD_FRAMEWORK_PATH=$LIBSDIR/osx/bin
else
	# symlink every compiled library for this platform to the correct name
	for i in $APPDIR/src/*/*.so.linux; do ln -fs $i ${i%.so.linux}.so;done
	
	export LD_LIBRARY_PATH=$LIBSDIR/linux/bin:$LIBSDIR/IRTK:$LD_LIBRARY_PATH
fi

python2.7 "$APPDIR/main.py" "$@"

