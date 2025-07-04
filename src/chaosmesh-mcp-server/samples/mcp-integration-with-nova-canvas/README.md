# MCP Integration with Amazon Nova Canvas

This repository outlines a basic implementation of the [Model Context Protocol](https://modelcontextprotocol.io/) integration with Amazon Nova Canvas for image generation

## Overview

There are two parts to this implementation:

1. The `user_interfaces/image_generator_st.py` file, which handles the Streamlit/User Interface for the image generator
2. The `client_server.py` file, which handles the MCP client and server implementation

The exact MCP server code leveraged can be found in the [src/nova-canvas-mcp-server](../../src/nova-canvas-mcp-server/) folder.

### Architecture

The implementation follows this flow:
1. A Streamlit UI provides the user interface for image generation
2. The UI communicates with a FastAPI server
3. The FastAPI server uses the MCP client to communicate with the Nova Canvas MCP server
4. The Nova Canvas MCP server interacts with Amazon Bedrock to generate images
5. The generated images are returned to the UI for display

## Setup

### Prerequisites

- The [uv](https://docs.astral.sh/uv/getting-started/installation/) package manager
- AWS Account with Bedrock access and proper IAM permissions - [Getting Started with Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/getting-started.html)
- Access to the Amazon Nova Canvas and Amazon Nova Micro model (optional for prompt improvement) in Bedrock

### Installation

1. Clone the repository.

```bash
git clone https://github.com/awslabs/mcp.git
```

2. Navigate to the sample directory and copy the .env.example file to .env and add your AWS credentials.

```bash
cd mcp/samples/mcp-integration-with-nova-canvas
cp .env.example .env
```

3. Open two different terminals and install the dependencies in each.

```bash
uv sync
```

then activate the virtual environment

```bash
source .venv/bin/activate
```
4. In one of the terminals, run the FastAPI server

```bash
uvicorn clients.client_server:app --reload
```

5. In the other terminal, run the Streamlit app

```bash
streamlit run user_interfaces/image_generator_st.py
```

6. The image generator should now be running on [http://localhost:8501/](http://localhost:8501/)

## Usage

1. Enter a text prompt describing the image you want to generate
2. Optionally, add a negative prompt to specify what you don't want in the image
3. Customize image parameters (dimensions, quality, etc.)
4. For color-guided generation, select colors from the color picker
5. Click "Generate Image" to create your image
6. View the generated image and save it if desired

## Troubleshooting

Logs are available in the terminal where you ran the FastAPI server, outlining various steps and actions taken by the server.

If you see an error about `boto3` or `streamlit` not being found, it is likely because you did not activate the virtual environment:

```bash
uv sync
source .venv/bin/activate
