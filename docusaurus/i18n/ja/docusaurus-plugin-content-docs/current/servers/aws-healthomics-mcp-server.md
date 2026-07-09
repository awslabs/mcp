---
title: "AWS HealthOmics MCPサーバー"
---

AI アシスタントに対して、ゲノムワークフローの管理・実行・分析のための AWS HealthOmics サービスへの包括的なアクセスを提供する Model Context Protocol (MCP) サーバーです。

## 概要 {#overview}

AWS HealthOmics は、ゲノム、トランスクリプトーム、その他のオミクスデータを保存、クエリ、分析するための専用サービスです。この MCP サーバーは、AI アシスタントが自然言語を通じて HealthOmics のワークフローを操作できるようにし、ゲノムデータ分析をよりアクセスしやすく効率的にします。

## 主な機能 {#key-capabilities}

この MCP サーバーは、以下のためのツールを提供します。

### 🧬 ワークフロー管理 {#-workflow-management}
- **ワークフローの作成と検証**: WDL、CWL、Nextflow のワークフロー言語をサポート
- **ワークフロー定義の Lint**: 業界標準の Lint ツールを使用して WDL および CWL ワークフローを検証
- **バージョン管理**: 異なる構成を持つワークフローバージョンの作成と管理
- **ワークフローのパッケージ化**: ワークフロー定義をデプロイ可能なパッケージにバンドル

### 🚀 ワークフロー実行 {#-workflow-execution}
- **実行の開始と監視**: カスタムパラメータでワークフローを実行し、進行状況を監視
- **タスク管理**: 個々のワークフロータスクとその実行ステータスを追跡
- **リソース構成**: コンピューティングリソース、ストレージ、キャッシュオプションを構成

### 📊 分析とトラブルシューティング {#-analysis-and-troubleshooting}
- **パフォーマンス分析**: ワークフロー実行のパフォーマンスとリソース使用状況を分析
- **障害診断**: 失敗したワークフロー実行のための包括的なトラブルシューティングツール
- **ログアクセス**: 実行、エンジン、タスク、マニフェストから詳細なログを取得

### 🔍 ファイル探索と検索 {#-file-discovery-and-search}
- **ゲノミクスファイル検索**: S3 バケット、HealthOmics シーケンスストア、リファレンスストアにまたがるゲノミクスファイルのインテリジェントな探索
- **パターンマッチング**: ファイルパスやオブジェクトタグに対するあいまい一致による高度な検索
- **ファイルの関連付け**: 関連ファイル（BAM/BAI インデックス、FASTQ ペア、FASTA インデックス）の自動検出とグループ化
- **関連性スコアリング**: 一致品質とファイル間の関係性に基づく検索結果のスマートなランク付け

### 🌍 リージョン管理 {#-region-management}
- **マルチリージョンサポート**: HealthOmics が利用可能な AWS リージョンに関する情報を取得

## 利用可能なツール {#available-tools}

### ワークフロー管理ツール {#workflow-management-tools}

1. **ListAHOWorkflows** - ページネーションをサポートし、利用可能な HealthOmics ワークフローを一覧表示
2. **CreateAHOWorkflow** - ローカルの ZIP ファイル、S3 URI、または base64 エンコードされたコンテンツから WDL、CWL、Nextflow 定義で新しいワークフローを作成し、オプションでコンテナレジストリマッピングを指定可能
3. **GetAHOWorkflow** - 詳細なワークフロー情報の取得と定義のエクスポート
4. **CreateAHOWorkflowVersion** - ローカルの ZIP ファイル、S3 URI、または base64 エンコードされたコンテンツから既存ワークフローの新しいバージョンを作成し、オプションでコンテナレジストリマッピングを指定可能
5. **ListAHOWorkflowVersions** - 特定のワークフローのすべてのバージョンを一覧表示
6. **LintAHOWorkflowDefinition** - miniwdl と cwltool を使用して単一の WDL または CWL ワークフローファイルを Lint し、ローカルファイルパス、S3 URI、またはインラインコンテンツを受け付け
7. **LintAHOWorkflowBundle** - インポート/依存関係をサポートしてマルチファイルの WDL または CWL ワークフローバンドルを Lint し、ローカルディレクトリ、ZIP ファイル、S3 プレフィックス、またはインラインの辞書を受け付け
8. **PackageAHOWorkflow** - ワークフローファイルを base64 エンコードされた ZIP 形式にパッケージ化し、ローカルファイルパス、S3 URI、またはインラインコンテンツを受け付け

### ワークフロー実行ツール {#workflow-execution-tools}

1. **StartAHORun** - カスタムパラメータ、リソース構成、および名前付き構成によるオプションの VPC ネットワーキングモードでワークフロー実行を開始
2. **ListAHORuns** - ステータスや日付範囲でフィルタリングしてワークフロー実行を一覧表示
3. **GetAHORun** - ステータスとメタデータを含む詳細な実行情報を取得
4. **ListAHORunTasks** - ステータスフィルタリングによって特定の実行のタスクを一覧表示
5. **GetAHORunTask** - 特定のワークフロータスクに関する詳細情報を取得

### 分析とトラブルシューティングツール {#analysis-and-troubleshooting-tools}

1. **AnalyzeAHORunPerformance** - ワークフロー実行のパフォーマンスとリソース使用状況を分析
2. **DiagnoseAHORunFailure** - 修復の提案を含む、失敗したワークフロー実行の包括的な診断
3. **GetAHORunLogs** - 高レベルなワークフロー実行ログとイベントにアクセス
4. **GetAHORunEngineLogs** - デバッグ用にワークフローエンジンのログ (STDOUT/STDERR) を取得
5. **GetAHORunManifestLogs** - ランタイム情報とメトリクスを含む実行マニフェストログにアクセス
6. **GetAHOTaskLogs** - 個々のワークフローステップをデバッグするためのタスク固有のログを取得

### ファイル探索ツール {#file-discovery-tools}

1. **SearchGenomicsFiles** - パターンマッチング、ファイル関連付け検出、関連性スコアリングを備え、S3 バケット、HealthOmics シーケンスストア、リファレンスストアにまたがるゲノミクスファイルのインテリジェントな検索

### 実行グループ管理ツール {#run-group-management-tools}

1. **CreateAHORunGroup** - オプションのリソース制限 (maxCpus、maxGpus、maxDuration、maxRuns) とタグを指定して新しい実行グループを作成
2. **GetAHORunGroup** - 特定の実行グループに関する詳細情報を取得
3. **ListAHORunGroups** - オプションの名前フィルタリングとページネーションによって利用可能な実行グループを一覧表示
4. **UpdateAHORunGroup** - 既存の実行グループの名前またはリソース制限を更新

### 実行キャッシュ管理ツール {#run-cache-management-tools}

1. **CreateAHORunCache** - キャッシュ動作 (CACHE_ALWAYS または CACHE_ON_FAILURE)、キャッシュストレージ用の S3 URI、およびオプションの名前、説明、タグ、クロスアカウントバケット所有者 ID を指定して新しい実行キャッシュを作成
2. **GetAHORunCache** - 構成、ステータス、メタデータを含む特定の実行キャッシュに関する詳細情報を取得
3. **ListAHORunCaches** - 名前、ステータス、キャッシュ動作によるオプションのフィルタリングとページネーションをサポートして利用可能な実行キャッシュを一覧表示
4. **UpdateAHORunCache** - 既存の実行キャッシュのキャッシュ動作、名前、または説明を更新

### シーケンスストア管理ツール {#sequence-store-management-tools}

1. **CreateAHOSequenceStore** - オプションの暗号化、説明、フォールバックロケーション、タグを指定して新しいシーケンスストアを作成
2. **ListAHOSequenceStores** - オプションの名前フィルタリングとページネーションによってシーケンスストアを一覧表示
3. **GetAHOSequenceStore** - 特定のシーケンスストアに関する詳細情報を取得
4. **UpdateAHOSequenceStore** - シーケンスストアの名前、説明、またはフォールバックロケーションを更新（ETag を内部で管理）
5. **ListAHOReadSets** - サンプル ID、サブジェクト ID、リファレンス ARN、ステータス、ファイルタイプ、日付範囲でフィルタリングしてシーケンスストア内のリードセットを一覧表示
6. **GetAHOReadSetMetadata** - シーケンス情報とファイル詳細を含む特定のリードセットの詳細なメタデータを取得
7. **StartAHOReadSetImportJob** - バッチサポートによって S3 からゲノムファイルをシーケンスストアにインポート
8. **GetAHOReadSetImportJob** - ソースごとのステータスを含むリードセットインポートジョブのステータスと詳細を取得
9. **ListAHOReadSetImportJobs** - ページネーションによってシーケンスストアのインポートジョブを一覧表示
10. **StartAHOReadSetExportJob** - バッチサポートによってシーケンスストアから S3 へリードセットをエクスポート
11. **GetAHOReadSetExportJob** - リードセットエクスポートジョブのステータスと詳細を取得
12. **ListAHOReadSetExportJobs** - ページネーションによってシーケンスストアのエクスポートジョブを一覧表示
13. **ActivateAHOReadSets** - 分析アクセスのためにアーカイブされたリードセットをアクティブ化

### リファレンスストア管理ツール {#reference-store-management-tools}

1. **ListAHOReferenceStores** - オプションの名前フィルタリングとページネーションによってリファレンスストアを一覧表示
2. **GetAHOReferenceStore** - 特定のリファレンスストアに関する詳細情報を取得
3. **ListAHOReferences** - オプションの名前およびステータスフィルタリングによってリファレンスストア内のリファレンスを一覧表示
4. **GetAHOReferenceMetadata** - ファイル情報を含む特定のリファレンスの詳細なメタデータを取得
5. **StartAHOReferenceImportJob** - バッチサポートによって S3 からリファレンスファイルをリファレンスストアにインポート
6. **GetAHOReferenceImportJob** - ソースごとのステータスを含むリファレンスインポートジョブのステータスと詳細を取得
7. **ListAHOReferenceImportJobs** - ページネーションによってリファレンスストアのインポートジョブを一覧表示

### 構成管理ツール {#configuration-management-tools}

1. **CreateAHOConfiguration** - オプションの実行設定、説明、タグを指定して、ワークフロー実行用の新しい HealthOmics 構成を作成
2. **GetAHOConfiguration** - 実行設定とステータスを含む特定の構成に関する詳細情報を取得
3. **ListAHOConfigurations** - ページネーションをサポートして利用可能な構成を一覧表示
4. **DeleteAHOConfiguration** - 構成を削除

### リージョン管理ツール {#region-management-tools}

1. **GetAHOSupportedRegions** - HealthOmics が利用可能な AWS リージョンを一覧表示

## AI アシスタント向けの説明 {#instructions-for-ai-assistants}

この MCP サーバーは、Kiro、Cline、Cursor、Windsurf などの AI アシスタントが、AWS HealthOmics のゲノムワークフロー管理においてユーザーを支援できるようにします。以下は、これらのツールを効果的に使用する方法です。

### AWS HealthOmics の理解 {#understanding-aws-healthomics}

AWS HealthOmics は、ゲノムデータ分析ワークフロー向けに設計されています。主要な概念は次のとおりです。

- **ワークフロー (Workflows)**: ゲノムデータを処理する、WDL、CWL、または Nextflow で記述された計算パイプライン
- **実行 (Runs)**: 特定の入力パラメータとデータを用いたワークフローの実行
- **タスク (Tasks)**: ワークフロー実行内の個々のステップ
- **ストレージタイプ (Storage Types)**: STATIC（固定ストレージ）または DYNAMIC（自動スケーリングストレージ）

### ワークフロー管理のベストプラクティス {#workflow-management-best-practices}

1. **ワークフローの作成**:
   - **ローカルファイルから**: `PackageAHOWorkflow` を使用してワークフローファイルをバンドルし、base64 エンコードされた ZIP を `CreateAHOWorkflow` で使用します
   - **S3 から**: ワークフロー定義の ZIP ファイルを S3 に保存し、`definition_uri` パラメータを使用して参照します
   - 適切な言語構文（WDL、CWL、Nextflow）でワークフローを検証します
   - ユーザーに必要な入力を案内するためのパラメータテンプレートを含めます
   - ワークフローのストレージの好みに基づいて適切な方法を選択します

2. **S3 URI サポート**:
   - `CreateAHOWorkflow` と `CreateAHOWorkflowVersion` はどちらも、base64 エンコードされた ZIP ファイルの代替として S3 URI をサポートします
   - **S3 URI の利点**:
     - 大規模なワークフロー定義に適している（base64 エンコードのオーバーヘッドがない）
     - S3 にアーティファクトを保存する CI/CD パイプラインとの統合が容易
     - ワークフロー作成中のメモリ使用量の削減
     - 既存の S3 保存ワークフロー定義への直接参照
   - **要件**:
     - S3 URI は `s3://` で始まる必要があります
     - S3 バケットは HealthOmics サービスと同じリージョンにある必要があります
     - HealthOmics サービスに対して適切な S3 権限が構成されている必要があります
   - **使用方法**: `definition_source`（ローカルの ZIP パス、S3 URI、または base64 コンテンツ）または `definition_uri` のいずれか一方を指定します（両方は指定できません）。レガシーの `definition_zip_base64` パラメータは、非推奨のエイリアスとして引き続き受け付けられます。

3. **バージョン管理**:
   - 既存のワークフローを変更するのではなく、更新のために新しいバージョンを作成します
   - 変更や改善を示すわかりやすいバージョン名を使用します
   - ユーザーが適切なものを選択できるようにバージョンを一覧表示します
   - バージョン作成には base64 ZIP と S3 URI の両方の方法がサポートされています

### ワークフロー実行のガイダンス {#workflow-execution-guidance}

1. **実行の開始**:
   - 必須パラメータを常に指定します: workflow_id、role_arn、name、output_uri
   - 適切なストレージタイプを選択します（ほとんどの場合 DYNAMIC を推奨）
   - 識別しやすいように意味のある実行名を使用します
   - コストと時間を節約するために、適切な場合はキャッシュを構成します

2. **実行の監視**:
   - `ListAHORuns` をステータスフィルタとともに使用してアクティブなワークフローを追跡します
   - 包括的なステータスを得るために `GetAHORun` で個々の実行の詳細を確認します
   - ボトルネックを特定するために `ListAHORunTasks` でタスクを監視します

### 失敗した実行のトラブルシューティング {#troubleshooting-failed-runs}

ワークフローが失敗した場合は、次の診断アプローチに従います。

1. **DiagnoseAHORunFailure から始める**: この包括的なツールは以下を提供します。
   - 失敗の理由とエラー分析
   - 失敗したタスクの特定
   - ログの要約と推奨事項
   - 実行可能なトラブルシューティング手順

2. **特定のログにアクセスする**:
   - **実行ログ (Run Logs)**: 高レベルなワークフローイベントとステータス変化
   - **エンジンログ (Engine Logs)**: システムレベルの問題に対するワークフローエンジンの STDOUT/STDERR
   - **タスクログ (Task Logs)**: 特定の失敗に対する個々のタスク実行の詳細
   - **マニフェストログ (Manifest Logs)**: リソース使用状況とワークフロー概要情報

3. **パフォーマンス分析**:
   - `AnalyzeAHORunPerformance` を使用してリソースのボトルネックを特定します
   - タスクのリソース使用パターンを確認します
   - 分析結果に基づいてワークフローパラメータを最適化します

### ワークフローの Lint と検証 {#workflow-linting-and-validation}

この MCP サーバーには、デプロイ前に WDL および CWL ワークフローを検証するための組み込みワークフロー Lint 機能が含まれています。

1. **ワークフロー定義の Lint**:
   - **単一ファイル**: 個々のワークフローファイルには `LintAHOWorkflowDefinition` を使用します
   - **マルチファイルバンドル**: インポートや依存関係を持つワークフローには `LintAHOWorkflowBundle` を使用します
   - **構文エラー**: デプロイ前にパースの問題を検出します
   - **不足コンポーネント**: 不足している入力、出力、またはステップを特定します
   - **ランタイム要件**: タスクに適切なランタイム仕様があることを確認します
   - **インポート解決**: ファイル間のインポートと依存関係を検証します
   - **ベストプラクティス**: 潜在的な改善に関する警告を取得します

2. **サポートされる形式**:
   - **WDL**: 包括的な検証のために miniwdl を使用します
   - **CWL**: 標準準拠の検証のために cwltool を使用します

3. **追加インストール不要**:
   miniwdl と cwltool はどちらも依存関係として含まれており、MCP サーバーのインストール後すぐに利用できます。

### ゲノミクスファイルの探索 {#genomics-file-discovery}

この MCP サーバーには、複数のストレージシステムにまたがってゲノミクスファイルを見つけ、探索するのに役立つ強力なゲノミクスファイル検索ツールが含まれています。

1. **マルチストレージ検索**:
   - **S3 バケット**: 構成された S3 バケットパスからゲノミクスファイルを検索します
   - **HealthOmics シーケンスストア**: リードセットと関連ファイルを探索します
   - **HealthOmics リファレンスストア**: リファレンスゲノムと関連インデックスを見つけます
   - **統合された結果**: すべてのストレージシステムから統合され重複排除された結果を取得します

2. **インテリジェントなパターンマッチング**:
   - **ファイルパスマッチング**: S3 オブジェクトキーと HealthOmics リソース名に対して検索します
   - **タグベース検索**: S3 オブジェクトタグと HealthOmics メタデータに対してマッチングします
   - **あいまい一致**: 部分的または近似的な検索語であってもファイルを見つけます
   - **複数の検索語**: 論理的なマッチングによる複数の検索語をサポートします

3. **自動ファイル関連付け**:
   - **BAM/CRAM インデックス**: BAM ファイルを .bai インデックスと、CRAM ファイルを .crai インデックスと自動的にグループ化します
   - **FASTQ ペア**: 標準的な命名規則 (_R1/_R2、_1/_2) を使用して R1/R2 リードペアを検出しグループ化します
   - **FASTA インデックス**: FASTA ファイルを .fai、.dict、BWA インデックスコレクションと関連付けます
   - **バリアントインデックス**: VCF/GVCF ファイルを .tbi および .csi インデックスファイルとグループ化します
   - **完全なファイルセット**: 分析パイプライン向けの完全なゲノミクスファイルコレクションを特定します

4. **スマートな関連性スコアリング**:
   - **パターン一致の品質**: 完全一致には高いスコア、あいまい一致には低いスコアを付けます
   - **ファイルタイプの関連性**: 要求されたタイプに一致するファイルのスコアを引き上げます
   - **関連ファイルのボーナス**: 完全なインデックスセットを持つファイルのスコアを増加させます
   - **ストレージのアクセス可能性**: スコアリングにおいてストレージクラス（Standard と Glacier）を考慮します

5. **包括的なファイルメタデータ**:
   - **アクセスパス**: 直接データアクセスのための S3 URI または HealthOmics S3 アクセスポイントパス
   - **ファイル特性**: サイズ、ストレージクラス、最終更新日、ファイルタイプ検出
   - **ストレージ情報**: アーカイブステータスと取得要件
   - **ソースシステム**: ファイルが S3、シーケンスストア、リファレンスストアのいずれから来たものかを明確に示す

6. **構成とセットアップ**:
   - **S3 バケット構成**: `GENOMICS_SEARCH_S3_BUCKETS` 環境変数にカンマ区切りのバケットパスを設定します
   - **例**: `GENOMICS_SEARCH_S3_BUCKETS=s3://my-genomics-data/,s3://shared-references/hg38/`
   - **権限**: 適切な S3 および HealthOmics の読み取り権限を確保します
   - **パフォーマンス**: 最適な応答時間を得るためにストレージシステム間で並列検索を行います

7. **パフォーマンスの最適化**:
   - **スマートな S3 API 使用**: インテリジェントなキャッシュとバッチ処理により、S3 API 呼び出しを 60〜90% 削減するよう最適化されています
   - **遅延タグ読み込み**: パターンマッチングに必要な場合にのみ S3 オブジェクトタグを取得します
   - **結果キャッシュ**: 検索結果をキャッシュし、同一の検索に対する S3 呼び出しの繰り返しを排除します
   - **バッチ操作**: 複数のオブジェクトのタグを並列バッチで取得します
   - **構成可能なパフォーマンス**: ユースケースに合わせてキャッシュ TTL、バッチサイズ、タグ検索の動作を調整します
   - **パス優先マッチング**: API 呼び出しを削減するために、タグマッチングよりもファイルパスマッチングを優先します

### ファイル検索の使用例 {#file-search-usage-examples}

1. **サンプルの FASTQ ファイルを見つける**:
   ```
   User: "Find all FASTQ files for sample NA12878"
   → Use SearchGenomicsFiles with file_type="fastq" and search_terms=["NA12878"]
   → Returns R1/R2 pairs automatically grouped together
   → Includes file sizes and storage locations
   ```

2. **リファレンスゲノムを見つける**:
   ```
   User: "Find human reference genome hg38 files"
   → Use SearchGenomicsFiles with file_type="fasta" and search_terms=["hg38", "human"]
   → Returns FASTA files with associated .fai, .dict, and BWA indexes
   → Provides S3 access point paths for HealthOmics reference stores
   ```

3. **アラインメントファイルを検索する**:
   ```
   User: "Find BAM files from the 1000 Genomes project"
   → Use SearchGenomicsFiles with file_type="bam" and search_terms=["1000", "genomes"]
   → Returns BAM files with their .bai index files
   → Ranked by relevance with complete file metadata
   ```

4. **バリアントファイルを探索する**:
   ```
   User: "Locate VCF files containing SNP data"
   → Use SearchGenomicsFiles with file_type="vcf" and search_terms=["SNP"]
   → Returns VCF files with associated .tbi index files
   → Includes both S3 and HealthOmics store results
   ```

### ファイル検索のパフォーマンスチューニング {#performance-tuning-for-file-search}

ゲノミクスファイル検索には、S3 API 呼び出しを最小限に抑え、パフォーマンスを向上させるためのいくつかの最適化が含まれています。

1. **パスベース検索の場合**（推奨）:
   ```bash
   # Use specific file/sample names in search terms
   # This enables path matching without tag retrieval
   GENOMICS_SEARCH_ENABLE_S3_TAG_SEARCH=true  # Keep enabled for fallback
   GENOMICS_SEARCH_RESULT_CACHE_TTL=600       # Cache results for 10 minutes
   ```

2. **タグの多い環境の場合**:
   ```bash
   # Optimize batch sizes for your dataset
   GENOMICS_SEARCH_MAX_TAG_BATCH_SIZE=200     # Larger batches for better performance
   GENOMICS_SEARCH_TAG_CACHE_TTL=900          # Longer tag cache for frequently accessed objects
   ```

3. **コストに敏感な環境の場合**:
   ```bash
   # Disable tag search if only path matching is needed
   GENOMICS_SEARCH_ENABLE_S3_TAG_SEARCH=false  # Eliminates all tag API calls
   GENOMICS_SEARCH_RESULT_CACHE_TTL=1800       # Longer result cache to reduce repeated searches
   ```

4. **開発/テストの場合**:
   ```bash
   # Disable caching for immediate results during development
   GENOMICS_SEARCH_RESULT_CACHE_TTL=0         # No result caching
   GENOMICS_SEARCH_TAG_CACHE_TTL=0            # No tag caching
   GENOMICS_SEARCH_MAX_TAG_BATCH_SIZE=50      # Smaller batches for testing
   ```

**パフォーマンスへの影響**: これらの最適化により、最適化されていない実装と比較して、S3 API 呼び出しを 60〜90% 削減し、検索応答時間を 5〜10 倍向上させることができます。

### 一般的なユースケース {#common-use-cases}

1. **ワークフロー開発**:
   ```
   User: "Help me create a new genomic variant calling workflow"
   → Option A: Use PackageAHOWorkflow to bundle files, then CreateAHOWorkflow with base64 ZIP
   → Option B: Upload workflow ZIP to S3, then CreateAHOWorkflow with S3 URI
   → Validate syntax and parameters
   → Choose method based on workflow size and storage preferences
   ```

2. **本番実行**:
   ```
   User: "Run my alignment workflow on these FASTQ files"
   → Use SearchGenomicsFiles to find FASTQ files for the run
   → Use StartAHORun with appropriate parameters
   → Monitor with ListAHORuns and GetAHORun
   → Track task progress with ListAHORunTasks
   ```

3. **トラブルシューティング**:
   ```
   User: "My workflow failed, what went wrong?"
   → Use DiagnoseAHORunFailure for comprehensive analysis
   → Access specific logs based on failure type
   → Provide actionable remediation steps
   ```

4. **パフォーマンス最適化**:
   ```
   User: "How can I make my workflow run faster?"
   → Use AnalyzeAHORunPerformance to identify bottlenecks
   → Review resource utilization patterns
   → Suggest optimization strategies
   ```

5. **ワークフロー検証**:
   ```
   User: "Check if my WDL workflow is valid"
   → Use LintAHOWorkflowDefinition for single files
   → Use LintAHOWorkflowBundle for multi-file workflows with imports
   → Check for missing inputs, outputs, or runtime requirements
   → Validate import resolution and dependencies
   → Get detailed error messages and warnings
   ```

### 重要な考慮事項 {#important-considerations}

- **IAM 権限**: HealthOmics 権限を持つ適切な IAM ロールを確保します
- **リージョンの可用性**: `GetAHOSupportedRegions` を使用してサービスの可用性を確認します
- **コスト管理**: 特に STATIC ストレージの場合、ストレージとコンピューティングのコストを監視します
- **データセキュリティ**: ゲノムデータ取り扱いのベストプラクティスとコンプライアンス要件に従います
- **リソース制限**: 同時実行に関するサービスクォータと制限に注意します

### エラーハンドリング {#error-handling}

ツールがエラーを返す場合:
- AWS 認証情報と権限を確認します
- リソース ID (workflow_id、run_id、task_id) が有効であることを確認します
- 適切なパラメータの書式と必須フィールドを確認します
- 失敗の根本原因を理解するために診断ツールを使用します
- ユーザーに明確で実行可能なエラーメッセージを提供します

## インストール {#installation}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.aws-healthomics-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-healthomics-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%2C%22AWS_PROFILE%22%3A%22your-profile%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22WARNING%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.aws-healthomics-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLWhlYWx0aG9taWNzLW1jcC1zZXJ2ZXJAbGF0ZXN0IiwiZW52Ijp7IkFXU19SRUdJT04iOiJ1cy1lYXN0LTEiLCJBV1NfUFJPRklMRSI6InlvdXItcHJvZmlsZSIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiV0FSTklORyJ9fQ%3D%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20HealthOmics%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-healthomics-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_REGION%22%3A%22us-east-1%22%2C%22AWS_PROFILE%22%3A%22your-profile%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22WARNING%22%7D%7D) |

uvx を使用してインストールします。

```bash
uvx awslabs.aws-healthomics-mcp-server
```

または、ソースからインストールします。

```bash
git clone <repository-url>
cd mcp/src/aws-healthomics-mcp-server
uv sync
uv run -m awslabs.aws_healthomics_mcp_server.server
```

## 設定 {#configuration}

### 環境変数 {#environment-variables}

#### コア設定 {#core-configuration}

- `AWS_REGION` - HealthOmics 操作用の AWS リージョン（デフォルト: us-east-1）
- `AWS_PROFILE` - 認証用の AWS プロファイル
- `FASTMCP_LOG_LEVEL` - サーバーのログレベル（デフォルト: WARNING）
- `HEALTHOMICS_DEFAULT_MAX_RESULTS` - ページネーションされた API 呼び出しのデフォルトの最大結果数（デフォルト: 10）

#### ゲノミクスファイル検索の設定 {#genomics-file-search-configuration}

- `GENOMICS_SEARCH_S3_BUCKETS` - ゲノミクスファイルを検索する S3 バケットパスのカンマ区切りリスト（例: "s3://my-genomics-data/,s3://shared-references/"）
- `GENOMICS_SEARCH_ENABLE_S3_TAG_SEARCH` - S3 タグベース検索の有効化/無効化（デフォルト: true）
  - `false` に設定するとタグの取得を無効にし、パスベースのマッチングのみを使用します
  - タグマッチングが不要な場合、S3 API 呼び出しを大幅に削減します
- `GENOMICS_SEARCH_MAX_TAG_BATCH_SIZE` - 単一のバッチでタグを取得するオブジェクトの最大数（デフォルト: 100）
  - 値を大きくするとタグの多い検索のパフォーマンスが向上しますが、メモリ使用量が増加します
  - 値を小さくするとメモリ使用量が減少しますが、API 呼び出しのレイテンシが増加する可能性があります
- `GENOMICS_SEARCH_RESULT_CACHE_TTL` - 結果キャッシュの TTL（秒単位、デフォルト: 600）
  - `0` に設定すると結果キャッシュを無効にします
  - 完全な検索結果をキャッシュし、同一の検索に対する S3 呼び出しの繰り返しを排除します
- `GENOMICS_SEARCH_TAG_CACHE_TTL` - タグキャッシュの TTL（秒単位、デフォルト: 300）
  - `0` に設定するとタグキャッシュを無効にします
  - 個々のオブジェクトタグをキャッシュし、検索間での重複取得を回避します
- `GENOMICS_SEARCH_MAX_CONCURRENT` - S3 バケット検索の最大同時実行数（デフォルト: 10）
- `GENOMICS_SEARCH_TIMEOUT_SECONDS` - 検索タイムアウト（秒単位、デフォルト: 300）
- `GENOMICS_SEARCH_ENABLE_HEALTHOMICS` - HealthOmics シーケンス/リファレンスストア検索の有効化/無効化（デフォルト: true）

> **大規模な S3 バケットに関する注意**: 非常に大規模な S3 バケット（数百万オブジェクト）を検索する場合、ゲノミクスファイル検索がデフォルトの MCP クライアントタイムアウトより長くかかることがあります。タイムアウトエラーが発生した場合は、MCP サーバー構成に `"timeout"` プロパティを追加して MCP サーバーのタイムアウトを増やしてください（例: 5 分の場合は `"timeout": 300000`、ミリ秒単位で指定）。これは、広範な S3 バケット構成で検索ツールを使用する場合や、大規模なデータセットで `GENOMICS_SEARCH_ENABLE_S3_TAG_SEARCH=true` を使用する場合に特に重要です。MCP タイムアウトがゲノミクス検索のタイムアウトを先取りするのを防ぎたい場合、`"timeout"` の値は常に `GENOMICS_SEARCH_TIMEOUT_SECONDS` の値より大きくする必要があります。

#### エージェントの識別 {#agent-identification}

- `AGENT` - すべての boto3 API 呼び出しの User-Agent 文字列に `agent/<value>` として付加されるエージェント識別子（オプション）
  - **ユースケース**: CloudTrail や AWS サービスログを通じたトレーサビリティのために、API 呼び出しを特定の AI エージェントに帰属させる
  - **動作**: 設定されると、値は表示可能な ASCII 文字 (0x20-0x7E) にサニタイズされ、前後の空白が除去され、小文字化され、User-Agent ヘッダに `agent/<value>` として付加されます
  - **検証**: 空、空白のみ、またはサニタイズ後に空になる値は未設定として扱われます
  - **例**: `export AGENT=KIRO` は `User-Agent: ... agent/kiro` を生成します

#### テスト設定変数 {#testing-configuration-variables}

以下の環境変数は、主にモックサービスエンドポイントに対する統合テストなどのテストシナリオを対象としています。

- `HEALTHOMICS_SERVICE_NAME` - HealthOmics クライアントが使用する AWS サービス名を上書きします（デフォルト: omics）
  - **ユースケース**: モックサービスや代替実装に対するテスト
  - **検証**: 空または空白のみにはできません。無効な場合は警告とともにデフォルトにフォールバックします
  - **例**: `export HEALTHOMICS_SERVICE_NAME=omics-mock`

- `HEALTHOMICS_ENDPOINT_URL` - HealthOmics クライアントが使用するエンドポイント URL を上書きします
  - **ユースケース**: ローカルのモックサービスや代替エンドポイントに対する統合テスト
  - **検証**: `http://` または `https://` で始まる必要があります。無効な場合は警告とともに無視されます
  - **例**: `export HEALTHOMICS_ENDPOINT_URL=http://localhost:8080`
  - **注意**: HealthOmics クライアントにのみ影響します。他の AWS サービスはデフォルトのエンドポイントを使用します

> **重要**: これらのテスト設定変数は、開発およびテスト環境でのみ使用してください。本番環境では、セキュリティと信頼性のために、常にデフォルトの AWS HealthOmics サービスエンドポイントを使用してください。

### AWS 認証情報 {#aws-credentials}

このサーバーには、HealthOmics 操作に適した権限を持つ AWS 認証情報が必要です。以下の方法で設定します。

1. AWS CLI: `aws configure`
2. 環境変数: `AWS_ACCESS_KEY_ID`、`AWS_SECRET_ACCESS_KEY`
3. IAM ロール（EC2/Lambda に推奨）
4. AWS プロファイル: `AWS_PROFILE` 環境変数を設定

### 必要な IAM 権限 {#required-iam-permissions}

以下の IAM 権限が必要です。

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "omics:ListWorkflows",
                "omics:CreateWorkflow",
                "omics:GetWorkflow",
                "omics:CreateWorkflowVersion",
                "omics:ListWorkflowVersions",
                "omics:StartRun",
                "omics:ListRuns",
                "omics:GetRun",
                "omics:ListRunTasks",
                "omics:GetRunTask",
                "omics:CreateRunGroup",
                "omics:GetRunGroup",
                "omics:ListRunGroups",
                "omics:UpdateRunGroup",
                "omics:CreateRunCache",
                "omics:GetRunCache",
                "omics:ListRunCaches",
                "omics:UpdateRunCache",
                "omics:ListSequenceStores",
                "omics:ListReadSets",
                "omics:GetReadSetMetadata",
                "omics:ListReferenceStores",
                "omics:ListReferences",
                "omics:GetReferenceMetadata",
                "omics:CreateSequenceStore",
                "omics:GetSequenceStore",
                "omics:UpdateSequenceStore",
                "omics:StartReadSetImportJob",
                "omics:GetReadSetImportJob",
                "omics:ListReadSetImportJobs",
                "omics:StartReadSetExportJob",
                "omics:GetReadSetExportJob",
                "omics:ListReadSetExportJobs",
                "omics:StartReadSetActivationJob",
                "omics:GetReferenceStore",
                "omics:StartReferenceImportJob",
                "omics:GetReferenceImportJob",
                "omics:ListReferenceImportJobs",
                "omics:CreateConfiguration",
                "omics:GetConfiguration",
                "omics:ListConfigurations",
                "omics:DeleteConfiguration",
                "logs:DescribeLogGroups",
                "logs:DescribeLogStreams",
                "logs:GetLogEvents"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket",
                "s3:GetObject",
                "s3:GetObjectTagging",
                "s3:HeadBucket"
            ],
            "Resource": [
                "arn:aws:s3:::*genomics*",
                "arn:aws:s3:::*genomics*/*",
                "arn:aws:s3:::*omics*",
                "arn:aws:s3:::*omics*/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "iam:PassRole"
            ],
            "Resource": "arn:aws:iam::*:role/HealthOmicsExecutionRole*"
        }
    ]
}
```

**注意**: 上記の S3 権限は、ゲノミクス関連のバケットに対してワイルドカードパターンを使用しています。本番環境では、これらを検索対象としたい特定のバケット ARN に置き換えてください。例:

```json
{
    "Effect": "Allow",
    "Action": [
        "s3:ListBucket",
        "s3:GetObject",
        "s3:GetObjectTagging",
        "s3:HeadBucket"
    ],
    "Resource": [
        "arn:aws:s3:::my-genomics-data",
        "arn:aws:s3:::my-genomics-data/*",
        "arn:aws:s3:::shared-references",
        "arn:aws:s3:::shared-references/*"
    ]
}
```

## MCP クライアントでの使用 {#usage-with-mcp-clients}

### Kiro {#kiro}

詳細については、[Kiro IDE ドキュメント](https://kiro.dev/docs/mcp/configuration/) または [Kiro CLI ドキュメント](https://kiro.dev/docs/cli/mcp/configuration/) を参照してください。

グローバル設定の場合は `~/.kiro/settings/mcp.json` を編集します。プロジェクト固有の設定の場合は、プロジェクトディレクトリ内の `.kiro/settings/mcp.json` を編集します。

Kiro の MCP 設定 (`~/.kiro/settings/mcp.json`) に以下を追加します。

```json
{
  "mcpServers": {
    "aws-healthomics": {
      "command": "uvx",
      "args": ["awslabs.aws-healthomics-mcp-server"],
      "timeout": 300000,
      "env": {
        "AWS_REGION": "us-east-1",
        "AWS_PROFILE": "your-profile",
        "HEALTHOMICS_DEFAULT_MAX_RESULTS": "10",
        "AGENT": "kiro",
        "GENOMICS_SEARCH_S3_BUCKETS": "s3://my-genomics-data/,s3://shared-references/",
        "GENOMICS_SEARCH_ENABLE_S3_TAG_SEARCH": "true",
        "GENOMICS_SEARCH_MAX_TAG_BATCH_SIZE": "100",
        "GENOMICS_SEARCH_RESULT_CACHE_TTL": "600",
        "GENOMICS_SEARCH_TAG_CACHE_TTL": "300"
      }
    }
  }
}
```

#### テスト設定の例 {#testing-configuration-example}

モックサービスに対する統合テストの場合:

```json
{
  "mcpServers": {
    "aws-healthomics-test": {
      "command": "uvx",
      "args": ["awslabs.aws-healthomics-mcp-server"],
      "timeout": 300000,
      "env": {
        "AWS_REGION": "us-east-1",
        "AWS_PROFILE": "test-profile",
        "HEALTHOMICS_SERVICE_NAME": "omics-mock",
        "HEALTHOMICS_ENDPOINT_URL": "http://localhost:8080",
        "GENOMICS_SEARCH_S3_BUCKETS": "s3://test-genomics-data/",
        "GENOMICS_SEARCH_ENABLE_S3_TAG_SEARCH": "false",
        "GENOMICS_SEARCH_RESULT_CACHE_TTL": "0",
        "FASTMCP_LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

### その他の MCP クライアント {#other-mcp-clients}

お使いのクライアントのドキュメントに従って、以下を使用して設定します。
- コマンド: `uvx`
- 引数: `["awslabs.aws-healthomics-mcp-server"]`
- 必要に応じて環境変数

### Windows でのインストール {#windows-installation}

Windows ユーザーの場合、MCP サーバーの設定形式は少し異なります。

```json
{
  "mcpServers": {
    "awslabs.aws-healthomics-mcp-server": {
      "disabled": false,
      "timeout": 300000,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.aws-healthomics-mcp-server@latest",
        "awslabs.aws-healthomics-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "GENOMICS_SEARCH_S3_BUCKETS": "s3://my-genomics-data/,s3://shared-references/",
        "GENOMICS_SEARCH_ENABLE_S3_TAG_SEARCH": "true",
        "GENOMICS_SEARCH_MAX_TAG_BATCH_SIZE": "100",
        "GENOMICS_SEARCH_RESULT_CACHE_TTL": "600",
        "GENOMICS_SEARCH_TAG_CACHE_TTL": "300"
      }
    }
  }
}
```

#### Windows でのテスト設定 {#windows-testing-configuration}

Windows でのテストシナリオの場合:

```json
{
  "mcpServers": {
    "awslabs.aws-healthomics-mcp-server-test": {
      "disabled": false,
      "timeout": 300000,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.aws-healthomics-mcp-server@latest",
        "awslabs.aws-healthomics-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "DEBUG",
        "AWS_PROFILE": "test-profile",
        "AWS_REGION": "us-east-1",
        "HEALTHOMICS_SERVICE_NAME": "omics-mock",
        "HEALTHOMICS_ENDPOINT_URL": "http://localhost:8080",
        "GENOMICS_SEARCH_S3_BUCKETS": "s3://test-genomics-data/",
        "GENOMICS_SEARCH_ENABLE_S3_TAG_SEARCH": "false",
        "GENOMICS_SEARCH_RESULT_CACHE_TTL": "0"
      }
    }
  }
}
```

## 開発 {#development}

### セットアップ {#setup}

```bash
git clone <repository-url>
cd aws-healthomics-mcp-server
uv sync
```

### テスト {#testing}

```bash
# Run tests with coverage
uv run pytest --cov --cov-branch --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_server.py -v
```

### コード品質 {#code-quality}

```bash
# Format code
uv run ruff format

# Lint code
uv run ruff check

# Type checking
uv run pyright
```

## コントリビューション {#contributing}

コントリビューションを歓迎します。詳細については、[コントリビューションガイドライン](https://github.com/awslabs/mcp/blob/main/CONTRIBUTING.md) を参照してください。

## ライセンス {#license}

このプロジェクトは Apache-2.0 ライセンスの下でライセンスされています。詳細については [LICENSE](https://github.com/awslabs/mcp/blob/main/LICENSE) ファイルを参照してください。
