---
id: "SUS02-BP02"
title: "Align SLAs with sustainability goals"
pillar: "Sustainability"
risk_level: "LOW"
capability: "How do you align cloud resources to your demand?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/sustainability-pillar/sus_sus_user_a3.html"
description: "Review and optimize workload service-level agreements (SLA) based on your sustainability goals to minimize the resources required to support your workload while continuing to meet business needs."
area: ["Alignment to demand"]
---

# SUS02-BP02 Align SLAs with sustainability goals

Review and optimize workload service-level agreements
(SLA) based on your sustainability goals to minimize the
resources required to support your workload while continuing
to meet business needs.

**Common anti-patterns:**

- Workload SLAs are unknown or ambiguous.
- You define your SLA just for availability and performance.
- You use the same design pattern (like Multi-AZ architecture) for all your workloads.

**Benefits of establishing this best practice:** Aligning
SLAs with sustainability goals leads to optimal resource usage while meeting business
needs.

**Level of risk exposed if this best practice
is not established:** Low

## Implementation guidance

SLAs define the level of service expected from a cloud workload,
such as response time, availability, and data retention. They
influence the architecture, resource usage, and environmental
impact of a cloud workload. At a regular cadence, review SLAs
and make trade-offs that significantly reduce resource usage
in exchange for acceptable decreases in service levels.

### Implementation steps

- **Understand sustainability goals:** Identify sustainability goals in your organization, such as carbon reduction or improving resource utilization.
- **Review SLAs:** Evaluate your SLAs to assess if they support your business requirements. If you are exceeding SLAs, perform further review.
- **Understand trade-offs:** Understand the trade-offs across your workload’s complexity (like high volume of concurrent users), performance (like latency), and sustainability impact (like required resources). Typically, prioritizing two of the factors comes at the expense of the third.
- **Adjust SLAs:** Adjust your SLAs by making trade-offs that significantly reduce sustainability impacts in exchange for acceptable decreases in service levels.

**Sustainability and reliability:** Highly available workloads tend to consume more resources.
- **Sustainability and performance:** Using more resources to boost performance could have a higher environmental impact.
- **Sustainability and security:** Overly secure workloads could have a higher environmental impact.

- **Define sustainability SLAs if possible:** Include sustainability SLAs for your workload. For example, define a minimum utilization level as a sustainability SLA for your compute instances.
- **Use efficient design patterns:** Use design patterns such as microservices on AWS that prioritize business-critical functions and allow lower service levels (such as response time or recovery time objectives) for non-critical functions.
- **Communicate and establish accountability:** Share the SLAs with all relevant stakeholders, including your development team and your customers. Use reporting to track and monitor the SLAs. Assign accountability to meet the sustainability targets for your SLAs.
- **Use incentives and rewards:** Use incentives and rewards to achieve or exceed SLAs aligned with sustainability goals.
- **Review and iterate:** Regularly review and adjust your SLAs to make sure they are aligned with evolving sustainability and performance goals.

## Resources

**Related documents:**

- [Understand resiliency patterns and trade-offs to architect efficiently in the cloud](https://aws.amazon.com/blogs/architecture/understand-resiliency-patterns-and-trade-offs-to-architect-efficiently-in-the-cloud/)
- [Importance
of Service Level Agreement for SaaS Providers](https://aws.amazon.com/blogs/apn/importance-of-service-level-agreement-for-saas-providers/)

**Related videos:**

- [AWS re:Invent 2023 - Capacity, availability, cost efficiency: Pick three](https://www.youtube.com/watch?v=E0dYLPXrX_w)
- [AWS re:Invent 2023 - Sustainable architecture: Past, present, and future](https://www.youtube.com/watch?v=2xpUQ-Q4QcM)
- [AWS re:Invent 2023 - Advanced integration patterns & trade-offs for loosely coupled systems](https://www.youtube.com/watch?v=FGKGdUiZKto)
- [AWS re:Invent 2022 - Delivering sustainable, high-performing architectures](https://www.youtube.com/watch?v=FBc9hXQfat0)
- [AWS re:Invent 2022 - Build a cost-, energy-, and resource-efficient compute environment](https://www.youtube.com/watch?v=8zsC5e1eLCg)
