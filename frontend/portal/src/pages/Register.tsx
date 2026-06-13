import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { startRegistration } from "@simplewebauthn/browser";
import { beginRegistration, completeRegistration, saveSession } from "../api";
import { useTranslation } from "react-i18next";

export default function Register() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [businessNumber, setBusinessNumber] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleRegister() {
    setLoading(true);
    setError("");
    try {
      const { options, challenge } = await beginRegistration(businessNumber);
      const credential = await startRegistration(options);
      const result = await completeRegistration(challenge, credential);
      if (result.session_token) {
        saveSession(result.session_token);
        navigate("/dashboard");
      } else {
        setError(result.detail ?? t("registration_failed"));
      }
    } catch (err: any) {
      setError(err.message ?? t("registration_failed"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ maxWidth: 480, margin: "80px auto", padding: "0 16px" }}>
      <h1>{t("register_title")}</h1>
      <p>{t("register_description")}</p>
      <label htmlFor="bn">{t("business_number_label")}</label>
      <input
        id="bn"
        type="text"
        value={businessNumber}
        onChange={(e) => setBusinessNumber(e.target.value)}
        placeholder="123456789"
        style={{ display: "block", width: "100%", marginBottom: 12 }}
      />
      {error && <p role="alert" style={{ color: "red" }}>{error}</p>}
      <button onClick={handleRegister} disabled={loading || !businessNumber}>
        {loading ? t("loading") : t("register_passkey_button")}
      </button>
      <p><a href="/login">{t("already_registered")}</a></p>
    </main>
  );
}
