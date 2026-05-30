---
id: "SEC06-BP04"
title: "Validate software integrity"
framework: "WAF"
domain: "Security"
capability: "How do you protect your compute resources?"
risk_level: "Medium"
---

# SEC06-BP04 Validate software integrity

## Desired Outcome
All artifacts are obtained from trusted sources. Vendor website certificates are validated.  Downloaded artifacts are cryptographically verified by their signatures. Your own software is cryptographically signed and verified by your computing environments.

## Anti-Patterns
- Trusting reputable vendor websites to obtain software artifacts, but ignoring certificate expiration notices.  Proceeding with downloads without confirming certificates are valid.
- Validating vendor website certificates, but not cryptographically verifying downloaded artifacts from these websites.
- Relying solely on digests or hashes to validate software integrity.  Hashes establish that artifacts have not been modified from the original version, but do not validate their source.
- Not signing your own software, code, or libraries, even when only used in your own deployments.

## Implementation Guidance
 Operating system images, container images, and code artifacts are often distributed with integrity checks available, such as through a digest or hash.  These allow clients to verify integrity by computing their own hash of the payload and validating it is the same as the one published.  While these checks help verify that the payload has not been tampered with, they do not validate the payload came from the original source (its *provenance*).  Verifying provenance requires a certificate that a trusted authority issues to digitally sign the artifact.

 If you are using a downloaded software or artifacts in your workload, check if the provider provides a public key for digital signature verification.  Here are some examples of how AWS provides a public key and verification instructions for software we publish:
- [EC2 Image Builder: Verify the signature of the AWSTOE installation download](https://docs.aws.amazon.com/imagebuilder/latest/userguide/awstoe-verify-sig.html)
- [AWS Systems Manager: Verifying the signature of SSM Agent](https://docs.aws.amazon.com/systems-manager/latest/userguide/verify-agent-signature.html)
- [Amazon CloudWatch: Verifying the signature of the CloudWatch agent package](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/verify-CloudWatch-Agent-Package-Signature.html)

 Incorporate digital signature verification into the processes you use for obtaining and hardening images, as discussed in [SEC06-BP02 Provision compute from hardened images](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_protect_compute_hardened_images.html).

 You can use [AWS Signer](https://docs.aws.amazon.com/signer/latest/developerguide/Welcome.html) to help manage the verification of signatures, as well as your own code-signing lifecycle for your own software and artifacts.  Both [AWS Lambda](https://aws.amazon.com/lambda/) and [Amazon Elastic Container Registry](https://aws.amazon.com/ecr/) provide integrations with Signer to verify the signatures of your code and images.  Using the examples in the Resources section, you can incorporate Signer into your continuous integration and delivery (CI/CD) pipelines to automate verification of signatures and the signing of your own code and images.

## Resources
### Related Documents
- [Cryptographic Signing for Containers](https://aws.amazon.com/blogs/containers/cryptographic-signing-for-containers/)
- [Best Practices to help secure your container image build pipeline by using AWS Signer](https://aws.amazon.com/blogs/security/best-practices-to-help-secure-your-container-image-build-pipeline-by-using-aws-signer/)
- [Announcing Container Image Signing with AWS Signer and Amazon EKS](https://aws.amazon.com/blogs/containers/announcing-container-image-signing-with-aws-signer-and-amazon-eks/)
- [Configuring code signing for AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/configuration-codesigning.html)
- [Best practices and advanced patterns for Lambda code signing](https://aws.amazon.com/blogs/security/best-practices-and-advanced-patterns-for-lambda-code-signing/)
- [Code signing using AWS Certificate Manager Private CA and AWS Key Management Service asymmetric keys](https://aws.amazon.com/blogs/security/code-signing-aws-certificate-manager-private-ca-aws-key-management-service-asymmetric-keys/)
### Related Examples
- [Automate Lambda code signing with Amazon CodeCatalyst and AWS Signer](https://aws.amazon.com/blogs/devops/automate-lambda-code-signing-with-amazon-codecatalyst-and-aws-signer/)
- [Signing and Validating OCI Artifacts with AWS Signer](https://aws.amazon.com/blogs/containers/signing-and-validating-oci-artifacts-with-aws-signer/)
### Related Tools
- [AWS Lambda](https://aws.amazon.com/lambda/)
- [AWS Signer](https://docs.aws.amazon.com/signer/latest/developerguide/Welcome.html)
- [AWS Certificate Manager](https://aws.amazon.com/certificate-manager/)
- [AWS Key Management Service](https://aws.amazon.com/kms/)
- [AWS CodeArtifact](https://aws.amazon.com/codeartifact/)
