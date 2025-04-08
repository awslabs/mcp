try:
    import diagrams_mcp_server
    print(f"Successfully imported diagrams_mcp_server from {diagrams_mcp_server.__file__}")
except ImportError as e:
    print(f"Failed to import diagrams_mcp_server: {e}")
