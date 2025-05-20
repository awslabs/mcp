FROM python:3.10-slim

WORKDIR /app

COPY . .

RUN pip install --upgrade pip && \
    pip install .[dev]

CMD ["python3", "-m", "awslabs.mcp_lambda_handler.server"] 