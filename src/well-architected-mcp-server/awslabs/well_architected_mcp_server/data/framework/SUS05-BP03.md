---
id: "SUS05-BP03"
title: "Use managed services"
pillar: "Sustainability"
risk_level: "MEDIUM"
capability: "How do you select and use cloud hardware and services in your architecture to support your sustainability goals?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/sustainability-pillar/sus_sus_hardware_a4.html"
---

# SUS05-BP03 Use managed services

Use managed services to operate more efficiently in the cloud.

**Common anti-patterns:**

- You use Amazon EC2 instances with low utilization to run your applications.
- Your in-house team only manages the workload, without time to focus on innovation or
simplifications.
- You deploy and maintain technologies for tasks that can run more efficiently on managed
services.

**Benefits of establishing this best practice:**

- Using managed services shifts the responsibility to AWS, which has insights across
millions of customers that can help drive new innovations and efficiencies.
- Managed service distributes the environmental impact of the service across many users
because of the multi-tenet control planes.

**Level of risk exposed if this best practice is not established:**
Medium

## Implementation guidance

Managed services shift responsibility to AWS for maintaining high utilization and
sustainability optimization of the deployed hardware. Managed services also remove the
operational and administrative burden of maintaining a service, which allows your team to have
more time and focus on innovation.

Review your workload to identify the components that can be replaced by AWS managed
services. For example, [Amazon RDS](https://aws.amazon.com/rds/), [Amazon Redshift](https://aws.amazon.com/redshift/), and [Amazon ElastiCache](https://aws.amazon.com/elasticache/) provide a managed database service. [Amazon Athena](https://aws.amazon.com/athena/), [Amazon EMR](https://aws.amazon.com/emr/), and [Amazon OpenSearch Service](https://aws.amazon.com/opensearch-service/)
provide a managed analytics service.

**Implementation steps**

- **Inventory your workload:** Inventory your workload for
services and components.
- **Identify candidates:** Assess and identify components
that can be replaced by managed services. Here are some examples of when you might
consider using a managed service:

Task
What to use on AWS

Hosting a database

Use managed [Amazon Relational Database Service (Amazon RDS)](https://aws.amazon.com/rds/)
instances instead of maintaining your own Amazon RDS instances on [Amazon Elastic Compute Cloud (Amazon EC2)](https://aws.amazon.com/ec2/).

Hosting a container workload

Use [AWS Fargate](https://aws.amazon.com/fargate/), instead of
implementing your own container infrastructure.

Hosting web apps

Use [AWS Amplify
Hosting](https://aws.amazon.com/amplify/hosting/) as fully managed CI/CD and hosting service for static websites
and server-side rendered web apps.
- **Create a migration plan:** Identify dependencies and
create a migrations plan. Update runbooks and playbooks accordingly.

The [AWS Application Discovery Service](https://aws.amazon.com/application-discovery/)
automatically collects and presents detailed information about application
dependencies and utilization to help you make more informed decisions as you plan your
migration

- **Perform tests** Test the service before migrating to
the managed service.
- **Replace self-hosted services:** Use your migration plan
to replace self-hosted services with managed service.
- **Monitor and adjust:** Continually monitor the service
after the migration is complete to make adjustments as required and optimize the service.

## Resources

**Related documents:**

- [AWS Cloud Products](https://aws.amazon.com/products/)
- [AWS Total Cost of Ownership (TCO) Calculator](https://calculator.aws/#/)
- [Amazon DocumentDB](https://aws.amazon.com/documentdb/)
- [Amazon Elastic Kubernetes Service (EKS)](https://aws.amazon.com/eks/)
- [Amazon Managed Streaming for Apache Kafka (Amazon MSK)](https://aws.amazon.com/msk/)

**Related videos:**

- [AWS re:Invent 2021 - Cloud
operations at scale with AWS Managed Services](https://www.youtube.com/watch?v=OCK8GCImWZw)
- [AWS re:Invent 2023 - Best
practices for operating on AWS](https://www.youtube.com/watch?v=XBKq2JXWsS4)
