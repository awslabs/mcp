---
title: "Amazon Q Business 匿名モード MCPサーバー"
---

Amazon Q Business の匿名モードアプリケーション向けの AWS Labs Model Context Protocol (MCP) サーバーです。これは Amazon Q Business 向けのシンプルな MCP サーバーで、[匿名モードアクセス](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/create-anonymous-application.html)を使用して作成された Amazon Q Business アプリケーションをサポートします。この MCP サーバーを使用して、匿名モードで作成された Amazon Q Business アプリケーションにクエリを実行し、そこに取り込んだコンテンツに基づいた応答を取得します。

## 機能 {#features}
- [x] この MCP サーバーはローカルマシンから使用できます
- [x] 匿名モードで作成された Amazon Q Business アプリケーションにクエリを実行し、そこに取り込んだコンテンツに基づいた応答を取得します

## 前提条件 {#prerequisites}

1. [AWS アカウントにサインアップする](https://aws.amazon.com/free/?trk=78b916d7-7c94-4cab-98d9-0ce5e648dd5f&sc_channel=ps&ef_id=Cj0KCQjwxJvBBhDuARIsAGUgNfjOZq8r2bH2OfcYfYTht5v5I1Bn0lBKiI2Ii71A8Gk39ZU5cwMLPkcaAo_CEALw_wcB:G:s&s_kwcid=AL!4422!3!432339156162!e!!g!!aws%20sign%20up!9572385111!102212379327&gad_campaignid=9572385111&gbraid=0AAAAADjHtp99c5A9DUyUaUQVhVEoi8of3&gclid=Cj0KCQjwxJvBBhDuARIsAGUgNfjOZq8r2bH2OfcYfYTht5v5I1Bn0lBKiI2Ii71A8Gk39ZU5cwMLPkcaAo_CEALw_wcB)
2. [匿名モードを使用して Amazon Q Business アプリケーションを作成する](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/create-anonymous-application.html)
3. [Astral](https://docs.astral.sh/uv/getting-started/installation/) または [GitHub README](https://github.com/astral-sh/uv#installation) から `uv` をインストールする
4. `uv python install 3.10` を使用して Python をインストールする

## ツール {#tools}
#### QBusinessQueryTool {#qbusinessquerytool}

- QBusinessQueryTool は、ユーザーが指定したクエリを受け取り、Amazon Q Business アプリケーションに対してクエリを実行して応答を取得します。
- 必須パラメータ: query(str)
- 例:
    * `Can you get me the details of the ACME project? Use the QBusinessQueryTool to get the context.`。この場合、ACME の詳細情報は、匿名モードで作成された基盤となる Amazon Q Business アプリケーションに取り込まれている必要があります。

## セットアップ {#setup}

### IAM の設定 {#iam-configuration}

1. AWS アカウントの IAM でユーザーをプロビジョニングする
2. 最低限 `qbusiness:ChatSync` 権限を含むポリシーをアタッチする。ユーザーに権限を付与する際は、常に最小権限の原則に従ってください。Amazon Q Business の IAM 権限に関する詳細については、[ドキュメント](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/security_iam_id-based-policy-examples.html#security_iam_id-based-policy-examples-application-1)を参照してください。
3. 環境で `aws configure` を使用して認証情報（アクセス ID とアクセスキー）を設定する

### インストール {#installation}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.amazon-qbusiness-anonymous-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-qbusiness-anonymous-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22QBUSINESS_APP_ID%22%3A%22your-qbusiness-app-id%22%2C%22QBUSINESS_USER_ID%22%3A%22your-user-id%22%2C%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.amazon-qbusiness-anonymous-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYW1hem9uLXFidXNpbmVzcy1hbm9ueW1vdXMtbWNwLXNlcnZlckBsYXRlc3QiLCJlbnYiOnsiUUJVU0lORVNTX0FQUF9JRCI6InlvdXItcWJ1c2luZXNzLWFwcC1pZCIsIlFCVVNJTkVTU19VU0VSX0lEIjoieW91ci11c2VyLWlkIiwiQVdTX1BST0ZJTEUiOiJ5b3VyLWF3cy1wcm9maWxlIiwiQVdTX1JFR0lPTiI6InVzLWVhc3QtMSIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Amazon%20Q%20Business%20Anonymous%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.amazon-qbusiness-anonymous-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22QBUSINESS_APP_ID%22%3A%22your-qbusiness-app-id%22%2C%22QBUSINESS_USER_ID%22%3A%22your-user-id%22%2C%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

MCP クライアントの設定で MCP サーバーを構成します（例: Kiro の場合は `~/.kiro/settings/mcp.json` を編集します）。

```json
{
      "mcpServers": {
            "awslabs.amazon-qbusiness-anonymous-mcp-server": {
                  "command": "uvx",
                  "args": ["awslabs.qbusiness-anonymous-mcp-server"],
                  "env": {
                    "FASTMCP_LOG_LEVEL": "ERROR",
                    "QBUSINESS_APPLICATION_ID": "[Your Amazon Q Business application id]",
                    "AWS_PROFILE": "[Your AWS Profile Name]",
                    "AWS_REGION": "[Region where your Amazon Q Business application resides]"
                  },
                  "disabled": false,
                  "autoApprove": []
                }
      }
}
```
### Windows でのインストール {#windows-installation}

Windows ユーザーの場合、MCP サーバーの設定形式は少し異なります。

```json
{
  "mcpServers": {
    "awslabs.amazon-qbusiness-anonymous-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.amazon-qbusiness-anonymous-mcp-server@latest",
        "awslabs.amazon-qbusiness-anonymous-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "QBUSINESS_APPLICATION_ID": "[Your Amazon Q Business application id]",
        "AWS_PROFILE": "[Your AWS Profile Name]",
        "AWS_REGION": "[Region where your Amazon Q Business application resides]"
      },
    }
  }
}
```

または、`docker build -t awslabs/amazon-kendra-index-mcp-server.` が成功した後に docker を使用します。

```file
# fictitious `.env` file with AWS temporary credentials
AWS_ACCESS_KEY_ID=<from the profile you set up>
AWS_SECRET_ACCESS_KEY=<from the profile you set up>
AWS_SESSION_TOKEN=<from the profile you set up>
```

```json
  {
    "mcpServers": {
      "awslabs.amazon-qbusiness-anonymous-mcp-server": {
        "command": "docker",
        "args": [
          "run",
          "--rm",
          "--interactive",
          "--env-file",
          "/full/path/to/file/above/.env",
          "awslabs/amazon-qbusiness-anonymous-mcp-server:latest"
        ],
        "env": {},
        "disabled": false,
        "autoApprove": []
      }
    }
  }
```
注意: 認証情報はホスト側で更新し続ける必要があります。

## ベストプラクティス {#best-practices}

- IAM 権限を設定する際は、最小権限の原則に従う
- 環境（dev、test、prod）ごとに個別の AWS プロファイルを使用する
- パフォーマンスや問題を把握するために、ブローカーのメトリクスとログを監視する
- クライアントアプリケーションで適切なエラーハンドリングを実装する

## セキュリティに関する考慮事項 {#security-considerations}

この MCP サーバーを使用する際は、以下を考慮してください。

- この MCP サーバーには、匿名モードで作成された Amazon Q Business アプリケーションで会話 API を使用するための権限が必要です。
- この MCP サーバーは、アカウント内のリソースを作成、変更、削除することはできません。

## トラブルシューティング {#troubleshooting}

- 権限エラーが発生した場合は、IAM ユーザーに正しいポリシーがアタッチされているか確認してください
- 接続に関する問題が発生した場合は、ネットワーク設定とセキュリティグループを確認してください
- リソースの変更がタグ検証エラーで失敗する場合は、そのリソースが MCP サーバーによって作成されたものではないことを意味します
- Amazon Q Business に関する一般的な問題については、[Amazon Q Business ユーザーガイド](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/what-is.html)を参照してください

## バージョン {#version}

現在の MCP サーバーバージョン: 0.0.0
