---
id: "SUS04-BP01"
title: "Implement a data classification policy"
pillar: "Sustainability"
risk_level: "MEDIUM"
capability: "How do you take advantage of data management policies and patterns to support your sustainability goals?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/sustainability-pillar/sus_sus_data_a2.html"
---

# SUS04-BP01 Implement a data classification policy

Classify data to understand its criticality to business
outcomes and choose the right energy-efficient storage tier
to store the data.

**Common anti-patterns:**

- You do not identify data assets with similar characteristics
(such as sensitivity, business criticality, or regulatory
requirements) that are being processed or stored.
- You have not implemented a data catalog to inventory your data assets.

**Benefits of establishing this best practice:** Implementing
a data classification policy allows you to determine the most energy-efficient storage
tier for data.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

Data classification involves identifying the types of data
that are being processed and stored in an information system
owned or operated by an organization. It also involves making
a determination on the criticality of the data and the likely
impact of a data compromise, loss, or misuse.

Implement data classification policy by working backwards
from the contextual use of the data and creating a categorization
scheme that takes into account the level of criticality of a
given dataset to an organization’s operations.

### Implementation steps

- **Perform data inventory:**
Conduct an inventory of the various data types that exist for your workload.
- **Group data:**
Determine criticality, confidentiality, integrity, and
availability of data based on risk to the organization.
Use these requirements to group data into one of the data
classification tiers that you adopt. As an example, see [Four simple steps to classify your data and
secure your startup](https://aws.amazon.com/blogs/startups/four-simple-steps-to-classify-your-data-and-secure-your-startup/).
- **Define data classification levels and policies:**
For each data group, define data classification level (for example, public or confidential) and handling policies. Tag data accordingly. For more detail on data classification categories, see Data Classification whitepaper.
- **Periodically review:**
Periodically review and audit your environment for untagged and
unclassified data. Use automation to identify this data, and classify and tag the data
appropriately. As an example, see [Data Catalog and crawlers in AWS Glue](https://docs.aws.amazon.com/glue/latest/dg/catalog-and-crawler.html).
- **Establish a data catalog:**
Establish a data catalog that provides
audit and governance capabilities.
- **Documentation:**
Document data classification policies and handling procedures
for each data class.

## Resources

**Related documents:**

- [Leveraging
AWS Cloud to Support Data Classification](https://docs.aws.amazon.com/whitepapers/latest/data-classification/leveraging-aws-cloud-to-support-data-classification.html)
- [Tag
policies from AWS Organizations](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_tag-policies.html)

**Related videos:**

- [AWS re:Invent 2022 - Enabling agility with data governance on AWS](https://www.youtube.com/watch?v=vznDgJkoH7k)
- [AWS re:Invent 2023 - Data protection and resilience with AWS storage](https://www.youtube.com/watch?v=rdG8JV3Fhk4)
