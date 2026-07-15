---
title: "セキュリティエージェント MCPサーバー"
---

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-yellow.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

**AWS Security Agent** 向けの AWS Labs Model Context Protocol (MCP) サーバーです。自動化されたセキュリティスキャンとペネトレーションテストを提供します。

この MCP サーバーは AWS Security Agent サービスへのフルアクセスを提供し、開発者がソースコードの脆弱性スキャン、稼働中のアプリケーションに対するペネトレーションテストの実行、インテグレーションの管理、自動生成された修正の適用を、MCP 互換の任意のクライアントからすべて行えるようにします。

## 機能 {#features}

- **コードセキュリティスキャン** — ソースコードの zip 化、アップロード、スキャンを行い、修正を含む検出結果を取得
- **ペネトレーションテスト** — ターゲットドメインを介して稼働中のアプリケーションをテスト
- **フル API アクセス** — `call_api` ツールですべての SecurityAgent の操作を公開
- **自動プロビジョニング** — 初回利用時にエージェントスペースと IAM サービスロールを作成
- **.gitignore の尊重** — パッケージングから無視対象ファイルを除外

## 前提条件 {#prerequisites}

1. [uv](https://docs.astral.sh/uv/getting-started/installation/) がインストールされていること
2. Python 3.10 以上（`uv python install 3.10`）
3. AWS 認証情報が設定されていること（`aws configure`、SSO、または環境変数を使用）

## インストール {#installation}

### uvx を使用する場合（推奨） {#using-uvx-recommended}

```json
{
  "mcpServers": {
    "awslabs.security-agent-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.security-agent-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

### Docker を使用する場合 {#using-docker}

```json
{
  "mcpServers": {
    "awslabs.security-agent-mcp-server": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "AWS_REGION=us-east-1",
        "-e", "AWS_ACCESS_KEY_ID",
        "-e", "AWS_SECRET_ACCESS_KEY",
        "-e", "AWS_SESSION_TOKEN",
        "awslabs/security-agent-mcp-server:latest"
      ]
    }
  }
}
```

## 環境変数 {#environment-variables}

| 変数 | 説明 | デフォルト |
|----------|-------------|---------|
| `AWS_REGION` | SecurityAgent API 呼び出しに使用する AWS リージョン | `us-east-1` |
| `AWS_PROFILE` | AWS 認証情報プロファイル名 | デフォルトプロファイル |
| `FASTMCP_LOG_LEVEL` | ログレベル（DEBUG、INFO、WARNING、ERROR） | `WARNING` |

### 利用可能なリージョン {#available-regions}

利用可能なリージョンについては [AWS ドキュメント](https://docs.aws.amazon.com/securityagent/latest/userguide/resilience.html) を参照してください。

## 利用可能なツール {#available-tools}

### セットアップ {#setup}

| ツール | 説明 |
|------|-------------|
| `setup_check` | 前提条件（認証情報、エージェントスペース、ロール）を検証 |
| `setup` | エージェントスペースと IAM サービスロールを作成または再利用 |

### コードレビュー（オーケストレーション） {#code-review-orchestrated}

| ツール | 説明 |
|------|-------------|
| `start_security_scan` | コードを zip 化し、S3 にアップロードし、レビューを作成してスキャンを開始します。scan_id を返します。 |
| `get_scan_status` | スキャンの進行状況をポーリング |
| `get_scan_findings` | 完了したスキャンから検出結果を取得 |
| `list_scans` | 追跡中のスキャンを一覧表示 |
| `stop_scan` | 実行中のスキャンをキャンセル |

### 修正 {#remediation}

| ツール | 説明 |
|------|-------------|

### フル API アクセス {#full-api-access}

| ツール | 説明 |
|------|-------------|
| `call_api` | 任意の SecurityAgent API 操作を呼び出します（ペネトレーションテスト、ターゲットドメイン、インテグレーション、アーティファクトなど） |
| `get_api_guide` | 利用可能なすべての操作を動的に一覧表示 + ドキュメントリンク |

## 使用フロー {#usage-flows}

### コードレビュー（ソーススキャン） {#code-review-source-scan}

```
1. setup_check()              → verify readiness
2. setup()                    → provision resources (one-time)
3. start_security_scan(path=".")
4. get_scan_status()          → poll until COMPLETED
5. get_scan_findings()        → retrieve findings
```

### ペネトレーションテスト {#penetration-test}

```
1. setup_check() → setup()   → one-time
2. call_api("CreateTargetDomain", {targetDomainName, verificationMethod})
3. call_api("VerifyTargetDomain", {targetDomainId})
4. call_api("CreatePentest", {agentSpaceId, title, assets: {endpoints: [...]}, serviceRole})
5. call_api("StartPentestJob", {agentSpaceId, pentestId})
6. Poll: call_api("BatchGetPentestJobs", {agentSpaceId, pentestJobIds})
7. call_api("ListFindings", {agentSpaceId, pentestJobId})
```

### 任意の操作 {#any-operation}

```
1. get_api_guide()            → see all operations + docs link
2. call_api(operation, params) → execute
```

## 必要な IAM 権限 {#required-iam-permissions}

以下の権限は **お使いの AWS 認証情報**（MCP サーバーを実行するアイデンティティ）に必要です。

### セットアップ用（一度のみ） {#for-setup-one-time}
- `iam:CreateRole`、`iam:PutRolePolicy`（新しいサービスロールを作成する場合）
- `s3:CreateBucket`、`s3:PutPublicAccessBlock`、`s3:PutLifecycleConfiguration`（新しいバケットを作成する場合）
- `sts:GetCallerIdentity`
- `securityagent:CreateAgentSpace`、`securityagent:UpdateAgentSpace`
- `securityagent:ListAgentSpaces`、`securityagent:BatchGetAgentSpaces`

### コードスキャン用 {#for-code-scanning}
- `s3:PutObject`
- `securityagent:CreateCodeReview`、`securityagent:StartCodeReviewJob`
- `securityagent:BatchGetCodeReviewJobs`、`securityagent:StopCodeReviewJob`
- `securityagent:ListFindings`、`securityagent:BatchGetFindings`
- `securityagent:StartCodeRemediation`、`securityagent:BatchDeleteCodeReviews`

### ペネトレーションテストおよびその他の操作用 {#for-pentesting-and-other-operations}

ユースケースに応じて必要な SecurityAgent 権限を追加してください。利用可能なアクションの詳細については [How AWS Security Agent works with IAM](https://docs.aws.amazon.com/securityagent/latest/userguide/security_iam_service-with-iam.html) を参照してください。

## サービスロール {#service-role}

セットアップ時に、サーバーは IAM サービスロール `SecurityAgentScanRole` を作成します（まだ存在しない場合）。エージェントスペースに既存のロールが見つかった場合は、その権限を検証したうえで再利用できます。

このサービスロールは、アップロードされたコードを読み取るために SecurityAgent サービスによって引き受けられます。

- **信頼ポリシー**: `securityagent.amazonaws.com` サービスプリンシパル
- **権限**: スキャンバケットに対する S3 読み取り、CloudWatch Logs への書き込み

> **Note**: スキャン対象のソースコードを一時的に保存するために S3 バケットが使用されます。MCP サーバーは自身が作成したバケットに 30 日間のライフサイクルポリシーを設定し、アップロードされたコンテンツは自動的に削除されます。独自のバケットを使用する場合は、ストレージコストを管理するためにライフサイクルルールの追加を検討してください。

## コントリビューション {#contributing}

コントリビューションを歓迎します。ガイドラインについては、メインリポジトリの [CONTRIBUTING.md](https://github.com/awslabs/mcp/blob/main/CONTRIBUTING.md) を参照してください。

## ライセンス {#license}

このプロジェクトは Apache License 2.0 の下でライセンスされています。詳細については [LICENSE](https://github.com/awslabs/mcp/blob/main/src/security-agent-mcp-server/LICENSE) ファイルを参照してください。
