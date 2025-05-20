from mcp_lambda_handler import MCPLambdaHandler
import random
import os

# Get session table name from environment variable
session_table = os.environ.get("MCP_SESSION_TABLE")

# Create the MCP server instance
mcp_server = MCPLambdaHandler(name="mcp-lambda-server", version="1.0.0", session_store=session_table)

@mcp_server.tool()
def roll_dice(sides: int = 6, be_nice: bool = False) -> str:
    """Roll a dice with the specified number of sides.
    
    Args:
        sides: Number of sides on the dice (default: 6, minimum: 4)
        be_nice: If True, prevents consecutive critical fails (1s) (default: False)
        
    Returns:
        str: A string containing either the roll result or an error message
             Success format: "Rolled a {number}"
             Error format: "Error: {error message}"
        
    Note:
        When be_nice is True and the last roll was a critical fail (rolled a 1),
        this function ensures the next roll cannot also be a critical fail,
        protecting against consecutive worst-case outcomes.
    """
    try:
        # Validate minimum sides
        if sides < 4:
            return f"Error: Dice must have at least 4 sides, got {sides}"
            
        # Get session if available - function will work without session too
        session = mcp_server.get_session()
        last_roll = session.get('last_roll') if session else None
        
        # Only prevent consecutive critical fails if be_nice is True
        if be_nice and last_roll == 1:
            this_roll = random.randint(2, sides)
            nice_msg = " (prevented consecutive 1s)"
        else:
            this_roll = random.randint(1, sides)
            nice_msg = ""
            
        # Store this roll if we have an active session
        if session:
            def update_roll(s):
                s.set('last_roll', this_roll)
                current_score = s.get('total_score', 0)
                s.set('total_score', current_score + this_roll)
                rolls_history = s.get('rolls_history', [])
                rolls_history.append({
                    'sides': sides,
                    'roll': this_roll,
                    'be_nice': be_nice
                })
                s.set('rolls_history', rolls_history)
            mcp_server.update_session(update_roll)
        
        return f"Rolled a {this_roll}{nice_msg}"
        
    except TypeError:
        return "Error: Invalid dice sides value - must be an integer"
    except Exception as e:
        return f"Error: An unexpected error occurred: {str(e)}"

@mcp_server.tool()
def get_total_score() -> str:
    """Get the total score from all dice rolls in this session.
    
    Returns:
        str: The total score if a session exists, or a message indicating no session
    """
    try:
        session = mcp_server.get_session()
        if not session:
            return "No active session - scores are only tracked in sessions"
        total_score = session.get('total_score', 0)
        return f"Total score: {total_score}"
    except Exception as e:
        return f"Error: An unexpected error occurred: {str(e)}"

@mcp_server.tool()
def get_roll_history() -> str:
    """Get the history of all rolls in this session.
    
    Returns:
        str: The roll history if a session exists, or a message indicating no session
    """
    try:
        session = mcp_server.get_session()
        if not session:
            return "No active session - roll history is only tracked in sessions"
        rolls_history = session.get('rolls_history', [])
        if not rolls_history:
            return "No rolls recorded yet in this session"
        
        history_str = "Roll History:\n"
        for roll in rolls_history:
            history_str += f"{roll['roll']} (d{roll['sides']})"
            if roll['be_nice']:
                history_str += " (nice mode)"
            history_str += "\n"
        return history_str
    except Exception as e:
        return f"Error: An unexpected error occurred: {str(e)}"

@mcp_server.tool()
def reset_score() -> str:
    """Reset the total score and roll history for the current session.
    
    Returns:
        str: Success message if reset was performed, or a message indicating no session
    """
    try:
        session = mcp_server.get_session()
        if not session:
            return "No active session - nothing to reset"
            
        def reset(s):
            s.set('total_score', 0)
            s.set('rolls_history', [])
        mcp_server.update_session(reset)
        
        return "Score and roll history have been reset"
    except Exception as e:
        return f"Error: An unexpected error occurred: {str(e)}"

def lambda_handler(event, context):
    """AWS Lambda handler function."""
    return mcp_server.handle_request(event, context) 