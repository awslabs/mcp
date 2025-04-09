from setuptools import setup, find_namespace_packages

setup(
    name="aws-diagram-mcp-server",
    version="0.8.0",
    packages=find_namespace_packages(include=["awslabs.*"]),
)
