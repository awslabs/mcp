import boto3
import os
import zipfile
import tempfile
import shutil
import logging
from pathlib import Path
from awslabs.aws_lambda_mcp_server.models import UpdateFunctionRequest

logger = logging.getLogger(__name__)

async def update_function(request: UpdateFunctionRequest):
    """
    Update an AWS Lambda function.
    
    Args:
        request: UpdateFunctionRequest object containing all function parameters
    
    Returns:
        Dict: Response from AWS Lambda API
    """
    # Initialize Lambda client
    session = boto3.Session(
        region_name=request.region or os.environ.get('AWS_REGION', 'us-east-1'),
        profile_name=os.environ.get('AWS_PROFILE', 'default')
    )
    lambda_client = session.client('lambda')
    
    # Update function configuration
    config_updates = {}
    
    # Add configuration parameters if provided
    if request.role:
        config_updates['Role'] = request.role
    
    if request.handler:
        config_updates['Handler'] = request.handler
    
    if request.description:
        config_updates['Description'] = request.description
    
    if request.timeout:
        config_updates['Timeout'] = request.timeout
    
    if request.memory_size:
        config_updates['MemorySize'] = request.memory_size
    
    if request.environment_variables:
        config_updates['Environment'] = {'Variables': request.environment_variables}
    
    if request.vpc_config:
        config_updates['VpcConfig'] = request.vpc_config
    
    if request.dead_letter_config:
        config_updates['DeadLetterConfig'] = request.dead_letter_config
    
    if request.tracing_config:
        config_updates['TracingConfig'] = request.tracing_config
    
    if request.layers:
        config_updates['Layers'] = request.layers
    
    if request.architectures:
        config_updates['Architectures'] = request.architectures
    
    # Update function configuration if there are any updates
    if config_updates:
        try:
            config_response = lambda_client.update_function_configuration(
                FunctionName=request.function_name,
                **config_updates
            )
            logger.info(f"Updated Lambda function configuration: {request.function_name}")
        except Exception as e:
            logger.error(f"Error updating Lambda function configuration: {str(e)}")
            raise
    
    # Update function code if provided
    code_update_params = {'FunctionName': request.function_name}
    
    # Check if S3 parameters are provided
    if request.s3_bucket and request.s3_key:
        code_update_params['S3Bucket'] = request.s3_bucket
        code_update_params['S3Key'] = request.s3_key
        
        if request.s3_object_version:
            code_update_params['S3ObjectVersion'] = request.s3_object_version
            
        if request.source_kms_key_arn:
            code_update_params['SourceKMSKeyArn'] = request.source_kms_key_arn
        
        # Update function code
        try:
            code_response = lambda_client.update_function_code(**code_update_params)
            logger.info(f"Updated Lambda function code from S3: {request.function_name}")
        except Exception as e:
            logger.error(f"Error updating Lambda function code from S3: {str(e)}")
            raise
    
    # Check if image URI is provided
    elif request.image_uri:
        code_update_params['ImageUri'] = request.image_uri
        
        # Update function code
        try:
            code_response = lambda_client.update_function_code(**code_update_params)
            logger.info(f"Updated Lambda function code with image: {request.function_name}")
        except Exception as e:
            logger.error(f"Error updating Lambda function code with image: {str(e)}")
            raise
    
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
            
            # Update function code
            try:
                code_response = lambda_client.update_function_code(
                    FunctionName=request.function_name,
                    ZipFile=code_content
                )
                logger.info(f"Updated Lambda function code: {request.function_name}")
            except Exception as e:
                logger.error(f"Error updating Lambda function code: {str(e)}")
                raise
    
    # Get the updated function
    try:
        response = lambda_client.get_function(FunctionName=request.function_name)
        return response
    except Exception as e:
        logger.error(f"Error getting updated Lambda function: {str(e)}")
        raise
