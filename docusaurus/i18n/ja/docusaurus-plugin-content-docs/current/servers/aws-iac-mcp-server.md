---
title: AWS Infrastructure as Code MCPサーバー
---

AWS インフラストラクチャのコード化(Infrastructure as Code)の作成とトラブルシューティングのための MCP サーバーです。ツールには、CloudFormation テンプレートの検証、コンプライアンスチェック、デプロイのトラブルシューティング、CloudFormation ドキュメント検索、公式 CDK ナレッジベースを利用した AWS CDK ドキュメント検索、CDK のコードサンプルとコンストラクト、CDK および CloudFormation のベストプラクティスが含まれます。

## MCP のハイライト {#mcp-highlights}

- **CloudFormation テンプレートをデプロイ前に検証**し、エラーを早期に検出
- インテリジェントな失敗分析と解決ガイダンスにより、**失敗した CloudFormation デプロイをデバッグ**
- AWS のベストプラクティスに照らして、CloudFormation テンプレートの**セキュリティコンプライアンスを確保**
- リソースタイプ、プロパティ、テンプレート構文に関する **CloudFormation ドキュメントを検索**
- **CDK ドキュメントを検索**し、AWS CDK 開発向けの AWS 承認済みコード例を発見
- 一般的な実装パターンのための **CDK コードサンプルとコミュニティコンストラクトを検索**
- 安全で効率的なインフラストラクチャ開発のための **CDK ベストプラクティスにアクセス**
- CloudFormation テンプレートの検証エラーに対して、行番号付きの**具体的な修正提案を取得**
- CloudFormation デプロイのトラブルシューティングのための **CloudTrail ディープリンクにアクセス**


## 機能 {#features}

### テンプレート検証 {#template-validation}
- **構文およびスキーマの検証** - cfn-lint を使用して CloudFormation テンプレートを検証します
- 構文エラー、無効なプロパティ、スキーマ違反を具体的な修正提案付きで検出します

### コンプライアンスチェック {#compliance-checking}
- **セキュリティおよびコンプライアンスルール** - cfn-guard を使用してセキュリティ標準に照らしてテンプレートを検証します
- AWS Guard Rules Registry および Control Tower のプロアクティブコントロールに対してチェックします

### デプロイのトラブルシューティング {#deployment-troubleshooting}
- **インテリジェントな失敗分析** - CloudFormation デプロイの失敗を分析し解決します
- CloudTrail ディープリンク付きで、30 件以上の既知の失敗ケースに対するパターンマッチングを行います

### CloudFormation ドキュメント検索 {#cloudformation-documentation-search}
- **CloudFormation ナレッジへのアクセス** - リソースタイプ、プロパティ、構文について公式 CloudFormation ドキュメントを検索します
- CloudFormation テンプレートの実装ガイダンスと例を見つけられます

### CDK ドキュメント検索 {#cdk-documentation-search}
- **CDK ナレッジへのアクセス** - AWS CDK のドキュメント、API リファレンス、ベストプラクティスを検索します
- CDK API リファレンス、ベストプラクティスガイド、コードサンプルとパターン、CDK-NAG セキュリティチェックにアクセスできます

### CDK コードサンプルとコンストラクト {#cdk-code-samples--constructs}
- **動作するコード例** - 一般的なパターンのための CDK コードサンプルとコミュニティコンストラクトを見つけられます
- 複数のプログラミング言語(TypeScript、Python、Java、C#、Go)を横断して検索できます

### CDK ベストプラクティス {#cdk-best-practices}
- **セキュリティおよび開発ガイドライン** - アプリケーション設定、コーディング、コンストラクト、セキュリティ、テストに関する包括的な CDK ベストプラクティスにアクセスできます
- 安全で効率的なインフラストラクチャのために AWS が推奨するパターンに従えます

## 利用可能な MCP ツール {#available-mcp-tools}

### ドキュメント読み取りツール {#read-documentation-tool}

#### read_iac_documentation_page {#read_iac_documentation_page}
任意の Infrastructure as Code(CDK または CloudFormation)ドキュメントページを取得し、マークダウン形式に変換します。

**このツールの用途:**
- 抜粋だけでなく、CDK ドキュメントページ全体を読む
- CloudFormation リソースタイプのドキュメントとプロパティリファレンス全体を読む
- CloudFormation テンプレートの詳細な構文と例を取得する
- CloudFormation API リファレンスドキュメントにアクセスする
- CloudFormation フックとライフサイクル管理ガイドを読む
- CFN Guard ポリシー検証のルールと構文を確認する
- CloudFormation CLI のドキュメントと使用パターンにアクセスする

### CloudFormation ツール {#cloudformation-tools}

#### validate_cloudformation_template {#validate_cloudformation_template}
cfn-lint を使用して、CloudFormation テンプレートの構文、スキーマ、リソースプロパティを検証します。

**このツールの用途:**
- AI が生成した CloudFormation テンプレートをデプロイ前に検証する
- 各エラーに対して行番号付きの具体的な修正提案を取得する

**パラメータ:**
- `template_content`(必須): 文字列としての CloudFormation テンプレート
- `regions`(任意): 検証対象とする AWS リージョンのリスト
- `ignore_checks`(任意): 無視する cfn-lint チェック ID のリスト

#### check_cloudformation_template_compliance {#check_cloudformation_template_compliance}
cfn-guard を使用して、セキュリティおよびコンプライアンスルールに照らして CloudFormation テンプレートを検証します。

**このツールの用途:**
- テンプレートがセキュリティおよびコンプライアンス要件を満たしていることを確認する
- 違反に対する詳細な修復ガイダンスを取得する

**パラメータ:**
- `template_content`(必須): 文字列としての CloudFormation テンプレート
- `custom_rules`(任意): 適用するカスタム cfn-guard ルール

#### troubleshoot_cloudformation_deployment {#troubleshoot_cloudformation_deployment}
失敗した CloudFormation スタックを分析し、解決ガイダンスを提供します。

**このツールの用途:**
- 30 件以上の既知のケースに対するパターンマッチングでデプロイ失敗を診断する
- CloudTrail ディープリンクと具体的な解決手順を取得する

**パラメータ:**
- `stack_name`(必須): 失敗した CloudFormation スタックの名前
- `region`(必須): スタックが存在する AWS リージョン
- `include_cloudtrail`(任意): CloudTrail 分析を含めるかどうか(デフォルトは true)

#### search_cloudformation_documentation {#search_cloudformation_documentation}
AWS CloudFormation ドキュメントのナレッジベースを検索し、関連するベストプラクティスを返します。

#### get_cloudformation_pre_deploy_validation_instructions {#get_cloudformation_pre_deploy_validation_instructions}
変更セット作成時にテンプレートを検証する、CloudFormation のデプロイ前検証機能の手順を返します。

**パラメータ:**
なし - CLI コマンドと修復ガイダンスを含む JSON を返します。

### CDK ツール {#cdk-tools}

#### search_cdk_documentation {#search_cdk_documentation}
AWS CDK ドキュメントのナレッジベースを検索し、関連する抜粋を返します。

**このツールの用途:**
- CDK のコンストラクト、API、実装パターンに関する具体的な情報を見つける
- 公式 CDK ドキュメントから実装ガイダンスを取得する
- CDK パターンの構文と例を調べる
- ベストプラクティスとアーキテクチャガイドラインを調査する

**ドキュメントソース:**
- AWS CDK API リファレンス
- AWS CDK ベストプラクティスガイド
- AWS CDK コードサンプルとパターン
- CDK-NAG 検証ルール

**パラメータ:**
- `query`(必須): CDK ドキュメントの検索クエリ

**検索のヒント:**
- 具体的なコンストラクト名を使用する(例: "aws-lambda.Function"、"aws-s3.Bucket")
- ターゲットを絞り込むためにサービス名を含める(例: "S3 AND encryption")
- ブール演算子を使用する: "DynamoDB AND table"、"Lambda OR Function"
- 特定のプロパティを検索する: "bucket encryption"、"lambda environment variables"


**パラメータ:**
- `url`(必須): ページ全体の内容を読むための、検索結果に含まれる URL
- `starting_index`(任意): ページネーション用の開始文字インデックス(デフォルト: 0)

#### search_cdk_samples_and_constructs {#search_cdk_samples_and_constructs}
CDK のコードサンプル、例、コンストラクト、パターンのドキュメントを検索します。

**パラメータ:**
- `query`(必須): CDK サンプルとコンストラクトの検索クエリ
- `language`(任意): プログラミング言語フィルター(デフォルト: "typescript")

#### cdk_best_practices {#cdk_best_practices}
アプリケーション設定、コーディング、コンストラクト、セキュリティ、テストに関する CDK ベストプラクティスを提供します。

**パラメータ:**
- なし

## 使用例 {#usage-examples}

### CloudFormation の例 {#cloudformation-examples}

#### テンプレートの検証 {#validate-a-template}
```
Validate this CloudFormation template:
[paste your template content]
```

#### コンプライアンスのチェック {#check-compliance}
```
Check this template for security and compliance issues:
[paste your template content]
```

#### 失敗したデプロイのトラブルシューティング {#troubleshoot-a-failed-deployment}
```
Troubleshoot my CloudFormation stack named "my-app-stack" in us-east-1
```

#### CloudFormation ドキュメントの検索 {#search-cloudformation-documentation}
```
Search CloudFormation documentation for AWS::Lambda::Function properties
```

### CDK の例 {#cdk-examples}

#### CDK ドキュメントの検索 {#search-cdk-documentation}
```
Search CDK documentation for S3 bucket encryption best practices
```

```
Find CDK examples for Lambda function with VPC configuration
```

```
Show me CDK constructs for DynamoDB table with encryption
```

#### Infrastructure as Code ドキュメントページの読み取り {#read-infrastructure-as-code-documentation-page}
```
Read the full CDK documentation for aws-s3.Bucket from this URL: [URL from search results]
```

```
Read the complete CloudFormation documentation for AWS::S3::Bucket from this URL: [URL from search results]
```

#### CDK サンプルとコンストラクトの検索 {#search-cdk-samples-and-constructs}
```
Find CDK code samples for serverless API with TypeScript
```

```
Show me Python CDK examples for API Gateway with Lambda integration
```

#### CDK ベストプラクティスの参照 {#consult-cdk-best-practices}
```
Suggest improvements to my CDK setup based on the best practices
```

```
What are the CDK security best practices for S3 buckets?
```

## 前提条件 {#prerequisites}

1. [Astral](https://docs.astral.sh/uv/getting-started/installation/) または [GitHub README](https://github.com/astral-sh/uv#installation) から `uv` をインストールします
2. `uv python install 3.10` を使用して Python をインストールします
3. AWS 認証情報を設定します:
   - AWS CLI 経由: `aws configure`
   - または環境変数を設定(AWS_ACCESS_KEY_ID、AWS_SECRET_ACCESS_KEY、AWS_DEFAULT_REGION)
4. IAM ロールまたはユーザーに、CloudFormation および CloudTrail へのアクセスに必要な権限があることを確認します

## インストール {#installation}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.aws-iac-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-iac-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-named-profile%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.aws-iac-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLWlhYy1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJBV1NfUFJPRklMRSI6InlvdXItbmFtZWQtcHJvZmlsZSIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifSwiZGlzYWJsZWQiOmZhbHNlLCJhdXRvQXBwcm92ZSI6W119) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Infrastructure%20as%20Code%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-iac-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-named-profile%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

MCP クライアントの設定で MCP サーバーを構成します(例: Kiro の場合は `~/.kiro/settings/mcp.json` を編集します):

```json
{
  "mcpServers": {
    "awslabs.aws-iac-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-iac-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-named-profile",
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Windows でのインストール {#windows-installation}

Windows ユーザーの場合、MCP サーバーの設定形式は少し異なります:

```json
{
  "mcpServers": {
    "awslabs.aws-iac-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.aws-iac-mcp-server@latest",
        "awslabs.aws-iac-mcp-server.exe"
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

または、`docker build -t awslabs/aws-iac-mcp-server .` の成功後に docker を使用します:

```file
# fictitious `.env` file with AWS temporary credentials
AWS_ACCESS_KEY_ID=ASIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_SESSION_TOKEN=AQoEXAMPLEH4aoAH0gNCAPy...truncated...zrkuWJOgQs8IZZaIv2BXIa2R4Olgk
```

注: Docker でのインストールは任意です

```json
{
  "mcpServers": {
    "awslabs.aws-iac-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--interactive",
        "--env",
        "AWS_PROFILE=your-aws-profile",
        "--env",
        "FASTMCP_LOG_LEVEL=ERROR",
        "--volume",
        "${HOME}/.aws:/root/.aws:ro",
        "awslabs/aws-iac-mcp-server:latest"
      ],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

注: 認証情報はホスト側で常に最新の状態に保つ必要があります

## セキュリティに関する考慮事項 {#security-considerations}

⚠️ **プライバシーに関する通知**: この MCP サーバーは、お客様の認証情報を使用して AWS API 呼び出しを実行し、そのレスポンスデータをサードパーティの AI モデルプロバイダー(例: Kiro、Claude Desktop、Cursor、VS Code)と共有します。このツールを AWS リソースで使用する際は、AI プロバイダーのデータ取り扱い方針を理解し、組織のセキュリティおよびプライバシー要件への準拠を確保する責任はユーザーにあります。

### IAM 権限 {#iam-permissions}

この MCP サーバーには、以下の AWS 権限が必要です:

**テンプレート検証およびコンプライアンスの場合:**
- AWS 権限は不要です(ローカル検証のみ)

**デプロイのトラブルシューティングの場合:**
- `cloudformation:DescribeStacks`
- `cloudformation:DescribeStackEvents`
- `cloudformation:DescribeStackResources`
- `cloudtrail:LookupEvents`(CloudTrail ディープリンク用)

IAM ポリシーの例:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudformation:DescribeStacks",
        "cloudformation:DescribeStackEvents",
        "cloudformation:DescribeStackResources",
        "cloudtrail:LookupEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

## 開発 {#development}

### ローカル開発 {#local-development}

```bash
# Clone the repository
git clone https://github.com/awslabs/mcp.git
cd mcp/src/aws-iac-mcp-server

# Install dependencies
uv sync

# Run the server
uv run awslabs.aws-iac-mcp-server
```

### テストの実行 {#running-tests}

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=awslabs.aws_iac_mcp_server --cov-report=term-missing
```

## コントリビューション {#contributing}

このプロジェクトへの貢献方法のガイドラインについては、[CONTRIBUTING.md](https://github.com/awslabs/mcp/blob/main/CONTRIBUTING.md) を参照してください。

## ライセンス {#license}

このプロジェクトは Apache-2.0 ライセンスの下でライセンスされています。詳細については [LICENSE](https://github.com/awslabs/mcp/blob/main/src/aws-iac-mcp-server/LICENSE) ファイルを参照してください。
