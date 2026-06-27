import { useEffect, useState } from "react";
import { api } from "../api";

export default function KnowledgeBase() {
  const [articles, setArticles] = useState([]);
  const [query, setQuery] = useState("");
  const [preview, setPreview] = useState(null);

  const load = () => api.listKB().then(setArticles);
  useEffect(() => { load(); }, []);

  const runPreview = () => {
    if (query.trim().length < 2) return;
    api.previewKB(query).then(setPreview);
  };

  return (
    <div className="body">
      <div className="panel" style={{ flex: 1 }}>
        <div className="section-title">RAG retrieval preview</div>
        <p style={{ fontSize: 13, color: "#64748b", marginTop: 0 }}>
          See which KB chunks the AI would retrieve for a given customer message.
        </p>
        <div className="toolbar">
          <input type="text" style={{ flex: 1 }} placeholder="e.g. my parcel is lost, where is my refund…"
            value={query} onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && runPreview()} />
          <button className="btn" onClick={runPreview}>Preview</button>
        </div>
        {preview && (
          <div style={{ marginBottom: 16 }}>
            {preview.results.map((r) => (
              <div key={r.id} style={{ borderLeft: "3px solid #2b3a8c", paddingLeft: 10, marginBottom: 8 }}>
                <b>{r.title}</b> <span className="kb-chip">score {r.score}</span>
                <div style={{ fontSize: 13, color: "#475569" }}>{r.content.slice(0, 160)}…</div>
              </div>
            ))}
          </div>
        )}

        <div className="section-title">Knowledge base ({articles.length} articles)</div>
        {articles.map((a) => (
          <div key={a.id} style={{ borderBottom: "1px solid #e2e8f0", padding: "10px 0" }}>
            <div><b>{a.title}</b> {a.category && <span className="kb-chip">{a.category}</span>}</div>
            <div style={{ fontSize: 13, color: "#475569" }}>{a.content.slice(0, 200)}…</div>
          </div>
        ))}
      </div>
    </div>
  );
}
