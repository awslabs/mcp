---
title: Amazon Nova Canvas との MCP 統合
---

このリポジトリは、画像生成のための [Model Context Protocol](https://modelcontextprotocol.io/) と Amazon Nova Canvas の統合に関する基本的な実装を概説します。

## 概要 {#overview}

この実装には 2 つのパートがあります。

1. `user_interfaces/image_generator_st.py` ファイル。画像生成のための Streamlit／ユーザーインターフェースを処理します。
2. `client_server.py` ファイル。MCP クライアントとサーバーの実装を処理します。

実際に利用される MCP サーバーのコードは、[src/nova-canvas-mcp-server](https://github.com/awslabs/mcp/blob/main/src/nova-canvas-mcp-server/) フォルダーにあります。

### アーキテクチャ {#architecture}

この実装は次のフローに従います。

1. Streamlit UI が画像生成用のユーザーインターフェースを提供します。
2. UI は FastAPI サーバーと通信します。
3. FastAPI サーバーは MCP クライアントを使用して Nova Canvas MCP サーバーと通信します。
4. Nova Canvas MCP サーバーは Amazon Bedrock とやり取りして画像を生成します。
5. 生成された画像は表示用に UI へ返されます。

## セットアップ {#setup}

### 前提条件 {#prerequisites}

- [uv](https://docs.astral.sh/uv/getting-started/installation/) パッケージマネージャー
- Bedrock アクセスと適切な IAM 権限を持つ AWS アカウント - [Amazon Bedrock の使用開始](https://docs.aws.amazon.com/bedrock/latest/userguide/getting-started.html)
- Bedrock における Amazon Nova Canvas および Amazon Nova Micro モデル（プロンプト改善用、オプション）へのアクセス

### インストール {#installation}

1. リポジトリをクローンします。

```bash
git clone https://github.com/awslabs/mcp.git
```

2. サンプルディレクトリに移動し、.env.example ファイルを .env にコピーして AWS 認証情報を追加します。

```bash
cd mcp/samples/mcp-integration-with-nova-canvas
cp .env.example .env
```

3. 2 つの異なるターミナルを開き、それぞれで依存関係をインストールします。

```bash
uv sync
```

続いて仮想環境を有効化します。

```bash
source .venv/bin/activate
```
4. 一方のターミナルで FastAPI サーバーを実行します。

```bash
uvicorn clients.client_server:app --reload
```

5. もう一方のターミナルで Streamlit アプリを実行します。

```bash
streamlit run user_interfaces/image_generator_st.py
```

6. これで画像生成ツールが [http://localhost:8501/](http://localhost:8501/) で実行されているはずです。

## 使い方 {#usage}

1. 生成したい画像を説明するテキストプロンプトを入力します。
2. オプションで、画像に含めたくないものを指定するネガティブプロンプトを追加します。
3. 画像パラメータ（寸法、品質など）をカスタマイズします。
4. 色を指定した生成を行う場合は、カラーピッカーから色を選択します。
5. "Generate Image" をクリックして画像を作成します。
6. 生成された画像を表示し、必要に応じて保存します。

## トラブルシューティング {#troubleshooting}

ログは FastAPI サーバーを実行したターミナルで確認でき、サーバーが実行したさまざまなステップやアクションが記載されます。

`boto3` または `streamlit` が見つからないというエラーが表示される場合、仮想環境を有効化していないことが原因である可能性が高いです。

```bash
uv sync
source .venv/bin/activate
```
