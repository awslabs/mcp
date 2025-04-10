"""Test fixtures for the diagrams-mcp-server tests."""

import pytest
import tempfile
from awslabs.aws_diagram_mcp_server.models import DiagramType
from typing import Dict, Generator


# # Set the asyncio_default_fixture_loop_scope to function
# pytest_asyncio.default_fixture_loop_scope = 'function'


@pytest.fixture
def temp_workspace_dir() -> Generator[str, None, None]:
    """Create a temporary directory for diagram output."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def aws_diagram_code() -> str:
    """Return example AWS diagram code for testing."""
    return """with Diagram("Test AWS Diagram", show=False):
    ELB("lb") >> EC2("web") >> RDS("userdb")
"""


@pytest.fixture
def sequence_diagram_code() -> str:
    """Return example sequence diagram code for testing."""
    return """with Diagram("Test Sequence Diagram", show=False):
    user = User("User")
    login = InputOutput("Login Form")
    auth = Decision("Authenticated?")
    success = Action("Access Granted")
    failure = Action("Access Denied")

    user >> login >> auth
    auth >> success
    auth >> failure
"""


@pytest.fixture
def flow_diagram_code() -> str:
    """Return example flow diagram code for testing."""
    return """with Diagram("Test Flow Diagram", show=False):
    start = StartEnd("Start")
    order = InputOutput("Order Received")
    check = Decision("In Stock?")
    process = Action("Process Order")
    wait = Delay("Backorder")
    ship = Action("Ship Order")
    end = StartEnd("End")

    start >> order >> check
    check >> process >> ship >> end
    check >> wait >> process
"""


@pytest.fixture
def invalid_diagram_code() -> str:
    """Return invalid diagram code for testing."""
    return """with Diagram("Invalid Diagram", show=False):
    # This is missing the diagram components
    # Should cause an error
"""


@pytest.fixture
def dangerous_diagram_code() -> str:
    """Return diagram code with dangerous functions for testing."""
    return """with Diagram("Dangerous Diagram", show=False):
    ELB("lb") >> EC2("web")

    # This contains a dangerous function
    exec("print('This is dangerous')")
"""


@pytest.fixture
def example_diagrams() -> Dict[str, str]:
    """Return a dictionary of example diagrams for different types."""
    return {
        DiagramType.AWS: """with Diagram("AWS Example", show=False):
    ELB("lb") >> EC2("web") >> RDS("userdb")
""",
        DiagramType.SEQUENCE: """with Diagram("Sequence Example", show=False):
    user = User("User")
    login = InputOutput("Login Form")
    auth = Decision("Authenticated?")
    user >> login >> auth
""",
        DiagramType.FLOW: """with Diagram("Flow Example", show=False):
    start = StartEnd("Start")
    process = Action("Process")
    end = StartEnd("End")
    start >> process >> end
""",
        DiagramType.CLASS: """with Diagram("Class Example", show=False):
    base = Python("BaseClass")
    child = Python("ChildClass")
    base >> child
""",
        DiagramType.K8S: """with Diagram("K8s Example", show=False):
    pod = Pod("pod")
    svc = Service("svc")
    svc >> pod
""",
        DiagramType.ONPREM: """with Diagram("OnPrem Example", show=False):
    server = Server("server")
    db = PostgreSQL("db")
    server >> db
""",
        DiagramType.CUSTOM: """# Define a custom icon
rabbitmq_url = "https://jpadilla.github.io/rabbitmqapp/assets/img/icon.png"
rabbitmq_icon = "rabbitmq.png"
urlretrieve(rabbitmq_url, rabbitmq_icon)

with Diagram("Custom Example", show=False):
    queue = Custom("Message queue", rabbitmq_icon)
    db = PostgreSQL("db")
    queue >> db
""",
    }
