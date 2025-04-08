try:
    print("Importing pydantic...")
    from pydantic import BaseModel, Field, field_validator
    print("Successfully imported pydantic")
    
    print("Importing aws_diagram.models...")
    from aws_cdk.aws_diagram.models import DiagramType, DiagramGenerateResponse
    print("Successfully imported aws_diagram.models")
    
    print("Importing aws_diagram.diagrams...")
    from aws_cdk.aws_diagram.diagrams import generate_diagram, get_diagram_examples
    print("Successfully imported aws_diagram.diagrams")
    
    print("All imports successful!")
except ImportError as e:
    print(f"Import error: {e}")
except Exception as e:
    print(f"Other error: {e}")
