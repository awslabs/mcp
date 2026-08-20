---
title: AWS Core Network MCP サーバー
---

Cloud WAN、Transit Gateway、VPC、Network Firewall、VPN 接続を含む AWS のコアネットワーキングサービスのトラブルシューティングと分析のための包括的なツールを提供する Model Context Protocol (MCP) サーバーです。

### 主な機能 {#key-features}

- **体系的なトラブルシューティング**: ネットワークパスのトレースと接続性分析のための組み込みの方法論
- **マルチサービス対応**: Cloud WAN、Transit Gateway、VPC、Network Firewall、VPN のための統一されたインターフェース
- **フローログ分析**: CloudWatch から VPC、Transit Gateway、Network Firewall のフローログをクエリおよびフィルタリング
- **インスペクション検出**: セキュリティ分析のためにトラフィックパス内のファイアウォールを自動的に特定
- **マルチリージョン対応**: すべての AWS リージョンにわたるリソース検索
- **読み取り専用の操作**: 設定変更のリスクなしで安全にトラブルシューティング

### AWS コアネットワークの機能 {#aws-core-network-capabilities}

- **パストレース**: ネットワーク接続性の問題を分析するための体系的な方法論
- **IP の検出**: リージョンをまたいで IP アドレスからネットワークインターフェースを特定
- **セキュリティ分析**: セキュリティグループ、NACL、ファイアウォールルールを調査
- **ルーティング分析**: VPC、Transit Gateway、Cloud WAN を通るトラフィックパスをトレース
- **トラフィックの検証**: フローログをクエリして実際のトラフィックパターンを確認
- **インスペクション検出**: トラフィックパス内の AWS Network Firewall およびサードパーティ製ファイアウォールを特定

### ツール {#tools}

#### 汎用ツール {#general-tools}
1. `get_path_trace_methodology`: 包括的なネットワークトラブルシューティング方法論を取得します (常に最初にこれを呼び出してください)
2. `find_ip_address`: マルチリージョン検索に対応し、IP アドレスから ENI を特定します
3. `get_eni_details`: セキュリティグループ、NACL、ルーティングを含む包括的な ENI の詳細を取得します

#### Cloud WAN ツール {#cloud-wan-tools}
4. `list_core_networks`: リージョン内のすべての Cloud WAN コアネットワークを一覧表示します
5. `get_cloudwan_details`: 包括的なコアネットワークの設定と状態を取得します
6. `get_cloudwan_routes`: 特定のセグメントとリージョンのルートを取得します
7. `get_all_cloudwan_routes`: すべてのセグメントとリージョンにわたるすべてのルーティングテーブルを取得します
8. `get_cloudwan_attachment_details`: タイプ別の詳細なアタッチメント情報を取得します
9. `detect_cloudwan_inspection`: インスペクションを実行している Network Function Group を検出します
10. `list_cloudwan_peerings`: コアネットワークのすべての Transit Gateway ピアリングを一覧表示します
11. `get_cloudwan_peering_details`: Cloud WAN と TGW の両方の観点からピアリングの詳細を取得します
12. `get_cloudwan_logs`: トポロジ変更とルーティング更新のイベントログを取得します
13. `simulate_cloud_wan_route_change`: 単一リージョンのネットワーク変更をシミュレートします

#### Transit Gateway ツール {#transit-gateway-tools}
14. `list_transit_gateways`: リージョン内のすべての Transit Gateway を一覧表示します
15. `get_tgw_details`: Transit Gateway の基本的な設定と運用状態の詳細を取得します
16. `get_tgw_routes`: フィルタリング付きで特定のルートテーブルからルートを取得します
17. `get_all_tgw_routes`: すべてのルートテーブルとルートを一度の呼び出しで取得します
18. `get_tgw_flow_logs`: CloudWatch から Transit Gateway のフローログを取得します
19. `list_tgw_peerings`: すべての Transit Gateway ピアリングを一覧表示します
20. `detect_tgw_inspection`: TGW にアタッチされた AWS Network Firewall およびサードパーティ製ファイアウォールを検出します

#### VPC ツール {#vpc-tools}
21. `list_vpcs`: リージョン内のすべての VPC を一覧表示します
22. `get_vpc_network_details`: 包括的な VPC ネットワーク設定を取得します
23. `get_vpc_flow_logs`: フィルタリング付きで CloudWatch から VPC フローログを取得します

#### Network Firewall ツール {#network-firewall-tools}
24. `list_network_firewalls`: リージョン内のすべての AWS Network Firewall を一覧表示します
25. `get_firewall_rules`: ステートレスおよびステートフルなファイアウォールルールを取得します
26. `get_network_firewall_flow_logs`: CloudWatch からファイアウォールのフローログを取得します

#### VPN ツール {#vpn-tools}
27. `list_vpn_connections`: リージョン内のすべての Site-to-Site VPN 接続を一覧表示します

## 前提条件 {#prerequisites}
- [認証情報が設定された](https://docs.aws.amazon.com/cli/v1/userguide/cli-configure-files.html) AWS アカウントを用意します
- [Astral](https://docs.astral.sh/uv/getting-started/installation/) または [GitHub README](https://github.com/astral-sh/uv#installation) から uv をインストールします
- uv python install 3.10 (またはそれ以降のバージョン) を使用して Python 3.10 以降をインストールします
- この MCP サーバーは、LLM クライアントと同じホスト上でのみローカルに実行できます。

## 設定 {#configuration}

AWS Network MCP サーバーは GitHub からダウンロードできます。Kiro、Cursor、Cline など、MCP をサポートするお好みのコードアシスタントで使い始めることができます。

```json
{
  "mcpServers": {
    "awslabs.aws-network-mcp-server": {
      "command": "uvx",
      "args": [
        "awslabs.aws-network-mcp-server@latest"
      ],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-west-2"
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
    "awslabs.aws-network-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.aws-network-mcp-server@latest",
        "awslabs.aws-network-mcp-server.exe"
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

### AWS 認証 {#aws-authentication}

推奨される認証方法は [AWS 名前付きプロファイル](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html)です。この MCP は名前付きプロファイルを使用することで、アカウントの高速な切り替えが可能です。

環境変数による AWS 認証情報も動作しますが、単一アカウントでの使用に限定されます。

#### 必要な IAM 権限 {#required-iam-permissions}

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeNetworkInterfaces",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeNetworkAcls",
        "ec2:DescribeRouteTables",
        "ec2:DescribeSubnets",
        "ec2:DescribeVpcs",
        "ec2:DescribeInternetGateways",
        "ec2:DescribeNatGateways",
        "ec2:DescribeVpcEndpoints",
        "ec2:DescribeTransitGateways",
        "ec2:DescribeTransitGatewayAttachments",
        "ec2:DescribeTransitGatewayRouteTables",
        "ec2:DescribeTransitGatewayPeeringAttachments",
        "ec2:DescribeVpnConnections",
        "ec2:DescribeFlowLogs",
        "ec2:DescribeRegions",
        "networkmanager:GetCoreNetwork",
        "networkmanager:GetCoreNetworkPolicy",
        "networkmanager:GetNetworkRoutes",
        "networkmanager:GetVpcAttachment",
        "networkmanager:GetConnectAttachment",
        "networkmanager:GetDirectConnectGatewayAttachment",
        "networkmanager:GetSiteToSiteVpnAttachment",
        "networkmanager:GetTransitGatewayRouteTableAttachment",
        "networkmanager:GetTransitGatewayPeering",
        "networkmanager:GetTransitGatewayRegistrations",
        "networkmanager:GetTransitGatewayRouteTableAssociations",
        "networkmanager:ListCoreNetworks",
        "networkmanager:ListAttachments",
        "networkmanager:ListPeerings",
        "network-firewall:DescribeFirewall",
        "network-firewall:DescribeFirewallPolicy",
        "network-firewall:DescribeRuleGroup",
        "network-firewall:DescribeLoggingConfiguration",
        "network-firewall:ListFirewalls",
        "elasticloadbalancing:DescribeLoadBalancers",
        "logs:StartQuery",
        "logs:GetQueryResults",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

#### マルチアカウントアクセス {#multi-account-access}

クロスアカウントアクセスのために別の AWS CLI プロファイルを指定するには、ツールの `profile_name` パラメータを使用します。一部のツールは、リソースごとに個別のプロファイルをサポートしています (例: `tgw_account_profile_name` と `cloudwan_account_profile_name`)。

### データの使用 {#data-usage}

この MCP サーバーは完全にローカルで動作し、AWS サービスに直接 API 呼び出しを行います。サードパーティのサービスにデータが送信されることはありません。すべての AWS API 呼び出しは、AWS のサービス利用規約および組織の AWS ポリシーに従います。

### よくある質問 {#faqs}

#### 1. AWS アカウントは必要ですか? {#1-do-i-need-an-aws-account}

はい。このサーバーは AWS サービスへ API 呼び出しを行うため、適切な IAM 権限を持つ有効な AWS 認証情報が必要です。

#### 2. どの AWS リージョンがサポートされていますか? {#2-what-aws-regions-are-supported}

すべての AWS 商用リージョンがサポートされています。マルチリージョン検索をサポートするツール (`find_ip_address` など) は、アカウントで有効化されているすべてのリージョンを検索できます。

#### 3. 一部のツールに Network Manager への登録が必要なのはなぜですか? {#3-why-do-some-tools-require-network-manager-registration}

Transit Gateway のルートツール (`get_tgw_routes`、`get_all_tgw_routes`) を使用するには、Transit Gateway が AWS Network Manager (Cloud WAN グローバルネットワーク) に登録されている必要があります。これは、Network Manager API 経由でルートテーブル情報にアクセスするための AWS の要件です。

#### 4. フローログのツールは CloudWatch Logs なしで動作しますか? {#4-do-flow-log-tools-work-without-cloudwatch-logs}

いいえ。フローログのツール (`get_vpc_flow_logs`、`get_tgw_flow_logs`、`get_network_firewall_flow_logs`) を使用するには、フローログが有効化され、ログの送信先が CloudWatch Logs (S3 や Kinesis Data Firehose ではなく) に設定されている必要があります。

#### 5. このサーバーは AWS インフラストラクチャに変更を加えることができますか? {#5-can-this-server-make-changes-to-my-aws-infrastructure}

いいえ。すべてのツールは読み取り専用で、Describe、Get、List 操作のみを実行します。このサーバーは AWS リソースの作成、変更、削除を行うことはできません。

#### 6. 「No flow logs found」エラーをトラブルシューティングするにはどうすればよいですか? {#6-how-do-i-troubleshoot-no-flow-logs-found-errors}

以下を確認してください。
- リソース (VPC、Transit Gateway、または Network Firewall) でフローログが有効化されていること
- ログの送信先が CloudWatch Logs に設定されていること
- 指定した時間範囲に、トラフィックが流れていた期間が含まれていること
- IAM 権限に `logs:FilterLogEvents` が含まれていること
