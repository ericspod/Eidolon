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

export LIBSDIR="$APPDIR/eidolon/EidolonLibs"
#export DYLD_FRAMEWORK_PATH=$LIBSDIR/osx/bin

export PYTHONPATH=$([ -z "$PYTHONPATH" ] && echo "$APPDIR" || echo "$PYTHONPATH:$APPDIR")
#export LD_LIBRARY_PATH=$LIBSDIR/linux/bin:$LIBSDIR/IRTK:$LD_LIBRARY_PATH

# generated executable, run this instead of the script
if [ -f "$APPDIR/Eidolon" ] 
then
	LD_LIBRARY_PATH="$APPDIR:$LD_LIBRARY_PATH" "$APPDIR/Eidolon" "$@"
	exit $?
fi

# Windows Cygwin or Msys shell
if [ "$(uname -o 2>/dev/null)" == "Cygwin" ] || [ "$(uname -o 2>/dev/null)" == "Msys" ] 
then
	"$APPDIR/run.bat" $@
	exit $?
fi

python "$APPDIR/main.py" "$@"

