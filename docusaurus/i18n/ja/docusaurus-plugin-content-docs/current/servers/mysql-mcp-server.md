---
title: AWS Labs MySQL MCP サーバー
---

Aurora MySQL 向けの AWS Labs Model Context Protocol (MCP) サーバーです。

## 機能 {#features}

### 自然言語から MySQL SQL クエリへの変換 {#natural-language-to-mysql-sql-query}

人間が読める形式の質問やコマンドを、構造化された MySQL 互換の SQL クエリに変換し、設定された Aurora MySQL データベースに対して実行します。

## 前提条件 {#prerequisites}

1. [Astral](https://docs.astral.sh/uv/getting-started/installation/) または [GitHub README](https://github.com/astral-sh/uv#installation) から `uv` をインストールします
2. `uv python install 3.10` を使用して Python をインストールします
3. この MCP サーバーは、LLM クライアントと同じホスト上でのみローカルに実行できます。
4. AWS サービスへのアクセス権を持つ AWS 認証情報を設定します
   - 適切な権限を持つ AWS アカウントが必要です
   - `aws configure` または環境変数で AWS 認証情報を設定します

## インストール {#installation}

MCP クライアントの設定で MCP サーバーを構成します(例:Amazon Q Developer CLI の場合は `~/.aws/amazonq/mcp.json` を編集します):

```json
{
  "mcpServers": {
    "awslabs.mysql-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.mysql-mcp-server@latest",
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

### Windows へのインストール {#windows-installation}

Windows ユーザーの場合、MCP サーバーの設定形式が少し異なります:

```json
{
  "mcpServers": {
    "awslabs.mysql-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.mysql-mcp-server@latest",
        "awslabs.mysql-mcp-server.exe"
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

注意:上記の MCP 設定例には、書き込みクエリを有効にする方法を示すために --allow_write_query が含まれています。書き込みクエリを無効にしたい場合は、--allow_write_query オプションを削除してください。

## データベースクラスター作成のサポート {#support-for-database-cluster-creation}

次の LLM プロンプトを使用して、新しい Aurora MySQL クラスターを作成できます:

> Create an Aurora MySQL cluster named 'mycluster' in us-west-2 region

---

## 接続方法 {#connection-methods}

この MCP サーバーは、LLM プロンプトを介してさまざまな接続方法を使用し、複数のデータベースエンドポイントへの接続をサポートします。

### データベースタイプ {#database-types}

これらのエンジン値は AWS RDS API のエンジン文字列と一致しているため、変換せずにそのまま `aws rds` の呼び出しに渡すことができます:

- **aurora-mysql**: Amazon Aurora MySQL
- **mysql**: Amazon RDS for MySQL
- **mariadb**: Amazon RDS for MariaDB

セルフホストの MySQL/MariaDB エンドポイントには `database_type` は不要です。エンドポイント、ポート、認証情報を使用して `mysqlwire` で直接接続してください。

### プロンプトの例 {#example-prompts}

**RDS Data API を使用した接続:**
> Connect to database named mydb in Aurora MySQL cluster 'my-cluster' with database_type as aurora-mysql, using rdsapi as connection method in us-west-2 region

**mysqlwire を使用した接続 (Aurora MySQL):**
> Connect to database named mydb with database endpoint as my-amy-instance-1.ctgfg6yyo9df.us-west-2.rds.amazonaws.com with database_type as aurora-mysql, using mysqlwire as connection method in us-west-2 region

**mysqlwire を使用した接続 (RDS MySQL):**
> Connect to database named mydb with database endpoint as test-rds-instance-1.ctgfg6yyo9df.us-west-2.rds.amazonaws.com with database_type as mysql, using mysqlwire as connection method in us-west-2 region

**mysqlwire を使用した接続 (RDS MariaDB):**
> Connect to database named mydb with database endpoint as test-mariadb-instance-1.ctgfg6yyo9df.us-west-2.rds.amazonaws.com with database_type as mariadb, using mysqlwire as connection method in us-west-2 region

---

### サポートされている接続方法 {#supported-connection-methods}

| 方法 | 説明 | aurora-mysql | mysql | mariadb |
|--------|-------------|:-:|:-:|:-:|
| `rdsapi` | RDS Data API を使用して Aurora MySQL に接続します。クラスターで Data API が有効になっている必要があります。 | ✓ | ✗ | ✗ |
| `mysqlwire` | MySQL ワイヤプロトコルを使用して直接接続します。VPC 接続が必要です。 | ✓ | ✓ | ✓ |
| `mysqlwire_iam` | IAM 認証を使用したワイヤプロトコルです。クラスターで IAM 認証が有効になっている必要があります。 | ✓ | ✓ | ✗ |

### 接続方法ごとの前提条件 {#prerequisites-by-connection-method}

#### mysqlwire / mysqlwire_iam {#mysqlwire--mysqlwire_iam}
- VPC セキュリティグループが、MCP サーバーからデータベースへのインバウンド接続を許可している必要があります
- `mysqlwire_iam` の場合:Aurora MySQL クラスターで IAM 認証が有効になっている必要があります

#### rdsapi {#rdsapi}
- Aurora MySQL クラスターで RDS Data API が有効になっている必要があります
- Data API へのアクセスに適切な IAM 権限が必要です

### AWS 認証 {#aws-authentication}

MCP サーバーは、AWS_PROFILE 環境変数で指定された AWS プロファイルを使用します。指定されていない場合は、AWS 設定ファイルの「default」プロファイルがデフォルトで使用されます。

```json
"env": {
  "AWS_PROFILE": "your-aws-profile"
}
```

AWS プロファイルに、RDS Data API と AWS Secrets Manager のシークレットへのアクセス権限があることを確認してください。MCP サーバーは、指定されたプロファイルを使用して boto3 セッションを作成し、AWS サービスで認証を行います。AWS IAM 認証情報はローカルマシン上に保持され、AWS サービスへのアクセスにのみ厳密に使用されます。

## セキュリティモデル {#security-model}

> **本サーバーの読み取り専用モードは、ベストエフォートの SQL テキストによる安全対策であり、セキュリティ境界ではありません。**

MCP サーバーを `--allow_write_query` なしで実行すると、SQL 文字列を検査して変更系キーワード(`INSERT`、`UPDATE`、`DELETE`、`DROP`、`SET`、`CALL`、`PREPARE`、`EXECUTE`、`HANDLER`、`LOCK`、`FLUSH`、`RESET`、`KILL`、`INSTALL`、`UNINSTALL` など)を検出し、データベースに到達する前に一致したものを拒否します。このガードは多層防御の一部であり、保証ではありません。SQL の文法は進化し、正規表現にはエッジケースがあり、プロンプトインジェクションを受けた LLM は創造的な攻撃者となります。

**実際のセキュリティ境界は、接続に使用するデータベースロールです。** Postgres、MSSQL、Oracle の姉妹サーバーもすべて同じ注意事項を掲げており、このセクションは MySQL パッケージをその文言に合わせたものです。

### 推奨設定 {#recommended-configuration}

ワークロードが実際に必要とする権限のみを持つ、最小権限の MySQL ユーザーで接続してください。読み取り専用のワークフローの場合は、データベースレベルで `SELECT`(および必要に応じて特定のプロシージャに対する `EXECUTE`)を付与します:

```sql
-- Aurora MySQL / RDS MySQL / RDS MariaDB
CREATE USER 'mcp_readonly'@'%' IDENTIFIED BY '...';
GRANT SELECT ON your_database.* TO 'mcp_readonly'@'%';
-- If the workflow legitimately needs specific stored procedures:
GRANT EXECUTE ON PROCEDURE your_database.some_safe_proc TO 'mcp_readonly'@'%';
FLUSH PRIVILEGES;
```

または、IAM 認証の場合は、専用の読み取り専用ユーザーに対してのみ `rds-db:connect` を付与するポリシーをアタッチします。

最小権限のロールを設定しておけば、正規表現が見逃す可能性のある変更系ステートメントも、`ERROR 1142 (42000): … command denied to user` としてデータベース側で失敗します。サーバーの正規表現は、MCP レイヤーでの迅速で分かりやすい拒否として機能し、データベースロールが恒久的な保証となります。

### サーバー側の正規表現が検出できるもの・できないもの {#what-the-server-side-regex-does-and-does-not-catch}

| 検出できるもの | 検出できないもの |
|---------|----------------|
| 単一の変更系ステートメント(`INSERT`、`UPDATE`、`DELETE`、DDL、GRANT/REVOKE など) | 本体が `@user_variable` 内にある `PREPARE` 済みステートメントの `EXECUTE` 内の変更系ロジック(防御策:`PREPARE`、`EXECUTE`、`DEALLOCATE` 自体がブロックされます) |
| スタッククエリ(`SELECT 1; INSERT …`、`SELECT 1; COMMIT; INSERT …`) | 本サーバーが認識していないストアドプロシージャ内の変更系ロジック(防御策:`CALL` がブロックされます) |
| 読み取り専用モードと書き込みモードの**両方**における、整合性制御用セッション変数の切り替え(`SET sql_log_bin = 0`、`SET foreign_key_checks = 0`、`SET unique_checks = 0`) | 引用符付き識別子による変数名の難読化 |
| MySQL の条件付きコメントペイロード(`/*!50000 INSERT … */`) | より高い権限を持つオペレーターによってすでにインストールされているトロイの木馬化された UDF |
| 危険な変数がどの位置にあっても検出する複数変数の `SET`(`SET @x = 1, sql_log_bin = 0`) | 将来の MySQL リリースで導入される新しい変更系の動詞(拒否リストに追加されるまで) |

判断に迷う場合は、データベースロールに頼ってください。

## 開発環境のセットアップ {#development-setup}

このパッケージは、IAM 認証接続(`mysqlwire_iam`)が最初から厳密な TLS 検証を実行できるよう、Amazon RDS グローバル CA バンドルを wheel 内に同梱しています。PEM 自体はソース管理にチェックインされておらず、ビルド時に `hatch_build.py` によって取得されます。

### バンドルをビルド時に取得する理由 {#why-the-bundle-is-fetched-at-build-time}

AWS は RDS グローバル CA バンドルを予告なくローテーションします。PEM をソース管理の外に置くことで、コードレビューにバイナリブロブをコミットすることを避け、ビルドフックがビルドのたびに `https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem` から最新のバンドルを自動的に取得できるようにしています。同梱された CA に対する実行時の TLS 検証では、証明書チェーンと FQDN のマッチングが通常どおり処理されます。

### ビルドフックの実行 {#running-the-build-hook}

`uv build`、`uv sync`、`pip wheel`、およびソースからの `pip install` は、いずれも自動的にこのフックを呼び出します。フックは冪等です。PEM がすでにディスク上に存在する場合、取得はスキップされます。

フックを単独で実行するには(たとえば、まだビルドされていない editable チェックアウトに PEM を配置する場合):

```bash
python hatch_build.py
```

これにより、バンドルが
`awslabs/mysql_mcp_server/connection/rds_global_bundle.pem` に書き込まれます。

### オフラインでのビルド {#building-offline}

ビルドマシンが `truststore.pki.rds.amazonaws.com` に到達できない場合、フックは `curl` によるリカバリコマンドを含むエラーで失敗します。接続可能なホストでそのコマンドを一度実行してからビルドを再実行してください。フックは配置されたファイルを使用します。

### オプション:実行時に CA バンドルを上書きする {#optional-override-the-ca-bundle-at-runtime}

パッケージに同梱されているものとは別の PEM を使用するには、サーバーに `--ca_bundle <path>` を渡します。独自のトラストストアを維持している企業や、新しい wheel が公開されるより早く AWS が CA をローテーションした場合に便利です:

```bash
uvx awslabs.mysql-mcp-server@latest --ca_bundle /path/to/custom.pem
```
