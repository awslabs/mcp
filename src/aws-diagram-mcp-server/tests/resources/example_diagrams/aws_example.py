"""Example AWS diagram for testing."""

from diagrams import Diagram
from diagrams.aws.compute import EC2, Lambda
from diagrams.aws.database import RDS
from diagrams.aws.network import ELB


with Diagram('AWS Example', show=False):
    lb = ELB('Load Balancer')
    web = EC2('Web Server')
    db = RDS('Database')
    fn = Lambda('Function')

    lb >> web >> db
    web >> fn
