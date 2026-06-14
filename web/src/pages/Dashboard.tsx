import { useCallback, useEffect, useState } from "react";
import {
  Agent,
  api,
  clearToken,
  Connection,
  DashboardSummary,
  LogEntry,
  MetricSnapshot,
  SoftwareItem,
} from "../api";
import AlertsPanel from "../components/AlertsPanel";
import ExtendedMetricsView from "../components/ExtendedMetricsView";
import GlobalSearch from "../components/GlobalSearch";
import LogsView from "../components/LogsView";
import MetricChart from "../components/MetricChart";
import { hoursForRange, METRIC_CHARTS, MetricChartKey, TIME_RANGES, TimeRangeKey } from "../components/timeRange";

function formatBytesPerSec(bps: number) {
  if (bps < 1024) return `${bps.toFixed(0)} B/s`;
  if (bps < 1024 ** 2) return `${(bps / 1024).toFixed(1)} KB/s`;
  return `${(bps / 1024 ** 2).toFixed(1)} MB/s`;
}

function formatUptime(seconds: number) {
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

type Tab = "overview" | "details" | "software" | "connections" | "logs" | "alerts";

export default function Dashboard() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [metrics, setMetrics] = useState<MetricSnapshot[]>([]);
  const [software, setSoftware] = useState<SoftwareItem[]>([]);
  const [connections, setConnections] = useState<Connection[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [tab, setTab] = useState<Tab>("overview");
  const [timeRange, setTimeRange] = useState<TimeRangeKey>("24h");
  const [chartMetric, setChartMetric] = useState<MetricChartKey>("cpu");
  const [sectionSearch, setSectionSearch] = useState("");
  const [logLevel, setLogLevel] = useState("");
  const [newAgentName, setNewAgentName] = useState("");
  const [showAddAgent, setShowAddAgent] = useState(false);
  const [newAgentKey, setNewAgentKey] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    const [s, a] = await Promise.all([api.getSummary(), api.getAgents()]);
    setSummary(s);
    setAgents(a);
    if (!selectedId && a.length > 0) setSelectedId(a[0].id);
  }, [selectedId]);

  const loadAgentDetail = useCallback(async (agentId: number) => {
    const hours = hoursForRange(timeRange);
    const q = sectionSearch.trim();
    const [m, sw, conn, lg] = await Promise.all([
      api.getMetrics(agentId, hours),
      api.getSoftware(agentId, tab === "software" ? q : ""),
      api.getConnections(agentId, tab === "connections" ? q : ""),
      api.getLogs(agentId, hours, tab === "logs" ? q : "", logLevel),
    ]);
    setMetrics(m);
    setSoftware(sw);
    setConnections(conn);
    setLogs(lg);
  }, [timeRange, sectionSearch, tab, logLevel]);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 15000);
    return () => clearInterval(interval);
  }, [loadData]);

  useEffect(() => {
    if (selectedId) {
      loadAgentDetail(selectedId);
      const interval = setInterval(() => loadAgentDetail(selectedId), 15000);
      return () => clearInterval(interval);
    }
  }, [selectedId, loadAgentDetail]);

  async function handleAddAgent() {
    if (!newAgentName.trim()) return;
    const agent = await api.createAgent(newAgentName.trim(), newAgentName.trim());
    setNewAgentKey(agent.agent_key);
    setNewAgentName("");
    await loadData();
    setSelectedId(agent.id);
  }

  function handleSearchNavigate(type: string) {
    if (type === "log") setTab("logs");
    else if (type === "software") setTab("software");
    else if (type === "connection") setTab("connections");
    else if (type === "agent") setTab("overview");
  }

  const selected = agents.find((a) => a.id === selectedId);
  const latest = metrics.length > 0 ? metrics[metrics.length - 1] : null;
  const chartLabel = METRIC_CHARTS.find((m) => m.key === chartMetric)?.label ?? chartMetric;

  return (
    <div className="dashboard">
      <header className="topbar">
        <div className="topbar-left">
          <div className="logo-icon sm">UM</div>
          <span className="topbar-title">Ubuntu Monitor</span>
        </div>
        <GlobalSearch
          agentId={selectedId ?? undefined}
          onSelectAgent={setSelectedId}
          onNavigate={(type) => handleSearchNavigate(type)}
        />
        <button className="btn-ghost" onClick={() => { clearToken(); window.location.href = "/login"; }}>
          Logout
        </button>
      </header>

      <div className="dashboard-body">
        <aside className="sidebar">
          <div className="sidebar-header">
            <h2>Servers</h2>
            <button className="btn-sm" onClick={() => setShowAddAgent(!showAddAgent)}>+ Add</button>
          </div>

          {showAddAgent && (
            <div className="add-agent-box">
              <input placeholder="Server name" value={newAgentName} onChange={(e) => setNewAgentName(e.target.value)} />
              <button onClick={handleAddAgent}>Create agent</button>
              {newAgentKey && (
                <div className="agent-key-box">
                  <p>Agent key:</p>
                  <code>{newAgentKey}</code>
                </div>
              )}
            </div>
          )}

          <ul className="agent-list">
            {agents.map((agent) => (
              <li
                key={agent.id}
                className={`agent-item ${selectedId === agent.id ? "active" : ""}`}
                onClick={() => setSelectedId(agent.id)}
              >
                <span className={`status-dot ${agent.is_online ? "online" : "offline"}`} />
                <div>
                  <strong>{agent.name}</strong>
                  <small>{agent.ip_address || agent.hostname}</small>
                </div>
              </li>
            ))}
          </ul>
        </aside>

        <main className="main-content">
          {summary && (
            <div className="summary-cards">
              <div className="card stat">
                <span className="stat-label">Servers</span>
                <span className="stat-value">{summary.online_agents}/{summary.total_agents}</span>
                <span className="stat-sub">online</span>
              </div>
              <div className="card stat">
                <span className="stat-label">Avg CPU</span>
                <span className="stat-value">{summary.avg_cpu}%</span>
              </div>
              <div className="card stat">
                <span className="stat-label">Avg RAM</span>
                <span className="stat-value">{summary.avg_memory}%</span>
              </div>
              <div className="card stat">
                <span className="stat-label">Connections</span>
                <span className="stat-value">{summary.total_connections}</span>
              </div>
            </div>
          )}

          {!selected ? (
            <div className="empty-state">
              <h3>No servers yet</h3>
              <p>Add a server and install the agent to start monitoring.</p>
            </div>
          ) : (
            <>
              <div className="server-header">
                <div>
                  <h2>{selected.name}</h2>
                  <p>{selected.os_info} · {selected.ip_address} · Last seen: {selected.last_seen ? new Date(selected.last_seen).toLocaleString() : "—"}</p>
                </div>
                <span className={`badge ${selected.is_online ? "online" : "offline"}`}>
                  {selected.is_online ? "Online" : "Offline"}
                </span>
              </div>

              {latest && (
                <div className="live-metrics">
                  <div className="live-metric"><span>CPU</span><strong>{latest.cpu_percent}%</strong></div>
                  <div className="live-metric"><span>RAM</span><strong>{latest.memory_percent}%</strong></div>
                  <div className="live-metric"><span>Disk</span><strong>{latest.disk_percent}%</strong></div>
                  <div className="live-metric"><span>Network ↑</span><strong>{formatBytesPerSec(latest.network_sent_rate)}</strong></div>
                  <div className="live-metric"><span>Network ↓</span><strong>{formatBytesPerSec(latest.network_recv_rate)}</strong></div>
                  <div className="live-metric"><span>Connections</span><strong>{latest.connection_count}</strong></div>
                  <div className="live-metric"><span>Load</span><strong>{latest.load_average}</strong></div>
                  <div className="live-metric"><span>Uptime</span><strong>{formatUptime(latest.uptime_seconds)}</strong></div>
                </div>
              )}

              <div className="toolbar">
                <div className="time-range">
                  <span className="toolbar-label">Period:</span>
                  {TIME_RANGES.map((r) => (
                    <button
                      key={r.key}
                      className={timeRange === r.key ? "active" : ""}
                      onClick={() => setTimeRange(r.key)}
                    >
                      {r.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="tabs">
                <button className={tab === "overview" ? "active" : ""} onClick={() => { setTab("overview"); setSectionSearch(""); }}>Charts</button>
                <button className={tab === "details" ? "active" : ""} onClick={() => setTab("details")}>Full monitor</button>
                <button className={tab === "software" ? "active" : ""} onClick={() => setTab("software")}>Software ({software.length})</button>
                <button className={tab === "connections" ? "active" : ""} onClick={() => setTab("connections")}>Connections ({connections.length})</button>
                <button className={tab === "logs" ? "active" : ""} onClick={() => setTab("logs")}>Logs ({logs.length})</button>
                <button className={tab === "alerts" ? "active" : ""} onClick={() => setTab("alerts")}>Alerts & Bale</button>
              </div>

              {(tab === "software" || tab === "connections" || tab === "logs") && (
                <div className="section-search">
                  <input
                    type="search"
                    placeholder={`Search ${tab}...`}
                    value={sectionSearch}
                    onChange={(e) => setSectionSearch(e.target.value)}
                  />
                </div>
              )}

              {tab === "overview" && (
                <div className="charts-panel">
                  <div className="metric-picker">
                    {METRIC_CHARTS.map((m) => (
                      <button
                        key={m.key}
                        className={chartMetric === m.key ? "active" : ""}
                        onClick={() => setChartMetric(m.key)}
                      >
                        {m.label}
                      </button>
                    ))}
                  </div>
                  <div className="card chart-card">
                    <h3>{chartLabel} — last {TIME_RANGES.find((r) => r.key === timeRange)?.label}</h3>
                    <MetricChart metrics={metrics} metric={chartMetric} timeRange={timeRange} />
                  </div>
                </div>
              )}

              {tab === "details" && <ExtendedMetricsView data={latest?.extended_metrics ?? null} />}

              {tab === "software" && (
                <div className="card table-card">
                  <table>
                    <thead>
                      <tr><th>Name</th><th>Version</th><th>Category</th><th>Status</th><th>Details</th></tr>
                    </thead>
                    <tbody>
                      {software.map((s) => (
                        <tr key={s.id}>
                          <td>{s.name}</td>
                          <td>{s.version || "—"}</td>
                          <td><span className="tag">{s.category}</span></td>
                          <td><span className={`tag status-${s.status}`}>{s.status}</span></td>
                          <td className="mono">{s.details}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {software.length === 0 && <p className="empty-table">No software found.</p>}
                </div>
              )}

              {tab === "connections" && (
                <div className="card table-card">
                  <table>
                    <thead>
                      <tr><th>Local</th><th>Remote</th><th>Status</th><th>Process</th><th>PID</th></tr>
                    </thead>
                    <tbody>
                      {connections.map((c) => (
                        <tr key={c.id}>
                          <td className="mono">{c.local_addr}</td>
                          <td className="mono">{c.remote_addr || "—"}</td>
                          <td><span className="tag">{c.status}</span></td>
                          <td>{c.process_name || "—"}</td>
                          <td>{c.pid || "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {connections.length === 0 && <p className="empty-table">No connections found.</p>}
                </div>
              )}

              {tab === "logs" && (
                <LogsView
                  logs={logs}
                  search={sectionSearch}
                  onSearchChange={setSectionSearch}
                  level={logLevel}
                  onLevelChange={setLogLevel}
                />
              )}

              {tab === "alerts" && <AlertsPanel agents={agents} />}
            </>
          )}
        </main>
      </div>
    </div>
  );
}
