# Migration Guide: AWS Support MCP Server to AWS MCP Server

This guide helps you migrate from `awslabs.aws-support-mcp-server` to the [AWS MCP Server](https://github.com/aws/agent-toolkit-for-aws), part of the Agent Toolkit for AWS.

## Why We're Deprecating

The AWS Support MCP Server registered 11 tools, and each one made one AWS Support API call. Four of them open, reply to, or resolve a case, or upload attachments for one (`CreateCase`, `AddCommunicationToCase`, `ResolveCase`, and `AddAttachmentsToSet`). The other seven read cases, communications, and attachments, and look up the codes, languages, and support hours a new case needs. Around those calls, the server mapped 42 service code aliases (such as `ecs` to `ec2-container-service`), checked email addresses, issue types, and language codes, base64-decoded attachment data, and rebuilt the responses with a fixed set of fields. The AWS MCP Server makes the same calls through its `run_script` tool, which executes sandboxed Python that calls AWS APIs through its built-in `call_boto3` helper, using your own IAM credentials. It also reaches the parts of the Support API this server didn't have, such as presigned attachment download links and the uploads for files larger than 5 MB.

No Agent Skill in the Agent Toolkit for AWS covers AWS Support cases, so there's no skill to install for it.

## Installing the Replacement

### Configuration

```json
{
  "mcpServers": {
    "aws": {
      "command": "uvx",
      "args": [
        "mcp-proxy-for-aws-cli@latest",
        "https://aws-mcp.us-east-1.api.aws/mcp",
        "--metadata",
        "AWS_REGION=us-east-1"
      ]
    }
  }
}
```

Support cases are global, and the Support API has endpoints in US East (N. Virginia), US West (Oregon), and Europe (Ireland), so use `region_name="us-east-1"` in each `call_boto3` call whatever Region your workloads run in. To use a named AWS profile, add an `env` block to the server entry:

```json
"env": { "AWS_MCP_PROXY_PROFILES": "<profile_name>" }
```

Your identity needs the same permissions the old server needed:

- `support:CreateCase`, `support:DescribeCases`, `support:DescribeCommunications`, `support:AddCommunicationToCase`, `support:ResolveCase`, `support:AddAttachmentsToSet`, and `support:DescribeAttachment`
- `support:DescribeServices`, `support:DescribeSeverityLevels`, `support:DescribeCreateCaseOptions`, and `support:DescribeSupportedLanguages`

The AWS managed policy `AWSSupportAccess` grants all of them (`support:*`). To let an agent read cases without opening, answering, or resolving them, grant only the `Describe*` actions, or deny `support:CreateCase`, `support:AddCommunicationToCase`, `support:ResolveCase`, and `support:AddAttachmentsToSet`.

The account also needs a support plan that includes the Support API: Business Support+, Enterprise Support, or Unified Operations, or, until the account moves to one of those, Business Support or Enterprise On-Ramp. On any other plan, every Support API call fails with `SubscriptionRequiredException`, through the old server and through `run_script` alike. See [About the AWS Support API](https://docs.aws.amazon.com/awssupport/latest/user/about-support-api.html).

For setup details, see [Getting started with the AWS MCP Server](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started-aws-mcp-server.html).

## Tool-by-Tool Migration

With the AWS MCP Server, ask your agent to do the same job and it makes the equivalent call through `run_script`. Inside `run_script`, AWS APIs are called with the built-in `call_boto3` helper, which takes the service name, the API operation name (in PascalCase, as in the API reference), and a dict of request parameters, and returns the response. The old tools reshaped the responses: `describe_services` and `describe_severity_levels` returned objects keyed by code, and the case and communication tools rebuilt each item from a fixed list of fields. `call_boto3` returns the response as AWS Support sends it, such as `{"cases": [...], "nextToken": ...}`.

To read your open cases with their full conversations, in place of `describe_support_cases` and `describe_communications`, the agent might run:

```python
cases = await call_boto3(
    service_name="support",
    operation_name="DescribeCases",
    region_name="us-east-1",
    params={"includeResolvedCases": False, "includeCommunications": False, "language": "en"},
)
result = []
for case in cases["cases"]:
    comms = await call_boto3(
        service_name="support",
        operation_name="DescribeCommunications",
        region_name="us-east-1",
        params={"caseId": case["caseId"]},
    )
    result.append(
        {
            "displayId": case["displayId"],
            "subject": case["subject"],
            "status": case["status"],
            "communications": [
                {"from": c["submittedBy"], "at": c["timeCreated"], "body": c["body"]}
                for c in comms["communications"]
            ],
        }
    )
result
```

A `run_script` call stops after 100 `call_boto3` calls, so with more than 99 open cases, read the communications a batch of cases at a time.

To find the codes for a new case, in place of `describe_services` and `describe_severity_levels`:

```python
services = await call_boto3(
    service_name="support",
    operation_name="DescribeServices",
    region_name="us-east-1",
    params={"language": "en"},
)
levels = await call_boto3(
    service_name="support",
    operation_name="DescribeSeverityLevels",
    region_name="us-east-1",
    params={"language": "en"},
)
result = {
    "services": [
        {"code": s["code"], "name": s["name"], "categories": [c["code"] for c in s["categories"]]}
        for s in services["services"]
        if "container" in s["name"].lower()
    ],
    "severityCodes": [level["code"] for level in levels["severityLevels"]],
}
result
```

And to open a case with a log file attached, in place of `add_attachments_to_set` and `create_support_case`:

```python
attachment_set = await call_boto3(
    service_name="support",
    operation_name="AddAttachmentsToSet",
    region_name="us-east-1",
    params={
        "attachments": [
            {
                "fileName": "deploy.log",
                "data": "2026-11-10T14:02:11Z ERROR task stopped: CannotPullContainerError\n",
            }
        ]
    },
)
case = await call_boto3(
    service_name="support",
    operation_name="CreateCase",
    region_name="us-east-1",
    params={
        "subject": "ECS tasks stop with CannotPullContainerError",
        "serviceCode": "ec2-container-service",
        "categoryCode": "general-guidance",
        "severityCode": "low",
        "issueType": "technical",
        "language": "en",
        "communicationBody": "Tasks in the web service stop at startup. The log is attached.",
        "attachmentSetId": attachment_set["attachmentSetId"],
    },
)
result = case["caseId"]
result
```

An attachment set holds up to three files of up to 5 MB each and expires one hour after it's created.

### Cases and communications

| Old tool | What it did | Replacement |
|----------|-------------|-------------|
| `create_support_case(subject, service_code, category_code, severity_code, communication_body, cc_email_addresses, language, issue_type, attachment_set_id)` | Refused the call if any `cc_email_addresses` entry failed its email pattern, if `issue_type` wasn't `technical`, `account-and-billing`, or `service-limit`, or if `language` wasn't one of `en`, `ja`, `zh`, `es`, `pt`, `fr`, `ko`, and `tr`. Then mapped `service_code` through its alias table, called `CreateCase`, and returned the `caseId` with a success message. | `call_boto3(service_name="support", operation_name="CreateCase", params={"subject": ..., "serviceCode": ..., "categoryCode": ..., "severityCode": ..., "communicationBody": ..., "issueType": ..., "language": ...})`, as in the third example |
| `describe_support_cases(case_id_list, display_id, after_time, before_time, include_resolved_cases, include_communications, language, max_results, next_token, format)` | Called `DescribeCases` with the filters given, except `max_results`, which it accepted and never sent. Rebuilt each case from a fixed field list, and failed the whole call with a validation error if any case had the status `customer-action-completed` or `all-open`, which its status list didn't include. `format="markdown"` returned only the first case. | `call_boto3(service_name="support", operation_name="DescribeCases", params={"caseIdList": [...], "afterTime": ..., "includeResolvedCases": ..., "includeCommunications": ..., "maxResults": ...})`, as in the first example. `maxResults` is 10 to 100. |
| `describe_communications(case_id, after_time, before_time, max_results, next_token)` | Called `DescribeCommunications`. It sent `max_results` as a string, so botocore refused every call that set it ("Invalid type for parameter maxResults"). It dropped each communication's `attachments` list, the one that includes files larger than 5 MB, and kept only `attachmentSet`. | `call_boto3(service_name="support", operation_name="DescribeCommunications", params={"caseId": ..., "afterTime": ..., "maxResults": 10})`, as in the first example |
| `add_communication_to_case(case_id, communication_body, cc_email_addresses, attachment_set_id)` | Checked the email addresses, then called `AddCommunicationToCase` | `call_boto3(service_name="support", operation_name="AddCommunicationToCase", params={"caseId": ..., "communicationBody": ..., "ccEmailAddresses": [...], "attachmentSetId": ...})` |
| `resolve_support_case(case_id)` | Called `ResolveCase` and returned `initialCaseStatus` and `finalCaseStatus` with a success message | `call_boto3(service_name="support", operation_name="ResolveCase", params={"caseId": ...})` |

### Attachments

| Old tool | What it did | Replacement |
|----------|-------------|-------------|
| `add_attachments_to_set(attachments, attachment_set_id)` | Base64-decoded each attachment's `data`, refused data that decoded to text that itself looked like base64 (a check for double encoding), and called `AddAttachmentsToSet` with the decoded bytes | `call_boto3(service_name="support", operation_name="AddAttachmentsToSet", params={"attachments": [{"fileName": ..., "data": ...}], "attachmentSetId": ...})`, with the file's text or bytes as `data`, as in the third example. botocore does the base64 encoding for the wire. |
| `describe_attachment(attachment_id)` | Called `DescribeAttachment` and returned the attachment as botocore parsed it, with the file content as bytes. Content that wasn't UTF-8 text, such as a PNG screenshot, failed with "Error serializing to JSON: invalid utf-8 sequence". | `call_boto3(service_name="support", operation_name="DescribeAttachment", params={"attachmentId": ...})`, which returns `data` as base64 text, or `GetAttachmentDownloadLink` with the same `attachmentId` for a presigned download URL that works for a file of any size |

### Codes and options for a new case

| Old tool | What it did | Replacement |
|----------|-------------|-------------|
| `describe_services(service_code_list, language, format)` | Mapped each code in `service_code_list` through its alias table, called `DescribeServices`, and returned an object keyed by service code with each service's name and categories. `format="markdown"` returned a Markdown list. | `call_boto3(service_name="support", operation_name="DescribeServices", params={"language": "en", "serviceCodeList": [...]})`, as in the second example |
| `describe_severity_levels(language, format)` | Called `DescribeSeverityLevels` and returned an object keyed by severity code. `format="markdown"` returned a Markdown list. | `call_boto3(service_name="support", operation_name="DescribeSeverityLevels", params={"language": "en"})`, as in the second example |
| `describe_create_case_options(service_code, language, category_code, issue_type)` | Mapped `service_code` through its alias table and called `DescribeCreateCaseOptions`. The tool marked `category_code` and `issue_type` optional, but the API requires both, so a call without them failed with `ParamValidationError` before it reached AWS. | `call_boto3(service_name="support", operation_name="DescribeCreateCaseOptions", params={"serviceCode": ..., "categoryCode": ..., "issueType": "technical", "language": "en"})` |
| `describe_supported_languages(service_code, category_code, issue_type)` | Mapped `service_code` through its alias table and called `DescribeSupportedLanguages`, with `issue_type` set to `technical` unless given | `call_boto3(service_name="support", operation_name="DescribeSupportedLanguages", params={"serviceCode": ..., "categoryCode": ..., "issueType": "technical"})` |

Because `run_script` exposes the full Support API, operations the old server never had, such as `GetAttachmentDownloadLink`, the large-file upload operations (`GetAttachmentUploadLinks`, `CompleteAttachmentUpload`, and `DescribeAttachmentUploadStatus`, for files up to 150 MB), and the Trusted Advisor operations (`DescribeTrustedAdvisorChecks` and the others), are also available.

### Environment variables and flags

| Old variable or flag | Replacement |
|----------------------|-------------|
| `AWS_REGION` (default `us-east-1`) | `region_name="us-east-1"` in each `call_boto3` call. In the `aws` partition, botocore sends every Support API call to the US East (N. Virginia) endpoint whatever Region it's given. |
| `AWS_PROFILE` | `AWS_MCP_PROXY_PROFILES` in the proxy's `env` block |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` | A profile through `AWS_MCP_PROXY_PROFILES`; the proxy signs requests with the standard AWS credential chain |
| `--debug`, `--log-file` | Not needed. They set the old server's log level and log file, and `--debug` turned on the request counts and timings in its `resource://diagnostics` resource. |
| `--port` | Not needed. The server read it but always ran over stdio. |

## What Improves

- **Case lists with every status.** `describe_support_cases` failed the whole call with a validation error when any case had the status `customer-action-completed` or `all-open`. `DescribeCases` returns every case with its status as AWS Support reports it.
- **Page size for communications.** `describe_communications` sent `max_results` as a string, so botocore refused every call that set it. `describe_support_cases` never sent `max_results` at all. Through `call_boto3`, `maxResults` reaches the API.
- **Customer service cases.** `create_support_case` refused `issue_type="customer-service"`, one of the two values the API reference lists for `issueType`.
- **Files that look like base64.** `add_attachments_to_set` refused, as double-encoded, any text file whose content used only base64 characters and decoded cleanly, such as a file holding a SHA-256 checksum. `call_boto3` sends the file's text unchanged.
- **Binary attachments.** `describe_attachment` couldn't return a file that wasn't UTF-8 text, such as a screenshot. `call_boto3` returns blob fields as base64 text, and `GetAttachmentDownloadLink` returns a presigned URL for a file of any size.
- **Attachments larger than 5 MB.** The old server could only use `AddAttachmentsToSet` (5 MB per file) and dropped the `attachments` list that names larger files. `run_script` reaches the upload and download link operations, and `DescribeCommunications` returns that list. The file parts go to presigned Amazon S3 URLs, so the upload itself needs a tool that can send HTTP requests.
- **AWS Support's own error messages.** For known error codes, the old server replaced AWS Support's message with fixed text, such as "Failed to authenticate with AWS Support API." for every `AccessDeniedException`. `run_script` returns a failed call in the same shape the old server did, a normal tool result with `"status": "error"` and no MCP `isError` flag, but its `error` field holds AWS Support's own error code and message, such as `SubscriptionRequiredException` with "Amazon Web Services Premium Support Subscription is required to use this service."

## Workflow Change

### Before (AWS Support Server)

1. Set `AWS_PROFILE` and start the server. Every tool is on, including `create_support_case`, `add_communication_to_case`, and `resolve_support_case`.
2. The agent picks a service code from the table in the server's instructions or calls `describe_services`, and the server maps short names such as `ecs` or `lambda` to the API's codes.
3. The agent calls the tool. If the call fails, the result still looks like a success, with `"status": "error"` and the server's message.

### After (AWS MCP Server)

1. Ask your agent about your cases, or ask it to open or answer one. It runs the Support API calls through `run_script` using your credentials.
2. The agent looks up service, category, and severity codes with `DescribeServices` and `DescribeSeverityLevels`, as in the second example, or uses the ones you give it.
3. IAM decides which Support actions the agent can take. Grant only the `Describe*` actions to keep it from opening, answering, or resolving cases.

## Summary of Gaps

| Feature | Status | Workaround |
|---------|--------|------------|
| 42 service code aliases, such as `ecs`, `s3`, `lambda`, and `fargate` | Not available | Call `DescribeServices` and pick the code from the list, as in the second example |
| A table of 22 common service codes and the five severity levels in the server's instructions | Not available | Call `DescribeServices` and `DescribeSeverityLevels`, as in the second example |
| Email address check on `cc_email_addresses` | Not available | Check the addresses before asking for the case; the API takes up to 10 |
| `issue_type` and `language` checks in `create_support_case` | Changed | The API reference lists `technical` and `customer-service` for `issueType` and the same eight language codes. To have AWS Support check a request without opening a case, add `"dryRun": True` to the `CreateCase` parameters; a valid request answers `DryRunOperationException`. |
| Base64 input for attachments, with a double-encoding check | Changed | Pass the file's text, or its bytes, as `data`; botocore encodes it |
| Markdown output (`format="markdown"`) for cases, services, and severity levels | Not available | Ask the agent to format the response |
| Fixed error messages for known error codes | Changed | `run_script` returns AWS Support's own error code and message in the `error` field of a normal tool result with `"status": "error"`, the same shape the old server used |
| Request counts and timings in `resource://diagnostics` (with `--debug`) | Not available | CloudTrail logs Support API calls; see [Logging AWS Support API calls with AWS CloudTrail](https://docs.aws.amazon.com/awssupport/latest/user/logging-using-cloudtrail.html) |

## Testing Notes

We tested on an account with a Basic support plan, which the Support API refuses with `SubscriptionRequiredException`. All 7 read-only tools over stdio and the matching `call_boto3` calls through `run_script` returned that error; the old server reported it as "AWS Support API access requires a Business, Enterprise On-Ramp, or Enterprise Support plan." That message is out of date: Business Support stopped taking new subscriptions on December 2, 2025 (see the [AWS Premium Support FAQs](https://aws.amazon.com/premiumsupport/faqs/)), and the plans that include the Support API today are Business Support+, Enterprise Support, and Unified Operations. The read-only examples above ran through `run_script` with the same result. The failures that happen before a request reaches AWS (`describe_communications` with `max_results`, and `describe_create_case_options` without `category_code` and `issue_type`) showed up live.

`CreateCase`, `AddCommunicationToCase`, and `ResolveCase` reach AWS Support staff, and `AddAttachmentsToSet` stores files for them, so we didn't send any of the four. We recorded the request each old tool built by stopping the call inside botocore, and checked the third example's parameters against the botocore model for the Support API. The behaviors that depend on a response, such as the case status and binary attachment failures, come from running the old server's code against recorded responses.

## What Deprecation Means

- The final release of `awslabs.aws-support-mcp-server` keeps working. It prints a `FutureWarning` at startup, and its server instructions and tool descriptions are marked deprecated.
- The package stays on PyPI and gets no further updates.
- Configurations that use `awslabs.aws-support-mcp-server@latest` get that final release.
- The source folder may later be removed from this repository, as earlier deprecated servers were.

## Removing the Old Server

Once you've verified the replacement meets your needs:

1. Remove `awslabs.aws-support-mcp-server` from your MCP configuration
2. Uninstall the package: `pip uninstall awslabs.aws-support-mcp-server`
