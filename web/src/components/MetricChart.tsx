import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { MetricSnapshot } from "../api";
import { formatChartTime, MetricChartKey, TimeRangeKey } from "./timeRange";

function formatNetwork(bps: number) {
  if (bps < 1024) return `${bps.toFixed(0)} B/s`;
  if (bps < 1024 ** 2) return `${(bps / 1024).toFixed(1)} KB/s`;
  return `${(bps / 1024 ** 2).toFixed(1)} MB/s`;
}

interface Props {
  metrics: MetricSnapshot[];
  metric: MetricChartKey;
  timeRange: TimeRangeKey;
}

export default function MetricChart({ metrics, metric, timeRange }: Props) {
  const data = metrics.map((m) => ({
    time: formatChartTime(m.timestamp, timeRange),
    cpu: m.cpu_percent,
    memory: m.memory_percent,
    disk: m.disk_percent,
    sent: m.network_sent_rate,
    recv: m.network_recv_rate,
    connections: m.connection_count,
    load: m.load_average,
    memory_mb: m.memory_used_mb,
  }));

  if (data.length === 0) {
    return <p className="empty-table">No data for selected time range.</p>;
  }

  if (metric === "network") {
    return (
      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2a2f3a" />
          <XAxis dataKey="time" stroke="#8b95a8" fontSize={10} interval="preserveStartEnd" />
          <YAxis stroke="#8b95a8" fontSize={11} tickFormatter={(v) => formatNetwork(v)} />
          <Tooltip
            contentStyle={{ background: "#1a1f2e", border: "1px solid #2a2f3a" }}
            formatter={(v: number) => formatNetwork(v)}
          />
          <Legend />
          <Area type="monotone" dataKey="sent" name="Upload" stroke="#f59e0b" fill="#f59e0b40" />
          <Area type="monotone" dataKey="recv" name="Download" stroke="#8b5cf6" fill="#8b5cf640" />
        </AreaChart>
      </ResponsiveContainer>
    );
  }

  const key = metric === "memory" ? "memory" : metric === "cpu" ? "cpu" : metric === "disk" ? "disk" : metric === "load" ? "load" : "connections";
  const name = metric.toUpperCase();
  const color = { cpu: "#3b82f6", memory: "#10b981", disk: "#f59e0b", connections: "#ef4444", load: "#8b5cf6" }[metric] || "#3b82f6";

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#2a2f3a" />
        <XAxis dataKey="time" stroke="#8b95a8" fontSize={10} interval="preserveStartEnd" />
        <YAxis stroke="#8b95a8" fontSize={11} domain={metric === "connections" || metric === "load" ? ["auto", "auto"] : [0, 100]} />
        <Tooltip contentStyle={{ background: "#1a1f2e", border: "1px solid #2a2f3a" }} />
        <Legend />
        <Line type="monotone" dataKey={key} name={name} stroke={color} dot={false} strokeWidth={2} />
      </LineChart>
    </ResponsiveContainer>
  );
}
