---
id: "OPS03-BP04"
title: "Communications are timely, clear, and actionable"
framework: "WAF"
domain: "Operational Excellence"
capability: "How does your organizational culture support your business outcomes?"
risk_level: "High"
---

# OPS03-BP04 Communications are timely, clear, and actionable

## Desired Outcome
Your organization designs communication strategies to address the impact of change to the organization. Teams remain informed and motivated to continue working with one another rather than against each other. Individuals understand how important their role is to achieve the stated objectives. Email is only a passive mechanism for communications and used accordingly. Management spends time with their individual contributors to help them understand their responsibility, the tasks to complete, and how their work contributes to the overall mission. When necessary, leaders engage people directly in smaller venues to convey messages and verify that these messages are being delivered effectively. As a result of good communications strategies, the organization performs at or above the expectations of leadership. Leadership encourages and seeks diverse opinions within and across teams.

## Anti-Patterns
- Your organization has a five year plan to migrate all workloads to AWS. The business case for cloud includes the modernization of 25% of all workloads to take advantage of serverless technology. The CIO communicates this strategy to direct reports and expects each leader to cascade this presentation to managers, directors, and individual contributors without any in-person communication. The CIO steps back and expects his organization to perform the new strategy.
- Leadership does not provide or use a mechanism for feedback, and an expectation gap grows, which leads to stalled projects.
- You are asked to make a change to your security groups, but you are not given any details of what change needs to be made, what the impact of the change could be on all the workloads, and when it should happen. The manager forwards an email from the VP of InfoSec and adds the message "Make this happen."
- Changes were made to your migration strategy that reduce the planned modernization number from 25% to 10%. This has downstream effects on the operations organization. They were not informed of this strategic change and thus, they are not ready with enough skilled capacity to support a greater number of workloads lifted and shifted into AWS.

## Implementation Guidance
 To implement this best practice, you must work with stakeholders across your organization to agree to communication standards. Publicize those standards to your organization. For any significant IT transitions, an established planning team can more successfully manage the impact of change to its people than an organization that ignores this practice. Larger organizations can be more challenging when managing change because it's critical to establish strong buy-in on a new strategy with all individual contributors. In the absence of such a transition planning team, leadership holds 100% of the responsibility for effective communications. When establishing a transition planning team, assign team members to work with all organizational leadership to define and manage effective communications at every level.

 **Customer example**

 AnyCompany Retail signed up for AWS Enterprise Support and depends on other third-party providers for its cloud operations. The company uses chat and chatops as their main communication medium for operational activities. Alerts and other information populate specific channels. When someone must act, they clearly state the desired outcome, and in many cases, they receive a runbook or playbook to use. They schedule major changes to production systems with a change calendar.

## Implementation Steps
1.  Establish a core team within the organization that has accountability to build and initiate communication plans for changes that happen at multiple levels within the organization.

1.  Institute single-threaded ownership to achieve oversight. Give individual teams the ability to innovate independently, and balance the use of consistent mechanisms, which allows for the right level of inspection and directional vision.

1.  Work with stakeholders across your organization to agree to communication standards, practices, and plans.

1.  Verify that the core communications team collaborates with organizational and program leadership to craft messages to appropriate staff on behalf of leaders.

1.  Build strategic communication mechanisms to manage change through announcements, shared calendars, all-hands meetings, and in-person or one-on-one methods so that team members have proper expectations on the actions they should take.

1.  Provide necessary context, details, and time (when possible) to determine if action is necessary. When action is needed, provide the required action and its impact.

1.  Implement tools that facilitate tactical communications, like internal chat, email, and knowledge management.

1.  Implement mechanisms to measure and verify that all communications lead to desired outcomes.

1.  Establish a feedback loop that measures the effectiveness of all communications, especially when communications are related to resistance to changes throughout the organization.

1.  For all AWS accounts, establish [alternate contacts](https://docs.aws.amazon.com/accounts/latest/reference/manage-acct-update-contact-alternate.html) for billing, security, and operations. Ideally, each contact should be an email distribution as opposed to a specific individual contact.

1.  Establish an escalation and reverse escalation communication plan to engage with your internal and external teams, including AWS support and other third-party providers.

1.  Initiate and perform communication strategies consistently throughout the life of each transformation program.

1.  Prioritize actions that are repeatable where possible to safely automate at scale.

1.  When communications are required in scenarios with automated actions, the communication's purpose should be to inform teams, for auditing, or a part of the change management process.

1.  Analyze communications from your alert systems for false positives or alerts that are constantly created. Remove or change these alerts so that they start when human intervention is required. If an alert is initiated, provide a runbook or playbook.

   1.  You can use [AWS Systems Manager Documents](https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-ssm-docs.html) to build playbooks and runbooks for alerts.

1.  Mechanisms are in place to provide notification of risks or planned events in a clear and actionable way with enough notice to allow appropriate responses. Use email lists or chat channels to send notifications ahead of planned events.

   1.  [AWS Chatbot](https://docs.aws.amazon.com/chatbot/latest/adminguide/what-is.html) can be used to send alerts and respond to events within your organizations messaging platform.

1.  Provide an accessible source of information where planned events can be discovered. Provide notifications of planned events from the same system.

   1.  [AWS Systems Manager Change Calendar](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-change-calendar.html) can be used to create change windows when changes can occur. This provides team members notice when they can make changes safely.

1.  Monitor vulnerability notifications and patch information to understand vulnerabilities in the wild and potential risks associated to your workload components. Provide notification to team members so that they can act.

   1.  You can subscribe to [AWS Security Bulletins](https://aws.amazon.com/security/security-bulletins/) to receive notifications of vulnerabilities on AWS.

1.  **Seek diverse opinions and perspectives:** Encourage contributions from everyone. Give communication opportunities to under-represented groups. Rotate roles and responsibilities in meetings.

   1.  **Expand roles and responsibilities:** Provide opportunities for team members to take on roles that they might not otherwise. They can gain experience and perspective from the role and from interactions with new team members with whom they might not otherwise interact. They can also bring their experience and perspective to the new role and team members they interact with. As perspective increases, identify emergent business opportunities or new opportunities for improvement. Rotate common tasks between members within a team that others typically perform to understand the demands and impact of performing them.

   1.  **Provide a safe and welcoming environment:** Establish policy and controls that protect the mental and physical safety of team members within your organization. Team members should be able to interact without fear of reprisal. When team members feel safe and welcome, they are more likely to be engaged and productive. The more diverse your organization, the better your understanding can be of the people you support, including your customers. When your team members are comfortable, feel free to speak, and are confident they are heard, they are more likely to share valuable insights (for example, marketing opportunities, accessibility needs, unserved market segments, and unacknowledged risks in your environment).

   1.  **Encourage team members to participate fully:** Provide the resources necessary for your employees to participate fully in all work related activities. Team members that face daily challenges develop skills for working around them. These uniquely-developed skills can provide significant benefit to your organization. Support team members with necessary accommodations to increase the benefits you can receive from their contributions.

## Resources
### Related Best Practices
- [OPS03-BP01 Provide executive sponsorship](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_org_culture_executive_sponsor.html)
- [OPS07-BP03 Use runbooks to perform procedures](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_ready_to_support_use_runbooks.html)
- [OPS07-BP04 Use playbooks to investigate issues](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_ready_to_support_use_playbooks.html)
### Related Documents
- [AWS Blog post \$1 Accountability and empowerment are key to high-performing agile organizations](https://aws.amazon.com/blogs/enterprise-strategy/two-pizza-teams-are-just-the-start-accountability-and-empowerment-are-key-to-high-performing-agile-organizations-part-2/)
- [AWS Executive Insights \$1 Learn to scale innovation, not complexity \$1 Single-threaded Leaders](https://aws.amazon.com/executive-insights/content/amazon-two-pizza-team/#Single-Threaded_Leaders)
- [AWS Security Bulletins](https://aws.amazon.com/security/security-bulletins)
- [Open CVE](https://www.opencve.io/welcome)
- [Support App in Slack to Manage Support Cases](https://aws.amazon.com/blogs/aws/new-aws-support-app-in-slack-to-manage-support-cases/)
- [Manage AWS resources in your Slack channels with Amazon Q Developer in chat applications](https://aws.amazon.com/blogs/mt/manage-aws-resources-in-your-slack-channels-with-aws-chatbot/)
### Related Services
- [Amazon Q Developer in chat applications](https://docs.aws.amazon.com/chatbot/latest/adminguide/what-is.html)
- [AWS Systems Manager Change Calendar](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-change-calendar.html)
- [AWS Systems Manager Documents](https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-ssm-docs.html)
