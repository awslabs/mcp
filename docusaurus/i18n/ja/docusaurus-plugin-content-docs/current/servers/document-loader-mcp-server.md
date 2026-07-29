---
title: "Document Loader MCPサーバー"
---

ドキュメントの解析とコンテンツ抽出を行う Model Context Protocol (MCP) サーバーです。

この MCP サーバーは、PDF、Word ドキュメント、Excel スプレッドシート、PowerPoint プレゼンテーション、画像など、さまざまなドキュメント形式からコンテンツを解析・抽出するためのツールを提供します。

## 機能 {#features}

- **PDF テキスト抽出**: pdfplumber を使用して PDF ファイルからテキストコンテンツを抽出
- **Word ドキュメント処理**: markitdown を使用して DOCX/DOC ファイルを Markdown に変換
- **Excel スプレッドシート読み取り**: XLSX/XLS ファイルを解析して Markdown に変換
- **PowerPoint プレゼンテーション処理**: PPTX/PPT ファイルからコンテンツを抽出
- **画像読み込み**: さまざまな画像形式（PNG、JPG、GIF、BMP、TIFF、WEBP）を読み込んで表示
- **スライド画像抽出**: LibreOffice と poppler を使用して、PPTX、PPT、PDF ファイルから個々のスライド/ページを PNG 画像として抽出

## 前提条件 {#prerequisites}

### インストール要件 {#installation-requirements}

1. [Astral](https://docs.astral.sh/uv/getting-started/installation/) または [GitHub README](https://github.com/astral-sh/uv#installation) から `uv` をインストールします
2. `uv python install 3.10` を使用して Python 3.10 以降（またはより新しいバージョン）をインストールします

### オプション: スライド画像抽出 {#optional-slide-image-extraction}

`extract_slides_as_images` ツールには、外部のシステムパッケージが必要です。

- **LibreOffice**（PPTX/PPT → PDF 変換用）:
  - Ubuntu/Debian: `sudo apt install libreoffice`
  - macOS: `brew install --cask libreoffice`
  - Windows: [libreoffice.org からダウンロード](https://www.libreoffice.org/download/)
- **poppler-utils**（PDF → 画像レンダリング用）:
  - Ubuntu/Debian: `sudo apt install poppler-utils`
  - macOS: `brew install poppler`
  - Windows: [GitHub からダウンロード](https://github.com/oschwartz10612/poppler-windows/releases)して PATH に追加

## インストール {#installation}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.document-loader-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.document-loader-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.document-loader-mcp-server&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyJhd3NsYWJzLmRvY3VtZW50LWxvYWRlci1tY3Atc2VydmVyQGxhdGVzdCJdLCJlbnYiOnsiRkFTVE1DUF9MT0dfTEVWRUwiOiJFUlJPUiJ9LCJkaXNhYmxlZCI6ZmFsc2UsImF1dG9BcHByb3ZlIjpbXX0%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=Document%20Loader%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.document-loader-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

お使いの MCP クライアントの設定で MCP サーバーを設定します。

```json
{
  "mcpServers": {
    "awslabs.document-loader-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.document-loader-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

Kiro の MCP 設定については、[Kiro IDE ドキュメント](https://kiro.dev/docs/mcp/configuration/) または [Kiro CLI ドキュメント](https://kiro.dev/docs/cli/mcp/configuration/) を参照してください。

グローバル設定の場合は `~/.kiro/settings/mcp.json` を編集します。プロジェクト固有の設定の場合は、プロジェクトディレクトリ内の `.kiro/settings/mcp.json` を編集します。

## 利用可能なツール {#available-tools}

- `read_document`: file_path と file_type（'pdf'、'docx'、'doc'、'xlsx'、'xls'、'pptx'、'ppt'）を指定して、さまざまなドキュメント形式からコンテンツを抽出します
- `read_image`: LLM での閲覧および分析用に画像ファイルを読み込みます
- `extract_slides_as_images`: PPTX、PPT、PDF ファイルからスライド/ページを個々の PNG 画像として抽出します。[LibreOffice](https://www.libreoffice.org/)（PPTX/PPT 用）と [poppler-utils](https://poppler.freedesktop.org/)（PDF から画像へのレンダリング用）が必要です

## 環境変数 {#environment-variables}

- `FASTMCP_LOG_LEVEL`: ログレベルを設定します（ERROR、INFO、DEBUG）
- `MAX_FILE_SIZE_MB`: 許可される最大ファイルサイズ（メガバイト単位、デフォルト: 50）。正の整数である必要があります。
- `DOCUMENT_BASE_DIR`: ファイルアクセスセキュリティ用のベースディレクトリ。ドキュメントの読み込みをこのディレクトリ内のファイルに制限します。デフォルトは現在の作業ディレクトリです。

## 開発 {#development}

### セットアップ {#setup}

```bash
# Clone the repository
git clone https://github.com/awslabs/mcp.git
cd mcp/src/document-loader-mcp-server

# Install dependencies
uv sync

# Install in development mode
uv pip install -e .
```

### テスト {#testing}

```bash
# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=awslabs.document_loader_mcp_server
```

テストスイートには以下が含まれます。

- サーバー機能の検証
- 生成されたサンプルファイルによるドキュメント解析テスト
- エラーハンドリングの検証

### サンプルドキュメント {#sample-documents}

テストスイートは、テスト用のサンプルドキュメントを自動的に生成します。

- 複数ページのコンテンツを持つ PDF
- 書式設定されたテキストとリストを持つ DOCX
- 複数のシートとデータを持つ XLSX
- スライドとコンテンツを持つ PPTX
- さまざまな画像形式

## Docker {#docker}

このサーバーを Docker コンテナで実行することもできます。

```bash
docker build -t document-loader-mcp-server .
docker run -p 8000:8000 document-loader-mcp-server
```

## ライセンス {#license}

このプロジェクトは Apache License 2.0 の下でライセンスされています。詳細については [LICENSE](https://github.com/awslabs/mcp/blob/main/src/document-loader-mcp-server/LICENSE) ファイルを参照してください。

## コントリビューション {#contributing}

コントリビューションを歓迎します。詳細については [CONTRIBUTING.md](https://github.com/awslabs/mcp/blob/main/CONTRIBUTING.md) を参照してください。

## サポート {#support}

問題や質問がある場合は、[GitHub issue トラッカー](https://github.com/awslabs/mcp/issues) をご利用ください。
