# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Secure storage utility for EC2 key pair private keys.

SECURITY NOTE: This module only stores private keys securely in AWS services.
Private keys are NEVER retrieved through this interface for security reasons.
Users must access stored keys directly through AWS Console/CLI.
"""

import json
import logging
from typing import Any, Dict, Optional

from awslabs.ec2_mcp_server.utils.aws import AWSClientManager, handle_aws_error, format_tags, format_s3_tags

logger = logging.getLogger(__name__)


class KeyStorageManager:
    """
    Manages secure storage of EC2 key pair private keys using multiple storage backends.
    
    SECURITY DESIGN: This class only supports STORING private keys, not retrieving them.
    This prevents exposure of private keys to LLMs or unauthorized access through the MCP interface.
    To access stored keys, users must use AWS Console, CLI, or direct API calls with proper permissions.
    """
    
    STORAGE_METHODS = {
        "secrets_manager": "AWS Secrets Manager",
        "s3_encrypted": "S3 with KMS Encryption", 
        "parameter_store": "AWS Systems Manager Parameter Store"
    }
    
    def __init__(self, aws_client: AWSClientManager, config: Dict[str, Any]):
        """
        Initialize the key storage manager.
        
        Args:
            aws_client: AWS client manager instance
            config: Configuration dictionary
        """
        self.aws_client = aws_client
        self.config = config
        self.region = config.get("aws_region", "us-east-1")
        
    async def store_private_key(
        self,
        key_name: str,
        private_key_material: str,
        storage_method: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Store private key using the specified storage method.
        
        Args:
            key_name: The EC2 key pair name
            private_key_material: The private key content
            storage_method: Storage method to use
            **kwargs: Additional method-specific parameters
            
        Returns:
            Dict containing storage results and metadata
        """
        try:
            if private_key_material is None:
                raise ValueError("Private key material cannot be None")
            
            if storage_method == "secrets_manager":
                return await self._store_in_secrets_manager(key_name, private_key_material, **kwargs)
            elif storage_method == "s3_encrypted":
                return await self._store_in_s3_encrypted(key_name, private_key_material, **kwargs)
            elif storage_method == "parameter_store":
                return await self._store_in_parameter_store(key_name, private_key_material, **kwargs)
            else:
                raise ValueError(f"Unsupported storage method: {storage_method}")
                
        except Exception as e:
            logger.error(f"Failed to store private key for {key_name}: {e}")
            return {
                "status": "error",
                "message": f"Failed to store private key: {str(e)}"
            }
    
    
    async def delete_stored_key(
        self,
        key_name: str,
        storage_method: str,
        storage_location: str
    ) -> Dict[str, Any]:
        """
        Delete stored private key.
        
        Args:
            key_name: The EC2 key pair name
            storage_method: Storage method used
            storage_location: Location identifier for the stored key
            
        Returns:
            Dict containing deletion results
        """
        try:
            if storage_method == "secrets_manager":
                return await self._delete_from_secrets_manager(storage_location)
            elif storage_method == "s3_encrypted":
                return await self._delete_from_s3_encrypted(storage_location)
            elif storage_method == "parameter_store":
                return await self._delete_from_parameter_store(storage_location)
            else:
                raise ValueError(f"Unsupported storage method: {storage_method}")
                
        except Exception as e:
            logger.error(f"Failed to delete stored key for {key_name}: {e}")
            return {
                "status": "error",
                "message": f"Failed to delete stored key: {str(e)}"
            }
    
    async def _store_in_secrets_manager(
        self,
        key_name: str,
        private_key_material: str,
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Store private key in AWS Secrets Manager."""
        try:
            if private_key_material is None:
                raise ValueError("Private key material cannot be None")
            
            secrets_client = self.aws_client.get_client("secretsmanager")
            secret_name = f"ec2/keypairs/{key_name}"
            
            secret_value = {
                "private_key": private_key_material,
                "key_name": key_name,
                "created_by": "ec2-mcp-server"
            }
            
            create_params = {
                "Name": secret_name,
                "Description": description or f"Private key for EC2 key pair {key_name}",
                "SecretString": json.dumps(secret_value)
            }
            
            if tags:
                create_params["Tags"] = format_tags(tags)
            
            response = secrets_client.create_secret(**create_params)
            
            return {
                "status": "success",
                "storage_method": "secrets_manager",
                "storage_location": secret_name,
                "secret_arn": response["ARN"],
                "message": f"Private key stored in Secrets Manager: {secret_name}"
            }
            
        except Exception as e:
            logger.error(f"Secrets Manager storage failed: {e}")
            raise
    
    async def _store_in_s3_encrypted(
        self,
        key_name: str,
        private_key_material: str,
        tags: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Store private key in S3 with KMS encryption."""
        try:
            s3_client = self.aws_client.get_client("s3")
            
            # Use configured bucket or default
            if self.region is None:
                raise ValueError("AWS region cannot be None for S3 storage")
            
            default_bucket = f"ec2-mcp-keypairs-{self.region}"
            bucket = self.config.get("s3_keypair_bucket") or default_bucket
            prefix = self.config.get("s3_keypair_prefix") or "private-keys"
            s3_key = f"{prefix}/{key_name}.pem"
            
            if bucket is None:
                raise ValueError("S3 bucket name cannot be None")
            
            # Check if this is a default bucket name (auto-generated)
            is_default_bucket = bucket == default_bucket
            
            # Ensure bucket exists, auto-create if it's a default bucket
            bucket_check = await self._ensure_s3_bucket_exists(bucket, is_default_bucket)
            if bucket_check["status"] != "success":
                raise ValueError(bucket_check["message"])
            
            # Store metadata with the key
            if key_name is None:
                raise ValueError("Key name cannot be None")
            
            metadata = {
                "key-name": str(key_name),
                "created-by": "ec2-mcp-server",
                "encryption-method": "kms"
            }
            
            # KMS key ID (use default aws/s3 if not specified)
            kms_key_id = self.config.get("kms_key_id")
            
            # Upload to S3 with KMS encryption
            # Validate and encode private_key_material
            if private_key_material is None:
                raise ValueError("Private key material cannot be None")
            
            if isinstance(private_key_material, bytes):
                key_body = private_key_material
            else:
                key_body = str(private_key_material).encode()
                
            put_object_params = {
                "Bucket": bucket,
                "Key": s3_key,
                "Body": key_body,
                "ServerSideEncryption": "aws:kms",
                "Metadata": metadata,
                "ContentType": "application/x-pem-file"
            }
            
            # Add KMS key ID if specified (otherwise uses default aws/s3 key)
            if kms_key_id:
                put_object_params["SSEKMSKeyId"] = kms_key_id
            
            # Add S3 object tags if provided
            if tags:
                s3_tags = format_s3_tags(tags)
                if s3_tags:
                    put_object_params["Tagging"] = s3_tags
            
            s3_client.put_object(**put_object_params)
            
            storage_location = f"s3://{bucket}/{s3_key}"
            
            return {
                "status": "success",
                "storage_method": "s3_encrypted",
                "storage_location": storage_location,
                "bucket": bucket,
                "key": s3_key,
                "encryption": "KMS",
                "kms_key": kms_key_id or "aws/s3 (default)",
                "message": f"Private key encrypted with KMS and stored in S3: {storage_location}"
            }
            
        except Exception as e:
            logger.error(f"S3 KMS storage failed: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Private key material type: {type(private_key_material)}")
            logger.error(f"Tags type: {type(tags)}, value: {tags}")
            raise
    
    async def _store_in_parameter_store(
        self,
        key_name: str,
        private_key_material: str,
        parameter_name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Store private key in AWS Systems Manager Parameter Store."""
        try:
            if private_key_material is None:
                raise ValueError("Private key material cannot be None")
            
            ssm_client = self.aws_client.get_client("ssm")
            
            param_name = parameter_name or f"/ec2/keypairs/{key_name}/private-key"
            
            put_params = {
                "Name": param_name,
                "Value": private_key_material,
                "Type": "SecureString",
                "Description": description or f"Private key for EC2 key pair {key_name}",
                "Overwrite": False
            }
            
            if tags:
                put_params["Tags"] = format_tags(tags)
            
            ssm_client.put_parameter(**put_params)
            
            return {
                "status": "success",
                "storage_method": "parameter_store",
                "storage_location": param_name,
                "message": f"Private key stored in Parameter Store: {param_name}"
            }
            
        except Exception as e:
            logger.error(f"Parameter Store storage failed: {e}")
            raise
    
    
    async def _delete_from_secrets_manager(self, secret_name: str) -> Dict[str, Any]:
        """Delete secret from Secrets Manager."""
        try:
            secrets_client = self.aws_client.get_client("secretsmanager")
            secrets_client.delete_secret(SecretId=secret_name, ForceDeleteWithoutRecovery=True)
            
            return {
                "status": "success",
                "message": f"Secret deleted from Secrets Manager: {secret_name}"
            }
            
        except Exception as e:
            logger.error(f"Secrets Manager deletion failed: {e}")
            raise
    
    async def _delete_from_s3_encrypted(self, s3_location: str) -> Dict[str, Any]:
        """Delete encrypted key from S3."""
        try:
            s3_client = self.aws_client.get_client("s3")
            
            # Parse S3 location
            bucket, key = s3_location.replace("s3://", "").split("/", 1)
            
            s3_client.delete_object(Bucket=bucket, Key=key)
            
            return {
                "status": "success",
                "message": f"Encrypted key deleted from S3: {s3_location}"
            }
            
        except Exception as e:
            logger.error(f"S3 deletion failed: {e}")
            raise
    
    async def _delete_from_parameter_store(self, parameter_name: str) -> Dict[str, Any]:
        """Delete parameter from Parameter Store."""
        try:
            ssm_client = self.aws_client.get_client("ssm")
            ssm_client.delete_parameter(Name=parameter_name)
            
            return {
                "status": "success",
                "message": f"Parameter deleted from Parameter Store: {parameter_name}"
            }
            
        except Exception as e:
            logger.error(f"Parameter Store deletion failed: {e}")
            raise
    
    async def _ensure_s3_bucket_exists(self, bucket_name: str, is_default_bucket: bool = False) -> Dict[str, Any]:
        """
        Ensure S3 bucket exists, optionally creating it if it's a default bucket.
        
        Args:
            bucket_name: Name of the S3 bucket
            is_default_bucket: True if this is a default auto-generated bucket name
            
        Returns:
            Dict with status and message
        """
        try:
            s3_client = self.aws_client.get_client("s3")
            
            # Check if bucket exists
            try:
                s3_client.head_bucket(Bucket=bucket_name)
                return {
                    "status": "success",
                    "message": f"Bucket {bucket_name} exists"
                }
            except Exception as head_error:
                # Check if it's a NoSuchBucket error, 404, or access denied
                error_code = getattr(head_error, 'response', {}).get('Error', {}).get('Code', '')
                error_str = str(head_error)
                
                # Multiple ways to detect bucket doesn't exist
                is_no_such_bucket = (
                    error_code == 'NoSuchBucket' or 
                    error_code == '404' or
                    'NoSuchBucket' in error_str or 
                    'Not Found' in error_str or
                    '(404)' in error_str
                )
                
                logger.debug(f"S3 head_bucket error: {head_error}, error_code: {error_code}, is_no_such_bucket: {is_no_such_bucket}")
                
                if is_no_such_bucket:
                    # Bucket doesn't exist
                    if not is_default_bucket:
                        return {
                            "status": "error",
                            "message": f"Custom bucket {bucket_name} does not exist. Please create it manually."
                        }
                    
                    # Auto-create default bucket
                    logger.info(f"Creating default S3 bucket: {bucket_name}")
                    
                    create_params = {"Bucket": bucket_name}
                    
                    # Add region-specific configuration for buckets outside us-east-1
                    if self.region and self.region != "us-east-1":
                        create_params["CreateBucketConfiguration"] = {
                            "LocationConstraint": self.region
                        }
                    
                    s3_client.create_bucket(**create_params)
                    
                    # Enable default encryption
                    s3_client.put_bucket_encryption(
                        Bucket=bucket_name,
                        ServerSideEncryptionConfiguration={
                            "Rules": [
                                {
                                    "ApplyServerSideEncryptionByDefault": {
                                        "SSEAlgorithm": "AES256"
                                    }
                                }
                            ]
                        }
                    )
                    
                    # Block public access
                    s3_client.put_public_access_block(
                        Bucket=bucket_name,
                        PublicAccessBlockConfiguration={
                            "BlockPublicAcls": True,
                            "IgnorePublicAcls": True,
                            "BlockPublicPolicy": True,
                            "RestrictPublicBuckets": True
                        }
                    )
                    
                    return {
                        "status": "success",
                        "message": f"Created default S3 bucket: {bucket_name}",
                        "created": True
                    }
                else:
                    # Handle other S3 errors (permissions, etc.)
                    return {
                        "status": "error",
                        "message": f"Cannot access bucket {bucket_name}: {str(head_error)}"
                    }
                
        except Exception as e:
            logger.error(f"Failed to ensure bucket exists: {e}")
            return {
                "status": "error", 
                "message": f"S3 bucket check failed: {str(e)}"
            }