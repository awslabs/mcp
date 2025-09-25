# AWS Labs Code Documentation Generation MCP Server

[![smithery badge](https://smithery.ai/badge/@awslabs/code-doc-gen-mcp-server)](https://smithery.ai/server/@awslabs/code-doc-gen-mcp-server)

A Model Context Protocol (MCP) server that automatically analyzes repository structure and generates comprehensive documentation for code projects. This server uses [repomix](https://github.com/yamadashy/repomix/tree/main) to extract project structure and creates tailored documentation based on project type.

## Architecture

### How the Server Works

The code-doc-gen-mcp-server follows this workflow:

1. **prepare_repository**:
   - Uses RepomixManager to analyze a project directory
   - Runs `repomix` to generate an XML representation of the repo
   - Extracts directory structure from this XML
   - Returns a ProjectAnalysis with the directory structure

2. **create_context**:
   - Creates a DocumentationContext with the ProjectAnalysis

3. **plan_documentation**:
   - Uses the directory structure from DocumentationContext
   - Creates a DocumentationPlan with document structure and sections

4. **generate_documentation**:
   - Generates document templates based on the plan

### Key Components

1. **RepomixManager**: Manages the execution of repomix and parses its XML output to extract directory structure
2. **DocumentationContext**: Central state container that tracks project info and documentation progress
3. **ProjectAnalysis**: Data structure containing analyzed project metadata (languages, dependencies, etc.)
4. **DocumentationPlan**: Structured plan for document generation with section outlines
5. **DocumentGenerator**: Creates actual document templates based on the plan

## Features

- **Project Structure Analysis**: Uses repomix to analyze repository structure and extract key components
- **Content Organization**: Creates appropriately structured documentation based on project type
- **Multiple Document Types**: Supports README, API docs, backend docs, frontend docs, and more
- **Integration with Other MCP Servers**: Works with AWS Diagram MCP server
- **Custom Document Templates**: Templates for different document types with appropriate sections

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. Install `repomix` using `pip install repomix>=0.2.6`

## Installation

| Cursor | VS Code |
|:------:|:-------:|
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.code-doc-gen-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuY29kZS1kb2MtZ2VuLW1jcC1zZXJ2ZXJAbGF0ZXN0IiwiZW52Ijp7IkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Code%20Documentation%20Generator%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.code-doc-gen-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

This MCP server can be added to your AWS AI assistants via the appropriate MCP configuration file:

```json
{
  "mcpServers": {
    "awslabs.code-doc-gen-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.code-doc-gen-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```
### Windows Installation

For Windows users, the MCP server configuration format is slightly different:

```json
{
  "mcpServers": {
    "awslabs.code-doc-gen-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.code-doc-gen-mcp-server@latest",
        "awslabs.code-doc-gen-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```


## Core Concepts

### DocumentationContext

The `DocumentationContext` class maintains the state of the documentation process throughout its lifecycle:

- `project_name`: Name of the project being documented
- `working_dir`: Working directory for the project (source code location)
- `repomix_path`: Path where documentation files will be generated
- `status`: Current status of the documentation process
- `current_step`: Current step in the documentation workflow
- `analysis_result`: Contains the ProjectAnalysis with project metadata

### ProjectAnalysis

The `ProjectAnalysis` class contains detailed information about the project:

- `project_type`: Type of project (e.g., "Web Application", "CLI Tool")
- `features`: Key capabilities and functions of the project
- `file_structure`: Project organization with directory structure
- `dependencies`: Project dependencies with versions
- `primary_languages`: Programming languages used in the project
- `apis` (optional): API endpoint details
- `backend` (optional): Backend implementation details
- `frontend` (optional): Frontend implementation details

## Tools

### prepare_repository

```python
async def prepare_repository(
    project_root: str = Field(..., description='Path to the code repository'),
    ctx: Context = None,
) -> ProjectAnalysis
```

This tool:
1. Extracts directory structure from the repository using repomix
2. Returns a ProjectAnalysis template for the MCP client to fill
3. Provides directory structure in file_structure["directory_structure"]

The MCP client then:
1. Reviews the directory structure
2. Uses read_file to examine key files
3. Fills out the ProjectAnalysis fields
4. Sets has_infrastructure_as_code=True if CDK/Terraform code is detected

### create_context

```python
async def create_context(
    project_root: str = Field(..., description='Path to the code repository'),
    analysis: ProjectAnalysis = Field(..., description='Completed ProjectAnalysis'),
    ctx: Context = None,
) -> DocumentationContext
```

Creates a DocumentationContext from the completed ProjectAnalysis.

### plan_documentation

```python
async def plan_documentation(
    doc_context: DocumentationContext,
    ctx: Context,
) -> DocumentationPlan
```

Creates a documentation plan based on the project analysis, determining what document types are needed and creating appropriate document structures.

### generate_documentation

```python
async def generate_documentation(
    plan: DocumentationPlan,
    doc_context: DocumentationContext,
    ctx: Context,
) -> List[GeneratedDocument]
```

Generates document structures with sections for the MCP client to fill with content.

## Integration with Other MCP Servers

This MCP server is designed to work with:

- **AWS Diagram MCP Server**: For generating architecture diagrams
- **AWS CDK MCP Server**: For documenting CDK infrastructure code

## License

This project is licensed under the Apache License, Version 2.0. See the [LICENSE](https://github.com/awslabs/mcp/blob/main/src/code-doc-gen-mcp-server/LICENSE) file for details.
