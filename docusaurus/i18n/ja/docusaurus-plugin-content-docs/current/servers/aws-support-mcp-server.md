---
title: "AWS Support MCPサーバー"
---

AWS Support API と連携するための Model Context Protocol (MCP) サーバー実装です。このサーバーにより、AI アシスタントがプログラムから AWS サポートケースを作成・管理できるようになります。

## 機能 {#features}

- AWS サポートケースの作成と管理
- ケース情報と全コミュニケーション履歴の取得
- 既存ケースへのコミュニケーションの追加（添付ファイル対応）
- サポートケースの解決
- 二重エンコード保護付きの添付ファイルのアップロードとダウンロード
- ケース作成前に有効なサービスコード、カテゴリコード、重大度レベル、言語を確認
- サービスごとに利用可能なケース作成オプションの閲覧

## 利用可能なツール {#available-tools}

| ツール | 説明 |
|------|-------------|
| `create_support_case` | 新しいサポートケースを作成します |
| `describe_support_cases` | 既存ケースの一覧表示・検索を行います |
| `describe_communications` | ケースの全コミュニケーション履歴を取得します |
| `add_communication_to_case` | ケースに返信します（添付ファイルはオプション） |
| `resolve_support_case` | ケースをクローズします |
| `describe_services` | AWS サービスとカテゴリコードを一覧表示します |
| `describe_severity_levels` | 重大度レベルを一覧表示します |
| `describe_create_case_options` | サービスに対して有効なカテゴリと重大度を取得します |
| `describe_supported_languages` | サポートされている言語を一覧表示します |
| `add_attachments_to_set` | ケースに添付するファイルをアップロードします |
| `describe_attachment` | ID を指定して添付ファイルをダウンロードします |


## 要件 {#requirements}

- Python 3.7 以上
- Support API へのアクセス権を持つ AWS 認証情報
- Business、Enterprise On-Ramp、または Enterprise サポートプラン

## 前提条件 {#prerequisites}

1. [Astral](https://docs.astral.sh/uv/getting-started/installation/) または [GitHub README](https://github.com/astral-sh/uv#installation) の手順に従って `uv` をインストールします
2. `uv python install 3.10` を使用して Python をインストールします

## インストール {#installation}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs_support_mcp_server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22-m%22%2C%22awslabs.aws-support-mcp-server%40latest%22%2C%22--debug%22%2C%22--log-file%22%2C%22./logs/mcp_support_server.log%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs_support_mcp_server&config=eyJjb21tYW5kIjoidXZ4IC1tIGF3c2xhYnMuYXdzLXN1cHBvcnQtbWNwLXNlcnZlckBsYXRlc3QgLS1kZWJ1ZyAtLWxvZy1maWxlIC4vbG9ncy9tY3Bfc3VwcG9ydF9zZXJ2ZXIubG9nIiwiZW52Ijp7IkFXU19QUk9GSUxFIjoieW91ci1hd3MtcHJvZmlsZSJ9fQ%3D%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20Support%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22-m%22%2C%22awslabs.aws-support-mcp-server%40latest%22%2C%22--debug%22%2C%22--log-file%22%2C%22.%2Flogs%2Fmcp_support_server.log%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%7D%7D) |

MCP クライアントの設定で MCP サーバーを構成します（例: Kiro の場合は `~/.kiro/settings/mcp.json` を編集します）:

```json

{
   "mcpServers": {
      "awslabs_support_mcp_server": {
         "command": "uvx",
         "args": [
            "-m", "awslabs.aws-support-mcp-server@latest",
            "--debug",
            "--log-file",
            "./logs/mcp_support_server.log"
         ],
         "env": {
            "AWS_PROFILE": "your-aws-profile"
         }
      }
   }
}
```

または:
```bash


uv pip install -e .
uv run awslabs/aws_support_mcp_server/server.py
```

```json
{
   "mcpServers": {
      "awslabs_support_mcp_server": {
         "command": "path-to-python",
         "args": [
            "-m",
            "awslabs.aws_support_mcp_server.server",
            "--debug",
            "--log-file",
            "./logs/mcp_support_server.log"
         ],
         "env": {
            "AWS_PROFILE": "manual_enterprise"
         }
      }
   }
}
```

### Windows でのインストール {#windows-installation}

Windows ユーザーの場合、MCP サーバーの設定形式が少し異なります:

```json
{
  "mcpServers": {
    "awslabs.aws-support-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.aws-support-mcp-server@latest",
        "awslabs.aws-support-mcp-server.exe"
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

## 使い方 {#usage}

サーバーを起動します:

```bash
python -m awslabs.aws_support_mcp_server.server [options]
```

オプション:
- `--port PORT`: サーバーを実行するポート（デフォルト: 8888）
- `--debug`: デバッグログを有効にします
- `--log-file`: ログファイルの保存先

## 設定 {#configuration}

サーバーは環境変数を使用して設定できます:

- `AWS_REGION`: AWS リージョン（デフォルト: us-east-1）
- `AWS_PROFILE`: AWS 認証情報のプロファイル名

## ドキュメント {#documentation}

利用可能なツールとリソースの詳細なドキュメントについては、[API ドキュメント](https://github.com/awslabs/mcp/blob/main/src/aws-support-mcp-server/docs/api.md)を参照してください。



## ライセンス {#license}

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License").
