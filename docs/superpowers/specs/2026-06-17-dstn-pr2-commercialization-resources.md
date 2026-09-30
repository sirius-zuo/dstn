# DSTN — PR2: Resources Required to Support Commercialization
**Innovative Solutions Canada — EN578-26ISC1 TS13**
**Date:** 2026-06-17
**Document type:** PR2 Commercialization Resources Response (Question 2)

---

## Physical and human resources required to support commercialization

DSTN's commercialization is resource-light by design: it is a SaaS credential service built on existing Stratos infrastructure, not a hardware product requiring manufacturing capacity, so the resource plan centers on people, partnerships, and cloud/network capacity rather than physical production.

**Marketing and sales strategies:** Go-to-market relies on ISC's Pathway to Commercialization (PTC) channel and direct relationship selling rather than broad-market advertising. PSPC's successful test deployment serves as the primary marketing asset — a documented reference case used in direct outreach to Shared Services Canada, ISED, and provincial procurement bodies. `did:stratos`'s W3C registration and Stratos's existing Web3 ecosystem presence (partnerships and integrations already listed publicly) provide secondary credibility signals. Sales is conducted by the Technical Lead and senior engineers directly engaging departmental IT and procurement contacts — appropriate for a small number of high-value government contracts rather than a high-volume sales motion.

**Staffing plan and employment strategies:** The core delivery team (5–7 engineers: 1 Technical Lead, 2 Protocol Engineers, 2 Application Engineers, 2 Infrastructure/TEE Engineers) carries directly into commercialization with expanded responsibilities — the same engineers who built the system support PSPC's production deployment and onboard subsequent departments, avoiding a costly handoff to a separate operations team. As department count grows (Phase 2), the company plans to add a dedicated customer success/support role and a second sales-engineering hire, sourced through the existing recruitment channels (Technation Diversity in Tech, Indigenous Works, Concordia/UQAM co-op pipeline) described in the EDI strategy, keeping hiring growth incremental and tied to confirmed contract revenue rather than speculative headcount.

**Partners and production capabilities:** DSTN does not require new manufacturing or production capacity — "production" is software deployment onto existing Stratos Dcloud infrastructure (already TRL 9, serving live commercial Web3 traffic). Relevant existing Stratos ecosystem partners support specific commercialization needs: NVIDIA for TEE-accelerated compute capacity as transaction/verification volume scales; BlockSec for independent security audits required by GC departments' procurement security review processes; and IoTeX/Entangle/Cluster Protocol for cross-chain interoperability if international (Track B) credential portability is required. No new production partnerships are needed to serve the initial PSPC/GC department customer base.

**Physical assets:** No proprietary hardware is purchased or manufactured. The system runs on Stratos's existing TEE-capable compute nodes (Intel SGX/AMD SEV), decentralized storage, and blockchain infrastructure, deployed via the Kubernetes manifests already built for this contract (`deploy/k8s/`). Department-side requirements are limited to standard government IT assets already in place: network/firewall access, a Kubernetes-capable hosting environment or equivalent cloud namespace, and standard employee devices with platform authenticators (Face ID, Touch ID, Windows Hello, or a FIDO2 key) — no new physical procurement is required of either the Offeror or the customer.

**Parts and materials:** Not applicable in the traditional sense, as DSTN is a software/protocol service. The closest analogues are licensed protocol/standard usage (Hyperledger Aries/AnonCreds under Apache 2.0, W3C VC/DID specifications under royalty-free terms) and Stratos network resource consumption (compute, storage, and blockchain transaction capacity), all of which are existing, already-operational Stratos infrastructure rather than externally sourced inputs subject to supply constraints.

Together, this resource plan supports commercialization without requiring capital-intensive manufacturing, large sales teams, or new physical infrastructure — consistent with a small company scaling a software service on infrastructure it already operates.

---

*Character count: 4,089 characters — under the 5,000 character limit.*
