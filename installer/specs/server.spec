from pathlib import Path

INSTALLER = Path(SPECPATH).parent
PROJECT = INSTALLER.parent
SERVER = PROJECT / "server"
WEB_DIST = PROJECT / "web" / "dist"
ENTRY = INSTALLER / "entries" / "server_entry.py"
APP_DIR = SERVER / "app"

if not WEB_DIST.is_dir():
    raise SystemExit(f"Build web UI first: cd web && npm run build (missing {WEB_DIST})")

app_scripts = [str(p) for p in APP_DIR.rglob("*.py")]

a = Analysis(
    [str(ENTRY)] + app_scripts,
    pathex=[str(SERVER)],
    binaries=[],
    datas=[
        (str(WEB_DIST), "web/dist"),
        (str(SERVER / ".env.example"), "."),
    ],
    hiddenimports=[
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
        "anyio._backends._asyncio",
        "bcrypt",
        "aiosqlite",
        "httpx",
        "jose",
        "multipart",
    ],
    hookspath=[],
    hooksconfig={
        "sqlalchemy": {
            "include_dialects": ["sqlite"],
        },
    },
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "pandas"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ubuntu-monitor-server",
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
    name="ubuntu-monitor-server",
)
