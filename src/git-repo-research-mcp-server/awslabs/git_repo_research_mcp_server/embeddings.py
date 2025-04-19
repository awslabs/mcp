"""Embeddings generation for Git Repository Research MCP Server.

This module provides functionality for generating embeddings from text
using AWS Bedrock models via LangChain.
"""

import os
from awslabs.git_repo_research_mcp_server.models import EmbeddingModel
from langchain_aws import BedrockEmbeddings
from loguru import logger
from typing import Optional


class EmbeddingGenerator:
    """Generator for text embeddings using AWS Bedrock via LangChain.

    This class provides methods for generating embeddings from text
    using AWS Bedrock embedding models.
    """

    def __init__(
        self,
        model_id: str = EmbeddingModel.AMAZON_TITAN_EMBED_TEXT_V2,
        aws_region: Optional[str] = None,
        aws_profile: Optional[str] = None,
    ):
        """Initialize the embedding generator.

        Args:
            model_id: ID of the embedding model to use
            aws_region: AWS region to use (optional, uses default if not provided)
            aws_profile: AWS profile to use (optional, uses default if not provided)
        """
        self.model_id = model_id
        self.aws_region = aws_region or os.environ.get('AWS_REGION', 'us-west-2')

        # Create LangChain BedrockEmbeddings
        self.bedrock_embeddings = BedrockEmbeddings(
            model_id=model_id,
            region_name=self.aws_region,
            credentials_profile_name=aws_profile,
        )
        logger.info(f'Initialized BedrockEmbeddings with model: {model_id}')


def get_embedding_generator(
    model_id: str = EmbeddingModel.AMAZON_TITAN_EMBED_TEXT_V2,
    aws_region: Optional[str] = None,
    aws_profile: Optional[str] = None,
) -> EmbeddingGenerator:
    """Get an embedding generator.

    Args:
        model_id: ID of the embedding model to use
        aws_region: AWS region to use (optional, uses default if not provided)
        aws_profile: AWS profile to use (optional, uses default if not provided)

    Returns:
        EmbeddingGenerator instance
    """
    return EmbeddingGenerator(model_id, aws_region, aws_profile)
