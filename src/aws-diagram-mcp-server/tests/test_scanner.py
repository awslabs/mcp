# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Tests for the scanner module of the diagrams-mcp-server."""

import pytest
from awslabs.aws_diagram_mcp_server.scanner import (
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

    @pytest.mark.asyncio
    async def test_import_rejected(self):
        """Test that import statements are rejected."""
        code = """
import os
print("Hello")
"""
        valid, error = await validate_syntax(code)
        assert valid is False
        assert error is not None
        assert 'Import statements are not allowed' in error

    @pytest.mark.asyncio
    async def test_import_from_rejected(self):
        """Test that from...import statements are rejected."""
        code = """
from typing import List
print("Hello")
"""
        valid, error = await validate_syntax(code)
        assert valid is False
        assert error is not None
        assert 'Import statements are not allowed' in error


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
exec("malicious_code")
eval("dangerous_expression")
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


class TestASTDangerousFunctions:
    """Tests for AST-based dangerous function detection."""

    # --- Dangerous builtin calls ---

    def test_detects_exec(self):
        """Test that exec() is detected via AST."""
        results = check_dangerous_functions('exec("code")')
        assert len(results) == 1
        assert results[0]['function'] == 'exec'

    def test_detects_eval(self):
        """Test that eval() is detected via AST."""
        results = check_dangerous_functions('eval("2+2")')
        assert len(results) == 1
        assert results[0]['function'] == 'eval'

    def test_detects_compile(self):
        """Test that compile() is detected via AST."""
        results = check_dangerous_functions('compile("code", "<string>", "exec")')
        assert len(results) == 1
        assert results[0]['function'] == 'compile'

    def test_detects_getattr(self):
        """Test that getattr() is detected via AST."""
        results = check_dangerous_functions('getattr(obj, "attr")')
        assert len(results) == 1
        assert results[0]['function'] == 'getattr'

    def test_detects_setattr(self):
        """Test that setattr() is detected via AST."""
        results = check_dangerous_functions('setattr(obj, "attr", value)')
        assert len(results) == 1
        assert results[0]['function'] == 'setattr'

    def test_detects_delattr(self):
        """Test that delattr() is detected via AST."""
        results = check_dangerous_functions('delattr(obj, "attr")')
        assert len(results) == 1
        assert results[0]['function'] == 'delattr'

    def test_detects_vars(self):
        """Test that vars() is detected via AST."""
        results = check_dangerous_functions('vars(obj)')
        assert len(results) == 1
        assert results[0]['function'] == 'vars'

    def test_detects_open(self):
        """Test that open() is detected via AST."""
        results = check_dangerous_functions('open("file.txt")')
        assert len(results) == 1
        assert results[0]['function'] == 'open'

    def test_detects_globals(self):
        """Test that globals() is detected via AST."""
        results = check_dangerous_functions('globals()')
        assert len(results) == 1
        assert results[0]['function'] == 'globals'

    def test_detects_locals(self):
        """Test that locals() is detected via AST."""
        results = check_dangerous_functions('locals()')
        assert len(results) == 1
        assert results[0]['function'] == 'locals'

    def test_detects_breakpoint(self):
        """Test that breakpoint() is detected via AST."""
        results = check_dangerous_functions('breakpoint()')
        assert len(results) == 1
        assert results[0]['function'] == 'breakpoint'

    def test_detects_import_dunder(self):
        """Test that __import__() is detected via AST."""
        results = check_dangerous_functions('__import__("os")')
        assert any(r['function'] == '__import__' for r in results)

    def test_detects_spawn(self):
        """Test that spawn() is detected via AST."""
        results = check_dangerous_functions('spawn("cmd")')
        assert len(results) == 1
        assert results[0]['function'] == 'spawn'

    # --- Dangerous attribute calls ---

    def test_detects_subprocess_run(self):
        """Test that subprocess.run() is detected via AST."""
        results = check_dangerous_functions('subprocess.run(["ls", "-la"])')
        assert len(results) == 1
        assert results[0]['function'] == 'subprocess.run'

    def test_detects_subprocess_popen(self):
        """Test that subprocess.Popen() is detected via AST."""
        results = check_dangerous_functions('subprocess.Popen("cmd")')
        assert len(results) == 1
        assert results[0]['function'] == 'subprocess.Popen'

    def test_detects_pickle_load(self):
        """Test that pickle.load() is detected via AST."""
        results = check_dangerous_functions('pickle.load(f)')
        assert len(results) == 1
        assert results[0]['function'] == 'pickle.load'

    def test_detects_os_popen(self):
        """Test that os.popen() is detected via AST."""
        results = check_dangerous_functions('os.popen("cmd").read()')
        assert any(r['function'] == 'os.popen' for r in results)

    # --- Dunder attribute access ---

    def test_detects_dict_dunder(self):
        """Test that __dict__ access is detected via AST."""
        results = check_dangerous_functions('obj.__dict__')
        assert any(r['function'] == '__dict__' for r in results)

    def test_detects_builtins_dunder(self):
        """Test that __builtins__ access is detected via AST."""
        results = check_dangerous_functions('__builtins__')
        assert any(r['function'] == '__builtins__' for r in results)

    def test_detects_class_dunder(self):
        """Test that __class__ access is detected via AST."""
        results = check_dangerous_functions('obj.__class__')
        assert any(r['function'] == '__class__' for r in results)

    def test_detects_subclasses_dunder(self):
        """Test that __subclasses__() access is detected via AST."""
        results = check_dangerous_functions('obj.__class__.__subclasses__()')
        funcs = [r['function'] for r in results]
        assert '__subclasses__' in funcs

    def test_detects_bases_dunder(self):
        """Test that __bases__ access is detected via AST."""
        results = check_dangerous_functions('obj.__class__.__bases__')
        funcs = [r['function'] for r in results]
        assert '__bases__' in funcs

    def test_detects_globals_dunder(self):
        """Test that __globals__ attribute access is detected via AST."""
        results = check_dangerous_functions('func.__globals__')
        assert any(r['function'] == '__globals__' for r in results)

    # --- False positive prevention ---

    def test_no_false_positive_exec_in_string(self):
        """Test that 'exec' inside a string literal is not flagged."""
        results = check_dangerous_functions('message = "do not use exec in production"')
        assert len(results) == 0

    def test_no_false_positive_exec_in_comment(self):
        """Test that 'exec' inside a comment is not flagged."""
        results = check_dangerous_functions('# exec("malicious")\nprint("safe")')
        assert len(results) == 0

    def test_no_false_positive_exec_in_docstring(self):
        """Test that 'exec' inside a docstring is not flagged."""
        results = check_dangerous_functions('"""exec("hidden")"""')
        assert len(results) == 0

    def test_no_false_positive_variable_name_executor(self):
        """Test that variable names like executor are not flagged."""
        results = check_dangerous_functions('executor = None\nevaluator = None')
        assert len(results) == 0

    def test_no_false_positive_safe_diagram_code(self):
        """Test that legitimate diagram code is not flagged."""
        code = (
            'with Diagram("AWS Architecture", show=False):\n'
            '    web = EC2("Web Server")\n'
            '    db = RDS("Database")\n'
            '    web >> db'
        )
        results = check_dangerous_functions(code)
        assert len(results) == 0

    def test_no_false_positive_function_def_spawn(self):
        """Test that a function named spawn_worker is not flagged."""
        results = check_dangerous_functions('def spawn_worker(self):\n    return "worker"')
        assert len(results) == 0

    def test_no_false_positive_print_call(self):
        """Test that print() is not flagged."""
        results = check_dangerous_functions('print("Hello, world!")')
        assert len(results) == 0

    # --- Edge cases ---

    def test_empty_code(self):
        """Test that empty code produces no results."""
        results = check_dangerous_functions('')
        assert len(results) == 0

    def test_syntax_error_fallback(self):
        """Test that string fallback is used when code has syntax errors."""
        code = 'exec("code"\n'  # Missing closing paren - SyntaxError
        results = check_dangerous_functions(code)
        assert len(results) > 0
        assert any(r['function'] == 'exec' for r in results)

    def test_line_number_accuracy(self):
        """Test that line numbers are accurate in AST results."""
        code = 'x = 1\ny = 2\nexec("code")\nz = 3'
        results = check_dangerous_functions(code)
        assert len(results) == 1
        assert results[0]['line'] == 3
        assert results[0]['function'] == 'exec'

    def test_nested_calls_both_detected(self):
        """Test that nested dangerous calls are both detected."""
        code = 'exec(eval("code"))'
        results = check_dangerous_functions(code)
        funcs = [r['function'] for r in results]
        assert 'exec' in funcs
        assert 'eval' in funcs

    # --- Known bypass vectors now caught ---

    def test_catches_getattr_bypass(self):
        """Test that getattr-based exec bypass is caught."""
        code = 'getattr(__builtins__, "exec")("print(1)")'
        results = check_dangerous_functions(code)
        funcs = [r['function'] for r in results]
        assert 'getattr' in funcs
        assert '__builtins__' in funcs

    def test_catches_globals_bypass(self):
        """Test that globals()-based bypass is caught."""
        code = 'globals()["exec"]("print(1)")'
        results = check_dangerous_functions(code)
        funcs = [r['function'] for r in results]
        assert 'globals' in funcs

    def test_catches_vars_bypass(self):
        """Test that vars()-based bypass is caught."""
        code = 'vars()["exec"]("print(1)")'
        results = check_dangerous_functions(code)
        funcs = [r['function'] for r in results]
        assert 'vars' in funcs

    def test_catches_class_traversal(self):
        """Test that class hierarchy traversal is caught."""
        code = '"".__class__.__bases__[0].__subclasses__()'
        results = check_dangerous_functions(code)
        funcs = [r['function'] for r in results]
        assert '__class__' in funcs
        assert '__bases__' in funcs
        assert '__subclasses__' in funcs

    def test_catches_dict_access_bypass(self):
        """Test that __dict__ access bypass is caught."""
        code = 'obj.__dict__["secret"]'
        results = check_dangerous_functions(code)
        funcs = [r['function'] for r in results]
        assert '__dict__' in funcs

    def test_catches_compile_bypass(self):
        """Test that compile() is caught as dangerous."""
        code = 'compile("print(1)", "<string>", "exec")'
        results = check_dangerous_functions(code)
        funcs = [r['function'] for r in results]
        assert 'compile' in funcs
