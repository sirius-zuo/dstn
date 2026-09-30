# DSTN — Certifications, Licences, and Approvals Remaining
**Innovative Solutions Canada — EN578-26ISC1 TS13**
**Date:** 2026-06-17
**Document type:** SC3 Remaining Certifications Response

---

## Certifications, licences, and approvals left to obtain, and when expected

Of the standards/frameworks listed previously, the following are not yet finalized at time of Offer submission:

| Standard/Framework | Issuing Body | Status | Expected | Relevance |
|---|---|---|---|---|
| `did:stratos` DID method | W3C DID Registry | Not yet submitted | Month 1–2 | Self-service GitHub PR submission, not a safety gate; holder-side `did:key` already adopted and in use today |
| WCAG 2.1 AA accessibility conformance | W3C / self-assessed | Not yet formally validated | Month 3–4 | Quality/accessibility target, not a precondition for safe operation |
| Official Languages Act bilingual compliance | Government of Canada | Not yet formally validated | Month 3–4 | Usability target, not a safety precondition |
| Treasury Board Directive on Privacy-aligned security/privacy assessment | Self-assessed, reviewed with PSPC | Not yet conducted | Month 5–6 | Most safety-relevant item outstanding; formally validates data handling, encryption, access controls |

**Safe deployability before these are finalized:** DSTN can be safely deployed for an initial operational test today because its core safety properties are architectural, not certification-dependent, and are already implemented and tested: biometric data never leaves the supplier's device; no personal data is stored on-chain; credential material is encrypted at rest inside a hardware-isolated TEE; the Admin Dashboard is key-gated; and security headers are enforced and automatically tested. The outstanding Treasury Board-aligned assessment formally validates these existing controls rather than introducing new ones, so it is scheduled to complete before test partner exposure scales to full operational volume (Month 5–6), consistent with a staged, increasing-exposure testing approach.

No statutory licence (e.g., MDL/MDEL) is required at all, since DSTN is not a regulated product category; the items above are standards conformance and assurance activities, not regulatory gates blocking safe testing.

---

*Character count: 1,981 characters — under the 2,000 character limit.*
