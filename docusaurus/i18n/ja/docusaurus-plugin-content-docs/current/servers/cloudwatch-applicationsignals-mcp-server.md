---
title: "CloudWatch Application Signals MCPサーバー"
---

[AWS Application Signals](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Signals.html) を使用して AWS サービスを監視・分析するための包括的なツールを提供する MCP (Model Context Protocol) サーバーです。

このサーバーは、Kiro、Claude、GitHub Copilot などの AI アシスタントが、サービスの健全性の監視、パフォーマンスメトリクスの分析、SLO コンプライアンスの追跡、そして高度な監査機能と根本原因分析を備えた分散トレーシングによる問題調査を支援できるようにします。

## 主な機能 {#key-features}

1. **包括的なサービス監査** - 組み込みの APM の専門知識により、サービス全体の健全性を監視し、根本原因を診断し、実行可能な修正を提案します
2. **高度な SLO コンプライアンス監視** - 違反検出と根本原因分析により、サービスレベル目標を追跡します
3. **オペレーションレベルのパフォーマンス分析** - 特定の API エンドポイントやオペレーションを詳細に調査します
4. **グループレベルの監視** - チームベースのワークフロー向けに、サービスグループ全体の健全性、依存関係、変更を評価します
5. **100% のトレース可視性** - Transaction Search 経由で OpenTelemetry のスパンデータをクエリし、完全なオブザーバビリティを実現します
6. **マルチサービス分析** - 自動バッチ処理により複数のサービスを同時に監査します
7. **自然言語によるインサイト** - 自然言語クエリを通じて、テレメトリデータからビジネスインサイトを生成します
8. **Synthetics Canary 分析** - 既知のランタイムおよび環境の問題に対するナレッジベースを活用した推奨事項により、Canary の失敗を詳細に調査します
9. **Canary とサービスの相関分析** - 監査対象のサービスやグループに関連付けられた Synthetics Canary を自動的に検出してレポートします

## 前提条件 {#prerequisites}

1. [AWS アカウントにサインアップ](https://aws.amazon.com/free/?trk=78b916d7-7c94-4cab-98d9-0ce5e648dd5f&sc_channel=ps&ef_id=Cj0KCQjwxJvBBhDuARIsAGUgNfjOZq8r2bH2OfcYfYTht5v5I1Bn0lBKiI2Ii71A8Gk39ZU5cwMLPkcaAo_CEALw_wcB:G:s&s_kwcid=AL!4422!3!432339156162!e!!g!!aws%20sign%20up!9572385111!102212379327&gad_campaignid=9572385111&gbraid=0AAAAADjHtp99c5A9DUyUaUQVhVEoi8of3&gclid=Cj0KCQjwxJvBBhDuARIsAGUgNfjOZq8r2bH2OfcYfYTht5v5I1Bn0lBKiI2Ii71A8Gk39ZU5cwMLPkcaAo_CEALw_wcB)します
2. アプリケーションで [Application Signals を有効化](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Monitoring-Sections.html)します
3. [Astral](https://docs.astral.sh/uv/getting-started/installation/) または [GitHub README](https://github.com/astral-sh/uv#installation) から `uv` をインストールします
4. `uv python install 3.10` で Python をインストールします

## 利用可能なツール {#available-tools}

### 有効化とセットアップのツール {#enablement--setup-tools}

#### 1. **`get_enablement_guide`** - Application Signals 有効化アシスタント {#1-get_enablement_guide---application-signals-enablement-assistant}
**AI 主導の自律的なコード変更によるオブザーバビリティの有効化**

エージェント型の有効化フローで AWS Application Signals を有効にするには、このツールを使用します。ツールは厳選されたガイドを返し、AI エージェントがそれに従って IaC、Dockerfile、依存関係ファイルに必要なコード変更を自律的に行います。ガイドは、サービスのプラットフォーム（EC2、ECS、Lambda、EKS）とプログラミング言語（Python、Node.js、Java）に合わせてカスタマイズされます。

**前提条件:**
- このツールを使用する前に、AWS アカウントとリージョンで **Start Discovery を有効化**してください
  - これは **AWSServiceRoleForCloudWatchApplicationSignals** サービスにリンクされたロールを作成する 1 回限りのセットアップです
  - CloudWatch コンソール → Services → 「Start discovering your Services」→ Enable Application Signals に移動します
  - 詳しい手順は[有効化ガイド](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Application-Signals-Enable.html)を参照してください

**仕組み:**
- 厳選された有効化ガイドを AI エージェント向けのプロンプトとして返します
- AI エージェントはガイドに従ってコードを自律的に変更します
- ガイドは、追加の質問ができるナレッジとしても機能します
- 有効化プロセス全体を通じてインタラクティブな Q&A をサポートします

**このツールを使用する場面:**
- AWS サービスに対してオブザーバビリティ、監視、または Application Signals を有効にする
- AWS 上のアプリケーションに自動計装をセットアップする
- EC2、ECS、Lambda、または EKS で実行されているサービスを計装する
- AWS アプリケーションにトレーシング、メトリクス、テレメトリを追加する

**要件:**
- IaC ファイル、Dockerfile、依存関係ファイルへの書き込み権限
- プラットフォームは次のいずれかである必要があります: `ec2`、`ecs`、`lambda`、`eks`
- 言語は次のいずれかである必要があります: `python`、`nodejs`、`java`

**推奨事項:**
- IaC とアプリケーションのディレクトリの両方に絶対パスを使用します（AI エージェントにとって曖昧さが少なくなります）
- 有効化を迅速に進めるため、最初のプロンプトで両方のディレクトリパスを指定します

**ベストプラクティスのプロンプト:**

良いプロンプト（具体的で完全）:
```
"Enable Application Signals for my Python service running on ECS.
My app code is in /home/user/myapp and IaC is in /home/user/myapp/infrastructure"

"I want to add observability to my Node.js Lambda function.
The Lambda code is at /Users/dev/checkout-service and
the CDK infrastructure is at /Users/dev/checkout-service/cdk"

"Help me instrument my Java application on EC2 with Application Signals.
Application directory: /opt/apps/payment-api
Terraform code: /opt/apps/payment-api/terraform"
```

効果の低いプロンプト:
```
"Enable monitoring for my app"
→ Missing: platform, language, paths

"Enable Application Signals. My code is in ./src and IaC is in ./infrastructure"
→ Problem: Relative paths instead of absolute paths

"Enable Application Signals for my ECS service at /home/user/myapp"
→ Missing: programming language
```

クイックテンプレート:
```
"Enable Application Signals for my [LANGUAGE] service on [PLATFORM].
App code: [ABSOLUTE_PATH_TO_APP]
IaC code: [ABSOLUTE_PATH_TO_IAC]"
```

### 🥇 主要な監査ツール（最初に使用するツール） {#-primary-audit-tools-use-these-first}

#### 1. **`audit_services`** ⭐ **主要なサービス監査ツール** {#1-audit_services--primary-service-audit-tool}
**AWS サービスの包括的な健全性監査と監視のための最重要ツール**

- サービスレベルのあらゆる監査タスクでは、**まずこのツールを使用してください**
- 実行可能なインサイトと推奨事項を伴う包括的な健全性評価
- 自動バッチ処理によるマルチサービス分析（1〜100 以上のサービスを同時に監査）
- 違反の自動検出を備えた SLO コンプライアンス監視
- トレース、ログ、メトリクスの相関による根本原因分析
- 深刻度による問題の優先順位付け（クリティカル、警告、情報の各所見）
- **ワイルドカードパターンのサポート**: `*payment*` を使ってサービスを自動検出できます
- **Synthetics Canary との相関**: 監査対象サービスの Canary の健全性を自動的に検出してレポートします
- 複数ターゲットに対する高速実行のためにパフォーマンスを最適化

**主なユースケース:**
- `audit_services(service_targets='[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*"}}}]')` - すべてのサービスを監査
- `audit_services(service_targets='[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*payment*"}}}]')` - 決済サービスを監査
- `audit_services(..., auditors="all")` - すべての監査項目による包括的な根本原因分析

#### 2. **`audit_slos`** ⭐ **主要な SLO 監査ツール** {#2-audit_slos--primary-slo-audit-tool}
**SLO コンプライアンス監視と違反分析のための最重要ツール**

- `get_slo()` を使用した後の SLO 根本原因分析に**推奨されるツール**です
- 個別のトレースツールよりもはるかに包括的で、統合された分析を提供します
- トレース、ログ、メトリクス、依存関係を 1 回の監査に統合します
- 優先順位付けされた所見を伴う SLO 違反の自動検出
- **ワイルドカードパターンのサポート**: `*payment*` を使って SLO を自動検出できます
- 多面的な分析に基づく実行可能な推奨事項

**主なユースケース:**
- `audit_slos(slo_targets='[{"Type":"slo","Data":{"Slo":{"SloName":"*"}}}]')` - すべての SLO を監査
- `audit_slos(..., auditors="all")` - SLO 違反に対する包括的な根本原因分析

#### 3. **`audit_service_operations`** 🥇 **主要なオペレーション監査ツール** {#3-audit_service_operations--primary-operation-audit-tool}
**オペレーション固有の分析とパフォーマンス調査に最も推奨されるツール**

- オペレーションレベルの監査では **audit_services() よりも推奨**されます
- サービス全体の平均ではなく、対象オペレーションの挙動を正確にターゲティング
- 具体的なエラートレースと依存関係の障害を伴う実行可能なインサイト
- 正確なスタックトレースとタイムアウト箇所を含むコードレベルの詳細
- **ワイルドカードパターンのサポート**: `*GET*` で特定のオペレーションタイプを指定できます
- 他のオペレーションによるノイズを排除する焦点を絞った分析

**主なユースケース:**
- `audit_service_operations(operation_targets='[{"Type":"service_operation","Data":{"ServiceOperation":{"Service":{"Type":"Service","Name":"*payment*"},"Operation":"*GET*","MetricType":"Latency"}}}]')` - 決済サービスの GET オペレーションを監査
- `audit_service_operations(..., auditors="all")` - 特定のオペレーションに対する根本原因分析

### 📊 サービス検出・情報ツール {#-service-discovery--information-tools}

#### 4. **`list_monitored_services`** - サービス検出ツール {#4-list_monitored_services---service-discovery-tool}
**オプションのツール** - `audit_services()` はワイルドカードパターンを使用してサービスを自動検出できます

- 環境内で監視されているすべてのサービスの詳細な概要を取得します
- 手動で監査ターゲットを構築するために、特定のサービス名や環境を検出します
- **推奨**: 包括的な検出と分析を同時に行うには、代わりにワイルドカードパターン付きの `audit_services()` を使用してください

### 🎯 SLO 管理ツール {#-slo-management-tools}

#### 5. **`get_slo`** - SLO 設定の詳細 {#5-get_slo---slo-configuration-details}
**詳細な調査の前に SLO 設定を理解するために不可欠**

- 包括的な SLO 設定の詳細（メトリクス、しきい値、目標）
- さらなる調査のためのオペレーション名と主要な属性
- メトリクスタイプ（LATENCY または AVAILABILITY）と比較演算子
- **次のステップ**: 根本原因分析には `auditors="all"` を指定した `audit_slos()` を使用します

#### 6. **`list_slos`** - SLO 検出 {#6-list_slos---slo-discovery}
**Application Signals のすべてのサービスレベル目標を一覧表示**

- アカウント内のすべての SLO の名前と ARN を含む完全なリスト
- サービス属性による SLO のフィルタリング
- 作成日時やオペレーション名を含む基本的な SLO 情報
- SLO の検出や、他のツールで使用する SLO 名の特定に便利です

### 📈 メトリクス・パフォーマンスツール {#-metrics--performance-tools}

#### 7. **`query_service_metrics`** - CloudWatch メトリクス分析 {#7-query_service_metrics---cloudwatch-metrics-analysis}
**特定の Application Signals サービスの CloudWatch メトリクスを取得**

- サービスのパフォーマンス（レイテンシー、スループット、エラー率）を分析します
- 標準統計とパーセンタイルの両方で時間の経過に伴うトレンドを表示します
- 時間範囲に基づく粒度の自動調整
- 最新のデータポイントとタイムスタンプを含むサマリー統計

### 🔍 高度なトレース・ログ分析ツール {#-advanced-trace--log-analysis-tools}

#### 8. **`search_transaction_spans`** - 100% のトレース可視性 {#8-search_transaction_spans---100-trace-visibility}
**Transaction Search 経由で OpenTelemetry のスパンデータをクエリ（100% サンプリングされたデータ）**

- X-Ray の 5% サンプリングに対して **100% サンプリングされたデータ**により、より正確な結果が得られます
- CloudWatch Logs の `@data_format = "AWS-OTEL-TRACE-V1"` デフォルトフィールドインデックスを使用して、すべてのロググループにわたって OpenTelemetry のスパンをクエリします。単一のロググループに絞り込むには `log_group_name` を渡します
- ビジネスパフォーマンスのインサイトとサマリーを生成します
- **重要**: コンテキストの肥大化を防ぐため、クエリには必ず limit を含めてください

**クエリ例:**
```
FILTER attributes.aws.local.service = "payment-service" and attributes.aws.local.environment = "eks:production"
| STATS avg(duration) as avg_latency by attributes.aws.local.operation
| LIMIT 50
```

#### 9. **`get_xray_trace`** - X-Ray トレース検索（ダウンストリーム依存関係分析） {#9-get_xray_trace---x-ray-trace-lookup-downstream-dependency-analysis}
**トレース ID を指定して特定の X-Ray トレースを検索し、ダウンストリームの依存関係呼び出しを分析**

- すべてのダウンストリーム呼び出しをレイテンシー、エラー、フォルトの状態とともに示す、完全な X-Ray トレースデータを取得します
- OTel、X-Ray、または生の 16 進数形式で、カンマ区切りの 1 つ以上のトレース ID（1 回の呼び出しにつき最大 5 件）を受け付けます
- **主な用途**: `get_incident_root_cause()` が `telemetry_correlation.trace_id` を提示した後に、ダウンストリームの依存関係を掘り下げる
- AWS マネージドサービスのセグメント（`namespace: "aws"`）と計装済みのリモートサービス（`namespace: "remote"`）を区別できるため、依存関係のチェーンをたどって真の根本原因に到達できます
- **注**: X-Ray データは 5% サンプリングです — 問題の発見には `get_service_health_overview()` / `get_recent_incidents()` を優先し、このツールは対象を絞ったトレースの掘り下げに使用してください

#### 10. **`analyze_canary_failures`** - 包括的な Canary 失敗分析 {#10-analyze_canary_failures---comprehensive-canary-failure-analysis}
**根本原因の特定を伴う CloudWatch Synthetics Canary の失敗の詳細調査**

- 問題の詳細な掘り下げを伴う包括的な Canary 失敗分析
- 過去のパターンと特定のインシデントの詳細を分析します
- ログ、スクリーンショット、HAR ファイルを含む包括的なアーティファクト分析を取得します
- AWS のデバッグ手法に基づく実行可能な推奨事項を受け取ります
- Canary の失敗を Application Signals のテレメトリデータと関連付けます
- サービスの依存関係全体でパフォーマンス低下と可用性の問題を特定します

**主な機能:**
- **失敗パターン分析**: 繰り返し発生する失敗モードや時間的なパターンを特定します
- **アーティファクトの詳細分析**: 根本原因を探るために Canary のログ、スクリーンショット、ネットワークトレースを分析します
- **サービス相関**: Application Signals を使用して、Canary の失敗をアップストリーム/ダウンストリームのサービスの問題に関連付けます
- **パフォーマンスインサイト**: レイテンシーの急上昇、フォルト率、接続の問題を検出します
- **実行可能な修復策**: AWS の運用ベストプラクティスに基づく具体的な手順を提供します
- **IAM 分析**: Canary のよくあるアクセス問題について IAM ロールと権限を検証します
- **バックエンドサービス統合**: Canary の失敗をバックエンドサービスのエラーや例外と関連付けます
- **ナレッジベースによる推奨事項**: 失敗パターンを、既知の Synthetics ランタイムおよび環境の問題を集約した厳選されたナレッジベースと自動的に照合し、的を絞った修正の推奨事項を提供します

**パラメータ:**
- `canary_name`（必須）: 分析する CloudWatch Synthetics Canary の名前
- `region`（オプション）: Canary がデプロイされている AWS リージョン
- `description`（オプション）: ユーザーが経験している問題の説明。Canary のエラーログだけでは十分なコンテキストが得られない場合でも、これをナレッジベースと照合して関連する推奨事項を提示します。例: 「コンソールに実行結果が表示されない」「ビジュアルモニタリングのベースラインがリセットされ続ける」「ランタイムアップグレード後に CloudFormation のロールバックが失敗した」

**よくあるユースケース:**
- インシデント対応: 障害発生時における Canary 失敗の迅速な診断
- パフォーマンス調査: レイテンシーと可用性の低下の把握
- 依存関係分析: どのサービスが Canary の失敗を引き起こしているかの特定
- 過去のトレンド分析: プロアクティブな改善に向けた長期的な失敗パターンの分析
- 根本原因分析: 完全なコンテキストを伴う特定の失敗シナリオの詳細調査
- インフラストラクチャの問題: S3 アクセス、VPC 接続、ブラウザターゲットの問題の診断
- バックエンドサービスのデバッグ: Canary の成功に影響するアプリケーションコードの問題の特定
- 既知の問題の検出: 既知のランタイムバグを自動的に特定し、的を絞った修正の推奨事項を取得

#### 11. **`list_canaries`** - Canary の検出とステータス {#11-list_canaries---canary-discovery-and-status}
**アカウント内のすべての CloudWatch Synthetics Canary を一覧表示**

- すべての Canary とその現在のステータス（Running、Stopped、Error）を検出します
- 各 Canary のスケジュール、ランタイムバージョン、最終実行時刻を表示します
- `analyze_canary_failures()` で詳細に調査する前に Canary を特定するのに便利です
- 大規模なアカウントで LLM のコンテキストウィンドウが肥大化しないよう、出力には上限が設けられています

**パラメータ:**
- `region`（オプション）: クエリする AWS リージョン（デフォルトは設定済みのリージョン）
- `max_results`（オプション）: 表示する Canary の最大数（デフォルト: 20、最大: 200）

**主なユースケース:**
- `list_canaries()` - デフォルトリージョンの Canary を一覧表示（最初の 20 件）
- `list_canaries(region="eu-west-1")` - 特定のリージョンの Canary を一覧表示
- `list_canaries(max_results=100)` - 最大 100 件の Canary を一覧表示

#### 12. **`list_change_events`** - AWS Application Signals 変更イベントクエリ {#12-list_change_events---aws-application-signals-change-event-query}
**AWS Application Signals の変更イベントをクエリし、インフラストラクチャやアプリケーションの変更をサービスのパフォーマンス問題と関連付け**

このツールは、2 つの補完的な API を通じて AWS Application Signals の変更検出機能へのアクセスを提供します。
- **ListEntityEvents**: インシデント調査と根本原因分析のための包括的な変更履歴
- **ListServiceStates**: ステータス監視のための現在のサービス状態情報

**主な機能:**
- **変更の相関**: デプロイ、設定変更、インフラストラクチャの変更をパフォーマンス問題に関連付けます
- **タイムライン分析**: インシデント、アラーム、SLO 違反に至るイベントの正確なタイムラインを構築します
- **サービス固有のフィルタリング**: Application Signals のサービス属性を使用して、特定のサービスへの変更に焦点を絞ります
- **複数の変更タイプの追跡**: デプロイイベント、設定更新、インフラストラクチャのスケーリング、その他の変更を監視します
- **インシデント調査**: サービスのパフォーマンスが低下した際の根本原因分析に不可欠です

**API の選択ガイド:**
- **comprehensive_history=True（デフォルト）**: ListEntityEvents API を使用します
  - **答えられる質問**: 「サービスにどのような変更があったか?」 - 包括的な変更履歴
  - **最適な用途**: インシデント調査、変更の相関、根本原因分析、タイムラインの再構築
  - **返される内容**: 時間範囲内のすべての変更イベント（デプロイ、設定、スケーリング）の完全な時系列リスト
  - **使用する場面**: 発生したすべての変更を確認し、パフォーマンス問題と関連付ける必要がある場合

- **comprehensive_history=False**: ListServiceStates API を使用します
  - **答えられる質問**: 「サービスに何か変更があったか?」 - 現在の変更ステータス
  - **最適な用途**: サービスステータスの監視、最近の変更の有無の確認、現在の状態のトラブルシューティング
  - **返される内容**: サービスの最後のデプロイやその他の変更状態に関する情報。サービスのパフォーマンスに影響した可能性のある最近の変更を可視化します
  - **使用する場面**: 完全な履歴を必要とせず、最近の変更の有無をすばやく確認したい場合

**よくあるユースケース:**
1. **アラームをきっかけとした調査**: 「checkout-service のアラームが発生している。最近何が変わった?」
2. **Canary 失敗分析**: 「checkout-canary が失敗している。関連しそうな最近の変更を見せて。」
3. **ログベースのエラー調査**: 「payment-service のログにエラーが出ている。このエラーの前にどんなデプロイがあった?」
4. **サービス変更履歴**: 「過去 24 時間の user-authentication-service へのすべての変更を見せて。」
5. **SLO 違反のタイムライン**: 「午後 3 時に SLO 違反があった。そこに至るまでにどんな変更があった?」
6. **デプロイ影響分析**: 「午後 2 時のデプロイがパフォーマンス低下を引き起こした?」

**他のツールとの統合:**
- **audit_services() を強化**: サービスの健全性の問題に対して変更のコンテキストを提供します
- **audit_slos() と連携**: 変更を SLO 違反分析に関連付けます
- **audit_service_operations() をサポート**: オペレーションのパフォーマンス調査にタイムラインのコンテキストを追加します
- **analyze_canary_failures() を補完**: Canary の問題に対してデプロイの相関を提供します

#### 13. **`list_slis`** - レガシー SLI ステータスレポート（特化ツール） {#13-list_slis---legacy-sli-status-report-specialized-tool}
**サービス監査の主要ツールとしては `audit_services()` を使用してください**

- サマリー件数（合計、正常、違反、データ不足）を示す基本レポート
- SLO 名を含む違反サービスのシンプルなリスト
- **重要**: あらゆるサービス監査タスクでは、`audit_services()` が主要かつ推奨のツールです
- レガシーの SLI ステータスレポート形式が特に必要な場合にのみ、このツールを使用してください

### 🏢 グループレベル監視ツール {#-group-level-monitoring-tools}

#### 14. **`list_group_services`** - グループサービス検出 {#14-list_group_services---group-service-discovery}
**特定のグループに属するすべてのサービスを検出**

- ワイルドカード（`*payment*`）に対応したグループ名でサービスを一覧表示します
- グループのメンバーシップの詳細とソース（TAG、OTEL など）を表示します
- チームの所有権やサービスの構成を把握するのに便利です

**主なユースケース:**
- `list_group_services(group_name="Payments")` - Payments グループのすべてのサービスを一覧表示
- `list_group_services(group_name="*prod*")` - すべての本番グループを検索

#### 15. **`audit_group_health`** - グループ健全性監視 {#15-audit_group_health---group-health-monitoring}
**グループ内のすべてのサービスに対する包括的な健全性評価**

- SLO とメトリクスを使用した健全性の自動検出
- フォルト、エラー、レイテンシーのしきい値を設定可能
- サービスを Healthy、Warning、Critical、Unknown に分類します
- 不健全なサービスに対して実行可能な推奨事項を提供します
- **Synthetics Canary 統合**: グループ内のサービスに対する Canary の健全性を自動的に検出してレポートします

**主なユースケース:**
- `audit_group_health(group_name="Payments")` - すべての決済サービスを監査
- `audit_group_health(group_name="Frontend", fault_threshold_critical=10.0)` - カスタムしきい値

#### 16. **`get_group_dependencies`** - グループ依存関係マッピング {#16-get_group_dependencies---group-dependency-mapping}
**サービスグループ内およびグループ間の依存関係をマッピング**

- グループ内の依存関係（サービス同士の呼び出し）を特定します
- グループ情報を伴うグループ間の依存関係を検出します
- 外部の AWS サービスへの依存関係（DynamoDB、S3 など）を一覧表示します

**主なユースケース:**
- `get_group_dependencies(group_name="Payments")` - 決済サービスの依存関係をマッピング
- サービスアーキテクチャと影響範囲の把握に便利です

#### 17. **`get_group_changes`** - グループ変更追跡 {#17-get_group_changes---group-change-tracking}
**グループ全体のデプロイを追跡**

- 最近のデプロイを一覧表示します
- 分析しやすいように変更をサービスごとにグループ化します
- デプロイとインシデントの関連付けに便利です
- カスタムの時間範囲をサポートします

**主なユースケース:**
- `get_group_changes(group_name="Payments")` - 過去 24 時間の最近のデプロイ
- `get_group_changes(group_name="API", start_time="2024-01-15 00:00:00")` - 指定時刻以降のデプロイ

#### 18. **`list_grouping_attribute_definitions`** - グループ設定 {#18-list_grouping_attribute_definitions---group-configuration}
**すべてのカスタムグルーピング属性定義を一覧表示**

- 設定済みのグルーピング属性（Team、BusinessUnit など）を表示します
- ソースキー（AWS タグ、OTEL 属性）を表示します
- 各グルーピング属性のデフォルト値を表示します
- 利用可能なグループの把握に便利です

### 🛰️ ServiceEvents テレメトリツール {#-serviceevents-telemetry-tools}

ServiceEvents（CloudWatch Logs の `incident_snapshot` レコード）と CloudWatch Metrics V2（PromQL）をソースとする、インシデントを考慮した健全性・パフォーマンス・デプロイのテレメトリです。広範な健全性/パフォーマンス調査はここから始めてください — これらのツールは、監査ツールでは表面化しないインシデントイベントを明らかにします。

**健全性・インシデントツール**

- `get_service_health_overview` — **一般的な健全性/パフォーマンスに関する質問（「何か問題ある?」「アプリは正常?」）の主要なエントリポイント**。SLO 違反、最近のインシデントイベント、エラーが多い上位の関数を 1 回の高速な呼び出しに集約します。
- `get_recent_incidents` — 最近のインシデント（エラー、タイムアウト、遅いリクエスト）の軽量なリスト。ServiceEvents のインシデントが存在しない場合は、Application Signals のトレース所見にフォールバックします。
- `get_incident_root_cause` — 1 つのインシデント `snapshot_id` の完全な詳細。例外/スタックトレースのコンテキストに加え、計装で取得できた場合は関数ごとの `call_tree` も含みます。

**関数・エンドポイントテレメトリ**

- `list_monitored_functions` — サービスについてテレメトリ（呼び出し数、エラー数、平均実行時間）が取得された関数を一覧表示します。
- `get_function_metrics` — 関数ごとのメトリクスの詳細。エンドポイント/オペレーションでフィルタリングできます。
- `search_functions_by_name` — 名前の部分文字列で計装済みの関数を検索します。
- `get_endpoint_performance` — エンドポイント/オペレーションの RED（レート、エラー、実行時間）パフォーマンスサマリー。

**デプロイ**

- `find_deployment` — 最近のデプロイイベントを特定します。返された `hours_since_deployment` を使用して、健全性/インシデントのクエリをデプロイ後の期間に絞り込みます。

### 🌐 CloudWatch RUM ツール {#-cloudwatch-rum-tools}

CloudWatch RUM のデータを使用して、Web およびモバイルアプリケーション全体で実際のユーザー体験を監視します。

> **前提条件:** ほとんどの RUM 分析アクションでは、アプリモニターで CloudWatch Logs が有効になっている必要があります（`CwLogEnabled=true`）。セットアップの確認には `check_data_access` を使用してください。

すべての RUM 機能は、`action` パラメータを持つ単一の **`query_rum_events`** ツールを通じて公開されています。

```
query_rum_events(action="<action_name>", app_monitor_name="my-app", ...)
```

#### アクションリファレンス {#actions-reference}

| アクション | 説明 | 必須パラメータ |
|--------|-------------|-----------------|
| **検出** | | |
| `check_data_access` | アプリモニターの設定を検査し、問題を検出 | `app_monitor_name` |
| `list_monitors` | すべてのアプリモニターを一覧表示 | *（なし）* |
| `get_monitor` | アプリモニターの完全な設定を取得 | `app_monitor_name` |
| `list_tags` | アプリモニターのタグを一覧表示 | `resource_arn` |
| `get_policy` | リソースベースのポリシーを取得 | `app_monitor_name` |
| **分析** *（CW Logs が必要）* | | |
| `query` | カスタムの Logs Insights クエリを実行 | `app_monitor_name`, `query_string`, `start_time`, `end_time` |
| `health` | クイック健全性監査（エラー、遅いページ、セッション） | `app_monitor_name`, `start_time`, `end_time` |
| `errors` | メッセージおよびページ別の JS/HTTP エラー | `app_monitor_name`, `start_time`, `end_time` |
| `performance` | 良好/要改善/不良の評価付きのページロードと Core Web Vitals | `app_monitor_name`, `start_time`, `end_time` |
| `sessions` | ブラウザ/OS/デバイス情報付きの最近のセッション | `app_monitor_name`, `start_time`, `end_time` |
| `session_detail` | 単一セッションの完全なイベントタイムライン | `app_monitor_name`, `session_id`, `start_time`, `end_time` |
| `page_views` | 表示回数の多い上位ページ | `app_monitor_name`, `start_time`, `end_time` |
| `timeseries` | 時間帯ごとのトレンド（エラー、パフォーマンス、セッション） | `app_monitor_name`, `start_time`, `end_time` |
| `locations` | 国別のセッションとパフォーマンス | `app_monitor_name`, `start_time`, `end_time` |
| `http_requests` | レイテンシーとエラー率付きの上位 HTTP リクエスト | `app_monitor_name`, `start_time`, `end_time` |
| `resources` | 所要時間とサイズ別の上位リソースリクエスト | `app_monitor_name`, `start_time`, `end_time` |
| `page_flows` | ページ間のナビゲーションフロー | `app_monitor_name`, `start_time`, `end_time` |
| `crashes` | モバイルのクラッシュと ANR（Android は検証済み、iOS は実験的） | `app_monitor_name`, `start_time`, `end_time` |
| `app_launches` | モバイルのコールド/ウォーム/プリウォーム起動時間 | `app_monitor_name`, `start_time`, `end_time` |
| `analyze` | 異常検出とメッセージパターン | `app_monitor_name`, `start_time`, `end_time` |
| **相関とメトリクス** | | |
| `correlate` | フロントエンドからバックエンドへの X-Ray トレース相関 | `app_monitor_name`, `page_url`, `start_time`, `end_time` |
| `metrics` | CloudWatch RUM 名前空間のメトリクス | `app_monitor_name`, `metric_names`（JSON 配列）, `start_time`, `end_time` |

**オプションパラメータ**（アクションにより異なる）: `resource_arn`、`page_url`、`group_by`、`platform`、`max_results`、`max_traces`、`statistic`、`period`、`session_id`、`metric`、`bucket`、`compare_previous`

### 🔬 動的計装ツール {#-dynamic-instrumentation-tools}

再デプロイなしで稼働中のサービスをインタラクティブにデバッグします。動的計装により、実行中の Application Signals サービスにブレークポイント形式またはプローブ形式の計装を配置し、取得されたスナップショット（引数、ローカルの状態、スタックトレース）を CloudWatch Logs から検査できます。

> **注:** これらのツールは、パブリックな AWS SDK（`boto3` >= 1.43.35）で利用可能な
> `application-signals` の動的計装オペレーションを呼び出します。

**設定・ステータスツール**

- `create_instrumentation` — BREAKPOINT または PROBE 用の動的計装設定を作成します。
- `list_instrumentations` — 1 つのサービス、環境、タイプについてアクティブな計装設定を一覧表示します。
- `get_instrumentation` — 単一の計装ターゲットの完全なバックエンド設定を取得します。
- `delete_instrumentation` — 単一の計装設定を削除します。
- `batch_delete_instrumentations_by_scope` — スコープを指定して計装設定を一括削除します。
- `batch_delete_instrumentations_by_arns` — 明示的なリソース ARN のリストを指定して計装設定を一括削除します。
- `get_instrumentation_configuration_status` — 1 つの計装設定と 1 つの明示的なステータスについて、ステータスイベントの履歴を取得します。
- `check_instrumentation_status` — 時間ウィンドウにわたって READY/ACTIVE/ERROR の統合ステータスチェックを実行します。

**スナップショット分析ツール**

- `search_snapshots_for_status_event` — 既知の計装ステータスのタイムスタンプ付近の CloudWatch Logs スナップショットを検索します。
- `get_sample_snapshot_for_breakpoint` — 取得されたデータの構造を検査するために、近傍のスナップショットを 1 件取得します。

## インストール {#installation}

### ワンクリックインストール {#one-click-installation}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=applicationsignals&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.cloudwatch-applicationsignals-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22%5BThe%20AWS%20Profile%20Name%20to%20use%20for%20AWS%20access%5D%22%2C%22AWS_REGION%22%3A%22%5BThe%20AWS%20region%20to%20run%20in%5D%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=applicationsignals&config=eyJhdXRvQXBwcm92ZSI6W10sImRpc2FibGVkIjpmYWxzZSwidGltZW91dCI6NjAsImNvbW1hbmQiOiJ1dnggYXdzbGFicy5jbG91ZHdhdGNoLWFwcGxpY2F0aW9uc2lnbmFscy1tY3Atc2VydmVyQGxhdGVzdCIsImVudiI6eyJBV1NfUFJPRklMRSI6IltUaGUgQVdTIFByb2ZpbGUgTmFtZSB0byB1c2UgZm9yIEFXUyBhY2Nlc3NdIiwiQVdTX1JFR0lPTiI6IltUaGUgQVdTIHJlZ2lvbiB0byBydW4gaW5dIiwiRkFTVE1DUF9MT0dfTEVWRUwiOiJFUlJPUiJ9LCJ0cmFuc3BvcnRUeXBlIjoic3RkaW8ifQ) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=applicationsignals&config=%7B%22autoApprove%22%3A%5B%5D%2C%22disabled%22%3Afalse%2C%22timeout%22%3A60%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.cloudwatch-applicationsignals-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22%5BThe%20AWS%20Profile%20Name%20to%20use%20for%20AWS%20access%5D%22%2C%22AWS_REGION%22%3A%22%5BThe%20AWS%20region%20to%20run%20in%5D%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22transportType%22%3A%22stdio%22%7D) |

### `uv` によるインストール {#installing-via-uv}

[`uv`](https://docs.astral.sh/uv/) を使用する場合、特別なインストールは不要です。[`uvx`](https://docs.astral.sh/uv/guides/tools/) を使用して *awslabs.cloudwatch-applicationsignals-mcp-server* を直接実行します。

### Claude Desktop へのインストール {#installing-via-claude-desktop}

MacOS の場合: `~/Library/Application\ Support/Claude/claude_desktop_config.json`
Windows の場合: `%APPDATA%/Claude/claude_desktop_config.json`

<details>
  <summary>開発版/未公開サーバーの設定</summary>
  開発版または未公開のサーバーをインストールする場合は、`--directory` フラグを追加します。

  ```json
  {
    "mcpServers": {
      "applicationsignals": {
        "command": "uvx",
        "args": ["--from", "/absolute/path/to/cloudwatch-applicationsignals-mcp-server", "awslabs.cloudwatch-applicationsignals-mcp-server"],
        "env": {
          "AWS_PROFILE": "[The AWS Profile Name to use for AWS access]",
          "AWS_REGION": "[AWS Region]",
          "FASTMCP_LOG_LEVEL": "ERROR"
        }
      }
    }
  }
  ```
</details>

<details>
  <summary>公開済みサーバーの設定</summary>

  ```json
  {
    "mcpServers": {
      "applicationsignals": {
        "command": "uvx",
        "args": ["awslabs.cloudwatch-applicationsignals-mcp-server@latest"],
        "env": {
          "AWS_PROFILE": "[The AWS Profile Name to use for AWS access]",
          "AWS_REGION": "[AWS Region]",
          "FASTMCP_LOG_LEVEL": "ERROR"
        }
      }
    }
  }
  ```
</details>

### Kiro へのインストール {#installing-for-kiro}

詳細は [Kiro IDE のドキュメント](https://kiro.dev/docs/mcp/configuration/)または [Kiro CLI のドキュメント](https://kiro.dev/docs/cli/mcp/configuration/)を参照してください。

グローバル設定の場合は `~/.kiro/settings/mcp.json` を編集します。プロジェクト固有の設定の場合は、プロジェクトディレクトリ内の `.kiro/settings/mcp.json` を編集します。

Kiro の MCP 設定ファイルに次の設定を追加します。

```json
{
    "mcpServers": {
        "applicationsignals": {
            "command": "uvx",
            "args": [
                "awslabs.cloudwatch-applicationsignals-mcp-server@latest"
            ],
            "env": {
                "AWS_PROFILE": "[The AWS Profile Name to use for AWS access]",
                "AWS_REGION": "[AWS Region]",
                "FASTMCP_LOG_LEVEL": "ERROR"
            },
            "disabled": false,
            "autoApprove": []
        }
    }
}
```

### Windows へのインストール {#windows-installation}

Windows ユーザーの場合、MCP サーバーの設定形式は少し異なります。

```json
{
  "mcpServers": {
    "applicationsignals": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.cloudwatch-applicationsignals-mcp-server@latest",
        "awslabs.cloudwatch-applicationsignals-mcp-server.exe"
      ],
      "env": {
        "AWS_PROFILE": "[The AWS Profile Name to use for AWS access]",
        "AWS_REGION": "[AWS Region]",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

### LLM クライアントと同じホスト上で Docker イメージをローカルにビルドしてインストール {#build-and-install-docker-image-locally-on-the-same-host-of-your-llm-client}

1. `git clone https://github.com/awslabs/mcp.git`
2. サブディレクトリ 'src/cloudwatch-applicationsignals-mcp-server/' に移動します
3. 'docker build -t awslabs/cloudwatch-applicationsignals-mcp-server:latest .' を実行します

### LLM クライアントの設定に以下を追加または更新: {#add-or-update-your-llm-clients-config-with-following}
```json
{
  "mcpServers": {
    "applicationsignals": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-v", "${HOME}/.aws:/root/.aws:ro",
        "-e", "AWS_PROFILE=[The AWS Profile Name to use for AWS access]",
        "-e", "AWS_REGION=[AWS Region]",
        "awslabs/cloudwatch-applicationsignals-mcp-server:latest"
      ]
    }
  }
}
```

### デバッグ {#debugging}

MCP インスペクターを使用してサーバーをデバッグできます。`uvx` でインストールした場合:

```bash
npx @modelcontextprotocol/inspector uvx awslabs.cloudwatch-applicationsignals-mcp-server
```

または、特定のディレクトリにパッケージをインストールしている場合:

```bash
cd /path/to/cloudwatch-applicationsignals-mcp-server
npx @modelcontextprotocol/inspector uv run awslabs.cloudwatch-applicationsignals-mcp-server
```

## 使用例 {#usage-examples}

### 例 1: 包括的なサービス健全性監査（推奨ワークフロー） {#example-1-comprehensive-service-health-audit-recommended-workflow}
```
User: "Audit the health of all my payment services"
Assistant: I'll perform a comprehensive health audit of all your payment services using the primary audit tool.

[Uses audit_services with wildcard pattern]

audit_services(
  service_targets='[{"Type":"service","Data":{"Service":{"Type":"Service","Name":"*payment*"}}}]',
  auditors="slo,operation_metric"
)

Results: Found 3 payment services with the following findings:

🔴 CRITICAL FINDINGS:
• payment-api-service: SLO breach detected - Latency SLO violated (p99: 2.1s > 1.5s threshold)
• payment-processor: High error rate detected (8.2% > 5% threshold)

⚠️ WARNING FINDINGS:
• payment-gateway: Dependency timeout issues with external payment provider

✅ HEALTHY:
• payment-validator: All metrics within normal ranges

Recommendations:
1. Investigate payment-api-service latency issues - check database connection pool
2. Review payment-processor error logs for root cause analysis
3. Consider circuit breaker pattern for payment-gateway external dependencies
```

### 例 2: SLO 違反の根本原因分析 {#example-2-slo-breach-root-cause-analysis}
```
User: "I have an SLO breach for my checkout service. Can you help me investigate?"
Assistant: I'll help you investigate the SLO breach. Let me first get the SLO configuration and then perform a comprehensive root cause analysis.

[Uses get_slo to understand configuration]
[Then uses audit_slos with auditors="all" for comprehensive analysis]

audit_slos(
  slo_targets='[{"Type":"slo","Data":{"Slo":{"SloName":"checkout-service-latency-slo"}}}]',
  auditors="all"
)

Root Cause Analysis Results:

🔴 SLO BREACH CONFIRMED:
• checkout-service-latency-slo: 87.3% attainment (< 95% goal)
• Breach duration: 2.5 hours
• Impact: 1,247 requests affected

🔍 ROOT CAUSE IDENTIFIED:
• Database connection pool exhaustion detected
• Trace analysis shows 95% of slow requests waiting for DB connections
• Dependency on payment-service also showing elevated latency

📊 SUPPORTING EVIDENCE:
• P99 latency: 3.2s (threshold: 2.0s)
• Error rate spike: 12% during breach period
• 15 error traces with "connection timeout" messages

🛠️ RECOMMENDED ACTIONS:
1. Increase database connection pool size from 10 to 25
2. Implement connection pool monitoring alerts
3. Review payment-service dependency performance
4. Consider implementing request queuing for high load periods
```

### 例 3: オペレーションレベルのパフォーマンス調査 {#example-3-operation-level-performance-investigation}
```
User: "The GET operations in my payment services are slow. Can you investigate?"
Assistant: I'll investigate the performance of GET operations specifically in your payment services using operation-level analysis.

[Uses audit_service_operations for precise operation targeting]

audit_service_operations(
  operation_targets='[{"Type":"service_operation","Data":{"ServiceOperation":{"Service":{"Type":"Service","Name":"*payment*"},"Operation":"*GET*","MetricType":"Latency"}}}]',
  auditors="operation_metric,trace"
)

Operation Performance Analysis Results:

🎯 GET OPERATIONS ANALYZED:
• payment-api: GET /api/payments/{id} - P99: 1.8s
• payment-api: GET /api/payments/history - P99: 3.2s ⚠️
• payment-processor: GET /api/process/status - P99: 0.8s ✅

🔴 PERFORMANCE ISSUES IDENTIFIED:
• GET /api/payments/history: Consistently slow (3.2s avg)
  - Root cause: Full table scan on payments table
  - 89% of requests show database query time > 2.5s
  - Missing index on user_id + created_date columns

📈 PERFORMANCE RECOMMENDATIONS:
1. Add composite index: CREATE INDEX idx_payments_user_date ON payments(user_id, created_date)
2. Implement pagination for history endpoint (limit 50 records)
3. Consider caching for frequently accessed payment histories
4. Add query timeout protection (max 5s)

🚀 EXPECTED IMPROVEMENT:
• Estimated latency reduction: 3.2s → 0.4s (87% improvement)
• Database load reduction: ~75%
```

### 例 4: 100% のトレース可視性のための Transaction Search {#example-4-transaction-search-for-100-trace-visibility}
```
User: "I want to analyze all the errors in my checkout service from the last hour"
Assistant: I'll use Transaction Search to analyze all errors with 100% trace visibility (no sampling).

[Uses search_transaction_spans for complete trace data]

search_transaction_spans(
  query_string='FILTER attributes.aws.local.service = "checkout-service" and attributes.http.status_code >= 400 | STATS count() as error_count by attributes.http.status_code, attributes.aws.local.operation | SORT error_count DESC | LIMIT 20',
  start_time="2024-01-15T10:00:00Z",
  end_time="2024-01-15T11:00:00Z"
)

✅ Transaction Search Results (100% sampled data):

ERROR BREAKDOWN (Last Hour):
• HTTP 500 errors: 47 occurrences
  - POST /api/checkout/complete: 31 errors
  - POST /api/checkout/validate: 16 errors

• HTTP 404 errors: 23 occurrences
  - GET /api/checkout/{id}: 23 errors

• HTTP 503 errors: 12 occurrences
  - POST /api/checkout/payment: 12 errors

🔍 KEY INSIGHTS:
• 82 total errors out of 1,247 requests (6.6% error rate)
• Most errors (66%) in checkout completion flow
• Service unavailable errors correlate with payment service dependency

🛠️ IMMEDIATE ACTIONS NEEDED:
1. Investigate checkout completion logic for 500 errors
2. Add validation for checkout ID existence (404s)
3. Implement circuit breaker for payment service calls (503s)
```

`log_group_name` はオプションです。省略した場合、ツールは `SOURCE logGroups() | filterIndex @data_format = "AWS-OTEL-TRACE-V1"` をクエリの先頭に付加するため、OTEL のスパンがどこに保存されていても見つけられます。単一のロググループに絞り込むには `log_group_name="my-spans-lg"` を渡します。

### 例 5: サービスの検出と概要 {#example-5-service-discovery-and-overview}
```
User: "What services are being monitored and what's their current health status?"
Assistant: I'll get an overview of all monitored services and their health status.

[Uses list_monitored_services for discovery, then audit_services for health analysis]

Found 8 services being monitored:

📊 SERVICE INVENTORY:
• api-gateway-service (AWS::ApiGateway::RestApi) - Production
• checkout-service (AWS::ECS::Service) - Production
• payment-api-service (AWS::ECS::Service) - Production
• payment-processor (AWS::Lambda::Function) - Production
• user-service (AWS::EKS::Service) - Production
• inventory-service (AWS::EKS::Service) - Production
• notification-lambda (AWS::Lambda::Function) - Production
• analytics-service (AWS::ECS::Service) - Production

[Then performs health audit]

🏥 HEALTH STATUS SUMMARY:
✅ HEALTHY (5 services):
• api-gateway-service: All SLOs met, low latency
• user-service: Excellent performance metrics
• inventory-service: All operations within thresholds
• notification-lambda: Fast execution, no errors
• analytics-service: Stable performance

⚠️ NEEDS ATTENTION (2 services):
• checkout-service: Elevated latency on completion operations
• payment-api-service: Intermittent timeout issues

🔴 CRITICAL (1 service):
• payment-processor: SLO breach - error rate 8.2% (threshold: 5%)

💡 RECOMMENDATIONS:
1. Focus immediate attention on payment-processor error investigation
2. Monitor checkout-service latency trends
3. Review payment-api-service timeout configurations
```

### 例 6: Canary 失敗分析と根本原因調査 {#example-6-canary-failure-analysis-and-root-cause-investigation}
```
User: "My Pet Clinic canaries are failing. Can you help me diagnose the issues?"
Assistant: I'll analyze your Pet Clinic canaries to identify the root causes of failures.

[Uses analyze_canary_failures for comprehensive canary analysis]

analyze_canary_failures(canary_name="pc-visit-vet")
analyze_canary_failures(canary_name="pc-add-visit")
analyze_canary_failures(canary_name="webapp-erorrpagecanary")

🔍 CANARY FAILURE ANALYSIS RESULTS:

🔴 CRITICAL ISSUES IDENTIFIED:

**pc-visit-vet canary:**
• Root Cause: S3 bucket access issue
• Error Pattern: Exit status 127, "No such file or directory"
• Failure Count: 5 consecutive failures
• IAM Analysis: ✅ Role exists but S3 bucket ARN patterns incorrect in policies

**pc-add-visit canary:**
• Root Cause: Selector timeout + backend service errors
• Error Pattern: 30000ms timeout waiting for UI element + MissingFormatArgumentException
• Backend Issue: Format specifier '% o' error in BedrockRuntimeV1Service.invokeTitanModel()
• Performance: 34 second average response time, 0% success rate

**webapp-erorrpagecanary:**
• Root Cause: Browser target close during selector wait
• Error Pattern: "Target closed" waiting for `#jsError` selector
• Failure Count: 5 consecutive failures with 60000ms connection timeouts

🔍 BACKEND SERVICE CORRELATION:
• MissingFormatArgumentException detected in Pet Clinic backend
• Location: org.springframework.samples.petclinic.customers.aws.BedrockRuntimeV1Service.invokeTitanModel (line 75)
• Impact: Affects multiple canaries testing Pet Clinic functionality
• 20% fault rate on GET /api/customer/diagnose/owners/{ownerId}/pets/{petId}

🛠️ RECOMMENDED ACTIONS:

**Immediate (Critical):**
1. Fix S3 bucket ARN patterns in pc-visit-vet IAM policy
2. Fix format string bug in BedrockRuntimeV1Service: change '% o' to '%s' or correct format
3. Add VPC permissions to canary IAM roles if Lambda runs in VPC

**Infrastructure (High Priority):**
4. Investigate browser target stability issues (webapp-erorrpagecanary)
5. Review canary timeout configurations - consider increasing from 30s to 60s
6. Implement circuit breaker pattern for external service dependencies

**Monitoring (Medium Priority):**
7. Add Application Signals monitoring for canary success rates
8. Set up alerts for consecutive canary failures (>3 failures)
9. Implement canary health dashboard with real-time status

🎯 EXPECTED OUTCOMES:
• S3 access fix: Immediate resolution of pc-visit-vet failures
• Backend service fix: 80%+ improvement in Pet Clinic canary success rates
• Infrastructure improvements: Reduced browser target close errors
• Enhanced monitoring: Proactive failure detection and faster resolution
```

### 例 7: 変更イベントのタイムライン分析 {#example-7-change-events-timeline-analysis}
```
User: "My checkout-service alarm is firing. What changed recently?"
Assistant: I'll investigate recent changes to your checkout-service that might have triggered the alarm.

[Uses list_change_events to correlate alarm timing with recent changes]

list_change_events(
  start_time="2024-01-15T12:00:00Z",  # 6 hours before alarm
  end_time="2024-01-15T18:00:00Z",   # Current time
  service_key_attributes='{"Name": "checkout-service", "Environment": "eks:production"}'
)

🚨 **ALARM CORRELATION ANALYSIS:**

**Alarm Details:**
• Trigger Time: 15:30 UTC
• Metric: ErrorRate > 5%
• Current Value: 12.3%

**RECENT CHANGES DETECTED:**
• 14:45 UTC: DEPLOYMENT - UpdateService (checkout-service v2.1.4)
• 15:15 UTC: CONFIGURATION - UpdateTaskDefinition (memory limit increased)
• 15:25 UTC: DEPLOYMENT - UpdateService (rollback attempted)

🎯 **TIMELINE CORRELATION:**
• Deployment at 14:45 UTC
• Alarm triggered 45 minutes later (15:30 UTC)
• Rollback attempt 5 minutes before alarm (15:25 UTC)
• Suggests deployment introduced errors, rollback may be incomplete

💡 **IMMEDIATE ACTIONS:**
1. Verify rollback completion status
2. Check if v2.1.4 introduced breaking changes
3. Monitor error logs from 14:45 UTC onwards
4. Consider full rollback to previous stable version
```

### 例 8: マルチサービスの変更パターン分析 {#example-8-multi-service-change-pattern-analysis}
```
User: "Multiple services are having issues. Show me all recent changes across my environment."
Assistant: I'll analyze recent changes across your environment. Since you want to see all changes without filtering to specific services, I'll use the ListServiceStates API which provides current service state information.

[Uses list_change_events with comprehensive_history=False for environment-wide analysis]

list_change_events(
  start_time="2024-01-15T06:00:00Z",  # Last 12 hours
  end_time="2024-01-15T18:00:00Z",
  comprehensive_history=False,  # Uses ListServiceStates API - no service filtering required
  max_results=100
)

🌐 **ENVIRONMENT-WIDE CHANGE ANALYSIS:**

**SERVICE STATE SUMMARY:**
• payment-service: Recent deployment detected (v2.1.4)
• checkout-service: Configuration change detected (memory limits updated)
• user-service: Stable - no recent changes
• api-gateway: Recent scaling event detected

**RECENT CHANGE INDICATORS:**
• Services with recent deployments: 3
• Services with configuration changes: 2
• Services with scaling events: 1
• Stable services: 2

🔍 **CHANGE CORRELATION ANALYSIS:**

**Services Requiring Investigation:**
• payment-service: Last deployment may correlate with reported issues
• checkout-service: Configuration changes might be reactive to problems
• api-gateway: Scaling events suggest increased load or performance issues

💡 **RECOMMENDED NEXT STEPS:**

For detailed change history of specific problematic services, I can investigate further:
1. Check service health first: get_service_health_overview(service_name="payment-service")
2. Then query comprehensive change history: list_change_events() with service_key_attributes
3. Correlate specific change timing with issue onset

Would you like me to investigate the change history for any specific service in detail?
```

### 例 9: CloudWatch RUM — リアルユーザーモニタリング {#example-9-cloudwatch-rum--real-user-monitoring}
```
User: "Are my users experiencing issues on the checkout page?"
Assistant: I'll check your RUM data for user-facing issues on the checkout page.

[Step 1: Verify the app monitor is configured correctly]
query_rum_events(action="check_data_access", app_monitor_name="my-web-app")
→ CW Logs enabled, X-Ray enabled, all telemetries active. Full analytics available.

[Step 2: Quick health check]
query_rum_events(action="health", app_monitor_name="my-web-app", start_time="2026-03-18T00:00:00Z", end_time="2026-03-19T00:00:00Z")
→ Error rate is 3x higher than normal, concentrated on /checkout page, mostly Chrome users in Germany.

[Step 3: Get error details]
query_rum_events(action="errors", app_monitor_name="my-web-app", start_time="...", end_time="...", page_url="/checkout")
→ Top error: "TypeError: Cannot read property 'total' of undefined" — 847 occurrences.

[Step 4: Is it frontend or backend?]
query_rum_events(action="correlate", app_monitor_name="my-web-app", page_url="/checkout", start_time="...", end_time="...")
→ Backend payment-service is returning 500 errors with avg 5.2s response time. Root cause is in the backend.
```

## 推奨ワークフロー {#recommended-workflows}

### 🎯 主要な監査ワークフロー（最も一般的） {#-primary-audit-workflow-most-common}
1. **`audit_services()` から始める** - ワイルドカードパターンを使用してサービスを自動検出します
2. **所見のサマリーを確認する** - どの問題をさらに調査するかをユーザーに選択してもらいます
3. **`auditors="all"` で深掘りする** - 根本原因分析が必要な選択済みのサービスに対して実行します

### 🔍 SLO 調査ワークフロー {#-slo-investigation-workflow}
1. **`get_slo()` を使用する** - SLO の設定としきい値を理解します
2. **`auditors="all"` を指定して `audit_slos()` を使用する** - 包括的な根本原因分析を行います
3. **実行可能な推奨事項に従う** - 提案された修正を実装します

### ⚡ オペレーションパフォーマンスワークフロー {#-operation-performance-workflow}
1. **`audit_service_operations()` を使用する** - 特定のオペレーションを正確にターゲティングします
2. **ワイルドカードパターンを適用する** - 例: すべての GET オペレーションには `*GET*`
3. **根本原因分析** - 詳細な調査には `auditors="all"` を使用します

### 🔄 変更相関ワークフロー {#-change-correlation-workflow}
1. **インシデント検出** - 問題の発生時点を特定します（アラーム、ログ、Canary の失敗）
2. **変更タイムライン** - `list_change_events()` を使用して最近の変更を特定します
3. **相関分析** - 変更のタイミングと問題の発生時点を突き合わせます
4. **根本原因の検証** - 監査ツールを使用して変更の影響を確認します
5. **修復** - 問題のある変更をロールバックするか、修正を実装します

### 📊 完全なオブザーバビリティワークフロー {#-complete-observability-workflow}
1. **サービス検出** - ワイルドカードパターン付きの `audit_services()`
2. **SLO コンプライアンス** - 違反検出のための `audit_slos()`
3. **オペレーション分析** - エンドポイント固有の問題のための `audit_service_operations()`
4. **変更相関** - タイムライン分析のための `list_change_events()`
5. **トレース調査** - 100% のトレース可視性のための `search_transaction_spans()`

## 設定 {#configuration}

### 必要な AWS 権限 {#required-aws-permissions}

このサーバーには次の AWS IAM 権限が必要です。

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "application-signals:ListServices",
        "application-signals:GetService",
        "application-signals:ListServiceOperations",
        "application-signals:ListServiceLevelObjectives",
        "application-signals:GetServiceLevelObjective",
        "application-signals:BatchGetServiceLevelObjectiveBudgetReport",
        "application-signals:ListAuditFindings",
        "application-signals:ListEntityEvents",
        "application-signals:ListServiceStates",
        "application-signals:ListServiceDependencies",
        "application-signals:ListServiceDependents",
        "application-signals:ListGroupingAttributeDefinitions",
        "cloudwatch:GetMetricData",
        "cloudwatch:GetMetricStatistics",
        "cloudwatch:ListMetrics",
        "logs:GetQueryResults",
        "logs:StartQuery",
        "logs:StopQuery",
        "logs:FilterLogEvents",
        "xray:GetTraceSummaries",
        "xray:BatchGetTraces",
        "xray:GetTraceSegmentDestination",
        "synthetics:GetCanary",
        "synthetics:GetCanaryRuns",
        "synthetics:DescribeCanaries",
        "rum:GetAppMonitor",
        "rum:ListAppMonitors",
        "rum:ListTagsForResource",
        "rum:GetResourcePolicy",
        "logs:DescribeLogGroups",
        "logs:ListLogAnomalyDetectors",
        "logs:ListAnomalies",
        "s3:GetObject",
        "s3:ListBucket",
        "iam:GetRole",
        "iam:ListAttachedRolePolicies",
        "iam:GetPolicy",
        "iam:GetPolicyVersion",
        "application-signals:CreateInstrumentationConfiguration",
        "application-signals:ListInstrumentationConfigurations",
        "application-signals:GetInstrumentationConfiguration",
        "application-signals:DeleteInstrumentationConfiguration",
        "application-signals:BatchDeleteInstrumentationConfigurations",
        "application-signals:GetInstrumentationConfigurationStatus"
      ],
      "Resource": "*"
    }
  ]
}
```

### 環境変数 {#environment-variables}

- `AWS_PROFILE` - 認証に使用する AWS プロファイル名（デフォルトは `default` プロファイル）
- `AWS_REGION` - AWS リージョン（デフォルトは us-east-1）
- `MCP_CLOUDWATCH_APPLICATION_SIGNALS_LOG_LEVEL` - ログレベル（デフォルトは INFO）
- `AUDITOR_LOG_PATH` - 監査ログファイルのパス（デフォルトは /tmp）
- `MCP_RUM_ENDPOINT` - RUM API のエンドポイント URL の上書き（非本番環境に対するテスト用）

### AWS 認証情報 {#aws-credentials}

このサーバーは認証に AWS プロファイルを使用します。`~/.aws/credentials` ファイルの特定のプロファイルを使用するには、`AWS_PROFILE` 環境変数を設定してください。

サーバーは boto3 を介して標準の AWS 認証情報チェーンを使用します。これには次が含まれます。
- `AWS_PROFILE` 環境変数で指定された AWS プロファイル
- AWS 認証情報ファイルのデフォルトプロファイル
- EC2、ECS、Lambda などで実行している場合の IAM ロール

### Transaction Search の設定 {#transaction-search-configuration}

100% のトレース可視性を得るには、AWS X-Ray Transaction Search を有効にします。
1. トレースを CloudWatch Logs に送信するよう X-Ray を設定します
2. 送信先を 'CloudWatchLogs'、ステータスを 'ACTIVE' に設定します
3. これにより、完全なオブザーバビリティのための `search_transaction_spans()` ツールが利用可能になります

Transaction Search を使用しない場合、X-Ray 経由で 5% サンプリングされたトレースデータにしかアクセスできません。

## 開発 {#development}

このサーバーは AWS Labs MCP コレクションの一部です。開発およびコントリビューションのガイドラインについては、メインリポジトリのドキュメントを参照してください。

### テストの実行 {#running-tests}

すべてのユースケース例とツール機能を検証する包括的なテストスイートを実行するには、次を実行します。

```bash
cd src/cloudwatch-applicationsignals-mcp-server
python -m pytest tests/test_use_case_examples.py -v
```

このテストファイルは、ツールのドキュメントにあるすべてのユースケース例が、正しいツールを正しいパラメータとターゲット形式で呼び出していることを検証します。次のテストが含まれます。

- `audit_services()`、`audit_slos()`、`audit_service_operations()` のドキュメント化されたすべてのユースケース
- ターゲット形式の検証（サービス、SLO、オペレーションのターゲット）
- ワイルドカードパターン展開機能
- さまざまなシナリオに対する監査項目（auditor）の選択
- すべてのドキュメント例に対する JSON 形式の検証

テストではモック化された AWS クライアントを使用し、実際の API 呼び出しを防ぎながらツールのロジックとパラメータ処理を検証します。

## ライセンス {#license}

このプロジェクトは Apache License, Version 2.0 の下でライセンスされています。詳細は LICENSE ファイルを参照してください。
