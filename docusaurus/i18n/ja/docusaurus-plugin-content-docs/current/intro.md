---
slug: /
title: AWS向けオープンソースMCPサーバーへようこそ
---

import styles from '@site/src/components/ServerCards/styles.module.css';

# AWS向けオープンソースMCPサーバーへようこそ

AWS向けオープンソースMCPサーバーを使い始めて、主要な機能を学びましょう。

AWS向けオープンソースMCPサーバーは、MCPを利用できるあらゆる場所でAWSを最大限に活用できるようにする、専門化されたMCPサーバー群です。

## Model Context Protocol(MCP)とは何か、AWS向けMCPサーバーとどう連携するのか

> Model Context Protocol(MCP)は、LLMアプリケーションと外部のデータソースやツールとのシームレスな統合を可能にするオープンプロトコルです。AIを活用したIDEの構築、チャットインターフェースの拡張、カスタムAIワークフローの作成など、どのような用途でも、MCPはLLMが必要とするコンテキストと接続するための標準化された方法を提供します。
>
> &mdash; [Model Context Protocol README](https://github.com/modelcontextprotocol#:~:text=The%20Model%20Context,context%20they%20need.)

MCPサーバーは、標準化されたModel Context Protocolを通じて特定の機能を公開する軽量なプログラムです。ホストアプリケーション(チャットボット、IDE、その他のAIツールなど)は、MCPサーバーと1対1の接続を維持するMCPクライアントを備えています。代表的なMCPクライアントには、エージェント型AIコーディングアシスタント(Kiro、Cline、Cursor、Windsurfなど)やClaude Desktopのようなチャットボットアプリケーションがあり、今後さらに多くのクライアントが登場する予定です。MCPサーバーはローカルのデータソースやリモートサービスにアクセスして追加のコンテキストを提供し、モデルが生成する出力の品質を向上させます。

AWS向けMCPサーバーはこのプロトコルを使用して、AIアプリケーションにAWSドキュメント、コンテキストに応じたガイダンス、ベストプラクティスへのアクセスを提供します。標準化されたMCPクライアント・サーバーアーキテクチャを通じて、AWSの機能が開発環境やAIアプリケーションのインテリジェントな拡張となります。

AWS向けMCPサーバーは、クラウドネイティブ開発、インフラストラクチャ管理、開発ワークフローを強化し、AI支援によるクラウドコンピューティングをより身近で効率的なものにします。

Model Context ProtocolはAnthropic, PBC.が運営するオープンソースプロジェクトであり、コミュニティ全体からのコントリビューションを受け付けています。MCPの詳細については、[こちらのドキュメント](https://modelcontextprotocol.io/introduction)を参照してください。

## なぜAWS向けMCPサーバーなのか

MCPサーバーは、基盤モデル(FM)の能力を以下の重要な点で強化します:

- **出力品質の向上**: 関連情報をモデルのコンテキストに直接提供することで、MCPサーバーはAWSサービスのような専門領域におけるモデルの応答を大幅に改善します。このアプローチにより、ハルシネーションが減り、より正確な技術的詳細が提供され、より精度の高いコード生成が可能になり、最新のAWSベストプラクティスやサービス機能に沿った推奨が保証されます。

- **最新ドキュメントへのアクセス**: FMは最近のリリース、API、SDKに関する知識を持っていない場合があります。MCPサーバーは最新のドキュメントを取り込むことでこのギャップを埋め、AIアシスタントが常に最新のAWS機能を扱えるようにします。

- **ワークフローの自動化**: MCPサーバーは、一般的なワークフローを基盤モデルが直接使用できるツールに変換します。CDK、Terraform、その他のAWS固有のワークフローなど、これらのツールによりAIアシスタントは複雑なタスクをより正確かつ効率的に実行できます。

- **専門的なドメイン知識**: MCPサーバーは、基盤モデルの学習データでは十分にカバーされていない可能性のあるAWSサービスに関する深いコンテキスト知識を提供し、クラウド開発タスクに対してより正確で有用な応答を可能にします。

## はじめるための基本

<div style={{
  background: '#F9FAFB',
  border: '1px solid #E5E7EB',
  borderLeft: '4px solid #0078D4',
  padding: '1.25rem',
  marginBottom: '2rem',
  borderRadius: '4px',
  display: 'flex',
  alignItems: 'center',
  gap: '1rem'
}}>

  <div>
    <div style={{ fontWeight: 600, color: '#111827', marginBottom: '0.25rem' }}>AWS re:Invent 2025の新発表!</div>
    <div style={{ color: '#6B7280', fontSize: '0.875rem' }}>AWSリソース管理に不可欠なMCPサーバー</div>
  </div>
</div>

個別のAWSサービスに進む前に、AWSリソースを扱うための基本となる以下のMCPサーバーをセットアップしましょう:

<div className={styles.cardGrid}>
  <a href="https://docs.aws.amazon.com/aws-mcp/latest/userguide/what-is-mcp-server.html" className={styles.serverCardLink}>
    <div className={styles.serverCard} style={{ height: 'auto', maxWidth: '100%' }}>
      <div className={styles.serverCardHeader}>
        <div className={styles.serverCardIcon}>
          <img src="/mcp/assets/icons/key.svg" alt="API icon" style={{ width: '22px', height: '22px' }} />
        </div>
        <div className={styles.serverCardTitleSection}>
          <h3 className={styles.serverCardTitle}>AWS MCP(プレビュー版)</h3>
          <div className={styles.serverCardTags}>
            <span className={styles.serverCardCategory}>必須セットアップ</span>
          </div>
        </div>
      </div>
      <div className={styles.serverCardContent} style={{ overflow: 'visible' }}>
        <p className={styles.serverCardDescription} style={{ height: 'auto', overflow: 'visible', display: 'block', WebkitBoxOrient: 'initial', WebkitLineClamp: 'unset', marginBottom: '0', marginLeft: '0', marginTop: '0' }}>
          安全で監査可能なAWS操作はここから始めましょう!このリモートマネージドMCPサーバーはAWSがホストしており、包括的なAWS APIサポートに加え、最新のAWSドキュメント、APIリファレンス、What's New投稿、Getting Started情報へのアクセスを提供します。AWSのベストプラクティスに従った事前構築済みのAgent SOPを備えており、エージェントが複雑な複数ステップのAWSタスクを確実に完了できるよう支援します。安全性と制御を重視した設計:構文検証済みのAPI呼び出し、認証情報を一切露出しないIAMベースの権限管理、CloudTrailによる完全な監査ログ。インフラストラクチャの管理、リソースの探索、AWS操作の実行を、完全な透明性とトレーサビリティのもとで、すべてのAWSサービスに対して行えます。
        </p>
        <div style={{
          display: 'flex',
          flexDirection: 'row',
          gap: '0.5rem',
          flexWrap: 'wrap',
          marginTop: '0.5rem'
        }}>
          <a href="https://kiro.dev/launch/mcp/add?name=aws-mcp&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22mcp-proxy-for-aws%40latest%22%2C%22https%3A//aws-mcp.us-east-1.api.aws/mcp%22%5D%7D" target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()}>
            <img src="https://img.shields.io/badge/Install-Kiro-9046FF?style=flat-square&logo=kiro" alt="Install on Kiro" />
          </a>
          <a href="https://cursor.com/en-US/install-mcp?name=aws-mcp&config=eyJjb21tYW5kIjoidXZ4IG1jcC1wcm94eS1mb3ItYXdzQGxhdGVzdCBodHRwczovL2F3cy1tY3AudXMtZWFzdC0xLmFwaS5hd3MvbWNwIn0%3D" target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()}>
            <img src="https://img.shields.io/badge/Install-Cursor-blue?style=flat-square&logo=cursor" alt="Install on Cursor" />
          </a>
          <a href="https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22mcp-proxy-for-aws%40latest%22%2C%22https%3A%2F%2Faws-mcp.us-east-1.api.aws%2Fmcp%22%5D%7D" target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()}>
            <img src="https://img.shields.io/badge/Install-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white" alt="Install on VS Code" />
          </a>
        </div>
      </div>
    </div>
  </a>
</div>

## 利用可能なAWS向けMCPサーバー

サーバーは以下の主要カテゴリに分類されています:

- **🚀 Essential**: AWSが完全に管理する公式AWS MCPサーバー
- **⚡  Core**: 幅広いAWSアクセスとタスクオーケストレーションのための柔軟なオープンソースサーバー
- **📚 ドキュメント**: 公式AWSドキュメントへのリアルタイムアクセス
- **🏗️ インフラストラクチャとデプロイ**: クラウドインフラストラクチャの構築、デプロイ、管理
- **🤖 AIと機械学習**: 知識検索とML機能によるAIアプリケーションの強化
- **📊 データと分析**: データベース、キャッシュシステム、データ処理の操作
- **🛠️ 開発者ツールとサポート**: コード分析とテストユーティリティによる開発の加速
- **📡 統合とメッセージング**: メッセージング、ワークフロー、位置情報サービスによるシステム連携
- **💰 コストと運用**: AWSインフラストラクチャとコストの監視、最適化、管理
- **🧬 ヘルスケアとライフサイエンス**: AWS HealthAIサービスとの連携

import ServerCards from '@site/src/components/ServerCards';

<ServerCards />

## ローカルMCPサーバーとリモートMCPサーバーの使い分け

AWS向けMCPサーバーは、開発マシン上でローカルに実行することも、クラウド上でリモートに実行することもできます。それぞれの使いどころは以下のとおりです:

### ローカルMCPサーバー
- **開発とテスト**: ローカルでの開発、テスト、デバッグに最適
- **オフライン作業**: インターネット接続が限られていても作業を継続可能
- **データプライバシー**: 機密データや認証情報をローカルマシン内に保持
- **低レイテンシー**: ネットワークのオーバーヘッドが最小限で応答が高速
- **リソース制御**: サーバーのリソースと設定を直接制御可能

### リモートMCPサーバー
- **チームコラボレーション**: チーム全体で一貫したサーバー設定を共有
- **リソース集約型タスク**: 重い処理を専用のクラウドリソースにオフロード
- **常時利用可能**: どこからでも、どのデバイスからでもMCPサーバーにアクセス
- **自動アップデート**: 最新の機能とセキュリティパッチを自動的に取得
- **スケーラビリティ**: ローカルリソースの制約なしに変動するワークロードに容易に対応
- **セキュリティ**: IAMベースの権限管理と認証情報の非露出による一元的なセキュリティ制御
- **ガバナンス**: エンタープライズレベルのガバナンスのための包括的な監査ログとコンプライアンス監視

> **注**: [公式AWS MCPサーバー](https://docs.aws.amazon.com/aws-mcp/latest/userguide/what-is-mcp-server.html)(プレビュー版)やAWS Knowledge MCPなど、一部のMCPサーバーはAWSがフルマネージドサービスとして提供しています。これらのAWSマネージドリモートサーバーは、セットアップやインフラストラクチャの管理が一切不要で、接続するだけですぐに使い始められます。

## ワークフロー

各サーバーは特定のユースケース向けに設計されています:

- **👨‍💻 バイブコーディングと開発**: より速い開発を支援するAIコーディングアシスタント
- **💬 会話型アシスタント**: 顧客向けチャットボットやインタラクティブなQ&Aシステム
- **🤖 自律型バックグラウンドエージェント**: ヘッドレス自動化、ETLパイプライン、運用システム

## サーバーのユースケース

**AWS Documentation MCPサーバー**を使えば、Amazon Bedrockインラインエージェントなど、あらゆるAWSサービスの最新情報の調査とコード生成をAIアシスタントに支援させることができます。また、**CDK MCPサーバー**や**Terraform MCPサーバー**を使えば、最新のAPIを使用しAWSのベストプラクティスに従ったInfrastructure as Codeの実装をAIアシスタントに作成させることができます。**Cost Analysis MCPサーバー**を使えば、「このCDKプロジェクトをデプロイする前に、月額コストの見積もりを教えて」や「このインフラ設計で発生しうるAWSサービスの費用を教えて」といった質問に対して、詳細なコスト見積もりと予算計画のインサイトを得られます。**Valkey MCPサーバー**はValkeyデータストアとの自然言語での対話を可能にし、AIアシスタントがシンプルな会話型インターフェースを通じてデータ操作を効率的に管理できるようにします。

## その他のリソース

- [Introducing AWS MCP Servers for code assistants](https://aws.amazon.com/blogs/machine-learning/introducing-aws-mcp-servers-for-code-assistants-part-1/)
- [Vibe coding with AWS MCP Servers | AWS Show & Tell](https://www.youtube.com/watch?v=qXGQQRMrcz0)
- [Terraform MCP Server Vibe Coding](https://youtu.be/i2nBD65md0Y)
- [How to Generate AWS Architecture Diagrams Using Amazon Q CLI and MCP](https://community.aws/content/2vPiiPiBSdRalaEax2rVDtshpf3/how-to-generate-aws-architecture-diagrams-using-amazon-q-cli-and-mcp)
- [Harness the power of MCP servers with Amazon Bedrock Agents](https://aws.amazon.com/blogs/machine-learning/harness-the-power-of-mcp-servers-with-amazon-bedrock-agents/)
- [Unlocking the power of Model Context Protocol (MCP) on AWS](https://aws.amazon.com/blogs/machine-learning/unlocking-the-power-of-model-context-protocol-mcp-on-aws/)
- [Introducing AWS Serverless MCP Server: AI-powered development for modern applications](https://aws.amazon.com/blogs/compute/introducing-aws-serverless-mcp-server-ai-powered-development-for-modern-applications/)
