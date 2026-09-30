# DSTN — Remaining Technical Challenges to Commercial Launch
**Innovative Solutions Canada — EN578-26ISC1 TS13**
**Date:** 2026-06-17
**Document type:** Technical Challenges Response

---

## Technical challenges remaining to reach commercial launch

Several technical challenges remain between the TRL-7 prototype and commercial launch (TRL 9):

1. **Authoritative data source integration.** Per AMD002, the GC's permanent authoritative public source for "GoC supplier" status does not yet exist; DSTN currently uses Open Government/CanadaBuys datasets as a stand-in. The Data Aggregation Service's connector layer is architected to be pluggable, but the actual connector to the future authoritative source cannot be built or tested until that source is defined and published.

2. **Scale validation of the revocation registry and verification path.** Current testing covers a small set of test suppliers in a local integration environment. Before commercial launch, the AnonCreds revocation registry and Verification API must be load- and stress-tested at GC-wide volume (potentially hundreds of thousands of suppliers and high-frequency verification traffic) to confirm the sub-1-second response time and Stratos Decentralized Storage propagation hold under production load, not just prototype-scale traffic.

3. **Independent security and privacy certification.** The prototype has not yet undergone third-party penetration testing or a formal Treasury Board-aligned security assessment (e.g., PBMM/ITSG-33-equivalent controls). TEE hardware attestation has been demonstrated on a single development enclave; verifying attestation integrity across a production fleet of Stratos TEE nodes, and getting that attestation independently validated, remains outstanding.

4. **Passkey recovery and cross-platform edge cases at scale.** The re-registration flow for lost or platform-migrated passkeys (e.g., Apple to Android) is designed but has only been tested in controlled conditions, not across the breadth of real-world device/OS/browser combinations GC suppliers will use.

5. **Multi-holder access.** Phase 1 supports a single designated passkey holder per company. Larger suppliers will need delegated, multi-user access with role-based permissions — a capability deferred to Phase 2 and not yet designed in detail.

6. **`did:stratos` standards adoption.** The DID method is submitted to the W3C registry via self-service GitHub PR, but final community acceptance and any requested revisions are outside Stratos's direct control and could affect the timeline for full standards-track status.

7. **Sustained operational reliability.** The 99.9% uptime target is validated only over a planned 30-day test window (Months 5–6). Commercial launch requires demonstrating that reliability over a longer, continuous production period, including patching, node churn, and real network conditions rather than a controlled test environment.

8. **Production data pipeline robustness.** Connectors must handle real-world data quality issues (inconsistent business numbers, delayed publications, format changes) at a scale and variability greater than the test datasets used during the ISC contract.

---

*Character count: 2,910 characters — under the 3,000 character limit.*
