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

"""Schema generator for Bedrock Agent Action Groups."""

import importlib.util
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple


def generate_fallback_script(lambda_code_path: str, output_path: str) -> str:
    """Generate a standalone script for schema generation."""
    return f'''# pyright: ignore
#!/usr/bin/env python3
"""
Schema Generator for Bedrock Agent Action Groups

This script generates an OpenAPI schema from a Lambda file containing a BedrockAgentResolver app.

IMPORTANT: This script requires the following dependencies:
1. aws-lambda-powertools
2. pydantic

Install them with:

    pip install aws-lambda-powertools pydantic

Then run this script again.

This script focuses on extracting the API definition (routes, parameters, responses)
from the BedrockAgentResolver app, NOT on executing the business logic in the Lambda function.
If you encounter errors related to missing dependencies or runtime errors in the business logic,
you can safely modify this script to bypass those errors while preserving the API definition.
"""

import os
import sys
import json
import importlib.util

# Check for required dependencies
missing_deps = []
for dep in ['aws_lambda_powertools', 'pydantic']:
    try:
        importlib.import_module(dep)
    except ImportError:
        missing_deps.append(dep)

if missing_deps:
    print("ERROR: Missing required dependencies: " + ", ".join(missing_deps))
    print("Please install them with:")
    print("pip install " + " ".join(missing_deps).replace('_', '-'))
    print("Then run this script again.")
    sys.exit(1)

# Configuration
LAMBDA_FILE_PATH = "{lambda_code_path}"
OUTPUT_PATH = "{output_path}"
APP_VAR_NAME = "app"  # Update this if your BedrockAgentResolver instance has a different name

def main():
    print(f"Generating schema from {{LAMBDA_FILE_PATH}}")
    print(f"Output path: {{OUTPUT_PATH}}")

    # Get the directory and module name
    lambda_dir = os.path.dirname(os.path.abspath(LAMBDA_FILE_PATH))
    module_name = os.path.basename(LAMBDA_FILE_PATH).replace('.py', '')

    # MODIFICATION GUIDE:
    # If you encounter import errors or runtime errors, you can:
    # 1. Create a simplified version of the Lambda file with problematic imports/code commented out
    # 2. Add try/except blocks around problematic code
    # 3. Create mock implementations for missing functions
    # The key is to preserve the BedrockAgentResolver app definition and routes

    # Example of creating a simplified version:
    simplified_path = os.path.join(lambda_dir, f"{{module_name}}_simplified.py")
    try:
        with open(LAMBDA_FILE_PATH, 'r', encoding='utf-8') as f:
            content = f.read()

        # Comment out problematic imports (add more as needed)
        problematic_packages = [
            'matplotlib', 'numpy', 'pandas', 'scipy', 'tensorflow', 'torch', 'sympy',
            'nltk', 'spacy', 'gensim', 'sklearn', 'networkx', 'plotly', 'dash',
            'opencv', 'cv2', 'PIL', 'pillow'
        ]

        lines = content.split('\\n')
        for i, line in enumerate(lines):
            stripped = line.strip()
            if (stripped.startswith('import ') or stripped.startswith('from ')) and \
               any(pkg in stripped for pkg in problematic_packages):
                lines[i] = f"# {{line}}  # Commented out for schema generation"

        simplified_content = '\\n'.join(lines)

        with open(simplified_path, 'w', encoding='utf-8') as f:
            f.write(simplified_content)

        print("Created simplified version with problematic imports commented out")

        # Try with the simplified version
        try:
            # Add directory to Python path
            sys.path.append(os.path.dirname(simplified_path))

            # Import the simplified module
            print(f"Importing {{simplified_path}}...")
            spec = importlib.util.spec_from_file_location(
                f"{{module_name}}_simplified", simplified_path
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Get the app object
            if not hasattr(module, APP_VAR_NAME):
                print(f"No '{{APP_VAR_NAME}}' variable found in the module.")
                print("If your BedrockAgentResolver instance has a different name, update APP_VAR_NAME.")
                return False

            app = getattr(module, APP_VAR_NAME)

            # Generate the OpenAPI schema
            print("Generating OpenAPI schema...")
            # Note: This might show a UserWarning about Pydantic v2 and OpenAPI versions
            openapi_schema = json.loads(app.get_openapi_json_schema(openapi_version="3.0.0"))

            # Fix Pydantic v2 issue (forcing OpenAPI 3.0.0)
            if openapi_schema.get("openapi") != "3.0.0":
                openapi_schema["openapi"] = "3.0.0"
                print("Note: Adjusted OpenAPI version for compatibility with Bedrock Agents")

            # Fix operationIds
            for path in openapi_schema['paths']:
                for method in openapi_schema['paths'][path]:
                    operation = openapi_schema['paths'][path][method]
                    if 'operationId' in operation:
                        # Get current operationId
                        current_id = operation['operationId']
                        # Remove duplication by taking the first part before '_post'
                        if '_post' in current_id:
                            # Split by underscore and remove duplicates
                            parts = current_id.split('_')
                            # Keep only unique parts and add '_post' at the end
                            unique_parts = []
                            seen = set()
                            for part in parts[:-1]:  # Exclude the last 'post' part
                                if part not in seen:
                                    unique_parts.append(part)
                                    seen.add(part)
                            new_id = '_'.join(unique_parts + ['post'])
                            operation['operationId'] = new_id
                            print(f"Fixed operationId: {{current_id}} -> {{new_id}}")

            # Create output directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(OUTPUT_PATH)), exist_ok=True)

            # Save the schema to the output path
            with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
                json.dump(openapi_schema, f, indent=2)

            print(f"Schema successfully generated and saved to {{OUTPUT_PATH}}")
            print("Next steps: Use this schema in your CDK code with bedrock.ApiSchema.fromLocalAsset()")
            return True

        except Exception as simplified_error:
            print(f"Error with simplified version: {{str(simplified_error)}}")
            if "No module named" in str(simplified_error):
                missing_dep = str(simplified_error).split("'")[-2] if "'" in str(simplified_error) else str(simplified_error).split("No module named ")[-1].strip()
                print("To resolve this error, install the missing dependency:")
                print("    pip install " + missing_dep.replace('_', '-'))
                print("Then run this script again.")
            else:
                print("You may need to manually modify the script to handle this error.")
                print("Focus on preserving the BedrockAgentResolver app definition and routes.")
            return False

    except Exception as e:
        print(f"Error creating simplified version: {{str(e)}}")

        # Try direct import as fallback
        try:
            # Add directory to Python path
            sys.path.append(lambda_dir)

            # Import module directly
            print(f"Trying direct import of {{LAMBDA_FILE_PATH}}...")
            module = __import__(module_name)

            # Get the app object
            if not hasattr(module, APP_VAR_NAME):
                print(f"No '{{APP_VAR_NAME}}' variable found in the module.")
                print("If your BedrockAgentResolver instance has a different name, update APP_VAR_NAME.")
                return False

            app = getattr(module, APP_VAR_NAME)

            # Generate the OpenAPI schema
            print("Generating OpenAPI schema...")
            openapi_schema = json.loads(app.get_openapi_json_schema(openapi_version="3.0.0"))

            # Fix schema issues
            if openapi_schema.get("openapi") != "3.0.0":
                openapi_schema["openapi"] = "3.0.0"
                print("Fixed OpenAPI version to 3.0.0 (Pydantic v2 issue)")

            # Create output directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(OUTPUT_PATH)), exist_ok=True)

            # Save the schema to the output path
            with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
                json.dump(openapi_schema, f, indent=2)

            print(f"Schema successfully generated and saved to {{OUTPUT_PATH}}")
            return True

        except Exception as direct_error:
            print(f"Error with direct import: {{str(direct_error)}}")
            print("You may need to manually modify this script to handle the errors.")
            print("Remember that the goal is to extract the API definition, not to run the business logic.")
            return False
    finally:
        # Clean up the simplified file
        if os.path.exists(simplified_path):
            os.remove(simplified_path)
            print("Cleaned up simplified file")

if __name__ == '__main__':
    main()
'''


def fix_operation_ids(openapi_schema: Dict[str, Any], result: Dict[str, Any]) -> None:
    """Fix operationIds in the OpenAPI schema.

    Args:
        openapi_schema: The OpenAPI schema to fix
        result: The result dictionary to update with warnings
    """
    fixed = False
    for path in openapi_schema['paths']:
        for method in openapi_schema['paths'][path]:
            operation = openapi_schema['paths'][path][method]
            if 'operationId' in operation:
                # Get current operationId
                current_id = operation['operationId']
                # Remove duplication by taking the first part before '_post'
                if '_post' in current_id:
                    # Split by underscore and remove duplicates
                    parts = current_id.split('_')
                    # Keep only unique parts and add '_post' at the end
                    unique_parts = []
                    seen = set()
                    for part in parts[:-1]:  # Exclude the last 'post' part
                        if part not in seen:
                            unique_parts.append(part)
                            seen.add(part)
                    new_id = '_'.join(unique_parts + ['post'])
                    operation['operationId'] = new_id
                    fixed = True

    if fixed:
        result['warnings'].append('Fixed operationIds for Claude 3.5 compatibility')


def comment_out_problematic_code(
    content: str, problematic_packages: List[str], import_name: Optional[str] = None
) -> Tuple[str, List[str]]:
    """Comment out problematic imports and code blocks that use them.

    Args:
        content: The source code content
        problematic_packages: List of problematic package names
        import_name: Specific import name that failed (optional)

    Returns:
        Tuple of (modified content, list of modifications made)
    """
    modifications = []

    # Add the specific import that failed if not already in the list
    if (
        import_name
        and import_name not in problematic_packages
        and import_name != 'No module named'
    ):
        problematic_packages.append(import_name)

    # Comment out problematic imports and their usage
    lines = content.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Check for import statements (both direct and from-imports)
        if line.startswith('import ') or line.startswith('from '):
            for pkg in problematic_packages:
                # Match both "import pkg" and "from pkg import ..."
                if (
                    line.startswith(f'import {pkg}')
                    or line.startswith(f'from {pkg} ')
                    or f' {pkg}' in line
                    or f'.{pkg}' in line
                ):
                    lines[i] = f'# {lines[i]}  # Commented out for schema generation'
                    modifications.append(f'Commented out import: {lines[i]}')
                    break

        # Check for try/except blocks that might use problematic packages
        if line.startswith('try:'):
            # Look ahead to see if the next lines use problematic packages
            j = i + 1
            block_level = 1
            contains_problematic_code = False

            # Check the content of the try block
            while j < len(lines) and block_level > 0:
                next_line = lines[j].strip()
                if next_line.startswith('try:'):
                    block_level += 1
                elif next_line.startswith('except'):
                    block_level -= 1

                # Check if this line uses any problematic package
                for pkg in problematic_packages:
                    if pkg in lines[j]:
                        contains_problematic_code = True
                        break

                j += 1

            # If the try block contains problematic code, comment out the entire block
            if contains_problematic_code:
                lines[i] = f'# {lines[i]}  # Commented out for schema generation'
                modifications.append(f'Commented out try block starting at line {i + 1}')

                # Comment out the entire try/except block
                j = i + 1
                block_level = 1
                while j < len(lines) and block_level > 0:
                    if lines[j].strip().startswith('try:'):
                        block_level += 1
                    elif lines[j].strip().startswith('except'):
                        block_level -= 1

                    lines[j] = f'# {lines[j]}  # Commented out for schema generation'
                    j += 1

                # Skip ahead to after the block
                i = j - 1

        i += 1

    return '\n'.join(lines), modifications


def generate_bedrock_schema_from_file(
    lambda_code_path: str,
    output_path: str,
) -> Dict[str, Any]:
    """Generate OpenAPI schema from a Lambda file with BedrockAgentResolver.

    This function implements a progressive fallback approach:
    1. First attempt: Direct import of the Lambda file
    2. Second attempt: Create a simplified version with problematic imports commented out
    3. Last resort: Generate a fallback script for manual execution

    Args:
        lambda_code_path: Path to Python file containing BedrockAgentResolver app
        output_path: Where to save the generated schema

    Returns:
        Dictionary with results of schema generation including:
        - status: "success" or "error"
        - schema_path: Path to the generated schema (if successful)
        - warnings: List of warnings or issues detected
        - process: Details about the approaches attempted
        - error: Error message (if failed)
        - diagnosis: Detailed diagnosis of the issue (if failed)
        - solution: Suggested solution (if failed)
        - fallback_script: Fallback script content (if failed)
    """
    result = {
        'status': 'success',
        'schema_path': output_path,
        'warnings': [],
        'process': {
            'direct_import': {'attempted': False, 'succeeded': False},
            'simplified_version': {'attempted': False, 'succeeded': False},
            'fallback_script': {'generated': False},
        },
    }

    try:
        # Check if the file exists
        if not os.path.exists(lambda_code_path):
            raise FileNotFoundError(f'Lambda code file not found: {lambda_code_path}')

        # Get the directory and module name
        lambda_dir = os.path.dirname(os.path.abspath(lambda_code_path))
        module_name = os.path.basename(lambda_code_path).replace('.py', '')

        # FIRST ATTEMPT: Direct import
        try:
            result['process']['direct_import']['attempted'] = True

            # Add the directory to the Python path
            sys.path.append(lambda_dir)

            # Import the module
            module = __import__(module_name)

            # Get the app object
            if not hasattr(module, 'app'):
                raise AttributeError("No 'app' variable found in the module")

            app = module.app

            # Generate the OpenAPI schema
            openapi_schema = json.loads(app.get_openapi_json_schema(openapi_version='3.0.0'))

            # Fix Pydantic v2 issue (forcing OpenAPI 3.0.0)
            if openapi_schema.get('openapi') != '3.0.0':
                openapi_schema['openapi'] = '3.0.0'
                result['warnings'].append('Fixed OpenAPI version to 3.0.0 (Pydantic v2 issue)')

            # Fix operationIds
            fix_operation_ids(openapi_schema, result)

            # Create output directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

            # Save the schema to the output path
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(openapi_schema, f, indent=2)

            result['schema'] = openapi_schema
            result['process']['direct_import']['succeeded'] = True

        except ImportError as e:
            # SECOND ATTEMPT: Simplified version with problematic imports commented out
            result['process']['direct_import']['error'] = str(e)
            result['warnings'].append(f'Direct import failed: {str(e)}')

            # Extract the import name that failed
            import_name = str(e).split("'")[-2] if "'" in str(e) else str(e)

            # Try simplified approach
            result['process']['simplified_version']['attempted'] = True
            simplified_path = os.path.join(lambda_dir, f'{module_name}_simplified.py')

            try:
                with open(lambda_code_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Define problematic packages
                problematic_packages = [
                    'matplotlib',
                    'numpy',
                    'pandas',
                    'scipy',
                    'tensorflow',
                    'torch',
                    'sympy',
                    'nltk',
                    'spacy',
                    'gensim',
                    'sklearn',
                    'networkx',
                    'plotly',
                    'dash',
                    'opencv',
                    'cv2',
                    'PIL',
                    'pillow',
                ]

                # Comment out problematic imports and code blocks
                simplified_content, modifications = comment_out_problematic_code(
                    content, problematic_packages, import_name
                )

                # Add modifications to the result
                result['process']['simplified_version']['modifications'] = modifications

                # Write simplified file
                with open(simplified_path, 'w', encoding='utf-8') as f:
                    f.write(simplified_content)

                try:
                    # Import simplified module
                    spec = importlib.util.spec_from_file_location(
                        f'{module_name}_simplified', simplified_path
                    )
                    if spec is None:
                        raise ImportError(
                            f'Could not find spec for module: {module_name}_simplified'
                        )

                    simplified_module = importlib.util.module_from_spec(spec)
                    if spec.loader is None:
                        raise ImportError(f'Module spec has no loader: {module_name}_simplified')

                    spec.loader.exec_module(simplified_module)

                    # Get app and generate schema
                    if not hasattr(simplified_module, 'app'):
                        raise AttributeError("No 'app' variable found in the simplified module")

                    app = getattr(simplified_module, 'app')
                    openapi_schema = json.loads(
                        app.get_openapi_json_schema(openapi_version='3.0.0')
                    )

                    # Fix Pydantic v2 issue (forcing OpenAPI 3.0.0)
                    if openapi_schema.get('openapi') != '3.0.0':
                        openapi_schema['openapi'] = '3.0.0'
                        result['warnings'].append(
                            'Fixed OpenAPI version to 3.0.0 (Pydantic v2 issue)'
                        )

                    # Fix operationIds
                    fix_operation_ids(openapi_schema, result)

                    # Create output directory if it doesn't exist
                    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

                    # Save the schema to the output path
                    with open(output_path, 'w', encoding='utf-8') as f:
                        json.dump(openapi_schema, f, indent=2)

                    result['schema'] = openapi_schema
                    result['warnings'].append(
                        'Used simplified version with problematic imports and code commented out'
                    )
                    result['process']['simplified_version']['succeeded'] = True

                except Exception as simplified_error:
                    # Both approaches failed
                    result['process']['simplified_version']['error'] = str(simplified_error)
                    result['status'] = 'error'
                    result['error'] = 'Both direct and simplified approaches failed'
                    result['original_error'] = str(e)  # Preserve the original error
                    result['simplified_error'] = str(
                        simplified_error
                    )  # Add the simplified approach error
                    result['diagnosis'] = (
                        f'The Lambda function has dependencies that cannot be resolved: {import_name}'
                    )
                    result['solution'] = (
                        'Use the fallback script and manually comment out problematic imports and code'
                    )

                    # LAST RESORT: Generate fallback script
                    script = generate_fallback_script(lambda_code_path, output_path)
                    result['fallback_script'] = script
                    result['process']['fallback_script']['generated'] = True

                    # Add instructions
                    result['instructions'] = (
                        f'Error encountered: {str(simplified_error)}\n\n'
                        'To generate the schema manually, save the fallback script to a file '
                        'and run it in an environment with all required dependencies installed.'
                    )

                    # Add client-agnostic instructions
                    result['client_instructions'] = {
                        'title': 'Schema Generation Failed',
                        'summary': f'The Lambda function has dependencies that cannot be resolved: {import_name}',
                        'steps': [
                            'Save the fallback script below to a file (e.g., generate_schema.py)',
                            'Run the script in your environment where all dependencies are available',
                            'The script will generate the schema at the specified output path',
                        ],
                        'script_filename_suggestion': 'generate_schema.py',
                        'command_suggestion': 'python generate_schema.py',
                    }

                finally:
                    # Clean up simplified file
                    if os.path.exists(simplified_path):
                        os.remove(simplified_path)

            except Exception as e:
                # Error creating simplified version
                result['process']['simplified_version']['error'] = str(e)
                result['status'] = 'error'
                result['error'] = f'Failed to create simplified version: {str(e)}'
                result['diagnosis'] = (
                    'Could not process the Lambda file to create a simplified version'
                )
                result['solution'] = (
                    'Use the fallback script and manually comment out problematic imports and code'
                )

                # Generate fallback script
                script = generate_fallback_script(lambda_code_path, output_path)
                result['fallback_script'] = script
                result['process']['fallback_script']['generated'] = True

                # Add instructions
                result['instructions'] = (
                    f'Error encountered: {str(e)}\n\n'
                    'To generate the schema manually, save the fallback script to a file '
                    'and run it in an environment with all required dependencies installed.'
                )

        except AttributeError as e:
            # App not found
            result['process']['direct_import']['error'] = str(e)
            result['status'] = 'error'
            result['error'] = str(e)
            result['diagnosis'] = 'The BedrockAgentResolver instance was not found in the module'
            result['solution'] = (
                'Edit the APP_VAR_NAME variable in the fallback script to match your BedrockAgentResolver instance name'
            )

            # Generate fallback script
            script = generate_fallback_script(lambda_code_path, output_path)
            result['fallback_script'] = script
            result['process']['fallback_script']['generated'] = True

            # Add instructions
            result['instructions'] = (
                f'Error encountered: {str(e)}\n\n'
                'To generate the schema manually, save the fallback script to a file '
                'and run it in an environment with all required dependencies installed. '
                'You may need to update the APP_VAR_NAME variable if your BedrockAgentResolver '
                'instance has a different name than "app".'
            )

        except Exception as e:
            # Other errors
            result['process']['direct_import']['error'] = str(e)
            result['status'] = 'error'
            result['error'] = str(e)
            result['diagnosis'] = f'An unexpected error occurred: {type(e).__name__}'
            result['solution'] = (
                'Use the fallback script and check for syntax errors or other issues in your Lambda function'
            )

            # Generate fallback script
            script = generate_fallback_script(lambda_code_path, output_path)
            result['fallback_script'] = script
            result['process']['fallback_script']['generated'] = True

            # Add instructions
            result['instructions'] = (
                f'Error encountered: {str(e)}\n\n'
                'To generate the schema manually, save the fallback script to a file '
                'and run it in an environment with all required dependencies installed.'
            )

        finally:
            # Clean up sys.path
            if lambda_dir in sys.path:
                sys.path.remove(lambda_dir)

    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
        result['diagnosis'] = f'Error accessing or processing the Lambda file: {type(e).__name__}'
        result['solution'] = 'Check file permissions and path correctness'

        # Generate fallback script
        script = generate_fallback_script(lambda_code_path, output_path)
        result['fallback_script'] = script
        result['process']['fallback_script']['generated'] = True

        # Add instructions
        result['instructions'] = (
            f'Error encountered: {str(e)}\n\n'
            'To generate the schema manually, save the fallback script to a file '
            'and run it in an environment with all required dependencies installed.'
        )

    return result
