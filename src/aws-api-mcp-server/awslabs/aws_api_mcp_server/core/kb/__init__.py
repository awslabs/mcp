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

from pathlib import Path
from typing import Protocol

from .dense_retriever import DenseRetriever
from awslabs.aws_api_mcp_server.scripts.download_latest_embeddings import (
    try_download_latest_embeddings,
)


class RAG(Protocol):
    def get_suggestions(self, query: str, **kwargs) -> dict[str, list[dict]]: ...


class KnowledgeBase:
    def __init__(self):
        self.rag: RAG | None = None

    def trim_text(self, text: str, max_length: int) -> str:
        return f'{text[:max_length]}...' if len(text) > max_length else text

    def setup(self, **kwargs):
        self.rag = DenseRetriever(**kwargs)
        cache_file = self.rag.get_cache_file_with_version()
        if not cache_file or not Path(cache_file).exists():
            success = try_download_latest_embeddings()
            if not success:
                raise FileNotFoundError(
                    'No embeddings file found. You can generate them by running: python -m awslabs.aws_api_mcp_server.scripts.generate_embeddings'
                )

    def get_suggestions(self, query: str, **kwargs):
        if self.rag is None:
            raise RuntimeError('RAG is not initialized. Call setup first.')

        results = self.rag.get_suggestions(query, **kwargs)

        for result in results['suggestions']:
            result['description'] = self.trim_text(result['description'], 1000)
            for key, value in result['parameters'].items():
                if isinstance(value, str):
                    result['parameters'][key] = self.trim_text(value, 500)
        return results


knowledge_base = KnowledgeBase()
