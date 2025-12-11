# Transform DynamoDB Access Pattern Validation Results

You are tasked with transforming DynamoDB access pattern validation results from JSON format to a comprehensive markdown report.

## Input
- Read the `dynamodb_model_validation.json` file from the current working directory.
- This file is generated after testing access patterns.
- The file contains detailed results of each access pattern test execution against DynamoDB Local.

## Output Requirements
1. Create a markdown file named `dynamodb_model_validation.md` in the current working directory.
2. Transform the JSON data into a well-structured, readable markdown report.
3. Display the generated markdown content to the user.

## Markdown Structure
The output markdown should include:

### Header
- Title: "DynamoDB Data Model Validation Report"
- Timestamp of the validation
- Overall validation effectiveness score

### Executive Summary
- Overall validation status and success rate
- Key issues identified
- Data model effectiveness assessment
- Test coverage summary

### Resource Creation Results
- Infrastructure setup summary
- Status of each table creation (success/failure with error details)
- GSI creation results
- Data insertion results

### Access Pattern Results
List EVERY pattern individually in sequential order. For each access pattern in the `validation_response` array, include:
- Pattern ID (from `pattern_id` field)
- Description (from `description` field)
- DynamoDB Operation Type (from `dynamodb_operation` field)
- Command Executed (only for failed patterns, formatted as code block)
- Response Summary (extract key information from the response field)
- Items Returned (count and sample data if applicable - mark empty results with HTTP 200 as ✅ Success)
- Error Details (if error field is present in response)
- External Integration Patterns (for patterns with `reason` field - mark as ✅ Success with integration guidance)
- Empty Result Explanation (for patterns returning 0 items with HTTP 200 - explain why this is expected/valid)

### Recommendations
- Specific fixes for failed patterns based on validation results
- Integration guidance for external service patterns

### Formatting Guidelines
- Use proper markdown headers (##, ###)
- Format JSON responses in code blocks with syntax highlighting
- Use tables where appropriate for structured data
- Include clear success/error indicators (✅/❌/⚠️/🔄)
- Calculate and display data model effectiveness percentage
- Provide specific, actionable recommendations
- Ensure proper spacing and readability

## Example Output Structure
```markdown
# DynamoDB Data Model Validation Report

**Validation Date:** [timestamp]
**Data Model Effectiveness:** X% (calculated from test coverage and success rates)

## Executive Summary

### Overall Status: ✅ PASSED / ❌ NEEDS ATTENTION / ⚠️ PARTIAL SUCCESS

- **Success Rate:** X% (Y out of Z patterns successful)
- **Critical Issues:** X high-priority failures identified
- **Test Coverage:** X patterns tested across Y tables
- **External Integration Patterns:** X patterns require external service integration

### Key Findings
- Brief summary of major successes
- Critical issues that need immediate attention
- Overall assessment of data model design

## Resource Creation Results

### Tables ✅/❌
- **Table 1:** ✅ Created successfully
- **Table 2:** ✅ Created successfully
- **Table 3:** ✅ Created successfully
- **Table 4:** ✅ Created successfully
- **Table 5:** ✅ Created successfully

### Global Secondary Indexes ✅/❌
- **GSI 1:** ✅ Created successfully

### Test Data Insertion ✅/❌
- **Sample Data Set 1:** ✅ Inserted successfully
- **Sample Data Set 2:** ✅ Inserted successfully
- **Sample Data Set 3:** ✅ Inserted successfully

## Access Pattern Results

### ✅ SUCCESSFUL PATTERNS

#### Access Patterns
[List patterns that executed successfully and returned data]

#### Access Patterns with empty results
[List patterns that returned 0 items but with successful HTTP 200 status]

#### External Integration Required
[List patterns that cannot be tested with DynamoDB operations due to external service requirements]

### ❌ FAILED PATTERNS
[List patterns that failed with errors]

##### Pattern 1: Retrieve entity data with related records
Operation: Query
Items Returned: 3
Items:
```json
{
  "entity_data": {"field1": "value1", "field2": "value2"},
  "related_items": [{"name": "Item A", "quantity": 2}],
  "historical_records": [{"date": "2024-10-20", "amount": 99.99}]
}
```

##### Pattern 3: Search items by name/keyword
Integration Type: OpenSearch
Reason: Delegated to external search service due to DynamoDB's limited text search capabilities

##### Pattern X: Create entity record (FAILED EXAMPLE)
Operation: TransactWriteItems
Command:
```bash
aws dynamodb transact-write-items --transact-items '[{"Put":{"TableName":"Table1","Item":{"pk":{"S":"entity123"},"sk":{"S":"TYPE_A"},"attribute1":{"S":"Value A"},"attribute2":{"S":"unique_value@example.com"}}}},{"Put":{"TableName":"Table2","Item":{"unique_field":{"S":"unique_value@example.com"},"reference_id":{"S":"entity123"}},"ConditionExpression":"attribute_not_exists(unique_field)"}}]'
```

**Error Details:**
- **Error:** TransactionCanceledException
- **Reason:** ConditionalCheckFailed - Unique constraint violation
- **Impact:** Data integrity constraint working as designed

##### Pattern Y: Create relationship record (FAILED EXAMPLE)
Operation: PutItem
Command:
```bash
aws dynamodb put-item --table-name Table3 --item '{"entity_id":{"S":"entity456"},"related_id":{"S":"entity123"},"relation_type":{"S":"ASSOCIATION"},"timestamp":{"S":"2024-10-23T12:01:00Z"}}' --condition-expression 'attribute_not_exists(related_id)'
```

**Error Details:**
- **Error:** ConditionalCheckFailedException
- **Reason:** The conditional request failed - Relationship already exists
- **Impact:** Duplicate relationship prevention working as designed

## Recommendations

**Based on Validation Results:**

1. **Fix Failed Patterns:** Address constraint violations in failed test cases
2. **External Service Integration:** Implement required integrations for delegated patterns
3. **Test Data Enhancement:** Add more test data if empty results were encountered

**Pattern-Specific Actions:**
- For ConditionalCheckFailed errors: Use unique values in test data
- For external integration patterns: Follow provided integration guidance
- For empty result patterns: Verify if additional test data is needed
```

Transform the validation results and create a comprehensive, professional markdown report that provides clear insights into the DynamoDB data model validation outcomes. Focus on actionable recommendations and clear assessment of the data model's effectiveness.
