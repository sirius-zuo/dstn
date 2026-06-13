# Treasury Board Privacy Checklist — DSTN

| Requirement | Status | Notes |
|---|---|---|
| No PII on-chain | ✅ Pass | Stratos stores DID docs, schema attr names, rev registry bit vector only |
| Audit log no credential content | ✅ Pass | Logs record cred_ex_id + did:key + timestamp — no attribute values |
| Encrypted at rest | ✅ Pass | AES-256-GCM with TEE-sealed key per did:key |
| Data minimization | ✅ Pass | Only BN + name stored; no SIN, no address |
| Consent | ✅ Pass | Supplier initiates registration via passkey — explicit consent |
| Retention | ✅ Pass | Credentials revocable; supplier can request deletion via admin API |
