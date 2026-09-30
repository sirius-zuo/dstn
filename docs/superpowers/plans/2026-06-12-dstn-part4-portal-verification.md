# DSTN Part 4: Supplier Portal Frontend, Verification API, and Verifier Widget

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the public-facing Verification API (< 1 second response), the React Supplier Portal frontend (WebAuthn passkey flows, credential status view, embed snippet generator), the embeddable Verifier Widget (vanilla JS `<script>` tag), bilingual EN/FR UI, and a basic Admin Dashboard.

**Architecture:** The Verification API is a separate FastAPI service (`services/verification/`). The Supplier Portal frontend is React + TypeScript (Vite), communicating with `services/portal/` backend. The Verifier Widget is a self-contained vanilla JS bundle. The Admin Dashboard is a server-side-rendered HTML page served by a new route on the portal backend.

**Tech Stack:** Python 3.12 + FastAPI (verification API), React 18 + TypeScript + Vite (portal frontend), @simplewebauthn/browser (WebAuthn client), react-i18next (i18n), vanilla JavaScript (widget), pytest + httpx (API tests), Vitest (frontend unit tests)

**Prerequisites:** Parts 1–3 complete. Portal backend running on :8030, PostgreSQL running.

**This is Part 4 of 5.**

---

## File Structure

```
services/
└── verification/
    ├── pyproject.toml
    ├── verification/
    │   ├── __init__.py
    │   ├── main.py             # FastAPI app — GET /api/verify/{business_number}
    │   └── verify.py           # Verification logic: DB lookup + revocation check
    └── tests/
        ├── conftest.py
        └── test_verify.py

frontend/
├── portal/                     # React + TypeScript supplier portal
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api.ts              # typed fetch wrappers for portal backend
│       ├── pages/
│       │   ├── Register.tsx    # passkey registration flow
│       │   ├── Login.tsx       # passkey authentication flow
│       │   └── Dashboard.tsx   # credential status + embed snippet
│       ├── components/
│       │   ├── CredentialBadge.tsx
│       │   └── EmbedSnippet.tsx
│       └── i18n/
│           ├── index.ts
│           ├── en.json
│           └── fr.json
└── widget/
    ├── package.json
    └── src/
        └── widget.js           # self-contained IIFE bundle
```

**New `.env` variables** (add to `.env.example`):
```bash
VERIFICATION_API_URL=http://localhost:8040
PORTAL_FRONTEND_URL=http://localhost:3000
```

---

### Task 22: Verification API

**Files:**
- Create: `services/verification/pyproject.toml`
- Create: `services/verification/verification/main.py`
- Create: `services/verification/verification/verify.py`
- Test: `services/verification/tests/test_verify.py`

The Verification API is public — no authentication required. It looks up the supplier by business number, checks the credential exists, and checks the Stratos revocation registry. Round-trip target: < 1 second.

- [ ] **Step 1: Create `services/verification/pyproject.toml`**

```toml
[project]
name = "verification"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.30.0",
    "httpx>=0.27.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "asyncpg>=0.29.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "python-dotenv>=1.0.0",
]
[project.optional-dependencies]
test = ["pytest>=8.0.0", "pytest-asyncio>=0.23.0", "respx>=0.21.0", "aiosqlite>=0.20.0", "httpx>=0.27.0"]
```

- [ ] **Step 2: Write the failing test**

```python
# services/verification/tests/conftest.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# services/verification/tests/test_verify.py
import pytest
import respx
import httpx
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from shared.models import Base, EncryptedCredential, PasskeyRecord
from verification.verify import VerificationService

STRATOS_URL = "https://stratos-api.example.org/api/v1"
REV_REG_ID = "did:stratos:issuer/rev_reg/1"

@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s

@pytest.mark.asyncio
@respx.mock
async def test_verify_active_supplier(session):
    # Pre-populate tables
    session.add(PasskeyRecord(
        credential_id=b"cred-id-1", business_number="123456789",
        public_key_cose=b"\x00" * 10, did_key="did:key:zTest", sign_count=0,
        created_at=datetime.now(timezone.utc),
    ))
    session.add(EncryptedCredential(
        did_key="did:key:zTest", ciphertext=b"enc", nonce=b"nonce000000",
        cred_ex_id="cred-001", updated_at=datetime.now(timezone.utc),
    ))
    await session.commit()

    respx.get(f"{STRATOS_URL}/anoncreds/revocation-registry/{REV_REG_ID}/status").mock(
        return_value=httpx.Response(200, json={"revoked": False})
    )
    svc = VerificationService(session, stratos_url=STRATOS_URL, stratos_key="key", rev_reg_id=REV_REG_ID)
    result = await svc.verify("123456789")
    assert result["status"] == "active"
    assert result["revoked"] is False
    assert result["business_number"] == "123456789"

@pytest.mark.asyncio
async def test_verify_unknown_supplier(session):
    svc = VerificationService(session, stratos_url=STRATOS_URL, stratos_key="key", rev_reg_id=REV_REG_ID)
    result = await svc.verify("000000000")
    assert result["status"] == "not_found"
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd services/verification && python -m pytest tests/ -v
```

Expected: `ImportError`

- [ ] **Step 4: Create `services/verification/verification/verify.py`**

```python
# services/verification/verification/verify.py
import httpx
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from shared.models import PasskeyRecord, EncryptedCredential

logger = logging.getLogger(__name__)

class VerificationService:
    def __init__(self, session: AsyncSession, stratos_url: str, stratos_key: str, rev_reg_id: str):
        self.session = session
        self.stratos_url = stratos_url.rstrip("/")
        self.stratos_key = stratos_key
        self.rev_reg_id = rev_reg_id

    async def verify(self, business_number: str) -> dict:
        # 1. Find the passkey record to get the did:key
        result = await self.session.execute(
            select(PasskeyRecord).where(PasskeyRecord.business_number == business_number)
        )
        passkey = result.scalar_one_or_none()
        if passkey is None:
            return {"business_number": business_number, "status": "not_found", "revoked": None}

        # 2. Check credential exists
        cred_record = await self.session.get(EncryptedCredential, passkey.did_key)
        if cred_record is None:
            return {"business_number": business_number, "status": "pending", "revoked": None}

        # 3. Check revocation registry on Stratos
        revoked = await self._check_revocation(cred_record.cred_ex_id or "0")

        return {
            "business_number": business_number,
            "did_key": passkey.did_key,
            "status": "revoked" if revoked else "active",
            "revoked": revoked,
            "credential_issued_at": cred_record.updated_at.isoformat() if cred_record.updated_at else None,
            "issuing_authority": "PSPC / DSTN",
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _check_revocation(self, cred_ex_id: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(
                    f"{self.stratos_url}/anoncreds/revocation-registry/{self.rev_reg_id}/status",
                    params={"cred_rev_id": cred_ex_id},
                    headers={"x-api-key": self.stratos_key},
                )
                r.raise_for_status()
                return r.json().get("revoked", False)
        except Exception as exc:
            logger.warning("Revocation check failed: %s — treating as not revoked", exc)
            return False
```

- [ ] **Step 5: Create `services/verification/verification/main.py`**

```python
# services/verification/verification/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared.config import settings
from shared.db import async_session_factory
from verification.verify import VerificationService

app = FastAPI(title="DSTN Verification API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])

@app.get("/api/verify/{business_number}")
async def verify(business_number: str):
    async with async_session_factory() as session:
        svc = VerificationService(
            session,
            stratos_url=settings.stratos_api_url,
            stratos_key=settings.stratos_api_key,
            rev_reg_id=settings.issuer_rev_reg_id,
        )
        return await svc.verify(business_number)

@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 6: Add `stratos_api_url` and `stratos_api_key` to `shared/config.py`**

```python
# shared/config.py — add to Settings class
stratos_api_url: str = "https://stratos-api.thestratos.org/api/v1"
stratos_api_key: str = "change-me"
```

- [ ] **Step 7: Run test to verify it passes**

```bash
cd services/verification && python -m pytest tests/ -v
```

Expected: both tests `PASSED`

- [ ] **Step 8: Start the Verification API and benchmark response time**

```bash
uvicorn verification.main:app --port 8040 --app-dir services/verification
```

```bash
time curl -s "http://localhost:8040/api/verify/123456789" | python -m json.tool
```

Expected: JSON response, total time well under 1 second (database + Stratos call).

- [ ] **Step 9: Commit**

```bash
git add services/verification/
git commit -m "feat: Verification API — GET /api/verify/{business_number} with Stratos revocation check"
```

---

### Task 23: Supplier Portal React Frontend — Project Setup

**Files:**
- Create: `frontend/portal/package.json`
- Create: `frontend/portal/vite.config.ts`
- Create: `frontend/portal/tsconfig.json`
- Create: `frontend/portal/index.html`
- Create: `frontend/portal/src/main.tsx`
- Create: `frontend/portal/src/App.tsx`
- Create: `frontend/portal/src/api.ts`

- [ ] **Step 1: Create `frontend/portal/package.json`**

```json
{
  "name": "dstn-portal",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "test": "vitest run"
  },
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^6.23.0",
    "@simplewebauthn/browser": "^10.0.0",
    "react-i18next": "^14.0.0",
    "i18next": "^23.0.0",
    "i18next-browser-languagedetector": "^8.0.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "typescript": "^5.4.0",
    "vite": "^5.2.0",
    "@vitejs/plugin-react": "^4.2.0",
    "vitest": "^1.5.0",
    "@testing-library/react": "^15.0.0",
    "@testing-library/jest-dom": "^6.4.0"
  }
}
```

- [ ] **Step 2: Create `frontend/portal/vite.config.ts`**

```typescript
// frontend/portal/vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      "/passkey": "http://localhost:8030",
      "/credential": "http://localhost:8030",
      "/holder": "http://localhost:8030",
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test-setup.ts"],
  },
});
```

- [ ] **Step 3: Create `frontend/portal/src/api.ts`**

```typescript
// frontend/portal/src/api.ts
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
```

- [ ] **Step 4: Install dependencies and verify the dev server starts**

```bash
cd frontend/portal && npm install
npm run dev
```

Expected: Vite dev server running on http://localhost:3000 (may 404 on routes — that's fine, App.tsx comes next).

- [ ] **Step 5: Commit**

```bash
git add frontend/portal/
git commit -m "feat: React portal frontend scaffold — Vite + TypeScript + WebAuthn client"
```

---

### Task 24: Register and Login Pages (WebAuthn Passkey Flows)

**Files:**
- Create: `frontend/portal/src/pages/Register.tsx`
- Create: `frontend/portal/src/pages/Login.tsx`
- Create: `frontend/portal/src/App.tsx`
- Create: `frontend/portal/src/main.tsx`
- Create: `frontend/portal/index.html`

- [ ] **Step 1: Create `frontend/portal/index.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>DSTN Supplier Portal</title>
</head>
<body>
  <div id="root"></div>
  <script type="module" src="/src/main.tsx"></script>
</body>
</html>
```

- [ ] **Step 2: Create `frontend/portal/src/main.tsx`**

```tsx
// frontend/portal/src/main.tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./i18n";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode><App /></React.StrictMode>
);
```

- [ ] **Step 3: Create `frontend/portal/src/App.tsx`**

```tsx
// frontend/portal/src/App.tsx
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Register from "./pages/Register";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";

export default function App() {
  const token = localStorage.getItem("dstn_session_token");
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/register" element={<Register />} />
        <Route path="/login" element={<Login />} />
        <Route path="/dashboard" element={token ? <Dashboard /> : <Navigate to="/login" replace />} />
        <Route path="*" element={<Navigate to={token ? "/dashboard" : "/login"} replace />} />
      </Routes>
    </BrowserRouter>
  );
}
```

- [ ] **Step 4: Create `frontend/portal/src/pages/Register.tsx`**

```tsx
// frontend/portal/src/pages/Register.tsx
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
```

- [ ] **Step 5: Create `frontend/portal/src/pages/Login.tsx`**

```tsx
// frontend/portal/src/pages/Login.tsx
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
```

- [ ] **Step 6: Commit**

```bash
git add frontend/portal/src/pages/ frontend/portal/src/App.tsx frontend/portal/src/main.tsx frontend/portal/index.html
git commit -m "feat: Register and Login pages with WebAuthn passkey flows"
```

---

### Task 25: Dashboard, CredentialBadge, and EmbedSnippet

**Files:**
- Create: `frontend/portal/src/pages/Dashboard.tsx`
- Create: `frontend/portal/src/components/CredentialBadge.tsx`
- Create: `frontend/portal/src/components/EmbedSnippet.tsx`

- [ ] **Step 1: Create `frontend/portal/src/components/CredentialBadge.tsx`**

```tsx
// frontend/portal/src/components/CredentialBadge.tsx
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
```

- [ ] **Step 2: Create `frontend/portal/src/components/EmbedSnippet.tsx`**

```tsx
// frontend/portal/src/components/EmbedSnippet.tsx
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
```

- [ ] **Step 3: Create `frontend/portal/src/pages/Dashboard.tsx`**

```tsx
// frontend/portal/src/pages/Dashboard.tsx
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
```

- [ ] **Step 4: Run the Vite dev server and navigate through the flows**

```bash
cd frontend/portal && npm run dev
```

Visit http://localhost:3000/register — verify the registration form renders in English.
Visit http://localhost:3000/login — verify the login button renders.

- [ ] **Step 5: Commit**

```bash
git add frontend/portal/src/components/ frontend/portal/src/pages/Dashboard.tsx
git commit -m "feat: Dashboard with CredentialBadge and EmbedSnippet components"
```

---

### Task 26: Bilingual EN/FR Internationalization

**Files:**
- Create: `frontend/portal/src/i18n/index.ts`
- Create: `frontend/portal/src/i18n/en.json`
- Create: `frontend/portal/src/i18n/fr.json`

- [ ] **Step 1: Create `frontend/portal/src/i18n/en.json`**

```json
{
  "register_title": "Register as a GoC Supplier",
  "register_description": "Enter your CRA business number and register your device passkey (Face ID, Touch ID, or security key). No app installation required.",
  "business_number_label": "CRA Business Number",
  "register_passkey_button": "Register with Passkey",
  "already_registered": "Already registered? Sign in",
  "login_title": "Sign In",
  "login_description": "Authenticate with your registered passkey. No password required.",
  "login_passkey_button": "Sign In with Passkey",
  "no_account": "New supplier? Register here",
  "dashboard_title": "DSTN Supplier Portal",
  "your_credential": "Your Supplier Credential",
  "credential_status_section": "Credential status",
  "embed_section": "Trust badge for your website",
  "embed_title": "Embed Your Trust Badge",
  "embed_description": "Paste this snippet anywhere on your website. It displays a live-verified trust badge.",
  "copy_snippet": "Copy Snippet",
  "copied": "Copied!",
  "loading": "Loading…",
  "logout": "Sign Out",
  "status_active": "GoC Verified Supplier",
  "status_revoked": "Credential Revoked",
  "status_pending": "Credential Pending",
  "status_not_found": "Not Found",
  "registration_failed": "Registration failed. Please try again.",
  "auth_failed": "Authentication failed. Please try again.",
  "business_name_label": "Business Name",
  "issued_label": "Issued"
}
```

- [ ] **Step 2: Create `frontend/portal/src/i18n/fr.json`**

```json
{
  "register_title": "Inscription en tant que fournisseur du GC",
  "register_description": "Entrez votre numéro d'entreprise ARC et enregistrez la clé d'accès de votre appareil (Face ID, Touch ID ou clé de sécurité). Aucune installation d'application requise.",
  "business_number_label": "Numéro d'entreprise ARC",
  "register_passkey_button": "S'inscrire avec une clé d'accès",
  "already_registered": "Déjà inscrit? Se connecter",
  "login_title": "Connexion",
  "login_description": "Authentifiez-vous avec votre clé d'accès enregistrée. Aucun mot de passe requis.",
  "login_passkey_button": "Se connecter avec une clé d'accès",
  "no_account": "Nouveau fournisseur? S'inscrire ici",
  "dashboard_title": "Portail des fournisseurs RNCF",
  "your_credential": "Votre attestation fournisseur",
  "credential_status_section": "Statut de l'attestation",
  "embed_section": "Badge de confiance pour votre site Web",
  "embed_title": "Intégrer votre badge de confiance",
  "embed_description": "Collez cet extrait n'importe où sur votre site Web. Il affiche un badge de confiance vérifié en temps réel.",
  "copy_snippet": "Copier l'extrait",
  "copied": "Copié!",
  "loading": "Chargement…",
  "logout": "Se déconnecter",
  "status_active": "Fournisseur GC vérifié",
  "status_revoked": "Attestation révoquée",
  "status_pending": "Attestation en attente",
  "status_not_found": "Introuvable",
  "registration_failed": "L'inscription a échoué. Veuillez réessayer.",
  "auth_failed": "L'authentification a échoué. Veuillez réessayer.",
  "business_name_label": "Nom de l'entreprise",
  "issued_label": "Émis le"
}
```

- [ ] **Step 3: Create `frontend/portal/src/i18n/index.ts`**

```typescript
// frontend/portal/src/i18n/index.ts
import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import en from "./en.json";
import fr from "./fr.json";

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: { en: { translation: en }, fr: { translation: fr } },
    fallbackLng: "en",
    supportedLngs: ["en", "fr"],
    detection: { order: ["navigator", "htmlTag"] },
    interpolation: { escapeValue: false },
  });

export default i18n;
```

- [ ] **Step 4: Verify language switching works**

Start the dev server, open http://localhost:3000/register. Click the language toggle on the dashboard after login.
Expected: all text switches between English and French without page reload.

- [ ] **Step 5: Commit**

```bash
git add frontend/portal/src/i18n/
git commit -m "feat: bilingual EN/FR i18n via react-i18next with browser language detection"
```

---

### Task 27: Verifier Widget (Embeddable Script)

**Files:**
- Create: `frontend/widget/package.json`
- Create: `frontend/widget/src/widget.js`
- Add widget build output to Verification API static serving

The widget is a vanilla JavaScript IIFE that reads `data-bn` from its own `<script>` tag, calls the Verification API, and renders a trust badge into a sibling element.

- [ ] **Step 1: Create `frontend/widget/package.json`**

```json
{
  "name": "dstn-widget",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "build": "node build.js",
    "dev": "node build.js --watch"
  },
  "devDependencies": {
    "esbuild": "^0.21.0"
  }
}
```

- [ ] **Step 2: Create `frontend/widget/src/widget.js`**

```javascript
// frontend/widget/src/widget.js
(function () {
  "use strict";

  const LABELS = {
    active: { en: "GoC Verified Supplier", fr: "Fournisseur GC vérifié", color: "#16a34a" },
    revoked: { en: "Credential Revoked", fr: "Attestation révoquée", color: "#dc2626" },
    pending: { en: "Verification Pending", fr: "Vérification en attente", color: "#d97706" },
    not_found: { en: "Not Found", fr: "Introuvable", color: "#6b7280" },
  };

  function getLang() {
    return (navigator.language || "en").startsWith("fr") ? "fr" : "en";
  }

  function renderBadge(container, status) {
    const lang = getLang();
    const info = LABELS[status] ?? LABELS.not_found;
    container.innerHTML = `
      <span role="img" aria-label="${info[lang]}" style="
        display:inline-flex;align-items:center;gap:6px;
        background:${info.color};color:#fff;border-radius:6px;
        padding:6px 14px;font-weight:700;font-size:14px;font-family:sans-serif;">
        ${status === "active" ? "✓" : "✗"} ${info[lang]}
      </span>`;
  }

  function renderError(container) {
    container.innerHTML = "";
  }

  async function init() {
    const scripts = document.querySelectorAll("script[data-bn]");
    scripts.forEach(async function (script) {
      const bn = script.getAttribute("data-bn");
      if (!bn) return;

      const apiBase = script.getAttribute("data-api") ?? "https://dstn.canada.ca";
      const container = document.createElement("div");
      container.setAttribute("data-dstn-badge", bn);
      script.parentNode.insertBefore(container, script.nextSibling);

      renderBadge(container, "pending");

      try {
        const r = await fetch(`${apiBase}/api/verify/${encodeURIComponent(bn)}`);
        if (!r.ok) throw new Error("API error");
        const data = await r.json();
        renderBadge(container, data.status ?? "not_found");
      } catch (_) {
        renderError(container);
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
```

- [ ] **Step 3: Create a minimal esbuild script at `frontend/widget/build.js`**

```javascript
// frontend/widget/build.js
const esbuild = require("esbuild");
const watch = process.argv.includes("--watch");
esbuild.build({
  entryPoints: ["src/widget.js"],
  bundle: true,
  minify: !watch,
  outfile: "../../services/verification/static/widget.js",
  format: "iife",
  watch: watch ? { onRebuild: (err) => { if (err) console.error(err); else console.log("rebuilt"); } } : false,
}).catch(() => process.exit(1));
```

- [ ] **Step 4: Build and verify the widget bundle**

```bash
cd frontend/widget && npm install && node build.js
```

Expected: `services/verification/static/widget.js` created (minified IIFE).

- [ ] **Step 5: Serve the widget from the Verification API**

In `services/verification/verification/main.py`, add static file serving:

```python
# Add after app = FastAPI(...) line:
from fastapi.staticfiles import StaticFiles
import os
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
```

Rebuild widget and restart Verification API. Verify:

```bash
curl http://localhost:8040/static/widget.js | head -5
```

Expected: minified JavaScript.

- [ ] **Step 6: Commit**

```bash
git add frontend/widget/ services/verification/verification/main.py services/verification/static/
git commit -m "feat: embeddable Verifier Widget — IIFE JS bundle served from Verification API"
```

---

### Task 28: Admin Dashboard

**Files:**
- Create: `services/portal/portal/admin.py`
- Modify: `services/portal/portal/main.py` (add admin routes)

The Admin Dashboard is a simple server-rendered HTML page showing: DAS sync status, recent supplier records, issuance count, and revocation log. No authentication framework needed — protect with a static API key header in production.

- [ ] **Step 1: Create `services/portal/portal/admin.py`**

```python
# services/portal/portal/admin.py
import json
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select, func
from shared.config import settings
from shared.db import async_session_factory
from shared.models import SupplierRecord, SupplierStatus

router = APIRouter(prefix="/admin")

def _require_admin(x_admin_key: str = Header(...)):
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(403, "Forbidden")

@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(x_admin_key: str = Header(...)):
    _require_admin(x_admin_key)
    async with async_session_factory() as session:
        total = (await session.execute(select(func.count()).select_from(SupplierRecord))).scalar()
        active = (await session.execute(select(func.count()).select_from(SupplierRecord).where(SupplierRecord.status == SupplierStatus.ACTIVE))).scalar()
        pending = (await session.execute(select(func.count()).select_from(SupplierRecord).where(SupplierRecord.status == SupplierStatus.PENDING_REGISTRATION))).scalar()
        revoked = (await session.execute(select(func.count()).select_from(SupplierRecord).where(SupplierRecord.status == SupplierStatus.REVOKED))).scalar()
        recent = (await session.execute(select(SupplierRecord).order_by(SupplierRecord.created_at.desc()).limit(20))).scalars().all()

    rows = "".join(
        f"<tr><td>{r.business_number}</td><td>{r.business_name}</td>"
        f"<td>{r.status.value}</td><td>{'Yes' if r.credential_issued else 'No'}</td>"
        f"<td>{r.last_synced_at.strftime('%Y-%m-%d %H:%M') if r.last_synced_at else '-'}</td></tr>"
        for r in recent
    )
    html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<title>DSTN Admin Dashboard</title>
<style>body{{font-family:sans-serif;padding:24px}}table{{border-collapse:collapse;width:100%}}
td,th{{border:1px solid #ddd;padding:8px}}th{{background:#f1f5f9}}</style></head>
<body><h1>DSTN Admin Dashboard</h1>
<p>Total suppliers: <strong>{total}</strong> &nbsp;|&nbsp;
Active: <strong>{active}</strong> &nbsp;|&nbsp;
Pending: <strong>{pending}</strong> &nbsp;|&nbsp;
Revoked: <strong>{revoked}</strong></p>
<h2>Recent Suppliers</h2>
<table><thead><tr><th>BN</th><th>Name</th><th>Status</th><th>Credential Issued</th><th>Last Synced</th></tr></thead>
<tbody>{rows}</tbody></table></body></html>"""
    return HTMLResponse(content=html)
```

- [ ] **Step 2: Register admin router in `services/portal/portal/main.py`**

```python
# Add near top of main.py (after existing imports):
from portal.admin import router as admin_router
# Add after app = FastAPI(...):
app.include_router(admin_router)
```

- [ ] **Step 3: Add admin API key to `shared/config.py`**

```python
# shared/config.py — add to Settings class
admin_api_key: str = "change-admin-key"
```

Also add to `.env.example`:
```bash
ADMIN_API_KEY=change-admin-key
```

- [ ] **Step 4: Verify the dashboard renders**

```bash
uvicorn portal.main:app --port 8030 --app-dir services/portal
curl -H "x-admin-key: change-admin-key" http://localhost:8030/admin/dashboard
```

Expected: HTML page with supplier statistics table.

- [ ] **Step 5: Commit**

```bash
git add services/portal/portal/admin.py shared/config.py .env.example
git commit -m "feat: Admin Dashboard — HTML monitoring page with supplier stats and recent records"
```

---

## Part 4 Complete

Run all test suites:

```bash
cd services/das && python -m pytest tests/ -v
cd services/issuer && python -m pytest tests/ -v
cd services/portal && python -m pytest tests/ -v
cd services/verification && python -m pytest tests/ -v
```

Expected: all green.

**What's working after Part 4:**
- Verification API returning real-time status with Stratos revocation check
- React Supplier Portal frontend with WebAuthn registration and login (EN + FR)
- Dashboard showing credential status, embed snippet generator
- Embeddable Verifier Widget served as minified JS bundle
- Admin Dashboard with supplier statistics

**Part 5 will:** integrate TEE-attested issuance (hardware attestation), harden security (WCAG audit, Treasury Board privacy), set up Docker/Kubernetes production deployment, establish performance benchmarks (< 1s verification API), and configure 30-day stability monitoring.
