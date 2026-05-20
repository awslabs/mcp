---
id: "OPS11-BP03"
title: "Implement feedback loops"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you evolve operations?"
risk_level: "High"
effort: "Medium"
---

# OPS11-BP03 Implement feedback loops

## Desired Outcome
You use immediate feedback and retrospective analysis to drive improvements. There is a mechanism to capture user and team member feedback. Retrospective analysis is used to identify trends that drive improvements.

## Anti-Patterns
- You launch a new feature but have no way of receiving customer feedback on it.
- After investing in operations improvements, you don’t conduct a retrospective to validate them.
- You collect customer feedback but don’t regularly review it.
- Feedback loops lead to proposed action items but they aren’t included in the software development process.
- Customers don’t receive feedback on improvements they’ve proposed.

## Implementation Guidance
 Implementing this best practice means that you use both immediate feedback and retrospective analysis. These feedback loops drive improvements. There are many mechanisms for immediate feedback, including surveys, customer polls, or feedback forms. Your organization also uses retrospectives to identify improvement opportunities and validate initiatives.

 **Customer example**

 AnyCompany Retail created a web form where customers can give feedback or report issues. During the weekly scrum, user feedback is evaluated by the software development team. Feedback is regularly used to steer the evolution of their platform. They conduct a retrospective at the end of each sprint to identify items they want to improve.

## Implementation Steps
1. Immediate feedback
   - You need a mechanism to receive feedback from customers and team members. Your operations activities can also be configured to deliver automated feedback.
   - Your organization needs a process to review this feedback, determine what to improve, and schedule the improvement.
   - Feedback must be added into your software development process.
   - As you make improvements, follow up with the feedback submitter.
     - You can use [AWS Systems Manager OpsCenter](https://docs.aws.amazon.com/systems-manager/latest/userguide/OpsCenter.html) to create and track these improvements as [OpsItems](https://docs.aws.amazon.com/systems-manager/latest/userguide/OpsCenter-working-with-OpsItems.html).

1.  Retrospective analysis
   - Conduct retrospectives at the end of a development cycle, on a set cadence, or after a major release.
   - Gather stakeholders involved in the workload for a retrospective meeting.
   - Create three columns on a whiteboard or spreadsheet: Stop, Start, and Keep.
     - *Stop* is for anything that you want your team to stop doing.
     - *Start* is for ideas that you want to start doing.
     - *Keep* is for items that you want to keep doing.
   - Go around the room and gather feedback from the stakeholders.
   - Prioritize the feedback. Assign actions and stakeholders to any Start or Keep items.
   - Add the actions to your software development process and communicate status updates to stakeholders as you make the improvements.

## Resources
### Related Best Practices
- [OPS01-BP01 Evaluate external customer needs](ops_priorities_ext_cust_needs.md): Feedback loops are a mechanism to gather external customer needs.
- [OPS01-BP02 Evaluate internal customer needs](ops_priorities_int_cust_needs.md): Internal stakeholders can use feedback loops to communicate needs and requirements.
- [OPS11-BP02 Perform post-incident analysis](ops_evolve_ops_perform_rca_process.md): Post-incident analyses are an important form of retrospective analysis conducted after incidents.
- [OPS11-BP07 Perform operations metrics reviews](ops_evolve_ops_metrics_review.md): Operations metrics reviews identify trends and areas for improvement.
### Related Documents
- [7 Pitfalls to Avoid When Building a CCOE](https://aws.amazon.com/blogs/enterprise-strategy/7-pitfalls-to-avoid-when-building-a-ccoe/)
- [Atlassian Team Playbook - Retrospectives](https://www.atlassian.com/team-playbook/plays/retrospective)
- [Email Definitions: Feedback Loops](https://aws.amazon.com/blogs/messaging-and-targeting/email-definitions-feedback-loops/)
- [Establishing Feedback Loops Based on the AWS Well-Architected Framework Review](https://aws.amazon.com/blogs/architecture/establishing-feedback-loops-based-on-the-aws-well-architected-framework-review/)
- [IBM Garage Methodology - Hold a retrospective](https://www.ibm.com/garage/method/practices/learn/practice_retrospective_analysis/)
- [Investopedia – The PDCS Cycle](https://www.investopedia.com/terms/p/pdca-cycle.asp)
- [Maximizing Developer Effectiveness by Tim Cochran](https://martinfowler.com/articles/developer-effectiveness.html)
- [Operations Readiness Reviews (ORR) Whitepaper - Iteration](https://docs.aws.amazon.com/wellarchitected/latest/operational-readiness-reviews/iteration.html)
- [ITIL CSI - Continual Service Improvement](https://wiki.en.it-processmaps.com/index.php/ITIL_CSI_-_Continual_Service_Improvement)
- [When Toyota met e-commerce: Lean at Amazon](https://www.mckinsey.com/capabilities/operations/our-insights/when-toyota-met-e-commerce-lean-at-amazon)
### Related Videos
- [Building Effective Customer Feedback Loops](https://www.youtube.com/watch?v=zz_VImJRZ3U)
### Related Examples
- [Astuto - Open source customer feedback tool](https://github.com/riggraz/astuto)
- [AWS Solutions - QnABot on AWS](https://aws.amazon.com/solutions/implementations/qnabot-on-aws/)
- [Fider - A platform to organize customer feedback](https://github.com/getfider/fider)
### Related Services
- [AWS Systems Manager OpsCenter](https://docs.aws.amazon.com/systems-manager/latest/userguide/OpsCenter.html)
