---
title: "Amazon Redshift MCPサーバー"
---

Amazon Redshift 向けの Model Context Protocol (MCP) サーバーです。

この MCP サーバーは、Amazon Redshift のクラスターおよびサーバーレスワークグループを検出、探索、クエリするためのツールを提供します。これにより、AI アシスタントは、包括的な検出およびクエリ実行ツールを通じて、Redshift リソースと安全かつ効率的に対話できるようになります。

## 機能 {#features}

- **クラスターの検出**: プロビジョンド Redshift クラスターとサーバーレスワークグループの両方を自動的に検出
- **メタデータの探索**: データベース、スキーマ、テーブル、カラムを閲覧
- **安全なクエリ実行**: 読み取り専用モードで SQL クエリを実行（単一ステートメント、書き込みは拒否）
- **マルチクラスターのサポート**: 複数のクラスターとワークグループを同時に操作

## 前提条件 {#prerequisites}

### インストール要件 {#installation-requirements}

1. [Astral](https://docs.astral.sh/uv/getting-started/installation/) または [GitHub README](https://github.com/astral-sh/uv#installation) から `uv` をインストールする
2. `uv python install 3.10` を使用して Python 3.10 以降（またはそれ以降のバージョン）をインストールする

### AWS クライアント要件 {#aws-client-requirements}

1. **認証情報**: AWS CLI または環境変数を使用して AWS 認証情報を設定する
2. **リージョン**: 以下のいずれかの方法で AWS リージョンを設定する（優先順位順）:
   - `AWS_REGION` 環境変数（最優先）
   - `AWS_DEFAULT_REGION` 環境変数
   - AWS プロファイル設定で指定されたリージョン
3. **権限**: AWS 認証情報に必要な権限があることを確認する（[権限](#permissions) セクションを参照）

## インストール {#installation}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.redshift-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.redshift-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22default%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22INFO%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.redshift-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMucmVkc2hpZnQtbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiQVdTX1BST0ZJTEUiOiJkZWZhdWx0IiwiQVdTX1JFR0lPTiI6InVzLWVhc3QtMSIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiSU5GTyJ9LCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Redshift%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.redshift-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22default%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22INFO%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

MCP クライアントの設定で MCP サーバーを構成します（例: Kiro の場合は `~/.kiro/settings/mcp.json` を編集します）。

```json
{
  "mcpServers": {
    "awslabs.redshift-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.redshift-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "default",
        "AWS_DEFAULT_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "INFO"
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
    "awslabs.redshift-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.redshift-mcp-server@latest",
        "awslabs.redshift-mcp-server.exe"
      ],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_DEFAULT_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

または、`docker build -t awslabs/redshift-mcp-server:latest .` が成功した後は docker を使用します。

```json
{
  "mcpServers": {
    "awslabs.redshift-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env", "AWS_ACCESS_KEY_ID=[your data]",
        "--env", "AWS_SECRET_ACCESS_KEY=[your data]",
        "--env", "AWS_DEFAULT_REGION=[your data]",
        "awslabs/redshift-mcp-server:latest"
      ]
    }
  }
}
```

### 環境変数 {#environment-variables}

- `AWS_REGION`: 使用する AWS リージョン（他のすべてのリージョン設定を上書きします）
- `AWS_DEFAULT_REGION`: デフォルトの AWS リージョン（AWS_REGION が未設定で、プロファイルにリージョンがない場合に使用されます）
- `AWS_PROFILE`: 使用する AWS プロファイル（オプション、指定しない場合は default を使用します）
- `FASTMCP_LOG_LEVEL`: ログレベル（`DEBUG`、`INFO`、`WARNING`、`ERROR`）
- `LOG_FILE`: ログファイルへのパス（オプション、指定しない場合は stdout にログを出力します）

## 基本的な使い方 {#basic-usage}

### 検出のワークフロー {#discovery-workflow}

1. **クラスターの検出**: 利用可能な Redshift リソースを見つける
2. **データベースの一覧表示**: 特定のクラスター内のデータベースを探索する
3. **データベース構造の閲覧**: スキーマ、テーブル、カラムを辿る
4. **データのクエリ**: 自然言語プロンプトで安全に SQL クエリを実行する

### 簡単な例 {#simple-examples}

- "Show me all available Redshift clusters"
- "List databases in cluster 'my-redshift-cluster'"
- "What tables are in the 'public' schema of database 'analytics'?"
- "Execute: SELECT COUNT(*) FROM users WHERE created_date > '2024-01-01'"

### 高度な例 {#advanced-examples}

#### 自然言語によるデータリクエスト {#natural-language-data-request}

```log
> Show me the last 3 sales from the analytics Redshift cluster.
I'll help you retrieve the last 3 sales from your analytics Redshift cluster. Let me start by discovering your available Redshift clusters and then
explore the database structure to find the sales data.

...skipping the auto-discovery logs...

Here are the last 3 sales from your analytics Redshift cluster:

Most Recent Sales (from tickit.sales table):

1. Sale ID 102373 - December 31, 2008 at 12:58:19
   • Price paid: $1,008.00
   • Seller ID: 26190, Buyer ID: 35491

2. Sale ID 75861 - December 31, 2008 at 12:50:02
   • Price paid: $372.00
   • Seller ID: 43402, Buyer ID: 39545

3. Sale ID 56302 - December 31, 2008 at 12:08:14
   • Price paid: $372.00
   • Seller ID: 5760, Buyer ID: 5797

The data shows ticket sales from the TICKIT sample dataset, which appears to be for event ticket transactions. All three sales occurred on December 31, 2008, with the most recent sale being for $1,008 for 4 tickets.

> Briefly describe your actions.
I performed the following actions to retrieve the last 3 sales from your analytics Redshift cluster:

1. Discovered clusters - Listed all available Redshift clusters and identified redshift-cluster-analytics as your analytics cluster
2. Explored databases - Found two databases: dev and sample_data_dev
3. Located schemas - Checked the sample_data_dev database and found the tickit schema containing sample data
4. Found sales table - Identified the sales table within the tickit schema
5. Analyzed table structure - Examined the columns in the sales table (salesid, pricepaid, qtysold, saletime, etc.)
6. Executed query - Ran a SQL query to get the 3 most recent sales ordered by saletime DESC

The process involved using the Redshift MCP tools to systematically navigate the cluster structure and retrieve the requested sales data from the TICKIT sample dataset.

> Show me the query text which you executed to get the sales.
Here's the exact SQL query I executed to get the last 3 sales:

sql
SELECT salesid, listid, sellerid, buyerid, eventid, qtysold, pricepaid, commission, saletime
FROM tickit.sales
ORDER BY saletime DESC
LIMIT 3;
```

#### クラスター間のデータ比較リクエスト {#cross-cluster-data-comparison-request}

```log
> How off is the analytics sales data from the ETL sales data based on the recent records in Redshift?
I'll help you analyze sales data from your Redshift ETL pipeline. To get started, I need to discover your Redshift environment and understand the data
structure.

...skipping auto-discovery logs...

# Sales Data Comparison: Analytics vs ETL

## Executive Summary
Sales data between Analytics cluster and ETL workgroup is perfectly synchronized with zero discrepancies found.

## Environment Overview
• **Analytics**: redshift-cluster-analytics (Provisioned, 2x dc2.large nodes)
• **ETL**: redshift-workgroup-etl (Serverless)
• **Database**: sample_data_dev.tickit.sales

## Data Comparison Results

### High-Level Metrics
| Metric          | Analytics Cluster | ETL Workgroup     | Status |
|-----------------|-------------------|-------------------|--------|
| Total Records   | 172,456           | 172,456           | Match  |
| Total Revenue   | $110,765,431      | $110,765,431      | Match  |
| Total Quantity  | 345,349           | 345,349           | Match  |
| Average Price   | $642.28           | $642.28           | Match  |
| Date Range      | 2008-01-01 to 2008-12-31 | 2008-01-01 to 2008-12-31 | Match |

### Recent Sales (Q4 2008)
| Month    | Analytics Revenue | ETL Revenue   | Analytics Txns | ETL Txns | Status |
|----------|-------------------|---------------|----------------|----------|--------|
| Dec 2008 | $4,521,806        | $4,521,806    | 7,059          | 7,059    | Match  |
| Nov 2008 | $9,044,905        | $9,044,905    | 14,261         | 14,261   | Match  |
| Oct 2008 | $10,726,368       | $10,726,368   | 16,741         | 16,741   | Match  |

## Key Findings
• Data Integrity: Perfect synchronization across all metrics
• Verification: Transaction-level details match exactly (verified 10 recent records)

> Briefly describe your actions.
I analyzed sales data from your Redshift environments by:

1. Discovered Infrastructure: Found 3 Redshift environments (analytics cluster, marketing cluster, ETL workgroup)
2. Explored Data Structure: Located sales data in sample_data_dev.tickit.sales table with 10 columns including salesid, pricepaid, qtysold, and saletime
3. Compared High-Level Metrics: Ran aggregate queries on both analytics cluster and ETL workgroup to compare total records (172,456), revenue ($110M), and date ranges
4. Analyzed Recent Data: Examined Q4 2008 monthly sales trends and verified the 10 most recent transactions from Dec 30-31, 2008
5. Performance Testing: Measured query execution times across different query types (6.7-19.5 seconds range)
6. Generated Report: Created a comprehensive comparison showing perfect data synchronization between environments with performance insights and recommendations

> Show me the text of the SQL queries you used.
Here are the SQL queries I executed during the analysis:

## 1. High-Level Metrics Query
sql
SELECT
    COUNT(*) as total_records,
    MIN(saletime) as earliest_sale,
    MAX(saletime) as latest_sale,
    SUM(pricepaid) as total_revenue,
    SUM(qtysold) as total_quantity,
    AVG(pricepaid) as avg_price
FROM tickit.sales;

## 2. Recent Monthly Sales Analysis
sql
SELECT
    DATE_TRUNC('month', saletime) as sale_month,
    COUNT(*) as transaction_count,
    SUM(pricepaid) as monthly_revenue,
    SUM(qtysold) as monthly_quantity,
    AVG(pricepaid) as avg_transaction_value
FROM tickit.sales
WHERE saletime >= '2008-10-01'
GROUP BY DATE_TRUNC('month', saletime)
ORDER BY sale_month DESC
LIMIT 10;

## 3. Recent Transaction Details
sql
SELECT
    salesid,
    listid,
    sellerid,
    buyerid,
    eventid,
    qtysold,
    pricepaid,
    commission,
    saletime
FROM tickit.sales
WHERE saletime >= '2008-12-30'
ORDER BY saletime DESC, salesid DESC
LIMIT 10;
```

## ツール {#tools}

### list_clusters {#list_clusters}

利用可能なすべての Amazon Redshift クラスターとサーバーレスワークグループを検出します。

```python
list_clusters() -> list[RedshiftCluster]
```

**戻り値**: 以下を含むクラスター情報のリスト:

- クラスター識別子とタイプ（プロビジョンド/サーバーレス）
- ステータスと接続の詳細
- 設定情報（ノードタイプ、暗号化など）
- タグとメタデータ

### list_databases {#list_databases}

指定した Redshift クラスター内のすべてのデータベースを一覧表示します。

```python
list_databases(cluster_identifier: str, database_name: str = "dev") -> list[RedshiftDatabase]
```

**パラメータ**:

- `cluster_identifier`: `list_clusters` から取得したクラスター識別子
- `database_name`: クエリのために接続するデータベース（デフォルト: "dev"）

**戻り値**: 以下を含むデータベース情報のリスト:

- データベース名と所有者
- データベースタイプ（local/shared）
- アクセス制御情報
- 分離レベル

### list_schemas {#list_schemas}

指定したデータベース内のすべてのスキーマを一覧表示します。

```python
list_schemas(cluster_identifier: str, schema_database_name: str) -> list[RedshiftSchema]
```

**パラメータ**:

- `cluster_identifier`: `list_clusters` から取得したクラスター識別子
- `schema_database_name`: スキーマを一覧表示するデータベース名

**戻り値**: 以下を含むスキーマ情報のリスト:

- スキーマ名と所有者
- スキーマタイプ（local/external/shared）
- アクセス権限
- 外部スキーマの詳細（該当する場合）

### list_tables {#list_tables}

指定したスキーマ内のすべてのテーブルを一覧表示します。

```python
list_tables(cluster_identifier: str, table_database_name: str, table_schema_name: str) -> list[RedshiftTable]
```

**パラメータ**:

- `cluster_identifier`: `list_clusters` から取得したクラスター識別子
- `table_database_name`: スキーマを含むデータベース名
- `table_schema_name`: テーブルを一覧表示するスキーマ名

**戻り値**: 以下を含むテーブル情報のリスト:

- テーブル名とタイプ（TABLE/VIEW/EXTERNAL TABLE）
- アクセス権限
- 備考とメタデータ

### list_columns {#list_columns}

指定したテーブル内のすべてのカラムを一覧表示します。

```python
list_columns(
    cluster_identifier: str,
    column_database_name: str,
    column_schema_name: str,
    column_table_name: str
) -> list[RedshiftColumn]
```

**パラメータ**:

- `cluster_identifier`: `list_clusters` から取得したクラスター識別子
- `column_database_name`: テーブルを含むデータベース名
- `column_schema_name`: テーブルを含むスキーマ名
- `column_table_name`: カラムを一覧表示するテーブル名

**戻り値**: 以下を含むカラム情報のリスト:

- カラム名とデータ型
- Nullable の状態とデフォルト値
- 数値の精度とスケール
- 文字長の制限
- 序数位置と備考

### execute_query {#execute_query}

安全性保護機能を備えた状態で、Redshift クラスターに対して SQL クエリを実行します。

```python
execute_query(cluster_identifier: str, database_name: str, sql: str) -> QueryResult
```

**パラメータ**:

- `cluster_identifier`: `list_clusters` から取得したクラスター識別子
- `database_name`: クエリを実行する対象のデータベース
- `sql`: 実行する SQL ステートメント（SELECT ステートメントを推奨）

**戻り値**: 以下を含むクエリ結果:

- カラム名とデータ型
- 適切な型変換が行われた結果行
- 行数と実行時間
- 参照用のクエリ ID

## 権限 {#permissions}

### AWS IAM の権限 {#aws-iam-permissions}

AWS 認証情報には、以下の IAM 権限が必要です。

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "redshift:DescribeClusters",
        "redshift-serverless:ListWorkgroups",
        "redshift-serverless:GetWorkgroup",
        "redshift-data:ExecuteStatement",
        "redshift-data:DescribeStatement",
        "redshift-data:GetStatementResult",
        "redshift-serverless:GetCredentials",
        "redshift:GetClusterCredentialsWithIAM",
        "redshift:GetClusterCredentials"
      ],
      "Resource": "*"
    }
  ]
}
```

### データベースの権限 {#database-permissions}

AWS IAM の権限に加えて、適切なデータベースレベルの権限が必要です。

- **読み取りアクセス**: クエリしたいテーブル/ビューに対する `SELECT` 権限
- **スキーマアクセス**: 探索したいスキーマに対する `USAGE` 権限
- **データベースアクセス**: アクセスしたいデータベースへの接続権限

最も強力な保護のためには、これらの権限を、広範な権限や書き込み可能なロールではなく、**最小権限の読み取り専用ロール**に付与してください。
