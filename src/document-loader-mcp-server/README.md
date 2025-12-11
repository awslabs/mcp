# Document Loader MCP Server

Model Context Protocol (MCP) server for document parsing and content extraction

This MCP server provides tools to parse and extract content from various document formats including PDF, Word documents, Excel spreadsheets, PowerPoint presentations, and images.

## Features

- **PDF Text Extraction**: Extract text content from PDF files using pdfplumber
- **Word Document Processing**: Convert DOCX/DOC files to markdown using markitdown
- **Excel Spreadsheet Reading**: Parse XLSX/XLS files and convert to markdown
- **PowerPoint Presentation Processing**: Extract content from PPTX/PPT files
- **Image Loading**: Load and display various image formats (PNG, JPG, GIF, BMP, TIFF, WEBP)

## Prerequisites

### Installation Requirements

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python 3.10 or newer using `uv python install 3.10` (or a more recent version)

## Installation

| Cursor | VS Code |
|:------:|:-------:|
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.document-loader-mcp-server&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyJhd3NsYWJzLmRvY3VtZW50LWxvYWRlci1tY3Atc2VydmVyQGxhdGVzdCJdLCJlbnYiOnsiRkFTVE1DUF9MT0dfTEVWRUwiOiJFUlJPUiJ9LCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Document%20Loader%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.document-loader-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

Configure the MCP server in your MCP client configuration:

```json
{
  "mcpServers": {
    "awslabs.document-loader-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.document-loader-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

For [Amazon Q Developer CLI](https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/command-line.html), add the MCP client configuration and tool command to the agent file in `~/.aws/amazonq/cli-agents`.

Example, `~/.aws/amazonq/cli-agents/default.json`

```json
{
  "mcpServers": {
    "awslabs.document-loader-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.document-loader-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Available Tools

- `read_document`: Extract content from various document formats by specifying file_path and file_type ('pdf', 'docx', 'doc', 'xlsx', 'xls', 'pptx', 'ppt')
- `read_image`: Load image files for LLM viewing and analysis

## Environment Variables

- `FASTMCP_LOG_LEVEL`: Set logging level (ERROR, INFO, DEBUG)

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/awslabs/mcp.git
cd mcp/src/document-loader-mcp-server

# Install dependencies
uv sync

# Install in development mode
uv pip install -e .
```

### Testing

```bash
# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=awslabs.document_loader_mcp_server
```

The test suite includes:

- Server functionality validation
- Document parsing tests with generated sample files
- Error handling verification

### Sample Documents

The test suite automatically generates sample documents for testing:

- PDF with multi-page content
- DOCX with formatted text and lists
- XLSX with multiple sheets and data
- PPTX with slides and content
- Various image formats

## Docker

You can also run this server in a Docker container:

```bash
docker build -t document-loader-mcp-server .
docker run -p 8000:8000 document-loader-mcp-server
```

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](https://github.com/awslabs/mcp/blob/main/src/document-loader-mcp-server/LICENSE) file for details.

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](https://github.com/awslabs/mcp/blob/main/CONTRIBUTING.md) for details.

## Support

For issues and questions, please use the [GitHub issue tracker](https://github.com/awslabs/mcp/issues).
