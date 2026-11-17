# -*- mode: python -*-
# macOS build, run with `make build`.  The Windows build still uses QuadStick.spec.
import re

version = re.search(r"VERSION = '(.+?)'", open('googledrive.py').read()).group(1)

a = Analysis(['QuadStick.py'], datas=[('quadstickx.ico', '.')])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, exclude_binaries=True, name='QuadStick', console=False)
coll = COLLECT(exe, a.binaries, a.datas, name='QuadStick')
app = BUNDLE(coll,
             name='QuadStick.app',
             icon='quadstickx.ico',  # converted to .icns by Pillow; the largest size in it is 48 px
             bundle_identifier='com.quadstick.qmp',
             version=version,
             info_plist={
                 'CFBundleDisplayName': 'QuadStick Manager Program',
                 'NSHighResolutionCapable': True,
                 # opening a .qmp file starts QMP, as the Windows installer sets up
                 'CFBundleDocumentTypes': [{
                     'CFBundleTypeName': 'QuadStick game profile link',
                     'CFBundleTypeExtensions': ['qmp'],
                     'CFBundleTypeRole': 'Viewer',
                     'LSHandlerRank': 'Owner',
                 }],
             })
