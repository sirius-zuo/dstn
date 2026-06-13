import { useTranslation } from "react-i18next";

type Status = "active" | "revoked" | "pending" | "not_found";

const COLORS: Record<Status, string> = {
  active: "#16a34a",
  revoked: "#dc2626",
  pending: "#d97706",
  not_found: "#6b7280",
};

export default function CredentialBadge({ status }: { status: Status }) {
  const { t } = useTranslation();
  return (
    <div
      role="status"
      aria-label={t(`status_${status}`)}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        background: COLORS[status],
        color: "#fff",
        borderRadius: 8,
        padding: "8px 16px",
        fontWeight: 700,
        fontSize: 16,
      }}
    >
      <span aria-hidden="true">{status === "active" ? "✓" : "✗"}</span>
      {t(`status_${status}`)}
    </div>
  );
}
