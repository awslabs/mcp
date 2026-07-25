---
title: "Amazon Data Processing MCP サーバー"
---

AWS DataProcessing MCP サーバーは、AWS Glue と Amazon EMR-EC2 にわたる包括的なデータ処理ツールとリアルタイムのパイプライン可視性を AI コードアシスタントに提供します。この統合により、大規模言語モデル (LLM) に不可欠なデータエンジニアリング機能とコンテキスト認識が備わり、AI コードアシスタントは、初期のデータ検出やカタログ化から、複雑な ETL パイプラインのオーケストレーション、ビッグデータ分析の最適化に至るまで、インテリジェントなガイダンスを通じてデータ処理ワークフローを効率化できるようになります。

DataProcessing MCP サーバーを AI コードアシスタントに統合することで、データエンジニアリングワークフローはあらゆるフェーズで変革されます。自動化されたスキーマ検出とデータ品質検証によりデータカタログ管理が簡素化されるほか、インテリジェントなコード生成とベストプラクティスの推奨により ETL ジョブの作成が効率化されます。また、EMR クラスターの自動プロビジョニングとワークロードの最適化により、ビッグデータ処理が加速されます。さらに、インテリジェントなデバッグツールと運用インサイトにより、トラブルシューティングが強化されます。これらすべてにより、AI コードアシスタントでの自然言語による対話を通じて、複雑なデータ操作が簡素化されます。


## 主な機能 {#key-features}

### AWS Glue との統合 {#aws-glue-integration}

* データカタログ管理: 自然言語のリクエストを通じてデータベース、テーブル、パーティションを探索、作成、管理できるようにし、リクエストを適切な AWS Glue Data Catalog 操作へ自動的に変換します。
* 接続タイプの検出: サポートされるプロパティ、認証方式、コンピューティング環境を含め、利用可能な AWS Glue の接続タイプを検出し、その詳細を確認できます。
* 接続メタデータとエンティティの探索: Glue 接続を通じて利用可能なエンティティ (SaaS オブジェクト、データベーステーブルなど) を探索し、エンティティのスキーマを確認し、接続されたデータソースからエンティティのデータレコードをプレビューできます。
* インタラクティブセッション: Spark および Ray ワークロード向けのインタラクティブな開発環境を提供し、マネージドな Jupyter ライクのセッションを通じてデータ探索、デバッグ、反復的な開発を可能にします。
* ワークフローとトリガー: ビジュアルワークフローと自動トリガーを通じて複雑な ETL アクティビティをオーケストレーションし、スケジュール実行、条件付き実行、イベントベースの実行パターンをサポートします。
* 共通機能 (Commons): 使用状況プロファイル、セキュリティ設定、カタログ暗号化設定、リソースポリシーの作成と管理を可能にし、ETL ジョブやカタログなどの各種 Glue リソースの設定と暗号化を管理する機能を提供します。
* ETL ジョブのオーケストレーション: ユーザーが定義したデータ変換要件に基づき、スクリプトの自動生成、ジョブのスケジューリング、ワークフローの調整を伴う Glue ETL ジョブの作成、監視、管理機能を提供します。
* クローラー管理: クローラーの自動設定、スケジューリング、さまざまなデータソースからのメタデータ抽出を通じて、インテリジェントなデータ検出を可能にします。

### Amazon EMR との統合 {#amazon-emr-integration}

* クラスター管理: 自然言語のリクエストを通じて、インスタンスタイプ、アプリケーション、設定を包括的に制御しながら、EMR クラスターの作成、設定、監視、終了を行えます。
* インスタンス管理: EMR クラスター内のインスタンスフリートおよびインスタンスグループの追加、変更、監視機能を提供し、オンデマンドインスタンスとスポットインスタンスの両方を自動スケーリング機能付きでサポートします。
* ステップ実行: EMR ステップを通じてデータ処理ワークフローをオーケストレーションし、実行中のクラスター上で Hadoop、Spark、その他のアプリケーションジョブの送信、監視、管理を可能にします。
* セキュリティ設定: 暗号化、認証、認可ポリシーを含む EMR のセキュリティ設定を管理し、安全なデータ処理環境を確保します。

### Amazon Athena との統合 {#amazon-athena-integration}

* クエリ実行: 自然言語のリクエストを通じて、クエリの開始、結果の取得、パフォーマンス統計の監視、実行中クエリのキャンセルなど、クエリのライフサイクル全体を包括的に制御しながら、SQL クエリの実行、監視、管理を行えます。
* 名前付きクエリ管理: 保存済み SQL クエリの作成、更新、取得、削除機能を提供し、適切な整理とチームコラボレーション機能を備えた再利用可能なクエリライブラリの構築を可能にします。
* データカタログ操作: 複数のカタログタイプ (LAMBDA、GLUE、HIVE、FEDERATED) をサポートする Athena データカタログを管理し、クロスプラットフォームのクエリ実行に向けたデータソース接続の作成、設定、維持を可能にします。
* データベースとテーブルの検出: 包括的なデータベースおよびテーブルメタデータの取得を通じてデータ探索を支援し、利用可能なデータソースの発見、スキーマ構造の理解、データカタログの効率的なナビゲーションを可能にします。
* ワークグループ管理: ワークグループ管理を通じてクエリ実行環境をオーケストレーションし、さまざまなユーザーグループや組織ポリシーに対応したコスト制御、アクセス管理、クエリ結果の設定を提供します。

## 前提条件 {#prerequisites}

* [Python 3.10+ のインストール](https://www.python.org/downloads/release/python-3100/)
* [`uv` パッケージマネージャーのインストール](https://docs.astral.sh/uv/getting-started/installation/)
* [AWS CLI のインストールと認証情報の設定](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html)

## セットアップ {#setup}

Glue、EMR-EC2、または Athena のリソース管理に使用する IAM ロールまたはユーザーに、以下の IAM ポリシーを追加してください。

### 読み取り専用操作ポリシー {#read-only-operations-policy}

読み取り操作には、以下の権限が必要です。

```
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "glue:GetDatabase*",
        "glue:GetTable*",
        "glue:GetPartition*",
        "glue:GetCrawler*",
        "glue:GetConnection*",
        "glue:DescribeConnectionType",
        "glue:ListConnectionTypes",
        "glue:ListEntities",
        "glue:DescribeEntity",
        "glue:GetEntityRecords",
        "glue:GetDatabases",
        "glue:GetTables",
        "glue:ListCrawlers",
        "glue:SearchTables",
        "glue:GetJobRun",
        "glue:GetJobRuns",
        "glue:GetJob",
        "glue:GetJobs",
        "glue:GetJobBookmark",
        "glue:GetUsageProfile",
        "glue:GetSecurityConfiguration",
        "glue:GetDataCatalogEncryptionSettings",
        "glue:GetResourcePolicy",
        "glue:GetSession",
        "glue:ListSessions",
        "glue:GetStatement",
        "glue:ListStatements",
        "glue:GetSession",
        "glue:ListSessions",
        "glue:GetStatement",
        "glue:ListStatements",
        "glue:GetWorkflow",
        "glue:ListWorkflows",
        "glue:GetTrigger",
        "glue:GetTriggers",
        "cloudwatch:GetMetricData",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams",
        "emr:DescribeCluster",
        "emr:ListClusters",
        "emr:DescribeStep",
        "emr:ListSteps",
        "emr:ListInstances",
        "emr:GetManagedScalingPolicy",
        "emr:DescribeStudio",
        "emr:ListStudios",
        "emr:DescribeNotebookExecution",
        "emr:ListNotebookExecutions",
        "athena:BatchGetQueryExecution",
        "athena:GetQueryExecution",
        "athena:GetQueryResults",
        "athena:GetQueryRuntimeStatistics",
        "athena:ListQueryExecutions",
        "athena:BatchGetNamedQuery",
        "athena:GetNamedQuery",
        "athena:ListNamedQueries",
        "athena:GetDataCatalog",
        "athena:ListDataCatalogs",
        "athena:GetDatabase",
        "athena:GetTableMetadata",
        "athena:ListDatabases",
        "athena:ListTableMetadata",
        "athena:GetWorkGroup",
        "athena:ListWorkGroups",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

### 書き込み操作ポリシー {#write-operations-policy}

書き込み操作には、以下の IAM ポリシーを推奨します。

* AWSGlueServiceRole: ジョブの実行、クローラーの実行、データカタログの変更を含む Glue サービスの操作を可能にします

**重要なセキュリティに関する注意**: これらの広範な権限とともに --allow-write および --allow-sensitive-data-access モードを有効にすると、MCP サーバーに大きな権限が付与されるため、十分注意してください。これらのフラグは、必要な場合にのみ、信頼できる環境でのみ有効にしてください。

**リソース管理の制限**: DataProcessing MCP サーバーは、もともと DataProcessing MCP サーバーを通じて作成されたリソースのみを更新または削除できます。他の手段で作成されたリソースは、DataProcessing MCP サーバーでは変更や削除ができません。


## インストール {#installation}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.aws-dataprocessing-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-dataprocessing-mcp-server%40latest%22%2C%22--allow-write%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22AWS_REGION%22%3A%22us-east-1%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en-US/install-mcp?name=awslabs.aws-dataprocessing-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLWRhdGFwcm9jZXNzaW5nLW1jcC1zZXJ2ZXJAbGF0ZXN0IC0tYWxsb3ctd3JpdGUiLCJlbnYiOnsiRkFTVE1DUF9MT0dfTEVWRUwiOiJFUlJPUiIsIkFXU19SRUdJT04iOiJ1cy1lYXN0LTEifSwiYXV0b0FwcHJvdmUiOltdLCJkaXNhYmxlZCI6ZmFsc2UsInRyYW5zcG9ydFR5cGUiOiJzdGRpbyJ9) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20Data%20Processing%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-dataprocessing-mcp-server%40latest%22%2C%22--allow-write%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22AWS_REGION%22%3A%22us-east-1%22%7D%2C%22autoApprove%22%3A%5B%5D%2C%22disabled%22%3Afalse%2C%22transportType%22%3A%22stdio%22%7D) |

## クイックスタート {#quickstart}

このクイックスタートガイドでは、Kiro や Cursor などのコーディングアシスタントで使用するために Amazon Data Processing MCP サーバーを設定する手順を説明します。以下の手順に従うことで、Glue、EMR、Athena のリソースを管理するための Data Processing MCP サーバーのツールを活用できる開発環境をセットアップできます。

**Kiro のセットアップ**

詳細については、[Kiro IDE のドキュメント](https://kiro.dev/docs/mcp/configuration/)または [Kiro CLI のドキュメント](https://kiro.dev/docs/cli/mcp/configuration/)を参照してください。

グローバル設定の場合は ~/.kiro/settings/mcp.json を編集します。プロジェクト固有の設定の場合は、プロジェクトディレクトリ内の .kiro/settings/mcp.json を編集します。

```json
{
  "mcpServers": {
    "aws.dp-mcp": {
      "command": "uvx",
      "args": [
        "awslabs.aws-dataprocessing-mcp-server@latest",
        "--allow-write"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

**Cursor のセットアップ**

1. Cursor を開きます。
2. 右上のギアアイコン (⚙️) をクリックして設定パネルを開き、**MCP**、**Add new global MCP server** の順にクリックします。
3. MCP サーバー定義を貼り付けます。たとえば、次の例では、サーバー引数に `--allow-write` フラグを追加して変更を伴う操作を有効にすることを含め、Data Processing MCP サーバーを設定する方法を示しています。

```
{
  "mcpServers": {
    "aws.dp-mcp": {
      "autoApprove": [],
      "disabled": false,
      "command": "uvx",
      "args": [
        "awslabs.aws-dataprocessing-mcp-server@latest",
        "--allow-write"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_REGION": "us-east-1"
      },
      "transportType": "stdio"
    }
  }
}
```

### Windows でのインストール {#windows-installation}

Windows ユーザーの場合、MCP サーバーの設定形式は少し異なります。

```json
{
  "mcpServers": {
    "awslabs.aws-dataprocessing-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.aws-dataprocessing-mcp-server@latest",
        "awslabs.aws-dataprocessing-mcp-server.exe"
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

数分後、MCP サーバー定義が有効であれば緑色のインジケーターが表示されます。

4. Cursor でチャットパネルを開き (例: `Ctrl/⌘ + L`)、Cursor のチャットウィンドウにプロンプトを入力します。たとえば、「Look at all the tables from my account federated across GDC」のように入力します。

なお、これは基本的なクイックスタートです。[コンテナで MCP サーバーを実行する](https://github.com/awslabs/mcp?tab=readme-ov-file#running-mcp-servers-in-containers)ことや、[AWS Documentation MCP Server](https://awslabs.github.io/mcp/servers/aws-documentation-mcp-server/) のような他の MCP サーバーを 1 つの MCP サーバー定義に組み合わせることなど、追加の機能を有効にできます。例については、AWS Labs のオープンソース MCP サーバーリポジトリの [Installation and Setup](https://github.com/awslabs/mcp?tab=readme-ov-file#installation-and-setup) ガイドを参照してください。MCP サーバーとともにアプリケーションコードを用いた実際の実装例については、Anthropic ドキュメントの [Server Developer](https://modelcontextprotocol.io/quickstart/server) ガイドを参照してください。

## 設定 {#configurations}

### 引数 {#arguments}

MCP サーバー定義の `args` フィールドには、サーバーの起動時に渡されるコマンドライン引数を指定します。これらの引数は、サーバーの実行方法と設定を制御します。例:

```
{
  "mcpServers": {
    "aws.dp-mcp": {
      "command": "uvx",
      "args": [
        "awslabs.aws-dataprocessing-mcp-server@latest",
        "--allow-write",
        "--allow-sensitive-data-access"
      ],
      "env": {
        "AWS_PROFILE": "your-profile",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

#### `awslabs.aws-dataprocessing-mcp-server@latest` (必須) {#awslabsaws-dataprocessing-mcp-serverlatest-required}

MCP クライアント設定における最新のパッケージ/バージョン指定子を指定します。

* MCP サーバーの起動とツールの登録を可能にします。

#### `--allow-write` (オプション) {#--allow-write-optional}

書き込みアクセスモードを有効にし、変更を伴う操作 (リソースの作成、更新、削除など) を許可します。

* デフォルト: false (サーバーはデフォルトで読み取り専用モードで動作します)
* 例: MCP サーバー定義の `args` リストに `--allow-write` を追加します。

**セキュリティ: 読み取り専用クエリの強制 (Athena)**

`--allow-write` が設定されていない場合、Athena クエリハンドラーは許可リストを使用して、どの SQL ステートメントが許可されるかを判断します。明示的に読み取り専用と認識される操作のみが許可されます。

* `SELECT`、`WITH` (CTE)、`SHOW`、`DESCRIBE`/`DESC`、`EXPLAIN`、`ANALYZE`

CTE (`WITH ... SELECT`) は、ステートメント全体が読み取りである場合にのみ読み取り専用と見なされます。書き込み操作が後続する CTE (例: `WITH cte AS (...) INSERT INTO ...`) は拒否されます。

その他のすべてのステートメント (`INSERT`、`UPDATE`、`DELETE`、`CREATE`、`DROP`、`UNLOAD` などを含む) はブロックされます。ワークロードで読み取り専用の許可リストを超えるステートメントが必要な場合は、`--allow-write` を有効にしてください。

#### `--allow-sensitive-data-access` (オプション) {#--allow-sensitive-data-access-optional}

機密性の高いユーザーデータを公開する操作へのアクセスを有効にします。無効の場合 (デフォルト)、以下の操作が制限されます。

**CRITICAL - データベース認証情報:**
* `get-connection` および `list-connections`: 接続プロパティ内の平文データベースパスワードの露出を防ぐため、`hide_password=True` を自動的に強制します

**HIGH - ユーザーデータ:**
* `get-query-results` (Athena): 実際のクエリ結果データの取得をブロックします
* `get-statement` (Glue Interactive Sessions): ステートメント実行出力の取得をブロックします
* `get-entity-records` (Data Catalog): 接続されたソースからのプレビューデータの取得をブロックします

**MEDIUM - ジョブ出力とログ:**
* `get-job-run` (Glue ETL および EMR Serverless): 機密性の高い引数やエラーメッセージを含む可能性のあるジョブ実行詳細へのアクセスをブロックします
* `describe-step` (EMR EC2): ステップ設定とエラー詳細へのアクセスをブロックします

* デフォルト: false (機密データへのアクセスはデフォルトで制限されます)
* セキュリティに関する注意: このフラグは、実際のデータへのアクセスが必要な場合に、信頼できる環境でのみ有効にしてください
* 例: MCP サーバー定義の `args` リストに `--allow-sensitive-data-access` を追加します。

### 環境変数 {#environment-variables}

MCP サーバー定義の `env` フィールドでは、DataProcessing MCP サーバーの動作を制御する環境変数を設定できます。例:

```
{
  "mcpServers": {
    "aws.dp-mcp": {
      "command": "uvx",
      "args": [
        "awslabs.aws-dataprocessing-mcp-server@latest",
        "--allow-write",
        "--allow-sensitive-data-access"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "my-profile",
        "AWS_REGION": "us-west-2",
        "CUSTOM_TAGS": "true"  // Skip adding and verifying MCP-managed tags
      }
    }
  }
}
```

#### `FASTMCP_LOG_LEVEL` (オプション) {#fastmcp_log_level-optional}

サーバーのログレベルの詳細度を設定します。

* 有効な値: "DEBUG"、"INFO"、"WARNING"、"ERROR"、"CRITICAL"
* デフォルト: "WARNING"
* 例: `"FASTMCP_LOG_LEVEL": "ERROR"`

#### `AWS_PROFILE` (オプション) {#aws_profile-optional}

認証に使用する AWS プロファイルを指定します。

* デフォルト: なし (設定されていない場合は、デフォルトの AWS 認証情報を使用します)。
* 例: `"AWS_PROFILE": "my-profile"`

#### `AWS_REGION` (オプション) {#aws_region-optional}

Glue、EMR クラスター、または Athena が管理されている AWS リージョンを指定します。このリージョンがすべての AWS サービス操作に使用されます。

* デフォルト: なし (設定されていない場合は、デフォルトの AWS リージョンを使用します)。
* 例: `"AWS_REGION": "us-west-2"`

#### `CUSTOM_TAGS` (オプション) {#custom_tags-optional}

MCP サーバーがリソースに MCP 管理タグを追加および検証するかどうかを制御します。

* 'true' に設定した場合、サーバーは次のように動作します。
  * リソース作成時にデフォルトの MCP タグの追加をスキップします
  * 操作時にリソースが MCP 管理タグを持つことの検証をスキップします
* デフォルト: なし (設定されていない場合は、MCP タグが追加および検証されます)
* 例: `"CUSTOM_TAGS": "true"`
* **重要**: このオプションを有効にすると、リソースは MCP 管理としてタグ付けされません。これは組み込みのリソース管理の安全機構をバイパスするため、所有者の同意と責任のもとで行ってください。

## ツール {#tools}

### Glue Data Catalog ハンドラーツール {#glue-data-catalog-handler-tools}

| ツール名 | 説明 | 主な操作 | 要件 |
|-----------|-------------|----------------|--------------|
| manage_aws_glue_databases | AWS Glue Data Catalog のデータベースを管理 | create-database, delete-database, get-database, list-databases, update-database | create/delete/update 操作には --allow-write フラグ、適切な AWS 権限 |
| manage_aws_glue_tables | AWS Glue Data Catalog のテーブルを管理 | create-table, delete-table, get-table, list-tables, update-table, search-tables | create/delete/update 操作には --allow-write フラグ、データベースが存在すること、適切な AWS 権限 |
| manage_aws_glue_connections | AWS Glue Data Catalog の接続を管理 | create-connection, delete-connection, get-connection, list-connections, update-connection, test-connection, batch-delete-connection | create/delete/update/test/batch-delete 操作には --allow-write フラグ、適切な AWS 権限 |
| manage_aws_glue_partitions | AWS Glue Data Catalog のパーティションを管理 | create-partition, delete-partition, get-partition, list-partitions, update-partition | create/delete/update 操作には --allow-write フラグ、データベースとテーブルが存在すること、適切な AWS 権限 |
| manage_aws_glue_catalog | AWS Glue Data Catalog を管理 | create-catalog, delete-catalog, get-catalog, list-catalogs, import-catalog-to-glue | create/delete/import 操作には --allow-write フラグ、適切な AWS 権限 |
| manage_aws_glue_connection_types | AWS Glue の接続タイプを検出し詳細を取得 | describe-connection-type, list-connection-types | 適切な AWS 権限 (読み取り専用操作) |
| manage_aws_glue_connection_metadata | Glue 接続の接続メタデータへのアクセスとエンティティデータのプレビュー | list-entities, describe-entity, get-entity-records | get-entity-records には --allow-sensitive-data-access フラグ、認証情報を持つ有効な接続、適切な AWS 権限 |

### Glue Interactive Sessions ハンドラーツール {#glue-interactive-sessions-handler-tools}

| ツール名 | 説明 | 主な操作 | 要件 |
|-----------|-------------|----------------|--------------|
| manage_aws_glue_sessions | Spark および Ray ワークロード向けの AWS Glue Interactive Sessions を管理 | create-session, delete-session, get-session, list-sessions, stop-session | create/delete/stop 操作には --allow-write フラグ、適切な AWS 権限 |
| manage_aws_glue_statements | Glue Interactive Sessions 内でコードステートメントを実行および管理 | run-statement, cancel-statement, get-statement, list-statements | run/cancel 操作には --allow-write フラグ、アクティブなセッションが必要 |

### Glue ワークフローとトリガーのハンドラーツール {#glue-workflows-and-triggers-handler-tools}

| ツール名 | 説明 | 主な操作 | 要件 |
|-----------|-------------|----------------|--------------|
| manage_aws_glue_workflows | ビジュアルワークフローを通じて複雑な ETL アクティビティをオーケストレーション | create-workflow, delete-workflow, get-workflow, list-workflows, start-workflow-run | create/delete/start 操作には --allow-write フラグ、適切な AWS 権限 |
| manage_aws_glue_triggers | スケジュールまたはイベントベースのトリガーでワークフローとジョブの実行を自動化 | create-trigger, delete-trigger, get-trigger, get-triggers, start-trigger, stop-trigger | create/delete/start/stop 操作には --allow-write フラグ、適切な AWS 権限 |


### EMR クラスターハンドラーツール {#emr-cluster-handler-tools}

| ツール名 | 説明 | 主な操作 | 要件 |
|-----------|-------------|----------------|--------------|
| manage_aws_emr_clusters | クラスターのライフサイクルを包括的に制御して Amazon EMR クラスターを管理 | create-cluster, describe-cluster, modify-cluster, modify-cluster-attributes, terminate-clusters, list-clusters, create-security-configuration, delete-security-configuration, describe-security-configuration, list-security-configurations | create/modify/terminate 操作には --allow-write フラグ、適切な AWS 権限 |

### EMR インスタンスハンドラーツール {#emr-instance-handler-tools}

| ツール名 | 説明 | 主な操作 | 要件 |
|-----------|-------------|----------------|--------------|
| manage_aws_emr_ec2_instances | 読み取りおよび書き込みの両方の操作で Amazon EMR EC2 インスタンスを管理 | add-instance-fleet, add-instance-groups, modify-instance-fleet, modify-instance-groups, list-instance-fleets, list-instances, list-supported-instance-types | add/modify 操作には --allow-write フラグ、適切な AWS 権限 |

### EMR ステップハンドラーツール {#emr-steps-handler-tools}

| ツール名 | 説明 | 主な操作 | 要件 |
|-----------|-------------|----------------|--------------|
| manage_aws_emr_ec2_steps | EMR クラスター上でデータを処理するための Amazon EMR ステップを管理 | add-steps, cancel-steps, describe-step, list-steps | add/cancel 操作には --allow-write フラグ、適切な AWS 権限 |

### EMR Serverless ハンドラーツール {#emr-serverless-handler-tools}

| ツール名 | 説明 | 主な操作 | 要件 |
|-----------|-------------|----------------|--------------|
| manage_aws_emr_serverless_applications | ライフサイクルを包括的に制御して Amazon EMR Serverless アプリケーションを管理 | create-application, get-application, update-application, delete-application, list-applications, start-application, stop-application | create/update/delete/start/stop 操作には --allow-write フラグ、適切な AWS 権限 |
| manage_aws_emr_serverless_job_runs | データ処理ワークロードを実行するための Amazon EMR Serverless ジョブ実行を管理 | start-job-run, get-job-run, cancel-job-run, list-job-runs, get-dashboard-for-job-run | start/cancel 操作には --allow-write フラグ、アプリケーションが存在すること、適切な AWS 権限 |

### Athena クエリハンドラーツール {#athena-query-handler-tools}

| ツール名 | 説明 | 主な操作 | 要件 |
|-----------|-------------|----------------|--------------|
| manage_aws_athena_query_executions | AWS Athena の SQL クエリを実行および管理 | batch-get-query-execution, get-query-execution, get-query-results, get-query-runtime-statistics, list-query-executions, start-query-execution, stop-query-execution | start/stop 操作には --allow-write フラグ、適切な AWS 権限 |
| manage_aws_athena_named_queries | AWS Athena の保存済み SQL クエリを管理 | batch-get-named-query, create-named-query, delete-named-query, get-named-query, list-named-queries, update-named-query | create/delete/update 操作には --allow-write フラグ、適切な AWS 権限 |


### Athena データカタログハンドラーツール {#athena-data-catalog-handler-tools}

| ツール名 | 説明 | 主な操作 | 要件 |
|-----------|-------------|----------------|--------------|
| manage_aws_athena_data_catalogs | AWS Athena のデータカタログを管理 | create-data-catalog, delete-data-catalog, get-data-catalog, list-data-catalogs, update-data-catalog | create/delete/update 操作には --allow-write フラグ、適切な AWS 権限 |
| manage_aws_athena_databases_and_tables | AWS Athena のデータベースとテーブルを管理 | get-database, get-table-metadata, list-databases, list-table-metadata | Athena データベース操作に対する適切な AWS 権限 |

### Athena ワークグループハンドラーツール {#athena-workgroup-handler-tools}

| ツール名 | 説明 | 主な操作 | 要件 |
|-----------|-------------|----------------|--------------|
| manage_aws_athena_workgroups | AWS Athena のワークグループを管理 | create-work-group, delete-work-group, get-work-group, list-work-groups, update-work-group | create/delete/update 操作には --allow-write フラグ、適切な AWS 権限 |

### Glue 共通機能ハンドラーツール {#glue-commons-handler-tools}

| ツール名 | 説明 | 主な操作 | 要件 |
|-----------|-----------------------------------------------------------------------------|----------------|-------------------------------------------------------------------------------------|
| manage_aws_glue_usage_profiles | リソース割り当てとコスト管理のための AWS Glue 使用状況プロファイルを管理 | create-profile, delete-profile, get-profile, update-profile | create/delete/update 操作には --allow-write フラグ、適切な AWS 権限 |
| manage_aws_glue_security_configurations | データ暗号化のための AWS Glue セキュリティ設定を管理 | create-security-configuration, delete-security-configuration, get-security-configuration | create/delete 操作には --allow-write フラグ、適切な AWS 権限 |
| manage_aws_glue_encryption | AWS Glue カタログの暗号化設定を管理 | get-catalog-encryption-settings, put-catalog-encryption-settings | put 操作には --allow-write フラグ、適切な AWS 権限 |
| manage_aws_glue_resource_policies | AWS Glue のカタログ、データベース、テーブルに対するリソースポリシーを管理 | get-resource-policy, put-resource-policy, delete-resource-policy | put/delete 操作には --allow-write フラグ、適切な AWS 権限 |

### Glue ETL ハンドラーツール {#glue-etl-handler-tools}

| ツール名 | 説明 | 主な操作 | 要件 |
|-----------|-------------|----------------|--------------|
| manage_aws_glue_jobs | AWS Glue の ETL ジョブとジョブ実行を管理 | create-job, delete-job, get-job, get-jobs, update-job, start-job-run, stop-job-run, get-job-run, get-job-runs, batch-stop-job-run, get-job-bookmark, reset-job-bookmark | create/delete/update/start/stop 操作には --allow-write フラグ、適切な AWS 権限 |

### Glue クローラーハンドラーツール {#glue-crawler-handler-tools}

| ツール名 | 説明 | 主な操作 | 要件 |
|-----------|-------------|----------------|--------------|
| manage_aws_glue_crawlers | データソースを検出しカタログ化するための AWS Glue クローラーを管理 | create-crawler, delete-crawler, get-crawler, get-crawlers, start-crawler, stop-crawler, batch-get-crawlers, list-crawlers, update-crawler | create/delete/start/stop/update 操作には --allow-write フラグ、適切な AWS 権限 |
| manage_aws_glue_classifiers | データ形式とスキーマを判別するための AWS Glue 分類子を管理 | create-classifier, delete-classifier, get-classifier, get-classifiers, update-classifier | create/delete/update 操作には --allow-write フラグ、適切な AWS 権限 |
| manage_aws_glue_crawler_management | AWS Glue クローラーのスケジュールを管理しパフォーマンスメトリクスを監視 | get-crawler-metrics, start-crawler-schedule, stop-crawler-schedule, update-crawler-schedule | スケジュール操作には --allow-write フラグ、適切な AWS 権限 |


### 共通リソースハンドラーツール {#common-resource-handler-tools}

#### IAM 管理ツール {#iam-management-tools}

| ツール名 | 説明 | 主な操作 | 要件 |
|-----------|-------------|----------------|--------------|
| add_inline_policy | IAM ロールに新しいインラインポリシーを追加 | データ処理サービス向けのカスタム権限を持つインラインポリシーの作成 | --allow-write フラグ、ロールが存在すること、ポリシー名が一意であること |
| get_policies_for_role | IAM ロールにアタッチされたすべてのポリシーを取得 | マネージドポリシーとインラインポリシー、AssumeRole ポリシードキュメント、ロールメタデータの取得 | ロールが存在すること、有効な AWS 認証情報 |
| create_data_processing_role | データ処理サービス向けの新しい IAM ロールを作成 | 信頼関係を持つ Glue/EMR/Athena 向けロールの作成、マネージドポリシーのアタッチ、インラインポリシーの追加 | --allow-write フラグ、一意のロール名、有効なサービスタイプ (glue/emr/athena) |
| get_roles_for_service | 特定の AWS サービスが引き受け可能なすべての IAM ロールを取得 | Glue/EMR/Athena サービスとの信頼関係を持つロールの一覧表示、サービスプリンシパルによるフィルタリング | 有効な AWS 認証情報、サービスタイプパラメータ |

#### S3 管理ツール {#s3-management-tools}

| ツール名 | 説明 | 主な操作 | 要件 |
|-----------|-------------|----------------|--------------|
| list_s3_buckets | 名前に 'glue' を含む S3 バケットと使用状況の統計を一覧表示 | リージョン別のバケット一覧表示、オブジェクト数、最終更新日、アイドル時間分析の表示 | 有効な AWS 認証情報、S3:ListAllMyBuckets 権限 |
| upload_to_s3 | Python コードの内容を S3 バケットに直接アップロード | Glue ジョブ、EMR ステップ、その他のデータ処理コード向けスクリプトのアップロード | --allow-write フラグ、バケットが存在すること、S3 書き込み権限 |
| analyze_s3_usage_for_data_processing | データ処理サービスにおける S3 バケットの使用パターンを分析 | Glue/EMR/Athena が使用するバケットの特定、アイドル状態のバケットの検出、使用に関する推奨事項 | 有効な AWS 認証情報、Glue/EMR/Athena サービス API に対する権限 |

## バージョン {#version}

現在の MCP サーバーバージョン: 0.1.28
