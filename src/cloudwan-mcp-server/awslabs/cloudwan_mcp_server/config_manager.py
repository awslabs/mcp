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

"""Configuration management for AWS CloudWAN MCP Server."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import loguru

logger = loguru.logger


class ConfigPersistence:
    """Handles persistent storage of AWS configuration."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize config persistence.
        
        Args:
            config_dir: Directory to store config files. Defaults to ~/.cloudwan-mcp/
        """
        if config_dir is None:
            config_dir = Path.home() / ".cloudwan-mcp"
        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / "config.json"
        self.history_file = self.config_dir / "config_history.json"
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def save_current_config(self, profile: str, region: str, metadata: Optional[Dict] = None) -> bool:
        """Save current configuration.
        
        Args:
            profile: AWS profile name
            region: AWS region
            metadata: Additional metadata to store
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            config_data = {
                "aws_profile": profile,
                "aws_region": region,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            }
            
            # Save current config
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            # Append to history
            history = self._load_history()
            history.append(config_data)
            # Keep last 100 entries
            history = history[-100:]
            
            with open(self.history_file, 'w') as f:
                json.dump(history, f, indent=2)
            
            logger.info(f"Configuration saved: profile={profile}, region={region}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False
    
    def load_current_config(self) -> Optional[Dict]:
        """Load current configuration.
        
        Returns:
            Configuration dict or None if not found
        """
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            return None
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            return None
    
    def get_config_history(self, limit: int = 20) -> List[Dict]:
        """Get configuration history.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of configuration entries
        """
        history = self._load_history()
        return history[-limit:] if history else []
    
    def validate_config_file(self) -> Dict:
        """Validate configuration file integrity.
        
        Returns:
            Validation result dict
        """
        try:
            if not self.config_file.exists():
                return {
                    "valid": False,
                    "error": "Configuration file does not exist",
                    "path": str(self.config_file)
                }
            
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            
            required_fields = ["aws_profile", "aws_region", "timestamp"]
            missing_fields = [f for f in required_fields if f not in config]
            
            if missing_fields:
                return {
                    "valid": False,
                    "error": f"Missing required fields: {missing_fields}",
                    "config": config
                }
            
            return {
                "valid": True,
                "config": config,
                "path": str(self.config_file)
            }
            
        except json.JSONDecodeError as e:
            return {
                "valid": False,
                "error": f"Invalid JSON: {e}",
                "path": str(self.config_file)
            }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "path": str(self.config_file)
            }
    
    def restore_config(self, profile: str, region: str) -> bool:
        """Restore configuration by setting environment variables.
        
        Args:
            profile: AWS profile to restore
            region: AWS region to restore
            
        Returns:
            True if restored successfully
        """
        try:
            os.environ["AWS_PROFILE"] = profile
            os.environ["AWS_DEFAULT_REGION"] = region
            logger.info(f"Configuration restored: profile={profile}, region={region}")
            return True
        except Exception as e:
            logger.error(f"Failed to restore configuration: {e}")
            return False
    
    def _load_history(self) -> List[Dict]:
        """Load configuration history.
        
        Returns:
            List of historical configurations
        """
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception:
            return []


class AWSConfigManager:
    """AWS configuration manager with persistence support."""
    
    def __init__(self):
        """Initialize AWS config manager."""
        self.persistence = ConfigPersistence()
    
    @property
    def profile(self) -> Optional[str]:
        """Get current AWS profile."""
        return os.environ.get("AWS_PROFILE")
    
    @property
    def default_region(self) -> str:
        """Get current AWS region."""
        return os.environ.get("AWS_DEFAULT_REGION", "us-east-1")


# Global config persistence instance
config_persistence = ConfigPersistence()
