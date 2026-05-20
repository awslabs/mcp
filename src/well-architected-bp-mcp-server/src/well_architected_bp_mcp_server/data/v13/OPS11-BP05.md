---
id: "OPS11-BP05"
title: "Define drivers for improvement"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you evolve operations?"
risk_level: "Medium"
---

# OPS11-BP05 Define drivers for improvement

## Desired Outcome
- You track data from across your environment.
- You correlate events and activities to business outcomes.
- You can compare and contrast between environments and systems.
- You maintain a detailed activity history of your deployments and outcomes.
- You collect data to support your security posture.

## Anti-Patterns
- You collect data from across your environment but do not correlate events and activities.
- You collect detailed data from across your estate, and it drives high Amazon CloudWatch and AWS CloudTrail activity and cost. However, you do not use this data meaningfully.
- You do not account for business outcomes when defining drivers for improvement.
- You do not measure the effects of new features.

## Implementation Guidance
- Understand drivers for improvement: You should only make changes to a system when a desired outcome is supported.
  - Desired capabilities: Evaluate desired features and capabilities when evaluating opportunities for improvement.
    - [What's New with AWS](https://aws.amazon.com/new/)
  - Unacceptable issues: Evaluate unacceptable issues, bugs, and vulnerabilities when evaluating opportunities for improvement. Track rightsizing options, and seek optimization opportunities.
    - [AWS Latest Security Bulletins](https://aws.amazon.com/security/security-bulletins/)
    - [AWS Trusted Advisor](https://aws.amazon.com/premiumsupport/trustedadvisor/)
    - [Cloud Intelligence Dashboards](https://www.wellarchitectedlabs.com/cloud-intelligence-dashboards/)
  - Compliance requirements: Evaluate updates and changes required to maintain compliance with regulation, policy, or to remain under support from a third party, when reviewing opportunities for improvement.
    - [AWS Compliance](https://aws.amazon.com/compliance/)
    - [AWS Compliance Programs](https://aws.amazon.com/compliance/programs/)
    - [AWS Compliance Latest News](https://aws.amazon.com/compliance/compliance-latest-news/)

## Resources
### Related Best Practices
- [OPS01 Organization priorities](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/organization-priorities.html)
- [OPS02 Relationships and Ownerships](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/relationships-and-ownership.html)
- [OPS04-BP01 Identify key performance indicators](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_observability_identify_kpis.html)
- [OPS08 Utilizing Workload Observability](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/utilizing-workload-observability.html)
- [OPS09 Understanding Operational Health](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/understanding-operational-health.html)
- [OPS11-BP03 Implement feedback loops](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_evolve_ops_feedback_loops.html)
### Related Documents
- [Amazon Athena](https://aws.amazon.com/athena/?whats-new-cards.sort-by=item.additionalFields.postDateTime&whats-new-cards.sort-order=desc)
- [Quick Suite](https://aws.amazon.com/quicksight/)
- [AWS Compliance](https://aws.amazon.com/compliance/)
- [AWS Compliance Latest News](https://aws.amazon.com/compliance/compliance-latest-news/)
- [AWS Compliance Programs](https://aws.amazon.com/compliance/programs/)
- [AWS Glue](https://aws.amazon.com/glue/?whats-new-cards.sort-by=item.additionalFields.postDateTime&whats-new-cards.sort-order=desc)
- [AWS Latest Security Bulletins](https://aws.amazon.com/security/security-bulletins/)
- [AWS Trusted Advisor](https://aws.amazon.com/premiumsupport/trustedadvisor/)
- [Export your log data to Amazon S3](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/S3Export.html)
- [What's New with AWS](https://aws.amazon.com/new/)
- [The Imperatives of Customer-Centric Innovation](https://aws.amazon.com/executive-insights/content/the-imperatives-of-customer-centric-innovation/)
- [Digital Transformation: Hype or a Strategic Necessity?](https://aws.amazon.com/blogs/enterprise-strategy/digital-transformation-hype-or-a-strategic-necessity/)
### Related Videos
- [AWS re:Invent 2023 - Improve operational efficiency and resilience with Support (SUP310)](https://youtu.be/jaehZYBNG0Y?si=UNEaLZsXDrxcBgYo)
