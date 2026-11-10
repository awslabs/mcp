# Migration Guide: Finch MCP Server to the Finch CLI and AWS MCP Server

This guide helps you migrate from `awslabs.finch-mcp-server` to two replacements: the [Finch CLI](https://github.com/runfinch/finch), which your agent runs from its own shell, and the [AWS MCP Server](https://github.com/aws/agent-toolkit-for-aws), part of the Agent Toolkit for AWS, for the Amazon ECR calls.

## Why We're Deprecating

The Finch MCP Server registered 3 tools. Two of them ran Finch CLI commands on your machine: `finch_build_container_image` ran `finch image build`, and `finch_push_image` ran `finch image inspect`, `finch image tag`, and `finch image push`. On macOS and Windows, both tools also started the Finch VM when it wasn't running, and for ECR images they added the `ecr-login` credential helper to `~/.finch/finch.yaml`. The third tool, `finch_create_ecr_repo`, called the ECR `DescribeRepositories` API and, when the repository didn't exist, `CreateRepository`.

Coding agents can already run shell commands, so your agent can run the same `finch` commands itself and read their full output. The AWS MCP Server makes the ECR calls through its `run_script` tool, which executes sandboxed Python that calls AWS APIs through its built-in `call_boto3` helper, using your own IAM credentials. It also reaches the rest of the ECR API, which this server didn't have.

The [`aws-containers`](https://github.com/aws/agent-toolkit-for-aws/tree/main/skills/core-skills/aws-containers) Agent Skill covers ECR repository setup, registry login, and pushing images. Its login and push steps use `docker`; Finch takes the same commands with `finch` in place of `docker`. No Agent Skill covers Finch itself.

## Installing the Replacement

### Finch CLI

Keep Finch installed, since the old server needed it too, and let your agent run `finch` commands in its shell. On Linux, Finch's daemons run as root, so Finch's own guides use `sudo finch ...`. To run `finch` without typing `sudo`, see [Running finch without sudo](https://runfinch.com/docs/managing-finch/linux/optional-components/#running-finch-without-sudo).

### AWS MCP Server (for Amazon ECR)

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
      ]
    }
  }
}
```

Set `AWS_REGION` to the Region of your ECR repositories. To use a named AWS profile, add an `env` block to the server entry:

```json
"env": { "AWS_MCP_PROXY_PROFILES": "<profile_name>" }
```

### Installing the Agent Skills

```bash
npx skills add aws/agent-toolkit-for-aws/skills
```

This installs the [`aws-containers`](https://github.com/aws/agent-toolkit-for-aws/tree/main/skills/core-skills/aws-containers) skill along with the other core skills.

### Permissions

Your identity needs the same permissions the old server needed:

- `ecr:DescribeRepositories` and `ecr:CreateRepository`, for the repository check in place of `finch_create_ecr_repo`
- `ecr:GetAuthorizationToken` (on `Resource: "*"`), `ecr:BatchCheckLayerAvailability`, `ecr:InitiateLayerUpload`, `ecr:UploadLayerPart`, `ecr:CompleteLayerUpload`, `ecr:PutImage`, and `ecr:BatchGetImage`, to push an image (see [IAM permissions for pushing an image](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-push-iam.html))
- `ecr:GetAuthorizationToken`, `ecr:BatchGetImage`, and `ecr:GetDownloadUrlForLayer`, to build from a base image in a private ECR repository

To use ECR operations the old server didn't have, add the matching actions, such as `ecr:DescribeImages` or `ecr:DeleteRepository`.

For setup details, see [Getting started with the AWS MCP Server](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/getting-started-aws-mcp-server.html).

### Signing in to Amazon ECR

The old server never called `GetAuthorizationToken` itself. When the image to push, or an image named in the Dockerfile, was in ECR, it added `ecr-login` to `creds_helpers` in `~/.finch/finch.yaml`, force-stopped the Finch VM, and started it again, so the Amazon ECR credential helper fetched tokens with your AWS credentials. On Linux it changed nothing and left sign-in to the `config.json` in `DOCKER_CONFIG`. On macOS, if `~/.finch/finch.yaml` didn't exist yet, the tool failed with `finch yaml file not found in finch.yaml`.

Replace it with either of the two methods in Finch's [Registry Authentication](https://runfinch.com/docs/container-images/authentication/) guide:

- **Credential helper, set up once.** On macOS and Windows, add `ecr-login` under `creds_helpers` in `finch.yaml`, add `"credsStore": "ecr-login"` to `~/.finch/config.json` if it isn't there, then run `finch vm stop` and `finch vm start`. On Linux, install the Amazon ECR credential helper and set `"credsStore": "ecr-login"` in `/root/.docker/config.json`.
- **A login for each session.** The agent runs this in its shell, and the login lasts 12 hours:

```bash
aws ecr get-login-password --region us-east-1 | finch login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
```

On Linux, run `finch login` the same way you run your other `finch` commands (Finch's guide uses `sudo -E finch login`), so the push reads the same credentials. Run the login in the shell rather than calling `GetAuthorizationToken` through `run_script`: the pipe hands the token straight to `finch login`, while `run_script` would return it into the conversation.

## Tool-by-Tool Migration

The two Finch tools become `finch` commands your agent runs in its shell. The command lines below come from the server's source, and we confirmed them by running both tools against a stand-in `finch` that recorded its arguments. The ECR tool becomes a `run_script` call.

### Building and pushing images (Finch CLI)

| Old tool | What it did | Replacement |
|----------|-------------|-------------|
| `finch_build_container_image` | Checked that `finch` was on `PATH` and that `dockerfile_path` and `context_path` existed. On macOS and Windows, made sure the Finch VM was running (see the next table). If the Dockerfile named an ECR image, set up ECR sign-in as described above. Then ran `finch image build -f <dockerfile_path> [-t <tag>]... [--platform <platform>]... [--target <stage>] [--no-cache] [--pull] [--build-context <context>]... [--output <destination>] [--cache-from <source>]... [--quiet] --progress <progress> <context_path>`, where `progress` defaulted to `auto`. Returned `Successfully built image from <dockerfile_path>` or the command's stderr. | Run the same command in the shell, for example `finch image build -f /path/to/Dockerfile -t my-app:latest --platform linux/amd64 /path/to/context`. Every other `finch image build` flag works too, such as `--build-arg`, `--secret`, `--label`, and `--cache-to`. |
| `finch_push_image` | Ran `finch image inspect <image>`, took the 12 hex digits after `sha256:` in the `Id` field, ran `finch image tag <image> <repository>:<id>`, and then `finch image push <repository>:<id>`. The tag you passed was never pushed. For an ECR image, it refused to run unless the server was in write mode, then set up ECR sign-in and, on macOS and Windows, made sure the VM was running. | `finch image push <image>` pushes the tag you name. To push under the image ID as the old tool did, run `finch image inspect <image>`, copy the 12 hex digits after `sha256:` in the `Id` field, then run `finch image tag <image> <repository>:<id>` and `finch image push <repository>:<id>`. |

### Finch VM (macOS and Windows)

Before each build or push, the old tools ran these commands for you. The agent runs them itself when a `finch` command reports that the VM isn't running.

| Situation | What the old tools ran | What the agent runs |
|-----------|------------------------|---------------------|
| Every build and push | `finch vm status` | `finch vm status` |
| The VM doesn't exist | `finch vm init` | `finch vm init` |
| The VM is stopped | `finch vm start` | `finch vm start` |
| The server had just added `ecr-login` to `finch.yaml` | `finch vm stop --force`, then `finch vm start` | `finch vm stop`, then `finch vm start`, once, after you set up the credential helper |

Finch doesn't use a VM on Linux and has no `finch vm` commands there (`unknown command "vm" for "finch"`), so the old server skipped these steps on Linux.

### ECR repositories (AWS MCP Server)

| Old tool | What it did | Replacement |
|----------|-------------|-------------|
| `finch_create_ecr_repo` | Called `DescribeRepositories` for `repository_name` in `region`, or in the default Region. If the repository existed, returned `ECR repository '<name>' already exists.` without its URI. If not, called `CreateRepository` with `imageTagMutability` set to `IMMUTABLE` and returned the URI in the message. Scan on push stayed off, and encryption was the `AES256` default. | `run_script` combining `call_boto3(service_name="ecr", operation_name="DescribeRepositories", params={"repositoryNames": [...]})` and `CreateRepository`, as in the example below |

With the AWS MCP Server, ask your agent to perform the same operation and it makes the equivalent calls through `run_script`. Inside `run_script`, AWS APIs are called with the built-in `call_boto3` helper, which takes the service name, the API operation name (in PascalCase, as in the API reference), and a dict of request parameters, and returns the response. For example, the agent might run this in place of `finch_create_ecr_repo`:

```python
name = "my-app"
try:
    resp = await call_boto3(
        service_name="ecr",
        operation_name="DescribeRepositories",
        region_name="us-east-1",
        params={"repositoryNames": [name]},
    )
    repo = resp["repositories"][0]
    created = False
except Exception as e:
    if e.response["Error"]["Code"] != "RepositoryNotFoundException":
        raise
    resp = await call_boto3(
        service_name="ecr",
        operation_name="CreateRepository",
        region_name="us-east-1",
        params={"repositoryName": name, "imageTagMutability": "IMMUTABLE"},
    )
    repo = resp["repository"]
    created = True
result = {"created": created, "repositoryUri": repo["repositoryUri"]}
result
```

When the repository doesn't exist yet, `run_script` lists the `RepositoryNotFoundException` from `DescribeRepositories` in its `stderr` and `api_calls`, and the script goes on to `CreateRepository`. In testing, a repository created this way and one created by `finch_create_ecr_repo` had the same settings: `IMMUTABLE` tags, `scanOnPush` off, and `AES256` encryption.

Because `run_script` exposes the full ECR API, operations the old server never had, such as `DescribeImages` to confirm a push, `PutLifecyclePolicy`, `PutRegistryScanningConfiguration`, and `DeleteRepository`, are also available.

### Command-line flags and environment variables

| Old setting | Replacement |
|-------------|-------------|
| `--enable-aws-resource-write` | IAM decides whether a push or `CreateRepository` succeeds. See the first row of the Summary of Gaps. |
| `--disable-file-logging`, `FINCH_DISABLE_FILE_LOGGING`, `FINCH_MCP_LOG_FILE`, and `FASTMCP_LOG_LEVEL` | Not needed. Your agent host shows each shell command and its output. |
| `AWS_REGION` | `--metadata AWS_REGION=<region>` in the proxy configuration, or `region_name` in each `call_boto3` call. Pass `--region` to `aws ecr get-login-password`. |
| `AWS_PROFILE` | `AWS_MCP_PROXY_PROFILES` in the proxy's `env` block. In the shell, `AWS_PROFILE` still selects the profile for `aws ecr get-login-password` and the ECR credential helper. |

## What Improves

- **ECR writes that work from the documented configuration.** The README's configurations start the server with `uvx awslabs.finch-mcp-server@latest`, which runs the package's console script. That script calls `main()` without reading the command line, so the server ignored `--enable-aws-resource-write` and always started in read-only mode. With version 0.2.1 from PyPI and the flag set, `finch_create_ecr_repo` returned "Server running in read-only mode, unable to perform the action", and in read-only mode `finch_push_image` refuses every ECR image. Only `python -m awslabs.finch_mcp_server.server --enable-aws-resource-write` turned writes on. The console script also ignored `--disable-file-logging` and the logging environment variables. With the replacement, your IAM permissions decide what's allowed.
- **The tag you asked for gets pushed.** `finch_push_image` always replaced the tag with the first 12 hex digits of the image ID, so asking for `my-app:v1.2` pushed `my-app:<image-id>` and never `v1.2`. `finch image push` pushes the tag you name.
- **Every Finch command and flag.** The build tool took 12 options. `finch image build` also takes `--build-arg`, `--secret`, `--ssh`, `--label`, `--cache-to`, `--network`, `--sbom`, and `--provenance`, and `finch image push` takes `--platform`, `--all-platforms`, and `--sign`. The agent can also run the image it built with `finch run`, list images with `finch images`, or read logs with `finch logs`, which the server had no tools for.
- **Full command output.** On success, the build tool returned only `Successfully built image from <path>` and dropped stdout, so the agent never saw the build log or, with `quiet`, the image ID. The shell returns everything Finch prints.
- **`finch.yaml` stays as you wrote it.** On macOS and Windows, the first ECR push or ECR-based build rewrote `~/.finch/finch.yaml` with PyYAML, which dropped its comments and sorted its keys, and then force-stopped the Finch VM, which stops any containers running in it. With the replacement, you change `finch.yaml` once yourself, or use `finch login` and leave the file alone.
- **The repository URI on every call, and the rest of the ECR API.** When the repository already existed, `finch_create_ecr_repo` returned only `ECR repository '<name>' already exists.`, because its response model kept just `status` and `message`. `DescribeRepositories` returns the URI along with the tag mutability, scanning, and encryption settings, and `run_script` reaches the rest of ECR.

## Workflow Change

### Before (Finch MCP Server)

1. Install Finch, and start the server with `--enable-aws-resource-write` to push to ECR or create repositories. The flag only took effect when the server was started with `python -m`.
2. Ask for a build or push. On macOS and Windows, the server starts the Finch VM if needed and, for ECR, adds `ecr-login` to `finch.yaml` and restarts the VM.
3. On Linux, the server runs `finch` as your user, so builds and pushes fail with `rootless containerd not running?` unless you've set Finch up to run without `sudo`.
4. The image goes out under its image ID tag, and the build log isn't returned.

### After (Finch CLI and AWS MCP Server)

1. Ask your agent for a build or push. It runs `finch` in its shell, and your agent host asks you to approve the command unless you've allowed it.
2. On macOS and Windows, the agent checks `finch vm status` and starts the VM if needed. On Linux, it runs `sudo finch ...`, or plain `finch` after the no-`sudo` setup.
3. For ECR, sign in once with the credential helper, or have the agent run `aws ecr get-login-password` and `finch login --password-stdin` at the start of the session.
4. The agent checks or creates the repository through `run_script` and pushes the tag you name.

## Summary of Gaps

| Feature | Status | Workaround |
|---------|--------|------------|
| Read-only mode for ECR (without `--enable-aws-resource-write`, `finch_push_image` refused ECR images and `finch_create_ecr_repo` refused to run) | Not available | Deny `ecr:CreateRepository`, `ecr:PutImage`, and the layer upload actions to the identity your agent uses, with an identity-based policy, a permissions boundary, or a service control policy (SCP) |
| Only `finch` commands could run, and none with an argument exactly equal to one of 45 strings, such as `;`, `&&`, `sudo`, `sh`, `curl`, or `--` | Not available | Use your agent host's command permissions: allow the `finch` commands you want to run without a prompt, and leave other commands to ask for approval |
| VM started or initialized before each build and push (macOS and Windows) | Changed | The agent runs `finch vm status`, then `finch vm start` or `finch vm init` |
| `ecr-login` added to `finch.yaml`, followed by a VM restart, before an ECR push or ECR-based build | Changed | Set up the credential helper once, or sign in with `finch login --password-stdin`, as in [Signing in to Amazon ECR](#signing-in-to-amazon-ecr) |
| Push under the image ID tag | Changed | Ask for it. The agent runs `finch image inspect`, `finch image tag`, and `finch image push`, as in the first table. |
| `IMMUTABLE` tags on every repository `finch_create_ecr_repo` created | Changed | Pass `"imageTagMutability": "IMMUTABLE"` to `CreateRepository`, as in the example. The `aws-containers` skill recommends it too. |
| Redaction of access keys, secrets, tokens, and URL credentials in the server's own log | Not available | The agent host shows commands and output as they ran. `finch login --password-stdin` keeps the registry password off the command line and out of the output. |

## Removing the Old Server

Once you've verified the replacement meets your needs:

1. Remove `awslabs.finch-mcp-server` from your MCP configuration
2. Uninstall the package: `pip uninstall awslabs.finch-mcp-server`
3. The old package will remain on PyPI but won't receive updates
