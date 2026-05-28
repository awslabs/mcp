---
id: "SEC05-BP03"
title: "Implement inspection-based protection"
framework: "WAF"
domain: "Security"
capability: "How do you protect your network resources?"
risk_level: "Medium"
---

# SEC05-BP03 Implement inspection-based protection

## Desired Outcome
Traffic that traverses between your network layers are inspected and authorized.  Allow and deny decisions are based on explicit rules, threat intelligence, and deviations from baseline behaviors.  Protections become stricter as traffic moves closer to sensitive data.

## Anti-Patterns
- Relying solely on firewall rules based on ports and protocols. Not taking advantage of intelligent systems.
- Authoring firewall rules based on specific current threat patterns that are subject to change.
- Only inspecting traffic where traffic transits from private to public subnets, or from public subnets to the Internet.
- Not having a baseline view of your network traffic to compare for behavior anomalies.

## Implementation Guidance
 Have fine-grained control over both your stateful and stateless network traffic using AWS Network Firewall, or other [Firewalls](https://aws.amazon.com/marketplace/search/results?searchTerms=firewalls) and [Intrusion Prevention Systems](https://aws.amazon.com/marketplace/search/results?searchTerms=Intrusion+Prevention+Systems) (IPS) on AWS Marketplace that you can deploy behind a [Gateway Load Balancer (GWLB)](https://aws.amazon.com/elasticloadbalancing/gateway-load-balancer/).  AWS Network Firewall supports [Suricata-compatible](https://docs.aws.amazon.com/network-firewall/latest/developerguide/stateful-rule-groups-ips.html) open source IPS specifications to help protect your workload.

 Both the AWS Network Firewall and vendor solutions that use a GWLB support different inline inspection deployment models.  For example, you can perform inspection on a per-VPC basis, centralize in an inspection VPC, or deploy in a hybrid model where east-west traffic flows through an inspection VPC and Internet ingress is inspected per-VPC.  Another consideration is whether the solution supports unwrapping Transport Layer Security (TLS), enabling deep packet inspection for traffic flows initiated in either direction. For more information and in-depth details on these configurations, see the [AWS Network Firewall Best Practice guide](https://aws.github.io/aws-security-services-best-practices/guides/network-firewall/).

 If you are using solutions that perform out-of-band inspections, such as pcap analysis of packet data from network interfaces operating in promiscuous mode, you can configure [VPC traffic mirroring](https://docs.aws.amazon.com/vpc/latest/mirroring/what-is-traffic-mirroring.html). Mirrored traffic counts towards the available bandwidth of your interfaces and is subject to the same data transfer charges as non-mirrored traffic. You can see if virtual versions of these appliances are available on the [AWS Marketplace](https://aws.amazon.com/marketplace/solutions/infrastructure-software/cloud-networking), which may support inline deployment behind a GWLB.

 For components that transact over HTTP-based protocols, protect your application from common threats with a web application firewall (WAF). [AWS WAF](https://aws.amazon.com/waf) is a web application firewall that lets you monitor and block HTTP(S) requests that match your configurable rules before sending to Amazon API Gateway, Amazon CloudFront, AWS AppSync or an Application Load Balancer. Consider deep packet inspection when you evaluate the deployment of your web application firewall, as some require you to terminate TLS before traffic inspection. To get started with AWS WAF, you can use [AWS Managed Rules](https://docs.aws.amazon.com/waf/latest/developerguide/getting-started.html#getting-started-wizard-add-rule-group) in combination with your own, or use existing [partner integrations](https://aws.amazon.com/waf/partners/).

 You can centrally manage AWS WAF, AWS Shield Advanced, AWS Network Firewall, and Amazon VPC security groups across your AWS Organization with [AWS Firewall Manager](https://aws.amazon.com/firewall-manager/).

## Implementation Steps
1.  Determine if you can scope inspection rules broadly, such as through an inspection VPC, or if you require a more granular per-VPC approach.

1.  For inline inspection solutions:

   1.  If using AWS Network Firewall, create rules, firewall policies, and the firewall itself. Once these have been configured, you can [route traffic to the firewall endpoint](https://aws.amazon.com/blogs/networking-and-content-delivery/deployment-models-for-aws-network-firewall/) to enable inspection.

   1.  If using a third-party appliance with a Gateway Load Balancer (GWLB), deploy and configure your appliance in one or more availability zones. Then, create your GWLB, the endpoint service, endpoint, and configure routing for your traffic.

1.  For out-of-band inspection solutions:

   1.  Turn on VPC Traffic Mirroring on interfaces where inbound and outbound traffic should be mirrored. You can use Amazon EventBridge rules to invoke an AWS Lambda function to turn on traffic mirroring on interfaces when new resources are created. Point the traffic mirroring sessions to the Network Load Balancer in front of your appliance that processes traffic.

1.  For inbound web traffic solutions:

   1.  To configure AWS WAF, start by configuring a web access control list (web ACL). The web ACL is a collection of rules with a serially processed default action (ALLOW or DENY) that defines how your WAF handles traffic. You can create your own rules and groups or use AWS managed rule groups in your web ACL.

   1.  Once your web ACL is configured, associate the web ACL with an AWS resource (like an Application Load Balancer, API Gateway REST API, or CloudFront distribution) to begin protecting web traffic.

## Resources
### Related Documents
- [What is Traffic Mirroring?](https://docs.aws.amazon.com/vpc/latest/mirroring/what-is-traffic-mirroring.html)
- [Implementing inline traffic inspection using third-party security appliances](https://docs.aws.amazon.com/prescriptive-guidance/latest/inline-traffic-inspection-third-party-appliances/welcome.html)
- [AWS Network Firewall example architectures with routing](https://docs.aws.amazon.com/network-firewall/latest/developerguide/architectures.html)
- [Centralized inspection architecture with AWS Gateway Load Balancer and AWS Transit Gateway](https://aws.amazon.com/blogs/networking-and-content-delivery/centralized-inspection-architecture-with-aws-gateway-load-balancer-and-aws-transit-gateway/)
### Related Examples
- [Best practices for deploying Gateway Load Balancer](https://aws.amazon.com/blogs/networking-and-content-delivery/best-practices-for-deploying-gateway-load-balancer/)
- [TLS inspection configuration for encrypted egress traffic and AWS Network Firewall](https://aws.amazon.com/blogs/security/tls-inspection-configuration-for-encrypted-egress-traffic-and-aws-network-firewall/)
### Related Tools
- [AWS Marketplace IDS/IPS](https://aws.amazon.com/marketplace/search/results?prevFilters=%257B%2522id%2522%3A%25220ed48363-5064-4d47-b41b-a53f7c937314%2522%257D&searchTerms=ids%2Fips)
