---
id: "OPS03-BP03"
title: "Escalation is encouraged"
pillar: "Operational Excellence"
risk_level: "HIGH"
capability: "How does your organizational culture support your business outcomes?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_org_culture_team_enc_escalation.html"
description: "Team members are encouraged by leadership to escalate issues and concerns to higher-level decision makers and stakeholders if they believe desired outcomes are at risk and expected standards are not met. This is a feature of the organization's culture and is driven at all levels. Escalation should be done early and often so that risks can be identified and prevented from causing incidents. Leadership does not reprimand individuals for escalating an issue."
area: ["Organization", "Operating model", "Organizational culture"]
relatedIds: ["OPS02-BP05"]
---

# OPS03-BP03 Escalation is encouraged

Team members are encouraged by leadership to escalate issues and
concerns to higher-level decision makers and stakeholders if they
believe desired outcomes are at risk and expected standards are not
met. This is a feature of the organization's culture and is driven
at all levels. Escalation should be done early and often so that
risks can be identified and prevented from causing incidents.
Leadership does not reprimand individuals for escalating an issue.

**Desired outcome:** Individuals
throughout the organization are comfortable to escalate problems to
their immediate and higher levels of leadership. Leadership has
deliberately and consciously established expectations that their
teams should feel safe to escalate any issue. A mechanism exists to
escalate issues at each level within the organization. When
employees escalate to their manager, they jointly decide the level
of impact and whether the issue should be escalated. In order to
initiate an escalation, employees are required to include a
recommended work plan to address the issue. If direct management
does not take timely action, employees are encouraged to take issues
to the highest level of leadership if they feel strongly that the
risks to the organization warrant the escalation.

**Common anti-patterns:**

- Executive leaders do not ask enough probing questions during
your cloud transformation program status meeting to find where
issues and blockers are occurring. Only good news is presented
as status. The CIO has made it clear that she only likes to hear
good news, as any challenges brought up make the CEO think that
the program is failing.
- You are a cloud operations engineer and you notice that the new
knowledge management system is not being widely adopted by
application teams. The company invested one year and several
million dollars to implement this new knowledge management
system, but people are still authoring their runbooks locally
and sharing them on an organizational cloud share, making it
difficult to find knowledge pertinent to supported workloads.
You try to bring this to leadership's attention, because
consistent use of this system can enhance operational
efficiency. When you bring this to the director who lead the
implementation of the knowledge management system, she
reprimands you because it calls the investment into question.
- The infosec team responsible for hardening compute resources has
decided to put a process in place that requires performing the
scans necessary to ensure that EC2 instances are fully secured
before the compute team releases the resource for use. This has
created a time delay of an additional week for resources to be
deployed, which breaks their SLA. The compute team is afraid to
escalate this to the VP over cloud because this makes the VP of
information security look bad.

**Benefits of establishing this best
practice:**

Complex or critical issues are addressed before they impact the
business. Less time is wasted. Risks are minimized. Teams become
more proactive and results focused when solving problems.

**Level of risk exposed if this best practice
is not established:** High

## Implementation guidance

The willingness and ability to escalate freely at every level in
the organization is an organizational and cultural foundation that
should be consciously developed through emphasized training,
leadership communications, expectation setting, and the deployment
of mechanisms throughout the organization at every level.

### Implementation steps

- Define policies, standards, and expectations for your
organization.

Ensure wide adoption and understanding of policies,
expectations, and standards.

- Encourage, train, and empower workers for early and frequent
escalation when standards are not met.
- Organizationally acknowledge that early and frequent
escalation is the best practice. Accept that escalations may
prove to be unfounded, and that it is better to have the
opportunity to prevent an incident then to miss that
opportunity by not escalating.

Build a mechanism for escalation (like an
Andon
cord system).
- Have documented procedures defining when and how
escalation should occur.
- Define the series of people with increasing authority to
take or approve action, as well as each stakeholder's
contact information.

- When escalation occurs, it should continue until the team
member is satisfied that the risk has been mitigated through
actions driven from leadership.

Escalations should include:

Description of the situation, and the nature of the
risk
- Criticality of the situation
- Who or what is impacted
- How great the impact is
- Urgency if impact occurs
- Suggested remedies and plans to mitigate

- Protect employees who escalate. Have policy that
protects team members from retribution if they escalate
around a non-responsive decision maker or stakeholder.
Have mechanisms in place to identify if this is
occurring and respond appropriately.

- Encourage a culture of continuous improvement feedback loops
in everything that the organization produces. Feedback loops
act as minor escalations to individuals responsible, and
they identify improvement opportunities, even when
escalation is not needed. Continuous improvement cultures
force everyone to be more proactive.
- Leadership should periodically reemphasize the policies,
standards, mechanisms, and the desire for open escalation
and continuous feedback loops without retribution.

**Level of effort for the Implementation
Plan:** Medium

## Resources

**Related best practices:**

- OPS02-BP05 Mechanisms exist to request additions, changes, and exceptions

**Related documents:**

- [How
do you foster a culture of continuous improvement and learning
from Andon and escalation systems?](https://www.linkedin.com/advice/0/how-do-you-foster-culture-continuous-improvement-7054190310033145857)
- [The
Andon Cord (IT Revolution)](https://itrevolution.com/articles/kata/)
- [AWS DevOps Guidance | Establish clear escalation paths and
encourage constructive disagreement](https://docs.aws.amazon.com/wellarchitected/latest/devops-guidance/oa.bcl.5-establish-clear-escalation-paths-and-encourage-constructive-disagreement.html)

**Related videos:**

- [Jeff
Bezos on how to make decisions (& increase
velocity)](https://www.youtube.com/watch?v=VFwCGECvq4I)
- [Toyota
Product System: Stopping Production, a Button, and an Andon
Electric Board](https://youtu.be/TUKpxjAftnk?si=qohtCCX0q78GDzJu)
- [Andon
Cord in LEAN Manufacturing](https://youtu.be/HshopyQk720?si=1XJkpCSqJSpk_zE6)

**Related examples:**

- [Working
with escalation plans in Incident Manager](https://docs.aws.amazon.com/incident-manager/latest/userguide/escalation.html)
