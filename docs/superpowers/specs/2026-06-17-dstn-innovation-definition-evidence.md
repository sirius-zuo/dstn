# DSTN — Innovation Definition & Evidence
**Innovative Solutions Canada — EN578-26ISC1 TS13**
**Date:** 2026-06-17
**Document type:** Innovation Definition Response

---

## 1) How the proposed innovation meets the ISC definitions of innovation, with evidence

DSTN meets all three ISC innovation definitions relative to the current state of the art.

**1) Invention (new/novel processes not commonly known)**
DSTN introduces three processes with no prior public implementation:
- `did:stratos`, a W3C DID method anchored to a permissionless, Proof-of-Traffic (PoT) consensus blockchain. Every existing production Aries/AnonCreds deployment — including BC Government's OrgBook and Digital Trust systems — anchors credentials on Hyperledger Indy, a permissioned ledger controlled by a fixed steward consortium. DSTN is the first AnonCreds deployment anchored on a permissionless, incentive-driven chain.
- TEE-attested credential issuance, where the issuer's private signing key is generated inside a hardware-isolated enclave (Intel SGX/AMD SEV) and never exported, with every issuance producing a verifiable hardware attestation. Standard Aries issuer agents hold signing keys in software wallets, exposing them to server compromise.
- A passkey-gated TEE Holder Agent, where the supplier's holder DID is derived deterministically (`did:key`) from a WebAuthn P-256 passkey, removing the wallet-install/seed-phrase step required by every current AnonCreds holder implementation.

*Evidence:* component-level functional testing of the TRL-7 prototype confirms (a) successful `did:stratos` resolution against the Stratos Blockchain, (b) an end-to-end AnonCreds issuance from data ingestion through DIDComm delivery to the TEE Holder Agent, and (c) a WebAuthn passkey registration/authentication flow correctly activating the holder session — all observed directly in our development/test environment, not vendor claims.

**2) Significant modification applied to a setting not currently feasible**
Stratos Dcloud (blockchain, storage, compute, database) is an existing TRL-9 production network used by Web3 application developers; Hyperledger Aries/AnonCreds is an existing TRL-9 protocol used in BC Government's supplier/professional credentialing systems. Neither has been combined with automated ingestion of public GC procurement data (CanadaBuys, Open Government) to drive credential issuance without manual government intervention — this specific government application is not currently possible with any existing deployment, all of which require manual issuer review per credential.

*Evidence:* PSPC's current process (per the solicitation's problem statement) relies on centralized systems and manual PSPC intervention for every supplier status validation — a documented limitation, not an estimate.

**3) Improvement in functionality/cost/performance over current best practice**
- *Latency:* DSTN's Verification API returns a signed status response in under 1 second, measured via internal load testing of the prototype Verification API endpoint against the Stratos Blockchain and revocation registry. Today's process requires a manual lookup across fragmented departmental and public datasets with no defined turnaround time.
- *Availability:* the AnonCreds revocation registry is replicated across the Stratos Decentralized Storage network with no single control point, unlike OCSP/CRL/StatusList2021 approaches that depend on a centrally hosted revocation server (a documented architectural constraint of those W3C-referenced standards).
- *Onboarding friction:* removing wallet installation and seed-phrase management (replaced by a device passkey already present on supplier hardware) eliminates the principal adoption barrier reported for prior VC holder deployments aimed at non-technical users.

All performance figures cited above were obtained from internal functional and load testing of the working TRL-7 prototype, not simulation or projection; third-party verification of these benchmarks (including hardware attestation validation) is scheduled as a contract milestone in Months 5–6.

---

*Character count: 3,823 characters — under the 4,000 character limit.*
