# DSTN — PS1: Minor Improvements, Competitive Advantages, Level of Advancement
**Innovative Solutions Canada — EN578-26ISC1 TS13**
**Date:** 2026-06-17
**Document type:** PS1 Competitive Advantages Response

---

## Minor improvements over the state of the art, competitive advantages, and level of advancement

Direct comparisons against existing technologies/substitutes:

- **vs. manual PSPC lookup (baseline):** DSTN returns a signed result in <1 second with zero staff involvement, vs. an unspecified, human-mediated turnaround today.
- **vs. OrgBook BC / VON (Hyperledger Indy):** DSTN anchors on a permissionless, Proof-of-Traffic chain rather than a fixed steward consortium — removing Indy's single-governance-point risk.
- **vs. Microsoft Entra Verified ID, Dock.io, Trinsic, Spruce ID:** these need a wallet app and seed-phrase management. DSTN's passkey-anchored TEE Holder Agent needs neither — a minor UX change with large adoption impact for non-technical SME suppliers.
- **vs. standard Aries deployments (software-wallet keys):** DSTN signs inside a hardware TEE with per-issuance attestation, closing the server-compromise vector present in conventional deployments.
- **vs. TrustPilot/BBB-style trust seals:** those are static or simply-hosted images; DSTN's badge calls a live cryptographic API per page load, so it cannot be stale or spoofed after a status change.

**Level of advancement:** each component technology (blockchain, TEE, AnonCreds, WebAuthn) is mature (TRL 9); DSTN's advancement is incremental at the component level (permissionless vs. permissioned, hardware-attested vs. software-signed, passkey vs. wallet) but the combination yields a system-level capability — automated, wallet-free, real-time, tamper-proof government credentialing — no competitor offers as a packaged solution.

---

*Character count: 1,494 characters — under the 1,500 character limit.*
