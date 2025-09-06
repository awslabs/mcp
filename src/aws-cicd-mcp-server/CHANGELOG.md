# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2024-01-XX

### Added
- Initial release of AWS CI/CD MCP Server
- CodePipeline tools: list_pipelines, get_pipeline_details, start_pipeline_execution, get_pipeline_execution_history
- CodeBuild tools: list_projects, get_project_details, start_build, get_build_logs
- CodeDeploy tools: list_applications, get_application_details, list_deployment_groups, create_deployment, get_deployment_status
- Read-only mode by default for security
- Comprehensive error handling and logging
- Docker support with health checks
