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

"""CDK project generator for DynamoDB data models."""

import json
import re
import shutil
import subprocess  # nosec B404 - used to invoke `cdk init` locally
from awslabs.dynamodb_mcp_server.cdk_generator.models import DataModel
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from loguru import logger
from pathlib import Path


# CDK Generation Configuration
CDK_INIT_TIMEOUT_SECONDS = 120
CDK_DIRECTORY_NAME = 'cdk'
STACK_TEMPLATE_NAME = 'stack.ts.j2'


class CdkGeneratorError(Exception):
    """Exception raised for CDK generation errors."""

    pass


class CdkGenerator:
    """Generates CDK projects from DynamoDB data model JSON files."""

    def __init__(self):
        """Initialize the generator.

        The templates directory is determined internally based on the module location.
        """
        self.templates_dir = Path(__file__).parent / 'templates'
        self.jinja_env = Environment(  # nosec B701 - Content is NOT HTML and NOT served
            loader=FileSystemLoader(str(self.templates_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=False,
        )
        self.jinja_env.filters['to_camel_case'] = self._to_camel_case
        self.jinja_env.filters['to_pascal_case'] = self._to_pascal_case

    def generate(self, json_file_path: Path) -> None:
        """Generate a CDK project from the given JSON file.

        Args:
            json_file_path: Path to dynamodb_data_model.json

        Returns:
            None - returns nothing on success

        Raises:
            CdkGeneratorError: If generation fails with descriptive error message
            ValueError: If data model validation fails
        """
        logger.info(f'Starting CDK generation. json_file_path: {json_file_path}')

        if not json_file_path.exists():
            raise CdkGeneratorError(f"JSON file not found. json_file_path: '{json_file_path}'")

        cdk_dir = json_file_path.parent / CDK_DIRECTORY_NAME
        if cdk_dir.exists():
            raise CdkGeneratorError(
                f"CDK directory already exists. To generate again, remove or rename it and try again. cdk_dir: '{cdk_dir}'"
            )

        logger.info('Creating cdk directory')
        cdk_dir.mkdir()

        logger.info('Running cdk init')
        self._run_cdk_init(cdk_dir)

        logger.info('Parsing data model')
        data_model = self._parse_data_model(json_file_path)

        logger.info('Checking for table name collisions')
        self._check_table_name_collisions(data_model)

        logger.info('Rendering template')
        self._render_template(data_model, cdk_dir)

        logger.info('Copying README template')
        self._copy_readme_template(cdk_dir)

        logger.info(f'CDK project generated successfully. cdk_dir: {cdk_dir}')

    def _run_cdk_init(self, target_dir: Path) -> None:
        """Execute cdk init in the target directory.

        Args:
            target_dir: Directory where cdk init should be executed

        Raises:
            CdkGeneratorError: If cdk init fails
        """
        try:
            subprocess.run(  # nosec B603, B607 - user local env, hardcoded cmd, no shell, timeout
                ['npx', 'cdk', 'init', 'app', '--language', 'typescript'],
                cwd=target_dir,
                capture_output=True,
                text=True,
                timeout=CDK_INIT_TIMEOUT_SECONDS,
                check=True,
            )

            logger.info('cdk init completed successfully')

        except subprocess.CalledProcessError as e:
            raise CdkGeneratorError(
                f'cdk init failed. exit_code: {e.returncode}, stderr: {e.stderr}'
            ) from e
        except subprocess.TimeoutExpired as e:
            raise CdkGeneratorError(
                f'cdk init timed out. timeout_seconds: {CDK_INIT_TIMEOUT_SECONDS}'
            ) from e
        except FileNotFoundError as e:
            raise CdkGeneratorError(
                'npx command not found. Install Node.js and npm, then try again.'
            ) from e
        except Exception as e:
            raise CdkGeneratorError(f'cdk init failed. error: {str(e)}') from e

    def _parse_data_model(self, json_file_path: Path) -> DataModel:
        """Parse the JSON file into a DataModel object with validation.

        Args:
            json_file_path: Path to dynamodb_data_model.json

        Returns:
            DataModel instance

        Raises:
            ValueError: If JSON is invalid or validation fails
        """
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(
                f'Invalid JSON. json_file_path: {json_file_path}, error: {str(e)}'
            ) from e
        except Exception as e:
            raise ValueError(
                f'Failed to read JSON file. json_file_path: {json_file_path}, error: {str(e)}'
            ) from e

        return DataModel.from_json(json_data)

    def _to_camel_case(self, table_name: str) -> str:
        """Convert table name to camelCase for variable names.

        Args:
            table_name: Original table name (e.g., 'UserProfiles', 'Product-Catalog', 'Analytics_Events')

        Returns:
            camelCase variable name (e.g., 'userProfiles', 'productCatalog', 'analyticsEvents')
        """
        name = table_name.replace('-', ' ').replace('_', ' ')

        # Split camelCase/PascalCase words (e.g., 'UserProfiles' -> 'User Profiles')
        # Insert space before uppercase letters that follow lowercase letters
        name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)

        words = name.split()

        # First word lowercase, rest title case
        parts = [words[0].lower()]
        parts.extend(word.capitalize() for word in words[1:])
        return ''.join(parts)

    def _to_pascal_case(self, table_name: str) -> str:
        """Convert table name to PascalCase for method names.

        Args:
            table_name: Original table name (e.g., 'UserProfiles', 'Product-Catalog', 'Analytics_Events')

        Returns:
            PascalCase name (e.g., 'UserProfiles', 'ProductCatalog', 'AnalyticsEvents')
        """
        camel = self._to_camel_case(table_name)
        return camel[0].upper() + camel[1:] if camel else camel

    def _check_table_name_collisions(self, data_model: DataModel) -> None:
        """Check for table name collisions after sanitization.

        Args:
            data_model: Parsed data model

        Raises:
            CdkGeneratorError: If two tables would produce the same variable name
        """
        seen: dict[str, str] = {}  # camelCase_name -> original_name
        for table in data_model.tables:
            camel_case = self._to_camel_case(table.table_name)
            if camel_case in seen:
                raise CdkGeneratorError(
                    f'Table name collision detected. Rename one of the tables to fix. '
                    f"table1: '{seen[camel_case]}', table2: '{table.table_name}', camelCase_name: '{camel_case}'"
                )
            seen[camel_case] = table.table_name

    def _render_template(self, data_model: DataModel, target_dir: Path) -> None:
        """Render the stack template and write to target directory.

        Stack filename and class name are derived from the CDK directory name.
        For directory 'cdk', generates 'cdk-stack.ts' with class 'CdkStack'.

        Args:
            data_model: Parsed data model
            target_dir: Directory where rendered file should be written (the CDK project root)

        Raises:
            CdkGeneratorError: If template rendering fails
        """
        # Derive stack info from CDK directory name
        dir_name = target_dir.name
        stack_class_name = ''.join(word.capitalize() for word in dir_name.split('-')) + 'Stack'
        stack_filename = f'{dir_name}-stack.ts'

        try:
            template = self.jinja_env.get_template(STACK_TEMPLATE_NAME)
        except TemplateNotFound as e:
            raise CdkGeneratorError(
                f"Required template file is missing. template_name: '{STACK_TEMPLATE_NAME}'"
            ) from e

        try:
            rendered_content = template.render(
                data_model=data_model, stack_class_name=stack_class_name
            )
            output_path = target_dir / 'lib' / stack_filename
            output_path.parent.mkdir(parents=True, exist_ok=True)

            output_path.write_text(rendered_content, encoding='utf-8')
            logger.info(
                f'Rendered template. template_name: {STACK_TEMPLATE_NAME}, output_path: {output_path}'
            )
        except Exception as e:
            raise CdkGeneratorError(f'Failed to render template. error: {str(e)}') from e

    def _copy_readme_template(self, target_dir: Path) -> None:
        """Copy the README template to the target directory.

        Args:
            target_dir: Directory where README.md should be copied

        Raises:
            CdkGeneratorError: If copy fails

        Note:
            The README template is part of the package and should always exist.
            If it's missing, that indicates a packaging issue.
        """
        readme_template = self.templates_dir / 'README.md'
        readme_dest = target_dir / 'README.md'

        try:
            shutil.copy2(readme_template, readme_dest)
        except Exception as e:
            raise CdkGeneratorError(
                f"README template copy failed. readme_template: '{readme_template}', readme_dest: '{readme_dest}', error: {str(e)}"
            ) from e
