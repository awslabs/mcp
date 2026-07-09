---
title: "Amazon ElastiCache/MemoryDB Valkey MCP サーバー"
---

Amazon ElastiCache [Valkey](https://valkey.io/) データストア向けの AWS Labs Model Context Protocol (MCP) サーバーです。

## 機能 {#features}

この MCP サーバーは、Valkey を扱う AI エージェント向けに特化した 12 個のツールを提供します。ツール群は、構造化された JSON 入力を受け付け、コマンド変換を内部で処理することで、トークンコストとエージェントのエラー率を最小限に抑えるよう設計されています。

### Valkey AI Search — 4 ツール {#valkey-ai-search--4-tools}

| ツール | 機能 |
|------|-------------|
| `manage_index` | 検索インデックスの作成、削除、検査、一覧表示を行います。TEXT、NUMERIC、TAG、VECTOR フィールドを含む構造化スキーマ定義を受け付けます。デフォルトは COSINE 距離 + HNSW アルゴリズムです。 |
| `add_documents` | オプションの埋め込み生成付きでドキュメントを取り込みます。Bedrock、OpenAI、Ollama プロバイダーをサポートします。インデックスが存在しない場合は自動作成します。 |
| `search` | セマンティック検索、テキスト検索、ハイブリッド検索、類似検索を統合したツールです。パラメータからモードを自動検出するほか、明示的な `mode` の上書き指定も受け付けます。 |
| `aggregate` | FT.AGGREGATE 用の構造化パイプラインビルダーです。GROUPBY、SORTBY、APPLY、FILTER、LIMIT ステージと 12 種類の REDUCE 関数をサポートします。 |

### Valkey JSON Intelligence — 5 ツール {#valkey-json-intelligence--5-tools}

| ツール | 機能 |
|------|-------------|
| `json_get` | Valkey キーの指定パスから JSON 値を取得します。 |
| `json_set` | 指定パスに JSON 値を設定します(オプションで TTL を指定可能)。 |
| `json_arrappend` | 指定パスの JSON 配列に値を追加します。 |
| `json_arrpop` | 指定パスの JSON 配列から要素を取り出します。 |
| `json_arrtrim` | JSON 配列を指定した範囲にトリムします。 |

### Valkey Command Runner — 3 ツール(3 段階の安全性) {#valkey-command-runner--3-tools-3-tier-safety}

| ツール | 階層 | 機能 |
|------|------|-------------|
| `valkey_read` | Safe | 読み取り専用コマンド(GET、HGETALL、SCAN、INFO など)。readonly モードでも常に利用可能です。 |
| `valkey_write` | Write | 変更系コマンド(SET、HSET、DEL、LPUSH など)。破壊的なコマンドはブロックされます。readonly モードでは無効です。 |
| `valkey_admin` | Admin | 破壊的なコマンド(FLUSHALL、CONFIG SET、EVAL など)。デフォルトでは無効で、`VALKEY_ADMIN_ENABLED=true` と `confirm=True` が必要です。 |

**3 段階の安全性モデル:** `valkey_read`(常に安全)→ `valkey_write`(変更可、破壊的操作は不可)→ `valkey_admin`(オプトイン専用、デフォルトで無効)。エージェントが誤ってステージングクラスターに FLUSHALL を実行することはありません。

### その他の機能 {#additional-features}

- **Valkey-GLIDE**: 非同期ネイティブなパフォーマンスを実現する [Valkey GLIDE](https://github.com/valkey-io/valkey-glide) 上に構築されています。
- **クラスターサポート**: スタンドアロンおよびクラスター構成の Valkey デプロイメントに対応します。
- **SSL/TLS セキュリティ**: CA 証明書検証付きの TLS によるセキュアな接続。
- **Readonly モード**: `--readonly` で書き込み操作を防止します。
- **マルチプロバイダー埋め込み**: Bedrock、OpenAI、Ollama に対応し、自動フォールバックを備えています。
- **ヘルスチェック**: ALB ターゲットグループのヘルスチェック用の `GET /health` エンドポイント。

## 前提条件 {#prerequisites}

1. [Astral](https://docs.astral.sh/uv/getting-started/installation/) から `uv` をインストールします
2. `uv python install 3.10` で Python をインストールします
3. Valkey データストアへのアクセス:
   - **AI Search ツール**には [Valkey Search モジュール](https://valkey.io/commands/?group=search)が必要です
   - **JSON ツール**には [Valkey JSON モジュール](https://valkey.io/commands/?group=json)が必要です
   - `valkey/valkey-bundle` Docker イメージには両方のモジュールが含まれています
4. **埋め込みプロバイダーの認証情報**(`add_documents` と `search` によるセマンティック検索を使用する場合にのみ必要):
   - **Bedrock**(デフォルト): AWS 認証情報が必要です — `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`、`AWS_PROFILE`、または IAM ロール。認証情報がない場合、セマンティック検索は `NoCredentialsError` で失敗します。
   - **OpenAI**: `OPENAI_API_KEY` が必要です
   - **Ollama**: 実行中の Ollama インスタンスが必要です(認証情報は不要)
5. Amazon ElastiCache/MemoryDB への接続手順については、[ELASTICACHECONNECT.md](https://github.com/awslabs/mcp/blob/main/src/valkey-mcp-server/ELASTICACHECONNECT.md) を参照してください。

## クイックスタート {#quickstart}

Search モジュールと JSON モジュールを含むローカル Valkey インスタンスを起動します:

```bash
docker run -d --name valkey -p 6379:6379 valkey/valkey-bundle:latest
```

起動していることを確認します:

```bash
docker exec valkey valkey-cli PING
# Should return: PONG
```

MCP サーバーを実行します(埋め込みに Ollama を使用 — AWS 認証情報は不要):

```bash
uvx awslabs.valkey-mcp-server@latest
```

または、セマンティック検索用に Ollama 埋め込みを使用する場合:

```bash
EMBEDDING_PROVIDER=ollama uvx awslabs.valkey-mcp-server@latest
```

AI IDE で次のクエリ例を試してみてください:

```
"Create a search index called products with title (TEXT), category (TAG), and price (NUMERIC) fields"
"Add 3 product documents to the products index"
"Search for electronics in the products index"
"Show me the average price by category"
```

## インストール {#installation}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.valkey-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.valkey-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22VALKEY_HOST%22%3A%22127.0.0.1%22%2C%22VALKEY_PORT%22%3A%226379%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.valkey-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMudmFsa2V5LW1jcC1zZXJ2ZXJAbGF0ZXN0IiwiZW52Ijp7IlZBTEtFWV9IT1NUIjoiMTI3LjAuMC4xIiwiVkFMS0VZX1BPUlQiOiI2Mzc5IiwiRkFTVE1DUF9MT0dfTEVWRUwiOiJFUlJPUiJ9LCJhdXRvQXBwcm92ZSI6W10sImRpc2FibGVkIjpmYWxzZX0%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Valkey%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.valkey-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22VALKEY_HOST%22%3A%22127.0.0.1%22%2C%22VALKEY_PORT%22%3A%226379%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22autoApprove%22%3A%5B%5D%2C%22disabled%22%3Afalse%7D) |

### MCP 設定 {#mcp-configuration}

MCP 設定ファイル(例: Kiro の場合は `~/.kiro/settings/mcp.json`、Cursor の場合は `.cursor/mcp.json`、VS Code の場合は `.vscode/mcp.json`)に以下を追加します:

```json
{
  "mcpServers": {
    "awslabs.valkey-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.valkey-mcp-server@latest"],
      "env": {
        "VALKEY_HOST": "127.0.0.1",
        "VALKEY_PORT": "6379",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

> **ヒント:** 初期セットアップ中は `FASTMCP_LOG_LEVEL=INFO` または `DEBUG` を使用すると、接続とツール登録の出力を確認できます。本番環境では `ERROR` に切り替えてください。

デフォルトの埋め込みプロバイダーは Bedrock で、AWS 認証情報が必要です。代わりに Ollama を使用する場合(認証情報は不要)、以下を追加します:

```json
        "EMBEDDING_PROVIDER": "ollama",
        "OLLAMA_HOST": "http://localhost:11434"
```

Readonly モード(すべての書き込み操作を無効化します — 埋め込みの設定はセマンティック検索を使用する場合にのみ必要です):

```json
{
  "mcpServers": {
    "awslabs.valkey-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.valkey-mcp-server@latest", "--readonly"],
      "env": {
        "VALKEY_HOST": "127.0.0.1",
        "VALKEY_PORT": "6379",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

### Windows でのインストール {#windows-installation}

```json
{
  "mcpServers": {
    "awslabs.valkey-mcp-server": {
      "command": "uv",
      "args": [
        "tool", "run", "--from",
        "awslabs.valkey-mcp-server@latest",
        "awslabs.valkey-mcp-server.exe"
      ],
      "env": {
        "VALKEY_HOST": "127.0.0.1",
        "VALKEY_PORT": "6379",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

### Docker {#docker}

まずイメージをビルドします:

```bash
docker build -t awslabs/valkey-mcp-server .
```

MCP 設定(ホスト上の Valkey に到達するには `host.docker.internal` を使用します。Linux では代わりに `--network host` を使用します):

```json
{
  "mcpServers": {
    "awslabs.valkey-mcp-server": {
      "command": "docker",
      "args": [
        "run", "--rm", "--interactive",
        "--env", "FASTMCP_LOG_LEVEL=ERROR",
        "--env", "VALKEY_HOST=host.docker.internal",
        "--env", "VALKEY_PORT=6379",
        "awslabs/valkey-mcp-server:latest"
      ]
    }
  }
}
```

Docker での readonly モード:

```json
{
  "mcpServers": {
    "awslabs.valkey-mcp-server": {
      "command": "docker",
      "args": [
        "run", "--rm", "--interactive",
        "--env", "FASTMCP_LOG_LEVEL=ERROR",
        "--env", "VALKEY_HOST=host.docker.internal",
        "--env", "VALKEY_PORT=6379",
        "awslabs/valkey-mcp-server:latest",
        "--readonly"
      ]
    }
  }
}
```

Docker コンテナを直接実行する場合:

```bash
docker run -p 8080:8080 \
  -e VALKEY_HOST=host.docker.internal \
  -e VALKEY_PORT=6379 \
  awslabs/valkey-mcp-server
```

## 設定 {#configuration}

### サーバー {#server}

| 変数 | 説明 | デフォルト |
|----------|-------------|---------|
| `MCP_TRANSPORT` | トランスポートプロトコル(`stdio`、`sse`) | `stdio` |

### Valkey 接続 {#valkey-connection}

| 変数 | 説明 | デフォルト |
|----------|-------------|---------|
| `VALKEY_HOST` | Valkey のホスト名または IP | `127.0.0.1` |
| `VALKEY_PORT` | Valkey のポート | `6379` |
| `VALKEY_USERNAME` | 認証用のユーザー名 | `None` |
| `VALKEY_PWD` | 認証用のパスワード(注: `VALKEY_PASSWORD` ではありません) | `""` |
| `VALKEY_USE_SSL` | TLS を有効化 | `false` |
| `VALKEY_SSL_CA_CERTS` | TLS 検証用の CA 証明書(PEM)へのパス | `None` |
| `VALKEY_CLUSTER_MODE` | クラスターモードを有効化 | `false` |
| `VALKEY_VECTOR_ALGORITHM` | デフォルトのベクトルインデックスアルゴリズム(`HNSW` または `FLAT`) | `HNSW` |
| `VALKEY_VECTOR_DISTANCE_METRIC` | デフォルトのベクトル距離メトリクス(`COSINE`、`L2`、または `IP`) | `COSINE` |
| `VALKEY_ADMIN_ENABLED` | 管理者階層(破壊的なコマンド)を有効化 | `false` |

### 埋め込みプロバイダー {#embeddings-provider}

埋め込み生成は、`add_documents`(ベクトルの生成)と `search`(セマンティック/ハイブリッドモード)で使用されます。テキスト検索、JSON ツール、または `manage_index` のみを使用する場合、埋め込みプロバイダーは不要です。

| 変数 | 説明 | デフォルト |
|----------|-------------|---------|
| `EMBEDDING_PROVIDER` | プロバイダー: `bedrock`、`openai`、`ollama`、または `hash` | `bedrock` |

> **注:** デフォルトのプロバイダーは Bedrock で、AWS 認証情報が必要です。AWS 認証情報を設定していない場合は、`EMBEDDING_PROVIDER=ollama` を設定してローカルの Ollama インスタンスを実行するか、テスト用に `EMBEDDING_PROVIDER=hash` を設定してください(決定的で低品質な埋め込み)。

#### Bedrock {#bedrock}

認証情報は `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`、`AWS_PROFILE`、または IAM ロール経由で指定します。

| 変数 | 説明 | デフォルト |
|----------|-------------|---------|
| `AWS_REGION` | AWS リージョン | `us-east-1` |
| `BEDROCK_MODEL_ID` | モデル ID | `amazon.nova-2-multimodal-embeddings-v1:0` |
| `BEDROCK_NORMALIZE` | 埋め込みを正規化 | `None` |
| `BEDROCK_DIMENSIONS` | 埋め込みの次元数 | `None`(モデルのデフォルト) |
| `BEDROCK_INPUT_TYPE` | 入力タイプ | `None` |
| `BEDROCK_MAX_ATTEMPTS` | 最大リトライ回数 | `3` |
| `BEDROCK_MAX_POOL_CONNECTIONS` | コネクションプールのサイズ | `50` |
| `BEDROCK_RETRY_MODE` | リトライモード | `adaptive` |

#### OpenAI {#openai}

| 変数 | 説明 | デフォルト |
|----------|-------------|---------|
| `OPENAI_API_KEY` | API キー(必須) | `None` |
| `OPENAI_MODEL` | モデル名 | `text-embedding-3-small` |

#### Ollama {#ollama}

| 変数 | 説明 | デフォルト |
|----------|-------------|---------|
| `OLLAMA_HOST` | Ollama エンドポイント URL(プロトコルが必要です。例: `http://localhost:11434`) | `http://localhost:11434` |
| `OLLAMA_EMBEDDING_MODEL` | モデル名 | `nomic-embed-text` |

## 使用例 {#example-usage}

```
"Create a search index for product data with title, category, price, and embedding fields"
"Add these product documents and generate embeddings from the title field"
"Search for products similar to 'wireless headphones'"
"Find products similar to product:123"
"Show me the average price by category"
"Store this JSON config and set a 1-hour TTL"
"Get the nested value at $.settings.theme from the config key"
```

## トラブルシューティング {#troubleshooting}

| 問題 | 原因 | 対処法 |
|---------|-------|-----|
| `Connection refused` または `timed out` | Valkey が起動していないか、ホスト/ポートが誤っている | `VALKEY_HOST` と `VALKEY_PORT` を確認します。`valkey-cli -h <host> -p <port> PING` でテストします。 |
| セマンティック検索での `NoCredentialsError` | Bedrock がデフォルトのプロバイダーだが AWS 認証情報が未設定 | `EMBEDDING_PROVIDER=ollama` を設定するか、AWS 認証情報を設定します。 |
| `Unknown command 'FT.CREATE'` | Valkey Search モジュールがロードされていない | `valkey/valkey-bundle` Docker イメージを使用するか、Search モジュールをロードします。 |
| `Unknown command 'JSON.GET'` | Valkey JSON モジュールがロードされていない | `valkey/valkey-bundle` Docker イメージを使用するか、JSON モジュールをロードします。 |
| Docker: `127.0.0.1` への `Connection refused` | コンテナのループバックはホストではない | `VALKEY_HOST=host.docker.internal`(macOS/Windows)または `--network host`(Linux)を使用します。 |
| `Request URL is missing 'http://'` | `OLLAMA_HOST` がプロトコルなしで設定されている | プロトコルを含めます: `localhost:11434` ではなく `http://localhost:11434` とします。 |
| サーバーから出力がない | `FASTMCP_LOG_LEVEL=ERROR` が情報出力を抑制している | トラブルシューティング時は `FASTMCP_LOG_LEVEL=INFO` または `DEBUG` を設定します。 |

### ツール名の衝突 {#tool-name-collisions}

このサーバーは `search` という名前のツールを公開しています。他の MCP サーバー(例: Atlassian Rovo)も同名のツールを公開している場合があります。複数の MCP サーバーが同時にアクティブな場合、AI エージェントがそれらを区別できず、誤ったツールが呼び出されることがあります。

この問題が発生した場合は、次のいずれかを行ってください:
- Valkey 検索を使用する際に、競合する MCP サーバーを無効化する
- MCP クライアントがサポートしている場合は、明示的なツールルーティングを使用する(例: サーバースコープ付きのツール名)
- インデックス名や Valkey 固有のパラメータを参照して、Valkey の `search` ツールを明示的に使用するようエージェントに指示する

## 開発 {#development}

### テストの実行 {#running-tests}

```bash
uv venv && source .venv/bin/activate && uv sync

# Unit tests
uv run --frozen pytest tests/ -m "not live and not integration"

# Live integration tests (requires VALKEY_HOST and EMBEDDING_PROVIDER)
uv run --frozen pytest tests/test_search_live.py -m live -v

# Type checking
uv run --frozen pyright
```

### Docker イメージのビルド {#building-docker-image}

```bash
docker build -t awslabs/valkey-mcp-server .
```

### Docker コンテナの実行 {#running-docker-container}

```bash
docker run -p 8080:8080 \
  -e VALKEY_HOST=host.docker.internal \
  -e VALKEY_PORT=6379 \
  awslabs/valkey-mcp-server
```

Readonly モード:

```bash
docker run -p 8080:8080 \
  -e VALKEY_HOST=host.docker.internal \
  -e VALKEY_PORT=6379 \
  awslabs/valkey-mcp-server --readonly
```
