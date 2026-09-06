---
title: AWS Labs OpenAPI MCP Server
---

このプロジェクトは、OpenAPI 仕様から Model Context Protocol (MCP) のツールとリソースを動的に作成するサーバーです。これにより、大規模言語モデル (LLM) が Model Context Protocol を通じて API と対話できるようになります。

## 機能 {#features}

- **動的なツール生成**: OpenAPI エンドポイントから MCP ツールを自動的に作成します
- **インテリジェントなルートマッピング**: クエリパラメータを持つ GET 操作を RESOURCES ではなく TOOLS にマッピングします
  - クエリパラメータを持つ API 操作を LLM が理解・使用しやすくします
  - 検索およびフィルタリング用エンドポイントの使いやすさを向上させます
  - route_patch モジュールで設定可能です
- **タグベースのフィルタリング**: LLM に公開する操作を制御します
  - 特定のタグのみを含める: `--include-tags pet,store`
  - 特定のタグを除外する: `--exclude-tags admin,internal`
  - CLI 引数または `INCLUDE_TAGS` / `EXCLUDE_TAGS` 環境変数で設定可能です
- **充実したツール説明**: OpenAPI 仕様のレスポンスコードとパラメータ例をツールの説明に自動的に追加し、LLM がより適切なツールを選択できるよう支援します
- **マルチスペック構成**: 複数の OpenAPI 仕様を単一の MCP サーバーに統合します
  - `--additional-specs` CLI 引数または `ADDITIONAL_SPECS` 環境変数で設定します
  - 各仕様には独立した認証(エントリごとの `auth_type`、`auth_token` など)を持つ専用の HTTP クライアントが割り当てられます
  - SSRF 対策済み: URL は取得前に DNS 解決と IP 許可リストによる検証が行われます
- **出力検証の切り替え**: 仕様が緩い API に対して、`--no-validate-output` または `VALIDATE_OUTPUT=false` でレスポンススキーマ検証を無効化できます
- **動的なプロンプト生成**: API 構造に基づいて有用なプロンプトを作成します
  - **操作固有のプロンプト**: 各 API 操作に対して自然言語のプロンプトを生成します
  - **API ドキュメントプロンプト**: 包括的な API ドキュメントプロンプトを作成します
  - **プロンプトの最適化**: コスト削減と明確性向上のためのトークン効率化戦略を実装しています
    - name、description、arguments、metadata を備えた MCP 準拠の構造に従います
    - 機能を維持しながらトークン使用量を 70〜75% 削減します
    - 開発者体験向上のため、必要な情報を含む簡潔な説明を使用します
- **トランスポートオプション**: stdio トランスポートをサポートします
- **柔軟な設定**: 環境変数またはコマンドライン引数で設定できます
- **OpenAPI サポート**: JSON または YAML 形式の OpenAPI 3.x 仕様に対応しています
- **OpenAPI 仕様の検証**: 問題が検出されても起動を失敗させず、代わりに警告をログに記録して仕様を検証するため、軽微な問題や非標準の拡張を含む仕様でも動作します
- **認証サポート**: 複数の認証方式(Basic、Bearer トークン、API キー、Cognito)をサポートします
- **AWS ベストプラクティス**: キャッシング、レジリエンス、可観測性に関する AWS のベストプラクティスを実装しています
- **包括的なテスト**: 高いコードカバレッジを持つ広範なユニットテストと統合テストを含みます
- **メトリクス収集**: API 呼び出し、ツール使用状況、エラー、パフォーマンスメトリクスを追跡します

## インストール {#installation}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.openapi-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.openapi-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22API_NAME%22%3A%22your-api-name%22%2C%22API_BASE_URL%22%3A%22https%3A//api.example.com%22%2C%22API_SPEC_URL%22%3A%22https%3A//api.example.com/openapi.json%22%2C%22LOG_LEVEL%22%3A%22ERROR%22%2C%22ENABLE_PROMETHEUS%22%3A%22false%22%2C%22ENABLE_OPERATION_PROMPTS%22%3A%22true%22%2C%22UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN%22%3A%225.0%22%2C%22UVICORN_GRACEFUL_SHUTDOWN%22%3A%22true%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.openapi-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMub3BlbmFwaS1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJBUElfTkFNRSI6InlvdXItYXBpLW5hbWUiLCJBUElfQkFTRV9VUkwiOiJodHRwczovL2FwaS5leGFtcGxlLmNvbSIsIkFQSV9TUEVDX1VSTCI6Imh0dHBzOi8vYXBpLmV4YW1wbGUuY29tL29wZW5hcGkuanNvbiIsIkxPR19MRVZFTCI6IkVSUk9SIiwiRU5BQkxFX1BST01FVEhFVVMiOiJmYWxzZSIsIkVOQUJMRV9PUEVSQVRJT05fUFJPTVBUUyI6InRydWUiLCJVVklDT1JOX1RJTUVPVVRfR1JBQ0VGVUxfU0hVVERPV04iOiI1LjAiLCJVVklDT1JOX0dSQUNFRlVMX1NIVVRET1dOIjoidHJ1ZSJ9LCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=OpenAPI%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.openapi-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22API_NAME%22%3A%22your-api-name%22%2C%22API_BASE_URL%22%3A%22https%3A%2F%2Fapi.example.com%22%2C%22API_SPEC_URL%22%3A%22https%3A%2F%2Fapi.example.com%2Fopenapi.json%22%2C%22LOG_LEVEL%22%3A%22ERROR%22%2C%22ENABLE_PROMETHEUS%22%3A%22false%22%2C%22ENABLE_OPERATION_PROMPTS%22%3A%22true%22%2C%22UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN%22%3A%225.0%22%2C%22UVICORN_GRACEFUL_SHUTDOWN%22%3A%22true%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

### PyPI からのインストール {#from-pypi}

```bash
pip install "awslabs.openapi-mcp-server"
```

### オプションの依存関係 {#optional-dependencies}

このパッケージはいくつかのオプションの依存関係をサポートしています。

```bash
# For YAML OpenAPI specification support
pip install "awslabs.openapi-mcp-server[yaml]"

# For Prometheus metrics support
pip install "awslabs.openapi-mcp-server[prometheus]"

# For testing
pip install "awslabs.openapi-mcp-server[test]"

# For all optional dependencies
pip install "awslabs.openapi-mcp-server[all]"
```

### ソースからのインストール {#from-source}

```bash
git clone https://github.com/awslabs/mcp.git
cd mcp/src/openapi-mcp-server
pip install -e .
```

### MCP 設定の使用 {#using-mcp-configuration}

Kiro 向けの設定例 (`~/.kiro/settings/mcp.json`):

```json
{
  "mcpServers": {
    "awslabs.openapi-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.openapi-mcp-server@latest"],
      "env": {
        "API_NAME": "your-api-name",
        "API_BASE_URL": "https://api.example.com",
          "API_SPEC_URL": "https://api.example.com/openapi.json",
          "LOG_LEVEL": "ERROR",
          "ENABLE_PROMETHEUS": "false",
          "ENABLE_OPERATION_PROMPTS": "true",
          "UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN": "5.0",
          "UVICORN_GRACEFUL_SHUTDOWN": "true"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Windows でのインストール {#windows-installation}

Windows ユーザーの場合、MCP サーバーの設定形式が若干異なります。

```json
{
  "mcpServers": {
    "awslabs.openapi-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.openapi-mcp-server@latest",
        "awslabs.openapi-mcp-server.exe"
      ],
      "env": {
          "API_NAME": "your-api-name",
          "API_BASE_URL": "https://api.example.com",
          "API_SPEC_URL": "https://api.example.com/openapi.json",
          "LOG_LEVEL": "ERROR",
          "ENABLE_PROMETHEUS": "false",
          "ENABLE_OPERATION_PROMPTS": "true",
          "UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN": "5.0",
          "UVICORN_GRACEFUL_SHUTDOWN": "true"
      },
    }
  }
}
```

## 使用方法 {#usage}

### 基本的な使用方法 {#basic-usage}

```bash
# Start with Petstore API example
awslabs.openapi-mcp-server --api-name petstore --api-url https://petstore3.swagger.io/api/v3 --spec-url https://petstore3.swagger.io/api/v3/openapi.json
```

### カスタム API {#custom-api}

```bash
# Use a different API
awslabs.openapi-mcp-server --api-name myapi --api-url https://api.example.com --spec-url https://api.example.com/openapi.json
```

### 認証付き API {#authenticated-api}

```bash
# Basic Authentication
awslabs.openapi-mcp-server --api-url https://api.example.com --spec-url https://api.example.com/openapi.json --auth-type basic --auth-username YOUR_USERNAME --auth-password YOUR_PASSWORD # pragma: allowlist secret

# Bearer Token Authentication
awslabs.openapi-mcp-server --api-url https://api.example.com --spec-url https://api.example.com/openapi.json --auth-type bearer --auth-token YOUR_TOKEN # pragma: allowlist secret

# API Key Authentication (in header)
awslabs.openapi-mcp-server --api-url https://api.example.com --spec-url https://api.example.com/openapi.json --auth-type api_key --auth-api-key YOUR_API_KEY --auth-api-key-name X-API-Key --auth-api-key-in header # pragma: allowlist secret
```

認証方式、設定オプション、および例の詳細については、[AUTHENTICATION.md](https://github.com/awslabs/mcp/blob/main/src/openapi-mcp-server/AUTHENTICATION.md) を参照してください。

### ローカルの OpenAPI 仕様 {#local-openapi-specification}

```bash
# Use a local OpenAPI specification file
awslabs.openapi-mcp-server --spec-path ./openapi.json
```

### タグフィルタリング {#tag-filtering}

```bash
# Only expose pet-related operations
awslabs.openapi-mcp-server --api-url https://petstore3.swagger.io/api/v3 --spec-url https://petstore3.swagger.io/api/v3/openapi.json --include-tags pet

# Hide admin and internal operations
awslabs.openapi-mcp-server --api-url https://api.example.com --spec-url https://api.example.com/openapi.json --exclude-tags admin,internal
```

### マルチスペック構成 {#multi-spec-composition}

```bash
# Combine multiple APIs into one MCP server (each with its own auth)
awslabs.openapi-mcp-server --api-url https://api.example.com --spec-url https://api.example.com/openapi.json \
  --additional-specs '[{"name":"payments","spec_url":"https://payments.example.com/openapi.json","base_url":"https://payments.example.com","auth_type":"bearer","auth_token":"your-payments-bearer-token"}]'

# Additional specs may also use a local OpenAPI file via spec_path
awslabs.openapi-mcp-server --api-url https://api.example.com --spec-url https://api.example.com/openapi.json \
  --additional-specs '[{"name":"payments","spec_path":"./specs/payments-openapi.json","base_url":"https://payments.example.com"}]'

# Allow HTTP URLs and private networks (for internal/development APIs)
awslabs.openapi-mcp-server --api-url https://api.example.com --spec-url https://api.example.com/openapi.json \
  --allow-insecure-http --allow-private-networks \
  --additional-specs '[{"name":"internal","spec_url":"http://10.0.0.5:8080/openapi.json","base_url":"http://10.0.0.5:8080"}]'
```

> **注:** 追加の仕様はプライマリ API の認証情報を継承しません。各エントリは独自の `auth_type`/`auth_token`/`auth_api_key` を宣言する必要があり、宣言しない場合は認証なしがデフォルトになります。詳細は[セキュリティ](#security)セクションを参照してください。

### 出力検証の無効化 {#disable-output-validation}

```bash
# For APIs with loose specs that don't match their own response schemas
awslabs.openapi-mcp-server --api-url https://api.example.com --spec-url https://api.example.com/openapi.json --no-validate-output
```

### YAML の OpenAPI 仕様 {#yaml-openapi-specification}

```bash
# Use a YAML OpenAPI specification file (requires pyyaml)
pip install "awslabs.openapi-mcp-server[yaml]"
awslabs.openapi-mcp-server --spec-path ./openapi.yaml
```

### ローカルでの開発とテスト {#local-development-and-testing}

ローカルでの開発とテストには、`uvx` コマンドを `--refresh` および `--from` オプションと組み合わせて使用できます。

```bash
# Run the server from the local directory with the Petstore API
uvx --refresh --from . awslabs.openapi-mcp-server --api-url https://petstore3.swagger.io/api/v3 --spec-url https://petstore3.swagger.io/api/v3/openapi.json --log-level DEBUG
```

**コマンドオプションの説明:**

- `uvx` - Python パッケージを実行するための uv パッケージマネージャーの実行ツール
- `--refresh` - パッケージキャッシュを更新して最新バージョンが使用されるようにします(開発時に重要)
- `--from .` - PyPI からインストールする代わりに、カレントディレクトリのパッケージを使用します
- `awslabs.openapi-mcp-server` - 実行するパッケージ名
- `--api-url` - API のベース URL
- `--spec-url` - OpenAPI 仕様の URL
- `--log-level DEBUG` - より詳細なログを出力するためにログレベルを DEBUG に設定します(開発時に便利)
**これらのオプションを使用するタイミング:**

- コードを変更した後、最新バージョンが使用されるようにしたい場合は `--refresh` を使用します
- トラブルシューティングや開発のために詳細なログが必要な場合は `--log-level DEBUG` を使用します

**注:** Petstore API は、API 認証の設定なしで簡単なテストに使用できる標準的な OpenAPI スキーマのエンドポイントです。独自の API を用意することなく MCP サーバーの実装をテストするのに最適です。

## 設定 {#configuration}

### 環境変数 {#environment-variables}

```bash
# Server configuration
export SERVER_NAME="My API Server"
export SERVER_DEBUG=true
export SERVER_MESSAGE_TIMEOUT=60
export SERVER_HOST="0.0.0.0"
export SERVER_PORT=8000
export SERVER_TRANSPORT="stdio"  # Option: stdio
export LOG_LEVEL="INFO"  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

# Metrics and monitoring configuration
export ENABLE_PROMETHEUS="false"  # Enable/disable Prometheus metrics (default: false)
export PROMETHEUS_PORT=9090  # Port for Prometheus metrics server
export ENABLE_OPERATION_PROMPTS="true"  # Enable/disable operation-specific prompts (default: true)

# Graceful shutdown configuration
export UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN=5.0  # Timeout for graceful shutdown in seconds
export UVICORN_GRACEFUL_SHUTDOWN=true  # Enable/disable graceful shutdown

# API configuration
export API_NAME="myapi"
export API_BASE_URL="https://api.example.com"
export API_SPEC_URL="https://api.example.com/openapi.json"
export API_SPEC_PATH="/path/to/local/openapi.json"  # Optional: local file path

# Authentication configuration
export AUTH_TYPE="none"  # Options: none, basic, bearer, api_key
export AUTH_USERNAME="PLACEHOLDER_USERNAME"  # For basic authentication # pragma: allowlist secret
export AUTH_PASSWORD="PLACEHOLDER_PASSWORD"  # For basic authentication # pragma: allowlist secret
export AUTH_TOKEN="PLACEHOLDER_TOKEN"  # For bearer token authentication # pragma: allowlist secret
export AUTH_API_KEY="PLACEHOLDER_API_KEY"  # For API key authentication # pragma: allowlist secret
export AUTH_API_KEY_NAME="X-API-Key"  # Name of the API key (default: api_key)
export AUTH_API_KEY_IN="header"  # Where to place the API key (options: header, query, cookie)

# Tag filtering
export INCLUDE_TAGS="pet,store"  # Only expose operations with these tags
export EXCLUDE_TAGS="admin,internal"  # Hide operations with these tags

# Output validation
export VALIDATE_OUTPUT="true"  # Set to "false" to disable response schema validation

# Multi-spec composition
# Each additional spec requires base_url and either spec_url or spec_path
# Each entry can optionally include auth_type, auth_token, auth_api_key, auth_api_key_name, auth_username, auth_password
export ADDITIONAL_SPECS='[{"name":"payments","spec_url":"https://payments.example.com/openapi.json","base_url":"https://payments.example.com","auth_type":"api_key","auth_api_key":"PLACEHOLDER_API_KEY","auth_api_key_name":"X-API-Key"}]' # pragma: allowlist secret

# Security settings
export ALLOW_INSECURE_HTTP="false"       # Set to "true" to permit http:// URLs
export ALLOW_PRIVATE_NETWORKS="false"    # Set to "true" to permit private/loopback/link-local IPs
export ALLOWED_SPEC_DIRS="/app/specs:/data/api"  # OS path-separated list of allowed directories for spec_path (use ; on Windows)
```

## ドキュメント {#documentation}

OpenAPI MCP Server には、導入と機能の活用を支援する包括的なドキュメントが含まれています。

- [**AUTHENTICATION.md**](https://github.com/awslabs/mcp/blob/main/src/openapi-mcp-server/AUTHENTICATION.md): 認証方式、設定オプション、トラブルシューティングに関する詳細情報
- [**DEPLOYMENT.md**](https://github.com/awslabs/mcp/blob/main/src/openapi-mcp-server/DEPLOYMENT.md): Docker や AWS を含むさまざまな環境へのサーバーデプロイに関するガイドライン
- [**AWS_BEST_PRACTICES.md**](https://github.com/awslabs/mcp/blob/main/src/openapi-mcp-server/AWS_BEST_PRACTICES.md): レジリエンス、キャッシング、効率性のためにサーバーに実装されている AWS ベストプラクティス
- [**OBSERVABILITY.md**](https://github.com/awslabs/mcp/blob/main/src/openapi-mcp-server/OBSERVABILITY.md): メトリクス、ロギング、モニタリング機能に関する情報
- [**tests/README.md**](https://github.com/awslabs/mcp/blob/main/src/openapi-mcp-server/tests/README.md): テスト構成と戦略の概要

## AWS ベストプラクティス {#aws-best-practices}

OpenAPI MCP Server は、レジリエントで可観測性が高く効率的なクラウドアプリケーションを構築するための AWS ベストプラクティスを実装しています。これには以下が含まれます。

- **キャッシング**: 複数のバックエンドオプションを備えた堅牢なキャッシングシステム
- **レジリエンス**: 一時的な障害に対処し、高可用性を確保するためのパターン
- **可観測性**: 包括的なモニタリング、メトリクス、ロギング機能

実装の詳細や設定オプションを含むこれらの機能の詳細については、[AWS_BEST_PRACTICES.md](https://github.com/awslabs/mcp/blob/main/src/openapi-mcp-server/AWS_BEST_PRACTICES.md) を参照してください。

## セキュリティ {#security}

サーバーは、`additional_specs` エントリ内のすべての URL を取得前に検証します。

| デフォルトでブロックされるもの | 例 |
|-------------------|----------|
| プライベートネットワーク (RFC 1918) | `10.0.0.0/8`、`172.16.0.0/12`、`192.168.0.0/16` |
| ループバック / リンクローカル | `127.0.0.0/8`、`169.254.0.0/16` (AWS IMDS) |
| HTTP スキーム | `http://...`(HTTPS が必須) |

**認証情報の分離**: 追加の仕様がプライマリ API の認証情報を継承することはありません。各エントリは独自の `auth_type`/`auth_token` を宣言する必要があり、宣言しない場合は認証なしがデフォルトになります。

**パストラバーサル保護**: `spec_path` は正規化され、仕様ファイルの拡張子(`.json`、`.yaml`、`.yml`)に制限され、ベストエフォートのシステムディレクトリのブロックリストと照合されます。本番環境へのデプロイでは、`--allowed-spec-dirs` を使用して許可するパスを明示的に制限してください。

開発/内部利用向けの**エスケープハッチ**:

| フラグ | 環境変数 | 効果 |
|------|---------|--------|
| `--allow-insecure-http` | `ALLOW_INSECURE_HTTP=true` | `http://` URL を許可します |
| `--allow-private-networks` | `ALLOW_PRIVATE_NETWORKS=true` | プライベート/ループバック IP を許可します |
| `--allowed-spec-dirs` | `ALLOWED_SPEC_DIRS=/path1:/path2` | `spec_path` を指定したディレクトリに制限します |

> **注**: DNS 検証は、チェック時点でホスト名がパブリック IP に解決されることを確認します。完全な DNS ピニングが必要な環境では、エグレスプロキシの背後にデプロイするか、ローカルファイルと `spec_path` を使用してください。

セキュリティの問題を報告するには、[コントリビューションガイドライン](https://github.com/awslabs/mcp/blob/main/CONTRIBUTING.md#security-issue-notifications)を参照してください。

## Docker デプロイ {#docker-deployment}

このプロジェクトには、コンテナ化デプロイ用の Dockerfile が含まれています。ビルドと実行の手順は次のとおりです。

```bash
# Build the Docker image
docker build -t openapi-mcp-server:latest .

# Run with default settings
docker run -p 8000:8000 openapi-mcp-server:latest

# Run with custom configuration
docker run -p 8000:8000 \
  -e API_NAME=myapi \
  -e API_BASE_URL=https://api.example.com \
  -e API_SPEC_URL=https://api.example.com/openapi.json \
  -e SERVER_TRANSPORT=stdio \
  -e ENABLE_PROMETHEUS=false \
  -e ENABLE_OPERATION_PROMPTS=true \
  -e UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN=5.0 \
  -e UVICORN_GRACEFUL_SHUTDOWN=true \
  openapi-mcp-server:latest
```

Docker デプロイ、AWS サービス統合、トランスポートに関する考慮事項の詳細については、[DEPLOYMENT.md](https://github.com/awslabs/mcp/blob/main/src/openapi-mcp-server/DEPLOYMENT.md) ファイルを参照してください。

## テスト {#testing}

このプロジェクトには、ユニットテスト、統合テスト、API 機能テストを網羅する包括的なテストスイートが含まれています。

### テストの実行 {#running-tests}

```bash
# Install test dependencies
pip install "awslabs.openapi-mcp-server[test]"

# Run all tests
pytest

# Run tests with coverage
pytest --cov=awslabs

# Run specific test modules
pytest tests/api/
pytest tests/utils/
```

テストスイートは以下をカバーしています。

1. **API 設定**: API 設定の処理と検証のテスト
2. **API ディスカバリー**: API エンドポイントの検出とツール生成のテスト
3. **キャッシング**: キャッシングシステムとプロバイダーのテスト
4. **HTTP クライアント**: レジリエンス機能を備えた HTTP クライアントのテスト
5. **メトリクス**: メトリクスの収集とレポートのテスト
6. **OpenAPI 検証**: OpenAPI 仕様の検証のテスト

テスト構成と戦略の詳細については、[tests/README.md](https://github.com/awslabs/mcp/blob/main/src/openapi-mcp-server/tests/README.md) ファイルを参照してください。

## 手順 {#instructions}

このサーバーは OpenAPI 仕様と LLM の間の橋渡しとして機能し、手動でツールを定義することなく、モデルが利用可能な API 機能をより深く理解できるようにします。サーバーは構造化された MCP ツールを作成し、LLM はそれを使用して API のエンドポイント、パラメータ、レスポンス形式を理解し、操作できます。

### 主な機能 {#key-features}

1. **動的なツール生成**: API エンドポイントから MCP ツールを自動的に作成します
2. **操作固有のプロンプト**: 各 API 操作に対して自然言語のプロンプトを生成します
3. **API ドキュメント**: API 全体の包括的なドキュメントプロンプトを作成します
4. **認証サポート**: Basic 認証、Bearer トークン、API キー、Cognito 認証に対応しています

### はじめに {#getting-started}

1. 以下を指定してサーバーを API に接続します。
   - API 名
   - API のベース URL
   - OpenAPI 仕様の URL またはローカルファイルパス
2. API で認証が必要な場合は、適切な認証を設定します
3. stdio トランスポートオプションを設定します

### モニタリングとメトリクス {#monitoring-and-metrics}

サーバーには組み込みのモニタリング機能が含まれています。
- Prometheus メトリクス(デフォルトでは無効)
- API 呼び出しとツール使用状況の詳細なロギング
- API 操作のパフォーマンストラッキング

## Kiro でのテスト {#testing-with-kiro}

OpenAPI MCP Server を Kiro でテストするには、Kiro が MCP サーバーを使用するように設定する必要があります。手順は次のとおりです。

1. **Kiro の MCP 統合を設定する**

   MCP 設定ファイルを作成または編集します。

   ```bash
   mkdir -p ~/.kiro/settings
   nano ~/.kiro/settings/mcp.json
   ```

   以下の設定を追加します。

   ```json
   {
     "mcpServers": {
       "awslabs.openapi-mcp-server": {
         "command": "python",
         "args": ["-m", "awslabs.openapi_mcp_server"],
         "cwd": "/path/to/your/openapi-mcp-server",
         "env": {
           "API_NAME": "petstore",
           "API_BASE_URL": "https://petstore3.swagger.io/api/v3",
           "API_SPEC_URL": "https://petstore3.swagger.io/api/v3/openapi.json",
           "LOG_LEVEL": "INFO",
           "ENABLE_PROMETHEUS": "false",
           "ENABLE_OPERATION_PROMPTS": "true",
           "UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN": "5.0",
           "UVICORN_GRACEFUL_SHUTDOWN": "true",
           "PYTHONPATH": "/path/to/your/openapi-mcp-server"
         },
         "disabled": false,
         "autoApprove": []
       }
     }
   }
   ```

2. **Kiro CLI を起動する**

   Kiro CLI を起動します。

   ```bash
   kiro-cli chat
   ```

3. **操作プロンプトをテストする**

   接続後、特定の API 操作について Kiro に支援を求めることで、操作プロンプトをテストできます。

   ```
   I need to find a pet by ID using the Petstore API
   ```

   Kiro は自然言語プロンプトを使用したガイダンスで応答するはずです。
