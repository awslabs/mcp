---
id: "REL06-BP05"
title: "Analyze logs"
pillar: "Reliability"
risk_level: "MEDIUM"
capability: "How do you monitor workload resources?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_monitor_aws_resources_storage_analytics.html"
---

# REL06-BP05 Analyze logs

Collect log files and metrics histories and analyze these for
broader trends and workload insights.

Amazon CloudWatch Logs Insights supports
a [simple
yet powerful query language](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax.html) that you can use to analyze log
data. Amazon CloudWatch Logs also supports subscriptions that allow
data to flow seamlessly to Amazon S3 where you can use or Amazon Athena to query the data. It also supports queries on a large array
of formats.
See [Supported
SerDes and Data Formats](https://docs.aws.amazon.com/athena/latest/ug/supported-format.html) in the Amazon Athena User Guide for
more information. For analysis of huge log file sets, you can run an
Amazon EMR cluster to run petabyte-scale analyses.

There are a number of tools provided by AWS Partners and third
parties that allow for aggregation, processing, storage, and
analytics. These tools include New Relic, Splunk, Loggly, Logstash,
CloudHealth, and Nagios. However, outside generation of system and
application logs is unique to each cloud provider, and often unique
to each service.

An often-overlooked part of the monitoring process is data
management. You need to determine the retention requirements for
monitoring data, and then apply lifecycle policies accordingly.
Amazon S3 supports lifecycle management at the S3 bucket level. This
lifecycle management can be applied differently to different paths
in the bucket. Toward the end of the lifecycle, you can transition
data to Amazon Glacier for long-term storage, and then expiration
after the end of the retention period is reached. The S3
Intelligent-Tiering storage class is designed to optimize costs by
automatically moving data to the most cost-effective access tier,
without performance impact or operational overhead.

**Level of risk exposed if this best practice
is not established:** Medium

## Implementation guidance

- CloudWatch Logs Insights allows you to interactively search and
analyze your log data in Amazon CloudWatch Logs.

[Analyzing Log Data
with CloudWatch Logs Insights](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/using_cloudwatch_logs.html)
- [Amazon CloudWatch Logs Insights Sample Queries](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AnalyzingLogData.html)

- Use Amazon CloudWatch Logs to send logs to Amazon S3 where you can
use or Amazon Athena to query the data.

[How
do I analyze my Amazon S3 server access logs using Athena?](https://aws.amazon.com/premiumsupport/knowledge-center/analyze-logs-athena/)

Create an S3 lifecycle policy for your server access logs bucket. Configure
the lifecycle policy to periodically remove log files. Doing so reduces the amount
of data that Athena analyzes for each query.

[How Do I Create a
Lifecycle Policy for an S3 Bucket?](https://docs.aws.amazon.com/AmazonS3/latest/user-guide/create-lifecycle.html)

## Resources

**Related documents:**

- [Amazon CloudWatch Logs Insights Sample Queries](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax-examples.html)
- [Analyzing
Log Data with CloudWatch Logs Insights](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/using_cloudwatch_logs.html)
- [Debugging
with Amazon CloudWatch Synthetics and AWS X-Ray](https://aws.amazon.com/blogs/devops/debugging-with-amazon-cloudwatch-synthetics-and-aws-x-ray/)
- [How
Do I Create a Lifecycle Policy for an S3 Bucket?](https://docs.aws.amazon.com/AmazonS3/latest/user-guide/create-lifecycle.html)
- [How
do I analyze my Amazon S3 server access logs using
Athena?](https://aws.amazon.com/premiumsupport/knowledge-center/analyze-logs-athena/)
- [One
Observability Workshop](https://observability.workshop.aws/)
- [The
Amazon Builders' Library: Instrumenting distributed systems
for operational visibility](https://aws.amazon.com/builders-library/instrumenting-distributed-systems-for-operational-visibility/)
