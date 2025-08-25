import importlib.metadata
import re

LOGIN_REGEX = r"^[a-z]{3,8}$"


def validate_amazon_login(login: str) -> None:
    if not re.match(LOGIN_REGEX, login):
        raise ValueError(f"Invalid login syntax. Must match regex {LOGIN_REGEX}")


def get_package_version() -> str:
    """
    Get the version of the package, \
        or return a default version if not available.
    """
    try:
        return importlib.metadata.version("awslabs.aws_iot_sitewise_mcp_server")
    except Exception:
        # Return a default version instead of raising an exception
        # to avoid crashing the server on startup
        return "0.1.0"
