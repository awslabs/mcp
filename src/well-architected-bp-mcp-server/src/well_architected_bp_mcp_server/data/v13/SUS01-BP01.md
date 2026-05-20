---
id: "SUS01-BP01"
title: "Choose Region based on both business requirements and sustainability goals"
framework: "WAF"
domain: "Sustainability"
capability: "How do you select Regions for your workload?"
risk_level: "Medium"
---

# SUS01-BP01 Choose Region based on both business requirements and sustainability goals

## Anti-Patterns
- You select the workload’s Region based on your own location.
- You consolidate all workload resources into one geographic location.

## Implementation Guidance
The AWS Cloud is a constantly expanding network of Regions and points of presence (PoP), with a global network infrastructure linking them together. The choice of Region for your workload significantly affects its KPIs, including performance, cost, and carbon footprint. To effectively improve these KPIs, you should choose Regions for your workload based on both your business requirements and sustainability goals.

## Implementation Steps
- **Shortlist potential Regions:** Follow these steps to assess and shortlist potential Regions for your workload based on your business requirements, including compliance, available features, cost, and latency:
  - Confirm that these Regions are compliant, based on your required local regulations (for example, data sovereignty).
  - Use the [AWS Regional Services Lists](https://aws.amazon.com/about-aws/global-infrastructure/regional-product-services/) to check if the Regions have the services and features you need to run your workload.
  - Calculate the cost of the workload on each Region using the [AWS Pricing Calculator](https://calculator.aws/).
  - Test the network latency between your end user locations and each AWS Region.
- **Choose Regions:** Choose Regions near Amazon renewable energy projects and Regions where the grid has a published carbon intensity that is lower than other locations (or Regions).
  - Identify your relevant sustainability guidelines to track and compare year-to-year carbon emissions based on [Greenhouse Gas Protocol](https://ghgprotocol.org/) (market-based and location based methods).
  - Choose region based on method you use to track carbon emissions. For more detail on choosing a Region based on your sustainability guidelines, see [How to select a Region for your workload based on sustainability goals](https://aws.amazon.com/blogs/architecture/how-to-select-a-region-for-your-workload-based-on-sustainability-goals/).

## Resources
### Related Documents
- [Understanding your carbon emission estimations](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/ccft-estimation.html)
- [Amazon Around the Globe](https://sustainability.aboutamazon.com/about/around-the-globe?energyType=true)
- [Renewable Energy Methodology](https://sustainability.aboutamazon.com/amazon-renewable-energy-methodology)
- [What to Consider when Selecting a Region for your Workloads](https://aws.amazon.com/blogs/architecture/what-to-consider-when-selecting-a-region-for-your-workloads/)
### Related Videos
- [AWS re:Invent 2023 - Sustainability innovation in AWS Global Infrastructure ](https://www.youtube.com/watch?v=0EkcwLKeOQA)
- [AWS re:Invent 2023 - Sustainable architecture: Past, present, and future ](https://www.youtube.com/watch?v=2xpUQ-Q4QcM)
- [AWS re:Invent 2022 - Delivering sustainable, high-performing architectures ](https://www.youtube.com/watch?v=FBc9hXQfat0)
- [AWS re:Invent 2022 - Architecting sustainably and reducing your AWS carbon footprint](https://www.youtube.com/watch?v=jsbamOLpCr8)
- [AWS re:Invent 2022 - Sustainability in AWS global infrastructure ](https://www.youtube.com/watch?v=NgMa8R9-Ywk)
