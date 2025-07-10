# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2025-07-09

### Added
- Enhanced FHIR functionality for better LLM interaction:
  - `create_fhir_bundle`: Create FHIR Bundles with multiple resources for batch processing
  - `search_fhir_resources_advanced`: Advanced search with include, revinclude, and sort parameters
  - `search_all_resources`: Search across all resource types in a datastore
  - `patch_fhir_resource`: Patch FHIR resources using JSON Patch or FHIRPath operations
  - `validate_fhir_resource`: Validate FHIR resource structure and provide feedback
  - `validate_fhir_resource_against_profile`: Validate FHIR resources against specific profiles
  - `create_patient_template`: Create FHIR Patient resource templates with common fields
  - `create_observation_template`: Create FHIR Observation resource templates
  - `get_fhir_resource_history`: Get version history of FHIR resources with filtering
  - `get_datastore_capabilities`: Get FHIR capabilities statement for datastores
  - `get_fhir_resource_compartment`: Get resources from FHIR compartments
- Enhanced documentation with comprehensive examples for all new features
- Support for FHIR Bundle transactions and batch operations
- Built-in validation for common FHIR resource types (Patient, Observation, Condition)
- Template-based resource creation for standardized healthcare data
- Advanced search capabilities with FHIR-specific parameters

### Enhanced
- **Improved FHIR CRUD Operations**: All FHIR operations now use proper HealthLake FHIR API patterns
- **Better Error Handling**: Comprehensive FHIR OperationOutcome error parsing and reporting
- **Optimistic Concurrency Control**: Support for If-Match headers in update and delete operations
- **Conditional Operations**: Support for conditional create (If-None-Exist) and conditional updates
- **Version Support**: Enhanced read operations with specific version ID support
- **Proper FHIR Headers**: All requests use appropriate FHIR content types and accept headers
- **Enhanced Validation**: Better resource validation with type checking and field validation
- **Improved Documentation**: More comprehensive examples and use cases for all operations

## [1.1.0] - 2025-07-08

### Added
- FHIR CRUD API operations:
  - `read_fhir_resource`: Retrieve FHIR resources by ID
  - `search_fhir_resources`: Search for FHIR resources using query parameters
  - `create_fhir_resource`: Create new FHIR resources
  - `update_fhir_resource`: Update existing FHIR resources
  - `delete_fhir_resource`: Delete FHIR resources
- Added requests library dependency
- Updated documentation with FHIR CRUD API examples
- Updated IAM permission recommendations

## [1.0.0] - 2025-07-01

### Added
- Initial release of AWS HealthLake MCP Server
- Support for datastore operations (create, delete, describe, list)
- Support for FHIR import/export job operations
- Support for resource tagging operations
- Read-only mode support via HEALTHLAKE_MCP_READONLY environment variable
- Comprehensive error handling and logging
- Full AWS credential integration
- Support for all AWS regions
