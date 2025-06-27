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
"""Embeddings generation for Git Repository Research MCP Server.

This module provides functionality for generating embeddings from text
using Amazon Bedrock models via LangChain.
"""

import os
from awslabs.git_repo_research_mcp_server.models import EmbeddingModel
from langchain_aws import BedrockEmbeddings
from langchain_core.embeddings.embeddings import Embeddings
from loguru import logger
from typing import Optional


def create_bedrock_embeddings(
    model_id: str = EmbeddingModel.AMAZON_TITAN_EMBED_TEXT_V2,
    aws_region: Optional[str] = None,
    aws_profile: Optional[str] = None,
) -> Embeddings:
    """Create and return an instance of BedrockEmbeddings.

    Args:
        model_id: ID of the embedding model to use
        aws_region: AWS region to use (optional, uses default if not provided)
        aws_profile: AWS profile to use (optional, uses default if not provided)

    Returns:
        BedrockEmbeddings: An instance of BedrockEmbeddings
    """
    aws_region = aws_region or os.environ.get('AWS_REGION', 'us-west-2')

    bedrock_embeddings = BedrockEmbeddings(
        model_id=model_id,
        region_name=aws_region,
        credentials_profile_name=aws_profile,
    )
    logger.info(f'Created BedrockEmbeddings with model: {model_id}')
    return bedrock_embeddings


def get_embedding_model(
    model_id: str = EmbeddingModel.AMAZON_TITAN_EMBED_TEXT_V2,
    aws_region: Optional[str] = None,
    aws_profile: Optional[str] = None,
) -> Embeddings:
    """Factory method to return a LangChain embedding model.

    Args:
        model_id: ID of the embedding model to use
        aws_region: AWS region to use (optional, uses default if not provided)
        aws_profile: AWS profile to use (optional, uses default if not provided)

    Returns:
        Embeddings instance
    """
    return create_bedrock_embeddings(model_id, aws_region, aws_profile)
