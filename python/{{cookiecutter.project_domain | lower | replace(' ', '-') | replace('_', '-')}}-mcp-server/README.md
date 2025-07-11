# AWS Labs {{cookiecutter.project_domain}} MCP Server

{{cookiecutter.description}}

## Instructions

{{cookiecutter.instructions}}

## TODO (REMOVE AFTER COMPLETING)

* [ ] Optionally add an ["RFC issue"](https://github.com/awslabs/mcp/issues) for the community to review
* [ ] Generate a `uv.lock` file with `uv sync` -> See [Getting Started](https://docs.astral.sh/uv/getting-started/)
* [ ] Remove the example tools in `./awslabs/{{cookiecutter.project_domain | lower | replace(' ', '-') | replace('_', '-') | replace('-', '_')}}_mcp_server/server.py`
* [ ] Add your own tool(s) following the [DESIGN_GUIDELINES.md](https://github.com/awslabs/mcp/blob/main/DESIGN_GUIDELINES.md)
* [ ] Keep test coverage at or above the `main` branch - NOTE: GitHub Actions run this command for CodeCov metrics `uv run --frozen pytest --cov --cov-branch --cov-report=term-missing`
* [ ] Document the MCP Server in this "README.md"
* [ ] Add a section for this {{cookiecutter.project_domain}} MCP Server at the top level of this repository "../../README.md"
* [ ] Create the "../../docusaraus/docs/servers/{{cookiecutter.project_domain | lower | replace(' ', '-') | replace('_', '-')}}-mcp-server.md" file with these contents:

    ```markdown
    ---
    title: {{cookiecutter.project_domain}} MCP Server
    ---

    import ReadmeContent from "../../../src/{{cookiecutter.project_domain | lower | replace(' ', '-') | replace('_', '-')}}-mcp-server/README.md";

    <div className="readme-content">
      <style>
        {`
        .readme-content h1:first-of-type {
          display: none;
        }
        `}
      </style>
      <ReadmeContent />
    </div>
    ```
  
* [ ] Reference within the "../../docusaraus/sidebars.ts" in the appropriate category.
* [ ] Add an entry to "../../docusaraus/statics/assets/server-cards.json" in the servers json. 



* [ ] Submit a PR and pass all the checks
