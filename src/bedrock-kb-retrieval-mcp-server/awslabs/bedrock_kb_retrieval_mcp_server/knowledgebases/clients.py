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
import boto3
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from mypy_boto3_bedrock_agent.client import AgentsforBedrockClient
    from mypy_boto3_bedrock_agent_runtime.client import AgentsforBedrockRuntimeClient
else:
    AgentsforBedrockClient = object
    AgentsforBedrockRuntimeClient = object


def get_bedrock_agent_runtime_client(
    region_name: str | None = 'us-west-2', profile_name: str | None = None
) -> AgentsforBedrockRuntimeClient:
    """Get a Bedrock agent runtime client.

    You access knowledge bases for RAG via the Bedrock agent runtime client.

    Args:
        region_name (str | None): The region name
        profile_name (str | None): The profile name
    """
    if profile_name:
        client = boto3.Session(profile_name=profile_name).client(
            'bedrock-agent-runtime', region_name=region_name or 'us-west-2'
        )
        return client  # type: ignore
    client = boto3.client('bedrock-agent-runtime', region_name=region_name or 'us-west-2')
    return client  # type: ignore


def get_bedrock_agent_client(
    region_name: str | None = 'us-west-2', profile_name: str | None = None
) -> AgentsforBedrockClient:
    """Get a Bedrock agent management client.

    You access configuration and management of Knowledge Bases via the Bedrock agent client.

    Args:
        region_name (str | None): The region name
        profile_name (str | None): The profile name
    """
    if profile_name:
        client = boto3.Session(profile_name=profile_name).client(
            'bedrock-agent', region_name=region_name or 'us-west-2'
        )
        return client  # type: ignore
    client = boto3.client('bedrock-agent', region_name=region_name or 'us-west-2')
    return client  # type: ignore
