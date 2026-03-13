# AWS GuardDuty MCP Server

A read-only Model Context Protocol (MCP) server for Amazon GuardDuty. It is designed for infosec workflows where an LLM needs structured access to GuardDuty findings for triage, enrichment, summarization, or downstream automation.

## Initial scope

- List GuardDuty detectors in a region
- List findings with optional severity and archived-state filters
- Fetch full finding payloads for selected finding IDs
- Return normalized, LLM-friendly models while preserving raw `resource` and `service` sections

## Why this server first

GuardDuty is a strong starting point for a security MCP set because it exposes high-signal detections that are already normalized by AWS. That makes it a practical bridge between AWS security telemetry and LLM-driven triage.

## Installation

```bash
uv tool install ./src/aws-guardduty-mcp-server
```

## AWS permissions

The AWS credentials used by this server need read access to GuardDuty:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "guardduty:ListDetectors",
        "guardduty:ListFindings",
        "guardduty:GetFindings"
      ],
      "Resource": "*"
    }
  ]
}
```

## Example MCP client configuration

```json
{
  "mcpServers": {
    "awslabs.aws-guardduty-mcp-server": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/src/aws-guardduty-mcp-server",
        "run",
        "awslabs.aws-guardduty-mcp-server"
      ],
      "env": {
        "AWS_PROFILE": "security-readonly",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

## Tooling model

Use `list_detectors` first if you do not already know the detector ID for the target region. Then use `list_findings` to page through findings and `get_findings` to retrieve the full payloads needed by the LLM.
