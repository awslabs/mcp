from typing import Any, Dict
import re
import logging

from ..consts import ECR_REPOSITORY_PATTERN, STATUS_SUCCESS, STATUS_ERROR
from .common import execute_command, format_result

logger = logging.getLogger(__name__)

def is_ecr_repository(repository: str) -> bool:
    """
    Validate if the provided repository URL is an ECR repository.
    
    ECR repository URLs typically follow the pattern:
    <aws_account_id>.dkr.ecr.<region>.amazonaws.com/<repository_name>:<tag>
    
    Args:
        repository: The repository URL to validate
        
    Returns:
        bool: True if the repository is an ECR repository, False otherwise
    """
    return bool(re.match(ECR_REPOSITORY_PATTERN, repository))

def push_image(image: str) -> Dict[str, Any]:
    """
    Push an image to a repository.
    
    Args:
        image: The image to push 
        
    Returns:
        Result of the push task
    """
    push_result = execute_command(['finch', 'image', 'push', image])
    
    if push_result.returncode == 0:
        return format_result(STATUS_SUCCESS, f"Successfully pushed image {image}.")
    else:
        return format_result(STATUS_ERROR, f"Failed to push image {image}: {push_result.stderr}",
                                stderr=push_result.stderr)
