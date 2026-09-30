# DSTN — PS1: Advance on State of the Art
**Innovative Solutions Canada — EN578-26ISC1 TS13**
**Date:** 2026-06-17
**Document type:** PS1 State of the Art / Competitors / Market Niches Response

---

## State-of-the-art approaches, competitors, and market niches

Current state-of-the-art approaches in GC supplier verification and digital credentialing fall into four categories:

1. **Manual/centralized government verification** (the baseline practice the problem statement targets): PSPC and departments validate supplier status by manual lookup across CanadaBuys, Open Government proactive-disclosure datasets, and internal records. There is no machine-readable, self-service, tamper-proof artifact a supplier can hold or display — every check requires human effort and produces no portable proof.

2. **Permissioned-ledger verifiable credentials** (the closest existing technology): BC Government's OrgBook BC / Verifiable Organizations Network, built on Hyperledger Indy and Aries/AnonCreds, issues business credentials anchored on a permissioned ledger controlled by a fixed steward consortium. This is real prior art for government VC issuance in Canada, but it is run as a government program, not commercialized, and depends on centrally governed ledger infrastructure with all credential holders needing wallet software.

3. **Enterprise VC infrastructure platforms:** Microsoft Entra Verified ID, Dock.io, Trinsic, Spruce ID, and Northern Block (a Canadian Aries-stack vendor that has worked with BC Gov and Ontario) offer general-purpose verifiable-credential issuance. These are centralized-cloud or wallet-first platforms, not procurement-specific, and require holders to install a wallet app and manage keys — a barrier for non-technical small suppliers.

4. **Trust-badge/seal products outside government:** TrustPilot ratings, Better Business Bureau accreditation seals, and SSL "trust seal" widgets are familiar embeddable-badge UX, but they are not cryptographically verifiable against an issuing authority in real time — most are static images or simple database lookups that can be spoofed or left stale after a status change.

**Competitors and similar technology:**
- OrgBook BC / Verifiable Organizations Network (government-run, Indy-based)
- Northern Block (Canadian Aries/AnonCreds systems integrator)
- Microsoft Entra Verified ID (enterprise VC platform, centralized cloud)
- Dock.io, Trinsic, Spruce ID (VC infrastructure-as-a-service vendors)
- SAM.gov and SAP Ariba/Business Network (centralized, non-cryptographic supplier registries)
- TrustPilot/BBB-style trust-seal widgets (UX precedent, no cryptographic backing)

**Market niches and spaces:** government-to-business credentialing remains served almost entirely by manual processes or single-province permissioned-ledger pilots, with no national, self-service, wallet-free GC supplier credential in market. The broader VC infrastructure market is wallet-first and generic, leaving the "non-technical SME holder" segment underserved. The trust-badge market is UX-familiar but cryptographically shallow. DSTN sits at the intersection — the cryptographically-backed, wallet-free, embeddable live trust badge niche — which is currently unoccupied.

---

*Character count: 2,950 characters — under the 3,000 character limit.*
