# IAM Policy Examples - AWS HealthImaging MCP Server

## Overview

This document provides tiered IAM policy examples following the principle of least privilege. Each policy is scoped to specific use cases and includes resource-level permissions where possible.

## Policy Tiers

### 1. Read-Only Policy (Clinicians/Viewers)

**Use Case:** Clinical staff who need to view medical imaging data but not modify it.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "HealthImagingReadOnly",
      "Effect": "Allow",
      "Action": [
        "medical-imaging:GetDatastore",
        "medical-imaging:ListDatastores",
        "medical-imaging:GetImageSet",
        "medical-imaging:GetImageSetMetadata",
        "medical-imaging:GetImageFrame",
        "medical-imaging:SearchImageSets",
        "medical-imaging:ListImageSetVersions"
      ],
      "Resource": [
        "arn:aws:medical-imaging:*:*:datastore/${DatastoreId}",
        "arn:aws:medical-imaging:*:*:datastore/${DatastoreId}/imageset/*"
      ],
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": ["us-east-1", "us-west-2"]
        },
        "IpAddress": {
          "aws:SourceIp": ["10.0.0.0/8", "172.16.0.0/12"]
        }
      }
    },
    {
      "Sid": "DenyDeleteOperations",
      "Effect": "Deny",
      "Action": [
        "medical-imaging:DeleteImageSet",
        "medical-imaging:DeleteDatastore"
      ],
      "Resource": "*"
    }
  ]
}
```

**Key Features:**
- Read-only access to specific datastores
- Geographic restrictions (us-east-1, us-west-2)
- IP address restrictions (internal networks only)
- Explicit deny for delete operations

### 2. Data Manager Policy (Metadata Updates)

**Use Case:** Data managers who can update metadata but not delete data.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "HealthImagingDataManager",
      "Effect": "Allow",
      "Action": [
        "medical-imaging:GetDatastore",
        "medical-imaging:ListDatastores",
        "medical-imaging:GetImageSet",
        "medical-imaging:GetImageSetMetadata",
        "medical-imaging:GetImageFrame",
        "medical-imaging:SearchImageSets",
        "medical-imaging:ListImageSetVersions",
        "medical-imaging:UpdateImageSetMetadata"
      ],
      "Resource": [
        "arn:aws:medical-imaging:*:*:datastore/${DatastoreId}",
        "arn:aws:medical-imaging:*:*:datastore/${DatastoreId}/imageset/*"
      ],
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": ["us-east-1", "us-west-2"]
        },
        "Bool": {
          "aws:MultiFactorAuthPresent": "true"
        }
      }
    },
    {
      "Sid": "RequireKMSEncryption",
      "Effect": "Allow",
      "Action": [
        "kms:Decrypt",
        "kms:DescribeKey"
      ],
      "Resource": "arn:aws:kms:*:*:key/${KMSKeyId}",
      "Condition": {
        "StringEquals": {
          "kms:ViaService": "medical-imaging.*.amazonaws.com"
        }
      }
    },
    {
      "Sid": "DenyDeleteOperations",
      "Effect": "Deny",
      "Action": [
        "medical-imaging:DeleteImageSet",
        "medical-imaging:DeleteDatastore"
      ],
      "Resource": "*"
    }
  ]
}
```

**Key Features:**
- Metadata update permissions
- MFA required for all operations
- KMS key access for encrypted data
- No delete permissions

### 3. Administrator Policy (Full Access with Conditions)

**Use Case:** System administrators with full access but with additional safeguards.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "HealthImagingFullAccess",
      "Effect": "Allow",
      "Action": [
        "medical-imaging:*"
      ],
      "Resource": [
        "arn:aws:medical-imaging:*:*:datastore/${DatastoreId}",
        "arn:aws:medical-imaging:*:*:datastore/${DatastoreId}/imageset/*"
      ],
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": ["us-east-1", "us-west-2"]
        },
        "Bool": {
          "aws:MultiFactorAuthPresent": "true"
        },
        "DateGreaterThan": {
          "aws:CurrentTime": "2024-01-01T00:00:00Z"
        },
        "DateLessThan": {
          "aws:CurrentTime": "2025-12-31T23:59:59Z"
        }
      }
    },
    {
      "Sid": "RequireKMSFullAccess",
      "Effect": "Allow",
      "Action": [
        "kms:Decrypt",
        "kms:Encrypt",
        "kms:DescribeKey",
        "kms:GenerateDataKey"
      ],
      "Resource": "arn:aws:kms:*:*:key/${KMSKeyId}",
      "Condition": {
        "StringEquals": {
          "kms:ViaService": "medical-imaging.*.amazonaws.com"
        }
      }
    },
    {
      "Sid": "RequireApprovalForDelete",
      "Effect": "Allow",
      "Action": [
        "medical-imaging:DeleteImageSet",
        "medical-imaging:DeleteDatastore"
      ],
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "aws:PrincipalTag/ApprovalTicket": "TICKET-*"
        }
      }
    },
    {
      "Sid": "CloudTrailLogging",
      "Effect": "Allow",
      "Action": [
        "cloudtrail:LookupEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

**Key Features:**
- Full access to HealthImaging operations
- MFA required
- Time-bound access (expires annually)
- Delete operations require approval ticket tag
- CloudTrail access for audit review

## Permission Boundaries

### Boundary for Delegated Access

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "HealthImagingBoundary",
      "Effect": "Allow",
      "Action": [
        "medical-imaging:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "DenyDangerousActions",
      "Effect": "Deny",
      "Action": [
        "medical-imaging:DeleteDatastore",
        "iam:*",
        "organizations:*",
        "account:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "RequireEncryption",
      "Effect": "Deny",
      "Action": "medical-imaging:*",
      "Resource": "*",
      "Condition": {
        "Bool": {
          "medical-imaging:EncryptionEnabled": "false"
        }
      }
    }
  ]
}
```

## Service Control Policies (SCPs)

### Prevent Privilege Escalation

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PreventPrivilegeEscalation",
      "Effect": "Deny",
      "Action": [
        "iam:CreatePolicyVersion",
        "iam:DeletePolicy",
        "iam:DeletePolicyVersion",
        "iam:SetDefaultPolicyVersion",
        "iam:PassRole"
      ],
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "aws:PrincipalTag/SecurityTeam": "true"
        }
      }
    },
    {
      "Sid": "RequireMFAForSensitiveOps",
      "Effect": "Deny",
      "Action": [
        "medical-imaging:DeleteImageSet",
        "medical-imaging:DeleteDatastore",
        "medical-imaging:UpdateImageSetMetadata"
      ],
      "Resource": "*",
      "Condition": {
        "BoolIfExists": {
          "aws:MultiFactorAuthPresent": "false"
        }
      }
    }
  ]
}
```

## IAM Access Analyzer Configuration

### Analyzer for HealthImaging Resources

```json
{
  "analyzerName": "healthimaging-access-analyzer",
  "type": "ACCOUNT",
  "archiveRules": [
    {
      "ruleName": "ArchiveInternalAccess",
      "filter": {
        "principal": {
          "contains": ["arn:aws:iam::${AccountId}:"]
        }
      }
    }
  ]
}
```

## Access Review Procedures

### Quarterly Review Checklist

1. **User Access Review**
   - Review all IAM users with HealthImaging permissions
   - Verify MFA is enabled for all users
   - Check for unused credentials (>90 days)
   - Validate business justification for access

2. **Permission Analysis**
   - Run IAM Access Analyzer
   - Review CloudTrail logs for unused permissions
   - Identify overly permissive policies
   - Implement least privilege recommendations

3. **Compliance Validation**
   - Verify MFA enforcement
   - Check permission boundary compliance
   - Validate SCP effectiveness
   - Review audit log completeness

4. **Documentation Updates**
   - Update policy documentation
   - Record access review findings
   - Document policy changes
   - Update training materials

## Best Practices

### 1. Use Resource-Level Permissions
```json
"Resource": "arn:aws:medical-imaging:*:*:datastore/${DatastoreId}/imageset/*"
```
Instead of:
```json
"Resource": "*"
```

### 2. Add Condition Keys
```json
"Condition": {
  "Bool": {"aws:MultiFactorAuthPresent": "true"},
  "IpAddress": {"aws:SourceIp": ["10.0.0.0/8"]},
  "StringEquals": {"aws:RequestedRegion": ["us-east-1"]}
}
```

### 3. Implement Permission Boundaries
- Attach to all delegated IAM roles
- Prevent privilege escalation
- Enforce organizational policies

### 4. Regular Access Reviews
- Quarterly user access reviews
- Monthly permission analysis
- Weekly CloudTrail log reviews
- Daily security event monitoring

## Troubleshooting

### Common Issues

**Issue:** "Access Denied" errors
**Solution:** Check IAM policy, permission boundaries, and SCPs

**Issue:** MFA not enforced
**Solution:** Add `aws:MultiFactorAuthPresent` condition

**Issue:** Cross-region access blocked
**Solution:** Update `aws:RequestedRegion` condition

## References

- [AWS HealthImaging IAM Documentation](https://docs.aws.amazon.com/healthimaging/latest/devguide/security-iam.html)
- [IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [HIPAA Compliance on AWS](https://aws.amazon.com/compliance/hipaa-compliance/)