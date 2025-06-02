class BaseTool:
    """Base class for MCP tools."""

    def __init__(self, allow_write=None, allow_sensitive_data_access=None):
        """Initialize instance variables. None value means that the flag does not apply for the given tool."""
        self.allow_write = allow_write
        self.sensitive_data_access = allow_sensitive_data_access

    def checkToolAccess(self):
        """Checks if access to the tool is allowed based on allow-write and allow-sensitive-access flags."""
        if self.allow_write is False:
            raise Exception(
                'Write operations are not allowed. Set --allow-write flag to true to enable write operations.'
            )
        if self.sensitive_data_access is False:
            raise Exception(
                'Sensitive data access is not allowed. Set --allow-sensitive-data-access flag to true to access logs.'
            )
