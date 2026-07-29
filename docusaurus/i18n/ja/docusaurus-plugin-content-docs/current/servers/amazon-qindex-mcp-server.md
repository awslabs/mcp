---
title: AWS Labs amazon-qindex MCP Server
---

AWS Labs amazon-qindex MCP Server は、Amazon Q Business の [SearchRelevantContent API](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/isv-calling-api-idc.html) との統合を容易にするために設計された Model Context Protocol (MCP) サーバーです。このサーバーは Amazon Q index を使用した認証と検索機能のための必須ツールと機能を提供しますが、現時点では [AWS 登録データアクセサー](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/isv.html)である独立系ソフトウェアベンダー (ISV) を対象としています。このサーバーはクロスアカウント検索機能を実現し、データアクセサーである ISV が、特定の認証・認可フローを使用して、エンタープライズ顧客の Q index を検索し、そのデータソース全体から関連コンテンツにアクセスできるようにします。

Amazon Q Business アプリケーションの所有者向けの直接統合サポートはまだ提供されていません。この MCP サーバーは、ISV への提供を目的とした包括的なソリューションです。

## 機能 {#features}

- Q Business とのやり取りのための Boto3 クライアント実装
- さまざまな認証方式(IAM 認証情報、プロファイルベース)のサポート
- Q index リクエストを処理する MCP サーバー実装
- トークンベースの認可サポート
- Q Business API レスポンスのエラー処理とマッピング

## ツール {#tools}

#### AuthorizeQIndex {#authorizeqindex}
- Q index 認証用の OIDC 認可 URL を生成します
- 必須パラメータ:
  - idc_region (str): IAM Identity Center の AWS リージョン(例: us-west-2)
  - isv_redirect_url (str): ISV 登録時に登録したリダイレクト URL
  - oauth_state (str): CSRF 保護用のランダム文字列
  - idc_application_arn (str): Amazon Q Business アプリケーション ID
- 戻り値: ユーザー認証用の認可 URL

#### CreateTokenWithIAM {#createtokenwithiam}
- IAM を通じて認可コードを使用し、認証トークンを作成します
- 必須パラメータ:
  - idc_application_arn (str): Amazon Q Business アプリケーション ID
  - redirect_uri (str): 登録済みのリダイレクト URL
  - code (str): OIDC エンドポイントからの認可コード
  - idc_region (str): IAM Identity Center の AWS リージョン
  - role_arn (str): 引き受ける IAM ロールの ARN
- 戻り値: アクセストークン、リフレッシュトークン、有効期限を含むトークン情報

#### AssumeRoleWithIdentityContext {#assumerolewithidentitycontext}
- トークンから取得したアイデンティティコンテキストを使用して IAM ロールを引き受けます
- 必須パラメータ:
  - role_arn (str): 引き受ける IAM ロールの ARN
  - identity_context (str): デコードされたトークンから取得したアイデンティティコンテキスト
  - role_session_name (str): セッション識別子(デフォルト: "qbusiness-session")
  - idc_region (str): IAM Identity Center の AWS リージョン
- 戻り値: 一時的な AWS 認証情報

#### SearchRelevantContent {#searchrelevantcontent}
- Amazon Q Business アプリケーション内のコンテンツを検索します
- 必須パラメータ:
  - application_id (str): Q Business アプリケーションの識別子
  - query_text (str): 検索クエリのテキスト
- オプションパラメータ:
  - attribute_filter (AttributeFilter): ドキュメント属性フィルター
  - content_source (ContentSource): コンテンツソースの設定
  - max_results (int): 返される結果の最大数 (1-100)
  - next_token (str): ページネーショントークン
  - qbuiness_region (str): AWS リージョン(デフォルト: us-east-1)
  - aws_credentials: 一時的な AWS 認証情報
- 戻り値: 関連コンテンツにマッチした検索結果

## セットアップ {#setup}

### 前提条件 {#pre-requisites}
- [Astral](https://docs.astral.sh/uv/getting-started/installation/) または [GitHub README](https://github.com/astral-sh/uv#installation) から `uv` をインストールします
- `uv python install 3.10` を使用して Python をインストールします

- 2 つの AWS アカウント(このテスターアプリケーションを実行する ISV としてのアカウントと、Amazon Q Business を実行するエンタープライズ顧客としてのアカウント)
- [ISV 用に登録されたデータアクセサー](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/isv-info-to-provide.html)
- エンタープライズ顧客の AWS アカウントに、ユーザーを追加した IAM Identity Center (IDC) インスタンスのセットアップ
- エンタープライズ顧客の AWS アカウントに、IAM IDC をアクセス管理として設定した Amazon Q Business アプリケーションのセットアップ


### インストール {#installation}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.amazon-qindex-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-qindex-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%2C%22QINDEX_ID%22%3A%22your-qindex-id%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.amazon-qindex-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYW1hem9uLXFpbmRleC1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJBV1NfUkVHSU9OIjoidXMtZWFzdC0xIiwiUUlOREVYX0lEIjoieW91ci1xaW5kZXgtaWQiLCJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ%3D%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Amazon%20Q%20Index%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-qindex-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%2C%22QINDEX_ID%22%3A%22your-qindex-id%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

MCP クライアントの設定で MCP サーバーを設定します(例: Kiro の場合は `~/.kiro/settings/mcp.json` を編集します)。

```json
{
  "mcpServers": {
    "awslabs.amazon_qindex_mcp_server": {
      "command": "uvx",
      "args": ["awslabs.amazon_qindex_mcp_server"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```
### Windows でのインストール {#windows-installation}

Windows ユーザーの場合、MCP サーバーの設定形式が若干異なります。

```json
{
  "mcpServers": {
    "awslabs.amazon-qindex-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.amazon-qindex-mcp-server@latest",
        "awslabs.amazon-qindex-mcp-server.exe"
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


```bash
# Clone the repository
git clone [repository-url]

# Go to root directory of this server
cd <your repo path>/mcp/src/amazon-qindex-mcp-server/

# Install dependencies
pip install -e .
```

## 使用方法 {#usage}

1. エンタープライズデータから何をクエリしたいかを説明するテキストプロンプトを入力します

```
search <your query> on enterprise data
```

2. SearchRelevantContent API を処理するための認証フローを進めるには、以下の詳細情報も提供する必要があります

```
application id - (enterprise account's Amazon Q Business application ID)
retriever id - (enterprise account's Amazon Q Business retriever ID)
iam idc arn - (enterprise account's IdC application ARN)
idc region - (Region for the IAM Identity Center instance)
qbuiness region - (enterprise account's Amazon Q Business application region)
redirect url - (ISV's redirect url - this could be anything within allowlisted for the data accessor - ie https://localhost:8081)
iam role arn - (ISV's IAM Role ARN registered with the data accessor)
```

3. 上記 2 つのステップで情報を提供すると、ブラウザで認可 URL にアクセスするよう求められます。認証に成功して URL パラメータに認可コードを含むリダイレクト URL に移動したら(`?code=ABC123...&state=xxx` のような形式になります)、コード部分をコピーしてクライアントに貼り付け、処理を再開します。

```
code is <your authorization code>
```

4. その後、この MCP サーバーは CreateTokenWithIAM で認証トークンを作成し、AssumeRoleWithIdentityContext でロールを引き受けて一時認証情報を取得し、最後に SearchRelevantContent を呼び出して、ユーザーがクエリしたコンテンツを Amazon Q Business アプリケーション内で検索します。

## テスト {#testing}

pytest を使用してテストを実行します。
```
pytest --cache-clear -v
```

## セキュリティに関する考慮事項 {#security-considerations}

この MCP サーバーの実装は、ユーザーを認識した認証を用いて MCP サーバー経由で SearchRelevantContent API にアクセスする方法を示すデモンストレーション目的のものです。本番環境で使用する場合は、以下のセキュリティ対策を検討してください。

### 認証と認可 {#authentication--authorization}
- 認証情報や機密情報をコードにハードコーディングしない
- 適切なセッション管理とトークン更新の仕組みを実装する
- OAuth フローに強力な CSRF 保護の仕組みを使用する
- すべての認可コードとトークンの適切な検証を実装する
- トークンを安全に保管し、決してログに記録しない
- セッション終了時に適切なトークン失効処理を実装する
