# AWS Well-Architected Best Practices MCP Server

A Model Context Protocol (MCP) server providing offline access to AWS Well-Architected Framework Best Practices across all six pillars and the Generative AI lens.

## Overview

This server provides a single source of truth for AWS Well-Architected Best Practices, making it easy for AI assistants and agents to access, search, and recommend best practices without web scraping or API calls. All 356 best practices are served from local data with full implementation guidance.

## Features

- **356 Best Practices**: Complete coverage across the Well-Architected Framework and Generative AI lens
- **Six Pillars**: Operational Excellence, Security, Reliability, Performance Efficiency, Cost Optimization, Sustainability
- **Full Implementation Guidance**: 307 detailed markdown reference documents with implementation steps, anti-patterns, and resources
- **57 WAR Questions**: Navigate best practices using the formal Well-Architected Review question structure
- **Full-Text Search**: Search across all implementation guidance, not just titles
- **Offline/Zero-Latency**: All data served from in-memory indexes built at startup

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

Search and filter best practices across all pillars and lenses. Returns paginated results.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `pillar` | No | OPERATIONAL_EXCELLENCE, SECURITY, RELIABILITY, PERFORMANCE_EFFICIENCY, COST_OPTIMIZATION, SUSTAINABILITY |
| `risk` | No | HIGH, MEDIUM, LOW |
| `lens` | No | FRAMEWORK, GENERATIVE_AI |
| `keyword` | No | Search in title and description |
| `area` | No | Filter by practice area |
| `max_results` | No | Results per page (default 20, max 50) |
| `offset` | No | Pagination offset (default 0) |

### `search_content`

Full-text search across all 307 implementation guidance documents. Use this to find best practices that mention specific AWS services, patterns, or techniques.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `query` | Yes | Text to search for (case-insensitive) |
| `pillar` | No | Filter results by pillar |
| `section` | No | Search only in: desired_outcome, anti_patterns, implementation_guidance, implementation_steps, resources |
| `max_results` | No | Max results (default 10, max 50) |

### `get_best_practice`

Get summary for a specific best practice by ID.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `id` | Yes | Best practice ID (e.g., "SEC01-BP01") |

### `get_best_practice_full`

Get complete markdown content including implementation steps, related documents, videos, and examples.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `id` | Yes | Best practice ID |
| `section` | No | Return only a specific section: desired_outcome, anti_patterns, implementation_guidance, implementation_steps, resources |

### `list_questions`

List all 57 Well-Architected Review questions organized by pillar. These are the questions used in a formal WAR.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `pillar` | No | Filter by pillar |

### `get_practices_for_question`

Find all best practices that answer a specific Well-Architected Review question. Results ordered by risk (HIGH first).

| Parameter | Required | Description |
|-----------|----------|-------------|
| `question` | Yes | Question text or keyword (partial match, case-insensitive) |

### `get_anti_patterns`

Extract anti-patterns (what NOT to do) for a specific practice, pillar, or risk level.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `id` | No | Specific best practice ID |
| `pillar` | No | Filter by pillar |
| `risk` | No | Filter by risk level |

### `list_pillars`

List all pillars with detailed metadata including practice counts, risk distribution, areas, and question counts.

### `get_related_practices`

Get all best practices related to a specific practice ID (cross-pillar connections).

| Parameter | Required | Description |
|-----------|----------|-------------|
| `id` | Yes | Best practice ID |

### `well_architected_framework_review`

Get a comprehensive framework overview with all pillars, high-risk practices, and assessment guidance.

## Recommended Workflow for Architecture Reviews

1. **Start with questions**: Use `list_questions` to see WAR questions by pillar
2. **Find practices**: Use `get_practices_for_question` to find BPs for each question
3. **Deep dive**: Use `get_best_practice_full` for implementation guidance
4. **Check anti-patterns**: Use `get_anti_patterns` to identify what to avoid
5. **Follow connections**: Use `get_related_practices` for cross-pillar links
6. **Search by service**: Use `search_content` to find practices mentioning specific AWS services

## Use Cases

- **Architecture Reviews**: Navigate by WAR questions and get implementation guidance
- **Security Assessments**: Find all high-risk security anti-patterns
- **Cost Optimization**: Search for cost-related implementation guidance
- **GenAI Workloads**: Review Generative AI lens best practices
- **Training & Workshops**: Provide complete, accurate best practice information
- **Automated Recommendations**: Enable AI agents to suggest appropriate best practices

## Data Source

Best practices are sourced from the official AWS Well-Architected Framework documentation (v13) and include the Generative AI lens. Updated regularly to ensure accuracy.

## License

Apache-2.0
