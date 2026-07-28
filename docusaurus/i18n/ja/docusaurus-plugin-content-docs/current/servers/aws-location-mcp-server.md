---
title: "Amazon Location Service MCPサーバー"
---

Amazon Location Service 用の Model Context Protocol (MCP) サーバーです

この MCP サーバーは、場所検索と地理座標を中心に、Amazon Location Service の機能にアクセスするためのツールを提供します。

## 機能 {#features}

- **場所の検索**: ジオコーディングを使用して場所を検索します
- **場所の詳細取得**: PlaceId を指定して特定の場所の詳細を取得します
- **リバースジオコーディング**: 座標を住所に変換します
- **周辺検索**: 指定した位置の近くにある場所を検索します
- **営業中の場所の検索**: 現在営業中の場所を検索します
- **ルート計算**: Amazon Location Service を使用して地点間のルートを計算します
- **経由地点の最適化**: Amazon Location Service を使用してルートの経由地点の順序を最適化します

## 前提条件 {#prerequisites}

### 要件 {#requirements}

1. Amazon Location Service が有効な AWS アカウントを持っていること
2. [Astral](https://docs.astral.sh/uv/getting-started/installation/) または [GitHub README](https://github.com/astral-sh/uv#installation) から `uv` をインストールすること
3. `uv python install 3.10` を使用して Python 3.10 以降をインストールすること（より新しいバージョンでも可）

## インストール {#installation}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.aws-location-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-location-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.aws-location-mcp-server&config=eyJjb21tYW5kIjoidXZ4IGF3c2xhYnMuYXdzLWxvY2F0aW9uLW1jcC1zZXJ2ZXJAbGF0ZXN0IiwiZW52Ijp7IkFXU19QUk9GSUxFIjoieW91ci1hd3MtcHJvZmlsZSIsIkFXU19SRUdJT04iOiJ1cy1lYXN0LTEiLCJGQVNUTUNQX0xPR19MRVZFTCI6IkVSUk9SIn0sImRpc2FibGVkIjpmYWxzZSwiYXV0b0FwcHJvdmUiOltdfQ%3D%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20Location%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.aws-location-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%2C%22disabled%22%3Afalse%2C%22autoApprove%22%3A%5B%5D%7D) |

Amazon Location MCP サーバーを利用する方法は次のとおりです。

## 設定 {#configuration}

MCP 設定ファイルでサーバーを設定します。AWS 全体で MCP を利用する方法はいくつかあり、今後さらに多くの製品への対応を追加していく予定です（例: Kiro の場合は `~/.kiro/settings/mcp.json`）。

```json
{
  "mcpServers": {
    "awslabs.aws-location-mcp-server": {
        "command": "uvx",
        "args": ["awslabs.aws-location-mcp-server@latest"],
        "env": {
          "AWS_PROFILE": "your-aws-profile",
          "AWS_REGION": "us-east-1",
          "FASTMCP_LOG_LEVEL": "ERROR"
        },
        "disabled": false,
        "autoApprove": []
    }
  }
}
```
### Windows でのインストール {#windows-installation}

Windows ユーザーの場合、MCP サーバーの設定形式は少し異なります。

```json
{
  "mcpServers": {
    "awslabs.aws-location-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.aws-location-mcp-server@latest",
        "awslabs.aws-location-mcp-server.exe"
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


### 一時的な認証情報の使用 {#using-temporary-credentials}

一時的な認証情報（AWS STS、IAM ロール、フェデレーションから取得したものなど）を使用する場合は次のとおりです。


```json
{
  "mcpServers": {
    "awslabs.aws-location-mcp-server": {
        "command": "uvx",
        "args": ["awslabs.aws-location-mcp-server@latest"],
        "env": {
          "AWS_ACCESS_KEY_ID": "your-temporary-access-key",
          "AWS_SECRET_ACCESS_KEY": "your-temporary-secret-key",
          "AWS_SESSION_TOKEN": "your-session-token",
          "AWS_REGION": "us-east-1",
          "FASTMCP_LOG_LEVEL": "ERROR"
        },
        "disabled": false,
        "autoApprove": []
    }
  }
}
```

### Docker の設定 {#docker-configuration}

`docker build -t awslabs/aws-location-mcp-server .` でビルドした後、次のように設定します。

```json
{
  "mcpServers": {
    "awslabs.aws-location-mcp-server": {
        "command": "docker",
        "args": [
          "run",
          "--rm",
          "-i",
          "awslabs/aws-location-mcp-server"
        ],
        "env": {
          "AWS_PROFILE": "your-aws-profile",
          "AWS_REGION": "us-east-1"
        },
        "disabled": false,
        "autoApprove": []
    }
  }
}
```

### Docker で一時的な認証情報を使用する場合 {#docker-with-temporary-credentials}

```json
{
  "mcpServers": {
    "awslabs.aws-location-mcp-server": {
        "command": "docker",
        "args": [
          "run",
          "--rm",
          "-i",
          "awslabs/aws-location-mcp-server"
        ],
        "env": {
          "AWS_ACCESS_KEY_ID": "your-temporary-access-key",
          "AWS_SECRET_ACCESS_KEY": "your-temporary-secret-key",
          "AWS_SESSION_TOKEN": "your-session-token",
          "AWS_REGION": "us-east-1"
        },
        "disabled": false,
        "autoApprove": []
    }
  }
}
```

### 環境変数 {#environment-variables}

- `AWS_PROFILE`: 認証情報に使用する AWS CLI プロファイル
- `AWS_REGION`: 使用する AWS リージョン（デフォルト: us-east-1）
- `AWS_ACCESS_KEY_ID` と `AWS_SECRET_ACCESS_KEY`: 明示的な AWS 認証情報（AWS_PROFILE の代替）
- `AWS_SESSION_TOKEN`: 一時的な認証情報用のセッショントークン（AWS_ACCESS_KEY_ID および AWS_SECRET_ACCESS_KEY と併用）
- `FASTMCP_LOG_LEVEL`: ログレベル（ERROR、WARNING、INFO、DEBUG）

## ツール {#tools}

このサーバーは、MCP インターフェースを通じて次のツールを公開します。

### search_places {#search_places}

Amazon Location Service のジオコーディング機能を使用して場所を検索します。

```python
search_places(query: str, max_results: int = 5, mode: str = 'summary') -> dict
```

### get_place {#get_place}

一意の場所 ID を使用して特定の場所の詳細を取得します。

```python
get_place(place_id: str, mode: str = 'summary') -> dict
```

### reverse_geocode {#reverse_geocode}

リバースジオコーディングを使用して座標を住所に変換します。

```python
reverse_geocode(longitude: float, latitude: float) -> dict
```

### search_nearby {#search_nearby}

特定の位置の近くにある場所を検索します。オプションで検索半径の拡大が可能です。

```python
search_nearby(longitude: float, latitude: float, radius: int = 500, max_results: int = 5,
              query: str = None, max_radius: int = 10000, expansion_factor: float = 2.0,
              mode: str = 'summary') -> dict
```

### search_places_open_now {#search_places_open_now}

現在営業中の場所を検索します。必要に応じて検索半径を拡大します。

```python
search_places_open_now(query: str, max_results: int = 5, initial_radius: int = 500,
                       max_radius: int = 50000, expansion_factor: float = 2.0) -> dict
```

### calculate_route {#calculate_route}

Amazon Location Service を使用して 2 地点間のルートを計算します。

```python
calculate_route(
    departure_position: list,  # [longitude, latitude]
    destination_position: list,  # [longitude, latitude]
    travel_mode: str = 'Car',  # 'Car', 'Truck', 'Walking', or 'Bicycle'
    optimize_for: str = 'FastestRoute'  # 'FastestRoute' or 'ShortestRoute'
) -> dict
```
ルートのジオメトリ、距離、所要時間、およびターンバイターンの経路案内を返します。

- `departure_position`: 出発地点の [longitude, latitude] のリスト。
- `destination_position`: 目的地の [longitude, latitude] のリスト。
- `travel_mode`: 移動手段。`'Car'`、`'Truck'`、`'Walking'`、`'Bicycle'` のいずれか。
- `optimize_for`: ルートの最適化方法。`'FastestRoute'` または `'ShortestRoute'` のいずれか。

詳細については [AWS ドキュメント](https://docs.aws.amazon.com/location/latest/developerguide/calculate-routes-custom-avoidance-shortest.html)を参照してください。

### geocode {#geocode}

場所の名前または住所から座標を取得します。

```python
geocode(location: str) -> dict
```

### optimize_waypoints {#optimize_waypoints}

Amazon Location Service の geo-routes API を使用して経由地点の順序を最適化します。

```python
optimize_waypoints(
    origin_position: list,  # [longitude, latitude]
    destination_position: list,  # [longitude, latitude]
    waypoints: list,  # List of waypoints, each as a dict with at least Position [longitude, latitude]
    travel_mode: str = 'Car',
    mode: str = 'summary'
) -> dict
```
最適化された経由地点の順序、総距離、および所要時間を返します。

## Amazon Location Service のリソース {#amazon-location-service-resources}

このサーバーは、Amazon Location Service の geo-places API とルート計算 API を次の用途に使用します。
- ジオコーディング（住所から座標への変換）
- リバースジオコーディング（座標から住所への変換）
- 場所の検索（名前やカテゴリなどによる場所の検索）
- 場所の詳細（特定の場所に関する情報の取得）
- **ルート計算（地点間のルートの検索）**

## セキュリティに関する考慮事項 {#security-considerations}

- 認証情報の管理には AWS プロファイルを使用してください
- IAM ポリシーを使用して、必要な Amazon Location Service リソースのみにアクセスを制限してください
- セキュリティを強化するために、AWS STS から取得した一時的な認証情報（AWS_ACCESS_KEY_ID、AWS_SECRET_ACCESS_KEY、AWS_SESSION_TOKEN）を使用してください
- アプリケーションやサービスには、一時的な認証情報を持つ AWS IAM ロールを実装してください
- 認証情報を定期的にローテーションし、一時的な認証情報には実用上可能な限り短い有効期限を使用してください
