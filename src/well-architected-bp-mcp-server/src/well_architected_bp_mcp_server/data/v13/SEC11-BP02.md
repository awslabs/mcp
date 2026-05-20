---
id: "SEC11-BP02"
title: "Automate testing throughout the development and release lifecycle"
framework: "WAF"
domain: "Security"
capability: "How do you incorporate and validate the security properties of applications throughout the design, development, and deployment lifecycle?"
risk_level: "Medium"
---

# SEC11-BP02 Automate testing throughout the development and release lifecycle

## Anti-Patterns
- Not communicating the test cases and test results of the automated testing.
- Performing the automated testing only immediately prior to a release.
- Automating test cases with frequently changing requirements.
- Failing to provide guidance on how to address the results of security tests.

## Implementation Guidance
As you build your software, adopt various mechanisms for software testing to ensure that you are testing your application for both functional requirements, based on your application’s business logic, and non-functional requirements, which are focused on application reliability, performance, and security.

 Static application security testing (SAST) analyzes your source code for anomalous security patterns, and provides indications for defect prone code. SAST relies on static inputs, such as documentation (requirements specification, design documentation, and design specifications) and application source code to test for a range of known security issues. Static code analyzers can help expedite the analysis of large volumes of code. The [NIST Quality Group](https://www.nist.gov/itl/ssd/software-quality-group) provides a comparison of [Source Code Security Analyzers](https://www.nist.gov/itl/ssd/software-quality-group/source-code-security-analyzers), which includes open source tools for [Byte Code Scanners](https://samate.nist.gov/index.php/Byte_Code_Scanners.html) and [Binary Code Scanners](https://samate.nist.gov/index.php/Binary_Code_Scanners.html).

 Complement your static testing with dynamic analysis security testing (DAST) methodologies, which performs tests against the running application to identify potentially unexpected behavior. Dynamic testing can be used to detect potential issues that are not detectable via static analysis. Testing at the code repository, build, and pipeline stages allows you to check for different types of potential issues from entering into your code. [Amazon Q Developers](https://aws.amazon.com/q/developer/) provides code recommendations, including security scanning, in the builder's IDE. [Amazon CodeGuru Security](https://aws.amazon.com/codeguru/) can identify critical issues, security issues, and hard-to-find bugs during application development, and provides recommendations to improve code quality. Extracting Software Bill of Materials (SBOM) also allows you to extract a formal record containing the details and relationships of the various components used in building your software. This allows you to inform vulnerability management, and quickly identify software or component dependencies and supply chain risks.

 The [Security for Developers workshop](https://catalog.workshops.aws/sec4devs) uses AWS developer tools, such as [AWS CodeBuild](https://aws.amazon.com/codebuild/), [AWS CodeCommit](https://aws.amazon.com/codecommit/), and [AWS CodePipeline](https://aws.amazon.com/codepipeline/), for release pipeline automation that includes SAST and DAST testing methodologies.

 As you progress through your SDLC, establish an iterative process that includes periodic application reviews with your security team. Feedback gathered from these security reviews should be addressed and validated as part of your release readiness review. These reviews establish a robust application security posture, and provide builders with actionable feedback to address potential issues.

## Implementation Steps
- Implement consistent IDE, code review, and CI/CD tools that include security testing.
- Consider where in the SDLC it is appropriate to block pipelines instead of just notifying builders that issues need to be remediated.
- [Automated Security Helper (ASH)](https://github.com/awslabs/automated-security-helper) is an example for open-source code security scanning tool.
- Performing testing or code analysis using automated tools, such as [Amazon Q Developer](https://aws.amazon.com/q/developer/) integrated with developer IDEs, and [Amazon CodeGuru Security](https://aws.amazon.com/codeguru/) for scanning code on commit, helps builders get feedback at the right time.
- When building using AWS Lambda, you can use [Amazon Inspector](https://docs.aws.amazon.com/inspector/latest/user/scanning-lambda.html) to scan the application code in your functions.
- When automated testing is included in CI/CD pipelines, you should use a ticketing system to track the notification and remediation of software issues.
- For security tests that might generate findings, linking to guidance for remediation helps builders improve code quality.
- Regularly analyze the findings from automated tools to prioritize the next automation, builder training, or awareness campaign.
- To extract SBOM as part of your CI/CD pipelines, use [Amazon Inspector SBOM Generator](https://docs.aws.amazon.com/inspector/latest/user/sbom-generator.html) to produce SBOMs for archives, container images, directories, local systems, and compiled Go and Rust binaries in the CycloneDX SBOM format.

## Resources
### Related Best Practices
- [DevOps Guidance: DL.CR.3 Establish clear completion criteria for code tasks](https://docs.aws.amazon.com/wellarchitected/latest/devops-guidance/dl.cr.3-establish-clear-completion-criteria-for-code-tasks.html)
### Related Documents
- [Continuous Delivery and Continuous Deployment](https://aws.amazon.com/devops/continuous-delivery/)
- [AWS DevOps Competency Partners](https://aws.amazon.com/devops/partner-solutions/?blog-posts-cards.sort-by=item.additionalFields.createdDate&blog-posts-cards.sort-order=desc&partner-solutions-cards.sort-by=item.additionalFields.partnerNameLower&partner-solutions-cards.sort-order=asc&awsf.partner-solutions-filter-partner-type=partner-type%23technology&awsf.Filter%20Name%3A%20partner-solutions-filter-partner-location=*all&awsf.partner-solutions-filter-partner-location=*all&partner-case-studies-cards.sort-by=item.additionalFields.sortDate&partner-case-studies-cards.sort-order=desc&awsm.page-partner-solutions-cards=1)
- [AWS Security Competency Partners for Application Security](https://aws.amazon.com/security/partner-solutions/?blog-posts-cards.sort-by=item.additionalFields.createdDate&blog-posts-cards.sort-order=desc&partner-solutions-cards.sort-by=item.additionalFields.partnerNameLower&partner-solutions-cards.sort-order=asc&awsf.partner-solutions-filter-partner-type=*all&awsf.Filter%20Name%3A%20partner-solutions-filter-partner-categories=use-case%23app-security&awsf.partner-solutions-filter-partner-location=*all&partner-case-studies-cards.sort-by=item.additionalFields.sortDate&partner-case-studies-cards.sort-order=desc&events-master-partner-webinars.sort-by=item.additionalFields.startDateTime&events-master-partner-webinars.sort-order=asc)
- [Choosing a Well-Architected CI/CD approach](https://aws.amazon.com/blogs/devops/choosing-well-architected-ci-cd-open-source-software-aws-services/)
- [Secrets detection in Amazon CodeGuru Security](https://docs.aws.amazon.com/codeguru/latest/reviewer-ug/recommendations.html#secrets-detection)
- [Amazon CodeGuru Security Detection Library](https://docs.aws.amazon.com/codeguru/detector-library/)
- [Accelerate deployments on AWS with effective governance](https://aws.amazon.com/blogs/architecture/accelerate-deployments-on-aws-with-effective-governance/)
- [How AWS approaches automating safe, hands-off deployments](https://aws.amazon.com/builders-library/automating-safe-hands-off-deployments/)
- [How Amazon CodeGuru Security helps you effectively balance security and velocity](https://aws.amazon.com/blogs/security/how_amazon_codeguru_security_helps_effectively_balance_security_and_velocity/)
### Related Videos
- [Hands-off: Automating continuous delivery pipelines at Amazon](https://www.youtube.com/watch?v=ngnMj1zbMPY)
- [Automating cross-account CI/CD pipelines](https://www.youtube.com/watch?v=AF-pSRSGNks)
- [The Software Development Prcess at Amazon](https://www.youtube.com/watch?t=1340&v=52SC80SFPOw&feature=youtu.be)
- [Testing software and systems at Amazon](https://www.youtube.com/watch?v=o1sc3cK9bMU&t)
### Related Examples
- [Industry awareness for developers](https://owasp.org/www-project-top-ten/)
- [Automated Security Helper (ASH)](https://github.com/awslabs/automated-security-helper)
- [AWS CodePipeline Governance - Github](https://github.com/awslabs/aws-codepipeline-governance)
