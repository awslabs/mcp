---
title: "HealthLake MCPサーバー"
---

AWS HealthLake の FHIR 操作向けの Model Context Protocol (MCP) サーバーです。データストアの自動検出により、包括的な FHIR リソース管理を実現する 11 個のツールを提供します。

## 目次 {#table-of-contents}

- [機能](#features)
- [前提条件](#prerequisites)
- [クイックスタート](#quick-start)
  - [オプション 1: uvx（推奨）](#option-1-uvx-recommended)
  - [オプション 2: uv install](#option-2-uv-install)
  - [オプション 3: Docker](#option-3-docker)
- [MCP クライアントの設定](#mcp-client-configuration)
  - [Kiro](#kiro)
  - [Docker の設定](#docker-configuration)
  - [その他の MCP クライアント](#other-mcp-clients)
- [読み取り専用モード](#read-only-mode)
- [利用可能なツール](#available-tools)
  - [データストア管理](#datastore-management)
  - [FHIR リソース操作（CRUD）](#fhir-resource-operations-crud)
  - [高度な検索](#advanced-search)
  - [ジョブ管理](#job-management)
  - [MCP リソース](#mcp-resources)
- [使用例](#usage-examples)
  - [基本的なリソース操作](#basic-resource-operations)
  - [高度な検索](#advanced-search-1)
  - [Patient Everything](#patient-everything)
- [認証](#authentication)
  - [必要な権限](#required-permissions)
- [エラーハンドリング](#error-handling)
- [トラブルシューティング](#troubleshooting)
  - [よくある問題](#common-issues)
  - [デバッグモード](#debug-mode)
- [開発](#development)
  - [ローカル開発環境のセットアップ](#local-development-setup)
  - [サーバーのローカル実行](#running-the-server-locally)
  - [開発ワークフロー](#development-workflow)
  - [IDE のセットアップ](#ide-setup)
  - [テスト](#testing)
  - [プロジェクト構成](#project-structure)
- [コントリビューション](#contributing)
- [ライセンス](#license)
- [サポート](#support)

## 機能 {#features}

- **11 個の FHIR ツール**: 完全な CRUD 操作（読み取り専用 6 個、書き込み 5 個）、高度な検索、patient-everything、ジョブ管理
- **読み取り専用モード**: 読み取りアクセスを維持しつつ、すべての変更操作をブロックするセキュリティ重視のモード
- **MCP リソース**: データストアの自動検出 — データストア ID を手動で指定する必要はありません
- **高度な検索**: チェーンパラメータ、includes、revIncludes、修飾子、日付/数値のプレフィックスに対応し、ページネーションもサポート
- **AWS 統合**: 認証情報の自動処理とリージョンサポートを備えた SigV4 認証
- **包括的なテスト**: 235 個のテストと 96% のカバレッジで信頼性を確保
- **タスク自動化**: Poethepoet の統合による効率的な開発ワークフロー
- **エラーハンドリング**: 特定のエラータイプと役立つメッセージを含む構造化されたエラーレスポンス
- **Docker サポート**: 柔軟な認証オプションを備えたコンテナ化されたデプロイ

## 前提条件 {#prerequisites}

- **Python 3.10 以上**（MCP フレームワークで必須）
- **AWS 認証情報**の設定
- 適切な権限を持つ **AWS HealthLake へのアクセス**

[↑ 目次に戻る](#table-of-contents)

## クイックスタート {#quick-start}

お好みのインストール方法を選択してください。

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.healthlake-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.healthlake-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%2C%22AWS_PROFILE%22%3A%22your-profile%22%2C%22MCP_LOG_LEVEL%22%3A%22WARNING%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.healthlake-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuaGVhbHRobGFrZS1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJBV1NfUkVHSU9OIjoidXMtZWFzdC0xIiwiQVdTX1BST0ZJTEUiOiJ5b3VyLXByb2ZpbGUiLCJNQ1BfTE9HX0xFVkVMIjoiV0FSTklORyJ9fQ%3D%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20HealthLake%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.healthlake-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%2C%22AWS_PROFILE%22%3A%22your-profile%22%2C%22MCP_LOG_LEVEL%22%3A%22WARNING%22%7D%7D) |

### オプション 1: uvx（推奨） {#option-1-uvx-recommended}

```bash
# Install and run latest version automatically
uvx awslabs.healthlake-mcp-server@latest
```

### オプション 2: uv install {#option-2-uv-install}

```bash
uv tool install awslabs.healthlake-mcp-server
awslabs.healthlake-mcp-server
```

### オプション 3: Docker {#option-3-docker}

```bash
# Build and run with Docker
docker build -t healthlake-mcp-server .
docker run -e AWS_ACCESS_KEY_ID=xxx -e AWS_SECRET_ACCESS_KEY=yyy healthlake-mcp-server

# Or use pre-built image with environment variables
docker run -e AWS_ACCESS_KEY_ID=your_key -e AWS_SECRET_ACCESS_KEY=your_secret -e AWS_REGION=us-east-1 awslabs/healthlake-mcp-server

# With AWS profile (mount credentials)
docker run -v ~/.aws:/root/.aws -e AWS_PROFILE=your-profile awslabs/healthlake-mcp-server

# Read-only mode
docker run -e AWS_ACCESS_KEY_ID=your_key -e AWS_SECRET_ACCESS_KEY=your_secret -e AWS_REGION=us-east-1 awslabs/healthlake-mcp-server --readonly
```

[↑ 目次に戻る](#table-of-contents)

## MCP クライアントの設定 {#mcp-client-configuration}

### Kiro {#kiro}

詳細については、[Kiro IDE ドキュメント](https://kiro.dev/docs/mcp/configuration/) または [Kiro CLI ドキュメント](https://kiro.dev/docs/cli/mcp/configuration/) を参照してください。

グローバル設定の場合は `~/.kiro/settings/mcp.json` を編集します。プロジェクト固有の設定の場合は、プロジェクトディレクトリ内の `.kiro/settings/mcp.json` を編集します。

**設定:**
```json
{
  "mcpServers": {
    "healthlake": {
      "command": "uvx",
      "args": ["awslabs.healthlake-mcp-server@latest"],
      "env": {
        "AWS_REGION": "us-east-1",
        "AWS_PROFILE": "your-profile-name",
        "MCP_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

**読み取り専用の設定:**
```json
{
  "mcpServers": {
    "healthlake-readonly": {
      "command": "uvx",
      "args": ["awslabs.healthlake-mcp-server@latest", "--readonly"],
      "env": {
        "AWS_REGION": "us-east-1",
        "AWS_PROFILE": "your-profile-name",
        "MCP_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### Docker の設定 {#docker-configuration}

**環境変数を使用する場合:**
```json
{
  "mcpServers": {
    "healthlake": {
      "command": "docker",
      "args": [
        "run", "--rm",
        "-e", "AWS_ACCESS_KEY_ID=your_key",
        "-e", "AWS_SECRET_ACCESS_KEY=your_secret",
        "-e", "AWS_REGION=us-east-1",
        "-e", "MCP_LOG_LEVEL=INFO",
        "awslabs/healthlake-mcp-server"
      ]
    }
  }
}
```

**AWS 認証情報をマウントする場合:**
```json
{
  "mcpServers": {
    "healthlake": {
      "command": "docker",
      "args": [
        "run", "--rm",
        "-v", "~/.aws:/root/.aws",
        "-e", "AWS_PROFILE=your-profile",
        "-e", "MCP_LOG_LEVEL=INFO",
        "awslabs/healthlake-mcp-server"
      ]
    }
  }
}
```

**Docker での読み取り専用モード:**
```json
{
  "mcpServers": {
    "healthlake-readonly": {
      "command": "docker",
      "args": [
        "run", "--rm",
        "-e", "AWS_ACCESS_KEY_ID=your_key",
        "-e", "AWS_SECRET_ACCESS_KEY=your_secret",
        "-e", "AWS_REGION=us-east-1",
        "-e", "MCP_LOG_LEVEL=INFO",
        "awslabs/healthlake-mcp-server",
        "--readonly"
      ]
    }
  }
}
```

### その他の MCP クライアント {#other-mcp-clients}

追加の設定例については `examples/mcp_config.json` を参照してください。

[↑ 目次に戻る](#table-of-contents)

## 読み取り専用モード {#read-only-mode}

このサーバーは、読み取り操作は許可しつつ、すべての変更操作を防止する読み取り専用モードをサポートしています。これは次のような用途に役立ちます。

- **安全性**: 本番環境での誤った変更を防止
- **テスト**: 変更のリスクなしに FHIR リソースを安全に探索
- **監査**: 読み取りアクセスのみを許可すべき環境でのサーバー実行
- **コンプライアンス**: ヘルスケアデータへの読み取り専用アクセスに関するセキュリティ要件を満たす

### 読み取り専用モードの有効化 {#enabling-read-only-mode}

サーバーの起動時に `--readonly` フラグを追加します。

```bash
# Using uvx
uvx awslabs.healthlake-mcp-server@latest --readonly

# Or if installed locally
python -m awslabs.healthlake_mcp_server.main --readonly
```

### 読み取り専用モードで利用可能な操作 {#operations-available-in-read-only-mode}

| 操作 | 利用可否 | 説明 |
|-----------|-----------|-------------|
| `list_datastores` | ✅ | すべての HealthLake データストアを一覧表示 |
| `get_datastore_details` | ✅ | データストアの詳細情報を取得 |
| `read_fhir_resource` | ✅ | 特定の FHIR リソースを取得 |
| `search_fhir_resources` | ✅ | 高度な FHIR 検索操作 |
| `patient_everything` | ✅ | 包括的な患者記録の取得 |
| `list_fhir_jobs` | ✅ | インポート/エクスポートジョブのステータスを監視 |

### 読み取り専用モードでブロックされる操作 {#operations-blocked-in-read-only-mode}

| 操作 | ブロック | 説明 |
|-----------|---------|-------------|
| `create_fhir_resource` | ❌ | 新しい FHIR リソースを作成 |
| `update_fhir_resource` | ❌ | 既存の FHIR リソースを更新 |
| `delete_fhir_resource` | ❌ | FHIR リソースを削除 |
| `start_fhir_import_job` | ❌ | FHIR データのインポートジョブを開始 |
| `start_fhir_export_job` | ❌ | FHIR データのエクスポートジョブを開始 |

[↑ 目次に戻る](#table-of-contents)

## 利用可能なツール {#available-tools}

このサーバーは、4 つのカテゴリに整理された **11 個の包括的な FHIR ツール**を提供します。

### データストア管理 {#datastore-management}
- **`list_datastores`** - オプションのステータスフィルタリングを使用して、すべての HealthLake データストアを一覧表示
- **`get_datastore_details`** - エンドポイントやメタデータを含むデータストアの詳細情報を取得

### FHIR リソース操作（CRUD） {#fhir-resource-operations-crud}
- **`create_fhir_resource`** - 検証付きで新しい FHIR リソースを作成
- **`read_fhir_resource`** - ID を指定して特定の FHIR リソースを取得
- **`update_fhir_resource`** - バージョニング付きで既存の FHIR リソースを更新
- **`delete_fhir_resource`** - データストアから FHIR リソースを削除

### 高度な検索 {#advanced-search}
- **`search_fhir_resources`** - 修飾子、チェーン、includes、ページネーションを備えた高度な FHIR 検索
- **`patient_everything`** - FHIR $patient-everything 操作を使用した包括的な患者記録の取得

### ジョブ管理 {#job-management}
- **`start_fhir_import_job`** - S3 から FHIR データのインポートジョブを開始
- **`start_fhir_export_job`** - S3 へ FHIR データのエクスポートジョブを開始
- **`list_fhir_jobs`** - ステータスフィルタリング付きでインポート/エクスポートジョブを一覧表示および監視

### MCP リソース {#mcp-resources}

このサーバーは HealthLake データストアを MCP リソースとして自動的に公開し、以下を可能にします。
- 利用可能なデータストアの**自動検出**
- データストア ID の**手動入力が不要**
- **ステータスの可視化**（ACTIVE、CREATING など）
- **メタデータへのアクセス**（作成日、エンドポイントなど）

[↑ 目次に戻る](#table-of-contents)

## 使用例 {#usage-examples}

### 基本的なリソース操作 {#basic-resource-operations}

```json
// Create a patient (datastore discovered automatically)
{
  "datastore_id": "discovered-from-resources",
  "resource_type": "Patient",
  "resource_data": {
    "resourceType": "Patient",
    "name": [{"family": "Smith", "given": ["John"]}],
    "gender": "male"
  }
}
```

### 高度な検索 {#advanced-search-1}

```json
// Search with modifiers and includes
{
  "datastore_id": "discovered-from-resources",
  "resource_type": "Patient",
  "search_params": {
    "name:contains": "smith",
    "birthdate": "ge1990-01-01"
  },
  "include_params": ["Patient:general-practitioner"],
  "revinclude_params": ["Observation:subject"]
}
```

### Patient Everything {#patient-everything}

```json
// Get all resources for a patient
{
  "datastore_id": "discovered-from-resources",
  "patient_id": "patient-123",
  "start": "2023-01-01",
  "end": "2023-12-31"
}
```

[↑ 目次に戻る](#table-of-contents)

## 認証 {#authentication}

以下のいずれかの方法で AWS 認証情報を設定します。

1. **AWS CLI**: `aws configure`
2. **環境変数**: `AWS_ACCESS_KEY_ID`、`AWS_SECRET_ACCESS_KEY`
3. **IAM ロール**（EC2/Lambda 向け）
4. **AWS プロファイル**: `AWS_PROFILE` 環境変数を設定

### 必要な権限 {#required-permissions}

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "healthlake:ListFHIRDatastores",
        "healthlake:DescribeFHIRDatastore",
        "healthlake:CreateResource",
        "healthlake:ReadResource",
        "healthlake:UpdateResource",
        "healthlake:DeleteResource",
        "healthlake:SearchWithGet",
        "healthlake:SearchWithPost",
        "healthlake:StartFHIRImportJob",
        "healthlake:StartFHIRExportJob",
        "healthlake:ListFHIRImportJobs",
        "healthlake:ListFHIRExportJobs"
      ],
      "Resource": "*"
    }
  ]
}
```

[↑ 目次に戻る](#table-of-contents)

## エラーハンドリング {#error-handling}

すべてのツールは構造化されたエラーレスポンスを返します。

```json
{
  "error": true,
  "type": "validation_error",
  "message": "Datastore ID must be 32 characters"
}
```

**エラータイプ:**
- `validation_error` - 無効な入力パラメータ
- `not_found` - リソースまたはデータストアが見つからない
- `auth_error` - AWS 認証情報が設定されていない
- `service_error` - AWS HealthLake サービスエラー
- `server_error` - 内部サーバーエラー

[↑ 目次に戻る](#table-of-contents)

## トラブルシューティング {#troubleshooting}

### よくある問題 {#common-issues}

**「AWS credentials not configured」**
- `aws configure` を実行するか、環境変数を設定してください
- `AWS_REGION` が正しく設定されていることを確認してください

**「Resource not found」**
- データストアが存在し、ACTIVE であることを確認してください
- データストア ID が正しいことを確認してください（32 文字）
- そのデータストアへのアクセス権があることを確認してください

**「Validation error」**
- 必須パラメータが指定されていることを確認してください
- データストア ID の形式が正しいことを確認してください
- count パラメータが 1〜100 の範囲内であることを確認してください

### デバッグモード {#debug-mode}

詳細なログ出力のために環境変数を設定します。
```bash
export PYTHONPATH=.
export MCP_LOG_LEVEL=DEBUG
awslabs.healthlake-mcp-server
```

[↑ 目次に戻る](#table-of-contents)

## 開発 {#development}

### ローカル開発環境のセットアップ {#local-development-setup}

#### オプション 1: uv を使用（推奨） {#option-1-using-uv-recommended}

```bash
git clone <repository-url>
cd healthlake-mcp-server
uv sync --dev
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

#### オプション 2: pip/venv を使用 {#option-2-using-pipvenv}

```bash
git clone <repository-url>
cd healthlake-mcp-server

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

#### オプション 3: conda を使用 {#option-3-using-conda}

```bash
git clone <repository-url>
cd healthlake-mcp-server

# Create conda environment
conda create -n healthlake-mcp python=3.10
conda activate healthlake-mcp

# Install dependencies
pip install -e ".[dev]"
```

### サーバーのローカル実行 {#running-the-server-locally}

```bash
# After activating your virtual environment
python -m awslabs.healthlake_mcp_server.main

# Or using the installed script
awslabs.healthlake-mcp-server
```

### 開発ワークフロー {#development-workflow}

```bash
# Run tests
poe test

# Run tests with coverage
poe test-cov

# Format code
poe format

# Lint code
poe lint

# Run all quality checks
poe check

# Clean build artifacts
poe clean

# Build package
poe build

# Run server
poe run
```

### 利用可能なタスク {#available-tasks}

このプロジェクトはタスク自動化に [Poethepoet](https://poethepoet.natn.io/) を使用しています。利用可能なすべてのタスクを確認するには `poe --help` を実行してください。

- **テスト**: `test`、`test-cov`
- **コード品質**: `lint`、`format`、`check`、`security`
- **ビルドと実行**: `build`、`run`
- **クリーンアップ**: `clean`

### 開発ワークフロー {#development-workflow-1}

```bash
# Run all checks
poe check
```

### IDE のセットアップ {#ide-setup}

#### VS Code {#vs-code}
1. Python 拡張機能をインストールします
2. 仮想環境を選択します: `Ctrl+Shift+P` → 「Python: Select Interpreter」
3. `.venv/bin/python` を選択します

#### PyCharm {#pycharm}
1. File → Settings → Project → Python Interpreter
2. Add Interpreter → Existing Environment
3. `.venv/bin/python` を選択します

### テスト {#testing}

```bash
# Run unit tests (fast, no AWS dependencies)
poe test

# Run with coverage
poe test-cov

# Format code
poe format

# Lint code
poe lint
```

**テスト結果**: 235 個のテストが成功、カバレッジ 96%

### プロジェクト構成 {#project-structure}

```
awslabs/healthlake_mcp_server/
├── server.py           # MCP server with tool handlers
├── fhir_operations.py  # AWS HealthLake client operations
├── models.py          # Pydantic validation models
├── main.py            # Entry point
└── __init__.py        # Package initialization
```

[↑ 目次に戻る](#table-of-contents)

## コントリビューション {#contributing}

1. リポジトリをフォークします
2. フィーチャーブランチを作成します: `git checkout -b feature-name`
3. 変更を加え、テストを追加します
4. テストを実行します: `poe test`
5. コードをフォーマットします: `poe format`
6. プルリクエストを送信します

[↑ 目次に戻る](#table-of-contents)

## ライセンス {#license}

Apache License, Version 2.0 の下でライセンスされています。詳細については LICENSE ファイルを参照してください。

[↑ 目次に戻る](#table-of-contents)

## サポート {#support}

問題や質問がある場合:
- 上記のトラブルシューティングセクションを確認してください
- AWS HealthLake のドキュメントを確認してください
- リポジトリで issue を作成してください

[↑ 目次に戻る](#table-of-contents)
