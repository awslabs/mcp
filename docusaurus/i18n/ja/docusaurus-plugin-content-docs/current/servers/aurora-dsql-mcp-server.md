---
title: "AWS Labs Aurora DSQL MCP サーバー"
---

Aurora DSQL 向けの AWS Labs Model Context Protocol (MCP) サーバーと、開発時にモデルを追加でステアリングするために使用できる対応 AI ルールです。

## 機能 {#features}

- 人間が読める形式の質問やコマンドを、構造化された Postgres 互換の SQL クエリに変換し、設定された Aurora DSQL データベースに対して実行します。
- デフォルトは読み取り専用で、`--allow-writes` によりトランザクションを有効化できます
- リクエスト間で接続を再利用してパフォーマンスを向上させます
- Aurora DSQL のドキュメント、検索、ベストプラクティスの推奨事項への組み込みアクセス

## 利用可能なツール {#available-tools}

### データベース操作 {#database-operations}

[重要]
MCP サーバーでデータベース操作を有効にするには、--cluster_endpoint、--database_user、--region の有効な設定が必要です。

- **readonly_query** - DSQL クラスターに対して読み取り専用の SQL クエリを実行します
- **transact** - トランザクション内で SQL ステートメントを実行します
  - 読み取り専用モードの場合: トランザクションの一貫性を保った読み取り操作をサポートします
  - `--allow-writes` を指定した場合: すべての書き込み操作もサポートします
- **get_schema** - テーブルスキーマ情報を取得します

### ドキュメントと推奨事項 {#documentation-and-recommendations}

- **dsql_search_documentation** - Aurora DSQL のドキュメントを検索します
  - パラメータ: `search_phrase`（必須）、`limit`（任意）
- **dsql_read_documentation** - 特定の DSQL ドキュメントページを読み取ります
  - パラメータ: `url`（必須）、`start_index`（任意）、`max_length`（任意）
- **dsql_recommend** - DSQL のベストプラクティスに関する推奨事項を取得します
  - パラメータ: `url`（必須）

### SQL 検証 {#sql-validation}

- **dsql_lint** - SQL の Aurora DSQL 互換性を検証し、必要に応じて問題を自動修正します
  - パラメータ: `sql`（必須）、`fix`（任意、デフォルトは false）
  - ルール違反、提案、および任意で修正済みの SQL 文字列を含む診断結果を返します

## 前提条件 {#prerequisites}

1. [Aurora DSQL クラスター](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/getting-started.html)を持つ AWS アカウント
1. この MCP サーバーは、LLM クライアントと同じホスト上でローカルにのみ実行できます。
1. AWS サービスへのアクセス権を持つ AWS 認証情報を設定すること
   - 適切な権限を持つ AWS アカウントが必要です
   - `aws configure` または環境変数で AWS 認証情報を設定します

## インストール {#installation}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.aurora-dsql-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aurora-dsql-mcp-server%40latest%22%2C%22--cluster_endpoint%22%2C%22%5Byour%20dsql%20cluster%20endpoint%5D%22%2C%22--region%22%2C%22%5Byour%20dsql%20cluster%20region%2C%20e.g.%20us-east-1%5D%22%2C%22--database_user%22%2C%22%5Byour%20dsql%20username%5D%22%2C%22--profile%22%2C%22default%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.aurora-dsql-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXVyb3JhLWRzcWwtbWNwLXNlcnZlckBsYXRlc3QgLS1jbHVzdGVyX2VuZHBvaW50IFt5b3VyIGRzcWwgY2x1c3RlciBlbmRwb2ludF0gLS1yZWdpb24gW3lvdXIgZHNxbCBjbHVzdGVyIHJlZ2lvbiwgZS5nLiB1cy1lYXN0LTFdIC0tZGF0YWJhc2VfdXNlciBbeW91ciBkc3FsIHVzZXJuYW1lXSAtLXByb2ZpbGUgZGVmYXVsdCIsImVudiI6eyJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ%3D%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Aurora%20DSQL%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aurora-dsql-mcp-server%40latest%22%2C%22--cluster_endpoint%22%2C%22%5Byour%20dsql%20cluster%20endpoint%5D%22%2C%22--region%22%2C%22%5Byour%20dsql%20cluster%20region%2C%20e.g.%20us-east-1%5D%22%2C%22--database_user%22%2C%22%5Byour%20dsql%20username%5D%22%2C%22--profile%22%2C%22default%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

### `uv` の使用 {#using-uv}

1. [Astral](https://docs.astral.sh/uv/getting-started/installation/) または [GitHub README](https://github.com/astral-sh/uv#installation) から `uv` をインストールします
2. `uv python install 3.10` を使用して Python をインストールします

MCP クライアントの設定で MCP サーバーを構成します（例: Kiro の場合は `~/.kiro/settings/mcp.json` を編集します）:

```json
{
  "mcpServers": {
    "awslabs.aurora-dsql-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.aurora-dsql-mcp-server@latest",
        "--cluster_endpoint",
        "[your dsql cluster endpoint]",
        "--region",
        "[your dsql cluster region, e.g. us-east-1]",
        "--database_user",
        "[your dsql username]",
        "--profile",
        "default"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Windows へのインストール {#windows-installation}

Windows ユーザーの場合、MCP サーバーの設定形式が若干異なります:

```json
{
  "mcpServers": {
    "awslabs.aurora-dsql-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.aurora-dsql-mcp-server@latest",
        "awslabs.aurora-dsql-mcp-server.exe"
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

### Docker の使用 {#using-docker}

1. 'git clone https://github.com/awslabs/mcp.git' を実行します
2. サブディレクトリ 'src/aurora-dsql-mcp-server/' に移動します
3. 'docker build -t awslabs/aurora-dsql-mcp-server:latest .' を実行します
4. 一時的な認証情報を含む env ファイルを作成します:

手動で作成する場合:

```file
# fictitious `.env` file with AWS temporary credentials
AWS_ACCESS_KEY_ID=<from the profile you set up>
AWS_SECRET_ACCESS_KEY=<from the profile you set up>
AWS_SESSION_TOKEN=<from the profile you set up>
```

または `aws configure` を使用する場合:

```bash
aws configure export-credentials --profile your-profile-name --format env > temp_aws_credentials.env | sed 's/^export //' > temp_aws_credentials.env
```

```json
{
  "mcpServers": {
    "awslabs.aurora-dsql-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "--env-file",
        "/full/path/to/file/above/.env",
        "awslabs/aurora-dsql-mcp-server:latest",
        "--cluster_endpoint",
        "[your data]",
        "--database_user",
        "[your data]",
        "--region",
        "[your data]"
      ]
    }
  }
}
```

## サーバー設定オプション {#server-configuration-options}

### `--allow-writes` {#--allow-writes}

デフォルトでは、DSQL MCP サーバーは読み取り専用モードで動作します。このモードでは:

- **readonly_query**: 単一の読み取り専用クエリを実行します
- **transact**: ポイントインタイムの一貫性を保った読み取り専用トランザクションを実行します
  - 同じ時点のデータを参照する必要がある複数のクエリに便利です
  - すべてのステートメントは読み取り専用操作であることが検証されます
  - 書き込み操作（INSERT、UPDATE、DELETE、CREATE、DROP、ALTER など）は拒否されます

書き込み操作を有効にするには、`--allow-writes` パラメータを指定します。読み書きモードでは:

- **readonly_query**: 同じ動作（読み取り専用クエリ）
- **transact**: すべての DDL および DML 操作（CREATE、INSERT、UPDATE、DELETE など）をサポートします

DSQL への接続には最小権限のアクセスを使用することを推奨します。たとえば、可能な限り読み取り専用のロールを使用してください。読み取り専用モードは、変更操作を拒否するためのベストエフォートのクライアント側検証を提供します。

### `--cluster_endpoint` {#--cluster_endpoint}

接続先のクラスターを指定する必須パラメータです。クラスターの完全なエンドポイントを指定する必要があります。例: `01abc2ldefg3hijklmnopqurstu.dsql.us-east-1.on.aws`

### `--database_user` {#--database_user}

接続に使用するユーザーを指定する必須パラメータです。例:
`admin` や `my_user`。使用する AWS 認証情報には、そのユーザーとしてログインする権限が必要であることに注意してください。DSQL でのデータベースロールの設定と使用の詳細については、[Using database roles with IAM roles](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/using-database-and-iam-roles.html) を参照してください。

### `--profile` {#--profile}

認証情報に使用する AWS プロファイルを指定できます。Docker でのインストールではサポートされていないことに注意してください。

MCP 設定で `AWS_PROFILE` 環境変数を使用することもサポートされています:

```json
"env": {
  "AWS_PROFILE": "your-aws-profile"
}
```

どちらも指定されていない場合、MCP サーバーは AWS 設定ファイル内の「default」プロファイルをデフォルトで使用します。

### `--region` {#--region}

DSQL データベースのリージョンを指定する必須パラメータです。

### `--knowledge-server` {#--knowledge-server}

DSQL ナレッジツール（ドキュメントの検索、読み取り、推奨事項）用のリモート MCP サーバーエンドポイントを指定する任意のパラメータです。
デフォルトで事前設定されています。

例:

```bash
--knowledge-server https://custom-knowledge-server.example.com
```

**注:** セキュリティのため、信頼できるナレッジサーバーエンドポイントのみを使用してください。サーバーは HTTPS エンドポイントである必要があります。

### `--knowledge-timeout` {#--knowledge-timeout}

ナレッジサーバーへのリクエストのタイムアウトを秒単位で指定する任意のパラメータです。

デフォルト: `30.0`

例:

```bash
--knowledge-timeout 60.0
```

低速なネットワークでドキュメントにアクセスする際にタイムアウトが発生する場合は、この値を増やしてください。

## 開発とテスト {#development-and-testing}

### テストの実行 {#running-tests}

このプロジェクトには、読み取り専用の強制メカニズムを検証するための包括的なテストが含まれています。テストを実行するには:

```bash
# Install dependencies and run tests
uv run pytest tests/test_readonly_enforcement.py -v

# Run all tests
uv run pytest -v

# Run tests with coverage
uv run pytest --cov=awslabs.aurora_dsql_mcp_server tests/ -v
```

### ローカルでの Docker テスト {#local-docker-testing}

Docker を使用して MCP サーバーをローカルでテストするには:

1. **Docker イメージをビルドします:**

   ```bash
   cd src/aurora-dsql-mcp-server
   docker build -t awslabs/aurora-dsql-mcp-server:latest .
   ```

2. **AWS 認証情報ファイルを作成します:**

   オプション A - 手動で作成:

   ```bash
   # Create .env file with your AWS credentials
   cat > .env << EOF
   AWS_ACCESS_KEY_ID=your_access_key_here
   AWS_SECRET_ACCESS_KEY=your_secret_key_here
   AWS_SESSION_TOKEN=your_session_token_here
   EOF
   ```

   オプション B - AWS CLI からエクスポート:

   ```bash
   aws configure export-credentials --profile your-profile-name --format env > temp_aws_credentials.env
   sed 's/^export //' temp_aws_credentials.env > .env
   rm temp_aws_credentials.env
   ```

3. **コンテナを直接テストします:**

   ```bash
   docker run -i --rm \
     --env-file .env \
     awslabs/aurora-dsql-mcp-server:latest \
     --cluster_endpoint "your-dsql-cluster-endpoint" \
     --database_user "your-username" \
     --region "us-east-1"
   ```

4. **書き込み操作を有効にしてテストします:**
   ```bash
   docker run -i --rm \
     --env-file .env \
     awslabs/aurora-dsql-mcp-server:latest \
     --cluster_endpoint "your-dsql-cluster-endpoint" \
     --database_user "your-username" \
     --region "us-east-1" \
     --allow-writes
   ```

**注:** プレースホルダーの値を、実際の DSQL クラスターエンドポイント、ユーザー名、リージョンに置き換えてください。

## AI ルール {#ai-rules}

このリポジトリには AI ルール（ステアリング）も含まれています。これらの Markdown ファイルは、AI アシスタントがコード生成時に自動的に適用するベストプラクティスとパターンに関するシンプルなコンテキストとガイダンスとして機能し、エージェンティックな開発の品質を向上させます。

推奨パス:
* [エージェント非依存のインストールのための Skills CLI](#skills-cli)
* [Kiro Power](#kiro-power) - ボタンクリックでのインストール
* [Claude Skill](#claude-skill) - インストール手順は [claude_skill_setup.md](https://github.com/awslabs/mcp/blob/main/src/aurora-dsql-mcp-server/skills/claude_skill_setup.md) を参照
* [Gemini Skill](#gemini-skill) - Gemini の github サブリポジトリスキルインストールで `--path` を使用
* [Codex Skill](#codex-skill) - Codex の `$skill-installer` スキルを使用。

代替手段:
[dsql-skill](https://github.com/awslabs/mcp/tree/main/src/aurora-dsql-mcp-server/skills/dsql-skill) を各ツールの `rules` ディレクトリにクローンして、他のコーディングアシスタントで使用することもできます。

### Skills CLI {#skills-cli}
[DSQL スキル](https://skills.sh/awslabs/mcp/dsql)は [Skills CLI](https://skills.sh/docs/cli) を使用してインストールすることもできます。

```bash
npx skills add awslabs/mcp --skill dsql
```

CLI は以下の項目をガイドします:
* インストール先のエージェントの選択（Kiro、Claude Code、Cursor、Copilot、Gemini、Codex、Roo、Cline、OpenCode、Windsurf など）
* インストールスコープ
  - プロジェクト: 現在のディレクトリにインストール（プロジェクトと一緒にコミットされます）
  - グローバル: ホームディレクトリにインストール（すべてのプロジェクトで利用可能）
*  インストール方法
   - シンボリックリンク（推奨）: 単一の信頼できるソース、簡単な更新
   - すべてのエージェントにコピー: 各エージェントごとに独立したコピー

以下のコマンドでいつでもスキルの確認と更新ができます:
```bash
npx skills check
npx skills update
```

### Kiro Power {#kiro-power}

Kiro のパワーをセットアップするには:
1. [Kiro Powers Registry](https://kiro.dev/launch/powers/amazon-aurora-dsql/) から直接インストールします
2. IDE 内のパワーにリダイレクトされたら、次のいずれかを行います:
   1. **`Try Power`** ボタンを選択します。以下を希望する方に推奨します:
      - AI による MCP サーバーセットアップのガイド
      - 新しいクラスターを作成する DSQL のインタラクティブなオンボーディング体験
   2. 新しい Kiro チャットを開き、DSQL に関連する質問をします
      - **必要に応じて MCP 設定を更新:** 既存のクラスターの詳細を追加して MCP サーバーの接続をテストすると、
        パワーですぐに MCP サーバーを使用できるようになります。
      - Kiro エージェントは、ユーザーのタスクの完了にパワーが有用であると判断すると、
        パワーを自動的にアクティブ化します。

### Claude Skill {#claude-skill}
**Skills CLI を使用したシンプルなセットアップ**:
前述のとおり、このスキルは [Skills CLI](#skills-cli) を使用して Claude Code にインストールできます。インストール先のエージェントとして
Claude Code のみを指定するには、以下を使用します:

```bash
npx skills add awslabs/mcp --skill dsql --agent claude-code
```

**Git クローンを使用した直接セットアップ**:
代替のセットアップ方法は [claude_skill_setup.md](https://github.com/awslabs/mcp/blob/main/src/aurora-dsql-mcp-server/skills/claude_skill_setup.md) に記載されています。

この方法では、dsql-skill ディレクトリのスパースクローンを取得し、このクローンを
`.claude/skills/` フォルダにシンボリックリンクします。これにより、スキルの更新が必要になったときに
いつでも変更を取得できます。

### Gemini Skill {#gemini-skill}

Gemini にスキルを直接追加するには、スコープを `workspace`（プロジェクト内に限定）または `user`（デフォルト、グローバル）から決定し、\
`skills` インストーラーを使用します。

```bash
gemini skills install https://github.com/awslabs/mcp.git --path src/aurora-dsql-mcp-server/skills/dsql-skill --scope $SCOPE
```

その後、Gemini で `/dsql` スキルコマンドを使用でき、Gemini はスキルを使用すべきタイミングを自動的に検出します。

### Codex Skill {#codex-skill}

Codex CLI または TUI から `$skill-installer` スキルを使用してスキルインストーラーを実行します。

```bash
$skill-installer install dsql skill: https://github.com/awslabs/mcp/tree/main/src/aurora-dsql-mcp-server/skills/dsql-skill
```

スキルを認識させるために codex を再起動します。その後、`$dsql` を使用してスキルをアクティブ化できます。
