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

import os
import sys
import json
from typing import Dict, Any, Optional

from fastmcp import FastMCP
from loguru import logger
from pydantic import Field

from .models.flex_workflow import FlexWorkflow

from .models.llm_config import LLMConfig
from .parsers.step_functions_parser import StepFunctionsParser
from .parsers.airflow_parser import AirflowParser
from .parsers.azure_data_factory_parser import AzureDataFactoryParser
from .generators.airflow_generator import AirflowGenerator
from .generators.step_functions_generator import StepFunctionsGenerator
from .validators.workflow_validator import WorkflowValidator
from .services.bedrock_service import BedrockService
from .utils.directory_processor import DirectoryProcessor


# Configure logging
logger.remove()
logger.add(sys.stderr, level=os.getenv('FASTMCP_LOG_LEVEL', 'WARNING'))

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

# Initialize service components (AWS services initialized on first use)
validator = WorkflowValidator()
_bedrock_service = None  # Lazy initialization
parsers = {
    "step_functions": StepFunctionsParser(),
    "airflow": AirflowParser(),
    "azure_data_factory": AzureDataFactoryParser()
}
generators = {
    "airflow": AirflowGenerator(),
    "step_functions": StepFunctionsGenerator()
}

def _get_bedrock_service():
    """Lazy initialization of Bedrock service - only when actually needed."""
    global _bedrock_service
    if _bedrock_service is None:
        _bedrock_service = BedrockService(LLMConfig(region=os.getenv('AWS_REGION', 'us-east-1')))
    return _bedrock_service


async def _enhance_with_bedrock(
    flex_workflow: FlexWorkflow,
    input_code: str,
    source_framework: str,
    llm_config: Optional[Dict[str, Any]],
    target_framework: Optional[str] = None
) -> FlexWorkflow:
    """Single function to enhance incomplete workflow using Bedrock API."""
    logger.info('Attempting Bedrock enhancement for incomplete workflow')
    
    try:
        enhanced_workflow_dict = _get_bedrock_service().enhance_flex_workflow(
            flex_workflow.to_dict(), input_code, source_framework, llm_config, target_framework
        )
        
        if enhanced_workflow_dict:
            try:
                enhanced_workflow = FlexWorkflow.from_dict(enhanced_workflow_dict)
                enhanced_validation = validator.validate(enhanced_workflow)
                current_validation = validator.validate(flex_workflow)
                
                if enhanced_validation['is_complete']:
                    logger.info('Bedrock successfully completed workflow')
                    return enhanced_workflow
                elif enhanced_validation['completion_percentage'] > current_validation['completion_percentage']:
                    logger.info('Bedrock partially enhanced workflow')
                    return enhanced_workflow
            except Exception as e:
                logger.warning(f'Failed to apply Bedrock enhancement: {str(e)}')
    except Exception as e:
        error_msg = str(e)
        if 'AccessDeniedException' in error_msg:
            logger.warning('Bedrock access denied - AI enhancement disabled. See README for setup instructions.')
        elif 'Unable to locate credentials' in error_msg:
            logger.warning('AWS credentials not configured - AI enhancement disabled. Run: aws configure')
        else:
            logger.warning(f'Bedrock enhancement failed: {error_msg}')
    
    return flex_workflow


def _validate_flex_workflow(flex_workflow: FlexWorkflow) -> Dict[str, Any]:
    """Validate FLEX workflow completeness."""
    return validator.validate(flex_workflow)


def _prompt_user_for_missing(
    flex_workflow: FlexWorkflow,
    validation_result: Dict[str, Any],
    target_framework: Optional[str] = None
) -> Dict[str, Any]:
    """Generate response with FLEX document containing '?' placeholders for missing fields."""
    
    missing_fields = validation_result.get('missing_fields', [])
    
    # Create FLEX document with question mark placeholders (target-aware)
    flex_with_placeholders = flex_workflow.to_dict_with_placeholders(missing_fields, target_framework)
    
    # Build missing information message with cron-specific guidance
    missing_info = []
    for field in missing_fields:
        if field == "schedule_configuration":
            missing_info.append("• Schedule: Replace '?' with cron expression (e.g., '0 9 * * *' for daily at 9 AM, '0 */6 * * *' for every 6 hours)")
        elif field.startswith("task_") and field.endswith("_execution_details"):
            task_id = field.split("_")[1]
            missing_info.append(f"• Task '{task_id}': Replace '?' in command field with execution script or SQL query")
        elif field.startswith("task_") and field.endswith("_sql_query"):
            task_id = field.split("_")[1]
            missing_info.append(f"• Task '{task_id}': Replace '?' in command field with SQL query")
        else:
            missing_info.append(f"• {field.replace('_', ' ').title()}: Replace '?' with appropriate value")
    
    missing_text = "\n".join(missing_info) if missing_info else "No missing fields identified."
    
    # Check if Bedrock enhancement was attempted
    bedrock_warning = ""
    try:
        import boto3
        boto3.client('bedrock-runtime', region_name=os.getenv('AWS_REGION', 'us-east-1'))
    except Exception as e:
        if 'Unable to locate credentials' in str(e):
            bedrock_warning = "\n\n⚠️ AWS credentials not configured. AI enhancement disabled."
        elif 'AccessDeniedException' in str(e):
            bedrock_warning = "\n\n⚠️ Bedrock access denied. AI enhancement disabled."
        else:
            bedrock_warning = "\n\n⚠️ Bedrock unavailable. AI enhancement disabled."
    
    return {
        'status': 'incomplete',
        'flex_workflow': flex_with_placeholders,
        'completion_percentage': validation_result['completion_percentage'],
        'missing_information': missing_text,
        'message': f'Workflow conversion is {validation_result["completion_percentage"]:.0%} complete.\n\n{missing_text}{bedrock_warning}\n\n📋 **Next Steps:**\n1. Replace all "?" placeholders in the FLEX document\n2. Check FLEX_SPECIFICATION.md for:\n   • **Framework Mapping Table**: Shows how FLEX elements map to Airflow, Step Functions, and Azure Data Factory\n   • Task type conversions for {target_framework or "your target framework"}\n   • Field requirements and examples\n   • Default values for optional fields\n3. Resubmit the updated FLEX document',
        'instructions': 'Check FLEX_SPECIFICATION.md for field requirements. Only required fields (marked with ✅) need to be provided.'
    }


def _format_parse_response(parse_result: Dict[str, Any]) -> Dict[str, Any]:
    """Format response for parse-to-flex tool."""
    return {
        'status': 'complete',
        'flex_workflow': parse_result['flex_workflow'],
        'validation': parse_result['validation_result'],
        'completion_percentage': 1.0,
        'message': 'FLEX workflow generated successfully.'
    }


async def _parse_to_flex_workflow(
    source_framework: str,
    input_code: str,
    llm_config: Optional[Dict[str, Any]],
    target_framework: Optional[str] = None
) -> Dict[str, Any]:
    """Parse source framework code to FLEX format."""
    # Stage 1: Parse source code to FLEX format
    if source_framework not in parsers:
        raise ValueError(f'No parser available for {source_framework}')
        
    parser = parsers[source_framework]
    flex_workflow = parser.parse_code(input_code)
    
    # Stage 2: Validate
    validation_result = _validate_flex_workflow(flex_workflow)
    
    if validation_result['is_complete']:
        return {
            'status': 'complete',
            'flex_workflow': flex_workflow,
            'validation_result': validation_result
        }
    
    # Stage 3: Call Bedrock with original source job for missing elements
    enhanced_workflow = await _enhance_with_bedrock(flex_workflow, input_code, source_framework, llm_config, target_framework)
    
    # Stage 4: Validate again
    validation_result = _validate_flex_workflow(enhanced_workflow)
    if validation_result['is_complete']:
        return {
            'status': 'complete',
            'flex_workflow': enhanced_workflow,
            'validation_result': validation_result
        }
    
    # Stage 5: Prompt user for remaining elements with target framework context
    return _prompt_user_for_missing(enhanced_workflow, validation_result, target_framework)


async def _generate_from_flex_workflow(
    flex_workflow: FlexWorkflow,
    target_framework: str,
    context_document: Optional[str]
) -> Dict[str, Any]:
    """Generate target framework code from complete FLEX format."""
    if target_framework not in generators:
        raise ValueError(f'No generator available for {target_framework}')
        
    generator = generators[target_framework]
    target_config = generator.generate(flex_workflow, context_document)
    
    return {
        'status': 'complete',
        'target_config': target_config,
        'flex_workflow': flex_workflow,
    }


@mcp.tool(name='convert-single-etl-workflow')
async def convert_single_etl_workflow(
    workflow_content: str = Field(
        ..., description='Source workflow definition content (JSON for Step Functions/ADF, Python for Airflow)'
    ),
    source_framework: str = Field(
        ..., description='Source framework identifier (step_functions, airflow, azure_data_factory)'
    ),
    target_framework: str = Field(
        ..., description='Target framework identifier (airflow, step_functions)'
    ),
    context_document: Optional[str] = Field(
        default=None, description='Optional context document for organizational standards'
    ),
    llm_config: Optional[Dict[str, Any]] = Field(
        default=None, description='LLM model configuration for AI-enhanced parsing'
    ),
) -> Dict[str, Any]:
    """Convert a single ETL workflow between frameworks.
    
    Process: Parse → FLEX → Generate Target
    
    ## Usage Examples
    - Convert Step Functions JSON to Airflow DAG
    - Convert Airflow DAG to Step Functions state machine
    
    ## Returns
    Complete conversion result with FLEX document and target code
    """
    try:
        # Parse to FLEX
        parse_result = await _parse_to_flex_workflow(source_framework, workflow_content, llm_config, target_framework)
        
        if parse_result['status'] != 'complete':
            return parse_result
        
        # Generate target
        generation_result = await _generate_from_flex_workflow(
            parse_result['flex_workflow'], target_framework, context_document
        )
        
        return {
            'status': 'complete',
            'flex_workflow': parse_result['flex_workflow'].to_dict(),
            'target_code': generation_result['target_config'],
            'message': f'Successfully converted {source_framework} workflow to {target_framework}'
        }
        
    except Exception as e:
        logger.error(f'Error in convert_single_etl_workflow: {str(e)}')
        raise


@mcp.tool(name='parse-single-workflow-to-flex')
async def parse_single_workflow_to_flex(
    workflow_content: str = Field(
        ..., description='Source workflow definition content (JSON for Step Functions/ADF, Python for Airflow)'
    ),
    source_framework: str = Field(
        ..., description='Source framework identifier (step_functions, airflow, azure_data_factory)'
    ),
    llm_config: Optional[Dict[str, Any]] = Field(
        default=None, description='LLM model configuration for AI-enhanced parsing'
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
    try:
        parse_result = await _parse_to_flex_workflow(source_framework, workflow_content, llm_config)
        
        if parse_result['status'] == 'complete':
            return _format_parse_response(parse_result)
        else:
            return parse_result
        
    except Exception as e:
        logger.error(f'Error in parse_single_workflow_to_flex: {str(e)}')
        raise


@mcp.tool(name='generate-single-workflow-from-flex')
async def generate_single_workflow_from_flex(
    flex_workflow: Dict[str, Any] = Field(
        ..., description='Complete FLEX workflow document as JSON'
    ),
    target_framework: str = Field(
        ..., description='Target framework identifier (airflow, step_functions)'
    ),
    context_document: Optional[str] = Field(
        default=None, description='Optional context document for organizational standards'
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
        validation_result = _validate_flex_workflow(workflow)
        
        if not validation_result['is_complete']:
            return _prompt_user_for_missing(workflow, validation_result, target_framework)
        
        # Generate target format
        generation_result = await _generate_from_flex_workflow(workflow, target_framework, context_document)
        
        return {
            'status': 'complete',
            'target_code': generation_result['target_config'],
            'flex_workflow': flex_workflow,
            'message': f'Successfully generated {target_framework} code from FLEX workflow'
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
    context_file: Optional[str] = Field(
        default=None, description='Path to plain text file containing organizational context'
    ),
    llm_config: Optional[Dict[str, Any]] = Field(
        default=None, description='LLM model configuration for AI-enhanced parsing'
    ),
) -> Dict[str, Any]:
    """Convert ETL workflows in a directory between frameworks.
    
    Process: Scan Directory → Auto-detect Formats → Parse → FLEX → Generate Target
    
    ## Usage Examples
    - "Convert jobs in ./step_functions_workflows to airflow"
    - "Convert the workflows in /path/to/jobs directory to step_functions"
    
    ## Output
    Creates two directories at the same level as input directory:
    - "output flex docs for jobs in {dir_name}"
    - "output jobs for jobs in {dir_name}"
    """
    try:
        # Scan directory and detect formats
        files_and_frameworks = DirectoryProcessor.scan_directory(directory_path)
        
        if not files_and_frameworks:
            return {
                'status': 'error',
                'message': f'No workflow files detected in directory: {directory_path}'
            }
        
        # Create output directories
        flex_output_dir, jobs_output_dir = DirectoryProcessor.create_output_directories(
            directory_path, 'convert_etl_workflow'
        )
        
        # Load context document for LLM processing
        context_document = None
        if context_file:
            try:
                with open(context_file, 'r', encoding='utf-8') as f:
                    context_document = f.read().strip()
            except Exception as e:
                logger.warning(f'Could not read context file {context_file}: {str(e)}')
        
        results = []
        
        # Process each file
        for file_path, source_framework in files_and_frameworks:
            try:
                # Read file content
                with open(file_path, 'r') as f:
                    input_code = f.read()
                
                # Parse to FLEX
                parse_result = await _parse_to_flex_workflow(source_framework, input_code, llm_config, target_framework)
                
                # Save FLEX document
                if 'flex_workflow' in parse_result:
                    flex_dict = parse_result['flex_workflow'].to_dict() if hasattr(parse_result['flex_workflow'], 'to_dict') else parse_result['flex_workflow']
                    DirectoryProcessor.save_flex_document(flex_dict, file_path, flex_output_dir)
                
                # Generate target if complete
                if parse_result['status'] == 'complete':
                    generation_result = await _generate_from_flex_workflow(
                        parse_result['flex_workflow'], target_framework, context_document
                    )
                    DirectoryProcessor.save_target_job(
                        generation_result['target_config'], file_path, jobs_output_dir, target_framework
                    )
                    results.append({'file': file_path, 'status': 'complete'})
                else:
                    results.append({'file': file_path, 'status': 'incomplete', 'missing': parse_result.get('missing_information')})
                    
            except Exception as e:
                logger.error(f'Error processing {file_path}: {str(e)}')
                results.append({'file': file_path, 'status': 'error', 'error': str(e)})
        
        completed = len([r for r in results if r['status'] == 'complete'])
        total = len(results)
        
        return {
            'status': 'complete' if completed == total else 'partial',
            'processed_files': total,
            'completed_conversions': completed,
            'flex_output_directory': flex_output_dir,
            'jobs_output_directory': jobs_output_dir,
            'results': results,
            'message': f'Processed {total} files, {completed} completed successfully'
        }
        
    except Exception as e:
        logger.error(f'Error in convert_etl_workflow: {str(e)}')
        raise


@mcp.tool(name='parse-to-flex')
async def parse_to_flex(
    directory_path: str = Field(
        ..., description='Path to directory containing workflow files to parse to FLEX format'
    ),
    llm_config: Optional[Dict[str, Any]] = Field(
        default=None, description='LLM model configuration for AI-enhanced parsing'
    ),
) -> Dict[str, Any]:
    """Parse workflow files in a directory to FLEX format.
    
    Process: Scan Directory → Auto-detect Formats → Parse → FLEX Format
    
    ## Usage Examples
    - "Get FLEX docs for files in ./my_workflows"
    - "Parse the jobs in /path/to/workflows directory to FLEX"
    
    ## Output
    Creates directory at the same level as input directory:
    - "output flex docs for jobs in {dir_name}"
    """
    try:
        # Scan directory and detect formats
        files_and_frameworks = DirectoryProcessor.scan_directory(directory_path)
        
        if not files_and_frameworks:
            return {
                'status': 'error',
                'message': f'No workflow files detected in directory: {directory_path}'
            }
        
        # Create output directory
        flex_output_dir, _ = DirectoryProcessor.create_output_directories(
            directory_path, 'parse_to_flex'
        )
        
        results = []
        
        # Process each file
        for file_path, source_framework in files_and_frameworks:
            try:
                logger.info(f'Parsing {source_framework} file: {file_path}')
                
                # Read file content
                with open(file_path, 'r') as f:
                    input_code = f.read()
                
                # Parse to FLEX
                parse_result = await _parse_to_flex_workflow(source_framework, input_code, llm_config)
                
                # Save FLEX document
                if 'flex_workflow' in parse_result:
                    flex_dict = parse_result['flex_workflow'].to_dict() if hasattr(parse_result['flex_workflow'], 'to_dict') else parse_result['flex_workflow']
                    DirectoryProcessor.save_flex_document(flex_dict, file_path, flex_output_dir)
                
                results.append({
                    'file': file_path,
                    'framework': source_framework,
                    'status': parse_result['status'],
                    'completion_percentage': parse_result.get('completion_percentage', 0.0)
                })
                
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
            'message': f'Processed {total} files, {completed} parsed successfully to FLEX format'
        }
        
    except Exception as e:
        logger.error(f'Error in parse_to_flex: {str(e)}')
        raise


@mcp.tool(name='generate-from-flex')
async def generate_from_flex(
    directory_path: str = Field(
        ..., description='Path to directory containing FLEX workflow files to generate target jobs from'
    ),
    target_framework: str = Field(
        ..., description='Target framework identifier (airflow, step_functions)'
    ),
    context_file: Optional[str] = Field(
        default=None, description='Path to plain text file containing organizational context'
    ),
    llm_config: Optional[Dict[str, Any]] = Field(
        default=None, description='LLM model configuration (not used in this tool)'
    ),
) -> Dict[str, Any]:
    """Generate target framework jobs from FLEX workflow files in a directory.
    
    Process: Scan Directory → Load FLEX Files → Validate → Generate Target Jobs
    
    ## Usage Examples
    - "Convert FLEX docs in ./flex_output to step_functions"
    - "Generate airflow jobs from FLEX files in /path/to/flex_docs"
    
    ## Output
    Creates directory at the same level as input directory:
    - "output jobs for flex docs in {dir_name}"
    """
    try:
        # Scan directory for FLEX files
        files_and_frameworks = DirectoryProcessor.scan_directory(directory_path)
        flex_files = [(f, fw) for f, fw in files_and_frameworks if fw == 'flex']
        
        if not flex_files:
            return {
                'status': 'error',
                'message': f'No FLEX workflow files detected in directory: {directory_path}'
            }
        
        # Create output directory
        _, jobs_output_dir = DirectoryProcessor.create_output_directories(
            directory_path, 'generate_from_flex'
        )
        
        # Load context document for LLM processing
        context_document = None
        if context_file:
            try:
                with open(context_file, 'r', encoding='utf-8') as f:
                    context_document = f.read().strip()
            except Exception as e:
                logger.warning(f'Could not read context file {context_file}: {str(e)}')
        
        results = []
        
        # Process each FLEX file
        for file_path, _ in flex_files:
            try:
                logger.info(f'Generating {target_framework} from FLEX file: {file_path}')
                
                # Read and parse FLEX file
                with open(file_path, 'r') as f:
                    flex_data = json.load(f)
                
                # Reconstruct and validate FLEX workflow
                workflow = FlexWorkflow.from_dict(flex_data)
                validation_result = _validate_flex_workflow(workflow)
                
                if not validation_result['is_complete']:
                    results.append({
                        'file': file_path,
                        'status': 'incomplete',
                        'missing': validation_result.get('missing_fields', [])
                    })
                    continue
                
                # Generate target format
                generation_result = await _generate_from_flex_workflow(workflow, target_framework, context_document)
                
                # Save target job
                DirectoryProcessor.save_target_job(
                    generation_result['target_config'], file_path, jobs_output_dir, target_framework
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
            'message': f'Processed {total} FLEX files, {completed} generated successfully to {target_framework}'
        }
        
    except Exception as e:
        logger.error(f'Error in generate_from_flex: {str(e)}')
        raise


def main():
    """Run the MCP server with CLI argument support."""
    mcp.run()


if __name__ == '__main__':
    main()