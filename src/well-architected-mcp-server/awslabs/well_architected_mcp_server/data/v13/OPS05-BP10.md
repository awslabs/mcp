---
id: "OPS05-BP10"
title: "Fully automate integration and deployment"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you reduce defects, ease remediation, and improve flow into production?"
risk_level: "Low"
---

# OPS05-BP10 Fully automate integration and deployment

## Desired Outcome
Developers use tools to deliver code and promote through to production. Developers do not have to log into the AWS Management Console to deliver updates. There is a full audit trail of change and configuration, meeting the needs of governance and compliance. Processes are repeatable and are standardized across teams. Developers are free to focus on development and code pushes, increasing productivity.

## Anti-Patterns
- On Friday, you finish authoring the new code for your feature branch. On Monday, after running your code quality test scripts and each of your unit tests scripts, you check in your code for the next scheduled release.
- You are assigned to code a fix for a critical issue impacting a large number of customers in production. After testing the fix, you commit your code and email change management to request approval to deploy it to production.
- As a developer, you log into the AWS Management Console to create a new development environment using non-standard methods and systems.

## Implementation Guidance
 You use build and deployment management systems to track and implement change, to reduce errors caused by manual processes, and reduce the level of effort. Fully automate the integration and deployment pipeline from code check-in through build, testing, deployment, and validation. This reduces lead time, encourages increased frequency of change, reduces the level of effort, increases the speed to market, results in increased productivity, and increases the security of your code as you promote through to production.

## Resources
### Related Best Practices
- [OPS05-BP03 Use configuration management systems](ops_dev_integ_conf_mgmt_sys.md)
- [OPS05-BP04 Use build and deployment management systems](ops_dev_integ_build_mgmt_sys.md)
### Related Documents
- [What is AWS CodeBuild?](https://docs.aws.amazon.com/codebuild/latest/userguide/welcome.html)
- [What is AWS CodeDeploy?](https://docs.aws.amazon.com/codedeploy/latest/userguide/welcome.html)
### Related Videos
- [AWS re:Invent 2022 - AWS Well-Architected best practices for DevOps on AWS](https://youtu.be/hfXokRAyorA)
