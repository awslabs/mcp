---
title: AWS向けオープンソースMCPサーバー - サンプル
---

このディレクトリには、`src` ディレクトリで提供されている AWS向けオープンソースMCPサーバーの使い方を示すサンプル集が含まれています。各サンプルは、関連するドキュメントとコードとともに、それぞれ独自のフォルダにまとめられています。

## 構成 {#structure}

```bash
samples/
├── project-name/
│   ├── README.md
│   └── (sample code and resources)
```

## 目的 {#purpose}

このディレクトリのサンプルは、次のものを提供します。

- AWS 向けの各オープンソース MCP サーバーの実際に動作する例
- 統合パターンとベストプラクティス
- 一般的なユースケースのコードスニペット
- ステップバイステップのガイド

## ガイドライン {#guidelines}

- 各サンプルディレクトリは、1 つ以上の MCP サーバーのデモンストレーションに焦点を当てる必要があります
- すべてのサンプルには、明確な手順を記載した README.md を含める必要があります
- サンプルは新しい MCP サーバーを導入するものであってはならず、既存のサーバーの使い方を示すだけにとどめる必要があります

## 利用可能なサンプル {#available-samples}

### KB との MCP 統合 {#mcp-integration-with-kb}

Amazon Bedrock Knowledge Base MCP サーバーと統合するクライアントです。コードは [mcp-integration-with-kb](https://github.com/awslabs/mcp/tree/main/samples/mcp-integration-with-kb) フォルダにあります。

### AWS Step Functions Tool MCP サーバー {#aws-step-functions-tool-mcp-server}

AI モデルが AWS Step Functions ステートマシンをツールとして実行できるようにするサーバーで、既存のワークフローとのシームレスな統合を可能にします。このサーバーは Standard ワークフローと Express ワークフローの両方をサポートし、入力の検証のために EventBridge Schema Registry と統合します。コードは [src/stepfunctions-tool-mcp-server](https://github.com/awslabs/mcp/tree/main/src/stepfunctions-tool-mcp-server) フォルダにあります。

### 近日公開 {#coming-soon}

## 貢献 {#contributing}

追加のサンプルの貢献を歓迎します。サンプルが上記のガイドラインに従い、MCP サーバーの実世界での使用例を示していることを確認してください。
