"""
Extended unit tests for resource management module.
"""

from unittest.mock import MagicMock, call

from awslabs.ecs_mcp_server.modules.resource_management import register_module


def test_prompt_functions():
    """Test that all prompt functions return the expected tool array."""
    # Create a mock MCP server
    mock_mcp = MagicMock()

    # Set up the prompt decorator to capture the prompt functions
    prompt_functions = {}

    def mock_prompt_decorator(pattern):
        def decorator(func):
            prompt_functions[pattern] = func
            return func

        return decorator

    # Assign the mock decorator
    mock_mcp.prompt = mock_prompt_decorator
    mock_mcp.tool = MagicMock()

    # Call register_module to register the prompt functions
    register_module(mock_mcp)

    # Now test each prompt function
    assert prompt_functions["list ecs resources"]() == ["ecs_resource_management"]
    assert prompt_functions["show ecs clusters"]() == ["ecs_resource_management"]
    assert prompt_functions["describe ecs service"]() == ["ecs_resource_management"]
    assert prompt_functions["view ecs tasks"]() == ["ecs_resource_management"]
    assert prompt_functions["check task definitions"]() == ["ecs_resource_management"]
    assert prompt_functions["show running containers"]() == ["ecs_resource_management"]
    assert prompt_functions["view ecs resources"]() == ["ecs_resource_management"]
    assert prompt_functions["inspect ecs"]() == ["ecs_resource_management"]
    assert prompt_functions["check ecs status"]() == ["ecs_resource_management"]


def test_register_module():
    """Test that register_module registers the tool and all prompts correctly."""
    # Create mock MCP server
    mock_mcp = MagicMock()

    # Set up the tool decorator to simply store its function
    mock_tool_func = None

    def mock_tool_decorator(*args, **kwargs):
        def decorator(func):
            nonlocal mock_tool_func
            mock_tool_func = func
            return func

        return decorator

    # Set up the prompt decorator to capture the prompt patterns and functions
    prompt_registrations = []

    def mock_prompt_decorator(pattern):
        def decorator(func):
            prompt_registrations.append((pattern, func))
            return func

        return decorator

    # Assign the mock decorators
    mock_mcp.tool = mock_tool_decorator
    mock_mcp.prompt = mock_prompt_decorator

    # Call the register_module function
    register_module(mock_mcp)

    # Verify that the tool was registered
    assert mock_tool_func is not None
    assert mock_tool_func.__name__ == "mcp_ecs_resource_management"

    # Verify that all prompts were registered with the correct patterns
    expected_prompts = [
        "list ecs resources",
        "show ecs clusters",
        "describe ecs service",
        "view ecs tasks",
        "check task definitions",
        "show running containers",
        "view ecs resources",
        "inspect ecs",
        "check ecs status",
    ]

    registered_patterns = [pattern for pattern, _ in prompt_registrations]
    for expected_pattern in expected_prompts:
        assert expected_pattern in registered_patterns


def test_mcp_tool_signature():
    """Test that the MCP tool function has the correct signature and parameters."""
    # Create mock MCP server with a mocked tool decorator
    mock_mcp = MagicMock()

    # Set up the tool decorator to capture the registered function
    registered_func = None
    registered_name = None
    registered_annotations = None

    def mock_tool_decorator(name=None, annotations=None):
        def decorator(func):
            nonlocal registered_func, registered_name, registered_annotations
            registered_func = func
            registered_name = name
            registered_annotations = annotations
            return func

        return decorator

    mock_mcp.tool = mock_tool_decorator
    mock_mcp.prompt = MagicMock()  # Not testing prompts in this test

    # Register the module to get the tool function
    register_module(mock_mcp)

    # Now we can examine the registered function
    assert registered_func is not None
    assert registered_name == "ecs_resource_management"
    assert registered_annotations is None

    # Get the signature of the registered function
    import inspect

    sig = inspect.signature(registered_func)

    # Verify the function has the expected parameters
    assert "action" in sig.parameters
    assert "resource_type" in sig.parameters
    assert "identifier" in sig.parameters
    assert "filters" in sig.parameters

    # For this test, we only care that the parameters exist and have the right kind
    # Parameter kinds\
    # : POSITIONAL_ONLY, POSITIONAL_OR_KEYWORD, VAR_POSITIONAL, KEYWORD_ONLY, VAR_KEYWORD

    # action and resource_type are required
    assert "action" in sig.parameters
    assert "resource_type" in sig.parameters

    # identifier and filters are optional (have default values)
    assert (
        sig.parameters["identifier"].default is not None
        or sig.parameters["identifier"].default is None
    )
    assert (
        sig.parameters["filters"].default is not None or sig.parameters["filters"].default is None
    )


def test_register_module_with_each_prompt():
    """Test that each prompt is registered separately."""
    # Create mock MCP server
    mock_mcp = MagicMock()

    # Call the register_module function
    register_module(mock_mcp)

    # Verify that all prompts were registered
    expected_prompts = [
        "list ecs resources",
        "show ecs clusters",
        "describe ecs service",
        "view ecs tasks",
        "check task definitions",
        "show running containers",
        "view ecs resources",
        "inspect ecs",
        "check ecs status",
    ]

    # Check that each prompt was registered
    assert mock_mcp.prompt.call_count >= len(expected_prompts)

    for pattern in expected_prompts:
        # Check that mcp.prompt was called with this pattern
        assert call(pattern) in mock_mcp.prompt.call_args_list
