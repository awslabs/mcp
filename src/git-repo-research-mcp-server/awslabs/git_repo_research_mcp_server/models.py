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
"""Data models for Git Repository Research MCP Server."""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class GitHubConfig(BaseModel):
    """GitHub API configuration.

    This model defines the configuration for the GitHub API, including
    the optional token for authentication and the API URL.
    """

    token: Optional[str] = Field(None, description='GitHub API token for increased rate limits')
    api_url: str = Field(
        default='https://api.github.com/graphql', description='GitHub GraphQL API URL'
    )


class IndexMetadata(BaseModel):
    """Metadata for a repository index.

    This model stores information about an indexed repository, including
    its location, creation time, and statistics about the indexed content.
    """

    repository_name: str = Field(..., description='Name of the repository')
    repository_path: str = Field(..., description='Path or URL of the repository')
    index_path: str = Field(..., description='Path to the index file')
    created_at: datetime = Field(
        default_factory=datetime.now, description='When the index was created'
    )
    last_accessed: Optional[datetime] = Field(None, description='When the index was last accessed')
    file_count: int = Field(0, description='Number of files indexed')
    chunk_count: int = Field(0, description='Number of text chunks indexed')
    embedding_model: str = Field(..., description='Model used for embeddings')
    file_types: Dict[str, int] = Field(
        default_factory=dict, description='Count of file types indexed'
    )
    total_tokens: Optional[int] = Field(None, description='Total number of tokens processed')
    index_size_bytes: Optional[int] = Field(None, description='Size of the index in bytes')
    last_commit_id: Optional[str] = Field(
        None, description='ID of the last commit in the repository'
    )
    repository_directory: Optional[str] = Field(
        None, description='Path to the cloned repository directory'
    )


class SearchResult(BaseModel):
    """Result from a repository search.

    This model represents a single search result, including the file path,
    relevant content, and similarity score.
    """

    file_path: str = Field(..., description='Path to the file within the repository')
    content: str = Field(..., description='Relevant content snippet')
    score: float = Field(..., description='Similarity score (0-1)')
    line_numbers: Optional[List[int]] = Field(None, description='Line numbers for the content')
    metadata: Optional[Dict[str, str]] = Field(
        None, description='Additional metadata about the result'
    )


class SearchResponse(BaseModel):
    """Response from a repository search.

    This model represents the complete response from a search operation,
    including all matching results and query metadata.
    """

    results: List[SearchResult] = Field(default_factory=list, description='Search results')
    query: str = Field(..., description='Original search query')
    index_path: str = Field(..., description='Path to the index that was searched')
    repository_name: str = Field(..., description='Name of the repository')
    repository_directory: Optional[str] = Field(
        None, description='Path to the cloned repository directory'
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description='When the search was performed'
    )
    total_results: int = Field(0, description='Total number of results found')
    execution_time_ms: Optional[float] = Field(
        None, description='Search execution time in milliseconds'
    )


class IndexedRepositoryInfo(BaseModel):
    """Information about an indexed repository.

    This model provides a summary of an indexed repository for listing purposes.
    """

    repository_name: str = Field(..., description='Name of the repository')
    repository_path: str = Field(..., description='Path or URL of the repository')
    index_path: str = Field(..., description='Path to the index file')
    repository_directory: Optional[str] = Field(
        None, description='Path to the cloned repository directory'
    )
    created_at: datetime = Field(..., description='When the index was created')
    last_accessed: Optional[datetime] = Field(None, description='When the index was last accessed')
    file_count: int = Field(0, description='Number of files indexed')
    embedding_model: str = Field(..., description='Model used for embeddings')


class IndexedRepositoriesResponse(BaseModel):
    """Response containing a list of indexed repositories.

    This model represents the complete response from a list operation,
    including all indexed repositories and summary statistics.
    """

    repositories: List[IndexedRepositoryInfo] = Field(
        default_factory=list, description='List of indexed repositories'
    )
    total_count: int = Field(0, description='Total number of indexed repositories')
    index_directory: str = Field(..., description='Directory containing the indices')


class DetailedIndexedRepositoryInfo(IndexedRepositoryInfo):
    """Detailed information about an indexed repository.

    This model extends the basic repository info with additional details
    about the indexed content.
    """

    chunk_count: int = Field(0, description='Number of text chunks indexed')
    file_types: Dict[str, int] = Field(
        default_factory=dict, description='Count of file types indexed'
    )
    total_tokens: Optional[int] = Field(None, description='Total number of tokens processed')
    index_size_bytes: Optional[int] = Field(None, description='Size of the index in bytes')
    last_commit_id: Optional[str] = Field(
        None, description='ID of the last commit in the repository'
    )


class DetailedIndexedRepositoriesResponse(BaseModel):
    """Response containing detailed information about indexed repositories.

    This model represents the complete response from a detailed list operation,
    including all indexed repositories with detailed information.
    """

    repositories: List[DetailedIndexedRepositoryInfo] = Field(
        default_factory=list,
        description='List of indexed repositories with detailed information',
    )
    total_count: int = Field(0, description='Total number of indexed repositories')
    index_directory: str = Field(..., description='Directory containing the indices')
    total_index_size_bytes: Optional[int] = Field(
        None, description='Total size of all indices in bytes'
    )


class EmbeddingModel(str, Enum):
    """Available embedding models.

    This enum defines the available embedding models that can be used
    for generating embeddings from repository content.
    """

    AMAZON_TITAN_EMBED_TEXT_V1 = 'amazon.titan-embed-text-v1'
    AMAZON_TITAN_EMBED_TEXT_V2 = 'amazon.titan-embed-text-v2:0'
    COHERE_EMBED_ENGLISH_V3 = 'cohere.embed-english-v3'
    COHERE_EMBED_MULTILINGUAL_V3 = 'cohere.embed-multilingual-v3'


class IndexRepositoryResponse(BaseModel):
    """Response from indexing a repository.

    This model represents the complete response from an indexing operation,
    including metadata about the created index.
    """

    status: str = Field(..., description='Status of the indexing operation')
    repository_name: str = Field(..., description='Name of the repository')
    repository_path: str = Field(..., description='Path or URL of the repository')
    index_path: str = Field(..., description='Path to the created index')
    repository_directory: Optional[str] = Field(
        None, description='Path to the cloned repository directory'
    )
    file_count: int = Field(0, description='Number of files indexed')
    chunk_count: int = Field(0, description='Number of text chunks indexed')
    embedding_model: str = Field(..., description='Model used for embeddings')
    execution_time_ms: Optional[float] = Field(
        None, description='Indexing execution time in milliseconds'
    )
    message: Optional[str] = Field(
        None, description='Additional information about the indexing operation'
    )


class GitHubRepoSearchInput(BaseModel):
    """Input for GitHub repository search.

    This model defines the input parameters for searching GitHub repositories
    based on keywords and organizations.
    """

    keywords: List[str] = Field(description='List of keywords to search for GitHub repositories')
    organizations: Optional[List[str]] = Field(
        default=['aws-samples', 'aws-solutions-library-samples', 'awslabs'],
        description='List of GitHub organizations to scope the search to',
    )
    num_results: Optional[int] = Field(default=5, description='Number of results to return')
    license_filter: Optional[List[str]] = Field(
        default=None,
        description="List of licenses to filter by (e.g., 'Apache License 2.0', 'MIT No Attribution')",
    )


class GitHubRepoSearchResult(BaseModel):
    """Result from a GitHub repository search.

    This model represents a single GitHub repository search result.
    """

    url: str = Field(..., description='URL of the GitHub repository')
    title: str = Field(..., description='Title of the repository')
    description: Optional[str] = Field(None, description='Description of the repository')
    organization: str = Field(..., description='GitHub organization that owns the repository')
    stars: Optional[int] = Field(None, description='Number of stars the repository has')
    updated_at: Optional[str] = Field(None, description='When the repository was last updated')
    language: Optional[str] = Field(
        None, description='Primary programming language of the repository'
    )
    topics: Optional[List[str]] = Field(
        None, description='Topics/tags associated with the repository'
    )
    license: Optional[str] = Field(None, description='License of the repository')
    forks: Optional[int] = Field(None, description='Number of forks the repository has')
    open_issues: Optional[int] = Field(None, description='Number of open issues in the repository')
    homepage: Optional[str] = Field(None, description='Homepage URL of the repository')


class GitHubRepoSearchResponse(BaseModel):
    """Response from a GitHub repository search.

    This model represents the complete response from a GitHub repository search.
    """

    status: str = Field(..., description='Status of the search operation')
    query: str = Field(..., description='Original search query')
    organizations: List[str] = Field(..., description='Organizations that were searched')
    results: List[GitHubRepoSearchResult] = Field(
        default_factory=list, description='Search results'
    )
    total_results: int = Field(0, description='Total number of results found')
    execution_time_ms: Optional[float] = Field(
        None, description='Search execution time in milliseconds'
    )


class DeleteRepositoryResponse(BaseModel):
    """Response from deleting a repository.

    This model represents the complete response from a delete operation,
    including status and information about the deleted repository.
    """

    status: str = Field(
        ..., description='Status of the delete operation (success, partial, or error)'
    )
    message: str = Field(..., description='Information about the delete operation')
    repository_name: Optional[str] = Field(None, description='Name of the deleted repository')
    execution_time_ms: Optional[float] = Field(
        None, description='Delete operation execution time in milliseconds'
    )
    deleted_files: Optional[List[str]] = Field(
        None, description='List of files that were successfully deleted'
    )
    errors: Optional[List[str]] = Field(
        None, description='List of errors encountered during deletion'
    )
    permission_issues: Optional[List[str]] = Field(
        None, description='List of files with permission issues'
    )
