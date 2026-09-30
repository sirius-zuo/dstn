# DSTN — Operational Test Objectives & Success Criteria
**Innovative Solutions Canada — EN578-26ISC1 TS13**
**Date:** 2026-06-17
**Document type:** Operational Test Objectives Response

---

## Technical and quantifiable objectives of testing; what constitutes a successful operational test

The operational test validates that DSTN's automated issuance, holder, display, and verification pipeline performs to defined, measurable targets when run against real public GC procurement data in a PSPC-adjacent environment — not just functioning, but functioning to specification under real conditions.

**Technical and quantifiable objectives:**

1. **Issuance latency and automation.** A credential becomes visible in the supplier's portal within 60 minutes of the scheduled data-ingestion cycle detecting a qualifying contract award, with zero PSPC staff actions per individual credential issued.

2. **Registration and authentication success rate.** Passkey registration (WebAuthn Level 3) completes and correctly activates the TEE Holder Agent session on first attempt for at least 95% of test registrations across at least three platform authenticator types (e.g., Apple Touch ID/Face ID, Windows Hello, a FIDO2 hardware key).

3. **Verification latency.** The public Verification API returns a signed status response (status, issuer, issue date, expiry, cryptographic proof) in under 1 second end-to-end, measured as the 95th-percentile response time under test load.

4. **Revocation propagation time.** When a supplier's status changes in the public data (deregistration, contract ended, adverse record), the updated status is reflected in the Verification API and the embedded badge within 30 seconds of the revocation registry update.

5. **System availability.** The deployed system maintains 99.9% uptime over a continuous 30-day operational test window, measured by automated health-check monitoring with logged downtime incidents and root causes.

6. **Cryptographic integrity.** 100% of issued credentials carry a verifiable TEE hardware attestation, and 0 credentials are issued with a signing key that leaves the secure enclave, confirmed by attestation log review.

7. **Security and privacy compliance.** A security and privacy assessment aligned with Treasury Board standards is completed with no critical or high-severity unresolved findings at test conclusion.

**What constitutes success:**
The operational test is successful if all seven quantifiable targets above are met or exceeded over the full 30-day test period in the PSPC-adjacent environment, using real (not synthetic) CanadaBuys and Open Government data as the issuance trigger, with at least one full issuance-to-verification-to-revocation cycle observed end-to-end without manual intervention. Partial success (e.g., meeting latency/uptime targets but with unresolved high-severity security findings, or requiring manual staff intervention for any issuance) would not satisfy the operational test, since manual-intervention-free operation and a clean security posture are both explicit, non-negotiable requirements of the underlying problem statement, not optional performance targets.

---

*Character count: 2,846 characters — under the 3,000 character limit.*
