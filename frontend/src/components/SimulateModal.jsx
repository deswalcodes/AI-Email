import { useState } from "react";
import { api } from "../api";

const SAMPLES = {
  "Angry delivery": {
    sender: "marcus@example.com", sender_name: "Marcus Lee",
    subject: "Where is my order?! 5 days late",
    body: "This is absolutely unacceptable. I paid for express shipping and my order still hasn't arrived after 5 days. The tracking hasn't updated at all. I want this sorted NOW or I'm done with you.",
  },
  "Legal threat": {
    sender: "angela@example.com", sender_name: "Angela Cruz",
    subject: "GDPR data request + possible legal action",
    body: "I am formally requesting deletion of all my personal data under GDPR. If this is not handled within the legal timeframe I will be contacting my solicitor and filing a complaint with the ICO.",
  },
  "Refund question": {
    sender: "priya@example.com", sender_name: "Priya N",
    subject: "How do I return a jacket?",
    body: "Hi, I bought a jacket last week but it's too small. How do I return it and how long does the refund take? Do I need an RMA number?",
  },
  "Happy feedback": {
    sender: "sam@example.com", sender_name: "Sam Patel",
    subject: "Love my new tent!",
    body: "Just wanted to say the tent I bought is amazing quality and arrived early. Best outdoor gear purchase I've made. Keep it up!",
  },
};

export default function SimulateModal({ onClose, onCreated }) {
  const [form, setForm] = useState(SAMPLES["Refund question"]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async () => {
    setBusy(true); setErr(null);
    try {
      await api.simulate(form);
      onCreated?.();
      onClose();
    } catch (e) {
      setErr(e.message);
    } finally { setBusy(false); }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>Simulate incoming email</h3>
        <p style={{ fontSize: 13, color: "#64748b", marginTop: 0 }}>
          Inject a test email through the full AI pipeline (analyze → RAG reply → escalation).
        </p>
        <div className="toolbar">
          {Object.keys(SAMPLES).map((k) => (
            <button key={k} className="btn ghost" onClick={() => setForm(SAMPLES[k])}>{k}</button>
          ))}
        </div>
        <div className="field"><label>From name</label>
          <input value={form.sender_name} onChange={set("sender_name")} /></div>
        <div className="field"><label>From email</label>
          <input value={form.sender} onChange={set("sender")} /></div>
        <div className="field"><label>Subject</label>
          <input value={form.subject} onChange={set("subject")} /></div>
        <div className="field"><label>Body</label>
          <textarea rows={6} value={form.body} onChange={set("body")} /></div>
        <label style={{ fontSize: 13, display: "flex", gap: 6, alignItems: "center" }}>
          <input type="checkbox" checked={form.has_attachments || false}
            onChange={(e) => setForm((f) => ({ ...f, has_attachments: e.target.checked,
              attachment_names: e.target.checked ? ["document.pdf"] : [] }))} />
          Has attachment (forces escalation)
        </label>
        {err && <div className="escalation-banner" style={{ marginTop: 12 }}>{err}</div>}
        <div className="toolbar" style={{ marginTop: 16, justifyContent: "flex-end" }}>
          <button className="btn ghost" onClick={onClose}>Cancel</button>
          <button className="btn" disabled={busy} onClick={submit}>
            {busy ? "Processing…" : "Send through pipeline"}
          </button>
        </div>
      </div>
    </div>
  );
}
