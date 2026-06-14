import { useEffect, useState } from "react";
import { api, SearchHit } from "../api";

interface Props {
  agentId?: number;
  onSelectAgent?: (id: number) => void;
  onNavigate?: (type: string, agentId: number) => void;
}

export default function GlobalSearch({ agentId, onSelectAgent, onNavigate }: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchHit[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (query.trim().length < 2) {
      setResults([]);
      return;
    }
    const t = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await api.search(query.trim(), agentId);
        setResults(res.results);
        setOpen(true);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 300);
    return () => clearTimeout(t);
  }, [query, agentId]);

  function handleClick(hit: SearchHit) {
    onSelectAgent?.(hit.agent_id);
    onNavigate?.(hit.type, hit.agent_id);
    setOpen(false);
    setQuery("");
  }

  return (
    <div className="global-search">
      <input
        type="search"
        placeholder="Search logs, software, connections..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => query.length >= 2 && setOpen(true)}
      />
      {open && query.length >= 2 && (
        <div className="search-dropdown">
          {loading && <div className="search-item muted">Searching...</div>}
          {!loading && results.length === 0 && <div className="search-item muted">No results</div>}
          {results.map((hit) => (
            <button key={`${hit.type}-${hit.id}`} className="search-item" onClick={() => handleClick(hit)}>
              <span className={`search-type tag`}>{hit.type}</span>
              <strong>{hit.title}</strong>
              <small>{hit.agent_name} · {hit.subtitle}</small>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
