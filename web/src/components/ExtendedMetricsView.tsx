import type { ReactNode } from "react";
import { ExtendedMetrics } from "../api";

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="card detail-section">
      <h3>{title}</h3>
      {children}
    </div>
  );
}

function MetricGrid({ items }: { items: Array<{ label: string; value: string | number | null | undefined }> }) {
  return (
    <div className="metric-grid">
      {items.map((item) => (
        <div key={item.label} className="metric-cell">
          <span>{item.label}</span>
          <strong>{item.value ?? "—"}</strong>
        </div>
      ))}
    </div>
  );
}

export default function ExtendedMetricsView({ data }: { data: ExtendedMetrics | null }) {
  if (!data) {
    return <p className="empty-table">Extended metrics not available yet. Wait for agent report.</p>;
  }

  const host = data.host;
  const os = data.os;
  const web = data.web;
  const sec = data.security;
  const conn = data.connectivity;
  const containers = data.containers;

  return (
    <div className="extended-metrics">
      {host && (
        <>
          <Section title="CPU">
            <MetricGrid
              items={[
                { label: "Usage %", value: host.cpu?.percent },
                { label: "Cores", value: host.cpu?.count },
                { label: "Load 1m", value: host.cpu?.load_1 },
                { label: "Load 5m", value: host.cpu?.load_5 },
                { label: "Load 15m", value: host.cpu?.load_15 },
                { label: "Running", value: host.cpu?.processes_running },
                { label: "Waiting", value: host.cpu?.processes_waiting },
              ]}
            />
            {host.cpu?.per_core && (
              <div className="core-bars">
                {host.cpu.per_core.map((c, i) => (
                  <div key={i} className="core-bar">
                    <span>Core {i}</span>
                    <div className="bar-track">
                      <div className="bar-fill" style={{ width: `${Math.min(c, 100)}%` }} />
                    </div>
                    <span>{c}%</span>
                  </div>
                ))}
              </div>
            )}
          </Section>

          <Section title="Memory & Swap">
            <MetricGrid
              items={[
                { label: "Used MB", value: host.memory?.used_mb },
                { label: "Free MB", value: host.memory?.free_mb },
                { label: "Cached MB", value: host.memory?.cached_mb },
                { label: "Buffers MB", value: host.memory?.buffers_mb },
                { label: "Usage %", value: host.memory?.percent },
                { label: "Swap Used MB", value: host.memory?.swap_used_mb },
                { label: "Swap %", value: host.memory?.swap_percent },
              ]}
            />
          </Section>

          <Section title="Disk partitions">
            <table>
              <thead>
                <tr>
                  <th>Mount</th>
                  <th>Used GB</th>
                  <th>Free GB</th>
                  <th>Usage %</th>
                  <th>Inode %</th>
                </tr>
              </thead>
              <tbody>
                {host.disks?.map((d) => (
                  <tr key={d.mountpoint}>
                    <td className="mono">{d.mountpoint}</td>
                    <td>{d.used_gb}</td>
                    <td>{d.free_gb}</td>
                    <td>{d.percent}%</td>
                    <td>{d.inode_percent}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Section>

          <Section title="Disk I/O">
            <MetricGrid
              items={[
                { label: "Read MB/s", value: host.disk_io?.read_mb_sec },
                { label: "Write MB/s", value: host.disk_io?.write_mb_sec },
                { label: "I/O Wait %", value: host.disk_io?.io_wait_percent },
              ]}
            />
          </Section>

          <Section title="Network">
            <MetricGrid
              items={[
                { label: "Sent Mbps", value: host.network?.sent_rate_mbps },
                { label: "Recv Mbps", value: host.network?.recv_rate_mbps },
                { label: "Pkts sent/s", value: host.network?.packets_sent_rate },
                { label: "Pkts recv/s", value: host.network?.packets_recv_rate },
                { label: "Errors in", value: host.network?.errors_in },
                { label: "Errors out", value: host.network?.errors_out },
                { label: "Drops in", value: host.network?.drops_in },
                { label: "Drops out", value: host.network?.drops_out },
              ]}
            />
            {host.network?.tcp_states && (
              <div className="tcp-states">
                {Object.entries(host.network.tcp_states).map(([state, count]) => (
                  <span key={state} className="tag">{state}: {count}</span>
                ))}
              </div>
            )}
          </Section>
        </>
      )}

      {os && (
        <>
          <Section title="Processes">
            <MetricGrid
              items={[
                { label: "Total", value: os.processes?.total },
                { label: "Zombies", value: os.processes?.zombie_count },
                { label: "Logged in", value: os.logins?.logged_in_users },
                { label: "Failed SSH", value: os.logins?.failed_ssh_attempts },
                { label: "NTP synced", value: os.system?.synced ? "Yes" : "No" },
                { label: "NTP offset ms", value: os.system?.offset_ms },
              ]}
            />
            <h4 className="sub-heading">Top CPU</h4>
            <table>
              <thead><tr><th>Process</th><th>PID</th><th>CPU %</th><th>RAM %</th></tr></thead>
              <tbody>
                {os.processes?.top_cpu?.map((p) => (
                  <tr key={p.pid}><td>{p.name}</td><td>{p.pid}</td><td>{p.cpu_percent}%</td><td>{p.memory_percent}%</td></tr>
                ))}
              </tbody>
            </table>
          </Section>

          <Section title="Critical services">
            <table>
              <thead><tr><th>Service</th><th>Status</th></tr></thead>
              <tbody>
                {os.services?.map((s) => (
                  <tr key={s.name}><td>{s.name}</td><td><span className="tag">{s.status}</span></td></tr>
                ))}
              </tbody>
            </table>
          </Section>

          {os.log_errors && os.log_errors.length > 0 && (
            <Section title="Recent log errors">
              <ul className="log-list">
                {os.log_errors.slice(0, 10).map((e, i) => (
                  <li key={i}><span className="tag">{e.source}</span> {e.message}</li>
                ))}
              </ul>
            </Section>
          )}
        </>
      )}

      {data.databases && data.databases.length > 0 && (
        <Section title="Databases">
          <table>
            <thead><tr><th>Type</th><th>Available</th><th>Connections</th><th>Details</th></tr></thead>
            <tbody>
              {data.databases.map((db) => (
                <tr key={db.type}>
                  <td>{db.type}</td>
                  <td>{db.available ? "✓" : "✗"}</td>
                  <td>{db.connections_active ?? "—"}</td>
                  <td className="mono">
                    {[
                      db.version,
                      db.memory_used_mb != null ? `${db.memory_used_mb} MB` : null,
                    ]
                      .filter(Boolean)
                      .join(" · ") || "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Section>
      )}

      {web && (
        <Section title="Web & Application">
          <MetricGrid
            items={[
              { label: "Nginx", value: web.nginx_status },
              { label: "Apache", value: web.apache_status },
              { label: "IIS", value: (web as { iis_status?: string }).iis_status },
              { label: "Error rate %", value: web.error_rate_percent },
            ]}
          />
          <table>
            <thead><tr><th>URL</th><th>Status</th><th>Response ms</th></tr></thead>
            <tbody>
              {web.http_checks?.map((c) => (
                <tr key={c.url}><td className="mono">{c.url}</td><td>{c.status_code}</td><td>{c.response_ms}</td></tr>
              ))}
            </tbody>
          </table>
        </Section>
      )}

      {conn && (
        <Section title="External connectivity">
          <MetricGrid
            items={[
              { label: "DNS OK", value: conn.dns?.ok ? "Yes" : "No" },
              { label: "DNS resolved", value: conn.dns?.resolved },
            ]}
          />
          <table>
            <thead><tr><th>Target</th><th>Latency ms</th><th>Packet loss %</th></tr></thead>
            <tbody>
              {conn.latency?.map((l) => (
                <tr key={l.target}><td>{l.target}</td><td>{l.latency_ms ?? "—"}</td><td>{l.packet_loss_percent}</td></tr>
              ))}
            </tbody>
          </table>
          <h4 className="sub-heading">Port availability</h4>
          <div className="tcp-states">
            {conn.ports?.map((p) => (
              <span key={p.port} className={`tag ${p.open ? "tag-ok" : "tag-bad"}`}>
                {p.port}: {p.open ? "open" : "closed"}
              </span>
            ))}
          </div>
        </Section>
      )}

      {sec && (
        <Section title="Security">
          <MetricGrid
            items={[
              { label: "Failed SSH", value: sec.failed_ssh_attempts },
              { label: "Root processes", value: sec.root_process_count },
              { label: "Kernel", value: sec.kernel_version },
              { label: "Security updates", value: sec.security_updates_available },
            ]}
          />
          {sec.unexpected_ports?.length > 0 && (
            <p>Unexpected ports: {sec.unexpected_ports.join(", ")}</p>
          )}
        </Section>
      )}

      {containers && (containers.docker || containers.kubernetes) && (
        <Section title="Containers / Cloud">
          {containers.docker && (
            <MetricGrid
              items={[
                { label: "Docker version", value: containers.docker.version },
                { label: "Running", value: containers.docker.running },
                { label: "Exited", value: containers.docker.exited },
                { label: "Images", value: containers.docker.image_count },
              ]}
            />
          )}
          {containers.kubernetes && (
            <MetricGrid
              items={[
                { label: "K8s nodes", value: containers.kubernetes.node_count },
                { label: "Pods", value: containers.kubernetes.pod_count },
                { label: "Running pods", value: containers.kubernetes.running_pods },
              ]}
            />
          )}
        </Section>
      )}
    </div>
  );
}
