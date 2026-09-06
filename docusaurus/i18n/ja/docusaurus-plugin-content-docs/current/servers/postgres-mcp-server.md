---
title: AWS Labs postgres MCP Server
---

Aurora Postgres 用の AWS Labs Model Context Protocol (MCP) サーバーです。

## 機能 {#features}

### 自然言語から Postgres SQL クエリへの変換 {#natural-language-to-postgres-sql-query}

- 人間が読める質問やコマンドを、構造化された Postgres 互換の SQL クエリに変換し、設定された Aurora Postgres データベースに対して実行します。

## 前提条件 {#prerequisites}

1. [Astral](https://docs.astral.sh/uv/getting-started/installation/) または [GitHub README](https://github.com/astral-sh/uv#installation) から `uv` をインストールします
2. `uv python install 3.10` を使用して Python をインストールします
3. この MCP サーバーは、LLM クライアントと同じホスト上でのみローカルに実行できます。
4. Docker ランタイム
5. AWS サービスへのアクセス権を持つ AWS 認証情報を設定します
   - 適切な権限を持つ AWS アカウントが必要です
   - `aws configure` または環境変数で AWS 認証情報を設定します

## インストール {#installation}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.postgres-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.postgres-mcp-server%40latest%22%2C%22--connection-string%22%2C%22postgresql%3A//%5Busername%5D%3A%5Bpassword%5D%40%5Bhost%5D%3A%5Bport%5D/%5Bdatabase%5D%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.postgres-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMucG9zdGdyZXMtbWNwLXNlcnZlckBsYXRlc3QgLS1jb25uZWN0aW9uLXN0cmluZyBwb3N0Z3Jlc3FsOi8vW3VzZXJuYW1lXTpbcGFzc3dvcmRdQFtob3N0XTpbcG9ydF0vW2RhdGFiYXNlXSIsImVudiI6eyJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdLCJ0cmFuc3BvcnRUeXBlIjoic3RkaW8iLCJhdXRvU3RhcnQiOnRydWV9) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=PostgreSQL%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.postgres-mcp-server%40latest%22%2C%22--connection-string%22%2C%22postgresql%3A%2F%2F%5Busername%5D%3A%5Bpassword%5D%40%5Bhost%5D%3A%5Bport%5D%2F%5Bdatabase%5D%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%2C%22transportType%22%3A%22stdio%22%2C%22autoStart%22%3Atrue%7D) |

MCP クライアントの設定で MCP サーバーを設定します（例：Kiro の場合は `~/.kiro/settings/mcp.json` を編集します）：

```json
{
  "mcpServers": {
    "awslabs.postgres-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.postgres-mcp-server@latest",
        "--allow_write_query"
      ],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Windows でのインストール {#windows-installation}

Windows ユーザーの場合、MCP サーバーの設定形式が少し異なります：

```json
{
  "mcpServers": {
    "awslabs.postgres-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.postgres-mcp-server@latest",
        "awslabs.postgres-mcp-server.exe"
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

### LLM クライアントと同じホスト上で Docker イメージをローカルにビルドしてインストールする {#build-and-install-docker-image-locally-on-the-same-host-of-your-llm-client}

1. 'git clone https://github.com/awslabs/mcp.git' を実行します
2. サブディレクトリ 'src/postgres-mcp-server/' に移動します
3. 'docker build -t awslabs/postgres-mcp-server:latest .' を実行します

### LLM クライアントの設定に以下を追加または更新します： {#add-or-update-your-llm-clients-config-with-following}

#### オプション 1：RDS Data API 接続を使用する（Aurora Postgres 向け） {#option-1-using-rds-data-api-connection-for-aurora-postgres}

```json
{
  "mcpServers": {
    "awslabs.postgres-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e", "AWS_ACCESS_KEY_ID=[your data]",
        "-e", "AWS_SECRET_ACCESS_KEY=[your data]",
        "-e", "AWS_REGION=[your data]",
        "awslabs/postgres-mcp-server:latest",
        "--allow_write_query"
      ]
    }
  }
}
```

注意：この MCP 設定例には、書き込みクエリを有効にする方法を示すために --allow_write_query が含まれています。書き込みクエリを無効にしたい場合は、--allow_write_query オプションを削除してください。

## データベースクラスター作成のサポート {#support-for-database-cluster-creation}

以下の LLM プロンプトを使用して、新しい Aurora PostgreSQL クラスターを作成できます：

> us-west-2 リージョンに 'mycluster' という名前の Aurora PostgreSQL クラスターを作成してください

---

## 接続方法 {#connection-methods}

この MCP サーバーは、LLM プロンプトを介してさまざまな接続方法を使用し、複数のデータベースエンドポイントへの接続をサポートします。

### データベースタイプ {#database-types}
- **APG**: Amazon Aurora PostgreSQL
- **RPG**: Amazon RDS for PostgreSQL

### プロンプトの例 {#example-prompts}

**RDS Data API を使用して接続する：**
> database_type を APG とし、us-west-2 リージョンで rdsapi を接続方法として使用して、Aurora PostgreSQL クラスター 'my-cluster' 内の postgres という名前のデータベースに接続してください

**pgwire を使用して接続する（Aurora PostgreSQL）：**
> database_type を APG とし、us-west-2 リージョンで pgwire を接続方法として使用して、データベースエンドポイント my-apg17-instance-1.ctgfg6yyo9df.us-west-2.rds.amazonaws.com の postgres という名前のデータベースに接続してください

**pgwire を使用して接続する（RDS PostgreSQL）：**
> database_type を RPG とし、us-west-2 リージョンで pgwire を接続方法として使用して、データベースエンドポイント test-apg17-instance-1.ctgfg6yyo9df.us-west-2.rds.amazonaws.com の postgres という名前のデータベースに接続してください

---

### サポートされている接続方法 {#supported-connection-methods}

| 方法 | 説明 | サポートされるデータベースタイプ |
|--------|-------------|--------------------------|
| `pgwire` | PostgreSQL ワイヤープロトコルを使用して PostgreSQL インスタンスに直接接続します。データベースへの直接接続には、適切な VPC セキュリティグループの設定が必要です。 | APG、RPG |
| `pgwire_iam` | `pgwire` と同じですが、IAM 認証を使用します。Aurora PostgreSQL クラスターで IAM 認証が有効になっている必要があります。 | APG のみ |
| `rdsapi` | RDS Data API を使用して Aurora PostgreSQL に接続します。クラスターで RDS Data API が有効になっている必要があります。 | APG のみ |

### 接続方法ごとの前提条件 {#prerequisites-by-connection-method}

#### pgwire / pgwire_iam {#pgwire--pgwire_iam}
- VPC セキュリティグループが、MCP サーバーからデータベースへのインバウンド接続を許可している必要があります
- `pgwire_iam` の場合：Aurora PostgreSQL クラスターで IAM 認証が有効になっている必要があります

#### rdsapi {#rdsapi}
- Aurora PostgreSQL クラスターで RDS Data API が有効になっている必要があります
- Data API へのアクセスに適切な IAM 権限が必要です

### AWS 認証 {#aws-authentication}

MCP サーバーは、データベースクラスターまたはインスタンスのデータを読み取り、クラスターやインスタンスを作成するために AWS 認証情報を必要とします。これらは、Postgres 操作（SELECT、CREATE など）とは別のコントロールプレーン操作です。rdsapi 接続方法を使用する場合、AWS 認証情報には Aurora クラスターに対する rds-data:ExecuteStatement 権限が必要です（https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazonrdsdataapi.html を参照してください）。MCP は、`AWS_PROFILE` 環境変数で指定された AWS プロファイルを使用します。指定されていない場合は、AWS 設定ファイルの "default" プロファイルがデフォルトで使用されます。

```json
"env": {
  "AWS_PROFILE": "your-aws-profile"
}
```

AWS プロファイルに、[RDS data API](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/data-api.html#data-api.access) および AWS Secrets Manager のシークレットにアクセスする権限があることを確認してください。MCP サーバーは、指定されたプロファイルを使用して boto3 セッションを作成し、AWS サービスで認証を行います。AWS IAM 認証情報はローカルマシン上に保持され、AWS サービスへのアクセスにのみ厳密に使用されます。

### Postgres 認証 {#postgres-authentication}

MCP サーバーは、Postgres 認証として IAM とユーザー名/パスワードの方法をサポートしています。認証情報の保存には AWS Secrets Manager を使用し、MCP 設定ファイルで --secretManagerARN を指定する必要があります。


### セキュリティに関する考慮事項 {#security-consideration}

#### `--allow_write_query` の読み取り専用強制はベストエフォートです {#--allow_write_query-read-only-enforcement-is-best-effort}

MCP サーバーを `--allow_write_query` なしで実行すると、データやセッション状態を変更すると思われるクエリは拒否されます。これは、キーワードと関数のブロックリスト（`INSERT`/`UPDATE`/`DROP` などの DML/DDL 動詞、`SET`/`RESET`/`DISCARD`/`LOAD` などのセッション状態ステートメント、匿名コードブロック `DO`、および `pg_terminate_backend`、`pg_sleep`、アドバイザリロック系などの影響の大きい関数）によって実装されています。

**これはベストエフォートの多層防御メカニズムであり、セキュリティ境界ではないものとして扱ってください。** ブロックリストはすべての危険な構文を列挙することはできず、十分に巧妙なクエリ（難読化、引用符付き識別子、新しいサーバー/拡張機能の関数など）はそれをバイパスする可能性があります。これを唯一の制御手段として頼らないでください。

#### ベストプラクティス：最小権限の Postgres ロールで MCP サーバーを実行する {#best-practice-run-the-mcp-server-as-a-minimal-privilege-postgres-role}

最も強力な制御は、実際に必要な権限のみを持つ専用の Postgres ロールを使用して MCP サーバーを接続することです。これにより、どのような SQL が到達しても、データベース自体が境界を強制します。具体的には：

- スーパーユーザー、`rds_superuser`、またはクラスターのマスターユーザーとして接続**しないでください**。
  これらのロールは行レベルセキュリティをバイパスし、認証情報カタログ
  （`pg_authid`、`pg_user_mappings`）を読み取ることができ、他のセッションを終了させることができます。
- 読み取り専用で使用する場合は、エージェントが必要とするスキーマに対して `CONNECT` + `USAGE` + `SELECT` のみを付与し、
  ロールレベルで読み取り専用トランザクションを強制してください。
- 読み取り/書き込みで使用する場合は、必要なスキーマとテーブルに限定して、必要な特定の
  `INSERT`/`UPDATE`/`DELETE` 権限のみを付与してください。

最小権限ロール（データベースによる強制）とブロックリスト（アプリケーションによる強制）を組み合わせることで、多層防御が実現します。クエリがブロックリストをすり抜けたとしても、ロールの権限によって実行できる範囲が制限されます。

以下は読み取り専用ロールの例です：

```sql
-- Create a read-only role for Postgres MCP server
CREATE ROLE postgres_mcp_server_readonly WITH LOGIN PASSWORD 'change-me'
    NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;

-- Allow connection and schema visibility for public schema
-- TODO: add additional schema if required
GRANT CONNECT ON DATABASE mydb TO postgres_mcp_server_readonly;
GRANT USAGE ON SCHEMA public TO postgres_mcp_server_readonly;

-- Read existing tables and sequences for public schema
-- TODO: add additional schema if required
GRANT SELECT ON ALL TABLES IN SCHEMA public TO postgres_mcp_server_readonly;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO postgres_mcp_server_readonly;

-- Read future tables and sequences for public schema
-- TODO: add additional schema if required
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO postgres_mcp_server_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON SEQUENCES TO postgres_mcp_server_readonly;

-- Force read-only transactions
ALTER ROLE postgres_mcp_server_readonly SET default_transaction_read_only = on;
```
