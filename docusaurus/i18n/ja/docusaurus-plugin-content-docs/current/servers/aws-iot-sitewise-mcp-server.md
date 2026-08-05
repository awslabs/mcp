---
title: AWS IoT SiteWise MCP サーバー
---

## 概要 {#overview}

産業用 IoT のアセット管理、データ取り込み、モニタリング、分析のための AWS IoT SiteWise の全機能を提供する包括的な MCP (Model Context Protocol) サーバーです。このサーバーにより、AI アシスタントは豊富なツールとプロンプトのセットを通じて AWS IoT SiteWise と連携できます。

## 機能 {#features}

### AWS IoT SiteWise のコア機能 {#core-aws-iot-sitewise-capabilities}

#### 🏭 アセット管理 {#-asset-management}

- **アセットの作成と管理**: 産業用アセットの作成、更新、削除、詳細取得
- **アセット階層**: 階層構造におけるアセットの関連付けと関連付け解除
- **アセットモデル**: プロパティ、階層、コンポジットモデルを持つアセットモデルの定義と管理
- **アセットプロパティ**: 測定値、属性、変換、メトリクスの管理

#### 📊 データ操作 {#-data-operations}

- **データ取り込み**: 品質インジケーター付きのバッチおよびリアルタイムのデータ取り込み
- **履歴データ**: 柔軟な時間範囲とフィルタリングによる時系列データの取得
- **集計**: 平均、合計、カウント、最小/最大、標準偏差の計算
- **補間**: 欠損データポイントの補間値の取得
- **バッチ操作**: 複数アセットに対する効率的な一括データ操作

#### 🌐 ゲートウェイと接続性 {#-gateway--connectivity}

- **ゲートウェイ管理**: IoT SiteWise Edge ゲートウェイの作成と設定
- **機能設定**: さまざまなプロトコルに対応するゲートウェイ機能の管理
- **時系列管理**: 時系列データストリームの関連付けと管理
- **エッジコンピューティング**: ローカルデータ処理と断続的な接続のサポート

#### 📦 一括操作とメタデータ転送 {#-bulk-operations--metadata-transfer}

- **一括エクスポート**: メタデータ転送ジョブを使用して、すべての IoT SiteWise リソース（アセットモデル、アセットなど）を 1 回の操作でエクスポート
- **一括インポートスキーマ**: アセット/モデルの一括インポート用の構造化スキーマの作成と検証
- **メタデータ転送ジョブ**: S3 と IoT SiteWise 間の大規模なデータ移行の管理
- **ジョブモニタリング**: 一括操作の進捗とステータスの追跡
- **マルチソースサポート**: S3 バケットと IoT SiteWise 間のデータ転送
- **スキーマ検証**: インポート前の包括的な検証によるデータ整合性の確保

#### 🤖 異常検出と計算モデル {#-anomaly-detection--computation-models}

- **異常検出モデル**: 産業用アセット向けの ML を活用した異常検出の作成と管理
- **計算モデル**: アセットプロパティに対するカスタムのデータ処理・分析ロジックの定義
- **トレーニングと推論**: 異常検出のためのトレーニングジョブとリアルタイム推論の実行
- **モデルバージョニング**: 自動プロモーションによるトレーニング済みモデルの複数バージョンの管理
- **自動再トレーニング**: 変化する運用パターンに適応するためのスケジュールされた再トレーニングの設定
- **アセットおよびアセットモデルレベルの設定**: 特定のアセットへの柔軟なバインドやアセットモデル間での再利用
- **実行モニタリング**: トレーニングの進捗、推論のステータス、モデルパフォーマンスの追跡
- **アクション管理**: 計算モデルとアセットに対するアクションの実行、監視、管理

#### 🔒 セキュリティと設定 {#-security--configuration}

- **アクセスポリシー**: ユーザーとリソースに対するきめ細かなアクセス制御
- **暗号化**: KMS 統合によるデフォルト暗号化設定の構成
- **ロギング**: 包括的なロギング設定と管理
- **ストレージ設定**: ホット層とウォーム層による多層ストレージ

### インテリジェントプロンプト {#intelligent-prompts}

#### 🔍 アセット階層の可視化 {#-asset-hierarchy-visualization}

以下を含むアセット階層の包括的な分析と可視化を提供します。

- 完全な階層ツリー図
- プロパティ分析と現在値
- ヘルスチェックとステータスモニタリング
- 最適化の推奨事項

#### 📥 データ取り込みヘルパー {#-data-ingestion-helper}

データ取り込みをセットアップするためのステップバイステップのガイダンスを提供します。

- アセットモデル設計の推奨事項
- ゲートウェイ設定テンプレート
- データマッピング戦略
- パフォーマンス最適化のヒント

## インストール {#installation}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.aws-iot-sitewise-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-iot-sitewise-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.aws-iot-sitewise-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLWlvdC1zaXRld2lzZS1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJBV1NfUkVHSU9OIjoidXMtZWFzdC0xIiwiRkFTVE1DUF9MT0dfTEVWRUwiOiJFUlJPUiJ9LCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20IoT%20SiteWise%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-iot-sitewise-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

### 前提条件 {#prerequisites}

- Python 3.10 以上
- IoT SiteWise へのアクセス権限が設定された AWS 認証情報

### オプション 1: UVX（推奨） {#option-1-uvx-recommended}

```bash
# Install UV if you don't have it yet
curl -sSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/awslabs/mcp.git
cd mcp/src/aws-iot-sitewise-mcp-server

# Install as a uv tool (this makes it available globally via uvx)
uv tool install .

# The server is now available globally via uvx
uvx awslabs.aws-iot-sitewise-mcp-server
# use @latest flag for automatically pull updates on server
uvx awslabs.aws-iot-sitewise-mcp-server@latest

# Note: The server runs silently, waiting for MCP client connections.
# You'll need to configure an MCP client to connect to it.
```

### オプション 2: Pip {#option-2-pip}

```bash
# Install from PyPI (when published)
pip install awslabs.aws-iot-sitewise-mcp-server

# Or install from source
git clone https://github.com/awslabs/mcp.git
cd mcp/src/aws-iot-sitewise-mcp-server
pip install .

# Run the server
python -m awslabs.aws_iot_sitewise_mcp_server.server
```

### AWS の設定 {#aws-configuration}

以下に対する権限を持つ AWS 認証情報を設定します。
- AWS IoT SiteWise（書き込み操作にはフルアクセス）
- AWS IoT TwinMaker（メタデータ転送操作用）
- Amazon S3（一括インポート/エクスポート操作用）

```bash
# AWS CLI (recommended)
aws configure

# Environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-west-2

# Or use AWS profiles
export AWS_PROFILE=your-profile-name
```

### MCP クライアントでの使用 {#usage-with-mcp-clients}

#### Claude Desktop {#claude-desktop}

`claude_desktop_config.json` に以下を追加します。

**オプション 1: UVX（推奨）- 読み取り専用モード**

```json
{
  "mcpServers": {
    "aws-iot-sitewise": {
      "command": "uvx",
      "args": ["awslabs.aws-iot-sitewise-mcp-server@latest"],
      "env": {
        "AWS_REGION": "us-west-2",
        "AWS_PROFILE": "your-profile-name",
        "FASTMCP_LOG_LEVEL": "DEBUG"
      },
      "transportType": "stdio"
    }
  }
}
```

**オプション 1: 書き込み操作を有効にした UVX**

```json
{
  "mcpServers": {
    "aws-iot-sitewise": {
      "command": "uvx",
      "args": ["awslabs.aws-iot-sitewise-mcp-server@latest"],
      "env": {
        "AWS_REGION": "us-west-2",
        "AWS_PROFILE": "your-profile-name",
        "FASTMCP_LOG_LEVEL": "DEBUG",
        "SITEWISE_MCP_ALLOW_WRITES": "True"
      },
      "transportType": "stdio"
    }
  }
}
```

**オプション 2: Python の直接実行 - 読み取り専用モード**

```json
{
  "mcpServers": {
    "aws-iot-sitewise": {
      "command": "python",
      "args": ["-m", "awslabs.aws_iot_sitewise_mcp_server.server"],
      "env": {
        "AWS_REGION": "us-west-2",
        "AWS_PROFILE": "your-profile-name",
        "FASTMCP_LOG_LEVEL": "DEBUG"
      },
      "transportType": "stdio"
    }
  }
}
```

**オプション 2: 書き込み操作を有効にした Python の直接実行**

```json
{
  "mcpServers": {
    "aws-iot-sitewise": {
      "command": "python",
      "args": ["-m", "awslabs.aws_iot_sitewise_mcp_server.server"],
      "env": {
        "AWS_REGION": "us-west-2",
        "AWS_PROFILE": "your-profile-name",
        "FASTMCP_LOG_LEVEL": "DEBUG",
        "SITEWISE_MCP_ALLOW_WRITES": "True"
      },
      "transportType": "stdio"
    }
  }
}
```

#### Claude Code {#claude-code}

ワークスペースまたはグローバル設定で構成します。

**オプション 1: UVX（推奨）- 読み取り専用モード**

```json
{
  "mcpServers": {
    "aws-iot-sitewise": {
      "command": "uvx",
      "args": ["awslabs.aws-iot-sitewise-mcp-server@latest"],
      "env": {
        "AWS_REGION": "us-west-2",
        "AWS_PROFILE": "your-profile-name",
        "FASTMCP_LOG_LEVEL": "DEBUG"
      },
      "transportType": "stdio"
    }
  }
}
```

**オプション 1: 書き込み操作を有効にした UVX**

```json
{
  "mcpServers": {
    "aws-iot-sitewise": {
      "command": "uvx",
      "args": ["awslabs.aws-iot-sitewise-mcp-server@latest"],
      "env": {
        "AWS_REGION": "us-west-2",
        "AWS_PROFILE": "your-profile-name",
        "FASTMCP_LOG_LEVEL": "DEBUG",
        "SITEWISE_MCP_ALLOW_WRITES": "True"
      },
      "transportType": "stdio"
    }
  }
}
```

**オプション 2: Python の直接実行 - 読み取り専用モード**

```json
{
  "mcpServers": {
    "aws-iot-sitewise": {
      "command": "python",
      "args": ["-m", "awslabs.aws_iot_sitewise_mcp_server.server"],
      "env": {
        "AWS_REGION": "us-west-2",
        "AWS_PROFILE": "your-profile-name",
        "FASTMCP_LOG_LEVEL": "DEBUG"
      },
      "transportType": "stdio"
    }
  }
}
```

**オプション 2: 書き込み操作を有効にした Python の直接実行**

```json
{
  "mcpServers": {
    "aws-iot-sitewise": {
      "command": "python",
      "args": ["-m", "awslabs.aws_iot_sitewise_mcp_server.server"],
      "env": {
        "AWS_REGION": "us-west-2",
        "AWS_PROFILE": "your-profile-name",
        "FASTMCP_LOG_LEVEL": "DEBUG",
        "SITEWISE_MCP_ALLOW_WRITES": "True"
      },
      "transportType": "stdio"
    }
  }
}
```

**注意事項:**

- `your-profile-name` は実際の AWS プロファイル名に置き換えるか、デフォルトの認証情報を使用する場合は `AWS_PROFILE` の行を削除してください
- UVX オプションはよりシンプルでパス設定が不要なため推奨されます
- 開発ワークフローについては、[開発ガイドライン](https://github.com/awslabs/mcp/blob/main/DEVELOPER_GUIDE.md)を参照してください

## ツールリファレンス {#tools-reference}

### アセット管理ツール {#asset-management-tools}

| ツール名 | 説明 |
|-----------|-------------|
| `create_asset` | アセットモデルから新しいアセットを作成 |
| `describe_asset` | アセットの詳細情報を取得 |
| `list_assets` | フィルタリングオプション付きでアセットを一覧表示 |
| `update_asset` | アセットプロパティを更新 |
| `delete_asset` | アセットを削除 |
| `associate_assets` | 親子関係を作成 |
| `disassociate_assets` | アセットの関係を削除 |
| `list_associated_assets` | 関連するアセットを一覧表示 |

### アセットモデル管理ツール {#asset-model-management-tools}

| ツール名 | 説明 |
|-----------|-------------|
| `create_asset_model` | アセットモデル定義を作成 |
| `describe_asset_model` | アセットモデルの詳細を取得 |
| `list_asset_models` | 利用可能なアセットモデルを一覧表示 |
| `update_asset_model` | アセットモデルのプロパティを変更 |
| `delete_asset_model` | アセットモデルを削除 |
| `list_asset_model_properties` | モデルのプロパティを一覧表示 |
| `create_asset_model_composite_model` | コンポジットモデルを作成 |

### データ操作ツール {#data-operations-tools}

| ツール名 | 説明 |
|-----------|-------------|
| `batch_put_asset_property_value` | データをバッチで取り込み |
| `get_asset_property_value` | 現在のプロパティ値を取得 |
| `get_asset_property_value_history` | 履歴データを取得 |
| `get_asset_property_aggregates` | 集計値を計算 |
| `get_interpl_asset_property_values` | 補間データを取得 |
| `batch_get_asset_property_value` | 現在値を一括取得 |
| `batch_get_asset_property_value_hist` | 履歴データを一括取得 |
| `batch_get_asset_property_aggregates` | 集計を一括取得 |
| `create_bulk_import_job` | 一括データ取り込み用の一括インポートジョブを作成 |
| `create_buffered_ingestion_job` | バッファリングされた取り込みジョブを作成 |
| `create_bulk_import_iam_role` | 一括インポート操作用の IAM ロールを作成 |
| `list_bulk_import_jobs` | 一括インポートジョブを一覧表示 |
| `describe_bulk_import_job` | 一括インポートジョブの情報を取得 |
| `execute_query` | 高度な分析のための SQL ライクなクエリを実行 |

### ゲートウェイと時系列ツール {#gateway--time-series-tools}

| ツール名 | 説明 |
|-----------|-------------|
| `create_gateway` | IoT SiteWise Edge ゲートウェイを作成 |
| `describe_gateway` | ゲートウェイの情報を取得 |
| `list_gateways` | 利用可能なゲートウェイを一覧表示 |
| `update_gateway` | ゲートウェイの設定を変更 |
| `delete_gateway` | ゲートウェイを削除 |
| `describe_gateway_capability_config` | 機能設定を取得 |
| `update_gateway_capability_config` | 機能を更新 |
| `list_time_series` | 時系列データストリームを一覧表示 |
| `describe_time_series` | 時系列の詳細を取得 |
| `link_time_series_asset_property` | データストリームをリンク |
| `unlink_time_series_asset_property` | ストリームのリンクを解除 |
| `delete_time_series` | 時系列を削除 |

### 計算モデルと異常検出ツール {#computation-models--anomaly-detection-tools}

| ツール名 | 説明 |
|-----------|-------------|
| `create_computation_model` | カスタム設定とデータバインディングを持つ汎用計算モデルを作成 - アセットモデルレベル（再利用可能）とアセットレベル（特定）の設定をサポート |
| `create_anomaly_detection_model` | **🤖 専用ツール** - 簡素化された設定で異常検出モデルを作成 |
| `describe_computation_model` | アクション定義を含む計算モデルの詳細情報を取得 |
| `list_computation_models` | タイプによるオプションのフィルタリング付きで計算モデルを一覧表示 |
| `update_computation_model` | 計算モデルの設定、データバインディング、メタデータを更新 |
| `delete_computation_model` | 計算モデルを削除（取り消し不可能な操作） |
| `describe_computation_model_execution_summary` | インテリジェントな設定検出付きで実行サマリーを取得 - アセットモデルレベルとアセットレベルの設定を自動的に処理し、resolve パラメータのスマートな利用とオプションのパフォーマンス最適化に対応 |
| `list_computation_model_data_binding_usages` | 特定のアセットまたはプロパティを使用している計算モデルを検索 |
| `list_computation_model_resolve_to_resources` | 計算モデルの解決先リソースを一覧表示 - resolve-to 関係を通じて関連付けられた特定のアセットを表示 |

### アクションと実行管理ツール {#action--execution-management-tools}

| ツール名 | 説明 |
|-----------|-------------|
| `execute_action` | ターゲットリソース（アセットまたは計算モデル）に対して汎用アクションを実行 - トレーニング、推論をサポート |
| `execute_training_action` | **🎯 専用ツール** - 異常検出モデルのトレーニングアクションを実行 |
| `execute_inference_action` | **🎯 専用ツール** - リアルタイム異常検出のための推論アクションを実行 |
| `list_actions` | フィルタリングオプション付きで特定のターゲットリソースのアクションを一覧表示 |
| `describe_action` | ペイロードと実行の詳細を含むアクションの詳細情報を取得 |
| `list_executions` | ステータスと進捗の追跡付きでアクションの実行を一覧表示 |
| `describe_execution` | 結果とエラーの詳細を含む実行の詳細情報を取得 |

### メタデータ転送と一括インポートツール {#metadata-transfer--bulk-import-tools}

| ツール名 | 説明 |
|-----------|-------------|
| `create_bulk_import_schema` | アセットモデルとアセット用の一括インポートスキーマを構築・検証 |
| `create_metadata_transfer_job` | **🚀 一括エクスポート/インポート操作の主要ツール** - すべてのリソースのエクスポートにはこれを使用 |
| `cancel_metadata_transfer_job` | 実行中のメタデータ転送ジョブをキャンセル |
| `get_metadata_transfer_job` | メタデータ転送ジョブの詳細情報を取得 |
| `list_metadata_transfer_jobs` | フィルタリングオプション付きでメタデータ転送ジョブを一覧表示 |

### アクセス制御と設定ツール {#access-control--configuration-tools}

| ツール名 | 説明 |
|-----------|-------------|
| `create_access_policy` | アクセス制御ポリシーを作成 |
| `describe_access_policy` | ポリシーの詳細を取得 |
| `list_access_policies` | アクセスポリシーを一覧表示 |
| `update_access_policy` | アクセス権限を変更 |
| `delete_access_policy` | アクセスポリシーを削除 |
| `describe_default_encryption_config` | 暗号化設定を取得 |
| `put_default_encryption_configuration` | 暗号化を設定 |
| `describe_logging_options` | ロギング設定を取得 |
| `put_logging_options` | ロギングを設定 |
| `describe_storage_configuration` | ストレージ設定を取得 |
| `put_storage_configuration` | ストレージ層を設定 |

## プロンプトリファレンス {#prompts-reference}

### アセット階層の可視化 {#asset-hierarchy-visualization}

```example
/prompts get asset_hierarchy_visualization_prompt <asset_id>
```

ツリー図、プロパティ分析、ヘルスチェックを含むアセット階層の包括的な分析を提供します。

### データ取り込みヘルパー {#data-ingestion-helper}

```example
/prompts get data_ingestion_helper_prompt <data_source> <target_assets>
```

ベストプラクティスと例を用いて、産業データの取り込みをセットアップするためのステップバイステップのガイダンスを提供します。

### データ探索ヘルパー {#data-exploration-helper}

```example
/prompts get data_exploration_helper_prompt <exploration_goal> <time_range>
```

SQL ライクな分析機能を持つ executeQuery API を使用して IoT データを探索するための包括的なガイダンスを提供します。

### 一括インポートワークフロー {#bulk-import-workflow}

```example
/prompts get bulk_import_workflow_helper_prompt
```

CSV 検証、IAM ロールの作成、ジョブ設定、モニタリングを含む、S3 からの一括データインポートをセットアップするためのステップバイステップのガイダンスを提供します。

### 異常検出ワークフロー {#anomaly-detection-workflow}

```example
/prompts get anomaly_detection_workflow_helper_prompt
```

AWS IoT SiteWise で異常検出をセットアップするための包括的なガイドで、以下を含みます。

- **設定戦略**: アセットモデルレベル（アセット間で再利用可能）またはアセットレベル（特定のアセットへのバインド）の選択
- **アセットとプロパティの検出**: 入力プロパティと結果の保存先を特定するためのステップバイステップのガイダンス
- **モデルの作成**: 適切なデータバインディングを持つ異常検出計算モデルの作成
- **トレーニングの実行**: 履歴データ、サンプリングレート、評価オプションを用いたトレーニングジョブの設定と実行
- **推論のセットアップ**: 設定可能な頻度と稼働ウィンドウによるリアルタイム異常検出の開始
- **自動再トレーニング**: 変化する運用パターンに適応するためのスケジュールされた再トレーニングの設定
- **モニタリングと結果**: 異常スコア、モデルパフォーマンス、実行ステータスの追跡
- **ベストプラクティス**: 最適化戦略、トラブルシューティングのガイダンス、運用上の推奨事項

## 使用例 {#usage-examples}

### アセットモデルとアセットの作成 {#creating-an-asset-model-and-asset}

```python
# Create an asset model for a wind turbine
asset_model = sitewise_create_asset_model(
    asset_model_name="WindTurbineModel",
    asset_model_description="Model for wind turbine assets",
    asset_model_properties=[
        {
            "name": "WindSpeed",
            "dataType": "DOUBLE",
            "unit": "m/s",
            "type": {
                "measurement": {}
            }
        },
        {
            "name": "PowerOutput",
            "dataType": "DOUBLE",
            "unit": "kW",
            "type": {
                "measurement": {}
            }
        }
    ]
)

# Create an asset from the model
asset = sitewise_create_asset(
    asset_name="WindTurbine001",
    asset_model_id=asset_model["asset_model_id"],
    asset_description="Wind turbine #001 in the north field"
)
```

### データの取り込み {#ingesting-data}

```python
# Ingest real-time data
entries = [
    {
        "entryId": "entry1",
        "assetId": asset["asset_id"],
        "propertyId": "wind_speed_property_id",
        "propertyValues": [
            {
                "value": {"doubleValue": 12.5},
                "timestamp": {"timeInSeconds": 1640995200},
                "quality": "GOOD"
            }
        ]
    }
]

result = sitewise_batch_put_asset_property_value(entries=entries)
```

### 異常検出のセットアップ {#setting-up-anomaly-detection}

```python
# Create an anomaly detection model for pump monitoring
anomaly_model = create_anomaly_detection_model(
    computation_model_name="PumpAnomalyDetection",
    input_properties=[
        {"assetModelProperty": {"assetModelId": "pump_model_id", "propertyId": "temperature_property_id"}},
        {"assetModelProperty": {"assetModelId": "pump_model_id", "propertyId": "pressure_property_id"}},
        {"assetModelProperty": {"assetModelId": "pump_model_id", "propertyId": "vibration_property_id"}}
    ],
    result_property={
        "assetModelProperty": {"assetModelId": "pump_model_id", "propertyId": "anomaly_score_property_id"}
    },
    computation_model_description="Detects operational anomalies in industrial pumps using temperature, pressure, and vibration data"
)

# Train the model with historical data
training_result = execute_training_action(
    training_action_definition_id="training_action_id",  # From describe_computation_model
    training_mode="TRAIN_MODEL",
    target_resource={"computationModelId": anomaly_model["computationModelId"]},
    export_data_start_time=1717225200,  # 90 days ago
    export_data_end_time=1722789360,    # Recent data
    target_sampling_rate="PT15M"        # 15-minute intervals
)

# Start real-time inference
inference_result = execute_inference_action(
    inference_action_definition_id="inference_action_id",  # From describe_computation_model
    inference_mode="START",
    target_resource={"computationModelId": anomaly_model["computationModelId"]},
    data_upload_frequency="PT15M",      # Process data every 15 minutes
    weekly_operating_window={
        "monday": ["08:00-17:00"],      # Business hours only
        "tuesday": ["08:00-17:00"],
        "wednesday": ["08:00-17:00"],
        "thursday": ["08:00-17:00"],
        "friday": ["08:00-17:00"]
    },
    inference_time_zone="America/Chicago"
)

# Monitor anomaly scores
anomaly_scores = get_asset_property_value_history(
    asset_id="pump_asset_id",
    property_id="anomaly_score_property_id",
    start_date="2024-11-01T00:00:00Z",
    end_date="2024-11-04T23:59:59Z"
)
```

## テストと検証 {#testing-and-validation}

### 包括的なテスト戦略 {#comprehensive-testing-strategy}

AWS IoT SiteWise MCP サーバーには、信頼性と API 準拠を確保するための複数のテストレイヤーが含まれています。

#### 1. パラメータ検証 {#1-parameter-validation}

- **入力検証**: すべてのパラメータは AWS IoT SiteWise の制約に対して検証されます
- **フォーマットチェック**: アセット名、ID、その他の識別子は AWS の命名規則に従います
- **クォータの適用**: サービスクォータと制限は API 呼び出しの前に適用されます
- **型安全性**: mypy による完全な型チェック

#### 2. 統合テスト {#2-integration-testing}

- **API 制約の検証**: テストは実際の AWS API 仕様に対して検証を行います
- **エラーハンドリング**: すべての AWS サービス例外に対する包括的なエラーハンドリング
- **実世界のシナリオ**: テストには現実的な産業用 IoT のユースケースが含まれます

#### 3. 検証機能 {#3-validation-features}

- **事前チェック**: AWS API 呼び出しの前にパラメータを検証
- **サービスクォータの認識**: AWS IoT SiteWise の制限に関する組み込みの知識
- **フォーマット検証**: タイムスタンプ、ARN、その他の AWS フォーマットの適切な検証
- **制約の適用**: 文字数制限、配列サイズ、その他の制約を適用

### テストの実行 {#running-tests}

```bash
# Run all tests
pytest

# Run tests with verbose output (shows individual test names)
pytest -v

# Run specific test file
pytest test/test_sitewise_tools.py -v
```

### リソースクリーンアップの保証 {#resource-cleanup-guarantees}

テストスイートには、AWS リソースのリークを防ぐための**包括的なリソースクリーンアップ**が含まれています。

#### 自動クリーンアップ機能 {#automatic-cleanup-features}

- **コンテキストマネージャー**: すべてのテストは `sitewise_test_resources()` コンテキストマネージャーを使用します
- **リソース追跡**: 作成されたすべてのリソースはクリーンアップのために自動的に登録されます
- **状態の待機**: クリーンアップの前にリソースが削除可能な状態になるまで待機します
- **エラーハンドリング**: 個々の削除が失敗してもクリーンアップは継続します

#### 緊急クリーンアップ {#emergency-cleanup}

- **シグナルハンドラー**: Ctrl+C またはプロセス終了時にクリーンアップがトリガーされます
- **Atexit ハンドラー**: テストが予期せずクラッシュした場合でもクリーンアップが実行されます
- **孤立リソースの検出**: 過去の失敗した実行によるリソースをスキャンしてクリーンアップします
- **リトライロジック**: 一時的な障害に対する指数バックオフによる自動リトライ
- **グローバルレジストリ**: プロセス全体のリソース追跡のための緊急クリーンアップレジストリ

#### クリーンアップの順序 {#cleanup-order}

1. アセットの関連付けと時系列の関連付け
2. ダッシュボード
3. プロジェクト
4. アクセスポリシー
5. 時系列
6. アセット
7. ゲートウェイ
8. アセットモデル（アセットが依存するため最後）

#### Pytest 統合 {#pytest-integration}

```python
def test_asset_creation(sitewise_tracker):
    """Test using the pytest fixture for automatic cleanup."""
    # Create asset model
    model_result = create_asset_model(name="TestModel", ...)
    sitewise_tracker.register_asset_model(model_result['asset_model_id'])

    # Create asset
    asset_result = create_asset(name="TestAsset", ...)
    sitewise_tracker.register_asset(asset_result['asset_id'])

    # Test operations...

    # Resources automatically cleaned up when test ends
```

#### 堅牢なエラーハンドリング {#robust-error-handling}

- **AWS 認証情報の検証**: 認証情報が利用できない場合、テストは自動的にスキップされます
- **サービスの可用性**: サービス停止時の適切な処理
- **権限エラー**: アクセス拒否シナリオの適切な処理
- **ネットワークの問題**: 一時的なネットワーク問題に対するリトライロジック
- **リソース状態の競合**: リソースが適切な状態になるまで待機します

### 検証の例 {#validation-examples}

サーバーには包括的なパラメータ検証が含まれています。

```python
# Asset name validation
create_asset("", "model-id")  # ❌ Fails: Empty name
create_asset("a" * 257, "model-id")  # ❌ Fails: Too long
create_asset("asset@invalid", "model-id")  # ❌ Fails: Invalid characters
create_asset("Valid_Asset-Name", "model-id")  # ✅ Passes validation

# Batch size validation
batch_put_asset_property_value([])  # ❌ Fails: Empty batch
batch_put_asset_property_value([...] * 11)  # ❌ Fails: Too many entries
batch_put_asset_property_value([...] * 5)  # ✅ Passes validation

# Service quota awareness
create_asset_model(properties=[...] * 201)  # ❌ Fails: Too many properties
create_asset_model(properties=[...] * 50)   # ✅ Passes validation
```

### エラーハンドリング {#error-handling}

すべてのツールは一貫したエラーハンドリングを提供します。

```python
{
    "success": False,
    "error": "Validation error: Asset name cannot exceed 256 characters",
    "error_code": "ValidationException"
}
```

### API 準拠 {#api-compliance}

実装は以下に対して検証されています。

- **AWS IoT SiteWise API リファレンス**: すべてのパラメータは公式ドキュメントと一致します
- **サービスクォータ**: 現在の AWS サービス制限が適用されます
- **データフォーマット**: タイムスタンプ、ARN、識別子の適切な検証
- **エラーコード**: AWS のエラーレスポンスパターンと一貫性があります
- アセットとプロパティには意味のある名前と説明を使用してください
- 適切なデータ型と単位を定義してください
- アセットを論理的な階層に整理してください
- 再利用可能なコンポーネントにはコンポジットモデルを使用してください

### データ取り込み {#data-ingestion}

- 適切なエラーハンドリングとリトライロジックを実装してください
- 効率のためにバッチ操作を使用してください
- データポイントに品質インジケーターを含めてください
- データの検証とクレンジングを計画してください

### セキュリティ {#security}
- 最小権限のアクセスポリシーを使用してください
- 機密データの暗号化を有効にしてください
- 包括的なロギングを設定してください
- 定期的なセキュリティ監査とレビューを実施してください

## トラブルシューティング {#troubleshooting}

### よくある問題 {#common-issues}

1. **認証エラー**
   - AWS 認証情報が適切に設定されていることを確認してください
   - IoT SiteWise 操作に対する IAM 権限を確認してください
   - リージョン設定を確認してください

2. **アセット作成の失敗**
   - アセットモデル定義を検証してください
   - 命名の競合を確認してください
   - プロパティ設定が適切であることを確認してください

3. **データ取り込みの問題**
   - プロパティエイリアスと ID を確認してください
   - タイムスタンプのフォーマットを確認してください
   - データ型と範囲を検証してください

4. **メタデータ転送の問題**
   - IoT TwinMaker サービスの権限を確認してください
   - ソース/宛先操作のための S3 バケットへのアクセスを確認してください
   - 一括インポートスキーマのフォーマットを検証してください
   - 詳細なエラーメッセージについてはジョブステータスを監視してください

5. **一括インポートスキーマのエラー**
   - アセットモデルの外部 ID が一意であることを確認してください
   - プロパティのデータ型が要件と一致することを確認してください
   - 階層参照が有効であることを確認してください
   - 検証には create_bulk_import_schema ツールを使用してください

### ヘルプの入手 {#getting-help}

- AWS IoT SiteWise のドキュメントを確認してください
- 詳細なエラーメッセージについては CloudWatch ログを確認してください
- トラブルシューティングのガイダンスには診断プロンプトを使用してください

## コントリビューション {#contributing}

この MCP サーバーは拡張可能なように設計されています。新しい機能を追加するには、以下の手順に従います。

1. 適切なモジュールに新しいツール関数を作成する
2. `Tool.from_function` パターンを使用してツール定義を追加する
3. メインサーバー設定にツールを登録する
4. ドキュメントと例を更新する

## ライセンス {#license}

このプロジェクトは Apache License 2.0 のもとでライセンスされています。詳細は [LICENSE](https://github.com/awslabs/mcp/blob/main/src/aws-iot-sitewise/LICENSE) ファイルを参照してください。

---

**Built with ❤️ by AWS Gen AI Labs and AWS IoT Sitewise Engineering teams**
