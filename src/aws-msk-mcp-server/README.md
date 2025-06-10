# AWS Labs aws-msk MCP Server

An AWS Labs Model Context Protocol (MCP) server for aws-msk

## Instructions

Instructions for using this aws-msk MCP server. This can be used by clients to improve the LLM's understanding of available tools, resources, etc. It can be thought of like a 'hint' to the model. For example, this information MAY be added to the system prompt. Important to be clear, direct, and detailed.

## TODO (REMOVE AFTER COMPLETING)

* [ ] Optionally add an ["RFC issue"](https://github.com/awslabs/mcp/issues) for the community to review
* [ ] Generate a `uv.lock` file with `uv sync` -> See [Getting Started](https://docs.astral.sh/uv/getting-started/)
* [ ] Remove the example tools in `./awslabs/aws_msk_mcp_server/server.py`
* [ ] Add your own tool(s) following the [DESIGN_GUIDELINES.md](https://github.com/awslabs/mcp/blob/main/DESIGN_GUIDELINES.md)
* [ ] Keep test coverage at or above the `main` branch - NOTE: GitHub Actions run this command for CodeCov metrics `uv run --frozen pytest --cov --cov-branch --cov-report=term-missing`
* [ ] Document the MCP Server in this "README.md"
* [ ] Add a section for this aws-msk MCP Server at the top level of this repository "../../README.md"
* [ ] Create the "../../doc/servers/aws-msk-mcp-server.md" file with these contents:

    ```markdown
    ---
    title: aws-msk MCP Server
    ---

    {% include "../../src/aws-msk-mcp-server/README.md" %}
    ```
  
* [ ] Reference within the "../../doc/index.md" like this:

    ```markdown
    ### aws-msk MCP Server
    
    An AWS Labs Model Context Protocol (MCP) server for aws-msk
    
    **Features:**
    
    - Feature one
    - Feature two
    - ...

    Instructions for using this aws-msk MCP server. This can be used by clients to improve the LLM's understanding of available tools, resources, etc. It can be thought of like a 'hint' to the model. For example, this information MAY be added to the system prompt. Important to be clear, direct, and detailed.
    
    [Learn more about the aws-msk MCP Server](servers/aws-msk-mcp-server.md)
    ```

* [ ] Submit a PR and pass all the checks
