# DSTN — SC3 Risk Considerations
**Innovative Solutions Canada — EN578-26ISC1 TS13**
**Date:** 2026-06-17
**Document type:** SC3 Risk Considerations Response

---

## Risks regarding the testing and use of the innovation (environmental, privacy, health and safety)

DSTN is a software-only service (web portal, REST APIs, blockchain/TEE-backed backend). It involves no physical equipment or hardware installation by the test partner, which limits the risk categories that apply.

**Environmental risk:** None identified. DSTN adds no new physical infrastructure, emissions, or resource use beyond standard cloud compute already used in the test partner's IT environment.

**Health and safety risk:** None identified. End users interact with DSTN only through a standard web browser on existing computers/mobile devices. No specialized equipment or physical installation is introduced.

**Privacy risk:** This is the one substantive risk category, mitigated by design rather than absent:
- Biometric data (Face ID, Touch ID, Windows Hello) never leaves the supplier's own device; DSTN only receives a cryptographic public key and signed assertion, never raw biometric data.
- No personal data is stored on the Stratos Blockchain; credentials reference opaque identifiers (`did:key`, `did:stratos`), not names or personal identifiers.
- Credential material is encrypted at rest inside a hardware-isolated TEE, accessible only during an authenticated session.
- Admin Dashboard access is key-gated; the audit log records event metadata, not raw personal data.
- A formal security and privacy assessment aligned with Treasury Board Directive on Privacy standards is a scheduled contract deliverable (Months 5–6), completed before test partner data volume scales.

**Certifications/licences:** DSTN is not a regulated product (not a medical device, controlled good, or safety-critical hardware system), so no sector-specific licence is required. The applicable approval is the Treasury Board-aligned assessment above.

No environmental or health/safety risks are identified because the innovation has no physical footprint; the identified privacy risk is addressed through TEE-based key isolation, on-chain data minimization, and a scheduled formal privacy assessment.

---

*Character count: 1,978 characters — under the 2,000 character limit.*
