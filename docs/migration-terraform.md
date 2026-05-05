# Migration Guide: AWS Labs Terraform MCP Server to HashiCorp Official

This guide helps you migrate from `awslabs.terraform-mcp-server` to [HashiCorp's official Terraform MCP Server](https://github.com/hashicorp/terraform-mcp-server).

## Why We're Deprecating

HashiCorp has released an official, production-grade Terraform MCP server that provides comprehensive access to the Terraform Registry and HCP Terraform/Terraform Enterprise. Rather than maintain a parallel implementation, we recommend adopting the official server.

## Installing the Official Server

### Claude Code

```bash
claude mcp add terraform --scope user --transport stdio -- docker run -i --rm hashicorp/terraform-mcp-server:0.4.0
```

### VS Code / Cursor

Add to your MCP server settings:

```json
{
  "mcpServers": {
    "terraform": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "TFE_TOKEN",
        "-e", "TFE_ADDRESS",
        "hashicorp/terraform-mcp-server:0.4.0"
      ],
      "env": {
        "TFE_TOKEN": "<your-token>",
        "TFE_ADDRESS": "https://app.terraform.io"
      }
    }
  }
}
```

The `env` block sets host-side environment variables, and the `-e` flags in `args` forward them into the Docker container.

### From Source (Go)

```bash
go install github.com/hashicorp/terraform-mcp-server/cmd/terraform-mcp-server@latest
```

## Tool-by-Tool Migration

### ExecuteTerraformCommand

**Our tool:** Executed `terraform init/plan/validate/apply/destroy` locally via subprocess.

**Official server:** Uses HCP Terraform API for remote run management (`create_run`, `action_run`, `list_runs`). This is a different execution model -- remote runs via HCP Terraform rather than local CLI execution.

**If you need local CLI execution:** Run Terraform commands directly in your terminal or have your AI assistant execute them via shell. The official server does not wrap local CLI execution.

### ExecuteTerragruntCommand -- No direct replacement

**Our tool:** Executed Terragrunt commands including `run-all` with `--queue-include-dir`/`--queue-exclude-dir` support.

**Official server:** No Terragrunt support.

**Alternative:** Run Terragrunt commands directly via shell. Consider creating a custom MCP server or skill if you need Terragrunt integration with AI assistants.

### SearchAwsProviderDocs

**Our tool:** Fetched full rendered documentation from GitHub raw content, including argument references, attribute references, and example code snippets.

**Official server:** Provides `search_providers`, `get_provider_details`, `get_provider_capabilities`, and `get_latest_provider_version`. Returns registry metadata rather than full rendered documentation pages.

**Note:** The official server provides structured metadata which may be sufficient for most use cases. For full documentation, reference the [Terraform AWS Provider docs](https://registry.terraform.io/providers/hashicorp/aws/latest/docs) directly.

### SearchAwsccProviderDocs

**Our tool:** Fetched AWSCC provider documentation with schema section parsing.

**Official server:** Same provider search tools work for the AWSCC provider. Search for `hashicorp/awscc` as the provider.

**Note:** Our server prioritized AWSCC resources over AWS provider resources as an opinionated workflow. The official server is provider-agnostic.

### SearchSpecificAwsIaModules

**Our tool:** Curated deep-dive into 4 specific AWS-IA modules (Bedrock, OpenSearch Serverless, SageMaker, Streamlit) with `variables.tf` parsing, submodule discovery, and GitHub release tracking.

**Official server:** Provides general `search_modules` and `get_module_details` that work with any module on the registry. Does not provide the same depth of analysis (no `variables.tf` parsing from GitHub).

**Alternative:** Use `search_modules` with query terms like "bedrock" or "opensearch" to find these modules, then use `get_module_details` for basic information.

### RunCheckovScan -- No direct replacement

**Our tool:** Ran Checkov security scans with auto-installation, multiple framework support, and structured vulnerability reporting.

**Official server:** No security scanning capability.

**Alternative:** Run Checkov directly:

```bash
pip install checkov
checkov -d /path/to/terraform --framework terraform --output json
```

### SearchUserProvidedModule

**Our tool:** Analyzed any Terraform Registry module with `variables.tf` parsing from GitHub, output extraction from README tables, and GitHub release details.

**Official server:** Provides `get_module_details` and `get_latest_module_version` for registry-level metadata. Does not parse `variables.tf` from GitHub.

## Resource Migration

| Our Resource | Replacement |
|-------------|-------------|
| `terraform://development_workflow` | No equivalent. Reference the workflow guide in [AWS Prescriptive Guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/terraform-aws-provider-best-practices/introduction.html). |
| `terraform://aws_provider_resources_listing` | Use `get_provider_capabilities` with provider `hashicorp/aws`. |
| `terraform://awscc_provider_resources_listing` | Use `get_provider_capabilities` with provider `hashicorp/awscc`. |
| `terraform://aws_best_practices` | No equivalent. Reference [AWS Prescriptive Guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/terraform-aws-provider-best-practices/introduction.html) directly. |

## Summary of Gaps

| Feature | Status | Workaround |
|---------|--------|------------|
| Local Terraform CLI execution | Different model (remote runs via HCP Terraform) | Run Terraform CLI directly |
| Terragrunt support | Not available | Run Terragrunt directly |
| Checkov security scanning | Not available | Use Checkov standalone |
| AWSCC provider prioritization | Not available (provider-agnostic) | Reference AWS guidance docs |
| AWS best practices (bundled) | Not available | Reference AWS Prescriptive Guidance |
| Deep module analysis (variables.tf) | Partial (registry metadata only) | Clone module repo for full analysis |
| AWS-IA GenAI module curation | Not available (general search only) | Use `search_modules` with specific queries |

## Removing the Old Server

Once you've verified the official server meets your needs:

1. Remove `awslabs.terraform-mcp-server` from your MCP configuration
2. Uninstall the package: `pip uninstall awslabs.terraform-mcp-server` or remove from your `uv` dependencies
3. The old package will remain on PyPI but will not receive updates
