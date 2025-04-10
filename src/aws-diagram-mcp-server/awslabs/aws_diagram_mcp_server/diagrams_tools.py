"""Diagram generation and example functions for the diagrams-mcp-server."""

import diagrams
import importlib
import inspect
import logging
import os
import re
import signal
import uuid
from awslabs.aws_diagram_mcp_server.models import (
    DiagramExampleResponse,
    DiagramGenerateResponse,
    DiagramIconsResponse,
    DiagramType,
)
from awslabs.aws_diagram_mcp_server.scanner import scan_python_code
from typing import Optional


logger = logging.getLogger(__name__)


async def generate_diagram(
    code: str,
    filename: Optional[str] = None,
    timeout: int = 90,
    workspace_dir: Optional[str] = None,
) -> DiagramGenerateResponse:
    """Generate a diagram from Python code using the `diagrams` package.

    You should use the `get_diagram_examples` tool first to get examples of how to use the `diagrams` package.

    This function accepts Python code as a string that uses the diagrams package DSL
    and generates a PNG diagram without displaying it. The code is executed with
    show=False to prevent automatic display.

    Supported diagram types:
    - AWS architecture diagrams
    - Sequence diagrams
    - Flow diagrams
    - Class diagrams
    - Kubernetes diagrams
    - On-premises diagrams
    - Custom diagrams with custom nodes

    Args:
        code: Python code string using the diagrams package DSL
        filename: Output filename (without extension). If not provided, a random name will be generated.
        timeout: Timeout in seconds for diagram generation
        workspace_dir: The user's current workspace directory. If provided, diagrams will be saved to a "generated-diagrams" subdirectory.

    Returns:
        DiagramGenerateResponse: Response with the path to the generated diagram and status
    """
    # Scan the code for security issues
    scan_result = await scan_python_code(code)
    if scan_result.has_errors:
        return DiagramGenerateResponse(
            status='error',
            message=f'Security issues found in the code: {scan_result.error_message}',
        )

    if filename is None:
        filename = f'diagram_{uuid.uuid4().hex[:8]}'

    # Determine the output path
    if os.path.isabs(filename):
        # If it's an absolute path, use it directly
        output_path = filename
    else:
        # For non-absolute paths, use the "generated-diagrams" subdirectory

        # Strip any path components to ensure it's just a filename
        # (for relative paths with directories like "path/to/diagram.png")
        simple_filename = os.path.basename(filename)

        if workspace_dir and os.path.isdir(workspace_dir) and os.access(workspace_dir, os.W_OK):
            # Create a "generated-diagrams" subdirectory in the workspace
            output_dir = os.path.join(workspace_dir, 'generated-diagrams')
        else:
            # Fall back to a secure temporary directory if workspace_dir isn't provided or isn't writable
            import tempfile

            temp_base = tempfile.gettempdir()
            output_dir = os.path.join(temp_base, 'generated-diagrams')

        # Create the output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Combine directory and filename
        output_path = os.path.join(output_dir, simple_filename)

    try:
        # Create a namespace for execution
        namespace = {}

        # Import necessary modules directly in the namespace
        # nosec B102 - These exec calls are necessary to import modules in the namespace
        exec('import os', namespace)  # nosec
        exec('import diagrams', namespace)  # nosec
        exec('from diagrams import Diagram, Cluster, Edge', namespace)  # nosec
        exec(  # nosec B102 - This exec is necessary to import all diagram modules
            """from diagrams.saas.crm import *
from diagrams.saas.identity import *
from diagrams.saas.chat import *
from diagrams.saas.recommendation import *
from diagrams.saas.cdn import *
from diagrams.saas.communication import *
from diagrams.saas.media import *
from diagrams.saas.logging import *
from diagrams.saas.security import *
from diagrams.saas.social import *
from diagrams.saas.alerting import *
from diagrams.saas.analytics import *
from diagrams.saas.automation import *
from diagrams.saas.filesharing import *
from diagrams.onprem.vcs import *
from diagrams.onprem.database import *
from diagrams.onprem.gitops import *
from diagrams.onprem.workflow import *
from diagrams.onprem.etl import *
from diagrams.onprem.inmemory import *
from diagrams.onprem.identity import *
from diagrams.onprem.network import *
from diagrams.onprem.proxmox import *
from diagrams.onprem.cd import *
from diagrams.onprem.container import *
from diagrams.onprem.certificates import *
from diagrams.onprem.mlops import *
from diagrams.onprem.dns import *
from diagrams.onprem.compute import *
from diagrams.onprem.logging import *
from diagrams.onprem.registry import *
from diagrams.onprem.security import *
from diagrams.onprem.client import *
from diagrams.onprem.groupware import *
from diagrams.onprem.iac import *
from diagrams.onprem.analytics import *
from diagrams.onprem.messaging import *
from diagrams.onprem.tracing import *
from diagrams.onprem.ci import *
from diagrams.onprem.search import *
from diagrams.onprem.storage import *
from diagrams.onprem.auth import *
from diagrams.onprem.monitoring import *
from diagrams.onprem.aggregator import *
from diagrams.onprem.queue import *
from diagrams.gis.database import *
from diagrams.gis.cli import *
from diagrams.gis.server import *
from diagrams.gis.python import *
from diagrams.gis.organization import *
from diagrams.gis.cplusplus import *
from diagrams.gis.mobile import *
from diagrams.gis.javascript import *
from diagrams.gis.desktop import *
from diagrams.gis.ogc import *
from diagrams.gis.java import *
from diagrams.gis.routing import *
from diagrams.gis.data import *
from diagrams.gis.geocoding import *
from diagrams.gis.format import *
from diagrams.elastic.saas import *
from diagrams.elastic.observability import *
from diagrams.elastic.elasticsearch import *
from diagrams.elastic.orchestration import *
from diagrams.elastic.security import *
from diagrams.elastic.beats import *
from diagrams.elastic.enterprisesearch import *
from diagrams.elastic.agent import *
from diagrams.programming.runtime import *
from diagrams.programming.framework import *
from diagrams.programming.flowchart import *
from diagrams.programming.language import *
from diagrams.gcp.storage import *
from diagrams.generic.database import *
from diagrams.generic.blank import *
from diagrams.generic.network import *
from diagrams.generic.virtualization import *
from diagrams.generic.place import *
from diagrams.generic.device import *
from diagrams.generic.compute import *
from diagrams.generic.os import *
from diagrams.generic.storage import *
from diagrams.k8s.others import *
from diagrams.k8s.rbac import *
from diagrams.k8s.network import *
from diagrams.k8s.ecosystem import *
from diagrams.k8s.compute import *
from diagrams.k8s.chaos import *
from diagrams.k8s.infra import *
from diagrams.k8s.podconfig import *
from diagrams.k8s.controlplane import *
from diagrams.k8s.clusterconfig import *
from diagrams.k8s.storage import *
from diagrams.k8s.group import *
from diagrams.aws.cost import *
from diagrams.aws.ar import *
from diagrams.aws.general import *
from diagrams.aws.database import *
from diagrams.aws.management import *
from diagrams.aws.ml import *
from diagrams.aws.game import *
from diagrams.aws.enablement import *
from diagrams.aws.network import *
from diagrams.aws.quantum import *
from diagrams.aws.iot import *
from diagrams.aws.robotics import *
from diagrams.aws.migration import *
from diagrams.aws.mobile import *
from diagrams.aws.compute import *
from diagrams.aws.media import *
from diagrams.aws.engagement import *
from diagrams.aws.security import *
from diagrams.aws.devtools import *
from diagrams.aws.integration import *
from diagrams.aws.business import *
from diagrams.aws.analytics import *
from diagrams.aws.blockchain import *
from diagrams.aws.storage import *
from diagrams.aws.satellite import *
from diagrams.aws.enduser import *
""",
            namespace,
        )
        exec('from urllib.request import urlretrieve', namespace)  # nosec

        # Process the code to ensure show=False and set the output path
        if 'with Diagram(' in code:
            # Find all instances of Diagram constructor
            diagram_pattern = r'with\s+Diagram\s*\((.*?)\)'
            matches = re.findall(diagram_pattern, code)

            for match in matches:
                # Get the original arguments
                original_args = match.strip()

                # Check if show parameter is already set
                has_show = 'show=' in original_args
                has_filename = 'filename=' in original_args

                # Prepare new arguments
                new_args = original_args

                # Add or replace parameters as needed
                # If filename is already set, we need to replace it with our output_path
                if has_filename:
                    # Replace the existing filename parameter
                    filename_pattern = r'filename\s*=\s*[\'"]([^\'"]*)[\'"]'
                    new_args = re.sub(filename_pattern, f"filename='{output_path}'", new_args)
                else:
                    # Add the filename parameter
                    if new_args and not new_args.endswith(','):
                        new_args += ', '
                    new_args += f"filename='{output_path}'"

                # Add show=False if not already set
                if not has_show:
                    if new_args and not new_args.endswith(','):
                        new_args += ', '
                    new_args += 'show=False'

                # Replace in the code
                code = code.replace(f'with Diagram({original_args})', f'with Diagram({new_args})')

        # Set up a timeout handler
        def timeout_handler(signum, frame):
            raise TimeoutError(f'Diagram generation timed out after {timeout} seconds')

        # Register the timeout handler
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)

        # Execute the code
        # nosec B102 - This exec is necessary to run user-provided diagram code in a controlled environment
        exec(code, namespace)  # nosec

        # Cancel the alarm
        signal.alarm(0)

        # Check if the file was created
        png_path = f'{output_path}.png'
        if os.path.exists(png_path):
            response = DiagramGenerateResponse(
                status='success',
                path=png_path,
                message=f'Diagram generated successfully at {png_path}',
            )

            return response
        else:
            return DiagramGenerateResponse(
                status='error',
                message='Diagram file was not created. Check your code for errors.',
            )
    except TimeoutError as e:
        return DiagramGenerateResponse(status='error', message=str(e))
    except Exception as e:
        # More detailed error logging
        error_type = type(e).__name__
        error_message = str(e)
        return DiagramGenerateResponse(
            status='error', message=f'Error generating diagram: {error_type}: {error_message}'
        )


def get_diagram_examples(diagram_type: DiagramType = DiagramType.ALL) -> DiagramExampleResponse:
    """Get example code for different types of diagrams.

    Args:
        diagram_type: Type of diagram example to return.

    Returns:
        DiagramExampleResponse: Dictionary with example code for the requested diagram type(s)
    """
    examples = {}

    # Basic examples
    if diagram_type in [DiagramType.AWS, DiagramType.ALL]:
        examples['aws_basic'] = """with Diagram("Web Service Architecture", show=False):
    ELB("lb") >> EC2("web") >> RDS("userdb")
"""

    if diagram_type in [DiagramType.SEQUENCE, DiagramType.ALL]:
        examples['sequence'] = """with Diagram("User Authentication Flow", show=False):
    user = User("User")
    login = InputOutput("Login Form")
    auth = Decision("Authenticated?")
    success = Action("Access Granted")
    failure = Action("Access Denied")

    user >> login >> auth
    auth >> success
    auth >> failure
"""

    if diagram_type in [DiagramType.FLOW, DiagramType.ALL]:
        examples['flow'] = """with Diagram("Order Processing Flow", show=False):
    start = Predefined("Start")
    order = InputOutput("Order Received")
    check = Decision("In Stock?")
    process = Action("Process Order")
    wait = Delay("Backorder")
    ship = Action("Ship Order")
    end = Predefined("End")

    start >> order >> check
    check >> process >> ship >> end
    check >> wait >> process
"""

    if diagram_type in [DiagramType.CLASS, DiagramType.ALL]:
        examples['class'] = """with Diagram("Simple Class Diagram", show=False):
    base = Python("BaseClass")
    child1 = Python("ChildClass1")
    child2 = Python("ChildClass2")

    base >> child1
    base >> child2
"""

    # Advanced examples from the documentation
    if diagram_type in [DiagramType.AWS, DiagramType.ALL]:
        examples[
            'aws_grouped_workers'
        ] = """with Diagram("Grouped Workers", show=False, direction="TB"):
    ELB("lb") >> [EC2("worker1"),
                  EC2("worker2"),
                  EC2("worker3"),
                  EC2("worker4"),
                  EC2("worker5")] >> RDS("events")
"""

        examples[
            'aws_clustered_web_services'
        ] = """with Diagram("Clustered Web Services", show=False):
    dns = Route53("dns")
    lb = ELB("lb")

    with Cluster("Services"):
        svc_group = [ECS("web1"),
                     ECS("web2"),
                     ECS("web3")]

    with Cluster("DB Cluster"):
        db_primary = RDS("userdb")
        db_primary - [RDS("userdb ro")]

    memcached = ElastiCache("memcached")

    dns >> lb >> svc_group
    svc_group >> db_primary
    svc_group >> memcached
"""

        examples['aws_event_processing'] = """with Diagram("Event Processing", show=False):
    source = EKS("k8s source")

    with Cluster("Event Flows"):
        with Cluster("Event Workers"):
            workers = [ECS("worker1"),
                       ECS("worker2"),
                       ECS("worker3")]

        queue = SQS("event queue")

        with Cluster("Processing"):
            handlers = [Lambda("proc1"),
                        Lambda("proc2"),
                        Lambda("proc3")]

    store = S3("events store")
    dw = Redshift("analytics")

    source >> workers >> queue >> handlers
    handlers >> store
    handlers >> dw
"""

        examples[
            'aws_bedrock'
        ] = """with Diagram("S3 Image Processing with Bedrock", show=False, direction="LR"):
    user = User("User")

    with Cluster("Amazon S3 Bucket"):
        input_folder = S3("Input Folder")
        output_folder = S3("Output Folder")

    lambda_function = Lambda("Image Processor Function")
    bedrock = Bedrock("Claude Sonnet 3.7")

    user >> Edge(label="Upload Image") >> input_folder
    input_folder >> Edge(label="Trigger") >> lambda_function
    lambda_function >> Edge(label="Process Image") >> bedrock
    bedrock >> Edge(label="Return Bounding Box") >> lambda_function
    lambda_function >> Edge(label="Upload Processed Image") >> output_folder
    output_folder >> Edge(label="Download Result") >> user
"""

    if diagram_type in [DiagramType.K8S, DiagramType.ALL]:
        examples['k8s_exposed_pod'] = """with Diagram("Exposed Pod with 3 Replicas", show=False):
    net = Ingress("domain.com") >> Service("svc")
    net >> [Pod("pod1"),
            Pod("pod2"),
            Pod("pod3")] << ReplicaSet("rs") << Deployment("dp") << HPA("hpa")
"""

        examples['k8s_stateful'] = """with Diagram("Stateful Architecture", show=False):
    with Cluster("Apps"):
        svc = Service("svc")
        sts = StatefulSet("sts")

        apps = []
        for _ in range(3):
            pod = Pod("pod")
            pvc = PVC("pvc")
            pod - sts - pvc
            apps.append(svc >> pod >> pvc)

    apps << PV("pv") << StorageClass("sc")
"""

    if diagram_type in [DiagramType.ONPREM, DiagramType.ALL]:
        examples[
            'onprem_web_service'
        ] = """with Diagram("Advanced Web Service with On-Premises", show=False):
    ingress = Nginx("ingress")

    metrics = Prometheus("metric")
    metrics << Grafana("monitoring")

    with Cluster("Service Cluster"):
        grpcsvc = [
            Server("grpc1"),
            Server("grpc2"),
            Server("grpc3")]

    with Cluster("Sessions HA"):
        primary = Redis("session")
        primary - Redis("replica") << metrics
        grpcsvc >> primary

    with Cluster("Database HA"):
        primary = PostgreSQL("users")
        primary - PostgreSQL("replica") << metrics
        grpcsvc >> primary

    aggregator = Fluentd("logging")
    aggregator >> Kafka("stream") >> Spark("analytics")

    ingress >> grpcsvc >> aggregator
"""

        examples[
            'onprem_web_service_colored'
        ] = """with Diagram(name="Advanced Web Service with On-Premise (colored)", show=False):
    ingress = Nginx("ingress")

    metrics = Prometheus("metric")
    metrics << Edge(color="firebrick", style="dashed") << Grafana("monitoring")

    with Cluster("Service Cluster"):
        grpcsvc = [
            Server("grpc1"),
            Server("grpc2"),
            Server("grpc3")]

    with Cluster("Sessions HA"):
        primary = Redis("session")
        primary - Edge(color="brown", style="dashed") - Redis("replica") << Edge(label="collect") << metrics
        grpcsvc >> Edge(color="brown") >> primary

    with Cluster("Database HA"):
        primary = PostgreSQL("users")
        primary - Edge(color="brown", style="dotted") - PostgreSQL("replica") << Edge(label="collect") << metrics
        grpcsvc >> Edge(color="black") >> primary

    aggregator = Fluentd("logging")
    aggregator >> Edge(label="parse") >> Kafka("stream") >> Edge(color="black", style="bold") >> Spark("analytics")

    ingress >> Edge(color="darkgreen") << grpcsvc >> Edge(color="darkorange") >> aggregator
"""

    if diagram_type in [DiagramType.CUSTOM, DiagramType.ALL]:
        examples['custom_rabbitmq'] = """# Download an image to be used into a Custom Node class
rabbitmq_url = "https://jpadilla.github.io/rabbitmqapp/assets/img/icon.png"
rabbitmq_icon = "rabbitmq.png"
urlretrieve(rabbitmq_url, rabbitmq_icon)

with Diagram("Broker Consumers", show=False):
    with Cluster("Consumers"):
        consumers = [
            Pod("worker"),
            Pod("worker"),
            Pod("worker")]

    queue = Custom("Message queue", rabbitmq_icon)

    queue >> consumers >> Aurora("Database")
"""

    return DiagramExampleResponse(examples=examples)


def list_diagram_icons() -> DiagramIconsResponse:
    """List all available icons from the diagrams package.

    This function dynamically inspects the diagrams package to find all available
    providers, services, and icons that can be used in diagrams.

    Returns:
        DiagramIconsResponse: Dictionary with all available providers, services, and icons
    """
    logger.debug('Starting list_diagram_icons function')

    try:
        # Dictionary to store all providers and their services/icons
        providers = {}

        # Get the base path of the diagrams package
        diagrams_path = os.path.dirname(diagrams.__file__)
        logger.debug(f'Diagrams package path: {diagrams_path}')

        # List of provider directories to exclude
        exclude_dirs = ['__pycache__', '_template']

        # Iterate through all provider directories
        for provider_name in os.listdir(os.path.join(diagrams_path)):
            provider_path = os.path.join(diagrams_path, provider_name)

            # Skip non-directories and excluded directories
            if (
                not os.path.isdir(provider_path)
                or provider_name.startswith('_')
                or provider_name in exclude_dirs
            ):
                logger.debug(f'Skipping {provider_name}: not a directory or in exclude list')
                continue

            # Add provider to the dictionary
            providers[provider_name] = {}
            logger.debug(f'Processing provider: {provider_name}')

            # Iterate through all service modules in the provider
            for service_file in os.listdir(provider_path):
                # Skip non-Python files and special files
                if not service_file.endswith('.py') or service_file.startswith('_'):
                    logger.debug(
                        f'Skipping file {service_file}: not a Python file or starts with _'
                    )
                    continue

                service_name = service_file[:-3]  # Remove .py extension
                logger.debug(f'Processing service: {provider_name}.{service_name}')

                # Import the service module
                module_path = f'diagrams.{provider_name}.{service_name}'
                try:
                    logger.debug(f'Attempting to import module: {module_path}')
                    service_module = importlib.import_module(module_path)

                    # Find all classes in the module that are Node subclasses
                    icons = []
                    for name, obj in inspect.getmembers(service_module):
                        # Skip private members and imported modules
                        if name.startswith('_') or inspect.ismodule(obj):
                            continue

                        # Check if it's a class and likely a Node subclass
                        if inspect.isclass(obj) and hasattr(obj, '_icon'):
                            icons.append(name)
                            logger.debug(f'Found icon: {name}')

                    # Add service and its icons to the provider
                    if icons:
                        providers[provider_name][service_name] = sorted(icons)
                        logger.debug(
                            f'Added {len(icons)} icons for {provider_name}.{service_name}'
                        )
                    else:
                        logger.warning(f'No icons found for {provider_name}.{service_name}')

                except ImportError as ie:
                    logger.error(f'ImportError for {module_path}: {str(ie)}')
                    continue
                except AttributeError as ae:
                    logger.error(f'AttributeError for {module_path}: {str(ae)}')
                    continue
                except Exception as e:
                    logger.error(f'Unexpected error processing {module_path}: {str(e)}')
                    continue

        logger.debug(f'Completed processing. Found {len(providers)} providers')
        return DiagramIconsResponse(providers=providers)
    except Exception as e:
        logger.exception(f'Error in list_diagram_icons: {str(e)}')
        # Return empty response on error
        return DiagramIconsResponse(providers={})
