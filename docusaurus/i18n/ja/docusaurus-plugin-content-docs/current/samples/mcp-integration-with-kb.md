---
title: "Amazon Bedrock Knowledge Bases との MCP 統合"
---

このリポジトリでは、[Model Context Protocol](https://modelcontextprotocol.io/) と Amazon Bedrock Knowledge Bases を統合する基本的な実装を紹介します。

## 概要 {#overview}

この実装は 2 つの部分から構成されています。

1. チャットボットの Streamlit / ユーザーインターフェイスを処理する `user_interfaces/chat_bedrock_st.py` ファイル
2. MCP クライアントとサーバーの実装を処理する `client_server.py` ファイル

この実装で使用している実際の MCP サーバーのコードは、[src/bedrock-kb-retrieval-mcp-server](https://github.com/awslabs/mcp/tree/main/src/bedrock-kb-retrieval-mcp-server) フォルダにあります。

### アーキテクチャ {#architecture}

![Architecture](https://github.com/awslabs/mcp/blob/main/samples/mcp-integration-with-kb/assets/simplified-mcp-flow-diagram.png?raw=true)

## セットアップ {#setup}

### 前提条件 {#prerequisites}

- [uv](https://docs.astral.sh/uv/getting-started/installation/) パッケージマネージャー
- Bedrock へのアクセス権と適切な IAM 権限を持つ AWS アカウント - [Amazon Bedrock の使用開始](https://docs.aws.amazon.com/bedrock/latest/userguide/getting-started.html)
- Bedrock ナレッジベース
  - ナレッジベースのセットアップのクイックリファレンスとしては、[e2e RAG solution via CDK](https://github.com/aws-samples/amazon-bedrock-samples/tree/main/rag/knowledge-bases/features-examples/04-infrastructure/e2e_rag_using_bedrock_kb_cdk) リポジトリを参照してください。これにより、IAM ロール、ベクトルストレージ（OpenSearch Serverless または Aurora PostgreSQL のいずれか）、サンプルデータを含む完全に構成されたナレッジベースなど、必要なものがすべて用意されます。この実装で実際に必要となるコンポーネントはナレッジベースのみです。

> **Note**: Amazon Bedrock の再ランク付けは us-east-1 ではサポートされていません。再ランク付けでサポートされているリージョンとモデルの詳細については、[Amazon Bedrock での再ランク付けがサポートされているリージョンとモデル](https://docs.aws.amazon.com/bedrock/latest/userguide/rerank-supported.html) を参照してください。

### インストール {#installation}

1. リポジトリをクローンします。

```bash
git clone https://github.com/awslabs/mcp.git
```

2. サンプルディレクトリに移動し、.env.example ファイルを .env にコピーして AWS 認証情報を追加します。

```bash
cd mcp/samples/mcp-integration-with-kb
cp .env.example .env
```

3. 2 つの異なるターミナルを開き、それぞれで依存関係をインストールします。

```bash
uv sync
```

その後、仮想環境を有効化します。

```bash
source .venv/bin/activate
```

4. 一方のターミナルで、FastAPI サーバーを実行します。

```bash
uvicorn clients.client_server:app --reload
```

5. もう一方のターミナルで、Streamlit アプリを実行します。

```bash
streamlit run user_interfaces/chat_bedrock_st.py
```

6. これでチャットボットが [http://localhost:8501/](http://localhost:8501/) で実行されているはずです。

## 使い方 {#usage}

Bedrock ナレッジベースのコンソールから Bedrock ナレッジベース ID を取得し、まず左側のメニューで UI に追加します。

あとは自由に質問してください。

## トラブルシューティング {#troubleshooting}

ログは FastAPI サーバーを実行したターミナルで確認でき、サーバーが実行したさまざまなステップやアクションが記載されています。

`boto3` または `streamlit` が見つからないというエラーが表示される場合は、仮想環境を有効化していないことが原因である可能性が高いです。

```bash
uv sync
source .venv/bin/activate
```
