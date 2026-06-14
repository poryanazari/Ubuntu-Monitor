from pathlib import Path

INSTALLER = Path(SPECPATH).parent
PROJECT = INSTALLER.parent
AGENT = PROJECT / "agent"
ENTRY = INSTALLER / "entries" / "agent_linux_entry.py"

a = Analysis(
    [str(ENTRY)],
    pathex=[str(AGENT)],
    binaries=[],
    datas=[
        (str(AGENT / "config.linux.yaml.example"), "."),
    ],
    hiddenimports=[
        "collector",
        "runner",
        "collectors",
        "collectors.common",
        "collectors.connectivity",
        "collectors.containers",
        "collectors.database",
        "collectors.host",
        "collectors.logs",
        "collectors.processes",
        "collectors.web_common",
        "platforms",
        "platforms.linux",
        "yaml",
        "psutil",
        "requests",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["platforms.windows"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ubuntu-monitor-agent",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="ubuntu-monitor-agent-linux",
)
