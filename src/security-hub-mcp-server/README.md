# Security Hub MCP Server

A Model Context Protocol (MCP) server for analyzing security findings in AWS Security Hub.

You can analyze your issues with prompts like:

> Identify the most important issues in Security Hub for AWS account ID 12345679012. Security Hub is enabled in region us-east-1.

Or filter by severity:

> What are the Security Hub issues with severity critical in account 12345679012?

Or several criteria, including custom filters:

> Get Security Hub findings with the following parameters (max results: 5):
> * region: us-east-1
> * severity: CRITICAL
> * workflow status: NEW
> * custom_filters: {'ResourceType': [{'Comparison': 'EQUALS', 'Value': 'AwsAccount'}]}

The `get_findings` tool supports the following parameters:

* `region` (required)
* `aws_account_id` (optional)
* `severity` (optional)
* `workflow_status` (optional)
*  `custom_filters` (optional)

`custom_filters` should be specified as a dictionary in the same format as the `Filters` key of the Security Hub
[`GetFindings` API](https://docs.aws.amazon.com/securityhub/1.0/APIReference/API_GetFindings.html). A filter specified
in `custom_filters` overrides a filter specified as a named parameter. So if you specify `severity` directly and in
`custom_filters`, the value in `custom_filters` will be used.

<div>
    <a href="https://www.loom.com/share/dd521aa1ec934137af8c4981a61b0410">
      <p>Here's a little demo of the POC 🚀 - Watch Video</p>
    </a>
    <a href="https://www.loom.com/share/dd521aa1ec934137af8c4981a61b0410">
      <img style="max-width:300px;" src="https://cdn.loom.com/sessions/thumbnails/dd521aa1ec934137af8c4981a61b0410-fb7d326efbf8252a-full-play.gif">
    </a>
  </div>

## Possible Next Steps

The near term goal is to make the `get_findings` tool more useful and reliable.

For utility, this includes:

* 🚧 support filtering issues by date created/updated/observed, severity, workflow status
* ✅ support querying with user-supplied filters, because the [set of supported Security Hub issue filters is massive](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/securityhub/client/get_findings.html)
* ✅ support pagination and limits on maximum number of issues retrieved

For reliability, this may include:

* creating [prompts](https://modelcontextprotocol.io/docs/concepts/prompts#dynamic-prompts) and tools to help select the intended issues
