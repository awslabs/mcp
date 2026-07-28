---
title: "Finch MCPサーバー"
---

Finch 向けの Model Context Protocol (MCP) サーバーです。生成 AI モデルが、finch cli を活用した MCP ツールを通じてコンテナイメージのビルドとプッシュを行えるようにします。

## 機能 {#features}

この MCP サーバーは、MCP クライアントと Finch の間のブリッジとして機能し、生成 AI モデルがコンテナイメージをビルドしてリポジトリにプッシュしたり、必要に応じて ECR リポジトリを作成したりできるようにします。このサーバーは、操作を実行する前に Finch VM が適切に初期化され実行中であることを確認し、Finch と安全にやり取りする手段を提供します。

## 主な機能 {#key-capabilities}

- Finch を使用したコンテナイメージのビルド
- Amazon ECR を含むリポジトリへのコンテナイメージのプッシュ
- ECR リポジトリの存在確認と、必要に応じた作成
- macOS および Windows における Finch VM の自動管理（初期化、起動など）
- 必要に応じた ECR 認証ヘルパーの自動設定（config.json は自動的に処理されるため、finch.yaml のみを変更します）

## 前提条件 {#prerequisites}

1. [Astral](https://docs.astral.sh/uv/getting-started/installation/) または [GitHub README](https://github.com/astral-sh/uv#installation) から `uv` をインストールします
2. `uv python install 3.10` を使用して Python をインストールします
3. システムに [Finch](https://github.com/runfinch/finch) をインストールします
4. ECR 操作を行う場合は、ECR リポジトリへのプッシュおよび ECR リポジトリの作成・記述の権限を持つ AWS 認証情報が必要です

## セットアップ {#setup}

### インストール {#installation}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.finch-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.finch-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22default%22%2C%22AWS_REGION%22%3A%22us-west-2%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22INFO%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.finch-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuZmluY2gtbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiQVdTX1BST0ZJTEUiOiJkZWZhdWx0IiwiQVdTX1JFR0lPTiI6InVzLXdlc3QtMiIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiSU5GTyJ9LCJ0cmFuc3BvcnRUeXBlIjoic3RkaW8iLCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Finch%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.finch-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22default%22%2C%22AWS_REGION%22%3A%22us-west-2%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22INFO%22%7D%2C%22transportType%22%3A%22stdio%22%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

MCP クライアントの設定で MCP サーバーを構成します。

#### デフォルトモード（読み取り専用 AWS リソース） {#default-mode-read-only-aws-resources}

デフォルトでは、サーバーは新しい AWS リソースの作成を防止するモードで実行されます。これは、リソースの作成を制限したい環境や、既存のリポジトリへのビルドとプッシュのみを許可すべきユーザーに便利です。

```json
{
  "mcpServers": {
    "awslabs.finch-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.finch-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-west-2",
        "FASTMCP_LOG_LEVEL": "INFO"
      },
      "transportType": "stdio",
      "disabled": false,
      "autoApprove": []
    }
  }
}
```
### Windows へのインストール {#windows-installation}

Windows ユーザーの場合、MCP サーバーの設定形式が若干異なります。

```json
{
  "mcpServers": {
    "awslabs.finch-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.finch-mcp-server@latest",
        "awslabs.finch-mcp-server.exe"
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


このデフォルトモードでは:
- `finch_build_container_image` ツールは通常どおり動作します
- `finch_create_ecr_repo` および `finch_push_image` ツールはエラーを返し、AWS リソースの作成や変更は行いません。

#### AWS リソース書き込みモード {#aws-resource-write-mode}

`--enable-aws-resource-write` フラグを使用することで、AWS リソースの作成と変更を有効にするようサーバーを設定することもできます。

```json
{
  "mcpServers": {
    "awslabs.finch-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.finch-mcp-server@latest",
        "--enable-aws-resource-write"
      ],
      "env": {
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-west-2",
        "FASTMCP_LOG_LEVEL": "INFO"
      },
      "transportType": "stdio",
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## 利用可能なツール {#available-tools}

### `finch_build_container_image` {#finch_build_container_image}

Finch を使用してコンテナイメージをビルドします。

このツールは、指定された Dockerfile とコンテキストディレクトリを使用して Docker イメージをビルドします。タグ、プラットフォームなど、さまざまなビルドオプションをサポートしています。

引数:
- `dockerfile_path` (str): Dockerfile への絶対パス
- `context_path` (str): ビルドコンテキストディレクトリへの絶対パス
- `tags` (List[str], オプション): イメージに適用するタグのリスト（例: ["myimage:latest", "myimage:v1"]）
- `platforms` (List[str], オプション): ターゲットプラットフォームのリスト（例: ["linux/amd64", "linux/arm64"]）
- `target` (str, オプション): ビルドするターゲットビルドステージ
- `no_cache` (bool, オプション): キャッシュを無効にするかどうか。デフォルトは False です。
- `pull` (bool, オプション): ベースイメージを常にプルするかどうか。デフォルトは False です。
- `build_contexts` (List[str], オプション): 追加のビルドコンテキストのリスト
- `outputs` (str, オプション): 出力先
- `cache_from` (List[str], オプション): 外部キャッシュソースのリスト
- `quiet` (bool, オプション): ビルド出力を抑制するかどうか。デフォルトは False です。
- `progress` (str, オプション): 進捗出力の種類。デフォルトは "auto" です。

### `finch_push_image` {#finch_push_image}

Finch を使用して、タグをイメージハッシュに置き換えてコンテナイメージをリポジトリにプッシュします。

イメージ URL が ECR リポジトリの場合、ECR ログイン認証ヘルパーが設定されていることを確認します。このツールはイメージハッシュを取得し、そのハッシュを使用して新しいタグを作成し、ハッシュタグ付きのイメージをリポジトリにプッシュします。

ワークフローは次のとおりです:
1. `finch image inspect` を使用してイメージハッシュを取得します
2. ハッシュの短縮形（先頭 12 文字）を使用してイメージの新しいタグを作成します
3. ハッシュタグ付きのイメージをリポジトリにプッシュします

引数:
- `image` (str): プッシュするイメージのフルネーム（リポジトリ URL とタグを含む）。ECR リポジトリの場合は、次の形式に従う必要があります: `<aws_account_id>.dkr.ecr.<region>.amazonaws.com/<repository_name>:<tag>`

例:
```
# Original image: myrepo/myimage:latest
# After processing: myrepo/myimage:1a2b3c4d5e6f (where 1a2b3c4d5e6f is the short hash)
```

### `finch_create_ecr_repo` {#finch_create_ecr_repo}

ECR リポジトリが存在するかどうかを確認し、存在しない場合は作成します。

このツールは、boto3 を使用して指定された ECR リポジトリが存在するかどうかを確認します。リポジトリが存在しない場合は、セキュリティ強化のためイミュータブルタグを設定した新しいリポジトリを指定の名前で作成します。このツールには、適切に設定された AWS 認証情報が必要です。

**注:** プッシュ時のスキャンオプションは、ユーザーが意図的に設定することを優先して、この MCP ツールでは無効になっています。

**注:** サーバーが読み取り専用モードで実行されている場合、このツールはエラーを返し、AWS リソースは一切作成しません。

引数:
- `app_name` (str): ECR で確認または作成するアプリケーション/リポジトリの名前
- `region` (str, オプション): ECR リポジトリの AWS リージョン。指定しない場合は、AWS 設定のデフォルトリージョンが使用されます

例:
```
# Check if 'my-app' repository exists in us-west-2 region, create it if it doesn't
{
  "app_name": "my-app",
  "region": "us-west-2"
}

# Response if repository already exists:
{
  "status": "success",
  "message": "ECR repository 'my-app' already exists.",
}

# Response if repository was created:
{
  "status": "success",
  "message": "Successfully created ECR repository 'my-app'.",
}

# Response if server is in readonly mode:
{
  "status": "error",
  "message": "Server running in read-only mode, unable to perform the action"
}
```

## ベストプラクティス {#best-practices}

- **開発およびプロトタイピング専用**: この MCP サーバーが提供するツールは、開発およびプロトタイピングの目的のみを想定しています。本番環境のユースケース向けではありません。
- **セキュリティに関する考慮事項**: イメージをビルドしてプッシュする前に、必ず Dockerfile とコンテナ設定を確認してください。
- **リソース管理**: ディスク容量を確保するため、未使用のイメージやコンテナを定期的にクリーンアップしてください。
- **バージョン管理**: 再現性を確保するため、イメージのバージョンとタグを記録・管理してください。
- **エラーハンドリング**: これらのツールを使用する際は、アプリケーションで適切なエラーハンドリングを実装してください。
- **ECR レジストリスキャン設定**: PutImageScanningConfiguration API は非推奨となり、レジストリレベルでイメージスキャン設定を指定する方式に移行しています。レジストリレベルのスキャンを設定するには、次の AWS CLI コマンドを使用します:
  ```bash
  aws ecr put-registry-scanning-configuration --scan-type ENHANCED --rules "[{\"scanFrequency\":\"SCAN_ON_PUSH\",\"repositoryFilters\":[{\"filter\":\"*\",\"filterType\":\"WILDCARD\"}]}]"
  ```
  詳細については、[ECR PutRegistryScanningConfiguration のドキュメント](https://docs.aws.amazon.com/AmazonECR/latest/APIReference/API_PutRegistryScanningConfiguration.html)を参照してください。


## ロギング {#logging}

Finch MCP サーバーは、操作のデバッグとモニタリングに役立つ包括的なロギング機能を提供します。

### ログの出力先 {#log-destinations}

デフォルトでは、サーバーは次の 2 つの出力先にログを記録します:
1. **stderr** - 標準エラー出力（MCP プロトコル標準に準拠）
2. **ファイル** - 詳細なデバッグのための永続的なログファイル

### ファイルロギング {#file-logging}

#### デフォルトのログ保存場所 {#default-log-location}

ログは、プラットフォーム固有のディレクトリに自動的に保存されます:
- **macOS/Linux**: `~/.finch/finch-mcp-server/finch_mcp_server.log`
- **Windows**: `%LOCALAPPDATA%\finch-mcp-server\finch_mcp_server.log`

#### カスタムログファイルの場所 {#custom-log-file-location}

`FINCH_MCP_LOG_FILE` 環境変数を使用して、カスタムログファイルのパスを指定できます:

```json
{
  "mcpServers": {
    "awslabs.finch-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.finch-mcp-server@latest"],
      "env": {
        "FINCH_MCP_LOG_FILE": "~/logs/finch-mcp-server.log"
      }
    }
  }
}
```

#### ファイルロギングの無効化 {#disable-file-logging}

stderr のみにログを記録する（厳密な MCP 標準に準拠する）には、ファイルロギングを無効にします:

```json
{
  "mcpServers": {
    "awslabs.finch-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.finch-mcp-server@latest"],
      "env": {
        "FINCH_DISABLE_FILE_LOGGING": "true"
      }
    }
  }
}
```

または、args 配列でコマンドライン引数を使用します:
```json
{
  "mcpServers": {
    "awslabs.finch-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.finch-mcp-server@latest",
        "--disable-file-logging"
      ]
    }
  }
}
```

### ログ機能 {#log-features}

#### 自動ログローテーション {#automatic-log-rotation}
- ログファイルは 10 MB を超えると自動的にローテーションされます
- 古いログは圧縮（gzip）され、7 日間保持されます
- これにより、巨大なログファイルによるディスク容量の問題を防止します

#### 機密データの保護 {#sensitive-data-protection}
ロギングシステムは、ログメッセージから機密情報を自動的にマスクします:
- AWS アクセスキーとシークレットキー
- API キー、パスワード、トークン
- JWT トークンと OAuth 認証情報
- 認証情報が埋め込まれた URL

#### ログ形式 {#log-format}
- **stderr**: `{time} | {level} | {message}`
- **ファイル**: `{time} | {level} | {name}:{function}:{line} | {message}`

ファイル形式には、詳細なデバッグのための追加コンテキスト（関数名と行番号）が含まれます。

### 設定例 {#example-configuration}

```json
{
  "mcpServers": {
    "awslabs.finch-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.finch-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "default",
        "AWS_REGION": "us-west-2",
        "FINCH_MCP_LOG_FILE": "~/logs/finch-mcp-server.log"
      }
    }
  }
}
```

## トラブルシューティング {#troubleshooting}

- ECR で権限エラーが発生した場合は、AWS 認証情報と boto3 の設定が正しくセットアップされているか確認してください
- Finch VM の問題については、手動で `finch vm stop` を実行してから `finch vm start` を実行してみてください
- ファイルが見つからないというエラーでビルドが失敗する場合は、コンテキストパスが正しいか確認してください
- Finch に関する一般的な問題については、[Finch のドキュメント](https://github.com/runfinch/finch)を参照してください
- **ログを確認する**: DEBUG レベルのロギングを有効にし、ログファイルで詳細なエラー情報を確認してください
- **ログファイルの権限**: ファイルロギングが失敗した場合、サーバーは stderr のみのロギングで動作を継続し、警告メッセージを表示します

## バージョン {#version}

現在の MCP サーバーバージョン: 0.1.0
