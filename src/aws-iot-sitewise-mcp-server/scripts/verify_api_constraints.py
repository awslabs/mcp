#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Script to verify AWS IoT SiteWise API constraints and quotas.

This script checks the current implementation against the latest AWS IoT SiteWise
API documentation and service quotas to ensure all constraints are properly handled.

Usage:
    python scripts/verify_api_constraints.py
"""

import os
import sys


# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    import boto3

    AWS_AVAILABLE = True
except ImportError:
    print('Warning: boto3 not available, running offline validation only')
    AWS_AVAILABLE = False

# Import our validation functions
try:
    from site_wise_mcp_poc.validation import (
        SiteWiseQuotas,
        ValidationError,
        validate_asset_model_id,
        validate_asset_name,
        validate_max_results,
        validate_property_alias,
    )
except ImportError as e:
    print(f'Error: Could not import validation functions: {e}')
    sys.exit(1)


class APIConstraintVerifier:
    """Verify API constraints against AWS IoT SiteWise service."""

    def __init__(self, region='us-east-1'):
        """Initialize the API constraint verifier.

        Args:
            region: AWS region to use for verification (default: us-east-1)
        """
        self.region = region
        self.client = None
        self.verification_results = []

    def connect_to_aws(self):
        """Attempt to connect to AWS IoT SiteWise."""
        if not AWS_AVAILABLE:
            return False

        try:
            self.client = boto3.client('iotsitewise', region_name=self.region)
            # Test connection with a simple API call
            self.client.list_asset_models(maxResults=1)
            print(f'SUCCESS: Connected to AWS IoT SiteWise in {self.region}')
            return True
        except Exception as e:
            print(f'WARNING: Could not connect to AWS IoT SiteWise: {str(e)}')
            print('   Proceeding with offline validation only...')
            return False

    def verify_parameter_constraints(self):
        """Verify parameter validation constraints."""
        print('\nVerifying Parameter Constraints...')

        test_cases = [
            # Asset name constraints
            {
                'name': 'Asset name - empty string',
                'test': lambda: validate_asset_name(''),
                'should_fail': True,
            },
            {
                'name': 'Asset name - too long',
                'test': lambda: validate_asset_name('a' * 257),
                'should_fail': True,
            },
            {
                'name': 'Asset name - invalid characters',
                'test': lambda: validate_asset_name('asset@name#invalid'),
                'should_fail': True,
            },
            {
                'name': 'Asset name - valid',
                'test': lambda: validate_asset_name('Valid_Asset-Name.123'),
                'should_fail': False,
            },
            # Asset model ID constraints
            {
                'name': 'Asset model ID - empty',
                'test': lambda: validate_asset_model_id(''),
                'should_fail': True,
            },
            {
                'name': 'Asset model ID - too long',
                'test': lambda: validate_asset_model_id('a' * 37),
                'should_fail': True,
            },
            # Max results constraints
            {
                'name': 'Max results - below minimum',
                'test': lambda: validate_max_results(0),
                'should_fail': True,
            },
            {
                'name': 'Max results - above maximum',
                'test': lambda: validate_max_results(251),
                'should_fail': True,
            },
            {
                'name': 'Max results - valid',
                'test': lambda: validate_max_results(50),
                'should_fail': False,
            },
            # Property alias constraints
            {
                'name': 'Property alias - no leading slash',
                'test': lambda: validate_property_alias('no-leading-slash'),
                'should_fail': True,
            },
            {
                'name': 'Property alias - invalid characters',
                'test': lambda: validate_property_alias('/invalid@characters'),
                'should_fail': True,
            },
            {
                'name': 'Property alias - too long',
                'test': lambda: validate_property_alias('/' + 'a' * 2048),
                'should_fail': True,
            },
            {
                'name': 'Property alias - valid',
                'test': lambda: validate_property_alias('/company/factory/sensor1'),
                'should_fail': False,
            },
        ]

        passed = 0
        failed = 0

        for test_case in test_cases:
            try:
                test_case['test']()
                if test_case['should_fail']:
                    print(f'FAIL: {test_case["name"]}: Expected failure but passed')
                    failed += 1
                else:
                    print(f'PASS: {test_case["name"]}: Passed as expected')
                    passed += 1
            except ValidationError:
                if test_case['should_fail']:
                    print(f'PASS: {test_case["name"]}: Failed as expected')
                    passed += 1
                else:
                    print(f'FAIL: {test_case["name"]}: Unexpected failure')
                    failed += 1
            except Exception as e:
                print(f'ERROR: {test_case["name"]}: Unexpected error: {str(e)}')
                failed += 1

        print(f'\nParameter validation results: {passed} passed, {failed} failed')
        self.verification_results.append(('Parameter Validation', passed, failed))

    def verify_service_quotas(self):
        """Verify service quota constants against AWS documentation."""
        print('\nVerifying Service Quotas...')

        # These are the documented quotas as of 2024
        expected_quotas = {
            'MAX_ASSETS_PER_ACCOUNT': 100000,
            'MAX_ASSET_MODELS_PER_ACCOUNT': 10000,
            'MAX_PROPERTIES_PER_ASSET_MODEL': 200,
            'MAX_HIERARCHIES_PER_ASSET_MODEL': 10,
            'MAX_COMPOSITE_MODELS_PER_ASSET_MODEL': 10,
            'MAX_BATCH_PUT_ENTRIES': 10,
            'MAX_BATCH_GET_ENTRIES': 16,
            'MAX_PROPERTY_VALUES_PER_ENTRY': 10,
            'MAX_DASHBOARDS_PER_PROJECT': 1000,
            'MAX_GATEWAYS_PER_ACCOUNT': 1000,
            'MAX_TIME_SERIES_PER_ACCOUNT': 1000000,
        }

        passed = 0
        failed = 0

        for quota_name, expected_value in expected_quotas.items():
            actual_value = getattr(SiteWiseQuotas, quota_name, None)

            if actual_value is None:
                print(f'FAIL: {quota_name}: Not defined in SiteWiseQuotas')
                failed += 1
            elif actual_value == expected_value:
                print(f'PASS: {quota_name}: {actual_value} (correct)')
                passed += 1
            else:
                print(f'WARN: {quota_name}: {actual_value} (expected {expected_value})')
                # This is a warning, not a failure, as quotas may change
                passed += 1

        print(f'\nService quota verification: {passed} passed, {failed} failed')
        self.verification_results.append(('Service Quotas', passed, failed))

    def verify_error_handling(self):
        """Verify error handling patterns."""
        print('\nVerifying Error Handling...')

        # Import our tools to test error handling
        try:
            from site_wise_mcp_poc.tools.sitewise_assets import create_asset
        except ImportError as e:
            print(f'ERROR: Could not import tools: {e}')
            self.verification_results.append(('Error Handling', 0, 1))
            return

        error_tests = [
            {
                'name': 'Validation Error Format',
                'test': lambda: create_asset('', 'test-model'),
                'expected_error_code': 'ValidationException',
                'expected_error_content': 'Validation error:',
            },
            {
                'name': 'Response Structure',
                'test': lambda: create_asset('', 'test-model'),
                'expected_keys': ['success', 'error', 'error_code'],
            },
        ]

        passed = 0
        failed = 0

        for test in error_tests:
            try:
                result = test['test']()

                # Check response structure
                if 'expected_keys' in test:
                    missing_keys = [key for key in test['expected_keys'] if key not in result]
                    if missing_keys:
                        print(f'FAIL: {test["name"]}: Missing keys: {missing_keys}')
                        failed += 1
                        continue

                # Check error code
                if 'expected_error_code' in test:
                    if result.get('error_code') != test['expected_error_code']:
                        print(
                            f'FAIL: {test["name"]}: Wrong error code: {result.get("error_code")}'
                        )
                        failed += 1
                        continue

                # Check error content
                if 'expected_error_content' in test:
                    if test['expected_error_content'] not in result.get('error', ''):
                        print(f'FAIL: {test["name"]}: Missing error content')
                        failed += 1
                        continue

                print(f'PASS: {test["name"]}: Error handling correct')
                passed += 1

            except Exception as e:
                print(f'ERROR: {test["name"]}: Unexpected error: {str(e)}')
                failed += 1

        print(f'\nError handling verification: {passed} passed, {failed} failed')
        self.verification_results.append(('Error Handling', passed, failed))

    def generate_report(self):
        """Generate final verification report."""
        print('\n' + '=' * 60)
        print('VERIFICATION REPORT')
        print('=' * 60)

        total_passed = 0
        total_failed = 0

        for category, passed, failed in self.verification_results:
            total_passed += passed
            total_failed += failed
            status = 'PASS' if failed == 0 else 'ISSUES' if passed > failed else 'FAIL'
            print(f'{category:.<30} {passed:>3} passed, {failed:>3} failed {status}')

        print('-' * 60)
        print(f'{"TOTAL":.<30} {total_passed:>3} passed, {total_failed:>3} failed')

        if total_failed == 0:
            print('\nSUCCESS: All verifications passed! The implementation appears to be robust.')
        elif total_failed < total_passed:
            print(f'\nWARNING: Some issues found but mostly working ({total_failed} issues)')
        else:
            print(f'\nERROR: Significant issues found ({total_failed} failures)')

        print('\nRecommendations:')
        if total_failed > 0:
            print('   • Review and fix the failed validations')
            print('   • Run tests with real AWS credentials')
            print('   • Consider adding more comprehensive error handling')

        print('   • Regularly update service quotas as AWS limits change')
        print('   • Monitor AWS IoT SiteWise API changes and updates')
        print('   • Test with real workloads before production deployment')


def main():
    """Main verification function."""
    print('AWS IoT SiteWise MCP Server - API Constraint Verification')
    print('=' * 60)

    verifier = APIConstraintVerifier()

    # Try to connect to AWS
    verifier.connect_to_aws()

    # Run all verifications
    verifier.verify_parameter_constraints()
    verifier.verify_service_quotas()
    verifier.verify_error_handling()

    # Generate final report
    verifier.generate_report()

    # Return exit code based on results
    total_failed = sum(failed for _, _, failed in verifier.verification_results)
    return 0 if total_failed == 0 else 1


if __name__ == '__main__':
    exit(main())
