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

"""Runtime lifecycle tools: create, get, update, delete, list."""

from .error_handler import handle_runtime_error
from .models import (
    CreateRuntimeResponse,
    DeleteRuntimeResponse,
    ErrorResponse,
    GetRuntimeResponse,
    ListRuntimesResponse,
    ListRuntimeVersionsResponse,
    RuntimeSummary,
    UpdateRuntimeResponse,
)
from mcp.server.fastmcp import Context
from pydantic import Field
from typing import Annotated, Callable, Optional, Union


class LifecycleTools:
    """Tools for managing AgentCore Runtime lifecycle."""

    def __init__(self, control_client_factory: Callable) -> None:
        """Initialise with a control-plane client factory.

        Args:
            control_client_factory: Callable returning a boto3 client.
        """
        self._get_client = control_client_factory

    def register(self, mcp) -> None:  # noqa: D102
        """Register lifecycle tools with the MCP server."""
        mcp.tool(name='create_agent_runtime')(self.create_agent_runtime)
        mcp.tool(name='get_agent_runtime')(self.get_agent_runtime)
        mcp.tool(name='update_agent_runtime')(self.update_agent_runtime)
        mcp.tool(name='delete_agent_runtime')(self.delete_agent_runtime)
        mcp.tool(name='list_agent_runtimes')(self.list_agent_runtimes)
        mcp.tool(name='list_agent_runtime_versions')(self.list_agent_runtime_versions)

    # ------------------------------------------------------------------ create
    async def create_agent_runtime(
        self,
        ctx: Context,
        agent_runtime_name: Annotated[
            str,
            Field(description=('Name for the runtime. Must match [a-zA-Z][a-zA-Z0-9_]{0,47}.')),
        ],
        role_arn: Annotated[
            str,
            Field(description='IAM execution role ARN for the runtime.'),
        ],
        network_mode: Annotated[
            str,
            Field(description='Network mode: "PUBLIC" or "VPC".'),
        ] = 'PUBLIC',
        container_uri: Annotated[
            Optional[str],
            Field(
                description=(
                    'ECR container URI. Provide either container_uri '
                    'or the s3 code fields, not both.'
                )
            ),
        ] = None,
        code_s3_bucket: Annotated[
            Optional[str],
            Field(description='S3 bucket for direct code deployment.'),
        ] = None,
        code_s3_prefix: Annotated[
            Optional[str],
            Field(description='S3 key/prefix for the code zip.'),
        ] = None,
        code_runtime: Annotated[
            Optional[str],
            Field(
                description=('Python runtime identifier for direct code deploy, e.g. PYTHON_3_13.')
            ),
        ] = None,
        code_entry_point: Annotated[
            Optional[str],
            Field(
                description=(
                    'Entry point command as comma-separated values, '
                    'e.g. "main.py" or "opentelemetry-instrument,main.py".'
                )
            ),
        ] = None,
        description: Annotated[
            Optional[str],
            Field(description='Description (max 4096 chars).'),
        ] = None,
        server_protocol: Annotated[
            Optional[str],
            Field(description='Protocol: "HTTP", "MCP", or "A2A".'),
        ] = None,
        idle_timeout: Annotated[
            Optional[int],
            Field(description=('Idle session timeout in seconds (60-28800). Default 900.')),
        ] = None,
        max_lifetime: Annotated[
            Optional[int],
            Field(description=('Max session lifetime in seconds (60-28800). Default 28800.')),
        ] = None,
        subnets: Annotated[
            Optional[str],
            Field(description='Comma-separated subnet IDs (required for VPC mode).'),
        ] = None,
        security_groups: Annotated[
            Optional[str],
            Field(description='Comma-separated security group IDs (required for VPC mode).'),
        ] = None,
    ) -> Union[CreateRuntimeResponse, ErrorResponse]:
        """Create a new AgentCore Runtime to host an agent or tool.

        This is a one-time setup operation that creates AWS infrastructure
        (IAM role binding, container deployment, endpoint). The DEFAULT
        endpoint is created automatically. Subsequent updates create new
        immutable versions.

        **Cost note:** Creating a runtime provisions infrastructure.
        You are not billed until sessions are invoked, but the runtime
        definition and its resources persist until deleted.
        """
        try:
            client = self._get_client()

            # Build artifact
            artifact: dict = {}
            if container_uri:
                artifact['containerConfiguration'] = {'containerUri': container_uri}
            elif code_s3_bucket and code_s3_prefix:
                code_cfg: dict = {
                    'code': {
                        's3': {
                            'bucket': code_s3_bucket,
                            'prefix': code_s3_prefix,
                        }
                    },
                }
                if code_runtime:
                    code_cfg['runtime'] = code_runtime
                if code_entry_point:
                    code_cfg['entryPoint'] = [
                        s.strip() for s in code_entry_point.split(',') if s.strip()
                    ]
                artifact['codeConfiguration'] = code_cfg
            else:
                return CreateRuntimeResponse(
                    status='error',
                    message=('Provide either container_uri or code_s3_bucket + code_s3_prefix.'),
                )

            # Build network config
            net_cfg: dict = {'networkMode': network_mode}
            if network_mode == 'VPC':
                mode_cfg: dict = {}
                if subnets is not None:
                    mode_cfg['subnets'] = [s.strip() for s in subnets.split(',') if s.strip()]
                if security_groups is not None:
                    mode_cfg['securityGroups'] = [
                        s.strip() for s in security_groups.split(',') if s.strip()
                    ]
                net_cfg['networkModeConfig'] = mode_cfg

            kwargs: dict = {
                'agentRuntimeName': agent_runtime_name,
                'agentRuntimeArtifact': artifact,
                'networkConfiguration': net_cfg,
                'roleArn': role_arn,
            }
            if description is not None:
                kwargs['description'] = description
            if server_protocol is not None:
                kwargs['protocolConfiguration'] = {'serverProtocol': server_protocol}
            lc: dict = {}
            if idle_timeout is not None:
                lc['idleRuntimeSessionTimeout'] = idle_timeout
            if max_lifetime is not None:
                lc['maxLifetime'] = max_lifetime
            if lc:
                kwargs['lifecycleConfiguration'] = lc

            resp = client.create_agent_runtime(**kwargs)

            wid = resp.get('workloadIdentityDetails', {}).get('workloadIdentityArn', '')
            return CreateRuntimeResponse(
                status=resp.get('status', 'CREATING'),
                agent_runtime_arn=resp.get('agentRuntimeArn', ''),
                agent_runtime_id=resp.get('agentRuntimeId', ''),
                agent_runtime_version=resp.get('agentRuntimeVersion', ''),
                created_at=str(resp.get('createdAt', '')),
                workload_identity_arn=wid,
                message='Runtime creation initiated.',
            )
        except Exception as e:
            return handle_runtime_error('CreateAgentRuntime', e)

    # -------------------------------------------------------------------- get
    async def get_agent_runtime(
        self,
        ctx: Context,
        agent_runtime_id: Annotated[
            str,
            Field(description='Runtime ID to retrieve.'),
        ],
        agent_runtime_version: Annotated[
            Optional[str],
            Field(description='Specific version to retrieve. Omit for latest.'),
        ] = None,
    ) -> Union[GetRuntimeResponse, ErrorResponse]:
        """Get details of an AgentCore Runtime including its configuration.

        This is a read-only operation with no cost implications.
        """
        try:
            client = self._get_client()
            kwargs: dict = {'agentRuntimeId': agent_runtime_id}
            if agent_runtime_version is not None:
                kwargs['agentRuntimeVersion'] = agent_runtime_version

            r = client.get_agent_runtime(**kwargs)

            wid = r.get('workloadIdentityDetails', {}).get('workloadIdentityArn', '')
            proto = r.get('protocolConfiguration', {}).get('serverProtocol', '')
            net = r.get('networkConfiguration', {}).get('networkMode', '')

            return GetRuntimeResponse(
                status='success',
                agent_runtime_arn=r.get('agentRuntimeArn', ''),
                agent_runtime_id=r.get('agentRuntimeId', ''),
                agent_runtime_name=r.get('agentRuntimeName', ''),
                agent_runtime_version=r.get('agentRuntimeVersion', ''),
                description=r.get('description', ''),
                role_arn=r.get('roleArn', ''),
                runtime_status=r.get('status', ''),
                failure_reason=r.get('failureReason', ''),
                created_at=str(r.get('createdAt', '')),
                last_updated_at=str(r.get('lastUpdatedAt', '')),
                protocol=proto,
                network_mode=net,
                lifecycle_configuration=r.get('lifecycleConfiguration'),
                environment_variables=r.get('environmentVariables'),
                workload_identity_arn=wid,
                message='Runtime retrieved.',
            )
        except Exception as e:
            return handle_runtime_error('GetAgentRuntime', e)

    # ----------------------------------------------------------------- update
    async def update_agent_runtime(
        self,
        ctx: Context,
        agent_runtime_id: Annotated[str, Field(description='Runtime ID to update.')],
        role_arn: Annotated[str, Field(description='IAM execution role ARN.')],
        network_mode: Annotated[
            str, Field(description='Network mode: "PUBLIC" or "VPC".')
        ] = 'PUBLIC',
        container_uri: Annotated[
            Optional[str], Field(description='Updated ECR container URI.')
        ] = None,
        code_s3_bucket: Annotated[
            Optional[str], Field(description='Updated S3 bucket for code deploy.')
        ] = None,
        code_s3_prefix: Annotated[
            Optional[str], Field(description='Updated S3 key/prefix for code zip.')
        ] = None,
        code_runtime: Annotated[
            Optional[str], Field(description='Updated Python runtime identifier.')
        ] = None,
        code_entry_point: Annotated[
            Optional[str], Field(description='Updated entry point (comma-separated).')
        ] = None,
        description: Annotated[Optional[str], Field(description='Updated description.')] = None,
        server_protocol: Annotated[
            Optional[str], Field(description='Updated protocol: "HTTP", "MCP", or "A2A".')
        ] = None,
        idle_timeout: Annotated[
            Optional[int], Field(description='Updated idle timeout in seconds.')
        ] = None,
        max_lifetime: Annotated[
            Optional[int], Field(description='Updated max lifetime in seconds.')
        ] = None,
        subnets: Annotated[
            Optional[str], Field(description='Comma-separated subnet IDs for VPC mode.')
        ] = None,
        security_groups: Annotated[
            Optional[str], Field(description='Comma-separated SG IDs for VPC mode.')
        ] = None,
    ) -> Union[UpdateRuntimeResponse, ErrorResponse]:
        """Update an AgentCore Runtime, creating a new immutable version.

        The DEFAULT endpoint automatically points to the new version.
        Custom endpoints must be updated separately.

        **Cost note:** Updating creates a new version. Active sessions
        continue using the previous version until they terminate.
        """
        try:
            client = self._get_client()

            artifact: dict = {}
            if container_uri:
                artifact['containerConfiguration'] = {'containerUri': container_uri}
            elif code_s3_bucket and code_s3_prefix:
                code_cfg: dict = {
                    'code': {
                        's3': {
                            'bucket': code_s3_bucket,
                            'prefix': code_s3_prefix,
                        }
                    },
                }
                if code_runtime:
                    code_cfg['runtime'] = code_runtime
                if code_entry_point:
                    code_cfg['entryPoint'] = [
                        s.strip() for s in code_entry_point.split(',') if s.strip()
                    ]
                artifact['codeConfiguration'] = code_cfg
            else:
                return UpdateRuntimeResponse(
                    status='error',
                    message=('Provide either container_uri or code_s3_bucket + code_s3_prefix.'),
                )

            net_cfg: dict = {'networkMode': network_mode}
            if network_mode == 'VPC':
                mode_cfg: dict = {}
                if subnets is not None:
                    mode_cfg['subnets'] = [s.strip() for s in subnets.split(',') if s.strip()]
                if security_groups is not None:
                    mode_cfg['securityGroups'] = [
                        s.strip() for s in security_groups.split(',') if s.strip()
                    ]
                net_cfg['networkModeConfig'] = mode_cfg

            kwargs: dict = {
                'agentRuntimeId': agent_runtime_id,
                'agentRuntimeArtifact': artifact,
                'networkConfiguration': net_cfg,
                'roleArn': role_arn,
            }
            if description is not None:
                kwargs['description'] = description
            if server_protocol is not None:
                kwargs['protocolConfiguration'] = {'serverProtocol': server_protocol}
            lc: dict = {}
            if idle_timeout is not None:
                lc['idleRuntimeSessionTimeout'] = idle_timeout
            if max_lifetime is not None:
                lc['maxLifetime'] = max_lifetime
            if lc:
                kwargs['lifecycleConfiguration'] = lc

            r = client.update_agent_runtime(**kwargs)
            return UpdateRuntimeResponse(
                status=r.get('status', 'UPDATING'),
                agent_runtime_arn=r.get('agentRuntimeArn', ''),
                agent_runtime_id=r.get('agentRuntimeId', ''),
                agent_runtime_version=r.get('agentRuntimeVersion', ''),
                last_updated_at=str(r.get('lastUpdatedAt', '')),
                message='Runtime update initiated (new version created).',
            )
        except Exception as e:
            return handle_runtime_error('UpdateAgentRuntime', e)

    # ----------------------------------------------------------------- delete
    async def delete_agent_runtime(
        self,
        ctx: Context,
        agent_runtime_id: Annotated[str, Field(description='Runtime ID to delete.')],
    ) -> Union[DeleteRuntimeResponse, ErrorResponse]:
        """Delete an AgentCore Runtime and all its versions.

        All endpoints must be deleted first. Active sessions will be
        terminated. This operation cannot be undone.
        """
        try:
            client = self._get_client()
            r = client.delete_agent_runtime(agentRuntimeId=agent_runtime_id)
            return DeleteRuntimeResponse(
                status='success',
                agent_runtime_id=r.get('agentRuntimeId', ''),
                runtime_status=r.get('status', 'DELETING'),
                message='Runtime deletion initiated.',
            )
        except Exception as e:
            return handle_runtime_error('DeleteAgentRuntime', e)

    # ------------------------------------------------------------------ list
    async def list_agent_runtimes(
        self,
        ctx: Context,
        max_results: Annotated[
            Optional[int], Field(description='Max results to return (1-100).')
        ] = None,
        next_token: Annotated[
            Optional[str], Field(description='Pagination token from previous response.')
        ] = None,
    ) -> Union[ListRuntimesResponse, ErrorResponse]:
        """List all AgentCore Runtimes in the account.

        This is a read-only operation with no cost implications.
        """
        try:
            client = self._get_client()
            kwargs: dict = {}
            if max_results is not None:
                kwargs['maxResults'] = max_results
            if next_token:
                kwargs['nextToken'] = next_token

            r = client.list_agent_runtimes(**kwargs)
            runtimes = [
                RuntimeSummary(
                    agent_runtime_arn=rt.get('agentRuntimeArn', ''),
                    agent_runtime_id=rt.get('agentRuntimeId', ''),
                    agent_runtime_name=rt.get('agentRuntimeName', ''),
                    agent_runtime_version=rt.get('agentRuntimeVersion', ''),
                    description=rt.get('description', ''),
                    last_updated_at=str(rt.get('lastUpdatedAt', '')),
                    runtime_status=rt.get('status', ''),
                )
                for rt in r.get('agentRuntimes', [])
            ]
            return ListRuntimesResponse(
                status='success',
                runtimes=runtimes,
                next_token=r.get('nextToken'),
                message=f'Found {len(runtimes)} runtime(s).',
            )
        except Exception as e:
            return handle_runtime_error('ListAgentRuntimes', e)

    # --------------------------------------------------------- list versions
    async def list_agent_runtime_versions(
        self,
        ctx: Context,
        agent_runtime_id: Annotated[str, Field(description='Runtime ID to list versions for.')],
        max_results: Annotated[Optional[int], Field(description='Max results (1-100).')] = None,
        next_token: Annotated[Optional[str], Field(description='Pagination token.')] = None,
    ) -> Union[ListRuntimeVersionsResponse, ErrorResponse]:
        """List all versions of a specific AgentCore Runtime.

        This is a read-only operation with no cost implications.
        """
        try:
            client = self._get_client()
            kwargs: dict = {'agentRuntimeId': agent_runtime_id}
            if max_results is not None:
                kwargs['maxResults'] = max_results
            if next_token:
                kwargs['nextToken'] = next_token

            r = client.list_agent_runtime_versions(**kwargs)
            versions = [
                RuntimeSummary(
                    agent_runtime_arn=v.get('agentRuntimeArn', ''),
                    agent_runtime_id=v.get('agentRuntimeId', ''),
                    agent_runtime_name=v.get('agentRuntimeName', ''),
                    agent_runtime_version=v.get('agentRuntimeVersion', ''),
                    description=v.get('description', ''),
                    last_updated_at=str(v.get('lastUpdatedAt', '')),
                    runtime_status=v.get('status', ''),
                )
                for v in r.get('agentRuntimes', [])
            ]
            return ListRuntimeVersionsResponse(
                status='success',
                versions=versions,
                next_token=r.get('nextToken'),
                message=f'Found {len(versions)} version(s).',
            )
        except Exception as e:
            return handle_runtime_error('ListAgentRuntimeVersions', e)
