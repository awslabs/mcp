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

"""Step Functions parser for converting to FLEX workflow format."""

import json
from typing import Dict, Any
from ..models.flex_workflow import FlexWorkflow, Task, Schedule, TaskDependency
from ..models.exceptions import ParsingError
from .base_parser import WorkflowParser


class StepFunctionsParser(WorkflowParser):
    """Parser to convert Step Functions state machines to FLEX workflow format"""
    
    @property
    def framework_name(self) -> str:
        return "step_functions"
    
    def can_parse(self, source_data: Dict[str, Any]) -> bool:
        """Check if source data is valid Step Functions format"""
        return "States" in source_data and "StartAt" in source_data
    
    def parse(self, source_data: Dict[str, Any]) -> FlexWorkflow:
        """Parse Step Functions state machine to FLEX workflow"""
        if not self.can_parse(source_data):
            raise ParsingError("Invalid Step Functions format", {"source_data": source_data})
        
        return self._parse_state_machine(source_data)
    
    def parse_code(self, input_code: str) -> FlexWorkflow:
        """Parse raw Step Functions JSON to FLEX workflow
        
        Intelligently extracts Step Functions components from raw JSON input.
        
        Args:
            input_code: Raw Step Functions JSON string
            
        Returns:
            FlexWorkflow with parsed state machine information
        """
        try:
            # Parse JSON
            state_machine = json.loads(input_code)
            return self._parse_state_machine(state_machine)
            
        except json.JSONDecodeError as e:
            raise ParsingError(f"Invalid JSON format: {str(e)}", {"input_code": input_code[:200]})
    
    def _parse_state_machine(self, source_data: Dict[str, Any]) -> FlexWorkflow:
        """Parse Step Functions state machine data"""
        name = source_data.get("Comment", "step_functions_workflow")
        states = source_data.get("States", {})
        start_at = source_data.get("StartAt")
        
        # First, extract all states including parallel branches
        all_states = self._extract_all_states(states)
        
        # Convert states to tasks with dependencies
        tasks = []
        
        for state_name, state_def in all_states.items():
            task = self._convert_state_to_task(state_name, state_def, all_states)
            if task:
                tasks.append(task)
        
        return FlexWorkflow(
            name=name.replace(" ", "_").lower(),
            description=source_data.get("Comment"),
            tasks=tasks,
            metadata={
                "created_from": "step_functions"
            }
        )
    
    def _extract_all_states(self, states: Dict[str, Any]) -> Dict[str, Any]:
        """Extract all states including those in parallel branches"""
        all_states = {}
        
        for state_name, state_def in states.items():
            if state_def.get("Type") == "Parallel":
                # Add the parallel state itself
                all_states[state_name] = state_def
                
                # Extract states from each branch
                branches = state_def.get("Branches", [])
                for i, branch in enumerate(branches):
                    branch_states = branch.get("States", {})
                    for branch_state_name, branch_state_def in branch_states.items():
                        # Use original state name, but ensure uniqueness
                        unique_name = branch_state_name
                        counter = 1
                        while unique_name in all_states:
                            unique_name = f"{branch_state_name}_{counter}"
                            counter += 1
                        all_states[unique_name] = branch_state_def
            else:
                all_states[state_name] = state_def
        
        return all_states
    
    def _convert_state_to_task(self, state_name: str, state_def: Dict[str, Any], all_states: Dict[str, Any]) -> Task:
        """Convert Step Functions state to generic FLEX task"""
        state_type = state_def.get("Type")
        
        if state_type == "Task":
            resource = state_def.get("Resource", "")
            parameters = state_def.get("Parameters", {})
            
            # Map AWS resources to generic task types
            if "redshiftdata:executeStatement" in resource:
                task_type = "sql"
                command = parameters.get("Sql", "")
            elif "lambda:invoke" in resource:
                task_type = "python"
                command = f"invoke_function({parameters.get('FunctionName', 'unknown')})"
            elif "batch:submitJob" in resource:
                task_type = "container"
                command = f"run_batch_job({parameters.get('JobDefinition', 'unknown')})"
            elif "sns:publish" in resource:
                task_type = "email"
                command = f"send_notification('{parameters.get('Message', 'notification')}')"
            elif "s3:" in resource:
                task_type = "file_transfer"
                command = "s3_operation"
            else:
                task_type = "bash"
                command = "generic_aws_service_call"
            
            # Extract retry configuration
            retry_config = state_def.get("Retry", [])
            retries = retry_config[0].get("MaxAttempts", 0) if retry_config else 0
            retry_delay = retry_config[0].get("IntervalSeconds", 300) if retry_config else 300
            
            # Find dependencies (states that have Next pointing to this state)
            depends_on = []
            for other_state_name, other_state_def in all_states.items():
                if other_state_def.get("Next") == state_name:
                    depends_on.append(TaskDependency(
                        task_id=other_state_name,
                        condition="success"
                    ))
            
            return Task(
                id=state_name,
                name=state_name.replace("_", " ").title(),
                type=task_type,
                command=command,
                timeout=state_def.get("TimeoutSeconds"),
                retries=retries,
                retry_delay=retry_delay,
                depends_on=depends_on
            )
        
        elif state_type == "Parallel":
            # Handle Parallel state by creating a placeholder task
            # The actual parallel tasks will be extracted from branches
            depends_on = []
            for other_state_name, other_state_def in all_states.items():
                if other_state_def.get("Next") == state_name:
                    depends_on.append(TaskDependency(
                        task_id=other_state_name,
                        condition="success"
                    ))
            
            return Task(
                id=state_name,
                name=state_name.replace("_", " ").title(),
                type="bash",
                command="echo 'Parallel execution container'",
                depends_on=depends_on
            )
        
        elif state_type == "Pass":
            # Find dependencies for Pass state
            depends_on = []
            for other_state_name, other_state_def in all_states.items():
                if other_state_def.get("Next") == state_name:
                    depends_on.append(TaskDependency(
                        task_id=other_state_name,
                        condition="success"
                    ))
            
            return Task(
                id=state_name,
                name=state_name.replace("_", " ").title(),
                type="bash",
                command="echo 'Pass state - no operation'",
                depends_on=depends_on
            )
        
        return None