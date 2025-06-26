"""
Amazon Q Business anonymous mode MCP Server

This module provides a Model Context Protocol (MCP) server for interacting with Amazon Q Business created using anonymous mode.
It allows users to query Amazon Q Business through an MCP tool interface, handling authentication,
error management, and response formatting automatically.

Features:
- Synchronous chat queries to Amazon Q Business
- Comprehensive error handling and validation
- Environment-based configuration

Required Environment Variables:
    AWS_REGION: The AWS region where your Q Business application is deployed
    QBUSINESS_APPLICATION_ID: The unique identifier for your Q Business application
    
AWS Credentials:
    This module requires valid AWS credentials to be configured. Credentials can be provided via:
    - AWS CLI configuration (~/.aws/credentials)
    - Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN)
    - IAM roles (when running on EC2 or other AWS services)
    - AWS SSO profiles

Usage:
    Run as an MCP server:
        uv run qbiz.py
    
    Or import and use the functions directly:
        from qbiz import qbiz_local_query
        response = qbiz_local_query("What is our company policy?")
    
    Or configure in mcp.json as below
    "qbiz": {
        "command": "uv",
        "args": [
            "--directory",
            "<REPLACE-WITH-FULL-PATH-FOR-qbiz-mcp-server-DIRECTORY>",
            "run",
            "qbiz.py"
        ],
        "env": {
            "QBUSINESS_APPLICATION_ID":"<REPLACE-WITH-YOUR-AMAZON-Q-BUSINESS-APPLICATION-ID>",
            "AWS_REGION":"<REPLACE-WITH-YOUR-AWS-REGION>",
            "AWS_ACCESS_KEY_ID":"<REPLACE-WITH-YOUR-AWS-ACCESS-KEY>",
            "AWS_SECRET_ACCESS_KEY":"<REPLACE-WITH-YOUR-AWS-SECRET-ACCESS-KEY>",
            "AWS_SESSION_TOKEN":"<REPLACE-WITH-YOUR-AWS-SESSION-TOKEN>"
        }
    }

Dependencies:
    - boto3: AWS SDK for Python
    - mcp: Model Context Protocol library
    - Standard library modules: os, secrets, json

Version: 0.1.0
"""

from typing import Any, Dict
import httpx
from mcp.server.fastmcp import FastMCP

import boto3
import secrets
import os
import json
from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError

mcp = FastMCP("qbiz-local")

def get_qbiz_client() -> boto3.client:
    """
    Create and return an Amazon Q Business client.
    
    Returns:
        boto3.client: Configured Q Business client instance
        
    Raises:
        Exception: If AWS_REGION environment variable is not set
        Exception: If AWS credentials are not found or configured
        Exception: If client creation fails for any other reason
        
    Environment Variables:
        AWS_REGION: The AWS region where Q Business is deployed
    """
    try:
        region = os.getenv('AWS_REGION')
        if not region:
            raise ValueError("AWS_REGION environment variable is not set")
        
        aq_client = boto3.client('qbusiness', region_name=region)
        return aq_client
    except NoCredentialsError:
        raise Exception("AWS credentials not found. Please configure your AWS credentials.")
    except Exception as e:
        raise Exception(f"Failed to create Q Business client: {str(e)}")

def make_query(client: boto3.client, query: str) -> Dict[str, Any]:
    """
    Execute a synchronous chat query against Amazon Q Business.
    
    Args:
        client (boto3.client): Configured Q Business client
        query (str): The user's question or query to send to Q Business
        
    Returns:
        Dict[str, Any]: Raw response from Q Business API containing systemMessage and metadata
        
    Raises:
        Exception: If QBUSINESS_APPLICATION_ID environment variable is not set
        Exception: If Amazon Q Business API returns an error
        Exception: If the query fails for any other reason
        
    Environment Variables:
        QBUSINESS_APPLICATION_ID: The ID of the Q Business application to query
    """
    try:
        app_id = os.getenv('QBUSINESS_APPLICATION_ID')
        if not app_id:
            raise ValueError("QBUSINESS_APPLICATION_ID environment variable is not set")
        
        resp = client.chat_sync(
            applicationId=app_id,
            userMessage=query,
            clientToken=str(secrets.SystemRandom().randint(0, 10000))
        )
        return resp
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        raise Exception(f"Amazon Q Business API error ({error_code}): {error_message}")
    except Exception as e:
        raise Exception(f"Failed to query Q Business: {str(e)}")

@mcp.tool()
def qbiz_local_query(query: str) -> str:
    """
    MCP tool to query Amazon Q Business and return a formatted response.
    
    This tool provides a Model Context Protocol interface for querying Amazon Q Business.
    It handles client initialization, query execution, and error handling automatically.
    
    Args:
        query (str): The question or query to send to Q Business
        
    Returns:
        str: Formatted response from Q Business or error message if the query fails
        
    Examples:
        >>> qbiz_local_query("What is our company policy on remote work?")
        "Qbiz response: According to company policy..."
        
        >>> qbiz_local_query("")
        "Error: Query cannot be empty"
        
    Note:
        Requires the following environment variables to be set:
        - AWS_REGION: AWS region where Q Business is deployed
        - QBUSINESS_APPLICATION_ID: ID of the Q Business application
        - AWS credentials must be configured (via AWS CLI, IAM roles, etc.)
    """
    try:
        if not query or not query.strip():
            return "Error: Query cannot be empty"
        
        client = get_qbiz_client()
        resp = make_query(client, query)
        
        # Check if response has the expected structure
        if 'systemMessage' not in resp:
            return f"Error: Unexpected response format from Q Business: {resp}"
        
        return f"Qbiz response: {resp['systemMessage']}"
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')