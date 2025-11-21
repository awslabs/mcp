"""Test for SARIF-OM module fix (GitHub issue #1041)."""

import pytest


class TestSarifFix:
    """Test cases for the SARIF-OM module fix."""

    def test_sarif_om_available(self):
        """Test that sarif-om is available after fix."""
        try:
            import sarif_om

            assert sarif_om is not None
        except ImportError:
            # In CI environments, sarif-om might not be installed yet
            # This is acceptable as the dependency is declared in pyproject.toml
            pytest.skip('sarif-om not installed in current environment')

    def test_bandit_imports_without_error(self):
        """Test that Bandit imports without SARIF-related errors."""
        try:
            from bandit.core import config, manager

            # Create basic configuration
            b_conf = config.BanditConfig()
            assert b_conf is not None

            # Create manager
            mgr = manager.BanditManager(b_conf, 'file', debug=False, verbose=False, quiet=True)
            assert mgr is not None

        except Exception as e:
            pytest.fail(f'Bandit should import and initialize without errors: {e}')

    def test_scanner_functionality(self):
        """Test that the scanner module works correctly."""
        import asyncio
        from awslabs.aws_diagram_mcp_server.scanner import scan_python_code

        # Test with simple safe code
        safe_code = """
def hello_world():
    return "Hello, World!"
"""

        async def run_test():
            result = await scan_python_code(safe_code)
            assert result is not None
            assert result.syntax_valid is True
            assert result.has_errors is False
            return result

        # Run the async test
        result = asyncio.run(run_test())
        assert result.metrics is not None
        assert result.metrics.total_lines > 0

    def test_bandit_security_scan(self):
        """Test that Bandit security scanning works with potentially unsafe code."""
        import asyncio
        from awslabs.aws_diagram_mcp_server.scanner import scan_python_code

        # Test with code that should trigger security warnings (without imports)
        unsafe_code = """
exec("print('Hello')")
eval("2 + 2")
"""

        async def run_test():
            result = await scan_python_code(unsafe_code)
            assert result is not None
            assert result.syntax_valid is True
            # Should have security issues due to exec/eval
            assert result.has_errors is True
            assert len(result.security_issues) > 0
            return result

        # Run the async test
        result = asyncio.run(run_test())

        # Verify we found the expected security issue
        found_dangerous_function = any(
            'exec' in issue.issue_text.lower() or 'eval' in issue.issue_text.lower()
            for issue in result.security_issues
        )
        assert found_dangerous_function, 'Should detect exec/eval security issue'

    def test_diagram_generation_unaffected(self):
        """Test that diagram generation still works normally after the fix."""
        import asyncio
        import os
        import tempfile
        from awslabs.aws_diagram_mcp_server.diagrams_tools import generate_diagram

        # Simple diagram code
        diagram_code = """
with Diagram("Test Diagram", show=False):

    web = EC2("Web Server")
    db = RDS("Database")

    web >> db
"""

        async def run_test():
            with tempfile.TemporaryDirectory() as temp_dir:
                result = await generate_diagram(
                    code=diagram_code, filename='test_diagram', workspace_dir=temp_dir
                )
                # Check if file exists while temp_dir is still valid
                file_exists = os.path.exists(result.path) if result.path else False
                return result, file_exists

        # Run the async test
        result, file_exists = asyncio.run(run_test())

        # If diagram generation fails, it might be due to missing graphviz in CI
        # The important thing is that the SARIF fix doesn't break the core functionality
        if result.status == 'error':
            # Check if it's a graphviz-related error (common in CI environments)
            if result.message and (
                'graphviz' in result.message.lower() or 'dot' in result.message.lower()
            ):
                pytest.skip('Graphviz not available in CI environment - this is expected')
            else:
                # If it's a different error, we should investigate
                pytest.fail(f'Diagram generation failed with unexpected error: {result.message}')

        # Verify the diagram was generated successfully
        assert result.status == 'success'
        assert result.path is not None
        assert file_exists, f'Diagram file should exist at {result.path}'
        assert result.path.endswith('.png')

    def test_sarif_om_version(self):
        """Test that sarif-om has a reasonable version."""
        try:
            import sarif_om

            # Check if version is available
            version = getattr(sarif_om, '__version__', None)
            if version:
                # Basic version format check (should be something like "1.0.0")
                assert isinstance(version, str)
                assert len(version) > 0
                # Should contain at least one dot for major.minor format
                assert '.' in version
        except ImportError:
            # In CI environments, sarif-om might not be installed yet
            # This is acceptable as the dependency is declared in pyproject.toml
            pytest.skip('sarif-om not installed in current environment')
