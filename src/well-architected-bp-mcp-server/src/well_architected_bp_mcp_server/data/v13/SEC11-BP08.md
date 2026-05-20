---
id: "SEC11-BP08"
title: "Build a program that embeds security ownership in workload teams"
framework: "WAF"
domain: "Security"
capability: "How do you incorporate and validate the security properties of applications throughout the design, development, and deployment lifecycle?"
risk_level: "Low"
---

# SEC11-BP08 Build a program that embeds security ownership in workload teams

## Desired Outcome
You have embedded security ownership and decision-making in your teams. You have either trained your teams on how to think about security or have augmented their team with embedded or associated security people. Your teams make higher-quality security decisions earlier in the development cycle as a result.

## Anti-Patterns
- Leaving all security design decisions to a security team.
- Not addressing security requirements early enough in the development process.
- Not obtaining feedback from builders and security people on the operation of the program.

## Implementation Guidance
 Start with the guidance in [SEC11-BP01 Train for application security](sec_appsec_train_for_application_security.md). Then identify the operational model for the program that you think might work best for your organization. The two main patterns are to train builders or to embed security people in builder teams. After you have decided on the initial approach, you should pilot with a single or small group of workload teams to prove the model works for your organization. Leadership support from the builder and security parts of the organization helps with the delivery and success of the program. As you build this program, it’s important to choose metrics that can be used to show the value of the program. Learning from how AWS has approached this problem is a good learning experience. This best practice is very much focused on organizational change and culture. The tools that you use should support the collaboration between the builder and security communities.

## Implementation Steps
- Start by training your builders for application security.
- Create a community and an onboarding program to educate builders.
- Pick a name for the program. Guardians, Champions, or Advocates are commonly used.
- Identify the model to use: train builders, embed security engineers, or have affinity security roles.
- Identify project sponsors from security, builders, and potentially other relevant groups.
- Track metrics for the number of people involved in the program, the time taken for reviews, and the feedback from builders and security people. Use these metrics to make improvements.

## Resources
### Related Best Practices
- [SEC11-BP01 Train for application security](sec_appsec_train_for_application_security.md)
- [SEC11-BP02 Automate testing throughout the development and release lifecycle](sec_appsec_automate_testing_throughout_lifecycle.md)
### Related Documents
- [How to approach threat modeling](https://aws.amazon.com/blogs/security/how-to-approach-threat-modeling/)
- [How to think about cloud security governance](https://aws.amazon.com/blogs/security/how-to-think-about-cloud-security-governance/)
- [How AWS built the Security Guardians program, a mechanism to distribute security ownership](https://aws.amazon.com/blogs/security/how-aws-built-the-security-guardians-program-a-mechanism-to-distribute-security-ownership/)
- [ How to build a Security Guardians program to distribute security ownership ](https://aws.amazon.com/blogs/security/how-to-build-your-own-security-guardians-program/)
### Related Videos
- [Proactive security: Considerations and approaches](https://www.youtube.com/watch?v=CBrUE6Qwfag)
- [AppSec tooling and culture tips from AWS and Toyota Motor North America](https://www.youtube.com/watch?v=aznmbzgj6Mg)
