# Contributing to Bedrock Advisor MCP Server

Thank you for your interest in contributing to the Bedrock Advisor MCP Server! This document provides guidelines for contributing to this project.

## 🤝 How to Contribute

### Reporting Issues
- Use the GitHub Issues tab to report bugs or request features
- Provide detailed information about the issue
- Include steps to reproduce for bugs
- Check existing issues to avoid duplicates

### Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/your-username/bedrock-advisor-mcp.git
   cd bedrock-advisor-mcp
   ```

2. **Set up Development Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements-dev.txt
   pip install -e .
   ```

3. **Install Pre-commit Hooks**
   ```bash
   pre-commit install
   ```

### Making Changes

1. **Create a Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Your Changes**
   - Follow the coding standards below
   - Add tests for new functionality
   - Update documentation as needed

3. **Test Your Changes**
   ```bash
   # Run tests
   pytest
   
   # Run linting
   flake8 bedrock_advisor/
   black bedrock_advisor/
   mypy bedrock_advisor/
   
   # Run security scan
   bandit -r bedrock_advisor/
   ```

4. **Commit and Push**
   ```bash
   git add .
   git commit -m "Add: your descriptive commit message"
   git push origin feature/your-feature-name
   ```

5. **Create Pull Request**
   - Open a pull request against the main branch
   - Provide a clear description of your changes
   - Link any related issues

## 📋 Coding Standards

### Python Style
- Follow PEP 8 style guidelines
- Use type hints for all functions and methods
- Maximum line length: 88 characters (Black formatter)
- Use meaningful variable and function names

### Code Structure
- Follow SOLID principles
- Use dependency injection where appropriate
- Maintain separation of concerns
- Write self-documenting code

### Documentation
- Write comprehensive docstrings (Google style)
- Update README.md for user-facing changes
- Add inline comments for complex logic
- Keep documentation up to date

### Testing
- Write unit tests for all new functionality
- Maintain >90% test coverage
- Use descriptive test names
- Test both success and failure scenarios
- Mock external dependencies

### Security
- Never commit credentials or sensitive data
- Validate all inputs
- Follow AWS security best practices
- Use secure coding practices

## 🧪 Testing Guidelines

### Test Structure
```
tests/
└── unit/           # Unit tests
```

### Writing Tests
- Use pytest framework
- Follow AAA pattern (Arrange, Act, Assert)
- Use fixtures for common setup
- Mock external dependencies
- Test edge cases and error conditions

### Running Tests
```bash
# All tests
pytest

# Specific test file
pytest tests/unit/test_model_data.py

# With coverage
pytest --cov=bedrock_advisor --cov-report=html

# Performance tests
# Performance tests would be implemented here
```

## 📦 Release Process

### Version Numbering
- Follow Semantic Versioning (SemVer)
- Format: MAJOR.MINOR.PATCH
- Update version in `pyproject.toml`

### Release Checklist
- [ ] All tests pass
- [ ] Documentation updated
- [ ] Version bumped
- [ ] CHANGELOG.md updated
- [ ] Security scan clean
- [ ] Performance benchmarks acceptable

## 🛡️ Security

### Reporting Security Issues
- Do not open public issues for security vulnerabilities
- Email security concerns to the maintainers
- Provide detailed information about the vulnerability

### Security Guidelines
- Never commit AWS credentials or API keys
- Use environment variables for sensitive configuration
- Validate and sanitize all inputs
- Follow principle of least privilege
- Keep dependencies updated

## 📝 Code Review Process

### For Contributors
- Ensure your code follows all guidelines
- Write clear commit messages
- Respond promptly to review feedback
- Keep pull requests focused and small

### For Reviewers
- Be constructive and respectful
- Focus on code quality and security
- Check for test coverage
- Verify documentation updates

## 🎯 Areas for Contribution

### High Priority
- Additional model providers integration
- Enhanced recommendation algorithms
- Performance optimizations
- Documentation improvements

### Medium Priority
- Additional MCP tools
- Enhanced error handling
- Monitoring and metrics
- CI/CD improvements

### Good First Issues
- Documentation fixes
- Test coverage improvements
- Code style improvements
- Minor bug fixes

## 📞 Getting Help

- Check existing documentation
- Search existing issues
- Ask questions in discussions
- Contact maintainers for complex issues

## 🙏 Recognition

Contributors will be recognized in:
- README.md contributors section
- Release notes
- Project documentation

Thank you for contributing to making this project better! 🚀
