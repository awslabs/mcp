# Security Hub MCP Server

A Model Context Protocol (MCP) server for analyzing security findings in AWS Security Hub.

You can analyze your issues with prompts like:

> Identify the most important issues in Security Hub for AWS account ID 12345679012. Security Hub is enabled in region us-east-1.

Or filter by severity:

> What are the Security Hub issues with severity critical in account 12345679012?

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

* support filtering issues by date created/updated/observed or criticality
* see if we can open up querying with user-supplied filters, because the [set of supported Security Hub issue filters is massive](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/securityhub/client/get_findings.html)
* ✅ support pagination and limits on maximum number of issues retrieved

For reliablity, this may include:

* creating instructions and tools (to generate prompts) so that the intended issues are selected

Contributions welcome!
