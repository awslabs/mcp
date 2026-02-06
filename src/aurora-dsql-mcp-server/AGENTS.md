# AGENTS.md

Guidelines for AI coding agents working with the AWS Labs Aurora DSQL MCP Server.

## Quick Reference

```bash
# Setup (run from repo root first, then server directory)
pre-commit install                   # Install git hooks (once, from repo root)
cd src/aurora-dsql-mcp-server
uv venv && uv sync --all-groups      # Create venv and install deps

# Lint and format
pre-commit run --all-files           # Run all checks (ruff, pyright, secrets)

# Test
uv run --frozen pytest --cov --cov-branch --cov-report=term-missing

# Run server locally
uvx awslabs.aurora-dsql-mcp-server@latest \
  --cluster_endpoint <endpoint> --region <region> --database_user <user>
```

## Project Overview

This is an MCP (Model Context Protocol) server that enables AI agents to execute SQL queries against Aurora DSQL clusters. The server provides both database operations (query execution, schema retrieval) and documentation access tools.

**Key characteristics:**
- Read-only by default for safety; writes require explicit `--allow-writes` flag
- Three-layer security validation for SQL injection and mutation prevention
- PostgreSQL wire protocol compatibility via psycopg async driver
- IAM-based authentication with automatic token refresh

## Architecture

```
awslabs/aurora_dsql_mcp_server/
├── server.py                     # Main MCP server, tool definitions, connection management
├── consts.py                     # SQL templates, error messages, constants
└── mutable_sql_detector.py       # SQL injection detection, mutation keyword detection

tests/                            # Comprehensive test suite

skills/                           # Agent Skills Open Standard (multi-agent)
├── claude_skill_setup.md         # Claude Code installation instructions
└── dsql-skill/                   # Skill for Claude, Cursor, Gemini, Codex, etc.
    ├── SKILL.md                  # Skill manifest and overview
    ├── mcp/                      # MCP setup and tool reference
    ├── references/               # Development guides, examples, troubleshooting
    └── scripts/                  # Bash utilities

kiro_power/                       # Kiro IDE-specific Power format
├── POWER.md                      # Kiro Power manifest and documentation
├── mcp.json                      # Kiro MCP configuration
└── steering/                     # Kiro steering rules
```

## Tech Stack

- **Python:** 3.10+ (supports 3.10, 3.11, 3.12, 3.13)
- **Package Manager:** uv
- **Build System:** hatchling
- **MCP Framework:** FastMCP (`mcp[cli]>=1.23.0`)
- **Database Driver:** psycopg with async support
- **AWS SDK:** boto3/botocore for IAM token generation
- **HTTP Client:** httpx for knowledge server proxy
- **Logging:** loguru

## Commands

### Setup
```bash
# From repo root (once)
pre-commit install                   # Install git hooks

# From this server directory
uv python install 3.10               # Install Python if needed
uv venv && uv sync --all-groups      # Create venv and install all deps
```

### Linting and Formatting
```bash
pre-commit run --all-files           # Run all checks (recommended)

# Or run individually:
uv run ruff check .                  # Lint code
uv run ruff format .                 # Format code
uv run pyright                       # Type checking
```

### Testing
```bash
uv run --frozen pytest --cov --cov-branch --cov-report=term-missing   # With coverage (recommended)
uv run --frozen pytest tests/ -v                                      # All tests verbose
uv run --frozen pytest tests/test_readonly_enforcement.py -v          # Security tests only
uv run --frozen pytest -m "not live" tests/                           # Skip live API tests
```

### Running the Server Locally
```bash
uvx awslabs.aurora-dsql-mcp-server@latest \
  --cluster_endpoint <endpoint> \
  --region <region> \
  --database_user <user> \
  --profile default
```

### Debugging with MCP Inspector
```bash
npx @modelcontextprotocol/inspector uv --directory $(pwd) run awslabs/aurora_dsql_mcp_server/server.py
```

## Code Style

- **Line length:** 99 characters
- **Quote style:** Single quotes
- **Docstrings:** Google convention
- **Imports:** isort with no sections, 2 blank lines after imports
- **Type hints:** Required on all functions
- **Linter:** ruff with rules C, D, E, F, I, W
- **Commits:** Conventional commits format (via commitizen)

## Security Architecture

This project has a **three-layer security model**. When modifying security-related code, ensure all layers remain intact:

### Layer 1: Mutating Keywords Detection
Located in `mutable_sql_detector.py`. Detects DDL/DML operations:
- CREATE, DROP, ALTER, TRUNCATE, INSERT, UPDATE, DELETE
- GRANT, REVOKE, CREATE USER, CREATE ROLE
- SET GLOBAL, FLUSH, RESET

### Layer 2: SQL Injection Prevention
Detects injection patterns:
- Comment injection (`'.*?--`)
- Tautology attacks (numeric and string)
- UNION-based injection
- Time-based injection (SLEEP, pg_sleep)
- File operations (LOAD_FILE, INTO OUTFILE)
- Stacked query detection

### Layer 3: Transaction Bypass Detection
Prevents attempts to escape read-only transaction context:
- COMMIT followed by other statements
- Multiple statements in single query
- Transaction control injection

**Important:** Read-only mode is the default. The `--allow-writes` flag enables write mode. Never weaken security checks without explicit approval.

## MCP Tools Reference

### Database Operations (require cluster configuration)

| Tool              | Purpose                                         | Mode                                    |
|-------------------|-------------------------------------------------|-----------------------------------------|
| `readonly_query`  | Execute single SELECT query                     | Always read-only                        |
| `transact`        | Execute transaction with multiple statements    | Read-only or read-write based on config |
| `get_schema`      | Retrieve table column names and types           | Always read-only                        |

### Documentation Tools (no database required)

| Tool                         | Purpose                              |
|------------------------------|--------------------------------------|
| `dsql_search_documentation`  | Search DSQL docs by phrase           |
| `dsql_read_documentation`    | Read specific documentation URL      |
| `dsql_recommend`             | Get best practice recommendations    |

## Aurora DSQL Best Practices

Follow these practices when writing SQL for Aurora DSQL:

### Schema Design
- **Use UUIDs for primary keys** - Generate with `gen_random_uuid()` to distribute workload across nodes
- **Enforce referential integrity in application code**
- **Serialize complex types as TEXT** - Store arrays and JSON as serialized TEXT columns
- **Include tenant_id in all tables** - For multi-tenant apps, always filter by tenant_id in WHERE clauses

### DDL Operations
- **Always create indexes asynchronously** - Use `CREATE INDEX ASYNC` and monitor via `SELECT * FROM sys.jobs`
- **Execute one DDL statement per transaction** - Split CREATE/ALTER operations into separate `transact` calls
- **Use DELETE instead of TRUNCATE** - DSQL does not support TRUNCATE; use `DELETE FROM table_name`

### Query Patterns
- **Keep transactions small** - Limit to ~3,000 rows per transaction for optimal performance
- **Validate all user inputs** - This server uses string interpolation; sanitize inputs before building SQL
- **Use transact for consistent reads** - When multiple queries need point-in-time consistency, use `transact` instead of multiple `readonly_query` calls

### Example: Creating a Table
```sql
-- Good: UUID primary key, tenant isolation, TEXT for complex types
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    customer_id UUID NOT NULL,
    items TEXT NOT NULL,  -- JSON serialized
    created_at TIMESTAMPTZ DEFAULT NOW()
)
```

### Example: Creating an Index
```sql
-- Good: Async index creation
CREATE INDEX ASYNC idx_orders_tenant ON orders(tenant_id)

-- Check job status
SELECT * FROM sys.jobs WHERE job_type = 'CREATE INDEX'
```

## Testing Guidelines

- **Security tests are critical** - `test_readonly_enforcement.py` has 50+ test cases
- **Use async fixtures** - pytest-asyncio with `asyncio_mode = "auto"`
- **Mock AWS and database** - Never make real connections in unit tests
- **Markers available:**
  - `@pytest.mark.live` - Tests making real API calls
  - `@pytest.mark.asyncio` - Async tests

When adding new security validation, add corresponding test cases in `test_readonly_enforcement.py`.

## Connection Management

The server maintains a persistent connection with these behaviors:
- Autocommit mode enabled for stability
- Fresh IAM token generated per request (prevents expiry)
- Automatic reconnection on `OperationalError` or `InterfaceError`
- Connection reuse between requests for performance

## Common Development Tasks

### Adding a New Tool
1. Define the tool function in `server.py` using `@mcp.tool()` decorator
2. Add Pydantic field annotations for parameters
3. Add error constants to `consts.py`
4. Write tests in appropriate test file
5. Update documentation in `skills/` if needed

### Modifying Security Validation
1. Update patterns in `mutable_sql_detector.py`
2. Add comprehensive test cases in `test_readonly_enforcement.py`
3. Test both positive (should block) and negative (should allow) cases
4. Document the change in the security section

### Updating Dependencies
1. Modify `pyproject.toml`
2. Run `uv sync` to update `uv.lock`
3. Ensure tests pass with new dependencies

## Creating and Updating Skills

This project supports two steering formats for AI agents:
- **Agent Skills Open Standard** (`skills/dsql-skill/`) - Works with Claude Code, Cursor, Gemini, Codex, and other agents
- **Kiro Power** (`kiro_power/`) - Kiro IDE-specific format

### Agent Skills Open Standard (SKILL.md)

#### Directory Structure
```
skills/dsql-skill/
├── SKILL.md                  # Required: Skill manifest
├── mcp/                      # MCP configuration and tool docs
│   ├── mcp-setup.md
│   ├── mcp-tools.md
│   └── .mcp.json
├── references/               # On-demand detailed documentation
│   ├── development-guide.md
│   ├── language.md
│   ├── dsql-examples.md
│   ├── troubleshooting.md
│   ├── onboarding.md
│   └── ddl-migrations.md
└── scripts/                 # Executable bash utilities
    └── *.sh
```

#### SKILL.md Format

```yaml
---
name: dsql                    # Required: lowercase, alphanumeric, hyphens only (must match directory)
description: Build with...    # Required: 1-1024 chars, explains WHAT it does AND WHEN to use it
---

# Skill Title

Brief overview paragraph.

## Reference Files
List files with **When:** triggers and **Contains:** summaries.

## MCP Tools Available
Document available tools.

## Quick Start
Essential workflows.

## Common Workflows
Step-by-step patterns.

## Best Practices
Key rules and guidelines.
```

#### Frontmatter Rules

| Field         | Required | Rules                                                                                 |
|---------------|----------|---------------------------------------------------------------------------------------|
| `name`        | Yes      | 1-64 chars, lowercase alphanumeric + hyphens, must match parent directory             |
| `description` | Yes      | 1-1024 chars, functions as **trigger mechanism** - be specific about when to activate |

**Good description:** "Build with Aurora DSQL - manage schemas, execute queries, and handle migrations with DSQL-specific requirements. Use when developing a scalable or distributed database/application or user requests DSQL."

**Bad description:** "Helps with databases."

#### Reference Files
Reference files provide detailed documentation loaded on-demand to save context tokens:

- Place in `references/` or `mcp/` subdirectories
- Document each in SKILL.md with **When:** (trigger condition) and **Contains:** (summary)
- Use imperative language and concrete examples
- Include both incorrect and correct patterns side-by-side

### Kiro Power Format (POWER.md)

Powers are reusable packages bundling tools, workflows, and best practices. Kiro automatically activates powers when developers mention relevant keywords.

#### Directory Structure
```
kiro_power/
├── POWER.md                   # Required: Power manifest with frontmatter + instructions
├── mcp.json                   # Optional: MCP server configuration
└── steering/                  # Optional: Workflow-specific guidance files
    ├── development-guide.md
    ├── language.md
    ├── mcp-setup.md
    └── ...
```

#### POWER.md Format

```yaml
---
name: "amazon-aurora-dsql"           # Required: Internal identifier (lowercase, no spaces)
displayName: "Build a database..."   # Required: User-facing name
description: "Build and deploy..."   # Required: Functionality overview
keywords: ["aurora", "dsql", ...]    # Required: Terms that trigger activation
---

# Power Title

## Overview
What the power does and key capabilities.

## Available Steering Files
List files with loading conditions (ALWAYS, MUST, SHOULD, CAN, MAY).
Kiro loads only relevant files based on user context.

## Available MCP Tools
Document database and documentation tools.

## Configuration
Setup steps and requirements.
```

#### Keywords Field
Keywords determine when Kiro activates the power. Match how developers naturally discuss the tool:
- Good: `["aurora", "dsql", "postgresql", "serverless", "database", "distributed"]`
- Think about: What terms would a user say when they need this power?

#### mcp.json Format
```json
{
  "mcpServers": {
    "aurora-dsql": {
      "command": "uvx",
      "args": ["awslabs.aurora-dsql-mcp-server@latest", "--cluster_endpoint", "${CLUSTER_ENDPOINT}"],
      "env": {
        "AWS_PROFILE": "${AWS_PROFILE}"
      }
    }
  }
}
```
Use `${VAR}` syntax for environment variables. Server names auto-namespace during installation.

#### Steering Files
Two approaches:
- **Simple:** Include all guidance directly in POWER.md
- **Advanced:** Map distinct workflows to separate files in `steering/`. Kiro loads only relevant files based on context, preventing information overload.

### Writing Effective Skills

#### Progressive Disclosure
Skills load in three tiers to optimize context usage:

1. **Metadata** (~100 tokens) - Always loaded for all skills
2. **Body** (<5k tokens recommended) - Loaded when skill triggers
3. **References** (variable) - Loaded on-demand by the agent

#### Best Practices

1. **Keep SKILL.md/POWER.md concise** - Under 500 lines; move details to reference files
2. **Write specific descriptions** - The description determines when the skill activates
3. **Use imperative language** - "Create the table" not "You should create the table"
4. **Document reference files clearly** - Include When/Contains for each file
5. **Show incorrect AND correct patterns** - Help agents avoid common mistakes
6. **Include concrete examples** - SQL snippets, code samples, command examples
7. **Organize by workflow** - Group related operations together

#### What NOT to Include in Skills
- README.md or installation guides (use main README)
- Changelogs
- Generic documentation available elsewhere
- Content not needed by AI agents

### Updating Skills

When modifying `skills/` or `kiro_power/`:

1. Keep SKILL.md and POWER.md content synchronized where applicable
2. Update reference files in both locations if they share content
3. Test with the target agent to verify activation triggers work
4. Ensure MCP tool documentation matches actual server behavior

## Files to Avoid Modifying

- `uv.lock` - Auto-generated; modify `pyproject.toml` and run `uv sync` instead

## Pre-commit Checklist

Before submitting changes:
```bash
pre-commit run --all-files                                           # All lint/format/security checks
uv run --frozen pytest --cov --cov-branch --cov-report=term-missing  # All tests with coverage
```

If pre-commit detects secrets:
```bash
detect-secrets scan --baseline .secrets.baseline
detect-secrets audit .secrets.baseline
# Commit the updated .secrets.baseline
```

Ensure security changes have corresponding tests in `test_readonly_enforcement.py`.

## External References

- **Aurora DSQL Documentation:** https://docs.aws.amazon.com/aurora-dsql/latest/userguide/what-is-aurora-dsql.html
- **Aurora DSQL Starter Kit:** https://awslabs.github.io/aurora-dsql-starter-kit/
- **MCP Server Documentation:** https://awslabs.github.io/mcp/servers/aurora-dsql-mcp-server/
- **Parent Repository:** https://github.com/awslabs/mcp
- **Developer Guide:** https://github.com/awslabs/mcp/blob/main/DEVELOPER_GUIDE.md
- **Agent Skills Open Standard:** https://agent-skills.org/
- **Kiro Powers Documentation:** https://kiro.dev/docs/powers/create/
