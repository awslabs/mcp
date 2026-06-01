---
id: "OPS03-BP05"
title: "Experimentation is encouraged"
pillar: "Operational Excellence"
risk_level: "MEDIUM"
capability: "How does your organizational culture support your business outcomes?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_org_culture_team_enc_experiment.html"
---

# OPS03-BP05 Experimentation is encouraged

Experimentation is a catalyst for turning new ideas into products and features. It accelerates learning and keeps team members interested and engaged. Team members are encouraged to experiment often to drive innovation. Even when an undesired result occurs, there is value in knowing what not to do. Team members are not punished for successful experiments with undesired results.

**Desired outcome:**

- Your organization encourages experimentation to foster innovation.
- Experiments are used as an opportunity to learn.

**Common anti-patterns:**

- You want to run an A/B test but there is no mechanism to run the experiment. You deploy a UI change without the ability to test it. It results in a negative customer experience.
- Your company only has a stage and production environment. There is no sandbox environment to experiment with new features or products so you must experiment within the production environment.

**Benefits of establishing this best practice:**

- Experimentation drives innovation.
- You can react faster to feedback from users through experimentation.
- Your organization develops a culture of learning.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

Experiments should be run in a safe manner. Leverage multiple environments to experiment without jeopardizing production resources. Use A/B testing and feature flags to test experiments. Provide team members the ability to conduct experiments in a sandbox environment.

**Customer example**

AnyCompany Retail encourages experimentation. Team members can use 20% of their work week to experiment or learn new technologies. They have a sandbox environment where they can innovate. A/B testing is used for new features to validate them with real user feedback.

**Implementation steps**

- Work with leadership across your organization to support experimentation. Team members should be encouraged to conduct experiments in a safe manner.
- Provide your team members with an environment where they can safely experiment. They must have access to an environment that is like production.

You can use a separate AWS account to create a sandbox environment for experimentation. [AWS Control Tower](https://docs.aws.amazon.com/controltower/latest/userguide/what-is-control-tower.html) can be used to provision these accounts.

- Use feature flags and A/B testing to experiment safely and gather user feedback.

[AWS AppConfig Feature Flags](https://docs.aws.amazon.com/appconfig/latest/userguide/what-is-appconfig.html) provides the ability to create feature flags.
- You can use [AWS Lambda versions](https://docs.aws.amazon.com/lambda/latest/dg/configuration-versions.html) to deploy a new version of a function for beta testing.

**Level of effort for the implementation plan:** High. Providing team members with an environment to experiment in and a safe way to conduct experiments can require significant investment. You may also need to modify application code to use feature flags or support A/B testing.

## Resources

**Related best practices:**

- [OPS11-BP02 Perform post-incident analysis](./ops_evolve_ops_perform_rca_process.html) - Learning from incidents is an important driver for innovation along with experimentation.
- [OPS11-BP03 Implement feedback loops](./ops_evolve_ops_feedback_loops.html) - Feedback loops are an important part of experimentation.

**Related documents:**

- [An Inside Look at the Amazon Culture: Experimentation, Failure, and Customer Obsession](https://aws.amazon.com/blogs/industries/an-inside-look-at-the-amazon-culture-experimentation-failure-and-customer-obsession/)
- [Best practices for creating and managing sandbox accounts in AWS](https://aws.amazon.com/blogs/mt/best-practices-creating-managing-sandbox-accounts-aws/)
- [Create a Culture of Experimentation Enabled by the Cloud](https://aws.amazon.com/blogs/enterprise-strategy/create-a-culture-of-experimentation-enabled-by-the-cloud/)
- [Enabling experimentation and innovation in the cloud at SulAmérica Seguros](https://aws.amazon.com/blogs/mt/enabling-experimentation-and-innovation-in-the-cloud-at-sulamerica-seguros/)
- [Experiment More, Fail Less](https://aws.amazon.com/blogs/enterprise-strategy/experiment-more-fail-less/)
- [Organizing Your AWS Environment Using Multiple Accounts - Sandbox OU](https://docs.aws.amazon.com/whitepapers/latest/organizing-your-aws-environment/sandbox-ou.html)
- [Using AWS AppConfig Feature Flags](https://aws.amazon.com/blogs/mt/using-aws-appconfig-feature-flags/)

**Related videos:**

- [AWS On Air ft. Amazon CloudWatch Evidently | AWS Events](https://www.youtube.com/watch?v=ydX7lRNKAOo)
- [AWS On Air San Fran Summit 2022 ft. AWS AppConfig Feature Flags integration with Jira](https://www.youtube.com/watch?v=miAkZPtjqHg)
- [AWS re:Invent 2022 - A deployment is not a release: Control your launches w/feature flags (BOA305-R)](https://www.youtube.com/watch?v=uouw9QxVrE8)
- [Programmatically Create an AWS account with AWS Control Tower](https://www.youtube.com/watch?v=LxxQTPdSFgw)
- [Set Up a Multi-Account AWS Environment that Uses Best Practices for AWS Organizations](https://www.youtube.com/watch?v=uOrq8ZUuaAQ)

**Related examples:**

- [AWS Innovation Sandbox](https://aws.amazon.com/solutions/implementations/aws-innovation-sandbox/)
- [End-to-end Personalization 101 for E-Commerce](https://catalog.workshops.aws/personalize-101-ecommerce/en-US/labs/ab-testing)

**Related services:**

- [Amazon CloudWatch Evidently](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Evidently.html)
- [AWS AppConfig](https://docs.aws.amazon.com/appconfig/latest/userguide/what-is-appconfig.html)
- [AWS Control Tower](https://docs.aws.amazon.com/controltower/latest/userguide/what-is-control-tower.html)
