# Ubuntu Monitor — Installers (offline / air-gapped)

Deploy on **internal networks without internet** using pre-built packages.

## Package types

| Package | Folder / ZIP | Needs Python on target? |
|---------|----------------|-------------------------|
| **Server (portable)** | `ubuntu-monitor-server-portable-windows` | No (venv included) |
| **Agent Windows (compiled)** | `ubuntu-monitor-agent-windows` | No |
| **Agent Linux (compiled)** | `ubuntu-monitor-agent-linux` | No (build on Linux) |
| **Offline venv** | `ubuntu-monitor-*-offline-*` | Yes (3.10+) |

Ready-made ZIPs: `dist/releases/*.zip`

---

## Step 1 — Build PC (with internet)

### Quick build (Windows)

```powershell
cd installer\scripts
.\package_release.ps1
```

This creates:

- `dist/ubuntu-monitor-server-portable-windows/` + ZIP
- `dist/ubuntu-monitor-agent-windows/` + ZIP (compiled `.exe`)

### All build scripts

| Script | Output |
|--------|--------|
| `build_server_portable.ps1` | Server + dashboard + venv (recommended for server) |
| `build_server.ps1` | PyInstaller server (needs Python 3.11+ on build PC) |
| `build_agent_windows.ps1` | Compiled Windows agent |
| `build_agent_linux.sh` | Compiled Linux agent + systemd install scripts |
| `build_agent_portable_linux.sh` | Portable Linux agent (venv) + systemd |
| `download_offline_packages.ps1` | Download wheels to `installer/wheels/` |
| `offline_install_server.ps1` | Offline venv server from wheels |
| `offline_install_agent_windows.ps1` | Offline venv agent from wheels |
| `package_release.ps1` | ZIP portable server + compiled agent |

Linux server portable:

```bash
cd installer/scripts
./build_server_portable.sh
./build_agent_linux.sh
```

### Download wheels only (for offline `pip install`)

```powershell
.\download_offline_packages.ps1
```

```bash
./download_offline_packages.sh
```

Then on air-gapped machine with Python:

```powershell
.\offline_install_server.ps1
.\offline_install_agent_windows.ps1
```

---

## Step 2 — Target servers (no internet)

Copy ZIP or folder via USB / internal share.

### Monitoring server

**Portable (recommended):**

1. Unzip `ubuntu-monitor-server-portable-windows.zip`
2. Copy `server\.env.example` to `server\.env` and edit (`SECRET_KEY`, Bale token, …)
3. Run `start_server.bat`
4. Open `http://SERVER_IP:8000` — login `admin` / `admin123`

Dashboard is bundled — no `npm` or separate web server.

### Windows agent (compiled)

1. Unzip `ubuntu-monitor-agent-windows.zip`
2. Edit `config.windows.yaml`:

```yaml
server_url: "http://MONITOR_SERVER_IP:8000"
agent_key: "from-dashboard"
interval_seconds: 30
```

3. Run `start_agent.bat`

### Linux agent (systemd service)

Packages include `install_service.sh`, `uninstall_service.sh`, and `ubuntu-monitor-agent.service`.

**Compiled** (`build_agent_linux.sh`) or **portable** (`build_agent_portable_linux.sh`):

1. Copy folder to the target server (or build on Linux and copy `dist/ubuntu-monitor-agent-linux`)
2. Edit `config.linux.yaml` (compiled) or `agent/config.linux.yaml` (portable):

```yaml
server_url: "http://MONITOR_SERVER_IP:8000"
agent_key: "from-dashboard"
interval_seconds: 30
```

3. Install as systemd service (default install path `/opt/ubuntu-monitor-agent`):

```bash
chmod +x install_service.sh uninstall_service.sh
sudo ./install_service.sh
```

4. Check status:

```bash
systemctl status ubuntu-monitor-agent
journalctl -u ubuntu-monitor-agent -f
```

Custom install directory:

```bash
sudo ./install_service.sh /usr/local/ubuntu-monitor-agent
```

Remove service (keeps files):

```bash
sudo ./uninstall_service.sh
```

Manual run (without service): `./start_agent.sh`

---

## Notes

- **Server portable** copies the full Python `venv` — works offline, no pip on target.
- **Compiled server** (`build_server.ps1`) may fail on Python 3.10 + SQLAlchemy; use portable or Python 3.11+ for PyInstaller.
- Linux agent must be built on Linux; Windows agent on Windows.
- Bale alerts need outbound HTTPS to `tapi.bale.ai` from the monitoring server only.
- Change default password after first login.
