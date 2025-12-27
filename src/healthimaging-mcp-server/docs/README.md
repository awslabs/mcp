# Documentation

Welcome to the AWS HealthImaging MCP Server documentation.

## Documentation Overview

This directory contains comprehensive documentation for the AWS HealthImaging MCP Server project.

### For Users

Start here if you want to use the HealthImaging MCP Server:

1. **[Quick Start Guide](QUICKSTART.md)** - Get up and running in minutes
   - Installation instructions
   - AWS setup
   - MCP client configuration
   - First steps and examples

2. **[API Reference](API.md)** - Complete tool documentation
   - All available tools
   - Parameters and return values
   - Usage examples
   - Error handling

### For Developers

Start here if you want to contribute or understand the internals:

1. **[Development Guide](DEVELOPMENT.md)** - Development setup and workflows
   - Environment setup
   - Development workflow
   - Adding new tools
   - Testing and debugging
   - Building and publishing

2. **[Architecture](ARCHITECTURE.md)** - System design and architecture
   - Component overview
   - Data flow
   - Security architecture
   - Scalability considerations
   - Future enhancements

### Additional Resources

- **[Contributing Guidelines](../CONTRIBUTING.md)** - How to contribute
- **[Security Policy](../SECURITY.md)** - Security best practices
- **[Changelog](../CHANGELOG.md)** - Version history
- **[Project Structure](../PROJECT_STRUCTURE.md)** - Complete file overview

## Quick Links

### Getting Started
- [Installation](QUICKSTART.md#installation)
- [AWS Setup](QUICKSTART.md#aws-setup)
- [Configuration](QUICKSTART.md#mcp-client-configuration)

### Using the Server
- [List Data Stores](API.md#list_datastores)
- [Search Image Sets](API.md#search_image_sets)
- [Get Metadata](API.md#get_image_set_metadata)

### Development
- [Setup Environment](DEVELOPMENT.md#development-environment-setup)
- [Adding Tools](DEVELOPMENT.md#adding-new-tools)
- [Running Tests](DEVELOPMENT.md#testing)

### Understanding the System
- [Components](ARCHITECTURE.md#components)
- [Data Flow](ARCHITECTURE.md#data-flow)
- [Security](ARCHITECTURE.md#security-architecture)

## Documentation Structure

```
docs/
├── README.md           # This file - documentation overview
├── QUICKSTART.md       # Quick start guide for users
├── API.md              # Complete API reference
├── ARCHITECTURE.md     # System architecture
└── DEVELOPMENT.md      # Development guide
```

## Reading Path

### For New Users

1. Start with [QUICKSTART.md](QUICKSTART.md)
2. Reference [API.md](API.md) as needed
3. Check [ARCHITECTURE.md](ARCHITECTURE.md) to understand how it works

### For Contributors

1. Read [DEVELOPMENT.md](DEVELOPMENT.md)
2. Review [ARCHITECTURE.md](ARCHITECTURE.md)
3. Check [../CONTRIBUTING.md](../CONTRIBUTING.md)
4. Reference [API.md](API.md) for tool specifications

### For Architects

1. Start with [ARCHITECTURE.md](ARCHITECTURE.md)
2. Review [API.md](API.md) for capabilities
3. Check [../SECURITY.md](../SECURITY.md) for security considerations

## Documentation Standards

All documentation in this project follows these standards:

- **Markdown Format**: All docs are in Markdown for easy reading and rendering
- **Clear Structure**: Hierarchical organization with clear headings
- **Code Examples**: Practical examples for all features
- **Up-to-Date**: Documentation is updated with code changes
- **Accessible**: Written for various skill levels

## Contributing to Documentation

Found an error or want to improve the docs?

1. Edit the relevant Markdown file
2. Follow the existing style and structure
3. Test any code examples
4. Submit a pull request

See [CONTRIBUTING.md](../CONTRIBUTING.md) for details.

## External Resources

- [AWS HealthImaging Documentation](https://docs.aws.amazon.com/healthimaging/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)

## Getting Help

- **Questions**: Open a GitHub Discussion
- **Issues**: Report bugs via GitHub Issues
- **Security**: See [SECURITY.md](../SECURITY.md) for reporting vulnerabilities

## License

This documentation is part of the AWS HealthImaging MCP Server project and is licensed under Apache License 2.0.

---

**Need help?** Start with [QUICKSTART.md](QUICKSTART.md) or open an issue on GitHub.
