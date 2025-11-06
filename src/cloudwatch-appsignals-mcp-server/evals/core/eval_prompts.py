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

Best practices: https://www.evidentlyai.com/llm-guide/llm-as-a-judge
"""

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
