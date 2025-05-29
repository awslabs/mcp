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
