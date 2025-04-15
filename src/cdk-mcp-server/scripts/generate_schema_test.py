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
LAMBDA_FILE_PATH = "test.py"
OUTPUT_PATH = "test.json"
APP_VAR_NAME = "app"  # Update this if your BedrockAgentResolver instance has a different name

def main():
    print(f"Generating schema from {LAMBDA_FILE_PATH}")
    print(f"Output path: {OUTPUT_PATH}")

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
    simplified_path = os.path.join(lambda_dir, f"{module_name}_simplified.py")
    try:
        with open(LAMBDA_FILE_PATH, 'r', encoding='utf-8') as f:
            content = f.read()

        # Comment out problematic imports (add more as needed)
        problematic_packages = [
            'matplotlib', 'numpy', 'pandas', 'scipy', 'tensorflow', 'torch', 'sympy',
            'nltk', 'spacy', 'gensim', 'sklearn', 'networkx', 'plotly', 'dash',
            'opencv', 'cv2', 'PIL', 'pillow'
        ]

        lines = content.split('\n')
        for i, line in enumerate(lines):
            stripped = line.strip()
            if (stripped.startswith('import ') or stripped.startswith('from ')) and                any(pkg in stripped for pkg in problematic_packages):
                lines[i] = f"# {line}  # Commented out for schema generation"

        simplified_content = '\n'.join(lines)

        with open(simplified_path, 'w', encoding='utf-8') as f:
            f.write(simplified_content)

        print("Created simplified version with problematic imports commented out")

        # Try with the simplified version
        try:
            # Add directory to Python path
            sys.path.append(os.path.dirname(simplified_path))

            # Import the simplified module
            print(f"Importing {simplified_path}...")
            spec = importlib.util.spec_from_file_location(
                f"{module_name}_simplified", simplified_path
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Get the app object
            if not hasattr(module, APP_VAR_NAME):
                print(f"No '{APP_VAR_NAME}' variable found in the module.")
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
                            print(f"Fixed operationId: {current_id} -> {new_id}")

            # Create output directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(OUTPUT_PATH)), exist_ok=True)

            # Save the schema to the output path
            with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
                json.dump(openapi_schema, f, indent=2)

            print(f"Schema successfully generated and saved to {OUTPUT_PATH}")
            print("Next steps: Use this schema in your CDK code with bedrock.ApiSchema.fromLocalAsset()")
            return True

        except Exception as simplified_error:
            print(f"Error with simplified version: {str(simplified_error)}")
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
        print(f"Error creating simplified version: {str(e)}")

        # Try direct import as fallback
        try:
            # Add directory to Python path
            sys.path.append(lambda_dir)

            # Import module directly
            print(f"Trying direct import of {LAMBDA_FILE_PATH}...")
            module = __import__(module_name)

            # Get the app object
            if not hasattr(module, APP_VAR_NAME):
                print(f"No '{APP_VAR_NAME}' variable found in the module.")
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

            print(f"Schema successfully generated and saved to {OUTPUT_PATH}")
            return True

        except Exception as direct_error:
            print(f"Error with direct import: {str(direct_error)}")
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
