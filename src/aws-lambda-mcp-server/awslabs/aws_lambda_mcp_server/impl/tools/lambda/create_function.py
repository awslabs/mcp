import boto3
import os
import zipfile
import tempfile
import shutil
import logging
from pathlib import Path
from awslabs.aws_lambda_mcp_server.models import CreateFunctionRequest

logger = logging.getLogger(__name__)

async def create_function(request: CreateFunctionRequest):
    """
    Create an AWS Lambda function.
    
    Args:
        request: CreateFunctionRequest object containing all function parameters
    
    Returns:
        Dict: Response from AWS Lambda API
    """
    # Initialize Lambda client
    session = boto3.Session(
        region_name=request.region or os.environ.get('AWS_REGION', 'us-east-1'),
        profile_name=os.environ.get('AWS_PROFILE', 'default')
    )
    lambda_client = session.client('lambda')
    
    # Prepare function code
    code_config = {}
    
    # Check if S3 parameters are provided
    if request.s3_bucket and request.s3_key:
        code_config['S3Bucket'] = request.s3_bucket
        code_config['S3Key'] = request.s3_key
        
        if request.s3_object_version:
            code_config['S3ObjectVersion'] = request.s3_object_version
            
        if request.source_kms_key_arn:
            code_config['SourceKMSKeyArn'] = request.source_kms_key_arn
    
    # Check if image URI is provided
    elif request.image_uri:
        code_config['ImageUri'] = request.image_uri
    
    # Use local code path if provided and no S3 or image URI parameters are provided
    elif request.code_path:
        code_path = Path(request.code_path)
        
        # Create a temporary directory for packaging
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = Path(temp_dir) / f"{request.function_name}.zip"
            
            # Check if code_path is a directory or a zip file
            if code_path.is_dir():
                # Create a zip file from the directory
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, _, files in os.walk(code_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, code_path)
                            zipf.write(file_path, arcname)
            elif code_path.suffix == '.zip':
                # Copy the zip file to the temporary directory
                shutil.copy(code_path, zip_path)
            else:
                raise ValueError(f"Code path must be a directory or a zip file: {code_path}")
            
            # Read the zip file
            with open(zip_path, 'rb') as f:
                code_content = f.read()
            
            code_config['ZipFile'] = code_content
    else:
        raise ValueError("Either code_path, s3_bucket and s3_key, or image_uri must be provided")
    
    # Prepare function configuration
    function_config = {
        'FunctionName': request.function_name,
        'Runtime': request.runtime.value,
        'Role': request.role,
        'Handler': request.handler,
        'Code': code_config,
        'Timeout': request.timeout,
        'MemorySize': request.memory_size,
        'Architectures': request.architectures
    }
    
    # Add optional parameters if provided
    if request.description:
        function_config['Description'] = request.description
    
    if request.environment_variables:
        function_config['Environment'] = {'Variables': request.environment_variables}
    
    if request.tags:
        function_config['Tags'] = request.tags
    
    if request.vpc_config:
        function_config['VpcConfig'] = request.vpc_config
    
    if request.dead_letter_config:
        function_config['DeadLetterConfig'] = request.dead_letter_config
    
    if request.tracing_config:
        function_config['TracingConfig'] = request.tracing_config
    
    if request.layers:
        function_config['Layers'] = request.layers
    
    # Create the Lambda function
    try:
        response = lambda_client.create_function(**function_config)
        logger.info(f"Created Lambda function: {request.function_name}")
        return response
    except Exception as e:
        logger.error(f"Error creating Lambda function: {str(e)}")
        raise
