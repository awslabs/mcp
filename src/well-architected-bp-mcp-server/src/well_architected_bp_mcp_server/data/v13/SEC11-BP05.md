---
id: "SEC11-BP05"
title: "Centralize services for packages and dependencies"
framework: "WAF"
domain: "Security"
capability: "How do you incorporate and validate the security properties of applications throughout the design, development, and deployment lifecycle?"
risk_level: "Medium"
---

# SEC11-BP05 Centralize services for packages and dependencies

## Desired Outcome
You build your workload from external software packages in addition to the code that you write. This makes it simpler for you to implement functionality that is repeatedly used, such as a JSON parser or an encryption library. You centralize the sources for these packages and dependencies so your security team can validate them before they are used. You use this approach in conjunction with the manual and automated testing flows to increase the confidence in the quality of the software that you develop.

## Anti-Patterns
- You pull packages from arbitrary repositories on the internet.
- You don't test new packages before you make them available to builders.

## Implementation Guidance
 Provide centralized services for packages and dependencies in a way that is simple for builders to consume. Centralized services can be logically central rather than implemented as a monolithic system. This approach allows you to provide services in a way that meets the needs of your builders. You should implement an efficient way of adding packages to the repository when updates happen or new requirements emerge. AWS services such as [AWS CodeArtifact](https://aws.amazon.com/codeartifact/) or similar AWS partner solutions provide a way of delivering this capability.

## Implementation Steps
- Implement a logically centralized repository service that is available in all of the environments where software is developed.
- Include access to the repository as part of the AWS account vending process.
- Build automation to test packages before they are published in a repository.
- Maintain metrics of the most commonly used packages, languages, and teams with the highest amount of change.
- Provide an automated mechanism for builder teams to request new packages and provide feedback.
- Regularly scan packages in your repository to identify the potential impact of newly discovered issues.

## Resources
### Related Best Practices
- [SEC11-BP02 Automate testing throughout the development and release lifecycle](sec_appsec_automate_testing_throughout_lifecycle.md)
### Related Documents
- [ DevOps Guidance: DL.CS.2 Sign code artifacts after each build ](https://docs.aws.amazon.com/wellarchitected/latest/devops-guidance/dl.cs.2-sign-code-artifacts-after-each-build.html)
- [ Supply chain Levels for Software Artifacts (SLSA) ](https://slsa.dev/)
### Related Examples
- [Accelerate deployments on AWS with effective governance](https://aws.amazon.com/blogs/architecture/accelerate-deployments-on-aws-with-effective-governance/)
- [Tighten your package security with CodeArtifact Package Origin Control toolkit](https://aws.amazon.com/blogs/devops/tighten-your-package-security-with-codeartifact-package-origin-control-toolkit/)
- [Multi Region Package Publishing Pipeline](https://github.com/aws-samples/multi-region-python-package-publishing-pipeline) (GitHub)
- [Publishing Node.js Modules on AWS CodeArtifact using AWS CodePipeline](https://github.com/aws-samples/aws-codepipeline-publish-nodejs-modules) (GitHub)
- [AWS CDK Java CodeArtifact Pipeline Sample](https://github.com/aws-samples/aws-cdk-codeartifact-pipeline-sample) (GitHub)
- [Distribute private .NET NuGet packages with AWS CodeArtifact](https://github.com/aws-samples/aws-codeartifact-nuget-dotnet-pipelines) (GitHub)
### Related Videos
- [Proactive security: Considerations and approaches](https://www.youtube.com/watch?v=CBrUE6Qwfag)
- [The AWS Philosophy of Security (re:Invent 2017)](https://www.youtube.com/watch?v=KJiCfPXOW-U)
- [When security, safety, and urgency all matter: Handling Log4Shell](https://www.youtube.com/watch?v=pkPkm7W6rGg)
