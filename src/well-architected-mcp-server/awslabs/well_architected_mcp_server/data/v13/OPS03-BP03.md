---
id: "OPS03-BP03"
title: "Escalation is encouraged"
framework: "WAF"
domain: "Operational Excellence"
capability: "How does your organizational culture support your business outcomes?"
risk_level: "High"
effort: "Medium"
---

# OPS03-BP03 Escalation is encouraged

## Desired Outcome
Individuals throughout the organization are comfortable to escalate problems to their immediate and higher levels of leadership. Leadership has deliberately and consciously established expectations that their teams should feel safe to escalate any issue. A mechanism exists to escalate issues at each level within the organization. When employees escalate to their manager, they jointly decide the level of impact and whether the issue should be escalated. In order to initiate an escalation, employees are required to include a recommended work plan to address the issue. If direct management does not take timely action, employees are encouraged to take issues to the highest level of leadership if they feel strongly that the risks to the organization warrant the escalation.

## Anti-Patterns
- Executive leaders do not ask enough probing questions during your cloud transformation program status meeting to find where issues and blockers are occurring. Only good news is presented as status. The CIO has made it clear that she only likes to hear good news, as any challenges brought up make the CEO think that the program is failing.
- You are a cloud operations engineer and you notice that the new knowledge management system is not being widely adopted by application teams. The company invested one year and several million dollars to implement this new knowledge management system, but people are still authoring their runbooks locally and sharing them on an organizational cloud share, making it difficult to find knowledge pertinent to supported workloads. You try to bring this to leadership's attention, because consistent use of this system can enhance operational efficiency. When you bring this to the director who lead the implementation of the knowledge management system, she reprimands you because it calls the investment into question.
- The infosec team responsible for hardening compute resources has decided to put a process in place that requires performing the scans necessary to ensure that EC2 instances are fully secured before the compute team releases the resource for use. This has created a time delay of an additional week for resources to be deployed, which breaks their SLA. The compute team is afraid to escalate this to the VP over cloud because this makes the VP of information security look bad.

## Implementation Guidance
 The willingness and ability to escalate freely at every level in the organization is an organizational and cultural foundation that should be consciously developed through emphasized training, leadership communications, expectation setting, and the deployment of mechanisms throughout the organization at every level.

## Implementation Steps
1.  Define policies, standards, and expectations for your organization.

   1.  Ensure wide adoption and understanding of policies, expectations, and standards.

1.  Encourage, train, and empower workers for early and frequent escalation when standards are not met.

1.  Organizationally acknowledge that early and frequent escalation is the best practice. Accept that escalations may prove to be unfounded, and that it is better to have the opportunity to prevent an incident then to miss that opportunity by not escalating.

   1.  Build a mechanism for escalation (like an Andon cord system).

   1.  Have documented procedures defining when and how escalation should occur.

   1.  Define the series of people with increasing authority to take or approve action, as well as each stakeholder's contact information.

1.  When escalation occurs, it should continue until the team member is satisfied that the risk has been mitigated through actions driven from leadership.

   1.  Escalations should include:

      1.  Description of the situation, and the nature of the risk

      1.  Criticality of the situation

      1.  Who or what is impacted

      1.  How great the impact is

      1.  Urgency if impact occurs

      1.  Suggested remedies and plans to mitigate

   1.  Protect employees who escalate. Have policy that protects team members from retribution if they escalate around a non-responsive decision maker or stakeholder. Have mechanisms in place to identify if this is occurring and respond appropriately.

1.  Encourage a culture of continuous improvement feedback loops in everything that the organization produces. Feedback loops act as minor escalations to individuals responsible, and they identify improvement opportunities, even when escalation is not needed. Continuous improvement cultures force everyone to be more proactive.

1.  Leadership should periodically reemphasize the policies, standards, mechanisms, and the desire for open escalation and continuous feedback loops without retribution.

## Resources
### Related Best Practices
- [OPS02-BP05 Mechanisms exist to request additions, changes, and exceptions](ops_ops_model_req_add_chg_exception.md)
### Related Documents
- [How do you foster a culture of continuous improvement and learning from Andon and escalation systems?](https://www.linkedin.com/advice/0/how-do-you-foster-culture-continuous-improvement-7054190310033145857)
- [The Andon Cord (IT Revolution)](https://itrevolution.com/articles/kata/)
- [AWS DevOps Guidance \$1 Establish clear escalation paths and encourage constructive disagreement](https://docs.aws.amazon.com/wellarchitected/latest/devops-guidance/oa.bcl.5-establish-clear-escalation-paths-and-encourage-constructive-disagreement.html)
### Related Videos
- [Jeff Bezos on how to make decisions (& increase velocity)](https://www.youtube.com/watch?v=VFwCGECvq4I)
- [Toyota Product System: Stopping Production, a Button, and an Andon Electric Board](https://youtu.be/TUKpxjAftnk?si=qohtCCX0q78GDzJu)
- [Andon Cord in LEAN Manufacturing](https://youtu.be/HshopyQk720?si=1XJkpCSqJSpk_zE6)
### Related Examples
- [Working with escalation plans in Incident Manager](https://docs.aws.amazon.com/incident-manager/latest/userguide/escalation.html)
