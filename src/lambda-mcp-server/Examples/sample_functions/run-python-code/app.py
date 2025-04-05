import json
import os
import subprocess


TMP_DIR = '/tmp'


def remove_tmp_contents() -> None:
    """Remove all contents (files and directories) from the temporary directory.

    This function traverses the /tmp directory tree and removes all files and empty
    directories. It handles exceptions for each removal attempt and prints any
    errors encountered.
    """
    # Traverse the /tmp directory tree
    for root, dirs, files in os.walk(TMP_DIR, topdown=False):
        # Remove files
        for file in files:
            file_path: str = os.path.join(root, file)
            try:
                os.remove(file_path)
            except Exception as e:
                print(f'Error removing {file_path}: {e}')

        # Remove empty directories
        for dir in dirs:
            dir_path: str = os.path.join(root, dir)
            try:
                os.rmdir(dir_path)
            except Exception as e:
                print(f'Error removing {dir_path}: {e}')


def do_install_modules(modules: list[str], current_env: dict[str, str]) -> str:
    """Install Python modules using pip.

    This function takes a list of module names and attempts to install them
    using pip. It handles exceptions for each module installation and prints
    any errors encountered.

    Args:
        modules (list[str]): A list of Python module names to install.
        current_env (dict[str, str]): The current environment variables to use for installation.
    """
    output = ''

    if type(modules) is list and len(modules) > 0:
        current_env['PYTHONPATH'] = TMP_DIR
        try:
            _ = subprocess.run(
                f'pip install -U pip setuptools wheel -t {TMP_DIR} --no-cache-dir'.split(),
                capture_output=True,
                text=True,
                check=True,
            )
        except Exception as e:
            error_message = f'Error installing {modules}: {e}'
            print(error_message)
            output += error_message

        for module in modules:
            try:
                _ = subprocess.run(
                    f'pip install {module} -t {TMP_DIR} --no-cache-dir'.split(),
                    capture_output=True,
                    text=True,
                    check=True,
                )
            except Exception as e:
                error_message = f'Error installing {module}: {e}'
                print(error_message)
                output += error_message

    return output


def lambda_handler(event: dict, context: dict) -> dict:
    """AWS Lambda function handler to execute Python code provided in the event.

    Args:
        event (dict): The Lambda event object containing the Python code to execute
                      Expected format: {"code": "your_python_code_as_string"}
        context (dict): AWS Lambda context object

    Returns:
        dict: Results of the code execution containing:
              - output (str): Output of the executed code or error message
    """
    remove_tmp_contents()

    output = ''
    current_env = os.environ.copy()

    # No need to go further if there is no script to run
    input_script = event.get('input_script', '')
    if len(input_script) == 0:
        return {'statusCode': 400, 'body': 'Input script is required'}

    install_modules = event.get('install_modules', [])
    output += do_install_modules(install_modules, current_env)

    print(f'Script:\n{input_script}')

    result = subprocess.run(
        ['python', '-c', input_script], env=current_env, capture_output=True, text=True
    )
    output += result.stdout + result.stderr

    print(f'Output: {output}')
    print(f'Len: {len(output)}')

    # After running the script
    remove_tmp_contents()

    result = {'output': output}

    return {'statusCode': 200, 'body': json.dumps(result)}
