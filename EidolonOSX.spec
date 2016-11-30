# -*- mode: python -*-

block_cipher = None

from PyInstaller import compat

binaries=[(compat.base_prefix+'/lib/libmkl*.dylib','')]

#binaries+=[
#('EidolonLibs/osx/bin/Ogre.framework/Ogre','EidolonLibs/bin'),
#('EidolonLibs/osx/bin/OgreOverlay.framework/OgreOverlay','EidolonLibs/bin'),
#('EidolonLibs/osx/bin/Cg.framework/Cg','EidolonLibs/bin'),
#('EidolonLibs/osx/bin/Plugin_CgProgramManager.framework/Plugin_CgProgramManager','EidolonLibs/bin'),
#('EidolonLibs/osx/bin/RenderSystem_GL.framework/RenderSystem_GL','EidolonLibs/bin')
#]

datas=[
	('res','res'),
	('config.ini','.'),
	('EidolonLibs/IRTK','EidolonLibs/IRTK'),
	('EidolonLibs/python','EidolonLibs/python'),
	('EidolonLibs/osx/bin/Ogre.framework','Contents/Frameworks/Ogre.framework'),
	('EidolonLibs/osx/bin/OgreOverlay.framework','Contents/Frameworks/OgreOverlay.framework'),
	('EidolonLibs/osx/bin/Cg.framework','Contents/Frameworks/Cg.framework'),
	('EidolonLibs/osx/bin/Plugin_CgProgramManager.framework','Contents/Frameworks/Plugin_CgProgramManager.framework'),
	('EidolonLibs/osx/bin/RenderSystem_GL.framework','Contents/Frameworks/RenderSystem_GL.framework')
]


a = Analysis(['main.py'],
             pathex=['src','src/eidolon','src/renderer','src/ui','src/plugins'],
             binaries=binaries,
             datas=datas,
             hiddenimports=['numpy', 'scipy','PyQt4.uic'],
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
               name='Eidolon')
