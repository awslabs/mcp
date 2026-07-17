---
title: "Amazon ElastiCache Memcached MCPサーバー"
---

安全で信頼性の高い接続を通じて Amazon ElastiCache Memcached と対話するための MCP サーバーです

## 機能 {#features}

### 完全な Memcached プロトコルサポート {#complete-memcached-protocol-support}

- すべての標準的な Memcached 操作を完全サポート
- SSL/TLS 暗号化による安全な通信
- 自動的な接続管理とプーリング
- 失敗した操作に対する組み込みのリトライ機構
- 書き込み操作を防止する読み取り専用モード

### 読み取り専用モード {#readonly-mode}

このサーバーは読み取り専用モードで起動でき、あらゆる書き込み操作の実行を防止します。これは、次のようにデータが変更されないことを保証したいシナリオで役立ちます。

- 読み取り専用レプリカ
- 書き込みを制限すべき本番環境
- データ変更のリスクなしで行うデバッグやモニタリング

読み取り専用モードが有効な場合、書き込み操作(set、add、replace、delete など)を実行しようとすると、エラーメッセージが返されます。

## 前提条件 {#prerequisites}

1. [Astral](https://docs.astral.sh/uv/getting-started/installation/) または [GitHub README](https://github.com/astral-sh/uv#installation) から `uv` をインストールします
2. `uv python install 3.10` を使用して Python をインストールします
3. Memcached サーバーへのアクセスが必要です。
4. Amazon ElastiCache Memcached キャッシュへの接続手順については、[こちらをクリック](https://github.com/awslabs/mcp/blob/main/src/memcached-mcp-server/ELASTICACHECONNECT.md)してください


## インストール {#installation}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.memcached-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.memcached-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22MEMCACHED_HOST%22%3A%22your-memcached-host%22%2C%22MEMCACHED_PORT%22%3A%2211211%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.memcached-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMubWVtY2FjaGVkLW1jcC1zZXJ2ZXJAbGF0ZXN0IiwiZW52Ijp7IkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IiLCJNRU1DQUNIRURfSE9TVCI6InlvdXItbWVtY2FjaGVkLWhvc3QiLCJNRU1DQUNIRURfUE9SVCI6IjExMjExIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ%3D%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Memcached%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.memcached-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22MEMCACHED_HOST%22%3A%22your-memcached-host%22%2C%22MEMCACHED_PORT%22%3A%2211211%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

MCP を利用する方法はいくつかあります(例:Kiro の場合は `~/.kiro/settings/mcp.json`)。

```json
{
  "mcpServers": {
    "awslabs.memcached-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.memcached-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "MEMCACHED_HOST": "your-memcached-host",
        "MEMCACHED_PORT": "11211"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

読み取り専用モードで実行する場合:

```json
{
  "mcpServers": {
    "awslabs.memcached-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.memcached-mcp-server@latest", "--readonly"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "MEMCACHED_HOST": "your-memcached-host",
        "MEMCACHED_PORT": "11211"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Windows でのインストール {#windows-installation}

Windows ユーザーの場合、MCP サーバーの設定形式が少し異なります。

```json
{
  "mcpServers": {
    "awslabs.memcached-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.memcached-mcp-server@latest",
        "awslabs.memcached-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "MEMCACHED_HOST": "your-memcached-host",
        "MEMCACHED_PORT": "11211"
      },
    }
  }
}
```

読み取り専用モードで実行する場合:

```json
{
  "mcpServers": {
    "awslabs.memcached-mcp-server": {
      "command": "uvx",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.memcached-mcp-server@latest",
        "awslabs.memcached-mcp-server.exe",
        "--readonly"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "MEMCACHED_HOST": "your-memcached-host",
        "MEMCACHED_PORT": "11211"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

または、`docker build -t awslabs/memcached-mcp-server .` が成功した後に docker を使用する場合:

```json
{
  "mcpServers": {
    "awslabs.memcached-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env",
        "FASTMCP_LOG_LEVEL=ERROR",
        "--env",
        "MEMCACHED_HOST=your-memcached-host",
        "--env",
        "MEMCACHED_PORT=11211",
        "awslabs/memcached-mcp-server:latest"
      ],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

Docker で読み取り専用モードで実行する場合:

```json
{
  "mcpServers": {
    "awslabs.memcached-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env",
        "FASTMCP_LOG_LEVEL=ERROR",
        "--env",
        "MEMCACHED_HOST=your-memcached-host",
        "--env",
        "MEMCACHED_PORT=11211",
        "awslabs/memcached-mcp-server:latest",
        "--readonly"
      ],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## 設定 {#configuration}

### 基本的な接続設定 {#basic-connection-settings}

次の環境変数を使用して接続を設定します。

```bash
# Basic settings
MEMCACHED_HOST=127.0.0.1          # Memcached server hostname
MEMCACHED_PORT=11211              # Memcached server port
MEMCACHED_TIMEOUT=1              # Operation timeout in seconds
MEMCACHED_CONNECT_TIMEOUT=5      # Connection timeout in seconds
MEMCACHED_RETRY_TIMEOUT=1        # Retry delay in seconds
MEMCACHED_MAX_RETRIES=3         # Maximum number of retry attempts
```

### SSL/TLS 設定 {#ssltls-configuration}

次の変数を使用して SSL/TLS サポートを有効化および設定します。

```bash
# SSL/TLS settings
MEMCACHED_USE_TLS=true                           # Enable SSL/TLS
MEMCACHED_TLS_CERT_PATH=/path/to/client-cert.pem # Client certificate
MEMCACHED_TLS_KEY_PATH=/path/to/client-key.pem   # Client private key
MEMCACHED_TLS_CA_CERT_PATH=/path/to/ca-cert.pem  # CA certificate
MEMCACHED_TLS_VERIFY=true                        # Enable cert verification
```

サーバーは次の処理を自動的に行います。
- 接続の確立と管理
- 有効化されている場合の SSL/TLS 暗号化
- 失敗した操作の自動リトライ
- タイムアウトの適用とエラーハンドリング

## 開発 {#development}

### テストの実行 {#running-tests}
```bash
uv venv
source .venv/bin/activate
uv sync
uv run --frozen pytest
```

### Docker イメージのビルド {#building-docker-image}
```bash
docker build -t awslabs/memcached-mcp-server .
```

### Docker コンテナの実行 {#running-docker-container}
```bash
docker run -p 8080:8080 \
  -e MEMCACHED_HOST=host.docker.internal \
  -e MEMCACHED_PORT=11211 \
  awslabs/memcached-mcp-server
```

読み取り専用モードで実行する場合:
```bash
docker run -p 8080:8080 \
  -e MEMCACHED_HOST=host.docker.internal \
  -e MEMCACHED_PORT=11211 \
  awslabs/memcached-mcp-server --readonly
```
