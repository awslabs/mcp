---
title: "AWS Labs CloudWatch MCPサーバー"
---

CloudWatch 向けのこの AWS Labs Model Context Protocol (MCP) サーバーは、トラブルシューティングエージェントが CloudWatch のデータを活用して、AI による根本原因分析を行い、推奨事項を提示できるようにします。監視をシンプルにし、コンテキストの切り替えを減らし、チームがサービスの問題を迅速に診断・解決できるよう支援する包括的なオブザーバビリティツールを提供します。このサーバーは、標準化された MCP インターフェースを通じて AI エージェントに CloudWatch テレメトリデータへのシームレスなアクセスを提供し、カスタム API 統合の必要性を排除して、トラブルシューティングワークフロー中のコンテキスト切り替えを削減します。CloudWatch のすべての機能へのアクセスを一元化することで、インシデント解決を加速し運用の可視性を向上させる、強力なサービス横断の相関分析とインサイトを実現します。

## 手順 {#instructions}

CloudWatch MCP サーバーは、アラームのトラブルシューティング、メトリクス定義の理解、アラームの推奨、ログ分析など、よくある運用シナリオに対応するための専用ツールを提供します。各ツールは、1 つまたは複数の CloudWatch API をタスク指向の操作としてカプセル化しています。

## 機能 {#features}

アラームベースのトラブルシューティング - アクティブなアラームを特定し、関連するメトリクスとログを取得し、過去のアラームパターンを分析して、発生したアラートの根本原因を特定します。コンテキストを考慮した修復の推奨事項を提示します。

ログアナライザー - 指定した時間ウィンドウ内で、CloudWatch ロググループの異常、メッセージパターン、エラーパターンを分析します。

メトリクス定義アナライザー - メトリクスが何を表しているか、どのように計算されるか、メトリクスデータの取得に推奨される統計は何かについて、包括的な説明を提供します。

アラームの推奨 - しきい値、評価期間、その他のアラーム設定を含む、CloudWatch メトリクスに推奨されるアラーム構成を提案します。

## 前提条件 {#prerequisites}
1. [CloudWatch Telemetry](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html) が利用できる AWS アカウント
2. この MCP サーバーは、LLM クライアントと同じホスト上でローカルにのみ実行できます。
3. AWS サービスへのアクセス権を持つ AWS 認証情報を設定すること
   - 適切な権限を持つ AWS アカウントが必要です（以下の必要な権限を参照）
   - `aws configure` または環境変数で AWS 認証情報を設定します

## 利用可能なツール {#available-tools}

### CloudWatch Metrics 用ツール {#tools-for-cloudwatch-metrics}
* `get_metric_data` - 任意の CloudWatch メトリクスについて、詳細な CloudWatch メトリクスデータを取得します。Application Signals 固有ではない一般的な CloudWatch メトリクスにはこちらを使用してください。任意のメトリクス名前空間、ディメンション、統計をクエリできます。高度なユースケース向けにオプションの `queries` パラメータをサポートしており、次のような用途に利用できます。
  * レイテンシー分析のための**パーセンタイル統計**（p50、p90、p99 など）
  * 派生メトリクスを計算する**数式**（例: エラー率 = errors/invocations × 100）
  * **複数メトリクスのバッチ処理** — 1 回の API 呼び出しで複数のメトリクスを取得
* `get_metric_metadata` - 特定の CloudWatch メトリクスに関する包括的なメタデータを取得します
* `get_recommended_metric_alarms` - ベストプラクティス、およびトレンド・季節性・統計分析に基づいて、CloudWatch メトリクスに推奨されるアラームを取得します。
* `analyze_metric` - CloudWatch メトリクスデータを分析して、トレンド、季節性、統計的特性を判定します

### CloudWatch PromQL 用ツール {#tools-for-cloudwatch-promql}
* `execute_promql_query` - CloudWatch に対してインスタント PromQL クエリを実行し、単一時点のメトリクス値を返します。OTLP 経由で取り込まれたメトリクス、エンリッチされた vended AWS メトリクス、および PromQL ラベル構文（`@resource.*`、`@aws.*`、`@instrumentation.*`）を使用するクエリに使用します。
* `execute_promql_range_query` - 時間ウィンドウにわたって PromQL レンジクエリを実行し、時系列データ（マトリックス）を返します。PromQL 構文によるトレンド分析やグラフ化に使用します。
* `get_promql_label_values` - 特定の PromQL ラベルの値を取得します（例: メトリクス名なら `__name__`、サービスなら `@resource.service.name`）。メトリクスの探索に使用します。
* `get_promql_series` - PromQL ラベルセレクターに一致する時系列を検索します。一致した系列の完全なラベルセットを返します。
* `get_promql_labels` - 利用可能なすべての PromQL ラベル名を一覧表示します。OTLP 経由で取り込まれたメトリクスやエンリッチされた vended メトリクスのラベル構造を把握するために使用します。

> **注:** エンリッチされた vended AWS メトリクスを利用するには、まず OTel エンリッチメントを有効にする必要があります（`aws cloudwatch start-otel-enrichment`）。vended メトリクスはヒストグラムです — `histogram_avg()`、`histogram_sum()` などを使用してください。サービス間でメトリクスを区別するには `@instrumentation.@name` を使用します（例: `"cloudwatch.aws/ec2"` と `"cloudwatch.aws/rds"`）。
>
> **OTLP スコープと PromQL ラベルのマッピング:**
> | OTLP スコープ | 属性プレフィックス | 例 |
> |---|---|---|
> | Resource | `@resource.` | `@resource.service.name="myservice"` |
> | Instrumentation Scope | `@instrumentation.` | `@instrumentation.@name="cloudwatch.aws/ec2"` |
> | Datapoint | `@datapoint.` またはプレフィックスなし | `InstanceId="i-xxx"` または `@datapoint.InstanceId="i-xxx"` |
> | AWS システムラベル | `@aws.` | `@aws.account_id="123456789012"`、`@aws.region="us-east-1"` |
> | AWS リソースタグ | `@aws.tag.` | `@aws.tag.Environment="production"`、`@aws.tag.Team="backend"` |

### CloudWatch Alarms 用ツール {#tools-for-cloudwatch-alarms}
* `get_active_alarms` - アカウント全体で現在アクティブな CloudWatch アラームを特定します
* `get_alarm_history` - 指定した CloudWatch アラームの過去の状態変化とパターンを取得します

### CloudWatch Logs 用ツール {#tools-for-cloudwatch-logs}
* `describe_log_groups` - CloudWatch ロググループに関するメタデータを検索します
* `analyze_log_group` - CloudWatch ログの異常、メッセージパターン、エラーパターンを分析します
* `execute_log_insights_query` - 指定した時間範囲とクエリ構文で、CloudWatch ロググループに対して CloudWatch Logs Insights クエリを実行し、結果の取得に使用する一意の ID を返します
* `execute_cwl_insights_batch` - 1 回の呼び出しで複数のロググループとリージョンにまたがって Logs Insights クエリを実行します。ロググループの自動チャンク分割（1 クエリあたり最大 50）、同時実行数の制御（1 リージョンあたり最大 7）、完了までのポーリング、失敗時のリトライ、10,000 レコードまたはタイムアウトの制限に達した場合の時間範囲の分割を自動で行います。リージョン、ロググループ、およびオプションのアカウントラベルが付与された、マージ済みの単一の結果セットを返します。下記の [`execute_cwl_insights_batch` の例](#execute_cwl_insights_batch-examples)を参照してください。
* `get_logs_insight_query_results` - クエリ ID を使用して、実行済みの CloudWatch Insights クエリの結果を取得します。`execute_log_insights_query` の呼び出し後に使用します
* `cancel_logs_insight_query` - 実行中の CloudWatch Logs Insights クエリをキャンセルします

#### `execute_cwl_insights_batch` の例 {#execute_cwl_insights_batch-examples}

**基本的な使い方:**
```python
result = await execute_cwl_insights_batch(
    ctx,
    log_group_names=['/aws/lambda/my-app'],  # Log group names (or ARNs for cross-account/region)
    regions=['us-east-1', 'us-west-2', 'eu-west-1'],  # Regions to query
    start_time='2025-04-19T20:00:00+00:00',  # ISO 8601 start time with timezone
    end_time='2025-04-19T21:00:00+00:00',  # ISO 8601 end time with timezone
    query_string='fields @timestamp, @message | filter @message like /ERROR/ | limit 100'  # Logs Insights query
)

print(f"Found {result.summary.total_records_returned} errors across {result.summary.total_regions} regions")
for warning in result.summary.warnings:
    print(f"Warning: {warning}")
```

**ロググループ ARN を使用したクロスアカウント/クロスリージョンクエリ:**
```python
# When querying log groups in different accounts or regions, use ARN format:
# arn:aws:logs:<region>:<account-id>:log-group:<log-group-name>
result = await execute_cwl_insights_batch(
    ctx,
    log_group_names=[
        'arn:aws:logs:us-east-1:123456789012:log-group:/aws/ecs/my-service',  # Source account log group ARN
        'arn:aws:logs:eu-west-1:123456789012:log-group:/aws/ecs/my-service'   # Different region
    ],
    regions=['us-east-1'],  # Monitoring account region
    start_time='2025-04-19T00:00:00+00:00',
    end_time='2025-04-19T23:59:59+00:00',
    query_string='fields @timestamp, @message | filter level = "ERROR" | stats count() by bin(5m)',
    account_label='prod-123456789012',  # Optional label for result annotation
    profile_name='prod-readonly'  # AWS profile with cross-account access
)
```

**パフォーマンスのヒント:**
- 結果サイズを制御するには、`limit` パラメータまたはクエリ内の `| limit N` を使用します
- クエリを高速化するには時間範囲を狭めます
- 10,000 レコードの制限に達した場合、ツールは時間範囲を自動的に分割します
- 最適化の提案については `summary.warnings` を確認してください

**よくあるエラーと解決策:**
- `Invalid ISO 8601 timestamp`: タイムスタンプにタイムゾーンが含まれていることを確認してください（例: `+00:00`）
- `start_time must be before end_time`: 時間範囲の順序を確認してください
- `Query failed... bad query syntax`: [AWS Logs Insights のドキュメント](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax.html)でクエリ構文を確認してください
- 結果が大きい旨の警告: クエリに `| limit N` を追加するか、より短い時間範囲を使用してください

### 必要な IAM 権限 {#required-iam-permissions}
* `cloudwatch:DescribeAlarms`
* `cloudwatch:DescribeAlarmHistory`
* `cloudwatch:GetMetricData`
* `cloudwatch:ListMetrics`

* `logs:DescribeLogGroups`
* `logs:DescribeQueryDefinitions`
* `logs:ListLogAnomalyDetectors`
* `logs:ListAnomalies`
* `logs:StartQuery`
* `logs:GetQueryResults`
* `logs:StopQuery`

## インストール {#installation}

### オプション 1: Python (UVX) {#option-1-python-uvx}
#### 前提条件 {#prerequisites-1}
1. [Astral](https://docs.astral.sh/uv/getting-started/installation/) または [GitHub README](https://github.com/astral-sh/uv#installation) から `uv` をインストールします
2. `uv python install 3.10` を使用して Python をインストールします

#### ワンクリックインストール {#one-click-install}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.cloudwatch-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.cloudwatch-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22%5BThe%20AWS%20Profile%20Name%20to%20use%20for%20AWS%20access%5D%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.cloudwatch-mcp-server&config=ewogICAgImF1dG9BcHByb3ZlIjogW10sCiAgICAiZGlzYWJsZWQiOiBmYWxzZSwKICAgICJjb21tYW5kIjogInV2eCBhd3NsYWJzLmNsb3Vkd2F0Y2gtbWNwLXNlcnZlckBsYXRlc3QiLAogICAgImVudiI6IHsKICAgICAgIkFXU19QUk9GSUxFIjogIltUaGUgQVdTIFByb2ZpbGUgTmFtZSB0byB1c2UgZm9yIEFXUyBhY2Nlc3NdIiwKICAgICAgIkZBU1RNQ1BfTE9HX0xFVkVMIjogIkVSUk9SIgogICAgfSwKICAgICJ0cmFuc3BvcnRUeXBlIjogInN0ZGlvIgp9) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=CloudWatch%20MCP%20Server&config=%7B%22autoApprove%22%3A%5B%5D%2C%22disabled%22%3Afalse%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.cloudwatch-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22%5BThe%20AWS%20Profile%20Name%20to%20use%20for%20AWS%20access%5D%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22transportType%22%3A%22stdio%22%7D) |

#### MCP 設定 (Kiro, Cline) {#mcp-config-kiro-cline}
* Kiro の場合、MCP 設定（~/.kiro/settings/mcp.json）を更新します
* Cline の場合、MCP タブから「Configure MCP Servers」オプションをクリックします
```json
{
  "mcpServers": {
    "awslabs.cloudwatch-mcp-server": {
      "autoApprove": [],
      "disabled": false,
      "command": "uvx",
      "args": [
        "awslabs.cloudwatch-mcp-server@latest"
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
### Windows でのインストール {#windows-installation}

Windows ユーザーの場合、MCP サーバーの設定形式は少し異なります。

```json
{
  "mcpServers": {
    "awslabs.cloudwatch-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.cloudwatch-mcp-server@latest",
        "awslabs.cloudwatch-mcp-server.exe"
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


認証情報プロファイルの作成と管理については、[AWS ドキュメント](https://docs.aws.amazon.com/cli/v1/userguide/cli-configure-files.html)を参照してください

### オプション 2: Docker イメージ {#option-2-docker-image}
#### 前提条件 {#prerequisites-2}
LLM クライアントと同じホスト上で Docker イメージをローカルにビルドしてインストールします
1. [Docker](https://docs.docker.com/desktop/) をインストールします
2. `git clone https://github.com/awslabs/mcp.git`
3. サブディレクトリに移動します `cd src/cloudwatch-mcp-server/`
4. `docker build -t awslabs/cloudwatch-mcp-server:latest .` を実行します

#### Cursor ワンクリックインストール {#one-click-cursor-install}
[![Install CloudWatch MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://www.cursor.com/install-mcp?name=awslabs.cloudwatch-mcp-server&config=ewogICAgICAgICJjb21tYW5kIjogImRvY2tlciIsCiAgICAgICAgImFyZ3MiOiBbCiAgICAgICAgICAicnVuIiwKICAgICAgICAgICItLXJtIiwKICAgICAgICAgICItLWludGVyYWN0aXZlIiwKICAgICAgICAgICItZSBBV1NfUFJPRklMRT1bVGhlIEFXUyBQcm9maWxlIE5hbWVdIiwKICAgICAgICAgICJhd3NsYWJzL2Nsb3Vkd2F0Y2gtbWNwLXNlcnZlcjpsYXRlc3QiCiAgICAgICAgXSwKICAgICAgICAiZW52Ijoge30sCiAgICAgICAgImRpc2FibGVkIjogZmFsc2UsCiAgICAgICAgImF1dG9BcHByb3ZlIjogW10KfQ==)

#### Docker イメージを使用した MCP 設定 (Kiro, Cline) {#mcp-config-using-docker-imagekiro-cline}
```json
  {
    "mcpServers": {
      "awslabs.cloudwatch-mcp-server": {
        "command": "docker",
        "args": [
          "run",
          "--rm",
          "--interactive",
          "-v",
          "~/.aws:/root/.aws",
          "-e",
          "AWS_PROFILE=[The AWS Profile Name to use for AWS access]",
          "awslabs/cloudwatch-mcp-server:latest"
        ],
        "env": {},
        "disabled": false,
        "autoApprove": []
      }
    }
  }
```
認証情報プロファイルの作成と管理については、[AWS ドキュメント](https://docs.aws.amazon.com/cli/v1/userguide/cli-configure-files.html)を参照してください

## スキル {#skills}

この MCP サーバーには、ドメインの専門知識を AI エージェント向けの構造化されたワークフローとしてまとめた、再利用可能な調査スキルが含まれています。

| スキル | 説明 | セットアップガイド |
|-------|-------------|-------------|
| [AgentCore Investigation](https://github.com/awslabs/mcp/blob/main/src/cloudwatch-mcp-server/skills/agentcore-investigation/SKILL.md) | Bedrock AgentCore ランタイムセッションを調査します — セッション/トレース ID の解決、OTEL スパンのクエリ、ノイズのフィルタリング、タイムラインの構築 | [Kiro CLI セットアップ](https://github.com/awslabs/mcp/blob/main/src/cloudwatch-mcp-server/skills/agentcore-investigation/kiro-skill-setup.md) |

スキルは、エージェントが従うことのできる事前構築済みの調査パイプラインを提供します。スキル定義（`SKILL.md`）、リファレンスドキュメント、MCP サーバー設定が含まれます。

詳細は [skills ディレクトリ](https://github.com/awslabs/mcp/tree/main/src/cloudwatch-mcp-server/skills)を参照してください。

## コントリビューション {#contributing}

コントリビューションを歓迎します！ガイドラインについては、モノレポのルートにある [CONTRIBUTING.md](https://github.com/awslabs/mcp/blob/main/CONTRIBUTING.md) を参照してください。

## フィードバックと問題報告 {#feedback-and-issues}

皆さまからのフィードバックをお待ちしています！フィードバック、機能リクエスト、バグは、タイトルに `cloudwatch-mcp-server` というプレフィックスを付けて [GitHub issues](https://github.com/awslabs/mcp/issues) に投稿してください。
