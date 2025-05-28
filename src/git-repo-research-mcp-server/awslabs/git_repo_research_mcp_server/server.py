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
"""awslabs git-repo-research MCP Server implementation."""

import json
import mimetypes
import os
import sys
from awslabs.git_repo_research_mcp_server.defaults import Constants
from awslabs.git_repo_research_mcp_server.github_search import (
    github_repo_search_wrapper,
)
from awslabs.git_repo_research_mcp_server.indexer import (
    IndexConfig,
    RepositoryConfig,
    get_repository_indexer,
)
from awslabs.git_repo_research_mcp_server.models import (
    DeleteRepositoryResponse,
    EmbeddingModel,
    GitHubRepoSearchResponse,
    GitHubRepoSearchResult,
)
from awslabs.git_repo_research_mcp_server.search import get_repository_searcher
from awslabs.git_repo_research_mcp_server.utils import (
    DateTimeEncoder,
    delete_indexed_repository,
    list_indexed_repositories,
)
from datetime import datetime
from loguru import logger
from mcp.server.fastmcp import Context, FastMCP, Image
from mcp.types import ImageContent
from pydantic import Field
from typing import Dict, List, Optional, Union


# Configure logging
logger.remove()
logger.add(sys.stderr, level=os.getenv('FASTMCP_LOG_LEVEL', 'INFO'))

# Create the MCP server
mcp = FastMCP(
    'Git Repository Research MCP Server',
    instructions="""
# Git Repository Research MCP Server

This MCP server provides tools and resources for indexing and searching Git repositories using semantic search.

## Important Note on Repository Names

When working with repository names that include organization (e.g., "awslabs/mcp"), you MUST use underscores instead of slashes in URIs (e.g., "awslabs_mcp") for compatibility. This affects:
- How repositories are stored in the index directory
- How repositories are referenced in metadata.json
- How repositories should be referenced in URIs and search queries

IMPORTANT: Always use underscores in URIs (e.g., `repositories://awslabs_mcp/summary`), NOT slashes.

## Available Tools

### create_research_repository
Build a FAISS index for a Git repository.

### search_research_repository
Perform semantic search within an indexed repository.

### delete_research_repository
Delete an indexed repository.

### search_research_repository_suggestions
Search for GitHub repositories based on keywords, scoped to specific organizations.

### access_file
Access file or directory contents. This tool is recommended for accessing files with complex paths, especially those containing slashes in repository names (e.g., "awslabs/mcp/repository/README.md").

## Available Resources

### repositories://{repository_name}/summary
Get a summary of an indexed repository including directory structure and helpful files (READMEs, etc.). This is particularly useful for understanding the structure of the repository and quickly finding important documentation. The repository_name can be a simple name or in the format "org_repo".

### repositories://
List all indexed repositories with detailed information including file counts, chunk counts, file types, etc.

### repositories://{index_directory}
List all indexed repositories from a specific index directory.

## Usage Examples

### Summarizing or describing purpose/objective/goals of the specific repository (e.g. 'What does this repo do?' or 'What are the main features?').
```
# Access the repository summary resource
repositories://awslabs_mcp/summary

# Or for a simple repository name
repositories://my-repo-name/summary
```

Then after identifying the main files of interest (e.g. README.md, diagrams, etc.), you can further investigate using other tools.

### Indexing a Repository
```
create_research_repository(repository_path="https://github.com/username/repo.git")
```

### Describing the Structure of a Repository (Directory Tree Format)
```
# Access the repository summary resource (with organization name)
repositories://awslabs_mcp/summary

# Or without organization name
repositories://my-repo-name/summary
```

### Searching a Repository
```
search_research_repository(index_path="repo_name", query="How does the authentication system work?")
```

### Listing Indexed Repositories
```
# Default listing
repositories://

# Listing from a specific directory
repositories:///path/to/custom/index/directory
```

### Accessing Files
```
# Using the tool
access_file(filepath="awslabs/mcp/repository/README.md")
access_file(filepath="/Users/username/.git_repo_research/repo_name/repository/src/file.py")
```

### Deleting a Repository
```
delete_research_repository(repository_name_or_path="repo_name")
```

### Searching for GitHub Repositories
```
search_research_repository_suggestions(
    keywords=["serverless", "lambda"],
    num_results=10
)
```
Results are automatically filtered to AWS organizations (aws-samples, aws-solutions-library-samples, awslabs) and specific licenses (Apache License 2.0, MIT, MIT No Attribution), and sorted by stars (descending) and then by updated date.
""",
    dependencies=[
        'boto3',
        'faiss-cpu',
        'gitpython',
        'loguru',
        'numpy',
        'pydantic',
    ],
)


@mcp.tool(name='create_research_repository')
async def mcp_index_repository(
    ctx: Context,
    repository_path: str = Field(
        description='Path to local repository or URL to remote repository'
    ),
    output_path: Optional[str] = Field(
        default=None,
        description='Where to store the index (optional, uses default if not provided)',
    ),
    embedding_model: str = Field(
        default=EmbeddingModel.AMAZON_TITAN_EMBED_TEXT_V2,
        description='Which AWS embedding model to use',
    ),
    include_patterns: Optional[List[str]] = Field(
        default=Constants.DEFAULT_INCLUDE_PATTERNS,
        description='Glob patterns for files to include (optional). Defaults to common source code and documentation files.',
    ),
    exclude_patterns: Optional[List[str]] = Field(
        default=Constants.DEFAULT_EXCLUDE_PATTERNS,
        description='Glob patterns for files to exclude (optional). Defaults to common binary files, build artifacts, and VCS directories.',
    ),
    chunk_size: int = Field(
        default=1000,
        description='Maximum size of each chunk in characters',
    ),
    chunk_overlap: int = Field(
        default=200,
        description='Overlap between chunks in characters',
    ),
) -> Dict:
    """Build a FAISS index for a Git repository.

    This tool indexes a Git repository (local or remote) using FAISS and Amazon Bedrock embeddings.
    The index can then be used for semantic search within the repository.

    Args:
        ctx: MCP context object used for progress tracking and error reporting
        repository_path: Path to local repository or URL to remote repository
        output_path: Where to store the index (optional, uses default if not provided)
        embedding_model: Which AWS embedding model to use
        include_patterns: Glob patterns for files to include (optional)
        exclude_patterns: Glob patterns for files to exclude (optional)
        chunk_size: Maximum size of each chunk in characters
        chunk_overlap: Overlap between chunks in characters

    Returns:
        Information about the created index
    """
    logger.info(f'Indexing repository: {repository_path}')

    # If output_path is provided and contains slashes, normalize it for file path compatibility
    if output_path and '/' in output_path:
        output_path = output_path.replace('/', '_')
        logger.info(f'Normalized output path: {output_path}')

    try:
        # Get AWS credentials from environment variables
        aws_region = os.environ.get('AWS_REGION')
        aws_profile = os.environ.get('AWS_PROFILE')

        index_config = IndexConfig(
            embedding_model=embedding_model, aws_region=aws_region, aws_profile=aws_profile
        )

        repository_config = RepositoryConfig(
            repository_path=repository_path,
            output_path=output_path,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        # Get the repository indexer
        indexer = get_repository_indexer(config=index_config)

        # Index the repository
        response = await indexer.index_repository(
            config=repository_config,
            ctx=ctx,  # Pass the context for progress tracking
        )

        # Add repository directory information to the response
        if response.status == 'success':
            repo_files_path = os.path.join(response.index_path, 'repository')
            if os.path.exists(repo_files_path) and os.path.isdir(repo_files_path):
                response.repository_directory = repo_files_path

        # Return the response
        return response.model_dump()
    except Exception as e:
        logger.error(f'Error indexing repository: {e}')
        await ctx.error(f'Error indexing repository: {str(e)}')
        raise


@mcp.resource(
    uri='repositories://{repository_name}/summary',
    name='Repository Summary',
    mime_type='application/json',
)
async def repository_summary(repository_name: str) -> str:
    """Get a summary of an indexed repository including structure and helpful files.

    This resource provides a summary of the repository including:
    - Directory tree structure of all files
    - List of helpful files (READMEs, documentation, etc.)

    Args:
        repository_name: Name of the repository

    Returns:
        Repository summary if repository is found, error message otherwise
    """
    # Use repository_name as is for the response
    full_repository_name = repository_name
    logger.info(f'Listing files for repository: {full_repository_name}')

    # Convert repository name with slashes to underscores for file path compatibility
    normalized_repo_name = full_repository_name.replace('/', '_')
    logger.info(f'Normalized repository name: {normalized_repo_name}')

    try:
        # Get AWS credentials from environment variables
        aws_region = os.environ.get('AWS_REGION')
        aws_profile = os.environ.get('AWS_PROFILE')

        # Get the repository searcher
        searcher = get_repository_searcher(
            aws_region=aws_region,
            aws_profile=aws_profile,
        )

        # List the repository files
        tree = searcher.list_repository_files(
            repository_name=normalized_repo_name,
        )

        if tree is None:
            return json.dumps(
                {
                    'status': 'error',
                    'message': f'Repository not found or no files available: {repository_name}',
                }
            )

        # Get the repository directory path
        index_path = searcher.repository_indexer._get_index_path(normalized_repo_name)
        repo_files_path = os.path.join(index_path, 'repository')

        # Find helpful files (READMEs, etc.)
        helpful_files = []
        if tree and isinstance(tree, dict):
            # Extract all README files from the tree
            def extract_readme_paths(tree_dict, current_path=''):
                readme_paths = []
                for name, content in tree_dict.items():
                    path = f'{current_path}/{name}' if current_path else name
                    if isinstance(content, dict):
                        # It's a directory
                        readme_paths.extend(extract_readme_paths(content, path))
                    elif name.lower().startswith('readme'):
                        # It's a README file
                        # Format the path for use with access_file tool
                        file_path = f'{repository_name}/{path}'
                        readme_paths.append(file_path)
                return readme_paths

            helpful_files = extract_readme_paths(tree)
        elif tree and isinstance(tree, str):
            # If tree is a string, try to parse it as a directory structure
            logger.info('Tree is a string, attempting to parse directory structure')

            # Extract README files with their full paths from the string representation of the tree
            import re

            # Parse the tree structure to extract full paths
            lines = tree.split('\n')
            current_path = []
            readme_files = []

            # Process each line to build the directory structure
            for line in lines:
                # Skip empty lines
                if not line.strip():
                    continue

                # Calculate the indentation level
                indent = 0
                for char in line:
                    if char in ' │':
                        indent += 1
                    else:
                        break

                # Adjust the current path based on indentation
                current_path = current_path[: indent // 4 + 1]

                # Extract the file or directory name
                match = re.search(r'[─└├]─+\s+(.+)$', line)
                if match:
                    name = match.group(1)

                    # If it's a directory, add it to the current path
                    if name.endswith('/'):
                        name = name.rstrip('/')
                        if len(current_path) <= indent // 4:
                            current_path.append(name)
                        else:
                            current_path[indent // 4] = name
                    # If it's a README file, add its full path to the list
                    elif re.match(r'README.*', name, re.IGNORECASE):
                        path = '/'.join(current_path + [name]) if current_path else name
                        # Format the path for use with access_file tool
                        file_path = f'{repository_name}/{path}'
                        readme_files.append(file_path)

            # Add all found README files to helpful_files
            if readme_files:
                helpful_files = readme_files
                logger.info(
                    f'Found {len(helpful_files)} README files with full paths in string tree'
                )
            else:
                logger.warning('No README files found in string tree')

        return json.dumps(
            {
                'status': 'success',
                'tree': tree,
                'repository_name': repository_name,
                'repository_directory': (
                    repo_files_path
                    if os.path.exists(repo_files_path) and os.path.isdir(repo_files_path)
                    else None
                ),
                'helpful_files': helpful_files,
            },
            cls=DateTimeEncoder,
        )
    except Exception as e:
        logger.error(f'Error listing repository files: {e}')
        return json.dumps(
            {'status': 'error', 'message': f'Error listing repository files: {str(e)}'},
            cls=DateTimeEncoder,
        )


@mcp.resource(uri='repositories://', name='Indexed Repositories', mime_type='application/json')
async def list_repositories() -> str:
    """List all indexed repositories with detailed information.

    This resource returns a list of all repositories that have been indexed and are available for searching.
    It provides detailed information about each index including file counts, chunk counts, file types, etc.

    Returns:
        List of indexed repositories with detailed information
    """
    logger.info('Listing indexed repositories')

    try:
        # List indexed repositories with detailed information by default
        response = list_indexed_repositories(
            index_dir=None,
            detailed=True,  # Return detailed information by default
        )

        # Add repository directory information to each repository
        for repo in response.repositories:
            repo_files_path = os.path.join(repo.index_path, 'repository')
            if os.path.exists(repo_files_path) and os.path.isdir(repo_files_path):
                repo.repository_directory = repo_files_path

        # Return the response with custom encoder for datetime objects
        return json.dumps(response.model_dump(), cls=DateTimeEncoder)
    except Exception as e:
        logger.error(f'Error listing indexed repositories: {e}')
        return json.dumps(
            {
                'status': 'error',
                'message': f'Error listing indexed repositories: {str(e)}',
            }
        )


async def access_file_or_directory(filepath: str) -> Union[str, List[str], Image]:
    """Access file or directory contents.

    This resource provides access to file or directory contents:
    - If the filepath references a text file, returns the content as a string
    - If the filepath references a directory, returns an array of files in the directory
    - If the filepath references a binary image (jpg, png), returns the image data

    For repository files, use the format: repository_name/repository/path/to/file
    Example: awslabs_mcp/repository/README.md

    For repositories with organization names, both formats are supported:
    - awslabs_mcp/repository/README.md (with underscore)
    - awslabs/mcp/repository/README.md (with slash)

    Args:
        filepath: Path to the file or directory to access

    Returns:
        File content, directory listing, or image data
    """
    logger.info(f'Accessing file or directory: {filepath}')

    try:
        # Check if this is a repository file path (format: repo_name/repository/...)
        parts = filepath.split('/')

        # Handle the case where the first part might contain a slash (e.g., "awslabs/mcp")
        if '/' in parts[0]:
            # Normalize the repository name by replacing slashes with underscores
            normalized_repo_name = parts[0].replace('/', '_')
            # Reconstruct the path with the normalized repository name
            parts[0] = normalized_repo_name
            filepath = '/'.join(parts)
            logger.info(f'Normalized filepath: {filepath}')

            # Re-split the filepath with the normalized repository name
            parts = filepath.split('/')

        if len(parts) >= 2 and parts[1] == 'repository':
            repo_name = parts[0]
            # Get the repository directory path
            try:
                # Get AWS credentials from environment variables
                aws_region = os.environ.get('AWS_REGION')
                aws_profile = os.environ.get('AWS_PROFILE')

                # Get the repository searcher
                searcher = get_repository_searcher(
                    aws_region=aws_region,
                    aws_profile=aws_profile,
                )

                # Get the repository directory path
                index_path = searcher.repository_indexer._get_index_path(repo_name)
                repo_path = os.path.join(index_path, 'repository')

                # Construct the full path to the file
                if len(parts) > 2:
                    file_path = os.path.join(repo_path, *parts[2:])
                else:
                    file_path = repo_path

                logger.info(f'Accessing repository file: {file_path}')
                filepath = file_path
            except Exception as e:
                logger.error(f'Error resolving repository path: {e}')
                return json.dumps(
                    {
                        'status': 'error',
                        'message': f'Error resolving repository path: {str(e)}',
                    }
                )

        # Check if the path exists
        if not os.path.exists(filepath):
            return json.dumps(
                {
                    'status': 'error',
                    'message': f'File or directory not found: {filepath}',
                }
            )

        # If it's a directory, return a listing of files
        if os.path.isdir(filepath):
            files = os.listdir(filepath)
            return json.dumps(
                {
                    'status': 'success',
                    'type': 'directory',
                    'path': filepath,
                    'files': files,
                }
            )

        # If it's a file, determine the mime type
        mime_type, _ = mimetypes.guess_type(filepath)

        # If it's an image, return the image data
        if mime_type and mime_type.startswith('image/'):
            try:
                # Read file directly as binary data
                with open(filepath, 'rb') as f:
                    image_data = f.read()

                # Extract format from mime_type (e.g., "image/png" -> "png")
                image_format = mime_type.split('/')[1]

                # Return Image with binary data
                return Image(data=image_data, format=image_format)
            except Exception as e:
                logger.error(f'Error processing image file: {e}')
                return json.dumps(
                    {
                        'status': 'error',
                        'message': f'Error processing image file: {str(e)}',
                    }
                )

        # For text files, return the content as a string
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except UnicodeDecodeError:
            # If we can't decode as text, it's likely a binary file
            return json.dumps(
                {
                    'status': 'error',
                    'message': f'File appears to be binary and not an image: {filepath}',
                }
            )

    except Exception as e:
        logger.error(f'Error accessing file or directory: {e}')
        return json.dumps(
            {
                'status': 'error',
                'message': f'Error accessing file or directory: {str(e)}',
            }
        )


@mcp.tool(name='search_research_repository')
async def mcp_search_repository(
    ctx: Context,
    index_path: str = Field(description='Name of the repository or path to the index to search'),
    query: str = Field(description='The search query to use for semantic search'),
    limit: int = Field(default=10, description='Maximum number of results to return'),
    threshold: float = Field(
        default=0.0, description='Minimum similarity score threshold (0.0 to 1.0)'
    ),
) -> Dict:
    """Perform semantic search within an indexed repository.

    This tool searches an indexed repository using semantic search with Amazon Bedrock embeddings.
    It returns results ranked by relevance to the query.

    Args:
        ctx: MCP context object used for error reporting
        index_path: Name of the repository or path to the index to search
        query: The search query to use for semantic search
        limit: Maximum number of results to return
        threshold: Minimum similarity score threshold (0.0 to 1.0)

    Returns:
        Search results ranked by relevance to the query
    """
    logger.info(f'Searching repository: {index_path} for query: {query}')

    # Convert repository name with slashes to underscores for file path compatibility
    normalized_index_path = str(index_path).replace('/', '_')
    if normalized_index_path != index_path:
        logger.info(f'Normalized index path: {normalized_index_path}')

    try:
        # Record start time
        start_time = datetime.now()

        # Get AWS credentials from environment variables
        aws_region = os.environ.get('AWS_REGION')
        aws_profile = os.environ.get('AWS_PROFILE')

        # Get the repository searcher
        searcher = get_repository_searcher(
            aws_region=aws_region,
            aws_profile=aws_profile,
        )

        # Search the repository
        response = searcher.search(
            index_path=normalized_index_path,
            query=query,
            limit=limit,
            threshold=threshold,
        )

        # Calculate execution time
        execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        # Add execution time to the response
        response_dict = response.model_dump()
        response_dict['execution_time_ms'] = execution_time_ms

        # Return the response
        return response_dict
    except Exception as e:
        logger.error(f'Error searching repository: {e}')
        await ctx.error(f'Error searching repository: {str(e)}')
        raise


@mcp.tool(name='search_research_repository_suggestions')
async def mcp_search_github_repos(
    ctx: Context,
    keywords: List[str] = Field(description='List of keywords to search for GitHub repositories'),
    num_results: int = Field(default=5, description='Number of results to return'),
) -> Dict:
    """Search for GitHub repositories based on keywords, scoped to specific organizations.

    This tool searches for GitHub repositories using the GitHub REST/GraphQL APIs, scoped to specific GitHub
    organizations (aws-samples, aws-solutions-library-samples, and awslabs).

    Results are filtered to only include repositories with specific licenses (Apache License 2.0,
    MIT, and MIT No Attribution) and are sorted by stars (descending) and then by updated date.

    For higher rate limits, you can set the GITHUB_TOKEN environment variable with a GitHub
    personal access token. Without a token, the API is limited to 60 requests per hour, and requests are
    made with the REST API. With a token, this increases to 5,000 requests per hour, and requests are made
    with the GraphQL API.

    Args:
        ctx: MCP context object used for error reporting
        keywords: List of keywords to search for
        num_results: Number of results to return

    Returns:
        List of GitHub repositories matching the search criteria
    """
    logger.info(f'Searching for GitHub repositories with keywords: {keywords}')

    try:
        # Record start time
        start_time = datetime.now()

        # Get GitHub token from environment variables
        github_token = os.environ.get('GITHUB_TOKEN')

        # Log whether we're using authenticated or unauthenticated mode
        if github_token:
            logger.info('Using authenticated GitHub API (higher rate limits)')
        else:
            logger.info('Using unauthenticated GitHub API (lower rate limits)')

        # Define fixed values for organizations and license filters
        organizations = ['aws-samples', 'aws-solutions-library-samples', 'awslabs']
        license_filter = ['Apache License 2.0', 'MIT', 'MIT No Attribution']

        # Call the search function
        results = github_repo_search_wrapper(
            keywords=keywords,
            organizations=organizations,
            num_results=num_results,
            license_filter=license_filter,
        )

        # Calculate execution time
        execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        # Convert results to GitHubRepoSearchResult objects
        repo_results = []
        for result in results:
            # Include all available fields
            repo_results.append(
                GitHubRepoSearchResult(
                    url=result['url'],
                    title=result['title'],
                    description=result.get('description'),
                    organization=result['organization'],
                    stars=result.get('stars'),
                    updated_at=result.get('updated_at'),
                    language=result.get('language'),
                    topics=result.get('topics'),
                    license=result.get('license'),
                    forks=result.get('forks'),
                    open_issues=result.get('open_issues'),
                    homepage=result.get('homepage'),
                )
            )

        # Create response object
        response = GitHubRepoSearchResponse(
            status='success',
            query=' '.join(keywords) if isinstance(keywords, list) else keywords,
            organizations=organizations,  # Using the organizations defined above
            results=repo_results,
            total_results=len(repo_results),
            execution_time_ms=execution_time_ms,
        )

        # Return the response
        return response.model_dump()
    except Exception as e:
        logger.error(f'Error searching for GitHub repositories: {e}')
        await ctx.error(f'Error searching for GitHub repositories: {str(e)}')
        raise


@mcp.tool(name='access_file')
async def mcp_access_file(
    ctx: Context,
    filepath: str = Field(description='Path to the file or directory to access'),
) -> Dict | ImageContent:
    """Access file or directory contents.

    This tool provides access to file or directory contents:
    - If the filepath references a text file, returns the content as a string
    - If the filepath references a directory, returns an array of files in the directory
    - If the filepath references a binary image (jpg, png), returns the image data

    For repository files, use the format: repository_name/repository/path/to/file
    Example: awslabs_mcp/repository/README.md

    For repositories with organization names, both formats are supported:
    - awslabs_mcp/repository/README.md (with underscore)
    - awslabs/mcp/repository/README.md (with slash)

    Args:
        ctx: MCP context object used for error reporting
        filepath: Path to the file or directory to access

    Returns:
        File content, directory listing, or image data
    """
    logger.info(f'Tool: Accessing file or directory: {filepath}')

    try:
        # Use the existing access_file_or_directory function
        result = await access_file_or_directory(filepath)

        # Handle different result types
        if isinstance(result, str):
            if result.startswith('{'):
                # It's a JSON string (error or directory listing)
                return json.loads(result)
            else:
                # It's a file content string
                return {'status': 'success', 'type': 'text', 'content': result}
        elif isinstance(result, Image):
            # It's an image
            return result.to_image_content()
        else:
            # Unknown type
            return {
                'status': 'error',
                'message': f'Unknown result type: {type(result)}',
            }
    except Exception as e:
        # Ensure exceptions are properly raised for the test case
        logger.error(f'Error in mcp_access_file: {e}')
        await ctx.error(f'Error accessing file or directory: {str(e)}')
        raise Exception(f'Error accessing file: {str(e)}')


@mcp.tool(name='delete_research_repository')
async def mcp_delete_repository(
    ctx: Context,
    repository_name_or_path: str = Field(
        description='Name of the repository or path to the index to delete'
    ),
    index_directory: Optional[str] = Field(
        default=None,
        description='Directory to look for indices (optional, uses default if not provided)',
    ),
) -> Dict:
    """Delete an indexed repository.

    This tool deletes an indexed repository and its associated files.
    It can be identified by repository name or the full path to the index.

    Args:
        ctx: MCP context object used for error reporting
        repository_name_or_path: Name of the repository or path to the index to delete
        index_directory: Directory to look for indices (optional, uses default if not provided)

    Returns:
        Status of the delete operation
    """
    logger.info(f'Deleting repository: {repository_name_or_path}')

    # Convert repository name with slashes to underscores for file path compatibility
    normalized_repo_name = str(repository_name_or_path).replace('/', '_')
    logger.info(f'Normalized repository name: {normalized_repo_name}')

    # Properly await the info call
    await ctx.info(f'Deleting repository: {normalized_repo_name}')

    # Ensure index_directory is None or a string, not a Field
    index_dir = None if index_directory is None else str(index_directory)

    try:
        # Record start time
        start_time = datetime.now()

        # Delete the repository
        result = await delete_indexed_repository(
            repository_name_or_path=normalized_repo_name,
            index_dir=index_dir,
        )

        # Calculate execution time
        execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        # Create response with all available fields
        response_data = {
            'status': result['status'],
            'message': result['message'],
            'repository_name': result.get('repository_name'),
            'execution_time_ms': execution_time_ms,
        }

        # Add optional fields if they exist in the result
        if 'deleted_files' in result:
            response_data['deleted_files'] = result['deleted_files']
        if 'errors' in result:
            response_data['errors'] = result['errors']
        if 'permission_issues' in result:
            response_data['permission_issues'] = result['permission_issues']

        # Create response object
        response = DeleteRepositoryResponse(**response_data)

        # Return the response
        return response.model_dump()
    except Exception as e:
        logger.error(f'Error deleting repository: {e}')
        await ctx.error(f'Error deleting repository: {str(e)}')
        raise


def main():
    """Run the MCP server with CLI argument support."""
    mcp.run()


if __name__ == '__main__':
    main()
