import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { startAuthentication } from "@simplewebauthn/browser";
import { beginAuthentication, completeAuthentication, saveSession } from "../api";
import { useTranslation } from "react-i18next";

export default function Login() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleLogin() {
    setLoading(true);
    setError("");
    try {
      const { options, challenge } = await beginAuthentication();
      const assertion = await startAuthentication(options);
      const result = await completeAuthentication(challenge, assertion);
      if (result.session_token) {
        saveSession(result.session_token);
        navigate("/dashboard");
      } else {
        setError(result.detail ?? t("auth_failed"));
      }
    } catch (err: any) {
      setError(err.message ?? t("auth_failed"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ maxWidth: 480, margin: "80px auto", padding: "0 16px" }}>
      <h1>{t("login_title")}</h1>
      <p>{t("login_description")}</p>
      {error && <p role="alert" style={{ color: "red" }}>{error}</p>}
      <button onClick={handleLogin} disabled={loading}>
        {loading ? t("loading") : t("login_passkey_button")}
      </button>
      <p><a href="/register">{t("no_account")}</a></p>
    </main>
  );
}
