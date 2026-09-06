---
title: "AWS Labs CloudTrail MCPサーバー"
---

CloudTrail 向けのこの AWS Labs Model Context Protocol (MCP) サーバーは、AI エージェントがセキュリティ調査、コンプライアンス監査、運用上のトラブルシューティングのために AWS アカウントのアクティビティをクエリできるようにします。CloudTrail イベントと CloudTrail Lake の分析機能への包括的なアクセスを提供し、エージェントが API 呼び出しの追跡、ユーザーアクティビティの分析、高度なセキュリティ分析を行えるようにします。このサーバーは、標準化された MCP インターフェースを通じて AI エージェントに CloudTrail データへのシームレスなアクセスを提供し、カスタム API 統合の必要性を排除して、強力なセキュリティインサイトと監査機能を実現します。

## 手順 {#instructions}

CloudTrail MCP サーバーは、イベント検索、ユーザーアクティビティ分析、API 呼び出しの追跡、高度な CloudTrail Lake 分析など、よくあるセキュリティおよび運用シナリオに対応するための専用ツールを提供します。各ツールは、1 つまたは複数の CloudTrail API をタスク指向の操作としてカプセル化しています。

## 機能 {#features}

**イベント検索** - ユーザー名、イベント名、リソース名など、さまざまな属性で CloudTrail イベントを検索します。セキュリティ調査やトラブルシューティングのために、過去 90 日間の管理イベントへのアクセスを提供します。

**CloudTrail Lake 分析** - 複雑な分析、フィルタリング、集計のために、CloudTrail Lake に対して高度な SQL クエリを実行します。包括的なイベント分析のために Trino 互換の SQL 構文をサポートします。

**ユーザーアクティビティ分析** - ユーザー名、アクセスキー、その他のユーザー関連属性でイベントをフィルタリングして、AWS サービス全体のユーザーアクティビティを追跡・分析します。

**API 呼び出しの追跡** - セキュリティおよびコンプライアンスの目的で、AWS 環境全体における特定の API 呼び出しとそのパターンを監視します。

**イベントデータストア管理** - 利用可能な CloudTrail Lake のイベントデータストアを一覧表示および探索し、データソースとその機能を把握します。

## 前提条件 {#prerequisites}
1. [CloudTrail](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-user-guide.html) が有効な AWS アカウント。CloudTrail イベント履歴はデフォルトで有効です。高度な SQL クエリには CloudTrail Lake を有効にする必要があります。
2. この MCP サーバーは、LLM クライアントと同じホスト上でローカルにのみ実行できます。
3. AWS サービスへのアクセス権を持つ AWS 認証情報を設定すること
   - 適切な権限を持つ AWS アカウントが必要です（以下の必要な権限を参照）
   - `aws configure` または環境変数で AWS 認証情報を設定します

## 利用可能なツール {#available-tools}

### CloudTrail Events 用ツール {#tools-for-cloudtrail-events}
* `lookup_events` - ユーザー名、イベント名、リソース名など、さまざまな条件に基づいて CloudTrail イベントを検索します。ページネーション対応で、過去 90 日間の管理イベントへのアクセスを提供します

### CloudTrail Lake 分析用ツール {#tools-for-cloudtrail-lake-analytics}
* `lake_query` - 複雑な分析やフィルタリングのために、CloudTrail Lake に対して SQL クエリを実行します。高度な分析のために Trino 互換の SQL 構文をサポートします
* `list_event_data_stores` - 利用可能な CloudTrail Lake のイベントデータストアを、その機能とイベントセレクターとともに一覧表示します
* `get_query_status` - 長時間実行されるクエリを監視するために、CloudTrail Lake クエリのステータスを取得します
* `get_query_results` - 完了した CloudTrail Lake クエリの結果を取得します。大きな結果セットに対応するページネーションをサポートします

### 必要な IAM 権限 {#required-iam-permissions}
* `cloudtrail:LookupEvents`
* `cloudtrail:ListEventDataStores`
* `cloudtrail:GetEventDataStore`
* `cloudtrail:StartQuery`
* `cloudtrail:DescribeQuery`
* `cloudtrail:GetQueryResults`

## インストール {#installation}

### オプション 1: Python (UVX) {#option-1-python-uvx}
#### 前提条件 {#prerequisites-1}
1. [Astral](https://docs.astral.sh/uv/getting-started/installation/) または [GitHub README](https://github.com/astral-sh/uv#installation) から `uv` をインストールします
2. `uv python install 3.10` で Python をインストールします

#### ワンクリックインストール {#one-click-install}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.cloudtrail-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.cloudtrail-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22%5BThe%20AWS%20Profile%20Name%20to%20use%20for%20AWS%20access%5D%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.cloudtrail-mcp-server&config=ewogICAgImF1dG9BcHByb3ZlIjogW10sCiAgICAiZGlzYWJsZWQiOiBmYWxzZSwKICAgICJjb21tYW5kIjogInV2eCBhd3NsYWJzLmNsb3VkdHJhaWwtbWNwLXNlcnZlckBsYXRlc3QiLAogICAgImVudiI6IHsKICAgICAgIkFXU19QUk9GSUxFIjogIltUaGUgQVdTIFByb2ZpbGUgTmFtZSB0byB1c2UgZm9yIEFXUyBhY2Nlc3NdIiwKICAgICAgIkZBU1RNQ1BfTE9HX0xFVkVMIjogIkVSUk9SIgogICAgfSwKICAgICJ0cmFuc3BvcnRUeXBlIjogInN0ZGlvIgp9) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=CloudTrail%20MCP%20Server&config=%7B%22autoApprove%22%3A%5B%5D%2C%22disabled%22%3Afalse%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.cloudtrail-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22%5BThe%20AWS%20Profile%20Name%20to%20use%20for%20AWS%20access%5D%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22transportType%22%3A%22stdio%22%7D) |

#### MCP 設定 (Kiro, Cline) {#mcp-config-kiro-cline}
* Kiro の場合は、Kiro の MCP 設定 (~/.kiro/settings/mcp.json) を更新します
* Cline の場合は、MCP タブから「Configure MCP Servers」オプションをクリックします
```json
{
  "mcpServers": {
    "awslabs.cloudtrail-mcp-server": {
      "autoApprove": [],
      "disabled": false,
      "command": "uvx",
      "args": [
        "awslabs.cloudtrail-mcp-server@latest"
      ],
      "env": {
        "AWS_PROFILE": "[The AWS Profile Name to use for AWS access]",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "transportType": "stdio"
    }
  }
}
```

認証情報プロファイルの作成と管理については、[AWS ドキュメント](https://docs.aws.amazon.com/cli/v1/userguide/cli-configure-files.html)を参照してください

### オプション 2: Docker イメージ {#option-2-docker-image}
#### 前提条件 {#prerequisites-2}
LLM クライアントと同じホスト上で、Docker イメージをローカルにビルドしてインストールします
1. [Docker](https://docs.docker.com/desktop/) をインストールします
2. `git clone https://github.com/awslabs/mcp.git`
3. サブディレクトリに移動します: `cd src/cloudtrail-mcp-server/`
4. `docker build -t awslabs/cloudtrail-mcp-server:latest .` を実行します

#### Cursor へのワンクリックインストール {#one-click-cursor-install}
[![Install CloudTrail MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://www.cursor.com/install-mcp?name=awslabs.cloudtrail-mcp-server&config=ewogICAgICAgICJjb21tYW5kIjogImRvY2tlciIsCiAgICAgICAgImFyZ3MiOiBbCiAgICAgICAgICAicnVuIiwKICAgICAgICAgICItLXJtIiwKICAgICAgICAgICItLWludGVyYWN0aXZlIiwKICAgICAgICAgICItZSBBV1NfUFJPRklMRT1bVGhlIEFXUyBQcm9maWxlIE5hbWVdIiwKICAgICAgICAgICJhd3NsYWJzL2Nsb3VkdHJhaWwtbWNwLXNlcnZlcjpsYXRlc3QiCiAgICAgICAgXSwKICAgICAgICAiZW52Ijoge30sCiAgICAgICAgImRpc2FibGVkIjogZmFsc2UsCiAgICAgICAgImF1dG9BcHByb3ZlIjogW10KfQ==)

#### Docker イメージを使用した MCP 設定 (Kiro, Cline) {#mcp-config-using-docker-imagekiro-cline}
```json
  {
    "mcpServers": {
      "awslabs.cloudtrail-mcp-server": {
        "command": "docker",
        "args": [
          "run",
          "--rm",
          "--interactive",
          "-v ~/.aws:/root/.aws",
          "-e AWS_PROFILE=[The AWS Profile Name to use for AWS access]",
          "awslabs/cloudtrail-mcp-server:latest"
        ],
        "env": {},
        "disabled": false,
        "autoApprove": []
      }
    }
  }
```
認証情報プロファイルの作成と管理については、[AWS ドキュメント](https://docs.aws.amazon.com/cli/v1/userguide/cli-configure-files.html)を参照してください

## コントリビューション {#contributing}

コントリビューションを歓迎します！ガイドラインについては、モノレポのルートにある [CONTRIBUTING.md](https://github.com/awslabs/mcp/blob/main/CONTRIBUTING.md) を参照してください。

## フィードバックと課題 {#feedback-and-issues}

皆様のフィードバックをお待ちしています！フィードバック、機能リクエスト、バグ報告は、タイトルに `cloudtrail-mcp-server` というプレフィックスを付けて [GitHub issues](https://github.com/awslabs/mcp/issues) に送信してください。
