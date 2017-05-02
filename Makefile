# Eidolon Biomedical Framework
# Copyright (C) 2016-7 Eric Kerfoot, King's College London, all rights reserved
# 
# This file is part of Eidolon.
#
# Eidolon is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# Eidolon is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along
# with this program (LICENSE.txt).  If not, see <http://www.gnu.org/licenses/>


KERNEL_NAME = $(shell uname)
ARCH = $(shell uname -m)

ifeq ($(KERNEL_NAME),Linux)
	PLAT=ubuntu$(shell lsb_release -rs 2>/dev/null | head -c 2)
ifeq ($(PLAT),)
	PLAT=linux
endif
else ifeq ($(KERNEL_NAME),Darwin)
	PLAT=osx
else ifeq ($(findstring MINGW,$(KERNEL_NAME)),MINGW)
	PLAT=win64_mingw
else ifeq ($(findstring CYGWIN,$(KERNEL_NAME)),CYGWIN)
	#PLAT=win64_cygwin
	PLAT=win64_mingw
endif

LIB_HOME = ./EidolonLibs/$(PLAT)
SRC=./src
RESRC=$(SRC)/renderer
PYSRC=$(SRC)/eidolon
PLUGINS=$(SRC)/plugins
UI=$(SRC)/ui

PYTHON=$(shell which python)
PYTHON_VERNAME=python2.7
PYUIC=pyuic4
PYRCC=pyrcc4
PYINST?=pyinstaller

# find the path to the python exe using the registry
ifeq ($(PLAT),win64_mingw)
	REG="$(shell cat /proc/registry/HKEY_CURRENT_USER/Software/Python/PythonCore/2.7/InstallPath/@ 2>/dev/null)"
	ifeq ($(REG),"")
		REG="$(shell cat /proc/registry/HKEY_LOCAL_MACHINE/SOFTWARE/Python/PythonCore/2.7/InstallPath/@ 2>/dev/null)"
	endif

	PYTHON=$(shell cygpath -u '$(REG)')/python.exe
	SO_SUFFIX=.pyd
endif

PYTHONVER=$(shell $(PYTHON) -V 2>&1)
CYTHONVER=$(shell $(PYTHON) -c 'import cython;print cython.__version__')

QTDIR=$(shell python -c 'import PyQt4;print PyQt4.__path__[0].replace("\\","/")')
PYUIC=$(PYTHON) $(QTDIR)/uic/pyuic.py

#--------------------------------------------------------------------------------------

.PHONY: clean clean_gen header all ui renderer pyxlibs resource distfile tutorialfile

all: header ui renderer pyxlibs

%.py : %.ui
	$(PYUIC) $< > $@

ui : $(patsubst %.ui,%.py,$(wildcard $(UI)/*.ui))

resource:
	$(PYRCC) res/Resources.qrc -py3 -o $(SRC)/ui/Resources_rc.py

renderer:
	cd $(RESRC) && $(PYTHON) setup.py build_ext --inplace

pyxlibs:
	cd $(PYSRC) && $(PYTHON) setup.py build_ext --inplace
	rm -f $(patsubst %.pyx,%.cpp,$(wildcard $(PYSRC)/*.pyx))

distfile: # creates the universal distributable zip file with path DISTNAME.zip
	$(eval DISTNAME?=Eidolon_All_$(shell ./run.sh --version 2>&1))
	mkdir $(DISTNAME)
	cp -Rf src EidolonLibs tutorial tests res $(DISTNAME)
	cp main.py run.sh run.bat config.ini *.md *.txt *.spec $(DISTNAME)
	find $(DISTNAME) -name .DS_Store -delete
	find $(DISTNAME) -name \*~ -delete
	find $(DISTNAME) -name \*.pickle -delete
	find $(DISTNAME) -name dicomdataset.ini -delete
	find $(DISTNAME) -name \*.pyc -delete
	zip -r $(DISTNAME).zip $(DISTNAME)
	rm -rf $(DISTNAME)
	
app:
	#$(MAKE)
	./run.sh --version
	rm -rf dist
ifeq ($(PLAT),win64_mingw)
	$(eval DISTNAME?=Eidolon_Win64_$(shell ./run.sh --version 2>&1))
	cp $(LIB_HOME)/bin/*.dll src/renderer
	$(PYINST) --clean PyInstaller.spec
	rm -rf src/renderer/*.dll build
	rm dist/Eidolon/res/*.png
	rm dist/Eidolon/EidolonLibs/IRTK/*.so.1
	rm dist/Eidolon/EidolonLibs/IRTK/*.bin
	find dist/Eidolon/EidolonLibs/IRTK/ -type f  ! -name "*.*" -delete
	-cd dist && zip -r ../$(DISTNAME).zip Eidolon
else ifeq ($(PLAT),osx)
	$(eval DISTNAME?=Eidolon_OSX64_$(shell ./run.sh --version 2>&1))
	DYLD_FRAMEWORK_PATH=$(LIB_HOME)/bin $(PYINST) --clean -F PyInstaller.spec
	rm -rf build
	install_name_tool -change @executable_path/../Frameworks/Ogre.framework/Versions/1.10.0/Ogre @executable_path/Ogre dist/Eidolon.app/Contents/Frameworks/RenderSystem_GL.framework/RenderSystem_GL
	install_name_tool -change @executable_path/../Frameworks/Ogre.framework/Versions/1.10.0/Ogre @executable_path/Ogre dist/Eidolon.app/Contents/Frameworks/Plugin_CgProgramManager.framework/Plugin_CgProgramManager
	install_name_tool -change @executable_path/../Frameworks/Cg.framework/Cg @executable_path/Contents/Frameworks/Cg.framework/Cg dist/Eidolon.app/Contents/Frameworks/Plugin_CgProgramManager.framework/Plugin_CgProgramManager
	rm dist/Eidolon.app/res/*.png
	rm dist/Eidolon.app/EidolonLibs/IRTK/*.so.1
	rm dist/Eidolon.app/EidolonLibs/IRTK/*.bin
	rm dist/Eidolon.app/EidolonLibs/IRTK/*.exe
	rm dist/Eidolon.app/EidolonLibs/IRTK/*.dll
	cd dist && hdiutil create -size 1000000k -volname Eidolon -srcfolder Eidolon.app -ov -format UDZO -imagekey zlib-level=9 ../$(DISTNAME).dmg
else
	$(eval DISTNAME?=Eidolon_Linux64_$(shell ./run.sh --version 2>&1))
	LD_LIBRARY_PATH=$(LIB_HOME)/bin $(PYINST) --clean PyInstaller.spec
	rm -rf build
	rm dist/Eidolon/res/*.png
	rm dist/Eidolon/EidolonLibs/IRTK/*.exe
	rm dist/Eidolon/EidolonLibs/IRTK/*.dll
	find dist/Eidolon/EidolonLibs/IRTK/ -type f  ! -name "*.*" -delete
	cd dist/Eidolon && rm -rf libstdc++.so.6 libglib-2.0.so.0 libgobject-2.0.so.0 libgpg-error.so.0 share/icons
	cp /usr/lib/x86_64-linux-gnu/libCg.so run.sh dist/Eidolon
	-cd dist && zip -r ../$(DISTNAME).zip Eidolon
endif

tutorialfile:
	tar czf Tutorials.tgz tutorial

clean:
ifeq ($(PLAT),win64_mingw)
	rm -rf $(SRC)/*/*.pyd
else ifeq ($(PLAT),osx)
	rm -rf $(SRC)/*/*.so.osx
else
	rm -rf $(SRC)/*/*.so.ubuntu* 
endif

clean_gen:
	rm -rf $(patsubst %.ui,%.py,$(wildcard $(UI)/*.ui $(PLUGINS)/*.ui))

header:
	@echo "---------------------------------"
	@echo " Eidolon Makefile Variables      "
	@echo "---------------------------------"
	@echo " Kernel name : $(KERNEL_NAME)    "
	@echo " Platform    : $(PLAT)           "
	@echo " Arch        : $(ARCH)           "
	@echo " Python      : $(PYTHON)         "
	@echo " PYTHONVER   : $(PYTHONVER)      "
	@echo " CYTHONVER   : $(CYTHONVER)      "
	@echo " PYUIC       : $(PYUIC)          "
	@echo " PYRCC       : $(PYRCC)          "
	@echo " QTDIR       : $(QTDIR)          "
	@echo "---------------------------------"

