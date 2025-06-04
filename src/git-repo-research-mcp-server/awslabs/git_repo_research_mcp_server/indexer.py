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
"""FAISS indexing for Git Repository Research MCP Server using LangChain.

This module provides functionality for creating and managing FAISS indices
for Git repositories using LangChain's FAISS implementation.
"""

import faiss
import json
import os
import shutil
import time
from awslabs.git_repo_research_mcp_server.defaults import Constants
from awslabs.git_repo_research_mcp_server.embeddings import get_embedding_model
from awslabs.git_repo_research_mcp_server.models import (
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
        # Allow test-model for testing purposes
        if embedding_model == 'test-model':
            return embedding_model

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
        self.embedding_generator = get_embedding_model(
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
            # Initialize helper classes
            repo_processor = RepositoryProcessor()
            index_builder = IndexBuilder()
            file_manager = FileManager()
            metadata_manager = MetadataManager()

            # Step 1: Repository preparation and processing
            repo_path, repository_name, temp_dir = await repo_processor.prepare_repository(
                config.repository_path, ctx
            )

            if ctx:
                await ctx.report_progress(0, 100)

            chunks, chunk_to_file, extension_stats = await repo_processor.process_content(
                repo_path, config, ctx
            )

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

            # Step 2: Index creation
            documents = await index_builder.create_documents(chunks, chunk_to_file, ctx)
            index_path = self._get_index_path(config.output_path or repository_name)
            repo_files_path = os.path.join(index_path, 'repository')
            os.makedirs(repo_files_path, exist_ok=True)

            # Step 3: File management
            await file_manager.copy_repository_files(repo_path, repo_files_path, ctx)
            vector_store = await index_builder.create_vector_store(
                documents, self.embedding_generator, ctx
            )
            index_builder.save_index(vector_store, index_path)

            # Save chunk map
            chunk_map_data = {'chunks': chunks, 'chunk_to_file': chunk_to_file}
            file_manager.save_chunk_map(chunk_map_data, index_path)

            # Step 4: Metadata management
            last_commit_id = await repo_processor.get_commit_id(
                repo_path, repository_name, config.repository_path
            )

            metadata = await metadata_manager.create_and_save(
                {
                    'repository_name': repository_name,
                    'config': config,
                    'index_path': index_path,
                    'repo_files_path': repo_files_path,
                    'chunks': chunks,
                    'chunk_to_file': chunk_to_file,
                    'extension_stats': extension_stats,
                    'last_commit_id': last_commit_id,
                    'embedding_model': self.embedding_model,
                },
                ctx,
            )

            # Return success response
            execution_time_ms = int((time.time() - start_time) * 1000)
            logger.info(f'Indexing completed in {execution_time_ms}ms')

            if ctx:
                await ctx.info(f'Indexing completed in {execution_time_ms}ms')
                await ctx.report_progress(100, 100)

            return IndexRepositoryResponse(
                status='success',
                repository_name=metadata.repository_name,
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
                await ctx.report_progress(100, 100)

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
            if temp_dir:
                cleanup_repository(temp_dir)

    def load_index_without_pickle(self, index_path):
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
            embedding_function=self.embedding_generator,
            index=index,
            docstore=docstore,
            index_to_docstore_id=index_to_docstore_id,
        )


class RepositoryProcessor:
    """Handles repository-specific operations for indexing."""

    async def prepare_repository(
        self, repository_path: str, ctx: Optional[Any] = None
    ) -> Tuple[str, str, Optional[str]]:
        """Prepare the repository for indexing.

        Args:
            repository_path: Path or URL to the repository
            ctx: Context object for progress tracking (optional)

        Returns:
            Tuple containing:
            - Path to the repository
            - Name of the repository
            - Temporary directory if created (for cleanup), None otherwise
        """
        temp_dir = None
        # If the repository path is a URL, clone it
        if is_git_url(repository_path):
            logger.info(f'Cloning repository from {repository_path}')
            if ctx:
                await ctx.info(f'Cloning repository from {repository_path}')
            temp_dir = clone_repository(repository_path)
            repo_path = temp_dir
        else:
            repo_path = repository_path

        # Get the repository name
        repository_name = get_repository_name(repository_path)
        logger.info(f'Indexing repository: {repository_name}')
        if ctx:
            await ctx.info(f'Indexing repository: {repository_name}')

        return repo_path, repository_name, temp_dir

    async def process_content(
        self, repo_path: str, config: RepositoryConfig, ctx: Optional[Any] = None
    ) -> Tuple[List[str], Dict[str, str], Dict[str, int]]:
        """Process repository files to get text chunks.

        Args:
            repo_path: Path to the repository
            config: Repository configuration
            ctx: Context object for progress tracking (optional)

        Returns:
            Tuple containing:
            - List of text chunks
            - Mapping of chunks to file paths
            - Statistics about file extensions
        """
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

        return chunks, chunk_to_file, extension_stats

    async def get_commit_id(
        self, repo_path: str, repository_name: str, repository_path: str
    ) -> str:
        """Get the last commit ID for a repository.

        Args:
            repo_path: Path to the repository
            repository_name: Name of the repository
            repository_path: Original path/URL to the repository

        Returns:
            Last commit ID, or 'unknown' if not available
        """
        last_commit_id = None
        if is_git_url(repository_path) or is_git_repo(repo_path):
            logger.info(f'Attempting to get last commit ID for {repository_name}')

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

        return last_commit_id or 'unknown'


class IndexBuilder:
    """Handles FAISS index creation and management."""

    async def create_documents(
        self, chunks: List[str], chunk_to_file: Dict[str, str], ctx: Optional[Any] = None
    ) -> List[Document]:
        """Convert chunks to LangChain Document objects.

        Args:
            chunks: List of text chunks
            chunk_to_file: Mapping of chunks to file paths
            ctx: Context object for progress tracking (optional)

        Returns:
            List of LangChain Document objects
        """
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
        return documents

    async def create_vector_store(
        self, documents: List[Document], embedding_generator, ctx: Optional[Any] = None
    ) -> FAISS:
        """Create a FAISS vector store from documents.

        Args:
            documents: List of LangChain Document objects
            embedding_generator: Embedding function to use
            ctx: Context object for progress tracking (optional)

        Returns:
            FAISS vector store
        """
        logger.info('Creating FAISS index with LangChain')
        if ctx:
            await ctx.info('Creating FAISS index...')
            await ctx.report_progress(70, 100)

        logger.debug(f'Using embedding function: {embedding_generator}')

        # Test the embedding function
        try:
            logger.info('Testing embedding function on sample document...')
            test_content = documents[0].page_content if documents else 'Test content'
            test_result = embedding_generator.embed_documents([test_content])
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

        try:
            vector_store = FAISS.from_documents(
                documents=documents, embedding=embedding_generator, normalize_L2=True
            )
            logger.debug(
                f'Created vector store with {get_docstore_dict_size(vector_store.docstore)} documents'
            )
            return vector_store
        except Exception as e:
            logger.error(f'Error creating vector store: {e}')
            logger.error(f'Document count: {len(documents)}')
            logger.error(
                f'First document content: {documents[0].page_content[:100] if documents else "None"}'
            )
            raise

    def save_index(self, vector_store: FAISS, index_path: str):
        """Save FAISS index without using pickle.

        Args:
            vector_store: FAISS vector store
            index_path: Path to save the index
        """
        save_index_without_pickle(vector_store, index_path)


class FileManager:
    """Handles file operations for indexing."""

    async def copy_repository_files(
        self, repo_path: str, repo_files_path: str, ctx: Optional[Any] = None
    ) -> int:
        """Copy all files from the repository to the target directory.

        Args:
            repo_path: Source repository path
            repo_files_path: Target path for copied files
            ctx: Context object for progress tracking (optional)

        Returns:
            Number of copied files
        """
        logger.info(f'Copying all files from {repo_path} to {repo_files_path}')
        if ctx:
            await ctx.info('Copying repository files...')
            await ctx.report_progress(60, 100)

        # First, ensure the target directory is empty
        if os.path.exists(repo_files_path):
            shutil.rmtree(repo_files_path)
        os.makedirs(repo_files_path, exist_ok=True)

        copied_files = 0
        for root, dirs, files in os.walk(repo_path):
            if '.git' in root.split(os.sep):
                continue

            rel_path = os.path.relpath(root, repo_path)
            if rel_path == '.':
                rel_path = ''

            target_dir = os.path.join(repo_files_path, rel_path)
            os.makedirs(target_dir, exist_ok=True)

            for file in files:
                source_file = os.path.join(root, file)
                target_file = os.path.join(target_dir, file)
                try:
                    shutil.copy2(source_file, target_file)
                    copied_files += 1
                except Exception as e:
                    logger.warning(f'Error copying file {source_file}: {e}')

        logger.info(f'Copied {copied_files} files to {repo_files_path}')
        return copied_files

    def save_chunk_map(self, chunk_map_data: Dict, index_path: str):
        """Save chunk map without using pickle.

        Args:
            chunk_map_data: Chunk map to save
            index_path: Path to save the chunk map
        """
        save_chunk_map_without_pickle(chunk_map_data, index_path)


class MetadataManager:
    """Handles metadata operations for indexing."""

    async def create_and_save(
        self, params: Dict[str, Any], ctx: Optional[Any] = None
    ) -> IndexMetadata:
        """Create and save metadata for the indexed repository.

        Args:
            params: Dictionary containing metadata parameters
            ctx: Context object for progress tracking (optional)

        Returns:
            Created IndexMetadata object
        """
        if ctx:
            await ctx.info('Finalizing index metadata...')
            await ctx.report_progress(90, 100)

        # Get index size
        index_size = 0
        for root, _, files in os.walk(params['index_path']):
            for file in files:
                index_size += os.path.getsize(os.path.join(root, file))

        # Use output_path as repository_name if provided
        final_repo_name = params['config'].output_path or params['repository_name']

        metadata = IndexMetadata(
            repository_name=final_repo_name,
            repository_path=params['config'].repository_path,
            index_path=params['index_path'],
            created_at=datetime.now(),
            last_accessed=None,
            file_count=len(set(params['chunk_to_file'].values())),
            chunk_count=len(params['chunks']),
            embedding_model=params['embedding_model'],
            file_types=params['extension_stats'],
            total_tokens=None,
            index_size_bytes=index_size,
            last_commit_id=params['last_commit_id'],
            repository_directory=params['repo_files_path'],
        )

        # Save metadata
        metadata_path = os.path.join(params['index_path'], 'metadata.json')
        metadata_json = metadata.model_dump_json(indent=2)
        with open(metadata_path, 'w') as f:
            f.write(metadata_json)

        return metadata


def get_repository_indexer(config: IndexConfig) -> RepositoryIndexer:
    """Factory method to return a repository indexer.

    Args:
        config: IndexConfig object with indexer configuration

    Returns:
        RepositoryIndexer instance
    """
    return RepositoryIndexer(config)
