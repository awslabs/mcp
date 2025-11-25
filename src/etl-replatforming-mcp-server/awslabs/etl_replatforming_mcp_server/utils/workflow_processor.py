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

"""Workflow processing utilities to break down long functions."""

from typing import Any, Dict, Optional, Tuple

from loguru import logger

from ..constants import (
    COMPLETENESS_THRESHOLD,
    STATUS_COMPLETE,
    STATUS_INCOMPLETE,
)
from ..models.flex_workflow import FlexWorkflow
from ..validators.workflow_validator import WorkflowValidator


class WorkflowProcessor:
    """Utility class for processing workflows and handling AI enhancement logic."""

    def __init__(self, validator: WorkflowValidator):
        self.validator = validator

    def should_enhance_with_ai(self, flex_workflow: FlexWorkflow) -> bool:
        """Determine if workflow should be enhanced with AI."""
        return flex_workflow.should_trigger_ai_enhancement()

    def calculate_enhancement_improvement(
        self,
        original_workflow: FlexWorkflow,
        enhanced_workflow: FlexWorkflow,
        original_completeness: float,
    ) -> Tuple[bool, float]:
        """Calculate if AI enhancement improved the workflow."""
        enhanced_required_missing = enhanced_workflow.get_missing_fields()
        original_required_missing = original_workflow.get_missing_fields()

        # Get final completeness
        final_completeness = (
            enhanced_workflow.parsing_info.parsing_completeness
            if enhanced_workflow.parsing_info
            else COMPLETENESS_THRESHOLD
        )

        # Check if improvement occurred
        improved = (
            len(enhanced_required_missing) < len(original_required_missing)
            or final_completeness > original_completeness
        )

        return improved, final_completeness

    def log_parsing_results(
        self,
        completeness: float,
        filename: Optional[str] = None,
        stage: str = 'deterministic',
    ) -> None:
        """Log parsing results with consistent formatting."""
        filename_info = f' ({filename})' if filename else ''

        if stage == 'deterministic':
            logger.info(f'Deterministic parsing: {completeness:.1%} complete{filename_info}')
        elif stage == 'ai_enhancement_start':
            logger.info(
                f'Deterministic parsing incomplete - invoking Bedrock AI enhancement{filename_info}'
            )
        elif stage == 'ai_enhancement_success':
            logger.info(f'AI enhancement successful{filename_info}')
        elif stage == 'ai_enhancement_no_improvement':
            logger.warning(f'AI enhancement showed no improvement{filename_info}')
        elif stage == 'ai_enhancement_failed':
            logger.warning(f'AI enhancement failed{filename_info}')
        elif stage == 'complete':
            logger.info(
                f'Deterministic parsing complete - no AI enhancement needed{filename_info}'
            )

    def update_parsing_info_after_enhancement(
        self, workflow: FlexWorkflow, missing_fields: list
    ) -> None:
        """Update parsing info with missing fields for targeted enhancement."""
        if workflow.parsing_info:
            workflow.parsing_info.missing_fields = missing_fields

    def determine_final_status(self, flex_workflow: FlexWorkflow) -> str:
        """Determine final workflow status based on required fields."""
        final_required_missing = flex_workflow.get_missing_fields()
        return STATUS_COMPLETE if len(final_required_missing) == 0 else STATUS_INCOMPLETE

    def prepare_parse_result(
        self,
        status: str,
        flex_workflow: FlexWorkflow,
        validation_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Prepare standardized parse result."""
        return {
            'status': status,
            'flex_workflow': flex_workflow,
            'validation_result': validation_result,
        }
