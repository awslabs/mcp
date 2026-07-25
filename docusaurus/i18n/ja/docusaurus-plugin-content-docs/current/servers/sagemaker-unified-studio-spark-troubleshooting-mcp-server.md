---
title: "Spark トラブルシューティングとコードレコメンデーション向けの Amazon SageMaker Unified Studio MCP"
---

Amazon EMR、AWS Glue、Amazon SageMaker Notebooks 上の Apache Spark アプリケーションのトラブルシューティングを行うための専門的なツールを提供する、フルマネージドのリモート MCP サーバーです。このサーバーは、対話型 AI 機能、自動化されたワークロード分析、インテリジェントなコード推奨を通じて、トラブルシューティングのプロセスを簡素化します。

**重要な注意事項**: 現時点では、すべての MCP クライアントがリモートサーバーをサポートしているわけではありません。このサーバーを使用するには、お使いのクライアントがリモート MCP サーバーをサポートしているか、適切なプロキシ構成があることを確認してください。

## 主な機能とケイパビリティ {#key-features--capabilities}

- **インテリジェントな障害分析**: Spark のイベントログ、エラーメッセージ、リソース使用状況を自動的に分析し、メモリの問題、設定エラー、コードのバグなど、正確な問題箇所を特定します
- **マルチプラットフォームのサポート**: Amazon EMR on EC2、EMR Serverless、AWS Glue、Amazon SageMaker Notebooks にまたがる PySpark および Scala アプリケーションのトラブルシューティングを行います
- **自動化された特徴抽出**: プラットフォーム固有の Spark History Server（EMR、Glue、EMR-Serverless）に接続し、包括的なコンテキストを抽出します
- **GenAI による根本原因分析**: AI モデルと Spark ナレッジベースを活用して特徴を相関付け、パフォーマンス問題や障害の根本原因を特定します
- **コード推奨エンジン**: 具体的な例を交えて、実行可能なコードの修正、設定の調整、アーキテクチャの改善を提供します
- **自然言語インターフェース**: 対話型のプロンプトを使用して、トラブルシューティング分析とコード推奨をリクエストできます

## アーキテクチャ {#architecture}

トラブルシューティングエージェントは 3 つの主要コンポーネントで構成されます: 対話に使用する開発環境内の MCP 互換 AI アシスタント、クライアントと AWS サービス間の安全な通信と認証を担う [MCP Proxy for AWS](https://github.com/aws/mcp-proxy-for-aws)、そして Amazon EMR、AWS Glue、Amazon SageMaker Notebooks 向けの専門的な Spark トラブルシューティングツールを提供する Amazon SageMaker Unified Studio リモート MCP サーバーです。次の図は、AI アシスタントを通じて Amazon SageMaker Unified Studio リモート MCP サーバーとやり取りする流れを示しています。

![img](https://docs.aws.amazon.com/images/emr/latest/ReleaseGuide/images/spark-troubleshooting-agent-architecture.png)

AI アシスタントは、MCP サーバーが提供する専門的なツールを使用し、以下のステップに従ってトラブルシューティングのプロセスをオーケストレーションします:

- **特徴抽出とコンテキスト構築**: Spark History Server のログ、設定、エラートレースなど、Spark アプリケーションのテレメトリデータを自動的に収集・分析します。主要なパフォーマンスメトリクス、リソース使用率のパターン、障害のシグネチャを抽出します。

- **GenAI 根本原因アナライザーと推奨エンジン**: AI モデルと Spark ナレッジベースを活用して、抽出した特徴を相関付け、パフォーマンス問題や障害の根本原因を特定します。アプリケーション実行の問題に関する診断的なインサイトと分析を提供します。

- **GenAI Spark コード推奨**: 根本原因分析に基づいて、既存のコードパターンを分析し、修正が必要な非効率な操作を特定します。具体的なコードの修正、設定の調整、アーキテクチャの改善を含む、実行可能な推奨事項を提供します。

### サポートされているプラットフォームと言語 {#supported-platforms--languages}

- **言語**: Python（PySpark）および Scala Spark アプリケーション
- **対象プラットフォーム**:
    - Amazon EMR on EC2
    - Amazon EMR Serverless
    - AWS Glue
    - Amazon SageMaker Notebooks

### データソースの統合 {#data-source-integration}

- **EMR on EC2**: クラスター分析のために [EMR Persistent UI](https://docs.aws.amazon.com/emr/latest/ManagementGuide/app-history-spark-UI.html) に接続します
- **AWS Glue**: ジョブ分析のために Glue Studio の [Spark UI](https://docs.aws.amazon.com/glue/latest/dg/monitor-spark-ui-jobs.html) からコンテキストを構築します
- **EMR Serverless**: ジョブ実行の分析のために EMR-Serverless の [Spark History Server](https://docs.aws.amazon.com/emr-serverless/latest/APIReference/API_GetDashboardForJobRun.html) に接続します

## 設定 {#configuration}

Apache Spark トラブルシューティングエージェントの MCP サーバーは、任意の MCP クライアントで使用できるように設定できます。

**Kiro CLI の設定例:**

コードのトラブルシューティングには、以下を追加できます。
```json
{
    "mcpServers": {
    "sagemaker-unified-studio-mcp-troubleshooting": {
        "type": "stdio",
        "command": "uvx",
        "args": [
        "mcp-proxy-for-aws@latest",
        "https://sagemaker-unified-studio-mcp.us-east-1.api.aws/spark-troubleshooting/mcp",
        "--service",
        "sagemaker-unified-studio-mcp",
        "--profile",
        "smus-mcp-profile",
        "--region",
        "us-east-1",
        "--read-timeout",
        "180"
        ],
        "timeout": 180000,
        "disabled": false
    }
    }
}
```

コード推奨には、さらに以下を追加できます。

```json
{
    "sagemaker-unified-studio-mcp-code-rec": {
    "type": "stdio",
    "command": "uvx",
    "args": [
        "mcp-proxy-for-aws@latest",
        "https://sagemaker-unified-studio-mcp.us-east-1.api.aws/spark-code-recommendation/mcp",
        "--service",
        "sagemaker-unified-studio-mcp",
        "--profile",
        "smus-mcp-profile",
        "--region",
        "us-east-1",
        "--read-timeout",
        "180"
    ],
    "timeout": 180000,
    "disabled": false
    }
}
```

## セットアップとインストール {#setup--installation}

### CloudFormation スタックのデプロイ {#deploy-cloudformation-stack}

お使いのリージョンに応じた適切な **Launch Stack** ボタンを選択して、必要なリソースをデプロイします。完全な一覧については [Setup Documentation](https://docs.aws.amazon.com/emr/latest/ReleaseGuide/spark-troubleshooting-agent-setup.html) を参照してください。

### ローカル環境と AWS CLI プロファイルのセットアップ {#setup-local-environment-and-aws-cli-profile}

CloudFormation の出力から 1 行の手順をコピーし、ローカルで実行します。

```bash
export SMUS_MCP_REGION=us-east-1 && export IAM_ROLE=arn:aws:iam::111122223333:role/spark-troubleshooting-role-xxxxxx
```

```bash
aws configure set profile.smus-mcp-profile.role_arn ${IAM_ROLE}
aws configure set profile.smus-mcp-profile.source_profile default
aws configure set profile.smus-mcp-profile.region ${SMUS_MCP_REGION}
```

### ワンクリックインストール {#one-click-installation}


|   IDE   |       Spark トラブルシューティングをインストール | Spark コード推奨をインストール |
| :-----: |  :-----: | :------: |
| Kiro IDE  | [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=spark-troubleshooting&config=%7B%22type%22%3A%20%22stdio%22%2C%20%22command%22%3A%20%22uvx%22%2C%20%22args%22%3A%20%5B%22mcp-proxy-for-aws%40latest%22%2C%20%22https%3A//sagemaker-unified-studio-mcp.us-east-1.api.aws/spark-troubleshooting/mcp%22%2C%20%22--service%22%2C%20%22sagemaker-unified-studio-mcp%22%2C%20%22--profile%22%2C%20%22smus-mcp-profile%22%2C%20%22--region%22%2C%20%22us-east-1%22%2C%20%22--read-timeout%22%2C%20%22180%22%5D%2C%20%22timeout%22%3A%20180000%7D)  | [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=spark-code-rec&config=%7B%22type%22%3A%20%22stdio%22%2C%20%22command%22%3A%20%22uvx%22%2C%20%22args%22%3A%20%5B%22mcp-proxy-for-aws%40latest%22%2C%20%22https%3A//sagemaker-unified-studio-mcp.us-east-1.api.aws/spark-code-recommendation/mcp%22%2C%20%22--service%22%2C%20%22sagemaker-unified-studio-mcp%22%2C%20%22--profile%22%2C%20%22smus-mcp-profile%22%2C%20%22--region%22%2C%20%22us-east-1%22%2C%20%22--read-timeout%22%2C%20%22180%22%5D%2C%20%22timeout%22%3A%20180000%7D) |
| VS Code  |  [![Install Troubleshooting VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900)](vscode:mcp/install?%7B%22name%22%3A%22sagemaker-unified-studio-mcp-troubleshooting%22%2C%22type%22%3A%22stdio%22%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22mcp-proxy-for-aws%40latest%22%2C%22https%3A%2F%2Fsagemaker-unified-studio-mcp.us-east-1.api.aws%2Fspark-troubleshooting%2Fmcp%22%2C%22--service%22%2C%22sagemaker-unified-studio-mcp%22%2C%22--profile%22%2C%22smus-mcp-profile%22%2C%22--region%22%2C%22us-east-1%22%2C%22--read-timeout%22%2C%22180%22%5D%7D) | [![Install Code Recommendation in VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900)](vscode:mcp/install?%7B%22name%22%3A%22sagemaker-unified-studio-mcp-code-rec%22%2C%22type%22%3A%22stdio%22%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22mcp-proxy-for-aws%40latest%22%2C%22https%3A%2F%2Fsagemaker-unified-studio-mcp.us-east-1.api.aws%2Fspark-code-recommendation%2Fmcp%22%2C%22--service%22%2C%22sagemaker-unified-studio-mcp%22%2C%22--profile%22%2C%22smus-mcp-profile%22%2C%22--region%22%2C%22us-east-1%22%2C%22--read-timeout%22%2C%22180%22%5D%7D) |

### MCP クライアントの設定（Kiro CLI の例） {#configure-mcp-client-kiro-cli-example}

```bash
# Add Spark Troubleshooting MCP Server
kiro-cli-chat mcp add \
    --name "sagemaker-unified-studio-mcp-troubleshooting" \
    --command "uvx" \
    --args "[\"mcp-proxy-for-aws@latest\",\"https://sagemaker-unified-studio-mcp.${SMUS_MCP_REGION}.api.aws/spark-troubleshooting/mcp\", \"--service\", \"sagemaker-unified-studio-mcp\", \"--profile\", \"smus-mcp-profile\", \"--region\", \"${SMUS_MCP_REGION}\", \"--read-timeout\", \"180\"]" \
    --timeout 180000 \
    --scope global

# Add Spark Code Recommendation MCP Server
kiro-cli-chat mcp add \
    --name "sagemaker-unified-studio-mcp-code-rec" \
    --command "uvx" \
    --args "[\"mcp-proxy-for-aws@latest\",\"https://sagemaker-unified-studio-mcp.${SMUS_MCP_REGION}.api.aws/spark-code-recommendation/mcp\", \"--service\", \"sagemaker-unified-studio-mcp\", \"--profile\", \"smus-mcp-profile\", \"--region\", \"${SMUS_MCP_REGION}\", \"--read-timeout\", \"180\"]" \
    --timeout 180000 \
    --scope global
```

## 使用例 {#usage-examples}

### 1. Spark ジョブ実行の失敗のトラブルシューティング {#1-troubleshoot-spark-job-execution-failures}

**EMR on EC2 のトラブルシューティング:**
```
Troubleshoot my EMR-EC2 step with id s-xxxxxxxxxxxx on cluster j-xxxxxxxxxxxxx
```

**Glue ジョブのトラブルシューティング:**
```
Troubleshoot my Glue job with job run id jr_xxxxxxxxxxxxxxxxxxxxxxxxxxxx and job name test_job
```

**EMR Serverless のトラブルシューティング:**
```
Troubleshoot my EMR-Serverless job run with application id 00xxxxxxxx and job run id 00xxxxxxxx
```

### 2. コード修正の推奨のリクエスト {#2-request-code-fix-recommendations}

**EMR on EC2 のコード推奨:**
```
Recommend code fix for my EMR-EC2 step with id s-STEP_ID on cluster j-CLUSTER_ID
```

**Glue ジョブのコード推奨:**
```
Recommend code fix for my Glue job with job run id jr_JOB_RUN_ID and job name test_job
```

## 制限事項と要件 {#limitations--requirements}

### サポートされているワークロードの状態 {#supported-workload-states}
- **失敗したワークロードのみ**: ツールは失敗した Spark ワークロードに対する応答のみをサポートします

### プラットフォーム固有の考慮事項 {#platform-specific-considerations}

- **EMR Persistent UI**: Amazon EMR-EC2 のワークロードを分析する際、ツールは EMR Persistent UI に接続します。[制限事項](https://docs.aws.amazon.com/emr/latest/ManagementGuide/app-history-spark-UI.html#app-history-spark-UI-limitations) を参照してください
- **Glue Studio Spark UI**: Amazon S3 の Spark イベントログを解析して情報を取得します。イベントログの最大許容サイズ: 512 MB（ローリングログの場合は 2 GB）
- **コード推奨**: PySpark アプリケーションについては、Amazon EMR-EC2 および AWS Glue のワークロードでのみサポートされます
- **リージョナルなリソース**: エージェントはリージョナルであり、そのリージョン内の基盤となる EMR リソースを使用します。クロスリージョンのトラブルシューティングはサポートされていません

## よくある問題のトラブルシューティング {#troubleshooting-common-issues}

### MCP サーバーの読み込みに失敗する {#mcp-server-failed-to-load}
- MCP の設定が正しくセットアップされているか確認します
- カンマ、引用符、括弧の欠落など、JSON 構文を検証します
- ローカルの AWS 認証情報と IAM ロールのポリシー設定を確認します
- `/mcp` を実行してサーバーの可用性を確認します（Kiro CLI）

### ツールの読み込みが遅い {#slow-tool-loading}
- ツールは初回起動時に読み込みに数秒かかることがあります
- ツールが表示されない場合は、チャットを再起動してみてください
- `/tools` コマンドを実行してツールの可用性を確認します

### ツール呼び出しエラー {#tool-invocation-errors}
- **Throttling Error**: 数秒待ってから再試行してください
- **AccessDeniedException**: 権限の問題を確認して修正します
- **InvalidInputException**: ツールの入力パラメータを修正します
- **ResourceNotFoundException**: リソース参照のための入力パラメータを修正します
- **Internal Service Exception**: 分析 ID を記録し、AWS サポートにお問い合わせください

## データの使用 {#data-usage}

このサーバーは、トラブルシューティングの推奨事項を提供するために、Spark アプリケーションのログと設定ファイルを処理します。機密データが永続的に保存されることはなく、すべての処理は AWS のデータ保護基準に従います。

## セキュリティのベストプラクティス {#security-best-practices}

- **信頼設定**: すべてのツール呼び出しに対して、デフォルトで「信頼（trust）」設定を有効にしないでください
- **バージョン管理**: コード推奨を受け入れる際は、git でバージョン管理されたビルド環境で操作してください
- **レビュープロセス**: どのような変更が行われるかを理解するために、各ツールの実行をレビューしてください
- **コードの変更**: すべてのコードの修正と推奨事項に対する完全なコントロールを維持してください

## FAQ {#faqs}

### 1. どのような種類の Spark アプリケーションがサポートされていますか? {#1-what-types-of-spark-applications-are-supported}
エージェントは、Amazon EMR on EC2、EMR Serverless、AWS Glue、Amazon SageMaker Notebooks 上で実行される PySpark と Scala Spark の両方のアプリケーションをサポートします。

### 2. Spark ジョブがまだ実行中の場合はどうなりますか? {#2-what-happens-if-my-spark-job-is-still-running}
トラブルシューティングツールは、失敗した Spark ワークロードの分析のみをサポートします。

### 3. 成功したジョブに対してコード推奨を取得できますか? {#3-can-i-get-code-recommendations-for-successful-jobs}
コード推奨は主に失敗したワークロードの問題を修正することに重点を置いていますが、完全な障害分析がなくても、最適化のためのコードレベルの提案をリクエストできます。

### 4. エージェントはどのように Spark ログにアクセスしますか? {#4-how-does-the-agent-access-my-spark-logs}
エージェントは、プラットフォーム固有のインターフェースに接続します: EMR-EC2 の場合は EMR Persistent UI、AWS Glue の場合は Glue Studio Spark UI、EMR Serverless の場合は Spark History Server、そして S3/CloudWatch のログに接続し、必要なテレメトリデータを抽出します。

### 5. トラブルシューティングのプロセス中、データは安全ですか? {#5-is-my-data-secure-during-the-troubleshooting-process}
はい。すべての処理は AWS のデータ保護基準に従います。エージェントは、機密データを永続的に保存することなく、推奨事項を提供するためにログと設定を一時的に分析します。

### 6. 自動トラブルシューティングで問題が特定されない場合はどうすればよいですか? {#6-what-should-i-do-if-the-automated-troubleshooting-doesnt-identify-the-issue}
エージェントは詳細なエラー分析と修正案を提供します。問題が解決しない場合は、分析 ID とツールの応答を添えて AWS サポートにエスカレーションし、さらなるサポートを受けることができます。

詳細については、[AWS EMR Spark トラブルシューティングドキュメント](https://docs.aws.amazon.com/emr/latest/ReleaseGuide/spark-troubleshoot.html) を参照してください。
