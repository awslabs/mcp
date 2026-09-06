---
title: "AWS IAM MCPサーバー"
---

AWS Identity and Access Management (IAM) の包括的な操作を提供する Model Context Protocol (MCP) サーバーです。このサーバーは、セキュリティのベストプラクティスに従いながら、AI アシスタントが IAM のユーザー、ロール、ポリシー、権限を管理できるようにします。

## 機能 {#features}

### IAM のコア管理 {#core-iam-management}
- **ユーザー管理**: IAM ユーザーの作成、一覧表示、取得、削除
- **ロール管理**: 信頼ポリシーを持つ IAM ロールの作成、一覧表示、管理
- **グループ管理**: メンバー管理を含む IAM グループの作成、一覧表示、取得、削除
- **ポリシー管理**: IAM ポリシー（マネージドおよびインライン）の一覧表示と管理
- **インラインポリシー管理**: ユーザーおよびロールのインラインポリシーに対する完全な CRUD 操作
- **権限管理**: ユーザーおよびロールへのポリシーのアタッチ/デタッチ
- **アクセスキー管理**: ユーザーのアクセスキーの作成と削除
- **セキュリティシミュレーション**: ポリシーを適用する前に権限をテスト

### セキュリティ機能 {#security-features}
- **ポリシーシミュレーション**: 変更を加えずに権限をテスト
- **強制削除**: 関連するすべてのリソースとともにユーザーを安全に削除
- **アクセス許可境界のサポート**: セキュリティを強化するためのアクセス許可境界の設定
- **信頼ポリシーの検証**: ロールの JSON 信頼ポリシーを検証
- **読み取り専用モード**: あらゆる変更を防止する読み取り専用モードでのサーバー実行

### ベストプラクティスの統合 {#best-practices-integration}
- AWS IAM のセキュリティベストプラクティスに準拠
- 最小権限の原則をサポート
- 機密性の高い操作に対する警告を提供
- 包括的なエラーハンドリングを搭載

## インストール {#installation}

```bash
# Install using uv (recommended)
uv tool install awslabs.iam-mcp-server

# Or install using pip
pip install awslabs.iam-mcp-server
```

## 設定 {#configuration}

### AWS 認証情報 {#aws-credentials}
このサーバーには AWS 認証情報の設定が必要です。以下のいずれかの方法を使用できます。

1. **AWS プロファイル**（推奨）:
   ```bash
   export AWS_PROFILE=your-profile-name
   ```

2. **環境変数**:
   ```bash
   export AWS_ACCESS_KEY_ID=your-access-key
   export AWS_SECRET_ACCESS_KEY=your-secret-key
   export AWS_REGION=us-east-1
   ```

3. **IAM ロール**（EC2/Lambda 向け）:
   AWS サービス上で実行されている場合、サーバーは自動的に IAM ロールを使用します。

### 必要な IAM 権限 {#required-iam-permissions}

このサーバーが使用する AWS 認証情報には、以下の IAM 権限が必要です。

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "iam:ListUsers",
                "iam:GetUser",
                "iam:CreateUser",
                "iam:DeleteUser",
                "iam:ListRoles",
                "iam:GetRole",
                "iam:CreateRole",
                "iam:DeleteRole",
                "iam:ListGroups",
                "iam:GetGroup",
                "iam:CreateGroup",
                "iam:DeleteGroup",
                "iam:AddUserToGroup",
                "iam:RemoveUserFromGroup",
                "iam:AttachGroupPolicy",
                "iam:DetachGroupPolicy",
                "iam:ListAttachedGroupPolicies",
                "iam:ListGroupPolicies",
                "iam:ListPolicies",
                "iam:GetPolicy",
                "iam:CreatePolicy",
                "iam:DeletePolicy",
                "iam:AttachUserPolicy",
                "iam:DetachUserPolicy",
                "iam:AttachRolePolicy",
                "iam:DetachRolePolicy",
                "iam:ListAttachedUserPolicies",
                "iam:ListAttachedRolePolicies",
                "iam:ListUserPolicies",
                "iam:ListRolePolicies",
                "iam:GetUserPolicy",
                "iam:GetRolePolicy",
                "iam:PutUserPolicy",
                "iam:PutRolePolicy",
                "iam:GetGroupsForUser",
                "iam:ListAccessKeys",
                "iam:CreateAccessKey",
                "iam:DeleteAccessKey",
                "iam:SimulatePrincipalPolicy",
                "iam:RemoveUserFromGroup",
                "iam:DeleteUserPolicy",
                "iam:DeleteRolePolicy"
            ],
            "Resource": "*"
        }
    ]
}
```

### MCP クライアントの設定 {#mcp-client-configuration}

#### Kiro {#kiro}
`~/.kiro/settings/mcp.json` に以下を追加します。

```json
{
  "mcpServers": {
    "awslabs.iam-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.iam-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

#### Cline {#cline}
`cline_mcp_settings.json` に以下を追加します。

```json
{
  "mcpServers": {
    "awslabs.iam-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.iam-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

### Windows でのインストール {#windows-installation}

Windows ユーザーの場合、MCP サーバーの設定形式は少し異なります。

```json
{
  "mcpServers": {
    "awslabs.iam-mcp-server": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "--from",
        "awslabs.iam-mcp-server@latest",
        "awslabs.iam-mcp-server.exe"
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

#### ワンクリックインストール {#one-click-installation}

| Kiro | Cursor | VS Code |
|:----:|:------:|:-------:|
| [![Add to Kiro](https://kiro.dev/images/add-to-kiro.svg)](https://kiro.dev/launch/mcp/add?name=awslabs.iam-mcp-server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.iam-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) | [![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/en/install-mcp?name=awslabs.iam-mcp-server&config=eyJjb21tYW5kIjoidXZ4IiwiYXJncyI6WyJhd3NsYWJzLmlhbS1tY3Atc2VydmVyQGxhdGVzdCJdLCJlbnYiOnsiQVdTX1BST0ZJTEUiOiJ5b3VyLWF3cy1wcm9maWxlIiwiQVdTX1JFR0lPTiI6InVzLWVhc3QtMSIsIkZBU1RNQ1BfTE9HX0xFVkVMIjoiRVJST1IifX0%3D) | [![Install on VS Code](https://img.shields.io/badge/Install_on-VS_Code-FF9900?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=AWS%20IAM%20MCP%20Server&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22awslabs.iam-mcp-server%40latest%22%5D%2C%22env%22%3A%7B%22AWS_PROFILE%22%3A%22your-aws-profile%22%2C%22AWS_REGION%22%3A%22us-east-1%22%2C%22FASTMCP_LOG_LEVEL%22%3A%22ERROR%22%7D%7D) |

#### 手動設定 {#manual-configuration}

`.cursor/mcp.json` に以下を追加します。

```json
{
  "mcpServers": {
    "awslabs.iam-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.iam-mcp-server@latest"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

## 読み取り専用モード {#read-only-mode}

このサーバーは、読み取り操作は許可しつつ、すべての変更操作を防止する読み取り専用モードをサポートしています。これは次のような用途に役立ちます。

- **安全性**: 本番環境での誤った変更を防止
- **テスト**: 変更のリスクなしに IAM リソースを安全に探索
- **監査**: 読み取りアクセスのみを許可すべき環境でのサーバー実行

### 読み取り専用モードの有効化 {#enabling-read-only-mode}

サーバーの起動時に `--readonly` フラグを追加します。

```bash
# Using uvx
uvx awslabs.iam-mcp-server@latest --readonly

# Or if installed locally
python -m awslabs.iam_mcp_server.server --readonly
```

### 読み取り専用モードでの MCP クライアント設定 {#mcp-client-configuration-with-read-only-mode}

#### Kiro {#kiro-1}
```json
{
  "mcpServers": {
    "awslabs.iam-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.iam-mcp-server@latest", "--readonly"],
      "env": {
        "AWS_PROFILE": "your-aws-profile",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

#### その他の MCP クライアント {#other-mcp-clients}
MCP 設定の args 配列に `"--readonly"` を追加するだけです。

### 読み取り専用モードでブロックされる操作 {#operations-blocked-in-read-only-mode}

読み取り専用モードが有効な場合、以下の操作はエラーを返します。
- `create_user`
- `delete_user`
- `create_role`
- `attach_user_policy`
- `detach_user_policy`
- `create_access_key`
- `delete_access_key`

### 読み取り専用モードで利用可能な操作 {#operations-available-in-read-only-mode}

以下の操作は通常どおり動作します。
- `list_users`
- `get_user`
- `list_roles`
- `list_policies`
- `simulate_principal_policy`

## 利用可能なツール {#available-tools}

### ユーザー管理 {#user-management}

#### `list_users` {#list_users}
アカウント内の IAM ユーザーを一覧表示します。オプションでフィルタリングが可能です。

**パラメータ:**
- `path_prefix`（オプション）: ユーザーをフィルタリングするパスプレフィックス（例: "/division_abc/"）
- `max_items`（オプション）: 返すユーザーの最大数（デフォルト: 100）

#### `get_user` {#get_user}
アタッチされたポリシー、グループ、アクセスキーを含む、特定の IAM ユーザーの詳細情報を取得します。

**パラメータ:**
- `user_name`: 取得する IAM ユーザーの名前

#### `create_user` {#create_user}
新しい IAM ユーザーを作成します。

**パラメータ:**
- `user_name`: 新しい IAM ユーザーの名前
- `path`（オプション）: ユーザーのパス（デフォルト: "/"）
- `permissions_boundary`（オプション）: アクセス許可境界ポリシーの ARN

#### `delete_user` {#delete_user}
IAM ユーザーを削除します。オプションで強制クリーンアップが可能です。

**パラメータ:**
- `user_name`: 削除する IAM ユーザーの名前
- `force`（オプション）: アタッチされているすべてのリソースを先に削除して強制削除する（デフォルト: false）

### ロール管理 {#role-management}

#### `list_roles` {#list_roles}
アカウント内の IAM ロールを一覧表示します。オプションでフィルタリングが可能です。

**パラメータ:**
- `path_prefix`（オプション）: ロールをフィルタリングするパスプレフィックス（例: "/service-role/"）
- `max_items`（オプション）: 返すロールの最大数（デフォルト: 100）

#### `create_role` {#create_role}
信頼ポリシーを持つ新しい IAM ロールを作成します。

**パラメータ:**
- `role_name`: 新しい IAM ロールの名前
- `assume_role_policy_document`: JSON 形式の信頼ポリシードキュメント
- `path`（オプション）: ロールのパス（デフォルト: "/"）
- `description`（オプション）: ロールの説明
- `max_session_duration`（オプション）: 最大セッション時間（秒単位、デフォルト: 3600）
- `permissions_boundary`（オプション）: アクセス許可境界ポリシーの ARN

### グループ管理 {#group-management}

#### `list_groups` {#list_groups}
アカウント内の IAM グループを一覧表示します。オプションでフィルタリングが可能です。

**パラメータ:**
- `path_prefix`（オプション）: グループをフィルタリングするパスプレフィックス（例: "/division_abc/"）
- `max_items`（オプション）: 返すグループの最大数（デフォルト: 100）

#### `get_group` {#get_group}
メンバー、アタッチされたポリシー、インラインポリシーを含む、特定の IAM グループの詳細情報を取得します。

**パラメータ:**
- `group_name`: 取得する IAM グループの名前

#### `create_group` {#create_group}
新しい IAM グループを作成します。

**パラメータ:**
- `group_name`: 新しい IAM グループの名前
- `path`（オプション）: グループのパス（デフォルト: "/"）

#### `delete_group` {#delete_group}
IAM グループを削除します。オプションで強制クリーンアップが可能です。

**パラメータ:**
- `group_name`: 削除する IAM グループの名前
- `force`（オプション）: すべてのメンバーとポリシーを先に削除して強制削除する（デフォルト: false）

#### `add_user_to_group` {#add_user_to_group}
ユーザーを IAM グループに追加します。

**パラメータ:**
- `group_name`: IAM グループの名前
- `user_name`: IAM ユーザーの名前

#### `remove_user_from_group` {#remove_user_from_group}
ユーザーを IAM グループから削除します。

**パラメータ:**
- `group_name`: IAM グループの名前
- `user_name`: IAM ユーザーの名前

#### `attach_group_policy` {#attach_group_policy}
マネージドポリシーを IAM グループにアタッチします。

**パラメータ:**
- `group_name`: IAM グループの名前
- `policy_arn`: アタッチするポリシーの ARN

#### `detach_group_policy` {#detach_group_policy}
マネージドポリシーを IAM グループからデタッチします。

**パラメータ:**
- `group_name`: IAM グループの名前
- `policy_arn`: デタッチするポリシーの ARN

### ポリシー管理 {#policy-management}

#### `list_policies` {#list_policies}
アカウント内の IAM ポリシーを一覧表示します。

**パラメータ:**
- `scope`（オプション）: 一覧表示するポリシーのスコープ。"All"、"AWS"、"Local" のいずれか（デフォルト: "Local"）
- `only_attached`（オプション）: アタッチされているポリシーのみを返す（デフォルト: false）
- `path_prefix`（オプション）: ポリシーをフィルタリングするパスプレフィックス
- `max_items`（オプション）: 返すポリシーの最大数（デフォルト: 100）

#### `attach_user_policy` {#attach_user_policy}
マネージドポリシーを IAM ユーザーにアタッチします。

**パラメータ:**
- `user_name`: IAM ユーザーの名前
- `policy_arn`: アタッチするポリシーの ARN

#### `detach_user_policy` {#detach_user_policy}
マネージドポリシーを IAM ユーザーからデタッチします。

**パラメータ:**
- `user_name`: IAM ユーザーの名前
- `policy_arn`: デタッチするポリシーの ARN

### アクセスキー管理 {#access-key-management}

#### `create_access_key` {#create_access_key}
IAM ユーザーの新しいアクセスキーを作成します。

**パラメータ:**
- `user_name`: IAM ユーザーの名前

**⚠️ セキュリティ警告:** シークレットアクセスキーは一度しか返されず、後から再取得することはできません。

#### `delete_access_key` {#delete_access_key}
IAM ユーザーのアクセスキーを削除します。

**パラメータ:**
- `user_name`: IAM ユーザーの名前
- `access_key_id`: 削除するアクセスキー ID

### セキュリティ分析 {#security-analysis}

#### `simulate_principal_policy` {#simulate_principal_policy}
プリンシパルに対する IAM ポリシー評価をシミュレートして権限をテストします。

**パラメータ:**
- `policy_source_arn`: シミュレートするユーザーまたはロールの ARN
- `action_names`: シミュレートするアクションのリスト
- `resource_arns`（オプション）: テスト対象のリソース ARN のリスト
- `context_entries`（オプション）: シミュレーション用のコンテキストエントリ

### インラインポリシー管理 {#inline-policy-management}

#### `put_user_policy` {#put_user_policy}
IAM ユーザーのインラインポリシーを作成または更新します。

**パラメータ:**
- `user_name`: IAM ユーザーの名前
- `policy_name`: インラインポリシーの名前
- `policy_document`: JSON 形式のポリシードキュメント（文字列または dict）

#### `get_user_policy` {#get_user_policy}
IAM ユーザーのインラインポリシーを取得します。

**パラメータ:**
- `user_name`: IAM ユーザーの名前
- `policy_name`: インラインポリシーの名前

#### `delete_user_policy` {#delete_user_policy}
IAM ユーザーからインラインポリシーを削除します。

**パラメータ:**
- `user_name`: IAM ユーザーの名前
- `policy_name`: 削除するインラインポリシーの名前

#### `list_user_policies` {#list_user_policies}
IAM ユーザーのすべてのインラインポリシーを一覧表示します。

**パラメータ:**
- `user_name`: IAM ユーザーの名前

#### `put_role_policy` {#put_role_policy}
IAM ロールのインラインポリシーを作成または更新します。

**パラメータ:**
- `role_name`: IAM ロールの名前
- `policy_name`: インラインポリシーの名前
- `policy_document`: JSON 形式のポリシードキュメント（文字列または dict）

#### `get_role_policy` {#get_role_policy}
IAM ロールのインラインポリシーを取得します。

**パラメータ:**
- `role_name`: IAM ロールの名前
- `policy_name`: インラインポリシーの名前

#### `delete_role_policy` {#delete_role_policy}
IAM ロールからインラインポリシーを削除します。

**パラメータ:**
- `role_name`: IAM ロールの名前
- `policy_name`: 削除するインラインポリシーの名前

#### `list_role_policies` {#list_role_policies}
IAM ロールのすべてのインラインポリシーを一覧表示します。

**パラメータ:**
- `role_name`: IAM ロールの名前

## 使用例 {#usage-examples}

### 基本的なユーザー管理 {#basic-user-management}
```python
# List all users
users = await list_users()

# Get specific user details
user_details = await get_user(user_name="john.doe")

# Create a new user
new_user = await create_user(
    user_name="jane.smith",
    path="/developers/"
)

# Delete a user (with force cleanup)
await delete_user(user_name="old.user", force=True)
```

### ロール管理 {#role-management-1}
```python
# Create a role for EC2 instances
trust_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"Service": "ec2.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }
    ]
}

role = await create_role(
    role_name="EC2-S3-Access-Role",
    assume_role_policy_document=json.dumps(trust_policy),
    description="Role for EC2 instances to access S3"
)
```

### グループ管理 {#group-management-1}
```python
# Create a new group
group = await create_group(
    group_name="Developers",
    path="/teams/"
)

# Add users to the group
await add_user_to_group(
    group_name="Developers",
    user_name="john.doe"
)

# Attach a policy to the group
await attach_group_policy(
    group_name="Developers",
    policy_arn="arn:aws:iam::123456789012:policy/DeveloperPolicy"
)

# Get group details including members
group_details = await get_group(group_name="Developers")
```

### ポリシー管理 {#policy-management-1}
```python
# List customer managed policies
policies = await list_policies(scope="Local", only_attached=True)

# Attach a policy to a user
await attach_user_policy(
    user_name="developer",
    policy_arn="arn:aws:iam::123456789012:policy/DeveloperPolicy"
)
```

### セキュリティテスト {#security-testing}
```python
# Test if a user can perform specific actions
simulation = await simulate_principal_policy(
    policy_source_arn="arn:aws:iam::123456789012:user/developer",
    action_names=["s3:GetObject", "s3:PutObject"],
    resource_arns=["arn:aws:s3:::my-bucket/*"]
)
```

### インラインポリシー管理 {#inline-policy-management-1}
```python
# Create an inline policy for a user
policy_document = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": ["s3:GetObject", "s3:PutObject"],
            "Resource": "arn:aws:s3:::my-bucket/*"
        }
    ]
}

await put_user_policy(
    user_name="developer",
    policy_name="S3AccessPolicy",
    policy_document=policy_document
)

# Retrieve an inline policy
policy = await get_user_policy(
    user_name="developer",
    policy_name="S3AccessPolicy"
)

# List all inline policies for a user
policies = await list_user_policies(user_name="developer")

# Create an inline policy for a role
await put_role_policy(
    role_name="EC2-S3-Access-Role",
    policy_name="S3ReadOnlyPolicy",
    policy_document={
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "s3:GetObject",
                "Resource": "*"
            }
        ]
    }
)

# Delete an inline policy
await delete_user_policy(
    user_name="developer",
    policy_name="S3AccessPolicy"
)
```

## セキュリティのベストプラクティス {#security-best-practices}

1. **最小権限の原則**: 常に必要最小限の権限のみを付与する
2. **アプリケーションにはロールを使用**: アプリケーションにはユーザーではなく IAM ロールを優先する
3. **定期的なアクセスレビュー**: 未使用のユーザーと権限を定期的に確認してクリーンアップする
4. **アクセスキーのローテーション**: アクセスキーを定期的にローテーションする
5. **MFA の有効化**: 可能な限り多要素認証を使用する
6. **アクセス許可境界**: アクセス許可境界を使用して最大権限を設定する
7. **ポリシーシミュレーション**: 本番環境に適用する前にポリシーをテストする
8. **マネージドポリシーの優先**: 再利用可能な権限にはインラインポリシーよりマネージドポリシーを使用する
9. **インラインポリシーのガイドライン**: インラインポリシーは単一のアイデンティティに固有の権限にのみ使用する

## エラーハンドリング {#error-handling}

このサーバーは、わかりやすいメッセージによる包括的なエラーハンドリングを提供します。

- **認証エラー**: 認証情報の問題に関する明確なメッセージ
- **権限エラー**: 不足している権限に関する具体的な情報
- **リソースが見つからない場合**: リソースが存在しない場合の役立つメッセージ
- **検証エラー**: 無効なパラメータに関する詳細なフィードバック

## 開発 {#development}

### テストの実行 {#running-tests}
```bash
# Install development dependencies
uv sync --dev

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=awslabs.iam_mcp_server
```

### ローカル開発 {#local-development}
```bash
# Install in development mode
uv pip install -e .

# Run the server directly
python -m awslabs.iam_mcp_server.server
```

## コントリビューション {#contributing}

コントリビューションを歓迎します。ガイドラインについては、メインリポジトリの [CONTRIBUTING.md](https://github.com/awslabs/mcp/blob/main/CONTRIBUTING.md) を参照してください。

## ライセンス {#license}

このプロジェクトは Apache License 2.0 の下でライセンスされています。詳細については [LICENSE](https://github.com/awslabs/mcp/blob/main/src/iam-mcp-server/LICENSE) ファイルを参照してください。

## サポート {#support}

問題や質問がある場合:
1. [AWS IAM ドキュメント](https://docs.aws.amazon.com/iam/) を確認する
2. [MCP 仕様](https://modelcontextprotocol.io/) を確認する
3. [GitHub リポジトリ](https://github.com/awslabs/mcp) で issue を作成する

## 変更履歴 {#changelog}

バージョン履歴と変更内容については [CHANGELOG.md](https://github.com/awslabs/mcp/blob/main/src/iam-mcp-server/CHANGELOG.md) を参照してください。
