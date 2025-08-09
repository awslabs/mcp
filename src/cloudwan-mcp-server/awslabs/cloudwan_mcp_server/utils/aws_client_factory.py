from functools import lru_cache
import boto3
from botocore.config import Config
from ..factory import AWSClientFactory


class AWSClientFactoryImpl:
    """Concrete AWS client factory with LRU cache"""

    def __init__(self, max_cache: int = 10):
        self._cache = lru_cache(maxsize=max_cache)(self._create_client)

    def create_client(self, service_name: str, region: str) -> Any:
        """Create boto3 client with standard configuration"""
        return self._cache(service_name, region)

    def _create_client(self, service_name: str, region: str) -> Any:
        """Actual client creation logic"""
        boto_config = Config(retries={"max_attempts": 3}, connect_timeout=5, read_timeout=15)
        return boto3.client(service_name, region_name=region, config=boto_config)
