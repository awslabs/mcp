import argparse

def main():
    parser = argparse.ArgumentParser(description="AWS Lambda MCP Handler CLI (for local dev/testing)")
    parser.add_argument('--version', action='version', version='awslabs.mcp-lambda-handler 0.1.0')
    args = parser.parse_args()
    print("This is the CLI entry point for awslabs.mcp-lambda-handler. No server functionality is exposed by default.")

if __name__ == "__main__":
    main() 