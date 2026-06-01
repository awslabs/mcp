---
id: "OPS05-BP10"
title: "Fully automate integration and deployment"
pillar: "Operational Excellence"
risk_level: "LOW"
capability: "How do you reduce defects, ease remediation, and improve flow into production?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_dev_integ_auto_integ_deploy.html"
description: "Automate build, deployment, and testing of the workload. This reduces errors caused by manual processes and reduces the effort to deploy changes."
area: ["Prepare", "Design for operations"]
relatedIds: ["OPS05-BP03", "OPS05-BP04"]
---

# OPS05-BP10 Fully automate integration and deployment

Automate build, deployment, and testing of the workload. This
reduces errors caused by manual processes and reduces the effort to
deploy changes.

Apply metadata using
[Resource
Tags](https://docs.aws.amazon.com/general/latest/gr/aws_tagging.html) and
[AWS Resource Groups](https://docs.aws.amazon.com/ARG/latest/APIReference/Welcome.html) following a consistent
[tagging
strategy](https://aws.amazon.com/answers/account-management/aws-tagging-strategies/) to aid in identification of your resources. Tag your
resources for organization, cost accounting, access controls, and
targeting the run of automated operations activities.

**Desired outcome:** Developers use tools to deliver code and promote through to production. Developers do not have to log into the AWS Management Console to deliver updates. There is a full audit trail of change and configuration, meeting the needs of governance and compliance. Processes are repeatable and are standardized across teams. Developers are free to focus on development and code pushes, increasing productivity.

**Common anti-patterns:**

- On Friday, you finish authoring the new code for your feature
branch. On Monday, after running your code quality test scripts
and each of your unit tests scripts, you check in your code
for the next scheduled release.
- You are assigned to code a fix for a critical issue impacting a
large number of customers in production. After testing the fix,
you commit your code and email change management to request
approval to deploy it to production.
- As a developer, you log into the AWS Management Console to create a new development environment using non-standard methods and systems.

**Benefits of establishing this best
practice:** By implementing automated build and deployment management systems, you reduce errors caused by manual processes and reduce the effort to deploy changes helping your team members to focus on delivering business value. You increase the speed of delivery as you promote through to production.

**Level of risk exposed if this best practice
is not established:** Low

## Implementation guidance

You use build and deployment management systems to track and implement change, to reduce errors caused by manual processes, and reduce the level of effort. Fully automate the integration and deployment pipeline from code check-in through build, testing, deployment, and validation. This reduces lead time, encourages increased frequency of change, reduces the level of effort, increases the speed to market, results in increased productivity, and increases the security of your code as you promote through to production.

## Resources

**Related best practices:**

- OPS05-BP03 Use configuration management systems
- OPS05-BP04 Use build and deployment management systems

**Related documents:**

- [What
is AWS CodeBuild?](https://docs.aws.amazon.com/codebuild/latest/userguide/welcome.html)
- [What
is AWS CodeDeploy?](https://docs.aws.amazon.com/codedeploy/latest/userguide/welcome.html)

**Related videos:**

- [AWS re:Invent 2022 - AWS Well-Architected best practices for DevOps on AWS](https://youtu.be/hfXokRAyorA)
