---
title: "AWS ElastiCache MCPサーバー"
---

AWS ElastiCache コントロールプレーンと対話するための公式 MCP サーバーです。ElastiCache Serverless キャッシュや自己設計クラスター内のデータを操作するには、[Valkey MCP Server](https://github.com/awslabs/mcp/blob/main/src/valkey-mcp-server) または [Memcached MCP Server](https://github.com/awslabs/mcp/blob/main/src/memcached-mcp-server) を使用してください。

## 利用可能な MCP ツール {#available-mcp-tools}

### サーバーレスキャッシュ操作 {#serverless-cache-operations}
- `create-serverless-cache` - 新しい ElastiCache サーバーレスキャッシュを作成します
- `delete-serverless-cache` - サーバーレスキャッシュを削除します
- `describe-serverless-caches` - サーバーレスキャッシュに関する情報を取得します
- `modify-serverless-cache` - サーバーレスキャッシュの設定を変更します
- `connect-jump-host-serverless-cache` - サーバーレスキャッシュへのアクセス用ジャンプホストとして EC2 インスタンスを設定します
- `create-jump-host-serverless-cache` - SSH トンネル経由でサーバーレスキャッシュにアクセスするための EC2 ジャンプホストを作成します
- `get-ssh-tunnel-command-serverless-cache` - サーバーレスキャッシュへのアクセス用 SSH トンネルコマンドを生成します

### レプリケーショングループ操作 {#replication-group-operations}
- `create-replication-group` - 指定した構成で Amazon ElastiCache レプリケーショングループを作成します
- `delete-replication-group` - ElastiCache レプリケーショングループを削除します（オプションで最終スナップショットを取得できます）
- `describe-replication-groups` - 1 つ以上のレプリケーショングループに関する詳細情報を取得します
- `modify-replication-group` - 既存のレプリケーショングループの設定を変更します
- `modify-replication-group-shard-configuration` - レプリケーショングループのシャード構成を変更します
- `test-migration` - Redis インスタンスから ElastiCache レプリケーショングループへの移行をテストします
- `start-migration` - Redis インスタンスから ElastiCache レプリケーショングループへの移行を開始します
- `complete-migration` - Redis インスタンスから ElastiCache レプリケーショングループへの移行を完了します
- `connect-jump-host-replication-group` - レプリケーショングループへのアクセス用ジャンプホストとして EC2 インスタンスを設定します
- `create-jump-host-replication-group` - SSH トンネル経由でレプリケーショングループにアクセスするための EC2 ジャンプホストを作成します
- `get-ssh-tunnel-command-replication-group` - レプリケーショングループへのアクセス用 SSH トンネルコマンドを生成します

### キャッシュクラスター操作 {#cache-cluster-operations}
- `create-cache-cluster` - 新しい ElastiCache キャッシュクラスターを作成します
- `delete-cache-cluster` - キャッシュクラスターを削除します（オプションで最終スナップショットを取得できます）
- `describe-cache-clusters` - 1 つ以上のキャッシュクラスターに関する詳細情報を取得します
- `modify-cache-cluster` - 既存のキャッシュクラスターの設定を変更します
- `connect-jump-host-cache-cluster` - クラスターへのアクセス用ジャンプホストとして EC2 インスタンスを設定します
- `create-jump-host-cache-cluster` - SSH トンネル経由でクラスターにアクセスするための EC2 ジャンプホストを作成します
- `get-ssh-tunnel-command-cache-cluster` - クラスターへのアクセス用 SSH トンネルコマンドを生成します

### CloudWatch 操作 {#cloudwatch-operations}
- `get-metric-statistics` - ElastiCache リソースの CloudWatch メトリクス統計を、期間やディメンションをカスタマイズして取得します

### CloudWatch Logs 操作 {#cloudwatch-logs-operations}
- `describe-log-groups` - CloudWatch Logs のロググループを一覧表示および説明します
- `create-log-group` - 新しい CloudWatch Logs ロググループを作成します
- `describe-log-streams` - ロググループ内のログストリームを一覧表示および説明します
- `filter-log-events` - ログストリーム全体でログイベントを検索およびフィルタリングします
- `get-log-events` - 特定のログストリームからログイベントを取得します

### Firehose 操作 {#firehose-operations}
- `list-delivery-streams` - Kinesis Data Firehose 配信ストリームを一覧表示します

### Cost Explorer 操作 {#cost-explorer-operations}
- `get-cost-and-usage` - ElastiCache リソースのコストと使用状況データを、期間や粒度をカスタマイズして取得します

### その他の操作 {#misc-operations}
- `describe-cache-engine-versions` - 利用可能なキャッシュエンジンとそのバージョンを一覧表示します
- `describe-engine-default-parameters` - キャッシュエンジンファミリーのデフォルトパラメータを取得します
- `describe-events` - クラスター、セキュリティグループ、パラメータに関連するイベントを取得します
- `describe-service-updates` - 利用可能なサービス更新に関する情報を取得します
- `batch-apply-update-action` - リソースにサービス更新を適用します
- `batch-stop-update-action` - リソースに対するサービス更新を停止します

## 手順 {#instructions}

AWS ElastiCache と対話するための公式 MCP サーバーは、ElastiCache リソースを管理するための包括的なツールセットを提供します。各ツールは ElastiCache API 操作に直接対応しており、関連するすべてのパラメータをサポートしています。

これらのツールを使用するには、ElastiCache 操作に対する適切な権限を持つ AWS 認証情報が設定されていることを確認してください。サーバーは、環境変数（AWS_ACCESS_KEY_ID、AWS_SECRET_ACCESS_KEY、AWS_SESSION_TOKEN）またはその他の標準的な AWS 認証情報ソースから自動的に認証情報を使用します。

すべてのツールは、操作対象の AWS リージョンを指定するためのオプションの `region_name` パラメータをサポートしています。指定しない場合は、AWS_REGION 環境変数を使用するか、デフォルトで 'us-west-2' を使用します。

## 前提条件 {#prerequisites}

1. [Astral](https://docs.astral.sh/uv/getting-started/installation/) または [GitHub README](https://github.com/astral-sh/uv#installation) から `uv` をインストールします
2. `uv python install 3.10` を使用して Python をインストールします
3. AWS サービスへのアクセス権を持つ AWS 認証情報を設定します
   - LLM にリソースを変更させたくない場合は、読み取り専用権限の設定を検討してください

## インストール {#installation}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.elasticache-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.elasticache-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22default%22%2C%22AWS_REGION%22%3A%22us-west-2%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.elasticache-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuZWxhc3RpY2FjaGUtbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiQVdTX1BST0ZJTEUiOiJkZWZhdWx0IiwiQVdTX1JFR0lPTiI6InVzLXdlc3QtMiIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=ElastiCache%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.elasticache-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22default%22%2C%22AWS_REGION%22%3A%22us-west-2%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

お好みのエージェントツールに MCP を追加してください。（例：Kiro の場合は `~/.kiro/settings/mcp.json`）：

```json
{
  "mcpServers": {
    "awslabs.elasticache-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.elasticache-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-west-2",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```
MCP による変更操作（リソースの作成/更新/削除など）を防ぎたい場合は、以下のように readonly フラグを指定できます：

```json
{
  "mcpServers": {
    "awslabs.elasticache-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.elasticache-mcp-server@latest",
        "--readonly"
      ],
      "env": {
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-west-2",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Windows へのインストール {#windows-installation}

Windows ユーザーの場合、MCP サーバーの設定形式は少し異なります：

```json
{
  "mcpServers": {
    "awslabs.elasticache-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.elasticache-mcp-server@latest",
        "awslabs.elasticache-mcp-server.exe"
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

または、`docker build -t awslabs/elasticache-mcp-server .` が成功した後に docker を使用する場合：

```json
{
  "mcpServers": {
    "awslabs.elasticache-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env",
        "FASTMCP_LOG_LEVEL=ERROR",
        "awslabs/elasticache-mcp-server:latest",
        "--readonly" // Optional paramter if you would like to restrict the MCP to only read actions
      ],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## 設定 {#configuration}

### AWS の設定 {#aws-configuration}

AWS 認証情報とリージョンを設定します：

```bash
# AWS settings
AWS_PROFILE=default              # AWS credential profile to use
AWS_REGION=us-east-1            # AWS region to connect to
```

### 接続設定 {#connection-settings}

接続動作とタイムアウトを設定します：

```bash
# Connection settings
ELASTICACHE_MAX_RETRIES=3        # Maximum number of retry attempts for AWS API calls
ELASTICACHE_RETRY_MODE=standard  # AWS SDK retry mode for API calls
ELASTICACHE_CONNECT_TIMEOUT=5    # Connection timeout in seconds
ELASTICACHE_READ_TIMEOUT=10      # Read timeout in seconds

# Cost Explorer settings
COST_EXPLORER_MAX_RETRIES=3      # Maximum number of retry attempts for Cost Explorer API calls
COST_EXPLORER_RETRY_MODE=standard # AWS SDK retry mode for Cost Explorer API calls
COST_EXPLORER_CONNECT_TIMEOUT=5   # Connection timeout in seconds for Cost Explorer
COST_EXPLORER_READ_TIMEOUT=10     # Read timeout in seconds for Cost Explorer

# CloudWatch settings
CLOUDWATCH_MAX_RETRIES=3         # Maximum number of retry attempts for CloudWatch API calls
CLOUDWATCH_RETRY_MODE=standard    # AWS SDK retry mode for CloudWatch API calls
CLOUDWATCH_CONNECT_TIMEOUT=5      # Connection timeout in seconds for CloudWatch
CLOUDWATCH_READ_TIMEOUT=10        # Read timeout in seconds for CloudWatch

# CloudWatch Logs settings
CLOUDWATCH_LOGS_MAX_RETRIES=3     # Maximum number of retry attempts for CloudWatch Logs API calls
CLOUDWATCH_LOGS_RETRY_MODE=standard # AWS SDK retry mode for CloudWatch Logs API calls
CLOUDWATCH_LOGS_CONNECT_TIMEOUT=5  # Connection timeout in seconds for CloudWatch Logs
CLOUDWATCH_LOGS_READ_TIMEOUT=10    # Read timeout in seconds for CloudWatch Logs

# Firehose settings
FIREHOSE_MAX_RETRIES=3            # Maximum number of retry attempts for Firehose API calls
FIREHOSE_RETRY_MODE=standard      # AWS SDK retry mode for Firehose API calls
FIREHOSE_CONNECT_TIMEOUT=5        # Connection timeout in seconds for Firehose
FIREHOSE_READ_TIMEOUT=10          # Read timeout in seconds for Firehose
```

サーバーは以下を自動的に処理します：
- AWS 認証と認証情報の管理
- 接続の確立と管理
- 失敗した操作の自動リトライ
- タイムアウトの適用とエラー処理

## 開発 {#development}

### テストの実行 {#running-tests}
```bash
uv venv
source .venv/bin/activate
uv sync
uv run --frozen pytest
```

### Docker イメージのビルド {#building-docker-image}
```bash
docker build -t awslabs/elasticache-mcp-server .
```

### Docker コンテナの実行 {#running-docker-container}
```bash
docker run -p 8080:8080 \
  -e AWS_PROFILE=default \
  -e AWS_REGION=us-west-2 \
  awslabs/elasticache-mcp-server
```
