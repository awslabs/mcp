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

"""Factory pattern for Infrastructure-as-Code parser selection."""

import re
from typing import Protocol, Dict, Type, Optional, Any
from abc import ABC, abstractmethod

from ..utils.logger import get_logger

logger = get_logger(__name__)


class IaCParser(Protocol):
    """Protocol for Infrastructure-as-Code parsers."""

    @abstractmethod
    def parse_content(self, content: str) -> Any:
        """Parse IaC content into unified model."""
        ...

    @abstractmethod
    def validate_syntax(self, content: str) -> Dict[str, Any]:
        """Validate IaC content syntax and structure."""
        ...

    @abstractmethod
    def detect_format(self, content: str) -> bool:
        """Detect if content matches this parser's format."""
        ...

    @abstractmethod
    def get_format_name(self) -> str:
        """Get the format name this parser handles."""
        ...


class TerraformParserWrapper:
    """Wrapper for Terraform parser to match IaCParser protocol."""

    def __init__(self, terraform_parser):
        self._parser = terraform_parser

    def parse_content(self, content: str) -> Any:
        return self._parser.parse_terraform_file(content)

    def validate_syntax(self, content: str) -> Dict[str, Any]:
        try:
            self._parser.parse_terraform_file(content)
            return {"valid": True, "format": "terraform", "resource_count": content.count("resource")}
        except Exception as e:
            return {"valid": False, "format": "terraform", "errors": [str(e)]}

    def detect_format(self, content: str) -> bool:
        """Detect Terraform format by looking for HCL syntax."""
        if not content.strip():
            return False

        terraform_patterns = [
            r'resource\s+"aws_networkfirewall_',
            r'provider\s+"aws"',
            r'variable\s+"[^"]+"\s*{',
            r"locals\s*{",
            r'data\s+"aws_',
        ]

        return any(re.search(pattern, content, re.IGNORECASE) for pattern in terraform_patterns)

    def get_format_name(self) -> str:
        return "terraform"


class CdkParserWrapper:
    """Wrapper for CDK parser to match IaCParser protocol."""

    def __init__(self, cdk_parser):
        self._parser = cdk_parser

    def parse_content(self, content: str) -> Any:
        return self._parser.parse_cdk_file(content)

    def validate_syntax(self, content: str) -> Dict[str, Any]:
        try:
            self._parser.parse_cdk_file(content)
            return {"valid": True, "format": "cdk", "resource_count": content.count("CfnFirewall")}
        except Exception as e:
            return {"valid": False, "format": "cdk", "errors": [str(e)]}

    def detect_format(self, content: str) -> bool:
        """Detect CDK format by looking for TypeScript AWS CDK patterns."""
        if not content.strip():
            return False

        cdk_patterns = [
            r"import.*@aws-cdk",
            r"CfnFirewallPolicy|CfnRuleGroup",
            r"new\s+nf\.Cfn",
            r'from\s+"@aws-cdk/aws-networkfirewall"',
            r"Construct",
            r"export\s+(function|class).*FirewallPolicy",
        ]

        return any(re.search(pattern, content, re.IGNORECASE) for pattern in cdk_patterns)

    def get_format_name(self) -> str:
        return "cdk"


class CloudFormationParserWrapper:
    """Wrapper for CloudFormation parser to match IaCParser protocol."""

    def __init__(self, cf_parser):
        self._parser = cf_parser

    def parse_content(self, content: str) -> Any:
        return self._parser.parse_cloudformation_template(content)

    def validate_syntax(self, content: str) -> Dict[str, Any]:
        try:
            policy = self._parser.parse_cloudformation_template(content)
            return {
                "valid": True,
                "format": "cloudformation",
                "template_format": "yaml" if "AWSTemplateFormatVersion" in content else "json",
                "resource_count": content.count("AWS::NetworkFirewall::"),
            }
        except Exception as e:
            return {"valid": False, "format": "cloudformation", "errors": [str(e)]}

    def detect_format(self, content: str) -> bool:
        """Detect CloudFormation format by looking for CF syntax."""
        if not content.strip():
            return False

        cf_patterns = [
            r"AWSTemplateFormatVersion",
            r"Type:\s*AWS::NetworkFirewall::",
            r'"Type"\s*:\s*"AWS::NetworkFirewall::',
            r"Resources:\s*$",
            r'"Resources"\s*:\s*{',
            r"!GetAtt|!Ref|!Sub",
        ]

        return any(re.search(pattern, content, re.MULTILINE | re.IGNORECASE) for pattern in cf_patterns)

    def get_format_name(self) -> str:
        return "cloudformation"


class IaCParserFactory:
    """Factory for creating appropriate Infrastructure-as-Code parsers."""

    def __init__(self):
        self._parsers: Dict[str, IaCParser] = {}
        self._detection_order = ["terraform", "cdk", "cloudformation"]

    def register_parser(self, parser: IaCParser) -> None:
        """Register a parser for a specific format."""
        format_name = parser.get_format_name().lower()
        self._parsers[format_name] = parser
        logger.info(f"Registered IaC parser for format: {format_name}")

    def get_parser(self, format_name: Optional[str] = None, content: Optional[str] = None) -> IaCParser:
        """Get appropriate parser instance."""
        if format_name:
            parser = self._parsers.get(format_name.lower())
            if parser:
                logger.debug(f"Using explicit parser for format: {format_name}")
                return parser
            raise ValueError(f"No parser registered for format: {format_name}")

        if content:
            for format_name in self._detection_order:
                parser = self._parsers.get(format_name)
                if parser and parser.detect_format(content):
                    logger.info(f"Auto-detected IaC format: {format_name}")
                    return parser

            raise ValueError("Unable to auto-detect IaC format from content")

        raise ValueError("Either format_name or content must be provided")

    def list_supported_formats(self) -> list[str]:
        """List all supported IaC formats."""
        return list(self._parsers.keys())


# Global factory instance
_parser_factory: Optional[IaCParserFactory] = None


def get_parser_factory() -> IaCParserFactory:
    """Get the global parser factory instance."""
    global _parser_factory
    if _parser_factory is None:
        _parser_factory = IaCParserFactory()
        _initialize_parsers()
    return _parser_factory


def _initialize_parsers():
    """Initialize all available parsers."""
    try:
        from .network_firewall import (
            NetworkFirewallTerraformParser,
            NetworkFirewallCdkParser,
            NetworkFirewallCloudFormationParser,
        )

        factory = _parser_factory

        # Register wrapped parsers
        factory.register_parser(TerraformParserWrapper(NetworkFirewallTerraformParser()))
        factory.register_parser(CdkParserWrapper(NetworkFirewallCdkParser()))
        factory.register_parser(CloudFormationParserWrapper(NetworkFirewallCloudFormationParser()))

        logger.info("Initialized IaC parser factory with all available parsers")

    except Exception as e:
        logger.error(f"Failed to initialize IaC parsers: {str(e)}")
        raise
