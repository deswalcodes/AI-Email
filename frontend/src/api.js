// Tiny fetch wrapper around the backend API.
const json = (r) => {
  if (!r.ok) return r.text().then((t) => Promise.reject(new Error(t || r.statusText)));
  return r.status === 204 ? null : r.json();
};

export const api = {
  health: () => fetch("/api/health").then(json),

  // Emails
  listEmails: (params = {}) => {
    const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v)).toString();
    return fetch(`/api/emails${q ? "?" + q : ""}`).then(json);
  },
  getEmail: (id) => fetch(`/api/emails/${id}`).then(json),
  getThread: (id) => fetch(`/api/emails/${id}/thread`).then(json),
  simulate: (body) =>
    fetch("/api/emails/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(json),
  reprocess: (id) => fetch(`/api/emails/${id}/reprocess`, { method: "POST" }).then(json),

  // Replies
  editReply: (id, body) =>
    fetch(`/api/replies/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ body }),
    }).then(json),
  approveReply: (id) => fetch(`/api/replies/${id}/approve`, { method: "POST" }).then(json),

  // Escalations
  listEscalations: () => fetch("/api/escalations").then(json),
  resolveEscalation: (emailId) =>
    fetch(`/api/escalations/${emailId}/resolve`, { method: "POST" }).then(json),

  // Knowledge base
  listKB: () => fetch("/api/kb").then(json),
  previewKB: (q) => fetch(`/api/kb/preview?q=${encodeURIComponent(q)}`).then(json),
  addKB: (body) =>
    fetch("/api/kb", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(json),

  // Analytics + Gmail
  analytics: () => fetch("/api/analytics/overview").then(json),
  gmailStatus: () => fetch("/api/gmail/status").then(json),
  gmailPoll: () => fetch("/api/gmail/poll", { method: "POST" }).then(json),
};
