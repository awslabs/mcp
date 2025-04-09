"""Example script to demonstrate the functionality of the diagrams-mcp-server.

This script creates a simple AWS diagram using the diagrams package.
"""

from diagrams import Diagram
from diagrams.aws.compute import EC2
from diagrams.aws.database import RDS
from diagrams.aws.network import ELB


# Create a simple AWS diagram
with Diagram('Web Service Architecture', show=True, outformat='png', filename='example_diagram'):
    ELB('lb') >> EC2('web') >> RDS('userdb')

print('Diagram generated successfully!')
