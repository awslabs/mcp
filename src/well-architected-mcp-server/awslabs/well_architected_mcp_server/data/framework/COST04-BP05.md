---
id: "COST04-BP05"
title: "Enforce data retention policies"
pillar: "Cost Optimization"
risk_level: "MEDIUM"
capability: "How do you decommission resources?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/cost_decomissioning_resources_data_retention.html"
description: "Define data retention policies on supported resources to handle object deletion per your organizations’ requirements. Identify and delete unnecessary or orphaned resources and objects that are no longer required."
area: ["Expenditure and usage awareness", "Decommission resources"]
---

# COST04-BP05 Enforce data retention policies

Define data retention policies on supported resources to handle object deletion
per your organizations’ requirements. Identify and delete unnecessary or orphaned
resources and objects that are no longer required.

**Level of risk exposed if this best practice
is not established:** Medium

Use data retention policies and lifecycle policies to reduce the associated costs of the
decommissioning process and storage costs for the identified resources. Defining your data
retention policies and lifecycle policies to perform automated storage class migration and
deletion will reduce the overall storage costs during its lifetime. You can use Amazon Data Lifecycle Manager
to automate the creation and deletion of Amazon Elastic Block Store snapshots and Amazon EBS-backed Amazon Machine Images (AMIs), and use
Amazon S3 Intelligent-Tiering or an Amazon S3 lifecycle configuration to manage the lifecycle of your Amazon S3 objects.
You can also implement custom code using the [API or SDK](https://aws.amazon.com/tools/) to
create lifecycle policies and policy rules for objects to be deleted automatically.

**Implementation steps**

- **Use Amazon Data Lifecycle Manager:** Use lifecycle policies on Amazon Data Lifecycle Manager to automate deletion of Amazon EBS snapshots and Amazon EBS-backed AMIs.
- **Set up lifecycle configuration on a bucket:** Use Amazon S3 lifecycle configuration on a bucket to define actions for
Amazon S3 to take during an object's lifecycle, as well as deletion at the end of the object's lifecycle, based on your business requirements.

## Resources

**Related documents:**

- [AWS Trusted Advisor](https://aws.amazon.com/premiumsupport/trustedadvisor/)
- [Amazon Data Lifecycle Manager](https://docs.aws.amazon.com/dlm/?icmpid=docs_homepage_mgmtgov)
- [How to set lifecycle configuration on Amazon S3 bucket](https://docs.aws.amazon.com/AmazonS3/latest/userguide/how-to-set-lifecycle-configuration-intro.html)

**Related videos:**

- [Automate Amazon EBS Snapshots with Amazon Data Lifecycle Manager](https://www.youtube.com/watch?v=RJpEjnVSdi4)
- [Empty an Amazon S3 bucket using a lifecycle configuration rule](https://www.youtube.com/watch?v=JfK9vamen9I)

**Related examples:**

- [Empty an Amazon S3 bucket using a lifecycle configuration rule](https://aws.amazon.com/premiumsupport/knowledge-center/s3-empty-bucket-lifecycle-rule/)
