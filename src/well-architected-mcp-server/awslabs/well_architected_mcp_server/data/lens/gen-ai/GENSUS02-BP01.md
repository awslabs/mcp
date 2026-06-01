---
id: "GENSUS02-BP01"
title: "Optimize data processing and storage to minimize energy consumption"
pillar: "Sustainability"
risk_level: "MEDIUM"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/gensus02-bp01.html"
---

# GENSUS02-BP01 Optimize data processing and storage to minimize energy consumption

Organizations should optimize data processing and storage, which
aims to enhance the sustainability and cost-effectiveness of their
data processing and storage systems, particularly for generative AI
workloads. Optimizing the use of computational resources helps you
minimize energy consumption and operational costs while maintaining
high performance and scalability.

**Desired outcome:** After
implementing this practice, you can achieve more efficient data
management, reduce carbon footprint, and allocate resources more
effectively, which leads to cost and resource efficiency. This
approach not only supports sustainable practices but also help
organizations scale their generative AI initiatives without
incurring unnecessary expenses or resource wastage.

**Benefits of establishing this best
practice:**
[Optimize
resource utilization](https://docs.aws.amazon.com/wellarchitected/latest/sustainability-pillar/sustainability-pillar.html) - Increase sustainability of data
processing and storage.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

To enhance sustainability and efficiency in data processing and
storage, minimize runtime and optimize resource utilization. Use
serverless architectures, which offer a fully-managed approach to
scaling resources dynamically based on demand. Serverless services
can reduce the need for maintaining persistent infrastructure,
lowering both operational overhead and energy consumption.

Amazon S3 is a highly scalable and energy-efficient storage
solution that integrates seamlessly with generative AI services.
With intelligent tiering, data can be automatically moved to the
most cost-effective storage class based on access patterns,
verifying that frequently-accessed data remains readily available
while less active data is stored more cost-effectively. S3
Lifecycle policies further enhance this by enabling the transition
of data between storage classes or the deletion of data when it is
no longer needed, which optimizes underlying resource usage.

For analytical workloads, using columnar formats like Apache
Parquet can reduce data transfer and processing requirements.
Compression techniques should be applied where appropriate to
further minimize storage and transfer costs. Amazon Athena
provides a serverless query service that allows for the analysis
of data directly in Amazon S3 without the need for persistent
infrastructure, enhancing both flexibility and efficiency.

AWS Glue offers serverless ETL capabilities, automatic schema
discovery, and cataloging, which helps you verify that data
integration services run only when needed. This reduces idle
resource consumption and aligns resource usage with actual demand.

AWS Lambda enables serverless computing that automatically scales
and operates only when initiated, further reducing unnecessary
resource consumption. While serverless approaches like AWS Lambda
are beneficial for many use cases, it is important to be cautious
when applying them to data processing tasks that require
long-running batch processing. In such scenarios, services like
Amazon EMR with auto scaling may offer more efficient resource
utilization.

In Amazon SageMaker AI HyperPod with both Amazon EKS and Slurm
orchestration, establish differentiated service-level
objectives that balance training performance requirements with
resource efficiency and environmental impact considerations.

For EKS-based HyperPod, use Kubernetes resource quotas and
priority classes to define different service tiers for various
training workloads, implementing horizontal pod autoscaling
policies that align with actual performance needs rather than
peak theoretical capacity. Configure task governance
capabilities to automatically prioritize critical training
jobs while verifying that lower-priority experimentation
workloads use sustainable resource allocation patterns.

For Slurm-based HyperPod, use Slurm's fair share scheduling
and quality of service (QoS) features to establish training
job SLAs that correspond to business criticality, implementing
job preemption policies that allow high-priority workloads to
temporarily utilize resources from less critical tasks.

Both systems benefit from establishing differentiated training
SLAs where production model training receives consistent
resources and fast completion times, while development and
experimentation workloads operate with longer acceptable
completion windows, enabling better resource sharing and
utilization.

Additionally, implement flexible training plans that
automatically find cost-efficient combinations of compute
capacity blocks, auto-resume functionality to handle
acceptable interruptions for non-critical workloads, and usage
reporting to continuously monitor and optimize the
relationship between SLA commitments and actual sustainability
impact.

In summary, adopting serverless data storage and processing
services, combined with intelligent data management practices such
as tiering, lifecycle policies, and efficient data formats, can
significantly enhance sustainability and operational efficiency in
data handling.

### Implementation steps

- Use Amazon S3 for data storage.

Enable S3 Intelligent-Tiering to automatically optimize
storage costs based on access patterns
- Implement S3 Lifecycle policies to manage data
transitions and deletions efficiently
- Automate processes to remove redundant data
- Use S3 Storage Lens for data usage insights and
optimization

- Optimize data formats and compression.

Adopt columnar formats and convert data to formats like
Parquet for enhanced analytical performance
- Apply compression techniques to reduce storage and
transfer costs using appropriate compression methods

- Use serverless query and processing services.

Use Athena to perform serverless SQL queries on S3 data
- Use AWS Glue to run serverless ETL jobs, discover
schemas, and catalog data
- AWS Lambda to handle event-driven computing tasks

- Automatically scale batch processing.

Consider Amazon EMR with autoscaling to process
large-scale Spark jobs efficiently
- Assess resource efficiency between Lambda, EMR, and AWS Batch
- Use Lambda for short (under 15 minutes) processing jobs
- Consider EMR or Batch for larger scale jobs

- Monitor your resource utilization.

Use AWS Cost Explorer and AWS Trusted Advisor for cost
and resource optimization recommendations
- Review Amazon CloudWatch metrics to identify efficiency
improvements

## Resources

**Related best practices:**

- SUS04-BP04
- SUS04-BP03
- SUS04-BP02

**Related documents:**

- [AWS Well Architected Framework Data Analytics Lens](https://docs.aws.amazon.com/wellarchitected/latest/analytics-lens/analytics-lens.html)
- [Revolutionizing Real-World Evidence: How Generative AI Can Simplify Data
Exploration](https://aws.amazon.com/blogs/industries/revolutionizing-real-world-evidence-how-generative-ai-can-simplify-data-exploration/)
- [Amazon S3 Storage Classes](https://aws.amazon.com/s3/storage-classes/)
- [Examples of S3
Lifecycle configurations](https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-configuration-examples.html)
- [Zero-ETL
integrations](https://docs.aws.amazon.com/glue/latest/dg/zero-etl-using.html)
- [AWS Lambda Machine Learning Blogs and Sample Applications](https://aws.amazon.com/blogs/machine-learning/category/compute/aws-lambda/)

**Related examples:**

- [Optimizing
streaming media workflows to reduce your carbon
footprint](https://aws.amazon.com/blogs/media/optimizing-streaming-media-workflows-to-reduce-your-carbon-footprint-part-i/)
- [Amazon Athena User Guide](https://docs.aws.amazon.com/athena/latest/ug/what-is.html)
- [Advanced Scaling for Amazon EMR](https://docs.aws.amazon.com/emr/latest/ManagementGuide/managed-scaling-allocation-strategy-optimized.html)

**Related tools:**

- [AWS Cost Explorer](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/)
- [AWS Trusted Advisor](https://aws.amazon.com/premiumsupport/technology/trusted-advisor/)
- [Amazon CloudWatch](https://aws.amazon.com/cloudwatch/)
- [AWS CloudTrail](https://aws.amazon.com/cloudtrail/)
- [Amazon S3 Storage Lens](https://aws.amazon.com/s3/storage-lens/)
- [AWS Glue](https://aws.amazon.com/glue/)
- [Data discovery
and cataloging in AWS Glue](https://docs.aws.amazon.com/glue/latest/dg/catalog-and-crawler.html)
