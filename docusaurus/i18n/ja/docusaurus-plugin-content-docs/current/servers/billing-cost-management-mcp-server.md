---
title: AWS Billing and Cost Management MCP サーバー
---

AWS Billing and Cost Management の機能にアクセスするための MCP サーバーです。

**重要な注意事項**: このサーバーは AWS Billing and Cost Management API からコストおよび使用状況データにアクセスします。すべての API 呼び出しは呼び出し元の AWS 認証情報を使用して実行され、AWS のサービス制限およびクォータに従います。

## 機能 {#features}

### AWS Free Tier {#aws-free-tier}

- **無料利用枠の最適化**: 無料利用枠の使用状況をモニタリングし、予期しない課金を回避します

### AWS のコストおよび使用状況の分析 {#aws-cost-and-usage-analysis}

- **Cost Explorer インサイト**: 柔軟なグループ化とフィルタリングにより、過去および予測される AWS コストを分析します
- **使用状況メトリクスの分析**: AWS 環境全体のリソース使用傾向を追跡します
- **予算のモニタリング**: 既存の予算と、実際の支出に対するそのステータスを確認します
- **コスト異常検出**: 通常と異なる支出パターンとその根本原因を特定します

### コスト最適化の推奨事項 {#cost-optimization-recommendations}

- **Compute Optimizer の推奨事項**: EC2、Lambda、EBS などのライトサイジングの提案を取得します
- **Cost Optimization Hub**: AWS 環境全体のコスト削減の機会にアクセスします

### Savings Plans とリザーブドインスタンス {#savings-plans-and-reserved-instanaces}

- **リザーブドインスタンスの計画**: RI のカバレッジを分析し、購入の推奨事項を受け取ります
- **Savings Plans のガイダンス**: 使用パターンに基づいてパーソナライズされた Savings Plans の推奨事項を取得します

### S3 Storage Lens 分析 {#s3-storage-lens-analysis}

- **ストレージメトリクスのクエリ**: Storage Lens のメトリクスデータに対して SQL クエリを実行します
- **ストレージコストの内訳**: S3 のストレージコストをバケット、ストレージクラス、リージョンごとに分析します
- **ストレージ最適化の機会**: ライフサイクルポリシーの機会とコスト削減策を特定します

### コストと使用状況の比較 {#cost-and-usage-comparison}

- **月次比較**: 期間ごとのコストと使用状況を詳細な内訳とともに比較します
- **マルチアカウント分析**: 複数のリンクされたアカウントにわたるコストを分析します
- **コスト要因の特定**: コスト変動を引き起こしている主な要因を特定します

### AWS Billing and Cost Management Pricing Calculator {#aws-billing-and-cost-management-pricing-calculator}

- **ワークロード見積もりのインサイト**: ワークロード見積もりをクエリして、見積もった使用量を確認します

### AWS Billing Conductor とプロフォーマコスト分析 {#aws-billing-conductor--proforma-cost-analysis}

- **請求グループの管理**: タイプ、ステータス、料金プラン、メンバーアカウントの詳細とともに請求グループを一覧表示およびフィルタリングします
- **アカウントの関連付け**: 請求グループに関連付けられたリンクアカウントを表示し、モニタリング対象/対象外のステータスでフィルタリングします
- **請求グループのコストレポート**: 実際の AWS 料金とプロフォーマコストを比較し、マージン分析を含むコストレポートのサマリーを取得します
- **詳細なコスト内訳**: サービス名または請求期間ごとに分解された請求グループのコストレポートを取得します
- **料金ルールと料金プラン**: 料金ルール (MARKUP、DISCOUNT、TIERING) と料金プラン、およびそれらの関連付けを一覧表示します
- **カスタム明細項目**: サポート料金、共有サービスコスト、税金、クレジット、RI/SP の配分など、カスタムコスト配分を一覧表示します

### コスト配分タグ {#cost-allocation-tags}

- **タグのアクティベーションステータス**: ステータス (Active/Inactive)、タイプ (AWSGenerated/UserDefined)、および特定のタグキーでフィルタリングしてコスト配分タグを一覧表示します
- **バックフィル履歴**: アクティベーションステータスを過去の請求データに遡って適用するタグバックフィルリクエストの履歴を取得します

### コストカテゴリの定義 {#cost-category-definitions}

- **コストカテゴリの記述**: ルール、分割請求ルール、処理ステータスを含むコストカテゴリの完全な定義を取得します
- **コストカテゴリの一覧表示**: アカウント内のすべてのコストカテゴリ定義を、サマリーメタデータとともに一覧表示し、有効日またはサポートされるリソースタイプでフィルタリングします

### 特化型コスト最適化プロンプト {#specialized-cost-optimization-prompts}

- **Graviton 移行分析**: AWS Graviton への移行に適した EC2 インスタンスを特定するためのガイド付き分析
- **Savings Plans 分析**: 使用パターンに基づいた最適な Savings Plans 購入のための体系的な推奨事項

## 前提条件 {#prerequisites}

1. [Astral](https://docs.astral.sh/uv/getting-started/installation/) または [GitHub README](https://github.com/astral-sh/uv#installation) から `uv` をインストールします
2. uv python install 3.10 (またはそれ以降のバージョン) を使用して Python 3.10 以降をインストールします
3. AWS サービスへのアクセス権を持つ AWS 認証情報を設定します
   - 適切な権限を持つ AWS アカウントが必要です
   - `aws configure` または環境変数で AWS 認証情報を設定します
   - IAM ロール/ユーザーに AWS Billing and Cost Management API へのアクセス権限があることを確認します

## インストール {#installation}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.billing-cost-management-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.billing-cost-management-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.billing-cost-management-mcp-server&config=ewogICAgImNvbW1hbmQiOiAidXZ4IGF3c2xhYnMuYmlsbGluZy1jb3N0LW1hbmFnZW1lbnQtbWNwLXNlcnZlckBsYXRlc3QiLAogICAgImVudiI6IHsKICAgICAgIkZBU1RNQ1BfTE9HX0xFVkVMIjogIkVSUk9SIiwKICAgICAgIkFXU19QUk9GSUxFIjogInlvdXItYXdzLXByb2ZpbGUiLAogICAgICAiQVdTX1JFR0lPTiI6ICJ1cy1lYXN0LTEiCiAgICB9LAogICAgImRpc2FibGVkIjogZmFsc2UsCiAgICAiYXV0b0FwcHJvdmUiOiBbXQogIH0K) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20Billing%20and%20Cost%20Management%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.billing-cost-management-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

### ⚡ uv を使用する場合 {#-using-uv}

MCP クライアントの設定ファイルで MCP サーバーを設定します (例: Kiro の場合は `~/.kiro/settings/mcp.json` を編集します)。


**Linux/MacOS ユーザーの場合:**

```json
{
  "mcpServers": {
    "awslabs.billing-cost-management-mcp-server": {
      "command": "uvx",
      "args": [
         "awslabs.billing-cost-management-mcp-server@latest"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

**Windows ユーザーの場合:**

```json
{
  "mcpServers": {
    "awslabs.billing-cost-management-mcp-server": {
      "command": "uvx",
      "args": [
         "--from",
         "awslabs.billing-cost-management-mcp-server@latest",
         "awslabs.billing-cost-management-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Docker を使用する場合 {#using-docker}

または、`docker build -t awslabs/billing-cost-management-mcp-server .` が成功した後に docker を使用します。

```file
# fictitious `.env` file with AWS temporary credentials
AWS_ACCESS_KEY_ID=ASIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_SESSION_TOKEN=AQoEXAMPLEH4aoAH0gNCAPy...truncated...zrkuWJOgQs8IZZaIv2BXIa2R4Olgk
AWS_REGION=us-east-1
```

```json
{
  "mcpServers": {
    "awslabs.billing-cost-management-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env",
        "FASTMCP_LOG_LEVEL=ERROR",
        "--env-file",
        "/full/path/to/file/above/.env",
        "awslabs/billing-cost-management-mcp-server:latest"
      ],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

注意: 認証情報はホスト側で更新し続ける必要があります

### Storage Lens の設定 {#storage-lens-configuration}

Storage Lens 機能を使用するには、次の環境変数を設定する必要があります。

- **`STORAGE_LENS_MANIFEST_LOCATION`**: Storage Lens のマニフェストファイルまたはフォルダへの S3 URI (例: `s3://bucket-name/storage-lens/manifests/`)
- **`STORAGE_LENS_OUTPUT_LOCATION`** (オプション): Athena クエリ結果の S3 保存先 (デフォルトはマニフェストと同じバケットに `athena-results/` サフィックスを付けた場所)

設定例:

```json
"env": {
  "AWS_PROFILE": "your-aws-profile",
  "AWS_REGION": "us-east-1",
  "STORAGE_LENS_MANIFEST_LOCATION": "s3://your-bucket/storage-lens-data/",
  "STORAGE_LENS_OUTPUT_LOCATION": "s3://your-bucket/athena-results/"
}
```

### AWS 認証 {#aws-authentication}

この MCP サーバーには、特定の AWS 権限と設定が必要です。

#### 必要な権限 {#required-permissions}

AWS IAM ロールまたはユーザーには、さまざまな AWS Billing and Cost Management API へのアクセス権限が必要です。

Cost Explorer:
- ce:GetReservationPurchaseRecommendation
- ce:GetReservationCoverage
- ce:GetReservationUtilization
- ce:GetSavingsPlansUtilization
- ce:GetSavingsPlansCoverage
- ce:GetSavingsPlansUtilizationDetails
- ce:GetSavingsPlansPurchaseRecommendation
- ce:GetCostAndUsageComparisons
- ce:GetCostComparisonDrivers
- ce:GetAnomalies
- ce:GetCostAndUsage
- ce:GetCostAndUsageComparisons
- ce:GetCostAndUsageWithResources
- ce:GetDimensionValues
- ce:GetCostForecast
- ce:GetUsageForecast
- ce:GetTags
- ce:GetCostCategories

コスト配分タグ:
- ce:ListCostAllocationTags
- ce:ListCostAllocationTagBackfillHistory

コストカテゴリの定義:
- ce:DescribeCostCategoryDefinition
- ce:ListCostCategoryDefinitions

Cost Optimization Hub:
- cost-optimization-hub:GetRecommendation
- cost-optimization-hub:ListRecommendations
- cost-optimization-hub:ListRecommendationSummaries

Compute Optimizer:
- compute-optimizer:GetAutoScalingGroupRecommendations
- compute-optimizer:GetEBSVolumeRecommendations
- compute-optimizer:GetEC2InstanceRecommendations
- compute-optimizer:GetECSServiceRecommendations
- compute-optimizer:GetRDSDatabaseRecommendations
- compute-optimizer:GetLambdaFunctionRecommendations
- compute-optimizer:GetEnrollmentStatus
- compute-optimizer:GetIdleRecommendations

AWS Budgets:
- budgets:ViewBudget

AWS Pricing:
- pricing:DescribeServices
- pricing:GetAttributeValues
- pricing:GetProducts

AWS Free Tier:
- freetier:GetFreeTierUsage

AWS Billing and Cost Management Pricing Calculator:
- bcm-pricing-calculator:GetPreferences
- bcm-pricing-calculator:GetWorkloadEstimate
- bcm-pricing-calculator:ListWorkloadEstimateUsage
- bcm-pricing-calculator:ListWorkloadEstimates

Storage Lens (Athena および S3):
- athena:StartQueryExecution
- athena:GetQueryExecution
- athena:GetQueryResults
- athena:CreateWorkGroup
- athena:GetWorkGroup
- athena:CreateDataCatalog
- athena:GetDataCatalog
- athena:GetDatabase
- athena:CreateTable
- athena:GetTableMetadata
- athena:ListDatabases
- athena:ListTableMetadata
- s3:GetObject
- s3:ListBucket
- s3:PutObject
- s3:GetBucketLocation
- s3:GetStorageLensConfiguration
- s3:ListStorageLensConfigurations
- s3:PutStorageLensConfiguration
- s3:GetStorageLensConfigurationTagging
- s3:PutStorageLensConfigurationTagging

AWS Billing Conductor:
- billingconductor:ListBillingGroups
- billingconductor:ListBillingGroupCostReports
- billingconductor:GetBillingGroupCostReport
- billingconductor:ListAccountAssociations
- billingconductor:ListPricingPlans
- billingconductor:ListPricingRules
- billingconductor:ListPricingRulesAssociatedToPricingPlan
- billingconductor:ListPricingPlansAssociatedWithPricingRule
- billingconductor:ListCustomLineItems
- billingconductor:ListCustomLineItemVersions
- billingconductor:ListResourcesAssociatedToCustomLineItem

#### 設定 {#configuration}

このサーバーは次の主要な環境変数を使用します。

- **`AWS_PROFILE`**: AWS 設定ファイルから使用する AWS プロファイルを指定します。指定しない場合は "default" プロファイルがデフォルトで使用されます。
- **`AWS_REGION`**: API 呼び出しに使用する AWS リージョンを決定します。Cost Explorer など一部の API は特定のリージョンでのみ利用可能です。

```json
"env": {
  "AWS_PROFILE": "your-aws-profile",
  "AWS_REGION": "us-east-1"
}
```

## サポートされる AWS サービス {#supported-aws-services}

このサーバーは現在、次の AWS サービスをサポートしています

1. **Cost Explorer**
   - get_reservation_purchase_recommendation
   - get_reservation_coverage
   - get_reservation_utilization
   - get_savings_plans_purchase_recommendation
   - get_savings_plans_utilization
   - get_savings_plans_coverage
   - get_savings_plans_details
   - get_cost_comparison_drivers
   - get_cost_and_usage_comparisons
   - get_anomalies
   - get_cost_and_usage
   - get_cost_and_usage_with_resources
   - get_dimension_values
   - get_cost_forecast
   - get_usage_forecast
   - get_tags
   - get_cost_categories

2. **AWS Budgets**
   - describe_budgets

3. **AWS Free Tier**
   - get_free_tier_usage

4. **AWS Pricing**
   - get_service_codes
   - get_service_attributes
   - get_attribute_values
   - get_products

5. **Cost Optimization Hub**
   - get_recommendation
   - list_recommendations
   - list_recommendation_summaries

6. **Compute Optimizer**
   - get_auto_scaling_group_recommendations
   - get_ebs_volume_recommendations
   - get_ec2_instance_recommendations
   - get_ecs_service_recommendations
   - get_rds_database_recommendations
   - get_lambda_function_recommendations
   - get_idle_recommendations
   - get_enrollment_status

7. **Pricing Calculator**
   - get-preferences
   - get-workload-estimate
   - list-workload-estimate-usage
   - list-workload-estimates

8. **S3 Storage Lens**
   - storage_lens_run_query (Athena を使用したカスタム実装)

9. **AWS Billing Conductor**
   - list_billing_groups
   - list_billing_group_cost_reports
   - get_billing_group_cost_report
   - list_account_associations
   - list_pricing_plans
   - list_pricing_rules
   - list_pricing_rules_associated_to_pricing_plan
   - list_pricing_plans_associated_with_pricing_rule
   - list_custom_line_items
   - list_custom_line_item_versions
   - list_resources_associated_to_custom_line_item

10. **コスト配分タグ**
    - list_cost_allocation_tags
    - list_cost_allocation_tag_backfill_history

11. **コストカテゴリの定義**
    - describe_cost_category_definition
    - list_cost_category_definitions
