---
id: "SUS04-BP07"
title: "Minimize data movement across networks"
framework: "WAF"
domain: "Sustainability"
capability: "How do you take advantage of data management policies and patterns to support your sustainability goals?"
risk_level: "Medium"
---

# SUS04-BP07 Minimize data movement across networks

## Anti-Patterns
- You store all data in the same AWS Region independent of where the data users are.
- You do not optimize data size and format before moving it over the network.

## Implementation Guidance
 Moving data around your organization requires compute, networking, and storage resources. Use techniques to minimize data movement and improve the overall efficiency of your workload.

## Implementation Steps
- **Use proximity:** Consider proximity to the data or users as a decision factor when [selecting a Region for your workload](https://aws.amazon.com/blogs/architecture/how-to-select-a-region-for-your-workload-based-on-sustainability-goals/).
- **Partition services:** Partition Regionally-consumed services so that their Region-specific data is stored within the Region where it is consumed.
- **Use efficient file formats:** Use efficient file formats (such as Parquet or ORC) and compress data before you move it over the network.
- **Minimize data movement:** Don't move unused data. Some examples that can help you avoid moving unused data:
  - Reduce API responses to only relevant data.
  - Aggregate data where detailed (record-level information is not required).
  - See [Well-Architected Lab - Optimize Data Pattern Using Amazon Redshift Data Sharing](https://catalog.workshops.aws/well-architected-sustainability/en-US/3-data/optimize-data-pattern-using-redshift-data-sharing).
  - Consider [Cross-account data sharing in AWS Lake Formation](https://docs.aws.amazon.com/lake-formation/latest/dg/cross-account-permissions.html).
- **Use edge services:** Use services that can help you run code closer to users of your workload.
[\[See the AWS documentation website for more details\]](http://docs.aws.amazon.com/wellarchitected/latest/framework/sus_sus_data_a8.html)

## Resources
### Related Documents
- [Optimizing your AWS Infrastructure for Sustainability, Part III: Networking](https://aws.amazon.com/blogs/architecture/optimizing-your-aws-infrastructure-for-sustainability-part-iii-networking/)
- [AWS Global Infrastructure](https://aws.amazon.com/about-aws/global-infrastructure/)
- [Amazon CloudFront Key Features including the CloudFront Global Edge Network](https://aws.amazon.com/cloudfront/features/)
- [Compressing HTTP requests in Amazon OpenSearch Service](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/gzip.html)
- [Intermediate data compression with Amazon EMR](https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-plan-output-compression.html#HadoopIntermediateDataCompression)
- [Loading compressed data files from Amazon S3 into Amazon Redshift](https://docs.aws.amazon.com/redshift/latest/dg/t_loading-gzip-compressed-data-files-from-S3.html)
- [Serving compressed files with Amazon CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/ServingCompressedFiles.html)
### Related Videos
- [ Demystifying data transfer on AWS](https://www.youtube.com/watch?v=-MqXgzw1IGA)
