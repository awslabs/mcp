---
id: "OPS01-BP06"
title: "Evaluate tradeoffs while managing benefits and risks"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you determine what your priorities are?"
risk_level: "Medium"
effort: "Medium-High"
---

# OPS01-BP06 Evaluate tradeoffs while managing benefits and risks

## Desired Outcome
You have a clearly defined decision-making governance framework to facilitate important decisions at every level within your cloud delivery organization. This framework includes features like a risk register, defined roles that are authorized to make decisions, and a defined models for each level of decision that can be made. This framework defines in advance how conflicts are resolved, what data needs to be presented, and how options are prioritized, so that once decisions are made you can commit without delay. The decision-making framework includes a standardized approach to reviewing and weighing the benefits and risks of every decision to understand the tradeoffs. This may include external factors, such as adherence to regulatory compliance requirements.

## Anti-Patterns
- Your investors request that you demonstrate compliance with Payment Card Industry Data Security Standards (PCI DSS). You do not consider the tradeoffs between satisfying their request and continuing with your current development efforts. Instead, you proceed with your development efforts without demonstrating compliance. Your investors stop their support of your company over concerns about the security of your platform and their investments.
- You have decided to include a library that one of your developers found on the internet. You have not evaluated the risks of adopting this library from an unknown source and do not know if it contains vulnerabilities or malicious code.
- The original business justification for your migration was based upon the modernization of 60% of your application workloads. However, due to technical difficulties, a decision was made to modernize only 20%, leading to a reduction in planned benefits long-term, increased operator toil for infrastructure teams to manually support legacy systems, and greater reliance on developing new skillsets in your infrastructure teams that were not planning for this change.

## Implementation Guidance
 Managing benefits and risks should be defined by a governing body that drives the requirements for key decision-making. You want decisions to be made and prioritized based on how they benefit the organization, with an understanding of the risks involved. Accurate information is critical for making the organizational decisions. This should be based on solid measurements and defined by common industry practices of cost benefit analysis. To make these types of decisions, strike a balance between centralized and decentralized authority. There is always a tradeoff, and it's important to understand how each choice impacts defined strategies and desired business outcomes.

## Implementation Steps
1.  Formalize benefits measurement practices within a holistic cloud governance framework.

   1.  Balance central control of decision-making with decentralized authority for some decisions.

   1.  Understand that burdensome decision-making processes imposed on every decision can slow you down.

   1.  Incorporate external factors into your decision making process (like compliance requirements).

1.  Establish an agreed-upon decision-making framework for various levels of decisions, which includes who is required to unblock decisions that are subject to conflicted interests.

   1.  Centralize one-way door decisions that could be irreversible.

   1.  Allow two-way door decisions to be made by lower level organizational leaders.

1.  Understand and manage benefits and risks. Balance the benefits of decisions against the risks involved.

   1.  **Identify benefits**: Identify benefits based on business goals, needs, and priorities. Examples include business case impact, time-to-market, security, reliability, performance, and cost.

   1.  **Identify risks**: Identify risks based on business goals, needs, and priorities. Examples include time-to-market, security, reliability, performance, and cost.

   1.  **Assess benefits against risks and make informed decisions**: Determine the impact of benefits and risks based on goals, needs, and priorities of your key stakeholders, including business, development, and operations. Evaluate the value of the benefit against the probability of the risk being realized and the cost of its impact. For example, emphasizing speed-to-market over reliability might provide competitive advantage. However, it may result in reduced uptime if there are reliability issues.

1.  Programatically enforce key decisions that automate your adherence to compliance requirements.

1.  Leverage known industry frameworks and capabilities, such as Value Stream Analysis and LEAN, to baseline current state performance, business metrics, and define iterations of progress towards improvements to these metrics.

## Resources
### Related Best Practices
- [OPS01-BP05 Evaluate threat landscape](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_priorities_eval_threat_landscape.html)
### Related Documents
- [Elements of Amazon's Day 1 Culture \$1 Make high quality, high velocity decisions](https://aws.amazon.com/executive-insights/content/how-amazon-defines-and-operationalizes-a-day-1-culture/)
- [Cloud Governance](https://aws.amazon.com/cloudops/cloud-governance/)
- [Management & Governance Cloud Environment](https://docs.aws.amazon.com/wellarchitected/latest/management-and-governance-guide/management-and-governance-cloud-environment-guide.html?did=wp_card&trk=wp_card)
- [Governance in the Cloud and in the Digital Age: Parts One & Two](https://aws.amazon.com/blogs/enterprise-strategy/governance-in-the-cloud-and-in-the-digital-age-part-one/)
### Related Videos
- [Podcast \$1 Jeff Bezos \$1 On how to make decisions](https://www.youtube.com/watch?v=VFwCGECvq4I)
### Related Examples
- [Make informed decisions using data (The DevOps Sagas)](https://docs.aws.amazon.com/wellarchitected/latest/devops-guidance/oa.bcl.10-make-informed-decisions-using-data.html)
- [Using development value stream mapping to identify constraints to DevOps outcomes](https://docs.aws.amazon.com/prescriptive-guidance/latest/strategy-devops-value-stream-mapping/introduction.html)
