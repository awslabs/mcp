---
id: "OPS07-BP04"
title: "Use playbooks to investigate issues"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you know that you are ready to support a workload?"
risk_level: "Medium"
effort: "Low"
---

# OPS07-BP04 Use playbooks to investigate issues

## Desired Outcome
Your organization has playbooks for common incidents. The playbooks are stored in a central location and available to your team members. Playbooks are updated frequently. For any known root causes, companion runbooks are built.

## Anti-Patterns
- There is no standard way to investigate an incident.
- Team members rely on muscle memory or institutional knowledge to troubleshoot a failed deployment.
- New team members learn how to investigate issues through trial and error.
- Best practices for investigating issues are not shared across teams.

## Implementation Guidance
 How you build and use playbooks depends on the maturity of your organization. If you are new to the cloud, build playbooks in text form in a central document repository. As your organization matures, playbooks can become semi-automated with scripting languages like Python. These scripts can be run inside a Jupyter notebook to speed up discovery. Advanced organizations have fully automated playbooks for common issues that are auto-remediated with runbooks.

 Start building your playbooks by listing common incidents that happen to your workload. Choose playbooks for incidents that are low risk and where the root cause has been narrowed down to a few issues to start. After you have playbooks for simpler scenarios, move on to the higher risk scenarios or scenarios where the root cause is not well known.

 Your text playbooks should be automated as your organization matures. Using services like [AWS Systems Manager Automations](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-automation.html), flat text can be transformed into automations. These automations can be run against your workload to speed up investigations. These automations can be activated in response to events, reducing the mean time to discover and resolve incidents.

 Customers can use [AWS Systems Manager Incident Manager](https://docs.aws.amazon.com/incident-manager/latest/userguide/what-is-incident-manager.html) to respond to incidents. This service provides a single interface to triage incidents, inform stakeholders during discovery and mitigation, and collaborate throughout the incident. It uses AWS Systems Manager Automations to speed up detection and recovery.

 **Customer example**

 A production incident impacted AnyCompany Retail. The on-call engineer used a playbook to investigate the issue. As they progressed through the steps, they kept the key stakeholders, identified in the playbook, up to date. The engineer identified the root cause as a race condition in a backend service. Using a runbook, the engineer relaunched the service, bringing AnyCompany Retail back online.

## Implementation Steps
 If you don't have an existing document repository, we suggest creating a version control repository for your playbook library. You can build your playbooks using Markdown, which is compatible with most playbook automation systems. If you are starting from scratch, use the following example playbook template.

```
# Playbook Title
## Playbook Info
| Playbook ID | Description | Tools Used | Special Permissions | Playbook Author | Last Updated | Escalation POC | Stakeholders | Communication Plan |
|-------|-------|-------|-------|-------|-------|-------|-------|-------|
| RUN001 | What is this playbook for? What incident is it used for? | Tools | Permissions | Your Name | 2022-09-21 | Escalation Name | Stakeholder Name | How will updates be communicated during the investigation? |
## Steps
1. Step one
2. Step two
```

1.  If you don't have an existing document repository or wiki, create a new version control repository for your playbooks in your version control system.

1.  Identify a common issue that requires investigation. This should be a scenario where the root cause is limited to a few issues and resolution is low risk.

1.  Using the Markdown template, fill in the Playbook Name section and the fields under Playbook Info.

1.  Fill in the troubleshooting steps. Be as clear as possible on what actions to perform or what areas you should investigate.

1.  Give a team member the playbook and have them go through it to validate it. If there's anything missing or something isn't clear, update the playbook.

1.  Publish your playbook in your document repository and inform your team and any stakeholders.

1.  This playbook library will grow as you add more playbooks. Once you have several playbooks, start automating them using tools like AWS Systems Manager Automations to keep automation and playbooks in sync.

## Resources
### Related Best Practices
- [OPS02-BP02 Processes and procedures have identified owners](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_ops_model_def_proc_owners.html)
- [OPS07-BP03 Use runbooks to perform procedures](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_ready_to_support_use_runbooks.html)
- [OPS10-BP01 Use a process for event, incident, and problem management](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_event_response_event_incident_problem_process.html)
- [OPS10-BP02 Have a process per alert](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_event_response_process_per_alert.html)
- [OPS11-BP04 Perform knowledge management](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_evolve_ops_knowledge_management.html)
### Related Documents
- [Achieving Operational Excellence using automated playbook and runbook](https://aws.amazon.com/blogs/mt/achieving-operational-excellence-using-automated-playbook-and-runbook/)
- [AWS Systems Manager: Working with runbooks](https://docs.aws.amazon.com/systems-manager/latest/userguide/automation-documents.html)
- [Use AWS Systems Manager Automation runbooks to resolve operational tasks](https://aws.amazon.com/blogs/mt/use-aws-systems-manager-automation-runbooks-to-resolve-operational-tasks/)
### Related Videos
- [AWS re:Invent 2019: DIY guide to runbooks, incident reports, and incident response (SEC318-R1)](https://www.youtube.com/watch?v=E1NaYN_fJUo)
- [AWS Systems Manager Incident Manager - AWS Virtual Workshops](https://www.youtube.com/watch?v=KNOc0DxuBSY)
- [Integrate Scripts into AWS Systems Manager](https://www.youtube.com/watch?v=Seh1RbnF-uE)
### Related Examples
- [AWS Customer Playbook Framework](https://github.com/aws-samples/aws-customer-playbook-framework)
- [AWS Systems Manager: Automation walkthroughs](https://docs.aws.amazon.com/systems-manager/latest/userguide/automation-walk.html)
- [Building an AWS incident response runbook using Jupyter notebooks and CloudTrail Lake](https://catalog.workshops.aws/workshops/a5801f0c-7bd6-4282-91ae-4dfeb926a035/en-US)
- [Rubix – A Python library for building runbooks in Jupyter Notebooks](https://github.com/Nurtch/rubix)
- [Using Document Builder to create a custom runbook](https://docs.aws.amazon.com/systems-manager/latest/userguide/automation-walk-document-builder.html)
### Related Services
- [AWS Systems Manager Automation](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-automation.html)
- [AWS Systems Manager Incident Manager](https://docs.aws.amazon.com/incident-manager/latest/userguide/what-is-incident-manager.html)
