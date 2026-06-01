---
id: "GENREL05-BP01"
title: "Load-balance inference requests across all regions of availability"
pillar: "Reliability"
risk_level: "HIGH"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/genrel05-bp01.html"
---

# GENREL05-BP01 Load-balance inference requests across all regions of availability

Inference to a foundation model may be available over a local or
large area of availability. Verify that you have resources
available across that area to service inference requests
reliably regardless of where they are coming from.

**Desired outcome:** When
implemented, this best practice improves the reliability of your
generative AI workload by creating a highly available
environment for serving inference requests.

**Benefits of establishing this best
practice:**
[Scale
horizontally to increase aggregate workload availability](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel-dp.html)
- Load-balanced inference requests across horizontally scaled
infrastructure enable inference requests to be serviced evenly
across a region of availability.

**Level of risk exposed if this best
practice is not established:** Medium

## Implementation guidance

Use load balancing and multi-Region deployment strategies to
distribute inference requests across multiple AWS Regions and
Availability Zones. This helps maintain consistent performance
and availability in the face of regional disruptions or
network issues. Consider using Amazon Bedrock's cross-Region
inference profiles to route requests to the nearest available
endpoint. For self-hosted models on Amazon SageMaker AI,
implement a multi-AZ deployment with an Amazon SageMaker AI
Inference Endpoint configured for auto-scaling to
automatically distribute and scale traffic across Regions.

This strategy provides improved reliability, reduced risk of
single points of failure, and better geographic coverage for
global users. Potential trade-offs include increased network
latency and operational complexity.

### Implementation steps

- Configure Amazon Bedrock cross-Region inference profiles
or deploy self-hosted models on Amazon SageMaker AI
Inference Endpoints across multiple Availability Zones.
- Set up an Amazon SageMaker AI Inference Endpoint with
auto-scaling enabled to distribute traffic based on
health and latency.
- Implement health checks and automated failover to
maintain availability.
- Monitor performance metrics like latency, error rates,
and throughput across Regions.

## Resources

**Related best practices:**

- REL04-BP01
- REL10-BP01

**Related documents:**

- [Supported Regions and models for inference profiles](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-support.html)

**Related examples:**

- [Getting Started with cross-Region inference in Amazon Bedrock](https://aws.amazon.com/blogs/machine-learning/getting-started-with-cross-region-inference-in-amazon-bedrock/)
