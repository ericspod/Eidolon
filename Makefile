# Eidolon Biomedical Framework
# Copyright (C) 2016-8 Eric Kerfoot, King's College London, all rights reserved
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
	PLAT=linux
else ifeq ($(KERNEL_NAME),Darwin)
	PLAT=osx
else ifeq ($(findstring MINGW,$(KERNEL_NAME)),MINGW)
	PLAT=win64_mingw
else ifeq ($(findstring CYGWIN,$(KERNEL_NAME)),CYGWIN)
	PLAT=win64_mingw
endif

PYSRC=./eidolon
LIB_HOME = $(PYSRC)/EidolonLibs/$(PLAT)
RESRC=$(PYSRC)/renderer
PLUGINS=$(PYSRC)/plugins
UI=$(PYSRC)/ui

PYTHON=$(shell which python)
PYINST?=pyinstaller

# find the path to the python exe using the registry, this uses cygpath to produce a Cygwin-formatted path
ifeq ($(PLAT),win64_mingw)
	WINVER=3.6
	REG="$(shell cat /proc/registry/HKEY_CURRENT_USER/Software/Python/PythonCore/$(WINVER)/InstallPath/@ 2>/dev/null)"
	ifeq ($(REG),"")
		REG="$(shell cat /proc/registry/HKEY_LOCAL_MACHINE/SOFTWARE/Python/PythonCore/$(WINVER)/InstallPath/@ 2>/dev/null)"
	endif

	ifneq ($(REG),"")
	    PYTHON=$(shell cygpath -u '$(REG)')/python.exe
	endif
	
	SO_SUFFIX=.pyd
endif

PYTHONVER=$(shell $(PYTHON) -V 2>&1)
CYTHONVER=$(shell $(PYTHON) -c "import cython;print(cython.__version__)")
PYTHONLIB=$(shell $(PYTHON) -c "import distutils.sysconfig,os;print(os.path.abspath(distutils.sysconfig.get_python_lib()+'/../..'))")

#--------------------------------------------------------------------------------------

.PHONY: clean clean_gen header all ui renderer pyxlibs distfile tutorialfile app

all: header ui renderer pyxlibs

ui:
	cd $(UI) && $(PYTHON) setup.py
    
renderer:
	cd $(RESRC) && $(PYTHON) setup.py build_ext --inplace

pyxlibs:
	cd $(PYSRC) && $(PYTHON) setup.py build_ext --inplace
	rm -f $(patsubst %.pyx,%.cpp,$(wildcard $(PYSRC)/*.pyx))

distfile: # creates the universal distributable zip file with path DISTNAME.zip
	$(MAKE) ui
	$(eval DISTNAME?=Eidolon_All_$(shell ./run.sh --version 2>&1))
	mkdir $(DISTNAME)
	cp -Rf eidolon tutorial tests res $(DISTNAME)
	cp main.py run.sh run.bat config.ini *.md *.txt *.spec $(DISTNAME)
	find $(DISTNAME) -name .DS_Store -delete
	find $(DISTNAME) -name \*~ -delete
	find $(DISTNAME) -name \*.pickle -delete
	find $(DISTNAME) -name dicomdataset.ini -delete
	find $(DISTNAME) -name \*.pyc -delete
	zip -r $(DISTNAME).zip $(DISTNAME)
	rm -rf $(DISTNAME)
	
app:
	$(MAKE) ui
	./run.sh --version
	rm -rf dist
ifeq ($(PLAT),win64_mingw)
	$(eval DISTNAME?=Eidolon_Win64_$(shell ./run.sh --version 2>&1))
	cp $(LIB_HOME)/bin/*.dll eidolon/renderer
	$(PYINST) --clean PyInstaller.spec
	rm -rf eidolon/renderer/*.dll build
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
	LD_LIBRARY_PATH=$(PYTHONLIB):$(LIB_HOME)/bin $(PYINST) --clean PyInstaller.spec
	rm -rf build
	rm dist/Eidolon/res/*.png
	rm dist/Eidolon/eidolon/EidolonLibs/IRTK/*.exe
	rm dist/Eidolon/eidolon/EidolonLibs/IRTK/*.dll
	find dist/Eidolon/eidolon/EidolonLibs/IRTK/ -type f  ! -name "*.*" -delete
	cd dist/Eidolon && rm -rf libglib-2.0.so.0 libgobject-2.0.so.0 libgpg-error.so.0 share/icons
	cp eidolon/EidolonLibs/linux/lib/libCg.so run.sh dist/Eidolon
	-cd dist && zip -r ../$(DISTNAME).zip Eidolon
endif

clean:
ifeq ($(PLAT),win64_mingw)
	rm -rf $(PYSRC)/*/*.pyd
else ifeq ($(PLAT),osx)
	rm -rf $(PYSRC)/*/*darwin.so
else
	rm -rf $(PYSRC)/*/*linux-gnu.so 
endif

docker:
	docker build -t eidolon .


header:
	@echo "---------------------------------"
	@echo " Eidolon Makefile Variables      "
	@echo "---------------------------------"
	@echo " Kernel name : $(KERNEL_NAME)    "
	@echo " Platform    : $(PLAT)           "
	@echo " Arch        : $(ARCH)           "
	@echo " Python      : $(PYTHON)         "
	@echo " PYTHONLIB   : $(PYTHONLIB)      "
	@echo " PYTHONVER   : $(PYTHONVER)      "
	@echo " CYTHONVER   : $(CYTHONVER)      "
	@echo "---------------------------------"
