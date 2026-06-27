// Small badge helpers shared across views.

const sentimentClass = (s) => {
  if (!s) return "s-Neutral";
  if (s.startsWith("Angry")) return "s-Angry";
  if (s.startsWith("Frustrated")) return "s-Frustrated";
  if (s.startsWith("Sad")) return "s-Sad";
  if (s.startsWith("Happy")) return "s-Happy";
  return "s-Neutral";
};

export function SentimentBadge({ value }) {
  if (!value) return null;
  return <span className={`badge ${sentimentClass(value)}`}>{value}</span>;
}

export function CategoryBadge({ value }) {
  if (!value) return null;
  return <span className="badge cat">{value}</span>;
}

export function StatusBadge({ value }) {
  if (!value) return null;
  return <span className={`badge st-${value}`}>{value}</span>;
}

export function EmailBadges({ email }) {
  return (
    <div className="badges">
      <CategoryBadge value={email.category} />
      <SentimentBadge value={email.sentiment} />
      <StatusBadge value={email.status} />
      {email.is_vip && <span className="badge vip">★ VIP</span>}
      {email.has_attachments && <span className="badge attach">📎 attachment</span>}
    </div>
  );
}
