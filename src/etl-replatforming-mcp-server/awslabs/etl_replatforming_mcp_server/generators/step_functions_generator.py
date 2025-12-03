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

from typing import Any, Dict, List, Optional, Union

from ..models.flex_workflow import FlexWorkflow
from .base_generator import BaseGenerator


class StepFunctionsGenerator(BaseGenerator):
    """Generator to convert FLEX workflow to AWS Step Functions format"""

    def generate(
        self,
        workflow: Union[FlexWorkflow, Dict[str, Any]],
        context_document: Optional[str] = None,
        llm_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Convert FLEX workflow to Step Functions state machine definition"""
        # Convert dict to FlexWorkflow if needed
        if isinstance(workflow, dict):
            workflow = FlexWorkflow.from_dict(workflow)

        state_machine = self._generate_state_machine(workflow)
        workflow_name = f'etl-{workflow.name}'

        result = {
            'state_machine_definition': state_machine,
            'state_machine_name': workflow_name,
            'execution_role': f'arn:aws:iam::{{account_id}}:role/{workflow_name}-execution-role',
            'framework': 'step_functions',
        }

        # Include Python files from FLEX metadata
        python_files = workflow.metadata.get('python_files', {})
        if python_files:
            result['python_files'] = python_files

        return result

    def _generate_state_machine(self, workflow: FlexWorkflow) -> Dict[str, Any]:
        """Generate Step Functions state machine using demand-driven approach"""
        states = {}
        start_task_id = self._find_start_state(workflow)
        self._create_task_chain(start_task_id, workflow, states)

        return {
            'Comment': workflow.description or f'Generated from FLEX workflow: {workflow.name}',
            'StartAt': start_task_id,
            'States': states,
        }

    def _create_task_chain(self, task_id: str, workflow: FlexWorkflow, states: Dict[str, Any]):
        """Create task and its chain using demand-driven approach"""
        if task_id in states:
            return  # Already created

        # Find task in FLEX
        task = self._find_task_in_flex(task_id, workflow)
        if not task:
            # Cannot create task chain for missing task
            return

        # Create task state
        states[task_id] = self._generate_task_state(task, workflow)

        # Get children tasks
        children = self._get_children_tasks(task_id, workflow)

        # Special handling for branch tasks
        if task.type == 'branch':
            # Create all branch target states
            for child_id in children:
                self._create_task_chain(child_id, workflow, states)
            # Add retry loop logic for branch tasks
            self._add_retry_loop_logic(task_id, workflow, states)
            return

        # Check if this task should loop back (retry pattern)
        loop_back_target = self._find_retry_loop_target(task_id, workflow)
        if loop_back_target:
            states[task_id]['Next'] = loop_back_target
            return

        if len(children) == 0:
            # No children - end workflow
            states[task_id]['End'] = True
        elif len(children) == 1:
            # Single child - simple transition
            states[task_id]['Next'] = children[0]
            self._create_task_chain(children[0], workflow, states)
        else:
            # Multiple children - create parallel state
            convergence = self._find_convergence_point(children, workflow)
            if convergence:
                # Create convergence task first
                self._create_task_chain(convergence, workflow, states)

            # Create parallel state
            parallel_id = f'{task_id}_parallel'
            self._create_parallel_with_chains(parallel_id, children, convergence, workflow, states)
            states[task_id]['Next'] = parallel_id

    def _create_parallel_with_chains(
        self,
        parallel_id: str,
        children: list,
        convergence: Optional[str],
        workflow: FlexWorkflow,
        states: Dict[str, Any],
    ):
        """Create parallel state with complete chains for each branch"""
        branches = []

        for child_id in children:
            # Build complete chain for this branch
            branch_states = {}
            self._build_branch_chain(child_id, convergence, workflow, branch_states)
            branches.append({'StartAt': child_id, 'States': branch_states})

        # Create parallel state
        parallel_state = {'Type': 'Parallel', 'Branches': branches}
        if convergence:
            parallel_state['Next'] = convergence
        else:
            parallel_state['End'] = True

        states[parallel_id] = parallel_state

    def _build_branch_chain(
        self,
        start_task_id: str,
        convergence: Optional[str],
        workflow: FlexWorkflow,
        branch_states: Dict[str, Any],
    ):
        """Build complete execution chain for a parallel branch"""
        current_task_id = start_task_id

        while current_task_id and current_task_id != convergence:
            # Find task in FLEX
            task = self._find_task_in_flex(current_task_id, workflow)
            if not task:
                # Cannot build branch chain for missing task
                break

            # Create task state for branch
            branch_states[current_task_id] = self._generate_task_state(task, workflow)

            # Get children of current task
            children = self._get_children_tasks(current_task_id, workflow)

            if len(children) == 0 or current_task_id == convergence:
                # End of chain
                branch_states[current_task_id]['End'] = True
                break
            elif len(children) == 1 and children[0] != convergence:
                # Continue chain
                branch_states[current_task_id]['Next'] = children[0]
                current_task_id = children[0]
            else:
                # Multiple children or reached convergence
                branch_states[current_task_id]['End'] = True
                break

    def _find_convergence_point(
        self, parallel_children: list, workflow: FlexWorkflow
    ) -> Optional[str]:
        """Find task that all parallel branches converge to"""
        # Find all tasks that are descendants of the parallel children
        all_descendants = set()
        for child_id in parallel_children:
            descendants = self._get_all_descendants(child_id, workflow)
            all_descendants.update(descendants)

        # Find tasks that depend on multiple parallel children (directly or indirectly)
        for workflow_task in workflow.tasks:
            if (
                workflow_task.id in all_descendants
                and workflow_task.depends_on
                and len(workflow_task.depends_on) > 1
            ):
                # Check if this task's dependencies trace back to multiple parallel children
                dependency_sources = set()
                for dep in workflow_task.depends_on:
                    source = self._trace_to_parallel_source(
                        dep.task_id, parallel_children, workflow
                    )
                    if source:
                        dependency_sources.add(source)

                # If this task depends on multiple parallel sources, it's a convergence point
                if len(dependency_sources) > 1:
                    return workflow_task.id

        return None

    def _get_all_descendants(self, task_id: str, workflow: FlexWorkflow) -> set:
        """Get all tasks that are descendants of the given task"""
        descendants = set()
        visited = set()

        def dfs(current_id):
            if current_id in visited:
                return
            visited.add(current_id)

            children = self._get_children_tasks(current_id, workflow)
            for child_id in children:
                descendants.add(child_id)
                dfs(child_id)

        dfs(task_id)
        return descendants

    def _trace_to_parallel_source(
        self, task_id: str, parallel_children: list, workflow: FlexWorkflow
    ) -> Optional[str]:
        """Trace a task back to its parallel source"""
        if task_id in parallel_children:
            return task_id

        task = self._find_task_in_flex(task_id, workflow)
        if not task or not task.depends_on:
            return None

        for dep in task.depends_on:
            source = self._trace_to_parallel_source(dep.task_id, parallel_children, workflow)
            if source:
                return source

        return None

    def _get_children_tasks(self, task_id: str, workflow: FlexWorkflow) -> list:
        """Get all tasks that depend on the given task"""
        children = []

        # For branch tasks, children are defined in branch paths
        task = self._find_task_in_flex(task_id, workflow)
        if task and task.type == 'branch' and task.parameters:
            branches = task.parameters.get('branches', [])
            return [branch['next_task'] for branch in branches if 'next_task' in branch]

        # For regular tasks, find dependents
        for workflow_task in workflow.tasks:
            if workflow_task.depends_on and any(
                dep.task_id == task_id for dep in workflow_task.depends_on
            ):
                children.append(workflow_task.id)
        return children

    def _find_task_in_flex(self, task_id: str, workflow: FlexWorkflow):
        """Find task in FLEX workflow with safe error handling"""
        if not workflow.tasks:
            # No tasks found in workflow
            return None

        task = next((t for t in workflow.tasks if t.id == task_id), None)
        if not task:
            # Task referenced but not found in FLEX workflow
            return None
        return task

    def _generate_task_state(self, task, workflow: FlexWorkflow) -> Dict[str, Any]:
        """Generate Step Functions state for a FLEX task"""
        # Handle loop tasks as Map states
        if task.type == 'for_each':
            return self._generate_map_state(task, workflow)

        # Handle branch tasks as Choice states
        if task.type == 'branch':
            return self._generate_choice_state(task, workflow)

        state = {'Type': 'Task', 'Comment': task.name}

        # Map task type to Step Functions resource
        if task.type == 'sql':
            state['Resource'] = 'arn:aws:states:::aws-sdk:redshiftdata:executeStatement'
            # Use connection_id for cluster/database if available
            cluster_id = 'default-cluster'
            database = 'default-db'
            if task.connection_id:
                # Extract cluster/database from connection_id if formatted as "cluster:database"
                if ':' in task.connection_id:
                    cluster_id, database = task.connection_id.split(':', 1)
                else:
                    cluster_id = task.connection_id

            state['Parameters'] = {
                'ClusterIdentifier': cluster_id,
                'Database': database,
                'Sql': task.command,
            }
        elif task.type == 'python':
            state['Resource'] = 'arn:aws:states:::glue:startJobRun.sync'

            # Use script_file if available, otherwise fallback to inline command
            if task.script_file:
                # External Python file for Glue execution
                state['Parameters'] = {
                    'JobName': f'etl-{workflow.name}-{task.id}-python-shell',
                    'Arguments': {
                        '--task_id': task.id,
                        '--workflow_name': workflow.name,
                        '--script_location': f's3://{{glue_scripts_bucket}}/scripts/{task.script_file}',
                    },
                }
            else:
                # Fallback to inline command (less common for Step Functions)
                state['Parameters'] = {
                    'JobName': f'etl-{workflow.name}-{task.id}-python-shell',
                    'Arguments': {
                        '--task_id': task.id,
                        '--script': task.command,
                        '--workflow_name': workflow.name,
                    },
                }
        elif task.type == 'bash':
            state['Resource'] = 'arn:aws:states:::batch:submitJob.sync'
            state['Parameters'] = {
                'JobDefinition': f'etl-{workflow.name}-batch-job',
                'JobName': task.id,
                'JobQueue': 'default-queue',
                'Parameters': {'command': task.command},
            }
        else:
            # Default to Glue Python Shell for ETL tasks
            state['Resource'] = 'arn:aws:states:::glue:startJobRun.sync'

            # Use script_file if available, otherwise fallback to inline command
            if task.script_file:
                # External script file for Glue execution
                state['Parameters'] = {
                    'JobName': f'etl-{workflow.name}-{task.id}-python-shell',
                    'Arguments': {
                        '--task_id': task.id,
                        '--workflow_name': workflow.name,
                        '--task_type': task.type,
                        '--script_location': f's3://{{glue_scripts_bucket}}/scripts/{task.script_file}',
                    },
                }
            else:
                # Fallback to inline command
                state['Parameters'] = {
                    'JobName': f'etl-{workflow.name}-{task.id}-python-shell',
                    'Arguments': {'--command': task.command, '--task_type': task.type},
                }

        # Add ResultPath for task output
        state['ResultPath'] = '$.task_output'

        # Add timeout if specified
        if task.timeout:
            state['TimeoutSeconds'] = task.timeout

        # Add retry configuration
        if task.retries > 0:
            state['Retry'] = [
                {
                    'ErrorEquals': ['States.TaskFailed'],
                    'IntervalSeconds': 30,
                    'MaxAttempts': task.retries,
                    'BackoffRate': 2.0,
                }
            ]

        return state

    def _generate_choice_state(self, task, workflow: FlexWorkflow) -> Dict[str, Any]:
        """Generate Step Functions Choice state for branch tasks"""
        branches = task.parameters.get('branches', []) if task.parameters else []

        choices = []
        default_next = None

        for branch in branches:
            next_task = branch['next_task']
            condition = branch['condition']

            # Extract the comparison value from the condition string
            condition_value = self._extract_condition_value(condition)

            # Create choice condition
            choice = {
                'Variable': '$.result',
                'StringEquals': condition_value,
                'Next': next_task,
            }
            choices.append(choice)

            # Use first branch as default (can be improved)
            if not default_next:
                default_next = next_task

        return {
            'Type': 'Choice',
            'Comment': f'Branch: {task.name}',
            'Choices': choices,
            'Default': default_next,
        }

    def _generate_map_state(self, task, workflow: FlexWorkflow) -> Dict[str, Any]:
        """Generate Step Functions Map state for for_each loops"""
        params = task.parameters

        # Handle dynamic patterns
        if params.get('dynamic_pattern'):
            return self._generate_dynamic_map_state(task, workflow)

        # Create the iterator definition based on loop type
        if params.get('loop_type') == 'range':
            start = params.get('start', 1)
            end = params.get('end', 4)
            items_path = f'$.range_{start}_{end}'
            iterator_name = 'ProcessBatch'
            payload_key = 'batch_id'
        elif params.get('loop_type') == 'enumerate':
            # items = params.get('items', [])  # Unused variable
            items_path = '$.file_list'
            iterator_name = 'ProcessFile'
            payload_key = 'file_name'
        else:
            items_path = '$.items'
            iterator_name = 'ProcessItem'
            payload_key = 'item'

        # Create the iterator state (the task that runs for each item)
        iterator_state = {
            'Type': 'Task',
            'Resource': 'arn:aws:states:::glue:startJobRun.sync',
            'Parameters': {
                'JobName': f'etl-{workflow.name}-{task.command}-python-shell',
                'Arguments': {
                    '--task_id.$': f'$.{payload_key}',
                    '--script': task.command,
                    '--workflow_name': workflow.name,
                    f'--{payload_key}.$': f'$.{payload_key}',
                },
            },
            'ResultPath': '$.task_output',
            'End': True,
        }

        # Use batch_size for MaxConcurrency if available
        max_concurrency = task.batch_size or 3

        return {
            'Type': 'Map',
            'Comment': f'Loop: {task.name}',
            'ItemsPath': items_path,
            'MaxConcurrency': max_concurrency,
            'Iterator': {
                'StartAt': iterator_name,
                'States': {iterator_name: iterator_state},
            },
            'ResultPath': '$.map_results',
        }

    def _generate_dynamic_map_state(self, task, workflow: FlexWorkflow) -> Dict[str, Any]:
        """Generate Step Functions Map state for dynamic patterns"""
        params = task.parameters
        loop_variable = params.get('loop_variable', 'item')

        # Determine items source
        if params.get('static_expanded'):
            # Static items were resolved at parse time
            items_path = '$.dynamic_items'
        else:
            # Runtime items - from previous task or parameter store
            items_path = f'$.{params.get("items_source", "items")}'

        # Create iterator state based on original operator type
        operator_type = params.get('operator_type', 'PythonOperator')

        if 'Python' in operator_type:
            iterator_state = {
                'Type': 'Task',
                'Resource': 'arn:aws:states:::glue:startJobRun.sync',
                'Parameters': {
                    'JobName': f'etl-{workflow.name}-{task.command}-python-shell',
                    'Arguments': {
                        f'--{loop_variable}.$': '$',
                        '--script_location': (
                            f's3://{{glue_scripts_bucket}}/scripts/{task.script_file}'
                            if task.script_file
                            else None
                        ),
                        '--workflow_name': workflow.name,
                    },
                },
                'ResultPath': '$.task_result',
                'End': True,
            }
        elif 'Bash' in operator_type:
            iterator_state = {
                'Type': 'Task',
                'Resource': 'arn:aws:states:::batch:submitJob.sync',
                'Parameters': {
                    'JobDefinition': f'etl-{workflow.name}-batch-job',
                    'JobName.$': f'$.{loop_variable}',
                    'JobQueue': 'default-queue',
                    'Parameters': {'command': task.command, f'{loop_variable}.$': '$'},
                },
                'ResultPath': '$.task_result',
                'End': True,
            }
        else:
            # Default to Glue Python Shell
            iterator_state = {
                'Type': 'Task',
                'Resource': 'arn:aws:states:::glue:startJobRun.sync',
                'Parameters': {
                    'JobName': f'etl-{workflow.name}-{task.command}-python-shell',
                    'Arguments': {
                        f'--{loop_variable}.$': '$',
                        '--task_type': task.type,
                        '--workflow_name': workflow.name,
                    },
                },
                'ResultPath': '$.task_result',
                'End': True,
            }

        # Remove None values from parameters
        if iterator_state['Parameters'].get('Arguments'):
            iterator_state['Parameters']['Arguments'] = {
                k: v for k, v in iterator_state['Parameters']['Arguments'].items() if v is not None
            }

        # Use batch_size for MaxConcurrency if available
        max_concurrency = task.batch_size or params.get('max_concurrency', 5)

        return {
            'Type': 'Map',
            'Comment': f'Dynamic processing: {task.name}',
            'ItemsPath': items_path,
            'MaxConcurrency': max_concurrency,
            'Iterator': {
                'StartAt': 'ProcessItem',
                'States': {'ProcessItem': iterator_state},
            },
            'ResultPath': '$.map_results',
        }

    def _find_start_state(self, workflow: FlexWorkflow) -> str:
        """Find the starting state (task with no upstream dependencies)"""
        tasks_with_deps = {task.id for task in workflow.tasks if task.depends_on}
        for task in workflow.tasks:
            if task.id not in tasks_with_deps:
                return task.id
        return workflow.tasks[0].id if workflow.tasks else 'EmptyWorkflow'

    # Required methods from base class
    def get_supported_task_types(self) -> List[str]:
        """Get supported task types for Step Functions"""
        from ..models.task_types import get_all_task_types

        return get_all_task_types()

    def supports_feature(self, feature: str) -> bool:
        """Check if Step Functions supports specific FLEX feature"""
        supported_features = {
            'loops',
            'conditional_logic',
            'parallel_execution',
            'error_handling',
        }
        return feature in supported_features

    def generate_metadata(self, workflow: FlexWorkflow) -> Dict[str, Any]:
        """Generate Step Functions metadata"""
        return {
            'state_machine_name': f'etl-{workflow.name}',
            'comment': workflow.description or f'Generated from FLEX workflow: {workflow.name}',
            'execution_role': f'arn:aws:iam::{{account_id}}:role/etl-{workflow.name}-execution-role',
        }

    def generate_schedule(self, schedule) -> Any:
        """Generate schedule - Step Functions uses EventBridge rules"""
        return None  # Step Functions doesn't have built-in scheduling

    def generate_task(self, task, workflow: FlexWorkflow) -> Any:
        """Generate individual Step Functions state"""
        return self._generate_task_state(task, workflow)

    def generate_dependencies(self, tasks) -> Any:
        """Generate dependencies - handled by Next transitions"""
        return None  # Dependencies handled in state machine structure

    def generate_error_handling(self, error_handling) -> Any:
        """Generate error handling - uses Catch blocks"""
        return None  # Error handling embedded in individual states

    def generate_conditional_logic(self, task, workflow: FlexWorkflow) -> Any:
        """Generate Choice state for conditional logic"""
        if task.type == 'branch':
            return self._generate_choice_state(task, workflow)
        return None

    def generate_loop_logic(self, task, workflow: FlexWorkflow) -> Any:
        """Generate Map state for loops"""
        if task.type == 'for_each':
            return self._generate_map_state(task, workflow)
        return None

    def generate_parallel_execution(self, tasks, workflow: FlexWorkflow) -> Any:
        """Generate Parallel state for parallel execution"""
        return None  # Handled in demand-driven generation

    def format_output(self, generated_content: Any, workflow: FlexWorkflow) -> Dict[str, Any]:
        """Format Step Functions output"""
        workflow_name = f'etl-{workflow.name}'
        return {
            'state_machine_definition': generated_content,
            'state_machine_name': workflow_name,
            'execution_role': f'arn:aws:iam::{{account_id}}:role/{workflow_name}-execution-role',
            'framework': 'step_functions',
        }

    def _find_retry_loop_target(self, task_id: str, workflow: FlexWorkflow) -> Optional[str]:
        """Find if this task should loop back to a branch task (retry pattern)"""
        # Check if this task is a retry task that should loop back
        if 'retry' in task_id.lower():
            # Find the corresponding branch task
            for task in workflow.tasks:
                if (
                    task.type == 'branch'
                    and task.parameters
                    and task_id in [b['next_task'] for b in task.parameters.get('branches', [])]
                ):
                    # This retry task should loop back to the python task that feeds the branch
                    branch_deps = task.depends_on
                    if branch_deps:
                        return branch_deps[0].task_id  # Loop back to the python task
        return None

    def _add_retry_loop_logic(
        self, branch_task_id: str, workflow: FlexWorkflow, states: Dict[str, Any]
    ):
        """Add retry loop logic for branch tasks"""
        # Find retry tasks that should loop back
        branch_task = self._find_task_in_flex(branch_task_id, workflow)
        if not branch_task or not branch_task.parameters:
            return
        branches = branch_task.parameters.get('branches', [])

        for branch in branches:
            next_task_id = branch['next_task']
            if 'retry' in next_task_id.lower():
                # This is a retry task - it should loop back to the python task
                if next_task_id in states:
                    # Find the python task that feeds this branch
                    branch_deps = branch_task.depends_on if branch_task else None
                    if branch_deps:
                        python_task_id = branch_deps[0].task_id
                        states[next_task_id]['Next'] = python_task_id

    def _extract_condition_value(self, condition: str) -> str:
        """Extract the comparison value from a condition string like "$.result == 'processing_complete'"""
        import re

        # Handle different condition formats
        if '==' in condition:
            # Format: "$.result == 'value'" or "$.result == \"value\""
            match = re.search(r"==\s*['\"]([^'\"]+)['\"]?", condition)
            if match:
                return match.group(1)

        # Fallback: try to extract quoted string
        match = re.search(r"['\"]([^'\"]+)['\"]?", condition)
        if match:
            return match.group(1)

        # Last resort: return the condition as-is
        return condition

    def validate_generated_output(self, output: Dict[str, Any]) -> bool:
        """Validate Step Functions output"""
        required_keys = ['state_machine_definition', 'state_machine_name', 'framework']
        if not all(key in output for key in required_keys):
            return False

        definition = output.get('state_machine_definition', {})
        return 'States' in definition and 'StartAt' in definition
