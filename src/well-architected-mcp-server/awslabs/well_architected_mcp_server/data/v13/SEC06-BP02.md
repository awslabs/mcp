---
id: "SEC06-BP02"
title: "Provision compute from hardened images"
framework: "WAF"
domain: "Security"
capability: "How do you protect your compute resources?"
risk_level: "High"
---

# SEC06-BP02 Provision compute from hardened images

## Desired Outcome
Your compute resources are provisioned from hardened baseline images. You retrieve external dependencies, such as container images and application libraries, only from trusted registries and verify their signatures. These are stored in private registries for your build and deployment processes to reference. You scan and update images and dependencies regularly to help protect against any newly discovered vulnerabilities.

## Anti-Patterns
- Acquiring images and libraries from trusted registries, but not verifying their signature or performing vulnerability scans before putting into use.
- Hardening images, but not regularly testing them for new vulnerabilities or updating to the latest version.
- Installing or not removing software packages that are not required during the expected lifecycle of the image.
- Relying solely on patching to keep production compute resources up to date. Patching alone can still cause compute resources to drift from the hardened standard over time. Patching can also fail to remove malware that may have been installed by a threat actor during a security event.

## Implementation Guidance
 To harden your systems, start from the latest versions of operating systems, container images, and application libraries. Apply patches to known issues. Minimize the system by removing any unneeded applications, services, device drivers, default users, and other credentials. Take any other needed actions, such as disabling ports to create an environment that has only the resources and capabilities needed by your workloads. From this baseline, you can then install software, agents, or other processes you need for purposes such as workload monitoring or vulnerability management.

 You can reduce the burden of hardening systems by using guidance that trusted sources provide, such as the [Center for Internet Security](https://www.cisecurity.org/) (CIS) and the Defense Information Systems Agency (DISA) [Security Technical Implementation Guides (STIGs)](https://public.cyber.mil/stigs/). We recommend you start with an [Amazon Machine Image](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/AMIs.html) (AMI) published by AWS or an APN partner, and use the AWS [EC2 Image Builder](https://aws.amazon.com/image-builder/) to automate configuration according to an appropriate combination of CIS and STIG controls.

 While there are available hardened images and EC2 Image Builder recipes that apply the CIS or DISA STIG recommendations, you may find their configuration prevents your software from running successfully. In this situation, you can start from a non-hardened base image, install your software, and then incrementally apply CIS controls to test their impact. For any CIS control that prevents your software from running, test if you can implement the finer-grained hardening recommendations in a DISA instead. Keep track of the different CIS controls and DISA STIG configurations you are able to apply successfully. Use these to define your image hardening recipes in EC2 Image Builder accordingly.

 For containerized workloads, hardened images from Docker are available on the [Amazon Elastic Container Registry (ECR)](https://aws.amazon.com/ecr/) [public repository](https://gallery.ecr.aws/docker). You can use EC2 Image Builder to harden container images alongside AMIs.

 Similar to operating systems and container images, you can obtain code packages (or *libraries*) from public repositories, through tooling such as pip, npm, Maven, and NuGet. We recommend you manage code packages by integrating private repositories, such as within [AWS CodeArtifact](https://aws.amazon.com/codeartifact/), with trusted public repositories. This integration can handle retrieving, storing, and keeping packages up-to-date for you. Your application build processes can then obtain and test the latest version of these packages alongside your application, using techniques like Software Composition Analysis (SCA), Static Application Security Testing (SAST), and Dynamic Application Security Testing (DAST).

 For serverless workloads that use AWS Lambda, simplify managing package dependencies using [Lambda layers.](https://docs.aws.amazon.com/lambda/latest/dg/chapter-layers.html) Use Lambda layers to configure a set of standard dependencies that are shared across different functions into a standalone archive. You can create and maintain layers through their own build process, providing a central way for your functions to stay up-to-date.

## Implementation Steps
- Harden operating systems. Use base images from trusted sources as a foundation for building your hardened AMIs. Use [EC2 Image Builder](https://aws.amazon.com/image-builder/) to help customize the software installed on your images.
- Harden containerized resources. Configure containerized resources to meet security best practices. When using containers, implement [ECR Image Scanning](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-scanning.html) in your build pipeline and on a regular basis against your image repository to look for CVEs in your containers.
- When using serverless implementation with AWS Lambda, use [Lambda layers](https://docs.aws.amazon.com/lambda/latest/dg/chapter-layers.html) to segregate application function code and shared dependent libraries. Configure [code signing](https://docs.aws.amazon.com/lambda/latest/dg/configuration-codesigning.html) for Lambda to make sure that only trusted code runs in your Lambda functions.

## Resources
### Related Best Practices
- [OPS05-BP05 Perform patch management](https://docs.aws.amazon.com/wellarchitected/latest/framework/ops_dev_integ_patch_mgmt.html)
### Related Videos
- [Deep dive into AWS Lambda security](https://www.youtube.com/watch?v=FTwsMYXWGB0)
### Related Examples
- [Quickly build STIG-compliant AMI using EC2 Image Builder](https://aws.amazon.com/blogs/security/quickly-build-stig-compliant-amazon-machine-images-using-amazon-ec2-image-builder/)
- [Building better container images](https://aws.amazon.com/blogs/containers/building-better-container-images/)
- [Using Lambda layers to simplify your development process](https://aws.amazon.com/blogs/compute/using-lambda-layers-to-simplify-your-development-process/)
- [Develop & Deploy AWS Lambda Layers using Serverless Framework](https://github.com/aws-samples/aws-serverless-lambda-layers)
- [Building end-to-end AWS DevSecOps CI/CD pipeline with open source SCA, SAST and DAST tools](https://aws.amazon.com/blogs/devops/building-end-to-end-aws-devsecops-ci-cd-pipeline-with-open-source-sca-sast-and-dast-tools/)
