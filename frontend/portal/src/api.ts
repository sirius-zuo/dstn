const getToken = () => localStorage.getItem("dstn_session_token") ?? "";

export async function beginRegistration(businessNumber: string) {
  const r = await fetch(`/passkey/register/begin?business_number=${encodeURIComponent(businessNumber)}`);
  return r.json();
}

export async function completeRegistration(challenge: string, credential: object) {
  const r = await fetch("/passkey/register/complete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ challenge, credential }),
  });
  return r.json();
}

export async function beginAuthentication() {
  const r = await fetch("/passkey/auth/begin");
  return r.json();
}

export async function completeAuthentication(challenge: string, assertion: object) {
  const r = await fetch("/passkey/auth/complete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ challenge, assertion }),
  });
  return r.json();
}

export async function getCredentialStatus() {
  const r = await fetch("/credential/status", {
    headers: { Authorization: `Bearer ${getToken()}` },
  });
  return r.json();
}

export function saveSession(token: string) {
  localStorage.setItem("dstn_session_token", token);
}

export function clearSession() {
  localStorage.removeItem("dstn_session_token");
}
