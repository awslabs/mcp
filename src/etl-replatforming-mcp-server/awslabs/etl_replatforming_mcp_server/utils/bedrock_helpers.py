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

"""Helper utilities for Bedrock service operations."""

from typing import Any, Dict, Optional

from ..constants import (
    CLAUDE_3_5_SONNET_INFERENCE_PROFILE,
    CLAUDE_3_5_SONNET_MODEL_ID,
    CLAUDE_SONNET_4_INFERENCE_PROFILE,
    CLAUDE_SONNET_4_MODEL_ID,
)


class BedrockHelpers:
    """Helper utilities for Bedrock operations."""

    @staticmethod
    def get_inference_profile_model_id(model_id: str) -> str:
        """Get the appropriate inference profile model ID for newer Claude models."""
        model_mapping = {
            CLAUDE_SONNET_4_MODEL_ID: CLAUDE_SONNET_4_INFERENCE_PROFILE,
            CLAUDE_3_5_SONNET_MODEL_ID: CLAUDE_3_5_SONNET_INFERENCE_PROFILE,
        }
        return model_mapping.get(model_id, model_id)

    @staticmethod
    def create_field_prompts(
        source_framework: str, input_code: str, context_document: Optional[str] = None
    ) -> Dict[str, str]:
        """Create targeted prompts for specific field extraction."""
        context_section = ''
        if context_document:
            context_section = f'\n\nOrganizational Context:\n{context_document}\n\nUse this context to make reasonable inferences about missing information.\n'

        return {
            'schedule': f"""Extract schedule/trigger information from this {source_framework} workflow.
Look for cron expressions, rate expressions, or event triggers.
Return only a JSON object with schedule information.{context_section}

Example response:
{{"type": "cron", "expression": "0 9 * * *", "timezone": "UTC"}}

Full {source_framework} Code:
{input_code}

Return only the schedule JSON object:""",
            'error_handling': f"""Extract error handling configuration from this {source_framework} workflow.
Look for retry policies, failure actions, notifications.
Return only a JSON object with error handling.{context_section}

Full {source_framework} Code:
{input_code}

Return only the error_handling JSON object:""",
            'parameters': f"""Extract workflow parameters/variables from this {source_framework} workflow.
Look for input parameters, environment variables, configuration values.
Return only a JSON object with parameters.{context_section}

Full {source_framework} Code:
{input_code}

Return only the parameters JSON object:""",
            'task_commands': f"""Analyze this {source_framework} workflow and enhance any tasks with missing or placeholder commands.

**PRIORITY PATTERNS TO DETECT:**
1. **Dynamic Task Creation**: Functions that create tasks in loops (e.g., create_dynamic_tasks())
   - Look for: for i in range(N): task = PythonOperator(...)
   - Convert to: for_each task type with loop parameters

2. **Missing Commands**: Tasks with empty commands, '?' placeholders, or generic function calls
   - Look for: python_callable missing, bash_command='?', lambda: None
   - Provide meaningful commands based on task context

**DYNAMIC TASK EXAMPLE:**
```python
def create_dynamic_tasks():
    for i in range(3):
        task = PythonOperator(task_id=f'dynamic_task_{{i}}', python_callable=lambda: print(f"Processing batch {{i}}"))
```
**Should become:**
{{"enhanced_tasks": [{{"task_id": "dynamic_tasks", "type": "for_each", "command": "print(f'Processing batch {{i}}')", "parameters": {{"loop_type": "range", "start": 0, "end": 3, "loop_var": "i", "task_template": "dynamic_task_{{i}}"}}, "confidence": 0.9}}]}}

{context_section}

Full {source_framework} Code:
{input_code}

Return enhanced tasks JSON with both missing commands AND detected dynamic patterns:""",
        }

    @staticmethod
    def calculate_field_confidence(response: str, field_name: str, field_value: Any) -> float:
        """Calculate confidence score for a specific field based on response quality."""
        from ..constants import (
            BASE_CONFIDENCE,
            CONFIDENCE_BONUS_COMPLETE_RESPONSE,
            CONFIDENCE_BONUS_DYNAMIC_DETECTION,
            CONFIDENCE_BONUS_FIELD_SPECIFIC,
            MAX_CONFIDENCE,
            MIN_RESPONSE_LENGTH_FOR_BONUS,
            TASK_TYPE_FOR_EACH,
        )

        confidence = BASE_CONFIDENCE

        # Increase confidence for complete responses
        if len(response) > MIN_RESPONSE_LENGTH_FOR_BONUS:
            confidence += CONFIDENCE_BONUS_COMPLETE_RESPONSE

        # Field-specific validation
        if field_name == 'schedule':
            if field_value.get('type') and field_value.get('expression'):
                confidence += CONFIDENCE_BONUS_FIELD_SPECIFIC
        elif field_name == 'error_handling':
            if field_value.get('on_failure'):
                confidence += CONFIDENCE_BONUS_FIELD_SPECIFIC
        elif field_name == 'parameters':
            if isinstance(field_value, dict) and field_value:
                confidence += CONFIDENCE_BONUS_FIELD_SPECIFIC
        elif field_name == 'task_commands':
            enhanced_tasks = field_value.get('enhanced_tasks', [])
            if enhanced_tasks and all('task_id' in t and 'command' in t for t in enhanced_tasks):
                confidence += CONFIDENCE_BONUS_FIELD_SPECIFIC
                # Extra confidence for dynamic task detection
                dynamic_tasks = [t for t in enhanced_tasks if t.get('type') == TASK_TYPE_FOR_EACH]
                if dynamic_tasks:
                    confidence += CONFIDENCE_BONUS_DYNAMIC_DETECTION

        return min(confidence, MAX_CONFIDENCE)
