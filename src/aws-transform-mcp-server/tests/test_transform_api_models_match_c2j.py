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

"""Drift check: Pydantic request models in ``fes_models`` stay in sync with C2J.

For every ``*Request`` model in :mod:`awslabs.aws_transform_mcp_server.fes_models`
that maps to a FES operation, this test verifies two properties against the
vendored C2J service model:

1. **No extra fields** — every Pydantic field name exists in the C2J input
   shape. Catches typos and removed-upstream fields.
2. **Required fields are required** — every C2J-required field is declared
   required on the Pydantic model. Catches silent relaxation of constraints.

These two checks together are the "drift protection" promised by the
hand-written approach: if FES adds/renames/removes a field, the next
``pytest`` run flags it.

Nested shapes (``AccountConnectionRequest``, ``HitlTaskArtifact``, etc.) are
validated when they are used as fields of a top-level request shape — the
parent check covers their name. Their own field names are not cross-checked
here to keep the test focused; the primary risk is the top-level request
shape.
"""
# ruff: noqa: D101, D102, D103

import pytest
from awslabs.aws_transform_mcp_server import transform_api_models as fes_models
from awslabs.aws_transform_mcp_server._service_model import create_session
from botocore import UNSIGNED
from botocore.config import Config as BotoConfig


# Map operation name -> Pydantic request model. Must be kept in sync when a
# new request model is added (the test below enumerates this dict).
OP_TO_MODEL = {
    'BatchGetMessage': fes_models.BatchGetMessageRequest,
    'BatchGetUserDetails': fes_models.BatchGetUserDetailsRequest,
    'CompleteArtifactUpload': fes_models.CompleteArtifactUploadRequest,
    'CreateArtifactDownloadUrl': fes_models.CreateArtifactDownloadUrlRequest,
    'CreateArtifactUploadUrl': fes_models.CreateArtifactUploadUrlRequest,
    'CreateAssetDownloadUrl': fes_models.CreateAssetDownloadUrlRequest,
    'CreateConnector': fes_models.CreateConnectorRequest,
    'CreateJob': fes_models.CreateJobRequest,
    'CreateWorkspace': fes_models.CreateWorkspaceRequest,
    'DeleteJob': fes_models.DeleteJobRequest,
    'DeleteSelfRoleMappings': fes_models.DeleteSelfRoleMappingsRequest,
    'DeleteUserRoleMappings': fes_models.DeleteUserRoleMappingsRequest,
    'DeleteWorkspace': fes_models.DeleteWorkspaceRequest,
    'GetConnector': fes_models.GetConnectorRequest,
    'GetHitlTask': fes_models.GetHitlTaskRequest,
    'GetJob': fes_models.GetJobRequest,
    'GetWorkspace': fes_models.GetWorkspaceRequest,
    'ListAgents': fes_models.ListAgentsRequest,
    'ListArtifacts': fes_models.ListArtifactsRequest,
    'ListConnectors': fes_models.ListConnectorsRequest,
    'ListHitlTasks': fes_models.ListHitlTasksRequest,
    'ListJobPlanSteps': fes_models.ListJobPlanStepsRequest,
    'ListJobs': fes_models.ListJobsRequest,
    'ListMessages': fes_models.ListMessagesRequest,
    'ListPlanUpdates': fes_models.ListPlanUpdatesRequest,
    'ListUserRoleMappings': fes_models.ListUserRoleMappingsRequest,
    'ListWorklogs': fes_models.ListWorklogsRequest,
    'ListWorkspaces': fes_models.ListWorkspacesRequest,
    'PutUserRoleMappings': fes_models.PutUserRoleMappingsRequest,
    'SearchUsersTypeahead': fes_models.SearchUsersTypeaheadRequest,
    'SendMessage': fes_models.SendMessageRequest,
    'StartJob': fes_models.StartJobRequest,
    'StopJob': fes_models.StopJobRequest,
    'SubmitCriticalHitlTask': fes_models.SubmitCriticalHitlTaskRequest,
    'SubmitStandardHitlTask': fes_models.SubmitStandardHitlTaskRequest,
    'UpdateHitlTask': fes_models.UpdateHitlTaskRequest,
}


@pytest.fixture(scope='module')
def service_model():
    """Load the vendored C2J model once per test module."""
    session = create_session()
    client = session.client(
        'elasticgumbyfrontendservice',
        region_name='us-east-1',
        endpoint_url='https://validation-only.invalid',
        config=BotoConfig(signature_version=UNSIGNED),
    )
    return client._service_model


@pytest.mark.parametrize('op,model_cls', sorted(OP_TO_MODEL.items()))
def test_pydantic_fields_exist_in_c2j(op, model_cls, service_model):
    """Every Pydantic field name must exist on the C2J input shape.

    Catches typos and fields removed upstream.
    """
    op_model = service_model.operation_model(op)
    input_shape = op_model.input_shape
    assert input_shape is not None, f'C2J operation {op!r} has no input shape'

    c2j_fields = set(input_shape.members.keys())
    py_fields = set(model_cls.model_fields.keys())

    unknown = py_fields - c2j_fields
    assert not unknown, (
        f'{model_cls.__name__} has fields not present in the C2J {op!r} input '
        f'shape: {sorted(unknown)}. Either fix the typo or remove the field.'
    )


@pytest.mark.parametrize('op,model_cls', sorted(OP_TO_MODEL.items()))
def test_c2j_required_fields_are_required_in_pydantic(op, model_cls, service_model):
    """Every C2J-required field must be declared required on the Pydantic model.

    Catches silent relaxation of constraints (a field that used to be required
    being made optional in our model).
    """
    op_model = service_model.operation_model(op)
    input_shape = op_model.input_shape
    assert input_shape is not None, f'C2J operation {op!r} has no input shape'

    c2j_required = set(input_shape.required_members)
    py_required = {name for name, field in model_cls.model_fields.items() if field.is_required()}

    missing = c2j_required - py_required
    assert not missing, (
        f'{model_cls.__name__} is missing required fields that C2J {op!r} '
        f'requires: {sorted(missing)}. Mark them as required (no default).'
    )
