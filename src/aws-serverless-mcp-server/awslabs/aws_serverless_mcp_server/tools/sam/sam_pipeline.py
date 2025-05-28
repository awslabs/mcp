#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#

"""SAM pipeline tool for AWS Serverless MCP Server."""

from typing import Dict, Any
from awslabs.aws_serverless_mcp_server.models import SamPipelineRequest
from awslabs.aws_serverless_mcp_server.utils.logger import logger
from awslabs.aws_serverless_mcp_server.utils.process import run_command

async def sam_pipeline(request: SamPipelineRequest) -> Dict[str, Any]:
    """
    Sets up CI/CD pipeline configuration for AWS SAM applications.
    
    Args:
        request: SamPipelineRequest object containing pipeline configuration parameters
    
    Returns:
        Dict: Pipeline setup result
    """
    try:
        project_directory = request.project_directory
        cicd_provider = request.cicd_provider
        bucket = request.bucket
        bootstrap_ecr = request.bootstrap_ecr
        bitbucket_repo_uuid = request.bitbucket_repo_uuid
        cloudformation_execution_role = request.cloudformation_execution_role
        confirm_changes = request.confirm_changes
        config_env = request.config_env
        config_file = request.config_file
        create_image_repository = request.create_image_repository
        debug = request.debug
        deployment_branch = request.deployment_branch
        github_org = request.github_org
        gitlab_group = request.gitlab_group
        gitlab_project = request.gitlab_project
        git_provider = request.git_provider
        image_repository = request.image_repository
        oidc_client_id = request.oidc_client_id
        oidc_provider = request.oidc_provider
        oidc_provider_url = request.oidc_provider_url
        output_dir = request.output_dir
        parameter_overrides = request.parameter_overrides
        permissions_provider = request.permissions_provider
        pipeline_execution_role = request.pipeline_execution_role
        pipeline_user = request.pipeline_user
        profile = request.profile
        region = request.region
        save_params = request.save_params
        stage = request.stage
        
        # Build the command arguments for bootstrap
        cmd = ['sam', 'pipeline', 'bootstrap', '--no-interactive']
        cmd.extend(['--cicd-provider', cicd_provider])
        
        if bucket:
            cmd.extend(['--bucket', bucket])
        
        if bootstrap_ecr:
            cmd.append('--bootstrap-ecr')
        
        if bitbucket_repo_uuid:
            cmd.extend(['--bitbucket-repo-uuid', bitbucket_repo_uuid])
        
        if cloudformation_execution_role:
            cmd.extend(['--cloudformation-execution-role', cloudformation_execution_role])
        
        if confirm_changes:
            cmd.append('--confirm-changeset')
        else:
            cmd.append('--no-confirm-changeset')
        
        if config_env:
            cmd.extend(['--config-env', config_env])
        
        if config_file:
            cmd.extend(['--config-file', config_file])
        
        if create_image_repository is True:
            cmd.append('--create-image-repository')
        elif create_image_repository is False:
            cmd.append('--no-create-image-repository')
        
        if debug:
            cmd.append('--debug')
        
        if deployment_branch:
            cmd.extend(['--deployment-branch', deployment_branch])
        
        if github_org:
            cmd.extend(['--github-org', github_org])
        
        if gitlab_group:
            cmd.extend(['--gitlab-group', gitlab_group])
        
        if gitlab_project:
            cmd.extend(['--gitlab-project', gitlab_project])
        
        if git_provider:
            cmd.extend(['--git-provider', git_provider])
        
        if image_repository:
            cmd.extend(['--image-repository', image_repository])
        
        if oidc_client_id:
            cmd.extend(['--oidc-client-id', oidc_client_id])
        
        if oidc_provider:
            cmd.extend(['--oidc-provider', oidc_provider])
        
        if oidc_provider_url:
            cmd.extend(['--oidc-provider-url', oidc_provider_url])
        
        if output_dir:
            cmd.extend(['--output-dir', output_dir])
        
        if parameter_overrides:
            cmd.extend(['--parameter-overrides', parameter_overrides])
        
        if permissions_provider:
            cmd.extend(['--permissions-provider', permissions_provider])
        
        if pipeline_execution_role:
            cmd.extend(['--pipeline-execution-role', pipeline_execution_role])
        
        if pipeline_user:
            cmd.extend(['--pipeline-user', pipeline_user])
        
        if profile:
            cmd.extend(['--profile', profile])
        
        if region:
            cmd.extend(['--region', region])
        
        if save_params:
            cmd.append('--save-params')
        
        if stage:
            cmd.extend(['--stage', stage])
        
        # Execute the bootstrap command with 'yes' to auto-confirm prompts
        logger.info(f"Executing command: yes | {' '.join(cmd)}")
        stdout, stderr = await run_command(['yes', '|'] + cmd, cwd=request.project_directory)
        
        # Generate init command for pipeline init
        init_cmd = ['sam', 'pipeline', 'init']
        
        if config_env:
            init_cmd.extend(['--config-env', config_env])
        
        if config_file:
            init_cmd.extend(['--config-file', config_file])
        
        if debug:
            init_cmd.append('--debug')
        
        if save_params:
            init_cmd.append('--save-params')
        
        init_command = ' '.join(init_cmd)
        
        return {
            'success': True,
            'message': f"Successfully bootstrapped CI/CD pipeline resources for SAM application.",
            'bootstrap_output': stdout.decode(),
            'next_steps': [
                "Review the generated resources in your AWS account",
                f"Run the following command to initialize the pipeline configuration: {init_command}",
                "Commit the generated configuration files to your repository",
                "Follow the provider-specific instructions to complete the setup"
            ]
        }
    except Exception as e:
        error_msg = getattr(e, 'stderr', str(e))
        logger.error(f"Error in sam_pipeline: {error_msg}")
        return {
            'success': False,
            'message': f"Failed to bootstrap SAM pipeline: {error_msg}",
            'error': str(e)
        }
