---
id: "COST03-BP02"
title: "Add organization information to cost and usage"
framework: "WAF"
domain: "Cost Optimization"
capability: "How do you monitor your cost and usage?"
risk_level: "Medium"
---

# COST03-BP02 Add organization information to cost and usage

## Implementation Guidance
Implement [tagging in AWS](https://docs.aws.amazon.com/general/latest/gr/aws_tagging.html) to add organization information to your resources, which will then be added to your cost and usage information. A tag is a key-value pair — the key is defined and must be unique across your organization, and the value is unique to a group of resources. An example of a key-value pair is the key is `Environment`, with a value of `Production`. All resources in the production environment will have this key-value pair. Tagging allows you categorize and track your costs with meaningful, relevant organization information. You can apply tags that represent organization categories (such as cost centers, application names, projects, or owners), and identify workloads and characteristics of workloads (such as test or production) to attribute your costs and usage throughout your organization.

When you apply tags to your AWS resources (such as Amazon Elastic Compute Cloud instances or Amazon Simple Storage Service buckets) and activate the tags, AWS adds this information to your Cost and Usage Reports. You can run reports and perform analysis on tagged and untagged resources to allow greater compliance with internal cost management policies and ensure accurate attribution.

Creating and implementing an AWS tagging standard across your organization’s accounts helps you manage and govern your AWS environments in a consistent and uniform manner. Use [Tag Policies](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_tag-policies.html) in AWS Organizations to define rules for how tags can be used on AWS resources in your accounts in AWS Organizations. Tag Policies allow you to easily adopt a standardized approach for tagging AWS resources

[AWS Tag Editor](https://docs.aws.amazon.com/ARG/latest/userguide/tag-editor.html) allows you to add, delete, and manage tags of multiple resources. With Tag Editor, you search for the resources that you want to tag, and then manage tags for the resources in your search results.

[AWS Cost Categories](https://aws.amazon.com/aws-cost-management/aws-cost-categories/) allows you to assign organization meaning to your costs, without requiring tags on resources. You can map your cost and usage information to unique internal organization structures. You define category rules to map and categorize costs using billing dimensions, such as accounts and tags. This provides another level of management capability in addition to tagging. You can also map specific accounts and tags to multiple projects.

## Implementation Steps
- **Define a tagging schema:** Gather all stakeholders from across your business to define a schema. This typically includes people in technical, financial, and management roles. Define a list of tags that all resources must have, as well as a list of tags that resources should have. Verify that the tag names and values are consistent across your organization.
- ** Tag resources: **Using your defined cost attribution categories, [place tags](https://docs.aws.amazon.com/general/latest/gr/aws_tagging.html) on all resources in your workloads according to the categories. Use tools such as the CLI, Tag Editor, or AWS Systems Manager to increase efficiency.
- **Implement AWS Cost Categories: **You can create [Cost Categories](https://aws.amazon.com/aws-cost-management/aws-cost-categories/) without implementing tagging. Cost categories use the existing cost and usage dimensions. Create category rules from your schema and implement them into cost categories.
- **Automate tagging:** To verify that you maintain high levels of tagging across all resources, automate tagging so that resources are automatically tagged when they are created. Use services such as [AWS CloudFormation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-resource-tags.html) to verify that resources are tagged when created. You can also create a custom solution to tag automatically using Lambda functions or use a microservice that scans the workload periodically and removes any resources that are not tagged, which is ideal for test and development environments.
- ** Monitor and report on tagging: **To verify that you maintain high levels of tagging across your organization, report and monitor the tags across your workloads. You can use [AWS Cost Explorer](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/) to view the cost of tagged and untagged resources, or use services such as [Tag Editor](https://docs.aws.amazon.com/tag-editor/latest/userguide/tagging.html). Regularly review the number of untagged resources and take action to add tags until you reach the desired level of tagging.

## Resources
### Related Documents
- [ Tagging Best Practices ](https://docs.aws.amazon.com/whitepapers/latest/tagging-best-practices/tagging-best-practices.html)
- [AWS CloudFormation Resource Tag](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-resource-tags.html)
- [AWS Cost Categories](https://aws.amazon.com/aws-cost-management/aws-cost-categories/)
- [Tagging AWS resources](https://docs.aws.amazon.com/general/latest/gr/aws_tagging.html)
- [Analyzing your costs with AWS Budgets](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/budgets-managing-costs.html)
- [Analyzing your costs with Cost Explorer](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/cost-explorer-what-is.html)
- [Managing AWS Cost and Usage Reports](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/billing-reports-costusage-managing.html)
### Related Videos
- [ How can I tag my AWS resources to divide up my bill by cost center or project ](https://www.youtube.com/watch?v=3j9xyyKIg6w)
- [ Tagging AWS Resources ](https://www.youtube.com/watch?v=MX9DaAQS15I)
