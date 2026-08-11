---
title: "AWS Step Functions ツール MCPサーバー"
---

コード変更なしにステートマシンを MCP ツールとして選択・実行するための、AWS Step Functions 向けの Model Context Protocol (MCP) サーバーです。

## 機能 {#features}

この MCP サーバーは、MCP クライアントと AWS Step Functions のステートマシンの間の**ブリッジ**として機能し、生成 AI モデルがステートマシンにアクセスしてツールとして実行できるようにします。これにより、定義を一切変更することなく、既存の Step Functions ワークフローとシームレスに統合できます。このブリッジを通じて、AI モデルは複数の AWS サービスにまたがる操作を調整する、複雑で多段階のビジネスプロセスを実行・管理できます。

このサーバーは Standard ワークフローと Express ワークフローの両方をサポートし、さまざまな実行ニーズに対応します。Standard ワークフローはステータスの追跡が不可欠な長時間実行プロセスに優れ、Express ワークフローは同期実行によって大量・短時間のタスクを処理します。この柔軟性により、さまざまなワークフローパターンや要件を最適に処理できます。

データ品質を確保し、明確なドキュメントを提供するため、このサーバーは入力検証のために EventBridge スキーマレジストリと統合されています。スキーマ情報とステートマシンの定義を組み合わせて包括的なツールドキュメントを生成し、AI モデルが各ワークフローの目的と技術的要件の両方を理解できるようにします。

セキュリティの観点から、このサーバーは IAM ベースの認証・認可を実装し、明確な職務分掌を実現します。モデルは MCP サーバーを通じてステートマシンを呼び出せますが、他の AWS サービスへの直接アクセスは持ちません。代わりに、ステートマシン自体が独自の IAM ロールを使用して AWS サービスとのやり取りを処理し、強力なワークフロー機能を実現しながら堅牢なセキュリティ境界を維持します。

```mermaid
graph LR
    A[Model] <--> B[MCP Client]
    B <--> C["MCP2StepFunctions<br>(MCP Server)"]
    C <--> D[State Machine]
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

## 前提条件 {#prerequisites}

1. [Astral](https://docs.astral.sh/uv/getting-started/installation/) または [GitHub README](https://github.com/astral-sh/uv#installation) から `uv` をインストールします
2. `uv python install 3.10` を使用して Python をインストールします

## インストール {#installation}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.stepfunctions-tool-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.stepfunctions-tool-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22STATE_MACHINE_PREFIX%22%3A%22your-state-machine-prefix%22%2C%22STATE_MACHINE_LIST%22%3A%22your-first-state-machine%2C%20your-second-state-machine%22%2C%22STATE_MACHINE_TAG_KEY%22%3A%22your-tag-key%22%2C%22STATE_MACHINE_TAG_VALUE%22%3A%22your-tag-value%22%2C%22STATE_MACHINE_INPUT_SCHEMA_ARN_TAG_KEY%22%3A%22your-state-machine-tag-for-input-schema%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.stepfunctions-tool-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuc3RlcGZ1bmN0aW9ucy10b29sLW1jcC1zZXJ2ZXJAbGF0ZXN0IiwiZW52Ijp7IkFXU19QUk9GSUxFIjoieW91ci1hd3MtcHJvZmlsZSIsIkFXU19SRUdJT04iOiJ1cy1lYXN0LTEiLCJTVEFURV9NQUNISU5FX1BSRUZJWCI6InlvdXItc3RhdGUtbWFjaGluZS1wcmVmaXgiLCJTVEFURV9NQUNISU5FX0xJU1QiOiJ5b3VyLWZpcnN0LXN0YXRlLW1hY2hpbmUsIHlvdXItc2Vjb25kLXN0YXRlLW1hY2hpbmUiLCJTVEFURV9NQUNISU5FX1RBR19LRVkiOiJ5b3VyLXRhZy1rZXkiLCJTVEFURV9NQUNISU5FX1RBR19WQUxVRSI6InlvdXItdGFnLXZhbHVlIiwiU1RBVEVfTUFDSElORV9JTlBVVF9TQ0hFTUFfQVJOX1RBR19LRVkiOiJ5b3VyLXN0YXRlLW1hY2hpbmUtdGFnLWZvci1pbnB1dC1zY2hlbWEifX0%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Step%20Functions%20Tool%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.stepfunctions-tool-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22STATE_MACHINE_PREFIX%22%3A%22your-state-machine-prefix%22%2C%22STATE_MACHINE_LIST%22%3A%22your-first-state-machine%2C%20your-second-state-machine%22%2C%22STATE_MACHINE_TAG_KEY%22%3A%22your-tag-key%22%2C%22STATE_MACHINE_TAG_VALUE%22%3A%22your-tag-value%22%2C%22STATE_MACHINE_INPUT_SCHEMA_ARN_TAG_KEY%22%3A%22your-state-machine-tag-for-input-schema%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

MCP サーバーを MCP クライアントの設定に追加します（例えば Kiro の場合は `~/.kiro/settings/mcp.json` を編集します）。

```json
{
  "mcpServers": {
    "awslabs.stepfunctions-tool-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.stepfunctions-tool-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "STATE_MACHINE_PREFIX": "your-state-machine-prefix",
        "STATE_MACHINE_LIST": "your-first-state-machine, your-second-state-machine",
        "STATE_MACHINE_TAG_KEY": "your-tag-key",
        "STATE_MACHINE_TAG_VALUE": "your-tag-value",
        "STATE_MACHINE_INPUT_SCHEMA_ARN_TAG_KEY": "your-state-machine-tag-for-input-schema"
      }
    }
  }
}
```
### Windows でのインストール {#windows-installation}

Windows ユーザーの場合、MCP サーバーの設定形式は少し異なります。

```json
{
  "mcpServers": {
    "awslabs.stepfunctions-tool-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.stepfunctions-tool-mcp-server@latest",
        "awslabs.stepfunctions-tool-mcp-server.exe"
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


または `docker build -t awslabs/stepfunctions-tool-mcp-server .` が成功した後に docker で実行します。

```file
# fictitious `.env` file with AWS temporary credentials
AWS_ACCESS_KEY_ID=ASIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_SESSION_TOKEN=AQoEXAMPLEH4aoAH0gNCAPy...truncated...zrkuWJOgQs8IZZaIv2BXIa2R4Olgk
```

```json
  {
    "mcpServers": {
      "awslabs.stepfunctions-tool-mcp-server": {
        "command": "docker",
        "args": [
          "run",
          "--rm",
          "--interactive",
          "--env",
          "AWS_REGION=us-east-1",
          "--env",
          "STATE_MACHINE_PREFIX=your-state-machine-prefix",
          "--env",
          "STATE_MACHINE_LIST=your-first-state-machine,your-second-state-machine",
          "--env",
          "STATE_MACHINE_TAG_KEY=your-tag-key",
          "--env",
          "STATE_MACHINE_TAG_VALUE=your-tag-value",
          "--env",
          "STATE_MACHINE_INPUT_SCHEMA_ARN_TAG_KEY=your-state-machine-tag-for-input-schema",
          "--env-file",
          "/full/path/to/file/above/.env",
          "awslabs/stepfunctions-tool-mcp-server:latest"
        ],
        "env": {},
        "disabled": false,
        "autoApprove": []
      }
    }
  }
```

注意: 認証情報はホスト側で更新し続ける必要があります。

`AWS_PROFILE` と `AWS_REGION` はオプションで、デフォルト値はそれぞれ `default` と `us-east-1` です。

`STATE_MACHINE_PREFIX`、`STATE_MACHINE_LIST`、またはその両方を指定できます。両方が空の場合、すべてのステートマシンが名前チェックを通過します。
名前チェックの後、`STATE_MACHINE_TAG_KEY` と `STATE_MACHINE_TAG_VALUE` の両方が設定されている場合、ステートマシンはさらにタグ（key=value）でフィルタリングされます。
`STATE_MACHINE_TAG_KEY` と `STATE_MACHINE_TAG_VALUE` のどちらか一方だけが設定されている場合は、ステートマシンは選択されず、警告が表示されます。

## ツールドキュメント {#tool-documentation}

MCP サーバーは、AI モデルがステートマシンを効果的に理解・利用できるよう、複数の情報源を組み合わせて包括的なツールドキュメントを構築します。

1. **ステートマシンの説明**: ステートマシンの説明フィールドがツール説明のベースになります。例えば次のとおりです。
   ```plaintext
   Retrieve customer status on the CRM system based on { 'customerId' } or { 'customerEmail' }
   ```

2. **ワークフローの説明**: ステートマシン定義の Comment フィールドがワークフローのコンテキストを追加します。例えば次のとおりです。
   ```json
   {
     "Comment": "This workflow first looks up a customer ID from email, then retrieves their info",
     "StartAt": "GetCustomerId",
     "States": { ... }
   }
   ```

3. **入力スキーマ**: サーバーは EventBridge スキーマレジストリと統合し、ステートマシンの入力に対する正式な JSON Schema ドキュメントを提供します。スキーマサポートを有効にするには次のようにします。
   - EventBridge スキーマレジストリでスキーマを作成します
   - ステートマシンにスキーマ ARN をタグ付けします。
     ```plaintext
     Key: STATE_MACHINE_INPUT_SCHEMA_ARN_TAG_KEY (configurable)
     Value: arn:aws:schemas:region:account:schema/registry-name/schema-name
     ```
   - MCP サーバーを設定します。
     ```json
     {
       "env": {
         "STATE_MACHINE_INPUT_SCHEMA_ARN_TAG_KEY": "your-schema-arn-tag-key"
       }
     }
     ```

サーバーはこれらの情報源を統一されたドキュメント形式に組み合わせます。
```plaintext
[State Machine Description]

Workflow Description: [Comment from state machine definition]

Input Schema:
[JSON Schema from EventBridge Schema Registry]
```

この包括的なドキュメントは、AI モデルが各ステートマシンの目的と技術的要件の両方を理解するのに役立ち、正式なスキーマサポートによって正しい入力形式が保証されます。

## ベストプラクティス {#best-practices}

- `STATE_MACHINE_LIST` を使用して、MCP ツールとして利用可能なステートマシンを指定します。
- `STATE_MACHINE_PREFIX` を使用して、MCP ツールとして利用可能なステートマシンのプレフィックスを指定します。
- `STATE_MACHINE_TAG_KEY` と `STATE_MACHINE_TAG_VALUE` を使用して、MCP ツールとして利用可能なステートマシンのタグキーと値を指定します。
- AWS Step Functions の `Description` プロパティ: ステートマシンの説明は MCP ツールの説明として使用されるため、モデルがステートマシンをいつどのように使用すべきかを理解できるよう、非常に詳細に記述する必要があります
- ステートマシン定義の `Comment` フィールドを使用してワークフローのドキュメントを追加します。
  - ワークフローの目的とステップを説明します
  - 重要なロジックや条件を説明します
  - 期待される入力と出力を記述します
- EventBridge スキーマレジストリを使用して正式な入力定義を提供します。
  - ステートマシンの入力に対する JSON Schema 定義を作成します
  - ステートマシンにスキーマ ARN をタグ付けします
  - MCP サーバーで `STATE_MACHINE_INPUT_SCHEMA_ARN_TAG_KEY` を設定します

## セキュリティに関する考慮事項 {#security-considerations}

この MCP サーバーを使用する際は、次の点を考慮する必要があります。

- 指定したリストに含まれるステートマシン、またはプレフィックスで始まる名前を持つステートマシンのみが MCP ツールとしてインポートされます。
- MCP サーバーには、ステートマシンを呼び出すための権限が必要です。
- 各ステートマシンには、オプションで他の AWS リソースにアクセスするための独自の権限があります。
