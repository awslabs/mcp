
import subprocess
from typing import Dict, Any
from awslabs.aws_lambda_mcp_server.models import SamInitRequest
from awslabs.aws_lambda_mcp_server.utils.logger import logger

async def sam_init(request: SamInitRequest) -> Dict[str, Any]:
    """
    Initialize a serverless application with an AWS SAM template

    Parameters
    ----------
    request : SamInitRequest
        Object containing init parameters
        
    Returns
    -------
    Dict[str, Any]
        Result of the initialization
    """
    try:
        # Initialize command list
        cmd = ["sam", "init"]
        
        # Add required parameters
        cmd.extend(["--name", request.project_name])
        cmd.extend(["--runtime", request.runtime])
        cmd.extend(["--dependency-manager", request.dependency_manager])
        
        # Add optional parameters if provided
        if request.architecture:
            cmd.extend(["--architecture", request.architecture])
            
        if request.package_type:
            cmd.extend(["--package-type", request.package_type])
            
        if request.application_template:
            cmd.extend(["--app-template", request.application_template])
            
        if request.application_insights is not None:
            if request.application_insights:
                cmd.append("--application-insights")
                
        if request.no_application_insights is not None:
            if request.no_application_insights:
                cmd.append("--no-application-insights")
                
        if request.base_image:
            cmd.extend(["--base-image", request.base_image])
            
        if request.config_env:
            cmd.extend(["--config-env", request.config_env])
            
        if request.config_file:
            cmd.extend(["--config-file", request.config_file])
            
        if request.debug:
            cmd.append("--debug")
            
        if request.extra_content:
            cmd.extend(["--extra-context", request.extra_content])
            
        if request.location:
            cmd.extend(["--location", request.location])
            
        if request.save_params:
            cmd.append("--save-params")
            
        if request.tracing is not None:
            if request.tracing:
                cmd.append("--tracing")
                
        if request.no_tracing is not None:
            if request.no_tracing:
                cmd.append("--no-tracing")
        
        # Set output directory
        cmd.extend(["--output-dir", request.project_directory])
        
        # Add --no-interactive to avoid prompts
        cmd.append("--no-interactive")
        
        # Execute sam init command
        logger.info(f"Executing command: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        return {
            "success": True,
            "message": f"Successfully initialized SAM project '{request.project_name}' in {request.project_directory}",
            "output": result.stdout
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"SAM init failed with error: {e.stderr}")
        return {
            "success": False,
            "message": f"Failed to initialize SAM project: {e.stderr}",
            "error": str(e)
        }
    except Exception as e:
        logger.error(f"Error in sam_init: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to initialize SAM project: {str(e)}",
            "error": str(e)
        }
