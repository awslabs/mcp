from setuptools import find_namespace_packages, setup


setup(
    name='aws-diagram-mcp-server',
    version='0.8.0',
    packages=find_namespace_packages(include=['awslabs.*']),
)
