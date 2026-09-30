# DSTN — SC4: Scope – Outcomes (Outcome 1)
**Innovative Solutions Canada — EN578-26ISC1 TS13**
**Date:** 2026-06-17
**Document type:** SC4 Scope/Outcomes Response

---

## Description of the proposed innovation and demonstration of relevance to the selected Problem Statement and Outcome 1

DSTN (Decentralized Supplier Trust Network) is a system that automatically issues a tamper-resistant, cryptographically verifiable digital credential confirming a company's "Government of Canada supplier" status, derived from public GC procurement data, and lets any party verify that status instantly without contacting PSPC.

**Scientific and technological basis:** DSTN combines four established but never-before-combined technology bases. (1) W3C Verifiable Credentials Data Model 2.0 and DID Core 1.0 provide the cryptographic credential format and identity model — a credential is a digitally signed claim that can be mathematically verified against a public key, not a document that can be photocopied or forged. (2) The AnonCreds protocol (Hyperledger Aries), built on zero-knowledge-proof-compatible signature schemes, governs how credentials are issued, held, and selectively presented, with revocation handled via a cryptographic accumulator rather than a simple status flag. (3) Trusted Execution Environment (TEE) hardware (Intel SGX/AMD SEV) provides hardware-enforced isolation so the issuer's private signing key is generated and used inside a secure enclave and never exposed to the host operating system, with each signing operation producing an independently verifiable hardware attestation. (4) W3C WebAuthn/FIDO2 public-key cryptography (the same standard underlying Face ID, Touch ID, and Windows Hello) anchors the supplier's holder identity to a device-bound key pair, removing the need for wallet software.

**Mapping to Outcome 1:**
- *"Issue secure, tamper-resistant digital credentials confirming GC supplier status"* — the Data Aggregation Service derives status from CanadaBuys/Open Government data and triggers the Aries Issuer Agent, which signs an AnonCreds credential inside the TEE; tampering is cryptographically detectable because any alteration invalidates the signature.
- *"Embeddable, dynamic trust indicators, verifiable in a single click or scan"* — the Verifier Widget is a one-line embeddable script that renders a live badge and calls the public Verification API on every page load; a QR code or direct API call gives the same result in under one second.
- *"Self-service display and sharing without manual PSPC intervention"* — issuance, renewal, and revocation are entirely data-event-driven; suppliers self-register with a device passkey and self-serve their embed snippet from the portal, with zero PSPC staff action required per credential.

This combination directly answers the problem statement: a portable, tamper-resistant, real-time verifiable credential that suppliers control and display themselves, removing the centralized manual bottleneck described in the problem statement's preamble.

---

*Character count: 2,739 characters — under the 3,000 character limit.*
