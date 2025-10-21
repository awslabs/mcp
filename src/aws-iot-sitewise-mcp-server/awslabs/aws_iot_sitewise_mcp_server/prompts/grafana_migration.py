# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""AWS IoT SiteWise to AWS Managed Grafana Migration Prompt."""

from awslabs.aws_iot_sitewise_mcp_server.validation import (
    validate_string_for_injection,
)
from awslabs.aws_iot_sitewise_mcp_server.utils.aws_helper import AwsHelper
from mcp.server.fastmcp.prompts import Prompt


def grafana_workspace_migration(portal_id: str) -> str:
    """Generate a comprehensive migration strategy from AWS IoT SiteWise Monitor to AWS Managed Grafana.

    This prompt helps migrate SiteWise Monitor portals, projects, and dashboards 
    to AWS Managed Grafana workspaces with proper folder organization and 
    dashboard conversion using the built-in conversion tools.

    Args:
        portal_id: The ID of the SiteWise portal to migrate

    Returns:
        Comprehensive migration strategy and implementation guide

    Raises:
        ValidationError: If the portal_id contains invalid characters
    """
    # Validate input strings for injections
    validate_string_for_injection(portal_id)

    region = AwsHelper.get_aws_region()
    partition = AwsHelper.get_aws_partition()
    
    return f"""
You are an AWS IoT SiteWise and AWS Managed Grafana expert helping to migrate 
monitoring infrastructure from SiteWise Monitor to AWS Managed Grafana.

**Migration Target**: Portal ID {portal_id}
**AWS Region**: {region}
**AWS Partition**: {partition}

## Partition Compatibility Check

⚠️ **IMPORTANT**: This migration process is only supported in the AWS commercial partition.

**Current Partition**: {partition}

{"✅ **SUPPORTED**: Proceeding with migration in AWS commercial partition." if partition == "aws" else f"❌ **NOT SUPPORTED**: Migration is not supported in the '{partition}' partition. This tool only works in the AWS commercial partition ('aws'). Please use this migration guide in an AWS commercial region."}

{"" if partition == "aws" else "**Migration process will be skipped due to unsupported partition.**"}

## Migration Architecture Overview

**Mapping Strategy**:
- **SiteWise Portal** → **AWS Managed Grafana Workspace**
- **SiteWise Project** → **Grafana Folder**
- **SiteWise Dashboard** → **Grafana Dashboard** (using convert_dashboard_by_id tool)
- **SiteWise Access Policy** → **Grafana Permission**

## Step-by-Step Migration Process

{f'''
⚠️ **MIGRATION SKIPPED**: The following migration steps are not executed because the current partition is "{partition}", not "aws".

To use this migration guide:
1. Switch to an AWS commercial region (us-east-1, us-west-2, eu-west-1, etc.)
2. Ensure your AWS CLI is configured for the commercial partition
3. Re-run this migration guide

The migration steps below are provided for reference only and will not be executed.

---
''' if partition != 'aws' else ""}

### 1. **Portal Discovery and Analysis**

First, analyze the source SiteWise portal structure:

```
# Get portal details
describe_portal(
    portal_id="{portal_id}"
    region="{region}"
)

# List all projects in the portal
list_projects(
    portal_id="{portal_id}"
    region="{region}"
)

# For each project, list dashboards
list_dashboards(
    project_id="<project_id>"
    region="{region}"
)

# List all access-policies in the portal
list_access_policies(
    identity_type="USER",
    resource_type="PORTAL",
    resource_id="{portal_id}"
    region="{region}"
)
```

**Analysis Checklist**:
- Portal name, description, and contact email
- Number of projects and their organization
- Total dashboard count and complexity
- User access patterns and permissions
- Asset dependencies and data sources

### 2. **AWS Managed Grafana Workspace Setup**

Create and configure the target Grafana workspace:

**Step 2.1: Create IAM Service Role for Grafana**

First, create the required IAM role for the Grafana workspace:

```bash
# Generate a unique UUID for the role name
ROLE_UUID=$(uuidgen)
ROLE_NAME="AmazonGrafanaServiceRole-$ROLE_UUID"
ACCOUNT_ID=$(aws sts get-caller-identity --region {region} --query Account --output text)

# Create trust policy document
cat > grafana-trust-policy.json << EOF
{{
    "Version": "2012-10-17",
    "Statement": [
        {{
            "Effect": "Allow",
            "Principal": {{
                "Service": "grafana.amazonaws.com"
            }},
            "Action": "sts:AssumeRole",
            "Condition": {{
                "StringEquals": {{
                    "aws:SourceAccount": "$ACCOUNT_ID"
                }},
                "StringLike": {{
                    "aws:SourceArn": "arn:{partition}:grafana:{region}:$ACCOUNT_ID:/workspaces/*"
                }}
            }}
        }}
    ]
}}
EOF

# Create the IAM role
aws iam create-role \\
  --role-name "$ROLE_NAME" \\
  --path "/service-role/" \\
  --assume-role-policy-document file://grafana-trust-policy.json \\
  --description "Service role for AWS Managed Grafana workspace" \\
  --region {region}

# Attach the AWS managed policy for SiteWise read-only access
aws iam attach-role-policy \\
  --role-name "$ROLE_NAME" \\
  --policy-arn "arn:{partition}:iam::aws:policy/AWSIoTSiteWiseReadOnlyAccess" \\
  --region {region}

# Get the role ARN for workspace creation
ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text --region {region})
echo "Created IAM role: $ROLE_ARN"
```

**Step 2.2: Create Grafana Workspace**

Using the portal details obtained from Step 1, create a workspace with the portal name:

```bash
# Extract portal information from Step 1 results
# Assuming portal details are stored in variables from describe_portal call in Step 1
PORTAL_NAME="<portal_name_from_step1>"  # Use the portal name from Step 1
PORTAL_DESCRIPTION="<portal_description_from_step1>"  # Use the portal description from Step 1

# Sanitize portal name for workspace naming (only allow [a-zA-Z0-9-._~] characters)
SANITIZED_PORTAL_NAME=$(echo "$PORTAL_NAME" | sed 's/[^a-zA-Z0-9._~-]/-/g' | sed 's/--*/-/g' | sed 's/^-\\|-$//g')
WORKSPACE_NAME="$SANITIZED_PORTAL_NAME-grafana-workspace"

# Ensure workspace name is within 255 character limit
if [ ${{#WORKSPACE_NAME}} -gt 255 ]; then
    # Truncate the sanitized portal name to fit within limit
    MAX_PORTAL_NAME_LENGTH=$((255 - 18))  # 18 = length of "-grafana-workspace"
    TRUNCATED_PORTAL_NAME=$(echo "$SANITIZED_PORTAL_NAME" | cut -c1-$MAX_PORTAL_NAME_LENGTH)
    WORKSPACE_NAME="$TRUNCATED_PORTAL_NAME-grafana-workspace"
fi

echo "Creating workspace for portal: $PORTAL_NAME"
echo "Workspace name: $WORKSPACE_NAME"
```

**Workspace Configuration**:
```json
{{
  "name": "$WORKSPACE_NAME",
  "description": "Migrated from SiteWise Portal: $PORTAL_NAME ({portal_id}) - $PORTAL_DESCRIPTION",
  "accountAccessType": "CURRENT_ACCOUNT",
  "authenticationProviders": ["AWS_SSO"],
  "permissionType": "SERVICE_MANAGED",
  "dataSources": ["SITEWISE"],
  "notificationDestinations": ["SNS"],
  "workspaceRoleArn": "$ROLE_ARN",
  "configuration": "{{\\"plugins\\":{{\\"pluginAdminEnabled\\":true}}}}"
}}
```

**Create Grafana workspace with the portal name**:
```bash
# Create Grafana workspace using the portal name from Step 1
WORKSPACE_ID=$(aws grafana create-workspace \\
  --workspace-name "$WORKSPACE_NAME" \\
  --workspace-description "Migrated from SiteWise Portal: $PORTAL_NAME ({portal_id}) - $PORTAL_DESCRIPTION" \\
  --account-access-type CURRENT_ACCOUNT \\
  --authentication-providers AWS_SSO \\
  --permission-type SERVICE_MANAGED \\
  --workspace-data-sources SITEWISE \\
  --workspace-role-arn "$ROLE_ARN" \\
  --configuration '{{"plugins":{{"pluginAdminEnabled":true}}}}' \\
  --region {region} \\
  --query 'workspace.id' --output text)

echo "Created Grafana workspace: $WORKSPACE_ID"
echo "Workspace name: $WORKSPACE_NAME"
echo "Based on portal: $PORTAL_NAME ({portal_id})"
```

**Step 2.3: Poll for Workspace Status**

Wait up to 10 minutes for the workspace to become ACTIVE before proceeding:

```bash
# Poll workspace status until ACTIVE (with 10-minute timeout)
echo "Waiting for workspace to become ACTIVE (timeout: 10 minutes)..."
TIMEOUT=600  # 10 minutes in seconds
ELAPSED=0
INTERVAL=30  # Check every 30 seconds

while [ $ELAPSED -lt $TIMEOUT ]; do
    STATUS=$(aws grafana describe-workspace \\
        --workspace-id "$WORKSPACE_ID" \\
        --region {region} \\
        --query 'workspace.status' --output text)
    
    echo "Current workspace status: $STATUS (elapsed: ${{ELAPSED}}s)"
    
    if [ "$STATUS" = "ACTIVE" ]; then
        echo "✅ Workspace is now ACTIVE and ready for configuration"
        break
    elif [ "$STATUS" = "CREATION_FAILED" ]; then
        echo "❌ ERROR: Workspace creation failed"
        exit 1
    else
        echo "Workspace status: $STATUS - waiting ${{INTERVAL}} seconds..."
        sleep $INTERVAL
        ELAPSED=$((ELAPSED + INTERVAL))
    fi
done

# Check if we timed out
if [ $ELAPSED -ge $TIMEOUT ]; then
    echo "❌ ERROR: Timeout waiting for workspace to become ACTIVE after 10 minutes"
    echo "Current status: $STATUS"
    echo "Please check the AWS console for workspace creation issues"
    exit 1
fi
```

**Step 2.4: Create API Key for Workspace Management**

Once the workspace is ACTIVE, create an API key for programmatic access:

```bash
# Create workspace API key
API_KEY_RESPONSE=$(aws grafana create-workspace-api-key \\
  --workspace-id "$WORKSPACE_ID" \\
  --key-name "migration-key" \\
  --key-role ADMIN \\
  --seconds-to-live 3600 \\
  --region {region})

API_KEY=$(echo "$API_KEY_RESPONSE" | jq -r '.key')
WORKSPACE_ENDPOINT=$(aws grafana describe-workspace \\
  --workspace-id "$WORKSPACE_ID" \\
  --region {region} \\
  --query 'workspace.endpoint' --output text)

echo "API Key created successfully"
echo "Workspace Endpoint: $WORKSPACE_ENDPOINT"
echo "API Key: $API_KEY"

# Store these values for subsequent operations
export GRAFANA_API_KEY="$API_KEY"
export GRAFANA_ENDPOINT="$WORKSPACE_ENDPOINT"
```

### 3. **SiteWise Data Source Configuration**

Set up the SiteWise data source in Grafana using the API key:

**Step 3.1: Install SiteWise Data Source Plugin** ⚠️ **CRITICAL - DO NOT SKIP**

First, install the required SiteWise data source plugin using the Grafana Plugin API:

```bash
# Install the SiteWise data source plugin
curl -X POST \\
  "$GRAFANA_ENDPOINT/api/plugins/grafana-iot-sitewise-datasource/install" \\
  -H "Authorization: Bearer $GRAFANA_API_KEY" \\
  -H "Content-Type: application/json"

# Verify plugin installation
curl -X GET \\
  "$GRAFANA_ENDPOINT/api/gnet/plugins/grafana-iot-sitewise-datasource" \\
  -H "Authorization: Bearer $GRAFANA_API_KEY" \\
  -H "Content-Type: application/json"

echo "SiteWise data source plugin installed successfully"
```

**Step 3.2: Configure SiteWise Data Source**

⚠️ **PREREQUISITE**: Ensure Step 3.1 (Install SiteWise Data Source Plugin) has been completed successfully before proceeding with this step. The data source configuration will fail if the plugin is not installed.

**Data Source Configuration using Grafana API**:
```bash
# Configure SiteWise data source using the API key
curl -X POST \\
  "$GRAFANA_ENDPOINT/api/datasources" \\
  -H "Authorization: Bearer $GRAFANA_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "name": "AWS IoT SiteWise",
    "type": "grafana-iot-sitewise-datasource",
    "uid": "sitewise-datasource",
    "access": "proxy",
    "jsonData": {{
      "authType": "default",
      "defaultRegion": "{region}",
      "assumeRoleArn": "",
      "externalId": ""
    }},
    "isDefault": true
  }}'

# Verify data source creation
curl -X GET \\
  "$GRAFANA_ENDPOINT/api/datasources/uid/"sitewise-datasource" \\
  -H "Authorization: Bearer $GRAFANA_API_KEY"
```

**Alternative: Data Source Configuration JSON**:
```json
{{
  "name": "AWS IoT SiteWise",
  "type": "grafana-iot-sitewise-datasource",
  "uid": "sitewise-datasource",
  "access": "proxy",
  "jsonData": {{
    "authType": "default",
    "defaultRegion": "{region}",
    "assumeRoleArn": "",
    "externalId": ""
  }},
  "isDefault": true
}}
```

### 4. **Project-to-Folder Migration**

Skip this step if there is no project to migrate.

For each SiteWise project, create corresponding Grafana folders using the API key:

**Migration Process**:
```python
# Get all projects
projects = list_projects(
    portal_id="{portal_id}"
    region="{region}"
)

for index, project in enumerate(projects["projectSummaries"]):
    project_id = project["id"]
    project_name = project["name"]
    project_description = project.get("description", "")
    
    # Generate folder UID using index (max 40 characters)
    folder_uid = f"folder-{{index + 1:04d}}"  # e.g., "folder-0001", "folder-0002"
    
    # Create Grafana folder using API
    folder_data = {{
        "title": project_name,
        "uid": folder_uid,
        "tags": ["migrated-from-sitewise", f"project-{{project_id}}"]
    }}
    
    # Use curl to create folder via Grafana API
    curl_command = f'''
    curl -X POST \\
      "$GRAFANA_ENDPOINT/api/folders" \\
      -H "Authorization: Bearer $GRAFANA_API_KEY" \\
      -H "Content-Type: application/json" \\
      -d '{{
        "title": "{{project_name}}",
        "uid": "{{folder_uid}}",
        "tags": ["migrated-from-sitewise", "project-{{project_id}}"]
      }}'
    '''
    
    print(f"Create folder {{index + 1}}: {{project_name}} ({{project_id}})")
    print(f"Folder UID: {{folder_uid}}")
    print(f"API Command: {{curl_command}}")
```

**Folder Organization Strategy**:
- Use project names as folder titles
- Folder titles do not need to be unique
- Generate folder UIDs using sequential index with 4 digits (folder-0001, folder-0002, etc.)
- Maintain project ID traceability through tags
- Add migration tags for easy identification
- Preserve project descriptions in folder metadata

### 5. **Dashboard Conversion and Migration**

Skip this step if there is no dashboard to migrate.

Use the built-in dashboard conversion tools for each dashboard:

**Conversion Process**:
```python
# For each project, get and convert dashboards
dashboard_counter = 0  # Global counter for dashboard UIDs

for project in projects["projectSummaries"]:
    project_id = project["id"]
    dashboards = list_dashboards(
        project_id="<project_id>"
        region="{region}"
    )
    
    for dashboard in dashboards["dashboardSummaries"]:
        dashboard_id = dashboard["id"]
        dashboard_name = dashboard["name"]
        
        # Generate dashboard UID using sequential index with 4 digits
        dashboard_counter += 1
        dashboard_uid = f"dashboard-{{dashboard_counter:04d}}"  # e.g., 'dashboard-0001', 'dashboard-0002'
        
        # Convert dashboard using the conversion tool
        converted_dashboard = convert_dashboard_by_id(
            dashboard_id=dashboard_id,
            datasource_uid="sitewise-datasource",
            dashboard_name=dashboard_name,
            dashboard_uid=dashboard_uid,
            region="{region}"
        )
        
        # The converted dashboard is ready for Grafana import
        print(f"Converted dashboard {{dashboard_counter}}: {{dashboard_name}} ({{dashboard_id}})")
        print(f"Dashboard UID: {{dashboard_uid}}")
```

**Import Process**:
```bash
echo "Importing converted dashboard to Grafana..."
curl -X POST \\
  "$GRAFANA_ENDPOINT/api/dashboards/db" \\
  -H "Authorization: Bearer $GRAFANA_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d <dashboard-request-json>
```

##Grafana Dashboard Request
Creates a new dashboard or updates an existing dashboard.

`POST /api/dashboards/db`

###Example request to create a new dashboard
```
POST $GRAFANA_ENDPOINT/api/dashboards/db HTTP/1.1
Accept: application/json
Content-Type: application/json
Authorization: Bearer <GRAFANA_API_KEY>

{{
  "dashboard": "<dashboard-json>,
  "folderUid": "<folder_uid>",
  "overwrite": true
}}
```

####JSON body schema:

- dashboard — The complete dashboard model. Use null to create a new dashboard.
- folderUid — The Uid of the folder to save the dashboard in. Overrides the value of folderid
- overwrite — Specify true to overwrite an existing dashboard with a newer version, same dashboard title in folder or same dashboard uid.

**Dashboard Migration Features**:
- Automatic widget type conversion (line charts, scatter plots, bar charts, etc.)
- 1:4 scaling ratio for proper Grafana sizing
- Metric reference ID generation (Query-0, Query-1, etc.)
- Proper time series configuration
- Status grid and KPI panel conversion
- Import converted dashboard to Grafana

### 6. **User Access and Permissions Migration**

**⚠️ Prerequisites**: This section only applies to SiteWise portals with `portalAuthMode` set to **SSO**. 
User migration is **not supported** for IAM authentication mode portals.

**Step 6.1: Check Portal Authentication Mode**

First, verify the portal authentication mode to determine if user migration is possible:

```python
# Check portal authentication mode
portal_details = (
    portal_id="{portal_id}"
    region="{region}"
)
portal_auth_mode = portal_details["portal"]["portalAuthMode"]

print(f"Portal authentication mode: {{portal_auth_mode}}")

if portal_auth_mode != "SSO":
    print("⚠️  User migration is not supported for IAM authentication mode.")
    print("Please refer to the AWS Managed Grafana authentication documentation:")
    print("https://docs.aws.amazon.com/grafana/latest/userguide/authentication-in-AMG.html")
    print("for alternative authentication setup options.")
    print("Skipping user migration section...")
else:
    print("✅ Portal uses SSO authentication - proceeding with user migration")
```

**Step 6.2: Execute User Migration (SSO Portals Only)**

Skip this step if there is no access policies to migrate.

If the portal uses SSO authentication, proceed with user migration:

```python
# Execute user migration for SSO portals
if portal_auth_mode == "SSO":
    print("🔄 Starting user permissions migration...")
    
    # Get portal access policies
    access_policies = list_access_policies(
        identity_type="USER",
        resource_type="PORTAL",
        resource_id="{portal_id}"
        region="{region}"
    )
    
    print(f"Found {{len(access_policies.get('accessPolicySummaries', []))}} user access policies")
    
    # Create corresponding Grafana user permissions
    for policy in access_policies["accessPolicySummaries"]:
        identity = policy["identity"]
        permission = policy["permission"]
        
        # Map SiteWise permissions to Grafana roles
        if permission == "ADMINISTRATOR":
            grafana_role = "Admin"
        elif permission == "VIEWER":
            grafana_role = "Viewer"
        else:
            grafana_role = "Viewer"  # Default fallback
        
        user_id = identity.get("user", {{}}).get("id", "Unknown")
        print(f"User {{user_id}}: {{permission}} → {{grafana_role}}")
        
        # TODO: Implement actual Grafana user permission assignment via API
        # This would require additional Grafana workspace user management calls
    
    print("✅ User permissions migration completed")
else:
    print("⏭️  Skipping user migration due to IAM authentication mode")
```

**Step 6.3: Grafana User Management Using AWS Managed Grafana API**

For SSO portals, implement Grafana workspace user management using the AWS Managed Grafana `update-permissions` API:

```bash
# Update workspace permissions for migrated users
echo "🔄 Updating workspace permissions for SiteWise users..."

# For each user from the SiteWise portal access policies, update Grafana workspace permissions
for policy in access_policies["accessPolicySummaries"]:
    identity = policy["identity"]
    permission = policy["permission"]
    
    # Extract user information
    user_info = identity.get("user", {{}})
    user_id = user_info.get("id", "")
    
    if [ -n "$user_id" ]; then
        # Map SiteWise permissions to Grafana roles
        if [ "$permission" = "ADMINISTRATOR" ]; then
            GRAFANA_ROLE="ADMIN"
        elif [ "$permission" = "VIEWER" ]; then
            GRAFANA_ROLE="VIEWER"
        else
            GRAFANA_ROLE="VIEWER"  # Default fallback
        fi
        
        echo "🔧 Updating permissions for user: $user_id ({{permission}} → $GRAFANA_ROLE)"
        
        # Update user permissions using AWS Managed Grafana API
        aws grafana update-permissions \\
          --workspace-id "$WORKSPACE_ID" \\
          --update-instruction-batch '[
            {{
              "action": "ADD",
              "role": "'$GRAFANA_ROLE'",
              "users": [
                {{
                  "id": "'$user_id'",
                  "type": "SSO_USER"
                }}
              ]
            }}
          ]' \\
          --region {region}
        
        if [ $? -eq 0 ]; then
            echo "✅ Successfully updated permissions for user: $user_id"
        else
            echo "❌ Failed to update permissions for user: $user_id"
        fi
    else
        echo "⚠️  Skipping user - no valid user ID found in policy"
    fi
done

# Alternative batch update approach (for multiple users)
# If you have multiple users to update, you can use a single batch operation:

# Create batch update instruction
cat > permissions-update.json << EOF
[
  {{
    "action": "ADD",
    "role": "ADMIN",
    "users": [
      {{
        "id": "admin-user-1@example.com",
        "type": "SSO_USER"
      }},
      {{
        "id": "admin-user-2@example.com", 
        "type": "SSO_USER"
      }}
    ]
  }},
  {{
    "action": "ADD",
    "role": "VIEWER",
    "users": [
      {{
        "id": "viewer-user-1@example.com",
        "type": "SSO_USER"
      }},
      {{
        "id": "viewer-user-2@example.com",
        "type": "SSO_USER"
      }}
    ]
  }}
]
EOF

# Execute batch update
echo "🔄 Executing batch permissions update..."
aws grafana update-permissions \\
  --workspace-id "$WORKSPACE_ID" \\
  --update-instruction-batch file://permissions-update.json \\
  --region {region}

echo "✅ Grafana workspace user permissions migration completed"
```

**AWS Managed Grafana Permissions API Reference**:

- **Supported Roles**: `ADMIN`, `EDITOR`, `VIEWER`
- **Supported User Types**: `SSO_USER`, `SSO_GROUP`
- **Supported Actions**: `ADD`, `REVOKE`

**Permission Update Structure**:
```json
{{
  "action": "ADD|REVOKE",
  "role": "ADMIN|EDITOR|VIEWER", 
  "users": [
    {{
      "id": "user-identifier",
      "type": "SSO_USER|SSO_GROUP"
    }}
  ]
}}
```

**Best Practices for Permission Management**:
1. **Batch Operations**: Use batch updates for multiple users to reduce API calls
2. **Error Handling**: Check command exit codes and handle failures gracefully
3. **Incremental Updates**: Use `ADD` action to grant permissions, `REVOKE` to remove them
4. **User Identification**: Ensure user IDs match the SSO provider configuration

**Debugging Tips for Section 6**:

1. **Check Portal Authentication Mode**: Ensure the portal uses SSO, not IAM
2. **Verify Access Policies**: Confirm that `list_access_policies` returns valid data
3. **Enable Debug Logging**: Add print statements to track execution flow
4. **Check Prerequisites**: Ensure all previous sections completed successfully
5. **Manual Execution**: Try running the user migration code separately to isolate issues

**For IAM Authentication Portals**:
User migration is not supported for portals using IAM authentication mode. 
Please refer to the AWS Managed Grafana authentication documentation for alternative authentication setup options:
https://docs.aws.amazon.com/grafana/latest/userguide/authentication-in-AMG.html

### 7. **Data Validation and Testing**

**Post-Migration Validation**:
```python
# Validate dashboard functionality
def validate_migrated_dashboards():
    validation_results = []
    
    for dashboard_id in migrated_dashboards:
        # Test data queries
        test_result = test_dashboard_queries(dashboard_id)
        
        # Verify panel rendering
        panel_result = verify_panel_configurations(dashboard_id)
        
        # Check time series data
        data_result = validate_time_series_data(dashboard_id)
        
        validation_results.append({{
            "dashboard_id": dashboard_id,
            "queries_working": test_result,
            "panels_configured": panel_result,
            "data_available": data_result
        }})
    
    return validation_results
```

## Migration Checklist

### Pre-Migration:
- [ ] Analyze source portal structure
- [ ] Identify user access patterns
- [ ] Document dashboard dependencies
- [ ] Plan Grafana workspace architecture
- [ ] Set up AWS Managed Grafana workspace
- [ ] Configure SiteWise data source

### During Migration:
- [ ] Create folder structure
- [ ] Convert all dashboards using convert_dashboard_by_id
- [ ] Validate dashboard functionality
- [ ] Test data queries and visualizations
- [ ] Configure user permissions
- [ ] Set up alerting and notifications

### Post-Migration:
- [ ] Conduct user acceptance testing
- [ ] Provide user training
- [ ] Monitor system performance
- [ ] Gather user feedback
- [ ] Optimize based on usage patterns
- [ ] Plan decommissioning of old portal

## Troubleshooting Guide

**Common Issues and Solutions**:

1. **Dashboard Conversion Errors**:
   - Use validate_dashboard_definition before conversion
   - Check for unsupported widget types
   - Verify asset and property references

2. **Data Source Connection Issues**:
   - Verify IAM permissions for Grafana workspace
   - Check SiteWise data source configuration
   - Test connectivity with sample queries

3. **Permission Mapping Problems**:
   - Review AWS SSO configuration
   - Verify user group mappings
   - Test access with different user roles

4. **Performance Issues**:
   - Optimize query intervals
   - Review dashboard complexity
   - Configure appropriate caching

## Success Metrics

Track the following metrics to measure migration success:

**Technical Metrics**:
- Dashboard conversion success rate (target: 100%)
- Data query accuracy (target: 100% match with original)
- Performance improvement (target: <2s load time)
- User adoption rate (target: 90% within 30 days)

**Business Metrics**:
- Reduced operational overhead
- Improved monitoring capabilities
- Enhanced user experience
- Cost optimization through managed service

**Migration Timeline**:
- Planning phase: 1-2 weeks
- Implementation phase: 2-4 weeks
- Testing and validation: 1-2 weeks
- User training and rollout: 1-2 weeks

This comprehensive migration strategy ensures a smooth transition from AWS IoT SiteWise Monitor to AWS Managed Grafana while maintaining data integrity, user access, and operational continuity.
"""


# Create the prompt using from_function
grafana_workspace_migration_prompt = Prompt.from_function(
    grafana_workspace_migration,
    name='grafana_workspace_migration',
    description=(
        'Generate comprehensive migration strategy from AWS IoT SiteWise Monitor to AWS Managed Grafana'
    ),
)
