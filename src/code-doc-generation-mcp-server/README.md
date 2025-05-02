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

## TODO (REMOVE AFTER COMPLETING)

* [ ] Optionally add an ["RFC issue"](https://github.com/awslabs/mcp/issues) for the community to review
* [ ] Generate a `uv.lock` file with `uv sync` -> See [Getting Started](https://docs.astral.sh/uv/getting-started/)
* [ ] Remove the example tools in `./awslabs/code_doc_generation_mcp_server/server.py`
* [ ] Add your own tool(s) following the [DESIGN_GUIDELINES.md](https://github.com/awslabs/mcp/blob/main/DESIGN_GUIDELINES.md)
* [ ] Keep test coverage at or above the `main` branch - NOTE: GitHub Actions run this command for CodeCov metrics `uv run --frozen pytest --cov --cov-branch --cov-report=term-missing`
* [ ] Document the MCP Server in this "README.md"
* [ ] Add a section for this code-doc-generation MCP Server at the top level of this repository "../../README.md"
* [ ] Create the "../../doc/servers/code-doc-generation-mcp-server.md" file with these contents:

    ```markdown
    ---
    title: code-doc-generation MCP Server
    ---

    {% include "../../src/code-doc-generation-mcp-server/README.md" %}
    ```

* [ ] Reference within the "../../doc/index.md" like this:

    ```markdown
    ### code-doc-generation MCP Server

    An AWS Labs Model Context Protocol (MCP) server for code-doc-generation

    **Features:**

    - Feature one
    - Feature two
    - ...

    Instructions for using this code-doc-generation MCP server. This can be used by clients to improve the LLM's understanding of available tools, resources, etc. It can be thought of like a 'hint' to the model. For example, this information MAY be added to the system prompt. Important to be clear, direct, and detailed.

    [Learn more about the code-doc-generation MCP Server](servers/code-doc-generation-mcp-server.md)
    ```

* [ ] Submit a PR and pass all the checks
