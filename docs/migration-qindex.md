# Migration Guide: Amazon Q Index MCP Server to AWS MCP Server

This guide helps you migrate from `awslabs.amazon-qindex-mcp-server` to the [AWS MCP Server](https://github.com/aws/agent-toolkit-for-aws), part of the Agent Toolkit for AWS.

## Why We're Deprecating

The Amazon Q Index MCP Server registered 4 tools for an independent software vendor (ISV) that a customer has added as a data accessor to their Amazon Q index. Three of them walked through the sign-in flow: `AuthorizeQIndex` built the IAM Identity Center sign-in URL (no AWS call), `CreateTokenWithIAM` made two calls (STS `AssumeRole`, then SSO OIDC `CreateTokenWithIAM`), and `AssumeRoleWithIdentityContext` made one STS `AssumeRole` call. The fourth, `SearchRelevantContent`, made one Amazon Q Business `SearchRelevantContent` call with the temporary credentials the flow produced. The server's README describes it as a demonstration, and every release we tried from PyPI (0.0.1, 0.0.5, 0.0.14, and 0.1.0) exits at startup with `ModuleNotFoundError: No module named 'mypy_boto3_qbusiness'`, because it imports a type-stub package it doesn't declare as a dependency.

The AWS MCP Server makes the search call through its `run_script` tool, which executes sandboxed Python that calls AWS APIs through its built-in `call_boto3` helper, using your own IAM credentials. The token exchange moves to a short script you run yourself, which saves the user's credentials as a named AWS profile for the proxy to sign with. Amazon Q Business is no longer open to new customers, and AWS recommends Amazon Quick for new work; see [Amazon Q Business availability change](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/qbusiness-availability-change.html).

No Agent Skill covers Amazon Q Business or the Q index, so there's no skill to install for it.

## Installing the Replacement

### Configuration

```json
{
  "mcpServers": {
    "aws": {
      "command": "uvx",
      "args": [
        "mcp-proxy-for-aws-cli@latest",
        "https://aws-mcp.us-east-1.api.aws/mcp",
        "--metadata",
        "AWS_REGION=us-east-1"
      ],
      "env": { "AWS_MCP_PROXY_PROFILES": "<your-profile> qindex-user" }
    }
  }
}
```

Set `AWS_REGION` to the Region of the customer's Amazon Q Business application. The first profile in `AWS_MCP_PROXY_PROFILES` signs requests by default. `qindex-user` is the profile the sign-in script below writes; with two or more profiles listed, the proxy adds an `aws_profile` argument to `run_script` so the agent can pick one per call. Run the sign-in script before you start the server, and restart the server each time you run it again.

Your identities need the same permissions the old server needed:

- The identity that runs the sign-in script needs `sts:AssumeRole` on your data accessor role, and the role's trust policy must allow `sts:AssumeRole`, `sts:TagSession`, and `sts:SetContext` for that identity.
- The data accessor role needs `sso-oauth:CreateTokenWithIAM`, `sts:SetContext`, `qbusiness:SearchRelevantContent`, and `kms:Decrypt`, as listed in [Information to be provided to the Amazon Q Business team](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/isv-info-to-provide.html).

For setup details, see [Getting started with the AWS MCP Server](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started-aws-mcp-server.html).

## Tool-by-Tool Migration

The old server handed temporary credentials from tool to tool: `AssumeRoleWithIdentityContext` returned an access key, secret key, and session token to the agent, and the agent passed them back as arguments of `SearchRelevantContent`. `call_boto3` has no credential arguments, and the proxy signs each `run_script` request with one of its profiles, so the user's credentials go into a named profile instead and the agent names that profile.

### Signing in

Your application, or the agent, builds the sign-in URL from the data accessor application ARN the customer gives you and your registered redirect URL. No AWS call is involved:

```text
https://oidc.<idc-region>.amazonaws.com/authorize?response_type=code&redirect_uri=<redirect-url>&state=<random-state>&client_id=<idc-application-arn>
```

URL-encode the redirect URL if it carries its own query string. The user signs in, and your redirect URL receives `code` and `state` parameters. Check that `state` matches, then run this script with the code. It assumes your data accessor role with your tenant ID tag, exchanges the code for tokens, reads `sts:identity_context` from the ID token, assumes the role again with that context, and saves the result as the `qindex-user` profile:

```python
# qindex_sign_in.py: python qindex_sign_in.py <code>
import base64
import configparser
import json
import os
import sys
from pathlib import Path

import boto3

ROLE_ARN = "<data-accessor-role-arn>"
TENANT_ID = "<tenant-id>"
IDC_APPLICATION_ARN = "<idc-application-arn>"
IDC_REGION = "<idc-region>"
REDIRECT_URL = "<redirect-url>"

sts = boto3.client("sts")
tags = [{"Key": "qbusiness-dataaccessor:ExternalId", "Value": TENANT_ID}]
isv = sts.assume_role(RoleArn=ROLE_ARN, RoleSessionName="qindex-token", Tags=tags)["Credentials"]
oidc = boto3.client(
    "sso-oidc",
    region_name=IDC_REGION,
    aws_access_key_id=isv["AccessKeyId"],
    aws_secret_access_key=isv["SecretAccessKey"],
    aws_session_token=isv["SessionToken"],
)
token = oidc.create_token_with_iam(
    clientId=IDC_APPLICATION_ARN,
    redirectUri=REDIRECT_URL,
    grantType="authorization_code",
    code=sys.argv[1],
)
payload = token["idToken"].split(".")[1]
claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
user = sts.assume_role(
    RoleArn=ROLE_ARN,
    RoleSessionName="qindex-user",
    Tags=tags,
    ProvidedContexts=[{
        "ProviderArn": "arn:aws:iam::aws:contextProvider/IdentityCenter",
        "ContextAssertion": claims["sts:identity_context"],
    }],
)["Credentials"]

# configparser rewrites the file, so comments in it aren't kept
path = Path(os.environ.get("AWS_SHARED_CREDENTIALS_FILE", "~/.aws/credentials")).expanduser()
creds = configparser.ConfigParser(interpolation=None)
creds.read(path)
creds["qindex-user"] = {
    "aws_access_key_id": user["AccessKeyId"],
    "aws_secret_access_key": user["SecretAccessKey"],
    "aws_session_token": user["SessionToken"],
}
path.parent.mkdir(parents=True, exist_ok=True)
with path.open("w") as f:
    creds.write(f)
path.chmod(0o600)
print("Saved profile qindex-user, valid until", user["Expiration"])
```

The credentials last one hour unless you pass `DurationSeconds`, which your role's maximum session duration caps. When they expire, sign in again, rerun the script, and restart the server.

### Searching

Ask your agent to search the customer's index and tell it the application ID, retriever ID, and Region, which the customer gives you from their data accessor details page. It runs the call through `run_script` with `aws_profile` set to `qindex-user`. For example:

```python
resp = await call_boto3(
    service_name="qbusiness",
    operation_name="SearchRelevantContent",
    region_name="us-east-1",
    params={
        "applicationId": "<application-id>",
        "queryText": "What is our parental leave policy?",
        "contentSource": {"retriever": {"retrieverId": "<retriever-id>"}},
        "maxResults": 5,
    },
)
result = {
    "results": [
        {"title": r.get("documentTitle"), "uri": r.get("documentUri"), "content": r.get("content")}
        for r in resp.get("relevantContent", [])
    ],
    "nextToken": resp.get("nextToken"),
}
result
```

With `maxResults` set, `call_boto3` returns one page and its `nextToken`; pass the token back as `nextToken` for the next page. Without `maxResults`, it pages through every result, up to 1,000.

| Old tool | What it did | Replacement |
|----------|-------------|-------------|
| `AuthorizeQIndex` | Built `https://oidc.<idc_region>.amazonaws.com/authorize?response_type=code&redirect_uri=...&state=...&client_id=<idc_application_arn>` without URL-encoding the values, and raised an error that asked the user to sign in at that URL and paste back the code. Made no AWS call. 0.0.14 passed that error to the agent. On 0.1.0 the agent gets only `Error executing tool AuthorizeQIndex`, and the URL goes to the server's stderr. | The sign-in URL template above |
| `CreateTokenWithIAM` | Called STS `AssumeRole` on `role_arn` with the session tag `qbusiness-dataaccessor:ExternalId` set to `Test-Tenant`, a placeholder written into the code, then called SSO OIDC `CreateTokenWithIAM` as that session with the code and `grantType` `authorization_code`. Returned the token response, including `idToken` and `refreshToken`. | The sign-in script above. Sent through `run_script`, `CreateTokenWithIAM` fails with `UnrecognizedClientException` ("The security token included in the request is invalid"), because SSO OIDC rejects the credentials the AWS MCP Server forwards. |
| `AssumeRoleWithIdentityContext` | Called STS `AssumeRole` on `role_arn` with `ProvidedContexts` (provider `arn:aws:iam::aws:contextProvider/IdentityCenter`, assertion `identity_context`) and the same `Test-Tenant` tag, and returned the temporary credentials, secret key included. It didn't decode the ID token, so you or the agent had to extract `sts:identity_context` first. | The sign-in script above. `call_boto3(service_name="sts", operation_name="AssumeRole", params={..., "ProvidedContexts": [...]})` also runs through `run_script`, but it returns the secret key into the conversation, and `call_boto3` can't sign later calls with it. |
| `SearchRelevantContent` | Took the temporary credentials as `aws_access_key_id`, `aws_secret_access_key`, and `aws_session_token` arguments. Refused a `query_text` or `application_id` containing any of 18 substrings (among them `exec`, `eval`, `system`, `;`, `\|`, `>`, `[`, and `{`), then called `SearchRelevantContent` with `max_results` defaulting to 3 and returned `relevantContent` and `nextToken`. | `run_script` with `aws_profile` set to `qindex-user` and `call_boto3(service_name="qbusiness", operation_name="SearchRelevantContent", params={"applicationId": ..., "queryText": ..., "contentSource": {"retriever": {"retrieverId": ...}}, "maxResults": ...})`, as in the example. Add `attributeFilter` to narrow by document attributes. |

### Environment variables

| Old variable | Replacement |
|--------------|-------------|
| `AWS_PROFILE` (`CreateTokenWithIAM` and `AssumeRoleWithIdentityContext` used profile `default` when it was unset) | The sign-in script uses the standard AWS credential chain. For the proxy, list your profiles in `AWS_MCP_PROXY_PROFILES`. |
| `AWS_REGION` | The old server didn't read it; each tool took its Region as a parameter (`idc_region`, `qbuiness_region`). Use `--metadata AWS_REGION=<region>` in the proxy configuration, or `region_name` in each `call_boto3` call. |
| `QINDEX_ID` (set by the install links) | The old server didn't read it. Tell the agent the application ID and retriever ID in your prompt or project instructions. |

## What Improves

- **Queries the old server refused.** `SearchRelevantContent` refused any query containing `exec`, `eval`, or `system`, so "executive summary", "Q3 performance evaluation template", and "system requirements" all failed with `Invalid character/pattern detected in query_text` (on 0.1.0 the agent sees only `Error executing tool SearchRelevantContent`), as did any query with brackets or a `>`. `run_script` passes the query to Amazon Q Business unchanged.
- **Your own tenant ID.** The old server tagged every session with `qbusiness-dataaccessor:ExternalId` set to `Test-Tenant`, a placeholder with no setting to change it, where the [Amazon Q Business docs](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/isv.html) call for your tenant ID. The sign-in script uses the tenant ID you set.
- **Credentials stay out of the conversation.** The old flow returned the secret key and session token to the agent and took them back as tool arguments. With a named profile, the agent only passes the profile name.
- **No `default` profile needed.** On a machine that gets credentials from environment variables or an instance role, and has no `[default]` profile, the old `CreateTokenWithIAM` and `AssumeRoleWithIdentityContext` failed with "The config profile (default) could not be found". The sign-in script and the proxy use the standard credential chain.

## Workflow Change

### Before (Amazon Q Index Server)

1. On 0.1.0 and earlier, install `mypy-boto3-qbusiness` next to the server, or it exits at startup. Even then, 0.1.0 uses the `default` profile when `AWS_PROFILE` is unset, so `CreateTokenWithIAM` and `AssumeRoleWithIdentityContext` fail with `ProfileNotFound` on a host that has no `default` profile, and the agent sees every tool error only as `Error executing tool <name>`.
2. Give the agent the application ID, retriever ID, data accessor application ARN, both Regions, your redirect URL, and your role ARN.
3. `AuthorizeQIndex` returns the sign-in URL as an error (on 0.1.0 the URL goes only to the server's stderr). The user signs in and pastes the code into the chat.
4. `CreateTokenWithIAM` returns the tokens, the agent decodes the ID token, and `AssumeRoleWithIdentityContext` returns temporary credentials to the agent.
5. The agent passes the credentials into each `SearchRelevantContent` call.

### After (AWS MCP Server)

1. The user signs in at the sign-in URL, and you run the sign-in script with the code. It saves the `qindex-user` profile.
2. Start or restart the AWS MCP Server with `qindex-user` in `AWS_MCP_PROXY_PROFILES`.
3. Ask your agent to search the index. It runs `SearchRelevantContent` through `run_script` with `aws_profile` set to `qindex-user`.
4. When the credentials expire, sign in again, rerun the script, and restart the server.

## Summary of Gaps

| Feature | Status | Workaround |
|---------|--------|------------|
| Token exchange (`CreateTokenWithIAM`) from inside the agent | Not available | SSO OIDC returns `UnrecognizedClientException` for calls through `run_script`. Run the sign-in script, or the same calls in your application, as shown in [Amazon Q index for ISVs](https://docs.aws.amazon.com/amazonq/latest/qbusiness-ug/isv.html). |
| Temporary credentials passed from one tool to the next | Changed | Save them as a named profile, list it in `AWS_MCP_PROXY_PROFILES`, and pass `aws_profile` to `run_script`. Restart the server after you refresh the profile. |
| The user's identity context applied to a search that arrives through the AWS MCP Server | Untested | The AWS MCP Server forwards your request and credentials to Amazon Q Business, as described in [How AWS MCP Server works with IAM](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/security_iam_service-with-iam.html). We confirmed that `run_script` signs as the `qindex-user` profile and that the call reaches Amazon Q Business, but we had no Q index to check that results are filtered to the user. If the search fails or returns content the user shouldn't see, call `SearchRelevantContent` from your application with the AWS SDK and the same credentials. |
| One page of 3 results by default | Changed | Pass `maxResults` (1 to 100) to get one page and a `nextToken`. Without it, `call_boto3` pages through every result, up to 1,000. |
| Substring checks on `query_text` and `application_id` | Not available | Amazon Q Business checks the request itself, for example returning `ResourceNotFoundException` for an application ID it doesn't know. |
| Errors hidden or rewritten by the server (0.1.0 reports every tool error to the agent as only `Error executing tool <name>` and writes the real message to stderr; 0.0.14 passed messages through, but any `SearchRelevantContent` failure became "Missing AWS credentials" when `aws_session_token` was empty) | Changed | `run_script` returns the error code and message as the service sent them. |

## What Deprecation Means

- The final release keeps working, and unlike 0.1.0 and earlier it starts without `mypy-boto3-qbusiness`. It prints a `FutureWarning` at startup, and its instructions and tool descriptions are marked deprecated.
- The package stays on PyPI and gets no further updates.
- Configurations that use `awslabs.amazon-qindex-mcp-server@latest` get that final release.
- The source folder may later be removed from this repository, as earlier deprecated servers were.

## Removing the Old Server

Once you've verified the replacement meets your needs:

1. Remove `awslabs.amazon-qindex-mcp-server` from your MCP configuration
2. Uninstall the package: `pip uninstall awslabs.amazon-qindex-mcp-server`
