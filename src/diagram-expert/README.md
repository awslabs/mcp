# AI3 Diagrams Expert MCP Server

An MCP server that seamlessly creates diagrams using the Python diagrams package DSL. This server allows you to generate AWS diagrams, sequence diagrams, flow diagrams, and class diagrams using Python code.

## Prerequisites

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python using `uv python install 3.13`
3. Install Graphviz (required by the diagrams package):
   - Ubuntu/Debian: `sudo apt-get install graphviz`
   - macOS: `brew install graphviz`
   - Windows: Download from [Graphviz website](https://graphviz.org/download/)

## Installation

Install the MCP server:
```bash
uv tool install --default-index=https://__token__:$GITLAB_TOKEN@gitlab.aws.dev/api/v4/projects/115863/packages/pypi/simple ai3-diagrams-expert --force 
```

Add the server to your MCP client config (e.g. `~/.cursor-server/data/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`):
```json
{
  "mcpServers": {
    "ai3-diagrams-expert": {
      "command": "uvx",
      "args": ["ai3-diagrams-expert"],
      "env": {
        "SHELL": "/usr/bin/zsh"
      }
    }
  }
}
```

## Development

1. Set up the development environment:
```bash
uv sync --all-groups
```

2. Run the server:
```bash
uv run ai3-diagrams-expert/server.py
```

3. Install pre-commit hooks:
```bash
GIT_CONFIG=/dev/null pre-commit install
```

## Running the Server

Run the server with default stdio transport:
```bash
uv run diagrams-expert/server.py
```

Or with SSE transport on a specific port:
```bash
uvx ai3-diagrams-expert/server.py --sse --port 8888
```

## Customizing the Server

1. Edit `diagrams_expert/server.py` to implement your MCP tools and resources
2. Add dependencies to `pyproject.toml` with `uv add <dependency>`
3. Update tests and documentation as needed
4. Build the project: `uv build`
5. Push the changes: `git push`
6. Create a release: `uv run cz bump`
7. Tag the release: `git push --tags`

## Testing

You can test the server directly using the provided test scripts:

1. Run the server in one terminal:
```bash
./run_server.py
```

2. Run the test script in another terminal:
```bash
python test_direct.py
```
