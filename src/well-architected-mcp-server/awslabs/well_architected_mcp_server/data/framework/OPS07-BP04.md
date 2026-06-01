---
id: "OPS07-BP04"
title: "Use playbooks to investigate issues"
pillar: "Operational Excellence"
risk_level: "MEDIUM"
capability: "How do you know that you are ready to support a workload?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_ready_to_support_use_playbooks.html"
description: "Playbooks are step-by-step guides used to investigate an incident. When incidents happen, playbooks are used to investigate, scope impact, and identify a root cause. Playbooks are used for a variety of scenarios, from failed deployments to security incidents. In many cases, playbooks identify the root cause that a runbook is used to mitigate. Playbooks are an essential component of your organization's incident response plans."
area: ["Prepare", "Operational readiness and change management"]
relatedIds: ["OPS02-BP02", "OPS07-BP03", "OPS10-BP01", "OPS10-BP02", "OPS11-BP04"]
---

# OPS07-BP04 Use playbooks to investigate issues

*Playbooks* are step-by-step guides used to investigate an incident.
When incidents happen, playbooks are used to investigate, scope
impact, and identify a root cause. Playbooks are used for a variety
of scenarios, from failed deployments to security incidents. In many
cases, playbooks identify the root cause that a runbook is used to
mitigate. Playbooks are an essential component of your
organization's incident response plans.

A good playbook has several key features. It guides the user, step
by step, through the process of discovery. Thinking outside-in, what
steps should someone follow to diagnose an incident? Clearly define
in the playbook if special tools or elevated permissions are needed
in the playbook. Having a communication plan to update stakeholders
on the status of the investigation is a key component. In situations
where a root cause can't be identified, the playbook should have an
escalation plan. If the root cause is identified, the playbook
should point to a runbook that describes how to resolve it.
Playbooks should be stored centrally and regularly maintained. If
playbooks are used for specific alerts, provide your team with
pointers to the playbook within the alert.

As your organization matures, automate your playbooks. Start with
playbooks that cover low-risk incidents. Use scripting to automate
the discovery steps. Make sure that you have companion runbooks to
mitigate common root causes.

**Desired outcome:** Your
organization has playbooks for common incidents. The playbooks are
stored in a central location and available to your team members.
Playbooks are updated frequently. For any known root causes,
companion runbooks are built.

**Common anti-patterns:**

- There is no standard way to investigate an incident.
- Team members rely on muscle memory or institutional knowledge to
troubleshoot a failed deployment.
- New team members learn how to investigate issues through trial
and error.
- Best practices for investigating issues are not shared across
teams.

**Benefits of establishing this best
practice:**

- Playbooks boost your efforts to mitigate incidents.
- Different team members can use the same playbook to identify a
root cause in a consistent manner.
- Known root causes can have runbooks developed for them, speeding
up recovery time.
- Playbooks help team members to start contributing sooner.
- Teams can scale their processes with repeatable playbooks.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

How you build and use playbooks depends on the maturity of your
organization. If you are new to the cloud, build playbooks in text
form in a central document repository. As your organization
matures, playbooks can become semi-automated with scripting
languages like Python. These scripts can be run inside a Jupyter
notebook to speed up discovery. Advanced organizations have fully
automated playbooks for common issues that are auto-remediated
with runbooks.

Start building your playbooks by listing common incidents that
happen to your workload. Choose playbooks for incidents that are
low risk and where the root cause has been narrowed down to a few
issues to start. After you have playbooks for simpler scenarios,
move on to the higher risk scenarios or scenarios where the root
cause is not well known.

Your text playbooks should be automated as your organization
matures. Using services like
[AWS Systems Manager Automations](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-automation.html), flat text can be transformed
into automations. These automations can be run against your
workload to speed up investigations. These automations can be
activated in response to events, reducing the mean time to
discover and resolve incidents.

Customers can use
[AWS Systems Manager Incident Manager](https://docs.aws.amazon.com/incident-manager/latest/userguide/what-is-incident-manager.html) to respond to incidents.
This service provides a single interface to triage incidents,
inform stakeholders during discovery and mitigation, and
collaborate throughout the incident. It uses AWS Systems Manager
Automations to speed up detection and recovery.

**Customer example**

A production incident impacted AnyCompany Retail. The on-call
engineer used a playbook to investigate the issue. As they
progressed through the steps, they kept the key stakeholders,
identified in the playbook, up to date. The engineer identified
the root cause as a race condition in a backend service. Using a
runbook, the engineer relaunched the service, bringing AnyCompany
Retail back online.

### Implementation steps

If you don't have an existing document repository, we suggest
creating a version control repository for your playbook library.
You can build your playbooks using Markdown, which is compatible
with most playbook automation systems. If you are starting from
scratch, use the following example playbook template.

# Playbook Title
## Playbook Info
| Playbook ID | Description | Tools Used | Special Permissions | Playbook Author | Last Updated | Escalation POC | Stakeholders | Communication Plan |
|-------|-------|-------|-------|-------|-------|-------|-------|-------|
| RUN001 | What is this playbook for? What incident is it used for? | Tools | Permissions | Your Name | 2022-09-21 | Escalation Name | Stakeholder Name | How will updates be communicated during the investigation? |
## Steps
1. Step one
2. Step two

- If you don't have an existing document repository or wiki,
create a new version control repository for your playbooks
in your version control system.
- Identify a common issue that requires investigation. This
should be a scenario where the root cause is limited to a
few issues and resolution is low risk.
- Using the Markdown template, fill in the Playbook Name
section and the fields under Playbook Info.
- Fill in the troubleshooting steps. Be as clear as possible
on what actions to perform or what areas you should
investigate.
- Give a team member the playbook and have them go through it
to validate it. If there's anything missing or something
isn't clear, update the playbook.
- Publish your playbook in your document repository and inform
your team and any stakeholders.
- This playbook library will grow as you add more playbooks.
Once you have several playbooks, start automating them using
tools like AWS Systems Manager Automations to keep
automation and playbooks in sync.

**Level of effort for the implementation
plan:** Low. Your playbooks should be text documents
stored in a central location. More mature organizations will
move towards automating playbooks.

## Resources

**Related best practices:**

- [OPS02-BP02
Processes and procedures have identified owners](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_ops_model_def_proc_owners.html)
- [OPS07-BP03
Use runbooks to perform procedures](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_ready_to_support_use_runbooks.html)
- [OPS10-BP01
Use a process for event, incident, and problem
management](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_event_response_event_incident_problem_process.html)
- [OPS10-BP02
Have a process per alert](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_event_response_process_per_alert.html)
- [OPS11-BP04
Perform knowledge management](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_evolve_ops_knowledge_management.html)

**Related documents:**

- [Achieving
Operational Excellence using automated playbook and
runbook](https://aws.amazon.com/blogs/mt/achieving-operational-excellence-using-automated-playbook-and-runbook/)
- [AWS Systems Manager: Working with runbooks](https://docs.aws.amazon.com/systems-manager/latest/userguide/automation-documents.html)
- [Use
AWS Systems Manager Automation runbooks to resolve operational
tasks](https://aws.amazon.com/blogs/mt/use-aws-systems-manager-automation-runbooks-to-resolve-operational-tasks/)

**Related videos:**

- [AWS re:Invent 2019: DIY guide to runbooks, incident reports, and
incident response (SEC318-R1)](https://www.youtube.com/watch?v=E1NaYN_fJUo)
- [AWS Systems Manager Incident Manager - AWS Virtual
Workshops](https://www.youtube.com/watch?v=KNOc0DxuBSY)
- [Integrate
Scripts into AWS Systems Manager](https://www.youtube.com/watch?v=Seh1RbnF-uE)

**Related examples:**

- [AWS Customer Playbook Framework](https://github.com/aws-samples/aws-customer-playbook-framework)
- [AWS Systems Manager: Automation walkthroughs](https://docs.aws.amazon.com/systems-manager/latest/userguide/automation-walk.html)
- [Building
an AWS incident response runbook using Jupyter notebooks and
CloudTrail Lake](https://catalog.workshops.aws/workshops/a5801f0c-7bd6-4282-91ae-4dfeb926a035/en-US)
- [Rubix – A
Python library for building runbooks in Jupyter
Notebooks](https://github.com/Nurtch/rubix)
- [Using
Document Builder to create a custom runbook](https://docs.aws.amazon.com/systems-manager/latest/userguide/automation-walk-document-builder.html)

**Related services:**

- [AWS Systems Manager Automation](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-automation.html)
- [AWS Systems Manager Incident Manager](https://docs.aws.amazon.com/incident-manager/latest/userguide/what-is-incident-manager.html)
