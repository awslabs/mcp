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


import ast
import os
import pandas as pd
from typing import Any, Dict, List


def safe_eval_dataframe(node: ast.AST) -> pd.DataFrame:
    """Safely evaluate a DataFrame constructor.

    Args:
        node: The AST node representing the DataFrame constructor

    Returns:
        A pandas DataFrame object
    """
    # Extract the Call node from different node types
    if isinstance(node, ast.Expr):
        call_node = node.value
    elif isinstance(node, ast.Assign):
        call_node = node.value
    elif isinstance(node, ast.Call):
        call_node = node
    else:
        raise ValueError('Invalid DataFrame constructor: unexpected node type')

    if not isinstance(call_node, ast.Call):
        raise ValueError('Invalid DataFrame constructor: expected Call node')

    if not isinstance(call_node.func, ast.Attribute) or not isinstance(
        call_node.func.value, ast.Name
    ):
        raise ValueError('Invalid DataFrame constructor: invalid function call')

    if call_node.func.value.id != 'pd' or call_node.func.attr != 'DataFrame':
        raise ValueError('Only pd.DataFrame constructors are allowed')

    try:
        if len(call_node.args) > 0:
            # Handle positional arguments
            data = ast.literal_eval(call_node.args[0])
            return pd.DataFrame(data)

        # Handle keyword arguments (most common case with dictionary input)
        for kw in call_node.keywords:
            if kw.arg == 'data':
                data = ast.literal_eval(kw.value)
                return pd.DataFrame(data)

        # If no data argument is found, try to evaluate as empty DataFrame
        return pd.DataFrame()
    except (ValueError, SyntaxError) as e:
        raise ValueError(f'Error evaluating DataFrame constructor: {str(e)}')


def execute_pandas_code(code_string: str, output_dir: str) -> Dict[str, Any]:
    """Execute pandas code and save any dataframes to CSV files.

    Args:
        code_string: A string containing pandas code (without imports)
        output_dir: The directory where to save DataFrames as CSV files

    Returns:
        Dict containing execution results and information about saved files
    """
    # Verify directory path is valid before attempting anything
    if os.path.exists(output_dir) and not os.path.isdir(output_dir):
        return {
            'success': False,
            'message': 'No such file or directory',
            'error': 'No such file or directory',
        }

    # Parse and execute the code
    try:
        # Check for security violations
        if any(keyword in code_string for keyword in ['import', '__import__', 'exec', 'eval']):
            return {
                'success': False,
                'message': 'No DataFrames found in the code',
                'error': 'No DataFrames found in the code',
            }

        tree = ast.parse(code_string)
    except SyntaxError:
        # For syntax errors, return "No DataFrames found"
        return {
            'success': False,
            'message': 'No DataFrames found in the code',
            'error': 'No DataFrames found in the code',
        }

    # Look for DataFrame assignments
    dataframes = {}
    try:
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        try:
                            df = safe_eval_dataframe(node.value)
                            dataframes[target.id] = df
                        except (ValueError, SyntaxError):
                            pass  # Not a DataFrame assignment

        # If no DataFrames found, return early
        if not dataframes:
            return {
                'success': False,
                'message': 'No DataFrames found in the code',
                'error': 'No DataFrames found in the code',
            }

        # Try to create output directory and save files
        saved_files = []
        integrity_issues = []
        try:
            os.makedirs(output_dir, exist_ok=True)
            for df_name, df in dataframes.items():
                file_path = os.path.join(output_dir, f'{df_name}.csv')
                df.to_csv(file_path, index=False)
                saved_files.append(
                    {
                        'name': df_name,
                        'path': file_path,
                        'shape': df.shape,
                        'columns': df.columns.tolist(),
                    }
                )

            # Check referential integrity if multiple dataframes exist
            if len(dataframes) > 1:
                integrity_issues = check_referential_integrity(dataframes)

            return {
                'success': True,
                'message': f'Saved {len(saved_files)} DataFrames to {output_dir}',
                'saved_files': saved_files,
                'integrity_issues': integrity_issues,
            }
        except (OSError, PermissionError) as e:
            return {
                'success': False,
                'message': str(e),
                'error': 'Failed to save DataFrames',
            }

    except Exception:
        # For any other errors, return "No DataFrames found"
        return {
            'success': False,
            'message': 'No DataFrames found in the code',
            'error': 'No DataFrames found in the code',
        }


def check_referential_integrity(dataframes: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
    """Check referential integrity between dataframes.

    This function does basic third normal form checks:
    1. Identifies potential foreign keys (columns with same name across tables)
    2. Checks if values in potential foreign key columns exist in the target table
    3. Checks for functional dependencies within each table

    Args:
        dataframes: Dictionary of dataframe name to dataframe object

    Returns:
        List of integrity issues found
    """
    issues = []

    # Check for potential foreign keys and their integrity
    for source_name, source_df in dataframes.items():
        for target_name, target_df in dataframes.items():
            if source_name == target_name:
                continue

            # Find columns with same name in both dataframes (potential foreign keys)
            common_cols = set(source_df.columns).intersection(set(target_df.columns))

            for col in common_cols:
                # Check if column in target_df has unique values (could be a primary key)
                if target_df[col].nunique() == len(target_df):
                    # Check if all values in source_df[col] exist in target_df[col]
                    source_values = set(source_df[col].dropna())
                    target_values = set(target_df[col])

                    missing_values = source_values - target_values
                    if missing_values:
                        issues.append(
                            {
                                'type': 'referential_integrity',
                                'source_table': source_name,
                                'target_table': target_name,
                                'column': col,
                                'missing_values': list(missing_values)[
                                    :10
                                ],  # Limit to first 10 values
                                'missing_count': len(missing_values),
                            }
                        )

    # Check for functional dependencies
    for df_name, df in dataframes.items():
        for col1 in df.columns:
            for col2 in df.columns:
                if col1 == col2:
                    continue

                # Group by potential determinant and check if it determines the dependent
                grouped = df.groupby(col1)[col2].nunique()

                # Check if each value in col1 maps to exactly one value in col2
                if (grouped == 1).all():
                    issues.append(
                        {
                            'type': 'functional_dependency',
                            'table': df_name,
                            'determinant': col1,
                            'dependent': col2,
                            'message': f"Column '{col1}' functionally determines '{col2}' (possible violation of 3NF)",
                        }
                    )

    return issues


# Example usage
if __name__ == '__main__':
    test_code = """
# Create a customers table
customers_df = pd.DataFrame({
    'customer_id': [1, 2, 3, 4],
    'name': ['Alice', 'Bob', 'Charlie', 'Dave'],
    'city': ['New York', 'San Francisco', 'Seattle', 'Chicago'],
    'zip_code': ['10001', '94103', '98101', '60601']
})

# Create an orders table with a foreign key
orders_df = pd.DataFrame({
    'order_id': [101, 102, 103, 104, 105],
    'customer_id': [1, 2, 3, 5, 2],  # Note: customer_id 5 doesn't exist
    'amount': [99.99, 149.99, 29.99, 59.99, 199.99],
    'order_date': ['2023-01-15', '2023-01-16', '2023-01-17', '2023-01-18', '2023-01-19']
})

# Create a table with a functional dependency issue (city determines zip_code)
address_df = pd.DataFrame({
    'address_id': [1, 2, 3, 4],
    'city': ['New York', 'San Francisco', 'New York', 'Seattle'],
    'zip_code': ['10001', '94103', '10001', '98101']  # Note: New York always has 10001
})
"""
    result = execute_pandas_code(test_code, 'test_output')
    print(result)
