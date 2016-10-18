# Eidolon Biomedical Framework
# Copyright (C) 2016 Eric Kerfoot, King's College London, all rights reserved
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
	PLAT=win64_cygwin
endif

LIB_HOME = ./Libs/$(PLAT)
SRC=./src
RESRC=$(SRC)/renderer
PYSRC=$(SRC)/eidolon
PLUGINS=$(SRC)/plugins
UI=$(SRC)/ui

PYTHON=python
PYTHON_VERNAME=python2.7
PYUIC=pyuic4
PYRCC=pyrcc4

# find the path to the python exe using the registry
ifeq ($(PLAT),win64_cygwin)
	REG="$(shell cat /proc/registry/HKEY_CURRENT_USER/Software/Python/PythonCore/2.7/InstallPath/@ 2>/dev/null)"
	ifeq ($(REG),"")
		REG="$(shell cat /proc/registry/HKEY_LOCAL_MACHINE/SOFTWARE/Python/PythonCore/2.7/InstallPath/@ 2>/dev/null)"
	endif

	PYTHON=$(shell cygpath -u '$(REG)')/python.exe
	SO_SUFFIX=.pyd
endif

PYTHONVER=$(shell $(PYTHON) -V 2>&1)
CYTHONVER=$(shell cython -V 2>&1)

QTDIR=$(shell python -c 'import PyQt4;print PyQt4.__path__[0].replace("\\","/")')
PYUIC=$(PYTHON) $(QTDIR)/uic/pyuic.py

#--------------------------------------------------------------------------------------

.PHONY: clean clean_gen header all ui cython resource distfile appfile package tutorialfile

all: header ui cython

%.py : %.ui
	$(PYUIC) $< > $@

ui : $(patsubst %.ui,%.py,$(wildcard $(UI)/*.ui))

resource:
	$(PYRCC) res/Resources.qrc -o $(SRC)/ui/Resources_rc.py

cython:
	cd $(RESRC) && python setup.py build_ext --inplace
	cd $(PYSRC) && python setup.py build_ext --inplace
	rm -f $(patsubst %.pyx,%.cpp,$(wildcard $(PYSRC)/*.pyx))

distfile: # creates the universal distributable .tgz file with path DISTNAME.tgz
	mkdir $(DISTNAME)
	cp -Rf src Libs tutorial res $(DISTNAME)
	cp main.py run.sh run.bat config.ini $(DISTNAME)
	rm -rf $(DISTNAME)/src/renderer $(DISTNAME)/src/*/*.ui $(DISTNAME)/src/*/*.o $(DISTNAME)/res/*.qrc
	rm -rf $(DISTNAME)/Libs/*/include $(DISTNAME)/Libs/*/lib $(DISTNAME)/Libs/*/bin/Debug
	rm -rf $(DISTNAME)/Libs/osx/bin/Release/*.framework/Versions/*/Headers
	rm -rf $(DISTNAME)/Libs/win64_msvc $(DISTNAME)/src/*/build
	find $(DISTNAME)/Libs -name \*.lib  -delete
	find $(DISTNAME)/Libs -name \*.a -delete
	find $(DISTNAME) -name .DS_Store -delete
	find $(DISTNAME) -name \*~ -delete
	#find $(DISTNAME) -name \*.pyc -delete
	find $(DISTNAME) -name \*.pxd -delete
	find $(DISTNAME) -name \*.pickle -delete
	-find $(DISTNAME) -name .svn -exec rm -rf '{}' ';' >/dev/null 2>&1
	tar czf $(DISTNAME).tgz $(DISTNAME)
	rm -rf $(DISTNAME)

appfile: # creates the OS X .app directory with path DISTNAME.app
	cp -R $(LIB_HOME)/Eidolon.app $(DISTNAME)
	cp -R main.py config.ini res src tutorial $(LIB_HOME)/bin/Release/*.dylib $(DISTNAME)/Contents/Resources
	rm -rf $(DISTNAME)/Contents/Resources/src/renderer $(DISTNAME)/Contents/Resources/src/*/build
	mkdir $(DISTNAME)/Contents/Resources/Libs
	cp -R ./Libs/python ./Libs/IRTK $(DISTNAME)/Contents/Resources/Libs
	cp -R $(LIB_HOME)/bin/Release/*.framework /Library/Frameworks/Python.framework $(DISTNAME)/Contents/Frameworks
	cp -R /Library/Frameworks/QtCore.framework /Library/Frameworks/QtGui.framework /Library/Frameworks/QtSvg.framework $(DISTNAME)/Contents/Frameworks
	rm -rf $(DISTNAME)/Contents/Frameworks/*/Headers $(DISTNAME)/Contents/Frameworks/*/Versions/Current/Headers
	rm -rf $(DISTNAME)/Contents/Resources/Libs/IRTK/*.exe $(DISTNAME)/Contents/Resources/Libs/IRTK/*.bin $(DISTNAME)/Contents/Resources/Libs/IRTK/*.dll $(DISTNAME)/Contents/Resources/Libs/IRTK/*.so.1
	-find $(DISTNAME) -name .svn -exec rm -rf '{}' ';' >/dev/null 2>&1
	find $(DISTNAME)/Contents/Resources -name \*.ui -delete
	find $(DISTNAME) -name \*~ -delete
	find $(DISTNAME) -name \*.pxd -delete
	find $(DISTNAME) -name \*.pickle -delete
	mv $(DISTNAME) $(DISTNAME).app
	tar czf $(DISTNAME).tgz $(DISTNAME).app
	rm -rf $(DISTNAME).app

package:
	git pull
	$(MAKE)
	./run.sh --version
ifeq ($(PLAT),osx)
	make appfile DISTNAME=$(shell date '+VizMac_%Y_%m_%d')
else
	make distfile DISTNAME=$(shell date '+VizAll_%Y_%m_%d')
endif

tutorialfile:
	tar czf Tutorials.tgz tutorial

clean:
ifeq ($(PLAT),win64_cygwin)
	rm -rf $(SRC)/*/*.pyd
else ifeq ($(PLAT),osx)
	rm -rf $(SRC)/*/*.dylib 
else
	rm -rf $(SRC)/*/*.so.* 
endif

clean_gen:
	rm -rf $(patsubst %.ui,%.py,$(wildcard $(UI)/*.ui $(PLUGINS)/*.ui))

epydoc:
	-mkdir ./docs/epydoc
	PYTHONPATH=./Libs/python/epydoc-3.0.1-py2.7.egg $(PYTHON) -c 'from epydoc.cli import cli;cli()' $(SRC)/* --graph=all -o ./docs/epydoc

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
	@echo "---------------------------------"

