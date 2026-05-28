---
id: "REL12-BP04"
title: "Test resiliency using chaos engineering"
framework: "WAF"
domain: "Reliability"
capability: "How do you test reliability?"
risk_level: "Medium"
---

# REL12-BP04 Test resiliency using chaos engineering

## Implementation Guidance
 Chaos engineering provides your teams with capabilities to continually inject real world disruptions (simulations) in a controlled way at the service provider, infrastructure, workload, and component level, with minimal to no impact to your customers. It allows your teams to learn from faults and observe, measure, and improve the resilience of your workloads, as well as validate that alerts fire and teams get notified in the case of an event.

 When performed continually, chaos engineering can highlight deficiencies in your workloads that, if left unaddressed, could negatively affect availability and operation.

**Note**
Chaos engineering is the discipline of experimenting on a system in order to build confidence in the system’s capability to withstand turbulent conditions in production. – [Principles of Chaos Engineering](https://principlesofchaos.org/)

 If a system is able to withstand these disruptions, the chaos experiment should be maintained as an automated regression test. In this way, chaos experiments should be performed as part of your systems development lifecycle (SDLC) and as part of your CI/CD pipeline.

 To ensure that your workload can survive component failure, inject real world events as part of your experiments. For example, experiment with the loss of Amazon EC2 instances or failover of the primary Amazon RDS database instance, and verify that your workload is not impacted (or only minimally impacted). Use a combination of component faults to simulate events that may be caused by a disruption in an Availability Zone.

 For application-level faults (such as crashes), you can start with stressors such as memory and CPU exhaustion.

 To validate [fallback or failover mechanisms](https://aws.amazon.com/builders-library/avoiding-fallback-in-distributed-systems/) for external dependencies due to intermittent network disruptions, your components should simulate such an event by blocking access to the third-party providers for a specified duration that can last from seconds to hours.

 Other modes of degradation might cause reduced functionality and slow responses, often resulting in a disruption of your services. Common sources of this degradation are increased latency on critical services and unreliable network communication (dropped packets). Experiments with these faults, including networking effects such as latency, dropped messages, and DNS failures, could include the inability to resolve a name, reach the DNS service, or establish connections to dependent services.

 **Chaos engineering tools:**

 AWS Fault Injection Service (AWS FIS) is a fully managed service for running fault injection experiments that can be used as part of your CD pipeline, or outside of the pipeline. AWS FIS is a good choice to use during chaos engineering game days. It supports simultaneously introducing faults across different types of resources including Amazon EC2, Amazon Elastic Container Service (Amazon ECS), Amazon Elastic Kubernetes Service (Amazon EKS), and Amazon RDS. These faults include termination of resources, forcing failovers, stressing CPU or memory, throttling, latency, and packet loss. Since it is integrated with Amazon CloudWatch Alarms, you can set up stop conditions as guardrails to rollback an experiment if it causes unexpected impact.

![\[\]](http://docs.aws.amazon.com/wellarchitected/latest/framework/images/fault-injection-simulator.png)

There are also several third-party options for fault injection experiments. These include open-source tools such as [Chaos Toolkit](https://chaostoolkit.org/), [Chaos Mesh](https://chaos-mesh.org/), and [Litmus Chaos](https://litmuschaos.io/), as well as commercial options like Gremlin. To expand the scope of faults that can be injected on AWS, AWS FIS [integrates with Chaos Mesh and Litmus Chaos](https://aws.amazon.com/about-aws/whats-new/2022/07/aws-fault-injection-simulator-supports-chaosmesh-litmus-experiments/), allowing you to coordinate fault injection workflows among multiple tools. For example, you can run a stress test on a pod’s CPU using Chaos Mesh or Litmus faults while terminating a randomly selected percentage of cluster nodes using AWS FIS fault actions.

## Implementation Steps
1.  Determine which faults to use for experiments.

    Assess the design of your workload for resiliency. Such designs (created using the best practices of the [Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html)) account for risks based on critical dependencies, past events, known issues, and compliance requirements. List each element of the design intended to maintain resilience and the faults it is designed to mitigate. For more information about creating such lists, see the [Operational Readiness Review whitepaper](https://docs.aws.amazon.com/wellarchitected/latest/operational-readiness-reviews/wa-operational-readiness-reviews.html) which guides you on how to create a process to prevent reoccurrence of previous incidents. The Failure Modes and Effects Analysis (FMEA) process provides you with a framework for performing a component-level analysis of failures and how they impact your workload. FMEA is outlined in more detail by Adrian Cockcroft in [Failure Modes and Continuous Resilience](https://adrianco.medium.com/failure-modes-and-continuous-resilience-6553078caad5).

1.  Assign a priority to each fault.

    Start with a coarse categorization such as high, medium, or low. To assess priority, consider frequency of the fault and impact of failure to the overall workload.

    When considering frequency of a given fault, analyze past data for this workload when available. If not available, use data from other workloads running in a similar environment.

    When considering impact of a given fault, the larger the scope of the fault, generally the larger the impact. Also consider the workload design and purpose. For example, the ability to access the source data stores is critical for a workload doing data transformation and analysis. In this case, you would prioritize experiments for access faults, as well as throttled access and latency insertion.

    Post-incident analyses are a good source of data to understand both frequency and impact of failure modes.

    Use the assigned priority to determine which faults to experiment with first and the order with which to develop new fault injection experiments.

1.  For each experiment that you perform, follow the chaos engineering and continuous resilience flywheel in the following figure.
![\[\]](http://docs.aws.amazon.com/wellarchitected/latest/framework/images/chaos-engineering-flywheel.png)

   1.  Define steady state as some measurable output of a workload that indicates normal behavior.

       Your workload exhibits steady state if it is operating reliably and as expected. Therefore, validate that your workload is healthy before defining steady state. Steady state does not necessarily mean no impact to the workload when a fault occurs, as a certain percentage in faults could be within acceptable limits. The steady state is your baseline that you will observe during the experiment, which will highlight anomalies if your hypothesis defined in the next step does not turn out as expected.

       For example, a steady state of a payments system can be defined as the processing of 300 TPS with a success rate of 99% and round-trip time of 500 ms.

   1.  Form a hypothesis about how the workload will react to the fault.

       A good hypothesis is based on how the workload is expected to mitigate the fault to maintain the steady state. The hypothesis states that given the fault of a specific type, the system or workload will continue steady state, because the workload was designed with specific mitigations. The specific type of fault and mitigations should be specified in the hypothesis.

       The following template can be used for the hypothesis (but other wording is also acceptable):
**Note**
 If *specific fault* occurs, the *workload name* workload will *describe mitigating controls* to maintain *business or technical metric impact*.

       For example:
      - If 20% of the nodes in the Amazon EKS node-group are taken down, the Transaction Create API continues to serve the 99th percentile of requests in under 100 ms (steady state). The Amazon EKS nodes will recover within five minutes, and pods will get scheduled and process traffic within eight minutes after the initiation of the experiment. Alerts will fire within three minutes.
      - If a single Amazon EC2 instance failure occurs, the order system’s Elastic Load Balancing health check will cause the Elastic Load Balancing to only send requests to the remaining healthy instances while the Amazon EC2 Auto Scaling replaces the failed instance, maintaining a less than 0.01% increase in server-side (5xx) errors (steady state).
      - If the primary Amazon RDS database instance fails, the Supply Chain data collection workload will failover and connect to the standby Amazon RDS database instance to maintain less than 1 minute of database read or write errors (steady state).

   1.  Run the experiment by injecting the fault.

       An experiment should by default be fail-safe and tolerated by the workload. If you know that the workload will fail, do not run the experiment. Chaos engineering should be used to find known-unknowns or unknown-unknowns. *Known-unknowns* are things you are aware of but don’t fully understand, and *unknown-unknowns* are things you are neither aware of nor fully understand. Experimenting against a workload that you know is broken won’t provide you with new insights. Your experiment should be carefully planned, have a clear scope of impact, and provide a rollback mechanism that can be applied in case of unexpected turbulence. If your due-diligence shows that your workload should survive the experiment, move forward with the experiment. There are several options for injecting the faults. For workloads on AWS, [AWS FIS](https://docs.aws.amazon.com/fis/latest/userguide/what-is.html) provides many predefined fault simulations called [actions](https://docs.aws.amazon.com/fis/latest/userguide/actions.html). You can also define custom actions that run in AWS FIS using [AWS Systems Manager documents](https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-ssm-docs.html).

       We discourage the use of custom scripts for chaos experiments, unless the scripts have the capabilities to understand the current state of the workload, are able to emit logs, and provide mechanisms for rollbacks and stop conditions where possible.

       An effective framework or toolset which supports chaos engineering should track the current state of an experiment, emit logs, and provide rollback mechanisms to support the controlled running of an experiment. Start with an established service like AWS FIS that allows you to perform experiments with a clearly defined scope and safety mechanisms that rollback the experiment if the experiment introduces unexpected turbulence. To learn about a wider variety of experiments using AWS FIS, also see the [Resilient and Well-Architected Apps with Chaos Engineering lab](https://catalog.us-east-1.prod.workshops.aws/workshops/44e29d0c-6c38-4ef3-8ff3-6d95a51ce5ac/en-US). Also, [AWS Resilience Hub](https://docs.aws.amazon.com/resilience-hub/latest/userguide/what-is.html) will analyze your workload and create experiments that you can choose to implement and run in AWS FIS.
**Note**
 For every experiment, clearly understand the scope and its impact. We recommend that faults should be simulated first on a non-production environment before being run in production.

       Experiments should run in production under real-world load using [canary deployments](https://medium.com/the-cloud-architect/chaos-engineering-q-a-how-to-safely-inject-failure-ced26e11b3db) that spin up both a control and experimental system deployment, where feasible. Running experiments during off-peak times is a good practice to mitigate potential impact when first experimenting in production. Also, if using actual customer traffic poses too much risk, you can run experiments using synthetic traffic on production infrastructure against the control and experimental deployments. When using production is not possible, run experiments in pre-production environments that are as close to production as possible.

       You must establish and monitor guardrails to ensure the experiment does not impact production traffic or other systems beyond acceptable limits. Establish stop conditions to stop an experiment if it reaches a threshold on a guardrail metric that you define. This should include the metrics for steady state for the workload, as well as the metric against the components into which you’re injecting the fault. A [synthetic monitor](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Canaries.html) (also known as a user canary) is one metric you should usually include as a user proxy. [Stop conditions for AWS FIS](https://docs.aws.amazon.com/fis/latest/userguide/stop-conditions.html) are supported as part of the experiment template, allowing up to five stop-conditions per template.

       One of the principles of chaos is minimize the scope of the experiment and its impact:

       While there must be an allowance for some short-term negative impact, it is the responsibility and obligation of the Chaos Engineer to ensure the fallout from experiments are minimized and contained.

       A method to verify the scope and potential impact is to perform the experiment in a non-production environment first, verifying that thresholds for stop conditions activate as expected during an experiment and observability is in place to catch an exception, instead of directly experimenting in production.

       When running fault injection experiments, verify that all responsible parties are well-informed. Communicate with appropriate teams such as the operations teams, service reliability teams, and customer support to let them know when experiments will be run and what to expect. Give these teams communication tools to inform those running the experiment if they see any adverse effects.

       You must restore the workload and its underlying systems back to the original known-good state. Often, the resilient design of the workload will self-heal. But some fault designs or failed experiments can leave your workload in an unexpected failed state. By the end of the experiment, you must be aware of this and restore the workload and systems. With AWS FIS you can set a rollback configuration (also called a post action) within the action parameters. A post action returns the target to the state that it was in before the action was run. Whether automated (such as using AWS FIS) or manual, these post actions should be part of a playbook that describes how to detect and handle failures.

   1.  Verify the hypothesis.

      [Principles of Chaos Engineering](https://principlesofchaos.org/) gives this guidance on how to verify steady state of your workload:

      Focus on the measurable output of a system, rather than internal attributes of the system. Measurements of that output over a short period of time constitute a proxy for the system’s steady state. The overall system’s throughput, error rates, and latency percentiles could all be metrics of interest representing steady state behavior. By focusing on systemic behavior patterns during experiments, chaos engineering verifies that the system does work, rather than trying to validate how it works.

       In our two previous examples, we include the steady state metrics of less than 0.01% increase in server-side (5xx) errors and less than one minute of database read and write errors.

       The 5xx errors are a good metric because they are a consequence of the failure mode that a client of the workload will experience directly. The database errors measurement is good as a direct consequence of the fault, but should also be supplemented with a client impact measurement such as failed customer requests or errors surfaced to the client. Additionally, include a synthetic monitor (also known as a user canary) on any APIs or URIs directly accessed by the client of your workload.

   1.  Improve the workload design for resilience.

       If steady state was not maintained, then investigate how the workload design can be improved to mitigate the fault, applying the best practices of the [AWS Well-Architected Reliability pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html). Additional guidance and resources can be found in the [AWS Builder’s Library](https://aws.amazon.com/builders-library/), which hosts articles about how to [improve your health checks](https://aws.amazon.com/builders-library/implementing-health-checks/) or [employ retries with backoff in your application code](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/), among others.

       After these changes have been implemented, run the experiment again (shown by the dotted line in the chaos engineering flywheel) to determine their effectiveness. If the verify step indicates the hypothesis holds true, then the workload will be in steady state, and the cycle continues.

1.  Run experiments regularly.

    A chaos experiment is a cycle, and experiments should be run regularly as part of chaos engineering. After a workload meets the experiment’s hypothesis, the experiment should be automated to run continually as a regression part of your CI/CD pipeline. To learn how to do this, see this blog on [how to run AWS FIS experiments using AWS CodePipeline](https://aws.amazon.com/blogs/architecture/chaos-testing-with-aws-fault-injection-simulator-and-aws-codepipeline/). This lab on recurrent [AWS FIS experiments in a CI/CD pipeline](https://chaos-engineering.workshop.aws/en/030_basic_content/080_cicd.html) allows you to work hands-on.

    Fault injection experiments are also a part of game days (see [REL12-BP05 Conduct game days regularly](rel_testing_resiliency_game_days_resiliency.md)). Game days simulate a failure or event to verify systems, processes, and team responses. The purpose is to actually perform the actions the team would perform as if an exceptional event happened.

1.  Capture and store experiment results.

   Results for fault injection experiments must be captured and persisted. Include all necessary data (such as time, workload, and conditions) to be able to later analyze experiment results and trends. Examples of results might include screenshots of dashboards, CSV dumps from your metric’s database, or a hand-typed record of events and observations from the experiment. [Experiment logging with AWS FIS](https://docs.aws.amazon.com/fis/latest/userguide/monitoring-logging.html) can be part of this data capture.

## Resources
### Related Best Practices
- [REL08-BP03 Integrate resiliency testing as part of your deployment](rel_tracking_change_management_resiliency_testing.md)
- [REL13-BP03 Test disaster recovery implementation to validate the implementation](rel_planning_for_recovery_dr_tested.md)
### Related Documents
- [What is AWS Fault Injection Service?](https://docs.aws.amazon.com/fis/latest/userguide/what-is.html)
- [What is AWS Resilience Hub?](https://docs.aws.amazon.com/resilience-hub/latest/userguide/what-is.html)
- [Principles of Chaos Engineering](https://principlesofchaos.org/)
- [Chaos Engineering: Planning your first experiment](https://medium.com/the-cloud-architect/chaos-engineering-part-2-b9c78a9f3dde)
- [Resilience Engineering: Learning to Embrace Failure](https://queue.acm.org/detail.cfm?id=2371297)
- [Chaos Engineering stories](https://github.com/ldomb/ChaosEngineeringPublicStories)
- [Avoiding fallback in distributed systems](https://aws.amazon.com/builders-library/avoiding-fallback-in-distributed-systems/)
- [Canary Deployment for Chaos Experiments](https://medium.com/the-cloud-architect/chaos-engineering-q-a-how-to-safely-inject-failure-ced26e11b3db)
### Related Videos
- [AWS re:Invent 2020: Testing resiliency using chaos engineering (ARC316)](https://www.youtube.com/watch?v=OlobVYPkxgg)
- [AWS re:Invent 2019: Improving resiliency with chaos engineering (DOP309-R1)](https://youtu.be/ztiPjey2rfY)
- [AWS re:Invent 2019: Performing chaos engineering in a serverless world (CMY301)](https://www.youtube.com/watch?v=vbyjpMeYitA)

 ** Related tools: **
- [AWS Fault Injection Service](https://aws.amazon.com/fis/)
- AWS Marketplace: [Gremlin Chaos Engineering Platform](https://aws.amazon.com/marketplace/pp/prodview-tosyg6v5cyney)
- [Chaos Toolkit](https://chaostoolkit.org/)
- [Chaos Mesh](https://chaos-mesh.org/)
- [Litmus](https://litmuschaos.io/)
