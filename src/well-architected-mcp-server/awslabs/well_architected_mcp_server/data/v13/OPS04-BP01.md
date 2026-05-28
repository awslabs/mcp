---
id: "OPS04-BP01"
title: "Identify key performance indicators"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you implement observability in your workload?"
risk_level: "High"
effort: "Medium"
---

# OPS04-BP01 Identify key performance indicators

## Desired Outcome
Efficient observability practices that are tightly aligned with business objectives, ensuring that monitoring efforts are always in service of tangible business outcomes.

## Anti-Patterns
- Undefined KPIs: Working without clear KPIs can lead to monitoring too much or too little, missing vital signals.
- Static KPIs: Not revisiting or refining KPIs as the workload or business objectives evolve.
- Misalignment: Focusing on technical metrics that don’t correlate directly with business outcomes or are harder to correlate with real-world issues.

## Implementation Guidance
 To effectively define workload KPIs:

1.  **Start with business outcomes:** Before diving into metrics, understand the desired business outcomes. Is it increased sales, higher user engagement, or faster response times?

1.  **Correlate technical metrics with business objectives:** Not all technical metrics have a direct impact on business outcomes. Identify those that do, but it's often more straightforward to identify an issue using a business KPI.

1.  **Use [Amazon CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html):** Employ CloudWatch to define and monitor metrics that represent your KPIs.

1.  **Regularly review and update KPIs:** As your workload and business evolve, keep your KPIs relevant.

1.  **Involve stakeholders:** Involve both technical and business teams in defining and reviewing KPIs.

## Resources
### Related Best Practices
- [OPS04-BP02 Implement application telemetry](ops_observability_application_telemetry.md)
- [OPS04-BP03 Implement user experience telemetry](ops_observability_customer_telemetry.md)
- [OPS04-BP04 Implement dependency telemetry](ops_observability_dependency_telemetry.md)
- [OPS04-BP05 Implement distributed tracing](ops_observability_dist_trace.md)
### Related Documents
- [AWS Observability Best Practices ](https://aws-observability.github.io/observability-best-practices/)
- [ CloudWatch User Guide ](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html)
- [AWS Observability Skill Builder Course ](https://explore.skillbuilder.aws/learn/course/external/view/elearning/14688/aws-observability)
### Related Videos
- [ Developing an observability strategy ](https://www.youtube.com/watch?v=Ub3ATriFapQ)
### Related Examples
- [One Observability Workshop](https://catalog.workshops.aws/observability/en-US)
