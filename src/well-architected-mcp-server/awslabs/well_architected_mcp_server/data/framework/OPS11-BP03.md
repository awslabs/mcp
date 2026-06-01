---
id: "OPS11-BP03"
title: "Implement feedback loops"
pillar: "Operational Excellence"
risk_level: "HIGH"
capability: "How do you evolve operations?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_evolve_ops_feedback_loops.html"
---

# OPS11-BP03 Implement feedback loops

Feedback loops provide actionable insights that drive decision making.
Build feedback loops into your procedures and workloads. This helps you
identify issues and areas that need improvement. They also validate investments
made in improvements. These feedback loops are the foundation for continuously
improving your workload.

Feedback loops fall into two categories: *immediate feedback* and *retrospective analysis*.
Immediate feedback is gathered through review of the performance and outcomes from operations
activities. This feedback comes from team members, customers, or the automated output of
the activity. Immediate feedback is received from things like A/B testing and shipping new
features, and it is essential to failing fast.

Retrospective analysis is performed regularly to capture feedback from the review of
operational outcomes and metrics over time. These retrospectives happen at the end of
a sprint, on a cadence, or after major releases or events. This type of feedback loop
validates investments in operations or your workload. It helps you measure success and
validates your strategy.

**Desired outcome:** You use immediate feedback and retrospective
analysis to drive improvements. There is a mechanism to capture user and team member feedback.
Retrospective analysis is used to identify trends that drive improvements.

**Common anti-patterns:**

- You launch a new feature but have no way of receiving customer feedback on it.
- After investing in operations improvements, you don’t conduct a retrospective to validate them.
- You collect customer feedback but don’t regularly review it.
- Feedback loops lead to proposed action items but they aren’t included in the software development process.
- Customers don’t receive feedback on improvements they’ve proposed.

**Benefits of establishing this best
practice:**

- You can work backwards from the customer to drive new features.
- Your organization culture can react to changes faster.
- Trends are used to identify improvement opportunities.
- Retrospectives validate investments made to your workload and operations.

**Level of risk exposed if this best practice
is not established:** High

## Implementation guidance

Implementing this best practice means that you use both immediate feedback and retrospective analysis.
These feedback loops drive improvements. There are many mechanisms for immediate feedback, including
surveys, customer polls, or feedback forms. Your organization also uses retrospectives to identify
improvement opportunities and validate initiatives.

**Customer example**

AnyCompany Retail created a web form where customers can give feedback or report issues. During the weekly
scrum, user feedback is evaluated by the software development team. Feedback is regularly used to steer the
evolution of their platform. They conduct a retrospective at the end of each sprint to identify items they
want to improve.

## Implementation steps

- Immediate feedback

You need a mechanism to receive feedback from customers and team members.
Your operations activities can also be configured to deliver automated feedback.
- Your organization needs a process to review this feedback, determine what to
improve, and schedule the improvement.
- Feedback must be added into your software development process.
- As you make improvements, follow up with the feedback submitter.

You can use [AWS Systems Manager OpsCenter](https://docs.aws.amazon.com/systems-manager/latest/userguide/OpsCenter.html) to create and track these improvements as [OpsItems](https://docs.aws.amazon.com/systems-manager/latest/userguide/OpsCenter-working-with-OpsItems.html).

- Retrospective analysis

Conduct retrospectives at the end of a development cycle, on a set cadence, or after a major release.
- Gather stakeholders involved in the workload for a retrospective meeting.
- Create three columns on a whiteboard or spreadsheet: Stop, Start, and Keep.

*Stop* is for anything that you want your team to
stop doing.
- *Start* is for ideas that you want to start
doing.
- *Keep* is for items that you want to keep doing.

- Go around the room and gather feedback from the stakeholders.
- Prioritize the feedback. Assign actions and stakeholders to any Start or Keep items.
- Add the actions to your software development process and communicate status updates to
stakeholders as you make the improvements.

**Level of effort for the implementation plan:** Medium. To implement this
best practice, you need a way to take in immediate feedback and analyze it. Also, you need to
establish a retrospective analysis process.

## Resources

**Related best practices:**

- [OPS01-BP01 Evaluate external customer needs](./ops_priorities_ext_cust_needs.html): Feedback loops are a mechanism to gather external customer needs.
- [OPS01-BP02 Evaluate internal customer needs](./ops_priorities_int_cust_needs.html): Internal stakeholders can use feedback loops to communicate needs and requirements.
- [OPS11-BP02 Perform post-incident analysis](./ops_evolve_ops_perform_rca_process.html): Post-incident analyses are an important form of retrospective analysis conducted after incidents.
- [OPS11-BP07 Perform operations metrics reviews](./ops_evolve_ops_metrics_review.html): Operations metrics reviews identify trends and areas for improvement.

**Related documents:**

- [7
Pitfalls to Avoid When Building a CCOE](https://aws.amazon.com/blogs/enterprise-strategy/7-pitfalls-to-avoid-when-building-a-ccoe/)
- [Atlassian Team
Playbook - Retrospectives](https://www.atlassian.com/team-playbook/plays/retrospective)
- [Email
Definitions: Feedback Loops](https://aws.amazon.com/blogs/messaging-and-targeting/email-definitions-feedback-loops/)
- [Establishing Feedback Loops Based on the AWS Well-Architected Framework Review](https://aws.amazon.com/blogs/architecture/establishing-feedback-loops-based-on-the-aws-well-architected-framework-review/)
- [IBM Garage Methodology - Hold a retrospective](https://www.ibm.com/garage/method/practices/learn/practice_retrospective_analysis/)
- [Investopedia – The PDCS
Cycle](https://www.investopedia.com/terms/p/pdca-cycle.asp)
- [Maximizing
Developer Effectiveness by Tim Cochran](https://martinfowler.com/articles/developer-effectiveness.html)
- [Operations Readiness Reviews (ORR) Whitepaper - Iteration](https://docs.aws.amazon.com/wellarchitected/latest/operational-readiness-reviews/iteration.html)
- [ITIL CSI - Continual Service Improvement](https://wiki.en.it-processmaps.com/index.php/ITIL_CSI_-_Continual_Service_Improvement)
- [When Toyota met e-commerce: Lean at Amazon](https://www.mckinsey.com/capabilities/operations/our-insights/when-toyota-met-e-commerce-lean-at-amazon)

**Related videos:**

- [Building Effective Customer
Feedback Loops](https://www.youtube.com/watch?v=zz_VImJRZ3U)

**Related examples:**

- [Astuto - Open source customer feedback
tool](https://github.com/riggraz/astuto)
- [AWS Solutions - QnABot on
AWS](https://aws.amazon.com/solutions/implementations/qnabot-on-aws/)
- [Fider - A platform to organize customer
feedback](https://github.com/getfider/fider)

**Related services:**

- [AWS Systems Manager OpsCenter](https://docs.aws.amazon.com/systems-manager/latest/userguide/OpsCenter.html)
