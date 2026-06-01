---
id: "GENREL05-BP02"
title: "Replicate embedding data across all regions of availability"
pillar: "Reliability"
risk_level: "HIGH"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/genrel05-bp02.html"
---

# GENREL05-BP02 Replicate embedding data across all regions of availability

Inference to a foundation model may be available over a local availability region, or could
be a large region of availability. Make sure your data is available across all regions of
availability to adequately service inference requests.

**Desired outcome:** When implemented, this best practice improves
the reliability of your generative AI workload by validating that models have access to the
appropriate data to service inference requests across an entire Region of availability.

**Benefits of establishing this best
practice:**
[Scale
horizontally to increase aggregate workload availability](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel-dp.html) -
Data replication across a region of availability enables horizontal
scaling of the data access infrastructure and supports consistent
serving of inference requests.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

Replicate the data required for generative AI workloads, such
as embeddings and knowledge bases, and make that data readily
available across all designated Regions. This helps prevent
data access from becoming a bottleneck and maintains
consistent performance for users regardless of their location.
Use solutions like Amazon S3 cross-Region replication, Amazon OpenSearch Service cross-cluster replication, and AWS Glue
data pipelines to distribute data efficiently.

Consider data sovereignty requirements and regulatory
restrictions that may limit your ability to freely replicate
data, including embeddings, across all Regions. Carefully
review the data residency and compliance needs for your
specific use case and workload. Implement data distribution
strategies that respect these constraints, such as keeping
embeddings within a defined geographic area or using
Region-specific data stores.

Replicating data across Regions can incur additional storage
and data transfer costs. Optimize data partitioning and
compression to minimize the overall storage footprint. Use
Amazon S3 Intelligent Tiering to automatically move less
frequently accessed data to more cost-effective storage
classes. Replicating data provides improved data availability
and reduced latency for users. If done properly, this practice
helps you maintain compliance with data sovereignty
regulations. Trade-offs may include increased costs and
potential consistency challenges within the allowed Regions.

### Implementation steps

- Assess data sovereignty requirements and regulatory
constraints for your generative AI workload, including
the distribution of embeddings.
- Identify the Regions where you can freely replicate
embeddings and other data based on your compliance
needs.
- Set up cross-Region replication for embedding data
stores like Amazon S3 and Amazon OpenSearch Service
within the allowed Regions.
- Implement data ingestion pipelines using AWS Glue to
keep the allowed Regions synchronized for embeddings and
other data.
- Configure monitoring and alerting to detect data
replication issues and compliance violations.
- Optimize data partitioning, compression, and storage
tiering to minimize the cost of cross-Region data
replication.

## Resources

**Related best practices:**

- [REL04-BP01](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_prevent_interaction_failure_identify.html)
- [REL07-BP01](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_adapt_to_changes_autoscale_adapt.html)
- [REL10-BP01](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_fault_isolation_multiaz_region_system.html)

**Related documents:**

- [Supported
Regions and Models for inference profiles](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-support.html)

**Related examples:**

- [Ensure
availability of your data using cross-cluster replication with
Amazon OpenSearch Service](https://aws.amazon.com/blogs/big-data/ensure-availability-of-your-data-using-cross-cluster-replication-with-amazon-opensearch-service/)
