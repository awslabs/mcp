---
title: AWS API MCPサーバー
---

## 概要 {#overview}
AWS API MCP Server は、AI アシスタントが AWS CLI コマンドを通じて AWS のサービスやリソースを操作できるようにします。適切なセキュリティコントロールを維持しながら、AWS インフラストラクチャをプログラムから管理するためのアクセスを提供します。

このサーバーは AI アシスタントと AWS サービスの間の橋渡しとして機能し、利用可能なすべてのサービスにわたって AWS リソースの作成、更新、管理を可能にします。AWS CLI コマンドの選択を支援し、AI モデルのナレッジカットオフ日以降にリリースされたものを含む、最新の AWS API の機能やサービスへのアクセスを提供します。


## 前提条件 {#prerequisites}
- 認証情報が適切に設定された AWS アカウントが必要です。設定方法については公式ドキュメント [こちら ↗](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html#configuring-credentials) を参照してください。認証情報の設定には `AWS_API_MCP_PROFILE_NAME` 環境変数の使用を推奨します（詳細は [設定オプション](#%EF%B8%8F-configuration-options) セクションを参照してください）。`AWS_API_MCP_PROFILE_NAME` が指定されていない場合、システムは boto3 のデフォルトの認証情報選択順序に従います。この場合、マシン上に複数の AWS プロファイルが設定されているときは、認証情報チェーンで正しいプロファイルが優先されるようにしてください。
- Python 3.10 以降がインストールされていることを確認してください。[Python 公式サイト](https://www.python.org/downloads/) からダウンロードするか、[pyenv](https://github.com/pyenv/pyenv) などのバージョンマネージャーを使用できます。
- （任意）より高速な依存関係管理と改善された Python 環境の取り扱いのために、[uv](https://docs.astral.sh/uv/getting-started/installation/) をインストールしてください。


## 📦 インストール方法 {#-installation-methods}

ワークフローに最も適したインストール方法を選択し、Kiro、Cursor、Cline など、MCP をサポートするお好みのアシスタントで使い始めましょう。

| Cursor | VS Code | Kiro |
|:------:|:-------:|:----:|
| [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.aws-api-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLWFwaS1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJBV1NfUkVHSU9OIjoidXMtZWFzdC0xIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ%3D%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20API%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-api-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%7D%2C%22type%22%3A%22stdio%22%7D) | [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.aws-api-mcp-server&config=%7B%22command%22%3A%20%22uvx%22%2C%20%22args%22%3A%20%5B%22awslabs.aws-api-mcp-server%40latest%22%5D%2C%20%22disabled%22%3A%20false%2C%20%22autoApprove%22%3A%20%5B%5D%7D) |



### ⚡ uv を使用する {#-using-uv}
MCP クライアントの設定ファイル（例えば Kiro の場合は `~/.kiro/settings/mcp.json`）に以下の設定を追加してください。

**Linux/MacOS ユーザーの場合:**

```json
{
  "mcpServers": {
    "awslabs.aws-api-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.aws-api-mcp-server@latest"
      ],
      "env": {
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
    "awslabs.aws-api-mcp-server": {
      "command": "uvx",
      "args": [
        "--from",
        "awslabs.aws-api-mcp-server@latest",
        "awslabs.aws-api-mcp-server.exe"
      ],
      "env": {
        "AWS_REGION": "us-east-1"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```



### 🐍 Python (pip) を使用する {#-using-python-pip}
> [!TIP]
> MCP サーバーの AWS CLI バージョンがローカルにインストールされているものと一致せず、ダウングレードを引き起こす可能性があるため、
> 仮想環境の使用を推奨します。MCP クライアントの設定ファイルでは、`"command"` を仮想環境内の python 実行ファイルのパスに
> 変更できます（例: `"command": "/workspace/project/.venv/bin/python"`）。

**ステップ 1: パッケージをインストールする**
```bash
pip install awslabs.aws-api-mcp-server
```

**ステップ 2: MCP クライアントを設定する**
MCP クライアントの設定ファイル（例えば Kiro の場合は `~/.kiro/settings/mcp.json`）に以下の設定を追加してください。

```json
{
  "mcpServers": {
    "awslabs.aws-api-mcp-server": {
      "command": "python",
      "args": [
        "-m",
        "awslabs.aws_api_mcp_server.server"
      ],
      "env": {
        "AWS_REGION": "us-east-1"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```



### 🐳 Docker を使用する {#-using-docker}

MCP サーバーを Docker コンテナで実行することで分離できます。Docker イメージは [パブリック AWS ECR レジストリ](https://gallery.ecr.aws/awslabs-mcp/awslabs/aws-api-mcp-server) で入手できます。

```json
{
  "mcpServers": {
    "awslabs.aws-api-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env",
        "AWS_REGION=us-east-1",
        "--volume",
        "/full/path/to/.aws:/app/.aws",
        "public.ecr.aws/awslabs-mcp/awslabs/aws-api-mcp-server:latest"
      ],
      "env": {}
    }
  }
}
```

### 🔧 クローンしたリポジトリを使用する {#-using-cloned-repository}

ローカル開発環境のセットアップとソースからのサーバー実行に関する詳細な手順については、CONTRIBUTING.md ファイルを参照してください。

### 🌐 HTTP モードの設定 {#-http-mode-configuration}

MCP サーバーは streamable HTTP モードをサポートしています。使用するには、以下を設定する必要があります。
- `AWS_API_MCP_TRANSPORT` を `"streamable-http"` に設定
- 認証を無効にしたい場合は `AUTH_TYPE` を `"no-auth"` に設定（それ以外の場合、デフォルトで OAuth が有効になります）

必要に応じて、`AWS_API_MCP_HOST` と `AWS_API_MCP_PORT` でホストとポートを設定できます。

#### Linux/macOS の場合: {#for-linuxmacos}
```bash
AWS_API_MCP_TRANSPORT=streamable-http AUTH_TYPE=no-auth uvx awslabs.aws-api-mcp-server@latest
```

#### Windows（コマンドプロンプト）の場合: {#for-windows-command-prompt}
```cmd
set AWS_API_MCP_TRANSPORT=streamable-http
set AUTH_TYPE=no-auth
uvx awslabs.aws-api-mcp-server@latest
```

#### Windows（PowerShell）の場合: {#for-windows-powershell}
```powershell
$env:AWS_API_MCP_TRANSPORT="streamable-http"
$env:AUTH_TYPE="no-auth"
uvx awslabs.aws-api-mcp-server@latest
```

サーバーが起動したら、以下の設定を使用して接続します（ホストとポート番号が `AWS_API_MCP_HOST` および `AWS_API_MCP_PORT` の設定と一致していることを確認してください）。"

```json
{
  "mcpServers": {
    "awslabs.aws-api-mcp-server": {
      "type": "streamableHttp",
      "url": "http://127.0.0.1:8000/mcp",
      "autoApprove": [],
      "disabled": false,
      "timeout": 60
    }
  }
}
```

**注意**: `AWS_API_MCP_HOST` を別の値に設定している場合は、`127.0.0.1` をカスタムホストに置き換えてください。

### 🔒 HTTP モードのセキュリティに関する考慮事項 {#-http-mode-security-considerations}

**重要**: HTTP モード（`streamable-http`）を使用する場合は、以下のセキュリティに関する考慮事項に注意してください。

- **シングルカスタマーサーバー**: この HTTP モードは**単一顧客での使用のみ**を想定しています。**マルチテナント環境**や複数ユーザーへの同時提供のためには設計されて**いません**
- **認証**: サーバーは `AUTH_TYPE=oauth` を使用して OAuth 認証付きで起動できます。必要に応じて `AUTH_TYPE=no-auth` を設定して認証を無効にできます
- **ネットワークセキュリティコントロール**: 適切なネットワークセキュリティコントロールが実施されていることを確認してください:
  - 可能な場合は localhost（`127.0.0.1`）にバインドする
  - アクセスを制限するファイアウォールルールを設定する
- **転送時の暗号化**: HTTP モードを使用する場合は、転送時の暗号化を追加することを**強く推奨**します:
  - TLS/SSL 証明書を使った HTTPS を使用する
  - 暗号化されていない HTTP 接続で機密データを送信しない

## 🏗️ AgentCore Runtime でのセルフホスト {#️-self-host-on-agentcore-runtime}

AWS API MCP Server を Amazon Bedrock AgentCore にデプロイして、組み込みの認証とセッション分離を備えたマネージドでスケーラブルなホスティングを利用できます。AgentCore は、スケーリング、セキュリティ、インフラストラクチャ管理を自動的に処理するコンテナ化されたランタイム環境を提供します。

詳細は [DEPLOYMENT.md](https://github.com/awslabs/mcp/blob/main/src/aws-api-mcp-server/DEPLOYMENT.md) と [AWS Marketplace](https://aws.amazon.com/marketplace/pp/prodview-lqqkwbcraxsgw) を参照してください。



## ⚙️ 設定オプション {#️-configuration-options}

| 環境変数                                                           | 必須                        | デフォルト                                                | 説明                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
|-------------------------------------------------------------------|----------------------------|----------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `AWS_REGION`                                                      | ❌ いいえ                    | `"us-east-1"`                                            | リクエストで特定のリージョンが指定されない限り、すべての CLI コマンドのデフォルト AWS リージョンを設定します。指定されていない場合、MCP サーバーは boto3 の [設定チェーン](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html#overview) と同様の方法でリージョンを決定しますが、フォールバックとして `us-east-1` を使用します。これにより、必要に応じて異なるリージョンでコマンドを実行できる柔軟性を保ちながら、一貫したデフォルトが提供されます。                                                                                                                                                                        |
| `AWS_API_MCP_WORKING_DIR`                                         | ❌ いいえ                    | \<プラットフォーム固有の一時ディレクトリ\>/aws-api-mcp/workdir | MCP サーバーの操作用の作業ディレクトリパスです。指定する場合は絶対パスである必要があります。`aws s3 cp` などのコマンドで相対パスを解決するために使用されます。サンドボックス化やセキュリティ上の制限は提供しません。`AWS_API_MCP_ALLOW_UNRESTRICTED_LOCAL_FILE_ACCESS` が `"workdir"`（デフォルト）に設定されている場合、ファイル操作はこのディレクトリに制限されます。指定されていない場合、プラットフォーム固有のディレクトリがデフォルトになります:<br/><br/>• **Windows**: `%TEMP%\aws-api-mcp\workdir`（通常は `C:\Users\<username>\AppData\Local\Temp\aws-api-mcp\workdir`）<br/>• **macOS**: `/private/var/folders/<hash>/T/aws-api-mcp/workdir`<br/>• **Linux**: `$XDG_RUNTIME_DIR/aws-api-mcp/workdir`（設定されている場合）、`$TMPDIR/aws-api-mcp/workdir`（設定されている場合）、または `/tmp/aws-api-mcp/workdir` |
| `AWS_API_MCP_ALLOW_UNRESTRICTED_LOCAL_FILE_ACCESS`                | ❌ いいえ                    | `"workdir"`                                              | ファイルシステムへのアクセスレベルを 3 つのモードで制御します:<br/><br/>• `"workdir"`（デフォルト）: ファイル操作を `AWS_API_MCP_WORKING_DIR` に制限します。このモードを使用する場合、このディレクトリ外のパスを含むコマンドは拒否されるため、ユースケースに応じた適切なパスを設定してください。<br/>• `"unrestricted"`: システム全体へのファイルアクセスを有効にします（意図しない上書きが発生する可能性があります）。明示的に必要な場合のみ使用してください。<br/>• `"no-access"`: すべてのローカルファイルパス引数をブロックします。ローカルファイルアクセスを必要とするコマンド（例: `aws s3 cp`、`aws cloudformation package`）は失敗します。S3 URI（`s3://...`）と stdout へのリダイレクト（`-`）は引き続き許可されます。<br/><br/>**非推奨**: ブール値の `"true"` と `"false"` は後方互換性のためにサポートされています。`"true"` の代わりに `"unrestricted"` を、`"false"` の代わりに `"workdir"` を使用してください。 |
| `AWS_API_MCP_PROFILE_NAME`                                        | ❌ いいえ                    | `"default"`                                              | コマンド実行に使用する認証情報の AWS プロファイルです。指定されていない場合、MCP サーバーは boto3 の [デフォルト認証情報チェーン](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html#configuring-credentials) に従って認証情報を探します。この方法で認証情報を設定することを強く推奨します。                                                                                                                                                                                                                                                                            |
| `READ_OPERATIONS_ONLY`                                            | ❌ いいえ                    | `"false"`                                                | "true" に設定すると、実行を読み取り専用操作のみに制限します。IAM のアクセス許可が引き続き主要なセキュリティコントロールです。このフラグで許可される操作の完全な一覧については、[Service Authorization Reference](https://docs.aws.amazon.com/service-authorization/latest/reference/reference_policies_actions-resources-contextkeys.html) を参照してください。これが "true" に設定されている場合、**Access level** 列が `Write` でない操作のみが許可されます。                                                                                                                                                 |
| `REQUIRE_MUTATION_CONSENT`                                        | ❌ いいえ                    | `"false"`                                                | "true" に設定すると、MCP サーバーは読み取り専用**ではない**操作を実行する前に明示的な同意を求めます。この安全メカニズムは [elicitation](https://modelcontextprotocol.io/docs/concepts/elicitation) を使用するため、[elicitation をサポートするクライアント](https://modelcontextprotocol.io/clients) が必要です。                                                                                                                                                                                                                                                                                                   |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` | ❌ いいえ                    | -                                                        | AWS 認証情報を設定するために環境変数を使用します                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `AWS_API_MCP_TELEMETRY`                                           | ❌ いいえ                    | `"true"`                                                 | サーバー設定に関する追加のテレメトリデータを AWS に送信することを許可します。これには、`call_aws()` ツールが `READ_OPERATIONS_ONLY` を true と false のどちらで使用されたかが含まれます。注意: この設定に関係なく、AWS は通常の AWS サービスとのやり取りの一環として、どの操作が呼び出されたかとサーバーバージョンの情報を取得します。この目的のためにサーバーが追加のテレメトリ呼び出しを行うことはありません。                                                                                                                                                                                            |
| `EXPERIMENTAL_AGENT_SCRIPTS`                                      | ❌ いいえ                    | `"false"`                                                | "true" に設定すると、実験的なエージェントスクリプト機能を有効にします。これにより、`get_execution_plan` ツールを通じて、複雑な AWS タスクのための構造化されたステップバイステップのワークフローにアクセスできます。エージェントスクリプトは、複雑なプロセスを自動化し、特定のタスクを達成するための詳細なガイダンスを提供する再利用可能なワークフローです。この機能は実験的であり、将来のリリースで変更される可能性があります。                                                                                                                                                                                                                           |
| `AWS_API_MCP_AGENT_SCRIPTS_DIR`                                   | ❌ いいえ                    | -                                                        | エージェントスクリプト機能用のカスタムユーザースクリプトを含むディレクトリパスです。指定すると、サーバーは組み込みスクリプトに加えて、このディレクトリから追加の `.script.md` ファイルを読み込みます。ディレクトリは存在し、読み取り可能である必要があります。スクリプトは、`description` フィールドを含むフロントマターメタデータを持つ組み込みスクリプトと同じ形式に従う必要があります。これにより、ユーザーは独自のカスタムワークフローでエージェントスクリプト機能を拡張できます。                                                                                                                                                          |
| `AWS_API_MCP_TRANSPORT`                                           | ❌ いいえ                    | `"stdio"`                                                | MCP サーバーのトランスポートプロトコルです。有効なオプションは、ローカル通信用の `"stdio"`（デフォルト）または HTTP ベースの通信用の `"streamable-http"` です。`"streamable-http"` を使用する場合、サーバーは `AWS_API_MCP_HOST` と `AWS_API_MCP_PORT` で指定されたホストとポートでリッスンします。                                                                                                                                                                                                                                                                                                                                |
| `AWS_API_MCP_HOST`                                                | ❌ いいえ                    | `"127.0.0.1"`                                            | `"streamable-http"` トランスポート使用時の MCP サーバーのホストアドレスです。`AWS_API_MCP_TRANSPORT` が `"streamable-http"` に設定されている場合のみ使用されます。                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| `AWS_API_MCP_PORT`                                                | ❌ いいえ                    | `"8000"`                                                 | `"streamable-http"` トランスポート使用時の MCP サーバーのポート番号です。`AWS_API_MCP_TRANSPORT` が `"streamable-http"` に設定されている場合のみ使用されます。                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `AWS_API_MCP_ALLOWED_HOSTS`                                       | ❌ いいえ                    | `AWS_API_MCP_HOST`                                       | HTTP リクエストで許可されるホスト名のカンマ区切りリストです。受信リクエストの `Host` ヘッダーを検証するために使用されます。すべてのホストを許可するには `*` を設定します（本番環境では非推奨）。ポート番号は検証時に自動的に除去されます。`AWS_API_MCP_TRANSPORT` が `"streamable-http"` に設定されている場合のみ使用されます。                                                                                                                                                                                                                                                                                                  |
| `AWS_API_MCP_ALLOWED_ORIGINS`                                     | ❌ いいえ                    | `AWS_API_MCP_HOST`                                       | HTTP リクエストで許可されるオリジンのホスト名のカンマ区切りリストです。受信リクエストの `Origin` ヘッダーを検証するために使用されます。すべてのオリジンを許可するには `*` を設定します（本番環境では非推奨）。ポート番号は検証時に自動的に除去されます。`AWS_API_MCP_TRANSPORT` が `"streamable-http"` に設定されている場合のみ使用されます。                                                                                                                                                                                                                                                                            |
| `AWS_API_MCP_STATELESS_HTTP`                                      | ❌ いいえ                    | `"false"`                                                | ⚠️ **警告: 重大なセキュリティ上の影響があるため、これは "false" のままにしておくことを強く推奨します。** "true" に設定すると、リクエストごとに完全に新しいトランスポートを作成し、リクエスト間でのセッショントラッキングや状態の永続化を行いません。`AWS_API_MCP_TRANSPORT` が `"streamable-http"` に設定されている場合のみ使用されます。                                                                                                                                                                                                                                                                                                      |
| `AUTH_TYPE`                                                       | ❌ いいえ                    | -                                                | `AWS_API_MCP_TRANSPORT` が `"streamable-http"` に設定されている場合のみ使用されます。MCP サーバーの認証タイプです。`"no-auth"` に設定すると認証を無効にします。`"oauth"` に設定すると OAuth 認証を有効にし、`AUTH_ISSUER` と `AUTH_JWKS_URI` の設定が必要になります。                                                                                                                                                                                                                                                                                                                                            |
| `AUTH_ISSUER`                                                     | ❌ いいえ                    | -                                                        | `AWS_API_MCP_TRANSPORT` が `"streamable-http"` に設定されている場合のみ使用されます。JWT トークン検証用の OAuth issuer URL です。JWT トークン内で検証される issuer です。例: `"https://your-auth-provider.com/"`。`AUTH_TYPE` が `"oauth"` に設定されている場合に必須です。                                                                                                                                                                                                                                                                                                                                                        |
| `AUTH_JWKS_URI`                                                   | ❌ いいえ                    | -                                                        | `AWS_API_MCP_TRANSPORT` が `"streamable-http"` に設定されている場合のみ使用されます。JWT トークン検証用の JWKS（JSON Web Key Set）エンドポイント URL です。JWT 署名の検証に使用される JSON Web Key Set を提供する、公開アクセス可能な HTTPS URL である必要があります。例: `"https://your-auth-provider.com/.well-known/jwks.json"`。`AUTH_TYPE` が `"oauth"` に設定されている場合に必須です。                                                                                                                                                                                                                                                         |

### 🚀 クイックスタート {#-quick-start}

設定が完了すると、AI アシスタントに次のような質問ができます。

- **「EC2 インスタンスをすべて一覧表示して」**
- **「us-west-2 の S3 バケットを見せて」**
- **「Web サーバー用の新しいセキュリティグループを作成して」** *（書き込み権限がある場合のみ）*


## 機能 {#features}

- **包括的な AWS CLI サポート**: 最新の AWS CLI バージョンで利用可能なすべてのコマンドをサポートし、最新の AWS サービスと機能へのアクセスを保証します
- **コマンド選択の支援**: AI アシスタントが特定のタスクを達成するために最も適切な AWS CLI コマンドを選択できるよう支援します
- **コマンド検証**: 実行前にすべての AWS CLI コマンドを検証することで安全性を確保し、無効な操作や潜在的に有害な操作を防ぎます
- **ハルシネーション対策**: 実行を有効な AWS CLI コマンドのみに厳密に限定することで、モデルのハルシネーションのリスクを軽減します - 任意のコード実行は許可されません
- **セキュリティファーストの設計**: セキュリティを中核原則として構築されており、AWS インフラストラクチャを保護するための多層防御を提供します
- **読み取り専用モード**: すべての変更操作を無効化する追加のセキュリティレイヤーを提供し、AWS リソースを安全に探索できるようにします


## 利用可能な MCP ツール {#available-mcp-tools}
ツール名は変更される可能性があります。変更については CHANGELOG.md を参照し、それに応じてワークフローを調整してください。

- `call_aws`: 検証と適切なエラーハンドリングを行いながら AWS CLI コマンドを実行します
- `suggest_aws_commands`: 自然言語のクエリに基づいて AWS CLI コマンドを提案します。このツールは、与えられたクエリに対して最も可能性の高い 5 つの CLI コマンドについて、説明と完全なパラメータセットを提供することで、モデルによる CLI コマンドの生成を支援します。これには最新の AWS CLI コマンドも含まれ、その一部は（モデルのナレッジカットオフ日以降にリリースされたため）モデルにとって未知のものである可能性があります。
- `get_execution_plan` *（実験的）*: エージェントスクリプトを通じて、複雑な AWS タスクを達成するための構造化されたステップバイステップのガイダンスを提供します。このツールは、環境変数 `EXPERIMENTAL_AGENT_SCRIPTS` が "true" に設定されている場合にのみ利用可能です。エージェントスクリプトは、複雑なプロセスを自動化し、特定のタスクを達成するための詳細なガイダンスを提供する再利用可能なワークフローです。


## セキュリティに関する考慮事項 {#security-considerations}
この MCP サーバーを使用する前に、その使用が自身の特定のセキュリティおよび品質管理の慣行と基準、ならびに自身とそのコンテンツに適用される法律、規則、規制に準拠することを確認するため、独自の評価を実施することを検討してください。

### ⚠️ マルチテナント環境での使用制限 {#️-multi-tenant-environment-restrictions}

**重要**: この MCP サーバーは**マルチテナント環境向けに設計されていません**。このサーバーを複数のユーザーやテナントに同時に提供するために使用しないでください。

- **シングルユーザーのみ**: MCP サーバーの各インスタンスは、専用の AWS 認証情報を持つ 1 人のユーザーのみに提供されるべきです
- **ディレクトリの分離**: 複数のインスタンスを実行する場合は、`AWS_API_MCP_WORKING_DIR` 環境変数を使用して、インスタンスごとに個別の作業ディレクトリを作成してください

### 🔑 認証情報の管理とアクセス制御 {#-credential-management-and-access-control}

この MCP サーバーが実行できるコマンドの制御には認証情報を使用します。この MCP サーバーは IAM ロールが適切に設定されていることに依存しています。特に以下の点に注意してください。
- `AdministratorAccess` ポリシーを持つ IAM ロール（通常は `Admin` IAM ロール）の認証情報を使用すると、変更を伴うアクション（AWS リソースの作成、削除、変更など）と変更を伴わないアクションの両方が許可されます。
- `ReadOnlyAccess` ポリシーを持つ IAM ロール（通常は `ReadOnly` IAM ロール）の認証情報を使用すると、変更を伴わないアクションのみが許可されます。アカウント内のリソースを確認するだけであればこれで十分です。
- IAM ロールが利用できない場合は、[これらの代替手段](https://docs.aws.amazon.com/cli/v1/userguide/cli-configure-files.html#cli-configure-files-examples) を使用して認証情報を設定することもできます。
- さらなるセキュリティレイヤーを追加するために、ユーザーは MCP 設定ファイルで環境変数 `READ_OPERATIONS_ONLY` を明示的に true に設定できます。true に設定すると、各 CLI コマンドを既知の読み取り専用アクションのリストと比較し、許可リストに含まれる場合にのみコマンドを実行します。「読み取り専用」は API の分類のみを指し、ファイルシステムを指すものではありません。つまり、そのような「読み取り専用」アクションでも、必要に応じて、またはユーザーの要求に応じてファイルシステムへの書き込みが可能です。この環境変数は追加の保護レイヤーを提供しますが、IAM のアクセス許可が引き続き主要かつ最も信頼性の高いセキュリティコントロールです。IAM の認証情報はこの環境変数よりも優先されるため、ユーザーは常にユースケースに応じた適切な IAM ロールとポリシーを設定してください。
- ⚠️ **重要**: `ReadOnlyAccess` IAM ロールを使用すると MCP サーバー経由の書き込み操作はブロックされますが、**一部の AWS の読み取り専用操作は、コマンド出力に AWS 認証情報や機密情報を返す可能性があり**、それらがこのサーバーの外部で使用される可能性があります。

この MCP サーバーはすべての AWS API のサポートを目指しています。ただし、一部の API はサブプロセスを生成し、セキュリティリスクをもたらします。そのような API は拒否リストに登録されます。完全な一覧は以下を参照してください。

| サービス | 操作 |
|---------|------------|
| **deploy** | `install`, `uninstall` |
| **emr** | `ssh`,  `sock`, `get`, `put` |

### ファイルシステムへのアクセスと動作モード {#file-system-access-and-operating-mode}

**重要**: この MCP サーバーは、単一ユーザーの認証情報を使用するローカルサーバーとして、**STDIO モードのみ**での使用を想定しています。サーバーは起動したユーザーと同じ権限で実行され、ファイルシステムへの完全なアクセス権を持ちます。

#### セキュリティとアクセスに関する考慮事項 {#security-and-access-considerations}

- **サンドボックス化なし**: `AWS_API_MCP_WORKING_DIR` 環境変数は作業ディレクトリを設定します。`AWS_API_MCP_ALLOW_UNRESTRICTED_LOCAL_FILE_ACCESS` フラグはデフォルトで `"workdir"` に設定されており、MCP サーバーのファイル操作を `<AWS_API_MCP_WORKING_DIR>` に制限します。`"unrestricted"` に設定するとシステム全体へのファイルアクセスが有効になりますが、意図しない上書きが発生する可能性があります。`"no-access"` に設定するとローカルファイルアクセスが無効になります。
- **ファイルシステムへのアクセス**: サーバーは、ユーザーが権限を持つファイルシステム上の任意の場所に対して読み書きできます。
- **確認プロンプトなし**: ユーザーによる追加の確認なしに、ファイルが変更、上書き、削除される可能性があります
- **ホストファイルシステムの共有**: このサーバーを使用する際、ホストのファイルシステムに直接アクセスできます
- **ネットワーク用途への改変禁止**: このサーバーはローカルの STDIO 使用のみを想定して設計されています。ネットワーク経由での運用は追加のセキュリティリスクをもたらします

#### 一般的なファイル操作 {#common-file-operations}

MCP サーバーは、AWS CLI コマンドを通じて次のようなさまざまなファイル操作を実行できます。

- `aws s3 sync` - 警告なしにディレクトリ全体を上書きする可能性があります
- `aws s3 cp` - 確認なしに既存のファイルを上書きする可能性があります
- `outfile` パラメータを使用するすべての AWS CLI コマンド
- `file://` プレフィックスを使用してファイルから読み取るコマンド

**注意**: `AWS_API_MCP_WORKING_DIR` 環境変数はサーバーの開始場所を設定しますが、ファイルへのアクセス可能な場所を制限するものではありません。

### プロンプトインジェクションと信頼できないデータ {#prompt-injection-and-untrusted-data}
この MCP サーバーは AI モデルの指示に従って AWS CLI コマンドを実行するため、プロンプトインジェクション攻撃に対して脆弱である可能性があります。

- **この MCP サーバーを信頼できないデータを含むデータソースに接続しないでください**（例: 生のユーザーデータを含む CloudWatch ログ、データベース内のユーザー生成コンテンツなど）
- 常に、特定のタスクに必要な最小限の権限に絞り込んだ IAM 認証情報を使用してください。
- プロンプトインジェクションの脆弱性は LLM の既知の問題であり、MCP サーバー自体に起因するものではないことに注意してください。信頼できないデータを扱う場合は、人間による確認を伴うコマンド検証をサポートするクライアントを使用してください。

### ロギング {#logging}

AWS API MCP サーバーは、コマンド実行の監視、問題のトラブルシューティング、デバッグに役立つログを書き込みます。これらのログは自動的にローテーションされ、コマンド実行、エラー、デバッグ情報などの運用データが含まれます。

#### ログファイルの場所 {#log-file-location}

ログは以下の場所にローテーションファイルとして書き込まれます。

- **macOS/Linux**: `<HOME>/.aws/aws-api-mcp/aws-api-mcp-server.log`
- **Windows**: `%USERPROFILE%\.aws\aws-api-mcp\aws-api-mcp-server.log`

#### Amazon CloudWatch Logs へのログの送信 {#shipping-logs-to-amazon-cloudwatch-logs}

より良い監視と分析のためにログを AWS CloudWatch に集約するには、CloudWatch Agent を使用して MCP サーバーのログを CloudWatch ロググループに自動的に送信できます。

**前提条件:**

1. マシンに **CloudWatch Agent をインストール**します:
   - **Amazon Linux 2/2023**: `sudo yum install amazon-cloudwatch-agent`
   - **その他のプラットフォーム**: [CloudWatch Agent ダウンロードページ](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/download-CloudWatch-Agent-on-EC2-Instance-commandline-first.html) からダウンロード
   - **詳細**: [CloudWatch Agent の概要](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Install-CloudWatch-Agent.html)

2. **IAM 権限を設定**します: インスタンスまたはユーザーが CloudWatch Logs への書き込み権限を持っていることを確認してください。`CloudWatchAgentServerPolicy` をアタッチするか、以下の権限を持つカスタムポリシーを作成できます:
   - `logs:CreateLogGroup`
   - `logs:CreateLogStream`
   - `logs:PutLogEvents`

**設定手順:**

1. ログ収集をセットアップするために**設定ウィザードを実行**します。ウィザードは、ロググループ名、ストリーム名、その他の設定をガイドします。ウィザードの詳細なドキュメントについては、[ウィザードを使用して CloudWatch エージェント設定ファイルを作成する](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/create-cloudwatch-agent-configuration-file-wizard.html) を参照してください。:

   **Linux/macOS:**
   ```bash
   sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-config-wizard
   ```

   **Windows:**
   ```cmd
   cd "C:\Program Files\Amazon\AmazonCloudWatchAgent"
   .\amazon-cloudwatch-agent-config-wizard.exe
   ```

2. **ログファイルのパスを求められたら**、MCP サーバーのログの場所を指定します:
   - **macOS**: `/Users/<user>/.aws/aws-api-mcp/aws-api-mcp-server.log`
   - **Linux**: `/home/<user>/.aws/aws-api-mcp/aws-api-mcp-server.log`
   - **Windows**: `C:\Users\<user>\.aws\aws-api-mcp\aws-api-mcp-server.log`

3. 公式 AWS ドキュメントに従って **CloudWatch Agent を起動**します:
   - [CloudWatch エージェントの起動](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/start-CloudWatch-Agent-on-premise-SSM-onprem.html)

#### トラブルシューティング {#troubleshooting}

CloudWatch Agent のセットアップやログ送信で問題が発生した場合は、[CloudWatch エージェントのトラブルシューティング](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/troubleshooting-CloudWatch-Agent.html) を参照してください。

### セキュリティのベストプラクティス {#security-best-practices}

- **最小権限の原則**: 上記の例では簡潔さのために `AdministratorAccess` や `ReadOnlyAccess` などの AWS マネージドポリシーを使用していますが、特定のユースケースに合わせたカスタムポリシーを作成し、最小権限の原則に従うことを**強く**推奨します。
- **最小限の権限**: 最小限の権限から始め、特定のワークフローに必要に応じて段階的にアクセス権を追加してください。
- **条件ステートメント**: セキュリティ要件に基づいて、リージョンやその他の要素によるアクセス制限をさらに強化するために、カスタムポリシーと条件ステートメントを組み合わせてください。
- **信頼できないデータソース**: 信頼できない可能性のあるデータソースに接続する場合は、最小限の権限に絞り込んだ認証情報を使用してください。
- **定期的な監視**: AWS CloudTrail ログを監視して、MCP サーバーが実行したアクションを追跡してください。

### カスタムセキュリティポリシーの設定 {#custom-security-policy-configuration}

IAM のアクセス許可に加えて追加のセキュリティコントロールを定義するために、カスタムセキュリティポリシーファイルを作成できます。MCP サーバーは `~/.aws/aws-api-mcp/mcp-security-policy.json` にあるセキュリティポリシーファイルを探します。

#### セキュリティポリシーファイルの形式 {#security-policy-file-format}

```json
{
  "version": "1.0",
  "policy": {
    "denyList": [],
    "elicitList": []
  }
}
```

#### コマンド形式の要件 {#command-format-requirements}

**重要**: コマンドは、AWS CLI が内部的に使用する正確な形式で指定する必要があります。

- **形式**: `aws <service> <operation>`
- **サービス名**: AWS CLI のサービス名を使用します（例: `s3api`、`ec2`、`iam`、`lambda`）
- **操作名**: ケバブケース形式を使用します（例: `delete-user`、`list-buckets`、`stop-instances`）

#### 正しいコマンド形式の例 {#examples-of-correct-command-formats}

| AWS CLI コマンド | セキュリティポリシーでの形式 |
|-----------------|------------------------|
| `aws iam delete-user --user-name john` | `"aws iam delete-user"` |
| `aws s3api list-buckets` | `"aws s3api list-buckets"` |
| `aws ec2 describe-instances` | `"aws ec2 describe-instances"` |
| `aws lambda delete-function --function-name my-func` | `"aws lambda delete-function"` |
| `aws s3 cp file.txt s3://bucket/` | `"aws s3 cp"` |
| `aws cloudformation delete-stack --stack-name my-stack` | `"aws cloudformation delete-stack"` |

#### ポリシー設定オプション {#policy-configuration-options}

- **`denyList`**: 完全にブロックされる AWS CLI コマンドの配列です。このリストに含まれるコマンドは決して実行されません。
- **`elicitList`**: 実行前にユーザーの明示的な同意を必要とする AWS CLI コマンドの配列です。これには [elicitation](https://modelcontextprotocol.io/docs/concepts/elicitation) をサポートするクライアントが必要です。

#### パターンマッチングとワイルドカード {#pattern-matching-and-wildcards}

**現在の制限**: セキュリティポリシーは**完全一致の文字列マッチングのみ**を使用します。ワイルドカードパターン（`iam:delete-*` や `organizations:*` など）は、現在の実装では**サポートされていません**。

各コマンドは、AWS CLI の形式に現れるとおりに正確に指定する必要があります。包括的にブロックするには、各コマンドを個別に列挙する必要があります。

```json
{
  "version": "1.0",
  "policy": {
    "denyList": [
      "aws iam delete-user",
      "aws iam delete-role",
      "aws iam delete-group",
      "aws iam delete-policy",
      "aws iam delete-access-key"
    ],
    "elicitList": [
      "aws s3api delete-object",
      "aws ec2 stop-instances",
      "aws lambda delete-function",
      "aws rds delete-db-instance",
      "aws cloudformation delete-stack"
    ]
  }
}
```

#### 正しいコマンド形式の確認方法 {#finding-the-correct-command-format}

コマンドの正確な形式を確認するには、次の方法があります。

1. **AWS CLI のドキュメントを確認する**: サービス名と操作名を調べます
2. **ケバブケースを使用する**: キャメルケースの操作名をケバブケースに変換します（例: `ListBuckets` → `list-buckets`）
3. **ログで確認する**: デバッグログを有効にして、コマンドが内部でどのように解析されるかを確認します

#### セキュリティポリシーの優先順位 {#security-policy-precedence}

1. **拒否リスト** - 拒否リストに含まれる操作は完全にブロックされます
2. **同意の要求** - 同意を必要とする操作はユーザーにプロンプトを表示します
3. **IAM のアクセス許可** - 標準の AWS IAM コントロールがすべての操作に適用されます
4. **READ_OPERATIONS_ONLY** - 環境変数による制限（有効な場合）

**注意**: IAM のアクセス許可が引き続き主要なセキュリティコントロールメカニズムです。セキュリティポリシーは追加の保護レイヤーを提供しますが、IAM の制限を上書きすることはできません。

## ライセンス {#license}
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

Apache License, Version 2.0（以下「License」）に基づいてライセンスされています。


## 免責事項 {#disclaimer}
この aws-api-mcp パッケージは、明示または黙示を問わず、いかなる種類の保証もなく「現状のまま」提供され、開発、テスト、評価のみを目的としています。当社は、このパッケージの品質、パフォーマンス、または信頼性についていかなる保証も提供しません。LLM は非決定的であり、間違いを犯します。顧客向けアカウントでこれらのツールを使用する前に、常に十分なテストを行い、所属組織のベストプラクティスに従うことをお勧めします。このパッケージのユーザーは、適切なセキュリティコントロールを実装する責任を単独で負い、AWS リソースへのアクセスを管理するために AWS Identity and Access Management (IAM) を使用しなければなりません（MUST）。適切な IAM ポリシー、ロール、アクセス許可を設定する責任はユーザーにあり、不適切な IAM 設定に起因するセキュリティ上の脆弱性はすべてユーザー自身の責任となります。このパッケージを使用することにより、あなたはこの免責事項を読み、理解した上で、自己の責任においてパッケージを使用することに同意したものとみなされます。
