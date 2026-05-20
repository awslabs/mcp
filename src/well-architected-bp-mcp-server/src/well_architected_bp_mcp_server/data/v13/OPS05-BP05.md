---
id: "OPS05-BP05"
title: "Perform patch management"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you reduce defects, ease remediation, and improve flow into production?"
risk_level: "Medium"
---

# OPS05-BP05 Perform patch management

## Desired Outcome
Your AMI and container images are patched, up-to-date, and ready for launch. You are able to track the status of all deployed images and know patch compliance. You are able to report on current status and have a process to meet your compliance needs.

## Anti-Patterns
- You are given a mandate to apply all new security patches within two hours resulting in multiple outages due to application incompatibility with patches.
- An unpatched library results in unintended consequences as unknown parties use vulnerabilities within it to access your workload.
- You patch the developer environments automatically without notifying the developers. You receive multiple complaints from the developers that their environment cease to operate as expected.
- You have not patched the commercial off-the-shelf software on a persistent instance. When you have an issue with the software and contact the vendor, they notify you that version is not supported and you have to patch to a specific level to receive any assistance.
- A recently released patch for the encryption software you used has significant performance improvements. Your unpatched system has performance issues that remain in place as a result of not patching.
- You are notified of a zero-day vulnerability requiring an emergency fix and you have to patch all your environments manually.
- You are not aware of critical actions needed to maintain your resources, such as mandatory version updates because you do not review upcoming planned lifecycle events and other information. You lose critical time for planning and execution, resulting in emergency changes for your teams and potential impact or unexpected downtime.

## Implementation Guidance
 Patch systems to remediate issues, to gain desired features or capabilities, and to remain compliant with governance policy and vendor support requirements. In immutable systems, deploy with the appropriate patch set to achieve the desired result. Automate the patch management mechanism to reduce the elapsed time to patch, to avoid errors caused by manual processes, and lower the level of effort to patch.

## Implementation Steps
 For Amazon EC2 Image Builder:

1.  Using Amazon EC2 Image Builder, specify pipeline details:

   1.  Create an image pipeline and name it

   1.  Define pipeline schedule and time zone

   1.  Configure any dependencies

1.  Choose a recipe:

   1.  Select existing recipe or create a new one

   1.  Select image type

   1.  Name and version your recipe

   1.  Select your base image

   1.  Add build components and add to target registry

1.  Optional - define your infrastructure configuration.

1.  Optional - define configuration settings.

1.  Review settings.

1.  Maintain recipe hygiene regularly.

 For Systems Manager Patch Manager:

1.  Create a patch baseline.

1.  Select a patching operations method.

1.  Enable compliance reporting and scanning.

## Resources
### Related Best Practices
- [OPS06-BP04 Automate testing and rollback](ops_mit_deploy_risks_auto_testing_and_rollback.md)
### Related Documents
- [ What is Amazon EC2 Image Builder ](https://docs.aws.amazon.com/imagebuilder/latest/userguide/what-is-image-builder.html)
- [ Create an image pipeline using the Amazon EC2 Image Builder ](https://docs.aws.amazon.com/imagebuilder/latest/userguide/start-build-image-pipeline.html)
- [ Create a container image pipeline ](https://docs.aws.amazon.com/imagebuilder/latest/userguide/start-build-container-pipeline.html)
- [AWS Systems Manager Patch Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-patch.html)
- [ Working with Patch Manager ](https://docs.aws.amazon.com/systems-manager/latest/userguide/patch-manager-console.html)
- [ Working with patch compliance reports ](https://docs.aws.amazon.com/systems-manager/latest/userguide/patch-manager-compliance-reports.html)
- [AWS Developer Tools ](https://aws.amazon.com/products/developer-tools)
### Related Videos
- [CI/CD for Serverless Applications on AWS](https://www.youtube.com/watch?v=tEpx5VaW4WE)
- [Design with Ops in Mind](https://youtu.be/uh19jfW7hw4)
### Related Examples
- [AWS Systems Manager Patch Manager tutorials ](https://docs.aws.amazon.com/systems-manager/latest/userguide/patch-manager-tutorials.html)
