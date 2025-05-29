"""Tests for the Step Functions Tool MCP Server."""

from awslabs.stepfunctions_tool_mcp_server.server import __version__


def test_version_matches_pyproject():
    """Test that the version in server.py matches pyproject.toml."""
    import pathlib
    import tomli

    # Read pyproject.toml
    pyproject_path = pathlib.Path(__file__).parent.parent / 'pyproject.toml'
    with open(pyproject_path, 'rb') as f:
        pyproject = tomli.load(f)

    # Get version from pyproject.toml
    pyproject_version = pyproject['project']['version']

    # Verify versions match
    assert __version__ == pyproject_version, (
        f'Version mismatch: server.py has version {__version__}, '
        f'but pyproject.toml has version {pyproject_version}'
    )
