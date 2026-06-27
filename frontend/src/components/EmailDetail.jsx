import { useEffect, useState } from "react";
import { api } from "../api";
import { EmailBadges } from "./Badges";

export default function EmailDetail({ emailId, onChanged }) {
  const [email, setEmail] = useState(null);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () => {
    api.getEmail(emailId).then((e) => {
      setEmail(e);
      const reply = e.replies?.[e.replies.length - 1];
      setDraft(reply?.body || "");
    });
  };

  useEffect(load, [emailId]);

  if (!email) return <div className="empty">Loading…</div>;

  const reply = email.replies?.[email.replies.length - 1];
  const analysis = email.analysis || {};

  const save = async () => {
    if (!reply) return;
    setBusy(true);
    try {
      await api.editReply(reply.id, draft);
      load();
    } finally { setBusy(false); }
  };

  const approve = async () => {
    if (!reply) return;
    setBusy(true);
    try {
      if (draft !== reply.body) await api.editReply(reply.id, draft);
      await api.approveReply(reply.id);
      load(); onChanged?.();
    } finally { setBusy(false); }
  };

  const reprocess = async () => {
    setBusy(true);
    try { await api.reprocess(emailId); load(); onChanged?.(); }
    finally { setBusy(false); }
  };

  return (
    <div className="detail">
      <h2>{email.subject || "(no subject)"}</h2>
      <div className="meta">
        From <b>{email.sender_name || email.sender}</b> &lt;{email.sender}&gt;
        {email.attachment_names?.length > 0 && (
          <> · 📎 {email.attachment_names.join(", ")}</>
        )}
      </div>
      <EmailBadges email={email} />

      {email.escalation && (
        <div className="escalation-banner" style={{ marginTop: 12 }}>
          🚩 <b>Escalated to a human</b> — reasons:
          <ul>{email.escalation.reasons.map((r, i) => <li key={i}>{r}</li>)}</ul>
        </div>
      )}

      <div className="section-title">Customer email</div>
      <div className="email-body">{email.body}</div>

      {analysis.summary && (
        <>
          <div className="section-title">AI analysis</div>
          <div style={{ fontSize: 14 }}>
            <div><b>Summary:</b> {analysis.summary}</div>
            {analysis.reasoning && <div style={{ color: "#64748b" }}><b>Why:</b> {analysis.reasoning}</div>}
            {analysis.intent?.length > 0 && (
              <div style={{ marginTop: 4 }}>
                {analysis.intent.map((t) => <span key={t} className="kb-chip">{t}</span>)}
              </div>
            )}
          </div>
        </>
      )}

      {reply ? (
        <>
          <div className="section-title">
            AI draft reply {reply.is_ai ? "" : "(edited by agent)"}
          </div>
          {reply.kb_sources?.length > 0 && (
            <div style={{ marginBottom: 8 }}>
              <span style={{ fontSize: 12, color: "#64748b" }}>Grounded in KB: </span>
              {reply.kb_sources.map((s, i) => <span key={i} className="kb-chip">{s}</span>)}
            </div>
          )}
          {reply.confidence != null && (
            <div className="confidence" style={{ marginBottom: 8 }}>
              Confidence
              <span className="bar"><span style={{ width: `${Math.round(reply.confidence * 100)}%` }} /></span>
              {Math.round(reply.confidence * 100)}%
            </div>
          )}
          <textarea className="reply-box" value={draft}
            disabled={reply.sent}
            onChange={(e) => setDraft(e.target.value)} />
          <div className="toolbar" style={{ marginTop: 10 }}>
            {reply.sent ? (
              <span className="badge st-replied">✓ Sent {reply.approved_by ? `by ${reply.approved_by}` : ""}</span>
            ) : (
              <>
                <button className="btn" disabled={busy} onClick={approve}>
                  Approve &amp; Send
                </button>
                <button className="btn ghost" disabled={busy} onClick={save}>
                  Save edit
                </button>
              </>
            )}
            <button className="btn ghost" disabled={busy} onClick={reprocess}>
              ↻ Re-run AI
            </button>
          </div>
        </>
      ) : (
        <>
          <div className="section-title">No AI draft</div>
          <p style={{ color: "#64748b", fontSize: 14 }}>
            This email was classified as {email.category} and no reply was drafted.
          </p>
          <button className="btn ghost" disabled={busy} onClick={reprocess}>↻ Re-run AI</button>
        </>
      )}
    </div>
  );
}
