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
    """AWS Lambda function to create a new customer.

    Args:
        event (dict): The Lambda event object containing customer information
                      Expected format: {
                          "name": "John Doe",
                          "email": "john@example.com",
                          "phone": "+1-555-123-4567",
                          "address": {  # Optional
                              "street": "123 Main St",
                              "city": "Anytown",
                              "state": "CA",
                              "zipCode": "12345"
                          }
                      }
        context (dict): AWS Lambda context object

    Returns:
        dict: Created customer information if successful, otherwise an error message
              Success format: {"customerId": "123", "name": "John Doe", ...}
              Error format: {"error": "Error message"}
    """
    try:
        # Extract customer information from the event
        name = event.get('name')
        email = event.get('email')
        phone = event.get('phone')
        address = event.get('address')

        # Validate required fields
        if not all([name, email, phone]):
            return {'error': 'Missing required customer information (name, email, phone)'}

        # Validate address fields if address is provided
        if address:
            required_address_fields = ['street', 'city', 'state', 'zipCode']
            if not all(field in address for field in required_address_fields):
                return {
                    'error': 'Address provided is missing required fields (street, city, state, zipCode)'
                }

        # This would normally create a record in a database
        # For demo purposes, we'll return mock data with a generated ID

        # Create response with required fields
        response = {
            'customerId': '98765',  # In real implementation, this would be generated
            'name': name,
            'email': email,
            'phone': phone,
            'accountCreated': '2025-05-06',  # In real implementation, this would be current date
        }

        # Add address if provided
        if address:
            response['address'] = address

        return response

    except Exception as e:
        return {'error': str(e)}
