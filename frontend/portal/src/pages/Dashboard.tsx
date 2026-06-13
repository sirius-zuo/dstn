import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { getCredentialStatus, clearSession } from "../api";
import CredentialBadge from "../components/CredentialBadge";
import EmbedSnippet from "../components/EmbedSnippet";

export default function Dashboard() {
  const { t, i18n } = useTranslation();
  const [credStatus, setCredStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getCredentialStatus().then(setCredStatus).finally(() => setLoading(false));
  }, []);

  function handleLogout() {
    clearSession();
    window.location.href = "/login";
  }

  const toggleLang = () => i18n.changeLanguage(i18n.language === "en" ? "fr" : "en");

  if (loading) return <main style={{ maxWidth: 640, margin: "80px auto" }}><p>{t("loading")}</p></main>;

  const businessNumber = credStatus?.credential?.business_number ?? credStatus?.business_number ?? "";

  return (
    <main style={{ maxWidth: 640, margin: "80px auto", padding: "0 16px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1>{t("dashboard_title")}</h1>
        <div>
          <button onClick={toggleLang} style={{ marginRight: 8 }}>
            {i18n.language === "en" ? "FR" : "EN"}
          </button>
          <button onClick={handleLogout}>{t("logout")}</button>
        </div>
      </div>

      <section aria-label={t("credential_status_section")}>
        <h2>{t("your_credential")}</h2>
        {credStatus && <CredentialBadge status={credStatus.status ?? "pending"} />}
        {credStatus?.credential && (
          <dl style={{ marginTop: 16 }}>
            <dt><strong>{t("business_number_label")}</strong></dt>
            <dd>{credStatus.credential.business_number}</dd>
            <dt><strong>{t("business_name_label")}</strong></dt>
            <dd>{credStatus.credential.business_name}</dd>
            <dt><strong>{t("issued_label")}</strong></dt>
            <dd>{credStatus.credential.issue_date}</dd>
          </dl>
        )}
      </section>

      {credStatus?.status === "active" && businessNumber && (
        <section aria-label={t("embed_section")}>
          <EmbedSnippet businessNumber={businessNumber} />
        </section>
      )}
    </main>
  );
}
