---
id: "SEC09-BP03"
title: "Authenticate network communications"
framework: "WAF"
domain: "Security"
capability: "How do you protect your data in transit?"
risk_level: "Low"
---

# SEC09-BP03 Authenticate network communications

## Desired Outcome
A workload with well-defined data plane and control plane traffic flows between services. The traffic flows use authenticated and encrypted network protocols where technically feasible.

## Anti-Patterns
- Unencrypted or unauthenticated traffic flows within your workload.
- Reusing authentication credentials across multiple users or entities.
- Relying solely on network controls as an access control mechanism.
- Creating a custom authentication mechanism rather than relying on industry-standard authentication mechanisms.
- Overly permissive traffic flows between service components or other resources in the VPC.

## Implementation Guidance
 Your workload’s network traffic patterns can be characterized into two categories:
- *East-west traffic* represents traffic flows between services that make up a workload.
- *North-south traffic* represents traffic flows between your workload and consumers.

 While it is common practice to encrypt north-south traffic, securing east-west traffic using authenticated protocols is less common. Modern security practices recommend that network design alone does not grant a trusted relationship between two entities. When two services may reside within a common network boundary, it is still best practice to encrypt, authenticate, and authorize communications between those services.

 As an example, AWS service APIs use the [AWS Signature Version 4 (SigV4)](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_aws-signing.html) signature protocol to authenticate the caller, no matter what network the request originates from. This authentication ensures that AWS APIs can verify the identity that requested the action, and that identity can then be combined with policies to make an authorization decision to determine whether the action should be allowed or not.

 Services such as [Amazon VPC Lattice](https://docs.aws.amazon.com/vpc-lattice/latest/ug/access-management-overview.html) and [Amazon API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/permissions.html) allow you use the same SigV4 signature protocol to add authentication and authorization to east-west traffic in your own workloads. If resources outside of your AWS environment need to communicate with services that require SigV4-based authentication and authorization, you can use [AWS Identity and Access Management (IAM) Roles Anywhere](https://docs.aws.amazon.com/rolesanywhere/latest/userguide/introduction.html) on the non-AWS resource to acquire temporary AWS credentials. These credentials can be used to sign requests to services using SigV4 to authorize access.

 Another common mechanism for authenticating east-west traffic is TLS mutual authentication (mTLS). Many Internet of Things (IoT), business-to-business applications, and microservices use mTLS to validate the identity of both sides of a TLS communication through the use of both client and server-side X.509 certificates. These certificates can be issued by AWS Private Certificate Authority (AWS Private CA). You can use services such as [Amazon API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/rest-api-mutual-tls.html) to provide mTLS authentication for inter- or intra-workload communication. [Application Load Balancer also supports mTLS](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/mutual-authentication.html) for internal or external facing workloads. While mTLS provides authentication information for both sides of a TLS communication, it does not provide a mechanism for authorization.

 Finally, OAuth 2.0 and OpenID Connect (OIDC) are two protocols typically used for controlling access to services by users, but are now becoming popular for service-to-service traffic as well. API Gateway provides a [JSON Web Token (JWT) authorizer](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-jwt-authorizer.html), allowing workloads to restrict access to API routes using JWTs issued from OIDC or OAuth 2.0 identity providers. OAuth2 scopes can be used as a source for basic authorization decisions, but the authorization checks still need to be implemented in the application layer, and OAuth2 scopes alone cannot support more complex authorization needs.

## Implementation Steps
- **Define and document your workload network flows:** The first step in implementing a defense-in-depth strategy is defining your workload’s traffic flows.
  - Create a data flow diagram that clearly defines how data is transmitted between different services that comprise your workload. This diagram is the first step to enforcing those flows through authenticated network channels.
  - Instrument your workload in development and testing phases to validate that the data flow diagram accurately reflects the workload’s behavior at runtime.
  - A data flow diagram can also be useful when performing a threat modeling exercise, as described in [SEC01-BP07 Identify threats and prioritize mitigations using a threat model](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_securely_operate_threat_model.html).
- **Establish network controls:** Consider AWS capabilities to establish network controls aligned to your data flows. While network boundaries should not be the only security control, they provide a layer in the defense-in-depth strategy to protect your workload.
  - Use [security groups](https://docs.aws.amazon.com/vpc/latest/userguide/security-groups.html) to establish define and restrict data flows between resources.
  - Consider using [AWS PrivateLink](https://docs.aws.amazon.com/vpc/latest/privatelink/what-is-privatelink.html) to communicate with both AWS and third-party services that support AWS PrivateLink. Data sent through a AWS PrivateLink interface endpoint stays within the AWS network backbone and does not traverse the public Internet.
- **Implement authentication and authorization across services in your workload:** Choose the set of AWS services most appropriate to provide authenticated, encrypted traffic flows in your workload.
  - Consider [Amazon VPC Lattice](https://docs.aws.amazon.com/vpc-lattice/latest/ug/what-is-vpc-lattice.html) to secure service-to-service communication. VPC Lattice can use [SigV4 authentication combined with auth policies](https://docs.aws.amazon.com/vpc-lattice/latest/ug/auth-policies.html) to control service-to-service access.
  - For service-to-service communication using mTLS, consider [API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/rest-api-mutual-tls.html), [Application Load Balancer](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/mutual-authentication.html). [AWS Private CA](https://docs.aws.amazon.com/privateca/latest/userguide/PcaWelcome.html) can be used to establish a private CA hierarchy capable of issuing certificates for use with mTLS.
  - When integrating with services using OAuth 2.0 or OIDC, consider [API Gateway using the JWT authorizer](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-jwt-authorizer.html).
  - For communication between your workload and IoT devices, consider [AWS IoT Core](https://docs.aws.amazon.com/iot/latest/developerguide/client-authentication.html), which provides several options for network traffic encryption and authentication.
- **Monitor for unauthorized access:** Continually monitor for unintended communication channels, unauthorized principals attempting to access protected resources, and other improper access patterns.
  - If using VPC Lattice to manage access to your services, consider enabling and monitoring [VPC Lattice access logs](https://docs.aws.amazon.com/vpc-lattice/latest/ug/monitoring-access-logs.html). These access logs include information on the requesting entity, network information including source and destination VPC, and request metadata.
  - Consider enabling [VPC flow logs](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html) to capture metadata on network flows and periodically review for anomalies.
  - Refer to the [AWS Security Incident Response Guide](https://docs.aws.amazon.com/whitepapers/latest/aws-security-incident-response-guide/aws-security-incident-response-guide.html) and the [Incident Response section](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/incident-response.html) of the AWS Well-Architected Framework security pillar for more guidance on planning, simulating, and responding to security incidents.

## Resources
### Related Best Practices
- [ SEC03-BP07 Analyze public and cross-account access ](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_permissions_analyze_cross_account.html)
- [ SEC02-BP02 Use temporary credentials ](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_identities_unique.html)
- [ SEC01-BP07 Identify threats and prioritize mitigations using a threat model ](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_securely_operate_threat_model.html)
### Related Documents
- [ Evaluating access control methods to secure Amazon API Gateway APIs ](https://aws.amazon.com/blogs/compute/evaluating-access-control-methods-to-secure-amazon-api-gateway-apis/)
- [ Configuring mutual TLS authentication for a REST API ](https://docs.aws.amazon.com/apigateway/latest/developerguide/rest-api-mutual-tls.html)
- [ How to secure API Gateway HTTP endpoints with JWT authorizer ](https://aws.amazon.com/blogs/security/how-to-secure-api-gateway-http-endpoints-with-jwt-authorizer/)
- [ Authorizing direct calls to AWS services using AWS IoT Core credential provider ](https://docs.aws.amazon.com/iot/latest/developerguide/authorizing-direct-aws.html)
- [AWS Security Incident Response Guide ](https://docs.aws.amazon.com/whitepapers/latest/aws-security-incident-response-guide/aws-security-incident-response-guide.html)
### Related Videos
- [AWS re:invent 2022: Introducing VPC Lattice ](https://www.youtube.com/watch?v=fRjD1JI0H5w)
- [AWS re:invent 2020: Serverless API authentication for HTTP APIs on AWS](https://www.youtube.com/watch?v=AW4kvUkUKZ0)
### Related Examples
- [ Amazon VPC Lattice Workshop ](https://catalog.us-east-1.prod.workshops.aws/workshops/9e543f60-e409-43d4-b37f-78ff3e1a07f5/en-US)
- [ Zero-Trust Episode 1 – The Phantom Service Perimeter workshop ](https://catalog.us-east-1.prod.workshops.aws/workshops/dc413216-deab-4371-9e4a-879a4f14233d/en-US)
