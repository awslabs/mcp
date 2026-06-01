---
id: "SUS04-BP07"
title: "Minimize data movement across networks"
pillar: "Sustainability"
risk_level: "MEDIUM"
capability: "How do you take advantage of data management policies and patterns to support your sustainability goals?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/sustainability-pillar/sus_sus_data_a8.html"
description: "Use shared file systems or object storage to access common data and minimize the total networking resources required to support data movement for your workload."
area: ["Data management"]
---

# SUS04-BP07 Minimize data movement across networks

Use shared file systems or object storage to access common data and minimize the total
networking resources required to support data movement for your workload.

**Common anti-patterns:**

- You store all data in the same AWS Region independent of where the data users are.
- You do not optimize data size and format before moving it over the network.

**Benefits of establishing this best practice:** Optimizing data
movement across the network reduces the total networking resources required for the workload and
lowers its environmental impact.

**Level of risk exposed if this best practice is not established:**
Medium

## Implementation guidance

Moving data around your organization requires compute, networking, and storage resources.
Use techniques to minimize data movement and improve the overall efficiency of your workload.

## Implementation steps

- **Use proximity:** Consider proximity to the data or users as a decision factor when [selecting a Region for your workload](https://aws.amazon.com/blogs/architecture/how-to-select-a-region-for-your-workload-based-on-sustainability-goals/).
- **Partition services:** Partition Regionally-consumed services so that their Region-specific data is stored
within the Region where it is consumed.
- **Use efficient file formats:** Use efficient file formats (such as Parquet or ORC) and compress data before you move
it over the network.
- **Minimize data movement:** Don't move unused data. Some examples that can help you avoid moving unused data:

Reduce API responses to only relevant data.
- Aggregate data where detailed (record-level information is not required).
- See [Well-Architected Lab - Optimize Data Pattern Using Amazon Redshift Data Sharing](https://catalog.workshops.aws/well-architected-sustainability/en-US/3-data/optimize-data-pattern-using-redshift-data-sharing).
- Consider [Cross-account data
sharing in AWS Lake Formation](https://docs.aws.amazon.com/lake-formation/latest/dg/cross-account-permissions.html).

- **Use edge services:** Use services that can help you run code closer to users of your workload.

Service
When to use

[Lambda@Edge](https://aws.amazon.com/lambda/edge/)

Use for compute-heavy operations that are run when objects are not in the
cache.

[CloudFront
Functions](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/cloudfront-functions.html)

Use for simple use cases such as HTTP(s) request/response manipulations that
can be initiated by short-lived functions.

[AWS IoT Greengrass](https://aws.amazon.com/greengrass/)

Run local compute, messaging, and data caching for connected devices.

## Resources

**Related documents:**

- [Optimizing your AWS Infrastructure for Sustainability, Part III: Networking](https://aws.amazon.com/blogs/architecture/optimizing-your-aws-infrastructure-for-sustainability-part-iii-networking/)
- [AWS Global
Infrastructure](https://aws.amazon.com/about-aws/global-infrastructure/)
- [Amazon CloudFront Key Features including the
CloudFront Global Edge Network](https://aws.amazon.com/cloudfront/features/)
- [Compressing HTTP requests in Amazon OpenSearch Service](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/gzip.html)
- [Intermediate data compression with Amazon EMR](https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-plan-output-compression.html#HadoopIntermediateDataCompression)
- [Loading
compressed data files from Amazon S3 into Amazon Redshift](https://docs.aws.amazon.com/redshift/latest/dg/t_loading-gzip-compressed-data-files-from-S3.html)
- [Serving compressed
files with Amazon CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/ServingCompressedFiles.html)

**Related videos:**

- [Demystifying data transfer
on AWS](https://www.youtube.com/watch?v=-MqXgzw1IGA)
