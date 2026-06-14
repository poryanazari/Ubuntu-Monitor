export type TimeRangeKey = "1h" | "6h" | "24h" | "7d" | "30d";

export const TIME_RANGES: { key: TimeRangeKey; label: string; hours: number }[] = [
  { key: "1h", label: "1 hour", hours: 1 },
  { key: "6h", label: "6 hours", hours: 6 },
  { key: "24h", label: "24 hours", hours: 24 },
  { key: "7d", label: "7 days", hours: 168 },
  { key: "30d", label: "30 days", hours: 720 },
];

export function hoursForRange(key: TimeRangeKey): number {
  return TIME_RANGES.find((r) => r.key === key)?.hours ?? 24;
}

export function formatChartTime(iso: string, range: TimeRangeKey): string {
  const d = new Date(iso);
  if (range === "1h" || range === "6h") {
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }
  if (range === "24h") {
    return d.toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  }
  return d.toLocaleString([], { month: "short", day: "numeric", hour: "2-digit" });
}

export type MetricChartKey = "cpu" | "memory" | "disk" | "network" | "connections" | "load";

export const METRIC_CHARTS: { key: MetricChartKey; label: string; unit: string }[] = [
  { key: "cpu", label: "CPU", unit: "%" },
  { key: "memory", label: "RAM", unit: "%" },
  { key: "disk", label: "Disk", unit: "%" },
  { key: "network", label: "Network", unit: "B/s" },
  { key: "connections", label: "Connections", unit: "" },
  { key: "load", label: "Load avg", unit: "" },
];
