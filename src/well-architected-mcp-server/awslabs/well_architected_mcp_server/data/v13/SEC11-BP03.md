---
id: "SEC11-BP03"
title: "Perform regular penetration testing"
framework: "WAF"
domain: "Security"
capability: "How do you incorporate and validate the security properties of applications throughout the design, development, and deployment lifecycle?"
risk_level: "High"
---

# SEC11-BP03 Perform regular penetration testing

## Desired Outcome
Penetration testing is used to detect, remediate, and validate your application’s security properties. Regular and scheduled penetration testing should be performed as part of the software development lifecycle (SDLC). The findings from penetration tests should be addressed prior to the software being released. You should analyze the findings from penetration tests to identify if there are issues that could be found using automation. Having a regular and repeatable penetration testing process that includes an active feedback mechanism helps inform the guidance to builders and improves software quality.

## Anti-Patterns
- Only penetration testing for known or prevalent security issues.
- Penetration testing applications without dependent third-party tools and libraries.
- Only penetration testing for package security issues, and not evaluating implemented business logic.

## Implementation Guidance
 Penetration testing is a structured security testing exercise where you run planned security breach scenarios to detect, remediate, and validate security controls. Penetration tests start with reconnaissance, during which data is gathered based on the current design of the application and its dependencies. A curated list of security-specific testing scenarios are built and run. The key purpose of these tests is to uncover security issues in your application, which could be exploited for gaining unintended access to your environment, or unauthorized access to data. You should perform penetration testing when you launch new features, or whenever your application has undergone major changes in function or technical implementation.

 You should identify the most appropriate stage in the development lifecycle to perform penetration testing. This testing should happen late enough that the functionality of the system is close to the intended release state, but with enough time remaining for any issues to be remediated.

## Implementation Steps
- Have a structured process for how penetration testing is scoped, basing this process on the [threat model](https://aws.amazon.com/blogs/security/how-to-approach-threat-modeling/) is a good way of maintaining context.
- Identify the appropriate place in the development cycle to perform penetration testing. This should be when there is minimal change expected in the application, but with enough time to perform remediation.
- Train your builders on what to expect from penetration testing findings, and how to get information on remediation.
- Use tools to speed up the penetration testing process by automating common or repeatable tests.
- Analyze penetration testing findings to identify systemic security issues, and use this data to inform additional automated testing and ongoing builder education.

## Resources
### Related Best Practices
- [SEC11-BP01 Train for application security](sec_appsec_train_for_application_security.md)
- [SEC11-BP02 Automate testing throughout the development and release lifecycle](sec_appsec_automate_testing_throughout_lifecycle.md)
### Related Documents
- [AWS Penetration Testing](https://aws.amazon.com/security/penetration-testing/) provides detailed guidance for penetration testing on AWS
- [Accelerate deployments on AWS with effective governance](https://aws.amazon.com/blogs/architecture/accelerate-deployments-on-aws-with-effective-governance/)
- [AWS Security Competency Partners](https://aws.amazon.com/security/partner-solutions/?blog-posts-cards.sort-by=item.additionalFields.createdDate&blog-posts-cards.sort-order=desc&partner-solutions-cards.sort-by=item.additionalFields.partnerNameLower&partner-solutions-cards.sort-order=asc&awsf.partner-solutions-filter-partner-type=*all&awsf.Filter%20Name%3A%20partner-solutions-filter-partner-categories=*all&awsf.partner-solutions-filter-partner-location=*all&partner-case-studies-cards.sort-by=item.additionalFields.sortDate&partner-case-studies-cards.sort-order=desc&events-master-partner-webinars.sort-by=item.additionalFields.startDateTime&events-master-partner-webinars.sort-order=asc)
- [Modernize your penetration testing architecture on AWS Fargate](https://aws.amazon.com/blogs/architecture/modernize-your-penetration-testing-architecture-on-aws-fargate/)
- [AWS Fault injection Simulator](https://aws.amazon.com/fis/)
### Related Examples
- [Automate API testing with AWS CodePipeline](https://github.com/aws-samples/aws-codepipeline-codebuild-with-postman) (GitHub)
- [Automated security helper](https://github.com/aws-samples/automated-security-helper) (GitHub)
