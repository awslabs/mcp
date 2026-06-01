---
id: "OPS06-BP01"
title: "Plan for unsuccessful changes"
pillar: "Operational Excellence"
risk_level: "HIGH"
capability: "How do you mitigate deployment risks?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_mit_deploy_risks_plan_for_unsucessful_changes.html"
description: "Plan to revert to a known good state, or remediate in the production environment if the deployment causes an undesired outcome. Having a policy to establish such a plan helps all teams develop strategies to recover from failed changes. Some example strategies are deployment and rollback steps, change policies, feature flags, traffic isolation, and traffic shifting. A single release may include multiple related component changes. The strategy should provide the ability to withstand or recover from a failure of any component change."
area: ["Prepare", "Mitigate deployment risks"]
relatedIds: ["OPS06-BP04"]
---

# OPS06-BP01 Plan for unsuccessful changes

Plan to revert to a known good state, or remediate in the production environment if the deployment causes an undesired outcome. Having a policy to establish such a plan helps all teams develop strategies to recover from failed changes. Some example strategies are deployment and rollback steps, change policies, feature flags, traffic isolation, and traffic shifting. A single release may include multiple related component changes. The strategy should provide the ability to withstand or recover from a failure of any component change.

**Desired outcome:** You have prepared a detailed recovery plan for your change in the event it is unsuccessful. In addition, you have reduced the size of your release to minimize the potential impact on other workload components. As a result, you have reduced your business impact by shortening the potential downtime caused by a failed change and increased the flexibility and efficiency of recovery times.

**Common anti-patterns:**

- You performed a deployment and your application has become unstable but there appear to be active users on the system. You have to decide whether to rollback the change and impact the active users or wait to rollback the change knowing the users may be impacted regardless.
- After making a routine change, your new environments are accessible, but one of your subnets has become unreachable. You have to decide whether to rollback everything or try to fix the inaccessible subnet. While you are making that determination, the subnet remains unreachable.
- Your systems are not architected in a way that allows them to be updated with smaller releases. As a result, you have difficulty in reversing those bulk changes during a failed deployment.
- You do not use infrastructure as code (IaC) and you made manual updates to your infrastructure that resulted in an undesired configuration. You are unable to effectively track and revert the manual changes.
- Because you have not measured increased frequency of your deployments, your team is not incentivized to reduce the size of their changes and improve their rollback plans for each change, leading to more risk and increased failure rates.
- You do not measure the total duration of an outage caused by unsuccessful changes. Your team is unable to prioritize and improve its deployment process and recovery plan effectiveness.

**Benefits of establishing this best
practice:** Having a plan to recover from unsuccessful changes minimizes the mean time to recover (MTTR) and reduces your business impact.

**Level of risk exposed if this best practice
is not established:** High

## Implementation guidance

A consistent, documented policy and practice adopted by release teams allows an organization to plan what should happen if unsuccessful changes occur. The policy should allow for fixing forward in specific circumstances. In either situation, a fix forward or rollback plan should be well documented and tested before deployment to live production so that the time it takes to revert a change is minimized.

### Implementation steps

- Document the policies that require teams to have effective plans to reverse changes within a specified period.

Policies should specify when a fix-forward situation is allowed.
- Require a documented rollback plan to be accessible by all involved.
- Specify the requirements to rollback (for example, when it is found that unauthorized changes have been deployed).

- Analyze the level of impact of all changes related to each component of a workload.

Allow repeatable changes to be standardized, templated, and preauthorized if they follow a consistent workflow that enforces change policies.
- Reduce the potential impact of any change by making the size of the change smaller so recovery takes less time and causes less business impact.
- Ensure rollback procedures revert code to the known good state to avoid incidents where possible.

- Integrate tools and workflows to enforce your policies programatically.
- Make data about changes visible to other workload owners to improve the speed of diagnosis of any failed change that cannot be rolled back.

Measure success of this practice using visible change data and identify iterative improvements.

- Use monitoring tools to verify the success or failure of a deployment to speed up decision-making on rolling back.
- Measure your duration of outage during an unsuccessful change to continually improve your recovery plans.

**Level of effort for the implementation plan:** Medium

## Resources

**Related best practices:**

- OPS06-BP04 Automate testing and rollback

**Related documents:**

- [AWS Builders Library | Ensuring Rollback Safety During Deployments](https://aws.amazon.com/builders-library/ensuring-rollback-safety-during-deployments/)
- [AWS Whitepaper | Change Management in the Cloud](https://docs.aws.amazon.com/whitepapers/latest/change-management-in-the-cloud/change-management-in-the-cloud.html)

**Related videos:**

- [re:Invent 2019 | Amazon’s approach to high-availability deployment](https://aws.amazon.com/builders-library/amazon-approach-to-high-availability-deployment/)
