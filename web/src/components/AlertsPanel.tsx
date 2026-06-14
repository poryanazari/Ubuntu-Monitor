import { useCallback, useEffect, useState } from "react";
import {
  Agent,
  AlertMetric,
  AlertRule,
  api,
  NotificationChannel,
  NotificationLog,
  BaleChat,
} from "../api";

const OPERATORS = [
  { value: "gt", label: ">" },
  { value: "gte", label: ">=" },
  { value: "lt", label: "<" },
  { value: "lte", label: "<=" },
  { value: "eq", label: "=" },
];

const emptyRule = {
  name: "",
  agent_id: null as number | null,
  channel_id: 0,
  metric: "cpu_percent",
  operator: "gt",
  threshold: 80,
  severity: "warning",
  cooldown_minutes: 5,
  enabled: true,
  notify_recovery: true,
};

export default function AlertsPanel({ agents }: { agents: Agent[] }) {
  const [channels, setChannels] = useState<NotificationChannel[]>([]);
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [metrics, setMetrics] = useState<AlertMetric[]>([]);
  const [logs, setLogs] = useState<NotificationLog[]>([]);
  const [baleStatus, setBaleStatus] = useState<{
    configured: boolean;
    connected?: boolean;
    bot?: { username?: string };
    error?: string;
  } | null>(null);
  const [discoveredChats, setDiscoveredChats] = useState<BaleChat[]>([]);
  const [newChannel, setNewChannel] = useState({ name: "Monitor Group", chat_id: "", enabled: true });
  const [ruleForm, setRuleForm] = useState(emptyRule);
  const [editingRuleId, setEditingRuleId] = useState<number | null>(null);
  const [msg, setMsg] = useState("");

  const load = useCallback(async () => {
    const [ch, ru, me, lg, st] = await Promise.all([
      api.getChannels(),
      api.getRules(),
      api.getAlertMetrics(),
      api.getNotificationLogs(),
      api.getBaleStatus(),
    ]);
    setChannels(ch);
    setRules(ru);
    setMetrics(me);
    setLogs(lg);
    setBaleStatus(st);
    if (ch.length > 0 && ruleForm.channel_id === 0) {
      setRuleForm((f) => ({ ...f, channel_id: ch[0].id }));
    }
  }, [ruleForm.channel_id]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleDiscover() {
    try {
      const chats = await api.discoverBaleChats();
      setDiscoveredChats(chats);
      setMsg(chats.length ? `Found ${chats.length} chat(s)` : "No chats — add bot to group and send a message");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Discover failed");
    }
  }

  async function handleTestChat(chatId: string) {
    try {
      await api.testBale(chatId);
      setMsg("Test message sent!");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Test failed");
    }
  }

  async function handleAddChannel() {
    if (!newChannel.chat_id.trim()) return;
    await api.createChannel(newChannel.name, newChannel.chat_id.trim());
    setNewChannel({ name: "Monitor Group", chat_id: "", enabled: true });
    await load();
    setMsg("Channel added");
  }

  async function handleSaveRule() {
    if (!ruleForm.name || !ruleForm.channel_id) return;
    const payload = { ...ruleForm, agent_id: ruleForm.agent_id || null };
    if (editingRuleId) {
      await api.updateRule(editingRuleId, payload);
    } else {
      await api.createRule(payload);
    }
    setRuleForm(emptyRule);
    setEditingRuleId(null);
    await load();
    setMsg("Rule saved");
  }

  async function handleDeleteRule(id: number) {
    await api.deleteRule(id);
    await load();
  }

  function startEdit(rule: AlertRule) {
    setEditingRuleId(rule.id);
    setRuleForm({
      name: rule.name,
      agent_id: rule.agent_id,
      channel_id: rule.channel_id,
      metric: rule.metric,
      operator: rule.operator,
      threshold: rule.threshold,
      severity: rule.severity,
      cooldown_minutes: rule.cooldown_minutes,
      enabled: rule.enabled,
      notify_recovery: rule.notify_recovery,
    });
  }

  return (
    <div className="alerts-panel">
      {msg && <div className="alert-banner">{msg}</div>}

      <div className="card detail-section">
        <h3>Bale notifications</h3>
        <p className="hint">
          Bale group chat id: use <strong>@your_group_id</strong> format (with @), not only numbers.
          Add bot to group, send a message, then Discover chats.
        </p>
        <div className="metric-grid">
          <div className="metric-cell">
            <span>Token configured</span>
            <strong>{baleStatus?.configured ? "Yes" : "No — add BALE_BOT_TOKEN to server/.env"}</strong>
          </div>
          {baleStatus?.configured && (
            <div className="metric-cell">
              <span>Bale API</span>
              <strong>{baleStatus.connected ? "Connected" : `Error: ${baleStatus.error ?? "offline"}`}</strong>
            </div>
          )}
          {baleStatus?.bot?.username && (
            <div className="metric-cell">
              <span>Bot username</span>
              <strong>{baleStatus.bot.username}</strong>
            </div>
          )}
        </div>
        <div className="alerts-actions">
          <button className="btn-sm" onClick={handleDiscover}>Discover group chats</button>
        </div>
        {discoveredChats.length > 0 && (
          <table>
            <thead><tr><th>Chat ID</th><th>Title</th><th>Type</th><th></th></tr></thead>
            <tbody>
              {discoveredChats.map((c) => (
                <tr key={c.chat_id}>
                  <td className="mono">{c.chat_id}</td>
                  <td>{c.title}</td>
                  <td>{c.type}</td>
                  <td>
                    <button className="btn-ghost-sm" onClick={() => setNewChannel({ ...newChannel, chat_id: c.chat_id })}>Use</button>
                    <button className="btn-ghost-sm" onClick={() => handleTestChat(c.chat_id)}>Test</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div className="channel-form">
          <input placeholder="Channel name" value={newChannel.name} onChange={(e) => setNewChannel({ ...newChannel, name: e.target.value })} />
          <input placeholder="Group chat_id" value={newChannel.chat_id} onChange={(e) => setNewChannel({ ...newChannel, chat_id: e.target.value })} />
          <button className="btn-sm" onClick={handleAddChannel}>Add channel</button>
        </div>
        {channels.length > 0 && (
          <ul className="channel-list">
            {channels.map((c) => (
              <li key={c.id}>
                <strong>{c.name}</strong> <span className="mono">{c.chat_id}</span>
                <span className={`tag ${c.enabled ? "tag-ok" : ""}`}>{c.enabled ? "active" : "disabled"}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="card detail-section">
        <h3>Alert rules (Zabbix-style)</h3>
        <div className="rule-form-grid">
          <input placeholder="Rule name" value={ruleForm.name} onChange={(e) => setRuleForm({ ...ruleForm, name: e.target.value })} />
          <select value={ruleForm.agent_id ?? ""} onChange={(e) => setRuleForm({ ...ruleForm, agent_id: e.target.value ? Number(e.target.value) : null })}>
            <option value="">All servers</option>
            {agents.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
          </select>
          <select value={ruleForm.channel_id} onChange={(e) => setRuleForm({ ...ruleForm, channel_id: Number(e.target.value) })}>
            <option value={0}>Select channel</option>
            {channels.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
          <select value={ruleForm.metric} onChange={(e) => setRuleForm({ ...ruleForm, metric: e.target.value })}>
            {metrics.map((m) => <option key={m.key} value={m.key}>{m.label}</option>)}
          </select>
          <select value={ruleForm.operator} onChange={(e) => setRuleForm({ ...ruleForm, operator: e.target.value })}>
            {OPERATORS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <input type="number" placeholder="Threshold" value={ruleForm.threshold} onChange={(e) => setRuleForm({ ...ruleForm, threshold: Number(e.target.value) })} />
          <select value={ruleForm.severity} onChange={(e) => setRuleForm({ ...ruleForm, severity: e.target.value })}>
            <option value="warning">Warning</option>
            <option value="critical">Critical</option>
          </select>
          <input type="number" placeholder="Cooldown min" value={ruleForm.cooldown_minutes} onChange={(e) => setRuleForm({ ...ruleForm, cooldown_minutes: Number(e.target.value) })} />
          <label className="checkbox-label">
            <input type="checkbox" checked={ruleForm.notify_recovery} onChange={(e) => setRuleForm({ ...ruleForm, notify_recovery: e.target.checked })} />
            Notify on recovery
          </label>
          <button className="btn-sm" onClick={handleSaveRule}>{editingRuleId ? "Update rule" : "Add rule"}</button>
        </div>

        <table>
          <thead>
            <tr>
              <th>Name</th><th>Server</th><th>Condition</th><th>Channel</th><th>Severity</th><th>Status</th><th></th>
            </tr>
          </thead>
          <tbody>
            {rules.map((r) => (
              <tr key={r.id}>
                <td>{r.name}</td>
                <td>{r.agent_id ? agents.find((a) => a.id === r.agent_id)?.name ?? r.agent_id : "All"}</td>
                <td className="mono">{metrics.find((m) => m.key === r.metric)?.label ?? r.metric} {r.operator} {r.threshold}</td>
                <td>{r.channel_name}</td>
                <td><span className={`tag level-${r.severity}`}>{r.severity}</span></td>
                <td>{r.enabled ? "on" : "off"}</td>
                <td>
                  <button className="btn-ghost-sm" onClick={() => startEdit(r)}>Edit</button>
                  <button className="btn-ghost-sm" onClick={() => handleDeleteRule(r.id)}>Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {rules.length === 0 && <p className="empty-table">No rules yet. Example: CPU &gt; 80% for 5 min cooldown.</p>}
      </div>

      <div className="card detail-section">
        <h3>Notification history</h3>
        <table>
          <thead><tr><th>Time</th><th>Type</th><th>Severity</th><th>Status</th><th>Message</th></tr></thead>
          <tbody>
            {logs.slice(0, 50).map((l) => (
              <tr key={l.id}>
                <td className="mono">{new Date(l.created_at).toLocaleString()}</td>
                <td>{l.event_type}</td>
                <td><span className={`tag level-${l.severity}`}>{l.severity}</span></td>
                <td>{l.success ? "✓" : "✗"}</td>
                <td className="log-message">{l.message.split("\n")[0]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
