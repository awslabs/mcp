---
id: "SUS02-BP04"
title: "Optimize geographic placement of workloads based on their networking requirements"
framework: "WAF"
domain: "Sustainability"
capability: "How do you align cloud resources to your demand?"
risk_level: "Medium"
---

# SUS02-BP04 Optimize geographic placement of workloads based on their networking requirements

## Implementation Guidance
 The AWS Cloud infrastructure is built around location options such as Regions, Availability Zones, placement groups, and edge locations such as [AWS Outposts](https://docs.aws.amazon.com/outposts/latest/userguide/what-is-outposts.html) and [AWS Local Zones](https://aws.amazon.com/about-aws/global-infrastructure/localzones/). These location options are responsible for maintaining connectivity between application components, cloud services, edge networks and on-premises data centers.

 Analyze the network access patterns in your workload to identify how to use these cloud location options and reduce the distance network traffic must travel.

## Implementation Steps
- Analyze network access patterns in your workload to identify how users use your application.
  - Use monitoring tools, such as [Amazon CloudWatch](https://aws.amazon.com/cloudwatch/) and [AWS CloudTrail](https://aws.amazon.com/cloudtrail/), to gather data on network activities.
  - Analyze the data to identify the network access pattern.
- Select the Regions for your workload deployment based on the following key elements:
  - **Your Sustainability goal:** as explained in [Region selection](https://docs.aws.amazon.com/wellarchitected/latest/sustainability-pillar/region-selection.html).
  - **Where your data is located:** For data-heavy applications (such as big data and machine learning), application code should run as close to the data as possible.
  - **Where your users are located:** For user-facing applications, choose a Region (or Regions) close to your workload’s users.
  - **Other constraints:** Consider constraints such as cost and compliance as explained in [What to Consider when Selecting a Region for your Workloads](https://aws.amazon.com/blogs/architecture/what-to-consider-when-selecting-a-region-for-your-workloads/).
- Use local caching or [AWS Caching Solutions](https://aws.amazon.com/caching/aws-caching/) for frequently used assets to improve performance, reduce data movement, and lower environmental impact.
[\[See the AWS documentation website for more details\]](http://docs.aws.amazon.com/wellarchitected/latest/framework/sus_sus_user_a5.html)
- Use services that can help you run code closer to users of your workload:
[\[See the AWS documentation website for more details\]](http://docs.aws.amazon.com/wellarchitected/latest/framework/sus_sus_user_a5.html)
- Use connection pooling to allow for connection reuse and reduce required resources.
- Use distributed data stores that don’t rely on persistent connections and synchronous updates for consistency to serve regional populations.
- Replace pre-provisioned static network capacity with shared dynamic capacity, and share the sustainability impact of network capacity with other subscribers.

## Resources
### Related Documents
- [Optimizing your AWS Infrastructure for Sustainability, Part III: Networking](https://aws.amazon.com/blogs/architecture/optimizing-your-aws-infrastructure-for-sustainability-part-iii-networking/)
- [Amazon ElastiCache Documentation](https://docs.aws.amazon.com/elasticache/index.html)
- [What is Amazon CloudFront?](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Introduction.html)
- [Amazon CloudFront Key Features](https://aws.amazon.com/cloudfront/features/)
- [AWS Global Infrastructure ](https://aws.amazon.com/about-aws/global-infrastructure/)
- [AWS Local Zones and AWS Outposts, choosing the right technology for your edge workload ](https://aws.amazon.com/blogs/compute/aws-local-zones-and-aws-outposts-choosing-the-right-technology-for-your-edge-workload/)
- [ Placement groups ](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/placement-groups.html)
- [AWS Local Zones ](https://aws.amazon.com/about-aws/global-infrastructure/localzones/)
- [AWS Outposts](https://aws.amazon.com/outposts/)
### Related Videos
- [Demystifying data transfer on AWS](https://www.youtube.com/watch?v=-MqXgzw1IGA)
- [ Scaling network performance on next-gen Amazon EC2 instances ](https://www.youtube.com/watch?v=jNYpWa7gf1A)
- [AWS Local Zones Explainer Video ](https://www.youtube.com/watch?v=JHt-D4_zh7w)
- [AWS Outposts: Overview and How it Works ](https://www.youtube.com/watch?v=ppG2FFB0mMQ)
- [AWS re:Invent 2023 - A migration strategy for edge and on-premises workloads ](https://www.youtube.com/watch?v=4wUXzYNLvTw)
- [AWS re:Invent 2021 - AWS Outposts: Bringing the AWS experience on premises ](https://www.youtube.com/watch?v=FxVF6A22498)
- [AWS re:Invent 2020 - AWS Wavelength: Run apps with ultra-low latency at 5G edge ](https://www.youtube.com/watch?v=AQ-GbAFDvpM)
- [AWS re:Invent 2022 - AWS Local Zones: Building applications for a distributed edge ](https://www.youtube.com/watch?v=bDnh_d-slhw)
- [AWS re:Invent 2021 - Building low-latency websites with Amazon CloudFront ](https://www.youtube.com/watch?v=9npcOZ1PP_c)
- [AWS re:Invent 2022 - Improve performance and availability with AWS Global Accelerator](https://www.youtube.com/watch?v=s5sjsdDC0Lg)
- [AWS re:Invent 2022 - Build your global wide area network using AWS](https://www.youtube.com/watch?v=flBieylTwvI)
- [AWS re:Invent 2020: Global traffic management with Amazon Route 53 ](https://www.youtube.com/watch?v=E33dA6n9O7I)
### Related Examples
- [AWS Networking Workshops](https://catalog.workshops.aws/networking/en-US)
- [ Architecting for sustainability - Minimize data movement across networks ](https://catalog.us-east-1.prod.workshops.aws/workshops/7c4f8394-8081-4737-aa1b-6ae811d46e0a/en-US)
