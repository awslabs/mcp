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

def lambda_handler(event: dict, context: dict) -> dict:
    """AWS Lambda function to retrieve customer ID based on customer email address.

    Args:
        event (dict): The Lambda event object containing the customer email
                      Expected format: {"email": "example@domain.com"}
        context (dict): AWS Lambda context object

    Returns:
        dict: Customer ID if found, otherwise an error message
              Success format: {"customerId": "123"}
              Error format: {"error": "Customer not found"}
    """
    try:
        # Extract email from the event
        email = event.get('email')

        if not email:
            return {'error': 'Missing email parameter'}

        # This would normally query a database
        # For demo purposes, we'll return mock data

        # Simulate database lookup
        if email == 'john.doe@example.com':
            return {'customerId': '12345'}
        else:
            return {'customerId': '54321'}

    except Exception as e:
        return {'error': str(e)}
