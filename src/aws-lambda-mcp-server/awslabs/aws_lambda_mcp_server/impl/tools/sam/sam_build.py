from awslabs.aws_lambda_mcp_server.utils.process import run_command
from awslabs.aws_lambda_mcp_server.models import SamBuildRequest

async def sam_build(request: SamBuildRequest):
    """
    Execute the AWS SAM build command with the provided parameters.
    
    Args:
        request: SamBuildRequest object containing all build parameters
    """
    cmd = ["sam", "build"]
    
    if request.resource_id:
        cmd.extend(["--resource-id", request.resource_id])
    if request.template_file:
        cmd.extend(["--template-file", request.template_file])
    if request.base_dir:
        cmd.extend(["--base-dir", request.base_dir])
    if request.build_dir:
        cmd.extend(["--build-dir", request.build_dir])
    if request.cache_dir:
        cmd.extend(["--cache-dir", request.cache_dir])
    if request.cached:
        cmd.append("--cached")
    if request.use_container:
        cmd.append("--use-container")
    if request.no_use_container:
        cmd.append("--no-use-container")
    if request.container_env_vars:
        for key, value in request.container_env_vars.items():
            cmd.extend(["--container-env-var", f"{key}={value}"])
    if request.container_env_var_file:
        cmd.extend(["--container-env-var-file", request.container_env_var_file])
    if request.skip_pull_image:
        cmd.append("--skip-pull-image")
    if request.build_method:
        cmd.extend(["--build-method", request.build_method])
    if request.build_in_source:
        cmd.append("--build-in-source")
    if request.no_build_in_source:
        cmd.append("--no-build-in-source")
    if request.beta_features:
        cmd.append("--beta-features")
    if request.no_beta_features:
        cmd.append("--no-beta-features")
    if request.build_image:
        cmd.extend(["--build-image", request.build_image])
    if request.debug:
        cmd.append("--debug")
    if request.docker_network:
        cmd.extend(["--docker-network", request.docker_network])
    if request.exclude:
        for item in request.exclude:
            cmd.extend(["--exclude", item])
    if request.manifest:
        cmd.extend(["--manifest", request.manifest])
    if request.mount_symlinks:
        cmd.append("--mount-symlinks")
    if request.parallel:
        cmd.append("--parallel")
    if request.parameter_overrides:
        cmd.extend(["--parameter-overrides", request.parameter_overrides])
    if request.region:
        cmd.extend(["--region", request.region])
    if request.save_params:
        cmd.append("--save-params")
    if request.skip_prepare_infra:
        cmd.append("--skip-prepare-infra")
    if request.terraform_project_root_path:
        cmd.extend(["--terraform-project-root-path", request.terraform_project_root_path])
    return run_command(cmd, cwd=request.project_directory)

