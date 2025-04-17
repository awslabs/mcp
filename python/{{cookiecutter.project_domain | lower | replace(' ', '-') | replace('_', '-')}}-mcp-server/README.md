# awslabs {{cookiecutter.project_domain}} MCP Server

{{cookiecutter.description}}

## Instructions

{{cookiecutter.instructions}}

## TODO (REMOVE AFTER COMPLETING)

* Optionally add an ["RFC issue"](https://github.com/awslabs/mcp/issues) for the community to review
* Generate a `uv.lock` file with `uv sync` -> See [Getting Started](https://docs.astral.sh/uv/getting-started/)
* Remove the example tools in `./awslabs/{{cookiecutter.project_domain | lower | replace(' ', '-') | replace('_', '-') | replace('-', '_')}}_mcp_server/server.py`
* Add your own tool(s) following the [DESIGN_GUIDELINES.md](https://github.com/awslabs/mcp/blob/main/DESIGN_GUIDELINES.md)
* Keep test coverage at or above the `main` branch - NOTE: GitHub Actions run this command for CodeCov metrics `uv run --frozen pytest --cov --cov-branch --cov-report=term-missing`
* Document the MCP Server in this `README.md`
* Document in a section at the top level of this repository `../../README.md`
* Create the `../../doc/servers/{{cookiecutter.project_domain | lower | replace(' ', '-') | replace('_', '-')}}-mcp-server.md` file with these contents:

    ```markdown
    ---
    title: {{cookiecutter.project_domain}} MCP Server
    ---
    
    {%include "../../src/{{cookiecutter.project_domain | lower | replace(' ', '-') | replace('_', '-')}}-mcp-server/README.md"%}
    ```
  
* Reference within the `../../doc/index.md` like this:

    ```markdown
    ### {{cookiecutter.project_domain}} MCP Server
    
    {{cookiecutter.description}}
    
    **Features:**
    
    - Feature one
    - Feature two
    - ...

    {{cookiecutter.instructions}}
    
    [Learn more about the {{cookiecutter.project_domain}} MCP Server](servers/{{cookiecutter.project_domain | lower | replace(' ', '-') | replace('_', '-')}}-mcp-server.md)

* Submit a PR and pass all the checks
