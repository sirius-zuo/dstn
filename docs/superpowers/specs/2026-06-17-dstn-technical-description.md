# DSTN — Technical Description of the Proposed Innovation
**Innovative Solutions Canada — EN578-26ISC1 TS13**
**Date:** 2026-06-17
**Document type:** Technical Description Response

---

## Technical description of the proposed innovation

DSTN is a three-layer software system (no physical hardware is supplied; specifications below are architectural/protocol specifications).

**Layer 1 — Stratos Dcloud (existing, TRL 9):** Stratos Blockchain (DID registry, schema/credential-definition anchoring, audit chain) secured by Proof-of-Traffic consensus; Decentralized Storage (AnonCreds revocation registry, no central server); Decentralized Compute (TEE nodes — Intel SGX/AMD SEV); Decentralized Database (immutable audit log).

**Layer 2 — Credential Protocol:** an Aries Issuer Agent inside a Stratos TEE, implementing Hyperledger Aries RFCs (DIDComm, issue-credential, present-proof) over an AnonCreds 1.0 schema/credential definition anchored on-chain. Credentials conform to W3C VC Data Model 2.0 and DID Core 1.0 (issuer DID: `did:stratos`; holder DID: `did:key` derived from a WebAuthn P-256 key per FIDO2/CTAP2).

**Layer 2.5 — Data Aggregation Service:** scheduled connectors pull CanadaBuys and Open Government procurement datasets; a Status Derivation Engine applies "contract awarded + good standing" logic; a Pending State Store holds unregistered suppliers; a Credential Trigger calls the Issuer Agent on status change.

**Layer 3 — Application Layer:** a Supplier Portal (WebAuthn Level 3, bilingual, WCAG 2.1 AA), a Passkey Registry (TEE-resident pubkey → business number → `did:key`), a TEE Holder Agent (session-scoped, clears key material at session end), a Credential Store (encrypted at rest), a Verifier Widget (`<script>` embed), and a public Verification API (REST, signed JSON).

**Operational functioning:**
1. *Issuance* — the Data Aggregation Service detects an award and, if a passkey is registered, triggers the Issuer Agent, which signs an AnonCreds credential inside the TEE (key never leaves the enclave) and delivers it via internal DIDComm to the Holder Agent; the event is logged. No PSPC staff action occurs.
2. *Registration* — a supplier enters their CRA business number and registers a device passkey (Face ID, Touch ID, Windows Hello, or a FIDO2 key); the P-256 key deterministically derives their `did:key` identity — no blockchain transaction, no wallet app, no seed phrase.
3. *Display* — the supplier embeds a one-line `<script>` tag; on each page load the widget calls the Verification API, which resolves `did:stratos` and checks the revocation registry, returning status in under one second.
4. *Verification* — a buyer or GC department calls the API or scans a QR code, receiving a signed response with status, issuer, issue date, expiry, and cryptographic proof.
5. *Revocation* — a public-data status change triggers the Issuer Agent to update the revocation registry, propagating network-wide within seconds.

Performance specification observed in the TRL-7 prototype: Verification API response < 1 second end-to-end; revocation propagation to verifier within 30 seconds of status change.

---

*Character count: 2,870 characters — under the 3,000 character limit.*
