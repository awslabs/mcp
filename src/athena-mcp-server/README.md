# AWS Labs Athena MCP Server

An AWS Labs Model Context Protocol (MCP) server for Athena

## Instructions

AWS Athena MCP Server provides tools to execute SQL queries against data stored in Amazon S3 using AWS Athena.

## TODO (REMOVE AFTER COMPLETING)

* [ ] Optionally add an ["RFC issue"](https://github.com/awslabs/mcp/issues) for the community to review
* [ ] Generate a `uv.lock` file with `uv sync` -> See [Getting Started](https://docs.astral.sh/uv/getting-started/)
* [ ] Remove the example tools in `./awslabs/athena_mcp_server/server.py`
* [ ] Add your own tool(s) following the [DESIGN_GUIDELINES.md](https://github.com/awslabs/mcp/blob/main/DESIGN_GUIDELINES.md)
* [ ] Keep test coverage at or above the `main` branch - NOTE: GitHub Actions run this command for CodeCov metrics `uv run --frozen pytest --cov --cov-branch --cov-report=term-missing`
* [ ] Document the MCP Server in this "README.md"
* [ ] Add a section for this Athena MCP Server at the top level of this repository "../../README.md"
* [ ] Create the "../../doc/servers/athena-mcp-server.md" file with these contents:

    ```markdown
    ---
    title: Athena MCP Server
    ---

    {% include "../../src/athena-mcp-server/README.md" %}
    ```

* [ ] Reference within the "../../doc/index.md" like this:

    ```markdown
    ### Athena MCP Server

    An AWS Labs Model Context Protocol (MCP) server for Athena

    **Features:**

    - Feature one
    - Feature two
    - ...

    AWS Athena MCP Server provides tools to execute SQL queries against data stored in Amazon S3 using AWS Athena.

    [Learn more about the Athena MCP Server](servers/athena-mcp-server.md)
    ```

* [ ] Submit a PR and pass all the checks
