---
title: AWS Bedrock Custom Model Import MCP サーバー
---

## 概要 {#overview}

Bedrock Custom Model Import Model Context Protocol (MCP) サーバーは、Amazon Bedrock へのカスタムモデルのインポートプロセスを効率化します。モデルインポートジョブとインポート済みモデルを管理するための包括的なツールセットを提供し、開発者がカスタムモデルを Amazon Bedrock の機能と効率的に統合できるようにします。

Bedrock Custom Model Import MCP サーバーの主なメリットは次のとおりです。

- **AI を活用したモデル管理**: AI コーディングアシスタントに豊富なコンテキスト情報を提供し、モデルインポート操作が AWS のベストプラクティスに沿ったものになるようにします。
- **包括的なツール群**: モデルインポートジョブとインポート済みモデルの作成、監視、管理のためのツールを提供します。
- **運用のベストプラクティス**: モデルインポートの操作と管理において、AWS のアーキテクチャ原則との整合性を確保します。

## 機能 {#features}

Bedrock Custom Model Import MCP サーバーが提供するツールセットは、次の 2 つのカテゴリに分類できます。

1. モデルインポートの処理
   - 新しいモデルインポートジョブの作成
   - 既存のモデルインポートジョブの一覧表示
   - 特定のモデルインポートジョブの詳細取得
2. インポート済みモデルの管理
   - インポート済みモデルの一覧表示
   - 特定のインポート済みモデルの詳細取得
   - インポート済みモデルの削除

## 前提条件 {#prerequisites}

- [認証情報が設定された](https://docs.aws.amazon.com/cli/v1/userguide/cli-configure-files.html) AWS アカウントを持っていること
- [Astral](https://docs.astral.sh/uv/getting-started/installation/) または [GitHub README](https://github.com/astral-sh/uv#installation) から uv をインストールすること
- uv python install 3.12 を使用して Python 3.12 以降(またはより新しいバージョン)をインストールすること
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) をインストールすること
- 適切な権限で Amazon Bedrock にアクセスできること

## インストール {#installation}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.aws-bedrock-custom-model-import-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-bedrock-custom-model-import-mcp-server%40latest%22%2C%22--allow-write%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.aws-bedrock-custom-model-import-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLWJlZHJvY2stY3VzdG9tLW1vZGVsLWltcG9ydC1tY3Atc2VydmVyQGxhdGVzdCAtLWFsbG93LXdyaXRlIiwiZW52Ijp7IkFXU19QUk9GSUxFIjoieW91ci1hd3MtcHJvZmlsZSIsIkFXU19SRUdJT04iOiJ1cy1lYXN0LTEifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Bedrock%20Custom%20Model%20Import%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-bedrock-custom-model-import-mcp-server%40latest%22%2C%22--allow-write%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

Bedrock Custom Model Import MCP サーバーは GitHub からダウンロードできます。Kiro、Cursor、Cline など、MCP をサポートするお好みのコードアシスタントで使い始めることができます。

以下のコードを MCP クライアント設定に追加してください。サーバーはデフォルトで AWS のデフォルトプロファイルを使用します。別のプロファイルを使用する場合は、AWS_PROFILE に値を指定してください。同様に、AWS リージョンとログレベルの値も必要に応じて調整してください。

```json
{
  "mcpServers": {
    "awslabs.aws-bedrock-custom-model-import-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.aws-bedrock-custom-model-import-mcp-server@latest",
        "--allow-write"
      ],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "BEDROCK_MODEL_IMPORT_S3_BUCKET": "your-model-bucket",
        "BEDROCK_MODEL_IMPORT_ROLE_ARN": "your-role-arn"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### 一時認証情報の使用 {#using-temporary-credentials}

```json
{
  "mcpServers": {
    "awslabs.aws-bedrock-custom-model-import-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-bedrock-custom-model-import-mcp-server@latest"],
      "env": {
        "AWS_ACCESS_KEY_ID": "your-temporary-access-key", // pragma: allowlist secret
        "AWS_SECRET_ACCESS_KEY": "your-temporary-secret-key", // pragma: allowlist secret
        "AWS_SESSION_TOKEN": "your-session-token", // pragma: allowlist secret
        "AWS_REGION": "us-east-1",
        "BEDROCK_MODEL_IMPORT_S3_BUCKET": "your-model-bucket",
        "BEDROCK_MODEL_IMPORT_ROLE_ARN": "your-role-arn"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## 環境変数 {#environment-variables}

サーバーは MCP 設定内の環境変数を通じて設定できます。

### AWS 認証 {#aws-authentication}

- `AWS_PROFILE`: 認証情報に使用する AWS CLI プロファイル
- `AWS_REGION`: 使用する AWS リージョン(デフォルト: us-east-1)
- `AWS_ACCESS_KEY_ID` および `AWS_SECRET_ACCESS_KEY`: 明示的な AWS 認証情報(AWS_PROFILE の代替)
- `AWS_SESSION_TOKEN`: 一時認証情報用のセッショントークン(`AWS_ACCESS_KEY_ID` および `AWS_SECRET_ACCESS_KEY` と併用)

**注意**: [Amazon Bedrock API キー](https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys-use.html)で認証する場合は、モデルのインポートに必要な `iam:PassRole` 権限が IAM ポリシーに含まれていることを確認してください。

### Bedrock Model Import の設定 {#bedrock-model-import-configuration}

- `BEDROCK_MODEL_IMPORT_S3_BUCKET`(必須): モデルファイルを含む S3 バケット。指定した場合、サーバーはモデル名に基づいてこのバケット内のモデルファイルを自動的に検索します。
- `BEDROCK_MODEL_IMPORT_ROLE_ARN`(オプション): モデルインポートジョブに使用する IAM 実行ロールの ARN。指定しない場合、サーバーは認証情報からロールを引き受けます。

### その他の設定 {#other-configuration}

- `FASTMCP_LOG_LEVEL`: ログレベル(ERROR、WARNING、INFO、DEBUG)

## ローカル開発 {#local-development}

この MCP をローカルで変更して実行するには、次の手順に従います。

1. このリポジトリをクローンします。

   ```bash
   git clone https://github.com/awslabs/mcp.git
   cd mcp/src/aws-bedrock-custom-model-import-mcp-server
   ```

2. 依存関係をインストールします。

   ```bash
   pip install -e .
   ```

3. AWS 認証情報を設定します。

   - `~/.aws/credentials` に AWS 認証情報が設定されていることを確認するか、適切な環境変数を設定してください。
   - AWS_PROFILE および AWS_REGION 環境変数を設定することもできます。

4. サーバーを実行します。

   ```bash
   python -m awslabs.aws_bedrock_custom_model_import_mcp_server.server
   ```

5. この MCP サーバーを AI クライアントで使用するには、以下を MCP 設定に追加します。

```json
{
  "mcpServers": {
    "awslabs.aws-bedrock-custom-model-import-mcp-server": {
      "command": "mcp/src/aws-bedrock-custom-model-import-mcp-server/bin/awslabs.aws-bedrock-custom-model-import-mcp-server/",
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "BEDROCK_MODEL_IMPORT_S3_BUCKET": "your-model-bucket",
        "BEDROCK_MODEL_IMPORT_ROLE_ARN": "your-role-arn"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## 利用可能なツール {#available-tools}

このサーバーは、モデルインポート機能をツールとして公開しています。

### create_model_import_job {#create_model_import_job}

Amazon Bedrock に新しいモデルインポートジョブを作成します。

**パラメータ**:

- `jobName`(必須)

  - モデルインポートジョブの名前
  - 最大長: 50 文字
  - アカウント内で一意である必要があります

- `importedModelName`(必須)

  - インポートするモデルの名前
  - 最大長: 50 文字
  - Bedrock 内でモデルを識別するために使用されます

- `roleArn`(オプション)

  - インポートジョブ用の IAM ロールの ARN
  - 指定しない場合、環境変数の BEDROCK_MODEL_IMPORT_ROLE_ARN を使用します
  - ロールにはモデルインポートに必要な権限が必要です

- `modelDataSource`(条件付き)

  - BEDROCK_MODEL_IMPORT_S3_BUCKET が設定されていない場合に必須
  - S3 データソースの設定を含みます:
    - s3Uri: モデルデータを指す S3 URI

- `jobTags`(オプション)

  - インポートジョブに適用するタグのリスト
  - 各タグは次の項目を持ちます:
    - key: タグキー(必須)
    - value: タグ値(必須)

- `importedModelTags`(オプション)

  - インポート済みモデルに適用するタグのリスト
  - jobTags と同じ構造

- `clientRequestToken`(オプション)

  - リクエストの冪等性トークン
  - ジョブの重複作成を防ぐのに役立ちます

- `vpcConfig`(オプション)

  - ネットワーク分離のための VPC 設定
  - 次の項目を含みます:
    - subnetIds: サブネット ID のリスト
    - securityGroupIds: セキュリティグループ ID のリスト

- `importedModelKmsKeyId`(オプション)
  - インポート済みモデルを暗号化するための KMS キー ID
  - Bedrock に必要な権限が必要です

### list_model_import_jobs {#list_model_import_jobs}

Amazon Bedrock 内の既存のモデルインポートジョブを一覧表示します。

**パラメータ**:

- `creationTimeAfter`(オプション)

  - この日時より後に作成されたジョブでフィルタリング
  - 形式: ISO 8601 日時文字列

- `creationTimeBefore`(オプション)

  - この日時より前に作成されたジョブでフィルタリング
  - 形式: ISO 8601 日時文字列

- `statusEquals`(オプション)

  - ステータスでジョブをフィルタリング
  - 有効な値: InProgress、Completed、Failed

- `nameContains`(オプション)

  - 名前の部分文字列でジョブをフィルタリング
  - 大文字と小文字を区別する検索

- `sortBy`(オプション)

  - 結果の並べ替えに使用するフィールド
  - 例: CreationTime

- `sortOrder`(オプション)
  - 並べ替え結果の順序
  - 有効な値: Ascending、Descending

### list_imported_models {#list_imported_models}

Amazon Bedrock に正常にインポートされたモデルを一覧表示します。

**パラメータ**:

- `creationTimeBefore`(オプション)

  - この日時より前に作成されたモデルでフィルタリング
  - 形式: ISO 8601 日時文字列

- `creationTimeAfter`(オプション)

  - この日時より後に作成されたモデルでフィルタリング
  - 形式: ISO 8601 日時文字列

- `nameContains`(オプション)

  - 名前の部分文字列でモデルをフィルタリング
  - 大文字と小文字を区別する検索

- `sortBy`(オプション)

  - 結果の並べ替えに使用するフィールド
  - 例: CreationTime

- `sortOrder`(オプション)
  - 並べ替え結果の順序
  - 有効な値: Ascending、Descending

### get_model_import_job {#get_model_import_job}

特定のモデルインポートジョブに関する詳細情報を取得します。

**パラメータ**:

- `job_identifier`(必須)
  - 詳細を取得するジョブの名前または ARN
  - 既存のジョブ名である必要があります

### get_imported_model {#get_imported_model}

特定のインポート済みモデルに関する詳細情報を取得します。

**パラメータ**:

- `model_identifier`(必須)
  - 詳細を取得するモデルの名前または ARN
  - 既存のインポート済みモデル名である必要があります

### delete_imported_model {#delete_imported_model}

Amazon Bedrock からインポート済みモデルを削除します。

**パラメータ**:

- `model_identifier`(必須)
  - 削除するモデルの識別子
  - 既存のインポート済みモデルの識別子である必要があります

## 使用例 {#example-usage}

### モデルインポートジョブの作成 {#creating-a-model-import-job}

ユーザープロンプトの例:

```
I want to import a Llama 3.3 model into Bedrock. Can you help me create a new import job?
```

このプロンプトにより、AI アシスタントは適切な設定で `create_model_import_job` ツールを使用し、設定された S3 バケットからモデルアーティファクトを自動的に検索します。

### インポートジョブの監視 {#monitoring-import-jobs}

ユーザープロンプトの例:

```
Show me all the model import jobs I have running in Bedrock?
```

このプロンプトにより、AI アシスタントは `list_model_import_jobs` ツールを使用して、すべてのジョブとその現在のステータスを表示します。

## セキュリティ機能 {#security-features}

1. **AWS 認証**: 環境の AWS 認証情報を使用して安全に認証します
2. **TLS 検証**: すべての AWS API 呼び出しで TLS 検証を強制します
3. **リソースタグ付け**: トレーサビリティのために、作成されたすべてのリソースにタグを付けます
4. **最小権限**: モデルインポート操作に適切な権限を持つ IAM ロールを使用します

## セキュリティに関する考慮事項 {#security-considerations}

### 本番環境のユースケース {#production-use-cases}

Bedrock Custom Model Import MCP サーバーは、適切なセキュリティ管理を実施したうえで本番環境で使用できます。本番環境のユースケースでは、次の点を考慮してください。

- **デフォルトで読み取り専用モード**: サーバーはデフォルトで読み取り専用モードで動作し、本番環境ではこの方が安全です。書き込みアクセスは必要な場合にのみ明示的に有効にしてください。
- **auto-approve の無効化**: AI アシスタントがツールを実行するたびにユーザーの承認を必須にしてください

### ロールスコープの推奨事項 {#role-scoping-recommendations}

セキュリティのベストプラクティスに従うには、次のことを行ってください。

1. 最小権限の原則に基づいて**専用の IAM ロールを作成**する
2. 読み取り専用操作と書き込み操作に**別々のロールを使用**する
3. サーバーが作成したリソースにアクションを限定するために**リソースタグ付けを実装**する
4. サーバーによるすべての API 呼び出しを監査するために **AWS CloudTrail を有効化**する
5. サーバーの IAM ロールに付与された権限を**定期的にレビュー**する
6. 削除可能な未使用の権限を特定するために **IAM Access Analyzer を使用**する

### 機密情報の取り扱い {#sensitive-information-handling}

**重要**: 許可された入力手段を介してシークレットや機密情報を渡さないでください。

- モデルインポートの設定にシークレットや認証情報を含めないでください
- モデルへのプロンプトに機密情報を直接渡さないでください

## リンク {#links}

- [ホームページ](https://awslabs.github.io/mcp/)
- [ドキュメント](https://awslabs.github.io/mcp/servers/aws-bedrock-custom-model-import-mcp-server/)
- [ソースコード](https://github.com/awslabs/mcp.git)
- [バグトラッカー](https://github.com/awslabs/mcp/issues)
- [変更履歴](https://github.com/awslabs/mcp/blob/main/src/aws-bedrock-custom-model-import-mcp-server/CHANGELOG.md)

## ライセンス {#license}

Apache-2.0
