---
title: "Prometheus MCPサーバー"
---

Prometheus MCP サーバーは、AWS Managed Prometheus とやり取りするための堅牢なインターフェースを提供し、ユーザーが AWS SigV4 認証のサポートのもとで PromQL クエリの実行、メトリクスの一覧表示、サーバー情報の取得を行えるようにします。

この MCP サーバーは Kiro と完全に互換性を持つように設計されており、Prometheus のモニタリング機能を Kiro のワークフローにシームレスに統合できます。サーバーを Kiro に直接ロードすることで、使い慣れた Kiro IDE や Kiro CLI のインターフェースを通じて、その強力なクエリ機能とメトリクス分析機能を活用できます。

## 機能 {#features}

- AWS Managed Prometheus に対する PromQL のインスタントクエリの実行
- 開始時刻、終了時刻、ステップ間隔を指定したレンジクエリの実行
- Prometheus インスタンスで利用可能なすべてのメトリクスの一覧表示
- サーバー設定情報の取得
- セキュアなアクセスのための AWS SigV4 認証
- 指数バックオフによる自動リトライ

## インストール {#installation}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.prometheus-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.prometheus-mcp-server%40latest%22%2C%22--url%22%2C%22https%3A//aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-%3CWorkspace%20ID%3E%22%2C%22--region%22%2C%22%3CYour%20AWS%20Region%3E%22%2C%22--profile%22%2C%22%3CYour%20CLI%20Profile%20%5Bdefault%5D%20if%20no%20profile%20is%20used%3E%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22DEBUG%22%2C%22AWS_PROFILE%22%3A%22%3CYour%20CLI%20Profile%20%5Bdefault%5D%20if%20no%20profile%20is%20used%3E%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.prometheus-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMucHJvbWV0aGV1cy1tY3Atc2VydmVyQGxhdGVzdCAtLXVybCBodHRwczovL2Fwcy13b3Jrc3BhY2VzLnVzLWVhc3QtMS5hbWF6b25hd3MuY29tL3dvcmtzcGFjZXMvd3MtPFdvcmtzcGFjZSBJRD4gLS1yZWdpb24gPFlvdXIgQVdTIFJlZ2lvbj4gLS1wcm9maWxlIDxZb3VyIENMSSBQcm9maWxlIFtkZWZhdWx0XSBpZiBubyBwcm9maWxlIGlzIHVzZWQ%2BIiwiZW52Ijp7IkZBU1RNQ1BfTE9HX0xFVkVMIjoiREVCVUciLCJBV1NfUFJPRklMRSI6IjxZb3VyIENMSSBQcm9maWxlIFtkZWZhdWx0XSBpZiBubyBwcm9maWxlIGlzIHVzZWQ%2BIn19) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Prometheus%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.prometheus-mcp-server%40latest%22%2C%22--url%22%2C%22https%3A%2F%2Faps-workspaces.us-east-1.amazonaws.com%2Fworkspaces%2Fws-%3CWorkspace%20ID%3E%22%2C%22--region%22%2C%22%3CYour%20AWS%20Region%3E%22%2C%22--profile%22%2C%22%3CYour%20CLI%20Profile%20%5Bdefault%5D%20if%20no%20profile%20is%20used%3E%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22DEBUG%22%2C%22AWS_PROFILE%22%3A%22%3CYour%20CLI%20Profile%20%5Bdefault%5D%20if%20no%20profile%20is%20used%3E%22%7D%7D) |

### 前提条件 {#prerequisites}

- Python 3.10 以降
- 適切な権限を設定した AWS 認証情報
- AWS Managed Prometheus のワークスペース



## 設定 {#configuration}

このサーバーは、以下の使用方法セクションに示すように、Kiro の MCP 設定ファイルを通じて設定します。

## Kiro での使用 {#usage-with-kiro}

1. 設定ファイルを作成します。
```bash
mkdir -p ~/.kiro/settings/
```

2. `~/.kiro/settings/mcp.json` に以下を追加します。

### 基本設定 {#basic-configuration}
```json
{
  "mcpServers": {
    "prometheus": {
      "command": "uvx",
      "args": [
        "awslabs.prometheus-mcp-server@latest"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```
### Windows でのインストール {#windows-installation}

Windows ユーザーの場合、MCP サーバーの設定形式は少し異なります。

```json
{
  "mcpServers": {
    "awslabs.prometheus-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.prometheus-mcp-server@latest",
        "awslabs.prometheus-mcp-server.exe"
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


### オプション引数を使った設定 {#configuration-with-optional-arguments}
```json
{
  "mcpServers": {
    "prometheus": {
      "command": "uvx",
      "args": [
        "awslabs.prometheus-mcp-server@latest",
        "--url",
        "https://aps-workspaces.<AWS Region>.amazonaws.com/workspaces/ws-<Workspace ID>",
        "--region",
        "<Your AWS Region>",
        "--profile",
        "<Your CLI Profile>"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

3. これで Kiro 上で Prometheus MCP サーバーを使ってメトリクスをクエリできるようになります。

## 利用可能なツール {#available-tools}

1. **GetAvailableWorkspaces**
   - 指定したリージョンで利用可能なすべての Prometheus ワークスペースを一覧表示します
   - パラメータ: region（オプション）
   - 戻り値: ID、エイリアス、ステータスを含むワークスペースのリスト

2. **ExecuteQuery**
   - Prometheus に対して PromQL のインスタントクエリを実行します
   - パラメータ: workspace_id（必須）、query（必須）、time（オプション）、region（オプション）

3. **ExecuteRangeQuery**
   - 指定した時間範囲にわたって PromQL クエリを実行します
   - パラメータ: workspace_id（必須）、query、start time、end time、step interval、region（オプション）

4. **ListMetrics**
   - Prometheus から利用可能なすべてのメトリクス名を取得します
   - パラメータ: workspace_id（必須）、region（オプション）
   - 戻り値: ソートされたメトリクス名のリスト

5. **GetServerInfo**
   - サーバーの設定詳細を取得します
   - パラメータ: workspace_id（必須）、region（オプション）
   - 戻り値: URL、リージョン、プロファイル、サービス情報

## クエリの例 {#example-queries}

```python
# Get available workspaces
workspaces = await get_available_workspaces()
for ws in workspaces['workspaces']:
    print(f"ID: {ws['workspace_id']}, Alias: {ws['alias']}, Status: {ws['status']}")

# Execute an instant query
result = await execute_query(
    workspace_id="ws-12345678-abcd-1234-efgh-123456789012",
    query="up"
)

# Execute a range query
data = await execute_range_query(
    workspace_id="ws-12345678-abcd-1234-efgh-123456789012",
    query="rate(node_cpu_seconds_total[5m])",
    start="2023-01-01T00:00:00Z",
    end="2023-01-01T01:00:00Z",
    step="1m"
)

# List available metrics
metrics = await list_metrics(
    workspace_id="ws-12345678-abcd-1234-efgh-123456789012"
)

# Get server information
info = await get_server_info(
    workspace_id="ws-12345678-abcd-1234-efgh-123456789012"
)
```

## トラブルシューティング {#troubleshooting}

よくある問題と解決策:

1. **AWS 認証情報が見つからない**
   - ~/.aws/credentials を確認する
   - AWS_PROFILE 環境変数を設定する
   - IAM 権限を確認する

2. **接続エラー**
   - Prometheus の URL が正しいか確認する
   - ネットワーク接続を確認する
   - AWS VPC アクセスが正しく設定されているか確認する

3. **認証の失敗**
   - AWS 認証情報が最新であるか確認する
   - システムクロックの同期を確認する
   - 正しい AWS リージョンが指定されているか確認する

## ライセンス {#license}

このプロジェクトは Apache License 2.0 の下でライセンスされています。詳細については LICENSE ファイルを参照してください。
