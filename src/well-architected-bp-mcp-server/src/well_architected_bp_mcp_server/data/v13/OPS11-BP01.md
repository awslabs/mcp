---
id: "OPS11-BP01"
title: "Have a process for continuous improvement"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you evolve operations?"
risk_level: "High"
effort: "Low"
---

# OPS11-BP01 Have a process for continuous improvement

## Desired Outcome
- You analyze your workload against architecture best practices frequently.
- You give improvement opportunities equal priority to features in your software development process.

## Anti-Patterns
- You have not conducted an architecture review on your workload since it was deployed several years ago.
- You give a lower priority to improvement opportunities. Compared to new features, these opportunities stay in the backlog.
- There is no standard for implementing modifications to best practices for the organization.

## Implementation Guidance
 Frequently conduct an architectural review of your workload. Use internal and external best practices, evaluate your workload, and identify improvement opportunities. Prioritize improvement opportunities into your software development cadence.

## Implementation Steps
1.  Conduct periodic architecture reviews of your production workload with an agreed-upon frequency. Use a documented architectural standard that includes AWS-specific best practices.

   1.  Use your internally-defined standards for these reviews. If you do not have an internal standard, use the AWS Well-Architected Framework.

   1.  Use the AWS Well-Architected Tool to create a custom lens of your internal best practices and conduct your architecture review.

   1.  Contact your AWS Solution Architect or Technical Account Manager to conduct a guided Well-Architected Framework Review of your workload.

1.  Prioritize improvement opportunities identified during the review into your software development process.

## Resources
### Related Best Practices
- [OPS11-BP02 Perform post-incident analysis](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_evolve_ops_perform_rca_process.html)
- [OPS11-BP08 Document and share lessons learned](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_evolve_ops_share_lessons_learned.html)
- [OPS04 Implement Observability](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_evolve_ops_process_cont_imp.html)
### Related Documents
- [AWS Well-Architected Tool - Custom lenses](https://docs.aws.amazon.com/wellarchitected/latest/userguide/lenses-custom.html)
- [AWS Well-Architected Whitepaper - The review process](https://docs.aws.amazon.com/wellarchitected/latest/framework/the-review-process.html)
- [Customize Well-Architected Reviews using Custom Lenses and the AWS Well-Architected Tool](https://aws.amazon.com/blogs/mt/customize-well-architected-reviews-using-custom-lenses-and-the-aws-well-architected-tool/)
- [Implementing the AWS Well-Architected Custom Lens lifecycle in your organization](https://aws.amazon.com/blogs/architecture/implementing-the-aws-well-architected-custom-lens-lifecycle-in-your-organization/)
### Related Videos
- [AWS re:Invent 2023 - Scaling AWS Well-Architected best practices across your organization](https://youtu.be/UXtZCoE9qfQ?si=OPATCOY2YAwiF2TS)
### Related Examples
- [AWS Well-Architected Tool](https://docs.aws.amazon.com/wellarchitected/latest/userguide/intro.html)
