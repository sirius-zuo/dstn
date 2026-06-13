import { useState } from "react";
import { useTranslation } from "react-i18next";

export default function EmbedSnippet({ businessNumber }: { businessNumber: string }) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);
  const verificationApiBase = import.meta.env.VITE_VERIFICATION_API_URL ?? "https://dstn.canada.ca";
  const snippet = `<script src="${verificationApiBase}/widget.js" data-bn="${businessNumber}" async></script>`;

  async function copyToClipboard() {
    await navigator.clipboard.writeText(snippet);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div>
      <h3>{t("embed_title")}</h3>
      <p>{t("embed_description")}</p>
      <pre style={{ background: "#f1f5f9", padding: 12, borderRadius: 6, overflowX: "auto", fontSize: 13 }}>
        <code>{snippet}</code>
      </pre>
      <button onClick={copyToClipboard}>
        {copied ? t("copied") : t("copy_snippet")}
      </button>
    </div>
  );
}
