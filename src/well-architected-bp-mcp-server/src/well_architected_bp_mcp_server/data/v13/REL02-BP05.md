---
id: "REL02-BP05"
title: "Enforce non-overlapping private IP address ranges in all private address spaces where they are connected"
framework: "WAF"
domain: "Reliability"
capability: "How do you plan your network topology?"
risk_level: "Medium"
---

# REL02-BP05 Enforce non-overlapping private IP address ranges in all private address spaces where they are connected

## Desired Outcome
- No IP address range conflicts between VPCs, on-premises environments, or other cloud providers.
- Proper IP address management allows for easier scaling of network infrastructure to accommodate growth and changes in network requirements.

## Anti-Patterns
- Using the same IP range in your VPC as you have on premises, in your corporate network, or other cloud providers
- Not tracking IP ranges of VPCs used to deploy your workloads.
- Relying on manual IP address management processes, such as spreadsheets.
- Over- or under-sizing CIDR blocks, which results in IP address waste or insufficient address space for your workload.

## Implementation Guidance
 Make use of an IPAM, such as the [Amazon VPC IP Address Manager](https://docs.aws.amazon.com/vpc/latest/ipam/what-it-is-ipam.html), to monitor and manage your CIDR use. Several IPAMs are also available from the AWS Marketplace. Evaluate your potential usage on AWS, add CIDR ranges to existing VPCs, and create VPCs to allow planned growth in usage.

## Implementation Steps
- Capture current CIDR consumption (for example, VPCs and subnets).
  - Use service API operations to collect current CIDR consumption.
  - Use the [Amazon VPC IP Address Manager to discover resources](https://docs.aws.amazon.com/vpc/latest/ipam/res-disc-work-with-view.html).
- Capture your current subnet usage.
  - Use service API operations to [collect subnets](https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_DescribeSubnets.html) per VPC in each Region.
  - Use the [Amazon VPC IP Address Manager to discover resources](https://docs.aws.amazon.com/vpc/latest/ipam/res-disc-work-with-view.html).
- Record the current usage.
- Determine if you created any overlapping IP ranges.
- Calculate the spare capacity.
- Identify overlapping IP ranges. You can either migrate to a new range of addresses or consider using techniques like [private NAT Gateway](https://docs.aws.amazon.com/whitepapers/latest/building-scalable-secure-multi-vpc-network-infrastructure/private-nat-gateway.html) or [AWS PrivateLink](https://docs.aws.amazon.com/whitepapers/latest/building-scalable-secure-multi-vpc-network-infrastructure/aws-privatelink.html) if you need to connect the overlapping ranges.

## Resources
### Related Best Practices
- [ Protecting networks ](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/protecting-networks.html)
### Related Documents
- [APN Partner: partners that can help plan your networking](https://aws.amazon.com/partners/find/results/?keyword=network)
- [AWS Marketplace for Network Infrastructure](https://aws.amazon.com/marketplace/b/2649366011)
- [Amazon Virtual Private Cloud Connectivity Options Whitepaper](https://docs.aws.amazon.com/whitepapers/latest/aws-vpc-connectivity-options/introduction.html)
- [Multiple data center HA network connectivity](https://aws.amazon.com/answers/networking/aws-multiple-data-center-ha-network-connectivity/)
- [ Connecting Networks with Overlapping IP Ranges ](https://aws.amazon.com/blogs/networking-and-content-delivery/connecting-networks-with-overlapping-ip-ranges/)
- [What Is Amazon VPC?](https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html)
- [What is IPAM?](https://docs.aws.amazon.com/vpc/latest/ipam/what-it-is-ipam.html)
### Related Videos
- [AWS re:Invent 2023 - Advanced VPC designs and new capabilities ](https://www.youtube.com/watch?v=cRdDCkbE4es)
- [AWS re:Invent 2019: AWS Transit Gateway reference architectures for many VPCs](https://youtu.be/9Nikqn_02Oc)
- [AWS re:Invent 2023 - Ready for what’s next? Designing networks for growth and flexibility ](https://www.youtube.com/watch?v=FkWOhTZSfdA)
- [AWS re:Invent 2021 - \$1New Launch\$1 Manage your IP addresses at scale on AWS](https://www.youtube.com/watch?v=xtLJgJfhPLg)
