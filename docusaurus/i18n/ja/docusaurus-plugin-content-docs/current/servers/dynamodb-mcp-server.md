---
title: AWS DynamoDB MCPサーバー
---

Amazon DynamoDB 向けの公式開発者体験 MCP サーバーです。このサーバーは、DynamoDB のエキスパートによる設計ガイダンスとデータモデリング支援を提供します。

> [!IMPORTANT]
> 生成 AI は誤りを犯す可能性があります。選択した AI モデルおよびエージェント型コーディングアシスタントが生成したすべての出力を確認することを検討してください。[AWS Responsible AI Policy](https://aws.amazon.com/ai/responsible-ai/policy/) を参照してください。

## 利用可能なツール {#available-tools}

DynamoDB MCP サーバーは、データモデリング、検証、コスト分析、コード生成のための 8 つのツールを提供します。

- `dynamodb_data_modeling` - エンタープライズレベルの設計パターン、コスト最適化戦略、マルチテーブル設計の考え方を含む、DynamoDB データモデリングエキスパートの完全なプロンプトを取得します。要件の収集、アクセスパターンの分析、スキーマ設計をガイドします。

  **呼び出し例:** 「DynamoDB データモデリング MCP サーバーを使って、私の e コマースアプリケーションのデータモデルを設計してください」

- `dynamodb_data_model_validation` - dynamodb_data_model.json を読み込み、DynamoDB Local をセットアップし、テストデータ付きのテーブルを作成し、定義されたすべてのアクセスパターンを実行することで、DynamoDB データモデルを検証します。詳細な検証結果を dynamodb_model_validation.json に保存します。

  **呼び出し例:** 「私の DynamoDB データモデルを検証してください」

- `source_db_analyzer` - 既存のデータベース(MySQL、PostgreSQL、SQL Server、Oracle)を分析してスキーマ構造とアクセスパターンを抽出し、dynamodb_data_modeling で使用するためのタイムスタンプ付き分析ファイルを生成します。MySQL については、RDS Data API ベースのアクセスと接続ベースのアクセスの両方をサポートします。

  **呼び出し例:** 「私の MySQL データベースを分析して、DynamoDB データモデルの設計を手伝ってください」

- `generate_resources` - DynamoDB データモデルの JSON ファイル(dynamodb_data_model.json)からさまざまなリソースを生成します。現在は `cdk` リソースタイプのみがサポートされています。`resource_type` パラメータに `cdk` を渡すと、DynamoDB テーブルをデプロイするための CDK アプリが生成されます。CDK アプリは dynamodb_data_model.json を読み取り、適切な設定でテーブルを作成します。

  **呼び出し例:** 「CDK を使って私の DynamoDB データモデルをデプロイするためのリソースを生成してください」

- `dynamodb_data_model_schema_converter` - データモデル(dynamodb_data_model.md)を、DynamoDB のテーブル、インデックス、エンティティ、フィールド、アクセスパターンを表す構造化された schema.json ファイルに変換します。この機械可読フォーマットはコード生成に使用され、ドキュメント生成やインフラストラクチャのプロビジョニングなど他の用途にも拡張できます。正確性を確保するため、最大 8 回のイテレーションでスキーマを自動的に検証します。

  **呼び出し例:** 「コード生成のために私のデータモデルを schema.json に変換してください」

- `dynamodb_data_model_schema_validator` - schema.json ファイルのコード生成互換性を検証します。フィールドタイプ、オペレーション、GSI マッピング、パターン ID をチェックし、修正提案付きの詳細なエラーメッセージを提供します。スキーマが generate_data_access_layer ツールで使用できる状態であることを保証します。

  **呼び出し例:** 「/path/to/schema.json にある私の schema.json ファイルを検証してください」

- `generate_data_access_layer` - schema.json から型安全な Python コードを生成します。これには、フィールド検証付きのエンティティクラス、CRUD 操作を備えたリポジトリクラス、完全に実装されたアクセスパターン、およびオプションの使用例が含まれます。生成されるコードは、検証に Pydantic を、DynamoDB 操作に boto3 を使用します。

  **呼び出し例:** 「私の schema.json から Python コードを生成してください」

- `compute_performances_and_costs` - アクセスパターンから DynamoDB のキャパシティユニット(RCU/WCU)と月額コストを計算します。すべての DynamoDB オペレーション(GetItem、Query、Scan、PutItem、UpdateItem、DeleteItem、BatchGetItem、BatchWriteItem、TransactGetItems、TransactWriteItems)を分析し、GSI の追加書き込みを追跡し、ストレージコストを計算します。包括的なコストレポートを dynamodb_data_model.md に追記します。

  **呼び出し例:** 「私の DynamoDB データモデルのコストとパフォーマンスを計算してください」

## 前提条件 {#prerequisites}

1. [Astral](https://docs.astral.sh/uv/getting-started/installation/) または [GitHub README](https://github.com/astral-sh/uv#installation) から `uv` をインストールします
2. `uv python install 3.10` を使用して Python をインストールします
3. AWS サービスへのアクセス権を持つ AWS 認証情報をセットアップします

## インストール {#installation}

| Kiro   | Cursor  | VS Code |
|:------:|:-------:|:-------:|
| [![Kiro](https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro)](https://kiro.dev/launch/mcp/add?name=awslabs-dynamodb-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.dynamodb-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22DDB-MCP-READONLY%22%3A%22true%22%2C%22AWS_PROFILE%22%3A%22default%22%2C%22AWS_REGION%22%3A%22us-west-2%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D)| [![Cursor](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs-dynamodb-mcp-server&config=JTdCJTIyY29tbWFuZCUyMiUzQSUyMnV2eCUyMGF3c2xhYnMuZHluYW1vZGItbWNwLXNlcnZlciU0MGxhdGVzdCUyMiUyQyUyMmVudiUyMiUzQSU3QiUyMkFXU19QUk9GSUxFJTIyJTNBJTIyZGVmYXVsdCUyMiUyQyUyMkFXU19SRUdJT04lMjIlM0ElMjJ1cy13ZXN0LTIlMjIlMkMlMjJGQVNUTUNQX0xPR19MRVZFTCUyMiUzQSUyMkVSUk9SJTIyJTdEJTJDJTIyZGlzYWJsZWQlMjIlM0FmYWxzZSUyQyUyMmF1dG9BcHByb3ZlJTIyJTNBJTVCJTVEJTdE)| [![VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=DynamoDB%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.dynamodb-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22default%22%2C%22AWS_REGION%22%3A%22us-west-2%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

> **注:** 上記のインストールボタンは、デフォルトで `AWS_REGION` を `us-west-2` に設定します。別のリージョンが必要な場合は、インストール後に MCP 設定でこの値を更新してください。

MCP サーバーを設定ファイルに追加します([Kiro](https://kiro.dev/docs/mcp/) の場合は `.kiro/settings/mcp.json` に追加します - [設定パス](https://kiro.dev/docs/cli/mcp/configuration/#mcp-server-loading-priority)を参照してください)。

```json
{
  "mcpServers": {
    "awslabs-dynamodb-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.dynamodb-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Windows でのインストール {#windows-installation}

Windows ユーザーの場合、MCP サーバーの設定フォーマットは少し異なります。

```json
{
  "mcpServers": {
    "awslabs-dynamodb-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.dynamodb-mcp-server@latest",
        "awslabs.dynamodb-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

### Docker でのインストール {#docker-installation}

`docker build -t awslabs/dynamodb-mcp-server .` が成功した後、次のように設定します。

```json
{
  "mcpServers": {
    "awslabs-dynamodb-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env",
        "FASTMCP_LOG_LEVEL=ERROR",
        "awslabs/dynamodb-mcp-server:latest"
      ],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## データモデリング {#data-modeling}

### 自然言語によるデータモデリング {#data-modeling-in-natural-language}

`dynamodb_data_modeling` ツールを使用すると、AI エージェントとの自然言語での対話を通じて DynamoDB データモデルを設計できます。「DynamoDB MCP を使って DynamoDB データモデルの設計を手伝ってください」と依頼するだけです。

このツールは、アプリケーション要件を DynamoDB データモデルに変換する体系的なワークフローを提供します。

**要件収集フェーズ:**
- 自然言語での対話を通じてアクセスパターンを把握します
- エンティティ、リレーションシップ、読み取り/書き込みパターンをドキュメント化します
- 各パターンの推定リクエスト数/秒(RPS)を記録します
- リアルタイムで更新される `dynamodb_requirements.md` ファイルを作成します
- 他の AWS サービスに適しているパターンを特定します(テキスト検索には OpenSearch、分析には Redshift)
- 特別な設計上の考慮事項をフラグ付けします(例: DynamoDB Streams と Lambda を必要とする大規模なファンアウトパターン)

**設計フェーズ:**
- 最適化されたテーブルおよびインデックス設計を生成します
- 詳細な設計根拠を含む `dynamodb_data_model.md` を作成します
- 推定月額コストを提示します
- 各アクセスパターンがどのようにサポートされるかをドキュメント化します
- スケールとパフォーマンスのための最適化に関する推奨事項を含みます

このツールは、推論モデルが高度なモデリング手法をガイドできるように、エキスパートが設計したコンテキストに支えられています。Anthropic Claude 4/4.5 Sonnet、OpenAI o3、Google Gemini 2.5 などの推論能力を持つモデルで最良の結果が得られます。

### データモデルの検証 {#data-model-validation}

**データモデル検証の前提条件:**
データモデル検証ツールを使用するには、以下のいずれかが必要です。
- **コンテナランタイム**: デーモンが実行中の Docker、Podman、Finch、または nerdctl
- **Java ランタイム**: Java JRE バージョン 17 以降(`JAVA_HOME` を設定するか、`java` がシステムの PATH にあることを確認してください)

データモデルの設計が完了したら、`dynamodb_data_model_validation` ツールを使用して、DynamoDB Local に対してデータモデルを自動的にテストできます。この検証ツールは、反復的な検証サイクルを作り出すことで、生成と実行の間のループを閉じます。

**仕組み:**

このツールは、従来の手動による検証プロセスを自動化します。

1. **セットアップ**: DynamoDB Local 環境を起動します(Docker/Podman/Finch/nerdctl、または Java フォールバック)
2. **テスト仕様の生成**: テスト対象のテーブル、サンプルデータ、アクセスパターンを列挙した `dynamodb_data_model.json` を作成します
3. **スキーマのデプロイ**: テーブルとインデックスを作成し、サンプルデータをローカルに挿入します
4. **テストの実行**: アクセスパターンで定義されたすべての読み取りおよび書き込み操作を実行します
5. **結果の検証**: 各アクセスパターンが正しく効率的に動作することをチェックします
6. **反復的な改善**: 検証が失敗した場合(例: パーティションキーの不整合によりクエリが不完全な結果を返す)、ツールは問題を記録し、影響を受けるスキーマを再生成して、すべてのパターンが合格するまでテストを再実行します

**検証の出力:**

- `dynamodb_model_validation.json`: パターンごとのレスポンスを含む詳細な検証結果
- `validation_result.md`: 各アクセスパターンの合格/不合格ステータスを含む検証プロセスのサマリー
- 不正なキー構造、欠落しているインデックス、非効率なクエリパターンなどの問題を特定します

### ソースデータベース分析 {#source-database-analysis}

`source_db_analyzer` ツールは、既存のデータベースからスキーマとアクセスパターンを抽出し、DynamoDB モデルの設計を支援します。これはリレーショナルデータベースからの移行時に役立ちます。

このツールは、MySQL について 2 つの接続方法をサポートします。
- **RDS Data API ベースのアクセス**: クラスター ARN を使用したサーバーレス接続
- **接続ベースのアクセス**: ホスト名/ポートを使用した従来型の接続

**サポートされるデータベース:**
- MySQL / Aurora MySQL
- PostgreSQL
- SQL Server
- Oracle

**実行モード:**
- **セルフサービスモード**: SQL クエリを生成し、ユーザー自身が実行して結果を提供します(MySQL、PostgreSQL、SQL Server、Oracle)
- **マネージドモード**: AWS RDS Data API 経由の直接接続(MySQL のみ)

このツールは、本番環境ではないデータベースインスタンスに対して実行することを推奨します。

### セルフサービスモード(MySQL、PostgreSQL、SQL Server、Oracle) {#self-service-mode-mysql-postgresql-sql-server-oracle}

セルフサービスモードでは、AWS への接続なしで任意のデータベースを分析できます。

1. **クエリの生成**: ツールが(選択したデータベースに基づいて)SQL クエリをファイルに書き出します
2. **クエリの実行**: ユーザーがデータベースに対してクエリを実行します
3. **結果の提供**: ツールが結果を解析して分析を生成します

### マネージドモード(MySQL のみ) {#managed-mode-mysql-only}

マネージドモードでは、ツールを AWS RDS Data API に接続して既存の MySQL/Aurora データベースを分析し、DynamoDB モデリングのためのスキーマとアクセスパターンを抽出できます。

#### MySQL 統合の前提条件(マネージドモード) {#prerequisites-for-mysql-integration-managed-mode}

**RDS Data API ベースのアクセスの場合:**
1. RDS Data API が有効化された MySQL クラスター
2. AWS Secrets Manager に保存されたデータベース認証情報
3. RDS Data API と Secrets Manager へのアクセス権限を持つ AWS 認証情報

**接続ベースのアクセスの場合:**
1. 使用する環境からアクセス可能な MySQL サーバー
2. AWS Secrets Manager に保存されたデータベース認証情報
3. Secrets Manager のシークレットには、(`username` と `password` に加えて)データベースのホスト名と一致する `host` フィールドが**必ず**含まれている必要があります。これにより、認証情報が意図したデータベースホストに対してのみ使用されることが保証されます。RDS が管理するシークレットにはこのフィールドが自動的に含まれます。シークレットを手動で作成した場合は、[標準的な構造](https://docs.aws.amazon.com/secretsmanager/latest/userguide/reference_secret_json_structure.html)に従っていることを確認してください。

   ```bash
   aws secretsmanager create-secret \
       --name "my-db-secret" \
       --secret-string '{
           "engine": "mysql",
           "host": "my-db.cluster-xxx.us-east-1.rds.amazonaws.com",
           "username": "<username>",
           "password": "<password>",
           "dbname": "<database name>",
           "port": 3306
       }'
   ```

4. Secrets Manager へのアクセス権限を持つ AWS 認証情報

**両方の接続方法の場合:**
4. アクセスパターン分析のために Performance Schema を有効化します(オプションですが推奨):
   - DB パラメータグループで `performance_schema` パラメータを 1 に設定します
   - 変更後に DB インスタンスを再起動します
   - `SHOW GLOBAL VARIABLES LIKE '%performance_schema'` で確認します
   - 以下のチューニングを検討してください:
     - `performance_schema_digests_size` - events_statements_summary_by_digest の最大行数
     - `performance_schema_max_digest_length` - ステートメントダイジェストごとの最大バイト長(デフォルト: 1024)
   - Performance Schema がない場合、分析は information schema のみに基づきます

#### MySQL 環境変数 {#mysql-environment-variables}

MySQL 統合を有効にするには、以下の環境変数を追加します。

**RDS Data API ベースのアクセスの場合:**
- `MYSQL_CLUSTER_ARN`: MySQL クラスターの ARN
- `MYSQL_SECRET_ARN`: データベース認証情報を含むシークレットの ARN
- `MYSQL_DATABASE`: 分析対象のデータベース名
- `AWS_REGION`: クラスターの AWS リージョン

**接続ベースのアクセスの場合:**
- `MYSQL_HOSTNAME`: MySQL サーバーのホスト名またはエンドポイント
- `MYSQL_PORT`: MySQL サーバーのポート(オプション、デフォルト: 3306)
- `MYSQL_SECRET_ARN`: データベース認証情報を含むシークレットの ARN
- `MYSQL_DATABASE`: 分析対象のデータベース名
- `AWS_REGION`: Secrets Manager が配置されている AWS リージョン

**共通オプション:**
- `MYSQL_MAX_QUERY_RESULTS`: 分析出力ファイルの最大行数(オプション、デフォルト: 500)

**注:** 明示的に指定されたツールパラメータは環境変数より優先されます。接続方法(クラスター ARN またはホスト名)はどちらか一方のみを指定してください。

#### MySQL を使用した MCP 設定 {#mcp-configuration-with-mysql}

**RDS Data API ベースのアクセスの場合:**

```json
{
  "mcpServers": {
    "awslabs-dynamodb-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.dynamodb-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-west-2",
        "FASTMCP_LOG_LEVEL": "ERROR",
        "MYSQL_CLUSTER_ARN": "arn:aws:rds:$REGION:$ACCOUNT_ID:cluster:$CLUSTER_NAME",
        "MYSQL_SECRET_ARN": "arn:aws:secretsmanager:$REGION:$ACCOUNT_ID:secret:$SECRET_NAME",
        "MYSQL_DATABASE": "<DATABASE_NAME>",
        "MYSQL_MAX_QUERY_RESULTS": "500"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

**接続ベースのアクセスの場合:**

```json
{
  "mcpServers": {
    "awslabs.dynamodb-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.dynamodb-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-west-2",
        "FASTMCP_LOG_LEVEL": "ERROR",
        "MYSQL_HOSTNAME": "<MYSQL_HOST>",
        "MYSQL_PORT": "3306",
        "MYSQL_SECRET_ARN": "arn:aws:secretsmanager:$REGION:$ACCOUNT_ID:secret:$SECRET_NAME",
        "MYSQL_DATABASE": "<DATABASE_NAME>",
        "MYSQL_MAX_QUERY_RESULTS": "500"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

#### ソースデータベース分析の使用方法 {#using-source-database-analysis}

1. データベースに対して `source_db_analyzer` を実行します(セルフサービスモードまたはマネージドモード)
2. 生成されたタイムスタンプ付きの分析フォルダ(database_analysis_YYYYMMDD_HHMMSS)を確認します
3. まず manifest.md ファイルを読みます - すべての分析ファイルと統計情報が列挙されています
4. すべての分析ファイルを読んで、スキーマ構造とアクセスパターンを理解します
5. この分析を `dynamodb_data_modeling` とともに使用して、DynamoDB スキーマを設計します

このツールは、以下を含む Markdown ファイルを生成します。
- スキーマ構造(テーブル、カラム、インデックス、外部キー)
- Performance Schema から得られるアクセスパターン(クエリパターン、RPS、頻度)
- 経時的な変化を追跡するためのタイムスタンプ付き分析

## スキーマ変換とコード生成 {#schema-conversion-and-code-generation}

DynamoDB データモデルを設計した後、それを構造化されたスキーマに変換し、リファレンス用の Python コードを生成できます。**LLM を通じて MCP ツールを使用する場合、このワークフロー全体が自動的に実行されます** - LLM が、手動でのツール呼び出しを必要とせず、単一の会話の中でスキーマ変換、検証、コード生成をガイドします。

スタンドアロンで使用する場合は、これらのツールを CLI から直接呼び出したり、schema.json ファイルを手動で編集して必要に応じてコードを再生成したりすることもできます。

> **注:** データモデル検証(`dynamodb_data_model_validation`)は、コード生成にとってはオプションです。ただし、生成されたコードを `usage_examples.py` を使って DynamoDB Local に対してテストする予定がある場合は、先に検証を実行することを推奨します。検証により DynamoDB Local にテーブルとテストデータが自動的にセットアップされるためです。

### データモデルからスキーマへの変換 {#converting-data-model-to-schema}

`dynamodb_data_model_schema_converter` ツールは、人間が読める形式のデータモデル(dynamodb_data_model.md)を、DynamoDB のテーブル、インデックス、エンティティ、アクセスパターンを表す構造化された JSON スキーマに変換します。この機械可読フォーマットによりコード生成が可能になり、ドキュメントやインフラストラクチャのプロビジョニングにも拡張できます。

このツールは生成されたスキーマを自動的に検証し、検証が失敗した場合は詳細なエラーメッセージと修正提案を提供します。出力は分離のためタイムスタンプ付きフォルダに保存されます。

**スキーマ構造:**

生成される schema.json は、以下を含む構造化された表現です。
- **Tables**: パーティションキー/ソートキーを持つ 1 つ以上の DynamoDB テーブル定義
- **GSI Definitions**: Global Secondary Index の設定(オプション)
- **Entities**: 型付きフィールドを持つドメインモデル(User、Order、Product など)
- **Field Types**: string、integer、decimal、boolean、array、object、uuid
- **Access Patterns**: パラメータ定義とキーテンプレートを持つ Query/Scan/GetItem オペレーション
- **Key Templates**: パーティションキーとソートキーを生成するためのパターン(例: `USER#{user_id}`)

この構造化フォーマットは、コード生成ツールの入力として機能します。

### スキーマファイルの検証 {#validating-schema-files}

`dynamodb_data_model_schema_validator` ツールは、schema.json ファイルがコード生成に適した正しいフォーマットになっていることを検証します。

**検証チェック項目:**

- 必須セクション(table_config、entities)が存在すること
- すべての必須フィールドが存在すること
- フィールドタイプが有効であること(string、integer、decimal、boolean、array、object、uuid)
- 列挙値が正しいこと(オペレーションタイプ、戻り値タイプ)
- パターン ID がすべてのエンティティにわたって一意であること
- GSI 名が gsi_list と gsi_mappings の間で一致していること
- テンプレートで参照されるフィールドがエンティティのフィールドに存在すること
- 範囲条件が有効で、パラメータ数が正しいこと
- アクセスパターンが有効なオペレーションと戻り値タイプを持つこと

**セキュリティ:**

スキーマファイルは、現在の作業ディレクトリまたはそのサブディレクトリ内に存在する必要があります。パストラバーサルの試行はセキュリティのためブロックされます。

**検証出力の例:**

成功:
```
✅ Schema validation passed!
```

修正提案付きのエラー:
```
❌ Schema validation failed:
  • entities.User.fields[0].type: Invalid type value 'strng'
    💡 Did you mean 'string'? Valid options: string, integer, decimal, boolean, array, object, uuid
```

### データアクセスレイヤーの生成 {#generating-data-access-layer}

`generate_data_access_layer` ツールは、検証済みの schema.json ファイルから型安全な Python コードを生成します。

**生成されるコード:**

- **エンティティクラス**: フィールド検証と型安全性を備えた Pydantic モデル
- **リポジトリクラス**: 各エンティティに対する CRUD 操作(create、read、update、delete)
- **アクセスパターン**: スキーマから完全に実装された query および scan 操作
- **ベースリポジトリ**: すべてのリポジトリで共有される機能
- **使用例**: 生成されたクラスの使い方を示すサンプルコード(オプション)
- **設定**: コード品質とフォーマットのための ruff.toml

**コード生成の前提条件:**

生成される Python コードには、以下のランタイム依存関係が必要です。
- `pydantic>=2.0` - エンティティ検証と型安全性のため
- `boto3>=1.38` - DynamoDB 操作のため

プロジェクトにインストールします。
```bash
uv add pydantic boto3
# or
pip install pydantic boto3
```

**オプションの開発用依存関係:**

生成されたコードのリンティングとフォーマットのため:
- `ruff==0.15.8` - Python のリンター兼フォーマッター(推奨)

**生成されるファイル構造:**

```
generated_dal/
├── entities.py              # Pydantic entity models
├── repositories.py          # Repository classes with CRUD operations
├── base_repository.py       # Base repository functionality
├── transaction_service.py   # Cross-table transaction methods (if schema includes cross_table_access_patterns)
├── access_pattern_mapping.json  # Pattern ID to method mapping
├── usage_examples.py        # Sample usage code (if enabled)
└── ruff.toml               # Linting configuration
```

**生成されたコードの使用:**

生成されたコードは、すべてのアクセスパターンに対応する型安全なエンティティクラスとリポジトリメソッドを提供します。

```python
from generated_dal.repositories import UserRepository
from generated_dal.entities import User

# Initialize repository
repo = UserRepository(table_name="MyTable")

# Create a new user
user = User(user_id="123", username="username", name="John Doe")
repo.create(user)

# Query by access pattern
users = repo.get_user_by_username(username="username")

# Update user
user.name = "Jane Doe"
repo.update(user)
```

ruff で生成されたコードをリンティングおよびフォーマットするには次を実行します。
```bash
ruff check generated_dal/        # Check for issues
ruff check --fix generated_dal/  # Auto-fix issues
ruff format generated_dal/       # Format code
```
