---
id: "OPS01-BP05"
title: "Evaluate threat landscape"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you determine what your priorities are?"
risk_level: "Medium"
---

# OPS01-BP05 Evaluate threat landscape

## Desired Outcome
- You regularly review and act on Well-Architected and Trusted Advisor outputs
- You are aware of the latest patch status of your services
- You understand the risk and impact of known threats and act accordingly
- You implement mitigations as necessary
- You communicate actions and context

## Anti-Patterns
- You are using an old version of a software library in your product. You are unaware of security updates to the library for issues that may have unintended impact on your workload.
- Your competitor just released a version of their product that addresses many of your customers' complaints about your product. You have not prioritized addressing any of these known issues.
- Regulators have been pursuing companies like yours that are not compliant with legal regulatory compliance requirements. You have not prioritized addressing any of your outstanding compliance requirements.

## Implementation Guidance
- **Evaluate threat landscape:** Evaluate threats to the business (for example, competition, business risk and liabilities, operational risks, and information security threats), so that you can include their impact when determining where to focus efforts.
  - [AWS Latest Security Bulletins](https://aws.amazon.com/security/security-bulletins/)
  - [AWS Trusted Advisor](https://aws.amazon.com/premiumsupport/trustedadvisor/)
- **Maintain a threat model:** Establish and maintain a threat model identifying potential threats, planned and in place mitigations, and their priority. Review the probability of threats manifesting as incidents, the cost to recover from those incidents and the expected harm caused, and the cost to prevent those incidents. Revise priorities as the contents of the threat model change.

## Resources
### Related Best Practices
- [SEC01-BP07 Identify threats and prioritize mitigations using a threat model](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_securely_operate_threat_model.html)
### Related Documents
- [AWS Cloud Compliance](https://aws.amazon.com/compliance/)
- [AWS Latest Security Bulletins](https://aws.amazon.com/security/security-bulletins/)
- [AWS Trusted Advisor](https://aws.amazon.com/premiumsupport/trustedadvisor/)
### Related Videos
- [AWS re:Inforce 2023 - A tool to help improve your threat modeling](https://youtu.be/CaYCsmjuiHg?si=e_CXPGqRF4WeBr1u)
