import importlib.util


try:
    print('Checking for pydantic...')
    pydantic_spec = importlib.util.find_spec('pydantic')
    if pydantic_spec is not None:
        print('Successfully found pydantic')
    else:
        print('pydantic not found')

    print('Checking for aws_diagram.models...')
    models_spec = importlib.util.find_spec('aws_cdk.aws_diagram.models')
    if models_spec is not None:
        print('Successfully found aws_diagram.models')
    else:
        print('aws_diagram.models not found')

    print('Checking for aws_diagram.diagrams...')
    diagrams_spec = importlib.util.find_spec('aws_cdk.aws_diagram.diagrams')
    if diagrams_spec is not None:
        print('Successfully found aws_diagram.diagrams')
    else:
        print('aws_diagram.diagrams not found')

    print('All checks successful!')
except ImportError as e:
    print(f'Import error: {e}')
except Exception as e:
    print(f'Other error: {e}')
