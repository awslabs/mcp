"""Tests for the scanner module of the diagrams-mcp-server."""

import pytest
from diagrams_mcp_server.scanner import (
    check_dangerous_functions,
    check_security,
    count_code_metrics,
    scan_python_code,
    validate_syntax,
)


class TestSyntaxValidation:
    """Tests for the syntax validation functionality."""

    @pytest.mark.asyncio
    async def test_valid_syntax(self):
        """Test that valid Python syntax is accepted."""
        code = 'print("Hello, world!")'
        valid, error = await validate_syntax(code)
        assert valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_invalid_syntax(self):
        """Test that invalid Python syntax is rejected."""
        code = 'print("Hello, world!'  # Missing closing quote
        valid, error = await validate_syntax(code)
        assert valid is False
        assert error is not None
        assert 'Syntax error' in error

    @pytest.mark.asyncio
    async def test_complex_valid_syntax(self):
        """Test that complex valid Python syntax is accepted."""
        code = """
def factorial(n):
    if n <= 1:
        return 1
    else:
        return n * factorial(n - 1)

print(factorial(5))
"""
        valid, error = await validate_syntax(code)
        assert valid is True
        assert error is None


class TestSecurityChecking:
    """Tests for the security checking functionality."""

    @pytest.mark.asyncio
    async def test_safe_code(self):
        """Test that safe code passes security checks."""
        code = """
def add(a, b):
    return a + b

print(add(2, 3))
"""
        issues = await check_security(code)
        assert len(issues) == 0

    @pytest.mark.asyncio
    async def test_dangerous_code(self):
        """Test that dangerous code is flagged."""
        code = """
import os
os.system("rm -rf /")  # This is dangerous
"""
        issues = await check_security(code)
        assert len(issues) > 0
        assert any('os.system' in issue.issue_text for issue in issues)

    @pytest.mark.asyncio
    async def test_exec_code(self):
        """Test that code with exec is flagged."""
        code = """
exec("print('Hello, world!')")  # This is dangerous
"""
        issues = await check_security(code)
        assert len(issues) > 0
        assert any('exec' in issue.issue_text for issue in issues)


class TestCodeMetrics:
    """Tests for the code metrics calculation functionality."""

    @pytest.mark.asyncio
    async def test_empty_code(self):
        """Test metrics for empty code."""
        code = ''
        metrics = await count_code_metrics(code)
        assert metrics.total_lines == 0
        assert metrics.code_lines == 0
        assert metrics.comment_lines == 0
        assert metrics.blank_lines == 0
        assert metrics.comment_ratio == 0

    @pytest.mark.asyncio
    async def test_code_with_comments(self):
        """Test metrics for code with comments."""
        code = """# This is a comment
def add(a, b):
    # This is another comment
    return a + b

# This is a third comment
print(add(2, 3))
"""
        metrics = await count_code_metrics(code)
        assert metrics.total_lines == 7
        assert metrics.code_lines == 4
        assert metrics.comment_lines == 3
        assert metrics.blank_lines == 0
        assert metrics.comment_ratio == pytest.approx(42.86, 0.01)  # 3/7 * 100

    @pytest.mark.asyncio
    async def test_code_with_blank_lines(self):
        """Test metrics for code with blank lines."""
        code = """
def add(a, b):
    return a + b

print(add(2, 3))

"""
        metrics = await count_code_metrics(code)
        assert metrics.total_lines == 6
        assert metrics.code_lines == 3
        assert metrics.comment_lines == 0
        assert metrics.blank_lines == 3
        assert metrics.comment_ratio == 0


class TestDangerousFunctions:
    """Tests for the dangerous function detection functionality."""

    def test_no_dangerous_functions(self):
        """Test that code with no dangerous functions is safe."""
        code = """
def add(a, b):
    return a + b

print(add(2, 3))
"""
        dangerous = check_dangerous_functions(code)
        assert len(dangerous) == 0

    def test_exec_function(self):
        """Test that exec is detected as dangerous."""
        code = """
exec("print('Hello, world!')")
"""
        dangerous = check_dangerous_functions(code)
        assert len(dangerous) == 1
        assert dangerous[0]['function'] == 'exec'

    def test_eval_function(self):
        """Test that eval is detected as dangerous."""
        code = """
eval("2 + 2")
"""
        dangerous = check_dangerous_functions(code)
        assert len(dangerous) == 1
        assert dangerous[0]['function'] == 'eval'

    def test_os_system(self):
        """Test that os.system is detected as dangerous."""
        code = """
import os
os.system("echo Hello")
"""
        dangerous = check_dangerous_functions(code)
        assert len(dangerous) == 1
        assert dangerous[0]['function'] == 'os.system'

    def test_multiple_dangerous_functions(self):
        """Test that multiple dangerous functions are detected."""
        code = """
import os
import pickle

exec("print('Hello')")
eval("2 + 2")
os.system("echo Hello")
pickle.loads(b"...")
"""
        dangerous = check_dangerous_functions(code)
        assert len(dangerous) == 4
        functions = [d['function'] for d in dangerous]
        assert 'exec' in functions
        assert 'eval' in functions
        assert 'os.system' in functions
        assert 'pickle.loads' in functions


class TestScanPythonCode:
    """Tests for the scan_python_code function."""

    @pytest.mark.asyncio
    async def test_safe_code(self):
        """Test scanning safe code."""
        code = """
def add(a, b):
    return a + b

print(add(2, 3))
"""
        result = await scan_python_code(code)
        assert result.has_errors is False
        assert result.syntax_valid is True
        assert len(result.security_issues) == 0
        assert result.error_message is None
        assert result.metrics is not None

    @pytest.mark.asyncio
    async def test_syntax_error(self):
        """Test scanning code with syntax errors."""
        code = """
def add(a, b):
    return a + b
print(add(2, 3)
"""  # Missing closing parenthesis
        result = await scan_python_code(code)
        assert result.has_errors is True
        assert result.syntax_valid is False
        assert result.error_message is not None
        assert 'Syntax error' in result.error_message

    @pytest.mark.asyncio
    async def test_security_issue(self):
        """Test scanning code with security issues."""
        code = """
import os
os.system("rm -rf /")  # This is dangerous
"""
        result = await scan_python_code(code)
        assert result.has_errors is True
        assert result.syntax_valid is True
        assert len(result.security_issues) > 0
        assert result.error_message is not None
        assert result.metrics is not None

    @pytest.mark.asyncio
    async def test_dangerous_function(self):
        """Test scanning code with dangerous functions."""
        code = """
exec("print('Hello, world!')")  # This is dangerous
"""
        result = await scan_python_code(code)
        assert result.has_errors is True
        assert result.syntax_valid is True
        assert len(result.security_issues) > 0
        assert result.error_message is not None
        assert any('exec' in issue.issue_text for issue in result.security_issues)
