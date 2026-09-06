---
title: AWS Transform MCPサーバー
---

[![PyPI Downloads](https://static.pepy.tech/personalized-badge/awslabs-aws-transform-mcp-server?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads)](https://pepy.tech/projects/awslabs-aws-transform-mcp-server) [![PyPI Downloads/month](https://static.pepy.tech/personalized-badge/awslabs-aws-transform-mcp-server?period=month&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads/month)](https://pepy.tech/projects/awslabs-aws-transform-mcp-server)

[AWS Transform](https://aws.amazon.com/transform/) 向けのMCPサーバーで、AIアシスタントがIDEから直接、変換ワークスペース、ジョブ、コネクタ、ヒューマンインザループ (HITL) タスク、アーティファクト、チャットを管理できるようにします。

AWS Transformは、発見、計画、実行の各段階にわたって特化型AIエージェントを活用し、エンタープライズワークロードの移行とモダナイゼーションを加速します。このMCPサーバーは、19個のツールを通じてTransformのライフサイクルを公開し、メインフレームモダナイゼーション、VMware移行、.NETモダナイゼーション、カスタムコード変換をサポートします。

> [!IMPORTANT]
> このサーバーはstdioトランスポートを使用し、MCPクライアントによって起動される長時間稼働プロセスとして動作します。

## 機能 {#features}

1. **ワークスペースとジョブの管理** - 変換ワークスペースおよびジョブの作成、開始、停止、削除
2. **ヒューマンインザループタスク** - 完全なコンポーネント検証、出力スキーマ、レスポンステンプレートを備えたHITLタスクへの応答
3. **アーティファクトの取り扱い** - 最大500 MBのアーティファクト (JSON、ZIP、PDF、HTML、TXT) のアップロードとダウンロード
4. **コネクタ管理** - S3およびコードソースコネクタの作成、プロファイルの管理、IAMロールの関連付けによるコネクタの承認
5. **チャット** - 自動レスポンスポーリング付きでTransformアシスタントへメッセージを送信
6. **ジョブステータスとポーリング** - AI生成のサマリーまたは詳細な生スナップショットによるジョブステータスの確認、遷移状態に対するアダプティブポーリング
7. **リソースの閲覧** - ワークスペース、ジョブ、コネクタ、タスク、アーティファクト、ワークログ、プラン、エージェント、コラボレーター、ユーザーなど、あらゆるリソースの一覧表示と確認

## 前提条件 {#prerequisites}

1. [Python](https://www.python.org/) 3.10以降
2. テナントへのアクセス権を持つ [AWS Transform](https://aws.amazon.com/transform/) アカウント

## インストール {#installation}

### クイックスタート {#quick-start}

```bash
uvx awslabs.aws-transform-mcp-server@latest
```

### MCPクライアントの設定 {#configure-your-mcp-client}

<details>
<summary>Claude Code</summary>

```bash
claude mcp add awslabs.aws-transform-mcp-server -- uvx awslabs.aws-transform-mcp-server@latest
```

</details>

<details>
<summary>Kiro</summary>

`~/.kiro/settings/mcp.json` に追加します:

```json
{
  "mcpServers": {
    "awslabs.aws-transform-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-transform-mcp-server@latest"],
      "env": {
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

</details>

<details>
<summary>Claude Desktop</summary>

お使いのOSに応じた設定ファイルを編集します:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

macOS/Linuxの場合:

```json
{
  "mcpServers": {
    "awslabs.aws-transform-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-transform-mcp-server@latest"],
      "env": {
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

Windowsの場合:

```json
{
  "mcpServers": {
    "awslabs.aws-transform-mcp-server": {
      "command": "uvx",
      "args": [
        "--from",
        "awslabs.aws-transform-mcp-server@latest",
        "awslabs.aws-transform-mcp-server.exe"
      ],
      "env": {
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false
    }
  }
}
```

</details>

<details>
<summary>Cursor / VS Code / Cline</summary>

MCP設定ファイル (`.cursor/mcp.json`、`.vscode/mcp.json`、またはClineのMCP設定) に追加します:

macOS/Linuxの場合:

```json
{
  "mcpServers": {
    "awslabs.aws-transform-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-transform-mcp-server@latest"],
      "env": {
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

Windowsの場合:

```json
{
  "mcpServers": {
    "awslabs.aws-transform-mcp-server": {
      "command": "uvx",
      "args": [
        "--from",
        "awslabs.aws-transform-mcp-server@latest",
        "awslabs.aws-transform-mcp-server.exe"
      ],
      "env": {
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false
    }
  }
}
```

</details>

### Windowsでのインストール {#windows-installation}

Windowsユーザーの場合、MCPサーバーの設定形式が少し異なります:

```json
{
  "mcpServers": {
    "awslabs.aws-transform-mcp-server": {
      "command": "uvx",
      "args": [
        "--from",
        "awslabs.aws-transform-mcp-server@latest",
        "awslabs.aws-transform-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_REGION": "us-east-1"
      },
      "disabled": false
    }
  }
}
```

### 動作確認 {#verify}

設定後、MCPクライアントを再起動して次のように尋ねてください: **「AWS Transformの接続ステータスを確認して」**。アシスタントは `get_status` を呼び出し、サーバーのバージョンと認証状態を返します。

## 認証 {#authentication}

ほとんどのツールは **Transform Web API認証** (ブラウザログイン) を必要とします。1つのツール (`accept_connector`) は加えて **AWS認証情報** を必要としますが、これは環境から自動的に検出されます。

### Web API認証 (必須) {#web-api-auth-required}

以下のいずれかを選択してください:

#### SSO / IAM Identity Center (推奨) {#sso--iam-identity-center-recommended}

AIアシスタントに次のように依頼します: **「AWS TransformをSSOで設定して」**

ツールはIdCスタートURL (例: `https://d-xxx.awsapps.com/start`) の入力を求め、ログイン用のブラウザウィンドウを開き、認証情報を `~/.aws-transform-mcp/config.json` に保存します。トークンは再起動時に自動的に読み込まれます。

#### セッションCookie {#session-cookie}

1. [AWS Transformコンソール](https://aws.amazon.com/transform/) にログインします
2. DevTools (F12) を開き、**Application** > **Cookies** を選択します
3. セッションCookieの値をコピーします
4. AIアシスタントに **「AWS TransformをCookie認証で設定して」** と依頼し、Cookieとテナント URLを提供します

### AWS認証情報による認証 (自動検出) {#aws-credential-auth-auto-detected}

`accept_connector` などのControl Planeツールで必要です。

AWS認証情報は環境から自動的に検出されるため、ツールの呼び出しは不要です。特定のプロファイルを選択するには、MCPクライアント設定の `env` ブロックで `AWS_PROFILE` を設定します。一時トークンの有効期限が切れると、認証情報は自動的に更新されます。

起動時に、サーバーはサポートされているすべてのリージョンを検査します。複数のリージョンにアクティブなプロファイルがある場合は、`switch_profile` を使用して使用するリージョンを選択してください。

認証情報が機能しているか確認するには、AIアシスタントに **「AWS Transformの接続ステータスを確認して」** と依頼します。`get_status` がSTS経由で検証を行い、アカウントID、ARN、解決されたTCPエンドポイントを表示します。

> [!IMPORTANT]
> `accept_connector` ツールは、Web API認証とAWS認証情報の **両方** を必要とします。

## 利用可能なツール {#available-tools}

### 設定 {#configuration}

| ツール | 説明 | 認証 |
|------|-------------|------|
| `configure` | セッションCookieまたはSSO/IdCベアラートークンで接続します。 | なし |
| `get_status` | すべての接続ステータスを確認し、STS経由でAWS認証情報を検証し、サーバーのバージョンを表示します。 | なし |
| `switch_profile` | 認証情報が有効なプロファイルが複数検出された場合に、利用可能なリージョンを切り替えます。 | Web API |

### ワークスペース管理 {#workspace-management}

| ツール | 説明 | 認証 |
|------|-------------|------|
| `create_workspace` | 新しい変換ワークスペースを作成します。 | Web API |
| `delete_workspace` | ワークスペースを完全に削除します。`confirm: true` が必要です。 | Web API |

### ジョブ管理 {#job-management}

| ツール | 説明 | 認証 |
|------|-------------|------|
| `create_job` | 変換ジョブを作成して即時に開始します。利用可能なエージェントを確認するには `list_resources(resource="agents")` を使用します。 | Web API |
| `control_job` | 既存のジョブを開始または停止します。 | Web API |
| `delete_job` | ジョブを完全に削除します。`confirm: true` が必要です。 | Web API |

### HITLタスク管理 {#hitl-task-management}

| ツール | 説明 | 認証 |
|------|-------------|------|
| `complete_task` | 検証、ファイルアップロード、送信を伴うHITLタスクを処理します。サポートするアクション: APPROVE、REJECT、SEND_FOR_APPROVAL、SAVE_DRAFT。TOOL_APPROVALタスク (エージェントのツール実行リクエスト) ではAPPROVEとREJECTのみが有効で、アーティファクトのアップロードは自動的にスキップされます。 | Web API |
| `upload_artifact` | ファイル (JSON、ZIP、PDF、HTML、TXT) をアーティファクトとしてアップロードします。最大500 MB。 | Web API |

### チャット {#chat}

| ツール | 説明 | 認証 |
|------|-------------|------|
| `send_message` | Transformアシスタントにメッセージを送信し、最大60秒間返信をポーリングします。タイムアウト時は、後で取得できるよう `sentMessageId` を返します。 | Web API |

### ジョブステータスとポーリング {#job-status-and-polling}

| ツール | 説明 | 認証 |
|------|-------------|------|
| `get_job_status` | 実行中のジョブのステータスを確認します。デフォルトでは、Transformアシスタントに簡潔なサマリーを問い合わせます。完全な生スナップショット (ワークログ、タスク、メッセージ、プランステップ) を取得するには `detailed=true` を渡します。 | Web API |
| `adaptive_poll` | 指定された時間待機してから、フォローアップメッセージを返します。リソースが遷移状態にあるときに使用します。API呼び出しは行わず、スリープするだけです。 | なし |

### ジョブの指示 {#job-instructions}

| ツール | 説明 | 認証 |
|------|-------------|------|
| `load_instructions` | ジョブに取り組む前に必ず呼び出す必要があります。アーティファクトストアをスキャンしてワークフローの指示を探し、見つかった場合はダウンロードします。このツールが呼び出されるまで、他のジョブスコープのツールは `INSTRUCTIONS_REQUIRED` でブロックされます。 | Web API |

### コネクタ {#connectors}

| ツール | 説明 | 認証 |
|------|-------------|------|
| `create_connector` | ワークスペースにS3またはコードソースコネクタを作成します。 | Web API |
| `accept_connector` | コネクタにIAMロールを関連付けます。 | Web API + AWS認証情報 |

### リソースの一覧と詳細 {#resource-listing-and-details}

| ツール | 説明 | 認証 |
|------|-------------|------|
| `list_resources` | あらゆるリソースタイプを一覧表示します: ワークスペース、ジョブ、コネクタ、タスク、アーティファクト、メッセージ、ワークログ、プラン、エージェント、コラボレーター、ユーザー。保留中のツール承認を一覧表示するには、`category="TOOL_APPROVAL"` と `taskStatus="AWAITING_APPROVAL"` を使用します。 | Web API |
| `get_resource` | IDを指定して任意のリソースの詳細を取得します。アーティファクトを自動ダウンロードし、HITLタスクに出力スキーマを付加します。 | Web API |

### コラボレーター {#collaborators}

| ツール | 説明 | 認証 |
|------|-------------|------|
| `manage_collaborator` | ワークスペースのコラボレーターを追加または削除します。 | Web API |

## サポートされている変換タイプ {#supported-transformation-types}

- **アセスメント** - 移行準備状況の評価
- **メインフレームモダナイゼーション** - IBM z/OSおよび富士通GS21からJavaへの変換 (COBOL、JCL、CICS、DB2、VSAM)
- **VMware移行** - アプリケーションの発見、依存関係のマッピング、ネットワーク変換、ウェーブ計画、EC2へのサーバーリホスト
- **.NETモダナイゼーション** - .NET FrameworkからLinux向けクロスプラットフォーム.NETへの変換
- **フルスタックWindows** - アプリケーション (.NET) + SQL Server + デプロイのエンドツーエンドなモダナイゼーション
- **カスタム変換** - Javaアップグレード、Node.js、Python、APIおよびフレームワークの移行、言語間変換

## 設定 {#configuration-1}

### 永続化される設定 {#persisted-configuration}

認証状態は `~/.aws-transform-mcp/config.json` に保存され、再起動時に自動的に読み込まれます。これには認証モード、トークン、テナントURL、リージョンが含まれます。

### 環境変数 {#environment-variables}

MCPクライアント設定の `env` ブロックで以下を設定します:

| 変数 | 必須 | デフォルト | 説明 |
|----------|----------|---------|-------------|
| `AWS_PROFILE` | いいえ | `default` プロファイル | Control Planeツール (例: `accept_connector`) に使用する `~/.aws/credentials` のAWSプロファイル。複数のAWSプロファイルがある場合は、Transformアカウントへのアクセス権を持つものを設定してください。未設定の場合、boto3は `[default]` プロファイルを使用し、次に環境変数 (`AWS_ACCESS_KEY_ID`)、その次にインスタンスメタデータにフォールバックします。完全な解決順序については [boto3 credential chain](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html#configuring-credentials) を参照してください。 |
| `AWS_REGION` | いいえ | プロファイルのリージョン、次に `us-east-1` | Control Plane API呼び出しに使用するAWSリージョン。未設定の場合、AWSプロファイル (`~/.aws/config`) のリージョンを使用し、次に `us-east-1` にフォールバックします。 |
| `FASTMCP_LOG_LEVEL` | いいえ | `INFO` | MCPサーバーのログレベル (`DEBUG`、`INFO`、`WARNING`、`ERROR`)。 |

## HITLタスクレスポンスシステム {#hitl-task-response-system}

`resource="task"` を指定して `get_resource` でタスクを取得すると、レスポンスには以下が含まれます:

- **`_outputSchema`** - フィールドの説明、型、列挙値、必須フィールドを含むJSON Schema
- **`_responseTemplate`** - スキーマに合致する具体的なレスポンス例
- **`_responseHint`** - レスポンスを構築するための人間が読める形式のガイダンス

実行時にフィールドが定義されるコンポーネント (AutoForm、DynamicHITLRenderEngine) については、サーバーがエージェントアーティファクトから動的スキーマを構築するため、フィールド名は常に正確です。

> [!IMPORTANT]
> ユーザーによる明示的なレビューなしにHITLタスクのレスポンスを自動送信しないでください。必ずタスクの詳細とエージェントアーティファクトをユーザーに提示し、ユーザーの判断を待ってから `complete_task` を呼び出してください。

## トラブルシューティング {#troubleshooting}

| 問題 | 原因 | 解決策 |
|-------|-------|----------|
| `AccessDeniedException: INVALID_SESSION` | セッションCookieの期限切れ | DevTools > Application > Cookies から再度コピーする |
| サーバーが起動しない | Python 3.10以降がない、依存関係の不足 | `python --version` が3.10以上であることを確認し、`uvx awslabs.aws-transform-mcp-server@latest` を再実行する |
| 結果が空 | 認証が未設定またはIDが誤っている | `get_status` を実行して認証を確認し、ワークスペース/ジョブIDを確認する |
| SSOトークンの期限切れ | ベアラートークンの有効期間超過 | SSOで `configure` を再実行して更新する |

## 制限事項 {#limitations}

- **Cookie認証のセッションは期限切れになります** - 自動更新はありません。定期的にブラウザから再度コピーしてください。
- **SSOトークンは期限切れになります** - ツールが認証エラーを返した場合は、SSO設定を再実行してください。

## セキュリティ {#security}

### アーキテクチャ {#architecture}

このMCPサーバーはユーザーのマシン上で **ローカルプロセス** として動作し、**stdio** (stdin/stdout) を介してMCPクライアントと通信します。ネットワークリスナー、HTTPサーバー、オープンポートは一切公開しません。すべてのアウトバウンド通信は、AWSが管理するTransform APIエンドポイントへのHTTPSを使用します。

### 認証と認証情報の保存 {#authentication-and-credential-storage}

サーバーは3つの認証モードをサポートし、いずれも呼び出し元自身の認証情報を使用します:

- **セッションCookie** — Transform Web API用のユーザーのブラウザセッションCookie
- **SSO / OAuthベアラートークン** — PKCEを使用してIAM Identity Center経由で取得され、期限切れ前に自動更新されます
- **SigV4** — Transform Control Plane API用の標準AWS認証情報チェーン

トークンを含む設定は `~/.aws-transform-mcp/config.json` に永続化され、`0o700` のディレクトリ内に `0o600` のパーミッションでアトミックに書き込まれます (一時ファイル + リネーム)。SigV4認証情報は標準のAWS認証情報チェーン (`boto3`) を通じて解決されます。

### 転送時の暗号化 {#encryption-in-transit}

すべてのアウトバウンドHTTP呼び出しは **HTTPS** のみを使用します。APIエンドポイントはハードコードされた `https://` プレフィックスから導出され、`http://` URLを構築または受け入れるコードパスは存在しません。TLS証明書の検証は `httpx` と `certifi` によりデフォルトで有効です。

### 認証情報の持ち出し防止 {#credential-exfiltration-prevention}

サーバーは、ツールの誤用による認証情報の持ち出しを防ぐため、機密性の高いファイルやディレクトリへの読み書きをブロックします:

- **ブロックされるファイル名:** `.env`、`.netrc`、`.pgpass`、SSHキー (`id_rsa`、`id_ed25519` など)、`credentials`、`authorized_keys` など
- **ブロックされるディレクトリ:** `~/.aws`、`~/.ssh`、`~/.gnupg`、`~/.docker`、`~/.aws-transform-mcp`
- **パストラバーサル防止:** すべてのファイルパスは解決され、ディレクトリ境界に対して検証されます
- **拡張子の許可リスト:** 承認されたファイル拡張子のみダウンロードできます

### 監査ログ {#audit-logging}

すべてのツール呼び出しは、サニタイズされた引数とともにログに記録されます。機密性の高いパラメータ (`secret`、`password`、`credential`、`token`、`cookie`、`content`、`clientSecretArn`、`startUrl`) はログ出力から自動的に除外されます。監査ログはフォールトトレラントであり、ログ処理の失敗がツールの実行をブロックすることはありません。

### ファイルダウンロードの安全性 {#file-download-safety}

アーティファクトのダウンロードでは以下が強制されます:
- パストラバーサルチェック (解決されたパスがターゲットディレクトリの外に出てはいけません)
- ブロック対象ファイル名のチェック
- 拡張子の許可リスト (json、pdf、html、txt、csv、md、zip、gz、tar、yaml、xmlなど)

## VPC設定 {#vpc-configuration}

サーバーはAWSが管理するエンドポイントへアウトバウンドHTTPS呼び出しを行います。直接のインターネットアクセスがないVPC内のインスタンスで実行する場合は、これらのエンドポイントに到達できることを確認してください。

> [!IMPORTANT]
> サーバーはインバウンドポートを一切開きません。MCPクライアントとのすべての通信はstdio経由です。必要なのはアウトバウンドTCP 443のみです。

### 必要なエンドポイント {#required-endpoints}

サーバーは以下のエンドポイントに接続します。`{region}` はお使いのAWSリージョン (例: `us-east-1`) に置き換えてください。

**コアAPI:**

| エンドポイント | 用途 | PrivateLinkサービス名 |
|----------|---------|--------------------------|
| `api.transform.{region}.on.aws` | Transform API — ジョブ、ワークスペース、アーティファクト、チャット | `com.amazonaws.{region}.api.transform` |
| `transform.{region}.api.aws` | TCP — コネクタ、プロファイル、エージェント | `com.amazonaws.{region}.transform` |

これらのサービス名の詳細については [AWS Transform and interface VPC endpoints](https://docs.aws.amazon.com/transform/latest/userguide/vpc-interface-endpoints.html) を参照してください。

**認証:**

| エンドポイント | 用途 | PrivateLinkサービス名 |
|----------|---------|--------------------------|
| `oidc.{region}.amazonaws.com` | SSO OIDCトークンの交換と更新 | なし — NAT Gatewayが必要 |
| `sts.{region}.amazonaws.com` | 認証情報の検証、コネクタ操作 | `com.amazonaws.{region}.sts` |

**アーティファクトストレージ:**

| エンドポイント | 用途 | PrivateLinkサービス名 |
|----------|---------|--------------------------|
| `*.s3.{region}.amazonaws.com` | 署名付きURLによるアップロードとダウンロード | `com.amazonaws.{region}.s3` (Gateway) |

サーバーはS3を直接呼び出さず、Transform APIから返される署名付きURLを使用します。ドメインは仮想ホスト形式 (`{bucket}.s3.{region}.amazonaws.com`) になる場合があります。

**SSOブラウザログイン** (SSO認証での `configure` 実行時のみ):

| エンドポイント | 用途 |
|----------|---------|
| `oidc.{region}.amazonaws.com` | OAuth認可リダイレクト |
| `portal.sso.{region}.amazonaws.com` | SSOポータルログイン |
| `assets.sso-portal.{region}.amazonaws.com` | SSOポータル静的アセット |
| `{directory-id}.awsapps.com` | IAM Identity Centerポータル |
| `{region}.signin.aws` | SSOサインインリダイレクト |

これらのドメインは [Accessing the AWS Transform web application from a VPC](https://docs.aws.amazon.com/transform/latest/userguide/vpc-webapp-access.html) に記載されています。AWS認証情報による認証 (SigV4) では、これらのブラウザ用エンドポイントは不要です。

### VPCエンドポイント {#vpc-endpoints}

NAT Gatewayなしでプライベート接続を行うには、以下のエンドポイントを作成します。サービス名は [AWS Transform and interface VPC endpoints](https://docs.aws.amazon.com/transform/latest/userguide/vpc-interface-endpoints.html) に記載されています。

| サービス名 | 用途 | プライベートDNS |
|--------------|---------|-------------|
| `com.amazonaws.{region}.api.transform` | Transform API | 必須 |
| `com.amazonaws.{region}.transform` | Control Plane | 任意 |
| `com.amazonaws.{region}.sts` | STS | 任意 |
| `com.amazonaws.{region}.s3` | S3 (Gateway) | 該当なし |

> [!IMPORTANT]
> `com.amazonaws.{region}.api.transform` エンドポイントにはプライベートDNSの有効化が必要です。有効化しないと、`api.transform.{region}.on.aws` がパブリックIPに解決され、API呼び出しは接続タイムアウトで失敗します。

SSO OIDCとSSOポータルはPrivateLinkをサポートしていません。これらにはNAT GatewayまたはHTTPプロキシを使用してください。

### セキュリティグループ {#security-groups}

**インスタンス (プライベートサブネット)** — `0.0.0.0/0` へのアウトバウンドTCP 443 (またはVPCエンドポイントENIとNAT Gatewayにスコープ)。

**VPCエンドポイントENI** — プライベートサブネットCIDRからのインバウンドTCP 443。

### Network Firewall (制御されたエグレス) {#network-firewall-controlled-egress}

厳格なドメインベースのフィルタリングを行うには、TLS SNI検査を備えたAWS Network Firewallをデプロイします。[VPC web application access guide](https://docs.aws.amazon.com/transform/latest/userguide/vpc-webapp-access.html) では以下がカバーされています:

- ドメイン許可リストを持つステートフルルールグループ
- プライベート、ファイアウォール、パブリックサブネット間の対称ルーティング
- 各サブネット層のルートテーブル設定
- 検証用コマンド

推定基本コスト: AZあたり月額約325ドル (Network Firewall + NAT Gateway + Elastic IP)。最新の料金は [AWS Network Firewall pricing](https://aws.amazon.com/network-firewall/pricing/) を参照してください。

### トラブルシューティング {#troubleshooting-1}

| 問題 | 原因 | 解決策 |
|-------|-------|----------|
| Transform API呼び出しの接続タイムアウト | VPCエンドポイントがない、またはプライベートDNSが無効 | プライベートDNSを有効にして `com.amazonaws.{region}.api.transform` を作成する |
| TCP呼び出しの接続タイムアウト | TCPエンドポイントへのルートがない | `com.amazonaws.{region}.transform` エンドポイントを作成するか、NAT Gatewayルートを追加する |
| SSOトークンの更新失敗 | OIDCエンドポイントに到達できない | NAT Gatewayが `oidc.{region}.amazonaws.com` にルーティングしているか確認する |
| アーティファクトのアップロード/ダウンロード失敗 | S3に到達できない | S3 Gateway Endpointを作成し、ルートテーブルのエントリを確認する |
| `api.transform.{region}.on.aws` のDNSがパブリックIPを返す | プライベートDNSが有効になっていない | VPCエンドポイントを削除し、**Enable DNS name** を選択して再作成する |

インスタンスからの接続確認:

```bash
# Should return a private IP address if VPC endpoint is configured
nslookup api.transform.us-east-1.on.aws

# Should return HTTP 403 or similar (confirms network path works)
curl -v --connect-timeout 15 'https://api.transform.us-east-1.on.aws/'

# Should return account info (confirms STS reachability)
aws sts get-caller-identity

# Should list buckets (confirms S3 Gateway Endpoint)
aws s3 ls --region us-east-1
```

## ライセンス {#license}

このプロジェクトはApache-2.0ライセンスの下でライセンスされています。
