---
id: "SUS02-BP05"
title: "Optimize team member resources for activities performed"
pillar: "Sustainability"
risk_level: "LOW"
capability: "How do you align cloud resources to your demand?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/sustainability-pillar/sus_sus_user_a6.html"
---

# SUS02-BP05 Optimize team member resources for activities performed

Optimize resources provided to team members to minimize the
environmental sustainability impact while supporting their needs.

**Common anti-patterns:**

- You ignore the impact of devices used by your team members on the overall efficiency of your cloud application.
- You manually manage and update resources used by team members.

**Benefits of establishing this best practice:** Optimizing
team member resources improves the overall efficiency of cloud-enabled applications.

**Level of risk exposed if this best practice
is not established:** Low

## Implementation guidance

Understand the resources your team members use to consume your services, their expected lifecycle, and the financial and sustainability impact. Implement strategies to optimize these resources. For example, perform complex operations, such as rendering and compilation, on highly utilized scalable infrastructure instead of on underutilized high-powered single-user systems.

### Implementation steps

- **Use energy-efficient workstations:** Provide team members with energy-efficient workstations and peripherals. Use efficient power management features (like low power mode) in these devices to reduce their energy usage
- **use virtualization:** Use virtual desktops and application streaming to limit upgrade and device requirements.
- **Encourage remote collaboration:** Encourage team members to use remote collaboration tools such as [Amazon Chime](https://aws.amazon.com/chime/) or [AWS Wickr](https://aws.amazon.com/wickr/) to reduce the need for travel and associated carbon emissions.
- **Use energy-efficient software:** Provide team members with energy-efficient software by removing or turning off unnecessary features and processes.
- **Manage lifecycles:** Evaluate the impact of processes and systems on your device lifecycle, and select solutions that minimize the requirement for device replacement while satisfying business requirements. Regularly maintain and update workstations or software to maintain and improve efficiency.
- **Remote device management:** Implement remote management for devices to reduce required business travel.

[AWS Systems Manager Fleet Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/fleet.html) is a unified user interface (UI) experience that helps you remotely manage your nodes running on AWS or on premises.

## Resources

**Related documents:**

- [What
is Amazon WorkSpaces?](https://docs.aws.amazon.com/workspaces/latest/adminguide/amazon-workspaces.html)
- [Cost Optimizer for Amazon WorkSpaces](https://docs.aws.amazon.com/solutions/latest/cost-optimizer-for-workspaces/overview.html)
- [Amazon
AppStream 2.0 Documentation](https://docs.aws.amazon.com/appstream2/)
- [NICE
DCV](https://docs.aws.amazon.com/dcv/)

**Related videos:**

- [Managing cost for Amazon WorkSpaces on AWS](https://www.youtube.com/watch?v=0MoY31hZQuE)
