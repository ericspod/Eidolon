# -*- mode: python -*-

block_cipher = None


a = Analysis(['main.py'],
             pathex=['src','src/eidolon','src/renderer','src/ui','src/plugins'],
             binaries=[
                ('EidolonLibs/win64_mingw/bin/cg.dll','EidolonLibs/bin'),
                ('EidolonLibs/win64_mingw/bin/Plugin_CgProgramManager.dll','EidolonLibs/bin'),
                ('EidolonLibs/win64_mingw/bin/RenderSystem_GL.dll','EidolonLibs/bin')
             ],
             datas=[
                ('res','res'),
                ('config.ini','.'),
                ('EidolonLibs/IRTK','EidolonLibs/IRTK'),
                ('EidolonLibs/python','EidolonLibs/python')
             ],
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
