---
title: "AWS AppSync MCPサーバー"
---

AI アシスタントがバックエンド API を管理・操作できるようにする、AWS AppSync 向けの Model Context Protocol (MCP) サーバーです。

## 概要 {#overview}

AWS AppSync MCP サーバーは、GraphQL API、データソース、リゾルバー、その他の AppSync リソースを作成する機能を提供することで、API の管理を簡素化します。これにより、API 開発の効率化と、自然言語による対話を通じた AWS バックエンドサービスとのより容易な統合が実現します。

## 機能 {#features}

- **API 管理**: さまざまな認証タイプで AppSync API を作成・設定
- **GraphQL API の作成**: スキーマ定義と認証を備えた GraphQL API のセットアップ
- **API キー管理**: 認証用の API キーの生成と管理
- **API キャッシュ**: API パフォーマンス向上のためのキャッシュ設定
- **データソース管理**: API をさまざまな AWS バックエンドサービス（DynamoDB、Lambda、RDS など）に接続
- **関数管理**: 複雑なビジネスロジックのための AppSync 関数の作成と管理
- **チャネル名前空間管理**: チャネル名前空間によるリアルタイムサブスクリプションのセットアップ
- **ドメイン名管理**: API のカスタムドメイン名の設定
- **リゾルバー管理**: GraphQL フィールドをデータソースに接続するリゾルバーの作成
- **スキーマ管理**: GraphQL スキーマの定義と更新
- **読み取り専用モード**: すべての操作を読み取り専用に制限し、あらゆる変更を防止するオプションのセキュリティモードを有効化

## 前提条件 {#prerequisites}

1. [Astral](https://docs.astral.sh/uv/getting-started/installation/) または [GitHub README](https://github.com/astral-sh/uv#installation) から `uv` をインストールします
2. `uv python install 3.10` を使用して Python をインストールします
3. AWS AppSync へのアクセス権を持つ AWS 認証情報をセットアップします
   - AWS AppSync が有効化された AWS アカウントが必要です
   - `aws configure` または環境変数で AWS 認証情報を設定します
   - IAM ロール/ユーザーに AWS AppSync を使用する権限があることを確認します

## セットアップ {#setup}

### インストール {#installation}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.aws-appsync-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-appsync-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.aws-appsync-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLWFwcHN5bmMtbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiQVdTX1BST0ZJTEUiOiJ5b3VyLWF3cy1wcm9maWxlIiwiQVdTX1JFR0lPTiI6InVzLWVhc3QtMSIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifX0%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20AppSync%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-appsync-mcp-server%40latest%22%2C%20%22--allow-write%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22default%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

## 設定 {#configuration}

MCP クライアントの設定に MCP サーバーを追加します（例: Kiro の場合、`~/.kiro/settings/mcp.json` を編集します）

### AWS プロファイルの使用 {#using-aws-profiles}

標準的な AWS プロファイルベースの認証の場合:

```json
{
  "mcpServers": {
    "awslabs.aws-appsync-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-appsync-mcp-server@latest"],
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

### 一時的な認証情報の使用 {#using-temporary-credentials}

一時的な認証情報（AWS STS、IAM ロール、フェデレーションから取得したものなど）の場合:

```json
{
  "mcpServers": {
    "awslabs.aws-appsync-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-appsync-mcp-server@latest"],
      "env": {
        "AWS_ACCESS_KEY_ID": "your-temporary-access-key",
        "AWS_SECRET_ACCESS_KEY": "your-temporary-secret-key", // pragma: allowlist secret
        "AWS_SESSION_TOKEN": "your-session-token",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### `--allow-write` による書き込み操作の有効化 {#enabling-write-operations-using---allow-write}

ユーザーの AWS アカウント内にリソースを作成または変更するツールを有効にします。このフラグが有効になっていない場合、サーバーは読み取り操作のみを許可する読み取り専用モードで動作します。これにより、AppSync リソースへのあらゆる変更を防止し、セキュリティが強化されます。読み取り専用モードでは:

- 読み取り操作は通常どおり動作します
- 書き込み操作（`create_api`、`create_graphql_api`、`create_datasource` など）はブロックされ、権限エラーを返します

このモードは特に以下の用途に有用です:
- デモンストレーション環境
- セキュリティ上の配慮が必要なアプリケーション
- 一般公開されている AI アシスタントとの統合
- 意図しない変更から本番 API を保護する場合

例:
```json
{
  "mcpServers": {
    "awslabs.aws-appsync-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.aws-appsync-mcp-server@latest",
        "--allow-write"
      ],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

### Docker の設定 {#docker-configuration}

`docker build -t awslabs/aws-appsync-mcp-server .` でビルドした後:

```json
{
  "mcpServers": {
    "awslabs.aws-appsync-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "awslabs/aws-appsync-mcp-server:latest"
      ],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### 環境変数 {#environment-variables}

- `AWS_PROFILE`: 認証情報に使用する AWS CLI プロファイル
- `AWS_REGION`: 使用する AWS リージョン（デフォルト: us-east-1）
- `AWS_ACCESS_KEY_ID` および `AWS_SECRET_ACCESS_KEY`: 明示的な AWS 認証情報（AWS_PROFILE の代替）
- `AWS_SESSION_TOKEN`: 一時的な認証情報用のセッショントークン（AWS_ACCESS_KEY_ID および AWS_SECRET_ACCESS_KEY と併用）
- `FASTMCP_LOG_LEVEL`: ログレベル（ERROR、WARNING、INFO、DEBUG）

## ツール {#tools}

このサーバーは、MCP インターフェースを通じて以下のツールを公開します:

### create_api {#create_api}

指定された設定で新しい AppSync API を作成します。

```python
create_api(name: str) -> dict
```

### create_graphql_api {#create_graphql_api}

認証やその他の設定オプションを備えた新しい GraphQL API を作成します。

```python
create_graphql_api(
    name: str,
    authentication_type: str = "API_KEY"
) -> dict
```

### create_api_key {#create_api_key}

AppSync API での認証に使用する API キーを作成します。

```python
create_api_key(
    api_id: str,
    description: str = None,
    expires: int = None
) -> dict
```

### create_api_cache {#create_api_cache}

パフォーマンス向上のために AppSync API のキャッシュを作成・設定します。

```python
create_api_cache(
    api_id: str,
    ttl: int = 3600,
    api_caching_behavior: str = "FULL_REQUEST_CACHING",
    type: str = "SMALL"
) -> dict
```

### create_datasource {#create_datasource}

API を DynamoDB、Lambda、RDS などのバックエンドサービスに接続するデータソースを作成します。

```python
create_datasource(
    api_id: str,
    name: str,
    type: str,
    service_role_arn: str = None,
    dynamodb_config: dict = None,
    lambda_config: dict = None,
    elasticsearch_config: dict = None,
    relational_database_config: dict = None
) -> dict
```

### create_function {#create_function}

再利用可能なビジネスロジックのための AppSync 関数を作成します。

```python
create_function(
    api_id: str,
    name: str,
    data_source_name: str,
    function_version: str = "2018-05-29",
    request_mapping_template: str = None,
    response_mapping_template: str = None
) -> dict
```

### create_channel_namespace {#create_channel_namespace}

リアルタイムサブスクリプション用のチャネル名前空間を作成します。

```python
create_channel_namespace(
    api_id: str,
    name: str,
    publish_auth_modes: list = None,
    subscribe_auth_modes: list = None
) -> dict
```

### create_domain_name {#create_domain_name}

AppSync API のカスタムドメイン名を作成します。

```python
create_domain_name(
    domain_name: str,
    certificate_arn: str,
    description: str = None
) -> dict
```

### create_resolver {#create_resolver}

GraphQL フィールドをデータソースに接続するリゾルバーを作成します。

```python
create_resolver(
    api_id: str,
    type_name: str,
    field_name: str,
    data_source_name: str = None,
    request_mapping_template: str = None,
    response_mapping_template: str = None,
    kind: str = "UNIT"
) -> dict
```

### create_schema {#create_schema}

API の GraphQL スキーマを作成または更新します。

```python
create_schema(
    api_id: str,
    definition: str
) -> dict
```

## 使用例 {#usage-examples}

| プロンプト | 説明 |
|--------|-------------|
| `Create a GraphQL API named "blog-api" with API key authentication` | 指定した名前と認証タイプで新しい GraphQL API を作成します |
| `Add a GraphQL schema with a Post type with an id primary key, content and author fields` | カスタムの型とフィールドで API スキーマを作成または更新します |
| `Create a DynamoDB data source for my API connecting to the "posts" table` | API を DynamoDB テーブルに接続するデータソースをセットアップします |
| `Create a resolver for the "getPosts" query field` | GraphQL クエリの実行を処理するリゾルバーを作成します |
| `Set up API caching with 1 hour TTL for better performance` | API の応答時間を改善するためのキャッシュを設定します |
| `Create an API key that expires in 30 days` | 特定の有効期限を持つ API キーを生成します |
| `Create a Lambda data source for custom business logic` | API を AWS Lambda 関数に接続するデータソースをセットアップします |


## AWS AppSync リソース {#aws-appsync-resources}

このサーバーは、以下の目的で AWS AppSync サービスの API を使用します:
- GraphQL API の作成と管理
- データソースの設定（DynamoDB、Lambda、RDS など）
- リゾルバーの作成と管理
- スキーマの定義と更新
- API キーと認証の管理
- キャッシュの設定
- リアルタイムサブスクリプションのセットアップ

## セキュリティに関する考慮事項 {#security-considerations}

- 認証情報の管理には AWS プロファイルを使用してください
- IAM ポリシーを使用して、必要な AWS AppSync リソースのみにアクセスを制限してください
- セキュリティ強化のため、AWS STS から取得した一時的な認証情報（AWS_ACCESS_KEY_ID、AWS_SECRET_ACCESS_KEY、AWS_SESSION_TOKEN）を使用してください
- アプリケーションやサービスには、一時的な認証情報を用いる AWS IAM ロールを実装してください
- 認証情報を定期的にローテーションし、一時的な認証情報には実用上可能な限り短い有効期限を使用してください
- AWS AppSync のサービスクォータと制限に注意してください
- `--allow-write` フラグは慎重に使用し、書き込み操作が必要な場合にのみ使用してください

> #### ⚠️ 重要: エージェントに対する責任はお客様にあります
>
> MCP サーバーを使用するエージェントの動作と権限については、お客様が単独で責任を負います。
>
> - デフォルトでは、MCP サーバーは**読み取り専用モード**で動作します。
> - 書き込みアクセスを有効にするには、**必要な IAM 権限を明示的に MCP に設定**し、"--allow-write" フラグを使用して MCP サーバー経由での AWS AppSync に対する作成操作を有効にする必要があります。
> - 常に**最小権限の原則**に従い、エージェントの動作に必要な権限のみを付与してください。
> - 書き込み操作を有効にする場合は、**データのバックアップを取得すること**を推奨し、LLM が生成した指示を実行前に慎重に検証してください。このような操作は、アプリケーションの計画されたメンテナンスウィンドウ中に実施してください。
> - AWS AppSync MCP サーバーを自動化ワークフローに統合する際は、慎重に行うことを推奨します。

## ライセンス {#license}

このプロジェクトは Apache License, Version 2.0 の下でライセンスされています。詳細については [LICENSE](https://github.com/awslabs/mcp/blob/main/src/aws-appsync-mcp-server/LICENSE) ファイルをご覧ください。
