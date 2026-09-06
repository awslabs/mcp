# インストール

各サーバーには個別のインストール手順があり、Kiro、Cursor、VSCode向けのワンクリックインストールが用意されています。一般的な手順は以下のとおりです:

1. [Astral](https://docs.astral.sh/uv/getting-started/installation/)から `uv` をインストールする
2. `uv python install 3.10` でPythonをインストールする
3. 必要なサービスにアクセスできるAWS認証情報を設定する
4. MCPクライアントの設定にサーバーを追加する

Kiro MCPの設定例(`~/.kiro/settings/mcp.json`):

```json
{
  "mcpServers": {
    "aws-mcp": {
      "command": "uvx",
      "timeout": 100000,
      "transport": "stdio",
      "args": [
        "mcp-proxy-for-aws@latest",
        "https://aws-mcp.us-east-1.api.aws/mcp",
        "--metadata",
        "AWS_REGION=us-west-2"
      ]
    },
    "awslabs.aws-pricing-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.aws-pricing-mcp-server@latest"
      ],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    },
    "awslabs.aws-iac-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.aws-iac-mcp-server@latest"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    },
    "awslabs.aws-documentation-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.aws-documentation-mcp-server@latest"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

各サーバー固有の要件や設定オプションについては、***利用可能なAWS向けMCPサーバー***配下の各サーバーのページを参照してください。

MCPの設定で問題が発生した場合や、適切なパラメータが設定されているか確認したい場合は、次の方法を試せます:

```shell
# MCPサーバーを手動で15秒のタイムアウト付きで実行
$ timeout 15s uv tool run [MCP Name] [args] 2>&1 || echo "Command completed or timed out"

# 例(Aurora MySQL MCPサーバー)
$ timeout 15s uv tool run awslabs.mysql-mcp-server --resource_arn [Your Resource ARN] --secret_arn [Your Secret ARN] ... 2>&1 || echo "Command completed or timed out"

# 引数が適切に設定されていない場合、以下のようなメッセージが表示されることがあります:
usage: awslabs.mysql-mcp-server [-h] --resource_arn RESOURCE_ARN --secret_arn SECRET_ARN --database DATABASE
                                --region REGION --readonly READONLY
awslabs.mysql-mcp-server: error: the following arguments are required: --resource_arn, --secret_arn, --database, --region, --readonly
```

**`uvx` の *"@latest"* サフィックス使用時のパフォーマンスに関する注意:**

*"@latest"* サフィックスを使用すると、MCPクライアントの起動のたびにpypiから最新のMCPサーバーパッケージを確認・ダウンロードしますが、初回ロード時間が長くなるというコストが伴います。初回ロード時間を最小化したい場合は、*"@latest"* を外し、以下のいずれかの方法でuvのキャッシュを自分で管理してください:

- `uv cache clean [tool]`: `[tool]` はキャッシュから削除して再インストールしたいMCPサーバーです(例: "awslabs.lambda-tool-mcp-server")(角括弧は外してください)。
- `uvx [tool]@latest`: ツールを最新バージョンに更新し、uvのキャッシュに追加します。

### コンテナでMCPサーバーを実行する

*この例では `awslabs.aws-documentation-mcp-server` をdockerで実行します。他のMCPサーバーでも同じ手順を繰り返せます*

- イメージをビルドしてタグ付けする

  ```base
  cd src/aws-documentation-mcp-server
  docker build -t awslabs/aws-documentation-mcp-server .
  ```

- 必要に応じて、機密性の高い環境変数をファイルに保存する:

  ```.env
  # 架空のAWS一時認証情報を含む.envファイルの内容
  AWS_ACCESS_KEY_ID=ASIAIOSFODNN7EXAMPLE
  AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
  AWS_SESSION_TOKEN=AQoEXAMPLEH4aoAH0gNCAPy...truncated...zrkuWJOgQs8IZZaIv2BXIa2R4Olgk
  ```

- コンテナ内では `"env": {}` が利用できないため、必要に応じてdockerのオプション `--env`、`--env-file`、`--volume` を使用してください。

  ```json
  {
    "mcpServers": {
      "awslabs.aws-documentation-mcp-server": {
        "command": "docker",
        "args": [
          "run",
          "--rm",
          "--interactive",
          "--env",
          "FASTMCP_LOG_LEVEL=ERROR",
          "--env",
          "AWS_REGION=us-east-1",
          "--env-file",
          "/full/path/to/.env",
          "--volume",
          "/full/path/to/.aws:/app/.aws",
          "awslabs/aws-documentation-mcp-server:latest"
        ],
        "env": {}
      }
    }
  }
  ```


### Kiroではじめる

詳細は[Kiro IDEドキュメント](https://kiro.dev/docs/mcp/configuration/)または[Kiro CLIドキュメント](https://kiro.dev/docs/cli/mcp/configuration/)を参照してください。

Kiro IDEでの手順:

1. `Kiro` > `MCP Servers` に移動する
2. `+ Add` ボタンをクリックして新しいMCPサーバーを追加する
3. 以下の設定を貼り付ける:

グローバル設定の場合は `~/.kiro/settings/mcp.json` を編集します。プロジェクト固有の設定の場合は、プロジェクトディレクトリ内の `.kiro/settings/mcp.json` を編集します。

#### `~/.kiro/settings/mcp.json`

macOS/Linuxの場合:

```json
{
  "mcpServers": {
    "awslabs-aws-documentation-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-documentation-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

Windowsの場合:

```json
{
  "mcpServers": {
    "awslabs-aws-documentation-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.aws-documentation-mcp-server@latest",
        "awslabs.aws-documentation-mcp-server.exe"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

### ClineとAmazon Bedrockではじめる

**重要:** 以下の手順に従うと費用が発生する可能性があり、[Amazon Bedrockの料金](https://aws.amazon.com/bedrock/pricing/)が適用されます。発生する費用はお客様の責任となります。Clineの設定で希望のモデルを選択することに加えて、選択したモデル(例: `anthropic.claude-3-7-sonnet`)がAmazon Bedrockでも有効になっていることを確認してください。詳細については、Amazon Bedrock基盤モデル(FM)へのモデルアクセスの有効化に関する[AWSドキュメント](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access-modify.html)を参照してください。

1. 上記の**インストールとセットアップ**セクションの手順に従い、[Astral](https://docs.astral.sh/uv/getting-started/installation/)から `uv` をインストールし、Pythonをインストールし、必要なサービスにアクセスできるAWS認証情報を設定します。
2. Visual Studio Codeを使用している場合は、[Cline VS Code拡張機能](https://marketplace.visualstudio.com/items?itemName=saoudrizwan.claude-dev)(または希望するIDE向けの同等の拡張機能)をインストールします。インストール後、拡張機能をクリックして開きます。プロンプトが表示されたら、希望するプランを選択します。ここではAmazon Bedrockを使用するため、Cline APIではなくAmazon Bedrock API経由でリクエストを送信することになり、Clineの無料プランで問題ありません。
3. **MCP Servers**ボタンを選択します。
4. **Installed**タブを選択し、**Configure MCP Servers**をクリックして `cline_mcp_settings.json` ファイルを開きます。
5. `cline_mcp_settings.json` ファイルの `mcpServers` オブジェクトに、使用したいMCPサーバーを追加します。このリポジトリで提供されているMCPサーバーの一つを使用する以下の例を参照してください。ファイルを保存するとMCPサーバーがインストールされます。

#### `cline_mcp_settings.json`

 ```json
  {
   "mcpServers": {
     "awslabs.aws-documentation-mcp-server": {
       "command": "uvx",
       "args": ["awslabs.aws-documentation-mcp-server@latest"],
       "env": {
         "AWS_PROFILE": "your-aws-profile",
         "AWS_REGION": "us-east-1",
         "FASTMCP_LOG_LEVEL": "ERROR"
       }
     }
    }
  }
 ```

6. インストールが完了すると、MCP ServerのInstalledタブにMCPサーバーの一覧が表示され、有効であることを示す緑色のスライダーが表示されます。完了したら**Done**をクリックします。Clineのチャットインターフェースが表示されます。
7. デフォルトではAPIプロバイダーとしてClineが設定されており、無料プランには制限があります。次に、APIプロバイダーをAWS Bedrockに変更して、Bedrock経由でLLMを使用できるようにします。この場合、課金は接続されたAWSアカウントを通じて行われます。
8. 設定の歯車アイコンをクリックしてClineの設定を開きます。**API Provider**で `Cline` から `AWS Bedrock` に切り替え、認証タイプとして `AWS Profile` を選択します。なお、`AWS Credentials` オプションも動作しますが、これはトークンの有効期限切れ時に自動的に再配布される一時認証情報ではなく、静的な認証情報(アクセスキーIDとシークレットアクセスキー)を使用するため、AWS Profileによる一時認証情報の方がより安全で推奨される方法です。
9. 使用したい既存のAWSプロファイルに基づいて設定を入力し、希望するAWSリージョンを選択して、クロスリージョン推論を有効にします。**Done**をクリックしてチャットインターフェースに戻ります。
10. これで、インストールしたMCPサーバーの機能について質問やテストを始められます。チャットインターフェースのデフォルトオプションは `Plan` で、手動で対応するための出力を提供します(例: ファイルにコピー&ペーストするためのサンプル設定の提示)。オプションで `Act` に切り替えると、Clineがあなたに代わって行動できるようになります(例: Webブラウザでのコンテンツ検索、リポジトリのクローン、コードの実行など)。「Auto-approve」をオンにすると提案の承認クリックを省略できますが、特にActトグルを選択している場合、テスト中はオフのままにしておくことを推奨します。

**注:** 最良の結果を得るには、使用したいMCPサーバーを明示的に指定してClineにプロンプトを送ってください。例: `Terraform MCPサーバーを使って、〜をして`


### Cursorではじめる

1. 上記の**インストールとセットアップ**セクションの手順に従い、[Astral](https://docs.astral.sh/uv/getting-started/installation/)から `uv` をインストールし、Pythonをインストールし、必要なサービスにアクセスできるAWS認証情報を設定します。

2. MCPの設定は、ユースケースに応じて2つの場所に配置できます:

  A. **プロジェクト設定**
    - プロジェクト固有のツールの場合、プロジェクトディレクトリに `.cursor/mcp.json` ファイルを作成します。
    - これにより、その特定のプロジェクト内でのみ利用可能なMCPサーバーを定義できます。

  B. **グローバル設定**
    - すべてのプロジェクトで使用したいツールの場合、ホームディレクトリに `~/.cursor/mcp.json` ファイルを作成します。
    - これにより、すべてのCursorワークスペースでMCPサーバーが利用可能になります。

#### `.cursor/mcp.json`

```json
 {
  "mcpServers": {
    "awslabs.aws-documentation-mcp-server": {
       "command": "uvx",
       "args": ["awslabs.aws-documentation-mcp-server@latest"],
       "env": {
         "AWS_PROFILE": "your-aws-profile",
         "AWS_REGION": "us-east-1",
         "FASTMCP_LOG_LEVEL": "ERROR"
       }
     }
  }
}
```

3. **チャットでMCPを使う** Composer Agentは、MCP設定ページのAvailable Toolsに列挙されているMCPツールを、関連があると判断した場合に自動的に使用します。意図的にツールを使わせるには、使用したいMCPサーバーを明示的に指定してCursorにプロンプトを送ってください。例: `Terraform MCPサーバーを使って、〜をして`

4. **ツールの承認** デフォルトでは、AgentがMCPツールを使用しようとすると、承認を求めるメッセージが表示されます。ツール名の横の矢印でメッセージを展開すると、Agentがどのような引数でツールを呼び出しているか確認できます。

### Windsurfではじめる


1. 上記の**インストールとセットアップ**セクションの手順に従い、[Astral](https://docs.astral.sh/uv/getting-started/installation/)から `uv` をインストールし、Pythonをインストールし、必要なサービスにアクセスできるAWS認証情報を設定します。

2. **MCP設定へのアクセス**
   - Windsurf - Settings > Advanced Settings に移動するか、コマンドパレットから Open Windsurf Settings Page を開きます
   - 「Model Context Protocol (MCP) Servers」セクションを探します

3. **MCPサーバーの追加**
   - 「Add Server」をクリックして新しいMCPサーバーを追加します
   - GitHub、Puppeteer、PostgreSQLなどの利用可能なテンプレートから選択できます
   - あるいは「Add custom server」をクリックして独自のサーバーを設定します

4. **手動設定**
   - `~/.codeium/windsurf/mcp_config.json` にあるMCP設定ファイルを直接編集することもできます

#### `~/.codeium/windsurf/mcp_config.json`

 ```json
 {
   "mcpServers": {
     "awslabs-aws-documentation-mcp-server": {
       "command": "uvx",
       "args": ["awslabs.aws-documentation-mcp-server@latest"],
       "env": {
         "FASTMCP_LOG_LEVEL": "ERROR",
         "MCP_SETTINGS_PATH": "path to your mcp settings file"
       }
     }
    }
  }
 ```

### VS Codeではじめる


VS Codeの設定または `.vscode/mcp.json` でMCPサーバーを設定します(詳細は[VS Code MCPドキュメント](https://code.visualstudio.com/docs/copilot/chat/mcp-servers)を参照):

#### `.vscode/mcp.json`

```json
{
  "mcpServers": {
    "awslabs-aws-documentation-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.aws-documentation-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```
