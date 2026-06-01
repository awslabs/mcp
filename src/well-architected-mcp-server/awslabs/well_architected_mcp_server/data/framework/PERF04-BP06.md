---
id: "PERF04-BP06"
title: "Choose your workload's location based on network requirements"
pillar: "Performance Efficiency"
risk_level: "MEDIUM"
capability: "How do you select and configure networking resources in your workload?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/performance-efficiency-pillar/perf_networking_choose_workload_location_network_requirements.html"
description: "Evaluate options for resource placement to reduce network latency and improve throughput, providing an optimal user experience by reducing page load and data transfer times."
area: ["Networking and content delivery"]
relatedIds: ["COST07-BP02", "COST08-BP03", "REL10-BP01", "REL10-BP02", "SUS01-BP01", "SUS02-BP04", "SUS04-BP07"]
---

# PERF04-BP06 Choose your workload's location based on network requirements

Evaluate options for resource placement to reduce network latency and improve throughput, providing an optimal user experience by reducing page load and data transfer times.

**Common anti-patterns:**

- You consolidate all workload resources into one geographic location.
- You chose the closest Region to your location but not to the workload end user.

**Benefits of establishing this best
practice:** User experience is greatly affected by the latency between the user and your application. By using appropriate AWS Regions and the AWS private global network, you can reduce latency and deliver a better experience to remote users.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

Resources, such as Amazon EC2 instances, are placed into Availability Zones within [AWS Regions](https://aws.amazon.com/about-aws/global-infrastructure/regions_az/), [AWS Local Zones](https://aws.amazon.com/about-aws/global-infrastructure/localzones/), [AWS Outposts](https://aws.amazon.com/outposts/), or [AWS Wavelength](https://aws.amazon.com/wavelength/) zones. Selection of this location influences network latency and throughput from a given user location. Edge services like [Amazon CloudFront](https://aws.amazon.com/cloudfront/) and [AWS Global Accelerator](https://aws.amazon.com/global-accelerator/) can also be used to improve network performance by either caching content at edge locations or providing users with an optimal path to the workload through the AWS global network.

Amazon EC2 provides placement groups for networking. A placement group is a logical grouping of instances to decrease latency. Using placement groups with supported instance types and an Elastic Network Adapter (ENA) enables workloads to participate in a low-latency, reduced jitter 25 Gbps network. Placement groups are recommended for workloads that benefit from low network latency, high network throughput, or both.

Latency-sensitive services are delivered at edge locations using AWS global network, such as [Amazon CloudFront](https://aws.amazon.com/cloudfront/). These edge locations commonly provide services like content delivery network (CDN) and domain name system (DNS). By having these services at the edge, workloads can respond with low latency to requests for content or DNS resolution. These services also provide geographic services, such as geotargeting of content (providing different content based on the end users’ location) or latency-based routing to direct end users to the nearest Region (minimum latency).

Use edge services to reduce latency and to enable content caching. Configure cache control correctly for both DNS and HTTP/HTTPS to gain the most benefit from these approaches.

### Implementation steps

- Capture information about the IP traffic going to and from network interfaces.

[Logging IP traffic using VPC Flow Logs](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html)
- [How the client IP address is preserved in AWS Global Accelerator](https://docs.aws.amazon.com/global-accelerator/latest/dg/preserve-client-ip-address.headers.html)

- Analyze network access patterns in your workload to identify how users use your application.

Use monitoring tools, such as [Amazon CloudWatch](https://aws.amazon.com/cloudwatch/) and [AWS CloudTrail](https://aws.amazon.com/cloudtrail/), to gather data on network activities.
- Analyze the data to identify the network access pattern.

- Select Regions for your workload deployment based on the following key elements:

**Where your data is located:** For data-heavy
applications (such as big data and machine learning), application code should run as
close to the data as possible.
- **Where your users are located**: For user-facing
applications, choose a Region (or Regions) close to your workload’s users.
- **Other constraints**: Consider constraints such as
cost and compliance as explained in [What to Consider when Selecting a Region for
your Workloads.](https://aws.amazon.com/blogs/architecture/what-to-consider-when-selecting-a-region-for-your-workloads/)

- Use [AWS Local Zones](https://aws.amazon.com/about-aws/global-infrastructure/localzones/) to run workloads like video rendering. Local Zones allow you to benefit from having compute and storage resources closer to end users.
- Use [AWS Outposts](https://aws.amazon.com/outposts/) for workloads that need to remain on-premises and where you want that workload to run seamlessly with the rest of your other workloads in AWS.
- Applications like high-resolution live video streaming, high-fidelity audio, and augmented reality or virtual reality (AR/VR) require ultra-low-latency for 5G devices. For such applications, consider [AWS Wavelength](https://aws.amazon.com/wavelength/). AWS Wavelength embeds AWS compute and storage services within 5G networks, providing mobile edge computing infrastructure for developing, deploying, and scaling ultra-low-latency applications.
- Use local caching or [AWS Caching Solutions](https://aws.amazon.com/caching/aws-caching/) for frequently used assets to improve performance, reduce data movement, and lower environmental impact.

Service
When to use

[Amazon CloudFront](https://aws.amazon.com/cloudfront/)

Use to cache static content such as images, scripts, and videos, as well as dynamic content such as API responses or web applications.

[Amazon ElastiCache](https://aws.amazon.com/elasticache/)

Use to cache content for web applications.

[DynamoDB Accelerator](https://aws.amazon.com/dynamodb/dax/)

Use to add in-memory acceleration to your DynamoDB tables.
- Use services that can help you run code closer to users of your workload like the following:

Service
When to use

[Lambda@edge](https://aws.amazon.com/lambda/edge/)

Use for compute-heavy operations that are initiated when objects are not in the cache.

[Amazon CloudFront Functions](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/cloudfront-functions.html)

Use for simple use cases like HTTP(s) requests or response manipulations that can be initiated by short-lived functions.

[AWS IoT Greengrass](https://aws.amazon.com/greengrass/)

Use to run local compute, messaging, and data caching for connected devices.
- Some applications require fixed entry points or higher performance by reducing first byte latency and jitter, and increasing throughput. These applications can benefit from networking services that provide static anycast IP addresses and TCP termination at edge locations. [AWS Global Accelerator](https://aws.amazon.com/global-accelerator/) can improve performance for your applications by up to 60% and provide quick failover for multi-region architectures. AWS Global Accelerator provides you with static anycast IP addresses that serve as a fixed entry point for your applications hosted in one or more AWS Regions. These IP addresses permit traffic to ingress onto the AWS global network as close to your users as possible. AWS Global Accelerator reduces the initial connection setup time by establishing a TCP connection between the client and the AWS edge location closest to the client. Review the use of AWS Global Accelerator to improve the performance of your TCP/UDP workloads and provide quick failover for multi-Region architectures.

## Resources

**Related best practices:**

- COST07-BP02 Implement Regions based on cost
- COST08-BP03 Implement services to reduce data transfer costs
- REL10-BP01 Deploy the workload to multiple locations
- REL10-BP02 Select the appropriate locations for your multi-location deployment
- SUS01-BP01 Choose Region based on both business requirements and sustainability goals
- SUS02-BP04 Optimize geographic placement of workloads based on their networking requirements
- SUS04-BP07 Minimize data movement across networks

**Related documents:**

- [AWS Global Infrastructure](https://aws.amazon.com/about-aws/global-infrastructure/)
- [AWS Local Zones and AWS Outposts, choosing the right technology for your edge workload](https://aws.amazon.com/blogs/compute/aws-local-zones-and-aws-outposts-choosing-the-right-technology-for-your-edge-workload/)
- [Placement groups](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/placement-groups.html)
- [AWS Local Zones](https://aws.amazon.com/about-aws/global-infrastructure/localzones/)
- [AWS Outposts](https://aws.amazon.com/outposts/)
- [AWS Wavelength](https://aws.amazon.com/wavelength/)
- [Amazon CloudFront](https://aws.amazon.com/cloudfront/)
- [AWS Global Accelerator](https://aws.amazon.com/global-accelerator/)
- [AWS Direct Connect](https://aws.amazon.com/directconnect/)
- [AWS Site-to-Site VPN](https://aws.amazon.com/vpn/site-to-site-vpn/)
- [Amazon Route 53](https://aws.amazon.com/route53/)

**Related videos:**

- [AWS Local Zones Explainer Video](https://www.youtube.com/watch?v=JHt-D4_zh7w)
- [AWS Outposts: Overview and How it Works](https://www.youtube.com/watch?v=ppG2FFB0mMQ)
- [AWS re:Invent 2023 - A migration strategy for edge and on-premises workloads](https://www.youtube.com/watch?v=4wUXzYNLvTw)
- [AWS re:Invent 2021 - AWS Outposts: Bringing the AWS experience on premises](https://www.youtube.com/watch?v=FxVF6A22498)
- [AWS re:Invent 2020: AWS Wavelength: Run apps with ultra-low latency at 5G edge](https://www.youtube.com/watch?v=AQ-GbAFDvpM)
- [AWS re:Invent 2022 - AWS Local Zones: Building applications for a distributed edge](https://www.youtube.com/watch?v=bDnh_d-slhw)
- [AWS re:Invent 2021 - Building low-latency websites with Amazon CloudFront](https://www.youtube.com/watch?v=9npcOZ1PP_c)
- [AWS re:Invent 2022 - Improve performance and availability with AWS Global Accelerator](https://www.youtube.com/watch?v=s5sjsdDC0Lg)
- [AWS re:Invent 2022 - Build your global wide area network using AWS](https://www.youtube.com/watch?v=flBieylTwvI)
- [AWS re:Invent 2020: Global traffic management with Amazon Route 53](https://www.youtube.com/watch?v=E33dA6n9O7I)

**Related examples:**

- [AWS Global Accelerator Custom Routing Workshop](https://catalog.us-east-1.prod.workshops.aws/workshops/ac213084-3f4a-4b01-9835-5052d6096b5b/en-US)
- [Handling Rewrites and Redirects using Edge Functions](https://catalog.us-east-1.prod.workshops.aws/workshops/814dcdac-c2ad-4386-98d5-27d37bb77766/en-US)
