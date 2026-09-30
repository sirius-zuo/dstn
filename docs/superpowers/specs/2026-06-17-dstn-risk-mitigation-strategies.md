# DSTN — Risk Mitigation Strategies
**Innovative Solutions Canada — EN578-26ISC1 TS13**
**Date:** 2026-06-17
**Document type:** SC3 Risk Mitigation Strategies Response (Add-a-Risk form entries)

---

## Risk mitigation strategies developed to address potential risks during testing

Five risk entries, formatted for the "Add a risk" form (Risk / Likelihood / Impact / Mitigation Strategy):

### Risk 1
- **Risk:** Exposure of supplier business data or test partner data during the operational test
- **Likelihood:** Low
- **Impact:** High
- **Mitigation Strategy:** No personal data is stored on the Stratos Blockchain; credentials reference opaque identifiers (`did:key`, `did:stratos`) rather than names or personal identifiers. Credential material is encrypted at rest inside a hardware-isolated TEE and is decrypted only during an authenticated passkey session, in memory, then re-encrypted at session end. Admin Dashboard access is key-gated. A Treasury Board Directive on Privacy-aligned security and privacy assessment is scheduled to validate these controls before test partner data volume scales (Month 5–6).

### Risk 2
- **Risk:** Compromise of the credential-issuance signing key, enabling fraudulent credential issuance
- **Likelihood:** Low
- **Impact:** High
- **Mitigation Strategy:** The Aries Issuer Agent's private signing key is generated inside a hardware-isolated Trusted Execution Environment (Intel SGX/AMD SEV) and never exported to software. Every issuance produces a verifiable hardware attestation, allowing any anomalous or unattested issuance to be detected and flagged. This eliminates the standard software-wallet attack surface present in conventional Aries deployments.

### Risk 3
- **Risk:** Outage or format change in the public CanadaBuys / Open Government data feeds disrupting credential issuance during the test
- **Likelihood:** Medium
- **Impact:** Low
- **Mitigation Strategy:** Connectors implement retry logic and local caching of the last successful sync. Already-issued credentials remain valid and verifiable during any source outage; verification and revocation services are unaffected by an upstream data feed disruption, so operational integrity for test partners and verifiers is preserved even if a public data source is temporarily unavailable.

### Risk 4
- **Risk:** Verification API or revocation registry unavailability affecting buyers/verifiers relying on supplier status (broader population/infrastructure impact)
- **Likelihood:** Low
- **Impact:** Medium
- **Mitigation Strategy:** The AnonCreds revocation registry is replicated across the Stratos Decentralized Storage network with no single point of failure, unlike centrally hosted OCSP/CRL approaches. Automated health-check monitoring and Prometheus-based alerting (already configured in the deployment manifests) provide continuous uptime visibility throughout the test, enabling rapid detection and response to any service degradation.

### Risk 5
- **Risk:** Test participants lose or change passkey-bearing devices, losing access to their credential mid-test
- **Likelihood:** Low
- **Impact:** Low
- **Mitigation Strategy:** A self-service re-registration flow lets a supplier enter their business number and register a new passkey; DSTN automatically re-issues the credential to the new `did:key` identity with no staff involvement and no credential data loss, since the credential is data-driven and re-derivable from the authoritative status record rather than tied irrevocably to a single device.
