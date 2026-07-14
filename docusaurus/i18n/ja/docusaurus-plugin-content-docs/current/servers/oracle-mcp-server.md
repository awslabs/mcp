---
title: AWS Labs Oracle Database 用 MCP サーバー
---

AWS RDS 上の Oracle Database 向けの AWS Labs Model Context Protocol (MCP) サーバーです。

## 機能 {#features}

- パスワード認証（AWS Secrets Manager）による Oracle への直接接続
- SQL インジェクション検出と Oracle 固有の変更系キーワードのブロック
- `SET TRANSACTION READ ONLY` を使用した読み取り専用トランザクションの強制
- python-oracledb の thin モードを使用した接続プール管理（Oracle Instant Client は不要）
- service_name と SID の両方の接続スタイルをサポート
- デフォルトで証明書検証付きの TLS 暗号化（`--ssl_encryption require`）

## ツール {#tools}

- `run_query` — Oracle Database に対して SQL クエリを実行
- `get_table_schema` — ALL_TAB_COLUMNS からテーブルの列情報を取得
- `connect_to_database` — Oracle RDS インスタンスに接続
- `is_database_connected` — 接続が存在するかを確認
- `get_database_connection_info` — キャッシュされたすべての接続を一覧表示

## 使い方 {#usage}

```bash
awslabs.oracle-mcp-server \
  --connection_method ORACLE_PASSWORD \
  --instance_identifier my-oracle-instance \
  --db_endpoint my-instance.xxxx.rds.amazonaws.com \
  --region us-east-1 \
  --database ORCL \
  --service_name ORCL
```

## 接続方式 {#connection-methods}

- `ORACLE_PASSWORD` — AWS Secrets Manager の認証情報を使用（デフォルトでは MasterUserSecret）

### カスタムの Secrets Manager シークレットの使用 {#using-a-custom-secrets-manager-secret}

デフォルトでは、サーバーは `describe_db_instances` を呼び出して RDS インスタンスの
**MasterUserSecret** を検出します。別のデータベースユーザーとして接続するには、
AWS Secrets Manager で独自のシークレットを作成し、その ARN を `--secret_arn` で渡します。

```bash
awslabs.oracle-mcp-server \
  --connection_method ORACLE_PASSWORD \
  --instance_identifier my-oracle-instance \
  --db_endpoint my-instance.xxxx.rds.amazonaws.com \
  --region us-east-1 \
  --database ORCL \
  --service_name ORCL \
  --secret_arn arn:aws:secretsmanager:us-east-1:123456789012:secret:my-readonly-user-AbCdEf
```

シークレットは以下のキーを持つ JSON オブジェクトである必要があります（大文字小文字の違いは許容されます）。

| キー | 許容されるバリエーション |
|-----|-------------------|
| username | `username`、`user`、`Username` |
| password | `password`、`Password` |

シークレット値の例:

```json
{
  "username": "mcp_readonly",
  "password": "UseAStrongPassword"  # pragma: allowlist secret
}
```

## TLS / SSL {#tls--ssl}

デフォルトでは、サーバーは `--ssl_encryption require` で接続します。これは Oracle TCPS を
使用して接続を暗号化し、システムの CA ストアに対してサーバー証明書を検証します。

RDS Oracle の証明書は **Amazon RDS CA** によって署名されており、これはデフォルトの
システム信頼ストアには含まれていません。初回接続時に証明書検証エラーが表示された場合は、
Amazon RDS CA バンドルをインストールしてください。

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

### ポートフォワーディング / SSH トンネル {#port-forwarding--ssh-tunnel}

Oracle TCPS (TLS) はデフォルトでポート **2484** をリッスンします。暗号化されていない標準の
Oracle TCP はポート **1521** を使用します。TLS で SSH トンネルを使用する場合は、
（1521 ではなく）ポート 2484 をトンネルします。

```bash
ssh -N \
  -L 2484:my-instance.xxxx.rds.amazonaws.com:2484 \
  ec2-user@<bastion-ip>
```

> **セキュリティグループの要件:** EC2 踏み台サーバーのセキュリティグループが、Oracle RDS の
> セキュリティグループでポート 2484 のインバウンドソースとして許可されている必要があります。

その後、`--ssl_encryption noverify` で接続すると、TLS 暗号化を維持しつつ証明書と
ホスト名の検証をスキップできます（証明書は `localhost` と一致しないためです）。

```bash
awslabs.oracle-mcp-server \
  --connection_method ORACLE_PASSWORD \
  --instance_identifier my-oracle-instance \
  --db_endpoint localhost \
  --port 2484 \
  --region us-east-1 \
  --database ORCL \
  --service_name ORCL \
  --ssl_encryption noverify
```

TLS を完全に無効にするには（例: ポート 1521 をトンネルし、SSH 接続が暗号化を提供する場合）:

```bash
awslabs.oracle-mcp-server \
  --connection_method ORACLE_PASSWORD \
  --instance_identifier my-oracle-instance \
  --db_endpoint localhost \
  --region us-east-1 \
  --database ORCL \
  --service_name ORCL \
  --ssl_encryption off
```

### `--ssl_encryption` のオプション {#--ssl_encryption-options}

| 値 | 動作 |
|-------|----------|
| `require` | *（デフォルト）* ポート 2484 での TCPS。接続を暗号化し、システムの CA ストアに対してサーバー証明書を検証します。 |
| `noverify` | ポート 2484 での TCPS。接続を暗号化しますが、証明書とホスト名の検証をスキップします。SSH トンネル経由で接続する場合や、RDS CA がローカルにインストールされていない場合に使用します。 |
| `off` | ポート 1521 でのプレーン TCP。暗号化なし。トランスポートが既に保護されている場合（例: SSH トンネル）や、隔離されたテスト環境でのみ使用してください。 |

## 読み取り専用モード {#read-only-mode}

デフォルトでは、サーバーは**読み取り専用モード**で動作します。クエリがデータベースに
到達する前に、複数の保護レイヤーが適用されます。

1. **変更系キーワードのブロック** — DML/DDL キーワード（INSERT、UPDATE、DELETE、DROP、
   CREATE、ALTER、TRUNCATE、GRANT、REVOKE、AUDIT、FLASHBACK、LOCK TABLE、BEGIN、
   DECLARE など）を含むクエリを拒否します
2. **SQL インジェクションパターンの検出** — EXECUTE IMMEDIATE、ALTER SYSTEM/SESSION、
   DBMS_* / UTL_* パッケージ、XMLTYPE XXE、代替引用符、SYS 内部テーブル、v$/gv$/dba_ ビュー、
   HTTPURITYPE/URITYPE SSRF、CTXSYS、CONNECT BY トートロジーなど、Oracle 固有の
   インジェクションベクトルをブロックします
3. **トランザクション制御のブロック** — 読み取り専用モードでは COMMIT、ROLLBACK、SAVEPOINT、
   SET TRANSACTION ステートメントを拒否します
4. **SET TRANSACTION READ ONLY** — すべてのクエリは読み取り専用トランザクション内で
   実行されるため、キーワードフィルターをすり抜けた変更操作もデータベース自体によって
   拒否されます

### アプリケーションレベルの読み取り専用モードの制限事項 {#limitations-of-application-level-read-only-mode}

キーワードとパターンのチェックは**ベストエフォートの安全策**であり、セキュリティ境界では
ありません。以下の理由により、変更操作がデータベースに一切到達しないことを保証することは
できません。

- 内部で書き込みを行う PL/SQL 関数が、ブロック対象のキーワードを含まない SELECT を介して
  呼び出される可能性があります（例:
  `SELECT my_func_that_writes() FROM DUAL`）。
- 将来の Oracle SQL 構文やエッジケースのエンコーディングが、正規表現ベースの検出器を
  バイパスする可能性があります。

**真の読み取り専用の強制には、読み取り権限のみを持つデータベースユーザーを使用してください。**
以下の[推奨: データベースレベルの読み取り専用ユーザー](#recommended-database-level-read-only-user)を参照してください。

### 書き込みモード {#write-mode}

書き込みクエリを許可するには、`--allow_write_query` を渡します。

```bash
awslabs.oracle-mcp-server \
  --connection_method ORACLE_PASSWORD \
  --instance_identifier my-oracle-instance \
  --db_endpoint my-instance.xxxx.rds.amazonaws.com \
  --region us-east-1 \
  --database ORCL \
  --service_name ORCL \
  --allow_write_query
```

## 推奨: データベースレベルの読み取り専用ユーザー {#recommended-database-level-read-only-user}

本番環境での使用には、読み取り権限のみを持つ専用の Oracle ユーザーを作成し、その認証情報を
Secrets Manager に保存してください。これにより、アプリケーションレイヤーではバイパスできない
強固なセキュリティ境界が提供されます。

### 1. Oracle で読み取り専用ユーザーを作成する {#1-create-the-read-only-user-in-oracle}

マスターユーザーとして RDS インスタンスに接続し、以下を実行します。

```sql
-- Create a read-only user
CREATE USER mcp_readonly IDENTIFIED BY "UseAStrongPassword";  -- pragma: allowlist secret

-- Allow the user to connect
GRANT CREATE SESSION TO mcp_readonly;

-- Grant read access to specific schemas (repeat for each schema)
GRANT SELECT ANY TABLE TO mcp_readonly;

-- (Optional) Restrict to specific tables instead of SELECT ANY TABLE
-- GRANT SELECT ON hr.employees TO mcp_readonly;
-- GRANT SELECT ON hr.departments TO mcp_readonly;

-- (Optional) Allow the user to view table definitions in ALL_TAB_COLUMNS
-- This is granted implicitly when SELECT access exists on the tables.
```

このユーザーは SELECT クエリの実行と `ALL_TAB_COLUMNS` の読み取りができますが、INSERT、
UPDATE、DELETE、CREATE、DROP、PL/SQL プロシージャの実行はできません。

### 2. 認証情報を Secrets Manager に保存する {#2-store-the-credentials-in-secrets-manager}

```bash
aws secretsmanager create-secret \
  --name mcp/oracle/readonly \
  --description "Read-only Oracle credentials for MCP server" \
  --secret-string '{"username":"mcp_readonly","password":"UseAStrongPassword"}'  # pragma: allowlist secret
```

出力に含まれる ARN を控えておきます。

### 3. カスタムシークレットで MCP サーバーを起動する {#3-start-the-mcp-server-with-the-custom-secret}

```bash
awslabs.oracle-mcp-server \
  --connection_method ORACLE_PASSWORD \
  --instance_identifier my-oracle-instance \
  --db_endpoint my-instance.xxxx.rds.amazonaws.com \
  --region us-east-1 \
  --database ORCL \
  --service_name ORCL \
  --secret_arn arn:aws:secretsmanager:us-east-1:123456789012:secret:mcp/oracle/readonly-AbCdEf
```

この構成により**多層防御**が実現します。アプリケーションレベルのキーワードブロッカーが
ミスを早期に検出して明確なエラーメッセージを提供し、データベースレベルの権限が、クエリが
検出器をすり抜けた場合でもあらゆる変更操作を防止します。

## 注意事項 {#notes}

- RDS for Oracle は RDS Data API をサポートしていません。直接接続のみがサポートされています。
- python-oracledb の thin モードを使用します — Oracle Instant Client のインストールは不要です。
- `--service_name` または `--sid` のいずれか一方を指定する必要があります（両方は指定できません）。
- Oracle のシステムカタログはテーブル名を大文字で保存します。`get_table_schema` に渡されたテーブル名は自動的に大文字に変換されます。
- デフォルトポート: 1521 (TCP)。Oracle TCPS (TLS) は通常ポート 2484 を使用します — `--ssl_encryption require` または `noverify` で接続する場合は `--port 2484` を渡してください。
- 接続プールは 30 分後に期限切れとなり、自動的に更新されます
