---
title: AWS Knowledge MCPサーバー
---

最新のドキュメント、コードサンプル、エージェントスキル、AWS APIおよびCloudFormationリソースのリージョン別提供状況に関する知識、その他のAWS公式コンテンツを提供する、フルマネージドのリモートMCPサーバーです。

このMCPサーバーは一般提供（GA）されています。

**重要な注意事項**: 現在、すべてのMCPクライアントがリモートサーバーに対応しているわけではありません。お使いのクライアントがリモートMCPサーバーをサポートしていること、または本サーバーを利用するための適切なプロキシ構成があることを確認してください。

### 主な機能 {#key-features}

- AWSドキュメント、APIリファレンス、トラブルシューティングガイドライン、アーキテクチャガイダンスへのリアルタイムアクセス
- クライアントホスト型サーバーと比べてローカルセットアップが少ない
- AIエージェント向けのAWSナレッジへの構造化されたアクセス
- AWS APIおよびCloudFormationリソースのリージョン別提供状況の情報
- Amplifyフレームワークのドキュメント、パターン、ベストプラクティスを含むフルスタック開発のガイダンス
- 最新のCDKおよびCloudFormationのドキュメント、ベストプラクティス、高品質なサンプルにアクセスでき、より良いInfrastructure as Code開発体験を実現
- Strands Agents SDKのドキュメント — Strands Agentsの全ドキュメント（ユーザーガイド、APIリファレンス、サンプルなど）の検索と閲覧
- エージェントスキルへのアクセス — AIエージェントをスペシャリストへと変えるドメイン特化の専門知識で、AWSの各ドメインに関するワークフロー、意思決定フレームワーク、ベストプラクティス、参考資料を提供

### AWS Knowledgeの機能 {#aws-knowledge-capabilities}

- **ベストプラクティス**: AWS APIやサービスの利用に関するベストプラクティスを発見できます
- **APIドキュメント**: 必須・任意のパラメータやフラグを含む、APIの呼び出し方法を学べます
- **入門情報**: ベストプラクティスに従いながらAWSサービスをすばやく使い始める方法を確認できます
- **最新情報**: 新しいAWSサービスや機能に関する最新の発表にアクセスできます
- **フルスタック開発**: フロントエンドとバックエンドの統合ガイダンスを通じて、AWS Amplifyを使った完全なアプリケーションの構築方法を学べます
- **Infrastructure as Code開発**: インフラストラクチャをコードでモデル化するための、最新のCDKおよびCloudFormationのガイダンス、ベストプラクティス、コード例にアクセスできます
- **Strands Agents SDK**: Strands Agents SDKでAIエージェントを構築するために、ユーザーガイド、APIリファレンス（Python & TypeScript）、サンプル、コミュニティコントリビューション、ブログ記事を含むStrands Agentsの全ドキュメントを検索・閲覧できます
- **エージェントスキル**: AIエージェントを特定のAWSドメインのスペシャリストへと変えるドメイン特化の専門知識パッケージで、デプロイ、トラブルシューティング、セキュリティ、最適化といった複雑なタスクのためのワークフロー、意思決定フレームワーク、ベストプラクティス、ステップバイステップの手順を提供します

### ツール {#tools}

1. `search_documentation`: すべてのAWSドキュメント、エージェントスキル、Strands Agents SDKドキュメントを横断検索します。トピックベースのフィルタリング（任意）により、より的を絞った結果を得られます
2. `read_documentation`: AWSドキュメントおよびStrands Agents（strandsagents.com）のページを取得し、markdownに変換します
3. `list_regions`: すべてのAWSリージョンの一覧を、識別子と名前を含めて取得します
4. `get_regional_availability`: サービス、機能、SDKサービスAPI、CloudFormationリソースに関するAWSのリージョン別提供状況の情報を取得します
5. `retrieve_skill`: AWSタスクに関するドメイン特化の専門知識、ワークフロー、ステップバイステップの手順を提供するAWSエージェントスキルを取得します

### 現在のナレッジソース {#current-knowledge-sources}

- 最新のAWSドキュメント
- APIリファレンス
- What's New投稿
- 入門（Getting Started）情報
- ブログ記事
- アーキテクチャリファレンス
- Well-Architectedガイダンス
- トラブルシューティングガイドとエラー解決策
- AWS Amplifyドキュメント
- CDKのドキュメント、CLIガイド、コンストラクト、パターン
- CloudFormationのテンプレートとリファレンス
- Strands Agents SDKドキュメント（ユーザーガイド、APIリファレンス、サンプル、コミュニティ、ブログ記事）
- AWSタスクドメイン向けのエージェントスキル

### 自然言語でAWSについて学ぶ {#learn-about-aws-with-natural-language}

- AWSのAPI、ベストプラクティス、新リリース、アーキテクチャガイダンスについて質問できます
- 複数のAWS情報ソースから即座に回答を得られます
- 包括的なガイダンスと情報を取得できます

## 設定 {#configuration}

Streamable HTTPトランスポート（HTTP）をサポートする任意のMCPクライアントで、次のURLを使用してKnowledge MCPサーバーを設定できます。

```url
https://knowledge-mcp.global.api.aws
```

**注:** 具体的な設定形式はMCPクライアントによって異なります。以下は[Kiro CLI](https://kiro.dev/)の例です。別のクライアントを使用している場合は、上記のURLを使ってリモートMCPサーバーを追加する方法について、お使いのクライアントのドキュメントを参照してください。

**Kiro CLI**

```json
{
  "mcpServers": {
    "aws-knowledge-mcp-server": {
      "url": "https://knowledge-mcp.global.api.aws",
      "type": "http",
      "disabled": false
    }
  }
}
```

お使いのクライアントがMCPのHTTPトランスポートをサポートしていない場合や、セットアップ中に問題が発生する場合は、[fastmcp](https://github.com/jlowin/fastmcp)ユーティリティを使用してstdioからHTTPトランスポートへプロキシできます。以下はfastmcpユーティリティの設定例です。

**fastmcp**

```json
{
  "mcpServers": {
    "aws-knowledge-mcp-server": {
      "command": "uvx",
      "args": ["fastmcp", "run", "https://knowledge-mcp.global.api.aws"]
    }
  }
}
```

### ワンクリックインストール {#one-click-installation}

|   IDE   |                                                                                                                                                   インストール                                                                                                                                                   |
| :-----: | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: |
|  Kiro   |                                                           [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=aws-knowledge-mcp&config=%7B%22url%22%3A%22https%3A//knowledge-mcp.global.api.aws%22%7D)                                                           |
| Cursor  |                                                [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=aws-knowledge-mcp&config=eyJ1cmwiOiJodHRwczovL2tub3dsZWRnZS1tY3AuZ2xvYmFsLmFwaS5hd3MifQ==)                                                 |
| VS Code | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://vscode.dev/redirect/mcp/install?name=aws-knowledge-mcp&config=%7B%22type%22%3A%22http%22%2C%22url%22%3A%22https%3A%2F%2Fknowledge-mcp.global.api.aws%22%7D) |

### MCPレジストリ {#mcp-registries}

AWS Knowledge MCPサーバーは、以下の公式MCPレジストリで利用できます。

- [Smithery](https://smithery.ai/server/@FaresYoussef94/aws-knowledge-mcp)
- [Cursor](https://cursor.directory/mcp/aws-knowledge-mcp-1)

インストールをさらに簡単にするため、追加のレジストリへの掲載にも積極的に取り組んでいます。

### テストとトラブルシューティング {#testing-and-troubleshooting}

LLMを介さずにKnowledge MCPサーバーを直接呼び出したい場合は、[MCP Inspector](https://github.com/modelcontextprotocol/inspector)ツールを使用できます。このツールは、任意のパラメータで`tools/list`や`tools/call`を実行できるUIを提供します。
次のコマンドでMCP Inspectorを起動できます。実行するとブラウザで開けるURLが出力されます。サーバーへの接続に問題がある場合は、ターミナルに表示されたURLを必ずクリックしてください。このURLにはMCP Inspectorを使用するためのセッショントークンが含まれています。

```
npx @modelcontextprotocol/inspector https://knowledge-mcp.global.api.aws
```

### AWS認証 {#aws-authentication}

Knowledge MCPサーバーは認証を必要としませんが、レート制限の対象となります。

### データの利用 {#data-usage}

AWS Knowledge MCPサーバーを通じて収集されたテレメトリーデータは、機械学習モデルのトレーニングや改善の目的には使用されません。

### よくある質問 {#faqs}

#### 1. ローカルのAWS Documentation MCPサーバーとリモートのAWS Knowledge MCPサーバーのどちらを使うべきですか？ {#1-should-i-use-the-local-aws-documentation-mcp-server-or-the-remote-aws-knowledge-mcp-server}

Knowledgeサーバーは、AWSドキュメントに加えて、What's New投稿、入門情報、ブログ記事、アーキテクチャリファレンス、Well-Architectedガイダンスなど、さまざまな情報ソースをインデックスしています。お使いのMCPクライアントがリモートサーバーをサポートしている場合は、Knowledge MCPサーバーを手軽に試して、ニーズに合うかどうかを確認できます。

#### 2. AWS Knowledge MCPサーバーを使うにはネットワークアクセスが必要ですか？ {#2-do-i-need-network-access-to-use-the-aws-knowledge-mcp-server}

はい。AWS Knowledge MCPサーバーにアクセスするには、パブリックインターネットへのアクセスが必要です。

#### 3. AWSアカウントは必要ですか？ {#3-do-i-need-an-aws-account}

いいえ。AWSアカウントがなくてもKnowledge MCPサーバーを使い始められます。Knowledge MCPは[AWSサイト利用規約](https://aws.amazon.com/terms/)の対象となります

#### 4. AWS上でのアプリケーション開発にAWS Knowledge MCPサーバーを使えますか？ {#4-can-i-use-the-aws-knowledge-mcp-server-for-application-development-on-aws}

はい。Knowledge MCPサーバーは、AWS Amplifyを使ったモバイル・Web・サーバーレスアプリケーション構築のガイダンス、Web（React/Vue/Angular）、モバイル（React Native/Android/Swift）、Flutter向けのフレームワーク別サンプル、そしてLambdaとAPI Gateway、Cognitoによる認証、AppSyncによるGraphQL、CodePipelineとAmplify HostingによるCI/CDパイプラインといった主要なAWSサービスのパターンを提供します。

#### 5. Infrastructure as Code開発にAWS Knowledge MCPサーバーを使えますか？ {#5-can-i-use-aws-knowledge-mcp-server-for-infrastructure-as-code-development}

はい。Knowledge MCPサーバーは、AWS CloudFormationおよびAWS CDK（Cloud Development Kit）向けの包括的なドキュメント、テンプレート、コード例を提供します。複数の言語にわたってAWSリソースをプログラムで定義・デプロイするためのガイダンスが見つかり、スケーラブルで保守しやすいインフラストラクチャ自動化の構築に役立ちます。

#### 6. AWS Management Consoleベースの開発にAWS Knowledge MCPサーバーを使えますか？ {#6-can-i-use-aws-knowledge-mcp-server-for-aws-management-console-based-development}

はい。Knowledge MCPサーバーは、AWS Management Consoleを通じてAWSサービスを直接設定・管理するためのガイダンスを提供します。サービスの機能を調べる場合でも、リソースを視覚的にセットアップする場合でも、サービスの仕組みを学ぶ場合でも、AWSのアプリケーションとインフラストラクチャを効果的に管理するために必要なリソースを提供します。

#### 7. エージェントスキルの取得にAWS Knowledge MCPサーバーを使えますか？ {#7-can-i-use-aws-knowledge-mcp-server-to-retrieve-agent-skills}

はい。Knowledge MCPサーバーは、エージェントスキル — AIエージェントを特定のAWSドメインのスペシャリストへと変えるドメイン特化の専門知識パッケージ — へのアクセスを提供します。スキルは、複雑なタスクのためのワークフロー、ベストプラクティス、意思決定フレームワーク、ステップバイステップの手順を提供します。`search_documentation`で`agent_skills`トピックを指定して検索することで利用可能なスキルを発見し、検索結果に含まれる正確な`skill_name`を指定して`retrieve_skill`ツールでスキル全体を読み込めます。スキルには参照ファイル（アーキテクチャドキュメント、スキーマ、サンプルなど）が含まれる場合もあり、任意の`file`パラメータを使って取得できます。

#### 8. Strands Agents SDKによるAIエージェント構築にAWS Knowledge MCPサーバーを使えますか？ {#8-can-i-use-aws-knowledge-mcp-server-for-building-ai-agents-with-the-strands-agents-sdk}

はい。Knowledge MCPサーバーは、Strands Agents SDKの全ドキュメント — ユーザーガイド、APIリファレンス（Python & TypeScript）、サンプル、コミュニティコントリビューション、ブログ記事 — をインデックスしています。`strands_docs`トピックで検索することも、自然に質問することもできます。アシスタントは、より詳しい情報のためにstrandsagents.comのページ全体をインラインで取得することもできます。
