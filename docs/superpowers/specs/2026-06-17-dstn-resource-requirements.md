# DSTN — Resource Requirements (Training, Configuration, Installation, Operation)
**Innovative Solutions Canada — EN578-26ISC1 TS13**
**Date:** 2026-06-17
**Document type:** Resource Requirements Response

---

## Resource requirements for training, configuration, installation, and operation

**Required physical resources (GC-provided)**
- Network/firewall access from the PSPC-adjacent test environment to the public CanadaBuys and Open Government data feeds, and outbound HTTPS access to the Stratos Blockchain network
- A test/staging environment (VMs or a Kubernetes namespace) able to run standard Linux containers — DSTN ships as containerized services (Docker/K8s manifests provided), so no specialized GC hardware is required
- A small set of test devices with platform authenticators (e.g., a laptop with Windows Hello, a phone/tablet with Face ID or Touch ID, or one FIDO2 hardware key) for registration/login testing
- TLS certificate(s) and a DNS entry for the Supplier Portal and Verification API endpoints under a GC-approved or test domain
- Standard utilities (power, network connectivity) for any GC-hosted infrastructure component; no specialized power, cooling, or physical security beyond normal data-centre/cloud standards, since there is no proprietary hardware to install

**Potential GC human resource requirements**
- A technical liaison/SME to provision network access, DNS, and TLS certificates, and to coordinate environment access during setup
- A privacy/security officer to review and sign off the Treasury Board-aligned security and privacy assessment before/during the test
- A small number of test participants (PSPC staff or consenting suppliers) to perform passkey registration and exercise the supplier-facing flows
- An accessibility/official-languages reviewer to validate the bilingual, WCAG 2.1 AA-targeted Portal and Widget against GC standards
- No ongoing GC operations staff are required to run the system day-to-day — issuance and revocation are automated and require no manual processing by GC staff once deployed

**Potential adoption challenges for a typical end user**
- Suppliers unfamiliar with passkeys (Face ID/Touch ID/Windows Hello) may need brief onboarding guidance, even though no wallet software or seed phrase is required
- Suppliers on older devices/browsers lacking WebAuthn/FIDO2 support may be unable to register a passkey without an alternate hardware key
- Small suppliers may be unsure how to embed the Verifier Widget `<script>` tag on their website without basic web-publishing knowledge
- PSPC staff transitioning from a manual verification workflow may initially be hesitant to trust an automated, non-staff-mediated credentialing process and may want an audit/override view (the Admin Dashboard addresses this but requires brief orientation)
- Suppliers who change devices or platforms (e.g., Apple to Android) will need to complete a one-time re-registration step, which is simple but is a process change from "nothing to do" expectations

---

*Character count: 2,723 characters — under the 3,000 character limit.*
