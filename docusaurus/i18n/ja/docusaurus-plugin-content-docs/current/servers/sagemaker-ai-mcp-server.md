---
title: "Amazon SageMaker AI MCPサーバー"
---

Amazon SageMaker AI MCP サーバーは、高性能かつ低コストな AI/ML モデル開発を実現するためのツールをエージェントに提供します。現在、このサーバーには SageMaker HyperPod クラスターを管理するためのツールが含まれています。

## 利用可能な機能 {#available-features}

### SageMaker HyperPod {#sagemaker-hyperpod}

Amazon EKS または Slurm でオーケストレーションされる SageMaker HyperPod クラスターを管理するための包括的なツールを提供します。これには、クラスターのデプロイ、ノード管理、ライフサイクル操作が含まれます。サポートされているツールの詳細については、[HyperPod ドキュメント](https://github.com/awslabs/mcp/blob/main/src/sagemaker-ai-mcp-server/awslabs/sagemaker_ai_mcp_server/README.md)を参照してください。

## 前提条件 {#prerequisites}

* [Python 3.10 以上をインストール](https://www.python.org/downloads/release/python-3100/)
* [`uv` パッケージマネージャーをインストール](https://docs.astral.sh/uv/getting-started/installation/)
* [AWS CLI をインストールして認証情報を設定](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html)

## クイックスタート {#quickstart}

このクイックスタートガイドでは、Kiro、Cursor、およびその他の互換性のある IDE で使用するために Amazon SageMaker AI MCP Server を設定する手順を説明します。

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.sagemaker-ai-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.sagemaker-ai-mcp-server%40latest%22%2C%22--allow-write%22%2C%22--allow-sensitive-data-access%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.sagemaker-ai-mcp-server&config=eyJhdXRvQXBwcm92ZSI6W10sImRpc2FibGVkIjpmYWxzZSwiY29tbWFuZCI6InV2eCBhd3NsYWJzLnNhZ2VtYWtlci1haS1tY3Atc2VydmVyQGxhdGVzdCAtLWFsbG93LXdyaXRlIC0tYWxsb3ctc2Vuc2l0aXZlLWRhdGEtYWNjZXNzIiwiZW52Ijp7IkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwidHJhbnNwb3J0VHlwZSI6InN0ZGlvIn0%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=SageMaker%20AI%20MCP%20Server&config=%7B%22autoApprove%22%3A%5B%5D%2C%22disabled%22%3Afalse%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.sagemaker-ai-mcp-server%40latest%22%2C%22--allow-write%22%2C%22--allow-sensitive-data-access%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22transportType%22%3A%22stdio%22%7D) |

**Kiro のセットアップ**

詳細については、[Kiro IDE ドキュメント](https://kiro.dev/docs/mcp/configuration/)または [Kiro CLI ドキュメント](https://kiro.dev/docs/cli/mcp/configuration/)を参照してください。

グローバル設定の場合は ~/.kiro/settings/mcp.json を編集します。プロジェクト固有の設定の場合は、プロジェクトディレクトリ内の .kiro/settings/mcp.json を編集します。

以下の例には、変更を伴う操作のための `--allow-write` フラグと、ログやイベントにアクセスするための `--allow-sensitive-data-access` フラグの両方が含まれています。

   **Mac/Linux の場合:**

	```
	{
	  "mcpServers": {
	    "awslabs.sagemaker-ai-mcp-server": {
	      "command": "uvx",
	      "args": [
	        "awslabs.sagemaker-ai-mcp-server@latest",
	        "--allow-write",
	        "--allow-sensitive-data-access"
	      ],
	      "env": {
	        "FASTMCP_LOG_LEVEL": "ERROR"
	      },
	      "autoApprove": [],
	      "disabled": false
	    }
	  }
	}
	```

   **Windows の場合:**

	```
	{
	  "mcpServers": {
	    "awslabs.sagemaker-ai-mcp-server": {
	      "command": "uvx",
	      "args": [
	        "--from",
	        "awslabs.sagemaker-ai-mcp-server@latest",
	        "awslabs.sagemaker-ai-mcp-server.exe",
	        "--allow-write",
	        "--allow-sensitive-data-access"
	      ],
	      "env": {
	        "FASTMCP_LOG_LEVEL": "ERROR"
	      },
	      "autoApprove": [],
	      "disabled": false
	    }
	  }
	}
	```

Kiro CLI で `/tools` コマンドを実行し、利用可能な SageMaker AI MCP ツールが表示されることを確認して、セットアップを検証してください。

これは基本的なクイックスタートである点にご注意ください。すべての SageMaker API を完全にカバーし、一般的な問題を効果的にトラブルシューティングするために、SageMaker AI MCP サーバーを [AWS API MCP Server](https://awslabs.github.io/mcp/servers/aws-api-mcp-server)、[AWS Knowledge MCP Server](https://awslabs.github.io/mcp/servers/aws-knowledge-mcp-server)/[AWS Documentation MCP Server](https://awslabs.github.io/mcp/servers/aws-documentation-mcp-server)、および [AWS EKS MCP Server](https://awslabs.github.io/mcp/servers/eks-mcp-server) と組み合わせて使用することをお勧めします。

## 設定 {#configurations}

### 引数 {#arguments}

MCP サーバー定義の `args` フィールドは、サーバーの起動時に渡されるコマンドライン引数を指定します。これらの引数は、サーバーの実行方法と設定を制御します。例:

**Mac/Linux の場合:**
```
{
  "mcpServers": {
    "awslabs.sagemaker-ai-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.sagemaker-ai-mcp-server@latest",
        "--allow-write",
        "--allow-sensitive-data-access"
      ],
      "env": {
        "AWS_PROFILE": "your-profile",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

**Windows の場合:**
```
{
  "mcpServers": {
    "awslabs.sagemaker-ai-mcp-server": {
      "command": "uvx",
      "args": [
        "--from",
        "awslabs.sagemaker-ai-mcp-server@latest",
        "awslabs.sagemaker-ai-mcp-server.exe",
        "--allow-write",
        "--allow-sensitive-data-access"
      ],
      "env": {
        "AWS_PROFILE": "your-profile",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

#### コマンド形式 {#command-format}

コマンド形式はオペレーティングシステムによって異なります。

**Mac/Linux の場合:**
* `awslabs.sagemaker-ai-mcp-server@latest` - MCP クライアント設定用の最新のパッケージ/バージョン指定子を指定します。

**Windows の場合:**
* `--from awslabs.sagemaker-ai-mcp-server@latest awslabs.sagemaker-ai-mcp-server.exe` - Windows では、パッケージを指定するための `--from` フラグと `.exe` 拡張子が必要です。

#### `--allow-write` (オプション) {#--allow-write-optional}

書き込みアクセスモードを有効にし、変更を伴う操作 (リソースの作成、更新、削除など) を許可します。

* デフォルト: true (サーバーはデフォルトで書き込みモードで実行されます)
* 例: 読み取り専用モードに切り替えるには、MCP サーバー定義の `args` リストから `--allow-write` を削除します。

#### `--allow-sensitive-data-access` (オプション) {#--allow-sensitive-data-access-optional}

ログ、イベント、リソース詳細などの機密データへのアクセスを有効にします。このフラグは、機密性の高い可能性がある情報にアクセスするツールに必要です。

* デフォルト: true (機密データへのアクセスはデフォルトで許可されています)
* 例: 無効にするには、MCP サーバー定義の `args` リストから `--allow-sensitive-data-access` を削除します。

### 環境変数 {#environment-variables}

MCP サーバー定義の `env` フィールドでは、SageMaker AI MCP サーバーの動作を制御する環境変数を設定できます。例:

```
{
  "mcpServers": {
    "awslabs.sagemaker-ai-mcp-server": {
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "my-profile",
        "AWS_REGION": "us-west-2"
      }
    }
  }
}
```

#### `FASTMCP_LOG_LEVEL` (オプション) {#fastmcp_log_level-optional}

サーバーのログレベルの詳細度を設定します。

* 有効な値: "DEBUG"、"INFO"、"WARNING"、"ERROR"、"CRITICAL"
* デフォルト: "WARNING"
* 例: `"FASTMCP_LOG_LEVEL": "ERROR"`

#### `AWS_PROFILE` (オプション) {#aws_profile-optional}

認証に使用する AWS プロファイルを指定します。

* デフォルト: なし (設定されていない場合は、デフォルトの AWS 認証情報を使用します)。
* 例: `"AWS_PROFILE": "my-profile"`

#### `AWS_REGION` (オプション) {#aws_region-optional}

SageMaker リソースを管理する AWS リージョンを指定します。これはすべての AWS サービス操作に使用されます。

* デフォルト: なし (設定されていない場合は、デフォルトの AWS リージョンを使用します)。
* 例: `"AWS_REGION": "us-west-2"`

## セキュリティと権限 {#security--permissions}

### 機能 {#features}

SageMaker AI MCP Server は、次のセキュリティ機能を実装しています。

1. **AWS 認証**: 安全な認証のために、環境の AWS 認証情報を使用します。
2. **SSL 検証**: すべての AWS API 呼び出しに対して SSL 検証を強制します。
3. **リソースタグ付け**: トレーサビリティのために、作成されたすべてのリソースにタグを付けます。
4. **最小権限**: 適切な権限を持つ IAM ロールを使用します。
5. **スタック保護**: HyperPod 用の CloudFormation スタックが、それを作成したツールによってのみ変更できるようにします。

### 考慮事項 {#considerations}

SageMaker AI MCP Server を使用する際は、次の点を考慮してください。

* **AWS 認証情報**: サーバーには、SageMaker AI リソースを作成および管理するための権限が必要です。
* **ネットワークセキュリティ**: SageMaker AI リソース用に VPC とセキュリティグループを適切に設定してください。
* **認証**: AWS リソースに対して適切な認証メカニズムを使用してください。
* **認可**: AWS リソースに対して IAM を適切に設定してください。
* **データ保護**: SageMaker AI リソース内の機密データを暗号化してください。
* **ログ記録とモニタリング**: SageMaker AI リソースのログ記録とモニタリングを有効にしてください。

### 権限 {#permissions}

SageMaker AI MCP Server は、適切なセキュリティ管理を実施した上で本番環境で使用できます。サーバーはデフォルトで読み取り専用モードで実行され、これは本番環境において推奨され、一般的により安全であると考えられています。書き込みアクセスは必要な場合にのみ明示的に有効にしてください。以下は、読み取り専用モードと書き込みアクセスモードのそれぞれで利用可能な HyperPod MCP ツールです。

* **読み取り専用モード (デフォルト)**: `manage_hyperpod_stacks` (operation="describe" を指定)、`manage_hyperpod_cluster_nodes` (operations="list_clusters"、"list_nodes"、"describe_node" を指定)。
* **書き込みアクセスモード**: (`--allow-write` が必要): `manage_hyperpod_stacks` ("deploy"、"delete" を指定)、`manage_hyperpod_cluster_nodes` (operations="update_software"、"batch_delete" を指定)。

#### `autoApprove` (オプション) {#autoapprove-optional}

MCP サーバー定義内の配列で、MCP Server クライアントによって自動的に承認されるツール名を列挙し、それらの特定のツールに対するユーザー確認をバイパスします。例:

**Mac/Linux の場合:**
```
{
  "mcpServers": {
    "awslabs.sagemaker-ai-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.sagemaker-ai-mcp-server@latest"
      ],
      "env": {
        "AWS_PROFILE": "sagemaker-ai-mcp-readonly-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "INFO"
      },
      "autoApprove": [
        "manage_hyperpod_stacks",
        "manage_hyperpod_cluster_nodes"
      ]
    }
  }
}
```

**Windows の場合:**
```
{
  "mcpServers": {
    "awslabs.sagemaker-ai-mcp-server": {
      "command": "uvx",
      "args": [
        "--from",
        "awslabs.sagemaker-ai-mcp-server@latest",
        "awslabs.sagemaker-ai-mcp-server.exe"
      ],
      "env": {
        "AWS_PROFILE": "sagemaker-ai-mcp-readonly-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "INFO"
      },
      "autoApprove": [
        "manage_hyperpod_stacks",
        "manage_hyperpod_cluster_nodes"
      ]
    }
  }
}
```

### ロールスコープに関する推奨事項 {#role-scoping-recommendations}

セキュリティのベストプラクティスに従い、次のことを推奨します。

1. 「最小権限」の原則に基づき、SageMaker AI MCP Server が使用する**専用の IAM ロールを作成**してください。
2. 読み取り専用操作と書き込み操作には**別々のロールを使用**してください。
3. サーバーが作成したリソースにアクションを限定するために、**リソースタグ付けを実装**してください。
4. サーバーが行うすべての API 呼び出しを監査するために、**AWS CloudTrail を有効化**してください。
5. サーバーの IAM ロールに付与された権限を**定期的に確認**してください。
6. 削除可能な未使用の権限を特定するために、**IAM Access Analyzer を使用**してください。

### 機密情報の取り扱い {#sensitive-information-handling}

**重要**: 許可された入力メカニズムを介してシークレットや機密情報を渡さないでください。

* CloudFormation テンプレートにシークレットや認証情報を含めないでください。
* モデルへのプロンプトに機密情報を直接渡さないでください。
* シークレットの作成に MCP ツールを使用することは避けてください。シークレットデータをモデルに提供する必要が生じるためです。

**CloudFormation テンプレートのセキュリティ**:

* 信頼できるソースからの CloudFormation テンプレートのみを使用してください。
* サーバーはテンプレートの内容について CloudFormation API の検証に依存しており、独自の検証は行いません。
* CloudFormation テンプレートをクラスターに適用する前に監査してください。

**MCP 経由でシークレットを渡す代わりに**:

* 機密情報の保存には AWS Secrets Manager または Parameter Store を使用してください。
* サービスアカウント用に適切な IAM ロールを設定してください。
* AWS サービスへのアクセスには、サービスアカウント用 IAM ロール (IRSA) を使用してください。

### ファイルシステムアクセスと動作モード {#file-system-access-and-operating-mode}

**重要**: この MCP サーバーは、単一ユーザーの認証情報を使用するローカルサーバーとして、**STDIO モード専用**を想定しています。サーバーは起動したユーザーと同じ権限で実行され、ファイルシステムへの完全なアクセス権を持ちます。

#### セキュリティとアクセスに関する考慮事項 {#security-and-access-considerations}

- **ファイルシステムへのフルアクセス**: サーバーは、ユーザーが権限を持つファイルシステム上の任意の場所に対して読み取りと書き込みが可能です
- **ホストファイルシステムの共有**: このサーバーを使用すると、ホストのファイルシステムに直接アクセスできます
- **ネットワーク用途への改変禁止**: このサーバーはローカルでの STDIO 使用のみを目的として設計されています。ネットワーク経由での運用は追加のセキュリティリスクをもたらします

#### 一般的なファイル操作 {#common-file-operations}

MCP サーバーは、HyperPod クラスターの作成時に、ユーザーが指定した絶対ファイルパスにテンプレート化されたパラメータ JSON ファイルを作成できます。


## 一般的なベストプラクティス {#general-best-practices}

* **リソースの命名**: SageMaker AI リソースにはわかりやすい名前を使用してください。
* **エラー処理**: ツールのレスポンスでエラーを確認し、適切に処理してください。
* **リソースのクリーンアップ**: 不要なコストを避けるため、未使用のリソースを削除してください。
* **モニタリング**: リソースの状態を定期的に監視してください。
* **セキュリティ**: SageMaker AI リソースに対して AWS セキュリティのベストプラクティスに従ってください。
* **バックアップ**: 重要な SageMaker AI リソースを定期的にバックアップしてください。

## 一般的なトラブルシューティング {#general-troubleshooting}

* **権限エラー**: AWS 認証情報に必要な権限があることを確認してください。
* **CloudFormation エラー**: CloudFormation コンソールでスタック作成エラーを確認してください。
* **SageMaker API エラー**: HyperPod クラスターが実行中でアクセス可能であることを確認してください。
* **ネットワークの問題**: VPC とセキュリティグループの設定を確認してください。
* **クライアントエラー**: MCP クライアントが正しく設定されていることを確認してください。
* **ログレベル**: より詳細なログを取得するには、ログレベルを DEBUG に上げてください。

サービス固有の問題については、関連するサービスドキュメントを参照してください。
- [HyperPod ドキュメント](https://github.com/awslabs/mcp/blob/main/src/sagemaker-ai-mcp-server/awslabs/sagemaker_ai_mcp_server/README.md)
- [Amazon SageMaker AI ドキュメント](https://docs.aws.amazon.com/sagemaker/)

## バージョン {#version}

現在の MCP サーバーバージョン: 1.0.0
