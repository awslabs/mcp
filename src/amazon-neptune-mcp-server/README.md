# AWS Labs amazon-neptune MCP Server

An Amazon Neptune MCP server that allows for fetching status, schema, and querying using openCypher, Gremlin, and SPARQL for Neptune Database and openCypher for Neptune Analytics.

## Instructions

Add some instructions

## TODO (REMOVE AFTER COMPLETING)

* [ ] Optionally add an ["RFC issue"](https://github.com/awslabs/mcp/issues) for the community to review
* [ ] Generate a `uv.lock` file with `uv sync` -> See [Getting Started](https://docs.astral.sh/uv/getting-started/)
* [ ] Remove the example tools in `./awslabs/amazon_neptune_mcp_server/server.py`
* [ ] Add your own tool(s) following the [DESIGN_GUIDELINES.md](https://github.com/awslabs/mcp/blob/main/DESIGN_GUIDELINES.md)
* [ ] Keep test coverage at or above the `main` branch - NOTE: GitHub Actions run this command for CodeCov metrics `uv run --frozen pytest --cov --cov-branch --cov-report=term-missing`
* [ ] Document the MCP Server in this "README.md"
* [ ] Add a section for this amazon-neptune MCP Server at the top level of this repository "../../README.md"
* [ ] Create the "../../doc/servers/amazon-neptune-mcp-server.md" file with these contents:

    ```markdown
    ---
    title: amazon-neptune MCP Server
    ---

    {% include "../../src/amazon-neptune-mcp-server/README.md" %}
    ```
  
* [ ] Reference within the "../../doc/index.md" like this:

    ```markdown
    ### amazon-neptune MCP Server
    
    An Amazon Neptune MCP server that allows for fetching status, schema, and querying using openCypher, Gremlin, and SPARQL for Neptune Database and openCypher for Neptune Analytics.
    
    **Features:**
    
    - Feature one
    - Feature two
    - ...

    Add some instructions
    
    [Learn more about the amazon-neptune MCP Server](servers/amazon-neptune-mcp-server.md)
    ```

* [ ] Submit a PR and pass all the checks
