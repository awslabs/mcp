---
title: "AWS Labs Microsoft SQL Server 用 MCP サーバー"
---

AWS RDS 上の Microsoft SQL Server 向けの AWS Labs Model Context Protocol (MCP) サーバーです。

## 機能 {#features}

- パスワード認証（AWS Secrets Manager）による SQL Server への直接接続
- SQL インジェクション検出と変更系キーワードのブロック
- 読み取り専用モードの強制
- 認証情報の自動更新を備えたコネクションプール管理

## ツール {#tools}

- `run_query` — SQL Server に対して SQL クエリを実行します
- `get_table_schema` — INFORMATION_SCHEMA からテーブルのカラム情報を取得します
- `connect_to_database` — SQL Server RDS インスタンスに接続します
- `is_database_connected` — 接続が存在するかどうかを確認します
- `get_database_connection_info` — キャッシュされたすべての接続を一覧表示します

## 使い方 {#usage}

```bash
awslabs.mssql-mcp-server \
  --connection_method MSSQL_PASSWORD \
  --instance_identifier my-sqlserver-instance \
  --db_endpoint my-instance.xxxx.rds.amazonaws.com \
  --region us-east-1 \
  --database master \
  --port 1433
```

## 接続方式 {#connection-methods}

- `MSSQL_PASSWORD` — AWS Secrets Manager の認証情報を使用します（デフォルトでは MasterUserSecret）

### カスタム Secrets Manager シークレットの使用 {#using-a-custom-secrets-manager-secret}

デフォルトでは、サーバーは `describe_db_instances` を呼び出して RDS インスタンスの **MasterUserSecret** を検出します。別のデータベースユーザーとして接続するには、AWS Secrets Manager に独自のシークレットを作成し、その ARN を `--secret_arn` で渡します。

```bash
awslabs.mssql-mcp-server \
  --connection_method MSSQL_PASSWORD \
  --instance_identifier my-sqlserver-instance \
  --db_endpoint my-instance.xxxx.rds.amazonaws.com \
  --region us-east-1 \
  --database master \
  --secret_arn arn:aws:secretsmanager:us-east-1:123456789012:secret:my-readonly-user-AbCdEf
```

シークレットは、以下のキーを持つ JSON オブジェクトである必要があります（大文字・小文字のバリエーションも受け付けられます）。

| キー | 受け付けられるバリエーション |
|-----|-------------------|
| username | `username`、`user`、`Username` |
| password | `password`、`Password` |

シークレット値の例:

```json
{
  "username": "mcp_readonly",
  "password": "UseAStrongPassword"
}
```

`--secret_arn` フラグは、`connect_to_database` MCP ツールの `secret_arn` パラメータを介して実行時に渡すこともでき、サーバーを再起動せずに LLM が認証情報を切り替えられるようになります。

## TLS / SSL {#tls--ssl}

デフォルトでは、サーバーは `--ssl_encryption require` で接続します。これにより接続が暗号化され、サーバー証明書がシステムの CA ストアに対して検証されます。

RDS SQL Server の証明書は **Amazon RDS CA** によって署名されていますが、この CA はデフォルトのシステム信頼ストアには含まれていません。初回接続時に証明書検証エラーが表示された場合は、Amazon RDS CA バンドルをインストールしてください。

**Windows**（PowerShell、管理者として実行）

```powershell
# Download the global RDS CA bundle
Invoke-WebRequest -Uri https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem `
  -OutFile global-bundle.pem

# Import all certificates in the bundle into the Trusted Root store
certutil -addstore "Root" global-bundle.pem
```

**macOS**

```bash
# Download the global RDS CA bundle
curl -O https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem

# Import into the macOS system keychain (requires sudo)
sudo security add-trusted-cert -d -r trustRoot \
  -k /Library/Keychains/System.keychain global-bundle.pem
```

**Linux (Debian/Ubuntu)**

```bash
curl -O https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem
sudo cp global-bundle.pem /usr/local/share/ca-certificates/amazon-rds-ca.crt
sudo update-ca-certificates
```

**Linux (RHEL/Amazon Linux)**

```bash
curl -O https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem
sudo cp global-bundle.pem /etc/pki/ca-trust/source/anchors/amazon-rds-ca.pem
sudo update-ca-trust
```

CA 証明書をインストールした後、MCP サーバーを再起動してください。

### SSH トンネル {#ssh-tunnel}

SSH トンネル経由で接続する場合、トランスポートはすでにエンドツーエンドで暗号化されています。証明書検証の失敗を回避するために、pymssql レイヤーで TLS を無効にできます。

```bash
awslabs.mssql-mcp-server \
  --connection_method MSSQL_PASSWORD \
  --instance_identifier my-sqlserver-instance \
  --db_endpoint my-instance.xxxx.rds.amazonaws.com \
  --region us-east-1 \
  --ssl_encryption off
```

## 読み取り専用モード {#read-only-mode}

デフォルトでは、サーバーは**読み取り専用モード**で動作します。クエリがデータベースに到達する前に、複数の保護レイヤーが適用されます。

1. **変更系キーワードのブロック** — DML/DDL キーワード（INSERT、UPDATE、DELETE、DROP、CREATE、ALTER、MERGE、TRUNCATE、EXEC、GRANT など）を含むクエリを拒否します
2. **SQL インジェクションパターンの検出** — スタッククエリ、UNION SELECT、恒真式、WAITFOR DELAY、およびシステム / 拡張 / RDS ストアドプロシージャ（`sp_*`、`xp_*`、`rds_*`）の呼び出しなど、一般的なインジェクションベクトルをブロックします。
3. **トランザクション分離** — `READ COMMITTED` 分離レベルを設定します。
4. **自動コミットの無効化と強制ロールバック** — 読み取り専用モードでは自動コミットがオフになり、すべてのクエリの後にロールバックが実行されるため、キーワードフィルターをすり抜けた変更操作がコミットされることはありません。

### アプリケーションレベルの読み取り専用モードの制限事項 {#limitations-of-application-level-read-only-mode}

キーワードチェックとパターンチェックは**ベストエフォートの保護策**であり、セキュリティ境界ではありません。次の理由から、変更操作がデータベースに一切到達しないことを保証することはできません。

- 内部で書き込みを行うストアドプロシージャが、ブロック対象のキーワードを含まない SELECT を介して呼び出される可能性があります（例:
  `SELECT dbo.my_func_that_writes()`）。
- 将来の T-SQL 構文やエッジケースのエンコーディングが、正規表現ベースの検出器をバイパスする可能性があります。

**真の読み取り専用の強制には、読み取り権限のみを持つデータベースユーザーを使用してください。** 以下の [推奨: データベースレベルの読み取り専用ユーザー](#recommended-database-level-read-only-user) を参照してください。

### 書き込みモード {#write-mode}

書き込みクエリを許可するには、`--allow_write_query` を渡します。

```bash
awslabs.mssql-mcp-server \
  --connection_method MSSQL_PASSWORD \
  --instance_identifier my-sqlserver-instance \
  --db_endpoint my-instance.xxxx.rds.amazonaws.com \
  --region us-east-1 \
  --database master \
  --allow_write_query
```

## 推奨: データベースレベルの読み取り専用ユーザー {#recommended-database-level-read-only-user}

本番環境での利用には、読み取り権限のみを持つ専用の SQL Server ログインを作成し、その認証情報を Secrets Manager に保存してください。これにより、アプリケーションレイヤーではバイパスできない強固なセキュリティ境界が提供されます。

### 1. SQL Server でログインとユーザーを作成する {#1-create-the-login-and-user-in-sql-server}

マスターユーザーとして RDS インスタンスに接続し、次を実行します。

```sql
-- Create a server-level login
CREATE LOGIN mcp_readonly WITH PASSWORD = 'UseAStrongPassword';  -- pragma: allowlist secret

-- Switch to the target database
USE my_database;

-- Create a database user mapped to the login
CREATE USER mcp_readonly FOR LOGIN mcp_readonly;

-- Grant read-only access
ALTER ROLE db_datareader ADD MEMBER mcp_readonly;

-- (Optional) Allow the user to view definitions (table schemas, view text, etc.)
GRANT VIEW DEFINITION TO mcp_readonly;
```

このユーザーは SELECT クエリの実行と `INFORMATION_SCHEMA` の読み取りができますが、INSERT、UPDATE、DELETE、CREATE、DROP、およびストアドプロシージャの実行はできません。

### 2. 認証情報を Secrets Manager に保存する {#2-store-the-credentials-in-secrets-manager}

```bash
aws secretsmanager create-secret \
  --name mcp/mssql/readonly \
  --description "Read-only SQL Server credentials for MCP server" \
  --secret-string '{"username":"mcp_readonly","password":"UseAStrongPassword"}'  # pragma: allowlist secret
```

出力に含まれる ARN を控えておいてください。

### 3. カスタムシークレットで MCP サーバーを起動する {#3-start-the-mcp-server-with-the-custom-secret}

```bash
awslabs.mssql-mcp-server \
  --connection_method MSSQL_PASSWORD \
  --instance_identifier my-sqlserver-instance \
  --db_endpoint my-instance.xxxx.rds.amazonaws.com \
  --region us-east-1 \
  --database my_database \
  --secret_arn arn:aws:secretsmanager:us-east-1:123456789012:secret:mcp/mssql/readonly-AbCdEf
```

この構成により、**多層防御**が実現します。アプリケーションレベルのキーワードブロッカーがミスを早期に検出して明確なエラーメッセージを提供し、データベースレベルの権限が、クエリが検出器をすり抜けた場合でもあらゆる変更操作を防ぎます。

## 注意事項 {#notes}

- デフォルトポート: 1433
- デフォルトの TLS モード: `require`（サーバー証明書を検証）
- コネクションプールは 30 分後に期限切れとなり、自動的に更新されます
