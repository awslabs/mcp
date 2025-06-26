# Local MCP Server for Amazon Q Business with anonymous mode

This is a simple local MCP server for Amazon Q Business, and it supports Amazon Q Business application created using [anonymous mode access](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/create-anonymous-application.html)

## Installation

This code is written using the [Python SDK for MCP](https://github.com/modelcontextprotocol/python-sdk). It uses [uv](https://docs.astral.sh/uv/) to manage the Python project.

If you need to install uv, use
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Initialize qbiz project
```bash
uv init amazon-qbusiness-anonymous-mcp-server
cd amazon-qbusiness-anonymous-mcp-server
```
Copy qbiz.py, README.md and requirements.txt to this directory.

Add requirements
```bash
uv add -r requirements.txt
```
Add the following to "mcpServers" in mcp.json.

```bash
"qbiz": {
        "command": "uv",
        "args": [
            "--directory",
            "<REPLACE-WITH-FULL-PATH-FOR-qbiz-mcp-server-DIRECTORY>",
            "run",
            "qbiz.py"
        ],
        "env": {
            "QBUSINESS_APPLICATION_ID":"<REPLACE-WITH-YOUR-AMAZON-Q-BUSINESS-APPLICATION-ID>",
            "AWS_REGION":"<REPLACE-WITH-YOUR-AWS-REGION>",
            "AWS_ACCESS_KEY_ID":"<REPLACE-WITH-YOUR-AWS-ACCESS-KEY>",
            "AWS_SECRET_ACCESS_KEY":"<REPLACE-WITH-YOUR-AWS-SECRET-ACCESS-KEY>",
            "AWS_SESSION_TOKEN":"<REPLACE-WITH-YOUR-AWS-SESSION-TOKEN>"
        }
    }
```
The Amazon Q Business (qbiz) MCP server supports qbiz_query tool that can be used to query the Amazon Q Business application pointed to by the QBUSINESS_APPLICATION_ID in mcp.json file.  
