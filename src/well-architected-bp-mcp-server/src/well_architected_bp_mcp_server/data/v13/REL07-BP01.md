---
id: "REL07-BP01"
title: "Use automation when obtaining or scaling resources"
framework: "WAF"
domain: "Reliability"
capability: "How do you design your workload to adapt to changes in demand?"
risk_level: "High"
---

# REL07-BP01 Use automation when obtaining or scaling resources

## Anti-Patterns
- You deploy resources manually using the command line or at the AWS Management Console (also known as *click-ops*).
- You tightly couple your application components or resources, and create inflexible architectures as a result.
- You implement inflexible scaling policies that do not adapt to changing business requirements, traffic patterns, or new resource types.
- You manually estimate capacity to meet anticipated demand.

## Implementation Guidance
 To set up automation with CI/CD pipelines and infrastructure as code (IaC) for your AWS architecture, choose a version control system such as Git to store your IaC templates and configuration. These templates can be written using tools such as [AWS CloudFormation](https://aws.amazon.com/cloudformation/). To start, define your infrastructure components (such as AWS VPCs, Amazon EC2 Auto Scaling Groups, and Amazon RDS databases) within these templates.

 Next, integrate these IaC templates with a CI/CD pipeline to automate the deployment process. [AWS CodePipeline](https://aws.amazon.com/codepipeline/) provides a seamless AWS-native solution, or you can use other third-party CI/CD solutions. Create a pipeline that activates when changes occur to your version control repository. Configure the pipeline to include stages that lint and validate your IaC templates, deploy the infrastructure to a staging environment, run automated tests, and finally, deploy to production. Incorporate approval steps where necessary to maintain control over changes. This automated pipeline not only speeds up deployment but also facilitates consistency and reliability across environments.

 Configure Auto Scaling of resources such as Amazon EC2 instances, Amazon ECS tasks, and database replicas in your IaC to provide automatic scale-out and scale-in as needed. This approach enhances application availability and performance and optimizes cost by dynamically adjusting resources based on demand. For a list of supported resources, see [Amazon EC2 Auto Scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/what-is-amazon-ec2-auto-scaling.html) and [AWS Auto Scaling](https://docs.aws.amazon.com/autoscaling/application/userguide/what-is-application-auto-scaling.html).

## Implementation Steps
1.  Create and use a source code repository to store the code that controls your infrastructure configuration. Commit changes to this repository to reflect any ongoing changes you want to make.

1.  Select an infrastructure as code solution such as AWS CloudFormation to keep your infrastructure up to date and detect inconsistency (drift) from your intended state.

1.  Integrate your IaC platform with your CI/CD pipeline to automate deployments.

1.  Determine and collect the appropriate metrics for automatic scaling of resources.

1.  Configure automatic scaling of resources using scale-out and scale-in policies appropriate for your workload components. Consider using scheduled scaling for predictable usage patterns.

1.  Monitor deployments to detect failures and regressions. Implement rollback mechanisms within your CI/CD platform to revert changes if necessary.

## Resources
### Related Documents
- [AWS Auto Scaling: How Scaling Plans Work](https://docs.aws.amazon.com/autoscaling/plans/userguide/how-it-works.html)
- [AWS Marketplace: products that can be used with auto scaling](https://aws.amazon.com/marketplace/search/results?searchTerms=Auto+Scaling)
- [Managing Throughput Capacity Automatically with DynamoDB Auto Scaling](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/AutoScaling.html)
- [Using a load balancer with an Auto Scaling group](https://docs.aws.amazon.com/autoscaling/ec2/userguide/autoscaling-load-balancer.html)
- [What Is AWS Global Accelerator?](https://docs.aws.amazon.com/global-accelerator/latest/dg/what-is-global-accelerator.html)
- [What Is Amazon EC2 Auto Scaling?](https://docs.aws.amazon.com/autoscaling/ec2/userguide/what-is-amazon-ec2-auto-scaling.html)
- [What is AWS Auto Scaling?](https://docs.aws.amazon.com/autoscaling/plans/userguide/what-is-aws-auto-scaling.html)
- [What is Amazon CloudFront?](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Introduction.html?ref=wellarchitected)
- [What is Amazon Route 53?](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/Welcome.html)
- [What is Elastic Load Balancing?](https://docs.aws.amazon.com/elasticloadbalancing/latest/userguide/what-is-load-balancing.html)
- [What is a Network Load Balancer?](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/introduction.html)
- [What is an Application Load Balancer?](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/introduction.html)
- [Integrating Jenkins with AWS CodeBuild and AWS CodeDeploy](https://aws.amazon.com/blogs/devops/setting-up-a-ci-cd-pipeline-by-integrating-jenkins-with-aws-codebuild-and-aws-codedeploy/)
- [Creating a four stage pipeline with AWS CodePipeline](https://docs.aws.amazon.com/codepipeline/latest/userguide/tutorials-four-stage-pipeline.html)
### Related Videos
- [Back to Basics: Deploy Your Code to Amazon EC2](https://www.youtube.com/watch?v=f2wvEQ_sWS8)
- [AWS Supports You \$1 Starting Your Infrastructure as Code Solution Using AWS CloudFormation Templates](https://www.youtube.com/watch?v=bgfx76jr7tA)
- [Streamline Your Software Release Process Using AWS CodePipeline](https://www.youtube.com/watch?v=zMa5gTLrzmQ)
- [Monitor AWS Resources Using Amazon CloudWatch Dashboards](https://www.youtube.com/watch?v=I7EFLChc07M)
- [Create Cross Account & Cross Region CloudWatch Dashboards \$1 Amazon Web Services](https://www.youtube.com/watch?v=eIUZdaqColg)
