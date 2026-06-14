const API_BASE = "/api";

export function getToken(): string | null {
  return localStorage.getItem("token");
}

export function setToken(token: string) {
  localStorage.setItem("token", token);
}

export function clearToken() {
  localStorage.removeItem("token");
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (res.status === 401) {
    clearToken();
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

export const api = {
  login: (username: string, password: string) =>
    request<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),

  getSummary: () => request<DashboardSummary>("/dashboard/summary"),

  getAgents: () => request<Agent[]>("/agents"),

  createAgent: (name: string, hostname: string) =>
    request<Agent>("/agents", {
      method: "POST",
      body: JSON.stringify({ name, hostname }),
    }),

  deleteAgent: (id: number) =>
    request<{ ok: boolean }>(`/agents/${id}`, { method: "DELETE" }),

  getMetrics: (agentId: number, hours = 24) =>
    request<MetricSnapshot[]>(`/agents/${agentId}/metrics?hours=${hours}`),

  getLatestMetrics: (agentId: number) =>
    request<MetricSnapshot>(`/agents/${agentId}/metrics/latest`),

  getSoftware: (agentId: number, q = "") =>
    request<SoftwareItem[]>(`/agents/${agentId}/software${q ? `?q=${encodeURIComponent(q)}` : ""}`),

  getConnections: (agentId: number, q = "") =>
    request<Connection[]>(`/agents/${agentId}/connections${q ? `?q=${encodeURIComponent(q)}` : ""}`),

  getLogs: (agentId: number, hours = 24, q = "", level = "") => {
    const params = new URLSearchParams({ hours: String(hours) });
    if (q) params.set("q", q);
    if (level) params.set("level", level);
    return request<LogEntry[]>(`/agents/${agentId}/logs?${params}`);
  },

  search: (q: string, agentId?: number) => {
    const params = new URLSearchParams({ q });
    if (agentId) params.set("agent_id", String(agentId));
    return request<SearchResponse>(`/search?${params}`);
  },

  getBaleStatus: () =>
    request<{ configured: boolean; connected?: boolean; bot?: { username?: string }; error?: string }>(
      "/notifications/bale/status"
    ),
  discoverBaleChats: () => request<BaleChat[]>("/notifications/bale/chats"),
  testBale: (chatId: string) => request<{ ok: boolean }>("/notifications/bale/test", { method: "POST", body: JSON.stringify({ chat_id: chatId }) }),
  getChannels: () => request<NotificationChannel[]>("/notifications/channels"),
  createChannel: (name: string, chatId: string, enabled = true) =>
    request<NotificationChannel>("/notifications/channels", {
      method: "POST",
      body: JSON.stringify({ name, chat_id: chatId, channel_type: "bale", enabled }),
    }),
  getRules: () => request<AlertRule[]>("/notifications/rules"),
  getAlertMetrics: () => request<AlertMetric[]>("/notifications/metrics"),
  createRule: (rule: Omit<AlertRule, "id" | "created_at" | "channel_name">) =>
    request<AlertRule>("/notifications/rules", { method: "POST", body: JSON.stringify(rule) }),
  updateRule: (id: number, rule: Partial<AlertRule>) =>
    request<AlertRule>(`/notifications/rules/${id}`, { method: "PUT", body: JSON.stringify(rule) }),
  deleteRule: (id: number) => request<{ ok: boolean }>(`/notifications/rules/${id}`, { method: "DELETE" }),
  getNotificationLogs: () => request<NotificationLog[]>("/notifications/logs"),
};

export interface DashboardSummary {
  total_agents: number;
  online_agents: number;
  total_connections: number;
  avg_cpu: number;
  avg_memory: number;
}

export interface Agent {
  id: number;
  name: string;
  hostname: string;
  ip_address: string;
  agent_key: string;
  os_info: string;
  is_online: boolean;
  last_seen: string | null;
  created_at: string;
}

export interface MetricSnapshot {
  id: number;
  agent_id: number;
  timestamp: string;
  cpu_percent: number;
  memory_percent: number;
  memory_used_mb: number;
  memory_total_mb: number;
  disk_percent: number;
  network_sent_rate: number;
  network_recv_rate: number;
  connection_count: number;
  load_average: number;
  uptime_seconds: number;
  extended_metrics: ExtendedMetrics;
}

export interface LogEntry {
  id: number;
  agent_id: number;
  timestamp: string;
  source: string;
  level: string;
  message: string;
  created_at: string;
}

export interface SearchHit {
  type: string;
  id: number;
  agent_id: number;
  agent_name: string;
  title: string;
  subtitle: string;
  timestamp: string | null;
}

export interface SearchResponse {
  query: string;
  total: number;
  results: SearchHit[];
}

export interface ExtendedMetrics {
  host?: {
    cpu?: {
      percent: number;
      per_core: number[];
      count: number;
      load_1: number;
      load_5: number;
      load_15: number;
      processes_running: number;
      processes_waiting: number;
    };
    memory?: {
      used_mb: number;
      free_mb: number;
      cached_mb: number;
      buffers_mb: number;
      percent: number;
      swap_used_mb: number;
      swap_percent: number;
    };
    disks?: Array<{
      mountpoint: string;
      used_gb: number;
      free_gb: number;
      percent: number;
      inode_percent: number;
    }>;
    disk_io?: {
      read_mb_sec: number;
      write_mb_sec: number;
      io_wait_percent: number;
    };
    network?: {
      sent_rate_mbps: number;
      recv_rate_mbps: number;
      packets_sent_rate: number;
      packets_recv_rate: number;
      errors_in: number;
      errors_out: number;
      drops_in: number;
      drops_out: number;
      tcp_states: Record<string, number>;
    };
  };
  os?: {
    processes?: {
      total: number;
      zombie_count: number;
      top_cpu: Array<{ pid: number; name: string; cpu_percent: number; memory_percent: number }>;
    };
    logins?: { logged_in_users: number; failed_ssh_attempts: number };
    system?: { synced: boolean; offset_ms: number | null; kernel_version: string };
    services?: Array<{ name: string; status: string }>;
    log_errors?: Array<{ source: string; message: string }>;
  };
  databases?: Array<{
    type: string;
    available: boolean;
    connections_active?: number;
    version?: string;
    memory_used_mb?: number;
  }>;
  web?: {
    nginx_status: string;
    apache_status: string;
    error_rate_percent: number;
    http_checks?: Array<{ url: string; status_code: number; response_ms: number }>;
  };
  connectivity?: {
    dns?: { ok: boolean; resolved: string };
    latency?: Array<{ target: string; latency_ms: number | null; packet_loss_percent: number }>;
    ports?: Array<{ port: number; open: boolean }>;
  };
  security?: {
    failed_ssh_attempts: number;
    root_process_count: number;
    kernel_version: string;
    security_updates_available: number;
    unexpected_ports: number[];
  };
  containers?: {
    docker?: {
      version: string;
      running: number;
      exited: number;
      image_count: number;
    };
    kubernetes?: {
      node_count: number;
      pod_count: number;
      running_pods: number;
    };
  };
}

export interface SoftwareItem {
  id: number;
  name: string;
  version: string;
  category: string;
  status: string;
  details: string;
  last_seen: string;
}

export interface Connection {
  id: number;
  local_addr: string;
  remote_addr: string;
  status: string;
  pid: number;
  process_name: string;
  timestamp: string;
}

export interface BaleChat {
  chat_id: string;
  title: string;
  type: string;
}

export interface NotificationChannel {
  id: number;
  name: string;
  channel_type: string;
  chat_id: string;
  enabled: boolean;
  created_at: string;
}

export interface AlertMetric {
  key: string;
  label: string;
}

export interface AlertRule {
  id: number;
  name: string;
  agent_id: number | null;
  channel_id: number;
  metric: string;
  operator: string;
  threshold: number;
  severity: string;
  cooldown_minutes: number;
  enabled: boolean;
  notify_recovery: boolean;
  created_at: string;
  channel_name: string;
}

export interface NotificationLog {
  id: number;
  channel_id: number;
  rule_id: number | null;
  agent_id: number | null;
  event_type: string;
  severity: string;
  message: string;
  success: boolean;
  created_at: string;
}
