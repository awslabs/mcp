---
id: "REL02-BP03"
title: "Ensure IP subnet allocation accounts for expansion and availability"
pillar: "Reliability"
risk_level: "MEDIUM"
capability: "How do you plan your network topology?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_network_topology_ip_subnet_allocation.html"
---

# REL02-BP03 Ensure IP subnet allocation accounts for expansion and availability

Amazon VPC IP address ranges must be large enough to accommodate workload requirements,
including factoring in future expansion and allocation of IP addresses to subnets across
Availability Zones. This includes load balancers, EC2 instances, and container-based
applications.

When you plan your network topology, the first step is to define the IP address space
itself. Private IP address ranges (following RFC 1918 guidelines) should be allocated for each
VPC. Accommodate the following requirements as part of this process:

- Allow IP address space for more than one VPC per Region.
- Within a VPC, allow space for multiple subnets so that you can cover multiple
Availability Zones.
- Consider leaving unused CIDR block space within a VPC for future expansion.
- Ensure that there is IP address space to meet the needs of any transient fleets of Amazon EC2
instances that you might use, such as Spot Fleets for machine learning, Amazon EMR clusters,
or Amazon Redshift clusters. Similar consideration should be given to Kubernetes clusters, such as
Amazon Elastic Kubernetes Service (Amazon EKS), as each Kubernetes pod is assigned a routable address from the VPC CIDR
block by default.
- Note that the first four IP addresses and the last IP address in each subnet CIDR block
are reserved and not available for your use.
- Note that the initial VPC CIDR block allocated to your VPC cannot be changed or deleted,
but you can add additional non-overlapping CIDR blocks to the VPC. Subnet IPv4 CIDRs cannot
be changed, however IPv6 CIDRs can.
- The largest possible VPC CIDR block is a /16, and the smallest is a /28.
- Consider other connected networks (VPC, on-premises, or other cloud providers) and
ensure non-overlapping IP address space. For more information, see [REL02-BP05 Enforce non-overlapping private IP address ranges in all private address
spaces where they are connected.](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_network_topology_non_overlap_ip.html)

**Desired outcome:** A scalable IP subnet can help you accomodate
for future growth and avoid unnecessary waste.

**Common anti-patterns:**

- Failing to consider future growth, resulting in CIDR blocks that are too small and
requiring reconfiguration, potentially causing downtime.
- Incorrectly estimating how many IP addresses an elastic load balancer can use.
- Deploying many high traffic load balancers into the same subnets
- Using automated scaling mechanisms whilst failing to monitor IP address
consumption.
- Defining excessively large CIDR ranges well beyond future growth expectations, which can
lead to difficulty peering with other networks with overlapping address ranges.

**Benefits of establishing this best practice:** This ensures that
you can accommodate the growth of your workloads and continue to provide availability as you
scale up.

**Level of risk exposed if this best practice is not established:**
Medium

## Implementation guidance

Plan your network to accommodate for growth, regulatory compliance, and integration with
others. Growth can be underestimated, regulatory compliance can change, and acquisitions or
private network connections can be difficult to implement without proper planning.

- Select relevant AWS accounts and Regions based on your service requirements,
latency, regulatory, and disaster recovery (DR) requirements.
- Identify your needs for regional VPC deployments.
- Identify the size of the VPCs.

Determine if you are going to deploy multi-VPC connectivity.

[What
Is a Transit Gateway?](https://docs.aws.amazon.com/vpc/latest/tgw/what-is-transit-gateway.html)
- [Single Region
Multi-VPC Connectivity](https://aws.amazon.com/answers/networking/aws-single-region-multi-vpc-connectivity/)

- Determine if you need segregated networking for regulatory requirements.
- Make VPCs with appropriately-sized CIDR blocks to accommodate your current and
future needs.

If you have unknown growth projections, you may wish to err on the side of
larger CIDR blocks to reduce the potential for future reconfiguration

- Consider using [IPv6 addressing](https://aws.amazon.com/vpc/ipv6/) for
subnets as part of a dual-stack VPC. IPv6 is well suited to being used in private
subnets containing fleets of ephemeral instances or containers that would otherwise
require large numbers of IPv4 addresses.

## Resources

**Related Well-Architected best practices:**

- [REL02-BP05 Enforce non-overlapping private IP address ranges in all private address
spaces where they are connected](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_network_topology_non_overlap_ip.html)

**Related documents:**

- [APN Partner: partners
that can help plan your networking](https://aws.amazon.com/partners/find/results/?keyword=network)
- [AWS Marketplace for Network
Infrastructure](https://aws.amazon.com/marketplace/b/2649366011)
- [Amazon Virtual Private Cloud
Connectivity Options Whitepaper](https://docs.aws.amazon.com/whitepapers/latest/aws-vpc-connectivity-options/introduction.html)
- [Multiple data
center HA network connectivity](https://aws.amazon.com/answers/networking/aws-multiple-data-center-ha-network-connectivity/)
- [Single Region Multi-VPC Connectivity](https://aws.amazon.com/answers/networking/aws-single-region-multi-vpc-connectivity/)
- [What Is
Amazon VPC?](https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html)
- [IPv6 on AWS](https://aws.amazon.com/vpc/ipv6)
- [IPv6 on reference architectures](https://d1.awsstatic.com/architecture-diagrams/ArchitectureDiagrams/IPv6-reference-architectures-for-AWS-and-hybrid-networks-ra.pdf)
- [Amazon Elastic Kubernetes Service
launches IPv6 support](https://aws.amazon.com/blogs/containers/amazon-eks-launches-ipv6-support/)
- [Recommendations for your VPC - Classic Load Balancers](https://docs.aws.amazon.com/elasticloadbalancing/latest/classic/elb-backend-instances.html#set-up-ec2)
- [Availability Zone subnets - Application Load Balancers](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/application-load-balancers.html#availability-zones)
- [Availability Zones - Network Load Balancers](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/network-load-balancers.html#availability-zones)

**Related videos:**

- [AWS re:Invent 2018: Advanced VPC Design and
New Capabilities for Amazon VPC (NET303)](https://youtu.be/fnxXNZdf6ew)
- [AWS re:Invent 2019: AWS Transit Gateway reference
architectures for many VPCs (NET406-R1)](https://youtu.be/9Nikqn_02Oc)
- [AWS re:Invent 2023: AWS Ready
for what's next? Designing networks for growth and flexibility (NET310)](https://www.youtube.com/watch?v=FkWOhTZSfdA)
