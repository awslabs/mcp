"""AWS IoT SiteWise Access Policies and Configuration Management Tools."""

from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError
from mcp.server.fastmcp.tools import Tool

from awslabs.aws_iot_sitewise_mcp_server.tool_metadata import tool_metadata


@tool_metadata(readonly=True)
def describe_default_encryption_configuration(
    region: str = "us-east-1",
) -> Dict[str, Any]:
    """
    Retrieve information about the default encryption configuration for \
        your AWS account.

    Args:
        region: AWS region (default: us-east-1)

    Returns:
        Dictionary containing default encryption configuration
    """
    try:
        client = boto3.client("iotsitewise", region_name=region)

        response = client.describe_default_encryption_configuration()

        return {
            "success": True,
            "encryption_type": response["encryptionType"],
            "kms_key_id": response.get("kmsKeyId", ""),
            "configuration_status": response["configurationStatus"],
        }

    except ClientError as e:
        return {
            "success": False,
            "error": str(e),
            "error_code": e.response["Error"]["Code"],
        }


@tool_metadata(readonly=False)
def put_default_encryption_configuration(
    encryption_type: str, region: str = "us-east-1", kms_key_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Set the default encryption configuration for your AWS account.

    Args:
        encryption_type: The type of encryption used for the encryption \
            configuration (
            SITEWISE_DEFAULT_ENCRYPTION,
            KMS_BASED_ENCRYPTION)        region: AWS region (
                default: us-east-1)
        kms_key_id: The Key ID of the customer managed key used for KMS \
            encryption

    Returns:
        Dictionary containing encryption configuration response
    """
    try:
        client = boto3.client("iotsitewise", region_name=region)

        params: Dict[str, Any] = {"encryptionType": encryption_type}
        if kms_key_id:
            params["kmsKeyId"] = kms_key_id

        response = client.put_default_encryption_configuration(**params)

        return {
            "success": True,
            "encryption_type": response["encryptionType"],
            "kms_key_id": response.get("kmsKeyId", ""),
            "configuration_status": response["configurationStatus"],
        }

    except ClientError as e:
        return {
            "success": False,
            "error": str(e),
            "error_code": e.response["Error"]["Code"],
        }


@tool_metadata(readonly=True)
def describe_logging_options(region: str = "us-east-1") -> Dict[str, Any]:
    """
    Retrieve the current AWS IoT SiteWise logging options.

    Args:
        region: AWS region (default: us-east-1)

    Returns:
        Dictionary containing logging options
    """
    try:
        client = boto3.client("iotsitewise", region_name=region)

        response = client.describe_logging_options()

        return {"success": True, "logging_options": response["loggingOptions"]}

    except ClientError as e:
        return {
            "success": False,
            "error": str(e),
            "error_code": e.response["Error"]["Code"],
        }


@tool_metadata(readonly=False)
def put_logging_options(
    logging_options: Dict[str, Any], region: str = "us-east-1"
) -> Dict[str, Any]:
    """
    Set logging options for AWS IoT SiteWise.

    Args:
        logging_options: The logging options to set
        region: AWS region (default: us-east-1)

    Returns:
        Dictionary containing logging options response
    """
    try:
        client = boto3.client("iotsitewise", region_name=region)

        client.put_logging_options(loggingOptions=logging_options)
        return {"success": True, "message": "Logging options updated successfully"}

    except ClientError as e:
        return {
            "success": False,
            "error": str(e),
            "error_code": e.response["Error"]["Code"],
        }


@tool_metadata(readonly=True)
def describe_storage_configuration(region: str = "us-east-1") -> Dict[str, Any]:
    """
    Retrieve information about the storage configuration for your AWS account.

    Args:
        region: AWS region (default: us-east-1)

    Returns:
        Dictionary containing storage configuration
    """
    try:
        client = boto3.client("iotsitewise", region_name=region)

        response = client.describe_storage_configuration()

        return {
            "success": True,
            "storage_type": response["storageType"],
            "multi_layer_storage": response.get("multiLayerStorage", {}),
            "disassociated_data_storage": response.get(
                "disassociatedDataStorage", "ENABLED"
            ),
            "retention_period": response.get("retentionPeriod", {}),
            "configuration_status": response["configurationStatus"],
            "last_update_date": (
                response.get("lastUpdateDate", "").isoformat()
                if response.get("lastUpdateDate")
                else ""
            ),
        }

    except ClientError as e:
        return {
            "success": False,
            "error": str(e),
            "error_code": e.response["Error"]["Code"],
        }


@tool_metadata(readonly=False)
def put_storage_configuration(
    storage_type: str,
    region: str = "us-east-1",
    multi_layer_storage: Optional[Dict[str, Any]] = None,
    disassociated_data_storage: str = "ENABLED",
    retention_period: Optional[Dict[str, Any]] = None,
    warm_tier: str = "ENABLED",
    warm_tier_retention_period: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Configure storage settings for AWS IoT SiteWise.

    Args:
        storage_type: The storage tier that you specified for your data (
            SITEWISE_DEFAULT_STORAGE,
            MULTI_LAYER_STORAGE)        region: AWS region (default: us-east-1)
        multi_layer_storage: Identifies a storage destination
        disassociated_data_storage: Contains the storage configuration for \
            time series data that isn't associated with asset properties
        retention_period: How many days your data is kept in the hot tier
        warm_tier: A service managed storage tier optimized for analytical \
            queries (
            ENABLED,
            DISABLED)        warm_tier_retention_period: Set this period to \
                specify how long your data is stored in the warm tier

    Returns:
        Dictionary containing storage configuration response
    """
    try:
        client = boto3.client("iotsitewise", region_name=region)

        params: Dict[str, Any] = {
            "storageType": storage_type,
            "disassociatedDataStorage": disassociated_data_storage,
            "warmTier": warm_tier,
        }

        if multi_layer_storage:
            params["multiLayerStorage"] = multi_layer_storage
        if retention_period:
            params["retentionPeriod"] = retention_period
        if warm_tier_retention_period:
            params["warmTierRetentionPeriod"] = warm_tier_retention_period

        response = client.put_storage_configuration(**params)

        return {
            "success": True,
            "storage_type": response["storageType"],
            "multi_layer_storage": response.get("multiLayerStorage", {}),
            "disassociated_data_storage": response.get(
                "disassociatedDataStorage", "ENABLED"
            ),
            "retention_period": response.get("retentionPeriod", {}),
            "configuration_status": response["configurationStatus"],
            "warm_tier": response.get("warmTier", "ENABLED"),
            "warm_tier_retention_period": response.get("warmTierRetentionPeriod", {}),
        }

    except ClientError as e:
        return {
            "success": False,
            "error": str(e),
            "error_code": e.response["Error"]["Code"],
        }


# Create MCP tools

describe_default_encryption_configuration_tool = Tool.from_function(
    fn=describe_default_encryption_configuration,
    name="describe_default_encryption_config",
    description=(
        "Retrieve information about the default encryption "
        "configuration for AWS IoT SiteWise."
    ),
)

put_default_encryption_configuration_tool = Tool.from_function(
    fn=put_default_encryption_configuration,
    name="put_default_encryption_configuration",
    description="Set the default encryption configuration for AWS IoT \
        SiteWise.",
)

describe_logging_options_tool = Tool.from_function(
    fn=describe_logging_options,
    name="describe_logging_options",
    description="Retrieve the current AWS IoT SiteWise logging options.",
)

put_logging_options_tool = Tool.from_function(
    fn=put_logging_options,
    name="put_logging_options",
    description="Set logging options for AWS IoT SiteWise.",
)

describe_storage_configuration_tool = Tool.from_function(
    fn=describe_storage_configuration,
    name="describe_storage_configuration",
    description=(
        "Retrieve information about the storage configuration for " "AWS IoT SiteWise."
    ),
)

put_storage_configuration_tool = Tool.from_function(
    fn=put_storage_configuration,
    name="put_storage_configuration",
    description=(
        "Configure storage settings for AWS IoT SiteWise including "
        "multi-layer storage and retention policies."
    ),
)
