"""Common utilities, imports, and constants for DataZone MCP Server tools."""

import logging
from typing import Any, Dict, List, Optional

import boto3
import httpx
from botocore.exceptions import ClientError

# Constants
USER_AGENT = "datazone-app/1.0"

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize boto3 client
datazone_client = boto3.client("datazone")
