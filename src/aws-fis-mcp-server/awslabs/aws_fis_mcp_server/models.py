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

"""Data models for the AWS FIS MCP server."""

from enum import Enum
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class ExperimentState(str, Enum):
    """Possible states of an AWS FIS experiment.

    Attributes:
        PENDING: The experiment is pending.
        INITIATING: The experiment is being initiated.
        RUNNING: The experiment is running.
        COMPLETED: The experiment has completed successfully.
        STOPPED: The experiment was stopped.
        FAILED: The experiment has failed.
    """

    PENDING = 'pending'
    INITIATING = 'initiating'
    RUNNING = 'running'
    COMPLETED = 'completed'
    STOPPED = 'stopped'
    FAILED = 'failed'


class ExperimentActionsMode(str, Enum):
    """Possible action modes for an AWS FIS experiment.

    Attributes:
        RUN_ALL: Run all actions in the experiment.
    """

    RUN_ALL = 'run-all'


class StopCondition(BaseModel):
    """Stop condition for an AWS FIS experiment.

    Attributes:
        source: The source of the stop condition.
        value: The value of the stop condition.
    """

    source: str = Field(..., description='The source of the stop condition')
    value: str = Field(..., description='The value of the stop condition')


class Target(BaseModel):
    """Target for an AWS FIS experiment.

    Attributes:
        resource_type: The type of resource to target.
        resource_arns: Optional list of resource ARNs to target.
        resource_tags: Optional dictionary of resource tags to target.
        filters: Optional list of filters to apply to the target.
        selection_mode: The selection mode for the target.
        parameters: Optional parameters for the target.
    """

    resource_type: str = Field(..., description='The type of resource to target')
    resource_arns: Optional[List[str]] = Field(None, description='List of resource ARNs to target')
    resource_tags: Optional[Dict[str, str]] = Field(
        None, description='Dictionary of resource tags to target'
    )
    filters: Optional[List[Dict[str, Any]]] = Field(
        None, description='List of filters to apply to the target'
    )
    selection_mode: str = Field(..., description='The selection mode for the target')
    parameters: Optional[Dict[str, Any]] = Field(None, description='Parameters for the target')


class Action(BaseModel):
    """Action for an AWS FIS experiment.

    Attributes:
        action_id: The ID of the action.
        description: Optional description of the action.
        parameters: Optional parameters for the action.
        targets: Optional dictionary of targets for the action.
        start_after: Optional list of action IDs that must complete before this action starts.
    """

    action_id: str = Field(..., description='The ID of the action')
    description: Optional[str] = Field(None, description='Description of the action')
    parameters: Optional[Dict[str, Any]] = Field(None, description='Parameters for the action')
    targets: Optional[Dict[str, str]] = Field(
        None, description='Dictionary of targets for the action'
    )
    start_after: Optional[List[str]] = Field(
        None, description='List of action IDs that must complete before this action starts'
    )


class LogConfiguration(BaseModel):
    """Log configuration for an AWS FIS experiment.

    Attributes:
        log_schema_version: The version of the log schema.
        cloud_watch_logs_configuration: Optional CloudWatch logs configuration.
        s3_configuration: Optional S3 configuration.
    """

    log_schema_version: int = Field(..., description='The version of the log schema')
    cloud_watch_logs_configuration: Optional[Dict[str, Any]] = Field(
        None, description='CloudWatch logs configuration'
    )
    s3_configuration: Optional[Dict[str, Any]] = Field(None, description='S3 configuration')


class ExperimentTemplateRequest(BaseModel):
    """Request model for creating an AWS FIS experiment template.

    Attributes:
        client_token: Client token for idempotency.
        description: Description of the experiment template.
        tags: Optional tags to apply to the template.
        stop_conditions: Conditions that stop the experiment.
        targets: Target resources for the experiment.
        actions: Actions to perform during the experiment.
        role_arn: IAM role ARN for experiment execution.
        log_configuration: Optional configuration for experiment logging.
        experiment_options: Optional additional experiment options.
        report_configuration: Optional configuration for experiment reporting.
    """

    client_token: str = Field(..., description='Client token for idempotency')
    description: str = Field(..., description='Description of the experiment template')
    tags: Optional[Dict[str, str]] = Field(None, description='Tags to apply to the template')
    stop_conditions: List[StopCondition] = Field(
        ..., description='Conditions that stop the experiment'
    )
    targets: Dict[str, Target] = Field(..., description='Target resources for the experiment')
    actions: Dict[str, Action] = Field(..., description='Actions to perform during the experiment')
    role_arn: str = Field(..., description='IAM role ARN for experiment execution')
    log_configuration: Optional[LogConfiguration] = Field(
        None, description='Configuration for experiment logging'
    )
    experiment_options: Optional[Dict[str, str]] = Field(
        None, description='Additional experiment options'
    )
    report_configuration: Optional[Dict[str, Any]] = Field(
        None, description='Configuration for experiment reporting'
    )


class StartExperimentRequest(BaseModel):
    """Request model for starting an AWS FIS experiment.

    Attributes:
        id: The experiment template ID.
        tags: Optional tags to apply to the experiment.
        action: The actions mode (default: 'run-all').
        max_timeout_seconds: Maximum time to wait for experiment completion.
        initial_poll_interval: Starting poll interval in seconds.
        max_poll_interval: Maximum poll interval in seconds.
    """

    id: str = Field(..., description='The experiment template ID')
    tags: Optional[Dict[str, str]] = Field(None, description='Tags to apply to the experiment')
    action: ExperimentActionsMode = Field(
        ExperimentActionsMode.RUN_ALL, description='The actions mode'
    )
    max_timeout_seconds: int = Field(
        3600, description='Maximum time to wait for experiment completion'
    )
    initial_poll_interval: int = Field(5, description='Starting poll interval in seconds')
    max_poll_interval: int = Field(60, description='Maximum poll interval in seconds')


class ResourceExplorerViewRequest(BaseModel):
    """Request model for creating a Resource Explorer view.

    Attributes:
        query: Filter string for the view.
        view_name: Name of the view.
        tags: Optional tags to apply to the view.
        scope: Optional scope of the view.
        client_token: Optional client token for idempotency.
    """

    query: str = Field(..., description='Filter string for the view')
    view_name: str = Field(..., description='Name of the view')
    tags: Optional[Dict[str, str]] = Field(None, description='Tags to apply to the view')
    scope: Optional[str] = Field(None, description='Scope of the view')
    client_token: Optional[str] = Field(None, description='Client token for idempotency')
