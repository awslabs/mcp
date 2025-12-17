# Security Policy

## Supported Versions

We release patches for security vulnerabilities. Currently supported versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability within this project, please send an email to the AWS Security team. All security vulnerabilities will be promptly addressed.

Please do not open public issues for security vulnerabilities.

### What to Include

When reporting a vulnerability, please include:

- Type of vulnerability
- Full paths of source file(s) related to the vulnerability
- Location of the affected source code (tag/branch/commit or direct URL)
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the vulnerability, including how an attacker might exploit it

### Response Timeline

- We will acknowledge receipt of your vulnerability report within 3 business days
- We will provide a detailed response within 7 business days
- We will work on a fix and keep you informed of progress
- Once the vulnerability is fixed, we will publicly disclose it (with your permission)

## Security Best Practices

When using this MCP server:

1. **AWS Credentials**: Never commit AWS credentials to version control
2. **IAM Permissions**: Use least-privilege IAM policies
3. **Network Security**: Use VPC endpoints when possible
4. **Logging**: Enable CloudTrail for audit trails
5. **Updates**: Keep dependencies up to date
6. **Environment Variables**: Use secure methods to manage environment variables
7. **Data Access**: Ensure proper authorization before accessing medical imaging data
8. **HIPAA Compliance**: Follow HIPAA guidelines when handling PHI

## Known Security Considerations

- This server requires AWS credentials with HealthImaging permissions
- Medical imaging data may contain PHI and must be handled according to HIPAA
- Always use encrypted connections (HTTPS) when accessing AWS services
- Regularly rotate AWS access keys
- Monitor CloudTrail logs for unusual activity

## Dependencies

We regularly update dependencies to address security vulnerabilities. Run:

```bash
pip install --upgrade awslabs.healthimaging-mcp-server
```

To check for known vulnerabilities in dependencies:

```bash
pip install safety
safety check
```

## Compliance

This project is designed to work with AWS HealthImaging, which is HIPAA eligible. However, proper configuration and usage are the responsibility of the user to maintain compliance.

For more information on AWS HIPAA compliance:
https://aws.amazon.com/compliance/hipaa-compliance/
