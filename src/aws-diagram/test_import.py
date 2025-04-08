try:
    import awslabs.aws_diagram
    print(f"Successfully imported diagrams_mcp_server from {awslabs.aws_diagram.__file__}")
except ImportError as e:
    print(f"Failed to import diagrams_mcp_server: {e}")
