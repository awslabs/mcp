---
id: "PERF04-BP02"
title: "Evaluate available networking features"
pillar: "Performance Efficiency"
risk_level: "HIGH"
capability: "How do you select and configure networking resources in your workload?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/performance-efficiency-pillar/perf_networking_evaluate_networking_features.html"
description: "Evaluate networking features in the cloud that may increase performance. Measure the impact of these features through testing, metrics, and analysis. For example, take advantage of network-level features that are available to reduce latency, network distance, or jitter."
area: ["Networking and content delivery"]
---

# PERF04-BP02 Evaluate available networking features

Evaluate networking features in the cloud that may increase performance. Measure the impact of these features through testing, metrics, and analysis. For example, take advantage of network-level features that are available to reduce latency, network distance, or jitter.

**Common anti-patterns:**

- You stay within one Region because that is where your headquarters is physically located.
- You use firewalls instead of security groups for filtering traffic.
- You break TLS for traffic inspection rather than relying on security groups, endpoint policies, and other cloud-native functionality.
- You only use subnet-based segmentation instead of security groups.

**Benefits of establishing this best
practice:** Evaluating all service features and options can increase your workload performance, reduce the cost of infrastructure, decrease the effort required to maintain your workload, and increase your overall security posture. You can use the global AWS backbone to provide the optimal networking experience for your customers.

**Level of risk exposed if this best practice
is not established:** High

## Implementation guidance

AWS offers services like [AWS Global Accelerator](https://aws.amazon.com/global-accelerator/) and [Amazon CloudFront](https://aws.amazon.com/cloudfront/) that can help improve network performance, while most AWS services have product features (such as the [Amazon S3 Transfer Acceleration](https://aws.amazon.com/s3/transfer-acceleration/) feature) to optimize network traffic.

Review which network-related configuration options are available to you and how they could impact your workload. Performance optimization depends on understanding how these options interact with your architecture and the impact that they will have on both measured performance and user experience.

### Implementation steps

- Create a list of workload components.

Consider using [AWS Cloud WAN](https://aws.amazon.com/cloud-wan/) to build, manage and monitor your organization's network when building a unified global network.
- Monitor your global and core networks with [Amazon CloudWatch Logs metrics](https://docs.aws.amazon.com/network-manager/latest/tgwnm/monitoring-cloudwatch-metrics.html). Leverage [Amazon CloudWatch RUM](https://aws.amazon.com/about-aws/whats-new/2021/11/amazon-cloudwatch-rum-applications-client-side-performance/), which provides insights to help to identify, understand, and enhance users’ digital experience.
- View aggregate network latency between AWS Regions and Availability Zones, as well as within each Availability Zone, using [AWS Network Manager](https://aws.amazon.com/transit-gateway/network-manager/) to gain insight into how your application performance relates to the performance of the underlying AWS network.
- Use an existing configuration management database (CMDB) tool or a service such as [AWS Config](https://aws.amazon.com/config/) to create an inventory of your workload and how it’s configured.

- If this is an existing workload, identify and document the benchmark for your performance metrics, focusing on the bottlenecks and areas to improve. Performance-related networking metrics will differ per workload based on business requirements and workload characteristics. As a start, these metrics might be important to review for your workload: bandwidth, latency, packet loss, jitter, and retransmits.
- If this is a new workload, perform [load tests](https://aws.amazon.com/solutions/implementations/distributed-load-testing-on-aws/) to identify performance bottlenecks.
- For the performance bottlenecks you identify, review the configuration options for your solutions to identify performance improvement opportunities. Check out the following key networking options and features:

Improvement opportunity
Solution

Network path or routes

Use [Network Access Analyzer](https://docs.aws.amazon.com/vpc/latest/network-access-analyzer/what-is-network-access-analyzer.html) to identify paths or routes.

Network protocols

See [PERF04-BP05 Choose network protocols to improve performance](./perf_networking_choose_network_protocols_improve_performance.html)

Network topology

Evaluate your operational and performance tradeoffs between [VPC Peering](https://docs.aws.amazon.com/vpc/latest/peering/what-is-vpc-peering.html) and [AWS Transit Gateway](https://aws.amazon.com/transit-gateway/) when connecting multiple accounts. AWS Transit Gateway simplifies how you interconnect all of your VPCs, which can span across thousands of AWS accounts and into on-premises networks. Share your AWS Transit Gateway between multiple accounts using [AWS Resource Access Manager](https://aws.amazon.com/ram/).

See [PERF04-BP03 Choose appropriate dedicated connectivity or VPN for your workload](./perf_networking_choose_appropriate_dedicated_connectivity_or_vpn.html)

Network services

[AWS Global Accelerator](https://aws.amazon.com/global-accelerator/) is a networking service that improves the performance of your users’ traffic by up to 60% using the AWS global network infrastructure.

[Amazon CloudFront](https://aws.amazon.com/cloudfront/) can improve the performance of your workload content delivery and latency globally.

Use [Lambda@edge](https://aws.amazon.com/lambda/edge/) to run functions that customize the content that CloudFront delivers closer to the users, reduce latency, and improve performance.

Amazon Route 53 offers [latency-based routing](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy-latency.html), [geolocation routing](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy-geo.html), [geoproximity routing](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy-geoproximity.html), and [IP-based routing](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy-ipbased.html) options to help you improve your workload’s performance for a global audience. Identify which routing option would optimize your workload performance by reviewing your workload traffic and user location when your workload is distributed globally.

Storage resource features

[Amazon S3 Transfer Acceleration](https://aws.amazon.com/s3/transfer-acceleration/) is a feature that lets external users benefit from the networking optimizations of CloudFront to upload data to Amazon S3. This improves the ability to transfer large amounts of data from remote locations that don’t have dedicated connectivity to the AWS Cloud.

[Amazon S3 Multi-Region Access Points](https://docs.aws.amazon.com/AmazonS3/latest/userguide/MultiRegionAccessPoints.html) replicates content to multiple Regions and simplifies the workload by providing one access point. When a Multi-Region Access Point is used, you can request or write data to Amazon S3 with the service identifying the lowest latency bucket.

Compute resource features

[Elastic Network Interfaces (ENI)](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-eni.html) used by Amazon EC2 instances, containers, and Lambda functions are limited on a per-flow basis. Review your placement groups to optimize your [EC2 networking throughput](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-network-bandwidth.html). To avoid a bottleneck on a per flow-basis, design your application to use multiple flows. To monitor and get visibility into your compute related networking metrics, use CloudWatch Metrics and [ethtool](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/monitoring-network-performance-ena.html). The ethtool command is included in the ENA driver and exposes additional network-related metrics that can be published as a [custom metric](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/publishingMetrics.html) to CloudWatch.

[Amazon Elastic Network Adapters (ENA)](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/enhanced-networking-ena.html) provide further optimization by delivering better throughput for your instances within a [cluster placement group](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/placement-groups.html#placement-groups-cluster%23placement-groups-limitations-cluster).

[Elastic Fabric Adapter (EFA)](https://aws.amazon.com/hpc/efa/) is a network interface for Amazon EC2 instances that allows you to run workloads requiring high levels of internode communications at scale on AWS.

[Amazon EBS-optimized instances](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-optimized.html) use an optimized configuration stack and provide additional, dedicated capacity to increase the Amazon EBS I/O.

## Resources

**Related documents:**

- [Application Load Balancer](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/introduction.html)
- [EC2 Enhanced Networking on Linux](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/enhanced-networking.html)
- [EC2 Enhanced Networking on Windows](https://docs.aws.amazon.com/AWSEC2/latest/WindowsGuide/enhanced-networking.html)
- [EC2 Placement Groups](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/placement-groups.html)
- [Enabling Enhanced Networking with the Elastic Network Adapter (ENA) on Linux Instances](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/enhanced-networking-ena.html)
- [Network Load Balancer](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/introduction.html)
- [Networking Products with AWS](https://aws.amazon.com/products/networking/)
- [Transitioning to Latency-Based Routing in Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/TutorialTransitionToLBR.html)
- [VPC Endpoints](https://docs.aws.amazon.com/vpc/latest/privatelink/concepts.html)
- [VPC Flow Logs](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html)

**Related videos:**

- [AWS re:Invent 2023 – Ready for what's next? Designing networks for growth and flexibility](https://www.youtube.com/watch?v=FkWOhTZSfdA)
- [AWS re:Invent 2023 – Advanced VPC designs and new capabilities](https://www.youtube.com/watch?v=cRdDCkbE4es)
- [AWS re:Invent 2023 – A developer's guide to cloud networking](https://www.youtube.com/watch?v=i77D556lrgY)
- [AWS re:Invent 2022 – Dive deep on AWS networking infrastructure](https://www.youtube.com/watch?v=HJNR_dX8g8c)
- [AWS re:Invent 2019 – Connectivity to AWS and hybrid AWS network architectures](https://www.youtube.com/watch?v=eqW6CPb58gs)
- [AWS re:Invent 2018 – Optimizing Network Performance for Amazon EC2 Instances](https://www.youtube.com/watch?v=DWiwuYtIgu0)
- [AWS Global Accelerator](https://www.youtube.com/watch?v=Docl4julOQw)

**Related examples:**

- [AWS Transit Gateway and Scalable Security Solutions](https://github.com/aws-samples/aws-transit-gateway-and-scalable-security-solutions)
- [AWS Networking Workshops](https://catalog.workshops.aws/networking/en-US)
- [Observing and diagnosing your network](https://catalog.us-east-1.prod.workshops.aws/workshops/cf2ecaa4-e4be-4f40-b93f-e9fe3b1c1f64/en-US)
- [Finding and addressing network misconfigurations on AWS](https://validating-network-reachability.awssecworkshops.com/)
