# MCP Lambda Handler Module

A Python library for creating serverless HTTP handlers for the Model Context Protocol (MCP) using AWS Lambda. This library provides a minimal, extensible framework for building MCP HTTP endpoints with pluggable session management support.

## Features

- 🚀 Easy serverless MCP HTTP handler creation using AWS Lambda
- 🔌 Pluggable session management system (NoOp or DynamoDB, or custom backends)
- 📝 Full TypedDict support with automatic JSON schema generation
- 💬 Docstring-based parameter descriptions with nested field support

## Quick Start

1. Install the package with development dependencies:
```bash
pip install -e .[dev]
```

2. Use the handler in your AWS Lambda function:

## Basic Usage

```python
from awslabs.mcp_lambda_handler import MCPLambdaHandler

mcp = MCPLambdaHandler(name="mcp-lambda-server", version="1.0.0")

@mcp.tool()
def add_two_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b

def lambda_handler(event, context):
    """AWS Lambda handler function."""
    return mcp.handle_request(event, context)
```

## Advanced Features

### TypedDict Support with Docstring Descriptions

The library provides full support for Python's TypedDict with automatic JSON schema generation and intelligent extraction of field descriptions from docstrings:

```python
from typing import TypedDict, List
from enum import Enum
from awslabs.mcp_lambda_handler import MCPLambdaHandler

class Address(TypedDict):
    street: str
    city: str
    zip_code: str

class Contact(TypedDict):
    email: str
    phone: str

class SkillLevel(Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    EXPERT = "expert"

class Skill(TypedDict):
    name: str
    level: SkillLevel
    years_experience: int

class Employee(TypedDict):
    name: str
    employee_id: int
    address: Address
    contact: Contact
    skills: List[Skill]
    tags: List[str]

mcp = MCPLambdaHandler(name="example-server")

@mcp.tool()
def register_employee(employee: Employee) -> str:
    """Register a new employee in the system.

    Args:
        employee: Complete employee information
        employee.name: Full legal name of the employee
        employee.employee_id: Unique employee identifier (auto-generated if not provided)
        employee.address: Employee's home address for records
        employee.address.street: Street address including number
        employee.address.city: City name
        employee.address.zip_code: ZIP or postal code
        employee.contact: Contact information
        employee.contact.email: Primary work email address
        employee.contact.phone: Contact phone number (with country code)
        employee.skills: List of professional skills and competencies
        employee.skills[].name: Name of the skill (e.g., "Python", "Project Management")
        employee.skills[].level: Proficiency level (beginner, intermediate, or expert)
        employee.skills[].years_experience: Years of experience with this skill
        employee.tags: Employee tags and labels for categorization

    Returns:
        Confirmation message with employee ID
    """
    return f"Registered {employee['name']} with ID {employee['employee_id']}"
```

#### Key Features:

**Automatic Schema Generation:**
- Generates proper JSON schemas for TypedDict structures
- Handles nested TypedDict definitions automatically
- Supports optional fields (using `total=False` or `NotRequired` in Python 3.11+)
- Preserves type information for validation

**Intelligent Docstring Parsing:**
- Extracts descriptions for parameters and nested fields
- Uses dot notation (e.g., `employee.address.city`) for nested structures
- Automatically maps descriptions to the appropriate schema fields
- Supports multi-level nesting for complex data structures

The resulting JSON schema includes both the structure from TypedDict and the descriptions from docstrings, providing rich metadata for MCP clients.

### Supported Type Hints

The library handles a wide variety of Python type hints:

- **Basic Types**: `int`, `float`, `bool`, `str`
- **Collections**: `List[T]`, `Dict[K, V]`
- **Enums**: Automatically converts to string enums with allowed values
- **TypedDict**: Full support including inheritance and mixed required/notRequired fields

### TypedDict with Optional Fields

For TypedDicts with optional fields:

```python
from typing import TypedDict

# All fields optional
class Config(TypedDict, total=False):
    timeout: int
    retries: int
    verbose: bool

# Mixed required and optional (Python 3.11+)
from typing import Required, NotRequired

class MixedConfig(TypedDict):
    id: Required[str]          # Explicitly required
    name: Required[str]         # Explicitly required
    description: NotRequired[str]  # Optional
    priority: NotRequired[int]     # Optional
```

## Session Management

The library provides flexible session management with built-in support for DynamoDB and the ability to create custom session backends. You can use the default stateless (NoOp) session store, or configure a DynamoDB-backed store for persistent sessions.

## Example Architecture for Auth & Session Management

A typical serverless deployment using this library might look like:

- **API Gateway**: Exposes the `/mcp` endpoint.
- **Lambda Authorizer**: Validates authentication tokens (e.g., bearer tokens in the `Authorization` header).
- **MCP Server Lambda**: Implements MCP tools and session logic using this library.
- **DynamoDB**: Stores session data (if using the DynamoDB session backend).

## Development

1. Clone the repository:
```bash
git clone https://github.com/awslabs/mcp.git
cd mcp/src/mcp-lambda-handler
```

2. Install development dependencies:
```bash
pip install -e .[dev]
```

3. Run tests:
```bash
pytest
```

## Contributing

Contributions are welcome! Please see the [CONTRIBUTING.md](../../CONTRIBUTING.md) in the monorepo root for guidelines.

## License

This project is licensed under the Apache-2.0 License - see the [LICENSE](LICENSE) file for details.

## Python Version Support

- Python 3.10+

## Dependencies

Core dependencies:
- python-dateutil >= 2.8.2

Optional dependencies:
- boto3 >= 1.38.1 (for AWS/DynamoDB support)
- botocore >= 1.38.1 (for AWS/DynamoDB support)

Development dependencies:
- pytest >= 8.0.0
- black >= 24.2.0
- isort >= 5.13.0
- flake8 >= 7.0.0
- moto >= 5.0.3 (for AWS mocking in tests)
