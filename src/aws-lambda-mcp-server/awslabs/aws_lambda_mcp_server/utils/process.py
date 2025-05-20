import subprocess

def run_command(command, *args):
    """
    Run a terminal command with arguments
    Args:
        command (str): The command to run
        *args: Variable length argument list for command arguments
    Returns:
        CompletedProcess: Object containing return code and output
    """
    # Combine command and args into list
    cmd_list = [command]
    cmd_list.extend(args)
    
    # Run command and capture output
    result = subprocess.run(cmd_list, 
                          capture_output=True,
                          text=True)
    
    return result