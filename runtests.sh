#! /bin/bash

# quit on error
# set -e

# configuration values
doCoverage=false
doDryRun=false

# home directory
homedir="$( cd -P "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$homedir"

# python path
export PYTHONPATH="$homedir:$PYTHONPATH"
echo "PYTHONPATH: $PYTHONPATH"

cmdPrefix=""
PY_EXE=${PY_EXE:-python}
echo "PY_EXE: $PY_EXE"

function print_usage {
    echo "runtests.sh [--coverage] [--dryrun] [--help] [--version]"
    echo ""
    echo "Eidolon unit testing utilities."
    echo ""
    echo "Examples:"
    echo "    ./runtests.sh             # run tests and fixes"
    echo "    ./runtests.sh --coverage  # run with coverage"
    echo ""
    echo "Options:"
    echo "    --coverage"
    echo "    --dryrun"
    echo "    -h, --help"
    echo "    -v, --version"
    exit 1
}

function print_version {
    ${PY_EXE} "eidolon/_version.py"
}

# parse arguments
while [[ $# -gt 0 ]]
do
    key="$1"
    case $key in
        --coverage)
            doCoverage=true
        ;;
        --dryrun)
            doDryRun=true
        ;;
        -h|--help)
            print_usage
        ;;
        -v|--version)
            print_version
            exit 1
        ;;
        *)
            echo "ERROR: Unknown argument: $key"
            print_usage
        ;;
    esac
    shift
done

if [ $doDryRun = true ]
then
    # commands are echoed instead of ran
    cmdPrefix="dryrun "
    function dryrun { echo "    " "$@"; }
fi

# isort
${cmdPrefix}${PY_EXE} -m isort "$(pwd)"

# black
${cmdPrefix}${PY_EXE} -m black --skip-magic-trailing-comma "$(pwd)"

# flake8
${cmdPrefix}${PY_EXE} -m flake8 "$(pwd)" --count --statistics

# pylint
ignore_codes="C,R,W,E1101,E1102,E0601,E1130,E1123,E0102,E1120,E1137,E1136"
${cmdPrefix}${PY_EXE} -m pylint eidolon tests --disable=$ignore_codes

# set coverage command
if [ $doCoverage = true ]
then
    cmd="${PY_EXE} -m coverage run --append"
else
    cmd=${PY_EXE}
fi

#unit tests
${cmdPrefix}${cmd} -m unittest tests/unittests/*.py 

if [ $doCoverage = true ]
then
    ${cmdPrefix}${PY_EXE} -m coverage report --ignore-errors
fi
