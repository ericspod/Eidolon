# Eidolon Tests

This directory contains tests for Eidolon, both interactive tests run manually and Nose run unit tests.
To run an interactive test, start Eidolon with one of the script files in **imagetests** or **meshtests**.
For example:

    ../run.sh meshtests/tritest.py
    
To run the unit tests with unittest execute the **rununittests.py** script in Eidolon:

    ../run.sh rununittests.py
    
The script **run_coverage.sh** starts Eidolon with code coverage enabled through Coverage.py. 
This can be run with the included tests to measure line coverage:

    ./run_coverage.sh /meshtests/*.py
    
The script will create the **.coverage** file and update it thereafter everytime it's run. This file will have to be
deleted to start a new coverage testing series. 
    
