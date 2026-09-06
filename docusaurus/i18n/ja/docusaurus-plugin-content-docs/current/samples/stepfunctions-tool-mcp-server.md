---
title: "Step Functions ツールのサンプル"
---

このディレクトリには、MCP サーバーのさまざまなユースケースを示すサンプルの Step Functions ステートマシンが含まれています。これらのステートマシンは、AWS SAM CLI を使用してデプロイするように設計されています。

## 利用可能なリソース {#available-resources}

### Lambda 関数 {#lambda-functions}

これらの Lambda 関数は、ステートマシンの構成要素として機能します。

1. **CustomerInfoFromId**
   - **目的**: 顧客 ID を使用して顧客のステータス情報を取得します
   - **入力**: `{ "customerId": "string" }`
   - **メモリ**: 128 MB
   - **タイムアウト**: 3 秒
   - **ランタイム**: Python 3.13
   - **アーキテクチャ**: ARM64

2. **CustomerIdFromEmail**
   - **目的**: メールアドレスを使用して顧客 ID を検索します
   - **入力**: `{ "email": "string" }`
   - **メモリ**: 128 MB
   - **タイムアウト**: 3 秒
   - **ランタイム**: Python 3.13
   - **アーキテクチャ**: ARM64

3. **CustomerCreate**
   - **目的**: 新しい顧客レコードを作成します
   - **入力**: 以下のスキーマを参照してください
   - **メモリ**: 128 MB
   - **タイムアウト**: 3 秒
   - **ランタイム**: Python 3.13
   - **アーキテクチャ**: ARM64

### ステートマシン {#state-machines}

1. **CustomerCreateStateMachine (EXPRESS)**
   - **目的**: 新しい顧客レコードを作成します
   - **タイプ**: EXPRESS（同期実行）
   - **入力**: CustomerCreate Lambda と同じ
   - **説明**: 同期実行のための CustomerCreate Lambda のシンプルなラッパー
   - **ユースケース**: 迅速な同期的な顧客作成操作

2. **GetCustomerInfoWorkflowStateMachine (STANDARD)**
   - **目的**: メールアドレスのみを使用して顧客情報を取得します
   - **タイプ**: STANDARD（非同期実行）
   - **入力**: `{ "email": "string" }`
   - **説明**: 次の処理を行う多段階のワークフローです。
     1. メールアドレスから顧客 ID を取得します
     2. その ID を使用して顧客情報を取得します
   - **ユースケース**: ワークフロー内で複数の Lambda 関数を連鎖させる方法を示します

## インストール {#installation}

### 前提条件 {#prerequisites}

1. [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html) をインストールします
2. 適切な権限を持つ AWS 認証情報を設定します
3. ローカルに Python 3.13 をインストールします（ローカルテスト用）

### デプロイ手順 {#deployment-steps}

1. サンプル関数のディレクトリに移動します。

   ```bash
   cd src/stepfunctions-tool-mcp-server/examples/sample_functions
   ```

2. アプリケーションをビルドします。

   ```bash
   sam build
   ```

3. アプリケーションをデプロイします。

   ```bash
   sam deploy --guided
   ```

   ガイド付きデプロイ中に、次の項目の入力を求められます。
   - スタック名の選択
   - AWS リージョンの選択
   - IAM ロール作成の確認
   - SAM CLI による IAM ロール作成の許可
   - samconfig.toml への引数の保存

4. 以降のデプロイでは、次のコマンドを使用できます。

   ```bash
   sam deploy
   ```

## クリーンアップ {#cleanup}

デプロイしたすべてのリソースを削除するには、次のコマンドを実行します。

```bash
sam delete --stack-name <your-stack-name>
```

## セキュリティに関する考慮事項 {#security-considerations}

- すべての Lambda 関数は、コスト最適化のために ARM64 アーキテクチャで実行されます
- Express ステートマシンは、迅速な同期操作に使用されます
- Standard ステートマシンは、ワークフローのオーケストレーションに使用されます
- すべての実行でロギングとトレースが有効になっています
- ステートマシンは、最小権限の権限を持つ IAM ロールを使用します
