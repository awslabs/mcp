---
title: Amazon EKS MCPサーバー
---

Amazon EKS MCPサーバーは、AIコードアシスタントにリソース管理ツールとリアルタイムのクラスター状態の可視性を提供します。これにより、大規模言語モデル（LLM）に不可欠なツール群とコンテキスト認識が提供され、AIコードアシスタントは初期セットアップから本番環境の最適化やトラブルシューティングに至るまで、状況に応じたガイダンスを通じてアプリケーション開発を効率化できます。

EKS MCPサーバーをAIコードアシスタントに統合すると、開発ワークフローがあらゆるフェーズで強化されます。まず、前提リソースの自動作成とベストプラクティスの適用により、初期のクラスターセットアップが簡素化されます。さらに、高レベルなワークフローと自動コード生成により、アプリケーションのデプロイが効率化されます。最後に、インテリジェントなデバッグツールとナレッジベースへのアクセスにより、トラブルシューティングが加速されます。これらすべてにより、AIコードアシスタントでの自然言語による対話を通じて、複雑なオペレーションが簡素化されます。

## 主な機能 {#key-features}

* AIコードアシスタントのユーザーが、リクエストを適切な AWS CloudFormation アクションに変換することで、専用のVPC、ネットワーキング、EKS Auto Modeノードプールなどの前提リソースを含む新しいEKSクラスターを作成できるようにします。
* 既存のKubernetes YAMLファイルを適用するか、ユーザーが指定したパラメータに基づいて新しいdeploymentおよびserviceマニフェストを生成することで、コンテナ化されたアプリケーションをデプロイする機能を提供します。
* EKSクラスター内の個々のKubernetesリソース（Pod、Service、Deploymentなど）の完全なライフサイクル管理をサポートし、作成、読み取り、更新、パッチ適用、削除の操作を可能にします。
* 名前空間、ラベル、フィールドによるフィルタリングを使用してKubernetesリソースを一覧表示する機能を提供し、ユーザーとLLMの双方がKubernetesアプリケーションとEKSインフラストラクチャの状態に関する情報を収集するプロセスを簡素化します。
* 特定のPodやコンテナからのログ取得、特定のリソースに関連するKubernetesイベントの取得などの運用タスクを支援し、直接のユーザーとAI駆動のワークフローの両方におけるトラブルシューティングとモニタリングをサポートします。
* ユーザーがEKSクラスターの問題をトラブルシューティングできるようにします。

## 前提条件 {#prerequisites}

* [Python 3.10以上のインストール](https://www.python.org/downloads/release/python-3100/)
* [`uv` パッケージマネージャーのインストール](https://docs.astral.sh/uv/getting-started/installation/)
* [AWS CLIのインストールと認証情報の設定](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html)（IAM認証モードで必要。kubeconfigモードでは不要）

## セットアップ {#setup}

EKSクラスターリソースの管理に使用するIAMロールまたはユーザーに、以下のIAMポリシーを追加してください。

### 読み取り専用オペレーションポリシー {#read-only-operations-policy}

読み取りオペレーションには、以下の権限が必要です。

```
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eks:DescribeCluster",
        "eks:DescribeInsight",
        "eks:ListInsights",
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets",
        "ec2:DescribeRouteTables",
        "cloudformation:DescribeStacks",
        "cloudwatch:GetMetricData",
        "logs:StartQuery",
        "logs:GetQueryResults",
        "iam:GetRole",
        "iam:GetRolePolicy",
        "iam:ListRolePolicies",
        "iam:ListAttachedRolePolicies",
        "iam:GetPolicy",
        "iam:GetPolicyVersion",
        "eks-mcpserver:QueryKnowledgeBase"
      ],
      "Resource": "*"
    }
  ]
}
```

### 書き込みオペレーションポリシー {#write-operations-policy}

書き込みオペレーションについては、`/awslabs/eks_mcp_server/templates/eks-templates/eks-with-vpc.yaml` のCloudFormationテンプレートを使用してEKSクラスターを確実にデプロイできるように、以下のIAMポリシーを推奨します。

* [**IAMFullAccess**](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/IAMFullAccess.html): クラスターの運用に必要なIAMロールとポリシーの作成および管理を可能にします
* [**AmazonVPCFullAccess**](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/AmazonVPCFullAccess.html): サブネット、ルートテーブル、インターネットゲートウェイ、NATゲートウェイを含むVPCリソースの作成と設定を許可します
* [**AWSCloudFormationFullAccess**](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/AWSCloudFormationFullAccess.html): デプロイをオーケストレーションするCloudFormationスタックの作成、更新、削除の権限を提供します
* **EKS Full Access（以下で提供）**: コントロールプレーンの設定、ノードグループ、アドオンを含む、EKSクラスターの作成と管理に必要です
   ```
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": "eks:*",
        "Resource": "*"
      }
    ]
  }
   ```


**重要なセキュリティに関する注意**: これらの広範な権限を付与した状態で `--allow-write` および `--allow-sensitive-data-access` モードを有効にする場合、この組み合わせはMCPサーバーに大きな権限を付与するため、ユーザーは注意を払う必要があります。これらのフラグは、必要な場合にのみ、信頼できる環境でのみ有効にしてください。本番環境での使用には、より制限的なカスタムポリシーの作成を検討してください。

### Kubernetes APIアクセス要件 {#kubernetes-api-access-requirements}

**IAMモード（デフォルト）:** すべてのKubernetes APIオペレーションは、以下のいずれかの条件を満たす場合にのみ動作します。

1. ユーザーのプリンシパル（IAMロール/ユーザー）が、アクセス対象のEKSクラスターを実際に作成した場合
2. ユーザーのプリンシパルに対してEKSアクセスエントリが設定されている場合

Kubernetes APIオペレーションの使用時に認可エラーが発生した場合は、プリンシパルに対してアクセスエントリが正しく設定されていることを確認してください。

**Kubeconfigモード（`EKS_AUTH_MODE=kubeconfig`）:** Kubernetes APIへのアクセスは、kubeconfigファイル内の認証情報（OIDCトークン、証明書など）とクラスターに設定されたRBACポリシーによって決まります。`cluster_name` パラメータはEKSクラスター名を受け付け、対応するkubeconfigコンテキストに自動的に解決されます。

## クイックスタート {#quickstart}

このクイックスタートガイドでは、Kiro、Cursor、およびその他のAIコーディングアシスタントで使用するために Amazon EKS MCP Server を設定する手順を説明します。以下の手順に従うことで、Amazon EKSクラスターとKubernetesリソースを管理するEKS MCPサーバーのツールを活用できるように開発環境をセットアップできます。

**IDEのセットアップ**

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.eks-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.eks-mcp-server%40latest%22%2C%22--allow-write%22%2C%22--allow-sensitive-data-access%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.eks-mcp-server&config=eyJhdXRvQXBwcm92ZSI6W10sImRpc2FibGVkIjpmYWxzZSwiY29tbWFuZCI6InV2eCBhd3NsYWJzLmVrcy1tY3Atc2VydmVyQGxhdGVzdCAtLWFsbG93LXdyaXRlIC0tYWxsb3ctc2Vuc2l0aXZlLWRhdGEtYWNjZXNzIiwiZW52Ijp7IkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwidHJhbnNwb3J0VHlwZSI6InN0ZGlvIn0%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=EKS%20MCP%20Server&config=%7B%22autoApprove%22%3A%5B%5D%2C%22disabled%22%3Afalse%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.eks-mcp-server%40latest%22%2C%22--allow-write%22%2C%22--allow-sensitive-data-access%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22transportType%22%3A%22stdio%22%7D) |

**Kiroのセットアップ**

詳細については、[Kiro IDEドキュメント](https://kiro.dev/docs/mcp/configuration/)または[Kiro CLIドキュメント](https://kiro.dev/docs/cli/mcp/configuration/)を参照してください。

グローバル設定の場合は `~/.kiro/settings/mcp.json` を編集します。プロジェクト固有の設定の場合は、プロジェクトディレクトリ内の `.kiro/settings/mcp.json` を編集します。

Kiro CLIで `/tools` コマンドを実行し、利用可能なEKS MCPツールが表示されることを確認して、セットアップを検証してください。

以下の例には、変更を伴うオペレーション用の `--allow-write` フラグと、ログおよびイベントにアクセスするための `--allow-sensitive-data-access` フラグの両方が含まれています（詳細については「引数」セクションを参照してください）。

   **Mac/Linuxの場合:**

	```
	{
	  "mcpServers": {
	    "awslabs.eks-mcp-server": {
	      "command": "uvx",
	      "args": [
	        "awslabs.eks-mcp-server@latest",
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

   **Windowsの場合:**

	```
	{
	  "mcpServers": {
	    "awslabs.eks-mcp-server": {
	      "command": "uvx",
	      "args": [
	        "--from",
	        "awslabs.eks-mcp-server@latest",
	        "awslabs.eks-mcp-server.exe",
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

なお、これは基本的なクイックスタートです。[コンテナでのMCPサーバーの実行](https://github.com/awslabs/mcp?tab=readme-ov-file#running-mcp-servers-in-containers)や、[AWS Documentation MCP Server](https://awslabs.github.io/mcp/servers/aws-documentation-mcp-server/)などのさらに多くのMCPサーバーを単一のMCPサーバー定義に組み合わせるといった、追加の機能を有効にすることもできます。例を確認するには、GitHub上のAWS向けオープンソースMCPサーバーリポジトリの[Installation and Setup](https://github.com/awslabs/mcp?tab=readme-ov-file#installation-and-setup)ガイドを参照してください。MCPサーバーと連携するアプリケーションコードを含む実際の実装例を確認するには、Anthropicドキュメントの[Server Developer](https://modelcontextprotocol.io/quickstart/server)ガイドを参照してください。

## 設定 {#configurations}

### 引数 {#arguments}

MCPサーバー定義の `args` フィールドは、サーバー起動時に渡されるコマンドライン引数を指定します。これらの引数は、サーバーの実行方法と設定を制御します。例:

**Mac/Linuxの場合:**
```
{
  "mcpServers": {
    "awslabs.eks-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.eks-mcp-server@latest",
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

**Windowsの場合:**
```
{
  "mcpServers": {
    "awslabs.eks-mcp-server": {
      "command": "uvx",
      "args": [
        "--from",
        "awslabs.eks-mcp-server@latest",
        "awslabs.eks-mcp-server.exe",
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

**Mac/Linuxの場合:**
* `awslabs.eks-mcp-server@latest` - MCPクライアント設定用に最新のパッケージ/バージョン指定子を指定します。

**Windowsの場合:**
* `--from awslabs.eks-mcp-server@latest awslabs.eks-mcp-server.exe` - Windowsでは、パッケージを指定するための `--from` フラグと `.exe` 拡張子が必要です。

どちらの形式でも、MCPサーバーの起動とツールの登録が可能です。

#### `--allow-write`（オプション） {#--allow-write-optional}

書き込みアクセスモードを有効にします。これにより、apply_yaml、generate_app_manifest、manage_k8s_resource、manage_eks_stacks、add_inline_policy の各ツールのオペレーションにおいて、変更を伴う操作（リソースの作成、更新、削除など）が可能になります。

* デフォルト: false（サーバーはデフォルトで読み取り専用モードで実行されます）
* 例: MCPサーバー定義の `args` リストに `--allow-write` を追加します。

#### `--allow-sensitive-data-access`（オプション） {#--allow-sensitive-data-access-optional}

ログ、イベント、Kubernetes Secretなどの機密データへのアクセスを有効にします。このフラグは、get_pod_logs、get_k8s_events、get_cloudwatch_logs、manage_k8s_resource（Kubernetes Secretの読み取りに使用する場合）など、機密情報にアクセスする可能性のあるツールに必要です。

* デフォルト: false（機密データへのアクセスはデフォルトで制限されています）
* 例: MCPサーバー定義の `args` リストに `--allow-sensitive-data-access` を追加します。

#### `--auth-mode`（オプション） {#--auth-mode-optional}

Kubernetes APIアクセスの認証モードを指定します。`EKS_AUTH_MODE` 環境変数でも設定できます。CLI引数は環境変数よりも優先されます。

* 有効な値: `iam`（デフォルト）、`kubeconfig`
* デフォルト: `iam`
* 例: MCPサーバー定義の `args` リストに `--auth-mode kubeconfig` を追加します。

### Kubeconfig/OIDC認証 {#kubeconfigoidc-authentication}

ユーザーがOIDC認証やその他のkubeconfigベースの方法（AWS IAM認証情報なし）でKubernetesにアクセスする環境向けに、EKS MCPサーバーはkubeconfig認証モードをサポートしています。

**OIDC/kubeconfigユーザー向けの設定例:**

```json
{
  "mcpServers": {
    "awslabs.eks-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.eks-mcp-server@latest",
        "--allow-write",
        "--allow-sensitive-data-access"
      ],
      "env": {
        "EKS_AUTH_MODE": "kubeconfig",
        "KUBECONFIG": "/home/user/.kube/config",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

このモードでは:

* `cluster_name` パラメータはEKSクラスター名を受け付け、対応するkubeconfigコンテキストに自動的に解決されます。
* kubernetes Pythonクライアントが、kubeconfigに設定されたexecプラグイン、証明書、またはトークンの方式を介してすべての認証を処理します。
* トークンの更新（OIDCの場合など）は、kubernetesクライアントによって自動的に処理されます。
* **重要**: kubeconfigモードでは、AWS固有のツールは**登録されません**。以下のツールはIAM認証モードを必要とし、`EKS_AUTH_MODE=iam`（デフォルト）の場合にのみ利用可能です。
  * `manage_eks_stacks`（CloudFormationベースのクラスター管理）
  * `get_cloudwatch_logs` および `get_cloudwatch_metrics`（CloudWatch統合）
  * `get_eks_vpc_config`（VPC設定）
  * `get_eks_insights`（EKSクラスターインサイト）
  * `get_policies_for_role` および `add_inline_policy`（IAM統合）
  * `search_eks_troubleshoot_guide`（EKSナレッジベース。AWS SigV4認証が必要）

### 環境変数 {#environment-variables}

MCPサーバー定義の `env` フィールドでは、EKS MCPサーバーの動作を制御する環境変数を設定できます。例:

```
{
  "mcpServers": {
    "awslabs.eks-mcp-server": {
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "my-profile",
        "AWS_REGION": "us-west-2",
        "HTTP_PROXY": "http://proxy.example.com:8080",
        "HTTPS_PROXY": "https://proxy.example.com:8080"
      }
    }
  }
}
```

#### `FASTMCP_LOG_LEVEL`（オプション） {#fastmcp_log_level-optional}

サーバーのログレベルの詳細度を設定します。

* 有効な値: "DEBUG"、"INFO"、"WARNING"、"ERROR"、"CRITICAL"
* デフォルト: "WARNING"
* 例: `"FASTMCP_LOG_LEVEL": "ERROR"`

#### `AWS_PROFILE`（オプション） {#aws_profile-optional}

認証に使用するAWSプロファイルを指定します。

* デフォルト: なし（未設定の場合、デフォルトのAWS認証情報を使用します）
* 例: `"AWS_PROFILE": "my-profile"`

#### `AWS_REGION`（オプション） {#aws_region-optional}

EKSクラスターが管理されているAWSリージョンを指定します。このリージョンはすべてのAWSサービスオペレーションで使用されます。

* デフォルト: なし（未設定の場合、デフォルトのAWSリージョンを使用します）
* 例: `"AWS_REGION": "us-west-2"`

#### `EKS_AUTH_MODE`（オプション） {#eks_auth_mode-optional}

Kubernetes APIアクセスの認証モードを指定します。

* 有効な値: `iam`（デフォルト）、`kubeconfig`
* `iam`: STS署名付きURLとともにAWS IAM認証情報を使用します（従来の動作）。AWS認証情報が必要です。
* `kubeconfig`: 認証にローカルのkubeconfigファイルを使用します。OIDC、証明書、execプラグイン、サービスアカウントトークンをサポートします。KubernetesオペレーションにAWS認証情報を必要としません。
* デフォルト: `iam`
* 例: `"EKS_AUTH_MODE": "kubeconfig"`

kubeconfigモードを使用する場合:

* `cluster_name` パラメータはEKSクラスター名を受け付け、対応するkubeconfigコンテキストに解決されます。
* kubeconfigファイルの場所の特定には、`KUBECONFIG` 環境変数または `~/.kube/config` が使用されます。
* kubeconfigがサポートするすべての認証方式（OIDC execプラグイン、クライアント証明書、ベアラートークンなど）が利用可能です。
* AWS固有のツール（CloudWatch、IAM、VPC設定、EKSインサイト、CloudFormation）は、kubeconfigモードでは登録されず、ツール一覧に表示されません。

#### `KUBECONFIG`（オプション） {#kubeconfig-optional}

kubeconfigファイルへのパスを指定します。`EKS_AUTH_MODE=kubeconfig` の場合に使用されます。

* デフォルト: `~/.kube/config`
* 例: `"KUBECONFIG": "/path/to/my/kubeconfig"`

#### `HTTP_PROXY` / `HTTPS_PROXY`（オプション） {#http_proxy--https_proxy-optional}

HTTPおよびHTTPS接続のプロキシ設定を行います。これらの環境変数は、EKS MCPサーバーがプロキシまたはファイアウォールを経由してK8s APIサーバーへのアウトバウンド接続を行う必要がある場合に使用されます。

* デフォルト: なし（未設定の場合は直接接続が使用されます）
* 例: `"HTTP_PROXY": "http://proxy.example.com:8080"`、`"HTTPS_PROXY": "https://proxy.example.com:8080"`
* 注: プロキシサーバーがHTTPとHTTPSの両方のトラフィックを処理する場合は、両方の変数に同じプロキシサーバーを設定できます。

## ツール {#tools}

Amazon EKSクラスターとKubernetesリソースを管理するために、EKS MCPサーバーは以下のツールを提供します。各ツールは特定のアクションを実行し、EKSクラスターとKubernetesワークロードにおける一般的なタスクを自動化するために呼び出すことができます。

### EKSクラスター管理 {#eks-cluster-management}

#### `manage_eks_stacks` {#manage_eks_stacks}

EKSのCloudFormationスタックを管理し、テンプレートの生成、デプロイ、詳細確認、およびEKSクラスターとその基盤インフラストラクチャの削除の操作を提供します。**注**: クラスターの作成が完了するまでには、通常15〜20分かかります。

機能:

* 指定されたクラスター名を埋め込んだ、EKSクラスター用のCloudFormationテンプレートを生成します。
* CloudFormationを使用してEKSクラスターをデプロイし、VPC、サブネット、NATゲートウェイ、IAMロール、ノードプールを含むスタックを作成または更新します。
* 既存のEKS CloudFormationスタックの詳細を確認し、ステータス、出力、作成時刻などの詳細を提供します。
* EKS CloudFormationスタックと関連リソースを削除し、適切なクリーンアップを保証します。
* このツールによって作成されたスタックのみを変更/削除することで、安全性を確保します。

パラメータ:

* operation (generate, deploy, describe, delete), template_file (for generate/deploy), cluster_name

### Kubernetesリソース管理 {#kubernetes-resource-management}

#### `manage_k8s_resource` {#manage_k8s_resource}

個々のKubernetesリソースをさまざまな操作で管理します。

機能:

* Kubernetesの作成、置換、パッチ適用、削除、読み取りの操作をサポートします。
* 名前空間スコープと非名前空間スコープの両方のKubernetesリソースを扱えます。

パラメータ:

* operation (create, replace, patch, delete, read), cluster_name, kind, api_version, name, namespace (optional), body (for create/replace/patch)

#### `apply_yaml` {#apply_yaml}

Kubernetes YAMLマニフェストをEKSクラスターに適用します。

機能:

* 複数ドキュメントのYAMLファイルをサポートします。
* マニフェスト内のすべてのリソースを指定された名前空間に適用します。
* forceがtrueの場合、既存のリソースを更新できます。

パラメータ:

* yaml_path, cluster_name, namespace, force

#### `list_k8s_resources` {#list_k8s_resources}

EKSクラスター内の特定の種類のKubernetesリソースを一覧表示します。

機能:

* メタデータを含むEKSリソースの概要を返します。
* EKSクラスターの名前空間、ラベル、フィールドによるフィルタリングをサポートします。

パラメータ:

* cluster_name, kind, api_version, namespace (optional), label_selector (optional), field_selector (optional)

#### `list_api_versions` {#list_api_versions}

指定されたKubernetesクラスターで利用可能なすべてのAPIバージョンを一覧表示します。

機能:

* Kubernetesクラスター上で利用可能なすべてのAPIバージョンを検出します。
* Kubernetesリソースの管理に使用する正しい `apiVersion` の特定に役立ちます。
* コアAPI（例: "v1"）とAPIグループ（例: "apps/v1"、"networking.k8s.io/v1"）の両方を含みます。

パラメータ:

* cluster_name

### アプリケーションサポート {#application-support}

#### `generate_app_manifest` {#generate_app_manifest}

アプリケーションのデプロイ用にKubernetesマニフェストを生成します。

機能:

* 設定可能なパラメータを使用して、KubernetesのdeploymentおよびserviceのYAMLを生成します。
* ロードバランサーの設定とリソースリクエストをサポートします。
* Kubernetesマニフェストを指定されたディレクトリに出力します。

パラメータ:

* app_name, image_uri, output_dir, port (optional), replicas (optional), cpu (optional), memory (optional), namespace (optional), load_balancer_scheme (optional)

#### `get_pod_logs` {#get_pod_logs}

Kubernetesクラスター内のPodからログを取得します。

機能:

* 時間、行数、バイトサイズによるログのフィルタリングをサポートします。
* Pod内の特定のコンテナからログを取得できます。
* サーバーフラグ `--allow-sensitive-data-access` の有効化が必要です。

パラメータ:

* cluster_name, pod_name, namespace, container_name (optional), since_seconds (optional), tail_lines (optional), limit_bytes (optional), previous (optional)

#### `get_k8s_events` {#get_k8s_events}

特定のKubernetesリソースに関連するイベントを取得します。

機能:

* タイムスタンプ、カウント、メッセージ、理由、レポートコンポーネント、タイプを含むKubernetesイベントの詳細を返します。
* 名前空間スコープと非名前空間スコープの両方のKubernetesリソースをサポートします。
* サーバーフラグ `--allow-sensitive-data-access` の有効化が必要です。

パラメータ:

* cluster_name, kind, name, namespace (optional)

#### `get_eks_vpc_config` {#get_eks_vpc_config}

ハイブリッドノード構成のサポートを含む、EKSクラスターの包括的なVPC設定の詳細を取得します。

機能:

* CIDRブロック、ルートテーブル、サブネット情報を含む詳細なVPC設定を返します
* ハイブリッドノード構成向けのリモートノードおよびPodのCIDR設定を自動的に識別して含めます
* EKSのネットワーキング要件に対するサブネットの容量を検証します
* EKSで使用できない、許可されていないアベイラビリティーゾーン内のサブネットにフラグを立てます
* サーバーフラグ `--allow-sensitive-data-access` の有効化が必要です

パラメータ:

* cluster_name, vpc_id (optional)

### CloudWatch統合 {#cloudwatch-integration}

#### `get_cloudwatch_logs` {#get_cloudwatch_logs}

EKSクラスター内の特定のリソースについて、CloudWatchからログを取得します。

機能:

* リソースタイプ（Pod、ノード、コンテナ）、リソース名、ログタイプに基づいてログを取得します。
* 時間範囲（分、開始/終了時刻）、ログ内容（filter_pattern）、エントリ数によるフィルタリングが可能です。
* クエリ結果に含めるカスタムフィールドの指定をサポートします。
* サーバーフラグ `--allow-sensitive-data-access` の有効化が必要です。

パラメータ:

* cluster_name, log_type (application, host, performance, control-plane, custom), resource_type (pod, node, container, cluster),
resource_name (optional), minutes (optional), start_time (optional), end_time (optional), limit (optional), filter_pattern (optional), fields (optional)

#### `get_cloudwatch_metrics` {#get_cloudwatch_metrics}

Kubernetesリソースについて、CloudWatchからメトリクスを取得します。

機能:

* メトリクス名とディメンションに基づいてメトリクスを取得します。
* CloudWatchの名前空間と時間範囲を指定できます。
* 期間、統計（Average、Sumなど）、データポイントの上限を設定できます。
* きめ細かなメトリクスクエリのために、カスタムディメンションの指定をサポートします。

パラメータ:

* cluster_name, metric_name, namespace, dimensions, minutes (optional), start_time (optional), end_time (optional), limit (optional), stat (optional), period (optional)

#### `get_eks_metrics_guidance` {#get_eks_metrics_guidance}

EKSクラスター内のさまざまなリソースタイプで利用可能なCloudWatchメトリクスに関するガイダンスを提供します。

機能:

* 指定されたリソースタイプで利用可能なContainer Insightsメトリクスの一覧（メトリクス名、ディメンション、説明を含む）を返します。
* `get_cloudwatch_metrics` ツールで使用する正しいディメンションの特定に役立ちます。
* 以下のリソースタイプをサポートします。
  * `cluster`: EKSクラスターのメトリクス（例: cluster_node_count、cluster_failed_node_count）
  * `node`: EKSノードのメトリクス（例: node_cpu_utilization、node_memory_utilization、node_network_total_bytes）
  * `pod`: Kubernetes Podのメトリクス（例: pod_cpu_utilization、pod_memory_utilization、pod_network_rx_bytes）
  * `namespace`: Kubernetes名前空間のメトリクス（例: namespace_number_of_running_pods）
  * `service`: Kubernetesサービスのメトリクス（例: service_number_of_running_pods）

パラメータ:

* resource_type

実装:

`/awslabs/eks_mcp_server/data/eks_cloudwatch_metrics_guidance.json` のデータは、AWSドキュメントの[Container Insightsメトリクステーブル](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-metrics-EKS.html)をスクレイピングするPythonスクリプト（`/awslabs/eks_mcp_server/scripts/update_eks_cloudwatch_metrics_guidance.py`）によって生成されます。このスクリプトの実行には、uvでBeautifulSoup（HTMLコンテンツの解析に使用）をインストールする必要があります: `uv pip install bs4`

### IAM統合 {#iam-integration}

#### `get_policies_for_role` {#get_policies_for_role}

指定されたIAMロールにアタッチされているすべてのポリシー（信頼ポリシー、管理ポリシー、インラインポリシーを含む）を取得します。

機能:

* 指定されたIAMロールの信頼ポリシー（assume role policy）ドキュメントを取得します。
* アタッチされているすべての管理ポリシーを一覧表示し、それらのポリシードキュメントを含めます。
* 埋め込まれているすべてのインラインポリシーを一覧表示し、それらのポリシードキュメントを含めます。

パラメータ:

* role_name

#### `add_inline_policy` {#add_inline_policy}

指定された権限を持つ新しいインラインポリシーをIAMロールに追加します。既存のポリシーは変更しません。新しいポリシーのみを作成し、既存のポリシーを変更するリクエストは拒否します。

機能:

* 指定されたIAMロールに新しいインラインポリシーを作成してアタッチします。
* 誤った変更を防ぐため、ポリシー名がロール上に既に存在する場合はリクエストを拒否します。
* サーバーフラグ `--allow-write` の有効化が必要です。
* 権限を単一のJSONオブジェクト（statement）またはJSONオブジェクトのリスト（statements）として受け付けます。

パラメータ:

* policy_name, role_name, permissions (JSON object or array of objects)

### トラブルシューティング {#troubleshooting}

#### `search_eks_troubleshoot_guide` {#search_eks_troubleshoot_guide}

クエリに基づいて、EKSトラブルシューティングガイドからトラブルシューティング情報を検索します。

機能:

* Amazon EKSの問題に対する詳細なトラブルシューティングガイダンスを提供します。
* EKS Auto Modeのノードプロビジョニング、ブートストラップの問題、コントローラーの障害モードをカバーします。
* 特定された問題に対する症状、段階的な短期的対処、および長期的な修正方法を返します。

パラメータ:

* query

#### `get_eks_insights` {#get_eks_insights}

EKSクラスターの設定やアップグレード準備状況に関する潜在的な問題を特定する Amazon EKS Insights を取得します。

機能:

* MISCONFIGURATIONとUPGRADE_READINESS（アップグレードの阻害要因）の2つのカテゴリでインサイトを返します
* リストモード（すべてのインサイト）と詳細モード（推奨事項を含む特定のインサイト）の両方をサポートします
* 各インサイトのステータス、説明、タイムスタンプを含みます
* 詳細モード使用時に、特定された問題に対処するための詳細な推奨事項を提供します
* インサイトのカテゴリによるオプションのフィルタリングをサポートします
* サーバーフラグ `--allow-sensitive-data-access` の有効化が必要です

パラメータ:

* cluster_name, insight_id (optional), category (optional), next_token (optional)


## セキュリティと権限 {#security--permissions}

### 機能 {#features}

EKS MCP Serverは、以下のセキュリティ機能を実装しています。

1. **AWS認証**: 安全な認証のために、環境のAWS認証情報を使用します。
2. **Kubernetes認証**: Kubernetes APIアクセス用の一時的な認証情報を生成します。
3. **SSL検証**: すべてのKubernetes API呼び出しに対してSSL検証を強制します。
4. **リソースタグ付け**: トレーサビリティのために、作成されたすべてのリソースにタグを付けます。
5. **最小権限**: CloudFormationテンプレートに対して適切な権限を持つIAMロールを使用します。
6. **スタック保護**: CloudFormationスタックが、それを作成したツールによってのみ変更できることを保証します。
7. **クライアントキャッシュ**: セキュリティとパフォーマンスのために、TTLベースの有効期限付きでKubernetesクライアントをキャッシュします。

### 考慮事項 {#considerations}

EKS MCP Serverを使用する際は、以下の点を考慮してください。

* **AWS認証情報**: サーバーには、EKSリソースを作成および管理する権限が必要です。
* **Kubernetesアクセス**: サーバーは、Kubernetes APIアクセス用の一時的な認証情報を生成します。
* **ネットワークセキュリティ**: EKSクラスターに対してVPCとセキュリティグループを適切に設定してください。
* **認証**: Kubernetesリソースに対して適切な認証メカニズムを使用してください。
* **認可**: Kubernetesリソースに対してRBACを適切に設定してください。
* **データ保護**: Kubernetes Secret内の機密データを暗号化してください。
* **ロギングとモニタリング**: EKSクラスターのロギングとモニタリングを有効にしてください。

### 権限 {#permissions}

EKS MCP Serverは、適切なセキュリティ管理策を講じることで本番環境でも使用できます。サーバーはデフォルトで読み取り専用モードで実行されます。これは推奨される設定であり、本番環境では一般的により安全とされています。書き込みアクセスは、必要な場合にのみ明示的に有効にしてください。以下は、読み取り専用モードと書き込みアクセスモードのそれぞれで利用可能なEKS MCPサーバーのツールです。

* **読み取り専用モード（デフォルト）**: `manage_eks_stacks`（operation="describe" の場合）、`manage_k8s_resource`（operation="read" の場合）、`list_k8s_resources`、`get_pod_logs`、`get_k8s_events`、`get_cloudwatch_logs`、`get_cloudwatch_metrics`、`get_policies_for_role`、`search_eks_troubleshoot_guide`、`list_api_versions`、`get_eks_vpc_config`、`get_eks_insights`
* **書き込みアクセスモード**（`--allow-write` が必要）: `manage_eks_stacks`（"generate"、"deploy"、"delete" の場合）、`manage_k8s_resource`（"create"、"replace"、"patch"、"delete" の場合）、`apply_yaml`、`generate_app_manifest`、`add_inline_policy`

#### `autoApprove`（オプション） {#autoapprove-optional}

MCPサーバー定義内の配列で、EKS MCP Serverクライアントによって自動的に承認されるツール名を列挙し、該当するツールについてユーザーの確認を省略します。例:

**Mac/Linuxの場合:**
```
{
  "mcpServers": {
    "awslabs.eks-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.eks-mcp-server@latest"
      ],
      "env": {
        "AWS_PROFILE": "eks-mcp-readonly-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "INFO"
      },
      "autoApprove": [
        "manage_eks_stacks",
        "manage_k8s_resource",
        "list_k8s_resources",
        "get_pod_logs",
        "get_k8s_events",
        "get_cloudwatch_logs",
        "get_cloudwatch_metrics",
        "get_policies_for_role",
        "search_eks_troubleshoot_guide",
        "list_api_versions"
      ]
    }
  }
}
```

**Windowsの場合:**
```
{
  "mcpServers": {
    "awslabs.eks-mcp-server": {
      "command": "uvx",
      "args": [
        "--from",
        "awslabs.eks-mcp-server@latest",
        "awslabs.eks-mcp-server.exe"
      ],
      "env": {
        "AWS_PROFILE": "eks-mcp-readonly-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "INFO"
      },
      "autoApprove": [
        "manage_eks_stacks",
        "manage_k8s_resource",
        "list_k8s_resources",
        "get_pod_logs",
        "get_k8s_events",
        "get_cloudwatch_logs",
        "get_cloudwatch_metrics",
        "get_policies_for_role",
        "search_eks_troubleshoot_guide",
        "list_api_versions"
      ]
    }
  }
}
```

### IAM権限管理 {#iam-permissions-management}

`--allow-write` フラグが有効な場合、EKS MCP Serverは `add_inline_policy` ツールを通じて、EKSリソースに不足しているIAM権限を作成できます。このツールについては以下のとおりです。

* 新しいインラインポリシーのみを作成し、既存のポリシーを変更することは決してありません。
* EKSクラスターの一般的な権限の問題を自動的に修正するのに便利です。
* 注意して使用し、適切にスコープを絞ったIAMロールとともに使用する必要があります。

### ロールスコープに関する推奨事項 {#role-scoping-recommendations}

セキュリティのベストプラクティスに従い、以下を推奨します。

1. 「最小権限」の原則に基づき、EKS MCP Serverが使用する**専用のIAMロールを作成する**。
2. 読み取り専用オペレーションと書き込みオペレーションで**別々のロールを使用する**。
3. サーバーによって作成されたリソースにアクションを限定するために、**リソースタグ付けを実装する**。
4. サーバーによるすべてのAPI呼び出しを監査するために、**AWS CloudTrailを有効にする**。
5. サーバーのIAMロールに付与された権限を**定期的にレビューする**。
6. 削除可能な未使用の権限を特定するために、**IAM Access Analyzerを使用する**。

### 機密情報の取り扱い {#sensitive-information-handling}

**重要**: 許可された入力メカニズムを介してシークレットや機密情報を渡さないでください。

* `apply_yaml` で適用するYAMLファイルにシークレットや認証情報を含めないでください。
* モデルへのプロンプトに機密情報を直接渡さないでください。
* CloudFormationテンプレートやアプリケーションマニフェストにシークレットを含めないでください。
* Kubernetes Secretの作成にMCPツールを使用することは避けてください。シークレットデータをモデルに提供する必要が生じるためです。

**YAMLコンテンツのセキュリティ**:

* 信頼できるソースからのYAMLファイルのみを使用してください。
* サーバーはYAMLコンテンツの検証をKubernetes APIの検証に依存しており、独自の検証は行いません。
* YAMLファイルをクラスターに適用する前に監査してください。

**MCPを介してシークレットを渡す代わりに**:

* 機密情報の保存には AWS Secrets Manager またはParameter Storeを使用してください。
* サービスアカウントに対して適切なKubernetes RBACを設定してください。
* PodからのAWSサービスへのアクセスには、サービスアカウント用のIAMロール（IRSA）を使用してください。

## 一般的なベストプラクティス {#general-best-practices}

* **リソースの命名**: EKSクラスターとKubernetesリソースにはわかりやすい名前を使用してください。
* **名前空間の活用**: 管理しやすいように、リソースを名前空間に整理してください。
* **エラー処理**: ツールのレスポンスに含まれるエラーを確認し、適切に処理してください。
* **リソースのクリーンアップ**: 不要なコストを避けるため、未使用のリソースを削除してください。
* **モニタリング**: クラスターとリソースの状態を定期的に監視してください。
* **セキュリティ**: EKSクラスターに対するAWSのセキュリティベストプラクティスに従ってください。
* **バックアップ**: 重要なKubernetesリソースを定期的にバックアップしてください。

## 一般的なトラブルシューティング {#general-troubleshooting}

* **権限エラー**: AWS認証情報に必要な権限があることを確認してください。
* **CloudFormationエラー**: CloudFormationコンソールでスタック作成エラーを確認してください。
* **Kubernetes APIエラー**: EKSクラスターが実行中でアクセス可能であることを確認してください。
* **ネットワークの問題**: VPCとセキュリティグループの設定を確認してください。
* **クライアントエラー**: MCPクライアントが正しく設定されていることを確認してください。
* **ログレベル**: より詳細なログを取得するには、ログレベルをDEBUGに上げてください。

EKS全般の問題については、[Amazon EKSドキュメント](https://docs.aws.amazon.com/eks/)を参照してください。
