---
title: AWS Documentation MCPサーバー
---

AWSドキュメント向けのModel Context Protocol (MCP) サーバーです

このMCPサーバーは、AWSドキュメントへのアクセス、コンテンツの検索、およびレコメンデーションの取得を行うツールを提供します。

## 機能 {#features}

- **ドキュメントの読み取り**: AWSドキュメントのページを取得し、markdown形式に変換します
- **ドキュメントの検索**: 公式の検索APIを使用してAWSドキュメントを検索します（グローバルのみ）
- **セクションの読み取り**: AWSドキュメントページのセクションを取得し、markdown形式に変換します。
- **レコメンデーション**: AWSドキュメントページのコンテンツレコメンデーションを取得します（グローバルのみ）
- **利用可能なサービス一覧の取得**: 中国リージョンで利用可能なAWSサービスの一覧を取得します（中国のみ）

## 前提条件 {#prerequisites}

### インストール要件 {#installation-requirements}

1. [Astral](https://docs.astral.sh/uv/getting-started/installation/) または [GitHub README](https://github.com/astral-sh/uv#installation) から `uv` をインストールします
2. `uv python install 3.10` を使用して Python 3.10 以降をインストールします（より新しいバージョンでも構いません）

## インストール {#installation}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.aws-documentation-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-documentation-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22AWS_DOCUMENTATION_PARTITION%22%3A%22aws%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.aws-documentation-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLWRvY3VtZW50YXRpb24tbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiRkFTVE1DUF9MT0dfTEVWRUwiOiJFUlJPUiIsIkFXU19ET0NVTUVOVEFUSU9OX1BBUlRJVElPTiI6ImF3cyJ9LCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20Documentation%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-documentation-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22AWS_DOCUMENTATION_PARTITION%22%3A%22aws%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

MCPクライアントの設定でMCPサーバーを構成します:

```json
{
  "mcpServers": {
    "awslabs.aws-documentation-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-documentation-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_DOCUMENTATION_PARTITION": "aws",
        "MCP_USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

KiroのMCP設定については、[Kiro IDEドキュメント](https://kiro.dev/docs/mcp/configuration/)または[Kiro CLIドキュメント](https://kiro.dev/docs/cli/mcp/configuration/)を参照してください。

グローバル設定の場合は `~/.kiro/settings/mcp.json` を編集します。プロジェクト固有の設定の場合は、プロジェクトディレクトリ内の `.kiro/settings/mcp.json` を編集します。

### Windowsでのインストール {#windows-installation}

Windowsユーザーの場合、MCPサーバーの設定形式は少し異なります:

```json
{
  "mcpServers": {
    "awslabs.aws-documentation-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.aws-documentation-mcp-server@latest",
        "awslabs.aws-documentation-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_DOCUMENTATION_PARTITION": "aws"
      }
    }
  }
}
```


> **注**: グローバルのAWSドキュメントではなくAWS中国のドキュメントを照会するには、`AWS_DOCUMENTATION_PARTITION` を `aws-cn` に設定してください。
>
> **企業ネットワーク**: 特定のUser-Agent文字列をブロックする企業のプロキシやファイアウォールの内側にいる場合は、`MCP_USER_AGENT` をお使いのブラウザのUser-Agentに合わせて許可される文字列に設定してください。

または、`docker build -t mcp/aws-documentation .` が成功した後にdockerを使用します:

```json
{
  "mcpServers": {
    "awslabs.aws-documentation-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env",
        "FASTMCP_LOG_LEVEL=ERROR",
        "--env",
        "AWS_DOCUMENTATION_PARTITION=aws",
        "mcp/aws-documentation:latest"
      ],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## 環境変数 {#environment-variables}

| 変数 | 説明 | デフォルト |
|----------|-------------|----------|
| `FASTMCP_LOG_LEVEL` | ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL) | `WARNING` |
| `AWS_DOCUMENTATION_PARTITION` | AWSパーティション（`aws` または `aws-cn`） | `aws` |
| `MCP_USER_AGENT` | HTTPリクエスト用のカスタムUser-Agent文字列 | Chromeベースのデフォルト |

### 企業ネットワークのサポート {#corporate-network-support}

特定のUser-Agent文字列をブロックするプロキシサーバーやファイアウォールがある企業環境の場合:

```json
{
  "env": {
    "MCP_USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
  }
}
```

## 基本的な使い方 {#basic-usage}

例:

- 「S3バケットの命名規則に関するドキュメントを調べてください。情報源を引用してください」
- 「ページ https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucketnamingrules.html のおすすめコンテンツを教えてください」

![AWS Documentation MCP Demo](https://github.com/awslabs/mcp/blob/main/src/aws-documentation-mcp-server/basic-usage.gif?raw=true)

## ツール {#tools}

### read_documentation {#read_documentation}

AWSドキュメントのページを取得し、markdown形式に変換します。

```python
read_documentation(url: str) -> str
```

### search_documentation（グローバルのみ） {#search_documentation-global-only}

公式のAWS Documentation Search APIを使用してAWSドキュメントを検索します。

```python
search_documentation(ctx: Context, search_phrase: str, limit: int, product_types: Optional[List[str]], guide_types: Optional[List[str]]) -> SearchResponse
```

### read_sections（グローバルのみ） {#read_sections-global-only}

AWSドキュメントページのセクションを取得し、markdown形式に変換します。

```python
read_sections(url: str, section: list[str]) -> list[dict]
```

### recommend（グローバルのみ） {#recommend-global-only}

AWSドキュメントページのコンテンツレコメンデーションを取得します。

```python
recommend(url: str) -> list[dict]
```

### get_available_services（中国のみ） {#get_available_services-china-only}

中国リージョンで利用可能なAWSサービスの一覧を取得します。

```python
get_available_services() -> str
```

## 開発 {#development}

AWS Documentation MCPサーバーの開発を始めるにあたっては、まず awslabs/mcp の DEVELOPER_GUIDE を参照してください。これより下の内容は、AWS Documentation MCPサーバーの開発に固有のものです。

### テストの実行 {#running-tests}

ユニットテスト: `uv run --frozen pytest --cov --cov-branch --cov-report=term-missing`
統合テストを含むユニットテスト: `uv run --frozen pytest --cov --cov-branch --cov-report=term-missing --run-live`
