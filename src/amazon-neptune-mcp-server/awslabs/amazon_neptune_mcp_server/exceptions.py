from typing import Dict, Any, Union

class NeptuneException(Exception):
    """
    Exception class for Neptune-related errors.
    
    This exception is raised when operations on Neptune graphs fail,
    providing structured error information including a message and details.
    
    Args:
        exception (Union[str, Dict]): Either a string message or a dictionary
            containing 'message' and 'details' keys
    """

    def __init__(self, exception: Union[str, Dict]):
        """
        Initialize a new NeptuneException.
        
        Args:
            exception (Union[str, Dict]): Either a string message or a dictionary
                containing 'message' and 'details' keys
        """
        if isinstance(exception, dict):
            self.message = exception["message"] if "message" in exception else "unknown"
            self.details = exception["details"] if "details" in exception else "unknown"
        else:
            self.message = exception
            self.details = "unknown"

    def get_message(self) -> str:
        """
        Get the exception message.
        
        Returns:
            str: The exception message
        """
        return self.message

    def get_details(self) -> Any:
        """
        Get the exception details.
        
        Returns:
            Any: Additional details about the exception
        """
        return self.details