import { useEffect, useState } from "react";
import { api } from "../api";

function BarChart({ data }) {
  const entries = Object.entries(data || {});
  const max = Math.max(1, ...entries.map(([, v]) => v));
  if (entries.length === 0) return <div className="empty">No data yet.</div>;
  return (
    <div>
      {entries.map(([label, count]) => (
        <div className="bar-row" key={label}>
          <span className="label">{label}</span>
          <span className="track"><span style={{ width: `${(count / max) * 100}%` }} /></span>
          <span className="count">{count}</span>
        </div>
      ))}
    </div>
  );
}

export default function Analytics({ refreshKey }) {
  const [data, setData] = useState(null);
  useEffect(() => { api.analytics().then(setData); }, [refreshKey]);
  if (!data) return <div className="body"><div className="panel" style={{ flex: 1 }}>Loading…</div></div>;

  return (
    <div className="body">
      <div style={{ flex: 1 }}>
        <div className="stat-grid">
          <div className="stat"><div className="n">{data.total_emails}</div><div className="l">Total emails</div></div>
          <div className="stat"><div className="n">{data.replied}</div><div className="l">Replied</div></div>
          <div className="stat"><div className="n">{data.escalated}</div><div className="l">Escalated</div></div>
          <div className="stat"><div className="n">{data.auto_handled_pct}%</div><div className="l">Auto-handled</div></div>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <div className="panel">
            <div className="section-title">Emails by category</div>
            <BarChart data={data.by_category} />
          </div>
          <div className="panel">
            <div className="section-title">Emails by sentiment</div>
            <BarChart data={data.by_sentiment} />
          </div>
          <div className="panel" style={{ gridColumn: "1 / -1" }}>
            <div className="section-title">Top escalation reasons</div>
            <BarChart data={data.top_escalation_reasons} />
          </div>
        </div>
      </div>
    </div>
  );
}
