# Implementation Plan: explain_infrastructure Tool

## Why This Needs to Be Done

### Problem Statement
- Users cannot see what infrastructure will be created/updated before execution
- Default management tags are added silently without user visibility
- No transparency in the token-based workflow
- Users only see tool requests, never responses, unless response becomes input to next tool

### Business Value
- **Transparency**: Users see exactly what will be created including default tags
- **Trust**: No hidden behavior in infrastructure operations
- **Compliance**: Users can review all tags before approval
- **Better UX**: Clear explanation of infrastructure changes in human-readable format

## What Has Been Done

### ✅ Completed Tasks

1. **Fixed Default Tagging Logic**
   - Modified `add_default_tags()` in `cloud_control_utils.py` to always try adding tags
   - Added `add_default_tags()` calls to UPDATE operations in `infrastructure_generator.py`
   - Default tags now work for both CREATE and UPDATE operations

2. **Enhanced Response Transparency**
   - Modified `infrastructure_generator.py` to include `properties` in response
   - Users can now see the complete resource definition with default tags

3. **Identified Token Flow Requirements**
   - Confirmed token system prevents LLM from bypassing generated properties
   - Established need for mandatory explanation step before destructive operations

## What Remains to Be Done

### ✅ COMPLETED Implementation

1. **✅ Added explain_infrastructure Tool**
   - Tool accepts both properties_token and raw content
   - Tracks explanation state in token metadata
   - Provides clear instructions to LLM for explanations

2. **✅ Enhanced Token Storage System**
   - Added `_metadata` tracking for `explained` flag
   - Modified validation in `create_resource()` and `update_resource()`
   - Added proper token cleanup for metadata

3. **✅ Updated System Prompt**
   - Added mandatory workflow sequences
   - Required `explain_infrastructure` before destructive operations
   - Included clear workflow for create, update, and delete operations

### 🎯 Implementation Steps

1. **Step 1: Add explain_infrastructure tool to server.py**
   - Insert tool definition after existing tools
   - Handle both token-based and content-based explanations
   - Return instruction for LLM to provide clear summary

2. **Step 2: Enhance token storage**
   - Modify `_properties_store` structure to include metadata
   - Add tracking for `explained` and `operation` flags
   - Update token cleanup logic

3. **Step 3: Add validation to destructive operations**
   - Modify `create_resource()` to check `explained` flag
   - Modify `update_resource()` to check `explained` flag
   - Provide clear error messages when explanation is missing

4. **Step 4: Update system prompt**
   - Add mandatory workflow instructions
   - Specify explanation requirements
   - Include examples of good explanations

### 🔍 Success Criteria

- [x] `explain_infrastructure` tool successfully explains properties from token
- [x] LLM provides clear, bulleted summaries of infrastructure changes
- [x] Default management tags are highlighted in explanations
- [x] `create_resource()` and `update_resource()` enforce explanation requirement
- [x] Error messages guide users to proper workflow
- [x] Tool works for both CREATE/UPDATE and DELETE flows

### 🚧 Technical Considerations

- **Token Management**: Single token per operation with state tracking
- **Error Handling**: Clear messages when workflow steps are skipped
- **Backward Compatibility**: Existing functionality remains unchanged
- **Performance**: Minimal overhead from additional validation

## Next Actions

1. Implement `explain_infrastructure` tool in server.py
2. Test token flow with explanation requirement
3. Verify LLM provides clear explanations
4. Update documentation and examples
