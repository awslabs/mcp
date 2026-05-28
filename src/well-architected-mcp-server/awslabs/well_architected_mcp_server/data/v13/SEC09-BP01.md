---
id: "SEC09-BP01"
title: "Implement secure key and certificate management"
framework: "WAF"
domain: "Security"
capability: "How do you protect your data in transit?"
risk_level: "High"
---

# SEC09-BP01 Implement secure key and certificate management

## Desired Outcome
A secure certificate management system that can provision, deploy, store, and renew certificates in a public key infrastructure (PKI). A secure key and certificate management mechanism prevents certificate private key material from disclosure and automatically renews the certificate on a periodic basis. It also integrates with other services to provide secure network communications and identity for machine resources inside of your workload. Key material should never be accessible to human identities.

## Anti-Patterns
- Performing manual steps during the certificate deployment or renewal processes.
- Paying insufficient attention to certificate authority (CA) hierarchy when designing a private CA.
- Using self-signed certificates for public resources.

## Implementation Guidance
 Modern workloads make extensive use of encrypted network communications using PKI protocols such as TLS. PKI certificate management can be complex, but automated certificate provisioning, deployment, and renewal can reduce the friction associated with certificate management.

 AWS provides two services to manage general-purpose PKI certificates: [AWS Certificate Manager](https://docs.aws.amazon.com/acm/latest/userguide/acm-overview.html) and [AWS Private Certificate Authority (AWS Private CA)](https://docs.aws.amazon.com/privateca/latest/userguide/PcaWelcome.html). ACM is the primary service that customers use to provision, manage, and deploy certificates for use in both public-facing as well as private AWS workloads. ACM issues private certificates using AWS Private CA and [integrates](https://docs.aws.amazon.com/acm/latest/userguide/acm-services.html) with many other AWS managed services to provide secure TLS certificates for workloads. ACM can also issue publicly trusted certificates from [Amazon Trust Services](https://www.amazontrust.com/repository/). Public certificates from ACM can be used on public facing workloads, as modern browsers and operating systems trust these certificates by default.

 AWS Private CA allows you to establish your own root or subordinate certificate authority and issue TLS certificates through an API. You can use these kinds of certificates in scenarios where you control and manage the trust chain on the client side of the TLS connection. In addition to TLS use cases, AWS Private CA can be used to issue certificates to Kubernetes pods, Matter device product attestations, code signing, and other use cases with a [custom template](https://docs.aws.amazon.com/privateca/latest/userguide/UsingTemplates.html). You can also use [IAM Roles Anywhere](https://docs.aws.amazon.com/rolesanywhere/latest/userguide/introduction.html) to provide temporary IAM credentials to on-premises workloads that have been issued X.509 certificates signed by your Private CA.

 In addition to ACM and AWS Private CA, [AWS IoT Core](https://docs.aws.amazon.com/iot/latest/developerguide/what-is-aws-iot.html) provides specialized support for provisioning, managing and deploying PKI certificates to IoT devices. AWS IoT Core provides specialized mechanisms for [onboarding IoT devices](https://docs.aws.amazon.com/whitepapers/latest/device-manufacturing-provisioning/device-manufacturing-provisioning.html) into your public key infrastructure at scale.

 Some AWS services, such as [Amazon API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/welcome.html) and [Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/userguide/what-is-load-balancing.html), offer their own capabilities for using certificates to secure application connections. For example, both API Gateway and Application Load Balancer (ALB) support mutual TLS (mTLS) using client certificates that you create and export using the AWS Management Console, CLI, or APIs.

**Considerations for establishing a private CA hierarchy **

 When you need to establish a private CA, it's important to take special care to properly design the CA hierarchy upfront. It's a best practice to deploy each level of your CA hierarchy into separate AWS accounts when creating a private CA hierarchy. This intentional step reduces the surface area for each level in the CA hierarchy, making it simpler to discover anomalies in CloudTrail log data and reducing the scope of access or impact if there is unauthorized access to one of the accounts. The root CA should reside in its own separate account and should only be used to issue one or more intermediate CA certificates.

 Then, create one or more intermediate CAs in accounts separate from the root CA's account to issue certificates for end users, devices, or other workloads. Finally, issue certificates from your root CA to the intermediate CAs, which will in turn issue certificates to your end users or devices. For more information on planning your CA deployment and designing your CA hierarchy, including planning for resiliency, cross-region replication, sharing CAs across your organization, and more, see [Planning your AWS Private CA deployment](https://docs.aws.amazon.com/privateca/latest/userguide/PcaPlanning.html).

## Implementation Steps
1.  Determine the relevant AWS services required for your use case:
   - Many use cases can leverage the existing AWS public key infrastructure using [AWS Certificate Manager](https://docs.aws.amazon.com/acm/latest/userguide/acm-overview.html). ACM can be used to deploy TLS certificates for web servers, load balancers, or other uses for publicly trusted certificates.
   - Consider [AWS Private CA](https://docs.aws.amazon.com/privateca/latest/userguide/PcaWelcome.html) when you need to establish your own private certificate authority hierarchy or need access to exportable certificates. ACM can then be used to issue [many types of end-entity certificates](https://docs.aws.amazon.com/privateca/latest/userguide/PcaIssueCert.html) using the AWS Private CA.
   - For use cases where certificates must be provisioned at scale for embedded Internet of things (IoT) devices, consider [AWS IoT Core](https://docs.aws.amazon.com/iot/latest/developerguide/x509-client-certs.html).
   - Consider using native mTLS functionality in services like [Amazon API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/welcome.html) or [Application Load Balancer](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/introduction.html).

1.  Implement automated certificate renewal whenever possible:
   - Use [ACM managed renewal](https://docs.aws.amazon.com/acm/latest/userguide/managed-renewal.html) for certificates issued by ACM along with integrated AWS managed services.

1.  Establish logging and audit trails:
   - Enable [CloudTrail logs](https://docs.aws.amazon.com/privateca/latest/userguide/PcaCtIntro.html) to track access to the accounts holding certificate authorities. Consider configuring log file integrity validation in CloudTrail to verify the authenticity of the log data.
   - Periodically generate and review [audit reports](https://docs.aws.amazon.com/privateca/latest/userguide/PcaAuditReport.html) that list the certificates that your private CA has issued or revoked. These reports can be exported to an S3 bucket.
   - When deploying a private CA, you will also need to establish an S3 bucket to store the Certificate Revocation List (CRL). For guidance on configuring this S3 bucket based on your workload's requirements, see [Planning a certificate revocation list (CRL)](https://docs.aws.amazon.com/privateca/latest/userguide/crl-planning.html).

## Resources
### Related Best Practices
- [SEC02-BP02 Use temporary credentials](sec_identities_unique.md)
- [SEC08-BP01 Implement secure key management](sec_protect_data_rest_key_mgmt.md)
- [SEC09-BP03 Authenticate network communications](sec_protect_data_transit_authentication.md)
### Related Documents
- [How to host and manage an entire private certificate infrastructure in AWS](https://aws.amazon.com/blogs/security/how-to-host-and-manage-an-entire-private-certificate-infrastructure-in-aws/)
- [How to secure an enterprise scale ACM Private CA hierarchy for automotive and manufacturing](https://aws.amazon.com/blogs/security/how-to-secure-an-enterprise-scale-acm-private-ca-hierarchy-for-automotive-and-manufacturing/)
- [Private CA best practices](https://docs.aws.amazon.com/privateca/latest/userguide/ca-best-practices.html)
- [How to use AWS RAM to share your ACM Private CA cross-account](https://aws.amazon.com/blogs/security/how-to-use-aws-ram-to-share-your-acm-private-ca-cross-account/)
### Related Videos
- [Activating AWS Certificate Manager Private CA (workshop)](https://www.youtube.com/watch?v=XrrdyplT3PE)
### Related Examples
- [Private CA workshop](https://catalog.workshops.aws/certificatemanager/en-US/introduction)
- [IOT Device Management Workshop](https://iot-device-management.workshop.aws/en/) (including device provisioning)
### Related Tools
- [Plugin to Kubernetes cert-manager to use AWS Private CA](https://github.com/cert-manager/aws-privateca-issuer)
