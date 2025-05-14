from awslabs.cfn_mcp_server.errors import ServerError


class Context:
    """A singleton which includes context for the MCP server such as startup parameters."""

    _instance = None

    def __init__(self, readonly_mode):
        """Initializes the context."""
        self.readonly_mode = readonly_mode

    @classmethod
    def readonly_mode(cls):
        """If a the server was started up with the argument --readonly True, this will be set to True."""
        if cls._instance is None:
            raise ServerError('Context was not initialized')
        return cls._instance.readonly_mode

    @classmethod
    def initialize(cls, readonly_mode):
        """Create the singleton instance of the type."""
        cls._instance = cls(readonly_mode)
