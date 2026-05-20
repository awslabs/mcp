---
id: "SEC01-BP04"
title: "Stay up to date with security threats and recommendations"
framework: "WAF"
domain: "Security"
capability: "How do you securely operate your workload?"
risk_level: "High"
---

# SEC01-BP04 Stay up to date with security threats and recommendations

## Desired Outcome
You stay informed as industry publications are updated with the latest threats and recommendations.  You use automation to detect potential vulnerabilities and exposures as you identify new threats. You take mitigating action against these threats.  You adopt AWS services that automatically update with the latest threat intelligence.

## Anti-Patterns
- Not having a reliable and repeatable mechanism to stay informed of the latest threat intelligence.
- Maintaining manual inventory of your technology portfolio, workloads, and dependencies that require human review for potential vulnerabilities and exposures.
- Not having mechanisms in place to update your workloads and dependencies to the latest versions available that provide known threat mitigations.

## Implementation Guidance
 Review trusted threat intelligence publications to stay on top of the threat landscape.  Consult the [MITRE ATT&CK](https://attack.mitre.org/) knowledge base for documentation on known adversarial tactics, techniques, and procedures (TTPs). Review MITRE's [Common Vulnerabilities and Exposures](https://cve.org/) (CVE) list to stay informed on known vulnerabilities in products you rely on. Understand critical risks to web applications with the Open Worldwide Application Security Project (OWASP)'s popular [OWASP Top 10](https://owasp.org/www-project-top-ten/) project.

 Stay up to date on AWS security events and recommended remediation steps with AWS [Security Bulletins](https://aws.amazon.com/security/security-bulletins/) for CVEs.

 To reduce your overall effort and overhead of staying up to date, consider using AWS services that automatically incorporate new threat intelligence over time.  For example, [Amazon GuardDuty](https://aws.amazon.com/guardduty/) stays up to date with industry threat intelligence for detecting anomalous behaviors and threat signatures within your accounts.  [Amazon Inspector](https://aws.amazon.com/inspector/) automatically keeps a database of the CVEs it uses for its continuous scanning features up to date.  Both [AWS WAF](https://aws.amazon.com/waf/) and [AWS Shield Advanced](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-advanced-summary.html) provide managed rule groups that are updated automatically as new threats emerge.

 Review the [Well-Architected operational excellence pillar](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/welcome.html) for automated fleet management and patching.

## Implementation Steps
- Subscribe to updates for threat intelligence publications that are relevant to your business and industry. Subscribe to the AWS Security Bulletins.
- Consider adopting services that incorporate new threat intelligence automatically, such as Amazon GuardDuty and Amazon Inspector.
- Deploy a fleet management and patching strategy that aligns with the best practices of the Well-Architected Operational Excellence Pillar.

## Resources
### Related Best Practices
- [SEC01-BP07 Identify threats and prioritize mitigations using a threat model](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_securely_operate_threat_model.html)
- [OPS01-BP05 Evaluate threat landscape](https://docs.aws.amazon.com/wellarchitected/latest/framework/ops_priorities_eval_threat_landscape.html)
- [OPS11-BP01 Have a process for continuous improvement](https://docs.aws.amazon.com/wellarchitected/latest/framework/ops_evolve_ops_process_cont_imp.html)
