---
title: "AWS S3 Tables MCPサーバー"
---

> ## ⚠️ 重要: エージェントの責任はお客様にあります
>
> MCP サーバーを使用するエージェントのアクションと権限については、お客様が単独で責任を負います。
>
> - デフォルトでは、MCP サーバーは**読み取り専用モード**で動作します。
> - 書き込みアクセスを有効にするには、**必要な IAM 権限を明示的に MCP に設定**し、"--allow-write" フラグを使用して、MCP サーバーによる S3 Tables への作成および追加操作を有効にする必要があります。
> - 常に**最小権限の原則**に従い、エージェントの動作に必要な権限のみを付与してください。
> - 書き込み操作を有効にする場合は、**データのバックアップを取得すること**を推奨し、実行前に LLM が生成した指示を慎重に検証してください。
> - AWS S3 Tables MCP サーバーを自動化ワークフローに統合する際は、慎重に行うことを推奨します。
>
> 権限の設定ミスや未検証のエージェントアクションは、**データ損失、操作の失敗、または予期しない LLM の動作**を引き起こす可能性があります。

AI アシスタントが S3 ベースのテーブルストレージと対話できるようにする、AWS S3 Tables 向けの AWS Labs Model Context Protocol (MCP) サーバーです。

## 概要 {#overview}

S3 Tables MCP サーバーは、テーブルの作成とクエリ、S3 にアップロードされた CSV ファイルからの直接的なテーブル生成、S3 Metadata Table を通じたメタデータへのアクセスといった機能を提供することで、S3 ベースのテーブル管理を簡素化します。これにより、データ操作の効率化と S3 に保存されたデータセットとのより容易な統合が可能になります。

## 機能 {#features}

- **テーブルバケット管理**: S3 Table Bucket を作成・一覧表示し、表形式データを大規模に整理できます。(削除や更新操作はサポートされていません。)
- **名前空間管理**: テーブルバケット内で名前空間を定義・一覧表示し、データの論理的な分離と整理を行えます。(削除や更新操作はサポートされていません。)
- **テーブル管理**: 名前空間内の個々のテーブルを作成、名前変更、一覧表示し、柔軟なデータモデリングを実現します。(削除や一般的な更新操作はなく、名前変更のみサポートされています。)
- **メンテナンス設定**: テーブルおよびバケットのメンテナンス設定を取得できます。(読み取り専用。更新や削除は不可。)
- **ポリシー管理**: アクセスとセキュリティを制御するため、テーブルおよびバケットのリソースポリシーにアクセスできます。(読み取り専用。更新や削除は不可。)
- **メタデータ管理**: スキーマやストレージ情報を含む詳細なテーブルメタデータを表示できます。メタデータファイルは更新可能です。
- **読み取り専用モード**: すべての操作を読み取り専用に制限し、いかなる変更も防止するオプションのセキュリティモードを有効化できます。
- **SQL クエリサポート**: S3 Tables に対して**読み取り専用**の SQL クエリを直接実行し、シームレスなデータ分析とレポート作成が行えます。書き込み操作については、**新規データの追加**(インサート)のみがサポートされており、SQL による更新や削除は利用できません。
- **CSV からテーブルへの変換**: S3 にアップロードされた CSV ファイルから S3 Table を自動的に作成し、データの取り込みとオンボーディングを効率化します。(この操作によるテーブルの削除や更新は不可。)
- **メタデータディスカバリー**: S3 Metadata Table を通じて包括的なバケットメタデータを検出・アクセスし、データガバナンスとカタログ化を強化します。(読み取り専用。)

## 前提条件 {#prerequisites}

1. [Astral](https://docs.astral.sh/uv/getting-started/installation/) または [GitHub README](https://github.com/astral-sh/uv#installation) から `uv` をインストールします
2. `uv python install 3.10` を使用して Python をインストールします
3. AWS サービスへのアクセス権を持つ AWS 認証情報を設定します
   - 適切な権限を持つ AWS アカウントが必要です
   - `aws configure` または環境変数で AWS 認証情報を設定します

## セットアップ {#setup}

### インストール {#installation}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.s3-tables-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.s3-tables-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.s3-tables-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuczMtdGFibGVzLW1jcC1zZXJ2ZXJAbGF0ZXN0IiwiZW52Ijp7IkFXU19QUk9GSUxFIjoieW91ci1hd3MtcHJvZmlsZSIsIkFXU19SRUdJT04iOiJ1cy1lYXN0LTEifX0%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=S3%20Tables%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.s3-tables-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%7D%7D) |

MCP クライアントの設定で MCP サーバーを設定します(例えば Kiro の場合は `~/.kiro/settings/mcp.json` を編集します)。

```json
{
  "mcpServers": {
    "awslabs.s3-tables-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.s3-tables-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```
### Windows でのインストール {#windows-installation}

Windows ユーザーの場合、MCP サーバーの設定形式は若干異なります。

```json
{
  "mcpServers": {
    "awslabs.s3-tables-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.s3-tables-mcp-server@latest",
        "awslabs.s3-tables-mcp-server.exe"
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


または、`docker build -t awslabs/s3-tables-mcp-server.` が成功した後に docker を使用します。

```file
# fictitious `.env` file with AWS temporary credentials
AWS_ACCESS_KEY_ID=<from the profile you set up>
AWS_SECRET_ACCESS_KEY=<from the profile you set up>
AWS_SESSION_TOKEN=<from the profile you set up>
```

```json
{
  "mcpServers": {
    "awslabs.s3-tables-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env-file",
        "/full/path/to/file/above/.env",
        "awslabs/s3-tables-mcp-server:latest"
      ],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## サーバー設定オプション {#server-configuration-options}

AWS S3 Tables MCP サーバーは、その動作を設定するために使用できる複数のコマンドライン引数をサポートしています。

### `--allow-write` {#--allow-write}

ユーザーの AWS アカウント内でリソースを作成または変更するツールを有効にします。このフラグが有効になっていない場合、サーバーは読み取り操作のみを許可する読み取り専用モードで動作します。これにより、テーブルへのいかなる変更も防止され、セキュリティが強化されます。読み取り専用モードでは次のようになります。

- 読み取り操作(`list_table_buckets`、`list_namespaces`、`list_tables`)は通常どおり動作します
- 書き込み操作(`create_table_bucket`、`delete_table_bucket`、`append data` など)はブロックされ、権限エラーを返します

このモードは特に次の用途に有用です。
- デモンストレーション環境
- セキュリティ上の配慮が必要なアプリケーション
- 一般公開されている AI アシスタントとの統合
- 本番環境のテーブルを意図しない変更から保護

例:
```json
{
  "mcpServers": {
    "awslabs.s3-tables-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.s3-tables-mcp-server@latest",
        "--allow-write"
      ],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

### `--log-dir` {#--log-dir}

サーバーがログファイルを書き込むディレクトリを指定します。指定しない場合、デフォルトのログディレクトリはオペレーティングシステムによって異なります。

- **macOS**: `~/Library/Logs`
- **Windows**: `~/AppData/Local/Logs`
- **Linux/その他**: `~/.local/share/s3-tables-mcp-server/logs/`

`--log-dir` フラグにカスタムパスを指定することで、デフォルトを上書きできます。例:

```json
{
  "mcpServers": {
    "awslabs.s3-tables-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.s3-tables-mcp-server@latest",
        "--log-dir",
        "/tmp/s3-tables-logs"
      ],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

## 使用例 {#usage-examples}

| プロンプト | 説明 |
|--------|-------------|
| `Query all available metadata about test-bucket` | 特定のテーブルバケットについて、名前空間、テーブル、設定の詳細を含む包括的なメタデータ情報を取得します |
| `Find top 3 customers by spending in the transactions table` | SQL クエリを実行して顧客のトランザクションデータを分析し、支出額が最も多い顧客を特定します |
| `Create a table bucket with name hello-world` | 指定した名前でテーブルデータを整理・管理するための新しい S3 Tables バケットを作成します |
| `Create an s3 table from s3://my-bucket/data.csv` | S3 上の既存の CSV ファイルから S3 Table を自動的に生成し、データの即時のクエリと分析を可能にします |
| `List all tables in the sales namespace` | データの検出と探索のために、特定の名前空間内で利用可能なすべてのテーブルを表示します |
| `Show the schema for customer_data table` | データの形式と型を理解するために、テーブル構造とカラム定義を取得します |
| `Run a query to find monthly revenue trends` | **読み取り専用**の SQL クエリを使用してデータ分析を実行し、保存されたテーブルデータからビジネスインサイトを抽出します。書き込み操作については、新規データの追加(インサート)のみがサポートされており、SQL による更新や削除は利用できません。 |

## S3 Tables MCP サーバーで Kiro を使用する {#using-kiro-with-s3-tables-mcp-server}

Kiro は追加のコンテキストがあると、より良い回答やコード提案を提供できます。S3 Tables に対する Kiro の理解を高めるために、提供されているコンテキストファイルを Kiro 環境に追加できます。

### Kiro CLI にコンテキストを追加する方法 {#how-to-add-context-to-kiro-cli}

1. **CONTEXT.md ファイルをダウンロードする**
   - このプロジェクトの GitHub リポジトリから `CONTEXT.md` ファイルをダウンロードします。

2. **Kiro CLI を起動する**
   - 次のコマンドを実行して Kiro とのチャットセッションを開始します。
     ```sh
     kiro-cli chat
     ```

3. **コンテキストファイルを追加する**
   - Kiro のチャットで次を実行します。
     ```sh
     /context add <path>/CONTEXT.md
     ```
   - `<path>` を、`CONTEXT.md` をダウンロードした実際のパスに置き換えてください。

これで、Kiro CLI は S3 Tables に関するより充実したコンテキストを持ち、より関連性の高い回答を提供できるようになります。

## セキュリティに関する考慮事項 {#security-considerations}

この MCP サーバーを使用する際は、次の点を考慮してください。

- MCP サーバーには AWS S3 Tables リソースを作成・管理するための権限が必要です
- リソースの作成はデフォルトで無効になっており、`--allow-write` フラグを設定することで有効にできます
- IAM 権限を設定する際は最小権限の原則に従ってください
- 環境ごと(開発、テスト、本番)に別々の AWS プロファイルを使用してください

## トラブルシューティング {#troubleshooting}

- 権限エラーが発生した場合は、IAM ユーザーに正しいポリシーがアタッチされているか確認してください
- 接続の問題については、ネットワーク設定とセキュリティグループを確認してください
- AWS S3 Tables 全般の問題については、[AWS S3 Tables ドキュメント](https://docs.aws.amazon.com/s3/)を参照してください
