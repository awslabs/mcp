---
title: "AWS Labs Amazon Kendra Index MCPサーバー"
---

Amazon Kendra 向けの AWS Labs Model Context Protocol (MCP) サーバーです。この MCP サーバーを使用すると、Kendra インデックスを RAG の追加コンテキストとして利用できます。

### 機能 {#features}

* 既存の MCP 対応チャットボットを追加の RAG インデックスで強化します
* Kiro、Cline、Cursor、Windsurf などのコーディングアシスタントの応答を強化します

### 前提条件 {#pre-requisites}

1. [AWS アカウントにサインアップする](https://aws.amazon.com/free/?trk=78b916d7-7c94-4cab-98d9-0ce5e648dd5f&sc_channel=ps&ef_id=Cj0KCQjwxJvBBhDuARIsAGUgNfjOZq8r2bH2OfcYfYTht5v5I1Bn0lBKiI2Ii71A8Gk39ZU5cwMLPkcaAo_CEALw_wcB:G:s&s_kwcid=AL!4422!3!432339156162!e!!g!!aws%20sign%20up!9572385111!102212379327&gad_campaignid=9572385111&gbraid=0AAAAADjHtp99c5A9DUyUaUQVhVEoi8of3&gclid=Cj0KCQjwxJvBBhDuARIsAGUgNfjOZq8r2bH2OfcYfYTht5v5I1Bn0lBKiI2Ii71A8Gk39ZU5cwMLPkcaAo_CEALw_wcB)
2. RAG 用ドキュメントを使用して [Amazon Kendra インデックスを作成する](https://docs.aws.amazon.com/kendra/latest/dg/create-index.html)
3. [Astral](https://docs.astral.sh/uv/getting-started/installation/) または [GitHub README](https://github.com/astral-sh/uv#installation) から `uv` をインストールする
4. `uv python install 3.10` を使用して Python をインストールする



### ツール {#tools}

#### KendraQueryTool {#kendraquerytool}

  - KendraQueryTool は、ユーザーが指定したクエリを受け取り、Kendra インデックスにクエリを実行して、応答のための追加コンテキストを取得します。デフォルトのインデックス、またはユーザーのプロンプトで指定されたインデックスのいずれかにクエリを実行します。
  - 必須パラメータ: query (str)
  - オプションパラメータ: indexId (str)、region (str)
  - 例:
    * `Can you help me understand how to implement a progress event in the CreateHandler using Java? Use the KendraQueryTool to gain additional context.`
    * `Can you use the test-kendra-index to help answer the following questions...`

#### KendraListIndexesTool {#kendralistindexestool}

  - KendraListIndexesTool は、アカウント内の Kendra インデックスを一覧表示します。デフォルトでは、mcp 設定ファイルに環境変数として指定されたリージョン内のすべてのインデックスを一覧表示します。それ以外の場合は、プロンプトでリージョンを指定できます。
  - オプションパラメータ: region (str)
  - 例:
    * `Can you list the Kendra Indexes in my account in the us-west-2 region`


## セットアップ {#setup}

### IAM の設定 {#iam-configuration}

1. AWS アカウントの IAM でユーザーをプロビジョニングします
2. 少なくとも `kendra:Query` と `kendra:ListIndices` の権限を含むポリシーをアタッチします。代わりに、AWS マネージドの `AmazonKendraFullAccess` ポリシーをアタッチすることもできます。ユーザーに権限を付与する際は、常に最小権限の原則に従ってください。Amazon Kendra の IAM 権限の詳細については、[ドキュメント](https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazonkendra.html)を参照してください。
3. 環境上で `aws configure` を使用して、認証情報（アクセス ID とアクセスキー）を設定します

### インストール {#installation}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.amazon-kendra-index-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-kendra-index-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%2C%22KEND_INDEX_ID%22%3A%22your-kendra-index-id%22%2C%22KEND_ROLE_ARN%22%3A%22your-kendra-role-arn%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.amazon-kendra-index-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYW1hem9uLWtlbmRyYS1pbmRleC1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJBV1NfUkVHSU9OIjoidXMtZWFzdC0xIiwiS0VORF9JTkRFWF9JRCI6InlvdXIta2VuZHJhLWluZGV4LWlkIiwiS0VORF9ST0xFX0FSTiI6InlvdXIta2VuZHJhLXJvbGUtYXJuIiwiRkFTVE1DUF9MT0dfTEVWRUwiOiJFUlJPUiJ9LCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Amazon%20Kendra%20Index%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-kendra-index-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%2C%22KEND_INDEX_ID%22%3A%22your-kendra-index-id%22%2C%22KEND_ROLE_ARN%22%3A%22your-kendra-role-arn%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

MCP クライアントの設定で MCP サーバーを設定します（例: Kiro の場合は `~/.kiro/settings/mcp.json` を編集します）:

```json
{
      "mcpServers": {
            "awslabs.amazon-kendra-index-mcp-server": {
                  "command": "uvx",
                  "args": ["awslabs.amazon-kendra-index-mcp-server"],
                  "env": {
                    "FASTMCP_LOG_LEVEL": "ERROR",
                    "KENDRA_INDEX_ID": "[Your Kendra Index Id]",
                    "AWS_PROFILE": "[Your AWS Profile Name]",
                    "AWS_REGION": "[Region where your Kendra Index resides]"
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
    "awslabs.amazon-kendra-index-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.amazon-kendra-index-mcp-server@latest",
        "awslabs.amazon-kendra-index-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "KENDRA_INDEX_ID": "[Your Kendra Index Id]",
        "AWS_PROFILE": "[Your AWS Profile Name]",
        "AWS_REGION": "[Region where your Kendra Index resides]"
      }
    }
  }
}
```

または、`docker build -t awslabs/amazon-kendra-index-mcp-server.` が成功した後に docker を使用します:

```file
# fictitious `.env` file with AWS temporary credentials
AWS_ACCESS_KEY_ID=<from the profile you set up>
AWS_SECRET_ACCESS_KEY=<from the profile you set up>
AWS_SESSION_TOKEN=<from the profile you set up>
```

```json
  {
    "mcpServers": {
      "awslabs.amazon-kendra-index-mcp-server": {
        "command": "docker",
        "args": [
          "run",
          "--rm",
          "--interactive",
          "--env-file",
          "/full/path/to/file/above/.env",
          "awslabs/amazon-kendra-index-mcp-server:latest"
        ],
        "env": {},
        "disabled": false,
        "autoApprove": []
      }
    }
  }
```
注: 認証情報はホスト側で継続的に更新しておく必要があります

## ベストプラクティス {#best-practices}

- IAM 権限を設定する際は最小権限の原則に従ってください
- 環境（開発、テスト、本番）ごとに別々の AWS プロファイルを使用してください
- パフォーマンスや問題を把握するために、ブローカーのメトリクスとログを監視してください
- クライアントアプリケーションに適切なエラーハンドリングを実装してください

## セキュリティに関する考慮事項 {#security-considerations}

この MCP サーバーを使用する際は、次の点を考慮してください:

- この MCP サーバーには、Amazon Kendra インデックスをクエリおよび一覧表示するための権限が必要です
- この MCP サーバーは、アカウント内のリソースを作成、変更、削除することはできません

## トラブルシューティング {#troubleshooting}

- 権限エラーが発生した場合は、IAM ユーザーに正しいポリシーがアタッチされているかを確認してください
- 接続の問題については、ネットワーク設定とセキュリティグループを確認してください
- リソースの変更がタグ検証エラーで失敗する場合、そのリソースは MCP サーバーによって作成されたものではないことを意味します
- Amazon Kendra に関する一般的な問題については、[Amazon Kendra 開発者ガイド](https://docs.aws.amazon.com/kendra/latest/dg/what-is-kendra.html)を参照してください

## バージョン {#version}

現在の MCP サーバーのバージョン: 0.0.0
