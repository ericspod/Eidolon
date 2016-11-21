@ECHO off

SET APPDIR=%~dp0

:: Pull out the Python install path we're using from the registry, if this gets the wrong value when there's multiple
:: Python installs, you'll have to set InstallPath manually
FOR /F "skip=2 tokens=2*" %%A IN ('REG QUERY HKCU\Software\Python\PythonCore\2.7\InstallPath 2^>NUL') DO  SET InstallPath=%%B

:: If the path wasn't set for the current user, check the local machine
IF "%InstallPath%" == "" FOR /F "skip=2 tokens=2*" %%A IN ('REG QUERY HKLM\SOFTWARE\Python\PythonCore\2.7\InstallPath 2^>nul') DO SET InstallPath=%%B

:: Choose a default value if neither registry key is present
IF [%InstallPath%] == [] SET InstallPath=C:\Python27\

SET PATH=%APPDIR%EidolonLibs\win64_mingw\bin;%PATH%
SET PYTHONPATH=%APPDIR%src;%APPDIR%src\eidolon;%APPDIR%src\plugins;%APPDIR%src\ui

%InstallPath%\python.exe "%APPDIR%main.py" %*

:: Alternative way of starting Eidolon without a script window hanging around 
:: START %InstallPath%\pythonw.exe %APPDIR%main.py %*
:: EXIT


