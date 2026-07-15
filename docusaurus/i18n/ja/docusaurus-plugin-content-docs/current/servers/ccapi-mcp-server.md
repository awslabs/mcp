---
title: "AWS Cloud Control API MCPサーバー"
---

> **⚠️ 非推奨のお知らせ**: このサーバーは非推奨となり、今後アップデートは提供されません。[AWS IAC MCP サーバー](https://github.com/awslabs/mcp/tree/main/src/aws-iac-mcp-server) への移行をお願いします。こちらは CloudFormation および CDK のドキュメントを用いた Infrastructure as Code のオーサリング、テンプレート検証 (cfn-lint)、コンプライアンスチェック (cfn-guard)、デプロイのトラブルシューティングを提供します。ツールごとの詳細な対応関係については [移行ガイド](https://github.com/awslabs/mcp/blob/main/docs/migration-ccapi.md) を参照してください。

AWS Cloud Control API と IaC Generator を使用し、Infrastructure as Code のベストプラクティスに従って、LLM が自然言語を通じて 1,100 以上の AWS リソースを直接作成・管理できるようにする Model Context Protocol (MCP) サーバーです。

## 前提条件 {#prerequisites}

- awslabs/mcp README 内の [Installation and Setup](https://github.com/awslabs/mcp#installation-and-setup) セクションに記載されているすべての前提条件を満たしていること
- 有効な AWS 認証情報
- 使用する IAM ロールまたはユーザーに必要な権限があること（[セキュリティに関する考慮事項](#security-considerations) を参照）

## 機能 {#features}

- **リソースの作成**: 宣言的なアプローチを使用し、Cloud Control API を通じて 1,100 以上の AWS リソースのいずれかを作成
- **リソースの読み取り**: 特定の AWS リソースのすべてのプロパティと属性を読み取り
- **リソースの更新**: 宣言的なアプローチを使用し、既存の AWS リソースに変更を適用
- **リソースの削除**: 適切な検証を行いながら AWS リソースを安全に削除
- **リソースの一覧表示**: AWS 環境全体で指定した種類のすべてのリソースを列挙
- **スキーマ情報**: より効果的な操作を可能にするため、任意のリソースの詳細な CloudFormation スキーマを返す
- **自然言語インターフェース**: Infrastructure as Code を静的なオーサリングから動的な対話へと変換
- **パートナーリソースのサポート**: AWS ネイティブおよびパートナー定義の両方のリソースに対応
- **テンプレート生成**: [一部のリソースタイプ](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/resource-import-supported-resources.html) について、作成済み/既存のリソースからテンプレートを生成

## セキュアなワークフロー {#secure-workflow}

リソースの作成および更新において、サーバーは次のセキュアなワークフローに従います。

1. AWS 認証情報を確認し、アカウント ID とリージョンをユーザーに表示する
2. プロパティと CloudFormation テンプレートを含むインフラストラクチャコードを生成する
3. **設定内容を説明する** - 何が作成/変更されるかをユーザーに正確に提示する
4. テンプレートに対してセキュリティスキャンを実行する（SECURITY_SCANNING=enabled の場合）
5. チェックに合格した場合（またはセキュリティスキャンが無効で警告が表示された場合）、AWS Cloud Control API でリソースの作成/更新を試みる
6. 追跡およびサポートのため、リソースにデフォルトの管理タグを自動的に追加する
7. リソースが正常に作成/更新されたことを検証する
8. セキュリティ警告を含め、実行された内容の概要を提供する
9. （オプション）作成または更新したばかりのリソースに対応する IaC テンプレートを作成する

このワークフローにより、以下が保証されます。

- **完全な透明性**: `explain()` ステップを通じて、実行前に何が作成/変更されるかをユーザーが正確に把握できる
- **セキュリティ検証**: リソースは作成/変更の前にセキュリティ問題についてスキャンされる（有効な場合、デフォルト設定）
- **インフォームドコンセント**: ユーザーが設定内容を理解しないまま誤ってリソースを作成することを防止
- **監査証跡**: 追跡およびサポートのため、デフォルトの管理タグが自動的に適用される
- **柔軟なセキュリティ**: 環境のニーズに応じてセキュリティスキャンを有効/無効にできる
- **IaC の保全**: ユーザーは Infrastructure as Code を保全するオプションを持つ
- **複数のフォーマット**: 最大限の柔軟性のために複数の IaC フォーマットがサポートされる

## セキュリティアーキテクチャ {#security-architecture}

この MCP サーバーは、以下を保証するトークンベースのワークフローシステムを使用します。

- **順次検証**: 各ステップは次のステップに進む前に完了している必要がある
- **サーバー側での強制**: トークンはサーバー側で生成・検証される
- **バイパス不可**: AI エージェントはセキュリティステップをスキップしたり、認証情報を偽装したりできない
- **監査証跡**: すべての操作はトークンチェーンを通じて追跡される

これにより、AI エージェントがセキュリティスキャン、認証情報チェック、ユーザーへの説明をバイパスすることを防止します。

## セキュリティ保護 {#security-protections}

この MCP サーバーは、いくつかの重要なセキュリティ保護を実装しています。

### 認証情報の認識 {#credential-awareness}

- CREATE/UPDATE 操作の前には常に AWS アカウント ID とリージョンを表示する
- どのアカウントが変更の影響を受けるかをユーザーが認識できるようにする

### 削除に対するセーフガード {#deletion-safeguards}

- リソースの削除には二重の確認を必須とする
- AWS インフラストラクチャの大量削除を防止する
- クリーンアップ操作では、直接削除する代わりに IaC Generator を使用してテンプレートを作成する
- より優れた制御とロールバックオプションを備えた、より安全な代替手段を提供する

### ポリシーの制限 {#policy-restrictions}

- 過度に許容的な IAM ポリシーの作成をブロックする
- プリンシパルとして "AWS": "\*" を持つ設定を防止する
- "Effect": "Allow" と "Action": "_" および "Resource": "_" の組み合わせをブロックする
- 機密性の高いリソースへのパブリックアクセスの要求を拒否する
- 機密データに対する暗号化の無効化を防止する

## 認証 {#authentication}

この MCP サーバーは、その主な目的がインフラストラクチャを管理できるようにすることであるため、AWS アカウントへの認証を必要とします。認証には以下のような複数のオプションがあります。

### AWS プロファイル {#aws-profile}

これは AWS CLI で `aws configure` を実行し、指示に従うことで設定できます。

### 環境変数 {#environment-variables}

環境変数（AWS_ACCESS_KEY_ID、AWS_SECRET_ACCESS_KEY、AWS_REGION）をエクスポートして設定できます。

## 環境変数 {#environment-variables-1}

この MCP サーバーは、その動作を制御するためのいくつかの環境変数をサポートしています。

### AWS の設定 {#aws-configuration}

| 変数          | デフォルト             | 説明                                       |
| ------------- | ---------------------- | ------------------------------------------ |
| `AWS_REGION`  | _(以下の優先順位を参照)_ | 操作を実行する AWS リージョン              |
| `AWS_PROFILE` | _(空)_                 | 認証に使用する AWS プロファイル名          |

**AWS リージョンの解決順序:**

この MCP サーバーは boto3 の標準的なリージョン解決チェーンに従います（優先度が高い順）。

1. **関数引数**: MCP ツールに渡される `region` パラメータ（最高優先度）
2. **AWS_REGION 環境変数**: 環境を通じて明示的に設定されたリージョン
3. **AWS プロファイルのリージョン**: アクティブなプロファイルの `~/.aws/config` に設定されているリージョン
4. **デフォルトのフォールバック**: 最終的なフォールバックとしての `us-east-1`

これにより、他の AWS ツールや SDK との一貫した動作が保証されます。リージョンの解決は boto3 の認証情報チェーンによって自動的に処理されます。

**AWS_REGION を設定する場合:**

- **リージョンを上書きする場合**: デフォルトとは異なるリージョンを使用したいとき
- **環境変数を使用する場合**: `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` を使用しており、`us-east-1` を使いたくないとき
- **プロファイル/SSO を使用する場合**: プロファイルに設定されたリージョンを上書きしたいとき
- **不要な場合**: AWS プロファイル/SSO を使用しており、プロファイルに設定されたリージョンを使いたいとき、または `us-east-1` で問題ないとき

### AWS 認証情報チェーン {#aws-credential-chain}

サーバーは boto3 の標準的な認証情報チェーンを自動的に使用します。

1. 環境変数（`AWS_ACCESS_KEY_ID`、`AWS_SECRET_ACCESS_KEY`）
2. `~/.aws/credentials` または `~/.aws/config` の AWS プロファイル
3. IAM ロール（EC2 インスタンス、ECS タスク、EKS ポッド）
4. AWS SSO（プロファイルで設定されている場合）

**SSO トークンの管理**: SSO トークンの有効期限が切れた場合、サーバーは `aws sso login --profile your-profile` でトークンを更新するための明確な手順を提供します。

### サーバーの設定 {#server-configuration}

| 変数                | デフォルト  | 説明                                                                                                                                       |
| ------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `FASTMCP_LOG_LEVEL` | _(未設定)_  | ログレベル（ERROR、WARN、INFO、DEBUG）                                                                                                     |
| `SECURITY_SCANNING` | `enabled`   | Checkov のセキュリティスキャンを有効/無効にする（`enabled` または `disabled`）。無効にすると警告を表示するが、リソース操作の続行を許可する。 |

### デフォルトのタグ付け {#default-tagging}

サーバーは、サポートされているすべてのリソースに以下の識別タグを自動的に追加します。

- `MANAGED_BY`: `CCAPI-MCP-SERVER`
- `MCP_SERVER_SOURCE_CODE`: `https://github.com/awslabs/mcp/tree/main/src/ccapi-mcp-server`
- `MCP_SERVER_VERSION`: `1.0.0`（現在のバージョン）

これらのタグは、サポートおよびトラブルシューティングの目的で、MCP サーバーによって作成されたリソースを識別するのに役立ちます。ユーザーは LLM との対話を通じて、追加のカスタムタグを付与できます。

### AWS アカウント情報の表示 {#aws-account-information-display}

サーバーは起動時に AWS アカウント情報を自動的に表示します。

- **AWS プロファイル**: 使用されているプロファイル（存在する場合）
- **認証タイプ**: どのように認証されているか（SSO プロファイル、標準 AWS プロファイル、環境変数、Assume Role プロファイル）
- **AWS アカウント ID**: AWS アカウント ID
- **AWS リージョン**: リソースが作成されるリージョン
- **読み取り専用モード**: サーバーが読み取り専用モードであるかどうか
- **セキュリティスキャン**: Checkov のセキュリティスキャンが有効かどうか

これにより、どの AWS アカウントとリージョンが操作の影響を受けるか、またどのようなセキュリティ対策が講じられているかを常に把握できます。

## インストール {#installation}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.ccapi-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.ccapi-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.ccapi-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuY2NhcGktbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiQVdTX1BST0ZJTEUiOiJ5b3VyLWF3cy1wcm9maWxlIiwiQVdTX1JFR0lPTiI6InVzLWVhc3QtMSIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20Cloud%20Control%20API%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.ccapi-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

**インストール前に、以下のいずれかの方法で AWS 認証情報を設定してください。**

- **AWS プロファイル**: `aws configure` を実行し、`AWS_PROFILE` 環境変数を設定する（プロファイルのリージョンが自動的に使用される）
- **環境変数**: `AWS_ACCESS_KEY_ID`、`AWS_SECRET_ACCESS_KEY` をエクスポートする（デフォルトは `us-east-1`、上書きするには `AWS_REGION` を設定する）
- **AWS SSO**: SSO プロファイルを設定し、`AWS_PROFILE` を設定する（プロファイルのリージョンが自動的に使用される）
- **インスタンスロール**: EC2 インスタンスロールまたは ECS タスクロールを使用する（自動検出、`AWS_REGION` が必要な場合がある）

使用する IAM ロールまたはユーザーに必要な権限があることを確認してください（[セキュリティに関する考慮事項](#security-considerations) を参照）。

### 設定 {#configuration}

MCP クライアントの設定で MCP サーバーを設定します（例: Kiro の場合は `~/.kiro/settings/mcp.json` を編集）。

```json
{
  "mcpServers": {
    "awslabs.ccapi-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.ccapi-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-named-profile",
        "DEFAULT_TAGS": "enabled",
        "SECURITY_SCANNING": "enabled",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```
### Windows でのインストール {#windows-installation}

Windows ユーザーの場合、MCP サーバーの設定形式は少し異なります。

```json
{
  "mcpServers": {
    "awslabs.ccapi-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.ccapi-mcp-server@latest",
        "awslabs.ccapi-mcp-server.exe"
      ],
      "env": {
        "AWS_PROFILE": "your-named-profile",
        "DEFAULT_TAGS": "enabled",
        "SECURITY_SCANNING": "enabled",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```


_注: AWS プロファイルのデフォルトリージョンを使用します。上書きするには `"AWS_REGION": "us-west-2"`（または任意の AWS リージョン）を追加してください。_

**セキュリティスキャンを無効にする場合:**

作成/更新前のすべてのインフラストラクチャに対する Checkov のセキュリティスキャンを有効/無効にするかを制御できます。以下の設定によりセキュリティスキャンが無効になります。

```json
{
  "mcpServers": {
    "awslabs.ccapi-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.ccapi-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-named-profile",
        "DEFAULT_TAGS": "enabled",
        "SECURITY_SCANNING": "disabled",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

**その他の設定例:**

**AWS IAM Identity Center 経由で SSO を使用する場合:**

```json
{
  "mcpServers": {
    "awslabs.ccapi-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.ccapi-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-sso-profile",
        "DEFAULT_TAGS": "enabled",
        "SECURITY_SCANNING": "enabled",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

_注: MCP サーバーを起動する前に `aws sso login --profile your-sso-profile` を実行してください_

**認証情報に環境変数を使用する場合:**

```json
{
  "mcpServers": {
    "awslabs.ccapi-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.ccapi-mcp-server@latest"],
      "env": {
        "AWS_REGION": "us-west-2",
        "DEFAULT_TAGS": "enabled",
        "SECURITY_SCANNING": "enabled",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

_注: シェルで AWS_ACCESS_KEY_ID と AWS_SECRET_ACCESS_KEY がエクスポートされていることを確認してください_

**読み取り専用モード（セキュリティ機能）:**

MCP サーバーがいかなる変更操作（Create/Update/Delete）も実行しないようにするには、`--readonly` コマンドラインフラグを使用します。これは環境変数ではバイパスできないセキュリティ機能です。なお、これが以下の例で `DEFAULT_TAGS` および `SECURITY_SCANNING` 環境変数が省略されている理由です。仮にそれらが存在していたとしても、`--readonly` フラグがあらゆる CREATE/UPDATE/DELETE 操作を防止するため、これらの環境変数は無意味になります。

```json
{
  "mcpServers": {
    "awslabs.ccapi-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.ccapi-mcp-server@latest", "--readonly"],
      "env": {
        "AWS_PROFILE": "your-named-profile",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

または、`docker build -t awslabs/ccapi-mcp-server .` が成功した後の docker を使用する場合:

```file
# fictitious `.env` file with AWS temporary credentials
AWS_ACCESS_KEY_ID=ASIAIOSFODNN7EXAMPLE  # pragma: allowlist secret
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY  # pragma: allowlist secret
AWS_SESSION_TOKEN=AQoEXAMPLEH4aoAH0gNCAPy...truncated...zrkuWJOgQs8IZZaIv2BXIa2R4Olgk  # pragma: allowlist secret
```

```json
{
  "mcpServers": {
    "awslabs.ccapi-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env-file",
        "/full/path/to/file/above/.env",
        "awslabs/ccapi-mcp-server:latest",
        "--readonly" // Optional paramter if you would like to restrict the MCP to only read actions
      ],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

注: 認証情報はホストから継続的に更新しておく必要があります

## 利用可能な MCP ツール {#available-mcp-tools}

**ツールの順序とワークフローの強制**: これらのツールは、適切なワークフロー順序を強制するパラメータ依存関係を持つように設計されています。LLM は、環境セットアップ → セキュリティ検証 → リソース操作という論理的なシーケンスに従う必要があります。これにより、セキュリティのバイパスを防止し、適切な認証情報の検証を保証します。

### コアツール {#core-tools}

#### check_environment_variables() {#check_environment_variables}

**要件**: なし（開始点）

AWS 認証情報が AWS_PROFILE または環境変数を通じて適切に設定されているかを確認します。認証情報のソース、認証タイプ、設定ステータスに関する詳細情報を返します。
**例**: 操作を実行する前に AWS 認証情報が利用可能であることを確認する。
**戻り値**: `get_aws_session_info()` で使用する `environment_token`、および環境変数、AWS プロファイル、リージョン、認証タイプ（sso_profile、standard_profile、assume_role_profile、env）、設定ステータス。

#### get_aws_session_info() {#get_aws_session_info}

**要件**: `check_environment_variables()` からの `environment_token` パラメータ

アカウント ID、リージョン、認証情報のソース、およびセキュリティのためにマスクされた認証情報を含む、現在の AWS セッションに関する詳細情報を提供します。
**例**: どの AWS アカウントとリージョンが操作の影響を受けるかを表示する。
**使用するタイミング**: 詳細なセッション情報が必要で、すでに `check_environment_variables()` を呼び出している場合。
**セキュリティ**: 機密性の高い認証情報を自動的にマスクします（末尾の 4 文字のみを表示）。
**戻り値**: `generate_infrastructure_code()` で使用する `credentials_token`

#### get_aws_account_info() {#get_aws_account_info}

**要件**: なし（内部で `check_environment_variables()` を呼び出す）

内部で `check_environment_variables()` を自動的に呼び出し、次に `get_aws_session_info()` を呼び出す便利なツールです。同じ情報を返しますが、パラメータは不要です。
**例**: 「どの AWS アカウントを使用していますか?」- ワンステップで素早くアカウント情報を取得。
**使用するタイミング**: 最初に `check_environment_variables()` を呼び出すことなく、素早くアカウント情報を取得したい場合。

#### generate_infrastructure_code() {#generate_infrastructure_code}

**要件**: `get_aws_session_info()` からの `credentials_token` パラメータ

Cloud Control API 操作用のリソースプロパティを準備し、デフォルトの管理タグを適用し、セキュリティスキャン用の CloudFormation 形式テンプレートを生成します。**重要**: CloudFormation サービスは一切関与しません。テンプレートはセキュリティ分析のために Checkov によってのみ使用されます。

**一貫性の保証**: まったく同じプロパティオブジェクトが、（Checkov スキャン用の）CF テンプレートと、（CCAPI 操作のために）`create_resource()`/`update_resource()` に渡される両方で使用されます。これにより、セキュリティスキャンされる対象がデプロイされる対象と同一であることが保証されます。

**例**: S3 バケットのプロパティを処理し、デフォルトタグを適用し、Checkov 用の CF 形式テンプレートを作成し、次に同じプロパティを CCAPI リソース作成に使用する。
**戻り値**: `explain()` で使用する `generated_code_token`、セキュリティスキャン用の CloudFormation テンプレート、および説明用のプロパティ。
**ワークフロー**: generate_infrastructure_code() → explain() → run_checkov()（有効な場合）→ create_resource()。

#### explain() {#explain}

**要件**: `generate_infrastructure_code()` からの `generated_code_token`（インフラストラクチャ操作用）または `content` パラメータ（一般的な説明用）

あらゆるデータを明確で人間が読める形式で説明します。インフラストラクチャ操作の場合、このツールは `generated_code_token` を消費し、作成/更新/削除操作に使用する必要がある `explained_token` を返します。

**インフラストラクチャワークフロー**:

- `generate_infrastructure_code()` から `generated_code_token` を受け取る
- 何が作成/更新/削除されるかについての包括的な説明を提供する
- `create_resource()`/`update_resource()`/`delete_resource()` で使用する `explained_token` を返す
- **セキュリティ**: 実行前に何が作成/変更されるかをユーザーが正確に確認できるようにする。

**一般的なデータの説明**:

- `content` パラメータに任意のデータを渡す
- JSON、YAML、辞書、リスト、API レスポンス、設定を説明する
- トークンワークフローは不要

**例**: 既存のバケットを取得する際に S3 バケットの設定を説明する、または一般的な API レスポンスデータを説明する。

#### run_checkov() {#run_checkov}

**要件**: `explain()` からの `explained_token`

サーバーに保存された CloudFormation テンプレートに対して Checkov セキュリティ・コンプライアンススキャナーを実行します。ユーザーが確認するためのスキャン結果を返します。

**セキュリティ検証の動作は SECURITY_SCANNING 環境変数によって異なります**:

- **SECURITY_SCANNING=enabled の場合**: このツールは必須であり、ユーザーが確認するためのスキャン結果を返す
- **SECURITY_SCANNING=disabled の場合**: 警告を表示し、セキュリティ検証なしで続行する

**例**: `run_checkov(explained_token)` - セキュリティスキャン結果を返す。
**戻り値**: `create_resource()` で使用する `security_scan_token`（セキュリティスキャンが有効な場合）、および詳細なスキャン結果。

### リソース変更ツール (CRUDL) {#resource-modification-tools-crudl}

#### create_resource() {#create_resource}

**要件**: `get_aws_session_info()` からの `credentials_token` および `explain()` からの `explained_token`

**セキュリティ要件**:

- SECURITY_SCANNING=enabled の場合: `run_checkov()` からの `security_scan_token` が必要
- SECURITY_SCANNING=disabled の場合: セキュリティ警告を表示するが、検証トークンなしで続行する

宣言的なアプローチで AWS Cloud Control API を使用して AWS リソースを作成します。追跡およびサポートのため、デフォルトの管理タグを自動的に追加します。
**例**: バージョニングと暗号化を有効にした S3 バケットを作成する。
**セキュリティ**: `explain()` ツールを通じてユーザーに説明されたプロパティのみを使用します。

#### get_resource() {#get_resource}

**要件**: なし

AWS Cloud Control API を使用して、特定の AWS リソースの詳細を取得します。
**例**: EC2 インスタンスの設定を取得する。
**戻り値**: リソース識別子と詳細なプロパティ。

#### update_resource() {#update_resource}

**要件**: `get_aws_session_info()` からの `credentials_token` および `explain()` からの `explained_token`

**セキュリティ要件**:

- SECURITY_SCANNING=enabled の場合: `run_checkov()` からの `security_scan_token` が必要
- SECURITY_SCANNING=disabled の場合: セキュリティ警告を表示するが、検証トークンなしで続行する

RFC 6902 JSON Patch 操作を使用して、AWS Cloud Control API で AWS リソースを更新します。
**例**: RDS インスタンスのストレージ容量を更新する。
**セキュリティ**: 実行前に `explain()` ツールを通じた変更内容の説明が必要です。

#### delete_resource() {#delete_resource}

**要件**: `get_aws_session_info()` からの `credentials_token` および `explain()` からの `explained_token`

AWS Cloud Control API を使用して AWS リソースを削除します。削除される内容についての明示的な確認と説明が必要です。
**例**: 未使用の NAT ゲートウェイを削除する。
**セキュリティ**: `explain()` ツールを通じた削除の影響の説明と明示的な確認が必要です。

#### list_resources() {#list_resources}

**要件**: なし

AWS Cloud Control API を使用して、指定した種類の AWS リソースを一覧表示します。
**例**: リージョン内のすべての EC2 インスタンスを一覧表示する。

### ユーティリティツール {#utility-tools}

#### get_resource_schema_information() {#get_resource_schema_information}

**要件**: なし

AWS CloudFormation リソースのスキーマ情報を取得します。
**例**: 利用可能なすべてのプロパティを理解するために AWS::S3::Bucket のスキーマを取得する。

#### get_resource_request_status() {#get_resource_request_status}

**要件**: 作成/更新/削除操作からの `request_token`

作成/更新/削除リソースによって開始された変更のステータスを取得します。
**例**: 直近に行ったリクエストのステータスを教えて。

#### create_template() {#create_template}

**要件**: なし（ただし通常はリソース操作の後に使用される）

AWS CloudFormation の IaC Generator API を使用して、既存の AWS リソースから CloudFormation テンプレートを作成します。**現在は JSON または YAML 形式の CloudFormation テンプレートのみを生成します**。この MCP ツールは Terraform や CDK などの他の IaC 形式を直接生成することはできませんが、LLM はそのネイティブ機能を使用して、生成された CloudFormation テンプレートを他の形式に変換できます。ただし、この変換は MCP サーバーのスコープ外で行われます。
**例**: 既存の S3 バケットと EC2 インスタンスから CloudFormation YAML テンプレートを生成し、その後 LLM に Terraform HCL への変換を依頼する。

### トークンワークフローの概要 {#token-workflow-summary}

**作成/更新操作のワークフロー例:**

1. `check_environment_variables()` → `environment_token`
2. `get_aws_session_info(environment_token)` → `credentials_token`
3. `generate_infrastructure_code(credentials_token)` → `generated_code_token`
4. `explain(generated_code_token)` → `explained_token`
5. `run_checkov(explained_token)` → `security_scan_token`（SECURITY_SCANNING=enabled の場合）
6. `create_resource(credentials_token, explained_token, security_scan_token)`

**トークン不要のツール:** `get_resource()`、`list_resources()`、`get_resource_schema_information()`、`create_template()`、`get_aws_account_info()`

## LLM ツール選択のガイドライン {#llm-tool-selection-guidelines}

**重要**: 複数の MCP サーバーを使用する場合、LLM はどれが最も適切かを考慮せずに、利用可能な任意のサーバーからツールを選択することがあります。MCP には現時点で組み込みのオーケストレーションや強制メカニズムがないため、LLM は任意のサーバーの任意のツールを自由に使用できます。

### 一般的なツール選択の競合 {#common-tool-selection-conflicts}

- **複数のインフラストラクチャ MCP サーバー**: CCAPI MCP サーバーを、同様の機能を実行する他の MCP サーバー（Terraform MCP、CDK MCP、CFN MCP など）と併用すると、LLM がそれらの間でランダムに選択する可能性があります
- **組み込みツール**: LLM はこの MCP サーバーのツールの代わりに組み込みツールを選択することがあります:
  - Kiro CLI: `aws`、`shell`、`read`、`write`
  - その他のツールにも同様の組み込み AWS またはシステム機能がある場合があります

## 基本的な使い方 {#basic-usage}

AWS Infrastructure as Code MCP サーバーの使用例:

- 「バージョニングと暗号化を有効にした新しい S3 バケットを作成して」
- 「本番環境内のすべての EC2 インスタンスを一覧表示して」
- 「RDS インスタンスのストレージを 500GB に増やすように更新して」
- 「VPC-123 内の未使用の NAT ゲートウェイを削除して」
- 「Web、アプリ、データベースの各層からなる 3 層アーキテクチャをセットアップして」
- 「us-east-1 にディザスタリカバリ環境を作成して」
- 「すべての本番リソースに CloudWatch アラームを設定して」
- 「重要な S3 バケットにクロスリージョンレプリケーションを実装して」
- 「AWS::Lambda::Function のスキーマを見せて」
- 「作成・変更したすべてのリソースのテンプレートを作成して」

## リソースタイプのサポート {#resource-type-support}

この MCP でサポートされているリソースとサポートされている操作は、こちらで確認できます: https://docs.aws.amazon.com/cloudcontrolapi/latest/userguide/supported-resources.html

## セキュリティに関する考慮事項 {#security-considerations}

この MCP サーバーを使用する際は、以下を考慮してください。

- 使用前に適切な IAM 権限が設定されていることを確認する
- 追加のセキュリティ監視のために AWS CloudTrail を使用する
- 可能な場合はワイルドカード権限の代わりにリソース固有の権限を設定する
- より良いガバナンスとコスト管理のためにリソースのタグ付けを利用することを検討する
- 定期的なセキュリティレビューの一環として、MCP サーバーによって行われたすべての変更をレビューする
- MCP を読み取り専用操作に制限したい場合は、MCP の起動引数で --readonly True を指定する

### 必要な IAM 権限 {#required-iam-permissions}

AWS 認証情報に以下の最小限の権限があることを確認してください。

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudcontrol:ListResources",
        "cloudcontrol:GetResource",
        "cloudcontrol:CreateResource",
        "cloudcontrol:DeleteResource",
        "cloudcontrol:UpdateResource",
        "cloudformation:CreateGeneratedTemplate",
        "cloudformation:DescribeGeneratedTemplate",
        "cloudformation:GetGeneratedTemplate"
      ],
      "Resource": "*"
    }
  ]
}
```

## 今後の機能拡張 {#future-enhancements}

- **IaC フォーマット変換**: `create_template` ツールにおいて、CloudFormation テンプレートを他の IaC フォーマット（Terraform HCL、CDK TypeScript、CDK Python）に変換するサポートを追加

## 制限事項 {#limitations}

- 操作は AWS Cloud Control API および IaC Generator でサポートされているリソースに限定されます
- パフォーマンスは基盤となる AWS サービスの応答時間に依存します
- 一部の複雑なリソース間の関係では、複数の操作が必要になる場合があります
- この MCP サーバーは、Cloud Control API および/または IaC Generator が利用可能な AWS リージョンでのみリソースを管理できます
- リソース変更操作は、サービス固有の制約によって制限される場合があります
- 多数のリソースを同時に管理する場合、レート制限が操作に影響を与える可能性があります
- 一部のリソースタイプは、すべての操作（作成、読み取り、更新、削除）をサポートしていない場合があります
- 生成されるテンプレートは、主に既存のリソースを CloudFormation スタックにインポートすることを目的としており、（別のアカウントやリージョンで）新しいリソースを作成する際には常に機能するとは限りません
- テンプレート生成は現在 CloudFormation フォーマット（JSON/YAML）のみをサポートしています
