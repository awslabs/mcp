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


"""Response formatting service for user interactions."""

import os
from typing import Any, Dict, Optional

from ..models.flex_workflow import FlexWorkflow


class ResponseFormatter:
    """Service for formatting responses and user prompts."""

    @staticmethod
    def prompt_user_for_missing(
        flex_workflow: FlexWorkflow,
        validation_result: Dict[str, Any],
        target_framework: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate response with FLEX document containing '?' placeholders for missing fields."""

        missing_fields = validation_result.get('missing_fields', [])

        # Create FLEX document with question mark placeholders (target-aware)
        flex_with_placeholders = flex_workflow.to_dict_with_placeholders(
            missing_fields, target_framework
        )

        # Build missing information message with cron-specific guidance
        missing_info = []
        for field in missing_fields:
            if field == 'schedule_configuration':
                missing_info.append(
                    "• Schedule: Replace '?' with cron expression (e.g., '0 9 * * *' for daily at 9 AM, '0 */6 * * *' for every 6 hours)"
                )
            elif field.startswith('task_') and field.endswith('_execution_details'):
                task_id = field.split('_')[1]
                missing_info.append(
                    f"• Task '{task_id}': Replace '?' in command field with execution script or SQL query"
                )
            elif field.startswith('task_') and field.endswith('_sql_query'):
                task_id = field.split('_')[1]
                missing_info.append(
                    f"• Task '{task_id}': Replace '?' in command field with SQL query"
                )
            else:
                missing_info.append(
                    f"• {field.replace('_', ' ').title()}: Replace '?' with appropriate value"
                )

        missing_text = '\n'.join(missing_info) if missing_info else 'No missing fields identified.'

        # Check if Bedrock enhancement was attempted
        bedrock_warning = ResponseFormatter._check_bedrock_availability()

        return {
            'status': 'incomplete',
            'flex_workflow': flex_with_placeholders,
            'completion_percentage': validation_result['completion_percentage'],
            'missing_information': missing_text,
            'message': f'Workflow conversion is {validation_result["completion_percentage"]:.0%} complete.\n\n{missing_text}{bedrock_warning}\n\n📋 **Next Steps:**\n1. Replace all "?" placeholders in the FLEX document\n2. Check FLEX_SPECIFICATION.md for:\n   • **Framework Mapping Table**: Shows how FLEX elements map to Airflow, Step Functions, and Azure Data Factory\n   • Task type conversions for {target_framework or "your target framework"}\n   • Field requirements and examples\n   • Default values for optional fields\n3. Resubmit the updated FLEX document',
            'instructions': 'Check FLEX_SPECIFICATION.md for field requirements. Only required fields (marked with ✅) need to be provided.',
        }

    @staticmethod
    def format_parse_response(parse_result: Dict[str, Any]) -> Dict[str, Any]:
        """Format response for parse-to-flex tool."""
        return {
            'status': 'complete',
            'flex_workflow': parse_result['flex_workflow'],
            'validation': parse_result['validation_result'],
            'completion_percentage': 1.0,
            'message': 'FLEX workflow generated successfully.',
        }

    @staticmethod
    def _check_bedrock_availability() -> str:
        """Check if Bedrock enhancement was attempted."""
        try:
            import boto3

            boto3.client('bedrock-runtime', region_name=os.getenv('AWS_REGION', 'us-east-1'))
            return ''
        except Exception as e:
            if 'Unable to locate credentials' in str(e):
                return '\n\n⚠️ AWS credentials not configured. AI enhancement disabled.'
            elif 'AccessDeniedException' in str(e):
                return '\n\n⚠️ Bedrock access denied. AI enhancement disabled.'
            else:
                return '\n\n⚠️ Bedrock unavailable. AI enhancement disabled.'
