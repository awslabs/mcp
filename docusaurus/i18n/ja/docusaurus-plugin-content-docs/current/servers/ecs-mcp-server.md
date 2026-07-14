---
title: "Amazon ECS MCPサーバー"
---

[![PyPI version](https://img.shields.io/pypi/v/awslabs.ecs-mcp-server.svg)](https://pypi.org/project/awslabs.ecs-mcp-server/)

アプリケーションのコンテナ化、Amazon Elastic Container Service (ECS) へのアプリケーションのデプロイ、ECSデプロイメントのトラブルシューティング、ECSリソースの管理を行うためのMCPサーバーです。このサーバーにより、AIアシスタントはAWS上のコンテナ化アプリケーションのライフサイクル全体をユーザーが管理できるよう支援します。

> **注:** AWSは、自動アップデート、IAM統合による一元化されたセキュリティ、CloudTrailによる包括的な監査ログ、そしてAWSの実績あるスケーラビリティと信頼性など、エンタープライズグレードの機能を提供するフルマネージド版のAmazon ECS MCPサーバーを提供しています。マネージドサービスを利用すれば、ローカルへのインストールやメンテナンスは不要になります。[マネージド版Amazon ECS MCPサーバーの詳細はこちら](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-mcp-introduction.html)。

## 機能 {#features}

- **コンテナ化ガイダンス**: Webアプリケーションのコンテナ化に関するベストプラクティスとガイダンスを提供します
- **ECS Express Modeデプロイメント**: インフラストラクチャの自動プロビジョニングを備えたECS Express Modeを使用して、コンテナ化アプリケーションをデプロイします
- **ECR統合**: ECRリポジトリの自動作成と、Dockerイメージのビルドおよび ECRへのプッシュを行います
- **ロードバランサー統合**: HTTPSサポート付きのApplication Load Balancer (ALB) を自動的に構成します
- **オートスケーリング**: CPU/メモリとスケーリングターゲットを設定可能な組み込みのオートスケーリングを提供します
- **Infrastructure as Code**: ECRおよびECSインフラストラクチャ用のCloudFormationテンプレートを生成・適用します
- **URL管理**: デプロイされたアプリケーションにすぐアクセスできるよう、パブリックALB URLを返します
- **サーキットブレーカー**: 自動ロールバック付きのデプロイメントサーキットブレーカーを実装します
- **Container Insights**: モニタリングのための拡張Container Insightsを有効化します
- **セキュリティベストプラクティス**: コンテナデプロイメントに対するAWSセキュリティベストプラクティスを実装します
- **リソース管理**: タスク定義、サービス、クラスター、タスクなどのECSリソースを一覧表示・確認します
- **AWSナレッジ統合**: 統合されたAWS Knowledge MCP Serverプロキシを通じて最新のAWSドキュメントにアクセスできます。これには、モデルが認識していない可能性のあるECSや新機能に関する知識が含まれます

お客様は `containerize_app` ツールを使用して、ベストプラクティスに沿ったアプリケーションのコンテナ化を行えます。`build_and_push_image_to_ecr` ツールはECRインフラストラクチャを作成し、Dockerイメージをプッシュします。`validate_ecs_express_mode_prerequisites` ツールは、デプロイ前に必要なIAMロールとイメージがすべて存在することを検証します。Express Modeのデプロイには、`ecs_resource_management` の `CreateExpressGatewayService` オペレーションを使用します。`wait_for_service_ready` ツールはデプロイの進行状況の追跡に役立ち、`delete_app` はExpress Modeデプロイメントの完全なクリーンアップを提供します。

お客様は `ecs_resource_management` ツールを使用して、ECSリソース(クラスター、サービス、タスク、タスク定義)の一覧表示や確認、ECRリソース(コンテナイメージ)へのアクセスを行えます。ECSのデプロイで問題が発生した場合は、`ecs_troubleshooting_tool` を使用して一般的な問題を診断・解決できます。

## インストール {#installation}

### オプション1(推奨): ホスト型MCPサーバー {#option-1-recommended-hosted-mcp-server}

セットアップの簡素化と自動アップデートのために、AWSマネージドのECS MCPサーバーを使用してください。ホスト型サービスを利用すればローカルへのインストールは不要になり、AWS IAM統合によるエンタープライズグレードのセキュリティが提供されます。

完全なセットアップ手順、設定例、IAM許可については、[Amazon ECS MCPサーバーのドキュメント](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-mcp-getting-started.html)を参照してください。

### オプション2: ローカルMCPサーバー(レガシー) {#option-2-local-mcp-server-legacy}

> **注**: これはレガシーのローカルインストール方法であり、今後アップデートは提供されません。代わりに[オプション1(ホスト型MCPサーバー)](#option-1-recommended-hosted-mcp-server)の使用を推奨します。

#### 前提条件 {#prerequisites}

ECS MCPサーバーをインストールする前に、以下の前提条件がインストールされていることを確認してください:

1. **DockerまたはFinch**: コンテナ化とローカルテストに必要です
   - コンテナ管理のための[Docker](https://docs.docker.com/get-docker/)
   - Dockerの代替としての[Finch](https://github.com/runfinch/finch)

2. **UV**: パッケージ管理とMCPサーバーの実行に必要です
   - [Astral](https://docs.astral.sh/uv/getting-started/installation/)から `uv` をインストールしてください

#### インストール手順 {#installation-steps}

```bash
# Install using uv
uv pip install awslabs.ecs-mcp-server

# Or install using pip
pip install awslabs.ecs-mcp-server
```

GitHubリポジトリのローカルクローンからMCPサーバーを直接実行することもできます:

```bash
# Clone the awslabs repository
git clone https://github.com/awslabs/mcp.git

# Run the server directly using uv
uv --directory /path/to/ecs-mcp-server/src/ecs-mcp-server/awslabs/ecs_mcp_server run main.py
```

お好みのMCPクライアント(Kiro、Cline、Cursor、VS Codeなど)にECS MCPサーバーをセットアップするには、[設定](#configuration)セクションに進んでください。

## 使用環境 {#usage-environments}

ECS MCPサーバーは現在開発中であり、以下の環境向けに設計されています:

- **開発とプロトタイピング**: ローカルでのアプリケーション開発、コンテナ化アプローチのテスト、デプロイメント設定の迅速な反復に最適です。
- **学習と探索**: コンテナ化、ECS、AWSインフラストラクチャについて学びたいユーザーに最適です。
- **テストとステージング**: 非クリティカルな環境における統合テストや本番前検証に適しています。

**推奨されない用途**:
- **本番ワークロード**: このツールはまだ活発に開発中のため、本番デプロイメントやビジネスクリティカルなアプリケーションには適していません。
- **規制対象または機密性の高いワークロード**: 機密データを扱うアプリケーションや、規制コンプライアンス要件の対象となるアプリケーションには適していません。

**トラブルシューティングツールに関する重要な注意**: トラブルシューティングツールであっても、本番環境では注意して使用する必要があります。本番アカウントに接続する場合は、機密情報の偶発的な漏えいや意図しないインフラストラクチャの変更を防ぐため、必ず `ALLOW_SENSITIVE_DATA=false` および `ALLOW_WRITE=false` フラグを設定してください。

## 本番環境での考慮事項 {#production-considerations}

ECS MCPサーバーは主に開発、テスト、非クリティカルな環境向けに設計されていますが、適切な安全策を講じることで、一部のコンポーネントは管理された本番利用を検討できます。

### 本番環境で許可可能なアクション {#allowlisted-actions-for-production}

以下のオペレーションは読み取り専用であり、適切なIAM許可とともに使用すれば本番環境でも比較的安全です。注: これらは機密情報を返す可能性があるため、本番環境の設定では `ALLOW_SENSITIVE_DATA=false` が設定されていることを確認してください。

| ツール | オペレーション | 本番環境での安全性 |
|------|-----------|-------------------|
| `ecs_resource_management` | 一覧表示オペレーション(クラスター、サービス、タスク) | ✅ 安全 - 読み取り専用 |
| `ecs_resource_management` | 詳細表示オペレーション(クラスター、サービス、タスク) | ✅ 安全 - 読み取り専用 |
| `validate_ecs_express_mode_prerequisites` | 前提条件の検証 | ✅ 安全 - 読み取り専用 |
| `wait_for_service_ready` | サービス準備状況のポーリング | ✅ 安全 - 読み取り専用 |
| `ecs_troubleshooting_tool` | `fetch_service_events` | ✅ 安全 - 読み取り専用 |
| `ecs_troubleshooting_tool` | `get_ecs_troubleshooting_guidance` | ✅ 安全 - 読み取り専用 |
| `aws_knowledge_aws___search_documentation` | AWSドキュメントの検索 | ✅ 安全 - 読み取り専用 |
| `aws_knowledge_aws___read_documentation` | AWSドキュメントの読み取り | ✅ 安全 - 読み取り専用 |
| `aws_knowledge_aws___recommend` | AWSドキュメントのレコメンデーション | ✅ 安全 - 読み取り専用 |

以下のオペレーションはリソースを変更するため、本番環境では細心の注意を払って使用する必要があります:

| ツール | オペレーション | 本番環境での安全性 |
|------|-----------|-------------------|
| `build_and_push_image_to_ecr` | Dockerイメージのビルドとプッシュ | ⚠️ 高リスク - ECRリポジトリを作成し、イメージをビルド/プッシュ |
| `delete_app` | Express ModeデプロイメントとECRインフラストラクチャの削除 | 🛑 危険 - リソースを削除 |
| `containerize_app` | コンテナ設定の生成 | 🟡 中リスク - ローカルの変更のみ |
| `ecs_resource_management` | 作成オペレーション(クラスター、サービス、タスク) | ⚠️ 高リスク - リソースを作成 |
| `ecs_resource_management` | 更新オペレーション(サービス、タスク、設定) | ⚠️ 高リスク - リソースを変更 |
| `ecs_resource_management` | 削除オペレーション(クラスター、サービス、タスク) | 🛑 危険 - リソースを削除 |
| `ecs_resource_management` | タスクの実行/開始/停止オペレーション | ⚠️ 高リスク - 実行中のワークロードに影響 |

### 本番利用を検討できる場合 {#when-to-consider-production-use}

以下のシナリオでは、ECS MCPサーバーの本番環境での利用が適切な場合があります:

1. **読み取り専用のモニタリング**: 読み取り専用のIAMポリシーとともにリソース管理ツールを使用する場合
2. **非クリティカルな問題のトラブルシューティング**: 診断ツールを使用してログやステータス情報を収集する場合
3. **サンドボックスまたは分離された環境**: コアサービスから分離された本番同等の環境でデプロイメントツールを使用する場合

### 本番利用を避けるべき場合 {#when-to-avoid-production-use}

以下の用途では、本番環境でのECS MCPサーバーの使用を避けてください:

1. クリティカルなビジネスインフラストラクチャ
2. 機密性の高い顧客データを扱うアプリケーション
3. 高スループットまたは高可用性のサービス
4. コンプライアンス要件のある規制対象ワークロード
5. 適切なバックアップおよび災害復旧手順が整備されていないインフラストラクチャ

## 設定 {#configuration}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.ecs-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22--from%22%2C%22awslabs-ecs-mcp-server%22%2C%22ecs-mcp-server%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22your-aws-region%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22FASTMCP_LOG_FILE%22%3A%22/path/to/ecs-mcp-server.log%22%2C%22ALLOW_WRITE%22%3A%22false%22%2C%22ALLOW_SENSITIVE_DATA%22%3A%22false%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.ecs-mcp-server&config=eyJjb21tYW5kIjoidXZ4IC0tZnJvbSBhd3NsYWJzLWVjcy1tY3Atc2VydmVyIGVjcy1tY3Atc2VydmVyIiwiZW52Ijp7IkFXU19QUk9GSUxFIjoieW91ci1hd3MtcHJvZmlsZSIsIkFXU19SRUdJT04iOiJ5b3VyLWF3cy1yZWdpb24iLCJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIiwiRkFTVE1DUF9MT0dfRklMRSI6Ii9wYXRoL3RvL2Vjcy1tY3Atc2VydmVyLmxvZyIsIkFMTE9XX1dSSVRFIjoiZmFsc2UiLCJBTExPV19TRU5TSVRJVkVfREFUQSI6ImZhbHNlIn19) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=ECS%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22--from%22%2C%22awslabs-ecs-mcp-server%22%2C%22ecs-mcp-server%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22your-aws-region%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22FASTMCP_LOG_FILE%22%3A%22%2Fpath%2Fto%2Fecs-mcp-server.log%22%2C%22ALLOW_WRITE%22%3A%22false%22%2C%22ALLOW_SENSITIVE_DATA%22%3A%22false%22%7D%7D) |

ECS MCPサーバーをMCPクライアントの設定に追加します:

```json
{
  "mcpServers": {
    "awslabs.ecs-mcp-server": {
      "command": "uvx",
      "args": ["--from", "awslabs-ecs-mcp-server", "ecs-mcp-server"],
      "env": {
        "AWS_PROFILE": "your-aws-profile", // Optional - uses your local AWS configuration if not specified
        "AWS_REGION": "your-aws-region", // Optional - uses your local AWS configuration if not specified
        "FASTMCP_LOG_LEVEL": "ERROR",
        "FASTMCP_LOG_FILE": "/path/to/ecs-mcp-server.log",
        "ALLOW_WRITE": "false",
        "ALLOW_SENSITIVE_DATA": "false"
      }
    }
  }
}
```
### Windowsでのインストール {#windows-installation}

Windowsユーザーの場合、MCPサーバーの設定形式が若干異なります:

```json
{
  "mcpServers": {
    "awslabs.ecs-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.ecs-mcp-server@latest",
        "ecs-mcp-server.exe"
      ],
     "env": {
        "AWS_PROFILE": "your-aws-profile", // Optional - uses your local AWS configuration if not specified
        "AWS_REGION": "your-aws-region", // Optional - uses your local AWS configuration if not specified
        "FASTMCP_LOG_LEVEL": "ERROR",
        "FASTMCP_LOG_FILE": "/path/to/ecs-mcp-server.log",
        "ALLOW_WRITE": "false",
        "ALLOW_SENSITIVE_DATA": "false"
      }
    }
  }
}
```


ローカルリポジトリから実行する場合は、MCPクライアントを次のように設定します:

```json
{
  "mcpServers": {
    "awslabs.ecs-mcp-server": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/ecs-mcp-server/src/ecs-mcp-server/awslabs/ecs_mcp_server",
        "run",
        "main.py"
      ],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "your-aws-region",
        "FASTMCP_LOG_LEVEL": "DEBUG",
        "FASTMCP_LOG_FILE": "/path/to/ecs-mcp-server.log",
        "ALLOW_WRITE": "false",
        "ALLOW_SENSITIVE_DATA": "false"
      }
    }
  }
}
```

## MCPサーバーのアップデート {#updating-the-mcp-server}

ECS MCPサーバーは、新機能、バグ修正、改善を含むアップデートが定期的に行われています。最新のアップデートを入手する方法は次のとおりです:

### 自動アップデート(デフォルトの動作) {#automatic-updates-default-behavior}

PyPI経由でインストールした場合(推奨)、アップデートは自動的に行われます:

- **PyPIインストール**: サーバーの再起動時に、MCPクライアントが自動的に最新バージョンをダウンロードします
- **操作は不要**: MCPクライアントを再起動するだけで最新のアップデートが適用されます

### 手動アップデート {#manual-updates}

最新バージョンであることを確実にするために手動でアップデートしたい場合:

```bash
uv pip install --upgrade awslabs.ecs-mcp-server
```

### ローカルリポジトリのアップデート {#local-repository-updates}

クローンしたリポジトリから実行している場合は、最新の変更をプルしてアップデートします:

```bash
# Navigate to your cloned repository
cd /path/to/mcp

# Pull the latest changes
git pull origin main

# The MCP server will automatically use the updated code on next restart
```

## セキュリティコントロール {#security-controls}

ECS MCPサーバーは、インフラストラクチャへの偶発的な変更を防ぎ、機密データへのアクセスを制限するためのセキュリティコントロールをMCPクライアントの設定に含んでいます:

### ALLOW_WRITE {#allow_write}

書き込みオペレーション(インフラストラクチャの作成や削除)を許可するかどうかを制御します。

```bash
# Enable write operations
"ALLOW_WRITE": "true"

# Disable write operations (default)
"ALLOW_WRITE": "false"
```

### ALLOW_SENSITIVE_DATA {#allow_sensitive_data}

ログや詳細なリソース情報を返すツールを許可するかどうかを制御します。

```bash
# Enable access to sensitive data
"ALLOW_SENSITIVE_DATA": "true"

# Disable access to sensitive data (default)
"ALLOW_SENSITIVE_DATA": "false"
```

### IAMベストプラクティス {#iam-best-practices}

ECS MCPサーバーを使用する際は、最小権限の許可を持つ専用のIAMロールを作成することを強く推奨します:

1. ECS MCPサーバーのオペレーション専用の**IAMロールを作成する**
2. ユースケースに応じて必要なポリシーのみをアタッチし、**最小権限の許可を適用する**
3. 可能な限り**リソースを絞り込んだポリシーを使用する**
4. 最大許可を制限するために**許可境界を適用する**

さまざまなECS MCPサーバーのユースケース(読み取り専用モニタリング、トラブルシューティング、デプロイメント、サービス固有のアクセス)に合わせた詳細なIAMポリシーの例については、[EXAMPLE_IAM_POLICIES.md](https://github.com/awslabs/mcp/blob/main/src/ecs-mcp-server/EXAMPLE_IAM_POLICIES.md)を参照してください。


## MCPツール {#mcp-tools}

### Express Modeデプロイメントツール {#express-mode-deployment-tools}

これらのツールは、必要なすべてのインフラストラクチャを自動的にプロビジョニングするECS Express Modeを使用して、アプリケーションのコンテナ化とデプロイをエンドツーエンドでサポートします。

- **containerize_app**: ベストプラクティスに基づいて、Webアプリケーション用のDockerfileとコンテナ設定を生成します
- **build_and_push_image_to_ecr**: ECRインフラストラクチャを作成し、Dockerイメージをビルド/プッシュします
  - CloudFormation経由でECRリポジトリを作成します
  - ECRプッシュ/プル許可を持つIAMロールを作成します
  - アプリケーションディレクトリからDockerイメージをビルドします
  - 設定可能なタグを付けてイメージをECRにプッシュします
  - デプロイで使用するための `full_image_uri` を返します
- **validate_ecs_express_mode_prerequisites**: Express Modeデプロイ前の前提条件を検証します
  - Task Execution Roleが存在するかを確認します(デフォルトは `ecsTaskExecutionRole`)
  - Infrastructure Roleが存在するかを確認します(デフォルトは `ecsInfrastructureRoleForExpressServices`)
  - DockerイメージがECRに存在することを検証します
- **wait_for_service_ready**: タスクがRUNNING状態に達するまでサービスのステータスをポーリングします
  - 10秒ごとに実行中のタスクを確認します
- **delete_app**: Express Modeデプロイメント全体を削除します
  - Express Gateway Serviceとプロビジョニングされたインフラストラクチャを削除します
  - ECRのCloudFormationスタック(リポジトリ + IAMロール)を削除します

### トラブルシューティングツール {#troubleshooting-tool}

トラブルシューティングツールは、インフラストラクチャ、サービス、タスク、ネットワーク設定に起因する一般的なECSデプロイメントの問題の診断と解決を支援します。

- **ecs_troubleshooting_tool**: 以下のアクションを持つ統合ツールです:
  - **get_ecs_troubleshooting_guidance**: 初期評価とトラブルシューティング手順の推奨
  - **fetch_cloudformation_status**: CloudFormationスタックのインフラストラクチャレベルの診断
  - **fetch_service_events**: ECSサービスのサービスレベルの診断
  - **fetch_task_failures**: ECSタスクの失敗に関するタスクレベルの診断
  - **fetch_task_logs**: CloudWatchログによるアプリケーションレベルの診断
  - **detect_image_pull_failures**: コンテナイメージのプル失敗を検出するための専用ツール
  - **fetch_network_configuration**: VPC、サブネット、セキュリティグループ、ロードバランサーを含むECSデプロイメントのネットワークレベルの診断

### リソース管理 {#resource-management}

このツールは、デプロイメント環境のモニタリング、理解、管理を支援するために、Amazon ECSリソースへの包括的なアクセスを提供します。

- **ecs_resource_management**: 一貫したインターフェースでECSリソースに対するオペレーションを実行します:
  - **読み取りオペレーション**(常に利用可能):
    - Express Gateway Service: Express Gateway Serviceの一覧表示と詳細表示
    - クラスター: すべてのクラスターの一覧表示、特定のクラスターの詳細表示
    - サービス: クラスター内のサービスの一覧表示、サービス設定の詳細表示
    - タスク: 実行中または停止済みタスクの一覧表示、タスクの詳細とステータスの表示
    - タスク定義: タスク定義ファミリーの一覧表示、特定のタスク定義リビジョンの詳細表示
    - コンテナインスタンス: コンテナインスタンスの一覧表示、インスタンスのヘルスとキャパシティの詳細表示
    - キャパシティプロバイダー: クラスターに関連付けられたキャパシティプロバイダーの一覧表示と詳細表示
    - サービスデプロイメント: サービスデプロイメントの詳細表示と一覧表示
    - ECRリポジトリとコンテナイメージ
  - **書き込みオペレーション**(ALLOW_WRITE=trueが必要):
    - Express Mode: Express Gateway Serviceの作成、更新、削除
    - リソースの作成: クラスター、サービス、タスクセット、キャパシティプロバイダーの作成
    - リソースの更新: サービス設定、タスク保護設定、クラスター設定の更新
    - リソースの削除: クラスター、サービス、タスク定義、キャパシティプロバイダーの削除
    - 登録/登録解除: タスク定義とコンテナインスタンスの登録および登録解除
    - タスク管理: タスクの実行、開始、停止、および実行中タスクでのコマンド実行
    - タグ管理: リソースへのタグ付けとタグの削除

リソース管理ツールは、書き込みオペレーションに対して許可チェックを実施します。リソースを変更するオペレーションには、ALLOW_WRITE環境変数をtrueに設定する必要があります。

### AWSドキュメントツール {#aws-documentation-tools}

ECS MCPサーバーは[AWS Knowledge MCP Server](https://github.com/awslabs/mcp/tree/main/src/aws-knowledge-mcp-server)と統合されており、最新のAWSドキュメントへのアクセスを提供します。これには、モデルが認識していない可能性のある、最近リリースされた新機能に関するECS固有の知識が含まれます。

注: MCPクライアントにAWS Knowledge MCP Serverをすでに設定している場合、これらのツールは重複します。以下のナレッジツールについて、ECS MCPサーバーは、LLMがECSのコンテキストでツールを活用しやすくなるよう、ツールの説明に追加のガイダンスを加えています。

- **aws_knowledge_aws___search_documentation**: 最新のAWSドキュメント、APIリファレンス、ブログ記事、アーキテクチャリファレンス、Well-Architectedベストプラクティスを含む、すべてのAWSドキュメントを横断的に検索します。

- **aws_knowledge_aws___read_documentation**: AWSドキュメントのページを取得してmarkdown形式に変換します。

- **aws_knowledge_aws___recommend**: AWSドキュメントのページに対するコンテンツのレコメンデーションを取得します。

## プロンプト例 {#example-prompts}

### Express Modeによるコンテナ化とデプロイ {#containerization-and-deployment-with-express-mode}

- 「このNode.jsアプリをコンテナ化して、Express Modeを使用してAWSにデプロイして」
- 「このFlaskアプリケーションをAmazon ECS Express Modeにデプロイして」
- 「アプリケーションのDockerイメージをビルドしてECRにプッシュして」
- 「Express Modeでのデプロイに必要な前提条件を検証して」
- 「オートスケーリング付きで私のアプリケーション用のExpress Gateway Serviceを作成して」
- 「サービスの準備が整うまで待って、URLを表示して」
- 「Express Modeデプロイメントを削除して、すべてのリソースをクリーンアップして」
- 「すべてのExpress Gateway Serviceを一覧表示して」
- 「私のExpress Gateway Serviceの詳細を表示して」

### トラブルシューティング {#troubleshooting}

- 「ECSデプロイメントのトラブルシューティングを手伝って」
- 「ECSタスクが失敗し続けているので、問題を診断してもらえますか?」
- 「ECSサービスのALBヘルスチェックが失敗しています」
- 「デプロイしたアプリケーションにアクセスできないのはなぜですか?」
- 「私のExpress Gateway Serviceの問題を確認して」

### リソース管理 {#resource-management-1}

- 「ECSクラスターを表示して」
- 「ECSクラスター内の実行中のタスクをすべて一覧表示して」
- 「ECSサービスの設定を詳しく表示して」
- 「タスク定義の情報を取得して」
- 「新しいECSクラスターを作成して」
- 「サービスの設定を更新して」
- 「新しいタスク定義を登録して」
- 「未使用のタスク定義を削除して」
- 「クラスターでタスクを実行して」
- 「実行中のタスクを停止して」

### AWSドキュメントとナレッジ {#aws-documentation-and-knowledge}

- 「ECS Express Modeとは何ですか?」
- 「ECSデプロイメントのベストプラクティスは何ですか?」
- 「ECSでブルー/グリーンデプロイメントを設定するにはどうすればよいですか?」
- 「ECSのセキュリティベストプラクティスに関するレコメンデーションを取得して」

## 要件 {#requirements}

- Python 3.10+
- ECS、ECR、CloudFormation、および関連サービスに対する許可を持つAWS認証情報
- Docker(ローカルでのコンテナ化テスト用)

## ライセンス {#license}

このプロジェクトはApache-2.0ライセンスの下でライセンスされています。
