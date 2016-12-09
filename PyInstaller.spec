# -*- mode: python -*-

block_cipher = None

from PyInstaller import compat
from glob import glob
import platform

pathex=['src']
binaries=[]
hiddenimports=['numpy', 'scipy','PyQt4.uic','_struct']
outname='Eidolon'
datas=[
	('res','res'), 
	('config.ini','.'), 
	('tests','tests'), 
	('tutorial','tutorial'),
	('EidolonLibs/IRTK','EidolonLibs/IRTK'),
	('EidolonLibs/python','EidolonLibs/python')
]

if compat.is_win:
	binaries=[
		('EidolonLibs/win64_mingw/bin/cg.dll','.'),
		('EidolonLibs/win64_mingw/bin/Plugin_CgProgramManager.dll','.'),
		('EidolonLibs/win64_mingw/bin/RenderSystem_GL.dll','.')
	]
	
elif compat.is_darwin:
	outname+='.app'
	hiddenimports+=['appdirs','packaging','packaging.version','packaging.specifiers','packaging.requirements','packaging.utils','cProfile']	
	datas+=[
		('EidolonLibs/osx/bin/Ogre.framework','Contents/Frameworks/Ogre.framework'),
		('EidolonLibs/osx/bin/OgreOverlay.framework','Contents/Frameworks/OgreOverlay.framework'),
		('EidolonLibs/osx/bin/Cg.framework','Contents/Frameworks/Cg.framework'),
		('EidolonLibs/osx/bin/Plugin_CgProgramManager.framework','Contents/Frameworks/Plugin_CgProgramManager.framework'),
		('EidolonLibs/osx/bin/RenderSystem_GL.framework','Contents/Frameworks/RenderSystem_GL.framework')
	]
else:
	d,v,_=platform.linux_distribution()
	assert d.lower()=='ubuntu'
	libs='EidolonLibs/ubuntu%s/bin'%v[:2]
	binaries+=[(f,'.') for f in glob(libs+'/*')]
	

a = Analysis(['main.py'],
             pathex=pathex,
             binaries=binaries,
             datas=datas,
             hiddenimports=hiddenimports,
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='Eidolon',
          debug=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name=outname)
