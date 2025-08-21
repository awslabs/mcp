#!/usr/bin/env python

from setuptools import find_namespace_packages, setup

if __name__ == "__main__":
    setup(
        name="awslabs-aws-iot-sitewise-mcp-server",
        version="0.1.0",
        description="An AWS Labs Model Context Protocol (MCP) server for "
        "AWS IoT SiteWise API integration",
        packages=find_namespace_packages(include=["awslabs.*"]),
        entry_points={
            "console_scripts": [
                "awslabs-aws-iot-sitewise-mcp-server="
                "awslabs.aws_iot_sitewise_mcp_server.server:main",
            ],
        },
    )
