---
title: "AWS Labs Timestream for InfluxDB MCPサーバー"
---

Timestream for InfluxDB 向けの AWS Labs Model Context Protocol (MCP) サーバーです。このサーバーは AWS Timestream for InfluxDB の API と対話するためのツールを提供し、データベースインスタンス、クラスター、パラメータグループなどの作成・管理を可能にします。また、InfluxDB の書き込みおよびクエリ API と対話するためのツールも含まれています。

## 機能 {#features}

- Timestream for InfluxDB データベースインスタンスの作成、更新、一覧表示、詳細取得、削除
- Timestream for InfluxDB データベースクラスターの作成、更新、一覧表示、詳細取得、削除
- DB パラメータグループの管理
- Timestream for InfluxDB リソースのタグ管理
- InfluxDB 2 のバケットと組織の管理
- InfluxDB 2 API を使用したデータの書き込みとクエリ


## 前提条件 {#pre-requisites}
1. [Astral](https://docs.astral.sh/uv/getting-started/installation/) または [GitHub README](https://github.com/astral-sh/uv#installation) から `uv` をインストールします
2. `uv python install 3.10` を使用して Python をインストールします
3. AWS サービスへのアクセス権を持つ AWS 認証情報を設定します
    - 適切な権限を持つ AWS アカウントが必要です
    - `aws configure` または環境変数で AWS 認証情報を設定します
    - LLM にリソースを変更させたくない場合は、読み取り専用権限から始めることを検討してください

## インストール {#installation}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.timestream-for-influxdb-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.timestream-for-influxdb-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.timestream-for-influxdb-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMudGltZXN0cmVhbS1mb3ItaW5mbHV4ZGItbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiQVdTX1BST0ZJTEUiOiJ5b3VyLWF3cy1wcm9maWxlIiwiQVdTX1JFR0lPTiI6InVzLWVhc3QtMSIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Timestream%20for%20InfluxDB%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.timestream-for-influxdb-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

MCP クライアントの設定を変更して、ローカルサーバーを実行できます（例: Kiro の場合は `~/.kiro/settings/mcp.json`）

```json
{
  "mcpServers": {
    "awslabs.timestream-for-influxdb-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.timestream-for-influxdb-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "INFLUXDB_URL": "https://your-influxdb-endpoint:8086",
        "INFLUXDB_TOKEN": "your-influxdb-token",
        "INFLUXDB_ORG": "your-influxdb-org",
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
    "awslabs.timestream-for-influxdb-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.timestream-for-influxdb-mcp-server@latest",
        "awslabs.timestream-for-influxdb-mcp-server.exe"
      ],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "INFLUXDB_URL": "https://your-influxdb-endpoint:8086",
        "INFLUXDB_TOKEN": "your-influxdb-token",
        "INFLUXDB_ORG": "your-influxdb-org",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```


### 利用可能なツール {#available-tools}

Timestream for InfluxDB MCP サーバーは以下のツールを提供します。

#### AWS Timestream for InfluxDB の管理 {#aws-timestream-for-influxdb-management}

##### データベースクラスターの管理 {#database-cluster-management}
- `CreateDbCluster`: 新しい Timestream for InfluxDB データベースクラスターを作成します
- `GetDbCluster`: 特定の DB クラスターに関する情報を取得します
- `DeleteDbCluster`: Timestream for InfluxDB データベースクラスターを削除します
- `ListDbClusters`: すべての Timestream for InfluxDB データベースクラスターを一覧表示します
- `UpdateDbCluster`: Timestream for InfluxDB データベースクラスターを更新します
- `ListDbClusters`: すべての Timestream for InfluxDB データベースクラスターを一覧表示します
- `ListDbInstancesForCluster`: 特定のクラスターに属する DB インスタンスを一覧表示します
- `ListClustersByStatus`: ステータスでフィルタリングした DB クラスターを一覧表示します

##### データベースインスタンスの管理 {#database-instance-management}
- `CreateDbInstance`: 新しい Timestream for InfluxDB データベースインスタンスを作成します
- `GetDbInstance`: 特定の DB インスタンスに関する情報を取得します
- `DeleteDbInstance`: Timestream for InfluxDB データベースインスタンスを削除します
- `ListDbInstances`: すべての Timestream for InfluxDB データベースインスタンスを一覧表示します
- `UpdateDbInstance`: Timestream for InfluxDB データベースインスタンスを更新します
- `ListDbInstancesByStatus`: ステータスでフィルタリングした DB インスタンスを一覧表示します

##### パラメータグループの管理 {#parameter-group-management}
- `CreateDbParamGroup`: 新しい DB パラメータグループを作成します
- `GetDbParameterGroup`: 特定の DB パラメータグループに関する情報を取得します
- `ListDbParamGroups`: すべての DB パラメータグループを一覧表示します

##### タグ管理 {#tag-management}
- `ListTagsForResource`: Timestream for InfluxDB リソースのすべてのタグを一覧表示します
- `TagResource`: Timestream for InfluxDB リソースにタグを追加します
- `UntagResource`: Timestream for InfluxDB リソースからタグを削除します

#### InfluxDB データ操作 {#influxdb-data-operations}

##### Write API {#write-api}
- `InfluxDBWritePoints`: InfluxDB にデータポイントを書き込みます
- `InfluxDBWriteLP`: Line Protocol 形式のデータを InfluxDB に書き込みます

##### Query API {#query-api}
- `InfluxDBQuery`: Flux クエリ言語を使用して InfluxDB からデータをクエリします

##### バケット管理 {#bucket-management}
- `InfluxDBListBuckets`: InfluxDB 内のすべてのバケットを一覧表示します
- `InfluxDBCreateBucket`: InfluxDB に新しいバケットを作成します

##### 組織管理 {#organization-management}
- `InfluxDBListOrgs`: InfluxDB 内のすべての組織を一覧表示します
- `InfluxDBCreateOrg`: InfluxDB に新しい組織を作成します
