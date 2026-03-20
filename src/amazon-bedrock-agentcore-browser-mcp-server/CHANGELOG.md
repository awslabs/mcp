# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 0.1.0 - Initial release

### Added
- Initial implementation of Amazon Bedrock AgentCore Browser MCP Server
- Support for creating and managing ephemeral browser sessions
- 8 MCP tools for browser automation:
  - create_browser_session
  - get_browser_session
  - list_browser_sessions
  - delete_browser_session
  - navigate_to_url
  - take_screenshot
  - execute_script
  - get_page_content
- AWS credential support via profile and environment variables
- Configuration via AWS_REGION, AWS_PROFILE, BROWSER_IDENTIFIER environment variables
