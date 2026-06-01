---
id: "OPS11-BP06"
title: "Validate insights"
pillar: "Operational Excellence"
risk_level: "MEDIUM"
capability: "How do you evolve operations?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_evolve_ops_validate_insights.html"
---

# OPS11-BP06 Validate insights

Review your analysis results and responses with cross-functional
teams and business owners. Use these reviews to establish common
understanding, identify additional impacts, and determine courses of
action. Adjust responses as appropriate.

**Desired outcomes:**

- You review insights with business owners on a regular basis.
Business owners provide additional context to newly-gained
insights.
- You review insights and request feedback from technical peers,
and you share your learnings across teams.
- You publish data and insights for other technical and business
teams to review. You factor in your learnings to new practices
by other departments.
- Summarize and review new insights with senior leaders. Senior
leaders use new insights to define strategy.

**Common anti-patterns:**

- You release a new feature. This feature changes some of your
customer behaviors. Your observability does not take these
changes into account. You do not quantify the benefits of these
changes.
- You push a new update and neglect refreshing your CDN. The CDN
cache is no longer compatible with the latest release. You
measure the percentage of requests with errors. All of your
users report HTTP 400 errors when communicating with backend
servers. You investigate the client errors and find that because
you measured the wrong dimension, your time was wasted.
- Your service-level agreement stipulates 99.9% uptime, and your
recovery point objective is four hours. The service owner maintains
that the system is zero downtime. You implement an expensive and
complex replication solution, which wastes time and money.

**Benefits of establishing this best practice:**

- When you validate insights with business owners and
subject matter experts, you establish common understanding and more
effectively guide improvement.
- You discover hidden issues and factor them into future
decisions.
- Your focus moves from technical outcomes to business outcomes.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

- **Validate insights:** Engage with business owners and subject
matter experts to ensure there is common understanding and
agreement of the meaning of the data you have collected.
Identify additional concerns, potential impacts, and determine
a courses of action.

## Resources

**Related best practices:**

- [OPS01-BP06
Evaluate tradeoffs while managing benefits and risks](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_priorities_eval_tradeoffs.html)
- [OPS02-BP06
Responsibilities between teams are predefined or
negotiated](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_ops_model_def_neg_team_agreements.html)
- [OPS11-BP03
Implement feedback loops](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_evolve_ops_feedback_loops.html)

**Related documents:**

- [Designing
a Cloud Center of Excellence (CCOE)](https://aws.amazon.com/blogs/enterprise-strategy/designing-a-cloud-center-of-excellence-ccoe/)

**Related videos:**

- [Building
observability to increase resiliency](https://youtu.be/6bJkYtrMMPI?si=yu8tVMz4a6ax9f34&t=2695)
