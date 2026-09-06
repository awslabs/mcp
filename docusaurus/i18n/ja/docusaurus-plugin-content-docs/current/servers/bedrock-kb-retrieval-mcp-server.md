---
title: "Amazon Bedrock ナレッジベース取得 MCPサーバー"
---

Amazon Bedrock ナレッジベースにアクセスするための MCP サーバーです。

## 機能 {#features}

### ナレッジベースとそのデータソースの探索 {#discover-knowledge-bases-and-their-data-sources}

- 利用可能なすべてのナレッジベースを検索して探索
- 名前またはタグでナレッジベースを検索
- 各ナレッジベースに関連付けられたデータソースを一覧表示

### 自然言語によるナレッジベースへのクエリ {#query-knowledge-bases-with-natural-language}

- 会話形式のクエリを使用して情報を取得
- ナレッジベースから関連するパッセージを取得
- すべての結果について引用情報にアクセス

### データソースによる結果のフィルタリング {#filter-results-by-data-source}

- 特定のデータソースにクエリを絞り込む
- 特定のデータソースを含めるか除外する
- 特定のデータソースからの結果を優先する

### 結果の再ランク付け {#rerank-results}

- 取得結果の関連性を向上
- Amazon Bedrock の再ランク付け機能を使用
- クエリとの関連性で結果を並べ替え

## 前提条件 {#prerequisites}

### インストール要件 {#installation-requirements}

1. [Astral](https://docs.astral.sh/uv/getting-started/installation/) または [GitHub README](https://github.com/astral-sh/uv#installation) から `uv` をインストールします
2. `uv python install 3.10` を使用して Python をインストールします

### AWS 要件 {#aws-requirements}

1. **AWS CLI の設定**: Amazon Bedrock およびナレッジベースへのアクセス権を持つ認証情報と AWS_PROFILE を用いて、AWS CLI が設定されている必要があります
2. **Amazon Bedrock ナレッジベース**: タグキー `mcp-multirag-kb` に値 `true` が設定された Amazon Bedrock ナレッジベースが少なくとも 1 つ必要です
3. **IAM 権限**: お使いの IAM ロール/ユーザーは、以下を実行するための適切な権限を持っている必要があります:
   - ナレッジベースの一覧表示と説明
   - データソースへのアクセス
   - ナレッジベースへのクエリ

### 再ランク付けの要件 {#reranking-requirements}

再ランク付け機能を使用する場合、お使いの Bedrock ナレッジベースには追加の権限が必要です:

1. お使いの IAM ロールには、`bedrock:Rerank` と `bedrock:InvokeModel` の両方のアクションに対する権限が必要です
2. Amazon Bedrock ナレッジベースのサービスロールにも、これらの権限が必要です
3. 再ランク付けは特定のリージョンでのみ利用可能です。サポートされているリージョンの最新の一覧については、公式の[ドキュメント](https://docs.aws.amazon.com/bedrock/latest/userguide/rerank-supported.html)を参照してください。
4. 指定したリージョンで、利用可能な再ランク付けモデルへのモデルアクセスを有効化してください。

### 再ランク付けの制御 {#controlling-reranking}

再ランク付けは、`BEDROCK_KB_RERANKING_ENABLED` 環境変数を使用してグローバルに有効化または無効化できます:

- `false`（デフォルト）に設定: 明示的に有効化されない限り、すべてのクエリで再ランク付けを無効化します
- `true` に設定: 明示的に無効化されない限り、すべてのクエリで再ランク付けを有効化します

この環境変数はさまざまな形式を受け付けます:

- 有効化する場合: 'true'、'1'、'yes'、または 'on'（大文字小文字を区別しません）
- 無効化する場合: それ以外の値、または未設定（デフォルトの動作）

この設定はグローバルなデフォルトを提供しますが、個々の API 呼び出しでは `reranking` パラメータを明示的に設定することで、これを上書きできます。

ナレッジベースのセットアップに関する詳細な手順については、以下を参照してください:

- [ナレッジベースの作成](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-create.html)
- [Amazon Bedrock ナレッジベースの権限の管理](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-prereq-permissions-general.html)
- [Amazon Bedrock における再ランク付けの権限](https://docs.aws.amazon.com/bedrock/latest/userguide/rerank-prereq.html)

## インストール {#installation}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.bedrock-kb-retrieval-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.bedrock-kb-retrieval-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-profile-name%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22KB_INCLUSION_TAG_KEY%22%3A%22optional-tag-key-to-filter-kbs%22%2C%22BEDROCK_KB_RERANKING_ENABLED%22%3A%22false%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.bedrock-kb-retrieval-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYmVkcm9jay1rYi1yZXRyaWV2YWwtbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiQVdTX1BST0ZJTEUiOiJ5b3VyLXByb2ZpbGUtbmFtZSIsIkFXU19SRUdJT04iOiJ1cy1lYXN0LTEiLCJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIiwiS0JfSU5DTFVTSU9OX1RBR19LRVkiOiJvcHRpb25hbC10YWcta2V5LXRvLWZpbHRlci1rYnMiLCJCRURST0NLX0tCX1JFUkFOS0lOR19FTkFCTEVEIjoiZmFsc2UifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Bedrock%20KB%20Retrieval%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.bedrock-kb-retrieval-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-profile-name%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%2C%22KB_INCLUSION_TAG_KEY%22%3A%22optional-tag-key-to-filter-kbs%22%2C%22BEDROCK_KB_RERANKING_ENABLED%22%3A%22false%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

MCP クライアントの設定で MCP サーバーを設定します（例: Kiro の場合は `~/.kiro/settings/mcp.json` を編集します）:

```json
{
  "mcpServers": {
    "awslabs.bedrock-kb-retrieval-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.bedrock-kb-retrieval-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-profile-name",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR",
        "KB_INCLUSION_TAG_KEY": "optional-tag-key-to-filter-kbs",
        "BEDROCK_KB_RERANKING_ENABLED": "false"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```
### Windows でのインストール {#windows-installation}

Windows ユーザーの場合、MCP サーバーの設定形式は少し異なります:

```json
{
  "mcpServers": {
    "awslabs.bedrock-kb-retrieval-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.bedrock-kb-retrieval-mcp-server@latest",
        "awslabs.bedrock-kb-retrieval-mcp-server.exe"
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


または、`docker build -t awslabs/bedrock-kb-retrieval-mcp-server .` が成功した後の docker で実行します:

```file
# fictitious `.env` file with AWS temporary credentials
AWS_ACCESS_KEY_ID=ASIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_SESSION_TOKEN=AQoEXAMPLEH4aoAH0gNCAPy...truncated...zrkuWJOgQs8IZZaIv2BXIa2R4Olgk
```

```json
  {
    "mcpServers": {
      "awslabs.bedrock-kb-retrieval-mcp-server": {
        "command": "docker",
        "args": [
          "run",
          "--rm",
          "--interactive",
          "--env",
          "FASTMCP_LOG_LEVEL=ERROR",
          "--env",
          "KB_INCLUSION_TAG_KEY=optional-tag-key-to-filter-kbs",
          "--env",
          "BEDROCK_KB_RERANKING_ENABLED=false",
          "--env",
          "AWS_REGION=us-east-1",
          "--env-file",
          "/full/path/to/file/above/.env",
          "awslabs/bedrock-kb-retrieval-mcp-server:latest"
        ],
        "env": {},
        "disabled": false,
        "autoApprove": []
      }
    }
  }
```

注意: 認証情報は、ホスト側から常に更新された状態に保つ必要があります

## 制限事項 {#limitations}

- `IMAGE` コンテンツタイプの結果は、KB クエリのレスポンスに含まれません。
- `reranking` パラメータには追加の権限と Amazon Bedrock のモデルアクセスが必要であり、特定のリージョンでのみ利用可能です。
