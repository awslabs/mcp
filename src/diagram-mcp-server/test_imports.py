try:
    print("Importing pydantic...")
    from pydantic import BaseModel, Field, field_validator
    print("Successfully imported pydantic")
    
    print("Importing diagrams_mcp_server.models...")
    from diagrams_mcp_server.models import DiagramType, DiagramGenerateResponse
    print("Successfully imported diagrams_mcp_server.models")
    
    print("Importing diagrams_mcp_server.diagrams...")
    from diagrams_mcp_server.diagrams import generate_diagram, get_diagram_examples
    print("Successfully imported diagrams_mcp_server.diagrams")
    
    print("All imports successful!")
except ImportError as e:
    print(f"Import error: {e}")
except Exception as e:
    print(f"Other error: {e}")
