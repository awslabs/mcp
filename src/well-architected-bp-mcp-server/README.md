# AWS Well-Architected Best Practices MCP Server

A Model Context Protocol (MCP) server providing direct access to AWS Well-Architected Framework Best Practices across all six pillars and specialized lenses.

## Overview

This server provides a single source of truth for AWS Well-Architected Best Practices, making it easy for AI assistants and agents to access, search, and recommend best practices without web scraping or incomplete data.

## Features

- **Complete Best Practices Coverage**: All 300+ best practices from the Well-Architected Framework
- **Six Pillars**: Operational Excellence, Security, Reliability, Performance Efficiency, Cost Optimization, Sustainability
- **Specialized Lenses**: Including Generative AI lens
- **Structured Data**: Each best practice includes ID, title, description, outcome, risk level, related practices, and documentation links
- **Search & Filter**: Find best practices by pillar, risk level, area, or keyword

## Installation

```bash
# Using uvx (recommended)
uvx awslabs.well-architected-bp-mcp-server@latest

# Using pip
pip install awslabs.well-architected-bp-mcp-server
```

## Configuration

### Amazon Q CLI

Add to `~/.aws/amazonq/mcp.json`:

```json
{
  "mcpServers": {
    "well-architected-bp": {
      "command": "uvx",
      "args": ["awslabs.well-architected-bp-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

### Cursor / Cline / VS Code

Add to `.cursor/mcp.json`, `cline_mcp_settings.json`, or `.vscode/mcp.json`:

```json
{
  "mcpServers": {
    "well-architected-bp": {
      "command": "uvx",
      "args": ["awslabs.well-architected-bp-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

## Available Tools

### `search_best_practices`
Search and filter best practices across all pillars and lenses.

**Parameters:**
- `pillar` (optional): Filter by pillar (OPERATIONAL_EXCELLENCE, SECURITY, RELIABILITY, PERFORMANCE_EFFICIENCY, COST_OPTIMIZATION, SUSTAINABILITY)
- `risk` (optional): Filter by risk level (HIGH, MEDIUM, LOW)
- `lens` (optional): Filter by lens (FRAMEWORK, GENERATIVE_AI)
- `keyword` (optional): Search in title and description
- `area` (optional): Filter by practice area

**Example:**
```
Search for high-risk security best practices
```

### `get_best_practice`
Get detailed information about a specific best practice by ID.

**Parameters:**
- `id` (required): Best practice ID (e.g., "SEC01-BP01")

**Example:**
```
Get details for SEC01-BP01
```

### `list_pillars`
List all available pillars with their best practice counts.

### `get_related_practices`
Get all best practices related to a specific practice ID.

**Parameters:**
- `id` (required): Best practice ID

## Use Cases

- **Architecture Reviews**: Quickly reference relevant best practices during design reviews
- **Security Assessments**: Find all high-risk security practices for compliance checks
- **Cost Optimization**: Identify cost optimization opportunities across workloads
- **Training & Workshops**: Provide complete, accurate best practice information
- **Automated Recommendations**: Enable AI agents to suggest appropriate best practices

## Data Source

Best practices are sourced from the official AWS Well-Architected Framework documentation and updated regularly to ensure accuracy.

## License

Apache-2.0
