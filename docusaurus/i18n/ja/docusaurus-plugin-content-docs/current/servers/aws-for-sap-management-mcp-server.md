---
title: "AWS Systems Manager for SAP MCPサーバー"
---

AWS Systems Manager for SAP 向けの AWS Labs Model Context Protocol (MCP) サーバーです。このサーバーにより、AI エージェントは AWS Systems Manager for SAP に登録された SAP アプリケーションを管理し、構成チェックを実行し、Amazon EventBridge Scheduler を介して定期的な操作をスケジュールできます。

## Instructions {#instructions}

この MCP サーバーを使用して、AWS Systems Manager for SAP に登録された SAP アプリケーションを管理します。SAP アプリケーションの一覧表示と検査、構成チェックの実行とレビュー、Amazon EventBridge Scheduler を介した定期的な操作（構成チェック、開始/停止）のスケジュールをサポートします。すべてのツールはマルチリージョンおよびマルチプロファイルの AWS アクセスをサポートします。

## Features {#features}

- SAP アプリケーション管理 — AWS Systems Manager for SAP に登録された SAP アプリケーション（HANA および SAP_ABAP）を一覧表示、検査、登録、開始、停止します。
- 構成チェック — 利用可能な構成チェックの種類を検出し、アプリケーションに対してチェックをトリガーし、サブチェックおよびルールレベルの結果を詳細に確認します。
- スケジューリング — 定期的な構成チェック、アプリケーションの開始、アプリケーションの停止操作のための EventBridge Scheduler スケジュールを作成、一覧表示、有効化/無効化、削除します。
- ヘルスサマリー — アプリケーションのステータス、コンポーネントの正常性、構成チェック、HANA ログバックアップのステータス、AWS Backup のステータス、CloudWatch メトリクスをカバーする、包括的な Markdown 形式のヘルスレポートを生成します。

## Prerequisites {#prerequisites}

1. [AWS Systems Manager for SAP](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-for-sap.html) が構成された AWS アカウント
2. この MCP サーバーは、LLM クライアントと同じホスト上でローカルにのみ実行できます。
3. AWS サービスへのアクセス権を持つ AWS 認証情報を設定する
   - 適切な権限を持つ AWS アカウントが必要です（下記の必要な権限を参照）
   - `aws configure` または環境変数で AWS 認証情報を設定します

## Available Tools {#available-tools}

### SAP Application Tools {#sap-application-tools}
* `list_applications` - AWS Systems Manager for SAP に登録されたすべての SAP アプリケーションを一覧表示します
* `get_application` - コンポーネントを含む特定の SAP アプリケーションの詳細なメタデータを取得します
* `get_component` - SAP アプリケーションの特定のコンポーネントの詳細な正常性ステータスを取得します
* `get_operation` - 非同期操作（登録、開始、停止）のステータスを取得します
* `register_application` - SAP アプリケーション（HANA または SAP_ABAP）を SSM for SAP に登録します
* `start_application` - SAP アプリケーションを開始します
* `stop_application` - オプションで EC2 のシャットダウンを伴って SAP アプリケーションを停止します

### Configuration Check Tools {#configuration-check-tools}
* `list_config_check_definitions` - 利用可能なすべての構成チェックの種類とメタデータを一覧表示します
* `start_config_checks` - 指定したアプリケーションに対して構成チェックをトリガーします
* `get_config_check_summary` - 最新の構成チェック結果のサマリーを取得します
* `get_config_check_operation` - 特定の構成チェック操作の詳細を取得します
* `list_sub_check_results` - 構成チェック操作のサブチェック結果を一覧表示します
* `list_sub_check_rule_results` - 特定のサブチェックのルール評価結果を一覧表示します

### Scheduling Tools {#scheduling-tools}
* `schedule_config_checks` - EventBridge Scheduler を介して定期的な構成チェックをスケジュールします
* `schedule_start_application` - SAP アプリケーションの自動開始をスケジュールします
* `schedule_stop_application` - SAP アプリケーションの自動停止をスケジュールします
* `list_app_schedules` - 特定のアプリケーションのすべての EventBridge Scheduler スケジュールを一覧表示します
* `delete_schedule` - EventBridge Scheduler スケジュールを削除します
* `update_schedule_state` - スケジュールを有効または無効にします
* `get_schedule_details` - 特定のスケジュールの詳細情報を取得します

### Health Summary Tools {#health-summary-tools}
* `get_sap_health_summary` - 1 つまたはすべての SAP アプリケーションについて、アプリケーション/コンポーネントのステータス、サブチェックおよびルール結果を含む構成チェック、HANA ログバックアップのステータス、AWS Backup のステータス、CloudWatch EC2 メトリクスを含む、包括的なヘルスサマリーを取得します
* `generate_health_report` - 1 つまたはすべての SAP アプリケーションについて、すべての正常性の側面をカバーする、詳細でダウンロード可能な Markdown ヘルスレポートを生成します

### Required IAM Permissions {#required-iam-permissions}

#### SSM for SAP {#ssm-for-sap}
* `ssm-sap:ListApplications`
* `ssm-sap:GetApplication`
* `ssm-sap:ListComponents`
* `ssm-sap:GetComponent`
* `ssm-sap:GetOperation`
* `ssm-sap:RegisterApplication`
* `ssm-sap:StartApplication`
* `ssm-sap:StopApplication`
* `ssm-sap:ListConfigurationCheckDefinitions`
* `ssm-sap:StartConfigurationChecks`
* `ssm-sap:ListConfigurationCheckOperations`
* `ssm-sap:GetConfigurationCheckOperation`
* `ssm-sap:ListSubCheckResults`
* `ssm-sap:ListSubCheckRuleResults`

#### EventBridge Scheduler (for scheduling tools) {#eventbridge-scheduler-for-scheduling-tools}
* `scheduler:CreateSchedule`
* `scheduler:GetSchedule`
* `scheduler:ListSchedules`
* `scheduler:DeleteSchedule`
* `scheduler:UpdateSchedule`

#### IAM (for scheduler role management) {#iam-for-scheduler-role-management}
* `iam:GetRole`
* `iam:CreateRole`
* `iam:AttachRolePolicy`
* `sts:GetCallerIdentity`

#### SSM (for health summary log backup and filesystem checks) {#ssm-for-health-summary-log-backup-and-filesystem-checks}
* `ssm:DescribeInstanceInformation`
* `ssm:SendCommand`
* `ssm:GetCommandInvocation`
* `ssm:ListCommands`

#### AWS Backup (for health summary backup status) {#aws-backup-for-health-summary-backup-status}
* `backup:ListBackupPlans`
* `backup:ListBackupJobs`

#### CloudWatch (for health summary EC2 metrics) {#cloudwatch-for-health-summary-ec2-metrics}
* `cloudwatch:GetMetricStatistics`
* `cloudwatch:ListMetrics`

## Installation {#installation}

### Option 1: Python (UVX) {#option-1-python-uvx}
#### Prerequisites {#prerequisites-1}
1. [Astral](https://docs.astral.sh/uv/getting-started/installation/) または [GitHub README](https://github.com/astral-sh/uv#installation) から `uv` をインストールします
2. `uv python install 3.10` を使用して Python をインストールします

#### MCP Config (Kiro, Cline) {#mcp-config-kiro-cline}
* Kiro の場合、MCP Config (~/.kiro/settings/mcp.json) を更新します
* Cline の場合、MCP タブから "Configure MCP Servers" オプションをクリックします
```json
{
  "mcpServers": {
    "awslabs.aws-for-sap-management-mcp-server": {
      "autoApprove": [],
      "disabled": false,
      "command": "uvx",
      "args": [
        "awslabs.aws-for-sap-management-mcp-server@latest"
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

### Windows Installation {#windows-installation}

Windows ユーザーの場合、MCP サーバーの設定形式は少し異なります。

```json
{
  "mcpServers": {
    "awslabs.aws-for-sap-management-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.aws-for-sap-management-mcp-server@latest",
        "awslabs.aws-for-sap-management-mcp-server.exe"
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

認証情報プロファイルの作成と管理については、[AWS ドキュメント](https://docs.aws.amazon.com/cli/v1/userguide/cli-configure-files.html) を参照してください

### Option 2: Docker Image {#option-2-docker-image}
#### Prerequisites {#prerequisites-2}
LLM クライアントと同じホスト上でローカルに docker イメージをビルドしてインストールします
1. [Docker](https://docs.docker.com/desktop/) をインストールします
2. `git clone https://github.com/awslabs/mcp.git`
3. サブディレクトリに移動します `cd src/aws-for-sap-management-mcp-server/`
4. `docker build -t awslabs/aws-for-sap-management-mcp-server:latest .` を実行します

#### MCP Config using Docker image (Kiro, Cline) {#mcp-config-using-docker-image-kiro-cline}
```json
{
  "mcpServers": {
    "awslabs.aws-for-sap-management-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "-v",
        "~/.aws:/root/.aws",
        "-e",
        "AWS_PROFILE=[The AWS Profile Name to use for AWS access]",
        "awslabs/aws-for-sap-management-mcp-server:latest"
      ],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

認証情報プロファイルの作成と管理については、[AWS ドキュメント](https://docs.aws.amazon.com/cli/v1/userguide/cli-configure-files.html) を参照してください

## Contributing {#contributing}

コントリビューションを歓迎します。ガイドラインについては、モノレポのルートにある [CONTRIBUTING.md](https://github.com/awslabs/mcp/blob/main/CONTRIBUTING.md) を参照してください。

## Feedback and Issues {#feedback-and-issues}

皆様のフィードバックを歓迎します。フィードバック、機能リクエスト、バグは、タイトルに `aws-for-sap-management-mcp-server` というプレフィックスを付けて [GitHub issues](https://github.com/awslabs/mcp/issues) に送信してください。
