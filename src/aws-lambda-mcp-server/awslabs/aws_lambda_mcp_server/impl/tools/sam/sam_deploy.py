from awslabs.aws_lambda_mcp_server.utils.process import run_command
from awslabs.aws_lambda_mcp_server.models import SamDeployRequest

async def sam_deploy(request: SamDeployRequest):
    """
    Execute the AWS SAM deploy command with the provided parameters.
    
    Args:
        request: SamDeployRequest object containing all deploy parameters
    """
    cmd = ["sam", "deploy"]
    
    cmd.extend(["--stack-name", request.application_name])
    
    if request.template_file:
        cmd.extend(["--template-file", request.template_file])
    if request.s3_bucket:
        cmd.extend(["--s3-bucket", request.s3_bucket])
    if request.s3_prefix:
        cmd.extend(["--s3-prefix", request.s3_prefix])
    if request.region:
        cmd.extend(["--region", request.region])
    if request.profile:
        cmd.extend(["--profile", request.profile])
    if request.parameter_overrides:
        cmd.extend(["--parameter-overrides", request.parameter_overrides])
    if request.capabilities:
        for capability in request.capabilities:
            cmd.extend(["--capabilities", capability])
    if request.no_confirm_changeset:
        cmd.append("--no-confirm-changeset")
    if request.config_file:
        cmd.extend(["--config-file", request.config_file])
    if request.config_env:
        cmd.extend(["--config-env", request.config_env])
    if request.guided_deploy:
        cmd.append("--guided")
    if request.no_execute_changeset:
        cmd.append("--no-execute-changeset")
    if request.fail_on_empty_changeset:
        cmd.append("--fail-on-empty-changeset")
    if request.force_upload:
        cmd.append("--force-upload")
    if request.use_json:
        cmd.append("--json")
    if request.metadata:
        for key, value in request.metadata.items():
            cmd.extend(["--metadata", f"{key}={value}"])
    if request.notification_arns:
        for arn in request.notification_arns:
            cmd.extend(["--notification-arns", arn])
    if request.tags:
        for key, value in request.tags.items():
            cmd.extend(["--tags", f"{key}={value}"])
    if request.resolve_s3:
        cmd.append("--resolve-s3")
    if request.disable_rollback:
        cmd.append("--disable-rollback")
    if request.debug:
        cmd.append("--debug")
    
    return run_command(cmd, cwd=request.project_directory)
