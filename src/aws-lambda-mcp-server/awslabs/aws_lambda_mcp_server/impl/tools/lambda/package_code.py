import os
import zipfile
import tempfile
import shutil
import logging
import subprocess
from pathlib import Path
from awslabs.aws_lambda_mcp_server.models import PackageCodeRequest

logger = logging.getLogger(__name__)

async def package_code(request: PackageCodeRequest):
    """
    Package Lambda function code into a deployment package.
    
    Args:
        request: PackageCodeRequest object containing packaging parameters
    
    Returns:
        Dict: Information about the packaged code
    """
    source_path = Path(request.source_path)
    output_path = Path(request.output_path)
    
    # Ensure source path exists
    if not source_path.exists():
        raise ValueError(f"Source path does not exist: {source_path}")
    
    # Create output directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create a temporary directory for packaging
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        
        # Copy source files to temporary directory
        if source_path.is_dir():
            # Copy all files from source directory to temp directory
            for item in source_path.glob('**/*'):
                if item.is_file():
                    # Check if file should be excluded
                    if request.exclude_patterns and any(item.match(pattern) for pattern in request.exclude_patterns):
                        continue
                    
                    # Create relative path
                    relative_path = item.relative_to(source_path)
                    target_path = temp_dir_path / relative_path
                    
                    # Create parent directories if they don't exist
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Copy file
                    shutil.copy2(item, target_path)
        else:
            # Copy single file
            shutil.copy2(source_path, temp_dir_path / source_path.name)
        
        # Install dependencies if requested
        if request.include_dependencies:
            # Check for package.json (Node.js)
            package_json_path = temp_dir_path / 'package.json'
            if package_json_path.exists():
                logger.info("Installing Node.js dependencies")
                try:
                    subprocess.run(['npm', 'install', '--production'], cwd=temp_dir_path, check=True)
                except subprocess.CalledProcessError as e:
                    logger.error(f"Error installing Node.js dependencies: {str(e)}")
            
            # Check for requirements.txt (Python)
            requirements_path = temp_dir_path / 'requirements.txt'
            if requirements_path.exists():
                logger.info("Installing Python dependencies")
                try:
                    # Create a subdirectory for Python packages
                    python_packages_dir = temp_dir_path / 'python_packages'
                    python_packages_dir.mkdir(exist_ok=True)
                    
                    # Install packages to the subdirectory
                    subprocess.run(['pip', 'install', '-r', 'requirements.txt', '-t', '.'], cwd=temp_dir_path, check=True)
                except subprocess.CalledProcessError as e:
                    logger.error(f"Error installing Python dependencies: {str(e)}")
        
        # Create zip file
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(temp_dir_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir_path)
                    zipf.write(file_path, arcname)
    
    # Get zip file size
    zip_size = output_path.stat().st_size
    
    logger.info(f"Packaged Lambda code to {output_path} ({zip_size} bytes)")
    
    return {
        "output_path": str(output_path),
        "size_bytes": zip_size,
        "success": True
    }
