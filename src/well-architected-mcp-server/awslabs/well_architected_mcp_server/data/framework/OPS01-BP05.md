---
id: "OPS01-BP05"
title: "Evaluate threat landscape"
pillar: "Operational Excellence"
risk_level: "MEDIUM"
capability: "How do you determine what your priorities are?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_priorities_eval_threat_landscape.html"
---

# OPS01-BP05 Evaluate threat landscape

Evaluate threats to the business (for example, competition, business
risk and liabilities, operational risks, and information security
threats) and maintain current information in a risk registry.
Include the impact of risks when determining where to focus efforts.

The
[Well-Architected
Framework](https://aws.amazon.com/architecture/well-architected/) emphasizes learning, measuring, and improving. It
provides a consistent approach for you to evaluate architectures,
and implement designs that will scale over time. AWS provides the
[AWS Well-Architected Tool](https://aws.amazon.com/well-architected-tool/) to help you review your approach prior
to development, the state of your workloads prior to production, and
the state of your workloads in production. You can compare them to
the latest AWS architectural best practices, monitor the overall
status of your workloads, and gain insight to potential risks.

AWS customers are eligible for a guided Well-Architected Review of
their mission-critical workloads to
[measure
their architectures](https://aws.amazon.com/premiumsupport/programs/) against AWS best practices. Enterprise
Support customers are eligible for an
[Operations
Review](https://aws.amazon.com/premiumsupport/programs/), designed to help them to identify gaps in their
approach to operating in the cloud.

The cross-team engagement of these reviews helps to establish common
understanding of your workloads and how team roles contribute to
success. The needs identified through the review can help shape your
priorities.

[AWS Trusted Advisor](https://aws.amazon.com/premiumsupport/technology/trusted-advisor/) is a tool that provides access to a core set
of checks that recommend optimizations that may help shape your
priorities.
[Business
and Enterprise Support customers](https://aws.amazon.com/premiumsupport/plans/) receive access to additional
checks focusing on security, reliability, performance, and
cost-optimization that can further help shape their priorities.

**Desired outcome:**

- You regularly
review and act on Well-Architected and Trusted Advisor outputs
- You are aware of the latest patch status of your services
- You understand the risk and impact of known threats and act
accordingly
- You implement mitigations as necessary
- You communicate actions and context

**Common anti-patterns:**

- You are
using an old version of a software library in your product. You are
unaware of security updates to the library for issues that may have
unintended impact on your workload.
- Your competitor just released a version of their product that
addresses many of your customers' complaints about your product.
You have not prioritized addressing any of these known issues.
- Regulators have been pursuing companies like yours that are not
compliant with legal regulatory compliance requirements. You
have not prioritized addressing any of your outstanding
compliance requirements.

**Benefits of establishing this best practice:** You identify and understand the threats to your
organization and workload, which helps your determination of which
threats to address, their priority, and the resources necessary to
do so.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

- **Evaluate threat landscape:**
Evaluate threats to the business (for example, competition,
business risk and liabilities, operational risks, and
information security threats), so that you can include their
impact when determining where to focus efforts.

[AWS Latest Security Bulletins](https://aws.amazon.com/security/security-bulletins/)
- [AWS Trusted Advisor](https://aws.amazon.com/premiumsupport/trustedadvisor/)

- **Maintain a threat model:**
Establish and maintain a threat model identifying potential
threats, planned and in place mitigations, and their priority.
Review the probability of threats manifesting as incidents,
the cost to recover from those incidents and the expected harm
caused, and the cost to prevent those incidents. Revise
priorities as the contents of the threat model change.

## Resources

**Related best practice:**

- [SEC01-BP07
Identify threats and prioritize mitigations using a threat
model](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_securely_operate_threat_model.html)

**Related documents:**

- [AWS Cloud
Compliance](https://aws.amazon.com/compliance/)
- [AWS Latest Security Bulletins](https://aws.amazon.com/security/security-bulletins/)
- [AWS Trusted Advisor](https://aws.amazon.com/premiumsupport/trustedadvisor/)

**Related videos:**

- [AWS re:Inforce 2023 - A tool to help improve your threat
modeling](https://youtu.be/CaYCsmjuiHg?si=e_CXPGqRF4WeBr1u)
