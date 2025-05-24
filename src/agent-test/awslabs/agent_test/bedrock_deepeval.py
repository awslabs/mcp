"""Bedrock model adapters for DeepEval.

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
"""

from deepeval.models.base_model import DeepEvalBaseEmbeddingModel, DeepEvalBaseLLM
from langchain_aws.chat_models import ChatBedrockConverse
from langchain_aws.embeddings import BedrockEmbeddings
from pydantic import BaseModel
from typing import List


class BedrockDeepEvalEmbeddingModel(DeepEvalBaseEmbeddingModel):
    """A wrapper around the BedrockEmbeddings model."""

    def __init__(
        self, model_id: str = 'amazon.titan-embed-text-v2:0', region_name: str = 'us-west-2'
    ):
        """Initialize the BedrockDeepEvalEmbeddingModel.

        Args:
            model_id (str): The ID of the Bedrock model to use. Defaults to 'amazon.titan-embed-text-v2:0'.
            region_name (str): The region of the Bedrock model. Defaults to 'us-west-2'.
        """
        self.model_id = model_id
        self.region_name = region_name

    def load_model(self):
        """Implements the abstract method from the base class."""
        return BedrockEmbeddings(
            model_id=self.model_id,
            region_name=self.region_name,
            normalize=True,
        )

    def embed_text(self, text: str) -> List[float]:
        """Implements the abstract method from the base class."""
        embedding_model = self.load_model()
        return embedding_model.embed_query(text)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Implements the abstract method from the base class."""
        embedding_model = self.load_model()
        return embedding_model.embed_documents(texts)

    async def a_embed_text(self, text: str) -> List[float]:
        """Implements the abstract method from the base class."""
        embedding_model = self.load_model()
        return await embedding_model.aembed_query(text)

    async def a_embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Implements the abstract method from the base class."""
        embedding_model = self.load_model()
        return await embedding_model.aembed_documents(texts)

    def get_model_name(self):
        """Implements the abstract method from the base class."""
        return self.model_id


class BedrockDeepEvalLLM(DeepEvalBaseLLM):
    """A wrapper around the BedrockConverse model."""

    def __init__(
        self,
        model_id: str,
        region_name: str,
        temperature: float = 0.0,
        max_tokens: int = 1000,
        top_p: float = 0.9999,
    ):
        """Initialize the BedrockDeepEvalLLM.

        Args:
            model_id (str): The ID of the Bedrock model to use.
            region_name (str): The region of the Bedrock model.
            temperature (float): The temperature of the model.
            max_tokens (int): The maximum number of tokens to generate.
            top_p (float): The top-p value.
        """
        self.model_id = model_id
        self.region_name = region_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.model = ChatBedrockConverse(
            model=model_id,
            region_name=region_name,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
        )

    def load_model(self):
        """Implements the abstract method from the base class."""
        return self.model

    def generate(self, prompt: str, schema: BaseModel) -> BaseModel:
        """Implements the abstract method from the base class."""
        structured_output_model = self.model.with_structured_output(schema)  # type: ignore
        messages = [{'role': 'user', 'content': prompt}]
        try:
            response = structured_output_model.invoke(messages)
            return response  # type: ignore
        except Exception as e:
            raise e

    async def a_generate(self, prompt: str, schema: BaseModel) -> BaseModel:
        """Implements the abstract method from the base class."""
        structured_output_model = self.model.with_structured_output(schema)  # type: ignore
        messages = [{'role': 'user', 'content': prompt}]
        try:
            response = await structured_output_model.ainvoke(messages)
            return response  # type: ignore
        except Exception as e:
            raise e

    def get_model_name(self) -> str:
        """Implements the abstract method from the base class."""
        return self.model_id
