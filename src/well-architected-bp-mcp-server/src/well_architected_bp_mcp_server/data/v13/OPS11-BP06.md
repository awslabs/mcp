---
id: "OPS11-BP06"
title: "Validate insights"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you evolve operations?"
risk_level: "Medium"
---

# OPS11-BP06 Validate insights

## Anti-Patterns
- You release a new feature. This feature changes some of your customer behaviors. Your observability does not take these changes into account. You do not quantify the benefits of these changes.
- You push a new update and neglect refreshing your CDN. The CDN cache is no longer compatible with the latest release. You measure the percentage of requests with errors. All of your users report HTTP 400 errors when communicating with backend servers. You investigate the client errors and find that because you measured the wrong dimension, your time was wasted.
- Your service-level agreement stipulates 99.9% uptime, and your recovery point objective is four hours. The service owner maintains that the system is zero downtime. You implement an expensive and complex replication solution, which wastes time and money.

## Implementation Guidance
- **Validate insights:** Engage with business owners and subject matter experts to ensure there is common understanding and agreement of the meaning of the data you have collected. Identify additional concerns, potential impacts, and determine a courses of action.

## Resources
### Related Best Practices
- [OPS01-BP06 Evaluate tradeoffs while managing benefits and risks](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_priorities_eval_tradeoffs.html)
- [OPS02-BP06 Responsibilities between teams are predefined or negotiated](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_ops_model_def_neg_team_agreements.html)
- [OPS11-BP03 Implement feedback loops](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_evolve_ops_feedback_loops.html)
### Related Documents
- [Designing a Cloud Center of Excellence (CCOE)](https://aws.amazon.com/blogs/enterprise-strategy/designing-a-cloud-center-of-excellence-ccoe/)
### Related Videos
- [Building observability to increase resiliency](https://youtu.be/6bJkYtrMMPI?si=yu8tVMz4a6ax9f34&t=2695)
