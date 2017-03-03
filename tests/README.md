# Eidolon Tests

This directory contains tests for Eidolon, both interactive tests run manually and Nose run unit tests.
To run an interactive test, start Eidolon with one of the script files in **imagetests** or **meshtests**.
For example:

    ../run.sh meshtests/tritest.py
    
To run the unit tests with Nose (assuming this is installed), start Eidolon with all of the *tests.py script files specified on the command line:

    ../run.sh unittests/*tests.py
    
The script **run_coverage.sh** starts Eidolon with code coverage enabled through Coverage.py. 
This can be run with the included tests to measure line coverage:

    ./run_coverage.sh /meshtests/*.py
    
