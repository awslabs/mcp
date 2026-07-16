---
title: AWS Serverless MCPサーバー
---

## 概要 {#overview}

AWS Serverless Model Context Protocol (MCP) Serverは、AIによる支援とサーバーレスの専門知識を組み合わせ、開発者によるサーバーレスアプリケーション構築を効率化するオープンソースツールです。サーバーレス開発に特化したコンテキストに基づくガイダンスを提供し、アプリケーション開発ライフサイクル全体を通じて、アーキテクチャ、実装、デプロイに関する的確な意思決定を支援します。AWS Serverless MCPを使うことで、開発者は信頼性が高く、効率的で、本番環境に対応したサーバーレスアプリケーションを自信を持って構築できます。

Serverless MCPサーバーの主なメリットは次のとおりです。

- AIを活用したサーバーレス開発: AIコーディングアシスタントに豊富なコンテキスト情報を提供し、サーバーレスアプリケーションがAWSのベストプラクティスに沿うようにします。
- 包括的なツール群: サーバーレスアプリケーションの初期化、デプロイ、モニタリング、トラブルシューティングのためのツールを提供します。
- アーキテクチャガイダンス: 設計上の選択肢を評価し、アプリケーションのニーズに基づいて最適なサーバーレスパターンを選択できるよう支援します。イベントソース、関数の境界、サービス統合に関する推奨事項を提供します。
- 運用のベストプラクティス: AWSのアーキテクチャ原則との整合性を確保します。イベント処理、データ永続化、サービス間通信におけるAWSサービスの効果的な活用を提案し、セキュリティコントロール、パフォーマンスチューニング、コスト最適化の実装をガイドします。
- セキュリティファーストのアプローチ: 読み取り専用をデフォルトとし、機密データへのアクセスを制御する組み込みのガードレールを実装しています。

## 機能 {#features}
Serverless MCPサーバーが提供するツール群は、次の4つのカテゴリに分類できます。

1. サーバーレスアプリケーションのライフサイクル
    - SAM CLIを使用したServerless Application Model (SAM) アプリケーションの初期化、ビルド、デプロイ
    - Lambda関数のローカルおよびリモートでのテスト
2. Webアプリケーションのデプロイと管理
    - Lambda Web Adapterを使用して、フルスタック、フロントエンド、バックエンドのWebアプリケーションをAWS Serverlessにデプロイ
    - フロントエンドアセットの更新と、必要に応じたCloudFrontキャッシュの無効化
    - 証明書とDNSの設定を含むカスタムドメイン名の作成
3. オブザーバビリティ
    - サーバーレスリソースのログとメトリクスの取得
4. ガイダンス、テンプレート、デプロイ支援
    - AWS Lambdaのユースケース、IaCフレームワークの選択、AWS Serverlessへのデプロイプロセスに関するガイダンスを提供
    - [Serverless Land](https://serverlessland.com/)から、さまざまな種類のサーバーレスアプリケーション向けのサンプルSAMテンプレートを提供
    - さまざまなLambdaイベントソースとランタイム向けのスキーマ型を提供
    - AWS EventBridgeイベントのスキーマレジストリ管理と検出機能を提供
    - 完全なイベントスキーマにより、型安全なLambda関数開発を実現

## 前提条件 {#prerequisites}
- [認証情報が設定された](https://docs.aws.amazon.com/cli/v1/userguide/cli-configure-files.html)AWSアカウントを持っていること
- [Astral](https://docs.astral.sh/uv/getting-started/installation/)または[GitHub README](https://github.com/astral-sh/uv#installation)からuvをインストールすること
- uv python install 3.10 を使用してPython 3.10以降をインストールすること（より新しいバージョンでも可）
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)をインストールすること
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)をインストールすること

## インストール {#installation}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.aws-serverless-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-serverless-mcp-server%40latest%22%2C%22--allow-write%22%2C%22--allow-sensitive-data-access%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.aws-serverless-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLXNlcnZlcmxlc3MtbWNwLXNlcnZlckBsYXRlc3QgLS1hbGxvdy13cml0ZSAtLWFsbG93LXNlbnNpdGl2ZS1kYXRhLWFjY2VzcyIsImVudiI6eyJBV1NfUFJPRklMRSI6InlvdXItYXdzLXByb2ZpbGUiLCJBV1NfUkVHSU9OIjoidXMtZWFzdC0xIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ%3D%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20Serverless%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-serverless-mcp-server%40latest%22%2C%22--allow-write%22%2C%22--allow-sensitive-data-access%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

AWS Serverless MCPサーバーはGitHubからダウンロードできます。Kiro、Cursor、ClineなどのMCPに対応したお好みのコードアシスタントで利用を開始できます。

以下のコードをMCPクライアントの設定に追加してください。Serverless MCPサーバーはデフォルトでAWSのデフォルトプロファイルを使用します。別のプロファイルを使用したい場合は、AWS_PROFILEに値を指定してください。同様に、AWSリージョンやログレベルの値も必要に応じて調整してください。
```json
{
  "mcpServers": {
    "awslabs.aws-serverless-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.aws-serverless-mcp-server@latest",
        "--allow-write",
        "--allow-sensitive-data-access"
      ],
      "env": {
          "AWS_PROFILE": "your-aws-profile",
          "AWS_REGION": "us-east-1"
        },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### 一時的な認証情報の使用 {#using-temporary-credentials}
```json
{
  "mcpServers": {
    "awslabs.aws-serverless-mcp-server": {
        "command": "uvx",
        "args": ["awslabs.aws-serverless-mcp-server@latest"],
        "env": {
          "AWS_ACCESS_KEY_ID": "your-temporary-access-key",
          "AWS_SECRET_ACCESS_KEY": "your-temporary-secret-key", // pragma: allowlist secret
          "AWS_SESSION_TOKEN": "your-session-token",
          "AWS_REGION": "us-east-1"
        },
        "disabled": false,
        "autoApprove": []
    }
  }
}
```

### Windowsでのインストール {#windows-installation}

Windowsユーザーの場合、MCPサーバーの設定形式は少し異なります。

```json
{
  "mcpServers": {
    "awslabs.aws-serverless-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.aws-serverless-mcp-server@latest",
        "awslabs.aws-serverless-mcp-server.exe"
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

## Serverless MCPサーバーの設定オプション {#serverless-mcp-server-configuration-options}
### `--allow-write` {#--allow-write}
書き込みアクセスモードを有効にします。このモードでは、変更を伴う操作やパブリックリソースの作成が可能になります。デフォルトでは、サーバーは読み取り専用モードで動作し、読み取りアクションのみに操作を制限することで、AWSリソースへの変更を防ぎます。

変更を伴う操作:

- sam_deploy: CloudFormationを使用してSAMアプリケーションをAWSクラウドにデプロイします
- deploy_webapp: SAMテンプレートを生成し、WebアプリケーションをAWS CloudFormationにデプロイします。Route 53 DNSレコードやCloudFrontディストリビューションなどのパブリックリソースを作成します
- configure_domain: Route53とACM証明書を使用してカスタムドメインを作成し、プロジェクトのCloudFrontディストリビューションに関連付けます
- update_frontend: フロントエンドアセットをS3バケットにアップロードします
- esm_guidance: Event Source Mappingのセットアップ用のSAMテンプレートを生成します（デプロイ前にユーザーの確認が必要です）
- esm_optimize: ESM設定の最適化用のSAMテンプレートを生成します（デプロイ前にユーザーの確認が必要です）
- esm_kafka_troubleshoot: Kafka ESMの問題を解決するためのテンプレートを生成します（デプロイ前にユーザーの確認が必要です）

**重要**: ESMツールはSAMテンプレートを生成しますが、デプロイの前には必ずユーザーの明示的な確認が必要です。実際のインフラストラクチャの変更にはsam_deployと連携します。


### `--allow-sensitive-data-access` {#--allow-sensitive-data-access}
ログなどの機密データへのアクセスを有効にします。デフォルトでは、サーバーは機密データへのアクセスを制限します。

機密データを返す操作:

- sam_logs: Lambda関数のログとAPI Gatewayのログを返します

## ローカル開発 {#local-development}

このMCPをローカルで変更して実行するには、次の手順に従います。

1. このリポジトリをクローンします:
   ```bash
   git clone https://github.com/awslabs/mcp.git
   cd mcp/src/aws-serverless-mcp-server
   ```

2. 依存関係をインストールします:
   ```bash
   pip install -e .
   ```

3. AWS認証情報を設定します:
   - `~/.aws/credentials`にAWS認証情報が設定されていることを確認するか、適切な環境変数を設定してください。
   - AWS_PROFILEおよびAWS_REGION環境変数を設定することもできます。

4. サーバーを実行します:
   ```bash
   python -m awslabs.aws_serverless_mcp_server.server
   ```

5. このMCPサーバーをAIクライアントで使用するには、MCP設定に以下を追加します:
```json
{
  "mcpServers": {
    "awslabs.aws-serverless-mcp-server": {
        "command": "mcp/src/aws-serverless-mcp-server/bin/awslabs.aws-serverless-mcp-server/",
        "env": {
          "AWS_PROFILE": "your-aws-profile",
          "AWS_REGION": "us-east-1",
        },
        "disabled": false,
        "autoApprove": []
    }
  }
}
```

## 環境変数 {#environment-variables}

デフォルトでは、AWSのデフォルトプロファイルが使用されます。ただし、MCP設定内の環境変数を通じてサーバーを構成できます。

- `AWS_PROFILE`: 認証情報に使用するAWS CLIプロファイル
- `AWS_REGION`: 使用するAWSリージョン（デフォルト: us-east-1）
- `AWS_ACCESS_KEY_ID`および`AWS_SECRET_ACCESS_KEY`: 明示的なAWS認証情報（AWS_PROFILEの代替）
- `AWS_SESSION_TOKEN`: 一時的な認証情報用のセッショントークン（AWS_ACCESS_KEY_IDおよびAWS_SECRET_ACCESS_KEYとともに使用）
- `FASTMCP_LOG_LEVEL`: ログレベル（ERROR、WARNING、INFO、DEBUG）

## 利用可能なリソース {#available-resources}

サーバーは以下のリソースを提供します。

### テンプレートリソース {#template-resources}
- `template://list`: 利用可能なデプロイテンプレートの一覧。
- `template://{template_name}`: 特定のデプロイテンプレートの詳細。

### デプロイメントリソース {#deployment-resources}
- `deployment://list`: MCPサーバーが管理するすべてのAWSデプロイメントの一覧。
- `deployment://{project_name}`: 特定のデプロイメントに関する詳細。

## 利用可能なツール {#available-tools}

サーバーはデプロイ機能をツールとして公開します。

### sam_init {#sam_init}

AWS SAM (Serverless Application Model) CLIを使用してサーバーレスアプリケーションを初期化します。
このツールは、以下で構成される新しいSAMプロジェクトを作成します。
- インフラストラクチャコードを定義するAWS SAMテンプレート
- アプリケーションを整理するフォルダ構造
- AWS Lambda関数の設定
環境にAWS SAM CLIがインストールおよび設定されている必要があります。

**Parameters:**

- `project_name` (required): 作成するSAMプロジェクトの名前
- `runtime` (required): Lambda関数のランタイム環境
- `project_directory` (required): SAMアプリケーションを初期化するディレクトリの絶対パス
- `dependency_manager` (required): Lambda関数の依存関係マネージャー
- `architecture` (default: x86_64): Lambda関数のアーキテクチャ
- `package_type` (default: Zip): Lambda関数のパッケージタイプ
- `application_template` (default: hello-world): SAMアプリケーションのテンプレート（例: hello-world、quick-startなど）
- `application_insights`: Amazon CloudWatch Application Insightsのモニタリングを有効化
- `no_application_insights`: Amazon CloudWatch Application Insightsのモニタリングを無効化
- `base_image`: パッケージタイプがImageの場合のアプリケーションのベースイメージ
- `config_env`: 設定ファイル内のデフォルトパラメータ値を指定する環境名
- `config_file`: デフォルトパラメータ値を含む設定ファイルの絶対パス
- `debug`: デバッグログを有効化
- `extra_content`: テンプレートのcookiecutter.json内のカスタムパラメータを上書き
- `location`: テンプレートまたはアプリケーションの場所（Git、HTTP/HTTPS、zipファイルパス）
- `save_params`: パラメータをSAM設定ファイルに保存
- `tracing`: Lambda関数のAWS X-Rayトレーシングを有効化
- `no_tracing`: Lambda関数のAWS X-Rayトレーシングを無効化

### sam_build {#sam_build}

AWS SAM (Serverless Application Model) CLIを使用してサーバーレスアプリケーションをビルドします。
このコマンドは、Lambda関数コードをコンパイルし、デプロイアーティファクトを作成し、アプリケーションのデプロイ準備を行います。
このツールを実行する前に、'sam_init'ツールでアプリケーションが初期化されている必要があります。
環境にAWS SAM CLIがインストールおよび設定されている必要があります。

**Parameters:**

- `project_directory` (required): SAMプロジェクトを含むディレクトリの絶対パス
- `template_file`: テンプレートファイルの絶対パス（デフォルトはtemplate.yaml）
- `base_dir`: 関数のソースコードへの相対パスをこのフォルダ基準で解決
- `build_dir`: ビルドされたアーティファクトを格納するディレクトリの絶対パス
- `use_container` (default: false): コンテナを使用して関数をビルド
- `no_use_container` (default: false): Dockerコンテナではなくローカルマシンでビルドを実行
- `parallel` (default: true): AWS SAMアプリケーションを並列でビルド
- `container_env_vars`: ビルドコンテナに渡す環境変数
- `container_env_var_file`: コンテナ環境変数を含むJSONファイルの絶対パス
- `build_image`: ビルド用にプルするコンテナイメージのURI
- `debug` (default: false): デバッグログを有効化
- `manifest`: デフォルトの代わりに使用するカスタム依存関係マニフェストファイル（例: package.json）の絶対パス
- `parameter_overrides`: キーと値のペアとしてエンコードされたCloudFormationパラメータの上書き
- `region`: デプロイ先のAWSリージョン（例: us-east-1）
- `save_params` (default: false): パラメータをSAM設定ファイルに保存
- `profile`: 使用するAWSプロファイル

### sam_deploy {#sam_deploy}

AWS SAM (Serverless Application Model) CLIを使用してサーバーレスアプリケーションをデプロイします。
このコマンドは、アプリケーションをAWS CloudFormationにデプロイします。
アプリケーションをデプロイする際は、毎回事前に'sam_build'ツールでビルドしておく必要があります。
環境にAWS SAM CLIがインストールおよび設定されている必要があります。

**Parameters:**

- `application_name` (required): デプロイするアプリケーションの名前
- `project_directory` (required): SAMプロジェクトを含むディレクトリの絶対パス（デフォルトは現在のディレクトリ）
- `template_file`: テンプレートファイルの絶対パス（デフォルトはtemplate.yaml）
- `s3_bucket`: アーティファクトのデプロイ先S3バケット
- `s3_prefix`: アーティファクトのS3プレフィックス
- `region`: デプロイ先のAWSリージョン
- `profile`: 使用するAWSプロファイル
- `parameter_overrides`: キーと値のペアとしてエンコードされたCloudFormationパラメータの上書き
- `capabilities` (default: ["CAPABILITY_IAM"]): デプロイに必要なIAM機能
- `config_file`: SAM設定ファイルの絶対パス
- `config_env`: 設定ファイル内のデフォルトパラメータ値を指定する環境名
- `metadata`: スタックに含めるメタデータ
- `tags`: スタックに適用するタグ
- `resolve_s3` (default: false): デプロイアーティファクト用のS3バケットを自動的に作成
- `debug` (default: false): デバッグログを有効化

### sam_logs {#sam_logs}

SAMアプリケーション内のリソースによって生成されたCloudWatchログを取得します。このツールは、
呼び出しの失敗をデバッグし、根本原因を特定するのに役立ちます。

**Parameters:**

- `resource_name`: ログを取得するリソースの名前（CloudFormation/SAMテンプレート内の論理ID）
- `stack_name`: CloudFormationスタックの名前
- `start_time`: この時刻以降のログを取得（形式: 5mins ago、tomorrow、またはYYYY-MM-DD HH:MM:SS）
- `end_time`: この時刻までのログを取得（形式: 5mins ago、tomorrow、またはYYYY-MM-DD HH:MM:SS）
- `output` (default: text): 出力形式（textまたはjson）
- `region`: 使用するAWSリージョン（例: us-east-1）
- `profile`: 使用するAWSプロファイル
- `cw_log_group`: ログを取得するCloudWatch Logsロググループ
- `config_env`: 設定ファイル内のデフォルトパラメータ値を指定する環境名
- `config_file`: デフォルトパラメータ値を含む設定ファイルの絶対パス
- `save_params` (default: false): パラメータをSAM設定ファイルに保存

### sam_local_invoke {#sam_local_invoke}

AWS SAM CLIを使用してLambda関数をローカルで呼び出します。
このコマンドは、AWS Lambda環境をシミュレートするDockerコンテナ内でLambda関数をローカルに実行します。
このツールを使用して、AWSにデプロイする前にLambda関数をテストできます。環境にDockerがインストールされ、実行されている必要があります。

**Parameters:**

- `project_directory` (required): SAMプロジェクトを含むディレクトリの絶対パス
- `resource_name` (required): ローカルで呼び出すLambda関数の名前
- `template_file`: SAMテンプレートファイルの絶対パス（デフォルトはtemplate.yaml）
- `event_file`: イベントデータを含むJSONファイルの絶対パス
- `event_data`: イベントデータを含むJSON文字列（event_fileの代替）
- `environment_variables_file`: 関数に渡す環境変数を含むJSONファイルの絶対パス
- `docker_network`: Lambda関数を実行するDockerネットワーク
- `container_env_vars`: コンテナに渡す環境変数
- `parameter`: テンプレートファイルのパラメータを上書き
- `log_file`: 関数のログを書き込むファイルの絶対パス
- `layer_cache_basedir`: レイヤーをキャッシュするディレクトリ
- `region`: 使用するAWSリージョン（例: us-east-1）
- `profile`: 使用するAWSプロファイル

### get_iac_guidance {#get_iac_guidance}

サーバーレスアプリケーションをAWSにデプロイするためのInfrastructure as Code (IaC) プラットフォームの選択に関するガイダンスを返します。
選択肢にはAWS SAM、CDK、CloudFormationが含まれます。このツールを使用して、特定のユースケースや要件に基づいて、Lambdaデプロイにどの
IaCツールを使用するかを判断できます。

**Parameters:**

- `iac_tool` (default: CloudFormation): 使用するIaCツール（CloudFormation、SAM、CDK、Terraform）
- `include_examples` (default: true): 例を含めるかどうか

### get_lambda_event_schemas {#get_lambda_event_schemas}

さまざまなイベントソース（例: s3、sns、apigw）とプログラミング言語向けのAWS Lambdaイベントスキーマを返します。各Lambdaイベントソースは独自のスキーマと言語固有の型を定義しており、
イベントデータを正しく解析するためにLambda関数ハンドラーで使用する必要があります。イベントソースのスキーマが見つからない場合は、イベントデータを
JSONオブジェクトとして直接解析できます。EventBridgeイベントの場合は、
list_registries、search_schema、describe_schemaツールを使用してスキーマレジストリに直接アクセスし、スキーマ定義を取得し、
コード処理ロジックを生成する必要があります。

**Parameters:**

- `event_source` (required): イベントソース（例: api-gw、s3、sqs、sns、kinesis、eventbridge、dynamodb）
- `runtime` (required): スキーマ参照のプログラミング言語（例: go、nodejs、python、java）

### get_lambda_guidance {#get_lambda_guidance}

AWS Lambdaがアプリケーションのデプロイ先プラットフォームとして適しているかどうかを判断するために、このツールを使用します。
デプロイプラットフォームとしてAWS Lambdaを選択すべきタイミングに関する包括的なガイドを返します。
Lambdaを使用すべきシナリオと使用すべきでないシナリオ、メリットとデメリット、
判断基準、さまざまなユースケースに対する具体的なガイダンスが含まれます。

**Parameters:**

- `use_case` (required): ユースケースの説明
- `include_examples` (default: true): 例を含めるかどうか

### deploy_webapp {#deploy_webapp}

コンピューティングとしてのLambda、データベースとしてのDynamoDB、API GW、ACM証明書、Route 53 DNSレコードを含め、WebアプリケーションをAWS Serverlessにデプロイします。
このツールはLambda Web Adapterフレームワークを使用するため、ExpressやNext.jsのような標準的なWebフレームワークで書かれたアプリケーションを簡単に
Lambdaにデプロイできます。このツールを使用する際、コードをアダプターフレームワークと統合する必要はありません。

**Parameters:**

- `deployment_type` (required): デプロイの種類（backend、frontend、fullstack）
- `project_name` (required): プロジェクト名
- `project_root` (required): プロジェクトルートディレクトリの絶対パス
- `region`: デプロイ先のAWSリージョン（例: us-east-1）
- `backend_configuration`: バックエンドの設定
- `frontend_configuration`: フロントエンドの設定

### configure_domain {#configure_domain}

AWS Serverless上にデプロイされたWebアプリケーションのカスタムドメインを設定します。
このツールは、必要に応じてRoute 53 DNSレコード、ACM証明書、CloudFrontカスタムドメインマッピングをセットアップします。
Webアプリケーションのデプロイ後にこのツールを使用して、独自のドメイン名と関連付けます。

**Parameters:**

- `project_name` (required): プロジェクト名
- `domain_name` (required): カスタムドメイン名
- `create_certificate` (default: true): ACM証明書を作成するかどうか
- `create_route53_record` (default: true): Route 53レコードを作成するかどうか
- `region`: 使用するAWSリージョン（例: us-east-1）

### webapp_deployment_help {#webapp_deployment_help}

deploy_webappを使用してWebアプリケーションをデプロイする方法に関するヘルプ情報を取得します。
deployment_typeが指定されている場合、そのデプロイタイプのヘルプ情報を返します。
指定されていない場合、デプロイメントの一覧と一般的なヘルプ情報を返します。

**Parameters:**

- `deployment_type` (required): ヘルプ情報を取得するデプロイの種類（backend、frontend、fullstack）

### get_metrics {#get_metrics}

デプロイされたWebアプリケーションからCloudWatchメトリクスを取得します。このツールを使用して、
エラー率、レイテンシー、同時実行数などのメトリクスを取得できます。

**Parameters:**

- `project_name` (required): プロジェクト名
- `start_time`: メトリクスの開始時刻（ISO形式）
- `end_time`: メトリクスの終了時刻（ISO形式）
- `period` (default: 60): メトリクスの期間（秒）
- `resources` (default: ["lambda", "apiGateway"]): メトリクスを取得するリソース
- `region`: 使用するAWSリージョン（例: us-east-1）
- `stage` (default: "prod"): API Gatewayのステージ

### update_webapp_frontend {#update_webapp_frontend}

デプロイされたWebアプリケーションのフロントエンドアセットを更新します。
このツールは、新しいフロントエンドアセットをS3にアップロードし、必要に応じてCloudFrontキャッシュを無効化します。

**Parameters:**

- `project_name` (required): プロジェクト名
- `project_root` (required): プロジェクトルート
- `built_assets_path` (required): ビルド済みフロントエンドアセットの絶対パス
- `invalidate_cache` (default: true): CloudFrontキャッシュを無効化するかどうか
- `region`: 使用するAWSリージョン（例: us-east-1）

### deploy_serverless_app_help {#deploy_serverless_app_help}

サーバーレスアプリケーションをAWS Lambdaにデプロイする方法についての手順を提供します。
Lambdaアプリケーションのデプロイには、IaCテンプレートの生成、コードのビルド、コードの
パッケージング、デプロイツールの選択、デプロイコマンドの実行が必要です。特にWebアプリケーションの
デプロイには、deploy_webappツールを使用してください。

**Parameters:**

- `application_type` (required): デプロイするアプリケーションの種類（event_driven、backend、fullstack）

### get_serverless_templates {#get_serverless_templates}

Serverless Land GitHubリポジトリからサンプルSAMテンプレートを返します。このツールを使用して、
AWS Lambdaによるサーバーレスアプリケーション構築の例や、サーバーレスアーキテクチャのベストプラクティスを取得できます。

**Parameters:**

- `template_type` (required): テンプレートの種類（例: API、ETL、Web）
- `runtime`: Lambdaランタイム（例: nodejs22.x、python3.13）

### スキーマツール {#schema-tools}

#### list_registries {#list_registries}

アカウント内のレジストリを一覧表示します。

**Parameters:**

- `registry_name_prefix`: このプレフィックスで始まるレジストリに結果を限定
- `scope`: レジストリスコープでフィルタリング（LOCALまたはAWS）
- `limit`: 返す結果の最大数（1〜100）
- `next_token`: 後続リクエスト用のページネーショントークン

#### search_schema {#search_schema}

キーワードを使用してレジストリ内のスキーマを検索します。

**Parameters:**

- `keywords` (required): 検索するキーワード（サービスイベントの場合は"aws."をプレフィックスとして付ける）
- `registry_name` (required): 検索対象のレジストリ（AWSサービスイベントの場合は"aws.events"を使用）
- `limit`: 結果の最大数（1〜100）
- `next_token`: ページネーショントークン

#### describe_schema {#describe_schema}

指定したスキーマバージョンのスキーマ定義を取得します。

**Parameters:**

- `registry_name` (required): スキーマを含むレジストリ（AWSサービスイベントの場合は"aws.events"を使用）
- `schema_name` (required): 取得するスキーマの名前（例: S3イベントの場合は"aws.s3@ObjectCreated"）
- `schema_version`: スキーマのバージョン番号（デフォルトは最新）

### ESMツール {#esm-tools}

ESMツールは、内部で専門的な機能を呼び出す少数の主要ツールを使用することで、信頼確認のプロンプトを最小限に抑えるように設計されています。これらのツールは、主に3つのカテゴリに分類できます。

##### esm_guidance {#esm_guidance}
Event Source Mappingのセットアップ、ネットワーキング、トラブルシューティングに関する包括的なガイダンスです。これは、内部で専門的なポリシーおよびセキュリティグループのジェネレーターを使用する主要ツールです。

**Parameters:**
- `event_source`: イベントソースの種類（"dynamodb"、"kinesis"、"kafka"、"sqs"、"unspecified"）- デフォルト: "unspecified"
- `guidance_type`: ガイダンスの種類（"setup"、"networking"、"troubleshooting"）- デフォルト: "setup"
- `networking_question`: ネットワーキングに関する具体的な質問 - デフォルト: "general"

##### esm_kafka_troubleshoot {#esm_kafka_troubleshoot}
接続性、認証、パフォーマンスの問題を含むKafka ESMの問題を診断し、解決する統合トラブルシューティングツールです。

**Parameters:**
- `kafka_type`: Kafkaクラスターの種類（"msk"、"self-managed"、"auto-detect"）- デフォルト: "auto-detect"
- `issue_type`: トラブルシューティングモード - 問題の特定には"diagnosis"、解決手順には具体的な問題の種類（"pre-broker-timeout"、"post-broker-timeout"、"authentication-failed"、"network-connectivity"、"lambda-unreachable"、"on-failure-destination-unreachable"、"sts-unreachable"、"others"）- デフォルト: "diagnosis"

#### 設定および最適化ツール {#configuration-and-optimization-tools}

##### esm_optimize {#esm_optimize}
複数の機能を組み合わせた包括的なESM最適化ツールです。
- `esm_get_config_tradeoff`: ESM設定を分析し、パフォーマンス改善を推奨します
- `esm_validate_configs`: ESMパラメータをAWSサービスの制限とベストプラクティスに照らして検証します
- `esm_generate_update_template`: 最適化されたESM設定を含む完全なSAMテンプレートを作成します

**Parameters:**
- `action`: 最適化アクション（"analyze"、"validate"、"generate_template"）- デフォルト: "analyze"
- `optimization_targets`: 分析の最適化目標（failure_rate、latency、throughput、cost）- "analyze"アクションで必須
- `event_source`: 検証対象のイベントソースの種類（"kinesis"、"dynamodb"、"kafka"、"sqs"）- "validate"アクションで必須
- `configs`: 検証するESM設定 - "validate"アクションで必須
- `esm_uuid`: テンプレート生成用のESM UUID - "generate_template"アクションで必須
- `optimized_configs`: テンプレート生成用の最適化済み設定 - "generate_template"アクションで必須
- `region`: AWSリージョン - デフォルト: "us-east-1"
- `project_name`: テンプレート生成用のプロジェクト名 - デフォルト: "esm-optimization"

## 使用例 {#example-usage}

### SAMによるLambda関数の作成 {#creating-a-lambda-function-with-sam}

ユーザープロンプトの例:

```
I want to build a simple backend for a todo app using Python and deploy it to the cloud with AWS Serverless. Can you help me create a new project called my-todo-app. It should include basic functionality to add and list todos. Once it's set up, please build and deploy it with all the necessary permissions. I don’t need to review the changeset before deployment.
```

このプロンプトにより、AIアシスタントは次の操作を行います。
1. テンプレートを使用して新しいSAMプロジェクトを初期化します。
2. Todoアプリ用にコードとインフラを変更します。
3. SAMアプリケーションをビルドします
4. CAPABILITY_IAM権限でアプリケーションをデプロイします

### Webアプリケーションのデプロイ {#deploying-a-web-application}

ユーザープロンプトの例:

```
I have a full-stack web app built with Node.js called my-web-app, and I want to deploy it to the cloud using AWS. Everything’s ready — both frontend and backend. Can you set it up and deploy it with AWS Lambda so it's live and works smoothly?
```

このプロンプトにより、AIアシスタントはdeploy_webappを使用して、指定された設定でフルスタックアプリケーションをデプロイします。

### EventBridgeスキーマの活用 {#working-with-eventbridge-schemas}

ユーザープロンプトの例:

```
I need to create a Lambda function that processes autoscaling events. Can you help me find the right event schema and implement type-safe event handling?
```

このプロンプトにより、AIアシスタントは次の操作を行います。
1. search_schemaを使用してaws.eventsレジストリ内のオートスケーリングイベントスキーマを検索します
2. describe_schemaを使用して完全なスキーマ定義を取得します
3. スキーマ構造に基づいて型安全なハンドラーコードを生成します
4. 必須フィールドの検証を実装します

### 🏗️ ESMの初期セットアップ {#-initial-esm-setup}

ユーザープロンプトの例:

```
I have a VPC named <your-vpc-name> in <your-aws-region>. Refer to ESM guidance for Kafka and use aws-serverless-mcp-server. Create a script to build a new cluster in the VPC's private subnet by a SAM template. Then, create a lambda function to consumer the stream from the cluster. Prefix created resources with <your prefix>.
```

このプロンプトにより、LLMはESMの初期セットアップを行います。
1. `esm_guidance`を使用してステップバイステップのデプロイ手順を取得します
2. 必要なIAMポリシーとセキュリティグループの設定を生成します
3. 生成されたSAMテンプレートを使用してインフラストラクチャをデプロイします
4. `esm_validate_configs`で設定を検証します

### 🔍 ESMの問題のトラブルシューティング {#-troubleshooting-esm-issues}

ユーザープロンプトの例:

```
I have a cluster called <your-cluster-name> and a consumer lambda function named <your-lambda-function-name> in <your-aws-region>. Look for ESM diagnosis tool to investigate on why I cannot get my ESM trigger working and create a SAM template to update the configurations.
```

このプロンプトにより、LLMはESMの問題をトラブルシューティングします。
1. `esm_kafka_diagnosis`を使用してタイムアウトのシナリオを特定します
2. `esm_kafka_resolution`で対象を絞った解決手順を取得します
3. ネットワーク、セキュリティ、または認証の設定に修正を適用します

### ESM設定の最適化: {#optimizing-esm-configurations}

ユーザープロンプトの例:

```
I have an ESM with UUID <your-esm-uuid> in <your-aws-region>. My target throughput is around 10 MB/s to 100 MB/s, create a script to update the ESM configuration using a SAM template such that the cost from the event pollers is optimized.
```

このプロンプトにより、LLMはESMを最適化します。
1. `esm_get_config_tradeoff`で現在の設定のトレードオフを分析します
2. 目標に基づいて最適化の機会を特定します
3. `esm_validate_configs`によりデプロイ前に提案された変更を検証します

### その他のESM最適化の例 {#additional-esm-optimization-examples}

#### SQSの最適化 {#sqs-optimization}

**ユーザープロンプトの例:**
```
I have an SQS FIFO queue processing financial transactions that must maintain strict ordering. I'm currently processing about 1,000 messages per minute, but I need to scale to 5,000 messages per minute while preserving message order. My current configuration uses BatchSize=1 and no concurrency limits. What's the optimal ESM configuration for FIFO queues?
```

これにより、FIFOキュー向けのESM最適化が実行されます。
1. `esm_optimize`を`event_source="sqs"`および`optimization_targets=["throughput"]`で使用します
2. ツールがBatchSizeとMaximumConcurrencyに関するFIFO固有のガイダンスを提供します
3. メッセージの順序保証を維持しながら最適化された設定を生成します

#### Kinesis Streamのスケーリング {#kinesis-stream-scaling}

**ユーザープロンプトの例:**
```
I have a Kinesis stream that started with 5 shards but has been scaled to 50 shards due to increased traffic. My ESM configuration hasn't been updated since the initial setup: ParallelizationFactor=2, BatchSize=500. I'm now processing 500 MB/s of data, but some shards seem to be processing faster than others, creating uneven load. How should I reconfigure my ESM for the current shard count?
```

これにより、シャードを考慮した最適化が実行されます。
1. `esm_optimize`を`event_source="kinesis"`および`optimization_targets=["throughput", "latency"]`で使用します
2. ツールがシャード数とParallelizationFactorの比率を分析します
3. シャード処理の負荷を均等化するための推奨事項を提供します

#### DynamoDB Streamの耐障害性 {#dynamodb-stream-resilience}

**ユーザープロンプトの例:**
```
My DynamoDB stream processes user profile updates, but occasionally encounters poison records that cause the entire batch to fail. Current configuration: ParallelizationFactor=3, BatchSize=20, no special error handling. When a bad record appears, it blocks processing for that shard until I manually intervene. How can I make my stream processing more resilient to bad records?
```

これにより、耐障害性の最適化が実行されます。
1. `esm_optimize`を`event_source="dynamodb"`および`optimization_targets=["failure_rate"]`で使用します
2. ツールがエラーハンドリングの設定を推奨します
3. BisectBatchOnFunctionErrorとリトライポリシーに関するガイダンスを提供します

#### 低ボリュームSQSのコスト最適化 {#low-volume-sqs-cost-optimization}

**ユーザープロンプトの例:**
```
I have an SQS queue that processes about 100 messages per day, but each message is critical and needs to be processed within 30 seconds. My current setup uses BatchSize=1 and MaximumConcurrency=50, which seems like overkill. How can I optimize for cost while maintaining low latency?
```

これにより、低ボリュームシナリオ向けのコスト最適化が実行されます。
1. `esm_optimize`を`optimization_targets=["cost", "latency"]`で使用します
2. ツールがメッセージ量と同時実行設定を分析します
3. 低スループット・低レイテンシー要件に対してコスト効率の高い設定を提供します

## セキュリティ機能 {#security-features}
1. **AWS認証**: 環境のAWS認証情報を使用して安全に認証します
2. **TLS検証**: すべてのAWS API呼び出しにTLS検証を適用します
3. **リソースタグ付け**: トレーサビリティのために、作成されたすべてのリソースにタグを付けます
4. **最小権限**: CloudFormationテンプレートに適切な権限を持つIAMロールを使用します
5. **データ保護**: ログとレスポンスから機密データ（AWS認証情報、IPアドレス、個人情報）を自動的に除去します
6. **ユーザー確認**: ESMツールは、デプロイやインフラストラクチャの変更の前に、ユーザーの明示的な承認を必要とします
7. **権限コントロール**: `--allow-write`フラグが有効になっていない限り、書き込み操作はデフォルトでブロックされます

## セキュリティに関する考慮事項 {#security-considerations}

### 本番環境のユースケース {#production-use-cases}
AWS Serverless MCPサーバーは、適切なセキュリティコントロールを整備することで本番環境でも使用できます。本番環境でのユースケースでは、以下を考慮してください。

* **デフォルトでの読み取り専用モード**: サーバーはデフォルトで読み取り専用モードで動作し、これは本番環境ではより安全です。書き込みアクセスは必要な場合にのみ明示的に有効にしてください。
* **自動承認の無効化**: AIアシスタントがツールを実行するたびにユーザーの承認を必須にしてください

### ロールスコープの推奨事項 {#role-scoping-recommendations}
セキュリティのベストプラクティスに従うために、次を推奨します。

1. 最小権限の原則に基づき、AWS Serverless MCPサーバーで使用する**専用のIAMロールを作成する**
2. 読み取り専用操作と書き込み操作で**別々のロールを使用する**
3. サーバーが作成したリソースにアクションを限定するために**リソースタグ付けを実装する**
4. サーバーによるすべてのAPI呼び出しを監査するために**AWS CloudTrailを有効にする**
5. サーバーのIAMロールに付与された権限を**定期的にレビューする**
6. 削除可能な未使用の権限を特定するために**IAM Access Analyzerを使用する**

### 機密情報の取り扱い {#sensitive-information-handling}
**重要**: 許可された入力手段を通じて、シークレットや機密情報を渡さないでください。

- CloudFormationテンプレートにシークレットや認証情報を含めないでください
- モデルへのプロンプトに機密情報を直接渡さないでください

### データ保護機能 {#data-protection-features}
サーバーには包括的なデータ保護メカニズムが含まれています。

* **自動データスクラビング**: 機密データは自動的に検出され、ログとレスポンスから削除されます。対象には以下が含まれます:
  - AWS認証情報（アクセスキー、シークレットキー、セッショントークン）
  - ネットワーク情報（IPアドレス、VPC ID、サブネットID）
  - 個人情報（メールアドレス、電話番号）
  - 接続文字列と認証の詳細
* **入力のサニタイズ**: 機密データの漏洩を防ぐため、ユーザー設定はログ記録前にスクラビングされます
* **出力の保護**: すべてのツールレスポンスは、AIモデルに送信される前にスクラビングされます
* **AWS固有の保護**: AWSリソース識別子と設定に対する特別な処理を行います

## リンク {#links}

- [ホームページ](https://awslabs.github.io/mcp/)
- [ドキュメント](https://awslabs.github.io/mcp/servers/aws-serverless-mcp-server/)
- [ソースコード](https://github.com/awslabs/mcp.git)
- [バグトラッカー](https://github.com/awslabs/mcp/issues)
- [変更履歴](https://github.com/awslabs/mcp/blob/main/src/aws-serverless-mcp-server/CHANGELOG.md)

## ライセンス {#license}

Apache-2.0
