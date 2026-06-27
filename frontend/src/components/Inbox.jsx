import { useEffect, useState } from "react";
import { api } from "../api";
import { EmailBadges } from "./Badges";
import EmailDetail from "./EmailDetail";

const CATEGORIES = [
  "Legal", "Product Issue", "Delivery Issue", "Return / Refund",
  "Billing", "General Enquiry", "Feedback / Praise", "Spam / Irrelevant",
];
const STATUSES = ["open", "drafted", "replied", "escalated"];

export default function Inbox({ refreshKey, onChanged, filterStatus }) {
  const [emails, setEmails] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [filters, setFilters] = useState({ category: "", status: filterStatus || "" });
  const [loading, setLoading] = useState(true);
  const lockStatus = Boolean(filterStatus);

  const load = () => {
    setLoading(true);
    api.listEmails(filters).then((data) => {
      setEmails(data);
      setLoading(false);
      if (data.length && !data.find((e) => e.id === selectedId)) {
        setSelectedId(data[0].id);
      }
    });
  };

  useEffect(load, [filters.category, filters.status, refreshKey]);

  return (
    <div className="body">
      <div className="panel list-pane">
        <div className="toolbar">
          <select value={filters.category}
            onChange={(e) => setFilters((f) => ({ ...f, category: e.target.value }))}>
            <option value="">All categories</option>
            {CATEGORIES.map((c) => <option key={c}>{c}</option>)}
          </select>
          {!lockStatus && (
            <select value={filters.status}
              onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value }))}>
              <option value="">All statuses</option>
              {STATUSES.map((s) => <option key={s}>{s}</option>)}
            </select>
          )}
        </div>
        {loading && <div className="empty">Loading…</div>}
        {!loading && emails.length === 0 && (
          <div className="empty">No emails yet. Use “Simulate email” to add one.</div>
        )}
        {emails.map((e) => (
          <div key={e.id}
            className={`email-row ${e.id === selectedId ? "selected" : ""}`}
            onClick={() => setSelectedId(e.id)}>
            <div className="row-top">
              <span className="sender">{e.sender_name || e.sender}</span>
            </div>
            <div className="subject">{e.subject || "(no subject)"}</div>
            <EmailBadges email={e} />
          </div>
        ))}
      </div>
      <div className="panel detail-pane">
        {selectedId ? (
          <EmailDetail emailId={selectedId} onChanged={() => { load(); onChanged?.(); }} />
        ) : (
          <div className="empty">Select an email to view details.</div>
        )}
      </div>
    </div>
  );
}
