"""
AWS Credential Manager for Cross-Account Access
Handles role assumption and credential caching for multi-account billing operations
"""
import boto3
from datetime import datetime, timedelta
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


class AWSCredentialManager:
    """Manages AWS credentials for cross-account access"""
    
    # Stable cross-account role name
    CROSS_ACCOUNT_ROLE_NAME = "MCPServerCrossAccountRole"
    
    def __init__(self):
        self.credentials_cache = {}
        self._current_account_id = None
        # Don't initialize on startup - do it lazily
        
    @property
    def current_account_id(self) -> str:
        """Lazy initialization of current account ID"""
        if self._current_account_id is None:
            self._initialize_current_account()
        return self._current_account_id
    
    def _initialize_current_account(self):
        """Initialize and cache the current account ID"""
        try:
            sts_client = boto3.client('sts')
            identity = sts_client.get_caller_identity()
            self._current_account_id = identity['Account']
            logger.info(f"Initialized with current account: {self._current_account_id}")
        except Exception as e:
            logger.warning(f"Failed to get current account ID during initialization: {e}")
            logger.warning("Will retry when needed. Ensure AWS credentials are configured.")
            # Don't raise - allow server to start even if AWS creds aren't ready
            self._current_account_id = "000000000000"  # Placeholder
    
    def get_client(self, service: str, account_id: Optional[str] = None, 
                   region: str = 'us-east-1'):
        """
        Get an AWS client, assuming cross-account role if needed
        
        Args:
            service: AWS service name (e.g., 'ce', 'cur', 'budgets')
            account_id: Target account ID (None = use current account)
            region: AWS region
            
        Returns:
            boto3 client for the specified service
        """
        # Ensure we have current account ID
        _ = self.current_account_id
        
        # If no account_id or same as current, use default credentials
        if not account_id or account_id == self._current_account_id:
            logger.debug(f"Using default credentials for service: {service}")
            try:
                return boto3.client(service, region_name=region)
            except Exception as e:
                logger.error(f"Failed to create AWS client for {service}: {e}")
                raise Exception(
                    f"Failed to create AWS client. Ensure AWS credentials are configured. "
                    f"Set AWS_PROFILE or AWS_ACCESS_KEY_ID environment variables. Error: {e}"
                )
        
        # Validate account ID format
        if not self._is_valid_account_id(account_id):
            raise ValueError(f"Invalid AWS account ID format: {account_id}")
        
        # Check credential cache
        cache_key = f"{account_id}:{service}"
        if cache_key in self.credentials_cache:
            cached = self.credentials_cache[cache_key]
            # Check if credentials are still valid (refresh 5 min before expiry)
            if cached['expiration'] > datetime.now(cached['expiration'].tzinfo) + timedelta(minutes=5):
                logger.debug(f"Using cached credentials for account: {account_id}")
                return boto3.client(
                    service,
                    region_name=region,
                    aws_access_key_id=cached['access_key'],
                    aws_secret_access_key=cached['secret_key'],
                    aws_session_token=cached['session_token']
                )
        
        # Assume role in target account
        logger.info(f"Assuming role in account: {account_id}")
        credentials = self._assume_role(account_id)
        
        # Cache credentials
        self.credentials_cache[cache_key] = credentials
        
        # Return client with assumed role credentials
        return boto3.client(
            service,
            region_name=region,
            aws_access_key_id=credentials['access_key'],
            aws_secret_access_key=credentials['secret_key'],
            aws_session_token=credentials['session_token']
        )
    
    def _assume_role(self, account_id: str) -> Dict:
        """Assume the standard cross-account role in target account"""
        try:
            sts_client = boto3.client('sts')
            role_arn = f"arn:aws:iam::{account_id}:role/{self.CROSS_ACCOUNT_ROLE_NAME}"
            
            response = sts_client.assume_role(
                RoleArn=role_arn,
                RoleSessionName=f'mcp-billing-{account_id}',
                DurationSeconds=3600  # 1 hour
            )
            
            credentials = response['Credentials']
            
            return {
                'access_key': credentials['AccessKeyId'],
                'secret_key': credentials['SecretAccessKey'],
                'session_token': credentials['SessionToken'],
                'expiration': credentials['Expiration']
            }
        except Exception as e:
            logger.error(f"Failed to assume role in account {account_id}: {str(e)}")
            raise Exception(
                f"Failed to assume role in account {account_id}. "
                f"Ensure the role '{self.CROSS_ACCOUNT_ROLE_NAME}' exists and has proper trust policy. "
                f"Error: {str(e)}"
            )
    
    def _is_valid_account_id(self, account_id: str) -> bool:
        """Validate AWS account ID format (12 digits)"""
        return account_id and len(account_id) == 12 and account_id.isdigit()
    
    def clear_cache(self, account_id: Optional[str] = None):
        """Clear cached credentials for specific account or all accounts"""
        if account_id:
            keys_to_remove = [k for k in self.credentials_cache.keys() 
                            if k.startswith(f"{account_id}:")]
            for key in keys_to_remove:
                del self.credentials_cache[key]
            logger.info(f"Cleared cache for account: {account_id}")
        else:
            self.credentials_cache.clear()
            logger.info("Cleared all cached credentials")
    
    def get_current_account_id(self) -> str:
        """Get the current account ID"""
        return self.current_account_id


# Create singleton instance
credential_manager = AWSCredentialManager()