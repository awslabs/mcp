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

"""ETL Replatforming MCP Server."""

import json
import os
import sys
from typing import Any, Dict, Optional

from fastmcp import FastMCP
from loguru import logger
from pydantic import Field

from .constants import (
    DEFAULT_AWS_REGION,
    DEFAULT_LOG_LEVEL,
    LOG_FORMAT,
    LOG_ROTATION_SIZE,
    STATUS_COMPLETE,
    STATUS_ERROR,
    STATUS_INCOMPLETE,
    SUPPORTED_SOURCE_FRAMEWORKS,
    SUPPORTED_TARGET_FRAMEWORKS,
)
from .generators.airflow_generator import AirflowGenerator
from .generators.step_functions_generator import StepFunctionsGenerator
from .models.flex_workflow import FlexWorkflow
from .models.llm_config import LLMConfig
from .parsers.airflow_parser import AirflowParser
from .parsers.azure_data_factory_parser import AzureDataFactoryParser
from .parsers.step_functions_parser import StepFunctionsParser
from .services.bedrock_service import BedrockService
from .services.response_formatter import ResponseFormatter
from .utils.directory_processor import DirectoryProcessor
from .utils.workflow_processor import WorkflowProcessor
from .validators.workflow_validator import WorkflowValidator

# Configure logging with structured format
logger.remove()
logger.add(
    sys.stderr,
    level=os.getenv('FASTMCP_LOG_LEVEL', DEFAULT_LOG_LEVEL),
    format=LOG_FORMAT,
)

# Add file logging if LOG_FILE environment variable is set
log_file = os.getenv('MCP_LOG_FILE')
if log_file:
    logger.add(
        log_file,
        level=os.getenv('FASTMCP_LOG_LEVEL', DEFAULT_LOG_LEVEL),
        rotation=LOG_ROTATION_SIZE,
        format=LOG_FORMAT,
    )

# Initialize MCP server
mcp = FastMCP(
    'awslabs-etl-replatforming-mcp-server',
    instructions="""
# ETL Replatforming Service

This MCP server converts ETL orchestration code between frameworks using FLEX (Framework for Linking ETL eXchange) with validation and user interaction.

## Available Tools

### Directory-Based Tools (Batch Processing)

#### parse-to-flex
Parse source framework code to FLEX workflow format with validation and user interaction.
Process: Parse → Validate → Bedrock Enhancement → Validate → User Prompts (if needed)

#### convert-etl-workflow
Complete ETL workflow conversion with user interaction.
Process: Parse → Validate → Bedrock Enhancement → Validate → User Prompts → Generate Target
**Key**: Generation only happens with complete FLEX - no validation during generation phase.

#### generate-from-flex
Generate target framework code from existing FLEX workflow.
Process: Validate FLEX → User Prompts (if incomplete) → Generate Target
**Key**: Validates user-provided FLEX before generation.

### Single Workflow Tools (Individual Processing)

#### parse-single-workflow-to-flex
Parse individual workflow content to FLEX format.
Input: Raw workflow content (JSON/Python), Output: FLEX document

#### convert-single-etl-workflow
Complete single workflow conversion.
Input: Raw workflow content, Output: FLEX document + target code

#### generate-single-workflow-from-flex
Generate target code from FLEX document.
Input: FLEX document, Output: Target framework code

## Process Flow
```
Source Code → Parse → Validate → AI Enhancement → Validate → User Interaction → Generate
```

**Validation Principles:**
- All validation happens during FLEX creation
- Generation assumes complete, valid FLEX documents
- User prompts only occur when parsing + AI cannot determine missing elements
- Iterative process - users provide responses until workflow is complete

## Supported Frameworks
- **Source**: Step Functions, Airflow, Azure Data Factory
- **Target**: Airflow, Step Functions
- **Planned**: Prefect, Dagster

## FLEX Workflow Standard
Framework for Linking ETL eXchange - purpose-built intermediate representation with completeness validation for universal task representation, dependency management, and schedule abstraction.
""",
    dependencies=[
        'pydantic',
        'boto3',
        'loguru',
    ],
)

# Initialize components
validator = WorkflowValidator()
response_formatter = ResponseFormatter()
workflow_processor = WorkflowProcessor(validator)
_bedrock_service = None
_global_llm_config = None


def set_global_llm_config(llm_config: Optional[Dict[str, Any]]):
    """Set global LLM configuration for consistent usage across all tools."""
    global _global_llm_config, _bedrock_service
    _global_llm_config = llm_config
    # Reset bedrock service to use new config
    _bedrock_service = None


def get_effective_llm_config(tool_llm_config: Optional[Dict[str, Any]] = None) -> LLMConfig:
    """Get effective LLM configuration with proper precedence."""
    # Priority: tool_llm_config > global_llm_config > default
    if tool_llm_config:
        return LLMConfig.from_dict(tool_llm_config)
    elif _global_llm_config:
        return LLMConfig.from_dict(_global_llm_config)
    else:
        return LLMConfig(region=os.getenv('AWS_REGION', DEFAULT_AWS_REGION))


def get_bedrock_service(llm_config: Optional[Dict[str, Any]] = None):
    """Get Bedrock service with consistent configuration."""
    global _bedrock_service

    # If no custom config and we have a global service, reuse it
    if not llm_config and not _global_llm_config and _bedrock_service is not None:
        return _bedrock_service

    # Create new service with effective config
    effective_config = get_effective_llm_config(llm_config)

    # Cache service only if using default config (no custom overrides)
    if not llm_config and not _global_llm_config:
        if _bedrock_service is None:
            _bedrock_service = BedrockService(effective_config)
        return _bedrock_service
    else:
        # Return new instance for custom configs
        return BedrockService(effective_config)


def get_parser(framework: str):
    """Get parser for framework."""
    parsers = {
        'step_functions': StepFunctionsParser(),
        'airflow': AirflowParser(),
        'azure_data_factory': AzureDataFactoryParser(),
    }
    if framework not in SUPPORTED_SOURCE_FRAMEWORKS:
        raise ValueError(
            f'Unsupported source framework: {framework}. Supported: {SUPPORTED_SOURCE_FRAMEWORKS}'
        )
    return parsers[framework]


def get_generator(framework: str, llm_config: Optional[Dict[str, Any]] = None):
    """Get generator for framework."""
    if framework not in SUPPORTED_TARGET_FRAMEWORKS:
        raise ValueError(
            f'Unsupported target framework: {framework}. Supported: {SUPPORTED_TARGET_FRAMEWORKS}'
        )

    if framework == 'airflow':
        llm_config_obj = LLMConfig.from_dict(llm_config) if llm_config else None
        return AirflowGenerator(llm_config_obj)
    elif framework == 'step_functions':
        return StepFunctionsGenerator()
    else:
        raise ValueError(f'No generator available for {framework}')


async def parse_to_flex_workflow(
    source_framework: str,
    input_code: str,
    llm_config: Optional[Dict[str, Any]] = None,
    context_document: Optional[str] = None,
    filename: Optional[str] = None,
) -> Dict[str, Any]:
    """Parse source code to FLEX format with AI enhancement."""
    # Parse with deterministic parser
    parser = get_parser(source_framework)
    flex_workflow = parser.parse_code(input_code)
    validation_result = validator.validate(flex_workflow)

    # Get initial state
    deterministic_completeness = (
        flex_workflow.parsing_info.parsing_completeness if flex_workflow.parsing_info else 0.0
    )
    required_missing = flex_workflow.get_missing_fields()

    # Log deterministic results
    workflow_processor.log_parsing_results(deterministic_completeness, filename, 'deterministic')

    # Apply AI enhancement if needed
    if workflow_processor.should_enhance_with_ai(flex_workflow):
        flex_workflow, validation_result = await _apply_ai_enhancement(
            flex_workflow,
            parser,
            input_code,
            source_framework,
            llm_config,
            context_document,
            required_missing,
            deterministic_completeness,
            filename,
        )
    else:
        workflow_processor.log_parsing_results(deterministic_completeness, filename, 'complete')

    # Determine final status and return
    status = workflow_processor.determine_final_status(flex_workflow)
    return workflow_processor.prepare_parse_result(status, flex_workflow, validation_result)


async def _apply_ai_enhancement(
    flex_workflow: FlexWorkflow,
    parser,
    input_code: str,
    source_framework: str,
    llm_config: Optional[Dict[str, Any]],
    context_document: Optional[str],
    required_missing: list,
    deterministic_completeness: float,
    filename: Optional[str],
) -> tuple[FlexWorkflow, Dict[str, Any]]:
    """Apply AI enhancement to incomplete workflow."""
    workflow_processor.log_parsing_results(
        deterministic_completeness, filename, 'ai_enhancement_start'
    )
    logger.info(f'Required missing fields: {required_missing}')

    # Prepare workflow for enhancement
    workflow_processor.update_parsing_info_after_enhancement(flex_workflow, required_missing)

    try:
        # Get enhanced workflow
        effective_config = llm_config if llm_config else _global_llm_config
        enhanced_dict = get_bedrock_service(effective_config).enhance_flex_workflow(
            flex_workflow.to_dict(),
            input_code,
            source_framework,
            effective_config,
            context_document,
            required_missing,
        )

        if enhanced_dict:
            return _process_enhancement_result(
                enhanced_dict,
                flex_workflow,
                parser,
                deterministic_completeness,
                filename,
            )
        else:
            return _handle_enhancement_failure(
                flex_workflow, parser, deterministic_completeness, filename
            )

    except ValueError as e:
        logger.warning(
            f'AI enhancement validation error: {deterministic_completeness:.1%} -> {deterministic_completeness:.1%} ({str(e)}){_format_filename(filename)}'
        )
        return flex_workflow, validator.validate(flex_workflow)
    except Exception as e:
        logger.warning(
            f'AI enhancement failed: {deterministic_completeness:.1%} -> {deterministic_completeness:.1%} ({str(e)}){_format_filename(filename)}'
        )
        return flex_workflow, validator.validate(flex_workflow)


def _process_enhancement_result(
    enhanced_dict: Dict[str, Any],
    original_workflow: FlexWorkflow,
    parser,
    deterministic_completeness: float,
    filename: Optional[str],
) -> tuple[FlexWorkflow, Dict[str, Any]]:
    """Process successful AI enhancement result."""
    enhanced_workflow = FlexWorkflow.from_dict(enhanced_dict)
    enhanced_validation = validator.validate(enhanced_workflow)

    # Recalculate completeness
    final_completeness = _recalculate_completeness(parser, enhanced_workflow)

    # Check if improvement occurred
    improved, final_completeness = workflow_processor.calculate_enhancement_improvement(
        original_workflow, enhanced_workflow, deterministic_completeness
    )

    if improved:
        workflow_processor.log_parsing_results(
            final_completeness, filename, 'ai_enhancement_success'
        )
        return enhanced_workflow, enhanced_validation
    else:
        workflow_processor.log_parsing_results(
            final_completeness, filename, 'ai_enhancement_no_improvement'
        )
        return original_workflow, validator.validate(original_workflow)


def _handle_enhancement_failure(
    flex_workflow: FlexWorkflow,
    parser,
    deterministic_completeness: float,
    filename: Optional[str],
) -> tuple[FlexWorkflow, Dict[str, Any]]:
    """Handle case where AI enhancement returned no result."""
    # Recalculate completeness in case it was wrong
    actual_completeness = _recalculate_completeness(parser, flex_workflow)

    if actual_completeness != deterministic_completeness:
        logger.info(
            f'Corrected parsing completeness: {deterministic_completeness:.1%} -> {actual_completeness:.1%}{_format_filename(filename)}'
        )
    else:
        workflow_processor.log_parsing_results(
            deterministic_completeness, filename, 'ai_enhancement_failed'
        )

    return flex_workflow, validator.validate(flex_workflow)


def _recalculate_completeness(parser, workflow: FlexWorkflow) -> float:
    """Recalculate parsing completeness after enhancement."""
    if hasattr(parser, '_calculate_parsing_completeness'):
        final_completeness = parser._calculate_parsing_completeness(
            workflow.tasks, workflow.schedule
        )
        if workflow.parsing_info:
            workflow.parsing_info.parsing_completeness = final_completeness
        return final_completeness
    else:
        return workflow.parsing_info.parsing_completeness if workflow.parsing_info else 1.0


def _format_filename(filename: Optional[str]) -> str:
    """Format filename for logging."""
    return f' ({filename})' if filename else ''


async def generate_from_flex_workflow(
    flex_workflow: FlexWorkflow,
    target_framework: str,
    context_document: Optional[str] = None,
    llm_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generate target code from FLEX workflow."""
    generator = get_generator(target_framework, llm_config)
    target_config = generator.generate(flex_workflow, context_document, llm_config)
    return {'status': 'complete', 'target_config': target_config}


@mcp.tool(name='convert-single-etl-workflow')
async def convert_single_etl_workflow(
    workflow_content: str = Field(
        ...,
        description='Source workflow definition content (JSON for Step Functions/ADF, Python for Airflow)',
    ),
    source_framework: str = Field(
        ...,
        description='Source framework identifier (step_functions, airflow, azure_data_factory)',
    ),
    target_framework: str = Field(
        ..., description='Target framework identifier (airflow, step_functions)'
    ),
    context_document: Optional[str] = None,
    llm_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Convert a single ETL workflow between frameworks.

    Process: Parse → FLEX → Generate Target

    ## Usage Examples
    - Convert Step Functions JSON to Airflow DAG
    - Convert Airflow DAG to Step Functions state machine

    ## Returns
    Complete conversion result with FLEX document and target code
    """
    # Set global LLM config for consistent usage across this tool call
    set_global_llm_config(llm_config)

    try:
        # Parse to FLEX
        parse_result = await parse_to_flex_workflow(
            source_framework,
            workflow_content,
            llm_config,
            context_document,
            'single_workflow',
        )

        if parse_result['status'] != STATUS_COMPLETE:
            return response_formatter.prompt_user_for_missing(
                parse_result['flex_workflow'],
                parse_result['validation_result'],
                target_framework,
            )

        # Generate target
        generation_result = await generate_from_flex_workflow(
            parse_result['flex_workflow'],
            target_framework,
            context_document,
            llm_config,
        )

        return {
            'status': STATUS_COMPLETE,
            'flex_workflow': parse_result['flex_workflow'].to_dict(),
            'target_code': generation_result['target_config'],
            'message': f'Successfully converted {source_framework} workflow to {target_framework}',
        }

    except Exception as e:
        logger.error(f'Error in convert_single_etl_workflow: {str(e)}')
        raise


@mcp.tool(name='parse-single-workflow-to-flex')
async def parse_single_workflow_to_flex(
    workflow_content: str = Field(
        ...,
        description='Source workflow definition content (JSON for Step Functions/ADF, Python for Airflow)',
    ),
    source_framework: str = Field(
        ...,
        description='Source framework identifier (step_functions, airflow, azure_data_factory)',
    ),
    llm_config: Optional[Dict[str, Any]] = None,
    context_document: Optional[str] = Field(
        default=None,
        description='Optional context document for organizational standards during AI enhancement',
    ),
) -> Dict[str, Any]:
    """Parse a single workflow to FLEX format.

    Process: Parse → FLEX Format

    ## Usage Examples
    - Parse Step Functions JSON to FLEX
    - Parse Airflow DAG to FLEX

    ## Returns
    FLEX document with validation status and completion percentage
    """
    # Set global LLM config for consistent usage across this tool call
    set_global_llm_config(llm_config)

    try:
        parse_result = await parse_to_flex_workflow(
            source_framework,
            workflow_content,
            llm_config,
            context_document,
            'single_workflow',
        )

        if parse_result['status'] == STATUS_COMPLETE:
            return response_formatter.format_parse_response(parse_result)
        else:
            return response_formatter.prompt_user_for_missing(
                parse_result['flex_workflow'], parse_result['validation_result']
            )

    except Exception as e:
        logger.error(f'Error in parse_single_workflow_to_flex: {str(e)}')
        raise


@mcp.tool(name='generate-single-workflow-from-flex')
async def generate_single_workflow_from_flex(
    flex_workflow: Dict[str, Any],
    target_framework: str = Field(
        ..., description='Target framework identifier (airflow, step_functions)'
    ),
    context_document: Optional[str] = Field(
        default=None,
        description='Optional context document for organizational standards',
    ),
) -> Dict[str, Any]:
    """Generate target framework code from a FLEX workflow.

    Process: Validate FLEX → Generate Target

    ## Usage Examples
    - Generate Airflow DAG from FLEX document
    - Generate Step Functions state machine from FLEX document

    ## Returns
    Generated target framework code
    """
    try:
        # Reconstruct and validate FLEX workflow
        workflow = FlexWorkflow.from_dict(flex_workflow)
        validation_result = validator.validate(workflow)

        if not validation_result['is_complete']:
            return response_formatter.prompt_user_for_missing(
                workflow, validation_result, target_framework
            )

        # Generate target format
        generation_result = await generate_from_flex_workflow(
            workflow, target_framework, context_document
        )

        return {
            'status': STATUS_COMPLETE,
            'target_code': generation_result['target_config'],
            'flex_workflow': flex_workflow,
            'message': f'Successfully generated {target_framework} code from FLEX workflow',
        }

    except Exception as e:
        logger.error(f'Error in generate_single_workflow_from_flex: {str(e)}')
        raise


@mcp.tool(name='convert-etl-workflow')
async def convert_etl_workflow(
    directory_path: str = Field(
        ..., description='Path to directory containing workflow files to convert'
    ),
    target_framework: str = Field(
        ..., description='Target framework identifier (airflow, step_functions, etc.)'
    ),
    output_directory: Optional[str] = Field(
        default=None,
        description='Optional custom output directory (defaults to outputs/ if not provided)',
    ),
    context_file: Optional[str] = None,
    llm_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Convert ETL workflows in a directory between frameworks.

    Process: Scan Directory → Auto-detect Formats → Parse → FLEX → Generate Target

    ## Usage Examples
    - "Convert jobs in ./step_functions_workflows to airflow"
    - "Convert the workflows in /path/to/jobs directory to step_functions"

    ## Output
    Creates single directory containing both FLEX documents and target framework files:
    - "outputs/generated_jobs_{dir_name}" (contains both .flex.json and target files)
    """
    # Set global LLM config for consistent usage across this tool call
    set_global_llm_config(llm_config)

    try:
        # Scan directory
        files_and_frameworks = DirectoryProcessor.scan_directory(directory_path)
        if not files_and_frameworks:
            return {
                'status': 'error',
                'message': f'No workflow files detected in directory: {directory_path}',
            }

        # Create output directory (single directory for both FLEX and target files)
        if output_directory:
            # Use custom output directory
            from pathlib import Path

            output_path = Path(output_directory)
            input_name = Path(directory_path).name
            jobs_output_dir = str(
                output_path / f'target_{target_framework}_from_source_{input_name}'
            )
            Path(jobs_output_dir).mkdir(parents=True, exist_ok=True)
        else:
            # Use default centralized outputs
            _, jobs_output_dir = DirectoryProcessor.create_output_directories(
                directory_path, 'convert_etl_workflow', output_directory
            )

        # Load context
        context_document = None
        if context_file:
            try:
                with open(context_file, 'r', encoding='utf-8') as f:
                    context_document = f.read().strip()
            except Exception as e:
                logger.warning(f'Could not read context file {context_file}: {str(e)}')

        results = []
        for file_path, source_framework in files_and_frameworks:
            try:
                with open(file_path, 'r') as f:
                    input_code = f.read()

                parse_result = await parse_to_flex_workflow(
                    source_framework,
                    input_code,
                    llm_config,
                    context_document,
                    file_path,
                )

                # Generate target if complete
                if parse_result['status'] == STATUS_COMPLETE:
                    try:
                        generation_result = await generate_from_flex_workflow(
                            parse_result['flex_workflow'],
                            target_framework,
                            context_document,
                            llm_config,
                        )

                        # Save both FLEX document and target job in the same output directory
                        flex_dict = (
                            parse_result['flex_workflow'].to_dict()
                            if hasattr(parse_result['flex_workflow'], 'to_dict')
                            else parse_result['flex_workflow']
                        )
                        DirectoryProcessor.save_flex_document(
                            flex_dict, file_path, jobs_output_dir
                        )
                        DirectoryProcessor.save_target_job(
                            generation_result['target_config'],
                            file_path,
                            jobs_output_dir,
                            target_framework,
                        )

                        results.append({'file': file_path, 'status': STATUS_COMPLETE})
                    except ValueError as e:
                        logger.error(f'Generation error for {file_path}: {str(e)}')
                        results.append(
                            {
                                'file': file_path,
                                'status': STATUS_ERROR,
                                'error': f'Generation error: {str(e)}',
                            }
                        )
                    except Exception as e:
                        logger.error(f'Unexpected generation error for {file_path}: {str(e)}')
                        results.append(
                            {
                                'file': file_path,
                                'status': STATUS_ERROR,
                                'error': f'Generation error: {str(e)}',
                            }
                        )
                else:
                    # Save FLEX document even if incomplete for user review
                    if 'flex_workflow' in parse_result:
                        flex_dict = (
                            parse_result['flex_workflow'].to_dict()
                            if hasattr(parse_result['flex_workflow'], 'to_dict')
                            else parse_result['flex_workflow']
                        )
                        DirectoryProcessor.save_flex_document(
                            flex_dict, file_path, jobs_output_dir
                        )

                    results.append({'file': file_path, 'status': STATUS_INCOMPLETE})

            except Exception as e:
                logger.error(f'Error processing {file_path}: {str(e)}')
                results.append({'file': file_path, 'status': 'error', 'error': str(e)})

        completed = len([r for r in results if r['status'] == 'complete'])
        total = len(results)

        return {
            'status': 'complete' if completed == total else 'partial',
            'processed_files': total,
            'completed_conversions': completed,
            'output_directory': jobs_output_dir,
            'results': results,
            'message': f'Processed {total} files, {completed} completed successfully. Both FLEX documents and {target_framework} files saved to: {jobs_output_dir}',
        }

    except FileNotFoundError as e:
        logger.error(f'Directory not found in convert_etl_workflow: {str(e)}')
        raise ValueError(f'Directory not found: {directory_path}') from e
    except PermissionError as e:
        logger.error(f'Permission denied in convert_etl_workflow: {str(e)}')
        raise ValueError(f'Permission denied accessing: {directory_path}') from e
    except Exception as e:
        logger.error(f'Unexpected error in convert_etl_workflow: {str(e)}')
        raise


@mcp.tool(name='parse-to-flex')
async def parse_to_flex(
    directory_path: str = Field(
        ...,
        description='Path to directory containing workflow files to parse to FLEX format',
    ),
    output_directory: Optional[str] = Field(
        default=None,
        description='Optional custom output directory (defaults to outputs/ if not provided)',
    ),
    context_file: Optional[str] = None,
    llm_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Parse workflow files in a directory to FLEX format.

    Process: Scan Directory → Auto-detect Formats → Parse → FLEX Format

    ## Usage Examples
    - "Get FLEX docs for files in ./my_workflows"
    - "Parse the jobs in /path/to/workflows directory to FLEX"

    ## Output
    Creates directory in centralized outputs/ folder:
    - "outputs/flex_docs_{dir_name}"
    """
    # Set global LLM config for consistent usage across this tool call
    set_global_llm_config(llm_config)

    try:
        files_and_frameworks = DirectoryProcessor.scan_directory(directory_path)
        if not files_and_frameworks:
            return {
                'status': 'error',
                'message': f'No workflow files detected in directory: {directory_path}',
            }

        # Create output directories
        if output_directory:
            # Use custom output directory
            from pathlib import Path

            output_path = Path(output_directory)
            input_name = Path(directory_path).name
            flex_output_dir = str(output_path / f'target_flex_from_source_{input_name}')
            Path(flex_output_dir).mkdir(parents=True, exist_ok=True)
        else:
            # Use default centralized outputs
            flex_output_dir, _ = DirectoryProcessor.create_output_directories(
                directory_path, 'parse_to_flex', output_directory
            )

        # Load context
        context_document = None
        if context_file:
            try:
                with open(context_file, 'r', encoding='utf-8') as f:
                    context_document = f.read().strip()
            except Exception as e:
                logger.warning(f'Could not read context file {context_file}: {str(e)}')

        results = []
        for file_path, source_framework in files_and_frameworks:
            try:
                with open(file_path, 'r') as f:
                    input_code = f.read()

                parse_result = await parse_to_flex_workflow(
                    source_framework,
                    input_code,
                    llm_config,
                    context_document,
                    file_path,
                )

                if 'flex_workflow' in parse_result:
                    flex_dict = (
                        parse_result['flex_workflow'].to_dict()
                        if hasattr(parse_result['flex_workflow'], 'to_dict')
                        else parse_result['flex_workflow']
                    )
                    DirectoryProcessor.save_flex_document(flex_dict, file_path, flex_output_dir)

                results.append(
                    {
                        'file': file_path,
                        'framework': source_framework,
                        'status': parse_result['status'],
                        'completion_percentage': parse_result.get('completion_percentage', 0.0),
                    }
                )

            except Exception as e:
                logger.error(f'Error processing {file_path}: {str(e)}')
                results.append({'file': file_path, 'status': 'error', 'error': str(e)})

        completed = len([r for r in results if r['status'] == 'complete'])
        total = len(results)

        return {
            'status': 'complete' if completed == total else 'partial',
            'processed_files': total,
            'completed_parses': completed,
            'flex_output_directory': flex_output_dir,
            'results': results,
            'message': f'Processed {total} files, {completed} parsed successfully to FLEX format. Outputs saved to centralized outputs/ directory.',
        }

    except Exception as e:
        logger.error(f'Error in parse_to_flex: {str(e)}')
        raise


@mcp.tool(name='generate-from-flex')
async def generate_from_flex(
    directory_path: str = Field(
        ...,
        description='Path to directory containing FLEX workflow files to generate target jobs from',
    ),
    target_framework: str = Field(
        ..., description='Target framework identifier (airflow, step_functions)'
    ),
    output_directory: Optional[str] = Field(
        default=None,
        description='Optional custom output directory (defaults to outputs/ if not provided)',
    ),
    context_file: Optional[str] = None,
    llm_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generate target framework jobs from FLEX workflow files in a directory.

    Process: Scan Directory → Load FLEX Files → Validate → Generate Target Jobs

    ## Usage Examples
    - "Convert FLEX docs in ./flex_output to step_functions"
    - "Generate airflow jobs from FLEX files in /path/to/flex_docs"

    ## Output
    Creates directory in centralized outputs/ folder:
    - "outputs/generated_jobs_{dir_name}"
    """
    # Set global LLM config for consistent usage across this tool call
    set_global_llm_config(llm_config)

    try:
        files_and_frameworks = DirectoryProcessor.scan_directory(directory_path)
        flex_files = [(f, fw) for f, fw in files_and_frameworks if fw == 'flex']

        if not flex_files:
            return {
                'status': 'error',
                'message': f'No FLEX workflow files detected in directory: {directory_path}',
            }

        # Create output directories
        if output_directory:
            # Use custom output directory
            from pathlib import Path

            output_path = Path(output_directory)
            input_name = Path(directory_path).name
            jobs_output_dir = str(
                output_path / f'target_{target_framework}_from_source_{input_name}'
            )
            Path(jobs_output_dir).mkdir(parents=True, exist_ok=True)
        else:
            # Use default centralized outputs
            _, jobs_output_dir = DirectoryProcessor.create_output_directories(
                directory_path, 'generate_from_flex', output_directory
            )

        context_document = None
        if context_file:
            try:
                with open(context_file, 'r', encoding='utf-8') as f:
                    context_document = f.read().strip()
            except Exception as e:
                logger.warning(f'Could not read context file {context_file}: {str(e)}')

        results = []
        for file_path, _ in flex_files:
            try:
                with open(file_path, 'r') as f:
                    flex_data = json.load(f)

                workflow = FlexWorkflow.from_dict(flex_data)
                validation_result = validator.validate(workflow)

                if not validation_result['is_complete']:
                    results.append(
                        {
                            'file': file_path,
                            'status': 'incomplete',
                            'missing': validation_result.get('missing_fields', []),
                        }
                    )
                    continue

                generation_result = await generate_from_flex_workflow(
                    workflow, target_framework, context_document
                )
                DirectoryProcessor.save_target_job(
                    generation_result['target_config'],
                    file_path,
                    jobs_output_dir,
                    target_framework,
                )
                results.append({'file': file_path, 'status': 'complete'})

            except Exception as e:
                logger.error(f'Error processing {file_path}: {str(e)}')
                results.append({'file': file_path, 'status': 'error', 'error': str(e)})

        completed = len([r for r in results if r['status'] == 'complete'])
        total = len(results)

        return {
            'status': 'complete' if completed == total else 'partial',
            'processed_files': total,
            'completed_generations': completed,
            'jobs_output_directory': jobs_output_dir,
            'results': results,
            'message': f'Processed {total} FLEX files, {completed} generated successfully to {target_framework}. Outputs saved to centralized outputs/ directory.',
        }

    except Exception as e:
        logger.error(f'Error in generate_from_flex: {str(e)}')
        raise


def main():
    """Run the MCP server with CLI argument support."""
    mcp.run()


if __name__ == '__main__':
    main()
