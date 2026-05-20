---
id: "COST06-BP02"
title: "Select resource type, size, and number based on data"
framework: "WAF"
domain: "Cost Optimization"
capability: "How do you meet cost targets when you select resource type, size and number?"
risk_level: "Medium"
---

# COST06-BP02 Select resource type, size, and number based on data

## Implementation Guidance
 Amazon EC2 provides a wide selection of instance types with different levels of CPU, memory, storage, and networking capacity to fit different use cases. These instance types feature different blends of CPU, memory, storage, and networking capabilities, giving you versatility when selecting the right resource combination for your projects. Every instance type comes in multiple sizes, so that you can adjust your resources based on your workload’s demands. To determine which instance type you need, gather details about the system requirements of the application or software that you plan to run on your instance. These details should include the following:
- Operating system
- Number of CPU cores
- GPU cores
- Amount of system memory (RAM)
- Storage type and space
- Network bandwidth requirement

 Identify the purpose of compute requirements and which instance is needed, and then explore the various Amazon EC2 instance families. Amazon offers the following instance type families:
- General Purpose
- Compute Optimized
- Memory Optimized
- Storage Optimized
- Accelerated Computing
- HPC Optimized

 For a deeper understanding of the specific purposes and use cases that a particular Amazon EC2 instance family can fulfill, see [AWS Instance types](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-types.html).

 System requirements gathering is critical for you to select the specific instance family and instance type that best serves your needs. Instance type names are comprised of the family name and the instance size. For example, the t2.micro instance is from the T2 family and is micro-sized.

 Select resource size or type based on workload and resource characteristics (for example, compute, memory, throughput, or write intensive). This selection is typically made using cost modeling, a previous version of the workload (such as an on-premises version), using documentation, or using other sources of information about the workload (whitepapers or published solutions). Using AWS pricing calculators or cost management tools can assist in making informed decisions about instance types, sizes, and configurations.

## Implementation Steps
- **Select resources based on data:** Use your cost modeling data to select the anticipated workload usage level, and choose the specified resource type and size. Relying on the cost modeling data, determine the number of virtual CPUs, total memory (GiB), the local instance store volume (GB), Amazon EBS volumes, and the network performance level, taking into account the data transfer rate required for the instance. Always make selections based on detailed analysis and accurate data to optimize performance while managing costs effectively.

## Resources
### Related Documents
- [AWS Instance types](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-types.html)
- [AWS Auto Scaling](https://aws.amazon.com/autoscaling/)
- [Amazon CloudWatch features](https://aws.amazon.com/cloudwatch/features/)
- [Cost Optimization: EC2 Right Sizing](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/ce-rightsizing.html)
### Related Videos
- [ Selecting the right Amazon EC2 instance for your workloads ](https://www.youtube.com/watch?v=q5Dn9gcmpJg)
- [ Right size your service ](https://youtu.be/wcp1inFS78A)
### Related Examples
- [ It just got easier to discover and compare Amazon EC2 instance types ](https://aws.amazon.com/blogs/compute/it-just-got-easier-to-discover-and-compare-ec2-instance-types/)
