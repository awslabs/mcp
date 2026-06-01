---
id: "GENREL05-BP03"
title: "Verify that agent capabilities are available across all regions of availability"
pillar: "Reliability"
risk_level: "MEDIUM"
lens: "GENERATIVE_AI"
url: "https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/genrel05-bp03.html"
---

# GENREL05-BP03 Verify that agent capabilities are available across all regions of availability

Agents require supporting infrastructure to service requests from
foundation models. Using agents across a region of availability
requires the supporting infrastructure to be available in that
region.

**Desired outcome:** When
implemented, this best practice improves the reliability of your
generative AI workload by verifying that agents have access to the
appropriate supporting infrastructure such as APIs or functions, so
they may service a wider region of availability.

**Benefits of establishing this best
practice:**
[Scale
horizontally to increase aggregate workload availability](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel-dp.html) -
Data replication across a region of availability horizontally scales
data access infrastructure, enabling foundation models to
consistently service inference requests across a region of
availability.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

Agents for Amazon Bedrock can be made available across
regions, so long as the models and supporting infrastructure
exist in the desired regions. Amazon Bedrock Agents make API
calls on behalf of a user. Once deployed to a new region,
these agents must have access to the same or
regionally-equivalent API. Consider deploying your APIs across
multiple regions behind a CloudFront distribution with
latency-based routing. When possible, leverage Amazon Route 53
with latency-based routing to direct traffic within your VPC
(and on the Amazon backbone) rather than taking private
traffic public to route to an internal service. If your agent
is not making calls to a foundation model using a cross-region
inference profile, be sure to configure model access in all
required regions.

When using agents in your generative AI architecture, make the
supporting infrastructure, such as APIs and functions,
available across all Regions where your agents are deployed.
This involves replicating the necessary components and
configuring appropriate routing mechanisms to maintain
consistent agent functionality regardless of user location.

### Implementation steps

- Deploy supporting agent infrastructure (APIs, functions)
in primary and secondary Regions.
- Implement latency-based routing or similar mechanisms to
distribute agent requests.
- Verify that agents can access the required resources in
all Regions.
- Monitor agent performance and resource utilization
across Regions.

## Resources

**Related best practices:**

- [REL04-BP01](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_prevent_interaction_failure_identify.html)
- [REL07-BP01](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_adapt_to_changes_autoscale_adapt.html)
- [REL10-BP01](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_fault_isolation_multiaz_region_system.html)

**Related documents:**

- [Latency-based
routing](https://docs.aws.amazon.com/Route%C2%A053/latest/DeveloperGuide/routing-policy-latency.html)

**Related examples:**

- [Using
latency-based routing with Amazon CloudFront for a
multi-Region active-active architecture](https://aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy-latency.html/)
