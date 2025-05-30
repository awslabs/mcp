# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
"""Search functionality for Git Repository Research MCP Server.

This module provides functionality for searching within indexed Git repositories
using LangChain's FAISS implementation.
"""

import os
import time
from awslabs.git_repo_research_mcp_server.defaults import Constants
from awslabs.git_repo_research_mcp_server.embeddings import get_embedding_model
from awslabs.git_repo_research_mcp_server.indexer import (
    IndexConfig,
    get_docstore_dict_size,
    get_repository_indexer,
)
from awslabs.git_repo_research_mcp_server.models import (
    EmbeddingModel,
    SearchResponse,
    SearchResult,
)
from loguru import logger
from typing import Optional


class RepositorySearcher:
    """Searcher for indexed Git repositories using LangChain.

    This class provides methods for searching within indexed Git repositories.
    """

    def __init__(
        self,
        embedding_model: str = EmbeddingModel.AMAZON_TITAN_EMBED_TEXT_V2,
        aws_region: Optional[str] = None,
        aws_profile: Optional[str] = None,
        index_dir: Optional[str] = None,
    ):
        """Initialize the repository searcher.

        Args:
            embedding_model: ID of the embedding model to use
            aws_region: AWS region to use (optional, uses default if not provided)
            aws_profile: AWS profile to use (optional, uses default if not provided)
            index_dir: Directory where indices are stored (optional, uses default if not provided)
        """
        self.embedding_model = embedding_model
        self.aws_region = aws_region
        self.aws_profile = aws_profile
        self.index_dir = index_dir or os.path.expanduser(f'~/{Constants.DEFAULT_INDEX_DIR}')

        self.config = IndexConfig(
            embedding_model=embedding_model,
            aws_region=aws_region,
            aws_profile=aws_profile,
            index_dir=index_dir or os.path.expanduser(f'~/{Constants.DEFAULT_INDEX_DIR}'),
        )

        # Initialize the embedding generator
        self.embedding_generator = get_embedding_model(
            model_id=embedding_model,
            aws_region=aws_region,
            aws_profile=aws_profile,
        )

        # Initialize the repository indexer
        self.repository_indexer = get_repository_indexer(self.config)

    def list_repository_files(self, repository_name: str) -> Optional[str]:
        """Generate a directory tree structure of the repository files.

        Args:
            repository_name: Name of the repository

        Returns:
            String representation of the directory tree, or None if repository not found
        """
        # Get the index path for the repository
        index_path = self.repository_indexer._get_index_path(repository_name)

        # Construct the path to the repository directory
        repo_files_path = os.path.join(index_path, 'repository')

        # Check if the repository directory exists
        if not os.path.exists(repo_files_path) or not os.path.isdir(repo_files_path):
            logger.warning(f'Repository directory not found: {repo_files_path}')
            return None

        try:
            # Generate the directory tree
            tree = self._generate_directory_tree(repo_files_path)
            return tree
        except Exception as e:
            logger.error(f'Error generating directory tree for {repository_name}: {e}')
            return None

    def _generate_directory_tree(self, path: str) -> str:
        """Generate a directory tree structure for a given path.

        Args:
            path: Path to the directory

        Returns:
            String representation of the directory tree
        """
        # Get the base name of the path
        base_name = os.path.basename(path)

        # Initialize the tree string
        tree = f'Directory structure:\n└── {base_name}/\n'

        # Generate the tree recursively
        tree += self._generate_tree(path, '', base_name)

        return tree

    def _generate_tree(self, path: str, prefix: str, base_path: str) -> str:
        """Recursively generate a directory tree structure.

        Args:
            path: Path to the current directory
            prefix: Prefix for the current line
            base_path: Base path to remove from the full path

        Returns:
            String representation of the directory tree
        """
        # Get all entries in the directory
        entries = sorted(os.listdir(path))

        # Filter out hidden files and directories
        entries = [e for e in entries if not e.startswith('.')]

        # Initialize the tree string
        tree = ''

        # Process each entry
        for i, entry in enumerate(entries):
            # Construct the full path
            full_path = os.path.join(path, entry)

            # Check if this is the last entry
            is_last = i == len(entries) - 1

            # Add the entry to the tree
            if is_last:
                tree += f'{prefix}    └── '
                new_prefix = prefix + '    '
            else:
                tree += f'{prefix}    ├── '
                new_prefix = prefix + '    │'

            # Check if the entry is a directory
            if os.path.isdir(full_path):
                # Add the directory name
                tree += f'{entry}/\n'

                # Recursively process the directory
                # Always include the directory in the tree, even if it's empty
                subtree = self._generate_tree(full_path, new_prefix, base_path)
                tree += subtree
            else:
                # Add the file name
                tree += f'{entry}\n'

        return tree

    def search(
        self,
        index_path: str,
        query: str,
        limit: int = 10,
        threshold: float = 0.0,
    ) -> SearchResponse:
        """Search within an indexed repository using LangChain's FAISS implementation.

        Args:
            index_path: Path to the index file or repository name
            query: Search query text
            limit: Maximum number of results to return
            threshold: Similarity threshold for results (0.0-1.0)

        Returns:
            SearchResponse object with search results

        Raises:
            Exception: If search fails
        """
        start_time = time.time()
        # Initialize repository_name with a default value outside the try block
        repository_name = 'unknown'

        try:
            # Check if index_path is a repository name or a file path
            if os.path.exists(index_path) and os.path.isdir(index_path):
                # It's a directory path, extract the repository name
                repository_name = os.path.basename(index_path)
            else:
                # It's a repository name
                repository_name = index_path
                index_path = self.repository_indexer._get_index_path(repository_name)

            # Load the index and chunk map
            vector_store = self.repository_indexer.load_index_without_pickle(index_path)
            if vector_store is None:
                logger.error(f'Index or chunk map not found for repository {repository_name}')
                # Set repository_directory even if index is not found
                repo_files_path = os.path.join(index_path, 'repository')
                return SearchResponse(
                    results=[],
                    query=query,
                    index_path=index_path,
                    repository_name=repository_name,
                    repository_directory=repo_files_path,
                    total_results=0,
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            # Use LangChain's similarity search
            logger.info(f"Searching for '{query}' in repository {repository_name}")

            # Debug: Print vector store info
            logger.info(f'Vector store type: {type(vector_store)}')
            logger.info(
                f'Vector store docstore size: {get_docstore_dict_size(vector_store.docstore)}'
            )

            # Use the same approach as in the test script
            try:
                # Use similarity_search directly
                langchain_results = vector_store.similarity_search(query, k=limit)

                # Process the results
                results = []
                if langchain_results:
                    logger.info(f'Found {len(langchain_results)} results')
                    for doc in langchain_results:
                        # Get file path from document metadata
                        file_path = doc.metadata.get('source', 'unknown')

                        # Create a search result
                        result = SearchResult(
                            file_path=file_path,
                            content=doc.page_content,
                            score=1.0,  # Default score since we're not using similarity_search_with_score
                            line_numbers=None,  # We don't track line numbers currently
                            metadata={'chunk_id': str(doc.metadata.get('chunk_id', -1))},
                        )
                        results.append(result)
                else:
                    logger.info('No results found')
            except Exception as e:
                logger.error(f'Error with similarity_search: {e}')
                # Try with similarity_search_with_score as a fallback
                try:
                    logger.info('Trying with similarity_search_with_score as fallback')
                    langchain_results = vector_store.similarity_search_with_score(query, k=limit)

                    # Process the results
                    results = []
                    for doc, score in langchain_results:
                        # Get file path from document metadata
                        file_path = doc.metadata.get('source', 'unknown')

                        # Convert score to similarity (0-1 range)
                        similarity = 1.0 - min(1.0, score / 2.0)

                        # Create a search result
                        result = SearchResult(
                            file_path=file_path,
                            content=doc.page_content,
                            score=float(similarity),
                            line_numbers=None,  # We don't track line numbers currently
                            metadata={
                                'distance': str(float(score)),
                                'chunk_id': str(doc.metadata.get('chunk_id', -1)),
                            },
                        )
                        results.append(result)
                except Exception as e:
                    logger.error(f'Error with similarity_search_with_score fallback: {e}')
                    results = []

            execution_time_ms = int((time.time() - start_time) * 1000)
            logger.info(f'Search completed in {execution_time_ms}ms, found {len(results)} results')

            # Add repository directory information to the response
            repo_files_path = os.path.join(index_path, 'repository')

            # Always set repository_directory to the expected path
            repository_directory = repo_files_path

            return SearchResponse(
                results=results,
                query=query,
                index_path=index_path,
                repository_name=repository_name,
                repository_directory=repository_directory,
                total_results=len(results),
                execution_time_ms=execution_time_ms,
            )

        except Exception as e:
            logger.error(f'Error searching repository: {e}')
            # repository_name is already defined outside the try block
            # Set repository_directory even in case of error
            repo_files_path = os.path.join(index_path, 'repository')
            return SearchResponse(
                results=[],
                query=query,
                index_path=index_path,
                repository_name=repository_name,
                repository_directory=repo_files_path,
                total_results=0,
                execution_time_ms=int((time.time() - start_time) * 1000),
            )


def get_repository_searcher(
    embedding_model: str = EmbeddingModel.AMAZON_TITAN_EMBED_TEXT_V2,
    aws_region: Optional[str] = None,
    aws_profile: Optional[str] = None,
    index_dir: Optional[str] = None,
) -> RepositorySearcher:
    """Factory method to return a repository searcher.

    Args:
        embedding_model: ID of the embedding model to use
        aws_region: AWS region to use (optional, uses default if not provided)
        aws_profile: AWS profile to use (optional, uses default if not provided)
        index_dir: Directory where indices are stored (optional, uses default if not provided)

    Returns:
        RepositorySearcher instance
    """
    return RepositorySearcher(
        embedding_model=embedding_model,
        aws_region=aws_region,
        aws_profile=aws_profile,
        index_dir=index_dir,
    )
