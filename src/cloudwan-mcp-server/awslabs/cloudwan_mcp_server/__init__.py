"""
AWS CloudWAN MCP Server

A professional MCP (Model Context Protocol) Server providing comprehensive operational
capabilities for AWS CloudWAN environments. Built for production use with enterprise-grade
security, performance, and monitoring.

Features:
- IP Address Resolution: Complete resource discovery across AWS services
- Network Path Tracing: End-to-end path analysis with inspection point detection
- Core Network Analysis: Global Network discovery and policy analysis
- AI/ML Anomaly Detection: Machine learning-based network anomaly detection
- BGP Protocol Analysis: Comprehensive BGP state and security analysis
- Dynamic Tool Loading: Fast startup with on-demand tool loading

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
"""

__version__ = "0.0.0"
__author__ = "AWS Labs"
__description__ = "AWS CloudWAN MCP Server - Network operations, troubleshooting, and AI-powered analysis"

# Core exports with graceful fallback for missing dependencies
try:
    from .config import CloudWANConfig

    _CONFIG_AVAILABLE = True
except ImportError:
    CloudWANConfig = None
    _CONFIG_AVAILABLE = False

try:
    from .server import CloudWANMCPServer, run_server

    _SERVER_AVAILABLE = True
except ImportError:
    CloudWANMCPServer = None
    run_server = None
    _SERVER_AVAILABLE = False

# Build __all__ list dynamically based on what's available
__all__ = ["__version__", "__author__", "__description__"]

if _CONFIG_AVAILABLE and CloudWANConfig:
    __all__.extend(["CloudWANConfig"])

if _SERVER_AVAILABLE:
    if CloudWANMCPServer:
        __all__.append("CloudWANMCPServer")
    if run_server:
        __all__.append("run_server")
