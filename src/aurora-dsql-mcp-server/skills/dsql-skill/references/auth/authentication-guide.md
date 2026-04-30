# DSQL Authentication & Connection Guide

Part of [DSQL Development Guide](../development-guide.md).

---

## Connection and Authentication

### IAM Authentication

**Principle of least privilege:**

- Grant only `dsql:DbConnect` for standard users
- Reserve `dsql:DbConnectAdmin` for administrative operations
- Link database roles to IAM roles for proper access control
- Use IAM policies to restrict cluster access by resource tags

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "dsql:DbConnect",
      "Resource": "arn:aws:dsql:us-east-1:123456789012:cluster/*",
      "Condition": {
        "StringEquals": {
          "aws:ResourceTag/Environment": "production"
        }
      }
    }
  ]
}
```

### Token Management

**Rotation strategies:**

- Generate fresh token per connection (simplest, most secure)
- Implement periodic refresh before 15-minute expiration
- Use connection pool hooks for automated refresh
- Handle token expiration gracefully with retry logic

**Best practices:**

- Keep authentication tokens in memory only; discard after use
- Regenerate token on connection errors
- Monitor token generation failures
- Set connection timeouts appropriately

### Secrets Management

**ALWAYS dynamically assign credentials:**

- Use environment variables for configuration
- Store cluster endpoints in AWS Systems Manager Parameter Store
- Use AWS Secrets Manager for any sensitive configuration
- Rotate credentials regularly even though tokens are short-lived

```bash
# Good - Use Parameter Store
export CLUSTER_ENDPOINT=$(aws ssm get-parameter \
  --name /myapp/dsql/endpoint \
  --query 'Parameter.Value' \
  --output text)

# Bad - Hardcoded in code
const endpoint = "abc123.dsql.us-east-1.on.aws" // ❌ Use Parameter Store instead
```

### Connection Rules

Verify current limits via `awsknowledge`: `aurora dsql connection limits`

- 15-minute token expiry (verify via `awsknowledge`: `aurora dsql authentication token`)
- 60-minute connection maximum
- 10,000 connections per cluster
- SSL required

### SSL/TLS Requirements

Aurora DSQL uses the [PostgreSQL wire protocol](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility.html) and enforces SSL:

```
sslmode: verify-full
sslnegotiation: direct      # PostgreSQL 17+ drivers (better performance)
port: 5432
database: postgres           # single database per cluster
```

**Key details:**

- SSL always enabled server-side
- Use `verify-full` to verify server certificate
- Use `direct` TLS negotiation for PostgreSQL 17+ compatible drivers
- System trust store must include Amazon Root CA

### Connection Pooling (Recommended)

For production applications:

- SHOULD Implement connection pooling
- ALWAYS Configure token refresh before expiration
- MUST Set appropriate pool size (e.g., max: 10, min: 2)
- MUST Configure connection lifetime and idle timeout
- MUST Generate fresh token in `BeforeConnect` or equivalent hook

### Security Best Practices

- ALWAYS dynamically set credentials
- MUST use IAM authentication exclusively
- ALWAYS use SSL/TLS with certificate verification
- SHOULD grant least privilege IAM permissions
- ALWAYS rotate tokens before expiration
- SHOULD use connection pooling to minimize token generation overhead

---

## Audit Logging

**CloudTrail integration:**

- Enable CloudTrail logging for DSQL API calls
- Monitor token generation patterns
- Track cluster configuration changes
- Set up alerts for suspicious activity

**Query logging:**

- Enable query logging if available
- Monitor slow queries and connection patterns
- Track failed authentication attempts
- Review logs regularly for anomalies

---

## Access Control

**ALWAYS prefer scoped database roles over the `admin` role.**

- **ALWAYS** use scoped database roles for application connections — reserve `admin` for initial setup and role management
- **MUST** create purpose-specific database roles and connect with `dsql:DbConnect`
- **MUST** place sensitive data (PII, credentials) in dedicated schemas — not `public`
- **MUST** grant only the minimum privileges each role requires
- **SHOULD** audit role mappings: `SELECT * FROM sys.iam_pg_role_mappings;`

For complete role setup instructions, schema separation patterns, and IAM configuration,
see [access-control.md](../access-control.md).

## Additional Resources

- [IAM Authentication Guide (AWS documentation)](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/using-database-and-iam-roles.html)
