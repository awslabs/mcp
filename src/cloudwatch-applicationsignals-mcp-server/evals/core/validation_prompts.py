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

"""LLM-as-a-Judge validation prompts.

PROMPT QUALITY CHECKLIST
========================
Use this checklist to evaluate whether prompts follow LLM-as-a-Judge best practices:

1. Binary/low-precision scoring: Use PASS/FAIL or 3-point scales (not 1-100)
2. Structured output format: Specify exact format for easy parsing
3. Split by task type: Separate prompts for different evaluation types
4. Per-criterion evaluation: Each rubric item gets individual judgment
5. Clear score definitions: Explain what PASS/FAIL means
6. Request reasoning: Ask for justification with each verdict
7. Low temperature: Use 0.0 or close for consistency (configured in eval_config.py)
8. Capable model: Use strong models for better human alignment (configured in eval_config.py)

Ref: https://www.evidentlyai.com/llm-guide/llm-as-a-judge
"""

from enum import Enum


CODE_MODIFICATION_VALIDATION_PROMPT = """You are evaluating code changes for a software modification task.

**Validation Rubric:**
{rubric_items}

{captured_data}

Instructions:
For each criterion in the rubric, evaluate whether it is satisfied by the changes and captured data.

Respond in this EXACT format:
1. [PASS/FAIL] Brief reasoning (1 sentence)
2. [PASS/FAIL] Brief reasoning (1 sentence)
... (continue for all {num_criteria} criteria)

Be strict but fair. Only mark as PASS if the criterion is clearly met."""

DATA_INTERPRETATION_VALIDATION_PROMPT = """You are evaluating an agent's data interpretation and analysis task.

**Validation Rubric:**
{rubric_items}

{captured_data}

Instructions:
For each criterion in the rubric, evaluate whether the agent's response correctly addresses it.

Respond in this EXACT format:
1. [PASS/FAIL] Brief reasoning (1 sentence)
2. [PASS/FAIL] Brief reasoning (1 sentence)
... (continue for all {num_criteria} criteria)

Be strict but fair. Only mark as PASS if the agent's answer is accurate and complete."""

WORKFLOW_VALIDATION_PROMPT = """You are evaluating whether an agent followed the correct workflow and tool usage.

**Validation Rubric:**
{rubric_items}

{captured_data}

Instructions:
For each criterion in the rubric, evaluate whether the agent's tool usage and workflow meets it.

Respond in this EXACT format:
1. [PASS/FAIL] Brief reasoning (1 sentence)
2. [PASS/FAIL] Brief reasoning (1 sentence)
... (continue for all {num_criteria} criteria)

Be strict but fair. Only mark as PASS if the criterion is clearly met."""


class ValidationPromptType(Enum):
    """Well-defined validation prompt templates that produce parseable output.

    All templates produce responses in the format:
    1. [PASS/FAIL] Brief reasoning
    2. [PASS/FAIL] Brief reasoning
    ...
    """

    CODE_MODIFICATION = CODE_MODIFICATION_VALIDATION_PROMPT
    DATA_INTERPRETATION = DATA_INTERPRETATION_VALIDATION_PROMPT
    WORKFLOW = WORKFLOW_VALIDATION_PROMPT

    def format(self, rubric_items: str, captured_data: str, num_criteria: int) -> str:
        r"""Format the prompt template with validation parameters.

        Args:
            rubric_items: Formatted rubric criteria (e.g., "1. Criterion 1\n2. Criterion 2")
            captured_data: Formatted captured data (git diff, tool calls, response, etc.)
            num_criteria: Number of criteria in the rubric

        Returns:
            Formatted prompt string ready for LLM
        """
        return self.value.format(
            rubric_items=rubric_items,
            captured_data=captured_data,
            num_criteria=num_criteria,
        )
