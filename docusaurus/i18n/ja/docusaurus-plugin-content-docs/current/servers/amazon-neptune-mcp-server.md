---
title: "AWS Labs Amazon Neptune MCPサーバー"
---

Neptune Database に対しては openCypher および Gremlin、Neptune Analytics に対しては openCypher を使用して、ステータスやスキーマの取得、クエリの実行を行うことができる Amazon Neptune MCP サーバーです。

## 機能 {#features}

Amazon Neptune MCP サーバーは、次の機能を提供します。

1. **クエリの実行**: 設定されたデータベースに対して openCypher や Gremlin のクエリを実行します
2. **スキーマ**: 設定されたグラフのスキーマをテキスト文字列として取得します
3. **ステータス**: グラフがサーバーから「Available（利用可能）」か「Unavailable（利用不可）」かを確認します。これはグラフが接続されていることを確認するのに役立ちます。

### AWS の要件 {#aws-requirements}

1. **AWS CLI の設定**: Amazon Neptune へのアクセス権を持つ認証情報と AWS_PROFILE で AWS CLI が設定されている必要があります
2. **Amazon Neptune**: 少なくとも 1 つの Amazon Neptune Database または Amazon Neptune Analytics グラフが必要です。
3. **IAM 権限**: IAM ロール/ユーザーには、次の操作を行うための適切な権限が必要です。
   - Amazon Neptune へのアクセス
   - Amazon Neptune へのクエリ
4. **アクセス**: サーバーを実行する場所から Amazon Neptune インスタンスにアクセスできる必要があります。Neptune Database はプライベート VPC 内に存在するため、そのプライベート VPC へのアクセスが必要です。Neptune Analytics は、設定されている場合はパブリックエンドポイントを使用してアクセスできますが、そうでない場合はプライベートエンドポイントへのアクセスが必要になります。

注: このサーバーは送信されたあらゆるクエリを実行します。これには変更を伴うアクションと読み取り専用アクションの両方が含まれる可能性があります。次に示すとおり、特定のデータプレーンアクションを許可/禁止するようロールの権限を適切に設定してください。
* [Neptune Database](https://docs.aws.amazon.com/neptune/latest/userguide/security.html)
* [Neptune Analytics](https://docs.aws.amazon.com/neptune-analytics/latest/userguide/security.html)


## 前提条件 {#prerequisites}

1. [Astral](https://docs.astral.sh/uv/getting-started/installation/) または [GitHub README](https://github.com/astral-sh/uv#installation) から `uv` をインストールします
2. `uv python install 3.10` で Python をインストールします

## インストール {#installation}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.amazon-neptune-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-neptune-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22NEPTUNE_ENDPOINT%22%3A%22https%3A//your-neptune-cluster-id.region.neptune.amazonaws.com%3A8182%22%2C%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.amazon-neptune-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYW1hem9uLW5lcHR1bmUtbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiTkVQVFVORV9FTkRQT0lOVCI6Imh0dHBzOi8veW91ci1uZXB0dW5lLWNsdXN0ZXItaWQucmVnaW9uLm5lcHR1bmUuYW1hem9uYXdzLmNvbTo4MTgyIiwiQVdTX1BST0ZJTEUiOiJ5b3VyLWF3cy1wcm9maWxlIiwiQVdTX1JFR0lPTiI6InVzLWVhc3QtMSIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Amazon%20Neptune%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-neptune-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22NEPTUNE_ENDPOINT%22%3A%22https%3A%2F%2Fyour-neptune-cluster-id.region.neptune.amazonaws.com%3A8182%22%2C%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

以下は MCP クライアントの設定例です。ただし、クライアントによっては異なる形式が必要になる場合があります。


```json
{
  "mcpServers": {
    "Neptune Query": {
      "command": "uvx",
      "args": ["awslabs.amazon-neptune-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "INFO",
        "NEPTUNE_ENDPOINT": "<INSERT NEPTUNE ENDPOINT IN FORMAT SPECIFIED BELOW>"
      }
    }
  }
}

```
### Windows へのインストール {#windows-installation}

Windows ユーザーの場合、MCP サーバーの設定形式は少し異なります。

```json
{
  "mcpServers": {
    "awslabs.amazon-neptune-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.amazon-neptune-mcp-server@latest",
        "awslabs.amazon-neptune-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "INFO",
        "NEPTUNE_ENDPOINT": "<INSERT NEPTUNE ENDPOINT IN FORMAT SPECIFIED BELOW>"
      }
    }
  }
}
```

### Docker の設定 {#docker-configuration}
`docker build -t awslabs/amazon-neptune-mcp-server .` でビルドした後、次のように設定します。

```
{
  "mcpServers": {
    "awslabs.amazon-neptune-mcp-server": {
        "command": "docker",
        "args": [
          "run",
          "--rm",
          "-i",
          "awslabs/amazon-neptune-mcp-server"
        ],
        "env": {
        "FASTMCP_LOG_LEVEL": "INFO",
        "NEPTUNE_ENDPOINT": "<INSERT NEPTUNE ENDPOINT IN FORMAT SPECIFIED BELOW>"
        },
        "disabled": false,
        "autoApprove": []
    }
  }
}
```

Neptune エンドポイントを指定する際は、次の形式が想定されています。

Neptune Database の場合:
`neptune-db://<Cluster Endpoint>`

Neptune Analytics の場合:
`neptune-graph://<graph identifier>`
