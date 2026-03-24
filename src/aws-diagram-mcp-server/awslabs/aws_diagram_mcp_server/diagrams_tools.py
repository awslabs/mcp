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

"""Diagram generation and example functions for the diagrams-mcp-server."""

import diagrams
import importlib
import inspect
import json
import logging
import os
import subprocess
import uuid
from awslabs.aws_diagram_mcp_server._sandbox_runner import (
    _SAFE_BUILTINS,  # noqa: F401
    _safe_urlretrieve,  # noqa: F401
)
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
        # Execute user code in an isolated subprocess for defense-in-depth.
        # Process isolation ensures user code runs independently of the
        # MCP server process.
        import sys

        sandbox_config = json.dumps({'code': code, 'output_path': output_path})
        result = subprocess.run(  # nosec B603 - args are not user-controlled
            [
                sys.executable,
                '-m',
                'awslabs.aws_diagram_mcp_server._sandbox_runner',
            ],
            input=sandbox_config,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if result.returncode != 0 and not result.stdout.strip():
            stderr_msg = result.stderr.strip() if result.stderr else 'Unknown error'
            return DiagramGenerateResponse(
                status='error',
                message=f'Sandbox process failed: {stderr_msg}',
            )

        try:
            sandbox_result = json.loads(result.stdout)
        except json.JSONDecodeError:
            return DiagramGenerateResponse(
                status='error',
                message=f'Sandbox produced invalid output: {result.stdout[:200]}',
            )

        return DiagramGenerateResponse(
            status=sandbox_result.get('status', 'error'),
            path=sandbox_result.get('path'),
            message=sandbox_result.get('message', 'Unknown result'),
        )
    except subprocess.TimeoutExpired:
        return DiagramGenerateResponse(
            status='error',
            message=f'Diagram generation timed out after {timeout} seconds',
        )
    except Exception as e:
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
rabbitmq_icon, _ = urlretrieve(rabbitmq_url, "rabbitmq.png")

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


def list_diagram_icons(
    provider_filter: Optional[str] = None, service_filter: Optional[str] = None
) -> DiagramIconsResponse:
    """List available icons from the diagrams package, with optional filtering.

    Args:
        provider_filter: Optional filter by provider name (e.g., "aws", "gcp")
        service_filter: Optional filter by service name (e.g., "compute", "database")

    Returns:
        DiagramIconsResponse: Dictionary with available providers, services, and icons
    """
    logger.debug('Starting list_diagram_icons function')
    logger.debug(f'Filters - provider: {provider_filter}, service: {service_filter}')

    try:
        # If no filters provided, just return the list of available providers
        if not provider_filter and not service_filter:
            # Get the base path of the diagrams package
            diagrams_path = os.path.dirname(diagrams.__file__)
            providers = {}

            # List of provider directories to exclude
            exclude_dirs = ['__pycache__', '_template']

            # Just list the available providers without their services/icons
            for provider_name in os.listdir(os.path.join(diagrams_path)):
                provider_path = os.path.join(diagrams_path, provider_name)

                # Skip non-directories and excluded directories
                if (
                    not os.path.isdir(provider_path)
                    or provider_name.startswith('_')
                    or provider_name in exclude_dirs
                ):
                    continue

                # Add provider to the dictionary with empty services
                providers[provider_name] = {}

            return DiagramIconsResponse(providers=providers, filtered=False, filter_info=None)

        # Dictionary to store filtered providers and their services/icons
        providers = {}

        # Get the base path of the diagrams package
        diagrams_path = os.path.dirname(diagrams.__file__)

        # List of provider directories to exclude
        exclude_dirs = ['__pycache__', '_template']

        # If only provider filter is specified
        if provider_filter and not service_filter:
            provider_path = os.path.join(diagrams_path, provider_filter)

            # Check if the provider exists
            if not os.path.isdir(provider_path) or provider_filter in exclude_dirs:
                return DiagramIconsResponse(
                    providers={},
                    filtered=True,
                    filter_info={'provider': provider_filter, 'error': 'Provider not found'},
                )

            # Add provider to the dictionary
            providers[provider_filter] = {}

            # Iterate through all service modules in the provider
            for service_file in os.listdir(provider_path):
                # Skip non-Python files and special files
                if not service_file.endswith('.py') or service_file.startswith('_'):
                    continue

                service_name = service_file[:-3]  # Remove .py extension

                # Import the service module
                module_path = f'diagrams.{provider_filter}.{service_name}'
                try:
                    service_module = importlib.import_module(  # nosem: python.lang.security.audit.non-literal-import.non-literal-import
                        module_path  # nosem: python.lang.security.audit.non-literal-import.non-literal-import
                    )  # nosem: python.lang.security.audit.non-literal-import.non-literal-import

                    # Find all classes in the module that are Node subclasses
                    icons = []
                    for name, obj in inspect.getmembers(service_module):
                        # Skip private members and imported modules
                        if name.startswith('_') or inspect.ismodule(obj):
                            continue

                        # Check if it's a class and likely a Node subclass
                        if inspect.isclass(obj) and hasattr(obj, '_icon'):
                            icons.append(name)

                    # Add service and its icons to the provider
                    if icons:
                        providers[provider_filter][service_name] = sorted(icons)

                except (ImportError, AttributeError, Exception) as e:
                    logger.error(f'Error processing {module_path}: {str(e)}')
                    continue

            return DiagramIconsResponse(
                providers=providers, filtered=True, filter_info={'provider': provider_filter}
            )

        # If both provider and service filters are specified
        elif provider_filter and service_filter:
            provider_path = os.path.join(diagrams_path, provider_filter)

            # Check if the provider exists
            if not os.path.isdir(provider_path) or provider_filter in exclude_dirs:
                return DiagramIconsResponse(
                    providers={},
                    filtered=True,
                    filter_info={
                        'provider': provider_filter,
                        'service': service_filter,
                        'error': 'Provider not found',
                    },
                )

            # Add provider to the dictionary
            providers[provider_filter] = {}

            # Check if the service exists
            service_file = f'{service_filter}.py'
            service_path = os.path.join(provider_path, service_file)

            if not os.path.isfile(service_path):
                return DiagramIconsResponse(
                    providers={provider_filter: {}},
                    filtered=True,
                    filter_info={
                        'provider': provider_filter,
                        'service': service_filter,
                        'error': 'Service not found',
                    },
                )

            # Import the service module
            module_path = f'diagrams.{provider_filter}.{service_filter}'
            try:
                service_module = importlib.import_module(  # nosem: python.lang.security.audit.non-literal-import.non-literal-import
                    module_path  # nosem: python.lang.security.audit.non-literal-import.non-literal-import
                )  # nosem: python.lang.security.audit.non-literal-import.non-literal-import

                # Find all classes in the module that are Node subclasses
                icons = []
                for name, obj in inspect.getmembers(service_module):
                    # Skip private members and imported modules
                    if name.startswith('_') or inspect.ismodule(obj):
                        continue

                    # Check if it's a class and likely a Node subclass
                    if inspect.isclass(obj) and hasattr(obj, '_icon'):
                        icons.append(name)

                # Add service and its icons to the provider
                if icons:
                    providers[provider_filter][service_filter] = sorted(icons)

            except (ImportError, AttributeError, Exception) as e:
                logger.error(f'Error processing {module_path}: {str(e)}')
                return DiagramIconsResponse(
                    providers={provider_filter: {}},
                    filtered=True,
                    filter_info={
                        'provider': provider_filter,
                        'service': service_filter,
                        'error': f'Error loading service: {str(e)}',
                    },
                )

            return DiagramIconsResponse(
                providers=providers,
                filtered=True,
                filter_info={'provider': provider_filter, 'service': service_filter},
            )

        # If only service filter is specified (not supported)
        elif service_filter:
            return DiagramIconsResponse(
                providers={},
                filtered=True,
                filter_info={
                    'service': service_filter,
                    'error': 'Service filter requires provider filter',
                },
            )

        # Original implementation for backward compatibility
        else:
            # Dictionary to store all providers and their services/icons
            providers = {}

            # Get the base path of the diagrams package
            diagrams_path = os.path.dirname(diagrams.__file__)
            logger.debug(f'Diagrams package path: {diagrams_path}')

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
                        service_module = importlib.import_module(  # nosem: python.lang.security.audit.non-literal-import.non-literal-import
                            module_path  # nosem: python.lang.security.audit.non-literal-import.non-literal-import
                        )  # nosem: python.lang.security.audit.non-literal-import.non-literal-import

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
            return DiagramIconsResponse(providers=providers, filtered=False, filter_info=None)

    except Exception as e:
        logger.exception(f'Error in list_diagram_icons: {str(e)}')
        # Return empty response on error
        return DiagramIconsResponse(providers={}, filtered=False, filter_info={'error': str(e)})
