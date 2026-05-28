---
id: "REL01-BP04"
title: "Monitor and manage quotas"
framework: "WAF"
domain: "Reliability"
capability: "How do you manage Service Quotas and constraints?"
risk_level: "Medium"
---

# REL01-BP04 Monitor and manage quotas

## Desired Outcome
Active and automated systems that manage and monitor have been deployed. These operations solutions ensure that quota usage thresholds are nearing being reached. These would be proactively remediated by requested quota changes.

## Anti-Patterns
- Not configuring monitoring to check for service quota thresholds
- Not configuring monitoring for hard limits, even though those values cannot be changed.
- Assuming that amount of time required to request and secure a soft quota change is immediate or a short period.
- Configuring alarms for when service quotas are being approached, but having no process on how to respond to an alert.
- Only configuring alarms for services supported by AWS Service Quotas and not monitoring other AWS services.
- Not considering quota management for multiple Region resiliency designs, like active/active, active/passive – hot, active/passive - cold, and active/passive - pilot light approaches.
- Not assessing quota differences between Regions.
- Not assessing the needs in every Region for a specific quota increase request.
- Not leveraging [templates for multi-Region quota management](https://docs.aws.amazon.com/servicequotas/latest/userguide/organization-templates.html).

## Implementation Guidance
 For supported services, you can monitor your quotas by configuring various different services that can assess and then send alerts or alarms. This can aid in monitoring usage and can alert you to approaching quotas. These alarms can be invoked from AWS Config, Lambda functions, Amazon CloudWatch, or from AWS Trusted Advisor. You can also use metric filters on CloudWatch Logs to search and extract patterns in logs to determine if usage is approaching quota thresholds.

## Implementation Steps
 For monitoring:
- Capture current resource consumption (for example, buckets or instances). Use service API operations, such as the Amazon EC2 `DescribeInstances` API, to collect current resource consumption.
- Capture your current quotas that are essential and applicable to the services using:
  - AWS Service Quotas
  - AWS Trusted Advisor
  - AWS documentation
  - AWS service-specific pages
  - AWS Command Line Interface (AWS CLI)
  - AWS Cloud Development Kit (AWS CDK)
- Use AWS Service Quotas, an AWS service that helps you manage your quotas for over 250 AWS services from one location.
- Use Trusted Advisor service limits to monitor your current service limits at various thresholds.
- Use the service quota history (console or AWS CLI) to check on regional increases.
- Compare service quota changes in each Region and each account to create equivalency, if required.

 For management:
- Automated: Set up an AWS Config custom rule to scan service quotas across Regions and compare for differences.
- Automated: Set up a scheduled Lambda function to scan service quotas across Regions and compare for differences.
- Manual: Scan services quota through AWS CLI, API, or AWS Console to scan service quotas across Regions and compare for differences. Report the differences.
- If differences in quotas are identified between Regions, request a quota change, if required.
- Review the result of all requests.

## Resources
### Related Best Practices
- [REL01-BP01 Aware of service quotas and constraints](rel_manage_service_limits_aware_quotas_and_constraints.md)
- [REL01-BP02 Manage service quotas across accounts and regions](rel_manage_service_limits_limits_considered.md)
- [REL01-BP03 Accommodate fixed service quotas and constraints through architecture](rel_manage_service_limits_aware_fixed_limits.md)
- [REL01-BP05 Automate quota management](rel_manage_service_limits_automated_monitor_limits.md)
- [REL01-BP06 Ensure that a sufficient gap exists between the current quotas and the maximum usage to accommodate failover](rel_manage_service_limits_suff_buffer_limits.md)
- [REL03-BP01 Choose how to segment your workload](rel_service_architecture_monolith_soa_microservice.md)
- [REL10-BP01 Deploy the workload to multiple locations](rel_fault_isolation_multiaz_region_system.md)
- [REL11-BP01 Monitor all components of the workload to detect failures](rel_withstand_component_failures_monitoring_health.md)
- [REL11-BP03 Automate healing on all layers](rel_withstand_component_failures_auto_healing_system.md)
- [REL12-BP04 Test resiliency using chaos engineering](rel_testing_resiliency_failure_injection_resiliency.md)
### Related Documents
- [AWS Well-Architected Framework’s Reliability Pillar: Availability ](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/availability.html)
- [AWS Service Quotas (formerly referred to as service limits)](https://docs.aws.amazon.com/general/latest/gr/aws_service_limits.html)
- [AWS Trusted Advisor Best Practice Checks (see the Service Limits section)](https://aws.amazon.com/premiumsupport/technology/trusted-advisor/best-practice-checklist/)
- [AWS limit monitor on AWS answers](https://aws.amazon.com/answers/account-management/limit-monitor/)
- [Amazon EC2 Service Limits](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-resource-limits.html)
- [What is Service Quotas?](https://docs.aws.amazon.com/servicequotas/latest/userguide/intro.html)
- [ How to Request Quota Increase ](https://docs.aws.amazon.com/servicequotas/latest/userguide/request-quota-increase.html)
- [ Service endpoints and quotas ](https://docs.aws.amazon.com/general/latest/gr/aws-service-information.html)
- [Service Quotas User Guide](https://docs.aws.amazon.com/servicequotas/latest/userguide/intro.html)
- [ Quota Monitor for AWS](https://aws.amazon.com/solutions/implementations/quota-monitor/)
- [AWS Fault Isolation Boundaries ](https://docs.aws.amazon.com/whitepapers/latest/aws-fault-isolation-boundaries/abstract-and-introduction.html)
- [ Availability with redundancy ](https://docs.aws.amazon.com/whitepapers/latest/availability-and-beyond-improving-resilience/availability-with-redundancy.html)
- [AWS for Data ](https://aws.amazon.com/data/)
- [ What is Continuous Integration? ](https://aws.amazon.com/devops/continuous-integration/)
- [ What is Continuous Delivery? ](https://aws.amazon.com/devops/continuous-delivery/)
- [ APN Partner: partners that can help with configuration management ](https://partners.amazonaws.com/search/partners?keyword=Configuration+Management&ref=wellarchitected)
- [ Managing the account lifecycle in account-per-tenant SaaS environments on AWS](https://aws.amazon.com/blogs/mt/managing-the-account-lifecycle-in-account-per-tenant-saas-environments-on-aws/)
- [ Managing and monitoring API throttling in your workloads ](https://aws.amazon.com/blogs/mt/managing-monitoring-api-throttling-in-workloads/)
- [ View AWS Trusted Advisor recommendations at scale with AWS Organizations](https://aws.amazon.com/blogs/mt/organizational-view-for-trusted-advisor/)
- [ Automating Service Limit Increases and Enterprise Support with AWS Control Tower](https://aws.amazon.com/blogs/mt/automating-service-limit-increases-enterprise-support-aws-control-tower/)
- [ Actions, resources, and condition keys for Service Quotas ](https://docs.aws.amazon.com/service-authorization/latest/reference/list_servicequotas.html)
### Related Videos
- [AWS Live re:Inforce 2019 - Service Quotas](https://youtu.be/O9R5dWgtrVo)
- [ View and Manage Quotas for AWS Services Using Service Quotas ](https://www.youtube.com/watch?v=ZTwfIIf35Wc)
- [AWS IAM Quotas Demo ](https://www.youtube.com/watch?v=srJ4jr6M9YQ)
- [AWS re:Invent 2018: Close Loops and Opening Minds: How to Take Control of Systems, Big and Small ](https://www.youtube.com/watch?v=O8xLxNje30M)
### Related Tools
- [AWS CodeDeploy](https://aws.amazon.com/codedeploy/)
- [AWS CloudTrail](https://aws.amazon.com/cloudtrail/)
- [ Amazon CloudWatch ](https://aws.amazon.com/cloudwatch/)
- [ Amazon EventBridge ](https://aws.amazon.com/eventbridge/)
- [ Amazon DevOps Guru ](https://aws.amazon.com/devops-guru/)
- [AWS Config](https://aws.amazon.com/config/)
- [AWS Trusted Advisor](https://aws.amazon.com/premiumsupport/technology/trusted-advisor/)
- [AWS CDK ](https://aws.amazon.com/cdk/)
- [AWS Systems Manager](https://aws.amazon.com/systems-manager/)
- [AWS Marketplace](https://aws.amazon.com/marketplace/search/results?searchTerms=CMDB)
