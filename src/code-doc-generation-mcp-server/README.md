# AWS Labs Code Documentation Generation MCP Server

[![smithery badge](https://smithery.ai/badge/@awslabs/code-doc-generation-mcp-server)](https://smithery.ai/server/@awslabs/code-doc-generation-mcp-server)

A Model Context Protocol (MCP) server that automatically generates comprehensive documentation for code repositories. This server analyzes repository structure, identifies key components, and creates appropriate documentation with AWS architecture diagrams.

## Features

- **Automated Documentation Generation**: Creates comprehensive documentation based on repository analysis
- **AWS Architecture Diagram Integration**: Automatically generates AWS architecture diagrams using ai3-diagrams-expert MCP server
- **Multiple Document Types**: Generates README, API, Backend, Frontend, and other specialized documentation
- **Project Analysis**: Identifies project type, architecture, and key features
- **Interactive Documentation Creation**: Guides AI assistants through repository analysis and documentation creation

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.10`
3. Install `repomix` using `pip install repomix>=0.2.6`

## Installation

This MCP server can be added to your AWS AI assistants via the appropriate MCP configuration file:

```json
{
  "mcpServers": {
    "awslabs.code-doc-generation-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.code-doc-generation-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Core Concepts

### DocumentationContext

The `DocumentationContext` class is a central component of the document generation workflow. It maintains the state and configuration of the documentation process throughout its lifecycle.

Key attributes:
- `project_name`: Name of the project being documented
- `working_dir`: Working directory for the project (source code location)
- `repomix_path`: Path where documentation files will be generated (typically `{project_root}/generated-docs`)
- `status`: Current status of the documentation process (e.g., 'initialized', 'ready_to_plan', 'structure_ready')
- `current_step`: Current step in the documentation workflow (e.g., 'analysis', 'planning', 'generation')
- `analysis_result`: Contains the ProjectAnalysis with project metadata, structure, and features

The DocumentationContext is created after the initial repository analysis and is passed between the different documentation tools to maintain state and configuration throughout the process.

## Documentation Process

### 1. Prepare Repository

First step: Extract directory structure from the repository.

```python
await prepare_repository(project_root='/path/to/project')
```

Returns a basic ProjectAnalysis that you must fill out with:
- `project_type`: Type of project based on code analysis
- `features`: Key capabilities and functions
- `file_structure`: Project organization with directories
- `dependencies`: Project dependencies and versions
- `primary_languages`: Programming languages used
- `apis` (optional): API interface details
- `backend` (optional): Backend implementation details
- `frontend` (optional): Frontend implementation details

### 2. Create Context

Second step: Create documentation context from your analysis.

```python
doc_context = await create_context(
    project_root='/path/to/project',
    analysis=project_analysis  # Your completed analysis
)
```

### 3. Plan Documentation

Third step: Create documentation plan based on the context.

```python
plan = await plan_documentation(doc_context=doc_context)
```

Returns a DocumentationPlan with:
- Document structure and organization
- Document specifications with sections

### 4. Generate Documentation

Final step: Generate documentation files.

```python
docs = await generate_documentation(plan=plan, doc_context=doc_context)
```

Returns a list of GeneratedDocument objects for you to fill with content.

## Integration with Other MCP Servers

This MCP server is designed to work seamlessly with:

- **AWS Diagram MCP Server**: For generating AWS architecture diagrams
- **AWS CDK MCP Server**: For documenting CDK infrastructure code
- **AWS Documentation MCP Server**: For incorporating AWS best practices

# Code Documentation Generation MCP Server

An AWS Labs Model Context Protocol (MCP) server that helps generate comprehensive documentation for code repositories.

## Overview

The Code Documentation Generation MCP Server automates the creation of high-quality technical documentation for software projects. It analyzes repository structure, code organization, and key components to produce well-structured documentation that follows best practices.

## Features

- **Repository Analysis**: Automatically analyzes project structure using repomix to understand code organization
- **Project Context Creation**: Creates a documentation context that captures the essence of the project
- **Documentation Planning**: Intelligently determines which documentation files are needed based on project type
- **Documentation Generation**: Generates documentation templates with appropriate sections for Cline to fill with content
- **Architecture Diagram Integration**: Includes placeholders for architecture diagrams that can be visualized using the AWS Diagram MCP Server

## Tools

### Prepare Repository

Prepares the repository for documentation by extracting directory structure:

```python
async def prepare_repository(
    project_root: str = Field(..., description='Path to the code repository'),
    ctx: Context = None,
) -> ProjectAnalysis
```

This tool:
1. Extracts directory structure from the repository
2. Returns an EMPTY ProjectAnalysis for Cline to fill out
3. Provides directory structure in file_structure["directory_structure"]

### Create Context

Creates a documentation context from project analysis:

```python
async def create_context(
    project_root: str = Field(..., description='Path to the code repository'),
    analysis_result: ProjectAnalysis = Field(..., description='Analysis result from prepare_repository'),
    ctx: Context = None,
) -> DocumentationContext
```

This creates a DocumentationContext object with project information and analysis results.

### Plan Documentation

Creates a documentation plan based on analysis:

```python
async def plan_documentation(
    doc_context: DocumentationContext,
    ctx: Context,
) -> DocumentationPlan
```

Using the analysis, this determines what documentation types are needed and creates an appropriate documentation structure.

### Generate Documentation

Generates documentation content based on the plan:

```python
async def generate_documentation(
    plan: DocumentationPlan,
    doc_context: DocumentationContext,
    ctx: Context,
) -> List[GeneratedDocument]
```

This generates document structures with empty sections for Cline to fill with content.

## Usage

```python
# Prepare the repository
analysis = await prepare_repository(project_root='/path/to/repository')

# Create documentation context
doc_context = await create_context(project_root='/path/to/repository', analysis_result=analysis)

# Plan documentation
plan = await plan_documentation(doc_context=doc_context)

# Generate documentation
documents = await generate_documentation(plan=plan, doc_context=doc_context)

# Fill documentation with content
# (Cline does this part based on the repository analysis)
```

## Requirements

- Python 3.10+
- repomix tool for repository analysis

## TODOs (REMOVE AFTER COMPLETING)

* [ ] Optionally add an ["RFC issue"](https://github.com/awslabs/mcp/issues) for the community to review
* [x] Generate a `uv.lock` file with `uv sync` -> See [Getting Started](https://docs.astral.sh/uv/getting-started/)
* [x] Remove the example tools in `./awslabs/code_doc_generation_mcp_server/server.py`
* [x] Add your own tool(s) following the [DESIGN_GUIDELINES.md](https://github.com/awslabs/mcp/blob/main/DESIGN_GUIDELINES.md)
* [x] Keep test coverage at or above the `main` branch - NOTE: GitHub Actions run this command for CodeCov metrics `uv run --frozen pytest --cov --cov-branch --cov-report=term-missing`
* [x] Document the MCP Server in this "README.md"
* [x] Add a section for this code-doc-generation MCP Server at the top level of this repository "../../README.md"
* [x] Create the "../../doc/servers/code-doc-generation-mcp-server.md" file with these contents:

    ```markdown
    ---
    title: code-doc-generation MCP Server
    ---

    {% include "../../src/code-doc-generation-mcp-server/README.md" %}
    ```
  
* [x] Reference within the "../../doc/index.md" like this:

    ```markdown
    ### code-doc-generation MCP Server
    
    An AWS Labs Model Context Protocol (MCP) server for code-doc-generation
    
    **Features:**
    
    - Repository analysis and structure extraction
    - Documentation planning based on project type
    - Documentation generation with appropriate templates
    - Architecture diagram integration

    The Code Documentation Generation MCP server helps Cline analyze code repositories and generate comprehensive documentation following best practices.
    
    [Learn more about the code-doc-generation MCP Server](servers/code-doc-generation-mcp-server.md)
    ```

* [ ] Submit a PR and pass all the checks

## Contributing

Contributions to the Code Documentation Generation MCP Server are welcome. Please follow the [contributing guidelines](https://github.com/awslabs/mcp/blob/main/CONTRIBUTING.md) in the main MCP repository.

## License

This project is licensed under the Apache License, Version 2.0. See the [LICENSE](LICENSE) file for details.
