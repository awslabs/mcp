---
id: "SEC01-BP08"
title: "Evaluate and implement new security services and features regularly"
framework: "WAF"
domain: "Security"
capability: "How do you securely operate your workload?"
risk_level: "Low"
---

# SEC01-BP08 Evaluate and implement new security services and features regularly

## Desired Outcome
You have a standard practice in place that informs you of new features and services released by AWS and AWS Partners. You evaluate how these new capabilities influence the design of current and new controls for your environments and workloads.

## Anti-Patterns
- You don't subscribe to AWS blogs and RSS feeds to learn of relevant new features and services quickly
- You rely on news and updates about security services and features from second-hand sources
- You don't encourage AWS users in your organization to stay informed on the latest updates

## Implementation Guidance
 AWS informs customers of new security services and features through several channels:
- [AWS What's New](https://aws.amazon.com/new)
- [AWS News Blog](https://aws.amazon.com/blogs/aws/)
- [AWS Security Blog](https://aws.amazon.com/blogs/security/)
- [AWS Security Bulletins](https://aws.amazon.com/security/security-bulletins/)
- [AWS documentation overview](https://aws.amazon.com/documentation/)

 You can subscribe to an [AWS Daily Feature Updates](https://aws.amazon.com/blogs/aws/subscribe-to-aws-daily-feature-updates-via-amazon-sns/) topic using Amazon Simple Notification Service (Amazon SNS) for a comprehensive daily summary of updates. Some security services, such as [Amazon GuardDuty](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_sns.html) and [AWS Security Hub](https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-announcements.html), provide their own SNS topics to stay informed about new standards, findings, and other updates for those particular services.

 New services and features are also announced and described in detail during [conferences, events, and webinars](https://aws.amazon.com/events/) conducted around the globe each year. Of particular note is the annual [AWS re:Inforce](https://reinforce.awsevents.com/) security conference and the more general [AWS re:Invent](https://reinvent.awsevents.com/) conference. The previously-mentioned AWS news channels share these conference announcements about security and other services, and you can view deep dive educational breakout sessions online at the [AWS Events channel](https://www.youtube.com/c/AWSEventsChannel) on YouTube.

 You can also ask your [AWS account team](https://aws.amazon.com/startups/learn/meet-your-aws-account-team) about the latest security service updates and recommendations. You can reach out to your team through the [Sales Support form](https://aws.amazon.com/contact-us/sales-support/) if you do not have their direct contact information. Similarly, if you subscribed to [AWS Enterprise Support, ](https://aws.amazon.com/premiumsupport/plans/enterprise/)you will receive weekly updates from your Technical Account Manager (TAM) and can schedule a regular review meeting with them.

## Implementation Steps
1.  Subscribe to the various blogs and bulletins with your favorite RSS reader or to the Daily Features Updates SNS topic.

1.  Evaluate which AWS events to attend to learn first-hand about new features and services.

1.  Set up meetings with your AWS account team for any questions about updating security services and features.

1.  Consider subscribing to Enterprise Support to have regular consultations with a Technical Account Manager (TAM).

## Resources
### Related Best Practices
- [PERF01-BP01 Learn about and understand available cloud services and features](https://docs.aws.amazon.com/wellarchitected/latest/framework/perf_architecture_understand_cloud_services_and_features.html)
- [COST01-BP07 Keep up-to-date with new service releases](https://docs.aws.amazon.com/wellarchitected/latest/framework/cost_cloud_financial_management_scheduled.html)
