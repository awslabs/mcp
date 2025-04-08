"""Direct test script for the diagrams-expert MCP server."""

import asyncio
import os
import sys
from pathlib import Path


# Add the current directory to the Python path
sys.path.append(str(Path.cwd()))

# Import the diagram generation function directly from our diagrams module
from ai3_diagrams_expert.diagrams import generate_diagram, get_diagram_examples, list_diagram_icons
from ai3_diagrams_expert.models import DiagramType


async def test_diagram_generation():
    """Test the diagram generation functionality directly."""
    # Get example code for AWS diagram
    examples = get_diagram_examples(diagram_type=DiagramType.AWS)
    aws_code = examples.examples['aws_basic']

    # Generate the diagram
    result = await generate_diagram(code=aws_code)

    # Print the result
    print('Diagram generation result:', result)

    # Check if the diagram was created
    if result.status == 'success':
        if result.path:
            print(f'Diagram created at: {result.path}')
            if os.path.exists(result.path):
                print(f'File size: {os.path.getsize(result.path)} bytes')
            else:
                print('Warning: File path exists in result but file not found on disk')
        else:
            print('Warning: No path returned in the success result')
    else:
        print(f'Error: {result.message}')

    print('-' * 50)


async def test_bedrock_diagram():
    """Test the Bedrock diagram generation."""
    # Get example code for AWS Bedrock diagram
    examples = get_diagram_examples(diagram_type=DiagramType.AWS)
    bedrock_code = examples.examples['aws_bedrock']

    # Generate the diagram
    result = await generate_diagram(code=bedrock_code)

    # Print the result
    print('\nBedrock diagram generation result:', result)

    # Check if the diagram was created
    if result.status == 'success':
        if result.path:
            print(f'Bedrock diagram created at: {result.path}')
            if os.path.exists(result.path):
                print(f'File size: {os.path.getsize(result.path)} bytes')
            else:
                print('Warning: File path exists in result but file not found on disk')
        else:
            print('Warning: No path returned in the success result')
    else:
        print(f'Error: {result.message}')


if __name__ == '__main__':
    asyncio.run(test_diagram_generation())
    asyncio.run(test_bedrock_diagram())
    icons = list_diagram_icons()
