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

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..models.flex_workflow import (
    ErrorHandling,
    FlexWorkflow,
    Schedule,
    Task,
)
from ..models.llm_config import LLMConfig


class BaseGenerator(ABC):
    """Abstract base class for all workflow generators

    ALL METHODS REQUIRED to ensure complete, consistent generation:
    - generate(): Main entry point (used by server)
    - get_supported_task_types(): Task type compatibility
    - supports_feature(): Feature support validation
    - generate_metadata(): Workflow metadata
    - generate_schedule(): Scheduling configuration
    - generate_task(): Individual task generation
    - generate_dependencies(): Task dependencies
    - generate_error_handling(): Error handling policies
    - generate_conditional_logic(): Branch/choice logic
    - generate_loop_logic(): Loop/iteration patterns
    - generate_parallel_execution(): Parallel execution
    - format_output(): Output formatting
    - validate_generated_output(): Output validation
    """

    def __init__(self, llm_config: Optional[LLMConfig] = None):
        self.llm_config = llm_config

    @abstractmethod
    def generate(
        self,
        workflow: FlexWorkflow,
        context_document: Optional[str] = None,
        llm_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate complete workflow for target framework

        This is the main entry point used by the server.
        Must return dict with framework-specific output and metadata.
        """
        pass

    # All methods required for complete generation
    @abstractmethod
    def get_supported_task_types(self) -> List[str]:
        """Get list of task types supported by this generator"""
        pass

    @abstractmethod
    def supports_feature(self, feature: str) -> bool:
        """Check if generator supports specific FLEX feature"""
        pass

    @abstractmethod
    def generate_metadata(self, workflow: FlexWorkflow) -> Dict[str, Any]:
        """Generate workflow metadata (name, description, tags)"""
        pass

    @abstractmethod
    def generate_schedule(self, schedule: Schedule) -> Any:
        """Generate scheduling configuration (return None if not supported)"""
        pass

    @abstractmethod
    def generate_task(self, task: Task, workflow: FlexWorkflow) -> Any:
        """Generate individual task definition"""
        pass

    @abstractmethod
    def generate_dependencies(self, tasks: List[Task]) -> Any:
        """Generate task dependencies"""
        pass

    @abstractmethod
    def generate_error_handling(self, error_handling: ErrorHandling) -> Any:
        """Generate error handling configuration (return None if not available)"""
        pass

    @abstractmethod
    def generate_conditional_logic(self, task: Task, workflow: FlexWorkflow) -> Any:
        """Generate branch/choice logic (return None if not supported)"""
        pass

    @abstractmethod
    def generate_loop_logic(self, task: Task, workflow: FlexWorkflow) -> Any:
        """Generate loop/iteration logic (return None if not supported)"""
        pass

    @abstractmethod
    def generate_parallel_execution(self, tasks: List[Task], workflow: FlexWorkflow) -> Any:
        """Generate parallel execution patterns (return None if not supported)"""
        pass

    @abstractmethod
    def format_output(self, generated_content: Any, workflow: FlexWorkflow) -> Dict[str, Any]:
        """Format generated content into standard output structure"""
        pass

    @abstractmethod
    def validate_generated_output(self, output: Dict[str, Any]) -> bool:
        """Validate generated output before returning"""
        pass

    # Optional methods for enhanced orchestration features
    def generate_task_groups(self, workflow: FlexWorkflow) -> Any:
        """Generate task groups/logical organization (optional)

        Override this method if the target framework supports task grouping.
        Default implementation returns None (no grouping).
        """
        return None

    def generate_connections(self, workflow: FlexWorkflow) -> Any:
        """Generate connection configurations (optional)

        Override this method if the target framework needs explicit connections.
        Default implementation returns None (connections handled elsewhere).
        """
        return None

    def generate_enhanced_schedule(self, workflow: FlexWorkflow) -> Any:
        """Generate enhanced scheduling with data triggers (optional)

        Override this method if the target framework supports data/event triggers.
        Default implementation falls back to basic schedule generation.
        """
        if workflow.schedule:
            return self.generate_schedule(workflow.schedule)
        return None

    def generate_monitoring_config(self, workflow: FlexWorkflow) -> Any:
        """Generate monitoring and metrics configuration (optional)

        Override this method if the target framework supports custom metrics.
        Default implementation returns None (no custom monitoring).
        """
        return None

    def use_enhanced_features(self, workflow: FlexWorkflow) -> bool:
        """Check if workflow has enhanced features that can be used

        Generators can use this to conditionally enable enhanced generation.
        """
        return (
            bool(workflow.task_groups)
            or bool(workflow.connections)
            or (workflow.schedule and bool(workflow.schedule.data_triggers))
            or any(task.monitoring_metrics for task in workflow.tasks)
        )
