---
title: "AWS Lambda Tool MCP サーバー"
---

コード変更なしで Lambda 関数を選択して MCP ツールとして実行するための、AWS Lambda 向け Model Context Protocol (MCP) サーバーです。

## 機能 {#features}

この MCP サーバーは、MCP クライアントと AWS Lambda 関数の間の**ブリッジ**として機能し、生成 AI モデルが Lambda 関数にツールとしてアクセスして実行できるようにします。これはたとえば、パブリックなネットワークアクセスを提供することなく、社内アプリケーションやデータベースなどのプライベートリソースにアクセスする際に便利です。このアプローチにより、モデルは他の AWS サービス、プライベートネットワーク、およびパブリックインターネットを利用できます。

```mermaid
graph LR
    A[Model] <--> B[MCP Client]
    B <--> C["MCP2Lambda<br>(MCP Server)"]
    C <--> D[Lambda Function]
    D <--> E[Other AWS Services]
    D <--> F[Internet]
    D <--> G[VPC]

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style B fill:#bbf,stroke:#333,stroke-width:2px
    style C fill:#bfb,stroke:#333,stroke-width:4px
    style D fill:#fbb,stroke:#333,stroke-width:2px
    style E fill:#fbf,stroke:#333,stroke-width:2px
    style F fill:#dff,stroke:#333,stroke-width:2px
    style G fill:#ffd,stroke:#333,stroke-width:2px
```

**セキュリティ**の観点では、このアプローチはモデルに Lambda 関数の呼び出しは許可するものの、他の AWS サービスへの直接アクセスは許可しないことで、職務分掌を実現しています。クライアントに必要なのは Lambda 関数を呼び出すための AWS 認証情報だけです。Lambda 関数は（関数のロールを使用して）他の AWS サービスと連携し、パブリックまたはプライベートネットワークにアクセスできます。

## 前提条件 {#prerequisites}

1. [Astral](https://docs.astral.sh/uv/getting-started/installation/) または [GitHub README](https://github.com/astral-sh/uv#installation) から `uv` をインストールします
2. `uv python install 3.10` を使用して Python をインストールします

## インストール {#installation}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.lambda-tool-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.lambda-tool-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FUNCTION_PREFIX%22%3A%22your-function-prefix%22%2C%22FUNCTION_LIST%22%3A%22your-first-function%2C%20your-second-function%22%2C%22FUNCTION_TAG_KEY%22%3A%22your-tag-key%22%2C%22FUNCTION_TAG_VALUE%22%3A%22your-tag-value%22%2C%22FUNCTION_INPUT_SCHEMA_ARN_TAG_KEY%22%3A%22your-function-tag-for-input-schema%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.lambda-tool-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMubGFtYmRhLXRvb2wtbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiQVdTX1BST0ZJTEUiOiJ5b3VyLWF3cy1wcm9maWxlIiwiQVdTX1JFR0lPTiI6InVzLWVhc3QtMSIsIkZVTkNUSU9OX1BSRUZJWCI6InlvdXItZnVuY3Rpb24tcHJlZml4IiwiRlVOQ1RJT05fTElTVCI6InlvdXItZmlyc3QtZnVuY3Rpb24sIHlvdXItc2Vjb25kLWZ1bmN0aW9uIiwiRlVOQ1RJT05fVEFHX0tFWSI6InlvdXItdGFnLWtleSIsIkZVTkNUSU9OX1RBR19WQUxVRSI6InlvdXItdGFnLXZhbHVlIiwiRlVOQ1RJT05fSU5QVVRfU0NIRU1BX0FSTl9UQUdfS0VZIjoieW91ci1mdW5jdGlvbi10YWctZm9yLWlucHV0LXNjaGVtYSJ9fQ%3D%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20Lambda%20Tool%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.lambda-tool-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FUNCTION_PREFIX%22%3A%22your-function-prefix%22%2C%22FUNCTION_LIST%22%3A%22your-first-function%2C%20your-second-function%22%2C%22FUNCTION_TAG_KEY%22%3A%22your-tag-key%22%2C%22FUNCTION_TAG_VALUE%22%3A%22your-tag-value%22%2C%22FUNCTION_INPUT_SCHEMA_ARN_TAG_KEY%22%3A%22your-function-tag-for-input-schema%22%7D%7D) |

MCP クライアントの設定で MCP サーバーを構成します（例: Kiro の場合は `~/.kiro/settings/mcp.json` を編集します）:

```json
{
  "mcpServers": {
    "awslabs.lambda-tool-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.lambda-tool-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "FUNCTION_PREFIX": "your-function-prefix",
        "FUNCTION_LIST": "your-first-function, your-second-function",
        "FUNCTION_TAG_KEY": "your-tag-key",
        "FUNCTION_TAG_VALUE": "your-tag-value",
        "FUNCTION_INPUT_SCHEMA_ARN_TAG_KEY": "your-function-tag-for-input-schema"
      }
    }
  }
}
```

### Windows へのインストール {#windows-installation}

Windows ユーザーの場合、MCP サーバーの設定形式が若干異なります:

```json
{
  "mcpServers": {
    "awslabs.lambda-tool-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.lambda-tool-mcp-server@latest",
        "awslabs.lambda-tool-mcp-server.exe"
      ],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "FUNCTION_PREFIX": "your-function-prefix",
        "FUNCTION_LIST": "your-first-function, your-second-function",
        "FUNCTION_TAG_KEY": "your-tag-key",
        "FUNCTION_TAG_VALUE": "your-tag-value",
        "FUNCTION_INPUT_SCHEMA_ARN_TAG_KEY": "your-function-tag-for-input-schema"
      }
    }
  }
}
```

または、`docker build -t awslabs/bedrock-kb-retrieval-mcp-server .` が成功した後に docker を使用します:

```file
# fictitious `.env` file with AWS temporary credentials
AWS_ACCESS_KEY_ID=ASIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_SESSION_TOKEN=AQoEXAMPLEH4aoAH0gNCAPy...truncated...zrkuWJOgQs8IZZaIv2BXIa2R4Olgk
```

```json
  {
    "mcpServers": {
      "awslabs.lambda-tool-mcp-server": {
        "command": "docker",
        "args": [
          "run",
          "--rm",
          "--interactive",
          "--env",
          "AWS_REGION=us-east-1",
          "--env",
          "FUNCTION_PREFIX=your-function-prefix",
          "--env",
          "FUNCTION_LIST=your-first-function,your-second-function",
          "--env",
          "FUNCTION_TAG_KEY=your-tag-key",
          "--env",
          "FUNCTION_TAG_VALUE=your-tag-value",
          "--env",
          "FUNCTION_INPUT_SCHEMA_ARN_TAG_KEY=your-function-tag-for-input-schema",
          "--env-file",
          "/full/path/to/file/above/.env",
          "awslabs/lambda-tool-mcp-server:latest"
        ],
        "env": {},
        "disabled": false,
        "autoApprove": []
      }
    }
  }
```

注: 認証情報はホスト側から継続的に更新し続ける必要があります

`AWS_PROFILE` と `AWS_REGION` は任意で、デフォルト値はそれぞれ `default` と `us-east-1` です。

`FUNCTION_PREFIX`、`FUNCTION_LIST` のいずれか、または両方を指定できます。両方が空の場合、すべての関数が名前チェックを通過します。
名前チェックの後、`FUNCTION_TAG_KEY` と `FUNCTION_TAG_VALUE` の両方が設定されている場合、関数はさらにタグ（key=value）でフィルタリングされます。
`FUNCTION_TAG_KEY` と `FUNCTION_TAG_VALUE` の一方のみが設定されている場合、関数は選択されず、警告が表示されます。

**重要**: 関数名は MCP ツール名として使用されます。AWS Lambda の関数の説明は MCP ツールの説明として使用されます。関数の説明では、その関数をいつ使用するか（何を提供するか）と、どのように使用するか（どのパラメータを指定するか）を明確にする必要があります。たとえば、社内の顧客関係管理（CRM）システムへのアクセスを提供する関数では、次のような説明が使用できます:
```plaintext
Retrieve customer status on the CRM system based on { 'customerId' } or { 'customerEmail' }
```

Lambda 関数のパラメータは、正式な JSON Schema を提供する EventBridge Schema Registry を通じて提供することもできます。後述の[スキーマサポート](#schema-support)を参照してください。

AWS SAM でデプロイできるサンプル関数が `examples` フォルダに用意されています。

## スキーマサポート {#schema-support}

Lambda MCP サーバーは、AWS EventBridge Schema Registry を通じた入力スキーマをサポートしています。これにより、Lambda 関数の入力に対する正式な JSON Schema ドキュメントが提供されます。

### 設定 {#configuration}

スキーマ検証を使用するには:

1. EventBridge Schema Registry でスキーマを作成します
2. Lambda 関数にスキーマ ARN のタグを付けます:
   ```plaintext
   Key: FUNCTION_INPUT_SCHEMA_ARN_TAG_KEY (configurable)
   Value: arn:aws:schemas:region:account:schema/registry-name/schema-name
   ```
3. タグキーを指定して MCP サーバーを設定します:
   ```json
   {
     "env": {
       "FUNCTION_INPUT_SCHEMA_ARN_TAG_KEY": "your-schema-arn-tag-key"
     }
   }
   ```

Lambda 関数にスキーマタグが付いている場合、MCP サーバーは以下を行います:
1. EventBridge Schema Registry からスキーマを取得します
2. スキーマをツールのドキュメントに追加します

これにより、関数の説明でパラメータを記述する場合と比較して、より優れたドキュメントが提供されます。

## ベストプラクティス {#best-practices}

- `FUNCTION_LIST` を使用して、MCP ツールとして利用可能な関数を指定します。
- `FUNCTION_PREFIX` を使用して、MCP ツールとして利用可能な関数のプレフィックスを指定します。
- `FUNCTION_TAG_KEY` と `FUNCTION_TAG_VALUE` を使用して、MCP ツールとして利用可能な関数のタグキーと値を指定します。
- AWS Lambda の `Description` プロパティ: 関数の説明は MCP ツールの説明として使用されるため、モデルが関数をいつどのように使用すべきかを理解できるよう、非常に詳細に記述してください
- EventBridge Schema Registry を使用して正式な入力検証を提供します:
  - 関数の入力に対する JSON Schema 定義を作成します
  - 関数にスキーマ ARN のタグを付けます
  - MCP サーバーで `FUNCTION_INPUT_SCHEMA_ARN_TAG_KEY` を設定します

## セキュリティに関する考慮事項 {#security-considerations}

この MCP サーバーを使用する際は、以下を考慮してください:

- 指定されたリストに含まれる Lambda 関数、またはプレフィックスで始まる名前を持つ Lambda 関数のみが MCP ツールとしてインポートされます。
- MCP サーバーには Lambda 関数を呼び出すための権限が必要です。
- 各 Lambda 関数は、必要に応じて他の AWS リソースにアクセスするための独自の権限を持ちます。
