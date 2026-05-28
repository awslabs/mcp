---
id: "REL01-BP03"
title: "Accommodate fixed service quotas and constraints through architecture"
framework: "WAF"
domain: "Reliability"
capability: "How do you manage Service Quotas and constraints?"
risk_level: "Medium"
---

# REL01-BP03 Accommodate fixed service quotas and constraints through architecture

## Desired Outcome
The application or service performs as expected under normal and high traffic conditions. They have been designed to work within the limitations for that resource’s fixed constraints or service quotas.

## Anti-Patterns
- Choosing a design that uses a resource of a service, unaware that there are design constraints that will cause this design to fail as you scale.
- Performing benchmarking that is unrealistic and will reach service fixed quotas during the testing. For example, running tests at a burst limit but for an extended amount of time.
- Choosing a design that cannot scale or be modified if fixed service quotas are to be exceeded. For example, an SQS payload size of 256KB.
- Observability has not been designed and implemented to monitor and alert on thresholds for service quotas that might be at risk during high traffic events

## Implementation Guidance
 Unlike soft service quotas or resources that be replaced with higher capacity units, AWS services’ fixed quotas cannot be changed. This means that all these type of AWS services must be evaluated for potential hard capacity limits when used in an application design.

 Hard limits are shown in the Service Quotas console. If the columns shows `ADJUSTABLE = No`, the service has a hard limit. Hard limits are also shown in some resources configuration pages. For example, Lambda has specific hard limits that cannot be adjusted.

 As an example, when designing a python application to run in a Lambda function, the application should be evaluated to determine if there is any chance of Lambda running longer than 15 minutes. If the code may run more than this service quota limit, alternate technologies or designs must be considered. If this limit is reached after production deployment, the application will suffer degradation and disruption until it can be remediated. Unlike soft quotas, there is no method to change to these limits even under emergency Severity 1 events.

 Once the application has been deployed to a testing environment, strategies should be used to find if any hard limits can be reached. Stress testing, load testing, and chaos testing should be part of the introduction test plan.

## Implementation Steps
- Review the complete list of AWS services that could be used in the application design phase.
- Review the soft quota limits and hard quota limits for all these services. Not all limits are shown in the Service Quotas console. Some services [describe these limits in alternate locations](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html).
- As you design your application, review your workload’s business and technology drivers, such as business outcomes, use case, dependent systems, availability targets, and disaster recovery objects. Let your business and technology drivers guide the process to identify the distributed system that is right for your workload.
- Analyze service load across Regions and accounts. Many hard limits are regionally based for services. However, some limits are account based.
- Analyze resilience architectures for resource usage during a zonal failure and Regional failure. In the progression of multi-Region designs using active/active, active/passive – hot, active/passive - cold, and active/passive - pilot light approaches, these failure cases will cause higher usage. This creates a potential use case for hitting hard limits.

## Resources
### Related Best Practices
- [REL01-BP01 Aware of service quotas and constraints](rel_manage_service_limits_aware_quotas_and_constraints.md)
- [REL01-BP02 Manage service quotas across accounts and regions](rel_manage_service_limits_limits_considered.md)
- [REL01-BP04 Monitor and manage quotas](rel_manage_service_limits_monitor_manage_limits.md)
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
