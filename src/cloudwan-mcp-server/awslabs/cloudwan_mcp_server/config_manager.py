"""Configuration persistence and management for CloudWAN MCP Server."""

import json
import os
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, Optional, Any
import tempfile


class AWSConfigManager:
    """AWS configuration manager following AWS Labs patterns."""
    
    def __init__(self, profile: Optional[str] = None, region: Optional[str] = None):
        """Initialize AWS configuration manager.
        
        Args:
            profile: AWS profile name
            region: AWS region
        """
        self.profile = profile or os.environ.get('AWS_PROFILE', 'default')
        self.region = region or os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
        self._client_cache = {}
    
    def get_aws_client(self, service_name: str, region: Optional[str] = None):
        """Get AWS client for specified service.
        
        Args:
            service_name: AWS service name
            region: AWS region (optional)
            
        Returns:
            Boto3 client instance
        """
        import boto3
        
        effective_region = region or self.region
        cache_key = f"{service_name}:{effective_region}:{self.profile}"
        
        if cache_key not in self._client_cache:
            if self.profile and self.profile != 'default':
                session = boto3.Session(profile_name=self.profile)
                self._client_cache[cache_key] = session.client(service_name, region_name=effective_region)
            else:
                self._client_cache[cache_key] = boto3.client(service_name, region_name=effective_region)
        
        return self._client_cache[cache_key]
    
    def cleanup(self):
        """Cleanup resources."""
        self._client_cache.clear()
    
    def __del__(self):
        """Destructor to cleanup resources."""
        self.cleanup()


class ConfigPersistenceManager:
    """Manages configuration persistence for AWS settings."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize configuration manager.
        
        Args:
            config_dir: Directory to store configuration files. Defaults to temp directory.
        """
        if config_dir is None:
            # Use a subdirectory in the system temp directory
            config_dir = Path(tempfile.gettempdir()) / "cloudwan_mcp" / "config"
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "aws_config.json"
        self.history_file = self.config_dir / "config_history.json"
        
    def save_current_config(self, profile: str, region: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Save current AWS configuration.
        
        Args:
            profile: AWS profile name
            region: AWS region
            metadata: Additional metadata to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            config_data = {
                "aws_profile": profile,
                "aws_region": region,
                "last_updated": datetime.now(UTC).isoformat(),
                "metadata": metadata or {}
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            # Also save to history
            self._save_to_history(config_data)
            
            return True
            
        except Exception:
            return False
    
    def load_current_config(self) -> Optional[Dict[str, Any]]:
        """Load current AWS configuration.
        
        Returns:
            Configuration dictionary if exists, None otherwise
        """
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            return None
        except Exception:
            return None
    
    def get_config_history(self, limit: int = 10) -> list:
        """Get configuration change history.
        
        Args:
            limit: Maximum number of history entries to return
            
        Returns:
            List of configuration history entries
        """
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r') as f:
                    history = json.load(f)
                    return history.get('entries', [])[-limit:]
            return []
        except Exception:
            return []
    
    def restore_config(self, profile: str, region: str) -> bool:
        """Restore AWS configuration and update environment.
        
        Args:
            profile: AWS profile to restore
            region: AWS region to restore
            
        Returns:
            True if restored successfully, False otherwise
        """
        try:
            # Update environment variables
            os.environ["AWS_PROFILE"] = profile
            os.environ["AWS_DEFAULT_REGION"] = region
            
            # Save the restored configuration
            return self.save_current_config(
                profile, 
                region, 
                metadata={"restored": True, "restored_at": datetime.now(UTC).isoformat()}
            )
        except Exception:
            return False
    
    def validate_config_file(self) -> Dict[str, Any]:
        """Validate configuration file integrity.
        
        Returns:
            Validation results dictionary
        """
        result = {
            "config_file_exists": self.config_file.exists(),
            "config_file_readable": False,
            "config_valid": False,
            "history_file_exists": self.history_file.exists(),
            "history_entries": 0,
            "errors": []
        }
        
        try:
            if result["config_file_exists"]:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    result["config_file_readable"] = True
                    
                    # Validate required fields
                    required_fields = ["aws_profile", "aws_region", "last_updated"]
                    if all(field in config for field in required_fields):
                        result["config_valid"] = True
                    else:
                        missing_fields = [f for f in required_fields if f not in config]
                        result["errors"].append(f"Missing required fields: {missing_fields}")
        
        except json.JSONDecodeError as e:
            result["errors"].append(f"Invalid JSON in config file: {str(e)}")
        except Exception as e:
            result["errors"].append(f"Error reading config file: {str(e)}")
        
        try:
            if result["history_file_exists"]:
                with open(self.history_file, 'r') as f:
                    history = json.load(f)
                    result["history_entries"] = len(history.get('entries', []))
        except Exception as e:
            result["errors"].append(f"Error reading history file: {str(e)}")
        
        return result
    
    def clear_config(self) -> bool:
        """Clear all configuration files.
        
        Returns:
            True if cleared successfully, False otherwise
        """
        try:
            if self.config_file.exists():
                self.config_file.unlink()
            
            if self.history_file.exists():
                self.history_file.unlink()
            
            return True
        except Exception:
            return False
    
    def _save_to_history(self, config_data: Dict[str, Any]) -> None:
        """Save configuration change to history file.
        
        Args:
            config_data: Configuration data to save
        """
        try:
            history = {"entries": []}
            
            # Load existing history
            if self.history_file.exists():
                with open(self.history_file, 'r') as f:
                    history = json.load(f)
            
            # Add new entry
            history_entry = config_data.copy()
            history_entry["change_id"] = len(history.get('entries', [])) + 1
            history.setdefault('entries', []).append(history_entry)
            
            # Keep only last 50 entries
            if len(history['entries']) > 50:
                history['entries'] = history['entries'][-50:]
            
            # Save back to file
            with open(self.history_file, 'w') as f:
                json.dump(history, f, indent=2)
                
        except Exception:
            # Don't fail the main operation if history save fails
            pass
    
    def export_config(self, export_path: Path) -> bool:
        """Export current configuration to a file.
        
        Args:
            export_path: Path to export configuration
            
        Returns:
            True if exported successfully, False otherwise
        """
        try:
            current_config = self.load_current_config()
            if current_config is None:
                return False
            
            export_data = {
                "export_timestamp": datetime.now(UTC).isoformat(),
                "current_config": current_config,
                "config_history": self.get_config_history(20)
            }
            
            with open(export_path, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            return True
        except Exception:
            return False
    
    def import_config(self, import_path: Path) -> bool:
        """Import configuration from a file.
        
        Args:
            import_path: Path to import configuration from
            
        Returns:
            True if imported successfully, False otherwise
        """
        try:
            with open(import_path, 'r') as f:
                import_data = json.load(f)
            
            current_config = import_data.get('current_config')
            if current_config and 'aws_profile' in current_config and 'aws_region' in current_config:
                return self.restore_config(
                    current_config['aws_profile'],
                    current_config['aws_region']
                )
            
            return False
        except Exception:
            return False


# Global instance for use across the application
config_persistence = ConfigPersistenceManager()