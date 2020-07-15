@ECHO off

SET APPDIR=%~dp0

:: Pull out the Python install path we're using from the registry, looking first in the current user settings then in the local machine
:: If this gets the wrong value when there's multiple Python installs, you'll have to set InstallPath manually

FOR /F "skip=2 tokens=2*" %%A IN ('REG QUERY HKCU\Software\Python\PythonCore\3.7\InstallPath 2^>NUL') DO  SET InstallPath=%%B

IF "%InstallPath%" == "" FOR /F "skip=2 tokens=2*" %%A IN ('REG QUERY HKLM\SOFTWARE\Python\PythonCore\3.7\InstallPath 2^>nul') DO SET InstallPath=%%B

IF "%InstallPath%" == "" FOR /F "skip=2 tokens=2*" %%A IN ('REG QUERY HKCU\Software\Python\PythonCore\3.6\InstallPath 2^>NUL') DO  SET InstallPath=%%B

IF "%InstallPath%" == "" FOR /F "skip=2 tokens=2*" %%A IN ('REG QUERY HKLM\SOFTWARE\Python\PythonCore\3.6\InstallPath 2^>nul') DO SET InstallPath=%%B

:: Choose a default value if no registry key is present
IF [%InstallPath%] == [] SET InstallPath=C:\Python37\

:: PATH is needed for the DLL the render links to and the renderer plugin DLLs
SET PATH=%APPDIR%\eidolon\EidolonLibs\win64_mingw\bin;%PATH%

:: set the Anaconda paths, if the PATH variable isn't set this is needed, if using other distributions you'll have to change this to include your DLLs
SET PATH=%PATH%;%InstallPath%;%InstallPath%\Library\mingw-w64\bin;%InstallPath%\Library\usr\bin;%InstallPath%\Library\bin;%InstallPath%\Scripts;%InstallPath%\bin;%InstallPath%\condabin

%InstallPath%\python.exe "%APPDIR%main.py" %*

:: Alternative way of starting Eidolon without a script window hanging around 
:: START %InstallPath%\pythonw.exe %APPDIR%main.py %*
:: EXIT
