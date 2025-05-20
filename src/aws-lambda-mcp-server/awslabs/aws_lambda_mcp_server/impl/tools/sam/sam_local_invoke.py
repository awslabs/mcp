"""SAM local invoke tool for AWS Lambda MCP Server."""

import os
import json
import tempfile
from typing import Dict, Any
import subprocess
from awslabs.aws_lambda_mcp_server.models import SamLocalInvokeRequest
from awslabs.aws_lambda_mcp_server.utils.logger import logger

async def sam_local_invoke(request: SamLocalInvokeRequest) -> Dict[str, Any]:
    """
    Locally invokes a Lambda function using AWS SAM CLI.
    
    Args:
        request: SamLocalInvokeRequest object containing local invoke parameters
    
    Returns:
        Dict: Local invoke result
    """
    try:
        project_directory = request.project_directory
        function_name = request.function_name
        template_file = request.template_file
        event_file = request.event_file
        event_data = request.event_data
        environment_variables = request.environment_variables
        debug_port = request.debug_port
        docker_network = request.docker_network
        container_env_vars = request.container_env_vars
        parameter = request.parameter
        log_file = request.log_file
        layer_cache_basedir = request.layer_cache_basedir
        skip_pull_image = request.skip_pull_image
        debug_args = request.debug_args
        debugger_path = request.debugger_path
        warm_containers = request.warm_containers
        region = request.region
        profile = request.profile
        
        # Create a temporary event file if eventData is provided
        temp_event_file = None
        if event_data and not event_file:
            fd, temp_event_file = tempfile.mkstemp(suffix='.json', prefix=f'.temp-event-', dir=project_directory)
            with os.fdopen(fd, 'w') as f:
                f.write(event_data)
            event_file = temp_event_file
        
        try:
            # Build the command arguments
            cmd = ['sam', 'local', 'invoke', function_name]
            
            if template_file:
                cmd.extend(['--template', template_file])
            
            if event_file:
                cmd.extend(['--event', event_file])
            
            if environment_variables:
                for key, value in environment_variables.items():
                    cmd.extend(['--env-vars', f"{key}={value}"])
            
            if debug_port:
                cmd.extend(['--debug-port', str(debug_port)])
            
            if docker_network:
                cmd.extend(['--docker-network', docker_network])
            
            if container_env_vars:
                for key, value in container_env_vars.items():
                    cmd.extend(['--container-env-var', f"{key}={value}"])
            
            if parameter:
                for key, value in parameter.items():
                    cmd.extend(['--parameter-overrides', f"{key}={value}"])
            
            if log_file:
                cmd.extend(['--log-file', log_file])
            
            if layer_cache_basedir:
                cmd.extend(['--layer-cache-basedir', layer_cache_basedir])
            
            if skip_pull_image:
                cmd.append('--skip-pull-image')
            
            if debug_args:
                cmd.extend(['--debug-args', debug_args])
            
            if debugger_path:
                cmd.extend(['--debugger-path', debugger_path])
            
            if warm_containers:
                cmd.extend(['--warm-containers', warm_containers])
            
            if region:
                cmd.extend(['--region', region])
            
            if profile:
                cmd.extend(['--profile', profile])
            
            # Execute the command
            logger.info(f"Executing command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                cwd=project_directory,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse the result to extract function output and logs
            function_output = result.stdout
            try:
                function_output = json.loads(function_output)
            except json.JSONDecodeError:
                # If not valid JSON, keep as string
                pass
            
            return {
                'success': True,
                'message': f"Successfully invoked Lambda function '{function_name}' locally.",
                'function_output': function_output,
                'logs': result.stderr
            }
        except subprocess.CalledProcessError as e:
            logger.error(f"Error invoking Lambda function locally: {e.stderr}")
            return {
                'success': False,
                'message': f"Failed to invoke Lambda function locally: {e.stderr}",
                'error': str(e)
            }
        except Exception as e:
            logger.error(f"Error in sam_local_invoke: {str(e)}")
            return {
                'success': False,
                'message': f"Failed to invoke Lambda function locally: {str(e)}",
                'error': str(e)
            }
        finally:
            # Clean up temporary event file if created
            if temp_event_file and os.path.exists(temp_event_file):
                os.unlink(temp_event_file)
    except Exception as e:
        logger.error(f"Error in sam_local_invoke: {str(e)}")
        return {
            'success': False,
            'message': f"Failed to invoke Lambda function locally: {str(e)}",
            'error': str(e)
        }
