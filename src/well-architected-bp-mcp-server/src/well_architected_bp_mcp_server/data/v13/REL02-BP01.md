---
id: "REL02-BP01"
title: "Use highly available network connectivity for your workload public endpoints"
framework: "WAF"
domain: "Reliability"
capability: "How do you plan your network topology?"
risk_level: "High"
---

# REL02-BP01 Use highly available network connectivity for your workload public endpoints

## Desired Outcome
It is critical to plan, build, and operationalize highly available network connectivity for your public endpoints. If your workload becomes unreachable due to a loss in connectivity, even if your workload is running and available, your customers will see your system as down. By combining the highly available and resilient network connectivity for your workload’s public endpoints, along with a resilient architecture for your workload itself, you can provide the best possible availability and service level for your customers.

 AWS Global Accelerator, Amazon CloudFront, Amazon API Gateway, AWS Lambda Function URLs, AWS AppSync APIs, and Elastic Load Balancing (ELB) all provide highly available public endpoints. Amazon Route 53 provides a highly available DNS service for domain name resolution to verify that your public endpoint addresses can be resolved.

 You can also evaluate AWS Marketplace software appliances for load balancing and proxying.

## Anti-Patterns
- Designing a highly available workload without planning out DNS and network connectivity for high availability.
- Using public internet addresses on individual instances or containers and managing the connectivity to them with DNS.
- Using IP addresses instead of domain names for locating services.
- Not testing out scenarios where connectivity to your public endpoints is lost.
- Not analyzing network throughput needs and distribution patterns.
- Not testing and planning for scenarios where internet network connectivity to your public endpoints of your workload might be interrupted.
- Providing content (like web pages, static assets, or media files) to a large geographic area and not using a content delivery network.
- Not planning for distributed denial of service (DDoS) attacks. DDoS attacks risk shutting out legitimate traffic and lowering availability for your users.

## Implementation Guidance
 At the core of building highly available network connectivity to your public endpoints is the routing of the traffic. To verify your traffic is able to reach the endpoints, the DNS must be able to resolve the domain names to their corresponding IP addresses. Use a highly available and scalable [Domain Name System (DNS)](https://aws.amazon.com/route53/what-is-dns/) such as Amazon Route 53 to manage your domain’s DNS records. You can also use health checks provided by Amazon Route 53. The health checks verify that your application is reachable, available, and functional, and they can be set up in a way that they mimic your user’s behavior, such as requesting a web page or a specific URL. In case of failure, Amazon Route 53 responds to DNS resolution requests and directs the traffic to only healthy endpoints. You can also consider using Geo DNS and Latency Based Routing capabilities offered by Amazon Route 53.

 To verify that your workload itself is highly available, use Elastic Load Balancing (ELB). Amazon Route 53 can be used to target traffic to ELB, which distributes the traffic to the target compute instances. You can also use Amazon API Gateway along with AWS Lambda for a serverless solution. Customers can also run workloads in multiple AWS Regions. With [multi-site active/active pattern](https://aws.amazon.com/blogs/architecture/disaster-recovery-dr-architecture-on-aws-part-i-strategies-for-recovery-in-the-cloud/), the workload can serve traffic from multiple Regions. With a multi-site active/passive pattern, the workload serves traffic from the active region while data is replicated to the secondary region and becomes active in the event of a failure in the primary region. Route 53 health checks can then be used to control DNS failover from any endpoint in a primary Region to an endpoint in a secondary Region, verifying that your workload is reachable and available to your users.

 Amazon CloudFront provides a simple API for distributing content with low latency and high data transfer rates by serving requests using a network of edge locations around the world. Content delivery networks (CDNs) serve customers by serving content located or cached at a location near to the user. This also improves availability of your application as the load for content is shifted away from your servers over to CloudFront’s [edge locations](https://aws.amazon.com/products/networking/edge-networking/). The edge locations and regional edge caches hold cached copies of your content close to your viewers resulting in quick retrieval and increasing reachability and availability of your workload.

 For workloads with users spread out geographically, AWS Global Accelerator helps you improve the availability and performance of the applications. AWS Global Accelerator provides Anycast static IP addresses that serve as a fixed entry point to your application hosted in one or more AWS Regions. This allows traffic to ingress onto the AWS global network as close to your users as possible, improving reachability and availability of your workload. AWS Global Accelerator also monitors the health of your application endpoints by using TCP, HTTP, and HTTPS health checks. Any changes in the health or configuration of your endpoints permit redirection of user traffic to healthy endpoints that deliver the best performance and availability to your users. In addition, AWS Global Accelerator has a fault-isolating design that uses two static IPv4 addresses that are serviced by independent network zones increasing the availability of your applications.

 To help protect customers from DDoS attacks, AWS provides AWS Shield Standard. Shield Standard comes automatically turned on and protects from common infrastructure (layer 3 and 4) attacks like SYN/UDP floods and reflection attacks to support high availability of your applications on AWS. For additional protections against more sophisticated and larger attacks (like UDP floods), state exhaustion attacks (like TCP SYN floods), and to help protect your applications running on Amazon Elastic Compute Cloud (Amazon EC2), Elastic Load Balancing (ELB), Amazon CloudFront, AWS Global Accelerator, and Route 53, you can consider using AWS Shield Advanced. For protection against Application layer attacks like HTTP POST or GET floods, use AWS WAF. AWS WAF can use IP addresses, HTTP headers, HTTP body, URI strings, SQL injection, and cross-site scripting conditions to determine if a request should be blocked or allowed.

## Implementation Steps
1.  Set up highly available DNS: Amazon Route 53 is a highly available and scalable [domain name system (DNS)](https://aws.amazon.com/route53/what-is-dns/) web service. Route 53 connects user requests to internet applications running on AWS or on-premises. For more information, see [configuring Amazon Route 53 as your DNS service](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/dns-configuring.html).

1.  Setup health checks: When using Route 53, verify that only healthy targets are resolvable. Start by [creating Route 53 health checks and configuring DNS failover](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/dns-failover.html). The following aspects are important to consider when setting up health checks:

   1. [ How Amazon Route 53 determines whether a health check is healthy ](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/dns-failover-determining-health-of-endpoints.html)

   1. [ Creating, updating, and deleting health checks ](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/health-checks-creating-deleting.html)

   1. [ Monitoring health check status and getting notifications ](https://docs.aws.amazon.com/)

   1. [ Best practices for Amazon Route 53 DNS ](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/health-checks-monitor-view-status.html)

1. [ Connect your DNS service to your endpoints. ](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/best-practices-dns.html)

   1.  When using Elastic Load Balancing as a target for your traffic, create an [alias record](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resource-record-sets-choosing-alias-non-alias.html) using Amazon Route 53 that points to your load balancer’s regional endpoint. During the creation of the alias record, set the Evaluate target health option to Yes.

   1.  For serverless workloads or private APIs when API Gateway is used, use [Route 53 to direct traffic to API Gateway](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-to-api-gateway.html).

1.  Decide on a content delivery network.

   1.  For delivering content using edge locations closer to the user, start by understanding [how CloudFront delivers content](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/HowCloudFrontWorks.html).

   1.  Get started with a [simple CloudFront distribution](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/GettingStarted.SimpleDistribution.html). CloudFront then knows where you want the content to be delivered from, and the details about how to track and manage content delivery. The following aspects are important to understand and consider when setting up CloudFront distribution:

      1. [ How caching works with CloudFront edge locations ](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/cache-hit-ratio-explained.html)

      1. [ Increasing the proportion of requests that are served directly from the CloudFront caches (cache hit ratio) ](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/cache-hit-ratio.html)

      1. [ Using Amazon CloudFront Origin Shield ](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/origin-shield.html)

      1. [ Optimizing high availability with CloudFront origin failover ](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/high_availability_origin_failover.html)

1.  Set up application layer protection: AWS WAF helps you protect against common web exploits and bots that can affect availability, compromise security, or consume excessive resources. To get a deeper understanding, review [how AWS WAF works](https://docs.aws.amazon.com/waf/latest/developerguide/how-aws-waf-works.html) and when you are ready to implement protections from application layer HTTP POST AND GET floods, review [Getting started with AWS WAF](https://docs.aws.amazon.com/waf/latest/developerguide/getting-started.html). You can also use AWS WAF with CloudFront see the documentation on [how AWS WAF works with Amazon CloudFront features](https://docs.aws.amazon.com/waf/latest/developerguide/cloudfront-features.html).

1.  Set up additional DDoS protection: By default, all AWS customers receive protection from common, most frequently occurring network and transport layer DDoS attacks that target your web site or application with AWS Shield Standard at no additional charge. For additional protection of internet-facing applications running on Amazon EC2, Elastic Load Balancing, Amazon CloudFront, AWS Global Accelerator, and Amazon Route 53 you can consider [AWS Shield Advanced](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-advanced-summary.html) and review [examples of DDoS resilient architectures](https://docs.aws.amazon.com/waf/latest/developerguide/ddos-resiliency.html). To protect your workload and your public endpoints from DDoS attacks review [Getting started with AWS Shield Advanced](https://docs.aws.amazon.com/waf/latest/developerguide/getting-started-ddos.html).

## Resources
### Related Best Practices
- [REL10-BP01 Deploy the workload to multiple locations](rel_fault_isolation_multiaz_region_system.md)
- [REL11-BP04 Rely on the data plane and not the control plane during recovery](rel_withstand_component_failures_avoid_control_plane.md)
- [REL11-BP06 Send notifications when events impact availability](rel_withstand_component_failures_notifications_sent_system.md)
### Related Documents
- [APN Partner: partners that can help plan your networking](https://aws.amazon.com/partners/find/results/?keyword=network)
- [AWS Marketplace for Network Infrastructure](https://aws.amazon.com/marketplace/b/2649366011)
- [What Is AWS Global Accelerator?](https://docs.aws.amazon.com/global-accelerator/latest/dg/what-is-global-accelerator.html)
- [What is Amazon CloudFront?](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Introduction.html)
- [What is Amazon Route 53?](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/Welcome.html)
- [What is Elastic Load Balancing?](https://docs.aws.amazon.com/elasticloadbalancing/latest/userguide/what-is-load-balancing.html)
- [ Network Connectivity capability - Establishing Your Cloud Foundations ](https://docs.aws.amazon.com/whitepapers/latest/establishing-your-cloud-foundation-on-aws/network-connectivity-capability.html)
- [ What is Amazon API Gateway? ](https://docs.aws.amazon.com/apigateway/latest/developerguide/welcome.html)
- [ What are AWS WAF, AWS Shield, and AWS Firewall Manager? ](https://docs.aws.amazon.com/waf/latest/developerguide/what-is-aws-waf.html)
- [ What is Amazon Application Recovery Controller? ](https://docs.aws.amazon.com/r53recovery/latest/dg/what-is-route53-recovery.html)
- [ Configure custom health checks for DNS failover ](https://docs.aws.amazon.com/apigateway/latest/developerguide/dns-failover.html)
### Related Videos
- [AWS re:Invent 2022 - Improve performance and availability with AWS Global Accelerator](https://www.youtube.com/watch?v=s5sjsdDC0Lg)
- [AWS re:Invent 2020: Global traffic management with Amazon Route 53 ](https://www.youtube.com/watch?v=E33dA6n9O7I)
- [AWS re:Invent 2022 - Operating highly available Multi-AZ applications ](https://www.youtube.com/watch?v=mwUV5skJJ0s)
- [AWS re:Invent 2022 - Dive deep on AWS networking infrastructure ](https://www.youtube.com/watch?v=HJNR_dX8g8c)
- [AWS re:Invent 2022 - Building resilient networks ](https://www.youtube.com/watch?v=u-qamiNgH7Q)
### Related Examples
- [ Disaster Recovery with Amazon Application Recovery Controller (ARC) ](https://catalog.us-east-1.prod.workshops.aws/workshops/4d9ab448-5083-4db7-bee8-85b58cd53158/en-US/)
- [AWS Global Accelerator Workshop ](https://catalog.us-east-1.prod.workshops.aws/workshops/effb1517-b193-4c59-8da5-ce2abdb0b656/en-US)
