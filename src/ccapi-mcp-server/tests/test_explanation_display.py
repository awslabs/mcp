import pytest
from awslabs.ccapi_mcp_server.server import explain

@pytest.mark.asyncio
async def test_explanation_has_display_signals():
    """Test that explain() function returns all necessary signals to encourage LLM display."""
    from awslabs.ccapi_mcp_server.server import _properties_store
    
    try:
        # Clean up and add test token to properties store
        _properties_store.clear()
        _properties_store["test-token"] = {"resource_type": "AWS::S3::Bucket", "properties": {"BucketName": "test-bucket"}}
        
        # Test create operation with properties token
        create_result = await explain(
            content={"resource_type": "AWS::S3::Bucket", "properties": {"BucketName": "test-bucket"}},
            operation="create",
            properties_token="test-token"
        )
        
        # Verify all required fields are present
        assert "EXPLANATION_REQUIRED" in create_result
        assert "explanation" in create_result
        assert "execution_token" in create_result
        assert "CRITICAL_INSTRUCTION" in create_result
        
    finally:
        # Clean up properties store
        _properties_store.clear()


@pytest.mark.asyncio
async def test_explanation_delete_operation():
    """Test explain function for delete operations."""
    # Test delete operation with content only (no properties_token)
    delete_result = await explain(
        content={"resource_type": "AWS::S3::Bucket", "identifier": "test-bucket"},
        operation="delete"
    )
    
    # Verify all required fields are present
    assert "explanation" in delete_result
    assert "execution_token" in delete_result