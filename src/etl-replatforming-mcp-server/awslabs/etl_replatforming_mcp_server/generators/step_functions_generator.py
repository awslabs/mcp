#!/usr/bin/env python3

import json
from typing import Dict, Any, Optional
from ..models.flex_workflow import FlexWorkflow


class StepFunctionsGenerator:
    """Generator to convert FLEX workflow to AWS Step Functions format"""
    
    def generate(self, workflow: FlexWorkflow, context_document: Optional[str] = None) -> Dict[str, Any]:
        """Convert FLEX workflow to Step Functions state machine definition
        
        Args:
            workflow: FLEX workflow representation
            context_document: Optional context for LLM processing
            
        Returns:
            Dict with generated Step Functions state machine and metadata
        """
        state_machine = self._generate_state_machine(workflow)
        workflow_name = f"etl-{workflow.name}"
        
        return {
            "state_machine_definition": state_machine,
            "state_machine_name": workflow_name,
            "execution_role": f"arn:aws:iam::{{account_id}}:role/{workflow_name}-execution-role",
            "framework": "step_functions"
        }
    
    def _generate_state_machine(self, workflow: FlexWorkflow) -> Dict[str, Any]:
        """Generate Step Functions state machine definition"""
        states = {}
        
        # Generate states for each task
        for task in workflow.tasks:
            states[task.id] = self._generate_task_state(task, workflow)
        
        # Add dependencies (Next transitions)
        self._add_transitions(states, workflow)
        
        # Determine start state
        start_state = self._find_start_state(workflow)
        
        return {
            "Comment": workflow.description or f"Generated from FLEX workflow: {workflow.name}",
            "StartAt": start_state,
            "States": states
        }
    
    def _generate_task_state(self, task, workflow: FlexWorkflow) -> Dict[str, Any]:
        """Generate Step Functions state for a FLEX task"""
        state = {
            "Type": "Task",
            "Comment": task.name
        }
        
        # Map task type to Step Functions resource
        if task.type == "sql":
            state["Resource"] = "arn:aws:states:::aws-sdk:redshiftdata:executeStatement"
            state["Parameters"] = {
                "ClusterIdentifier": "default-cluster",
                "Database": "default-db",
                "Sql": task.command
            }
        elif task.type == "python":
            state["Resource"] = "arn:aws:states:::lambda:invoke"
            state["Parameters"] = {
                "FunctionName": f"etl-{workflow.name}-{task.id}",
                "Payload": {
                    "script": task.command
                }
            }
        elif task.type == "bash":
            state["Resource"] = "arn:aws:states:::batch:submitJob.sync"
            state["Parameters"] = {
                "JobDefinition": f"etl-{workflow.name}-batch-job",
                "JobName": task.id,
                "JobQueue": "default-queue",
                "Parameters": {
                    "command": task.command
                }
            }
        else:
            # Default to Lambda
            state["Resource"] = "arn:aws:states:::lambda:invoke"
            state["Parameters"] = {
                "FunctionName": f"etl-{workflow.name}-{task.id}",
                "Payload": {"command": task.command}
            }
        
        # Add timeout if specified
        if task.timeout:
            state["TimeoutSeconds"] = task.timeout
        
        # Add retry configuration
        if task.retries > 0:
            state["Retry"] = [{
                "ErrorEquals": ["States.TaskFailed"],
                "IntervalSeconds": 30,
                "MaxAttempts": task.retries,
                "BackoffRate": 2.0
            }]
        
        return state
    
    def _add_transitions(self, states: Dict[str, Any], workflow: FlexWorkflow):
        """Add Next transitions based on dependencies"""
        # Create dependency map from task.depends_on
        downstream_map = {}
        for task in workflow.tasks:
            if task.depends_on:
                for dep in task.depends_on:
                    if dep.task_id not in downstream_map:
                        downstream_map[dep.task_id] = []
                    downstream_map[dep.task_id].append(task.id)
        
        # Add Next transitions
        for task_id, state in states.items():
            if task_id in downstream_map:
                downstream_tasks = downstream_map[task_id]
                if len(downstream_tasks) == 1:
                    state["Next"] = downstream_tasks[0]
                else:
                    # Multiple downstream tasks - use first one for simplicity
                    state["Next"] = downstream_tasks[0]
            else:
                # No downstream tasks - this is an end state
                state["End"] = True
    
    def _find_start_state(self, workflow: FlexWorkflow) -> str:
        """Find the starting state (task with no upstream dependencies)"""
        # Find tasks that have dependencies (not start tasks)
        tasks_with_deps = set()
        for task in workflow.tasks:
            if task.depends_on:
                tasks_with_deps.add(task.id)
        
        # Find tasks without dependencies (start tasks)
        for task in workflow.tasks:
            if task.id not in tasks_with_deps:
                return task.id
        
        # If no clear start state, use first task
        return workflow.tasks[0].id if workflow.tasks else "EmptyWorkflow"