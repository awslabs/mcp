---
id: "OPS05-BP01"
title: "Use version control"
pillar: "Operational Excellence"
risk_level: "HIGH"
capability: "How do you reduce defects, ease remediation, and improve flow into production?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_dev_integ_version_control.html"
description: "Use version control to activate tracking of changes and releases."
area: ["Prepare", "Design for operations"]
relatedIds: ["OPS05-BP04"]
---

# OPS05-BP01 Use version control

Use version control to activate tracking of changes and releases.

Many AWS services offer version control capabilities. Use a revision
or [source control](https://aws.amazon.com/devops/source-control/) system such as
[Git](https://aws.amazon.com/devops/source-control/git/) to manage code and other artifacts such as
version-controlled
[AWS CloudFormation](https://aws.amazon.com/cloudformation/) templates of your infrastructure.

**Desired outcome:** Your teams collaborate on code. When merged, the code is consistent and no changes are lost. Errors are easily reverted through correct versioning.

**Common anti-patterns:**

- You have been developing and storing your code on your
workstation. You have had an unrecoverable storage failure on
the workstation and your code is lost.
- After overwriting the existing code with your changes, you
restart your application and it is no longer operable. You are
unable to revert the change.
- You have a write lock on a report file that someone else needs
to edit. They contact you asking that you stop work on it so
that they can complete their tasks.
- Your research team has been working on a detailed analysis that
shapes your future work. Someone has accidentally saved
their shopping list over the final report. You are unable to
revert the change and have to recreate the report.

**Benefits of establishing this best
practice:** By using version control capabilities you can
easily revert to known good states and previous versions, and limit the
risk of assets being lost.

**Level of risk exposed if this best practice
is not established:** High

## Implementation guidance

Maintain assets in version controlled repositories. Doing so supports tracking changes, deploying new versions, detecting changes to existing versions, and reverting to prior versions (for example, rolling back to a known good state in the event of a failure). Integrate the version control capabilities of your configuration management systems into your procedures.

## Resources

**Related best practices:**

- OPS05-BP04 Use build and deployment management systems

**Related videos:**

- [AWS re:Invent 2023 - How Lockheed Martin builds software faster, powered by DevSecOps](https://www.youtube.com/watch?v=Q1OSyxYkl5w)
- [AWS re:Invent 2023 - How GitHub operationalizes AI for team collaboration and productivity](https://www.youtube.com/watch?v=cOVvGaiusOI)
