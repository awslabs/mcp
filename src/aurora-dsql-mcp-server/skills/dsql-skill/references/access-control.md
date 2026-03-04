# Access Control & Role-Based Permissions

ALWAYS prefer scoped database roles over the `admin` role. The `admin` role should ONLY be
used for initial cluster setup, creating roles, and granting permissions. Applications and
services MUST connect using scoped-down database roles with `dsql:DbConnect`.

---

## Scoped Roles Over Admin

- **ALWAYS** use scoped database roles for application connections and routine operations
- **MUST** create purpose-specific database roles for each application component
- **MUST** place user-sensitive data (PII, credentials) in a dedicated schema — NOT `public`
- **MUST** grant only the minimum permissions each role requires
- **MUST** create an IAM role with `dsql:DbConnect` for each database role
- **SHOULD** audit role mappings regularly: `SELECT * FROM sys.iam_pg_role_mappings;`

---

## Setting Up Scoped Roles

Connect as `admin` (the only time `admin` should be used):

```sql
-- 1. Create scoped database roles
CREATE ROLE app_readonly WITH LOGIN;
CREATE ROLE app_readwrite WITH LOGIN;
CREATE ROLE user_service WITH LOGIN;

-- 2. Map each to an IAM role (each IAM role needs dsql:DbConnect permission)
AWS IAM GRANT app_readonly TO 'arn:aws:iam::*:role/AppReadOnlyRole';
AWS IAM GRANT app_readwrite TO 'arn:aws:iam::*:role/AppReadWriteRole';
AWS IAM GRANT user_service TO 'arn:aws:iam::*:role/UserServiceRole';

-- 3. Create a dedicated schema for sensitive data
CREATE SCHEMA users_schema;

-- 4. Grant scoped permissions
GRANT USAGE ON SCHEMA public TO app_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_readonly;

GRANT USAGE ON SCHEMA public TO app_readwrite;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_readwrite;

GRANT USAGE ON SCHEMA users_schema TO user_service;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA users_schema TO user_service;
GRANT CREATE ON SCHEMA users_schema TO user_service;
```

---

## IAM Role Requirements

Each scoped database role requires a corresponding IAM role with `dsql:DbConnect`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "dsql:DbConnect",
      "Resource": "arn:aws:dsql:*:*:cluster/*"
    }
  ]
}
```

Reserve `dsql:DbConnectAdmin` strictly for administrative IAM identities:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "dsql:DbConnectAdmin",
      "Resource": "arn:aws:dsql:us-east-1:123456789012:cluster/*"
    }
  ]
}
```

---

## Schema Separation for Sensitive Data

- **MUST** place user PII, credentials, and tokens in a dedicated schema (e.g., `users_schema`)
- **MUST** restrict sensitive schema access to only the roles that need it
- **SHOULD** name schemas descriptively: `users_schema`, `billing_schema`, `audit_schema`
- **SHOULD** use `public` only for non-sensitive, shared application data

```sql
-- Sensitive data: dedicated schema
CREATE TABLE users_schema.profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id VARCHAR(255) NOT NULL,
  email VARCHAR(255) NOT NULL,
  name VARCHAR(255),
  phone VARCHAR(50)
);

-- Non-sensitive data: public schema
CREATE TABLE public.products (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id VARCHAR(255) NOT NULL,
  name VARCHAR(255) NOT NULL,
  category VARCHAR(100)
);
```

---

## Connecting as a Scoped Role

Applications generate tokens with `generate-db-connect-auth-token` (NOT the admin variant):

```bash
# Application connection — uses DbConnect
PGPASSWORD="$(aws dsql generate-db-connect-auth-token \
  --hostname ${CLUSTER_ENDPOINT} \
  --region ${REGION})" \
psql -h ${CLUSTER_ENDPOINT} -U app_readwrite -d postgres
```

Set the search path to the correct schema after connecting:

```sql
SET search_path TO users_schema, public;
```

---

## Role Design Patterns

| Component | Database Role | Permissions | Schema Access |
|-----------|---------------|-------------|---------------|
| Web API (read) | `api_readonly` | SELECT | `public` |
| Web API (write) | `api_readwrite` | SELECT, INSERT, UPDATE, DELETE | `public` |
| User service | `user_service` | SELECT, INSERT, UPDATE | `users_schema`, `public` |
| Reporting | `reporting_readonly` | SELECT | `public`, `users_schema` |
| Admin setup | `admin` | ALL (setup only) | ALL |

---

## Revoking Access

```sql
-- Revoke database permissions
REVOKE ALL ON ALL TABLES IN SCHEMA users_schema FROM app_readonly;
REVOKE USAGE ON SCHEMA users_schema FROM app_readonly;

-- Revoke IAM mapping
AWS IAM REVOKE app_readonly FROM 'arn:aws:iam::*:role/AppReadOnlyRole';
```

---

## References

- [Using Database and IAM Roles](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/using-database-and-iam-roles.html)
- [PostgreSQL GRANT](https://www.postgresql.org/docs/current/sql-grant.html)
- [PostgreSQL Privileges](https://www.postgresql.org/docs/current/ddl-priv.html)
