---
id: "PERF04-BP07"
title: "Optimize network configuration based on metrics"
pillar: "Performance Efficiency"
risk_level: "LOW"
capability: "How do you select and configure networking resources in your workload?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/performance-efficiency-pillar/perf_networking_optimize_network_configuration_based_on_metrics.html"
---

# PERF04-BP07 Optimize network configuration based on metrics

Use collected and analyzed data to make informed decisions about
optimizing your network configuration.

**Common anti-patterns:**

- You assume that all performance-related issues are
application-related.
- You only test your network performance from a location close to
where you have deployed the workload.
- You use default configurations for all network services.
- You overprovision the network resource to provide sufficient
capacity.

**Benefits of establishing this best
practice:** Collecting necessary metrics of your AWS
network and implementing network monitoring tools allows you to
understand network performance and optimize network configurations.

**Level of risk exposed if this best practice
is not established:** Low

## Implementation guidance

Monitoring traffic to and from VPCs, subnets, or network
interfaces is crucial to understand how to utilize AWS network
resources and optimize network configurations. By using the
following AWS networking tools, you can further inspect
information about the traffic usage, network access and logs.

### Implementation steps

- Identify the key performance metrics such as latency or packet
loss to collect. AWS provides several tools that can
help you to collect these metrics. By using the following
tools, you can further inspect information about the traffic
usage, network access, and logs:

AWS tool

Where to use

[Amazon VPC IP Address Manager](https://docs.aws.amazon.com/vpc/latest/ipam/what-it-is-ipam.html).

Use IPAM to plan, track, and monitor IP addresses for
your AWS and on-premises workloads. This is a best
practice to optimize IP address usage and allocation.

[VPC
Flow logs](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html)

Use VPC Flow Logs to capture detailed information about
traffic to and from network interfaces in your VPCs.
With VPC Flow Logs, you can diagnose overly restrictive
or permissive security group rules and determine the
direction of the traffic to and from the network
interfaces.

[AWS Transit Gateway Flow Logs](https://docs.aws.amazon.com/vpc/latest/tgw/tgw-flow-logs.html)

Use AWS Transit Gateway Flow Logs to capture information
about the IP traffic going to and from your transit
gateways.

[DNS
query logging](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/query-logs.html)

Log information about public or private DNS queries
Route 53 receives. With DNS logs, you can optimize DNS
configurations by understanding the domain or subdomain
that was requested or Route 53 EDGE locations that
responded to DNS queries.

[Reachability Analyzer](https://docs.aws.amazon.com/vpc/latest/reachability/what-is-reachability-analyzer.html)

Reachability Analyzer helps you analyze and debug
network reachability. Reachability Analyzer is a
configuration analysis tool that allows you to perform
connectivity testing between a source resource and a
destination resource in your VPCs. This tool helps you
verify that your network configuration matches your
intended connectivity.

[Network Access Analyzer](https://docs.aws.amazon.com/vpc/latest/network-access-analyzer/what-is-network-access-analyzer.html)

Network Access Analyzer helps you understand network
access to your resources. You can use Network Access Analyzer to specify your network access requirements and
identify potential network paths that do not meet your
specified requirements. By optimizing your corresponding
network configuration, you can understand and verify the
state of your network and demonstrate if your network on
AWS meets your compliance requirements.

[Amazon CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html)

Use [Amazon CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html) and turn on the appropriate metrics
for network options. Make sure to choose the right
network metric for your workload. For example, you can
turn on metrics for VPC Network Address Usage, VPC NAT
Gateway, AWS Transit Gateway, VPN tunnel, AWS Network Firewall, Elastic Load Balancing, and AWS Direct Connect. Continually monitoring metrics is a good
practice to observe and understand your network status
and usage, which helps you optimize network
configuration based on your observations.

[AWS Network Manager](https://aws.amazon.com/about-aws/whats-new/2022/11/network-manager-real-time-performance-monitoring-aws-global-network/)

Using AWS Network Manager, you can monitor the real-time
and historical performance of
the [AWS Global Network](https://aws.amazon.com/about-aws/global-infrastructure/global_network/) for operational and planning
purposes. Network Manager provides aggregate network
latency between AWS Regions and Availability Zones and
within each Availability Zone, allowing you to better
understand how your application performance relates to
the performance of the underlying AWS network.

[Amazon CloudWatch RUM](https://aws.amazon.com/blogs/aws/cloudwatch-rum/)

Use Amazon CloudWatch RUM to collect the metrics that
give you the insights that help you identify,
understand, and improve user experience.
- Identify top talkers and application traffic patterns using
VPC and AWS Transit Gateway Flow Logs.
- Assess and optimize your current network architecture
including VPCs, subnets, and routing. As an example, you can
evaluate how different VPC peering or AWS Transit Gateway
can help you improve the networking in your architecture.
- Assess the routing paths in your network to verify that the
shortest path between destinations is always used. Network Access Analyzer can help you do this.

## Resources

**Related documents:**

- [Public
DNS query logging](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/query-logs.html)
- [What
is IPAM?](https://docs.aws.amazon.com/vpc/latest/ipam/what-it-is-ipam.html)
- [What
is Reachability Analyzer?](https://docs.aws.amazon.com/vpc/latest/reachability/what-is-reachability-analyzer.html)
- [What
is Network Access Analyzer?](https://docs.aws.amazon.com/vpc/latest/network-access-analyzer/what-is-network-access-analyzer.html)
- [CloudWatch
metrics for your VPCs](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-cloudwatch.html)
- [Optimize
performance and reduce costs for network analytics with VPC
Flow Logs in Apache Parquet format](https://aws.amazon.com/blogs/big-data/optimize-performance-and-reduce-costs-for-network-analytics-with-vpc-flow-logs-in-apache-parquet-format/)
- [Monitoring
your global and core networks with Amazon CloudWatch
metrics](https://docs.aws.amazon.com/vpc/latest/tgwnm/monitoring-cloudwatch-metrics.html)
- [Continuously
monitor network traffic and resources](https://docs.aws.amazon.com/whitepapers/latest/security-best-practices-for-manufacturing-ot/continuously-monitor-network-traffic-and-resources.html)

**Related videos:**

- [AWS re:Invent 2023 – A developer's guide to cloud networking](https://www.youtube.com/watch?v=i77D556lrgY)
- [AWS re:Invent 2023 – Ready for what’s next? Designing networks for growth and flexibility](https://www.youtube.com/watch?v=FkWOhTZSfdA)
- [AWS re:Invent 2023 – Advanced VPC designs and new capabilities](https://www.youtube.com/watch?v=cRdDCkbE4es)
- [AWS re:Invent 2022 – Dive deep on AWS networking infrastructure](https://www.youtube.com/watch?v=HJNR_dX8g8c)
- [AWS re:Invent 2020 – Networking
best practices and tips with the AWS Well-Architected
Framework](https://www.youtube.com/watch?v=wOMNpG49BeM)
- [AWS re:Invent 2020 – Monitoring
and troubleshooting network traffic](https://www.youtube.com/watch?v=Ed09ReWRQXc)

**Related examples:**

- [AWS Networking Workshops](https://networking.workshop.aws/)
- [AWS Network Monitoring](https://github.com/aws-samples/monitor-vpc-network-patterns)
- [Observing and diagnosing your network on AWS](https://catalog.us-east-1.prod.workshops.aws/workshops/cf2ecaa4-e4be-4f40-b93f-e9fe3b1c1f64/en-US)
- [Finding and addressing network misconfigurations on AWS](https://validating-network-reachability.awssecworkshops.com/)
