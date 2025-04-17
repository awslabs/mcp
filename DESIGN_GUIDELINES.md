# MCP Server Design Guidelines

This document outlines the design guidelines and best practices for developing MCP (Multimodal Code Platform) servers. These guidelines are based on the patterns used in examples like `bedrock-kb-retrieval-mcp-server` and `nova-canvas-mcp-server`.

## Table of Contents

- [MCP Server Design Guidelines](#mcp-server-design-guidelines)
  - [Table of Contents](#table-of-contents)
  - [Project Structure](#project-structure)
  - [Code Organization](#code-organization)
    - [Entry Points](#entry-points)
  - [Package Naming and Versioning](#package-naming-and-versioning)
  - [License and Copyright Headers](#license-and-copyright-headers)
  - [Constants Management](#constants-management)
  - [Type Definitions and Pydantic Models](#type-definitions-and-pydantic-models)
    - [Best Practices](#best-practices)
    - [Example](#example)
  - [Function Parameters with Pydantic Field](#function-parameters-with-pydantic-field)
    - [Field Guidelines](#field-guidelines)
    - [Instructing AI Models in Parameter Descriptions](#instructing-ai-models-in-parameter-descriptions)
      - [Workspace Directory Pattern](#workspace-directory-pattern)
      - [Best Practices for AI Instructions](#best-practices-for-ai-instructions)
      - [Example with Multiple AI Instructions](#example-with-multiple-ai-instructions)
  - [Resources and Tools](#resources-and-tools)
    - [Resource Definition](#resource-definition)
    - [Tool Definition](#tool-definition)
  - [Asynchronous Programming](#asynchronous-programming)
  - [Response Formatting](#response-formatting)
  - [Security Practices](#security-practices)
    - [Code Security Scanning](#code-security-scanning)
    - [Controlled Execution Environments](#controlled-execution-environments)
    - [Timeouts for Long-Running Operations](#timeouts-for-long-running-operations)
    - [Explicit Allowlists](#explicit-allowlists)
  - [Logging with Loguru](#logging-with-loguru)
    - [Logging Guidelines](#logging-guidelines)
  - [Authentication to AWS Services](#authentication-to-aws-services)
    - [Authentication Guidelines](#authentication-guidelines)
  - [Environment Variables](#environment-variables)
    - [Environment Variable Guidelines](#environment-variable-guidelines)
  - [Error Handling](#error-handling)
    - [Error Handling Guidelines](#error-handling-guidelines)
  - [Documentation](#documentation)
    - [Docstrings](#docstrings)
    - [MCP Server Instructions](#mcp-server-instructions)
    - [Documentation Guidelines](#documentation-guidelines)
  - [Code Style and Linting](#code-style-and-linting)
  - [Testing](#testing)
    - [Testing Tools](#testing-tools)
  - [Conclusion](#conclusion)

## Project Structure

MCP servers should follow this basic structure:

```
mcp-server-project/
├── README.md               # Project description, setup instructions
├── CHANGELOG.md            # Version history and changes
├── LICENSE                 # License information
├── NOTICE                  # Additional copyright notices
├── pyproject.toml          # Project configuration
├── .gitignore              # Git ignore patterns
├── .pre-commit-config.yaml # Pre-commit hooks
├── awslabs/                # Source code directory
│   ├── __init__.py         # Package initialization
│   └── your_mcp_server/    # Main server package
│       ├── __init__.py     # Package version and metadata
│       ├── models.py       # Pydantic models
│       ├── server.py       # MCP server implementation
│       ├── consts.py       # Constants definition
│       └── ...             # Additional modules
└── tests/                  # Test directory
```

## Code Organization

1. **Separation of Concerns**:
   - `models.py`: Define data models and validation logic
   - `server.py`: Implement MCP server, tools, and resources
   - `consts.py`: Define constants used across the server
   - Additional modules for specific functionality (e.g., API clients)

2. **Keep modules focused and limited to a single responsibility**

3. **Use clear and consistent naming conventions**

### Entry Points

MCP servers should follow these guidelines for application entry points:

1. **Single Entry Point**: Define the main entry point only in `server.py`
   - Do not create a separate `main.py` file
   - This maintains clarity about how the application starts

2. **Main Function**: Implement a `main()` function in `server.py` that:
   - Handles command-line arguments
   - Sets up environment and logging
   - Initializes the MCP server
   - Starts the server with appropriate transport

Example:

```python
def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(description='A Model Context Protocol (MCP) server')
    parser.add_argument('--sse', action='store_true', help='Use SSE transport')
    parser.add_argument('--port', type=int, default=8888, help='Port to run the server on')

    args = parser.parse_args()

    # Run server with appropriate transport
    if args.sse:
        mcp.settings.port = args.port
        mcp.run(transport='sse')
    else:
        mcp.run()


if __name__ == '__main__':
    main()
```

3. **Package Entry Point**: Configure the entry point in `pyproject.toml`:

```toml
[project.scripts]
"awslabs.your-mcp-server" = "awslabs.your_mcp_server.server:main"
```

## Package Naming and Versioning

1. **Package Naming**: Follow the established naming pattern:
   - Namespace: `awslabs`
   - Package name: lowercase with hyphens (in pyproject.toml)
   - Python module: lowercase with underscores

   Example:
   ```toml
   # In pyproject.toml
   name = "awslabs.nova-canvas-mcp-server"
   ```

   ```python
   # In Python imports
   from awslabs.nova_canvas_mcp_server import models
   ```

2. **Versioning**: Store version information in `__init__.py`:

   ```python
   # awslabs/your_mcp_server/__init__.py
   """awslabs Your MCP Server."""

   __version__ = "0.1.0"
   ```

3. **Version Synchronization**: Keep version consistent between:
   - `pyproject.toml`
   - `__init__.py` in the package
   - Configure `commitizen` in `pyproject.toml` to update versions automatically

   ```toml
   [tool.commitizen]
   name = "cz_conventional_commits"
   version = "0.0.0"
   tag_format = "v$version"
   version_files = [
       "pyproject.toml:version",
       "awslabs/your_mcp_server/__init__.py:__version__"
   ]
   update_changelog_on_bump = true
   ```

## License and Copyright Headers

Include standard license headers at the top of each source file:

```python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
```

## Constants Management

Organize constants in a dedicated `consts.py` file:

1. **Constant Naming**: Use UPPER_CASE for constant names
2. **Grouping**: Group related constants together
3. **Documentation**: Add docstrings to explain the purpose and valid values

Example:

```python
"""Constants for the MCP server."""

# Default configuration values
DEFAULT_WIDTH = 1024
DEFAULT_HEIGHT = 1024
DEFAULT_QUALITY = 'standard'
DEFAULT_CFG_SCALE = 6.5
DEFAULT_NUMBER_OF_IMAGES = 1

# Documentation content
PROMPT_INSTRUCTIONS = """
An effective prompt often includes short descriptions of:
1. The subject
2. The environment
3. (optional) The position or pose of the subject
4. (optional) Lighting description
5. (optional) Camera position/framing
6. (optional) The visual style or medium ("photo", "illustration", "painting", etc.)
"""

# API endpoints and configuration
API_ENDPOINT = "https://api.example.com/v1"
API_TIMEOUT = 30  # seconds
```

## Type Definitions and Pydantic Models

### Best Practices

1. Use Pydantic for all data models, with comprehensive type hints
2. Define clear class hierarchies with inheritance where appropriate
3. Define enums for constrained values
4. Include comprehensive field validation
5. Document models with detailed docstrings

### Example

```python
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Dict, List, Literal, Optional

class Quality(str, Enum):
    """Quality options for image generation.

    Attributes:
        STANDARD: Standard quality image generation.
        PREMIUM: Premium quality image generation with enhanced details.
    """

    STANDARD = 'standard'
    PREMIUM = 'premium'

class ImageGenerationConfig(BaseModel):
    """Configuration for image generation.

    This model defines the parameters that control the image generation process,
    including dimensions, quality, and generation settings.

    Attributes:
        width: Width of the generated image (320-4096, must be divisible by 16).
        height: Height of the generated image (320-4096, must be divisible by 16).
        quality: Quality level of the generated image (standard or premium).
        cfgScale: How strongly the image adheres to the prompt (1.1-10.0).
        seed: Seed for reproducible generation (0-858993459).
        numberOfImages: Number of images to generate (1-5).
    """

    width: int = Field(default=1024, ge=320, le=4096)
    height: int = Field(default=1024, ge=320, le=4096)
    quality: Quality = Quality.STANDARD
    cfgScale: float = Field(default=6.5, ge=1.1, le=10.0)
    seed: int = Field(default_factory=lambda: random.randint(0, 858993459), ge=0, le=858993459)
    numberOfImages: int = Field(default=1, ge=1, le=5)

    @field_validator('width', 'height')
    @classmethod
    def must_be_divisible_by_16(cls, v: int) -> int:
        """Validate that width and height are divisible by 16."""
        if v % 16 != 0:
            raise ValueError('Value must be divisible by 16')
        return v

    @model_validator(mode='after')
    def validate_aspect_ratio_and_total_pixels(self):
        """Validate aspect ratio and total pixel count."""
        width = self.width
        height = self.height

        # Check aspect ratio between 1:4 and 4:1
        aspect_ratio = width / height
        if aspect_ratio < 0.25 or aspect_ratio > 4.0:
            raise ValueError('Aspect ratio must be between 1:4 and 4:1')

        # Check total pixel count
        total_pixels = width * height
        if total_pixels >= 4194304:
            raise ValueError('Total pixel count must be less than 4,194,304')

        return self
```

## Function Parameters with Pydantic Field

MCP tool functions should use spread parameters with Pydantic's `Field` for detailed descriptions:

```python
@mcp.tool(name='QueryKnowledgeBases')
async def query_knowledge_bases_tool(
    query: str = Field(
        ..., description='A natural language query to search the knowledge base with'
    ),
    knowledge_base_id: str = Field(
        ...,
        description='The knowledge base ID to query. It must be a valid ID from the resource://knowledgebases MCP resource',
    ),
    number_of_results: int = Field(
        10,
        description='The number of results to return. Use smaller values for focused results and larger values for broader coverage.',
    ),
    reranking: bool = Field(
        True,
        description='Whether to rerank the results. Useful for improving relevance and sorting.',
    ),
    reranking_model_name: Literal['COHERE', 'AMAZON'] = Field(
        'AMAZON',
        description="The name of the reranking model to use. Options: 'COHERE', 'AMAZON'",
    ),
    data_source_ids: Optional[List[str]] = Field(
        None,
        description='The data source IDs to filter the knowledge base by. It must be a list of valid data source IDs from the resource://knowledgebases MCP resource',
    ),
) -> str:
    """Query an Amazon Bedrock Knowledge Base using natural language.

    ## Usage Requirements
    - You MUST first use the `resource://knowledgebases` resource to get valid knowledge base IDs
    - You can query different knowledge bases or make multiple queries to the same knowledge base

    [Detailed function documentation...]
    """
```

### Field Guidelines

1. **Required parameters**: Use `...` as the default value to indicate a parameter is required
2. **Optional parameters**: Provide sensible defaults and mark as `Optional` in the type hint
3. **Descriptions**: Write clear, informative descriptions for each parameter
4. **Validation**: Use Field constraints like `ge`, `le`, `min_length`, `max_length`
5. **Literals**: Use `Literal` for parameters with a fixed set of valid values

### Instructing AI Models in Parameter Descriptions

Parameter descriptions in MCP tools can contain explicit instructions for AI assistants that will be using the tools. This is especially important for parameters that require context-specific information.

#### Workspace Directory Pattern

A common pattern is instructing AI models to provide the current workspace directory for operations that need to save files:

```python
@mcp.tool(name='generate_image')
async def mcp_generate_image(
    ctx: Context,
    prompt: str = Field(...),
    # ... other parameters
    workspace_dir: Optional[str] = Field(
        default=None,
        description="""The current workspace directory where the image should be saved.
        CRITICAL: Assistant must always provide the current IDE workspace directory parameter to save images to the user's current project.""",
    ),
) -> McpImageGenerationResponse:
    """Generate an image using Amazon Nova Canvas with text prompt."""
    # ... implementation
```

This pattern has several key elements:

1. **Clear purpose**: Explains that the parameter is for saving files to a specific location
2. **Highlighted instruction**: Uses "CRITICAL" to emphasize importance
3. **Explicit requirement**: States "Assistant must always provide..."
4. **Contextual reason**: Explains why this is important ("to save images to the user's current project")

#### Best Practices for AI Instructions

When writing parameter descriptions that contain instructions for AI models:

1. **Be explicit**: Clearly state what the AI should do
2. **Highlight importance**: Use keywords like "CRITICAL", "IMPORTANT", or "REQUIRED" for essential instructions
3. **Provide context**: Explain why the instruction matters
4. **Use consistent formatting**: Format AI-specific instructions similarly across all parameters
5. **Place near the end**: Put instructions to the AI toward the end of the description, after explaining the parameter's purpose

#### Example with Multiple AI Instructions

```python
@mcp.tool(name='process_document')
async def process_document(
    ctx: Context,
    document_text: str = Field(
        ...,
        description='The text content of the document to process'
    ),
    output_format: Literal["markdown", "html", "text"] = Field(
        "markdown",
        description='The desired output format. IMPORTANT: Assistant should select format based on user needs.'
    ),
    workspace_dir: Optional[str] = Field(
        default=None,
        description="""Directory where output files will be saved.
        CRITICAL: Assistant must always provide the current IDE workspace directory."""
    ),
) -> str:
    """Process a document and convert it to the specified format."""
    # ... implementation
```

## Resources and Tools

MCP servers implement two main types of endpoints:

### Resource Definition

Resources provide data that tools can use:

```python
@mcp.resource(uri='resource://knowledgebases', name='KnowledgeBases', mime_type='application/json')
async def knowledgebases_resource() -> str:
    """List all available Amazon Bedrock Knowledge Bases and their data sources.

    This resource returns a mapping of knowledge base IDs to their details, including:
    - name: The human-readable name of the knowledge base
    - data_sources: A list of data sources within the knowledge base, each with:
      - id: The unique identifier of the data source
      - name: The human-readable name of the data source

    ## Example response structure:
    ```json
    {
        "kb-12345": {
            "name": "Customer Support KB",
            "data_sources": [
                {"id": "ds-abc123", "name": "Technical Documentation"},
                {"id": "ds-def456", "name": "FAQs"}
            ]
        },
        "kb-67890": {
            "name": "Product Information KB",
            "data_sources": [
                {"id": "ds-ghi789", "name": "Product Specifications"}
            ]
        }
    }
    ```

    ## How to use this information:
    1. Extract the knowledge base IDs (like "kb-12345") for use with the QueryKnowledgeBases tool
    2. Note the data source IDs if you want to filter queries to specific data sources
    3. Use the names to determine which knowledge base and data source(s) are most relevant to the user's query
    """
    return json.dumps(await discover_knowledge_bases(kb_agent_mgmt_client))
```

Resource guidelines:
1. Use a consistent URI pattern: `resource://name`
2. Specify the MIME type for proper content handling
3. Return data in a format that tools can easily consume
4. Document the resource structure and usage comprehensively

### Tool Definition

Tools provide functionality that LLMs can use:

```python
@mcp.tool(name='generate_image')
async def mcp_generate_image(
    ctx: Context,
    prompt: str = Field(...),
    negative_prompt: Optional[str] = Field(default=None),
    # ... other parameters
) -> McpImageGenerationResponse:
    """Generate an image using Amazon Nova Canvas with text prompt."""

    # ... implementation
```

Tool guidelines:
1. Use descriptive tool names in `camelCase` or `snake_case` consistently
2. Include the Context parameter for error reporting
3. Use detailed Field descriptions for all parameters
4. Return structured responses using Pydantic models when possible
5. Document the tool's purpose, inputs, and outputs comprehensively

## Asynchronous Programming

MCP servers use asynchronous programming patterns:

1. **Async Functions**: Use `async`/`await` for all MCP tool and resource functions
2. **Concurrent Operations**: Use `asyncio.gather` for concurrent operations
3. **Non-blocking I/O**: Ensure external API calls use async libraries when possible
4. **Context Management**: Handle async context managers properly

Example:

```python
import asyncio

@mcp.tool(name='parallel_operations')
async def perform_parallel_operations(ctx: Context, query: str = Field(...)) -> str:
    """Performs multiple operations concurrently."""

    # Execute operations concurrently
    results = await asyncio.gather(
        operation1(query),
        operation2(query),
        operation3(query),
        return_exceptions=True
    )

    # Process results
    valid_results = [r for r in results if not isinstance(r, Exception)]

    return json.dumps(valid_results)
```

## Response Formatting

Standardize response formats across tools:

1. **JSON Responses**: Return JSON-serialized strings for structured data
2. **Path Formatting**: Use URI format for file paths (e.g., `file:///path/to/file`)
3. **Response Models**: Define Pydantic models for consistent response structure

Example:

```python
class McpImageGenerationResponse(BaseModel):
    """Response from image generation API."""
    status: str
    paths: List[str]

@mcp.tool(name='generate_image')
async def mcp_generate_image(...) -> McpImageGenerationResponse:
    # ... implementation
    return McpImageGenerationResponse(
        status='success',
        paths=[f'file://{path}' for path in response.paths],
    )
```

## Security Practices

MCP servers that execute user-provided code or interface with potentially dangerous operations should implement comprehensive security measures. This section provides guidelines based on patterns observed in the `aws-diagram-mcp-server`.

### Code Security Scanning

When accepting user-provided code for execution, implement robust security scanning:

```python
async def scan_python_code(code: str) -> CodeScanResult:
    """Use ast and bandit to scan the python code for security issues."""
    # Get code metrics
    metrics = await count_code_metrics(code)

    # Check syntax
    syntax_valid, syntax_error = await validate_syntax(code)
    if not syntax_valid:
        return CodeScanResult(
            has_errors=True, syntax_valid=False, error_message=syntax_error, metrics=metrics
        )

    # Check security
    security_issues = await check_security(code)

    # Check for dangerous functions explicitly
    dangerous_functions = check_dangerous_functions(code)
    if dangerous_functions:
        for func in dangerous_functions:
            security_issues.append(
                SecurityIssue(
                    severity='HIGH',
                    confidence='HIGH',
                    line=func['line'],
                    issue_text=f"Dangerous function '{func['function']}' detected",
                    issue_type='DangerousFunctionDetection',
                )
            )

    # Determine if there are errors
    has_errors = bool(security_issues)

    # Generate error message if needed
    error_message = None
    if has_errors:
        messages = [f'{issue.issue_type}: {issue.issue_text}' for issue in security_issues]
        error_message = '\n'.join(messages) if messages else None

    return CodeScanResult(
        has_errors=has_errors,
        syntax_valid=True,
        security_issues=security_issues,
        error_message=error_message,
        metrics=metrics,
    )
```

Key security scanning practices:

1. **Multiple Validation Layers**:
   - Syntax validation using AST parsing
   - Security scanning with tools like Bandit
   - Custom checks for dangerous functions
   - Content validation for potentially harmful patterns

2. **Comprehensive Tracking**:
   - Track severity and confidence levels for issues
   - Maintain line numbers for precise error reporting
   - Categorize issues by type for better organization
   - Generate actionable error messages

3. **Custom Security Checks**:
   - Implement function-specific security scanners:

```python
def check_dangerous_functions(code: str) -> List[Dict[str, Any]]:
    """Check for dangerous functions like exec, eval, etc."""
    dangerous_patterns = [
        'exec(',
        'eval(',
        'subprocess.',
        'os.system',
        'os.popen',
        '__import__',
        'pickle.loads',
    ]

    results = []
    lines = code.splitlines()

    for i, line in enumerate(lines):
        for pattern in dangerous_patterns:
            if pattern in line:
                results.append(
                    {
                        'function': pattern.rstrip('('),
                        'line': i + 1,
                        'code': line.strip(),
                    }
                )

    return results
```

### Controlled Execution Environments

When executing user code, create controlled environments:

```python
# Create a namespace for execution
namespace = {}

# Import necessary modules directly in the namespace
exec('import os', namespace)
exec('import diagrams', namespace)
exec('from diagrams import Diagram, Cluster, Edge', namespace)
# [Additional imports specific to the allowed functionality]

# Set up a timeout handler
def timeout_handler(signum, frame):
    raise TimeoutError(f'Diagram generation timed out after {timeout} seconds')

# Register the timeout handler
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(timeout)

# Execute the code in the controlled namespace
exec(code, namespace)

# Cancel the alarm
signal.alarm(0)
```

Key practices for controlled execution:

1. **Isolated Namespace**:
   - Execute in a dedicated namespace dict
   - Explicitly import only required modules
   - Avoid exposing sensitive globals or builtins

2. **Code Transformation**:
   - Rewrite user code to enforce security constraints
   - Inject safety parameters (e.g., `show=False` for diagrams)
   - Replace potentially dangerous parameters

3. **Resource Management**:
   - Create temporary directories/files with proper permissions
   - Clean up resources even if execution fails
   - Use context managers for resource lifecycle

4. **Exception Handling**:
   - Catch and handle all exceptions from user code
   - Provide meaningful error messages
   - Prevent exception details from leaking sensitive information

### Timeouts for Long-Running Operations

Implement timeouts to prevent resource exhaustion:

```python
def timeout_handler(signum, frame):
    raise TimeoutError(f'Operation timed out after {timeout} seconds')

# Register the timeout handler
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(timeout)

try:
    # Long-running operation
    result = operation()

    # Cancel the alarm
    signal.alarm(0)
    return result
except TimeoutError as e:
    return ErrorResponse(status='error', message=str(e))
```

Timeout implementation best practices:

1. **Configurable Timeouts**:
   - Allow timeouts to be configured per operation
   - Set reasonable defaults based on expected execution time
   - Consider environment (development vs. production) for timeout values

2. **Graceful Handling**:
   - Provide clear error messages when timeouts occur
   - Ensure resources are properly cleaned up
   - Log timeout events for monitoring and debugging

3. **Operation-Specific Timeouts**:
   - Adjust timeouts based on operation complexity
   - Consider input size when setting timeouts
   - Allow client-specified timeouts with upper bounds

### Explicit Allowlists

Define explicit allowlists for permitted operations and modules:

```python
# Allowlisted modules that can be safely imported
ALLOWED_MODULES = {
    'os': ['path.join', 'path.basename', 'path.dirname', 'makedirs', 'path.exists'],
    'diagrams': ['*'],  # All diagrams functionality is permitted
    'json': ['dumps', 'loads'],
    # Additional allowed modules and functions
}

def is_import_allowed(module_name, function_name=None):
    """Check if a module or function import is allowed."""
    if module_name not in ALLOWED_MODULES:
        return False

    if function_name is None:
        return True  # The module itself is allowed

    allowed_functions = ALLOWED_MODULES[module_name]
    if '*' in allowed_functions:
        return True  # All functions from this module are allowed

    return function_name in allowed_functions
```

Allowlist implementation best practices:

1. **Granular Permissions**:
   - Define allowlists at the function level, not just module level
   - Consider object methods and properties
   - Specify exact versions of allowed modules when possible

2. **Comprehensive Coverage**:
   - Review all required functionality to create complete allowlists
   - Document why each item is on the allowlist
   - Regularly review and update allowlists

3. **Defense in Depth**:
   - Combine allowlists with other security measures
   - Don't rely solely on allowlists for security
   - Implement runtime checks in addition to static analysis

4. **Clear Documentation**:
   - Document allowlists in code and external documentation
   - Explain the security model to users
   - Provide examples of permissible and non-permissible operations

## Logging with Loguru

All MCP servers should use Loguru for consistent, structured logging:

```python
import sys
from loguru import logger

# Remove default handler and add custom configuration
logger.remove()
logger.add(sys.stderr, level=os.getenv('FASTMCP_LOG_LEVEL', 'WARNING'))

# Usage examples
logger.debug("Detailed information, typically of interest only when diagnosing problems")
logger.info("Confirmation that things are working as expected")
logger.warning("Indication that something unexpected happened, but the application still works")
logger.error("The application has failed to perform some function")
logger.critical("A serious error, indicating that the program itself may be unable to continue running")
```

### Logging Guidelines

1. Configure log level through environment variables (e.g., `FASTMCP_LOG_LEVEL`)
2. Log important operations, especially at service boundaries
3. Include context in log messages (request IDs, operation details)
4. Use appropriate log levels based on severity
5. Log exceptions with full context

## Authentication to AWS Services

MCP servers that access AWS services should handle authentication consistently:

```python
import boto3
import os

# Bedrock Runtime Client
aws_region: str = os.environ.get('AWS_REGION', 'us-east-1')

try:
    if aws_profile := os.environ.get('AWS_PROFILE'):
        bedrock_runtime_client = boto3.Session(
            profile_name=aws_profile, region_name=aws_region
        ).client('bedrock-runtime')
    else:
        bedrock_runtime_client = boto3.Session(region_name=aws_region).client('bedrock-runtime')
except Exception as e:
    logger.error(f'Error creating bedrock runtime client: {str(e)}')
    raise
```

### Authentication Guidelines

1. Support both `AWS_PROFILE` and default credentials
2. Allow region configuration via `AWS_REGION` environment variable
3. Provide clear error messages for authentication failures
4. Document required IAM permissions in README
5. Leverage boto3 for consistent AWS service interaction

## Environment Variables

MCP servers should support configuration through environment variables:

```python
# Configuration via environment variables
LOG_LEVEL = os.environ.get('FASTMCP_LOG_LEVEL', 'WARNING')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
AWS_PROFILE = os.environ.get('AWS_PROFILE')
CUSTOM_SETTING = os.environ.get('CUSTOM_SETTING', 'default_value')
```

### Environment Variable Guidelines

1. Use consistent naming conventions (`UPPERCASE_WITH_UNDERSCORES`)
2. Provide sensible defaults for optional configuration
3. Document all supported environment variables in README
4. Validate and handle missing required configurations gracefully
5. Use environment variables for anything that might vary by deployment

## Error Handling

MCP tools should implement comprehensive error handling:

```python
@mcp.tool(name='generate_image')
async def mcp_generate_image(
    ctx: Context,
    prompt: str = Field(...),
    # ... other parameters
) -> McpImageGenerationResponse:
    """Generate an image using Amazon Nova Canvas with text prompt."""

    try:
        logger.info(f'Generating image with text prompt, quality: {quality}')
        response = await generate_image_with_text(
            # ... parameters
        )

        if response.status == 'success':
            return McpImageGenerationResponse(
                status='success',
                paths=[f'file://{path}' for path in response.paths],
            )
        else:
            logger.error(f'Image generation returned error status: {response.message}')
            await ctx.error(f'Failed to generate image: {response.message}')
            raise Exception(f'Failed to generate image: {response.message}')
    except Exception as e:
        logger.error(f'Error in mcp_generate_image: {str(e)}')
        await ctx.error(f'Error generating image: {str(e)}')
        raise
```

### Error Handling Guidelines

1. Use try/except blocks to catch and handle exceptions
2. Log exceptions with appropriate context
3. Use MCP context for error reporting (`ctx.error`)
4. Provide meaningful error messages to clients
5. Consider categorizing errors (client vs. server errors)

## Documentation

### Docstrings

All modules, classes, and functions should have comprehensive docstrings:

```python
"""Query an Amazon Bedrock Knowledge Base using natural language.

## Usage Requirements
- You MUST first use the `resource://knowledgebases` resource to get valid knowledge base IDs
- You can query different knowledge bases or make multiple queries to the same knowledge base

## Query Tips
- Use clear, specific natural language queries for best results
- You can use this tool MULTIPLE TIMES with different queries to gather comprehensive information
- Break complex questions into multiple focused queries
- Consider querying for factual information and explanations separately

## Tool output format
The response contains multiple JSON objects (one per line), each representing a retrieved document with:
- content: The text content of the document
- location: The source location of the document
- score: The relevance score of the document


## Interpretation Best Practices
1. Extract and combine key information from multiple results
2. Consider the source and relevance score when evaluating information
3. Use follow-up queries to clarify ambiguous or incomplete information
4. If the response is not relevant, try a different query, knowledge base, and/or data source
5. After a few attempts, ask the user for clarification or a different query.
"""
```

### MCP Server Instructions

Provide detailed instructions for LLMs using the MCP server:

```python
mcp = FastMCP(
    'awslabs-nova-canvas-mcp-server',
    instructions=f"""
# Amazon Nova Canvas Image Generation

This MCP server provides tools for generating images using Amazon Nova Canvas through Amazon Bedrock.

## Available Tools

### generate_image
Generate an image from a text prompt using Amazon Nova Canvas.

### generate_image_with_colors
Generate an image from a text prompt and color palette using Amazon Nova Canvas.

## Prompt Best Practices

{PROMPT_INSTRUCTIONS}
""",
    dependencies=[
        'pydantic',
        'boto3',
    ],
)
```

### Documentation Guidelines

1. Include detailed README with setup instructions and usage examples
2. Document all available tools and resources
3. Provide examples of input and output formats
4. Explain limitations and edge cases
5. Document all environment variables and configuration options

## Code Style and Linting

MCP servers should follow consistent code style and linting:

1. **Code Formatters**: Use `ruff format` for consistent code formatting
2. **Linters**: Use `ruff` and `pyright` for type checking and code quality
3. **Pre-commit Hooks**: Configure pre-commit to enforce standards

Example `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.0.291
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format
```

Example `pyproject.toml` configuration:

```toml
[tool.ruff]
line-length = 99
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "Q"]
ignore = ["E203", "E501"]

[tool.ruff.lint.isort]
known-first-party = ["awslabs"]

[tool.ruff.format]
quote-style = "single"
indent-style = "space"
line-ending = "auto"
```

## Testing

MCP servers should have comprehensive test coverage:

1. **Unit tests** for individual functions
2. **Integration tests** for API communication
3. **End-to-end tests** for complete workflows
4. **Mock AWS services** for testing without real AWS credentials
5. **Test coverage** reports to ensure adequate coverage

### Testing Tools

- Use pytest for testing
- Consider pytest-asyncio for testing async functions
- Use moto for mocking AWS services
- Implement CI/CD pipelines for automated testing

## Conclusion

Following these design guidelines will help create consistent, maintainable, and user-friendly MCP servers. The patterns established in example servers like `bedrock-kb-retrieval-mcp-server` and `nova-canvas-mcp-server` provide a solid foundation for developing new MCP services.
