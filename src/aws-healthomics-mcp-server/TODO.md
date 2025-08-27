# TODO: Workflow Linting Test Coverage Improvements

Current coverage: **37%** → Target: **80%+**

## High Priority (Easy Wins) 🎯

### 1. CWL Bundle Linting Tests
- [ ] Add `test_lint_cwl_bundle_success` - Multi-file CWL workflow with imports
- [ ] Add `test_lint_cwl_bundle_validation_errors` - Invalid CWL bundle scenarios
- [ ] Add `test_lint_cwl_bundle_missing_imports` - Test import resolution failures

### 2. Malformed Workflow Tests
- [ ] Add `test_lint_wdl_syntax_error` - Invalid WDL syntax
- [ ] Add `test_lint_cwl_syntax_error` - Invalid CWL syntax
- [ ] Add `test_lint_wdl_missing_required_fields` - WDL without workflow block
- [ ] Add `test_lint_cwl_missing_required_fields` - CWL without class/cwlVersion

### 3. Bundle Error Scenarios
- [ ] Add `test_lint_bundle_missing_main_file_cwl` - CWL version of existing WDL test
- [ ] Add `test_lint_bundle_invalid_file_structure` - Malformed directory structure
- [ ] Add `test_lint_bundle_circular_imports` - Detect circular import dependencies

## Medium Priority 📈

### 4. Workflow Validation Warnings
- [ ] Add `test_wdl_workflow_no_inputs_warning` - WDL workflow without inputs
- [ ] Add `test_wdl_workflow_no_outputs_warning` - WDL workflow without outputs
- [ ] Add `test_cwl_workflow_no_inputs_warning` - CWL workflow without inputs
- [ ] Add `test_cwl_workflow_no_outputs_warning` - CWL workflow without outputs
- [ ] Add `test_wdl_missing_runtime_requirements` - Tasks without runtime specs

### 5. Complex Multi-File Workflows
- [ ] Add `test_lint_wdl_bundle_nested_imports` - WDL with nested directory imports
- [ ] Add `test_lint_cwl_bundle_nested_imports` - CWL with nested directory imports
- [ ] Add `test_lint_bundle_mixed_file_types` - Bundle with both WDL and CWL files
- [ ] Add `test_lint_bundle_large_workflow` - Performance test with many files

### 6. Tool Function Coverage
- [ ] Add `test_lint_workflow_bundle_unsupported_format` - Invalid format parameter
- [ ] Add `test_lint_workflow_definition_file_io_error` - Mock file write failures

## Lower Priority 🔧

### 7. Error Handling Edge Cases
- [ ] Add `test_wdl_event_loop_conflict` - Mock RuntimeError with event loop message
- [ ] Add `test_cwl_event_loop_conflict` - Mock RuntimeError with event loop message
- [ ] Add `test_file_permission_error` - Mock PermissionError during temp file creation
- [ ] Add `test_disk_space_error` - Mock OSError during file operations

### 8. Advanced Workflow Scenarios
- [ ] Add `test_wdl_workflow_with_structs` - Complex WDL with custom types
- [ ] Add `test_cwl_workflow_with_subworkflows` - CWL with embedded workflows
- [ ] Add `test_wdl_workflow_with_conditionals` - WDL with if/else logic
- [ ] Add `test_cwl_workflow_with_scatter` - CWL with scatter/gather patterns

## Coverage Target Areas

**Lines needing coverage:**
- 58-71: Error handling in main lint functions
- 95-102: File I/O error scenarios
- 121-126: Event loop conflict handling
- 204-220: WDL validation warnings
- 232-233: WDL parsing edge cases
- 362-524: WDL bundle linting logic
- 534-675: CWL bundle linting logic
- 775-778: LintAHOWorkflowBundle tool errors
- 836-840: Tool function error handling

## Implementation Notes

- **Mock strategy**: Use `unittest.mock.patch` for file I/O and import errors
- **Test data**: Create minimal valid/invalid WDL/CWL examples in test fixtures
- **Bundle tests**: Use `tempfile.TemporaryDirectory` for multi-file scenarios
- **Error simulation**: Mock specific exceptions (RuntimeError, PermissionError, etc.)

## Success Metrics

- [ ] Achieve 80%+ coverage on `workflow_linting.py`
- [ ] All new tests pass consistently
- [ ] No regression in existing functionality
- [ ] Pre-commit hooks pass for all new test code
