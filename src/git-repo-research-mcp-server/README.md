# Git Repo Research MCP Server

Model Context Protocol (MCP) server for researching Git repositories using semantic search

This MCP server enables developers to research external Git repositories and influence their code generation without having to clone repositories to local projects. It provides tools to index, search, and explore Git repositories using semantic search powered by Amazon Bedrock and FAISS.

## Features

- **Repository Indexing**: Create searchable FAISS indexes from local or remote Git repositories
- **Semantic Search**: Query repository content using natural language and retrieve relevant code snippets
- **Repository Summary**: Get directory structures and identify key files like READMEs
- **GitHub Repository Search**: Find repositories in AWS-related organizations filtered by licenses and keywords
- **File Access**: Access repository files and directories with support for both text and binary content

## Prerequisites

### Installation Requirements

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python 3.12 or newer using `uv python install 3.12`
3. - [uv](https://github.com/astral-sh/uv) - Fast Python package installer and resolver
4. AWS credentials configured with Bedrock access
5. Node.js (for UVX installation support)


### AWS Requirements

1. **AWS CLI Configuration**: You must have the AWS CLI configured with credentials that have access to Amazon Bedrock
2. **Amazon Bedrock Access**: Ensure your AWS account has access to embedding models like Titan Embeddings
3. **Environment Variables**: The server uses `AWS_REGION` and `AWS_PROFILE` environment variables

### Optional Requirements

1. **GitHub Token**: Set `GITHUB_TOKEN` environment variable for higher rate limits when searching GitHub repositories

## Installation

| Cursor | VS Code |
|:------:|:-------:|
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.git-repo-research-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuZ2l0LXJlcG8tcmVzZWFyY2gtbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiQVdTX1BST0ZJTEUiOiJ5b3VyLXByb2ZpbGUtbmFtZSIsIkFXU19SRUdJT04iOiJ1cy13ZXN0LTIiLCJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIiwiR0lUSFVCX1RPS0VOIjoieW91ci1naXRodWItdG9rZW4ifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Git%20Repo%20Research%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.git-repo-research-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-profile-name%22%2C%22AWS_REGION%22%3A%22us-west-2%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22GITHUB_TOKEN%22%3A%22your-github-token%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

To add this MCP server to your Amazon Q or Claude, add the following to your MCP config file:

```json
{
  "mcpServers": {
    "awslabs.git-repo-research-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.git-repo-research-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-profile-name",
        "AWS_REGION": "us-west-2",
        "FASTMCP_LOG_LEVEL": "ERROR",
        "GITHUB_TOKEN": "your-github-token"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```
### Windows Installation

For Windows users, the MCP server configuration format is slightly different:

```json
{
  "mcpServers": {
    "awslabs.git-repo-research-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.git-repo-research-mcp-server@latest",
        "awslabs.git-repo-research-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```


## Tools

### create_research_repository

Indexes a Git repository (local or remote) using FAISS and Amazon Bedrock embeddings.

```python
create_research_repository(
    repository_path: str,
    output_path: Optional[str] = None,
    embedding_model: str = "amazon.titan-embed-text-v2:0",
    include_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> Dict
```

### search_research_repository

Performs semantic search within an indexed repository.

```python
search_research_repository(
    index_path: str,
    query: str,
    limit: int = 10,
    threshold: float = 0.0
) -> Dict
```

### search_repos_on_github

Searches for GitHub repositories based on keywords, scoped to AWS organizations.

```python
search_repos_on_github(
    keywords: List[str],
    num_results: int = 5
) -> Dict
```

### access_file

Accesses file or directory contents within repositories or on the filesystem.

```python
access_file(
    filepath: str
) -> Dict | ImageContent
```

### delete_research_repository

Deletes an indexed repository.

```python
delete_research_repository(
    repository_name_or_path: str,
    index_directory: Optional[str] = None
) -> Dict
```

## Resources

### repositories://repository_name/summary

Get a summary of an indexed repository including structure and helpful files.

```
repositories://awslabs_mcp/summary
```

### repositories://

List all indexed repositories with detailed information.

```
repositories://
```

### repositories://index_directory

List all indexed repositories from a specific index directory.

```
repositories:///path/to/custom/index/directory
```

## Considerations

- Repository indexing requires Amazon Bedrock access and sufficient permissions
- Large repositories may take significant time to index
- Binary files (except images) are not supported for content viewing
- GitHub repository search is by default limited to AWS organizations: aws-samples, aws-solutions-library-samples, and awslabs (but can be configured to include other organizations)
