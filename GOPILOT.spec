# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:/Users/Sulai/OneDrive/Desktop/GOPILOT/app/splash.py'],
    pathex=['C:/Users/Sulai/OneDrive/Desktop/GOPILOT/app'],
    binaries=[],
    datas=[('C:/Users/Sulai/OneDrive/Desktop/GOPILOT/asset', 'asset'), ('C:/Users/Sulai/OneDrive/Desktop/GOPILOT/GoPiliotsplashscreen.ui', '.')],
    hiddenimports=['GOPILOT', 'watchdog.observers'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtWebEngineQuick', 'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtQuickWidgets', 'PySide6.Qt3DCore', 'PySide6.QtCharts', 'PySide6.QtDataVisualization', 'PySide6.QtMultimedia', 'PySide6.QtPdf', 'PySide6.QtPdfWidgets', 'PySide6.QtSql', 'PySide6.QtNetwork', 'PySide6.QtBluetooth', 'PySide6.QtDesigner', 'PySide6.QtHelp', 'PySide6.QtTest', 'tkinter'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='GOPILOT',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:/Users/Sulai/OneDrive/Desktop/GOPILOT/asset/GOPILOT.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='GOPILOT',
)
