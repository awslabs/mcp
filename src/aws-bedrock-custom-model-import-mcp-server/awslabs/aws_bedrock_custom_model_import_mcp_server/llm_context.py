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

"""LLM context builder for Bedrock Custom Model Import MCP Server."""

from awslabs.aws_bedrock_custom_model_import_mcp_server.models import (
    ImportedModel,
    JobStatus,
    ListImportedModelsResponse,
    ListModelImportJobsResponse,
    ModelImportJob,
)
from typing import Any, Dict


def build_list_model_import_jobs_context(response: ListModelImportJobsResponse) -> str:
    """Provide LLM context for model import jobs.

    Args:
        response: The list model import jobs response

    Returns:
        str: Markdown-formatted context for the LLM
    """
    context = {}

    # Add Bedrock knowledge
    context['bedrock_knowledge'] = build_bedrock_knowledge()

    # Add model import knowledge
    context['model_import_knowledge'] = build_model_import_knowledge()

    # Add job-specific guidance
    context['job_guidance'] = {
        'job_status': 'The status of a model import job can be InProgress, Completed, or Failed. '
        'A job in the InProgress state is still being processed. A job in the Completed state has '
        'successfully imported the model. A job in the Failed state encountered an error during import.',
        'job_naming': 'Job names are automatically appended with a timestamp to ensure uniqueness. '
        'The original job name is preserved in the job metadata.',
        'job_filtering': 'You can filter jobs by status, creation time, or name. This is useful for '
        'finding specific jobs in a large list.',
        'job_monitoring': 'You can monitor job progress by periodically checking its status.',
    }

    return dict_to_markdown(context)


def build_list_imported_models_context(response: ListImportedModelsResponse) -> str:
    """Provide LLM context for imported models.

    Args:
        response: The list imported models response

    Returns:
        str: Markdown-formatted context for the LLM
    """
    context = {}

    # Add Bedrock knowledge
    context['bedrock_knowledge'] = build_bedrock_knowledge()

    # Add model import knowledge
    context['model_import_knowledge'] = build_model_import_knowledge()

    # Add model-specific guidance
    context['model_guidance'] = {
        'model_usage': 'Imported models can be used for inference through the Bedrock runtime API. '
        'Each model has a unique ARN that can be used to reference it in API calls.',
        'model_architecture': 'The model architecture indicates the underlying framework and structure '
        'of the model. This affects the types of inputs and outputs the model supports.',
        'instruct_support': 'Models with instruct support can be used with the Converse API. '
        'Models without instruct support can only be used with the InvokeModel API both streaming and non-streaming.',
        'model_management': 'You can manage imported models through the Bedrock console or API.',
    }

    return dict_to_markdown(context)


def build_model_import_job_details_context(job: ModelImportJob) -> str:
    """Provide LLM context for model import job details.

    Args:
        job: The model import job details

    Returns:
        str: Markdown-formatted context for the LLM
    """
    context = {}

    # Add Bedrock knowledge
    context['bedrock_knowledge'] = build_bedrock_knowledge()

    # Add model import knowledge
    context['model_import_knowledge'] = build_model_import_knowledge()

    # Add job-specific guidance
    context['job_guidance'] = {
        'job_status': 'The status of a model import job can be InProgress, Completed, or Failed. '
        'A job in the InProgress state is still being processed. A job in the Completed state has '
        'successfully imported the model. A job in the Failed state encountered an error during import.',
        'model_data_source': 'The model data source specifies where the model artifacts are stored. '
        'This is typically an S3 bucket and key.',
        'role_arn': 'The IAM role ARN used for the import job. This role must have permissions to '
        'access the model data source and create resources in Bedrock.',
    }

    # Add status-specific guidance
    status = job.status
    if status == JobStatus.IN_PROGRESS:
        context['status_guidance'] = {
            'monitoring': 'The job is still in progress. You can monitor its status by periodically '
            'calling the GetModelImportJob API.',
            'duration': 'Model import jobs can take several hours to complete, depending on the size '
            'of the model and the current service load.',
        }
    elif status == JobStatus.COMPLETED:
        context['status_guidance'] = {
            'next_steps': 'The model has been successfully imported and is ready to use. You can now '
            'use the model for inference through the Bedrock runtime API.',
            'model_access': f'The imported model can be accessed using the ARN: {job.imported_model_arn}',
        }
    elif status == JobStatus.FAILED:
        context['status_guidance'] = {
            'troubleshooting': 'The job failed to import the model. Check the failure message for details '
            'on what went wrong.',
            'common_issues': 'Common issues include insufficient permissions, invalid model format, or '
            'problems with the model data source.',
        }

    return dict_to_markdown(context)


def build_imported_model_details_context(model: ImportedModel) -> str:
    """Provide LLM context for imported model details.

    Args:
        model: The imported model details

    Returns:
        str: Markdown-formatted context for the LLM
    """
    context = {}

    # Add Bedrock knowledge
    context['bedrock_knowledge'] = build_bedrock_knowledge()

    # Add model import knowledge
    context['model_import_knowledge'] = build_model_import_knowledge()

    # Add model-specific guidance
    context['model_guidance'] = build_model_guidance(model)

    return dict_to_markdown(context)


def build_bedrock_knowledge() -> Dict[str, str]:
    """Provide general Bedrock knowledge.

    Returns:
        Dict[str, str]: General knowledge about Amazon Bedrock
    """
    knowledge = {
        'service_description': 'Amazon Bedrock is a fully managed service that offers a choice of high-performing '
        'foundation models (FMs) from leading AI companies like AI21 Labs, Anthropic, Cohere, Meta, Stability AI, '
        'and Amazon via a single API, along with a broad set of capabilities you need to build generative AI '
        'applications with security, privacy, and responsible AI.',
        'custom_models': 'Amazon Bedrock allows you to import custom models, which can be fine-tuned versions of '
        'foundation models or completely custom models built using compatible frameworks.',
    }

    return knowledge


def build_model_import_knowledge() -> Dict[str, str]:
    """Provide knowledge about model importing in Bedrock.

    Returns:
        Dict[str, str]: Knowledge about model importing in Bedrock
    """
    knowledge = {
        'import_process': 'Importing a model into Amazon Bedrock involves creating a model import job, which '
        "copies the model artifacts from a source location (typically an S3 bucket) into Bedrock's managed "
        'infrastructure.',
        'supported_formats': 'Amazon Bedrock supports importing models in Huggingface .safetensors format.',
        'permissions': 'To import a model, you need an IAM role with permissions to access the source data '
        'and create resources in Bedrock. The role is specified when creating the import job.',
    }

    return knowledge


def build_model_guidance(model: ImportedModel) -> Dict[str, str]:
    """Provide guidance on imported model in Bedrock.

    Returns:
        Dict[str, str]: Guidance on model in Bedrock
    """
    guidance = {
        'model_usage': 'Imported models can be used for inference through the Bedrock runtime API. '
        'Each model has a unique ARN that can be used to reference it in API calls.',
        'model_architecture': f'This model uses the {model.model_architecture} architecture. '
        'This affects the types of inputs and outputs the model supports.',
        'instruct_support': 'Models with instruct support can be used with the Converse API. '
        'Models without instruct support can only be used with the InvokeModel API both streaming and non-streaming.',
        'billing': 'Amazon Bedrock Custom Model Import does not incur a direct fee for the import '
        'process itself. However, once a custom model is imported and activated, billing is based on '
        'its usage for inference. The primary cost component is the number of active copies of your '
        'custom model and the duration for which these copies are active to serve inference requests. '
        'This is measured in Custom Model Units (CMUs), and you are billed based on the number of CMUs per minute, '
        'typically in 5-minute increments.',
        'architecture_guidance': f'Models with the {model.model_architecture} architecture may require '
        'specific inference parameters. Consult the [Bedrock documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters.html) for details.',
    }

    return guidance


def dict_to_markdown(data: Dict[str, Any], level: int = 0) -> str:
    """Convert a nested dictionary to a well-formatted Markdown string.

    Args:
        data: The dictionary to format
        level: The current nesting level (used for recursion)

    Returns:
        A formatted Markdown string
    """
    result = []

    # Process each key-value pair
    for key, value in data.items():
        # Format the key as a header (with appropriate level)
        # Convert snake_case to Title Case
        header_text = key.replace('_', ' ').title()
        header_level = min(level + 2, 6)  # H2 to H6 (avoid going beyond H6)
        header = '#' * header_level + ' ' + header_text

        # Process the value based on its type
        if isinstance(value, dict):
            # Recursively format nested dictionaries
            result.append(f'\n{header}\n')
            result.append(dict_to_markdown(value, level + 1))
        elif isinstance(value, (list, tuple)):
            # Format lists as bullet points
            result.append(f'\n{header}\n')
            for item in value:
                if isinstance(item, dict):
                    result.append(dict_to_markdown(item, level + 1))
                else:
                    result.append(f'- {item}\n')
        elif isinstance(value, bool):
            # Format booleans
            result.append(f'\n{header}: {"Yes" if value else "No"}\n')
        else:
            # Format strings and other types
            result.append(f'\n{header}\n\n{value}\n')

    return '\n'.join(result)
