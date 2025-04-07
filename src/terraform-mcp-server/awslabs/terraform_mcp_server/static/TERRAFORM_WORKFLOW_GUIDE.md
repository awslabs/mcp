# Terraform Workflow Guide

## Core Commands

### terraform init
* Initialize a working directory containing Terraform configuration files.
* Sets up the backend and provider plugins.

```bash
terraform init
```

Options:
- `-backend-config=PATH` - Configuration for backend
- `-reconfigure` - Reconfigure backend

### terraform plan
* Creates an execution plan to reach desired state.
* Shows changes to add, modify, or destroy resources.
* Safe operation with no changes to infrastructure

```bash
terraform plan -out=plan.tfplan
```

Options:
- `-var 'name=value'` - Set variable
- `-var-file=filename` - Set variables from file

### terraform validate
* Validates the configuration files.
* Checks configuration files for syntax and consistency.
* Validates resource relationships and dependencies.

```bash
terraform validate
```

### terraform apply
* Apply changes to reach desired state.
* Updates the state file to match the new reality.

```bash
terraform apply plan.tfplan
# Or directly
terraform apply
```

Options:
- `-auto-approve` - Skip interactive approval
- `-var 'name=value'` - Set variable

### terraform destroy
* Destroy the Terraform-managed infrastructure.
* Completely tears down the infrastructure and updates state

```bash
terraform destroy
```

Options:
- `-auto-approve` - Skip interactive approval


## Best Practices for Workflow

1. Always run `terraform plan` before `apply`.
2. Run `terraform validate` after you make changes to the terraform application.
3. Use `-out` to save plans and apply those exact plans.
4. Always show changes from the plan to the user and get confirmation before applying them.

## Key Principles

- **Security First**: Always implement security best practices by default
- **Cost Optimization**: Design resources to minimize costs while meeting requirements
- **Operational Excellence**: Implement proper monitoring, logging, and observability
- **Serverless-First**: Prefer serverless services when possible
- **Infrastructure as Code**: Use Terraform to define all infrastructure
- **Regional Awareness**: Consider regional availability and constraints for services