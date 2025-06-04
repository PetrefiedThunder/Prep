# Data Protection Impact Assessment

This document summarizes potential privacy risks and mitigation strategies for the project.

## Overview
- **Purpose**: Assess how personal data is collected, processed, and protected.
- **Scope**: Covers all services that store or transmit user information.

## Risk Identification
1. **Unauthorized Access** – Attackers gain access to PII.
2. **Data Leakage** – Personal data accidentally exposed or shared with third parties.
3. **Incomplete Deletion** – User data not removed upon request.
4. **Insufficient Consent** – Users unaware of how data is used.
5. **Third-Party Vulnerabilities** – External vendors compromise user data.

## Mitigation Measures
- Implement strong authentication and role-based access controls.
- Encrypt PII at rest and in transit.
- Provide `/user/delete` and scheduled purge routines.
- Use consent checkboxes for marketing or analytics collection.
- Vet vendors for compliance (SOC2, ISO 27001, GDPR).
- Maintain access logs for 30 days and review for suspicious activity.

## Security Checklist (Investor/Data Partner Due Diligence)
- [ ] HTTPS enforced everywhere
- [ ] Regular rotation of JWT secrets
- [ ] Database role restrictions (read/read-write/admin)
- [ ] Vendor compliance reviews on file
- [ ] XSS, CSRF, and SQL injection protections tested
- [ ] Incident response plan documented
- [ ] Periodic penetration testing scheduled
- [ ] Data retention policies implemented

