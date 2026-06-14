import { LogEntry } from "../api";

interface Props {
  logs: LogEntry[];
  search: string;
  onSearchChange: (v: string) => void;
  level: string;
  onLevelChange: (v: string) => void;
}

export default function LogsView({ logs, search, onSearchChange, level, onLevelChange }: Props) {
  return (
    <div className="logs-view">
      <div className="logs-filters">
        <input
          type="search"
          placeholder="Filter logs..."
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
        />
        <select value={level} onChange={(e) => onLevelChange(e.target.value)}>
          <option value="">All levels</option>
          <option value="critical">Critical</option>
          <option value="error">Error</option>
          <option value="warning">Warning</option>
          <option value="info">Info</option>
        </select>
      </div>
      <div className="card table-card logs-table">
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Source</th>
              <th>Level</th>
              <th>Message</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id} className={`log-level-${log.level}`}>
                <td className="mono">{new Date(log.timestamp).toLocaleString()}</td>
                <td><span className="tag">{log.source}</span></td>
                <td><span className={`tag level-${log.level}`}>{log.level}</span></td>
                <td className="log-message">{log.message}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {logs.length === 0 && <p className="empty-table">No logs stored yet. Agent will collect on next cycle.</p>}
      </div>
    </div>
  );
}
