---
title: "Amazon DocumentDB MCPサーバー"
---

AI アシスタントが DocumentDB データベースと連携できるようにする、AWS DocumentDB 向けの AWS Labs Model Context Protocol (MCP) サーバーです。

## 概要 {#overview}

DocumentDB MCP サーバーは、AWS DocumentDB データベースへの接続とクエリを行うためのツールを提供します。AI アシスタントと AWS DocumentDB の橋渡し役として機能し、Model Context Protocol (MCP) を通じて安全かつ効率的なデータベース操作を可能にします。

## 機能 {#features}

- **接続管理**: DocumentDB クラスターへの接続の確立と維持
- **データベース管理**: データベースの一覧表示とデータベース統計の取得
- **コレクション管理**: コレクションの一覧表示、作成、削除、およびコレクション統計の取得
- **ドキュメント操作**: ドキュメントのクエリ、挿入、更新、削除
- **集約パイプライン**: DocumentDB の集約パイプラインの実行
- **クエリプランニング**: 操作がどのように実行されるかの説明の取得
- **スキーマ分析**: ドキュメントをサンプリングしてコレクションのスキーマを分析
- **読み取り専用モード**: 操作を読み取り専用に制限するオプションのセキュリティ機能

## 利用可能なツール {#available-tools}

DocumentDB MCP サーバーは、以下のツールを提供します。

### 接続管理 {#connection-management}

- `connect`: DocumentDB クラスターに接続し、接続 ID を取得する
- `disconnect`: アクティブな接続を閉じる

### データベース管理 {#database-management}

- `listDatabases`: DocumentDB クラスター内の利用可能なすべてのデータベースを一覧表示する
- `getDatabaseStats`: DocumentDB データベースに関する統計を取得する

### コレクション管理 {#collection-management}

- `listCollections`: データベース内のコレクションを一覧表示する
- `createCollection`: データベース内に新しいコレクションを作成する（読み取り専用モードではブロックされます）
- `dropCollection`: データベースからコレクションを削除する（読み取り専用モードではブロックされます）
- `getCollectionStats`: コレクションに関する統計を取得する
- `countDocuments`: コレクション内のドキュメント数をカウントする
- `analyzeSchema`: ドキュメントをサンプリングしてコレクションのスキーマを分析し、フィールドのカバレッジを提供する

### ドキュメント操作 {#document-operations}

- `find`: コレクションからドキュメントをクエリする
- `aggregate`: 集約パイプラインを実行する（`$out` または `$merge` ステージを含むパイプラインは読み取り専用モードではブロックされます）
- `insert`: ドキュメントを挿入する（読み取り専用モードではブロックされます）
- `update`: ドキュメントを更新する（読み取り専用モードではブロックされます）
- `delete`: ドキュメントを削除する（読み取り専用モードではブロックされます）

### クエリプランニング {#query-planning}

- `explainOperation`: 操作がどのように実行されるかの説明を取得する

## サーバー設定 {#server-configuration}

### サーバーの起動 {#starting-the-server}

```bash
# Basic usage
python -m awslabs.documentdb_mcp_server.server

# With custom port and host
python -m awslabs.documentdb_mcp_server.server --port 9000 --host 0.0.0.0

# With write operations enabled
python -m awslabs.documentdb_mcp_server.server --allow-write
```

### コマンドラインオプション {#command-line-options}

| オプション | 説明 | デフォルト |
|--------|-------------|---------|
| `--log-level` | ログレベルを設定する（TRACE、DEBUG、INFO など） | INFO |
| `--connection-timeout` | アイドル接続のタイムアウト（分単位） | 30 |
| `--allow-write` | 書き込み操作を有効にする（指定しない場合は読み取り専用モードがデフォルト） | False |

### 読み取り専用モード {#read-only-mode}

デフォルトでは、サーバーは読み取り操作のみを許可する読み取り専用モードで実行されます。これにより、データベースへのいかなる変更も防止され、セキュリティが強化されます。読み取り専用モードでは、次のようになります。

- 読み取り操作（`find`、`listCollections`）は通常どおり動作します
- 集約パイプライン（`aggregate`）は通常どおり動作しますが、`$out` または `$merge` ステージを含むパイプラインはブロックされます
- 書き込み操作（`insert`、`update`、`delete`、`createCollection`、`dropCollection`）はブロックされ、権限エラーを返します
- 接続管理操作（`connect`、`disconnect`）は通常どおり動作します

このモードは、特に以下のような用途に役立ちます。
- デモンストレーション環境
- セキュリティが重視されるアプリケーション
- 一般公開向けの AI アシスタントとの統合
- 意図しない変更から本番データベースを保護する場合

## 使用例 {#usage-examples}

### 基本的な接続とクエリ（読み取り専用操作） {#basic-connection-and-query-read-only-operations}

```python
# Connect to a DocumentDB cluster
connection_result = await use_mcp_tool(
    server_name="awslabs.aws-documentdb-mcp-server",
    tool_name="connect",
    arguments={
        "connection_string": "mongodb://<username>:<password>@docdb-cluster.cluster-xyz.us-west-2.docdb.amazonaws.com:27017/?tls=true&tlsCAFile=global-bundle.pem"
    }
)
connection_id = connection_result["connection_id"]

# Query documents
query_result = await use_mcp_tool(
    server_name="awslabs.aws-documentdb-mcp-server",
    tool_name="find",
    arguments={
        "connection_id": connection_id,
        "database": "my_database",
        "collection": "users",
        "query": {"active": True},
        "limit": 5
    }
)

# Close the connection when done
await use_mcp_tool(
    server_name="awslabs.aws-documentdb-mcp-server",
    tool_name="disconnect",
    arguments={"connection_id": connection_id}
)
```

### 書き込み操作の有効化 {#enabling-write-operations}

書き込み操作を有効にするには、`--allow-write` フラグを付けてサーバーを起動します。

```bash
python -m awslabs.documentdb_mcp_server.server --allow-write
```

書き込み操作が有効な状態でサーバーが実行されている場合:

```python
# This operation will succeed
query_result = await use_mcp_tool(
    server_name="awslabs.aws-documentdb-mcp-server",
    tool_name="find",
    arguments={
        "connection_id": connection_id,
        "database": "my_database",
        "collection": "users",
        "query": {"active": True}
    }
)

# This operation will now succeed when --allow-write is used
insert_result = await use_mcp_tool(
    server_name="awslabs.aws-documentdb-mcp-server",
    tool_name="insert",
    arguments={
        "connection_id": connection_id,
        "database": "my_database",
        "collection": "users",
        "documents": {"name": "New User", "active": True}
    }
)

# Without the --allow-write flag, you would receive this error:
# ValueError: "Operation not permitted: Server is configured in read-only mode. Use --allow-write flag when starting the server to enable write operations."
```

### MCP クライアントでの設定 {#configure-in-your-mcp-client}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.documentdb-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.documentdb-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22AWS_PROFILE%22%3A%22your-aws-profile%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.documentdb-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuZG9jdW1lbnRkYi1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIiwiQVdTX1BST0ZJTEUiOiJ5b3VyLWF3cy1wcm9maWxlIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ==) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=DocumentDB%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.documentdb-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22AWS_PROFILE%22%3A%22your-aws-profile%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

MCP クライアントの設定で MCP サーバーを設定します（例: Kiro の場合、~/.kiro/settings/mcp.json を編集）。

```json
{
  "mcpServers": {
    "awslabs.documentdb-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.documentdb-mcp-server@latest",
      ],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```
### Windows でのインストール {#windows-installation}

Windows ユーザーの場合、MCP サーバーの設定形式は少し異なります。

```json
{
  "mcpServers": {
    "awslabs.documentdb-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.documentdb-mcp-server@latest",
        "awslabs.documentdb-mcp-server.exe"
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


## 前提条件 {#prerequisites}

- DocumentDB クラスターへのネットワークアクセス
- クラスターが TLS を必要とする場合は SSL/TLS 証明書（通常は `global-bundle.pem`）
