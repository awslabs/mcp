---
description: Creates secure static website with CloudFront and S3 using Origin Access Control
version: "1.0"
parameters:
  website_name:
    required: true
    description: "Name for your website (used for S3 bucket naming)"
  region:
    required: false
    default: "us-east-1"
    description: "AWS region for S3 bucket"
---

# Secure S3 Website with CloudFront

## Overview

This script creates a secure static website using Amazon S3 and CloudFront with Origin Access Control (OAC). The website will be accessible via HTTPS through CloudFront's default certificate.

## Steps

### 1. Pre-flight Validation and Parameter Check

Verify AWS environment and validate bucket name availability.

**Validate Credentials and Get Account ID:**
- call_aws("aws sts get-caller-identity")
- Extract and save ACCOUNT_ID from response (needed for fallback naming)

**Check Bucket Name Availability:**
- call_aws("aws s3api head-bucket --bucket {website_name}")
- If 404: Bucket available ✓ Proceed
- If 200 or 403: Bucket taken → Ask user for new name
  - Suggest: {website_name}-{random_6char} (e.g., my-site-a8f3k2)
  - Or: {website_name}-{timestamp}

**Validate Region:**
- You MUST confirm region is valid for S3

**Constraints:**
- You MUST NOT proceed with taken bucket names
- You MUST save ACCOUNT_ID for Step 6 (bucket policy)
- You MUST validate all prerequisites before creating resources

### 2. Create S3 Bucket with Security

Create the S3 bucket with production security settings.

**Idempotency Check:**
- call_aws("aws s3api head-bucket --bucket {website_name}")
- If 200: Bucket exists → Ask user "Reuse existing bucket?"
- If 404: Proceed with creation

**S3 Bucket Creation:**
- For us-east-1: call_aws("aws s3api create-bucket --bucket {website_name} --region us-east-1")
- For other regions: call_aws("aws s3api create-bucket --bucket {website_name} --region {region} --create-bucket-configuration LocationConstraint={region}")

**Enable Security:**
- call_aws("aws s3api put-bucket-versioning --bucket {website_name} --versioning-configuration Status=Enabled")
- call_aws("aws s3api put-bucket-encryption --bucket {website_name} --server-side-encryption-configuration Rules=[{ApplyServerSideEncryptionByDefault={SSEAlgorithm=AES256}}]")
- call_aws("aws s3api put-public-access-block --bucket {website_name} --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true")

**Save Variables:**
- BUCKET_NAME = {website_name}
- REGION = {region}

**Constraints:**
- You MUST check if bucket exists before creating
- You MUST use region-specific create-bucket command
- You MUST save BUCKET_NAME and REGION for subsequent steps

### 3. Upload Website Content

Create and upload website content using absolute file paths.

**File Path Setup:**
- Working directory: Platform-specific (check AWS_API_MCP_WORKING_DIR environment variable)
- Default locations:
  - macOS/Linux: /var/folders/.../aws-api-mcp/workdir
  - Windows: C:\Users\...\aws-api-mcp\workdir
- You MUST create HTML files in the MCP working directory before uploading

**Sample index.html:**
```html
<!DOCTYPE html>
<html>
<head><title>Welcome</title></head>
<body>
    <h1>Welcome to My Secure Website</h1>
    <p>Powered by Amazon S3 and CloudFront</p>
</body>
</html>
```

**Upload (use absolute paths without file:// prefix):**
- call_aws("aws s3api put-object --bucket {BUCKET_NAME} --key index.html --body {working_directory}/index.html --content-type text/html")

**Constraints:**
- You MUST use absolute file paths (no file:// prefix for --body parameter)
- You MUST create files in MCP working directory first
- You MUST use BUCKET_NAME variable from Step 2

### 4. Create Origin Access Control

Create OAC for secure communication between CloudFront and S3.

**Create OAC:**
- call_aws("aws cloudfront create-origin-access-control --origin-access-control-config Name={BUCKET_NAME}-oac,OriginAccessControlOriginType=s3,SigningBehavior=always,SigningProtocol=sigv4,Description='OAC for {BUCKET_NAME} static website'")

**Extract OAC ID:**
- From response: OriginAccessControl.Id
- Example: "EW2H62YK6BINP"

**Save Variables:**
- OAC_ID = {extracted_id_from_response}

**Constraints:**
- You MUST extract OAC ID from response and save for Step 5
- You MUST use Description parameter (not Comment)
- You MUST NOT use Origin Access Identity (OAI) - it's deprecated

### 5. Create CloudFront Distribution

Create CloudFront distribution using template.

**Get Template:**
- get_template("cloudfront-distribution-basic", {"bucket_name": "{BUCKET_NAME}", "oac_id": "{OAC_ID}", "region": "{REGION}", "caller_reference": "{timestamp}"})

**Create Distribution:**
- call_aws("aws cloudfront create-distribution --distribution-config '{template_json}'")

**Extract Distribution Details:**
- From response: Distribution.Id → DISTRIBUTION_ID
- From response: Distribution.DomainName → CF_DOMAIN
- Example ID: "E345E04Y7JDNTC"
- Example Domain: "dhtrrtva9003v.cloudfront.net"

**Save Variables:**
- DISTRIBUTION_ID = {extracted_id}
- CF_DOMAIN = {extracted_domain_name}

**Constraints:**
- You MUST use variables from previous steps (BUCKET_NAME, OAC_ID, REGION)
- You MUST extract both DISTRIBUTION_ID and CF_DOMAIN from response
- You MUST save for use in Steps 6, 7, and 8

### 6. Apply S3 Bucket Policy

Configure bucket policy to allow CloudFront access.

**Apply Policy:**
- get_template("s3-bucket-policy-oac", {"bucket_name": "{BUCKET_NAME}", "account_id": "{ACCOUNT_ID}", "distribution_id": "{DISTRIBUTION_ID}"})
- call_aws("aws s3api put-bucket-policy --bucket {BUCKET_NAME} --policy '{policy_json}'")

**Constraints:**
- You MUST use ACCOUNT_ID from Step 1
- You MUST use BUCKET_NAME from Step 2
- You MUST use DISTRIBUTION_ID from Step 5

### 7. Wait for Distribution Deployment

Monitor CloudFront deployment status.

**Check Deployment Status:**
- Command: call_aws("aws cloudfront get-distribution --id {DISTRIBUTION_ID} --query 'Distribution.Status'")
- Expected time: 5-15 minutes for "Deployed" status
- Status progression: InProgress → Deployed

**Polling Guidance:**
- You MAY poll every 60 seconds if implementing automated waiting
- You SHOULD inform user of expected 5-15 minute wait time
- You MAY proceed to next steps while deployment continues in background
- Final testing (Step 8) requires "Deployed" status

**Constraints:**
- You MUST inform user distribution is deploying
- You SHOULD provide the distribution URL immediately for later testing
- Distribution is NOT functional until Status = "Deployed"

### 8. Test Website Functionality

Validate that the website is accessible and secure.

**Constraints:**
- You MUST provide the CloudFront URL for testing
- You SHOULD verify HTTP redirects to HTTPS
- You SHOULD test that direct S3 access is blocked (403 expected)

## Examples

### Example Input
```
website_name: "my-portfolio-2024"
region: "us-east-1"
```

### Example Output
```
✓ S3 bucket created: my-portfolio-2024
✓ Content uploaded: index.html
✓ Origin Access Control created: OAC-my-portfolio-2024
✓ CloudFront distribution created: E1ABCDEF123456
✓ S3 bucket policy applied

Your secure website is ready!
CloudFront URL: https://d1abcdefghijkl.cloudfront.net
Distribution ID: E1ABCDEF123456

The website is accessible via HTTPS and direct S3 access is blocked for security.
```

## Troubleshooting

### S3 Bucket Creation Fails
If bucket creation fails with BucketAlreadyExists error:
- Check that the bucket name is globally unique
- Try a different bucket name with timestamp suffix

### CloudFront Distribution Not Accessible
If the distribution is not accessible:
- Verify distribution status is "Deployed" (can take 5-15 minutes)
- Check that index.html exists in S3 bucket
- Ensure OAC and bucket policy are properly configured

### 403 Errors After Setup
If you get 403 errors when accessing CloudFront:
- Verify OAC ID is correct in distribution config
- Check S3 bucket policy allows CloudFront service principal
- Ensure public access block is enabled on S3 bucket

## Error Recovery

### If Script Fails Mid-Execution

**Identify what was created:**
1. Check S3 bucket: call_aws("aws s3api head-bucket --bucket {BUCKET_NAME}")
2. Check OAC: call_aws("aws cloudfront list-origin-access-controls")
3. Check Distribution: call_aws("aws cloudfront list-distributions")

**Recovery Options:**

**Option A: Resume from where it failed**
- Identify last successful step
- Continue from next step using saved variables

**Option B: Start fresh (manual cleanup via AWS Console)**
- Use AWS Console to delete created resources manually
- Rerun script with same or different parameters

**Option C: Reuse existing resources**
- Keep S3 bucket if it exists and is correct
- Skip to step that failed, use existing resource IDs
