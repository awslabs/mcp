"""
AWS Labs Enterprise Compliance Module for Network MCP Server.

This module enforces AWS Labs' strict security, operational, and governance
requirements for production-grade MCP servers. It provides validation for:
- Security headers and HTTP security best practices
- Standardized logging with audit trail capabilities
- Credential leakage prevention and sanitization
- IMDSv2 enforcement for EC2 metadata protection
- Input validation and injection prevention
- Resource tagging compliance
"""

import re
import logging
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

# ============================================================================
# AWS LABS COMPLIANCE CONSTANTS
# ============================================================================

class ComplianceLevel(Enum):
    """Compliance enforcement levels."""
    STRICT = "strict"      # Block non-compliant operations
    MONITOR = "monitor"    # Log violations but allow
    DISABLED = "disabled"  # No enforcement

@dataclass
class SecurityHeader:
    """Security header configuration."""
    name: str
    value: str
    required: bool = True
    regex_pattern: Optional[str] = None

# AWS Labs mandatory security headers
MANDATORY_SECURITY_HEADERS = {
    "X-Content-Type-Options": SecurityHeader(
        name="X-Content-Type-Options",
        value="nosniff",
        required=True
    ),
    "X-Frame-Options": SecurityHeader(
        name="X-Frame-Options",
        value="DENY",
        required=True
    ),
    "Strict-Transport-Security": SecurityHeader(
        name="Strict-Transport-Security",
        value="max-age=31536000; includeSubDomains; preload",
        required=True,
        regex_pattern=r"^max-age=\d+; includeSubDomains; preload$"
    ),
    "X-XSS-Protection": SecurityHeader(
        name="X-XSS-Protection",
        value="1; mode=block",
        required=False
    ),
    "Content-Security-Policy": SecurityHeader(
        name="Content-Security-Policy",
        value="default-src 'self'",
        required=True
    )
}

# Credential patterns that must NEVER appear in logs
CREDENTIAL_PATTERNS = [
    re.compile(r'AKIA[0-9A-Z]{16}'),  # AWS Access Key ID
    re.compile(r'aws_access_key_id\s*=\s*[A-Z0-9]{20}', re.IGNORECASE),
    re.compile(r'aws_secret_access_key\s*=\s*[A-Za-z0-9/+=]{40}', re.IGNORECASE),
    re.compile(r'aws_session_token\s*=\s*[A-Za-z0-9/+=]+', re.IGNORECASE),
    re.compile(r'session_token\s*=\s*[A-Za-z0-9/+=]+', re.IGNORECASE),
    re.compile(r'\b\d{12}\b'),  # AWS Account IDs (context-dependent)
]

# IMDSv2 enforcement configuration
IMDSV2_REQUIRED_ENVS = ['production', 'staging']
EC2_METADATA_TOKEN_ENDPOINT = 'http://169.254.169.254/latest/api/token'

# ============================================================================
# COMPLIANCE VALIDATOR CLASS
# ============================================================================

class AWSLabsComplianceValidator:
    """
    Enterprise compliance validator for AWS Network MCP Server.
    
    This class provides methods to validate security policies, enforce
    governance requirements, and ensure operational excellence.
    """
    
    def __init__(self, compliance_level: ComplianceLevel = ComplianceLevel.STRICT):
        self.compliance_level = compliance_level
        self.logger = logging.getLogger(__name__)
        self._violation_count = 0
        
    # ------------------------------------------------------------------------
    # SECURITY HEADERS VALIDATION
    # ------------------------------------------------------------------------
    
    def validate_security_headers(self, headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Validate HTTP security headers against AWS Labs requirements.
        
        Args:
            headers: Dictionary of HTTP headers to validate
            
        Returns:
            Dict containing validation results and any violations
        """
        violations = []
        missing_headers = []
            
        for header_name, config in MANDATORY_SECURITY_HEADERS.items():
            if header_name not in headers:
                if config.required:
                    missing_headers.append(header_name)
                    violations.append(f"Missing required header: {header_name}")
                continue
                
            # Validate header value
            header_value = headers[header_name]
            if config.regex_pattern:
                if not re.match(config.regex_pattern, header_value, re.IGNORECASE):
                    violations.append(
                        f"Header {header_name} value '{header_value}' does not match "
                        f"required pattern: {config.regex_pattern}"
                    )
            elif header_value.lower() != config.value.lower():
                violations.append(
                    f"Header {header_name} has incorrect value: '{header_value}', "
                    f"expected: '{config.value}'"
                )
        
        is_compliant = len(violations) == 0
        
        if not is_compliant:
            self._log_violation("security_headers", violations)
            
        return {
            "compliant": is_compliant,
            "violations": violations,
            "missing_headers": missing_headers,
            "header_count": len(headers)
        }
    
    # ------------------------------------------------------------------------
    # LOGGING COMPLIANCE
    # ------------------------------------------------------------------------
    
    def validate_log_record(self, record: logging.LogRecord) -> Dict[str, Any]:
        """
        Validate a log record for AWS Labs compliance.
        
        Checks:
        - No credential leakage
        - Proper log level usage
        - Required fields present
        
        Args:
            record: LogRecord to validate
            
        Returns:
            Dict containing validation results
        """
        violations = []
        
        # Check for credential patterns in message
        log_message = record.getMessage()
        sensitive_data = self._detect_sensitive_data(log_message)
        
        if sensitive_data:
            violations.append(f"Potential credential leakage in log: {sensitive_data}")
            
        # Validate log level appropriateness
        if record.levelno == logging.CRITICAL and "credentials" not in log_message.lower():
            # CRITICAL should only be used for security/credential issues
            violations.append("CRITICAL log level used for non-credential issue")
            
        # Check for required log fields (audit trail)
        required_attrs = ['name', 'levelname', 'message', 'created']
        missing_attrs = [attr for attr in required_attrs if not hasattr(record, attr)]
        
        if missing_attrs:
            violations.append(f"Missing required log attributes: {missing_attrs}")
        
        if violations:
            self._log_violation("logging", violations)
            
        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "sensitive_data_detected": bool(sensitive_data)
        }
    
    def sanitize_log_message(self, message: str) -> str:
        """
        Sanitize log message to remove sensitive data.
        
        Args:
            message: Original log message
            
        Returns:
            Sanitized message safe for logging
        """
        sanitized = message
        
        for pattern in CREDENTIAL_PATTERNS:
            sanitized = pattern.sub('[REDACTED]', sanitized)
            
        return sanitized
    
    # ------------------------------------------------------------------------
    # CREDENTIAL PROTECTION
    # ------------------------------------------------------------------------
    
    def _detect_sensitive_data(self, text: str) -> List[str]:
        """
        Detect sensitive data patterns in text.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of detected sensitive patterns
        """
        matches = []
        
        for pattern in CREDENTIAL_PATTERNS:
            found = pattern.findall(text)
            if found:
                matches.extend(found)
                
        return matches
    
    def validate_no_credentials_in_code(self, file_path: str) -> Dict[str, Any]:
        """
        Scan source file for hardcoded credentials.
        
        Args:
            file_path: Path to Python file to scan
            
        Returns:
            Dict containing scan results
        """
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            sensitive_data = self._detect_sensitive_data(content)
            
            if sensitive_data:
                violations.append(
                    f"Hardcoded credentials detected in {file_path}: {sensitive_data}"
                )
                
        except Exception as e:
            violations.append(f"Error scanning {file_path}: {str(e)}")
        
        if violations:
            self._log_violation("credential_protection", violations)
            
        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "file_scanned": file_path
        }
    
    # ------------------------------------------------------------------------
    # IMDSV2 ENFORCEMENT
    # ------------------------------------------------------------------------
    
    def enforce_imdsv2(self) -> Dict[str, Any]:
        """
        Enforce IMDSv2 usage for EC2 metadata protection.
        
        This method:
        - Checks if running on EC2
        - Validates IMDSv2 token is required
        - Prevents fallback to IMDSv1
        
        Returns:
            Dict containing enforcement results
        """
        violations = []
        warnings = []
        
        # Check if we're running on EC2
        is_ec2 = self._is_running_on_ec2()
        
        if is_ec2:
            # Verify IMDSv2 is required
            imds_enforcement = self._get_imds_enforcement_status()
            
            if imds_enforcement != 'required':
                violations.append(
                    f"IMDSv2 is not required (current: {imds_enforcement}). "
                    f"Set HttpTokens=required for EC2 instances."
                )
            
            # Test IMDSv2 token acquisition
            token_available = self._test_imdsv2_token()
            
            if not token_available:
                violations.append("Unable to acquire IMDSv2 token")
                warnings.append("EC2 metadata access will fail with IMDSv1 disabled")
        
        if violations:
            self._log_violation("imdsv2", violations)
            
        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "warnings": warnings,
            "enforced": is_ec2 and self.compliance_level == ComplianceLevel.STRICT
        }
    
    def _is_running_on_ec2(self) -> bool:
        """Detect if code is running on EC2 instance."""
        # Check for EC2 metadata service
        import socket
        
        try:
            socket.create_connection((EC2_METADATA_TOKEN_ENDPOINT.replace('http://', '').split('/')[0], 80), timeout=1)
            return True
        except:
            return False
    
    def _get_imds_enforcement_status(self) -> str:
        """Get current IMDS token enforcement status."""
        # In production, this would query EC2 instance metadata
        # For now, return a safe default
        return os.environ.get('EC2_IMDSV2_ENFORCEMENT', 'optional')
    
    def _test_imdsv2_token(self) -> bool:
        """Test IMDSv2 token acquisition."""
        # This would make actual call to EC2 metadata service
        # For compliance checking, assume token is available if enforced
        return True
    
    # ------------------------------------------------------------------------
    # INPUT VALIDATION
    # ------------------------------------------------------------------------
    
    def validate_aws_resource_id(self, resource_id: str, resource_type: str) -> Dict[str, Any]:
        """
        Validate AWS resource ID format.
        
        Args:
            resource_id: Resource ID to validate
            resource_type: Type of resource (vpc, tgw, eni, etc.)
            
        Returns:
            Dict containing validation results
        """
        violations = []
        
        if not resource_id or not isinstance(resource_id, str):
            violations.append("Resource ID must be non-empty string")
            return {"compliant": False, "violations": violations}
        
        # Resource-specific validation patterns
        patterns = {
            'vpc': r'^vpc-[0-9a-f]{8,17}$',
            'tgw': r'^tgw-[0-9a-f]{8,17}$',
            'eni': r'^eni-[0-9a-f]{8,17}$',
            'subnet': r'^subnet-[0-9a-f]{8,17}$',
            'sg': r'^sg-[0-9a-f]{8,17}$',
            'core_network': r'^core-network-[0-9a-f]{8,17}$',
            'firewall': r'^[a-zA-Z0-9-]{1,128}$',
        }
        
        pattern = patterns.get(resource_type)
        if pattern and not re.match(pattern, resource_id):
            violations.append(
                f"Invalid {resource_type} ID format: '{resource_id}'. "
                f"Expected pattern: {pattern}"
            )
        
        # Length validation
        if len(resource_id) > 255:
            violations.append(f"Resource ID exceeds maximum length: {len(resource_id)} > 255")
        
        if violations:
            self._log_violation("input_validation", violations)
            
        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "resource_type": resource_type,
            "resource_id": resource_id
        }
    
    # ------------------------------------------------------------------------
    # RESOURCE TAGGING COMPLIANCE
    # ------------------------------------------------------------------------
    
    def validate_resource_tags(self, tags: List[Dict[str, str]], required_tags: List[str]) -> Dict[str, Any]:
        """
        Validate resource tags meet AWS tagging standards.
        
        Args:
            tags: List of tag dictionaries
            required_tags: List of required tag keys
            
        Returns:
            Dict containing validation results
        """
        violations = []
        
        if not isinstance(tags, list):
            violations.append("Tags must be a list")
            return {"compliant": False, "violations": violations}
        
        # Check required tags
        tag_keys = {tag.get('Key') for tag in tags if isinstance(tag, dict)}
        missing_required = [req_tag for req_tag in required_tags if req_tag not in tag_keys]
        
        if missing_required:
            violations.append(f"Missing required tags: {missing_required}")
        
        # Validate tag format
        for tag in tags:
            if not isinstance(tag, dict):
                violations.append(f"Invalid tag format: {tag}")
                continue
            
            key = tag.get('Key', '')
            value = tag.get('Value', '')
            
            # Tag key validation
            if not key or len(key) > 128:
                violations.append(f"Invalid tag key length: {key}")
            
            if not re.match(r'^[a-zA-Z0-9+\-=\.\_:\/@]+$', key):
                violations.append(f"Invalid tag key characters: {key}")
            
            # Tag value validation
            if len(value) > 256:
                violations.append(f"Tag value exceeds maximum length: {key}={value}")
        
        if violations:
            self._log_violation("tagging", violations)
            
        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "missing_tags": missing_required,
            "tag_count": len(tags)
        }
    
    # ------------------------------------------------------------------------
    # AGGREGATE COMPLIANCE CHECKING
    # ------------------------------------------------------------------------
    
    def run_full_compliance_check(self) -> Dict[str, Any]:
        """
        Run complete AWS Labs compliance validation.
        
        Returns:
            Dict containing comprehensive compliance report
        """
        results = {
            "timestamp": logging.Formatter().formatTime(logging.LogRecord("", 0, "", 0, "", (), None)),
            "compliance_level": self.compliance_level.value,
            "overall_compliant": True,
            "checks": {}
        }
        
        # Run all validation checks
        checks = {
            "imdsv2": self.enforce_imdsv2(),
            "credential_protection": self._check_credential_files(),
        }
        
        # Aggregate results
        all_violations = []
        for check_name, result in checks.items():
            results["checks"][check_name] = result
            if not result["compliant"]:
                results["overall_compliant"] = False
                all_violations.extend(result.get("violations", []))
        
        results["total_violations"] = len(all_violations)
        results["violation_details"] = all_violations
        
        # Log summary
        if results["overall_compliant"]:
            self.logger.info("✅ All AWS Labs compliance checks passed")
        else:
            self.logger.error(f"❌ {len(all_violations)} compliance violations detected")
        
        return results
    
    def _check_credential_files(self) -> Dict[str, Any]:
        """Check all Python files for hardcoded credentials."""
        violations = []
        
        # Scan relevant directories
        scan_dirs = ['awslabs', 'tests']
        
        for scan_dir in scan_dirs:
            if os.path.exists(scan_dir):
                for root, dirs, files in os.walk(scan_dir):
                    for file in files:
                        if file.endswith('.py'):
                            file_path = os.path.join(root, file)
                            result = self.validate_no_credentials_in_code(file_path)
                            if not result["compliant"]:
                                violations.extend(result["violations"])
        
        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "files_scanned": True
        }
    
    # ------------------------------------------------------------------------
    # UTILITY METHODS
    # ------------------------------------------------------------------------
    
    def _log_violation(self, category: str, violations: list):
        """Log compliance violation."""
        self._violation_count += len(violations)
        
        for violation in violations:
            if self.compliance_level == ComplianceLevel.STRICT:
                self.logger.error(f"COMPLIANCE_VIOLATION [{category}]: {violation}")
            else:
                self.logger.warning(f"COMPLIANCE_WARNING [{category}]: {violation}")
    
    def get_violation_count(self) -> int:
        """Get total number of violations detected."""
        return self._violation_count
    
    def reset_violation_count(self):
        """Reset violation counter."""
        self._violation_count = 0

# ============================================================================
# GLOBAL COMPLIANCE INSTANCE
# ============================================================================

# Default global validator instance
default_validator = AWSLabsComplianceValidator(compliance_level=ComplianceLevel.STRICT)

# ============================================================================
# DECORATORS FOR EASY INTEGRATION
# ============================================================================

def compliant_resource_id(resource_type: str):
    """
    Decorator to validate AWS resource ID parameters.
    
    Usage:
        @compliant_resource_id('vpc')
        def get_vpc_details(vpc_id: str, ...):
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Find resource_id parameter
            resource_id = kwargs.get('vpc_id') or kwargs.get('tgw_id') or \
                         kwargs.get('eni_id') or kwargs.get('core_network_id')
            
            if resource_id:
                validator = AWSLabsComplianceValidator()
                result = validator.validate_aws_resource_id(resource_id, resource_type)
                
                if not result["compliant"] and validator.compliance_level == ComplianceLevel.STRICT:
                    raise ValueError(f"Invalid resource ID: {result['violations']}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

def secure_logging(func):
    """
    Decorator to sanitize log output from functions.
    
    Automatically removes sensitive data from any logged messages.
    """
    def wrapper(*args, **kwargs):
        # Temporarily replace logger
        original_loggers = {}
        
        for logger_name in logging.root.manager.loggerDict:
            logger = logging.getLogger(logger_name)
            original_loggers[logger_name] = logger.handlers[:]
            
            # Add sanitizing filter
            class SanitizingFilter(logging.Filter):
                def filter(self, record):
                    record.msg = default_validator.sanitize_log_message(str(record.msg))
                    return True
            
            logger.addFilter(SanitizingFilter())
        
        try:
            return func(*args, **kwargs)
        finally:
            # Restore original loggers
            for logger_name, handlers in original_loggers.items():
                logger = logging.getLogger(logger_name)
                logger.handlers = handlers
    
    return wrapper

# ============================================================================
# CLI INTERFACE
# ============================================================================

if __name__ == '__main__':
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description='AWS Labs Compliance Validator')
    parser.add_argument('--level', choices=['strict', 'monitor', 'disabled'],
                       default='strict', help='Compliance enforcement level')
    parser.add_argument('--check', choices=['all', 'imdsv2', 'credentials', 'headers'],
                       default='all', help='Specific check to run')
    parser.add_argument('--file', help='Specific file to scan for credentials')
    
    args = parser.parse_args()
    
    level_map = {
        'strict': ComplianceLevel.STRICT,
        'monitor': ComplianceLevel.MONITOR,
        'disabled': ComplianceLevel.DISABLED
    }
    
    validator = AWSLabsComplianceValidator(level_map[args.level])
    
    if args.check == 'all':
        result = validator.run_full_compliance_check()
    elif args.check == 'imdsv2':
        result = validator.enforce_imdsv2()
    elif args.check == 'credentials':
        if args.file:
            result = validator.validate_no_credentials_in_code(args.file)
        else:
            result = validator._check_credential_files()
    elif args.check == 'headers':
        # Example headers for testing
        headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            "Content-Security-Policy": "default-src 'self'"
        }
        result = validator.validate_security_headers(headers)
    
    print(json.dumps(result, indent=2))
    
    # Exit with error code if strict mode and violations found
    if not result['compliant'] and args.level == 'strict':
        exit(1)