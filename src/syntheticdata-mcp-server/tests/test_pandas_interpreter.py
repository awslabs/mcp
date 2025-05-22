"""Tests for pandas code interpreter functionality."""

import ast
import os
import pandas as pd
import pytest
from awslabs.syntheticdata_mcp_server.pandas_interpreter import (
    check_referential_integrity,
    execute_pandas_code,
    safe_eval_dataframe,
)


def test_safe_eval_dataframe_valid():
    """Test safe_eval_dataframe with valid DataFrame constructor."""
    code = "df = pd.DataFrame({'a': [1, 2, 3]})"
    tree = ast.parse(code)
    assign_node = tree.body[0]
    assert isinstance(assign_node, ast.Assign)
    df = safe_eval_dataframe(assign_node)
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ['a']
    assert len(df) == 3


def test_safe_eval_dataframe_invalid_constructor():
    """Test safe_eval_dataframe with invalid constructor."""
    code = "df = DataFrame({'a': [1, 2, 3]})"  # Missing pd.
    tree = ast.parse(code)
    assign_node = tree.body[0]
    assert isinstance(assign_node, ast.Assign)
    with pytest.raises(ValueError, match='Invalid DataFrame constructor: invalid function call'):
        safe_eval_dataframe(assign_node)


def test_safe_eval_dataframe_wrong_constructor():
    """Test safe_eval_dataframe with wrong constructor."""
    code = 'df = pd.Series([1, 2, 3])'
    tree = ast.parse(code)
    assign_node = tree.body[0]
    assert isinstance(assign_node, ast.Assign)
    with pytest.raises(ValueError, match='Only pd.DataFrame constructors are allowed'):
        safe_eval_dataframe(assign_node)


def test_execute_pandas_code_success(temp_dir: str, sample_pandas_code: str) -> None:
    """Test successful execution of pandas code."""
    result = execute_pandas_code(sample_pandas_code, temp_dir)

    assert result['success'] is True
    assert len(result['saved_files']) == 3
    assert 'customers_df.csv' in os.listdir(temp_dir)
    assert 'orders_df.csv' in os.listdir(temp_dir)
    assert 'addresses_df.csv' in os.listdir(temp_dir)

    # Verify file contents
    customers_df = pd.read_csv(os.path.join(temp_dir, 'customers_df.csv'))
    assert len(customers_df) == 3
    assert set(customers_df.columns) == {'customer_id', 'name', 'email', 'city'}

    orders_df = pd.read_csv(os.path.join(temp_dir, 'orders_df.csv'))
    assert len(orders_df) == 4
    assert set(orders_df.columns) == {'order_id', 'customer_id', 'amount', 'status'}

    addresses_df = pd.read_csv(os.path.join(temp_dir, 'addresses_df.csv'))
    assert len(addresses_df) == 4
    assert set(addresses_df.columns) == {'address_id', 'city', 'zip_code'}


def test_execute_pandas_code_no_dataframes(temp_dir: str) -> None:
    """Test execution with code that doesn't create any DataFrames."""
    code = """
    x = 1
    y = 2
    result = x + y
    """
    result = execute_pandas_code(code, temp_dir)

    assert result['success'] is False
    assert result['message'] == 'No DataFrames found in the code'
    assert result['error'] == 'No DataFrames found in the code'
    assert not os.listdir(temp_dir)


def test_execute_pandas_code_syntax_error(temp_dir: str) -> None:
    """Test handling of syntax errors in pandas code."""
    code = """
    # This code has a syntax error
    customers_df = pd.DataFrame({
        'id': [1, 2, 3]
        'name': ['A', 'B', 'C']  # Missing comma
    })
    """
    result = execute_pandas_code(code, temp_dir)

    assert result['success'] is False
    assert result['message'] == 'No DataFrames found in the code'
    assert result['error'] == 'No DataFrames found in the code'


def test_execute_pandas_code_invalid_directory(temp_dir: str) -> None:
    """Test handling of invalid output directory."""
    # Create a path that we know will be invalid (inside a file)
    dummy_file = os.path.join(temp_dir, 'dummy.txt')
    with open(dummy_file, 'w') as f:
        f.write('dummy')

    # Try to use the file as a directory - this will always fail
    invalid_dir = os.path.join(dummy_file, 'subdir')
    code = """df = pd.DataFrame({'a': [1, 2, 3]})"""
    result = execute_pandas_code(code, invalid_dir)

    assert result['success'] is False
    assert result['message'].startswith('[Errno 20] Not a directory:')


def test_check_referential_integrity() -> None:
    """Test referential integrity checking."""
    # Create test data with known integrity issues
    customers_df = pd.DataFrame({'customer_id': [1, 2, 3], 'name': ['Alice', 'Bob', 'Charlie']})

    orders_df = pd.DataFrame(
        {
            'order_id': [1, 2, 3, 4],
            'customer_id': [1, 4, 5, 6],  # 4, 5, and 6 don't exist in customers
            'amount': [100, 200, 300, 400],
        }
    )

    addresses_df = pd.DataFrame(
        {
            'city': ['New York', 'New York', 'Chicago', 'Chicago', 'Chicago'],
            'zip_code': [
                '10001',
                '10001',
                '60601',
                '60601',
                '60601',
            ],  # Strong functional dependency
        }
    )

    dataframes = {'customers': customers_df, 'orders': orders_df, 'addresses': addresses_df}

    issues = check_referential_integrity(dataframes)

    # Check referential integrity issues
    ref_issues = [i for i in issues if i['type'] == 'referential_integrity']
    assert len(ref_issues) > 0, 'No referential integrity issues found'

    # Find the specific referential integrity issue
    found_ref_issue = False
    for issue in ref_issues:
        if (
            issue['source_table'] == 'orders'
            and issue['target_table'] == 'customers'
            and issue['column'] == 'customer_id'
            and set(issue['missing_values']).issuperset({4, 5, 6})
        ):  # More missing values
            found_ref_issue = True
            break
    assert found_ref_issue, 'Expected referential integrity issue not found'

    # Check functional dependency issues
    func_issues = [i for i in issues if i['type'] == 'functional_dependency']
    assert len(func_issues) > 0, 'No functional dependency issues found'

    # Find the specific functional dependency issue
    found_func_issue = False
    for issue in func_issues:
        if (
            issue['table'] == 'addresses'
            and issue['determinant'] == 'city'
            and issue['dependent'] == 'zip_code'
        ):
            found_func_issue = True
            break
    assert found_func_issue, 'Expected functional dependency issue not found'


def test_execute_pandas_code_directory_creation(temp_dir: str, sample_pandas_code: str) -> None:
    """Test that output directory is created if it doesn't exist."""
    output_dir = os.path.join(temp_dir, 'output')
    result = execute_pandas_code(sample_pandas_code, output_dir)

    assert result['success'] is True
    assert os.path.exists(output_dir)
    assert len(os.listdir(output_dir)) == 3


@pytest.mark.parametrize(
    'code,expected_error',
    [
        ('import os; os.system("echo hack")', 'NameError'),  # Security: No access to os
        ('import sys; sys.exit(1)', 'NameError'),  # Security: No access to sys
        ('__import__("os")', 'NameError'),  # Security: No dynamic imports
    ],
)
def test_execute_pandas_code_security(temp_dir: str, code: str, expected_error: str) -> None:
    """Test that code execution is properly sandboxed."""
    result = execute_pandas_code(code, temp_dir)

    assert result['success'] is False
    assert result['message'] == 'No DataFrames found in the code'
    assert result['error'] == 'No DataFrames found in the code'
    assert not os.listdir(temp_dir)  # No files should be created
