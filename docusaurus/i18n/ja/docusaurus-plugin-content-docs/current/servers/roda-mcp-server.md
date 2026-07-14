---
title: "Registry of Open Data on AWS (RODA) MCPサーバー"
---

[Registry of Open Data on AWS (RODA)](https://registry.opendata.aws/) のデータセットを検出・探索するための Model Context Protocol (MCP) サーバーです。Registry は、気候データ、ゲノミクス、衛星画像など、Amazon Simple Storage Service (S3) 上で公開されている数百のデータセットをホストしています。

## 機能 {#features}

- AWS 上の 1,000 以上のオープンデータセットからデータセットを検出
- キーワード、組織、ライセンス、トピックによる自然言語での検索
- 関連データセットの検索とドメイン別の探索
- ライセンス情報を常に表示
- 早期評価のためのデータセットのプレビューとサンプリング
- データセットへのアクセス方法に関する厳選された次のステップ
- アクセス制御のない公開データセットの場合:
  - S3 バケット構造のプレビュー
  - 会話内でのファイルの直接サンプリング

## 基本的な使い方 {#basic-usage}

AI アシスタントに自然言語で質問してください:
  * 「AWS 上にはどのようなオープンデータがありますか?」
  * 「地表面温度に関連するデータセットを見せてください。」
  * 「1000 Genomes の詳細を教えてください。」
  * 「CHIRPS のファイル構造をプレビューして、ファイルをサンプリングしてください。」

MCP サーバーの使い方のさらなる例については、[Example Usage](https://github.com/awslabs/mcp/blob/main/src/roda-mcp-server/examples/example_usage.md) をご覧ください。

> [!NOTE]
> RODA 上の各データセットには固有のライセンス条項があります。データにアクセスまたは使用する前に、必ず確認してください。

## 前提条件 {#prerequisites}

1. [Astral](https://docs.astral.sh/uv/getting-started/installation/) から `uv` をインストールすること
1. `uv python install 3.10` を使用して Python 3.10 以降をインストールすること


## 利用可能なツール {#available-tools}

| ツール | 説明 |
|------|-------------|
| `search_datasets` | タグ、組織、ライセンスタイプのオプションフィルター付きでキーワード検索を行います |
| `list_datasets` | オプションのタグフィルタリング付きですべてのデータセットを一覧表示します |
| `get_dataset_details` | リソースやアクセス情報を含む、特定のデータセットの完全な詳細を取得します |
| `discover_by_organization` | 特定の組織（例: NASA、NOAA）が管理するデータセットを検索します |
| `discover_by_license` | ライセンスタイプ（例: Creative Commons、MIT）でデータセットを検索します |
| `find_related_datasets` | 共有タグに基づいて、指定したデータセットに関連するデータセットを検索します |
| `get_knowledge_base_stats` | 上位のタグ、組織、リソースタイプを含むレジストリの統計情報を取得します |
| `preview_dataset` | データセットの S3 バケット構造を表示します（ダウンロード不要、AWS アカウント不要）。これはアクセス制御のない公開データセットでのみ利用できます。データセットをプレビューする前に、データセットのライセンスを確認し同意する必要があります。|
| `sample_dataset` | 公開データセットの S3 バケットから特定のファイルの先頭 100KB を読み取ります。これはアクセス制御のない公開データセットでのみ利用できます。データセットをサンプリングする前に、データセットのライセンスを確認し同意する必要があります。|
| `search_stac_endpoints` | STAC (SpatioTemporal Asset Catalog) API エンドポイントを持つデータセットを検索します |

Registry 上のデータセットは、さまざまなコンプライアンス上の理由により、3 つのアクセス階層に分かれています:
- オープンかつ無料。公開 S3 バケットでホストされており、利用に AWS アカウントは不要
- オープンだが、AWS 認証情報とリクエスタ支払い（requester pays）が必要
- アクセス制御あり。特にヘルスケア分野に多く、データセットへのアクセスには追加の手順が必要

オープンかつ無料のデータセットについては、ユーザーがデータセットを迅速に評価できるよう、S3 バケットのプレビューとファイルのサンプリング機能を提供しています。その他のデータセットについては、データセットへのアクセス方法に関する手順をユーザーに提供します。

この MCP サーバーの設計について詳しくは、[High-Level Design](https://github.com/awslabs/mcp/blob/main/src/roda-mcp-server/docs/high-level-design.md) をご覧ください。

## セットアップ {#setup}

### uv を使用する場合 {#using-uv}

MCP クライアントの設定で MCP サーバーを構成します（例: Kiro の場合は `~/.kiro/settings/mcp.json` を編集します）:

**Linux/MacOS ユーザーの場合:**

```json
{
  "mcpServers": {
    "awslabs.roda-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.roda-mcp-server@latest"
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

**Windows ユーザーの場合:**

```json
{
  "mcpServers": {
    "awslabs.roda-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.roda-mcp-server@latest",
        "awslabs.roda-mcp-server.exe"
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
### Claude Code CLI を使用する場合 {#using-claude-code-cli}

```
# Add RODA MCP
claude mcp add roda-mcp uvx awslabs.roda-mcp-server@latest

# List installed server
claude mcp list
```


## セキュリティ {#security}
この MCP サーバーに関するセキュリティ上の考慮事項については、[Security](https://github.com/awslabs/mcp/blob/main/src/roda-mcp-server/SECURITY.md) をご覧ください。

## ライセンス {#license}
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

Apache License, Version 2.0（以下「ライセンス」）に基づいてライセンスされています。


## 免責事項 {#disclaimer}
この roda-mcp-server パッケージは、明示または黙示を問わずいかなる種類の保証もなく「現状のまま」提供されており、開発、テスト、および評価の目的のみを意図しています。当社は、このパッケージの品質、性能、または信頼性についていかなる保証も提供しません。LLM は非決定的であり、間違いを犯すことがあります。顧客向けアカウントでこれらのツールを使用する前に、必ず十分にテストし、組織のベストプラクティスに従うことをお勧めします。このパッケージのユーザーは、適切なセキュリティ管理を実装する責任を単独で負い、AWS リソースへのアクセスを管理するために AWS Identity and Access Management (IAM) を使用しなければなりません（MUST）。適切な IAM ポリシー、ロール、および権限を設定する責任はユーザーにあり、不適切な IAM 設定に起因するセキュリティ上の脆弱性はすべてユーザーの単独の責任となります。このパッケージを使用することにより、ユーザーは本免責事項を読み理解したこと、および自己の責任においてパッケージを使用することに同意したものとみなされます。
