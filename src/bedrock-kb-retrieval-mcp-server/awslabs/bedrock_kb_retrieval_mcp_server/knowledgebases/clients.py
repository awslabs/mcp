import boto3
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from mypy_boto3_bedrock_agent.client import AgentsforBedrockClient
    from mypy_boto3_bedrock_agent_runtime.client import AgentsforBedrockRuntimeClient
else:
    AgentsforBedrockClient = object
    AgentsforBedrockRuntimeClient = object


def get_bedrock_agent_runtime_client(
    region_name: str = "us-west-2", profile_name: str | None = None
) -> AgentsforBedrockRuntimeClient:
    """Get a Bedrock agent runtime client.

    You access knowledge bases for RAG via the Bedrock agent runtime client.

    Args:
        region_name (str): The region name
        profile_name (str | None): The profile name
    """
    if profile_name:
        return boto3.Session(profile_name=profile_name).client(
            "bedrock-agent-runtime", region_name=region_name
        )
    return boto3.client("bedrock-agent-runtime", region_name=region_name)


def get_bedrock_agent_client(
    region_name: str = "us-west-2", profile_name: str | None = None
) -> AgentsforBedrockClient:
    """Get a Bedrock agent management client.

    You access configuration and management of Knowledge Bases via the Bedrock agent client.

    Args:
        region_name (str): The region name
        profile_name (str | None): The profile name
    """
    if profile_name:
        return boto3.Session(profile_name=profile_name).client(
            "bedrock-agent", region_name=region_name
        )
    return boto3.client("bedrock-agent", region_name=region_name)
