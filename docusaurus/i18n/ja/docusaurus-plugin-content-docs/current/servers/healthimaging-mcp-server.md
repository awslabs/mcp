# AWS HealthImaging MCP サーバー

AWS HealthImaging 操作のための包括的な Model Context Protocol (MCP) サーバーです。データストアの自動検出により、医療画像データのライフサイクル全体を管理する **39 個のツール**を提供します。

## 目次 {#table-of-contents}

- [機能](#features)
- [クイックスタート](#quick-start)
- [インストール](#installation)
- [利用可能なツール](#available-tools)
  - [データストア管理](#datastore-management)
  - [イメージセット操作](#image-set-operations)
  - [DICOM ジョブ管理](#dicom-job-management)
  - [メタデータとフレームの操作](#metadata--frame-operations)
  - [タグ付け操作](#tagging-operations)
  - [高度な DICOM 操作](#advanced-dicom-operations)
  - [一括操作](#bulk-operations)
  - [DICOM 階層操作](#dicom-hierarchy-operations)
- [使用例](#usage-examples)
- [認証](#authentication)
- [エラーハンドリング](#error-handling)
- [トラブルシューティング](#troubleshooting)
- [開発](#development)

## 機能 {#features}

- **39 個の包括的な HealthImaging ツール**: 医療画像データのライフサイクル全体を管理
- **削除操作**: 患者データの削除およびスタディの削除ツールが「忘れられる権利/消去の権利」の目的をサポート
- **データストアの自動検出**: 既存のデータストアをシームレスに検索して操作
- **DICOM メタデータ操作**: 医療画像メタデータの抽出と分析
- **イメージフレーム管理**: 個々のイメージフレームの取得と処理
- **検索機能**: イメージセットとスタディを横断する高度な検索
- **一括操作**: 効率的な患者メタデータの更新と削除
- **DICOM 階層**: イメージセット内のシリーズおよびインスタンスの操作
- **エラーハンドリング**: 詳細なフィードバックを備えた包括的なエラーハンドリング
- **型安全性**: 完全な型アノテーションと検証

## クイックスタート {#quick-start}

### オプション 1: uvx（推奨） {#option-1-uvx-recommended}

```bash
uvx awslabs.healthimaging-mcp-server@latest
```

### オプション 2: uv install {#option-2-uv-install}

```bash
uv add awslabs.healthimaging-mcp-server
```

### オプション 3: Docker {#option-3-docker}

```bash
docker run -it --rm \
  -e AWS_REGION=us-east-1 \
  -e AWS_PROFILE=your-profile \
  -v ~/.aws:/root/.aws:ro \
  public.ecr.aws/awslabs/healthimaging-mcp-server:latest
```

## MCP クライアントの設定 {#mcp-client-configuration}

### Amazon Q Developer CLI {#amazon-q-developer-cli}

```json
{
  "mcpServers": {
    "healthimaging": {
      "command": "uvx",
      "args": ["awslabs.healthimaging-mcp-server@latest"],
      "env": {
        "AWS_REGION": "us-east-1",
        "AWS_PROFILE": "your-profile",
        "FASTMCP_LOG_LEVEL": "WARNING"
      }
    }
  }
}
```

### その他の MCP クライアント {#other-mcp-clients}

Claude Desktop などの他の MCP クライアントの場合は、以下を設定に追加します。

```json
{
  "mcpServers": {
    "healthimaging": {
      "command": "uvx",
      "args": ["awslabs.healthimaging-mcp-server@latest"],
      "env": {
        "AWS_REGION": "us-east-1",
        "AWS_PROFILE": "your-profile"
      }
    }
  }
}
```

## 利用可能なツール {#available-tools}

### データストア管理 {#datastore-management}
- `list_datastores` - すべての HealthImaging データストアを一覧表示（オプションでフィルタリング可能）
- `get_datastore` - 特定のデータストアに関する詳細情報を取得
- `create_datastore` - 新しい HealthImaging データストアを作成
- `delete_datastore` - データストアを削除（安全チェック付き）

### イメージセット操作 {#image-set-operations}
- `search_image_sets` - DICOM 条件によるイメージセットの高度な検索
- `get_image_set` - 特定のイメージセットに関する詳細情報を取得
- `get_image_set_metadata` - イメージセットの完全な DICOM メタデータを取得
- `list_image_set_versions` - イメージセットのすべてのバージョンを一覧表示
- `update_image_set_metadata` - イメージセットの DICOM メタデータを更新
- `delete_image_set` - イメージセットを削除（安全チェック付き）
- `copy_image_set` - イメージセットを別のデータストアにコピー

### DICOM ジョブ管理 {#dicom-job-management}
- `start_dicom_import_job` - S3 からの新しい DICOM インポートジョブを開始
- `get_dicom_import_job` - インポートジョブのステータスと詳細を取得
- `list_dicom_import_jobs` - すべての DICOM インポートジョブを一覧表示（フィルタリング付き）
- `start_dicom_export_job` - S3 への新しい DICOM エクスポートジョブを開始
- `get_dicom_export_job` - エクスポートジョブのステータスと詳細を取得
- `list_dicom_export_jobs` - すべての DICOM エクスポートジョブを一覧表示（フィルタリング付き）

### メタデータとフレームの操作 {#metadata--frame-operations}
- `get_image_frame` - ピクセルデータを含む個々のイメージフレームを取得

### タグ付け操作 {#tagging-operations}
- `list_tags_for_resource` - HealthImaging リソースのすべてのタグを一覧表示
- `tag_resource` - HealthImaging リソースにタグを追加
- `untag_resource` - HealthImaging リソースからタグを削除

### 高度な DICOM 操作 {#advanced-dicom-operations}
- `delete_patient_studies` - 特定の患者のすべてのスタディを削除（GDPR コンプライアンス）
- `delete_study` - 特定のスタディのすべてのイメージセットを削除
- `search_by_patient_id` - 患者 ID によってすべてのイメージセットを検索
- `search_by_study_uid` - study instance UID によってイメージセットを検索
- `search_by_series_uid` - series instance UID によってイメージセットを検索
- `get_patient_studies` - 特定の患者のすべてのスタディを取得
- `get_patient_series` - 特定の患者のすべてのシリーズを取得
- `get_study_primary_image_sets` - スタディのプライマリイメージセットを取得
- `delete_series_by_uid` - series instance UID によって特定のシリーズを削除
- `get_series_primary_image_set` - シリーズのプライマリイメージセットを取得
- `get_patient_dicomweb_studies` - 患者の DICOMweb スタディレベル情報を取得
- `delete_instance_in_study` - スタディ内の特定のインスタンスを削除
- `delete_instance_in_series` - シリーズ内の特定のインスタンスを削除
- `update_patient_study_metadata` - スタディ全体の患者およびスタディのメタデータを更新

### 一括操作 {#bulk-operations}
- `bulk_update_patient_metadata` - 患者のすべてのスタディにわたって患者メタデータを更新
- `bulk_delete_by_criteria` - 指定した条件に一致する複数のイメージセットを削除

### DICOM 階層操作 {#dicom-hierarchy-operations}
- `remove_series_from_image_set` - イメージセットから特定のシリーズを削除
- `remove_instance_from_image_set` - イメージセットから特定のインスタンスを削除

## 使用例 {#usage-examples}

### 基本的な操作 {#basic-operations}

```python
# List all datastores
datastores = await list_datastores()

# Get specific datastore
datastore = await get_datastore(datastore_id="12345678901234567890123456789012")

# Search for image sets
results = await search_image_sets(
    datastore_id="12345678901234567890123456789012",
    search_criteria={
        "filters": [
            {
                "values": [{"DICOMPatientId": "PATIENT123"}],
                "operator": "EQUAL"
            }
        ]
    }
)
```

### 高度な検索 {#advanced-search}

```python
# Complex search with multiple filters
results = await search_image_sets(
    datastore_id="12345678901234567890123456789012",
    search_criteria={
        "filters": [
            {
                "values": [{"DICOMStudyDate": "20240101"}],
                "operator": "EQUAL"
            },
            {
                "values": [{"DICOMModality": "CT"}],
                "operator": "EQUAL"
            }
        ]
    },
    max_results=50
)
```

### DICOM メタデータ {#dicom-metadata}

```python
# Get DICOM metadata for an image set
metadata = await get_image_set_metadata(
    datastore_id="12345678901234567890123456789012",
    image_set_id="98765432109876543210987654321098"
)

# Get specific image frame
frame = await get_image_frame(
    datastore_id="12345678901234567890123456789012",
    image_set_id="98765432109876543210987654321098",
    image_frame_information={
        "imageFrameId": "frame123"
    }
)
```

## 認証 {#authentication}

### 必要な権限 {#required-permissions}

AWS 認証情報には以下の権限が必要です。

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "medical-imaging:ListDatastores",
                "medical-imaging:GetDatastore",
                "medical-imaging:CreateDatastore",
                "medical-imaging:DeleteDatastore",
                "medical-imaging:ListImageSets",
                "medical-imaging:GetImageSet",
                "medical-imaging:SearchImageSets",
                "medical-imaging:CopyImageSet",
                "medical-imaging:UpdateImageSetMetadata",
                "medical-imaging:DeleteImageSet",
                "medical-imaging:GetImageFrame",
                "medical-imaging:GetImageSetMetadata",
                "medical-imaging:ListDICOMImportJobs",
                "medical-imaging:GetDICOMImportJob",
                "medical-imaging:StartDICOMImportJob"
            ],
            "Resource": "*"
        }
    ]
}
```

## エラーハンドリング {#error-handling}

このサーバーは包括的なエラーハンドリングを提供します。

- **検証エラー**: 詳細なエラーメッセージを伴う入力検証
- **AWS サービスエラー**: AWS API エラーの適切な処理
- **リソースが見つからない場合**: 存在しないリソースに関する明確なメッセージ
- **権限エラー**: アクセスの問題に対する役立つガイダンス
- **レート制限**: 指数バックオフによる自動再試行

## トラブルシューティング {#troubleshooting}

### よくある問題 {#common-issues}

1. **認証エラー**
   - AWS 認証情報が設定されているか確認する
   - IAM 権限を確認する
   - 正しい AWS リージョンであることを確認する

2. **リソースが見つからない**
   - データストア/イメージセットの ID を確認する
   - 指定したリージョンにリソースが存在するか確認する
   - アクセス権限を確認する

3. **インポートジョブの失敗**
   - S3 バケットの権限を確認する
   - DICOM ファイル形式を確認する
   - インポートジョブのログを確認する

### デバッグモード {#debug-mode}

デバッグログを有効にします。

```bash
export FASTMCP_LOG_LEVEL=DEBUG
uvx awslabs.healthimaging-mcp-server@latest
```

## 開発 {#development}

### ローカル開発のセットアップ {#local-development-setup}

1. リポジトリをクローンします。
```bash
git clone https://github.com/awslabs/mcp-server-collection.git
cd mcp-server-collection/src/healthimaging-mcp-server
```

2. 依存関係をインストールします。
```bash
uv sync --dev
```

3. テストを実行します。
```bash
uv run python -m pytest tests/ -v
```

4. サーバーをローカルで実行します。
```bash
uv run python -m awslabs.healthimaging_mcp_server
```

### テスト {#testing}

このサーバーには 99% のカバレッジを持つ包括的なテストが含まれています。

```bash
# Run all tests
uv run python -m pytest tests/ -v

# Run with coverage
uv run python -m pytest tests/ -v --cov=awslabs.healthimaging_mcp_server --cov-report=html
```

## コントリビューション {#contributing}

コントリビューションを歓迎します。詳細については [コントリビューションガイド](https://github.com/awslabs/mcp-server-collection/blob/main/CONTRIBUTING.md) を参照してください。

## ライセンス {#license}

このプロジェクトは Apache License 2.0 の下でライセンスされています。詳細については [LICENSE](https://github.com/awslabs/mcp-server-collection/blob/main/LICENSE) ファイルを参照してください。

## サポート {#support}

サポートが必要な場合は、以下を行ってください。
1. [トラブルシューティングのセクション](#troubleshooting) を確認する
2. [AWS HealthImaging ドキュメント](https://docs.aws.amazon.com/healthimaging/) を確認する
3. [GitHub リポジトリ](https://github.com/awslabs/mcp-server-collection/issues) で issue を作成する
