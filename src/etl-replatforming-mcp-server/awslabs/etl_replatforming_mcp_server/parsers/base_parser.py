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
    TaskDependency,
    TaskGroup,
    TaskLoop,
    TriggerConfig,
)


class WorkflowParser(ABC):
    """Abstract base class for workflow parsers

    ALL METHODS REQUIRED to ensure complete, consistent parsing:
    - parse_code(): Main entry point (used by server)
    - detect_framework(): Framework identification
    - parse_metadata(): Workflow name, description, tags
    - parse_tasks(): All tasks with types, commands, parameters
    - parse_schedule(): Scheduling (return None if not available)
    - parse_error_handling(): Error policies (return None if not available)
    - parse_dependencies(): Task execution order
    - parse_loops(): Loop constructs (return empty dict if none)
    - parse_conditional_logic(): Branch logic (return empty list if none)
    - parse_parallel_execution(): Parallel patterns (return empty list if none)
    - validate_input(): Input format validation
    - get_parsing_completeness(): Quality metrics (should return >= 0.8)
    """

    @abstractmethod
    def parse_code(self, input_code: str) -> FlexWorkflow:
        """Parse raw input code to FLEX workflow format

        This is the main entry point used by the server.
        Must return complete FlexWorkflow with parsing_info populated.
        """
        pass

    # All methods required for complete parsing
    @abstractmethod
    def detect_framework(self, input_code: str) -> bool:
        """Detect if input code matches this parser's framework"""
        pass

    @abstractmethod
    def parse_metadata(self, source_data: Any) -> Dict[str, Any]:
        """Extract workflow metadata (name, description, tags)"""
        pass

    @abstractmethod
    def parse_tasks(self, source_data: Any) -> List[Task]:
        """Extract tasks from source data"""
        pass

    @abstractmethod
    def parse_schedule(self, source_data: Any) -> Optional[Schedule]:
        """Extract schedule from source data (return None if not available)"""
        pass

    @abstractmethod
    def parse_error_handling(self, source_data: Any) -> Optional[ErrorHandling]:
        """Extract error handling from source data (return None if not available)"""
        pass

    @abstractmethod
    def parse_dependencies(self, source_data: Any) -> List[TaskDependency]:
        """Extract dependencies from source data"""
        pass

    @abstractmethod
    def parse_loops(self, source_data: Any) -> Dict[str, TaskLoop]:
        """Extract loops from source data (return empty dict if none)"""
        pass

    @abstractmethod
    def parse_conditional_logic(self, source_data: Any) -> List[Task]:
        """Extract branch/choice tasks from source data (return empty list if none)"""
        pass

    @abstractmethod
    def parse_parallel_execution(self, source_data: Any) -> List[Task]:
        """Extract parallel execution patterns (return empty list if none)"""
        pass

    @abstractmethod
    def validate_input(self, input_code: str) -> bool:
        """Validate input code format before parsing"""
        pass

    @abstractmethod
    def get_parsing_completeness(self, flex_workflow: FlexWorkflow) -> float:
        """Calculate parsing completeness percentage (0.0-1.0)"""
        pass

    # New methods for enhanced orchestration features
    @abstractmethod
    def parse_task_groups(self, source_data: Any) -> List[TaskGroup]:
        """Extract task groups/logical groupings (return empty list if none)"""
        pass

    @abstractmethod
    def parse_connections(self, source_data: Any) -> Dict[str, str]:
        """Extract connection references (return empty dict if none)"""
        pass

    @abstractmethod
    def parse_trigger_rules(self, source_data: Any) -> Dict[str, str]:
        """Extract task trigger rules (return empty dict if none)"""
        pass

    @abstractmethod
    def parse_data_triggers(self, source_data: Any) -> List[TriggerConfig]:
        """Extract data availability triggers (return empty list if none)"""
        pass
