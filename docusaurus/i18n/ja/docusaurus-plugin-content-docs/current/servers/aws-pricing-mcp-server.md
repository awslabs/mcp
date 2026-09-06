---
title: AWS Pricing MCPサーバー
---

リアルタイムのAWS料金情報にアクセスし、コスト分析機能を提供するMCPサーバーです

**重要な注意事項**: このサーバーはAWS Pricing APIからリアルタイムの料金データを提供します。AIアシスタントが常に正しくフィルターを構築したり、絶対的に最安のオプションを特定したりできることは保証できません。すべての呼び出しは無料です。

## 機能 {#features}

### AWS料金の検索と情報取得 {#aws-pricing-discovery--information}

- **サービスカタログの探索**: 料金情報が利用可能なすべてのAWSサービスを検索できます
- **料金属性の検出**: 任意のAWSサービスについて、フィルタリング可能なディメンション（インスタンスタイプ、リージョン、ストレージクラスなど）を特定できます
- **リアルタイム料金クエリ**: 複数オプションの比較やパターンマッチングを含む高度なフィルタリング機能を使って、最新の料金データにアクセスできます
- **マルチリージョン料金比較**: 1回のクエリで複数のAWSリージョン間の料金を比較できます
- **一括料金データアクセス**: 履歴分析やオフライン処理のために、完全な料金データセットをCSV/JSON形式でダウンロードできます

### コスト分析と計画 {#cost-analysis--planning}

- **詳細なコストレポート生成**: 単価、計算の内訳、使用シナリオを含む包括的なコスト分析レポートを作成できます
- **インフラストラクチャプロジェクト分析**: CDKおよびTerraformプロジェクトをスキャンし、AWSサービスとその構成を自動的に特定します
- **アーキテクチャパターンのガイダンス**: 特にAmazon Bedrockサービスについて、詳細なアーキテクチャパターンとコストに関する考慮事項を取得できます
- **コスト最適化の推奨事項**: AWS Well-Architected Frameworkに沿ったコスト最適化の提案を受け取れます

### 自然言語による料金データのクエリ {#query-pricing-data-with-natural-language}

- 複雑なクエリ言語を必要とせず、平易な言葉でAWSの料金について質問できます
- あらゆるAWSサービスについて、AWS Pricing APIから即座に回答を得られます
- 柔軟なフィルタリングオプションで包括的な料金情報を取得できます

## 前提条件 {#prerequisites}

1. [Astral](https://docs.astral.sh/uv/getting-started/installation/) または [GitHub README](https://github.com/astral-sh/uv#installation) から `uv` をインストールします
2. `uv python install 3.10` を使用してPythonをインストールします
3. AWSサービスにアクセスできるAWS認証情報を設定します
   - 適切な権限を持つAWSアカウントが必要です
   - `aws configure` または環境変数でAWS認証情報を設定します
   - AWS Pricing APIにアクセスするために、IAMロール/ユーザーに `pricing:*` 権限があることを確認してください

## インストール {#installation}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.aws-pricing-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-pricing-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22AWS_PROFILE%22%3A%22default%22%2C%22AWS_REGION%22%3A%22us-east-1%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.aws-pricing-mcp-server&config=ewogICAgImNvbW1hbmQiOiAidXZ4IGF3c2xhYnMuYXdzLXByaWNpbmctbWNwLXNlcnZlckBsYXRlc3QiLAogICAgImVudiI6IHsKICAgICAgIkZBU1RNQ1BfTE9HX0xFVkVMIjogIkVSUk9SIiwKICAgICAgIkFXU19QUk9GSUxFIjogImRlZmF1bHQiLAogICAgICAiQVdTX1JFR0lPTiI6ICJ1cy1lYXN0LTEiCiAgICB9LAogICAgImRpc2FibGVkIjogZmFsc2UsCiAgICAiYXV0b0FwcHJvdmUiOiBbXQogIH0K) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20Pricing%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-pricing-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22AWS_PROFILE%22%3A%22default%22%2C%22AWS_REGION%22%3A%22us-east-1%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |


### ⚡ uvの使用 {#-using-uv}

MCPクライアントの設定でMCPサーバーを構成します（例: Kiroの場合は `~/.kiro/settings/mcp.json` を編集します）:


**Linux/MacOSユーザーの場合:**

```json
{
  "mcpServers": {
    "awslabs.aws-pricing-mcp-server": {
      "command": "uvx",
      "args": [
         "awslabs.aws-pricing-mcp-server@latest"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-east-1"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

**Windowsユーザーの場合:**

```json
{
  "mcpServers": {
    "awslabs.aws-pricing-mcp-server": {
      "command": "uvx",
      "args": [
         "--from",
         "awslabs.aws-pricing-mcp-server@latest",
         "awslabs.aws-pricing-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-east-1"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Dockerの使用 {#using-docker}

または、`docker build -t awslabs/aws-pricing-mcp-server .` が成功した後にDockerを使用します:

```file
# fictitious `.env` file with AWS temporary credentials
AWS_ACCESS_KEY_ID=ASIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_SESSION_TOKEN=AQoEXAMPLEH4aoAH0gNCAPy...truncated...zrkuWJOgQs8IZZaIv2BXIa2R4Olgk
AWS_REGION=us-east-1
```

```json
  {
    "mcpServers": {
      "awslabs.aws-pricing-mcp-server": {
        "command": "docker",
        "args": [
          "run",
          "--rm",
          "--interactive",
          "--env",
          "FASTMCP_LOG_LEVEL=ERROR",
          "--env-file",
          "/full/path/to/file/above/.env",
          "awslabs/aws-pricing-mcp-server:latest"
        ],
        "env": {},
        "disabled": false,
        "autoApprove": []
      }
    }
  }
```

注意: 認証情報はホスト側で更新し続ける必要があります

### AWS認証 {#aws-authentication}

このMCPサーバーには、特定のAWS権限と設定が必要です。

#### 必要な権限 {#required-permissions}
AWS Pricing APIにアクセスするには、AWS IAMロールまたはユーザーに `pricing:*` 権限が必要です。このサーバーは一般公開されているAWS料金情報のみにアクセスし、ユーザー固有のデータは一切取得しません。すべての料金API呼び出しは**無料**であり、費用は発生しません。

#### 設定 {#configuration}
このサーバーは2つの主要な環境変数を使用します。

- **`AWS_PROFILE`**: AWS設定ファイルから使用するAWSプロファイルを指定します。指定しない場合、デフォルトで "default" プロファイルが使用されます。
- **`AWS_REGION`**: 地理的に最も近いAWS Pricing APIエンドポイントを決定します。リクエストを最寄りのリージョンエンドポイントにルーティングすることで、パフォーマンスが向上します。

```json
"env": {
  "AWS_PROFILE": "default",
  "AWS_REGION": "us-east-1"
}
```

### コストレポートの出力ディレクトリ {#cost-report-output-directory}

`generate_cost_report` ツールは、`output_file` パラメータを使用して生成したレポートをファイルに保存できます。意図した場所の外へのパストラバーサルによる書き込みを防ぐため、`output_file` はベースディレクトリ内に制限されています。

- **`AWS_PRICING_MCP_OUTPUT_DIR`**（オプション）: レポートの書き込み先となるベースディレクトリです。デフォルトはサーバープロセスの現在の作業ディレクトリです。

パスは解決された上で、このベースディレクトリ内に収まっている必要があります。ベースディレクトリの外を指す絶対パス、`..` によるトラバーサルセグメント、およびベースの外に抜けるシンボリックリンクはすべて拒否されます。レポートを別の場所に書き込めるようにするには、この変数を目的のディレクトリに設定してください。

```json
"env": {
  "AWS_PROFILE": "default",
  "AWS_REGION": "us-east-1",
  "AWS_PRICING_MCP_OUTPUT_DIR": "/path/to/reports"
}
```
