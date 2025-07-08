#!/usr/bin/env python3
"""Test the explain workflow to ensure properties are passed correctly."""

import asyncio
import sys
import os

# Add the source directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src/ccapi-mcp-server'))

from awslabs.ccapi_mcp_server.server import generate_infrastructure_code, explain, _properties_store

async def test_explain_workflow():
    """Test that properties flow correctly from generate_infrastructure_code to explain."""
    
    # Mock AWS session info
    aws_session_info = {
        'credentials_valid': True,
        'account_id': '123456789012',
        'region': 'us-east-1'
    }
    
    # Test properties
    test_properties = {
        'Description': 'Test KMS key',
        'EnableKeyRotation': True,
        'KeyPolicy': {
            'Statement': [{
                'Effect': 'Allow',
                'Principal': {'AWS': 'arn:aws:iam::123456789012:root'},
                'Action': 'kms:*',
                'Resource': '*'
            }]
        }
    }
    
    print("🧪 Testing explain workflow...")
    
    # Step 1: Generate infrastructure code
    print("\n1️⃣ Calling generate_infrastructure_code...")
    result = await generate_infrastructure_code(
        resource_type='AWS::KMS::Key',
        properties=test_properties,
        aws_session_info=aws_session_info
    )
    
    # Check what generate_infrastructure_code returns
    print(f"✅ Properties token: {result.get('properties_token', 'MISSING')}")
    print(f"✅ Properties for explanation present: {'properties_for_explanation' in result}")
    
    if 'properties_for_explanation' in result:
        props = result['properties_for_explanation']
        print(f"✅ Properties count: {len(props) if isinstance(props, dict) else 'Not a dict'}")
        print(f"✅ Has Tags: {'Tags' in props if isinstance(props, dict) else False}")
        if isinstance(props, dict) and 'Tags' in props:
            print(f"✅ Tag count: {len(props['Tags'])}")
            for tag in props['Tags']:
                if isinstance(tag, dict):
                    print(f"   - {tag.get('Key', 'NO_KEY')}: {tag.get('Value', 'NO_VALUE')}")
    
    # Step 2: Call explain with both content and properties_token
    print("\n2️⃣ Calling explain with properties...")
    
    properties_token = result.get('properties_token')
    properties_for_explanation = result.get('properties_for_explanation')
    
    if not properties_token:
        print("❌ FAIL: No properties_token returned")
        return False
        
    if not properties_for_explanation:
        print("❌ FAIL: No properties_for_explanation returned")
        return False
    
    explain_result = await explain(
        content=properties_for_explanation,
        properties_token=properties_token,
        context="Test KMS key creation",
        operation="create"
    )
    
    # Check explain results
    print(f"✅ Explain returned execution_token: {'execution_token' in explain_result}")
    print(f"✅ Explain has explanation: {'explanation' in explain_result}")
    print(f"✅ Properties being explained present: {'properties_being_explained' in explain_result}")
    
    if 'execution_token' in explain_result:
        execution_token = explain_result['execution_token']
        print(f"✅ Execution token: {execution_token}")
        
        # Check that execution token is different from properties token
        if execution_token != properties_token:
            print("✅ Execution token is different from properties token (correct)")
        else:
            print("❌ FAIL: Execution token same as properties token")
            return False
    
    # Step 3: Verify token workflow
    print("\n3️⃣ Verifying token workflow...")
    
    # Check that original properties_token is consumed
    if properties_token in _properties_store:
        print("❌ FAIL: Original properties_token still in store (should be consumed)")
        return False
    else:
        print("✅ Original properties_token consumed correctly")
    
    # Check that execution_token is in store
    execution_token = explain_result.get('execution_token')
    if execution_token and execution_token in _properties_store:
        print("✅ Execution token stored correctly")
        stored_props = _properties_store[execution_token]
        print(f"✅ Stored properties count: {len(stored_props) if isinstance(stored_props, dict) else 'Not a dict'}")
    else:
        print("❌ FAIL: Execution token not in store")
        return False
    
    # Step 4: Check explanation content
    print("\n4️⃣ Checking explanation content...")
    
    if 'explanation' in explain_result:
        explanation = explain_result['explanation']
        print(f"✅ Explanation length: {len(explanation)} characters")
        
        # Check if explanation mentions key properties
        if 'KMS' in explanation or 'Key' in explanation:
            print("✅ Explanation mentions KMS/Key")
        else:
            print("⚠️  Explanation doesn't mention KMS/Key")
            
        if 'Tags' in explanation or 'tags' in explanation:
            print("✅ Explanation mentions tags")
        else:
            print("⚠️  Explanation doesn't mention tags")
    
    print("\n🎉 Test completed successfully!")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_explain_workflow())
    if success:
        print("\n✅ ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("\n❌ TESTS FAILED")
        sys.exit(1)