import { useEffect, useState } from "react";
import { api } from "./api";
import Inbox from "./components/Inbox";
import Analytics from "./components/Analytics";
import KnowledgeBase from "./components/KnowledgeBase";
import SimulateModal from "./components/SimulateModal";

const TABS = ["Inbox", "Escalations", "Analytics", "Knowledge Base"];

export default function App() {
  const [tab, setTab] = useState("Inbox");
  const [refreshKey, setRefreshKey] = useState(0);
  const [showSim, setShowSim] = useState(false);
  const [health, setHealth] = useState(null);
  const [gmail, setGmail] = useState(null);

  const bump = () => setRefreshKey((k) => k + 1);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth({ status: "down" }));
    api.gmailStatus().then(setGmail).catch(() => {});
  }, [refreshKey]);

  const poll = async () => { await api.gmailPoll(); bump(); };

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>AI Email Automation</h1>
          <div className="sub">
            {health?.llm_configured
              ? `${health.llm_provider} ✓ (${health.chat_model})`
              : `${health?.llm_provider || "LLM"} not configured`}
            {" · "}
            {gmail?.connected ? `Gmail: ${gmail.email}` : "Gmail not connected"}
            {health?.reply_mode ? ` · mode: ${health.reply_mode}` : ""}
          </div>
        </div>
        <nav className="tabs">
          {TABS.map((t) => (
            <button key={t} className={`tab ${tab === t ? "active" : ""}`} onClick={() => setTab(t)}>
              {t}
            </button>
          ))}
        </nav>
        <div style={{ display: "flex", gap: 8 }}>
          {gmail?.connected ? (
            <button className="btn ghost" onClick={poll}>↻ Poll Gmail</button>
          ) : (
            <a className="btn ghost" href="/api/gmail/connect" target="_blank" rel="noreferrer">Connect Gmail</a>
          )}
          <button className="btn" onClick={() => setShowSim(true)}>+ Simulate email</button>
        </div>
      </header>

      {tab === "Inbox" && <Inbox refreshKey={refreshKey} onChanged={bump} mode="all" />}
      {tab === "Escalations" && <Inbox refreshKey={refreshKey} onChanged={bump} mode="escalated" key="esc" filterStatus="escalated" />}
      {tab === "Analytics" && <Analytics refreshKey={refreshKey} />}
      {tab === "Knowledge Base" && <KnowledgeBase />}

      {showSim && <SimulateModal onClose={() => setShowSim(false)} onCreated={bump} />}
    </div>
  );
}
