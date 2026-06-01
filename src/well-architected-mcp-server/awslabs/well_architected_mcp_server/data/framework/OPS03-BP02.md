---
id: "OPS03-BP02"
title: "Team members are empowered to take action when outcomes are at risk"
pillar: "Operational Excellence"
risk_level: "MEDIUM"
capability: "How does your organizational culture support your business outcomes?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_org_culture_team_emp_take_action.html"
---

# OPS03-BP02 Team members are empowered to take action when outcomes are at risk

A cultural behavior of ownership instilled by leadership results in
any employee feeling empowered to act on behalf of the entire
company beyond their defined scope of role and accountability.
Employees can act to proactively identify risks as they emerge and
take appropriate action. Such a culture allows employees to make
high value decisions with situational awareness.

For example, Amazon uses
[Leadership
Principles](https://www.amazon.jobs/content/en/our-workplace/leadership-principles) as the guidelines to drive desired behavior for
employees to move forward in situations, solve problems, deal with
conflict, and take action.

**Desired outcome:** Leadership has
influenced a new culture that allows individuals and teams to make
critical decisions, even at lower levels of the organization (as
long as decisions are defined with auditable permissions and safety
mechanisms). Failure is not discouraged, and teams iteratively learn
to improve their decision-making and responses to tackle similar
situations going forward. If someone's actions result in an
improvement that can benefit other teams, they proactively share
knowledge from such actions. Leadership measures operational
improvements and incentivizes the individual and organization for
adoption of such patterns.

**Common anti-patterns:**

- There isn't clear guidance or mechanisms in an organization for
what to do when a risk is identified. For example, when an
employee notices a phishing attack, they fail to report to the
security team, resulting in a large portion of the organization
falling for the attack. This causes a data breach.
- Your customers complain about service unavailability, which
primarily stems from failed deployments. Your SRE team is
responsible for the deployment tool, and an automated rollback
for deployments is in their long-term roadmap. In a recent
application rollout, one of the engineers devised a solution to
automate rolling back their application to a previous version.
Though their solution can become the pattern for SRE teams,
other teams do not adopt, as there is no process to track such
improvements. The organization continues to be plagued with
failed deployments impacting customers and causing further
negative sentiment.
- In order to stay compliant, your infosec team oversees a
long-established process to rotate shared SSH keys regularly on
behalf of operators connecting to their Amazon EC2 Linux
instances. It takes several days for the infosec teams to
complete rotating keys, and you are blocked from connecting to
those instances. No one inside or outside of infosec suggests
using other options on AWS to achieve the same result.

**Benefits of establishing this best practice:** By decentralizing authority to make decisions and
empowering your teams to decide key decisions, you are able to
address issues more quickly with increasing success rates. In
addition, teams start to realize a sense of ownership, and failures
are acceptable. Experimentation becomes a cultural mainstay.
Managers and directors do not feel as though they are micro-managed
through every aspect of their work.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

- Develop a culture where it is expected that failures can
occur.
- Define clear ownership and accountability for various
functional areas within the organization.
- Communicate ownership and accountability to everyone so that
individuals know who can help them facilitate decentralized
decisions.
- Define your one-way and two-way door decisions to help
individuals know when they do need to escalate to higher
levels of leadership.
- Create organizational awareness that all employees are
empowered to take action at various levels when outcomes are
at risk. Provide your team members documentation of
governance, permission-levels, tools, and opportunities to
practice the skills necessary to respond effectively.
- Give your team members the opportunity to practice the skills
necessary to respond to various decisions. Once decision
levels are defined, perform game days to verify that all
individual contributors understand and can demonstrate the
process.

Provide alternative safe environments where processes and
procedures can be tested and trained upon.
- Acknowledge and create awareness that team members have
authority to take action when the outcome has a predefined
level of risk.
- Define the authority of your team members to take action
by assigning permissions and access to the workloads and
components they support.

- Provide ability for teams to share their learnings
(operational successes and failures).
- Empower teams to challenge the status quo, and provide
mechanisms to track and measure improvements, as well as their
impact to the organization.

**Level of effort for the implementation
plan:** Medium

## Resources

**Related best practices:**

- OPS01-BP06 Evaluate tradeoffs while managing benefits and risks
- [OPS02-BP05
Mechanisms exist to identify responsibility and
ownership](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_ops_model_req_add_chg_exception.html)

**Related documents:**

- [AWS Blog Post | The agile enterprise](https://aws.amazon.com/blogs/enterprise-strategy/the-agile-enterprise/)
- [AWS Blog Post | Measuring success : A paradox and a plan](https://aws.amazon.com/blogs/enterprise-strategy/measuring-success-a-paradox-and-a-plan/)
- [AWS Blog Post | Letting go : Enabling autonomy in teams](https://aws.amazon.com/blogs/enterprise-strategy/letting-go-enabling-autonomy-in-teams/)
- [Centralize
or Decentralize?](https://aws.amazon.com/blogs/enterprise-strategy/centralize-or-decentralize/)

**Related videos:**

- [re:Invent
2023 | How to not sabotage your transformation (SEG201)](https://www.youtube.com/watch?v=heLvxK5N8Aw)
- [re:Invent
2021 | Amazon Builders' Library: Operational Excellence at
Amazon](https://www.youtube.com/watch?v=7MrD4VSLC_w)
- [Centralization
vs. Decentralization](https://youtu.be/jviFsd4hhfE?si=fjt8avVAYxA9jF01)

**Related examples:**

- [Using
architectural decision records to streamline technical
decision-making for a software development project](https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/welcome.html)
