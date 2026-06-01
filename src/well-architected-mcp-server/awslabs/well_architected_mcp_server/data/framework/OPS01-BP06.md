---
id: "OPS01-BP06"
title: "Evaluate tradeoffs while managing benefits and risks"
pillar: "Operational Excellence"
risk_level: "MEDIUM"
capability: "How do you determine what your priorities are?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_priorities_eval_tradeoffs.html"
---

# OPS01-BP06 Evaluate tradeoffs while managing benefits and risks

Competing interests from multiple parties can make it challenging to
prioritize efforts, build capabilities, and deliver outcomes aligned
with business strategies. For example, you may be asked to
accelerate speed-to-market for new features over optimizing IT
infrastructure costs. This can put two interested parties in
conflict with one another. In these situations, decisions need to be
brought to a higher authority to resolve conflict. Data is required
to remove emotional attachment from the decision-making process.

The same challenge may occur at a tactical level. For example, the
choice between using relational or non-relational database
technologies can have a significant impact on the operation of an
application. It's critical to understand the predictable results of
various choices.

AWS can help you educate your teams about AWS and its services to
increase their understanding of how their choices can have an impact
on your workload. Use the resources provided by
[Support](https://aws.amazon.com/premiumsupport/programs/)
([AWS Knowledge Center](https://aws.amazon.com/premiumsupport/knowledge-center/),
[AWS Discussion Forums](https://forums.aws.amazon.com/index.jspa), and
[Support Center](https://console.aws.amazon.com/support/home/)) and
[AWS Documentation](https://docs.aws.amazon.com/) to educate your teams. For further questions,
reach out to Support.

AWS also shares operational best practices and patterns in
[The
Amazon Builders' Library](https://aws.amazon.com/builders-library/). A wide variety of other useful
information is available through the
[AWS Blog](https://aws.amazon.com/blogs/) and
[The
Official AWS Podcast](https://aws.amazon.com/podcasts/aws-podcast/).

**Desired outcome:** You have a
clearly defined decision-making governance framework to facilitate
important decisions at every level within your cloud delivery
organization. This framework includes features like a risk register,
defined roles that are authorized to make decisions, and a defined
models for each level of decision that can be made. This framework
defines in advance how conflicts are resolved, what data needs to be
presented, and how options are prioritized, so that once decisions
are made you can commit without delay. The decision-making framework
includes a standardized approach to reviewing and weighing the
benefits and risks of every decision to understand the tradeoffs.
This may include external factors, such as adherence to regulatory
compliance requirements.

**Common anti-patterns:**

- Your
investors request that you demonstrate compliance with Payment Card
Industry Data Security Standards (PCI DSS). You do not consider the
tradeoffs between satisfying their request and continuing with your
current development efforts. Instead, you proceed with your
development efforts without demonstrating compliance. Your investors
stop their support of your company over concerns about the security
of your platform and their investments.
- You have decided to include a library that one of your
developers found on the internet. You have not evaluated the
risks of adopting this library from an unknown source and do not
know if it contains vulnerabilities or malicious code.
- The original business justification for your migration was based
upon the modernization of 60% of your application workloads.
However, due to technical difficulties, a decision was made to
modernize only 20%, leading to a reduction in planned benefits
long-term, increased operator toil for infrastructure teams to
manually support legacy systems, and greater reliance on
developing new skillsets in your infrastructure teams that were
not planning for this change.

**Benefits of establishing this best
practice:** Fully aligning and supporting board-level
business priorities, understanding the risks to achieving success,
making informed decisions, and acting appropriately when risks
impede chances for success. Understanding the implications and
consequences of your decisions helps you to prioritize your options
and bring leaders into agreement faster, leading to improved
business outcomes. Identifying the available benefits of your
choices and being aware of the risks to your organization helps you
make data-driven decisions, rather than relying on anecdotes.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

Managing benefits and risks should be defined by a governing body
that drives the requirements for key decision-making. You want
decisions to be made and prioritized based on how they benefit the
organization, with an understanding of the risks involved.
Accurate information is critical for making the organizational
decisions. This should be based on solid measurements and defined
by common industry practices of cost benefit analysis. To make
these types of decisions, strike a balance between centralized and
decentralized authority. There is always a tradeoff, and it's
important to understand how each choice impacts defined strategies
and desired business outcomes.

### Implementation steps

- Formalize benefits measurement practices within a holistic
cloud governance framework.

Balance central control of decision-making with
decentralized authority for some decisions.
- Understand that burdensome decision-making processes
imposed on every decision can slow you down.
- Incorporate external factors into your decision making
process (like compliance requirements).

- Establish an agreed-upon decision-making framework for
various levels of decisions, which includes who is required
to unblock decisions that are subject to conflicted
interests.

Centralize one-way door decisions that could be
irreversible.
- Allow two-way door decisions to be made by lower level
organizational leaders.

- Understand and manage benefits and risks. Balance the
benefits of decisions against the risks involved.

**Identify benefits**:
Identify benefits based on business goals, needs, and
priorities. Examples include business case impact,
time-to-market, security, reliability, performance, and
cost.
- **Identify risks**:
Identify risks based on business goals, needs, and
priorities. Examples include time-to-market, security,
reliability, performance, and cost.
- **Assess benefits against risks
and make informed decisions**: Determine the
impact of benefits and risks based on goals, needs, and
priorities of your key stakeholders, including business,
development, and operations. Evaluate the value of the
benefit against the probability of the risk being
realized and the cost of its impact. For example,
emphasizing speed-to-market over reliability might
provide competitive advantage. However, it may result in
reduced uptime if there are reliability issues.

- Programatically enforce key decisions that automate your
adherence to compliance requirements.
- Leverage known industry frameworks and capabilities, such as
Value Stream Analysis and LEAN, to baseline current state
performance, business metrics, and define iterations of
progress towards improvements to these metrics.

**Level of effort for the implementation
plan:** Medium-High

## Resources

**Related best practices:**

- [OPS01-BP05
Evaluate threat landscape](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_priorities_eval_threat_landscape.html)

**Related documents:**

- [Elements
of Amazon's Day 1 Culture | Make high quality, high velocity
decisions](https://aws.amazon.com/executive-insights/content/how-amazon-defines-and-operationalizes-a-day-1-culture/)
- [Cloud
Governance](https://aws.amazon.com/cloudops/cloud-governance/)
- [Management
& Governance Cloud Environment](https://docs.aws.amazon.com/wellarchitected/latest/management-and-governance-guide/management-and-governance-cloud-environment-guide.html?did=wp_card&trk=wp_card)
- [Governance
in the Cloud and in the Digital Age: Parts One &
Two](https://aws.amazon.com/blogs/enterprise-strategy/governance-in-the-cloud-and-in-the-digital-age-part-one/)

**Related videos:**

- [Podcast
| Jeff Bezos | On how to make decisions](https://www.youtube.com/watch?v=VFwCGECvq4I)

**Related examples:**

- [Make
informed decisions using data (The DevOps Sagas)](https://docs.aws.amazon.com/wellarchitected/latest/devops-guidance/oa.bcl.10-make-informed-decisions-using-data.html)
- [Using
development value stream mapping to identify constraints to
DevOps outcomes](https://docs.aws.amazon.com/prescriptive-guidance/latest/strategy-devops-value-stream-mapping/introduction.html)
