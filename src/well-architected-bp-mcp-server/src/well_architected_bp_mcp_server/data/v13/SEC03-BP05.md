---
id: "SEC03-BP05"
title: "Define permission guardrails for your organization"
framework: "WAF"
domain: "Security"
capability: "How do you manage permissions for people and machines?"
risk_level: "Medium"
---

# SEC03-BP05 Define permission guardrails for your organization

## Desired Outcome
You have clear isolation of environments using separate AWS accounts.  Service control policies (SCPs) are used to define organization-wide permission guardrails. Broader guardrails are set at the hierarchy levels closest to your organization root, and more strict guardrails are set closer to the level of individual accounts.

 Where supported, resource policies define the conditions that a principal must satisfy to gain access to a resource. Resource policies also scope down the set of allowable actions, where appropriate. Permission boundaries are placed on principals that manage workload permissions, delegating permission management to individual workload owners.

## Anti-Patterns
- Creating member AWS accounts within an [AWS Organization](https://aws.amazon.com/organizations/), but not using SCPs to restrict the use and permissions available to their root credentials.
- Assigning permissions based on least privilege, but not placing guardrails on the maximum set of permissions that can be granted.
- Relying on the *implicit deny* foundation of AWS IAM to restrict permissions, trusting that policies will not grant an undesired *explicit allow* permission.
- Running multiple workload environments in the same AWS account, and then relying on mechanisms such as VPCs, tags, or resource policies to enforce permission boundaries.

## Implementation Guidance
 We recommend you use a layer-based approach to define permission guardrails for your organization. This approach systematically reduces the maximum set of possible permissions as additional layers are applied. This helps you grant access based on the principle of least privilege, reducing the risk of unintended access due to policy misconfiguration.

 The first step to establish permission guardrails is to isolate your workloads and environments into separate AWS accounts. Principals from one account cannot access resources in another account without explicit permission to do so, even when both accounts are in the same AWS organization or under the same [organizational unit (OU)](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_ous.html). You can use OUs to group accounts you want to administer as a single unit.

 The next step is to reduce the maximum set of permissions that you can grant to principals within the member accounts of your organization. You can use [service control policies (SCPs)](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html) for this purpose, which you can apply to either an OU or an account. SCPs can enforce common access controls, such as restricting access to specific AWS Regions, help prevent resources from being deleted, or disabling potentially risky service actions. SCPs that you apply to the root of your organization only affect its member accounts, not the management account.  SCPs only govern the principals within your organization. Your SCPs don't govern principals outside your organization that are accessing your resources.

 If you are using [AWS Control Tower](https://docs.aws.amazon.com/controltower/latest/userguide/what-is-control-tower.html), you can leverage its [controls](https://docs.aws.amazon.com/controltower/latest/userguide/how-control-tower-works.html#how-controls-work) and [landing zones](https://docs.aws.amazon.com/controltower/latest/userguide/aws-multi-account-landing-zone.html) as the foundation for your permission guardrails and multi-account environment. The landing zones provide a pre-configured, secure baseline environment with separate accounts for different workloads and applications. The guardrails enforce mandatory controls around security, operations, and compliance through a combination of Service Control Policies (SCPs), AWS Config rules, and other configurations. However, when using Control Tower guardrails and landing zones alongside custom Organization SCPs, it's crucial to follow the best practices outlined in the AWS documentation to avoid conflicts and ensure proper governance. Refer to the [AWS Control Tower guidance for AWS Organizations](https://docs.aws.amazon.com/controltower/latest/userguide/orgs-guidance.html) for detailed recommendations on managing SCPs, accounts, and organizational units (OUs) within a Control Tower environment.

 By adhering to these guidelines, you can effectively leverage Control Tower's guardrails, landing zones, and custom SCPs while mitigating potential conflicts and ensuring proper governance and control over your multi-account AWS environment.

 A further step is to use [IAM resource policies](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies.html#policies_resource-based) to scope the available actions that you can take on the resources they govern, along with any conditions that the acting principal must meet. This can be as broad as allowing all actions so long as the principal is part of your organization (using the PrincipalOrgId [condition key](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html)), or as granular as only allowing specific actions by a specific IAM role. You can take a similar approach with conditions in IAM role trust policies.  If a resource or role trust policy explicitly names a principal in the same account as the role or resource it governs, that principal does not need an attached IAM policy that grants the same permissions.  If the principal is in a different account from the resource, then the principal does need an attached IAM policy that grants those permissions.

 Often, a workload team will want to manage the permissions their workload requires.  This may require them to create new IAM roles and permission policies.  You can capture the maximum scope of permissions the team is allowed to grant in an [IAM permission boundary](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_boundaries.html), and associate this document to an IAM role the team can then use to manage their IAM roles and permissions.  This approach can provide them the flexibility to complete their work while mitigating risks of having IAM administrative access.

 A more granular step is to implement *privileged access management* (PAM) and *temporary elevated access management* (TEAM) techniques.  One example of PAM is to require principals to perform multi-factor authentication before taking privileged actions.  For more information, see [Configuring MFA-protected API access](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_mfa_configure-api-require.html). TEAM requires a solution that manages the approval and timeframe that a principal is allowed to have elevated access.  One approach is to temporarily add the principal to the role trust policy for an IAM role that has elevated access.  Another approach is to, under normal operation, scope down the permissions granted to a principal by an IAM role using a [session policy](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies.html#policies_session), and then temporarily lift this restriction during the approved time window. To learn more about solutions that AWS and select partners validated, see [Temporary elevated access](https://docs.aws.amazon.com/singlesignon/latest/userguide/temporary-elevated-access.html).

## Implementation Steps
1.  Isolate your workloads and environments into separate AWS accounts.

1.  Use SCPs to reduce the maximum set of permissions that can be granted to principals within the member accounts of your organization.

   1.  When defining SCPs to reduce the maximum set of permissions that can be granted to principals within your organization's member accounts, you can choose between an *allow list* or *deny list* approach. The allow list strategy explicitly specifies the access that is allowed and implicitly blocks all other access. The deny list strategy explicitly specifies the access that isn't allowed and allows all other access by default. Both strategies have their advantages and trade-offs, and the appropriate choice depends on your organization's specific requirements and risk model. For more detail, see [Strategy for using SCPs](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps_strategies.html).

   1.  Additionally, review the [service control policy examples](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps_examples.html) to understand how to construct SCPs effectively.

1.  Use IAM resource policies to scope down and specify conditions for permitted actions on resources.  Use conditions in IAM role trust policies to create restrictions on assuming roles.

1.  Assign IAM permission boundaries to IAM roles that workload teams can then use to manage their own workload IAM roles and permissions.

1.  Evaluate PAM and TEAM solutions based on your needs.

## Resources
### Related Documents
- [Data perimeters on AWS](https://aws.amazon.com/identity/data-perimeters-on-aws/)
- [Establish permissions guardrails using data perimeters](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_data-perimeters.html)
- [Policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)
### Related Examples
- [Service control policy examples](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps_examples.html)
### Related Tools
- [AWS Solution: Temporary Elevated Access Management](https://aws-samples.github.io/iam-identity-center-team/)
- [Validated security partner solutions for TEAM](https://docs.aws.amazon.com/singlesignon/latest/userguide/temporary-elevated-access.html#validatedpartners)
