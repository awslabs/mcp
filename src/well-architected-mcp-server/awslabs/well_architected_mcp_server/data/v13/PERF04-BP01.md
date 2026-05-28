---
id: "PERF04-BP01"
title: "Understand how networking impacts performance"
framework: "WAF"
domain: "Performance Efficiency"
capability: "How do you select and configure networking resources in your workload?"
risk_level: "High"
---

# PERF04-BP01 Understand how networking impacts performance

## Anti-Patterns
- All traffic flows through your existing data centers.
- You route all traffic through central firewalls instead of using cloud-native network security tools.
- You provision AWS Direct Connect connections without understanding actual usage requirements.
- You don’t consider workload characteristics and encryption overhead when defining your networking solutions.
- You use on-premises concepts and strategies for networking solutions in the cloud.

## Implementation Guidance
 The network is responsible for the connectivity between application components, cloud services, edge networks, and on-premises data, and therefore it can heavily impact workload performance. In addition to workload performance, user experience can be also impacted by network latency, bandwidth, protocols, location, network congestion, jitter, throughput, and routing rules.

 Have a documented list of networking requirements from the workload including latency, packet size, routing rules, protocols, and supporting traffic patterns. Review the available networking solutions and identify which service meets your workload networking characteristics. Cloud-based networks can be quickly rebuilt, so evolving your network architecture over time is necessary to improve performance efficiency.

## Implementation Steps
- Define and document networking performance requirements, including metrics such as network latency, bandwidth, protocols, locations, traffic patterns (spikes and frequency), throughput, encryption, inspection, and routing rules.
- Learn about key AWS networking services like [VPCs](https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html), [AWS Direct Connect](https://docs.aws.amazon.com/whitepapers/latest/aws-vpc-connectivity-options/aws-direct-connect.html), [Elastic Load Balancing (ELB)](https://aws.amazon.com/elasticloadbalancing/), and [Amazon Route 53](https://aws.amazon.com/route53/).
- Capture the following key networking characteristics:
[\[See the AWS documentation website for more details\]](http://docs.aws.amazon.com/wellarchitected/latest/framework/perf_networking_understand_how_networking_impacts_performance.html)
- Benchmark and test network performance:
  - [Benchmark](https://aws.amazon.com/premiumsupport/knowledge-center/network-throughput-benchmark-linux-ec2/) network throughput, as some factors can affect Amazon EC2 network performance when instances are in the same VPC. Measure the network bandwidth between Amazon EC2 Linux instances in the same VPC.
  - Perform [load tests](https://aws.amazon.com/solutions/implementations/distributed-load-testing-on-aws/) to experiment with networking solutions and options.

## Resources
### Related Documents
- [Application Load Balancer](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/introduction.html)
- [EC2 Enhanced Networking on Linux](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/enhanced-networking.html)
- [EC2 Enhanced Networking on Windows](https://docs.aws.amazon.com/AWSEC2/latest/WindowsGuide/enhanced-networking.html)
- [EC2 Placement Groups](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/placement-groups.html)
- [Enabling Enhanced Networking with the Elastic Network Adapter (ENA) on Linux Instances](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/enhanced-networking-ena.html)
- [Network Load Balancer](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/introduction.html)
- [Networking Products with AWS](https://aws.amazon.com/products/networking/)
- [Transit Gateway](https://docs.aws.amazon.com/vpc/latest/tgw)
- [Transitioning to latency-based routing in Amazon Route 53](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/TutorialTransitionToLBR.html)
- [VPC Endpoints](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-endpoints.html)
### Related Videos
- [AWS re:Invent 2023 - AWS networking foundations ](https://www.youtube.com/watch?v=8nNurTFy-h4)
- [AWS re:Invent 2023 - What can networking do for your application? ](https://www.youtube.com/watch?v=tUh26i8uY9Q)
- [AWS re:Invent 2023 - Advanced VPC designs and new capabilities ](https://www.youtube.com/watch?v=cRdDCkbE4es)
- [AWS re:Invent 2023 - A developer’s guide to cloud networking ](https://www.youtube.com/watch?v=i77D556lrgY)
- [AWS re:Invent 2019 - Connectivity to AWS and hybrid AWS network architectures](https://www.youtube.com/watch?v=eqW6CPb58gs)
- [AWS re:Invent 2019 - Optimizing Network Performance for Amazon EC2 Instances](https://www.youtube.com/watch?v=DWiwuYtIgu0)
- [AWS Summit Online - Improve Global Network Performance for Applications](https://youtu.be/vNIALfLTW9M)
- [AWS re:Invent 2020 - Networking best practices and tips with the Well-Architected Framework](https://youtu.be/wOMNpG49BeM)
- [AWS re:Invent 2020 - AWS networking best practices in large-scale migrations](https://youtu.be/qCQvwLBjcbs)
### Related Examples
- [AWS Transit Gateway and Scalable Security Solutions](https://github.com/aws-samples/aws-transit-gateway-and-scalable-security-solutions)
- [AWS Networking Workshops](https://networking.workshop.aws/)
- [ Hands-on Network Firewall Workshop ](https://catalog.us-east-1.prod.workshops.aws/workshops/d071f444-e854-4f3f-98c8-025fa0d1de2f/en-US)
- [ Observing and Diagnosing your Network on AWS](https://catalog.us-east-1.prod.workshops.aws/workshops/cf2ecaa4-e4be-4f40-b93f-e9fe3b1c1f64/en-US)
- [ Finding and addressing Network Misconfigurations on AWS](https://validating-network-reachability.awssecworkshops.com/)
