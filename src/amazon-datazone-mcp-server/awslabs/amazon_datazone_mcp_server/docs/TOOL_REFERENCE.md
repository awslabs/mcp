# AWS DataZone MCP Server Tool Reference

Complete reference for all tools provided by the AWS DataZone MCP server. Each tool corresponds to AWS DataZone API operations and is accessible through MCP-compatible clients.

## Quick Reference

| Category | Tools Count | Description |
|----------|-------------|-------------|
| [Domain Management](#-domain-management) | 11 tools | Domain operations, organizational units, permissions |
| [Project Management](#-project-management) | 6 tools | Projects, memberships, profiles |
| [Data Management](#-data-management) | 14 tools | Assets, listings, subscriptions, data sources |
| [Glossary Management](#-glossary-management) | 4 tools | Business glossaries and terms |
| [Environment Management](#-environment-management) | 3 tools | Environments and connections |

**Total: 38 tools** providing comprehensive AWS DataZone management capabilities.

---

## Domain Management

Manage AWS DataZone domains, organizational units, and access permissions.

### `get_domain`

Retrieve detailed information about a specific DataZone domain.

**Parameters:**
- `identifier` (str, required): Domain identifier (e.g., "dzd_4p9n6sw4qt9xgn")

**Returns:**
Domain details including name, ID, ARN, status, description, creation timestamp, portal URL, and SSO configuration.

**Example:**
```python
result = await client.call_tool("get_domain", {
    "identifier": "dzd_4p9n6sw4qt9xgn"
})
```

### `create_domain`

Create a new AWS DataZone domain.

**Parameters:**
- `name` (str, required): Domain name
- `domain_execution_role` (str, required): ARN of domain execution role
- `service_role` (str, required): ARN of service role
- `domain_version` (str, optional): Domain version ("V1" or "V2", default: "V2")
- `description` (str, optional): Domain description
- `kms_key_identifier` (str, optional): KMS key ARN for encryption
- `tags` (dict, optional): Tags to associate with domain
- `single_sign_on` (dict, optional): SSO configuration

**Returns:**
Created domain details including ID, ARN, status, and portal URL.

**Example:**
```python
result = await client.call_tool("create_domain", {
    "name": "Data Analytics Domain",
    "domain_execution_role": "arn:aws:iam::123456789012:role/DataZoneExecutionRole",
    "service_role": "arn:aws:iam::123456789012:role/DataZoneServiceRole",
    "description": "Domain for analytics workloads"
})
```

### `list_domain_units`

List child domain units for a specified parent domain unit.

**Parameters:**
- `domain_identifier` (str, required): Domain identifier
- `parent_domain_unit_identifier` (str, required): Parent domain unit identifier

**Returns:**
List of domain units with details including ID, name, description, and creation info.

### `create_domain_unit`

Create a new organizational unit within a domain.

**Parameters:**
- `domain_identifier` (str, required): Domain identifier
- `name` (str, required): Domain unit name (1-128 characters)
- `parent_domain_unit_identifier` (str, required): Parent domain unit ID
- `description` (str, optional): Description (0-2048 characters)
- `client_token` (str, optional): Idempotency token

**Returns:**
Created domain unit details including ID, name, parent relationships, and owners.

### `get_domain_unit`

Retrieve detailed information about a specific domain unit.

**Parameters:**
- `domain_identifier` (str, required): Domain identifier
- `identifier` (str, required): Domain unit identifier

**Returns:**
Domain unit details including hierarchy, owners, and metadata.

### `update_domain_unit`

Update properties of an existing domain unit.

**Parameters:**
- `domain_identifier` (str, required): Domain identifier
- `identifier` (str, required): Domain unit identifier
- `name` (str, optional): New name
- `description` (str, optional): New description
- `client_token` (str, optional): Idempotency token

**Returns:**
Updated domain unit details.

### `add_entity_owner`

Add ownership to DataZone entities (domain units, assets, etc.).

**Parameters:**
- `domain_identifier` (str, required): Domain identifier
- `entity_identifier` (str, required): Entity identifier
- `owner_identifier` (str, required): Owner identifier (user/group)
- `entity_type` (str, optional): Entity type (default: "DOMAIN_UNIT")
- `owner_type` (str, optional): Owner type (default: "USER")
- `client_token` (str, optional): Idempotency token

**Returns:**
Ownership assignment confirmation.

### `add_policy_grant`

Grant permissions to principals via DataZone policies.

**Parameters:**
- `domain_identifier` (str, required): Domain identifier
- `entity_identifier` (str, required): Entity identifier
- `entity_type` (str, required): Entity type
- `policy_type` (str, required): Policy type
- `principal_identifier` (str, required): Principal identifier
- `principal_type` (str, optional): Principal type (default: "USER")
- `client_token` (str, optional): Idempotency token
- `detail` (dict, optional): Policy-specific details

**Returns:**
Policy grant confirmation.

### `list_policy_grants`

List existing policy grants for an entity.

**Parameters:**
- `domain_identifier` (str, required): Domain identifier
- `entity_identifier` (str, required): Entity identifier
- `entity_type` (str, required): Entity type
- `policy_type` (str, required): Policy type
- `max_results` (int, optional): Max results (default: 50)
- `next_token` (str, optional): Pagination token

**Returns:**
List of policy grants with principal and permission details.

### `remove_policy_grant`

Remove policy grants from principals.

**Parameters:**
- `domain_identifier` (str, required): Domain identifier
- `entity_identifier` (str, required): Entity identifier
- `entity_type` (str, required): Entity type
- `policy_type` (str, required): Policy type
- `principal_identifier` (str, required): Principal identifier
- `principal_type` (str, optional): Principal type (default: "USER")
- `client_token` (str, optional): Idempotency token

**Returns:**
Policy grant removal confirmation.

### `search`

Search across DataZone entities (assets, projects, glossaries, etc.).

**Parameters:**
- `domain_identifier` (str, required): Domain identifier
- `search_scope` (str, required): Search scope ("ASSET", "LISTING", etc.)
- `additional_attributes` (list, optional): Additional attributes to return
- `filters` (dict, optional): Search filters
- `max_results` (int, optional): Max results (default: 50)
- `next_token` (str, optional): Pagination token
- `owning_project_identifier` (str, optional): Filter by owning project
- `search_in` (list, optional): Fields to search in
- `search_text` (str, optional): Search text query
- `sort` (dict, optional): Sort configuration

**Returns:**
Search results with matching entities and metadata.

---

## Project Management

Manage DataZone projects, memberships, and project profiles.

### `create_project`

Create a new project within a DataZone domain.

**Parameters:**
- `domain_identifier` (str, required): Domain identifier
- `name` (str, required): Project name
- `description` (str, optional): Project description
- `domain_unit_id` (str, optional): Domain unit ID
- `glossary_terms` (list, optional): List of glossary terms
- `project_profile_id` (str, optional): Project profile ID
- `user_parameters` (list, optional): User-defined parameters

**Returns:**
Created project details including ID, name, domain associations, and configuration.

**Example:**
```python
result = await client.call_tool("create_project", {
    "domain_identifier": "dzd_4p9n6sw4qt9xgn",
    "name": "Customer Analytics",
    "description": "Analytics project for customer data"
})
```

### `get_project`

Retrieve detailed information about a specific project.

**Parameters:**
- `domain_identifier` (str, required): Domain identifier
- `project_identifier` (str, required): Project identifier

**Returns:**
Project details including name, description, timestamps, domain relationships, status, environment deployments, user parameters, and glossary terms.

### `list_projects`

List projects in a DataZone domain with optional filtering.

**Parameters:**
- `domain_identifier` (str, required): Domain identifier
- `max_results` (int, optional): Max results (1-50, default: 50)
- `next_token` (str, optional): Pagination token
- `name` (str, optional): Filter by project name
- `user_identifier` (str, optional): Filter by user
- `group_identifier` (str, optional): Filter by group

**Returns:**
List of projects with basic information and pagination details.

### `create_project_membership`

Add members (users/groups) to a project.

**Parameters:**
- `domain_identifier` (str, required): Domain identifier
- `project_identifier` (str, required): Project identifier
- `member_identifier` (str, required): Member identifier
- `designation` (str, required): Member designation ("PROJECT_OWNER", "PROJECT_CONTRIBUTOR")
- `member_type` (str, optional): Member type ("USER" or "GROUP", default: "USER")

**Returns:**
Membership creation confirmation with member details.

### `list_project_profiles`

List available project profiles in a domain.

**Parameters:**
- `domain_identifier` (str, required): Domain identifier
- `max_results` (int, optional): Max results (1-50, default: 50)
- `next_token` (str, optional): Pagination token
- `name` (str, optional): Filter by profile name
- `sort_by` (str, optional): Sort field
- `sort_order` (str, optional): Sort order

**Returns:**
List of project profiles with configuration details.

### `create_project_profile`

Create a new project profile template.

**Parameters:**
- `domain_identifier` (str, required): Domain identifier
- `name` (str, required): Profile name
- `description` (str, optional): Profile description
- `domain_unit_identifier` (str, optional): Domain unit identifier
- `environment_configurations` (list, optional): Environment configurations
- `status` (str, optional): Profile status (default: "ENABLED")

**Returns:**
Created project profile details including ID, name, and configurations.

---

## Data Management

Manage data assets, listings, subscriptions, and data sources.

### `get_asset`

Retrieve detailed information about a data asset.

**Parameters:**
- `domain_identifier` (str, required): Domain identifier
- `asset_identifier` (str, required): Asset identifier
- `revision` (str, optional): Specific asset revision

**Returns:**
Asset details including name, description, type, creation timestamps, forms, metadata, glossary terms, listing status, and time series data.

### `create_asset`

Create a new data asset in a project.

**Parameters:**
- `domain_identifier` (str, required): Domain identifier
- `name` (str, required): Asset name
- `owning_project_identifier` (str, required): Owning project ID
- `type_identifier` (str, required): Asset type identifier
- `description` (str, optional): Asset description
- `external_identifier` (str, optional): External identifier
- `forms_input` (list, optional): Metadata forms
- `glossary_terms` (list, optional): Glossary terms
- `prediction_configuration` (dict, optional): ML prediction config
- `type_revision` (str, optional): Asset type revision
- `client_token` (str, optional): Idempotency token

**Returns:**
Created asset details including ID, name, type, and metadata.

### `publish_asset`

Publish an asset to the DataZone catalog to make it discoverable.

**Parameters:**
- `domain_identifier` (str, required): Domain identifier
- `asset_identifier` (str, required): Asset identifier
- `asset_scope` (dict, optional): Asset scope configuration
- `client_token` (str, optional): Idempotency token
- `glossary_terms` (list, optional): Glossary terms for listing
- `name` (str, optional): Custom listing name
- `type` (str, optional): Listing type

**Returns:**
Published listing details including listing ID and status.

### `get_listing`

Retrieve information about a published asset listing.

**Parameters:**
- `domain_identifier` (str, required): Domain identifier
- `identifier` (str, required): Listing identifier
- `listing_revision` (str, optional): Specific listing revision

**Returns:**
Listing details including asset information, publication status, and metadata.

### `search_listings`

Search for published asset listings in the catalog.

**Parameters:**
- `domain_identifier` (str, required): Domain identifier
- `additional_attributes` (list, optional): Additional attributes
- `filters` (dict, optional): Search filters
- `max_results` (int, optional): Max results (default: 50)
- `next_token` (str, optional): Pagination token
- `search_in` (list, optional): Fields to search in
- `search_text` (str, optional): Search query
- `sort` (dict, optional): Sort configuration

**Returns:**
Search results with matching listings and asset details.

### `create_data_source`

Create a new data source for ingesting data into DataZone.

**Parameters:**
- `domain_identifier` (str, required): Domain identifier
- `name` (str, required): Data source name
- `project_identifier` (str, required): Project identifier
- `type` (str, required): Data source type
- `asset_forms_input` (list, optional): Asset forms configuration
- `configuration` (dict, optional): Data source configuration
- `description` (str, optional): Description
- `enable_setting` (str, optional): Enable setting
- `environment_identifier` (str, optional): Environment identifier
- `publish_on_import` (bool, optional): Auto-publish on import
- `recommendation` (dict, optional): Recommendation configuration
- `schedule` (dict, optional): Schedule configuration
- `client_token` (str, optional): Idempotency token

**Returns:**
Created data source details including ID, configuration, and status.

### `get_data_source`

Retrieve information about a data source.

**Parameters:**
- `domain_identifier` (str, required): Domain identifier
- `identifier` (str, required): Data source identifier

**Returns:**
Data source details including configuration, status, and run history.

### `start_data_source_run`

Trigger a data source run to ingest or sync data.

**Parameters:**
- `domain_identifier` (str, required): Domain identifier
- `data_source_identifier` (str, required): Data source identifier
- `client_token` (str, optional): Idempotency token

**Returns:**
Data source run details including run ID and status.

### `create_subscription_request`

Request access to published data assets.

**Parameters:**
- `domain_identifier` (str, required): Domain identifier
- `request_reason` (str, required): Reason for the request
- `subscribed_listings` (list, required): List of listing identifiers
- `subscribed_principals` (list, required): List of principals
- `metadata_forms` (list, optional): Metadata forms
- `client_token` (str, optional): Idempotency token

**Returns:**
Subscription request details including request ID and status.

### `accept_subscription_request`

Accept a pending subscription request (for asset owners).

**Parameters:**
- `domain_identifier` (str, required): Domain identifier
- `identifier` (str, required): Subscription request identifier
- `asset_scopes` (list, optional): Asset scope limitations
- `decision_comment` (str, optional): Decision comment

**Returns:**
Accepted subscription details including subscription ID.

### `get_subscription`

Retrieve information about an active subscription.

**Parameters:**
- `domain_identifier` (str, required): Domain identifier
- `identifier` (str, required): Subscription identifier

**Returns:**
Subscription details including status, principals, and asset access.

### `get_form_type`

Retrieve metadata form type definitions.

**Parameters:**
- `domain_identifier` (str, required): Domain identifier
- `form_type_identifier` (str, required): Form type identifier
- `revision` (str, optional): Specific revision

**Returns:**
Form type details including field definitions and validation rules.

### `list_form_types`

List available metadata form types in a domain.

**Parameters:**
- `domain_identifier` (str, required): Domain identifier
- `max_results` (int, optional): Max results (1-50, default: 50)
- `next_token` (str, optional): Pagination token
- `status` (str, optional): Filter by status ("ENABLED"/"DISABLED")

**Returns:**
List of form types with definitions and status.

### `create_form_type`

Create a custom metadata form type.

**Parameters:**
- `domain_identifier` (str, required): Domain identifier
- `name` (str, required): Form type name
- `model` (dict, required): Form model definition
- `owning_project_identifier` (str, required): Owning project ID
- `status` (str, required): Status ("ENABLED" or "DISABLED")
- `description` (str, optional): Description

**Returns:**
Created form type details including ID and model definition.

---

## Glossary Management

Manage business glossaries and terminology definitions.

### `create_glossary`

Create a new business glossary in a project.

**Parameters:**
- `domain_identifier` (str, required): Domain identifier
- `name` (str, required): Glossary name (1-256 characters)
- `owning_project_identifier` (str, required): Owning project ID
- `description` (str, optional): Description (0-4096 characters)
- `status` (str, optional): Status ("ENABLED" or "DISABLED", default: "ENABLED")
- `client_token` (str, optional): Idempotency token

**Returns:**
Created glossary details including ID, name, and ownership information.

**Example:**
```python
result = await client.call_tool("create_glossary", {
    "domain_identifier": "dzd_4p9n6sw4qt9xgn",
    "name": "Business Terms",
    "owning_project_identifier": "prj_123456789",
    "description": "Standard business terminology"
})
```

### `get_glossary`

Retrieve detailed information about a glossary.

**Parameters:**
- `domain_identifier` (str, required): Domain identifier
- `identifier` (str, required): Glossary identifier

**Returns:**
Glossary details including name, description, status, creation info, and ownership.

### `create_glossary_term`

Create a new term definition in a glossary.

**Parameters:**
- `domain_identifier` (str, required): Domain identifier
- `glossary_identifier` (str, required): Glossary identifier
- `name` (str, required): Term name (1-256 characters)
- `long_description` (str, optional): Detailed description (0-4096 characters)
- `short_description` (str, optional): Brief description (0-1024 characters)
- `status` (str, optional): Status ("ENABLED" or "DISABLED", default: "ENABLED")
- `term_relations` (dict, optional): Relations to other terms
- `client_token` (str, optional): Idempotency token

**Returns:**
Created glossary term details including ID, name, descriptions, and relationships.

### `get_glossary_term`

Retrieve information about a specific glossary term.

**Parameters:**
- `domain_identifier` (str, required): Domain identifier
- `identifier` (str, required): Glossary term identifier

**Returns:**
Glossary term details including definitions, status, relationships, and usage information.

---

## Environment Management

Manage project environments and external connections.

### `list_environments`

List environments available in a project.

**Parameters:**
- `domain_identifier` (str, required): Domain identifier
- `project_identifier` (str, required): Project identifier
- `max_results` (int, optional): Max results (default: 50)
- `next_token` (str, optional): Pagination token
- `aws_account_id` (str, optional): Filter by AWS account
- `aws_account_region` (str, optional): Filter by AWS region
- `environment_blueprint_identifier` (str, optional): Filter by blueprint
- `environment_profile_identifier` (str, optional): Filter by profile
- `name` (str, optional): Filter by environment name
- `provider` (str, optional): Filter by provider
- `status` (str, optional): Filter by status

**Valid status values:** ACTIVE, CREATING, UPDATING, DELETING, CREATE_FAILED, UPDATE_FAILED, DELETE_FAILED, VALIDATION_FAILED, SUSPENDED, DISABLED, EXPIRED, DELETED, INACCESSIBLE

**Returns:**
List of environments with configuration and status details.

### `create_connection`

Create a connection to external resources or services.

**Parameters:**
- `domain_identifier` (str, required): Domain identifier
- `name` (str, required): Connection name (0-64 characters)
- `environment_identifier` (str, optional): Environment identifier
- `aws_location` (dict, optional): AWS location configuration with:
  - `accessRole` (str): Access role ARN
  - `awsAccountId` (str): AWS account ID
  - `awsRegion` (str): AWS region
  - `iamConnectionId` (str): IAM connection ID
- `description` (str, optional): Description (0-128 characters)
- `client_token` (str, optional): Idempotency token
- `props` (dict, optional): Connection properties

**Returns:**
Created connection details including ID, endpoints, and configuration.

### `get_connection`

Retrieve information about a specific connection.

**Parameters:**
- `domain_identifier` (str, required): Domain identifier
- `identifier` (str, required): Connection identifier
- `with_secret` (bool, optional): Include connection secrets (default: False)

**Returns:**
Connection details including endpoints, properties, and optionally credentials if `with_secret` is True.

### `list_connections`

List connections available in a project.

**Parameters:**
- `domain_identifier` (str, required): Domain identifier
- `project_identifier` (str, required): Project identifier
- `max_results` (int, optional): Max results (1-50, default: 50)
- `next_token` (str, optional): Pagination token
- `environment_identifier` (str, optional): Filter by environment
- `name` (str, optional): Filter by connection name
- `sort_by` (str, optional): Sort field ("NAME")
- `sort_order` (str, optional): Sort order ("ASCENDING" or "DESCENDING")
- `type` (str, optional): Filter by connection type

**Returns:**
List of connections with summary information and pagination details.

---

## Error Handling

All tools may return the following common errors:

### Authentication Errors
- **NoCredentialsError**: AWS credentials not configured
- **AccessDeniedException**: Insufficient permissions for the operation

### Validation Errors
- **ValidationException**: Invalid parameters provided
- **ConflictException**: Resource already exists or conflicts with existing state

### Resource Errors
- **ResourceNotFoundException**: Specified resource doesn't exist
- **ThrottlingException**: API rate limits exceeded

### Example Error Response
```json
{
  "error": "ResourceNotFoundException",
  "message": "Domain dzd_invalid123 not found",
  "details": "Verify the domain identifier and ensure you have access"
}
```

## Usage Patterns

### Chaining Operations
Many workflows require multiple tool calls:

```python
# 1. Create project
project = await client.call_tool("create_project", {...})

# 2. Add project members
await client.call_tool("create_project_membership", {
    "project_identifier": project["id"],
    ...
})

# 3. Create assets in project
await client.call_tool("create_asset", {
    "owning_project_identifier": project["id"],
    ...
})
```

### Pagination
For list operations, handle pagination with `next_token`:

```python
all_projects = []
next_token = None

while True:
    result = await client.call_tool("list_projects", {
        "domain_identifier": domain_id,
        "next_token": next_token
    })

    projects = json.loads(result.content[0].text)
    all_projects.extend(projects["items"])

    next_token = projects.get("nextToken")
    if not next_token:
        break
```

### Error Recovery
Handle errors gracefully with retries:

```python
import time

async def retry_operation(operation, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await operation()
        except Exception as e:
            if "ThrottlingException" in str(e) and attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                time.sleep(wait_time)
                continue
            raise
```

---

**Need help?** Check the [User Guide](./USER_GUIDE.md) for setup instructions and [examples](../examples/) for complete usage scenarios.
