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

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from loguru import logger


class DirectoryProcessor:
    """Utility for processing directories of workflow files"""

    @staticmethod
    def detect_framework(file_path: str) -> Optional[str]:
        """Auto-detect framework from file content and extension.

        Detection Strategy:
        - File extension provides initial hint
        - Content analysis provides definitive identification
        - Hierarchical detection: most specific patterns first
        - Extensible: new frameworks can be added by extending detection rules
        """
        path = Path(file_path)

        # Check by extension first
        if path.suffix == '.py':
            # Read content to detect Airflow
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                if 'from airflow' in content or 'import airflow' in content or 'DAG(' in content:
                    return 'airflow'
                # Future: Add Prefect detection here
                # if 'from prefect' in content or '@flow' in content:
                #     return 'prefect'
            except (IOError, OSError) as e:
                logger.debug(f'Could not read file {file_path}: {e}')
            except Exception as e:
                logger.debug(f'Error detecting framework in {file_path}: {e}')

        elif path.suffix == '.json':
            # Read JSON to detect Step Functions, Azure Data Factory, or FLEX
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)

                # Step Functions detection (most specific first)
                if 'States' in data and 'StartAt' in data:
                    return 'step_functions'

                # FLEX detection (check for FLEX-specific structure)
                if (
                    'name' in data
                    and 'tasks' in data
                    and isinstance(data.get('tasks'), list)
                    and data.get('parsing_info', {}).get('source_framework')
                ):
                    return 'flex'

                # Generic FLEX detection (fallback)
                if 'name' in data and 'tasks' in data and isinstance(data.get('tasks'), list):
                    tasks = data.get('tasks', [])
                    if tasks and all(isinstance(task, dict) and 'id' in task for task in tasks):
                        return 'flex'

                # Azure Data Factory detection
                if 'properties' in data and 'activities' in data.get('properties', {}):
                    return 'azure_data_factory'

                # Future: Add other JSON-based frameworks here
                # if 'workflow' in data and 'jobs' in data:
                #     return 'github_actions'

            except (IOError, OSError, json.JSONDecodeError) as e:
                logger.debug(f'Could not parse JSON file {file_path}: {e}')
            except Exception as e:
                logger.debug(f'Error detecting framework in JSON {file_path}: {e}')

        elif path.suffix == '.yaml' or path.suffix == '.yml':
            # Future: Add YAML-based framework detection
            # try:
            #     with open(file_path, 'r') as f:
            #         content = f.read()
            #     if 'apiVersion: argoproj.io' in content:
            #         return 'argo_workflows'
            # except:
            #     pass
            pass

        return None

    @staticmethod
    def scan_directory(directory_path: str) -> List[Tuple[str, str]]:
        """Scan directory and return list of (file_path, detected_framework) tuples"""
        results = []

        if not os.path.exists(directory_path):
            logger.error(f'Directory does not exist: {directory_path}')
            return results

        for root, _dirs, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                framework = DirectoryProcessor.detect_framework(file_path)
                if framework:
                    results.append((file_path, framework))
                    logger.info(f'Detected {framework} in {file_path}')

        return results

    @staticmethod
    def create_output_directories(
        input_dir: str, operation_type: str, custom_output_dir: Optional[str] = None
    ) -> Tuple[str, str]:
        """Create output directories in centralized outputs folder or custom location"""
        input_path = Path(input_dir).resolve()

        if custom_output_dir:
            # Use custom output directory
            outputs_dir = Path(custom_output_dir)
            outputs_dir.mkdir(parents=True, exist_ok=True)
            project_root = outputs_dir  # Set for later use
        else:
            # Find project root (where outputs directory should be)
            project_root = input_path
            while project_root.parent != project_root:
                if (project_root / 'pyproject.toml').exists() or (
                    project_root / 'setup.py'
                ).exists():
                    break
                project_root = project_root.parent
            else:
                # If no project root found, use input path parent
                project_root = input_path.parent

            # Create outputs directory structure
            outputs_dir = project_root / 'outputs'
            outputs_dir.mkdir(exist_ok=True)

        # Use relative path from project root for cleaner names
        try:
            relative_input = input_path.relative_to(project_root)
            dir_name = str(relative_input).replace('/', '_').replace('\\', '_')
        except ValueError:
            dir_name = input_path.name

        if operation_type == 'parse_to_flex':
            flex_dir = outputs_dir / f'target_flex_from_source_{dir_name}'
            flex_dir.mkdir(exist_ok=True)
            return str(flex_dir), ''

        elif operation_type == 'generate_from_flex':
            jobs_dir = outputs_dir / f'target_jobs_from_source_flex_{dir_name}'
            jobs_dir.mkdir(exist_ok=True)
            return '', str(jobs_dir)

        else:  # convert_etl_workflow
            flex_dir = outputs_dir / f'target_flex_from_source_{dir_name}'
            jobs_dir = outputs_dir / f'target_jobs_from_source_{dir_name}'
            flex_dir.mkdir(exist_ok=True)
            jobs_dir.mkdir(exist_ok=True)
            return str(flex_dir), str(jobs_dir)

    @staticmethod
    def save_flex_document(flex_workflow: Dict, original_file_path: str, output_dir: str):
        """Save FLEX document to output directory with incomplete marking"""
        original_path = Path(original_file_path)
        original_name = original_path.stem

        # Always save FLEX documents with .flex.json extension
        # Remove .flex from name if already present to avoid double .flex
        if original_name.endswith('.flex'):
            base_name = original_name[:-5]  # Remove '.flex' suffix
        else:
            base_name = original_name

        # Check if workflow is incomplete or has AI-generated content
        is_incomplete = False
        has_ai_content = False

        if 'parsing_info' in flex_workflow:
            missing_fields = flex_workflow['parsing_info'].get('missing_fields', [])
            # Check for required fields that indicate incompleteness
            required_indicators = ['task_commands', 'parameters']
            is_incomplete = any(field in missing_fields for field in required_indicators)

            # Check if AI was used for enhancements
            llm_enhancements = flex_workflow['parsing_info'].get('llm_enhancements', [])
            has_ai_content = len(llm_enhancements) > 0

        # Check for AI-generated tasks
        ai_generated_tasks = []
        for task in flex_workflow.get('tasks', []):
            if task.get('ai_generated', False):
                ai_generated_tasks.append(task['id'])

        if ai_generated_tasks:
            has_ai_content = True

        # Add appropriate markers to filename
        if is_incomplete and has_ai_content:
            filename = f'{base_name}.ai_enhanced.incomplete.flex.json'
        elif is_incomplete:
            filename = f'{base_name}.incomplete.flex.json'
        elif has_ai_content:
            filename = f'{base_name}.ai_enhanced.flex.json'
        else:
            filename = f'{base_name}.flex.json'

        flex_file_path = os.path.join(output_dir, filename)

        with open(flex_file_path, 'w') as f:
            json.dump(flex_workflow, f, indent=2)

        logger.info(f'Saved FLEX document: {flex_file_path}')

        # Also save Python files from FLEX metadata if they exist
        python_files = flex_workflow.get('metadata', {}).get('python_files', {})
        if python_files:
            # Create Glue Python Shell jobs directory
            dag_name = flex_workflow.get('name', base_name)
            glue_jobs_dir = os.path.join(output_dir, 'glue_python_shell_jobs', dag_name)
            os.makedirs(glue_jobs_dir, exist_ok=True)

            for filename, file_content in python_files.items():
                # Save Python script
                python_file_path = os.path.join(glue_jobs_dir, filename)
                with open(python_file_path, 'w') as f:
                    f.write(file_content)
                logger.info(f'Saved Python file from FLEX: {python_file_path}')

                # Create Glue job definition
                job_name = filename.replace('.py', '')
                glue_job_def = {
                    'Name': f'{dag_name}_{job_name}',
                    'Role': 'arn:aws:iam::ACCOUNT_ID:role/GlueServiceRole',
                    'Command': {
                        'Name': 'pythonshell',
                        'ScriptLocation': f's3://YOUR_BUCKET/glue_scripts/{dag_name}/{filename}',
                        'PythonVersion': '3.9',
                    },
                    'DefaultArguments': {
                        '--job-language': 'python',
                        '--enable-metrics': '',
                        '--enable-continuous-cloudwatch-log': 'true',
                    },
                    'MaxRetries': 0,
                    'Timeout': 2880,
                    'GlueVersion': '3.0',
                }

                job_def_path = os.path.join(glue_jobs_dir, f'{job_name}_glue_job.json')
                with open(job_def_path, 'w') as f:
                    json.dump(glue_job_def, f, indent=2)
                logger.info(f'Saved Glue job definition: {job_def_path}')

    @staticmethod
    def save_target_job(
        target_config: Dict,
        original_file_path: str,
        output_dir: str,
        target_framework: str,
    ):
        """Save generated target job to output directory"""
        original_path = Path(original_file_path)
        original_name = original_path.stem

        # Handle FLEX files: remove .flex from filename if present
        if original_name.endswith('.flex'):
            original_name = original_name[:-5]  # Remove '.flex' suffix

        if target_framework == 'airflow':
            target_file_path = os.path.join(output_dir, f'{original_name}.py')
            content = target_config.get('dag_code', '')
        elif target_framework == 'step_functions':
            target_file_path = os.path.join(output_dir, f'{original_name}.json')
            content = json.dumps(target_config.get('state_machine_definition', {}), indent=2)
        else:
            target_file_path = os.path.join(output_dir, f'{original_name}.json')
            content = json.dumps(target_config, indent=2)

        with open(target_file_path, 'w') as f:
            f.write(content)

        logger.info(f'Saved target job: {target_file_path}')

        # Save Python files if they exist in target config
        python_files = target_config.get('python_files', {})
        if python_files:
            # Create Glue Python Shell jobs directory
            glue_jobs_dir = os.path.join(output_dir, 'glue_python_shell_jobs', original_name)
            os.makedirs(glue_jobs_dir, exist_ok=True)

            for filename, file_content in python_files.items():
                # Save Python script
                python_file_path = os.path.join(glue_jobs_dir, filename)
                with open(python_file_path, 'w') as f:
                    f.write(file_content)
                logger.info(f'Saved Python file: {python_file_path}')

                # Create Glue job definition
                job_name = filename.replace('.py', '')
                glue_job_def = {
                    'Name': f'{original_name}_{job_name}',
                    'Role': 'arn:aws:iam::ACCOUNT_ID:role/GlueServiceRole',
                    'Command': {
                        'Name': 'pythonshell',
                        'ScriptLocation': f's3://YOUR_BUCKET/glue_scripts/{original_name}/{filename}',
                        'PythonVersion': '3.9',
                    },
                    'DefaultArguments': {
                        '--job-language': 'python',
                        '--enable-metrics': '',
                        '--enable-continuous-cloudwatch-log': 'true',
                    },
                    'MaxRetries': 0,
                    'Timeout': 2880,
                    'GlueVersion': '3.0',
                }

                job_def_path = os.path.join(glue_jobs_dir, f'{job_name}_glue_job.json')
                with open(job_def_path, 'w') as f:
                    json.dump(glue_job_def, f, indent=2)
                logger.info(f'Saved Glue job definition: {job_def_path}')
