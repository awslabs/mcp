# Amazon Bedrock AgentCore Browser MCP Server

Model Context Protocol (MCP) server for browser automation via Amazon Bedrock AgentCore.

## Why this server?

- **No local browser needed** — sessions run in isolated Firecracker microVMs via AgentCore. No Chromium install, no OS dependencies, no version conflicts.
- **Token-efficient automation** — the accessibility-tree paradigm returns compact, semantic element references (e1, e2, ...) instead of raw HTML/DOM, keeping LLM context usage low.
- **Deterministic element targeting** — refs map to `get_by_role` locators derived from the accessibility tree, which are stable across minor DOM changes (unlike CSS selectors or XPath).
- **Cloud-native session lifecycle** — start, stop, and manage browser sessions via AWS APIs with standard IAM authentication. Sessions are ephemeral and isolated.

**When to use this vs Playwright MCP**: Use this server when you need browser sessions without local infrastructure (CI/CD pipelines, shared automation, compliance-sensitive environments). Use Playwright MCP when you need local-only execution with zero network latency.

## Features

- **24 browser tools** — navigation, interaction, observation, and tab management
- **Session lifecycle management** — start, stop, get, and list cloud browser sessions
- **Element ref system** — short identifiers (e1, e2, ...) for clicking, typing, and interacting
- **Accessibility tree snapshots** — deterministic, token-efficient page representation

## Prerequisites

### Installation Requirements

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python 3.10 or newer using `uv python install 3.10` (or a more recent version)
3. AWS credentials configured (via environment variables, profile, or IAM role)
4. Access to Amazon Bedrock AgentCore Browser APIs

## Installation

Configure the MCP server in your MCP client configuration.

### Command Line

Run the server directly using `uvx` (no install required):

```bash
uvx awslabs.amazon-bedrock-agentcore-browser-mcp-server@latest
```

Or from a local source checkout (for development):

```bash
uv run --directory /path/to/amazon-bedrock-agentcore-browser-mcp-server \
  awslabs.amazon-bedrock-agentcore-browser-mcp-server
```

Set environment variables as needed (see [Environment Variables](#environment-variables)):

```bash
AWS_REGION=us-east-1 AWS_PROFILE=your-profile \
  uvx awslabs.amazon-bedrock-agentcore-browser-mcp-server@latest
```

The server uses stdio transport. Any MCP client that supports stdio can use the commands above — configure the command and args in your client's MCP server settings.

### Claude Desktop

Example configuration for Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "amazon-bedrock-agentcore-browser-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.amazon-bedrock-agentcore-browser-mcp-server@latest"],
      "env": {
        "AWS_REGION": "us-east-1",
        "AWS_PROFILE": "your-profile"
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
    "amazon-bedrock-agentcore-browser-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.amazon-bedrock-agentcore-browser-mcp-server@latest",
        "awslabs.amazon-bedrock-agentcore-browser-mcp-server.exe"
      ],
      "env": {
        "AWS_REGION": "us-east-1",
        "AWS_PROFILE": "your-profile"
      }
    }
  }
}
```

Or using Docker after a successful `docker build -t mcp/bedrock-agentcore-browser .`:

```json
{
  "mcpServers": {
    "amazon-bedrock-agentcore-browser-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env", "AWS_REGION=us-east-1",
        "--env", "AWS_PROFILE=your-profile",
        "mcp/bedrock-agentcore-browser:latest"
      ],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## Basic Usage

1. Start a browser session with `start_browser_session`
2. Navigate to a URL with `browser_navigate`
3. Take a snapshot with `browser_snapshot` to see the page as an accessibility tree with element refs
4. Interact using refs: `browser_click(ref='e3')`, `browser_type(ref='e2', text='hello')`
5. Stop the session with `stop_browser_session` when done

Example conversation:

> "Go to example.com and click the 'More information' link"
>
> The agent calls `start_browser_session`, then `browser_navigate(url='https://example.com')`,
> reads the snapshot to find `link "More information..." [ref=e2]`, and calls `browser_click(ref='e2')`.

## Tools

### Session Lifecycle (4 tools)

#### start_browser_session

Start a cloud browser session via AgentCore and connect Playwright automatically.

```python
start_browser_session(
    browser_identifier: str | None = None,
    timeout_seconds: int = 900,
    viewport_width: int = 1456,
    viewport_height: int = 819,
    extension_s3_url: str | None = None,
    region: str | None = None,
) -> BrowserSessionResponse
```

**Parameters:**
- `browser_identifier`: AgentCore browser resource identifier (default: `aws.browser.v1`)
- `timeout_seconds`: Session timeout in seconds (default: 900, max: 28800)
- `viewport_width`: Browser viewport width in pixels (default: 1456)
- `viewport_height`: Browser viewport height in pixels (default: 819)
- `extension_s3_url`: S3 URL for a browser extension zip file to install (format: `s3://bucket/path/extension.zip`)
- `region`: AWS region override (default: from `AWS_REGION` environment variable)

**Returns:** Session ID, status, automation stream URL, viewport dimensions, browser identifier.

#### get_browser_session

Get the status and metadata of a browser session.

```python
get_browser_session(
    session_id: str,
    browser_identifier: str | None = None,
    region: str | None = None,
) -> BrowserSessionResponse
```

#### stop_browser_session

Terminate a browser session and disconnect Playwright.

```python
stop_browser_session(
    session_id: str,
    browser_identifier: str | None = None,
    region: str | None = None,
) -> BrowserSessionResponse
```

#### list_browser_sessions

List active browser sessions.

```python
list_browser_sessions(
    browser_identifier: str | None = None,
    max_results: int = 20,
    region: str | None = None,
) -> SessionListResponse
```

### Navigation (3 tools)

#### browser_navigate

Navigate to a URL and return an accessibility tree snapshot.

```python
browser_navigate(session_id: str, url: str) -> str
```

#### browser_navigate_back

Navigate back in browser history and return a snapshot.

```python
browser_navigate_back(session_id: str) -> str
```

#### browser_navigate_forward

Navigate forward in browser history and return a snapshot.

```python
browser_navigate_forward(session_id: str) -> str
```

### Interaction (8 tools)

#### browser_click

Click an element by its ref from the accessibility snapshot.

```python
browser_click(
    session_id: str,
    ref: str,
    double_click: bool = False,
    button: str = 'left',
) -> str
```

**Parameters:**
- `ref`: Element ref from the accessibility snapshot (e.g., `e3`)
- `double_click`: Double-click instead of single click (default: false)
- `button`: Mouse button — `"left"`, `"right"`, or `"middle"` (default: `"left"`)

#### browser_type

Type text into an element by ref. Clears existing content by default.

```python
browser_type(
    session_id: str,
    ref: str,
    text: str,
    clear_first: bool = True,
    submit: bool = False,
) -> str
```

**Parameters:**
- `clear_first`: Clear existing content before typing (default: true)
- `submit`: Press Enter after typing (default: false)

#### browser_fill_form

Fill multiple form fields at once by ref.

```python
browser_fill_form(
    session_id: str,
    fields: list[dict[str, str]],
    submit_ref: str | None = None,
) -> str
```

**Parameters:**
- `fields`: List of `{"ref": "e2", "value": "text"}` dicts
- `submit_ref`: Optional ref of a submit button to click after filling

#### browser_select_option

Select a dropdown option by label, value, or index.

```python
browser_select_option(
    session_id: str,
    ref: str,
    value: str | None = None,
    label: str | None = None,
    index: int | None = None,
) -> str
```

#### browser_hover

Hover over an element by ref (useful for tooltips and menus).

```python
browser_hover(session_id: str, ref: str) -> str
```

#### browser_press_key

Press a keyboard key or key combination.

```python
browser_press_key(session_id: str, key: str) -> str
```

**Parameters:**
- `key`: Key name (e.g., `Enter`, `Tab`, `Escape`, `Control+a`, `Meta+c`)

#### browser_upload_file

Upload files to a file input element by ref. For cloud sessions, paths refer to files on the remote VM.

```python
browser_upload_file(session_id: str, ref: str, paths: list[str]) -> str
```

**Parameters:**
- `ref`: Element ref of the file input
- `paths`: List of file paths to upload

#### browser_handle_dialog

Configure automatic handling of JavaScript dialogs (alert, confirm, prompt).

```python
browser_handle_dialog(
    session_id: str,
    action: str = 'accept',
    prompt_text: str | None = None,
) -> str
```

**Parameters:**
- `action`: `"accept"` or `"dismiss"`
- `prompt_text`: Text to enter for prompt dialogs (only with accept)

### Observation (6 tools)

#### browser_snapshot

Capture the accessibility tree with element refs.

```python
browser_snapshot(session_id: str, selector: str | None = None) -> str
```

- **`selector`** *(optional)* — CSS selector to scope the snapshot to a specific element's subtree. When provided, only the accessibility nodes within the matched element are returned. If the element is not found, returns a full-page snapshot with a warning.

**Returns:** YAML-like text with element refs:
```
- heading "Sign In" [level=1]
- textbox "Email" [ref=e1]
- textbox "Password" [ref=e2]
- button "Sign In" [ref=e3]
```

#### browser_take_screenshot

Capture a PNG screenshot of the page.

```python
browser_take_screenshot(session_id: str, full_page: bool = False) -> list
```

**Returns:** List with one image content block (base64-encoded PNG).

#### browser_wait_for

Wait for text to appear or a CSS selector to match.

```python
browser_wait_for(
    session_id: str,
    text: str | None = None,
    selector: str | None = None,
    timeout: int = 10000,
) -> str
```

#### browser_console_messages

Get browser console messages.

```python
browser_console_messages(session_id: str) -> str
```

#### browser_network_requests

List network requests made by the page.

```python
browser_network_requests(session_id: str) -> str
```

#### browser_evaluate

Execute a JavaScript expression and return the result.

```python
browser_evaluate(session_id: str, expression: str) -> str
```

### Management (3 tools)

#### browser_tabs

Manage browser tabs: list, create, select, or close.

```python
browser_tabs(
    session_id: str,
    action: str = 'list',
    tab_index: int | None = None,
    url: str | None = None,
) -> str
```

**Parameters:**
- `action`: One of `list`, `new`, `select`, `close`
- `tab_index`: Zero-based tab index (for `select` and `close`)
- `url`: URL to open in a new tab (for `new`)

#### browser_close

Close the current page.

```python
browser_close(session_id: str) -> str
```

#### browser_resize

Resize the browser viewport.

```python
browser_resize(session_id: str, width: int, height: int) -> str
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_REGION` | AWS region for AgentCore APIs | `us-east-1` |
| `AWS_PROFILE` | AWS CLI profile name | (default profile) |
| `BROWSER_IDENTIFIER` | AgentCore browser resource ID | `aws.browser.v1` |
| `BROWSER_NAVIGATION_TIMEOUT_MS` | Timeout for page navigation in milliseconds | `30000` |
| `BROWSER_INTERACTION_TIMEOUT_MS` | Timeout for element interactions in milliseconds | `5000` |
| `FASTMCP_LOG_LEVEL` | Log level for the MCP server (FastMCP framework) | `INFO` |

## License

Apache-2.0. See [LICENSE](LICENSE).
