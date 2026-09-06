---
title: "Amazon Keyspaces (for Apache Cassandra) サーバー"
---

Amazon Keyspaces および Apache Cassandra を操作するための Amazon Keyspaces (for Apache Cassandra) MCP サーバーです。

## 概要 {#overview}

Amazon Keyspaces MCP サーバーは Model Context Protocol (MCP) を実装し、Kiro のような AI アシスタントが自然言語を通じて Amazon Keyspaces または Apache Cassandra データベースを操作できるようにします。このサーバーを使うと、CQL コードを直接記述することなく、データベースのスキーマを探索したり、クエリを実行したり、クエリのパフォーマンスを分析したりできます。

## 機能 {#features}

Amazon Keyspaces (for Apache Cassandra) MCP サーバーは、以下の機能を提供します。
1. **スキーマ**: キースペースとテーブルを探索します。
2. **クエリの実行**: 設定されたデータベースに対して CQL の SELECT クエリを実行します。
3. **クエリ分析**: クエリのパフォーマンスを改善するためのフィードバックと提案を取得します。
4. **Cassandra 互換**: Amazon Keyspaces でも、Apache Cassandra でも利用できます。

この MCP サーバーが役立つプロンプトの例を以下に示します。
- 「Cassandra データベース内のすべてのキースペースを一覧表示して」
- 「'sales' キースペース内のテーブルを表示して」
- 「'sales' キースペースの 'users' テーブルについて説明して」
- 「'products' テーブルのスキーマは何ですか?」
- 「'sales' の 'users' テーブルからすべてのユーザーを取得する SELECT クエリを実行して」
- 「'events' テーブルから最初の 10 件のレコードをクエリして」
- 「このクエリのパフォーマンスを分析して: SELECT * FROM users WHERE last_name = 'Smith'」
- 「このクエリは効率的ですか: SELECT * FROM orders WHERE order_date > '2023-01-01'?」

## インストール {#installation}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.amazon-keyspaces-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-keyspaces-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.amazon-keyspaces-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYW1hem9uLWtleXNwYWNlcy1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJBV1NfUFJPRklMRSI6InlvdXItYXdzLXByb2ZpbGUiLCJBV1NfUkVHSU9OIjoidXMtZWFzdC0xIiwiRkFTVE1DUF9MT0dfTEVWRUwiOiJFUlJPUiJ9LCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Amazon%20Keyspaces%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-keyspaces-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

### 前提条件 {#prerequisites}

- Python 3.10 または 3.11（asyncore モジュールが削除されたため、Python 3.12 以降は完全にはサポートされていません）
- パスワード認証をサポートする Amazon Keyspaces インスタンスまたは Apache Cassandra クラスターへのアクセス
- 適切な Cassandra ログイン認証情報
- Starfield デジタル証明書（Amazon Keyspaces では必須）

### PyPI からのインストール {#install-from-pypi}

```bash
pip install awslabs.amazon-keyspaces-mcp-server
```

### ソースからのインストール {#install-from-source}

1. リポジトリをクローンします。
   ```bash
   git clone https://github.com/awslabs/mcp.git
   cd mcp/src/amazon-keyspaces-mcp-server
   ```

2. 仮想環境を作成します。
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. パッケージをインストールします。
   ```bash
   pip install -e .
   ```

## 設定 {#configuration}

ホームディレクトリに `.keyspaces-mcp` ディレクトリを作成します。その `.keyspaces-mcp` ディレクトリ内に、データベース接続設定を記述した `env` ファイルを作成します。

```
# Set to true for Amazon Keyspaces, false for Apache Cassandra
DB_USE_KEYSPACES=true

# Cassandra configuration (for native Cassandra)
DB_CASSANDRA_CONTACT_POINTS=127.0.0.1
DB_CASSANDRA_PORT=9042
DB_CASSANDRA_LOCAL_DATACENTER=datacenter1
DB_CASSANDRA_USERNAME=
DB_CASSANDRA_PASSWORD=

# Keyspaces configuration (for Amazon Keyspaces)
DB_KEYSPACES_ENDPOINT=cassandra.us-west-2.amazonaws.com
DB_KEYSPACES_REGION=us-west-2
```

設定ファイルを使う代わりに、これらの設定はすべて環境変数として直接設定することもできます。

### 認証情報 {#authentication-credentials}

この MCP サーバーは、Amazon Keyspaces と Apache Cassandra の両方でユーザー名とパスワードによる認証を使用します。

- **Amazon Keyspaces** の場合: `DB_CASSANDRA_USERNAME` と `DB_CASSANDRA_PASSWORD` 環境変数に、Keyspaces のユーザー名とパスワードを設定します。これらは、Cassandra Query Language (CQL) シェル経由で Keyspaces にアクセスする際に使用するものと同じサービス固有の認証情報です。

- **Apache Cassandra** の場合: `DB_CASSANDRA_USERNAME` と `DB_CASSANDRA_PASSWORD` 環境変数に、Cassandra のユーザー名とパスワードを設定します。

### Amazon Keyspaces 用の Starfield デジタル証明書 {#starfield-digital-certificate-for-amazon-keyspaces}

Amazon Keyspaces に接続する前に、Amazon Keyspaces が TLS 接続に使用する Starfield デジタル証明書をダウンロードしてインストールする必要があります。

1. Starfield デジタル証明書をダウンロードします。
   ```bash
   curl -O https://certs.secureserver.net/repository/sf-class2-root.crt
   ```

2. 証明書を正しい場所に配置します。
   ```bash
   mkdir -p ~/.keyspaces-mcp/certs
   cp sf-class2-root.crt ~/.keyspaces-mcp/certs/
   ```

## MCP サーバーの実行 {#running-the-mcp-server}

インストール後、サーバーを直接実行できます。

```bash
awslabs.amazon-keyspaces-mcp-server
```

## Kiro で MCP サーバーを使用するための設定 {#configuring-kiro-to-use-the-mcp-server}

Amazon Keyspaces MCP サーバーを Kiro で使用するには、Kiro の設定ファイルで構成する必要があります。

### Kiro 向けの設定 {#configuration-for-kiro}

詳細については、[Kiro IDE のドキュメント](https://kiro.dev/docs/mcp/configuration/) または [Kiro CLI のドキュメント](https://kiro.dev/docs/cli/mcp/configuration/) を参照してください。

グローバル設定の場合は `~/.kiro/settings/mcp.json` を編集します。プロジェクト固有の設定の場合は、プロジェクトディレクトリ内の `.kiro/settings/mcp.json` を編集します。

```json
{
  "mcpServers": {
    "keyspaces-mcp": {
      "command": "awslabs.amazon-keyspaces-mcp-server",
      "args": [],
      "env": {}
    }
  }
}
```

### Windows でのインストール {#windows-installation}

Windows ユーザーの場合、MCP サーバーの設定形式は少し異なります。MCP 設定ファイル（例: `~/.kiro/settings/mcp.json`）を以下の形式で編集します。

```json
{
  "mcpServers": {
    "keyspaces-mcp": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.amazon-keyspaces-mcp-server@latest",
        "awslabs.amazon-keyspaces-mcp-server.exe"
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

ファイルがまだ存在しない場合や `mcpServers` セクションがない場合は、上記の構造で作成してください。

これで Kiro を使用する際、自動的に Keyspaces MCP サーバーに接続されるようになります。

## 利用可能なツール {#available-tools}

Amazon Keyspaces MCP サーバーは、AI アシスタントが使用できる以下のツールを提供します。

- `listKeyspaces`: データベース内のすべてのキースペースを一覧表示します
- `listTables`: 指定したキースペース内のすべてのテーブルを一覧表示します
- `describeKeyspace`: キースペースに関する詳細情報を取得します
- `describeTable`: テーブルに関する詳細情報を取得します
- `executeQuery`: データベースに対して読み取り専用の SELECT クエリを実行します
- `analyzeQueryPerformance`: CQL クエリのパフォーマンス特性を分析します

## セキュリティに関する考慮事項 {#security-considerations}

- Amazon Keyspaces を使用する場合は、IAM ポリシーが最小権限の原則に従っていることを確認してください。この MCP サーバーは Keyspaces のデータやリソースを変更することはありませんが、エージェントがユーザーに代わって（例えば）変更を伴う操作を含む AWS SDK 操作を呼び出そうとする試みを防ぐことはできません。
- この MCP サーバーは、データを保護するために読み取り専用の SELECT クエリのみを許可します。
- クエリは、潜在的に有害な操作を防ぐために検証されます。

## トラブルシューティング {#troubleshooting}

### 接続の問題 {#connection-issues}

- ホームディレクトリ内の `.keyspaces-mcp/env` ファイルにあるデータベース接続設定を確認します。
- ログインしているユーザーが、このサーバーが実行する操作に必要な権限を持っていることを確認します。
- データベースがネットワークからアクセス可能であることを確認します。
- Amazon Keyspaces の場合、Starfield 証明書が `.keyspaces-mcp/certs` ディレクトリに正しくインストールされていることを確認します。
- SSL/TLS エラーが発生する場合は、証明書のパスが正しく、証明書が有効であることを確認します。

### Python バージョンの互換性 {#python-version-compatibility}

- MCP サーバーは Python 3.10 または 3.11 で最適に動作します。
- Python 3.12 以降では、Cassandra ドライバーが依存している asyncore モジュールが削除されているため、問題が発生する可能性があります。

### Cassandra ドライバーの問題 {#cassandra-driver-issues}

Cassandra ドライバーで問題が発生した場合:

1. Cassandra ドライバーに必要な C 依存関係がインストールされていることを確認します。
2. 次のコマンドでドライバーをインストールしてみてください: `pip install cassandra-driver --no-binary :all:`

## ライセンス {#license}

このプロジェクトは Apache License 2.0 の下でライセンスされています。詳細については LICENSE ファイルを参照してください。
