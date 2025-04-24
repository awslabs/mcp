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
"""FAISS indexing for Git Repository Research MCP Server using LangChain.

This module provides functionality for creating and managing FAISS indices
for Git repositories using LangChain's FAISS implementation.
"""

import faiss
import json
import os
import shutil
import time
from awslabs.git_repo_research_mcp_server.embeddings import get_embedding_generator
from awslabs.git_repo_research_mcp_server.models import (
    Constants,
    EmbeddingModel,
    IndexMetadata,
    IndexRepositoryResponse,
)
from awslabs.git_repo_research_mcp_server.repository import (
    cleanup_repository,
    clone_repository,
    get_repository_name,
    is_git_repo,
    is_git_url,
    process_repository,
)
from datetime import datetime
from git import Repo
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from loguru import logger
from pydantic import BaseModel, field_validator
from pydantic_core.core_schema import ValidationInfo
from typing import Any, Dict, List, Optional, Tuple


class RepositoryConfig(BaseModel):
    """Configuration for repository indexing.

    This class defines the configuration parameters for indexing a Git repository,
    including paths, patterns for file inclusion/exclusion, and chunking parameters.
    """

    repository_path: str
    output_path: Optional[str] = None
    include_patterns: Optional[List[str]] = None
    exclude_patterns: Optional[List[str]] = None
    chunk_size: int = 1000
    chunk_overlap: int = 200

    @field_validator('repository_path')
    @classmethod
    def validate_repository_path(cls, git_string_url):
        """Validate the repository path.

        :param git_string_url: Git URL or local path
        :return: Validated repository path.
        """
        if not (is_git_url(git_string_url) or os.path.exists(git_string_url)):
            raise ValueError('Repository path must be a valid Git URL or existing local path')
        return git_string_url

    @field_validator('chunk_size')
    @classmethod
    def validate_chunk_size(cls, chunk_size):
        """Validate the chunk size.

        :param chunk_size: Chunk size value
        :return: Validated chunk size.
        """
        if chunk_size <= 0:
            raise ValueError('Chunk size must be positive')
        return chunk_size

    @field_validator('chunk_overlap')
    @classmethod
    def validate_chunk_overlap(cls, v: int, info: ValidationInfo) -> int:
        """Validate the chunk overlap.

        Args:
            v: Chunk overlap value
            info: Validation context information

        Returns:
            Validated chunk overlap value.
        """
        chunk_size = info.data.get('chunk_size', None)
        if chunk_size is not None and v >= chunk_size:
            raise ValueError('Chunk overlap must be less than chunk size')
        return v


class IndexConfig(BaseModel):
    """Configuration for the indexing process.

    This class defines the configuration parameters for the indexing process,
    including the embedding model and AWS-specific settings.
    """

    embedding_model: str
    aws_region: Optional[str] = None
    aws_profile: Optional[str] = None
    index_dir: Optional[str] = None

    @field_validator('embedding_model')
    @classmethod
    def validate_embedding_model(cls, embedding_model):
        """Validate the embedding model.

        Args:
            embedding_model: AWS embedding model

        Returns:
            Validated embedding model string.
        """
        if embedding_model not in EmbeddingModel.__members__.values():
            raise ValueError(
                f'Invalid embedding model. Must be one of: {list(EmbeddingModel.__members__.values())}'
            )
        return embedding_model

    @field_validator('aws_region')
    @classmethod
    def validate_aws_region(cls, aws_region_string):
        """Validate the AWS region.

        Args:
            aws_region_string: AWS region string

        Returns:
            Validated AWS region string.
        """
        # Allow any region format or None
        return aws_region_string


def get_docstore_dict(docstore):
    """Safely get the document dictionary from a docstore.

    Args:
        docstore: LangChain docstore object

    Returns:
        Document dictionary if _dict exists, empty dict otherwise
    """
    return docstore._dict if hasattr(docstore, '_dict') else {}


def ensure_docstore_dict(docstore):
    """Ensure the docstore has a _dict attribute.

    Args:
        docstore: LangChain docstore object

    Returns:
        The docstore's _dict (creating it if needed)
    """
    if not hasattr(docstore, '_dict'):
        docstore._dict = {}
    return docstore._dict


def get_docstore_dict_size(docstore):
    """Safely get the size of the document dictionary from a docstore.

    Args:
        docstore: LangChain docstore object

    Returns:
        Size of document dictionary if _dict exists, 0 otherwise
    """
    return len(get_docstore_dict(docstore))


def save_index_without_pickle(vector_store, index_path):
    """Save FAISS index without using pickle.

    Args:
        vector_store: FAISS vector store
        index_path: Path to save the index

    This function saves a FAISS index using FAISS's native methods and JSON
    instead of pickle for serialization.
    """
    os.makedirs(index_path, exist_ok=True)

    # 1. Save FAISS index using faiss's native methods
    faiss_path = os.path.join(index_path, 'index.faiss')
    faiss.write_index(vector_store.index, faiss_path)

    # 2. Save docstore as JSON
    docstore_path = os.path.join(index_path, 'docstore.json')
    docstore_data = {}
    for doc_id, doc in get_docstore_dict(vector_store.docstore).items():
        docstore_data[doc_id] = {'page_content': doc.page_content, 'metadata': doc.metadata}

    with open(docstore_path, 'w') as f:
        json.dump(docstore_data, f)

    # 3. Save index_to_docstore_id mapping as JSON
    mapping_path = os.path.join(index_path, 'index_mapping.json')
    # Convert numeric keys to strings for JSON serialization
    mapping = {str(k): v for k, v in vector_store.index_to_docstore_id.items()}
    with open(mapping_path, 'w') as f:
        json.dump(mapping, f)


def load_index_without_pickle(index_path, embedding_function):
    """Load FAISS index without using pickle.

    Args:
        index_path: Path to the index
        embedding_function: Embedding function to use

    Returns:
        FAISS vector store

    This function loads a FAISS index using FAISS's native methods and JSON
    instead of pickle for serialization.
    """
    # 1. Load FAISS index using faiss's native methods
    faiss_path = os.path.join(index_path, 'index.faiss')
    index = faiss.read_index(faiss_path)

    # 2. Load docstore from JSON
    docstore_path = os.path.join(index_path, 'docstore.json')
    with open(docstore_path, 'r') as f:
        docstore_data = json.load(f)

    # Reconstruct the document store
    docstore = InMemoryDocstore({})
    for doc_id, doc_data in docstore_data.items():
        dict_obj = ensure_docstore_dict(docstore)
        dict_obj[doc_id] = Document(
            page_content=doc_data['page_content'], metadata=doc_data['metadata']
        )

    # 3. Load index_to_docstore_id mapping from JSON
    mapping_path = os.path.join(index_path, 'index_mapping.json')
    with open(mapping_path, 'r') as f:
        mapping_data = json.load(f)

    # Convert string keys back to integers for the mapping
    index_to_docstore_id = {int(k): v for k, v in mapping_data.items()}

    # 4. Create and return the FAISS vector store
    return FAISS(
        embedding_function=embedding_function,
        index=index,
        docstore=docstore,
        index_to_docstore_id=index_to_docstore_id,
    )


def save_chunk_map_without_pickle(chunk_map, index_path):
    """Save chunk map without using pickle.

    Args:
        chunk_map: Chunk map to save
        index_path: Path to save the chunk map

    This function saves a chunk map using JSON instead of pickle for serialization.
    """
    # Convert the chunk map to a JSON-serializable format
    serializable_chunk_map = {'chunks': chunk_map['chunks'], 'chunk_to_file': {}}

    # Convert the chunk_to_file dictionary to a serializable format
    # Since chunks are not hashable in JSON, we use indices
    for i, chunk in enumerate(chunk_map['chunks']):
        if chunk in chunk_map['chunk_to_file']:
            serializable_chunk_map['chunk_to_file'][str(i)] = chunk_map['chunk_to_file'][chunk]

    # Save as JSON
    chunk_map_path = os.path.join(index_path, 'chunk_map.json')
    with open(chunk_map_path, 'w') as f:
        json.dump(serializable_chunk_map, f)


def load_chunk_map_without_pickle(index_path):
    """Load chunk map without using pickle.

    Args:
        index_path: Path to the chunk map

    Returns:
        Chunk map dictionary if found, None otherwise

    This function loads a chunk map using JSON instead of pickle for serialization.
    """
    chunk_map_path = os.path.join(index_path, 'chunk_map.json')

    if not os.path.exists(chunk_map_path):
        return None

    try:
        with open(chunk_map_path, 'r') as f:
            serialized_map = json.load(f)

        # Reconstruct the chunk-to-file mapping
        chunks = serialized_map['chunks']
        chunk_to_file = {}
        for i, chunk in enumerate(chunks):
            if str(i) in serialized_map['chunk_to_file']:
                chunk_to_file[chunk] = serialized_map['chunk_to_file'][str(i)]

        return {'chunks': chunks, 'chunk_to_file': chunk_to_file}
    except Exception as e:
        logger.error(f'Error loading chunk map: {e}')
        return None


class RepositoryIndexer:
    """Indexer for Git repositories using LangChain's FAISS implementation.

    This class provides methods for creating and managing FAISS indices
    for Git repositories.
    """

    def __init__(self, config: IndexConfig):
        """Initialize the repository indexer.

        Args:
            config: IndexConfig object with indexer configuration
        """
        self.embedding_model = config.embedding_model
        self.aws_region = config.aws_region
        self.aws_profile = config.aws_profile
        self.index_dir = config.index_dir or os.path.expanduser(f'~/{Constants.DEFAULT_INDEX_DIR}')

        # Create the index directory if it doesn't exist
        os.makedirs(self.index_dir, exist_ok=True)

        # Initialize the embedding generator
        self.embedding_generator = get_embedding_generator(
            model_id=self.embedding_model,
            aws_region=self.aws_region,
            aws_profile=self.aws_profile,
        )

    def _get_index_path(self, repository_name: str) -> str:
        """Get the path to the index directory for a repository.

        Args:
            repository_name: Name of the repository

        Returns:
            Path to the index directory
        """
        # Sanitize the repository name for use in a filename
        sanitized_name = ''.join(c if c.isalnum() or c in '-_' else '_' for c in repository_name)
        return os.path.join(self.index_dir, sanitized_name)

    def _get_metadata_path(self, repository_name: str) -> str:
        """Get the path to the metadata file for a repository.

        Args:
            repository_name: Name of the repository

        Returns:
            Path to the metadata file
        """
        # Store metadata file in the repository's index directory
        index_path = self._get_index_path(repository_name)
        return os.path.join(index_path, 'metadata.json')

    def _get_chunk_map_path(self, repository_name: str) -> str:
        """Get the path to the chunk map file for a repository.

        Args:
            repository_name: Name of the repository

        Returns:
            Path to the chunk map file
        """
        # Store chunk map file in the repository's index directory
        index_path = self._get_index_path(repository_name)
        return os.path.join(index_path, 'chunk_map.json')

    async def index_repository(
        self,
        config: RepositoryConfig,
        ctx: Optional[Any] = None,
    ) -> IndexRepositoryResponse:
        """Index a Git repository.

        Args:
            config: RepositoryConfig object with indexing configuration
            ctx: Context object for progress tracking (optional)

        Returns:
            IndexRepositoryResponse object with information about the created index

        Raises:
            Exception: If indexing fails
        """
        start_time = time.time()
        temp_dir = None

        try:
            # If the repository path is a URL, clone it
            if is_git_url(config.repository_path):
                logger.info(f'Cloning repository from {config.repository_path}')
                if ctx:
                    await ctx.info(f'Cloning repository from {config.repository_path}')
                temp_dir = clone_repository(config.repository_path)
                repo_path = temp_dir
            else:
                repo_path = config.repository_path

            # Get the repository name
            repository_name = get_repository_name(config.repository_path)
            logger.info(f'Indexing repository: {repository_name}')
            if ctx:
                await ctx.info(f'Indexing repository: {repository_name}')
                await ctx.report_progress(0, 100)  # Start progress at 0%

            # Process the repository to get text chunks
            if ctx:
                await ctx.info('Processing repository files...')
                await ctx.report_progress(10, 100)

            chunks, chunk_to_file, extension_stats = process_repository(
                repo_path,
                include_patterns=config.include_patterns,
                exclude_patterns=config.exclude_patterns,
                chunk_size=config.chunk_size,
                chunk_overlap=config.chunk_overlap,
            )

            if ctx:
                await ctx.report_progress(30, 100)

            if not chunks:
                logger.warning('No text chunks found in repository')
                if ctx:
                    await ctx.info('No text chunks found in repository')
                    await ctx.report_progress(100, 100)
                return IndexRepositoryResponse(
                    status='error',
                    repository_name=repository_name,
                    repository_path=config.repository_path,
                    index_path='',
                    repository_directory=repo_path,
                    file_count=0,
                    chunk_count=0,
                    embedding_model=self.embedding_model,
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    message='No text chunks found in repository',
                )

            # Convert chunks to LangChain Document objects
            if ctx:
                await ctx.info(f'Converting {len(chunks)} chunks to Document objects...')
                await ctx.report_progress(40, 100)

            documents = []
            for i, chunk in enumerate(chunks):
                file_path = chunk_to_file.get(chunk, 'unknown')
                documents.append(
                    Document(
                        page_content=chunk,
                        metadata={'source': file_path, 'chunk_id': i},
                    )
                )

            logger.debug(f'Number of documents to embed: {len(documents)}')
            logger.debug(f'Embedding function type: {type(self.embedding_generator)}')

            # Determine the output path
            if config.output_path:
                # Use output_path as the repository name and get the index path
                index_path = self._get_index_path(config.output_path)
                # Ensure the directory exists
                os.makedirs(index_path, exist_ok=True)
            else:
                index_path = self._get_index_path(repository_name)

            # Create a directory for the repository files
            repo_files_path = os.path.join(index_path, 'repository')
            os.makedirs(repo_files_path, exist_ok=True)

            # Copy ALL files from the repository to the repository directory
            # This ensures that all directories and files, including image files and empty directories,
            # are included in the repository structure
            logger.info(f'Copying all files from {repo_path} to {repo_files_path}')
            if ctx:
                await ctx.info('Copying repository files...')
                await ctx.report_progress(60, 100)  # 60% progress - starting file copying

            # First, ensure the target directory is empty
            if os.path.exists(repo_files_path):
                shutil.rmtree(repo_files_path)
            os.makedirs(repo_files_path, exist_ok=True)

            # Track copied files for logging
            copied_files = 0

            # Walk through the repository and copy all files
            for root, dirs, files in os.walk(repo_path):
                # Skip .git directory
                if '.git' in root.split(os.sep):
                    continue

                # Get the relative path from the repository root
                rel_path = os.path.relpath(root, repo_path)
                if rel_path == '.':
                    rel_path = ''

                # Create the corresponding directory in the target
                target_dir = os.path.join(repo_files_path, rel_path)
                os.makedirs(target_dir, exist_ok=True)

                # Copy all files in this directory
                for file in files:
                    source_file = os.path.join(root, file)
                    target_file = os.path.join(target_dir, file)
                    try:
                        shutil.copy2(source_file, target_file)
                        copied_files += 1
                    except Exception as e:
                        logger.warning(f'Error copying file {source_file}: {e}')

            logger.info(f'Copied {copied_files} files to {repo_files_path}')

            logger.info('Creating FAISS index with LangChain')
            if ctx:
                await ctx.info('Creating FAISS index...')
                await ctx.report_progress(70, 100)

            embedding_function = self.embedding_generator
            logger.debug(f'Using embedding function: {embedding_function}')

            # Test the embedding function
            try:
                logger.info('Testing embedding function on sample document...')
                test_content = documents[0].page_content if documents else 'Test content'
                test_result = embedding_function.embed_documents([test_content])
                logger.info(
                    f'Test embedding successful - shape: {len(test_result)}x{len(test_result[0])}'
                )
            except Exception as e:
                logger.error(f'Embedding function test failed: {e}')
                raise

            if ctx:
                await ctx.info('Generating embeddings and creating vector store...')
                await ctx.report_progress(75, 100)

            logger.debug(f'Number of documents: {len(documents)}')

            # Create the FAISS vector store with error handling
            try:
                vector_store = FAISS.from_documents(
                    documents=documents, embedding=embedding_function, normalize_L2=True
                )
                logger.debug(
                    f'Created vector store with {get_docstore_dict_size(vector_store.docstore)} documents'
                )
            except Exception as e:
                logger.error(f'Error creating vector store: {e}')
                logger.error(f'Document count: {len(documents)}')
                logger.error(
                    f'First document content: {documents[0].page_content[:100] if documents else "None"}'
                )
                raise

            # Save the index without pickle
            logger.info(f'Saving index to {index_path}')
            if ctx:
                await ctx.info(f'Saving index to {index_path}')
                await ctx.report_progress(85, 100)

            save_index_without_pickle(vector_store, index_path)

            # Verify the saved index
            logger.info('Verifying saved index')
            try:
                test_store = load_index_without_pickle(index_path, embedding_function)
                logger.info(
                    f'Loaded index contains {get_docstore_dict_size(test_store.docstore)} documents'
                )
            except Exception as e:
                logger.error(f'Error verifying saved index: {e}')

            # Save the chunk map without pickle
            chunk_map_data = {
                'chunks': chunks,
                'chunk_to_file': chunk_to_file,
            }
            save_chunk_map_without_pickle(chunk_map_data, index_path)

            # Get index size by summing up the sizes of all files in the index directory
            index_size = 0
            for root, _, files in os.walk(index_path):
                for file in files:
                    index_size += os.path.getsize(os.path.join(root, file))

            # Get the last commit ID if it's a git repository
            # Do this before any cleanup to ensure we have access to the .git directory
            last_commit_id = None
            if is_git_url(config.repository_path) or is_git_repo(repo_path):
                logger.info(f'Attempting to get last commit ID for {repository_name}')

                # Check if .git directory exists
                git_dir = os.path.join(repo_path, '.git')
                if os.path.exists(git_dir):
                    logger.info(f'.git directory found at {git_dir}')
                    try:
                        repo = Repo(repo_path)
                        if repo.heads:
                            last_commit = repo.head.commit
                            last_commit_id = last_commit.hexsha
                            logger.info(f'Successfully got last commit ID: {last_commit_id}')
                        else:
                            logger.warning('Repository has no commits')
                    except Exception as e:
                        logger.warning(f'Error accessing Git repository: {e}')
                        logger.exception(e)
                else:
                    logger.warning(f'.git directory not found at {git_dir}')
                    # List the contents of the directory to debug
                    logger.info(f'Contents of {repo_path}: {os.listdir(repo_path)}')

            # If we couldn't get the last commit ID, use a placeholder value
            if last_commit_id is None:
                last_commit_id = 'unknown'
                logger.info(f'Using placeholder commit ID: {last_commit_id}')

            # Create and save metadata
            if ctx:
                await ctx.info('Finalizing index metadata...')
                await ctx.report_progress(90, 100)  # 90% progress - creating metadata

            # Use output_path as repository_name if provided
            final_repo_name = config.output_path if config.output_path else repository_name

            metadata = IndexMetadata(
                repository_name=final_repo_name,
                repository_path=config.repository_path,
                index_path=index_path,
                created_at=datetime.now(),
                last_accessed=None,  # Explicitly set to None initially
                file_count=len(set(chunk_to_file.values())),
                chunk_count=len(chunks),
                embedding_model=self.embedding_model,
                file_types=extension_stats,
                total_tokens=None,  # We don't track tokens currently
                index_size_bytes=index_size,
                last_commit_id=last_commit_id,
                repository_directory=repo_files_path,
            )

            logger.info(f'Created metadata with last_commit_id: {metadata.last_commit_id}')

            # Debug: Print all fields in the metadata object
            logger.info(f'Metadata object fields: {metadata.model_dump()}')
            logger.info(f'Last commit ID in metadata: {metadata.last_commit_id}')

            metadata_path = self._get_metadata_path(repository_name)
            metadata_json = metadata.model_dump_json(indent=2)
            logger.info(f'Metadata JSON: {metadata_json}')

            # Check if last_commit_id is in the JSON string
            if '"last_commit_id":' in metadata_json:
                logger.info('last_commit_id field is present in the JSON string')
            else:
                logger.warning('last_commit_id field is NOT present in the JSON string')

            # Write the metadata to the file
            with open(metadata_path, 'w') as f:
                f.write(metadata_json)

            # Verify the file was written correctly
            with open(metadata_path, 'r') as f:
                file_content = f.read()
                logger.info(f'File content: {file_content}')
                if '"last_commit_id":' in file_content:
                    logger.info('last_commit_id field is present in the file')
                else:
                    logger.warning('last_commit_id field is NOT present in the file')

            execution_time_ms = int((time.time() - start_time) * 1000)
            logger.info(f'Indexing completed in {execution_time_ms}ms')

            if ctx:
                await ctx.info(f'Indexing completed in {execution_time_ms}ms')
                await ctx.report_progress(100, 100)  # 100% progress - completed

            return IndexRepositoryResponse(
                status='success',
                repository_name=final_repo_name,
                repository_path=config.repository_path,
                index_path=index_path,
                repository_directory=repo_files_path,
                file_count=metadata.file_count,
                chunk_count=metadata.chunk_count,
                embedding_model=self.embedding_model,
                execution_time_ms=execution_time_ms,
                message=f'Successfully indexed repository with {metadata.file_count} files and {metadata.chunk_count} chunks',
            )

        except Exception as e:
            logger.error(f'Error indexing repository: {e}')
            error_message = f'Error indexing repository: {str(e)}'

            if ctx:
                await ctx.error(error_message)
                await ctx.report_progress(100, 100)  # Complete the progress even on error

            return IndexRepositoryResponse(
                status='error',
                repository_name=get_repository_name(config.repository_path),
                repository_path=config.repository_path,
                index_path='',
                repository_directory=locals().get('repo_path'),
                file_count=0,
                chunk_count=0,
                embedding_model=self.embedding_model,
                execution_time_ms=int((time.time() - start_time) * 1000),
                message=error_message,
            )
        finally:
            # Clean up temporary directory if it was created
            if temp_dir:
                cleanup_repository(temp_dir)

    def get_index_metadata(self, repository_name: str) -> Optional[IndexMetadata]:
        """Get metadata for an indexed repository.

        Args:
            repository_name: Name of the repository

        Returns:
            IndexMetadata object if the repository is indexed, None otherwise
        """
        metadata_path = self._get_metadata_path(repository_name)
        if not os.path.exists(metadata_path):
            return None

        try:
            with open(metadata_path, 'r') as f:
                metadata_dict = json.load(f)
            return IndexMetadata(**metadata_dict)
        except Exception as e:
            logger.error(f'Error loading metadata for repository {repository_name}: {e}')
            return None

    def list_indexed_repositories(self) -> List[str]:
        """List all indexed repositories.

        Returns:
            List of repository names
        """
        repositories = []
        # Look for repository directories in the index directory
        for dirname in os.listdir(self.index_dir):
            dir_path = os.path.join(self.index_dir, dirname)
            if os.path.isdir(dir_path):
                # Check if this directory contains a metadata.json file
                metadata_path = os.path.join(dir_path, 'metadata.json')
                if os.path.exists(metadata_path):
                    try:
                        with open(metadata_path, 'r') as f:
                            metadata_dict = json.load(f)
                        if 'repository_name' in metadata_dict:
                            repositories.append(metadata_dict['repository_name'])
                    except Exception as e:
                        logger.warning(f'Error reading metadata file {metadata_path}: {e}')
        return repositories

    def load_index(self, repository_name: str) -> Tuple[Optional[Any], Optional[Dict]]:
        """Load the FAISS index and chunk map for a repository.

        Args:
            repository_name: Name of the repository

        Returns:
            Tuple containing:
            - LangChain FAISS vectorstore if the repository is indexed, None otherwise
            - Chunk map dictionary if the repository is indexed, None otherwise
        """
        index_path = self._get_index_path(repository_name)
        chunk_map_path = self._get_chunk_map_path(repository_name)

        logger.info(f'Loading index from {index_path}')
        logger.info(f'Loading chunk map from {chunk_map_path}')

        # Check if the index directory exists
        if os.path.isdir(index_path):
            logger.info(f'Index directory exists: {index_path}')
            # Check if the index files exist
            index_faiss_path = os.path.join(index_path, 'index.faiss')
            if not os.path.exists(index_faiss_path):
                logger.error(f'FAISS index file not found in {index_path}')
                return None, None
        else:
            logger.error(f'Index directory not found: {index_path}')
            return None, None

        if not os.path.exists(chunk_map_path):
            logger.error(f'Chunk map not found: {chunk_map_path}')
            return None, None

        try:
            # Load the LangChain FAISS index without pickle
            embedding_function = self.embedding_generator
            logger.info(f'Loading FAISS index with embedding function: {embedding_function}')

            try:
                vector_store = load_index_without_pickle(index_path, embedding_function)
                logger.info(
                    f'Successfully loaded vector store with {get_docstore_dict_size(vector_store.docstore)} documents'
                )
            except Exception as e:
                logger.error(f'Error loading FAISS index: {e}')
                # Try a different approach - list the files in the directory
                logger.info('Files in index directory:')
                for root, dirs, files in os.walk(index_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        logger.info(f'  {file_path} ({os.path.getsize(file_path)} bytes)')
                raise

            # Load the chunk map without pickle
            chunk_map = load_chunk_map_without_pickle(index_path)
            if chunk_map is None:
                logger.error('Failed to load chunk map')
                return None, None
            logger.info(f'Successfully loaded chunk map with {len(chunk_map["chunks"])} chunks')

            # Update the last accessed timestamp in metadata
            metadata_path = self._get_metadata_path(repository_name)
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, 'r') as f:
                        metadata_dict = json.load(f)

                    # Only update last_accessed if it exists in the schema
                    if 'last_accessed' in metadata_dict:
                        metadata_dict['last_accessed'] = datetime.now().isoformat()

                    with open(metadata_path, 'w') as f:
                        json.dump(metadata_dict, f, indent=2)
                except Exception as e:
                    logger.warning(
                        f'Error updating metadata for repository {repository_name}: {e}'
                    )

            return vector_store, chunk_map
        except Exception as e:
            logger.error(f'Error loading index for repository {repository_name}: {e}')
            return None, None


def get_repository_indexer(config: IndexConfig) -> RepositoryIndexer:
    """Get a repository indexer.

    Args:
        config: IndexConfig object with indexer configuration

    Returns:
        RepositoryIndexer instance
    """
    return RepositoryIndexer(config)
