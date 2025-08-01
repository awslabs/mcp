# AWS QuickSight Dashboards MCP Server

Model Context Protocol (MCP) server for AWS QuickSight Create Dashboard Experience

This MCP server provides tools to create polished dashboards in AWS QuickSight.

## Features

- **Create Dashboards**: Create empty dashboards linked to an existing dataset
- **Create Sheets**: Create empty sheets within a dashboard
- **Create Bar Charts**: Create bar charts
- **Create Line Charts**: Create line charts
- **Create Tables**: Create tables
- **Create Pivot Tables**: Create pivot tables
- **Create KPIs**: Create KPIs
- **Create Highcharts**: Create Highcharts
- **Delete Sheets**: Delete sheets along with any visuals within that sheet
- **Delete Visuals**: Delete a specific visual regardless of type
- **Edit Visuals**: Edit properties of a visual (* Since we are removing & re-creating the visuals, should this be a separate bullet?)
- **Edit Layouts**: Edit positions of visuals
- **Edit Visual Size**: Edit size of a visual

## Prerequisites

### Installation Requirements

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python 3.10 or newer using `uv python install 3.10` (or a more recent version)
3. Install `AWS CLI` (Needed for connecting to Bedrock model and QuickSight access)


## Installation

First of all, clone / download this repo

You have two options to interact with this server:

Option 1: Cline extension via VSCode

1. Install VScode
2. Install Cline extension
3. Click on the "MCP Servers" menu (between the "+" and history menu at the top)
4. Click "Installed" section
5. Click "Configure MCP Servers". This will lead you to a cline_mcp_settings.json file 
6. Configure the MCP server. Add the following json code:

```json
{
  "mcpServers": {
    "aws-quicksight-dashboards-mcp": {
      "disabled": true,
      "timeout": 60,
      "type": "stdio",
      "command": "/home/<your_username>/.local/bin/uv", // or to your uv directory
      "args": [
        "--directory",
        "<PATH/TO/THE/REPO>/mcp/src/aws-quicksight-dashboards-mcp-server/awslabs/aws_quicksight_dashboards_mcp_server",
        "run",
        "server.py"
      ],
      "env": {
        "AWS_ACCOUNT_ID": "your_AWS_account_id (usually in numbers)",
        "AWS_USERNAME": "your_QuickSight_username (exactly as shown under QuickSight account info including any slashes)"
      }
    }
  }
}
```
7. Save the file, and you should be able to see a new server in the "Installed" section of MCP Servers. (If not, restart vsCode)

Option 2: Q CLI

1. Follow this link to install Q CLI: https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/command-line-installing.html
2. Navigate to home/your_username/.aws/amazonq/mcp.json
    If mcp.json file does not exist, create one
3. Add the following JSON code:

```json
{
  "mcpServers": {
    "aws-quicksight-dashboards-mcp": {
      "disabled": true,
      "timeout": 60,
      "type": "stdio",
      "command": "/home/<your_username>/.local/bin/uv", // or to your uv directory
      "args": [
        "--directory",
        "<PATH/TO/THE/REPO>/mcp/src/aws-quicksight-dashboards-mcp-server/awslabs/aws_quicksight_dashboards_mcp_server",
        "run",
        "server.py"
      ],
      "env": {
        "AWS_ACCOUNT_ID": "your_AWS_account_id (usually in numbers)",
        "AWS_USERNAME": "your_QuickSight_username (exactly as shown under QuickSight account info including any slashes)"
      }
    }
  }
}
```

4. Restart terminal session 
5. Type "q chat" into your terminal and you should see a message like "aws_quicksight_dashboards_mcp loaded in 0.85 s"

## Basic Usage

Example:

- "Create a new dashboard titled 2025 Business Review using 2025 Sales Report dataset."
- "In the 2025 Business Review dashboard, add 4 KPIs regarding sales, profit, discount, and total quantity of sales."
- "Compare the profits between each region using bar charts."

