# Ubuntu Monitor

A Zabbix-style server monitoring platform with a central dashboard, login, and lightweight agents for Ubuntu/Linux servers.

## Features

- **Login page** with JWT authentication
- **Dashboard** with CPU, RAM, disk, network throughput, connections, load, uptime
- **Charts** for historical metrics (24h)
- **Agent system** — install agents on remote servers; they report to the central server
- **Software detection** — packages (dpkg/rpm), systemd services, notable running processes
- **Connection monitoring** — active network connections with process names

## Architecture

```
┌─────────────┐     HTTP POST      ┌──────────────────┐     REST API    ┌─────────────┐
│   Agent     │ ─────────────────► │  FastAPI Server  │ ◄────────────── │  React Web  │
│ (on server) │   /api/agent/report│  + SQLite DB     │   /api/*        │  Dashboard  │
└─────────────┘                    └──────────────────┘                 └─────────────┘
```

## Quick Start

### 1. Server (central monitoring host)

```bash
cd server
python -m venv venv
# Windows: venv\Scripts\activate
# Linux:   source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Default login: **admin** / **admin123**

### 2. Web dashboard

```bash
cd web
npm install
npm run dev
```

Open http://localhost:5173

### 3. Add a server (agent)

Two platform-specific agents are available:

| Platform | Entry script | Config file |
|----------|--------------|-------------|
| **Linux** (Ubuntu/Debian) | `agent_linux.py` | `config.linux.yaml` |
| **Windows** | `agent_windows.py` | `config.windows.yaml` |
| Auto-detect | `agent.py` | `config.yaml` |

1. Log in to the dashboard
2. Click **+ Add** in the sidebar and create a server
3. Copy the **agent key** shown after creation

**Linux server:**

```bash
cd agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp config.linux.yaml.example config.linux.yaml
# Edit config.linux.yaml: set server_url and agent_key
python3 agent_linux.py
# or: ./run_linux.sh
```

**Windows server:**

```powershell
cd agent
pip install -r requirements.txt
copy config.windows.yaml.example config.windows.yaml
# Edit config.windows.yaml: set server_url and agent_key
python agent_windows.py
# or: run_windows.bat
```

For production on Linux, install as a systemd service: `sudo ./install_service.sh` (see [installer/README.md](installer/README.md)).

### Agent config

```yaml
server_url: "http://YOUR_SERVER_IP:8000"
agent_key: "paste-key-from-dashboard"
interval_seconds: 30
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/auth/login` | Login |
| `GET /api/dashboard/summary` | Dashboard totals |
| `GET /api/agents` | List agents |
| `POST /api/agents` | Register new agent (get key) |
| `GET /api/agents/{id}/metrics` | Metric history |
| `GET /api/agents/{id}/software` | Software inventory |
| `GET /api/agents/{id}/connections` | Connections |
| `POST /api/agent/report` | Agent report (header: `X-Agent-Key`) |

## Security notes

- Change default admin password after first login
- Set `SECRET_KEY` in server `.env` for production
- Use HTTPS in production
- Agent key authenticates each server — treat it like a password

## Project structure

```
Ubuntu-Monitor/
├── server/          # FastAPI backend
│   └── app/
├── agent/           # Monitoring agents
│   ├── agent_linux.py      # Linux entry
│   ├── agent_windows.py    # Windows entry
│   ├── agent.py            # Auto-detect
│   ├── platforms/
│   │   ├── linux.py        # systemd, dpkg, syslog
│   │   └── windows.py      # services, registry, event log
│   └── collectors/         # Shared (CPU, RAM, network, ...)
└── web/             # React dashboard
```

## Monitored metrics (Zabbix-style coverage)

### 1. Host resources
- **CPU**: overall %, per-core %, load average (1/5/15 min), running/waiting processes
- **Memory**: used/free, cache/buffers, swap usage
- **Disk**: per-partition usage, inode usage, read/write MB/s, I/O wait
- **Network**: Mbps throughput, packets/s, errors/drops, TCP states (ESTABLISHED, TIME_WAIT, …)

### 2. OS level
- Process count, zombies, top CPU/RAM processes
- Syslog/kernel/auth log errors, dmesg warnings
- NTP sync and offset, kernel version
- Logged-in users, failed SSH attempts
- Critical systemd services (sshd, nginx, mysql, …)

### 3. Databases (auto-detected)
- PostgreSQL, MySQL/MariaDB, Redis: availability, connections, version/memory

### 4. Web & application
- HTTP checks (localhost), response time, status codes
- SSL certificate expiry
- Nginx/Apache status, app process memory (Python/Node/Java)

### 5. External connectivity
- Ping latency & packet loss (8.8.8.8, 1.1.1.1)
- DNS resolution test
- Port checks (22, 80, 443, 3306, 5432, 6379)

### 6. Security
- Failed SSH logins, open/listening ports, unexpected ports
- Root processes sample, large log files
- Kernel version, available security updates (apt)

### 7. Containers / cloud
- Docker: containers, images, running/exited counts
- Kubernetes: nodes and pods (if `kubectl` available)

View all details in the dashboard tab **Full monitor**.

**Note:** If you already ran the server before this update, delete `server/monitor.db` to apply the new schema (or migrate manually).

## Offline / air-gapped install

For internal networks **without internet**:

```powershell
cd installer\scripts
.\package_release.ps1
```

Copy ZIPs from `dist/releases/` to target servers. Full guide: [installer/README.md](installer/README.md).

| Package | Description |
|---------|-------------|
| `ubuntu-monitor-server-portable-windows.zip` | Server + dashboard + Python venv (no install needed) |
| `ubuntu-monitor-agent-windows.zip` | Compiled Windows agent (`ubuntu-monitor-agent.exe`) |

Open `http://SERVER_IP:8000` after starting the server — dashboard is included.
