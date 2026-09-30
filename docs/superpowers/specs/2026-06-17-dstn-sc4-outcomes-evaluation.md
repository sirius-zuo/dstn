# DSTN — SC4 Outcomes Evaluation
**Innovative Solutions Canada — EN578-26ISC1 TS13**
**Date:** 2026-06-17
**Document type:** SC4 Outcomes Evaluation Response

---

## Section 20 Problem Statements — Scope Review

Section 20 of the solicitation (EN578-26ISC1 TS13, pages 31–40) contains problem statements across three unrelated themes:

- **Theme 1 — Trust & Verification in Digital Government:** one problem statement, 20.1.a *"Supplier verification and decentralized credentialing"* — this is the only one DSTN addresses.
- **Theme 2 — Enhancing Capabilities in Complex Environments:** seven problem statements (RPAS for RCMP/Arctic/ISR, ship building automation, multi-function RF systems, underwater comms, UAS for sensor ranging) — not applicable to DSTN.
- **Theme 3 — Quantum:** one problem statement on quantum technologies — not applicable to DSTN.

DSTN's response addresses only Problem Statement 20.1.a. There is therefore one SC4 outcomes evaluation to complete.

---

## SC4 — Outcomes Evaluation
### Problem Statement 20.1.a — Supplier verification and decentralized credentialing (Theme 1)

**Required outcome (per solicitation, Section 20.1, Outcome 1):**
> "Solutions that enable the GC to issue secure, tamper-resistant digital credentials that can confirm a company's supplier to the GC status. Solutions must provide suppliers with embeddable, dynamic trust indicators that are capable of interactive verification by users in a single click or scan. Solutions must allow suppliers to easily display and share their verified GC supplier status... without requiring manual PSPC intervention (supplier self-service verification tools)."

**How DSTN meets this outcome:**

| Outcome requirement | DSTN response |
|---|---|
| GC can issue secure, tamper-resistant digital credentials confirming supplier status | The Data Aggregation Service ingests CanadaBuys Contract History and Open Government procurement datasets, derives "active supplier" status automatically, and triggers the Aries Issuer Agent — running inside a Stratos TEE — to sign a W3C-aligned AnonCreds credential anchored on the Stratos Blockchain (`did:stratos`). The private signing key never leaves the hardware enclave, and every credential carries a hardware attestation proof (Technical Proposal §5, Innovation 2). |
| Embeddable, dynamic trust indicators, verifiable in a single click or scan | The Verifier Widget is a single `<script>` embed that renders a live trust badge on any supplier website, calling the public Verification API on every page load. A buyer can also scan a QR code to call the same API directly. Verification round-trips in under one second (Technical Proposal, Flows 4–5; Business Plan Figure BP-0b). |
| Suppliers can display/share verified status without manual PSPC intervention | Issuance and revocation are entirely data-event-driven — no PSPC staff action is required per credential. Suppliers self-serve: they register once with a device passkey (Face ID, Touch ID, Windows Hello, or a hardware key — no wallet install, no seed phrase) and the system automatically issues, renews, or revokes their credential as the underlying public contract data changes (Technical Proposal, Flows 1, 2, 6). |

**Scope and social impact (Business Plan §5.5):**
DSTN reduces administrative barriers for the 45,000+ Indigenous-owned and 15,000+ women-owned businesses pursuing federal procurement access. Removing the wallet/seed-phrase requirement in favor of a passkey lowers the technical barrier for small suppliers and those in remote or rural communities with limited IT support. The Supplier Portal is WCAG 2.1 AA compliant and bilingual. The underlying architecture is credential-type-agnostic, so the same infrastructure can extend to other GC- and equity-body-issued credentials (e.g., CCIB Indigenous Business Certification, WBE Canada) — making it shared trust infrastructure rather than a single-purpose tool (Business Plan §4.3, Track A).

**Commercialization path supporting sustained outcome delivery (Business Plan §4):**
Beyond the ISC Testing Stream, the Pathway to Commercialization route brings DSTN to PSPC, Shared Services Canada, ISED, and provincial procurement bodies as paying customers (Business Plan §4.2), with longer-term expansion into other GC credential domains, international procurement bodies, and enterprise B2B verification (Business Plan §4.3–4.4) — demonstrating the outcome is durable and scalable beyond the testing contract itself.
