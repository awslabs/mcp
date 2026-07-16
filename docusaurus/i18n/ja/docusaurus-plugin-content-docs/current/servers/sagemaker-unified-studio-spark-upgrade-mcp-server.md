---
title: Sparkアップグレード向けSageMaker Unified Studio MCP
---

Amazon EMR上のApache Sparkアプリケーションをアップグレードするための専門的なツールとガイダンスを提供する、フルマネージドのリモートMCPサーバーです。このサーバーは、自動分析、コード変換、検証機能を通じてSparkバージョンのアップグレードを加速します。

**重要な注意事項**: 現時点では、すべてのMCPクライアントがリモートサーバーをサポートしているわけではありません。このサーバーを使用するには、お使いのクライアントがリモートMCPサーバーをサポートしているか、適切なプロキシ構成があることを確認してください。

## 主な機能とケイパビリティ {#key-features--capabilities}

- **プロジェクト分析と計画**: Sparkアプリケーションの構造、依存関係、API使用状況を詳細に分析し、リスク評価を含む包括的でステップバイステップのアップグレード計画を生成します
- **自動コード変換**: バージョン互換性のためにPySparkおよびScalaコードを自動的に更新し、APIの変更や非推奨化に対応します
- **依存関係とビルドの管理**: ターゲットのSparkバージョンに合わせてMaven/SBT/pipの依存関係とビルド環境を更新・管理し、エラーを反復的に解決します
- **包括的なテストと検証**: ユニットテスト、統合テスト、EMR検証ジョブを実行し、アップグレード後のアプリケーションをターゲットのSparkバージョンに対して検証します
- **データ品質の検証**: 検証ルールにより、アップグレードプロセス全体を通じてデータの整合性を確保します
- **EMR統合とモニタリング**: Amazon EMR on EC2およびAmazon EMR Serverlessの両方で、アップグレード検証のためのEMRジョブを送信・監視します
- **可観測性と進捗の追跡**: アップグレードの進捗を追跡し、結果を分析し、アップグレードプロセス全体を通じて詳細なインサイトを提供します


## アーキテクチャ {#architecture}
アップグレードエージェントは3つの主要コンポーネントで構成されます: 対話に使用する開発環境内の任意のMCP互換AIアシスタント、クライアントとMCPサーバー間の安全な通信を担う [MCP Proxy for AWS](https://github.com/aws/mcp-proxy-for-aws)、そしてAmazon EMR向けの専門的なSparkアップグレードツールを提供するAmazon SageMaker Unified StudioマネージドMCPサーバーです。次の図は、AIアシスタントを通じてAmazon SageMaker Unified StudioマネージドMCPサーバーとやり取りする流れを示しています。

![img](https://docs.aws.amazon.com/images/emr/latest/ReleaseGuide/images/SparkUpgradeIntroduction.png)


AIアシスタントは、MCPサーバーが提供する専門的なツールを使用し、以下のステップに従ってアップグレードをオーケストレーションします:

- **計画**: エージェントがプロジェクト構造を分析し、Sparkアップグレードプロセス全体を導くアップグレード計画を生成または改訂します。

- **コンパイルとビルド**: エージェントがビルド環境と依存関係を更新し、プロジェクトをコンパイルし、ビルドおよびテストの失敗を反復的に修正します。

- **Sparkコード編集ツール**: Sparkバージョンの非互換性を解消するための的を絞ったコード更新を適用し、ビルド時と実行時の両方のエラーを修正します。

- **実行と検証**: リモート検証ジョブをEMRに送信し、実行とログを監視し、実行時およびデータ品質の問題を反復的に修正します。

- **可観測性**: EMRの可観測性ツールを使用してアップグレードの進捗を追跡し、ユーザーはいつでもアップグレードの分析結果とステータスを確認できます。

各ステップの主要なツールの一覧は [Using Spark Upgrade Tools](https://docs.aws.amazon.com/emr/latest/ReleaseGuide/emr-spark-upgrade-agent-tools.html) を参照してください。

### サポートされているアップグレードパス {#supported-upgrade-paths}
- Apache Sparkのバージョン2.4から3.5へのアップグレードをサポートしています。対応するデプロイモードのマッピングは以下のとおりです
- **EMRリリースのアップグレード**:
    - EMR-EC2の場合
        - ソースバージョン: EMR 5.20.0以降
        - ターゲットバージョン: EMR 7.12.0以前 (EMR 5.20.0より新しいバージョンである必要があります)

    - EMR-Serverlessの場合
        - ソースバージョン: EMR Serverless 6.6.0以降
        - ターゲットバージョン: EMR Serverless 7.12.0以前




## 設定 {#configuration}
**注:** 具体的な設定形式はMCPクライアントによって異なります。

### ワンクリックインストール {#one-click-installation}


|   IDE   |       Spark Upgradeをインストール |
| :-----: |   :------: |
| Kiro IDE  | [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=spark-upgrade&config=%7B%22type%22%3A%20%22stdio%22%2C%20%22command%22%3A%20%22uvx%22%2C%20%22args%22%3A%20%5B%22mcp-proxy-for-aws%40latest%22%2C%20%22https%3A//sagemaker-unified-studio-mcp.us-east-1.api.aws/spark-upgrade/mcp%22%2C%20%22--service%22%2C%20%22sagemaker-unified-studio-mcp%22%2C%20%22--profile%22%2C%20%22spark-upgrade-profile%22%2C%20%22--region%22%2C%20%22us-east-1%22%2C%20%22--read-timeout%22%2C%20%22180%22%5D%2C%20%22timeout%22%3A%20180000%7D) |
| VS Code  |  [![Install in VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900)](vscode:mcp/install?%7B%22name%22%3A%22spark-upgrade%22%2C%22type%22%3A%22stdio%22%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22mcp-proxy-for-aws%40latest%22%2C%22https%3A%2F%2Fsagemaker-unified-studio-mcp.us-east-1.api.aws%2Fspark-upgrade%2Fmcp%22%2C%22--service%22%2C%22sagemaker-unified-studio-mcp%22%2C%22--profile%22%2C%22spark-upgrade-profile%22%2C%22--region%22%2C%22us-east-1%22%2C%22--read-timeout%22%2C%22180%22%5D%7D)|

**Kiro CLI**

```json
{
  "mcpServers": {
    "spark-upgrade": {
      "type": "stdio",
      "command": "uvx",
      "args": [
        "mcp-proxy-for-aws@latest",
        "https://sagemaker-unified-studio-mcp.us-east-1.api.aws/spark-upgrade/mcp",
        "--service",
        "sagemaker-unified-studio-mcp",
        "--profile",
        "spark-upgrade-profile",
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

Kiro、Cline、GitHub CoPilotなど各種MCPクライアントの設定ガイダンスについては、[Using the Upgrade Agent](https://docs.aws.amazon.com/emr/latest/ReleaseGuide/emr-spark-upgrade-agent-using.html) を参照してください。

## 使用例 {#usage-examples}

1. **Sparkアップグレード分析の実行**:
  - EMR-S
    ```
    Help me upgrade my spark application in <project-path> from EMR-EC2 version 6.0.0 to 7.12.0. you can use EMR-S Application id xxg017hmd2agxxxx and execution role <role name> to run the validation and s3 paths s3://s3-staging-path to store updated application artifacts.
    ```
  - EMR-EC2
    ```
    Upgrade my Spark application <local-project-path> from EMR-S version 6.6.0 to 7.12.0. Use EMR-EC2 Cluster j-PPXXXXTG09XX to run the validation and s3 paths s3://s3-staging-path to store updated application artifacts.
    ```

2. **分析の一覧表示**:
   ```
   Provide me a list of analyses performed by the spark agent
   ```

3. **分析の説明**:
   ```
   can you explain the analysis 439715b3-xxxx-42a6-xxxx-3bf7f1fxxxx
   ```
4. **他の分析への計画の再利用**:
    ```
    Use my upgrade_plan spark_upgrade_plan_xxx.json to upgrade my project in <project-path>
    ```

## AWS認証 {#aws-authentication}

### ステップ1: AWS CLIプロファイルの設定 {#step-1-configure-aws-cli-profile}
```
aws configure set profile.spark-upgrade-profile.role_arn ${IAM_ROLE}
aws configure set profile.spark-upgrade-profile.source_profile <AWS CLI Profile to assume the IAM role - ex: default>
aws configure set profile.spark-upgrade-profile.region ${SMUS_MCP_REGION}
```
### ステップ2: Kiro CLIを使用している場合は、次のコマンドでMCP設定を追加します {#step-2-if-you-are-using-kiro-cli-use-the-following-command-to-add-the-mcp-configuration}
```
kiro-cli-chat mcp add \
    --name "spark-upgrade" \
    --command "uvx" \
    --args "[\"mcp-proxy-for-aws@latest\",\"https://sagemaker-unified-studio-mcp.${SMUS_MCP_REGION}.api.aws/spark-upgrade/mcp\", \"--service\", \"sagemaker-unified-studio-mcp\", \"--profile\", \"spark-upgrade-profile\", \"--region\", \"${SMUS_MCP_REGION}\", \"--read-timeout\", \"180\"]" \
    --timeout 180000\
    --scope global
```
詳細については、[AWS docs](https://docs.aws.amazon.com/emr/latest/ReleaseGuide/emr-spark-upgrade-agent-setup.html) を参照してください
## データの使用 {#data-usage}

このサーバーは、アップグレードの推奨事項を提供するためにコードと設定ファイルを処理します。機密データが永続的に保存されることはなく、すべての処理はAWSのデータ保護基準に従います。

## FAQ {#faqs}

### 1. どのSparkバージョンがサポートされていますか? {#1-which-spark-versions-are-supported}
- EMR-EC2の場合
    - ソースバージョン: EMR 5.20.0以降
    - ターゲットバージョン: EMR 7.12.0以前 (EMR 5.20.0より新しいバージョンである必要があります)

- EMR-Serverlessの場合
    - ソースバージョン: EMR Serverless 6.6.0以降
    - ターゲットバージョン: EMR Serverless 7.12.0以前



### 2. Scalaアプリケーションにも使用できますか? {#2-can-i-use-this-for-scala-applications}

はい。エージェントは、MavenおよびSBTビルドシステムを含め、PySparkとScala Sparkの両方のアプリケーションをサポートします

### 3. カスタムライブラリやUDFはどうなりますか? {#3-what-about-custom-libraries-and-udfs}

エージェントはカスタムの依存関係を分析し、ユーザー定義関数やサードパーティライブラリの更新に関するガイダンスを提供します。

### 4. データ品質の検証はどのように機能しますか? {#4-how-does-data-quality-validation-work}

エージェントは、検証ルールと統計分析を使用して、旧バージョンと新バージョンのSpark間の出力データを比較します。

### 5. アップグレードプロセスをカスタマイズできますか? {#5-can-i-customize-the-upgrade-process}

はい。要件に応じて、アップグレード計画の変更、特定の変換の除外、検証基準のカスタマイズが可能です。

### 6. 自動アップグレードが失敗した場合はどうなりますか? {#6-what-if-the-automated-upgrade-fails}

エージェントは詳細なエラー分析、修正案、フォールバック戦略を提供します。すべての変更に対する完全なコントロールはユーザーが保持します。
