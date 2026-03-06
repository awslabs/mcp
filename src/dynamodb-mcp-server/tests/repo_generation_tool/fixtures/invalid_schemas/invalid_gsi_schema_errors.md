# Invalid GSI Schema - Expected Validation Errors

This schema is designed to trigger various GSI validation errors to test the validation system.

## Expected Validation Errors

### 1. Duplicate GSI Names
**Error**: GSI names must be unique within a table
**Location**: `gsi_list` contains two GSIs named "DuplicateIndex"
**Expected Message**: "Duplicate GSI name 'DuplicateIndex' found in table 'InvalidGSIExample'"

### 2. Non-Existent GSI Reference
**Error**: Entity mapping references GSI that doesn't exist
**Location**: TestEntity maps to "NonExistentIndex" which is not in gsi_list
**Expected Message**: "GSI 'NonExistentIndex' referenced in entity mapping but not found in gsi_list"

### 3. Missing Template Parameters
**Error**: Template references fields that don't exist in entity
**Location**: ValidIndex mapping uses `{missing_field}` and `{another_missing_field}`
**Expected Message**: "Template parameter 'missing_field' not found in entity fields"

### 4. Invalid Range Condition
**Error**: range_condition uses invalid value
**Location**: Pattern #3 uses "invalid_condition"
**Expected Message**: "Invalid range_condition 'invalid_condition'. Valid options: begins_with, between, >, <, >=, <="

### 5. Wrong Parameter Count for Range Condition
**Error**: "between" condition requires exactly 2 range parameters
**Location**: Pattern #4 uses "between" but only provides 1 range parameter
**Expected Message**: "Range condition 'between' requires exactly 2 range parameters in addition to partition key parameter"

### 6. Access Pattern References Non-Existent Index
**Error**: Access pattern references index that doesn't exist
**Location**: Pattern #2 references "NonExistentIndex"
**Expected Message**: "Access pattern references index 'NonExistentIndex' which does not exist in gsi_list"

### 7. Too Many Parameters for Range Condition
**Error**: "begins_with" condition should have exactly 1 range parameter
**Location**: Pattern #5 uses "begins_with" but provides 2 range parameters
**Expected Message**: "Range condition 'begins_with' requires exactly 1 range parameter in addition to partition key parameter"

### 8. Missing Required Parameters
**Error**: Query operation missing partition key parameter
**Location**: Pattern #6 only provides range parameter, missing partition key
**Expected Message**: "Query operation requires partition key parameter"

### 9. Empty Template Parameters
**Error**: Template contains empty parameter braces
**Location**: AnotherTestEntity uses "{}" in template
**Expected Message**: "Empty template parameter '{}' found in template"

### 10. Malformed Template Parameters
**Error**: Template contains unclosed braces
**Location**: AnotherTestEntity uses "{unclosed_brace" without closing brace
**Expected Message**: "Malformed template parameter in 'MALFORMED#{unclosed_brace'"

### 11. Invalid Operation Type
**Error**: Access pattern uses invalid operation
**Location**: Pattern #7 uses "InvalidOperation"
**Expected Message**: "Invalid operation 'InvalidOperation'. Valid operations: GetItem, Query, Scan"

## Validation Rules Tested

1. **GSI Name Uniqueness**: Ensures no duplicate GSI names within a table
2. **GSI Reference Validation**: Ensures entity mappings reference valid GSIs
3. **Template Parameter Validation**: Ensures template parameters exist as entity fields
4. **Range Condition Validation**: Ensures valid range_condition values
5. **Parameter Count Validation**: Ensures correct parameter count for range conditions
6. **Index Reference Validation**: Ensures access patterns reference valid indexes
7. **Template Syntax Validation**: Ensures proper template parameter syntax
8. **Operation Type Validation**: Ensures valid DynamoDB operations
9. **Required Parameter Validation**: Ensures required parameters are provided

## Usage in Tests

This schema should be used to verify that the validation system:
- Catches all these errors
- Provides helpful error messages
- Suggests valid alternatives where appropriate
- Fails validation before attempting code generation
