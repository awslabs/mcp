---
title: "AWS Bedrock AgentCore MCPサーバー"
---

Amazon Bedrock AgentCore 向けの Model Context Protocol (MCP) サーバーです。AI コーディングエージェントが AgentCore のリソースを直接管理できるようにする運用 API ツールを提供します。

## 概要 {#overview}

この MCP サーバーは、AI エージェント（Claude Code、Kiro、Cursor、VS Code、Codex CLI）に AgentCore プラットフォーム API への直接アクセスを提供します。エージェントは、ランタイムの作成と管理、メモリの保存と取得、アイデンティティプロバイダーの設定、ゲートウェイのデプロイ、ポリシーの管理をすべて標準的な MCP ツール呼び出しを通じて行えます。これらはすべて実際の boto3 API 呼び出しに支えられています。

7 つの運用プリミティブ + ドキュメント検索にまたがる **122 個のツール**。

|プリミティブ         |ツール数|機能                                                                                           |
|--------------------|----:|-----------------------------------------------------------------------------------------------|
|**Runtime**         |14   |エージェントランタイムとエンドポイントのデプロイ、管理、呼び出し                                |
|**Memory**          |21   |メモリリソースの作成、イベントの保存、セマンティック検索、バッチ操作、抽出ジョブ                |
|**Identity**        |21   |ワークロードアイデンティティ、API キープロバイダー、OAuth2 プロバイダー、トークンボールト、リソースポリシーの管理|
|**Gateway**         |15   |API ゲートウェイ、ゲートウェイターゲット、リソースポリシーの作成と管理                          |
|**Policy**          |15   |ポリシーエンジンの作成、ポリシーの管理、ポリシーアセットの生成とレビュー                        |
|**Browser**         |25   |クラウドベースのブラウザ自動化 — ナビゲート、クリック、入力、スクリーンショット、データ抽出     |
|**Code Interpreter**|9    |サンドボックス化されたコード実行、ファイルのアップロード/ダウンロード、パッケージのインストール |
|**Documentation**   |2    |AgentCore ドキュメントの検索と取得                                                             |

## 前提条件 {#prerequisites}

1. [Astral](https://docs.astral.sh/uv/getting-started/installation/) から `uv` をインストールします
1. `uv python install 3.10` を使用して Python 3.10 以降をインストールします
1. AWS 認証情報を設定します（AWS_PROFILE、AWS_ACCESS_KEY_ID、または IAM ロール）

## インストール {#installation}

|Kiro                                                                                                                                                                                                                                                                                                         |Cursor                                                                                                                                                                                                                                                                                                                                                                                                     |VS Code                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------:|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------:|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------:|
|[![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=bedrock-agentcore-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-bedrock-agentcore-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D)|[![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=bedrock-agentcore-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYW1hem9uLWJlZHJvY2stYWdlbnRjb3JlLW1jcC1zZXJ2ZXJAbGF0ZXN0IiwiZW52Ijp7IkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6WyJzZWFyY2hfYWdlbnRjb3JlX2RvY3MiLCJmZXRjaF9hZ2VudGNvcmVfZG9jIl19)|[![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Bedrock%20AgentCore%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-bedrock-agentcore-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%22search_agentcore_docs%22%2C%22fetch_agentcore_doc%22%5D%7D)|

### 設定 {#configuration}

MCP クライアントの設定（例: `~/.kiro/settings/mcp.json`）に以下を追加します。

```json
{
  "mcpServers": {
    "bedrock-agentcore-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.amazon-bedrock-agentcore-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

### Windows {#windows}

```json
{
  "mcpServers": {
    "bedrock-agentcore-mcp-server": {
      "command": "uv",
      "args": [
        "tool", "run", "--from",
        "awslabs.amazon-bedrock-agentcore-mcp-server@latest",
        "awslabs.amazon-bedrock-agentcore-mcp-server.exe"
      ],
      "env": { "FASTMCP_LOG_LEVEL": "ERROR" }
    }
  }
}
```

## ツールの設定 {#tool-configuration}

すべてのプリミティブツールはデフォルトで有効になっています。どのツールを登録するかは環境変数で制御します。

```bash
# Disable specific primitives
AGENTCORE_DISABLE_TOOLS=browser,code_interpreter

# Or enable only specific primitives
AGENTCORE_ENABLE_TOOLS=memory,runtime,identity
```

`AGENTCORE_ENABLE_TOOLS` が設定されている場合、リストに指定されたプリミティブのみが登録されます。ドキュメントツール（`search_agentcore_docs`、`fetch_agentcore_doc`）は常に利用可能です。

## プリミティブ {#primitives}

### Runtime (14 tools) {#runtime-14-tools}

AgentCore 上でエージェントランタイムとエンドポイントを管理します。ランタイムの作成、エンドポイントバージョンのデプロイ、エージェントの呼び出し、セッションの管理を行います。

主なツール: `create_agent_runtime`、`create_agent_runtime_endpoint`、`invoke_agent_runtime`、`stop_runtime_session`、`get_runtime_guide`

### Memory (21 tools) {#memory-21-tools}

メモリリソースの作成、会話イベントの保存、セマンティックに関連性の高いメモリの取得、抽出ジョブの管理を行います。短期メモリ（セッションイベント）と長期メモリ（抽出されたインサイト）の両方をサポートします。

主なツール: `memory_create`、`memory_create_event`、`memory_retrieve_records`、`memory_batch_create_records`、`get_memory_guide`

> **Note:** MCP ツールは boto3 を介して AgentCore Memory API を直接呼び出します。これらのツールを使用するのに `agentcore` CLI は必要ありません。

### Identity (21 tools) {#identity-21-tools}

ワークロードアイデンティティ、API キー認証情報プロバイダー、OAuth2 認証情報プロバイダー、トークンボールトの設定、リソースポリシーを管理します。データプレーンの操作（トークンの取得）は意図的に除外されています。これらはライブの認証情報を返すため、LLM のコンテキストを流れるべきではありません。

主なツール: `identity_create_workload_identity`、`identity_create_api_key_provider`、`identity_create_oauth2_provider`、`identity_get_token_vault`、`get_identity_guide`

### Gateway (15 tools) {#gateway-15-tools}

既存の API をエージェントから呼び出し可能な MCP ツールに変換する API ゲートウェイを作成・管理します。ゲートウェイターゲット（Lambda、OpenAPI、Smithy、MCP サーバー）とリソースポリシーを管理します。`InvokeGateway` データプレーン操作は除外されています。これは agent-runtime の JWT を必要とし、機密性の高いコンテンツを返す可能性があるためです。

主なツール: `gateway_create`、`gateway_target_create`、`gateway_target_synchronize`、`gateway_resource_policy_put`、`get_gateway_guide`

### Policy (15 tools) {#policy-15-tools}

ポリシーエンジンの作成、認可ポリシーの管理、ポリシーアセットの生成を行います。ポリシーエンジンは、エージェントのアクションに対してきめ細かいアクセス制御を適用します。

主なツール: `policy_engine_create`、`policy_create`、`policy_generation_start`、`policy_generation_get`、`get_policy_guide`

### Browser (25 tools) {#browser-25-tools}

AgentCore を利用したクラウドベースのブラウザ自動化です。各セッションは分離された Firecracker マイクロ VM 内で実行されるため、ローカルにブラウザをインストールする必要はありません。

```
start_browser_session → browser_navigate → browser_snapshot → browser_click → stop_browser_session
```

ヒント:

- Google の代わりに DuckDuckGo または Bing を使用してください（CAPTCHA がクラウド IP をブロックします）
- データ抽出には `querySelectorAll` を指定した `browser_evaluate` を使用してください
- `timeout_seconds` はアイドルタイムアウトであり、絶対的な継続時間ではありません

### Code Interpreter (9 tools) {#code-interpreter-9-tools}

分離された環境でのサンドボックス化されたコード実行です。セッションを開始し、コードまたはシェルコマンドを実行し、パッケージをインストールし、ファイルを転送します。

主なツール: `start_code_interpreter_session`、`execute_code`、`execute_command`、`install_packages`、`upload_file`、`download_file`

> **Cost note:** セッションには AWS の料金が発生します。完了したらセッションを停止してください。

### Documentation (2 tools) {#documentation-2-tools}

AgentCore ドキュメントを検索・取得します。これらのツールは `AGENTCORE_DISABLE_TOOLS` の設定に関係なく常に利用可能です。

- `search_agentcore_docs` — ランク付けされた結果とスニペットで検索します
- `fetch_agentcore_doc` — URL によってドキュメントの全文コンテンツを取得します

## コストへの注意 {#cost-awareness}

AWS リソースを作成したりコンピューティングを呼び出したりするツールには料金が発生します。各プリミティブのガイドツール（`get_memory_guide`、`get_runtime_guide` など）には、コストの区分が記載されています。

- **読み取り専用**（コストなし）: get、list、guide 操作
- **課金対象**（AWS 料金あり）: create、update、invoke、search 操作
- **破壊的**（取り消し不可）: delete 操作

課金対象および破壊的なツールは、その説明に `COST WARNING:` または `WARNING:` を含んでおり、エージェントが呼び出す前にその影響を理解できるようになっています。

## セキュリティ {#security}

- すべての API 呼び出しは、環境（AWS_PROFILE、環境変数、または IAM ロール）から解決された認証情報を使用して boto3 で行われます
- 認証情報（トークン、API キー、シークレット）を返す操作は MCP ツールから除外されています。認証情報は LLM のコンテキストを流れるべきではありません
- 取得したコンテンツ（メモリレコード、ゲートウェイのレスポンス）は信頼できない入力として扱う必要があります
- ユーザーエージェントのトラッキング（`agentcore-mcp-server/{version} {primitive}`）は利用状況分析のために API 呼び出しに含まれています。テレメトリが他の場所に送信されることはありません

## アーキテクチャ {#architecture}

各プリミティブは `tools/` 配下の独立したサブパッケージとして実装されています。

```
tools/
├── runtime/       # 14 tools — agent runtime management
├── memory/        # 21 tools — memory resources and records
├── identity/      # 21 tools — workload identity and credentials
├── gateway/       # 15 tools — API gateway management
├── policy/        # 15 tools — policy engine management
├── browser/       # 25 tools — cloud browser automation
├── code_interpreter/  # 9 tools — sandboxed code execution
└── docs.py        # 2 tools — documentation search
```

各サブパッケージには、キャッシュされた boto3 クライアントラッパー、Pydantic のレスポンスモデル、構造化されたエラーハンドラー、ドメインツールファイル、および包括的なガイドツールが含まれています。
