"""
Security utilities for CloudWAN MCP Network Data Export.

This module provides security features for the export functionality, including
path validation, data encryption, and secure file handling.
"""

import os
import re
import logging
import secrets
import hashlib
import hmac
import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import base64

# Setup secure logging with sensitive data protection
logger = logging.getLogger(__name__)

# List of patterns for sensitive data that should never be logged
SENSITIVE_PATTERNS = [
    r"password",
    r"secret",
    r"token",
    r"key",
    r"credential",
    r"auth",
    r"private",
    r"cert",
]

# Maximum file size for in-memory operations (50MB)
MAX_IN_MEMORY_SIZE = 50 * 1024 * 1024


def validate_path(path: str, allowed_dirs: Optional[List[str]] = None) -> Tuple[bool, str]:
    """
    Validate if a path is safe to use for file operations.

    This function checks if a path is properly formatted, doesn't contain dangerous
    patterns like directory traversal attempts, and is within allowed directories.
    It also verifies that the path doesn't contain symbolic links or other dangerous
    constructs that could lead to security vulnerabilities.

    Args:
        path: File path to validate
        allowed_dirs: Optional list of allowed directory prefixes

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check if path is None or empty
    if not path:
        return False, "Empty path provided"

    try:
        # Convert to Path object for safer handling
        path_obj = Path(path).resolve()
        norm_path = str(path_obj)

        # Check if path is absolute
        if not os.path.isabs(norm_path):
            return False, "Path must be absolute"

        # Check for directory traversal attempts (explicit check)
        parts = path_obj.parts
        if ".." in parts:
            return False, "Directory traversal detected"

        # Check if path contains symbolic links
        if os.path.islink(path) or any(
            os.path.islink(os.path.join(*parts[: i + 1]))
            for i in range(len(parts))
            if os.path.exists(os.path.join(*parts[: i + 1]))
        ):
            return False, "Path contains symbolic links which are not allowed"

        # Enhanced check for dangerous patterns
        dangerous_patterns = [
            # Executable files in temporary directories
            r"\/tmp\/.*\.(exe|sh|bash|py|pl|rb)$",
            # System directories
            r"^\/dev\/|^\/proc\/|^\/sys\/",
            # System binaries and configuration
            r"^\/bin\/|^\/sbin\/|^\/etc\/|^\/lib\/|^\/lib64\/|^\/boot\/",
            # User profile directories that might contain sensitive data
            r"^\/home\/.*\/(\.|\.|ssh|config|secrets|credentials)",
            # Alternate directory traversal patterns
            r".*\.\..*",
            r".*\\\.\\\.$",  # Windows-style path traversal
            r".*\%2e\%2e.*",  # URL-encoded path traversal
            r".*\%252e\%252e.*",  # Double URL-encoded path traversal
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, norm_path):
                return False, f"Path matches dangerous pattern: {pattern}"

        # Check if the parent directory exists for new files
        parent_dir = os.path.dirname(norm_path)
        if parent_dir and not os.path.exists(parent_dir):
            return False, f"Parent directory does not exist: {parent_dir}"

        # Check if path is within allowed directories with more strict checking
        if allowed_dirs and allowed_dirs:  # Make sure it's not an empty list
            # Normalize all allowed directories for comparison
            normalized_allowed_dirs = [os.path.normpath(dir_path) for dir_path in allowed_dirs]
            within_allowed = any(
                norm_path.startswith(allowed_dir) for allowed_dir in normalized_allowed_dirs
            )
            if not within_allowed:
                return (
                    False,
                    f"Path must be within allowed directories: {', '.join(allowed_dirs)}",
                )

        # Check permissions if file exists
        if os.path.exists(norm_path) and not os.access(norm_path, os.R_OK | os.W_OK):
            return False, f"Insufficient permissions for path: {norm_path}"

        return True, ""

    except Exception as e:
        # Catch any unexpected errors in path validation
        logger.error(f"Path validation error: {str(e)}")
        return False, f"Path validation error: {str(e)}"


def generate_encryption_key(
    password: Optional[str] = None, salt: Optional[bytes] = None
) -> Tuple[bytes, Optional[bytes]]:
    """
    Generate a secure encryption key using either random generation or password-based key derivation.

    Args:
        password: Optional password to derive key from
        salt: Optional salt for password-based key derivation (generated if not provided)

    Returns:
        Tuple of (encryption_key, salt). Salt is None if password is None.
    """
    if password is None:
        # Generate a random key directly
        return Fernet.generate_key(), None
    else:
        # Password-based key derivation
        if salt is None:
            salt = os.urandom(16)  # Generate a secure random salt

        # Use PBKDF2 to derive a secure key from the password
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 32 bytes = 256 bits
            salt=salt,
            iterations=100000,  # High iteration count for security
        )

        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key, salt


def encrypt_file(
    input_path: str,
    output_path: Optional[str] = None,
    encryption_key: Optional[bytes] = None,
    password: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Tuple[str, bytes, Optional[bytes]]:
    """
    Encrypt a file using Fernet symmetric encryption with metadata support.

    This enhanced function supports both key-based and password-based encryption,
    as well as including metadata in the encrypted file for better identification
    and verification purposes.

    Args:
        input_path: Path to the file to encrypt
        output_path: Optional path for the encrypted file (default: input_path + .enc)
        encryption_key: Optional encryption key (generated if not provided)
        password: Optional password to derive encryption key from
        metadata: Optional metadata to include in the encrypted file

    Returns:
        Tuple of (encrypted_file_path, encryption_key, salt) - salt is None if password is not used
    """
    # Validate paths
    is_valid, error = validate_path(input_path)
    if not is_valid:
        raise ValueError(f"Invalid input path: {error}")

    if output_path:
        is_valid, error = validate_path(output_path)
        if not is_valid:
            raise ValueError(f"Invalid output path: {error}")
    else:
        # Create output in a secure temporary location if not specified
        temp_path = secure_temp_file("encrypted", ".enc")
        output_path = temp_path

    # Generate or use encryption key
    salt = None
    if password is not None and encryption_key is None:
        key, salt = generate_encryption_key(password=password)
    else:
        key = encryption_key or generate_encryption_key()[0]

    cipher = Fernet(key)

    # Read input file
    with open(input_path, "rb") as f:
        data = f.read()

    # Prepare metadata if provided
    if metadata is None:
        metadata = {}

    # Add encryption timestamp and file information
    metadata.update(
        {
            "encrypted_at": str(datetime.now().isoformat()),
            "original_filename": os.path.basename(input_path),
            "original_filesize": len(data),
            "hash_algorithm": "sha256",
            "content_hash": hashlib.sha256(data).hexdigest(),
            "has_password": password is not None,
        }
    )

    # Convert metadata to bytes
    metadata_bytes = base64.b64encode(json.dumps(metadata).encode())

    # Encrypt data
    encrypted_data = cipher.encrypt(data)

    # Format output with metadata header
    # Format: [METADATA_LENGTH:4 bytes][METADATA][SALT_LENGTH:2 bytes][SALT (if any)][ENCRYPTED_DATA]
    metadata_length = len(metadata_bytes)
    header = metadata_length.to_bytes(4, byteorder="big")

    # Add salt information if password-based encryption was used
    if salt:
        salt_header = len(salt).to_bytes(2, byteorder="big")
        output_data = header + metadata_bytes + salt_header + salt + encrypted_data
    else:
        salt_header = (0).to_bytes(2, byteorder="big")
        output_data = header + metadata_bytes + salt_header + encrypted_data

    # Write encrypted data with metadata to output file
    try:
        # Use secure file operations
        temp_output = output_path + ".tmp"
        with open(temp_output, "wb") as f:
            f.write(output_data)

        # Set secure file permissions
        os.chmod(temp_output, 0o600)  # Only owner can read/write

        # Rename for atomic operation
        os.replace(temp_output, output_path)
    except Exception as e:
        # Clean up partial file if encryption fails
        if os.path.exists(temp_output):
            try:
                os.unlink(temp_output)
            except Exception:
                pass
        # Log error securely
        logger.error(secure_log(f"Failed to write encrypted file: {str(e)}"))
        raise ValueError(
            f"Failed to write encrypted file: {secure_error_message(e, 'Encryption failed')}"
        )

    return output_path, key, salt


def decrypt_file(
    input_path: str,
    output_path: str,
    encryption_key: Optional[bytes] = None,
    password: Optional[str] = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Decrypt a file encrypted with enhanced Fernet encryption and extract metadata.

    This enhanced function supports both key-based and password-based decryption,
    and handles metadata embedded in the encrypted file.

    Args:
        input_path: Path to the encrypted file
        output_path: Path for the decrypted file
        encryption_key: The encryption key used to encrypt the file (or None if password is provided)
        password: Optional password to derive encryption key from

    Returns:
        Tuple of (decrypted_file_path, metadata)
    """
    # Validate paths
    is_valid, error = validate_path(input_path)
    if not is_valid:
        raise ValueError(f"Invalid input path: {error}")

    is_valid, error = validate_path(output_path)
    if not is_valid:
        raise ValueError(f"Invalid output path: {error}")

    # Read encrypted file with metadata and salt
    try:
        with open(input_path, "rb") as f:
            # Read metadata length (first 4 bytes)
            header = f.read(4)
            metadata_length = int.from_bytes(header, byteorder="big")

            # Read metadata
            metadata_bytes = f.read(metadata_length)
            metadata = json.loads(base64.b64decode(metadata_bytes).decode())

            # Read salt length (next 2 bytes)
            salt_header = f.read(2)
            salt_length = int.from_bytes(salt_header, byteorder="big")

            # Read salt if present
            salt = None
            if salt_length > 0:
                salt = f.read(salt_length)

            # Read encrypted data
            encrypted_data = f.read()
    except Exception as e:
        # For older files without the metadata header format, fallback to old format
        logger.warning(
            f"Could not read metadata from encrypted file, trying legacy format: {str(e)}"
        )
        try:
            with open(input_path, "rb") as f:
                encrypted_data = f.read()
            metadata = {}
            salt = None
        except Exception as e2:
            raise ValueError(f"Failed to read encrypted file: {str(e2)}")

    # Derive key from password if provided
    if password is not None and encryption_key is None:
        if not salt and metadata.get("has_password", False):
            raise ValueError(
                "Salt is required when decrypting with password, but no salt found in file"
            )

        encryption_key, _ = generate_encryption_key(password=password, salt=salt)
    elif encryption_key is None:
        raise ValueError("Either encryption_key or password must be provided")

    # Create cipher with key
    cipher = Fernet(encryption_key)

    # Decrypt data
    try:
        decrypted_data = cipher.decrypt(encrypted_data)
    except InvalidToken as e:
        # Provide a secure error message that doesn't reveal too much
        raise ValueError(
            secure_error_message(e, "Decryption failed: Invalid key or corrupted data")
        )
    except Exception as e:
        raise ValueError(secure_error_message(e, "Failed to decrypt file"))

    # Verify content hash if available in metadata
    if "content_hash" in metadata and "hash_algorithm" in metadata:
        if metadata["hash_algorithm"] == "sha256":
            content_hash = hashlib.sha256(decrypted_data).hexdigest()
            if content_hash != metadata["content_hash"]:
                raise ValueError(
                    "Integrity check failed: decrypted content hash does not match metadata"
                )

    # Write decrypted data to output file in a secure manner
    try:
        # Write to temporary file first, then rename for atomic operation
        temp_output = output_path + ".tmp"
        with open(temp_output, "wb") as f:
            f.write(decrypted_data)

        # Set secure permissions
        os.chmod(temp_output, 0o600)  # Only owner can read/write

        # Rename to final output file (atomic operation)
        os.replace(temp_output, output_path)
    except Exception as e:
        # Clean up temporary file if decryption fails
        if os.path.exists(temp_output):
            try:
                os.unlink(temp_output)
            except Exception:
                pass
        raise ValueError(secure_error_message(e, "Failed to write decrypted file"))

    return output_path, metadata


def secure_temp_file(prefix: str, suffix: str, permissions: int = 0o600) -> str:
    """
    Create a secure temporary file path with appropriate permissions.

    This function generates a secure random filename in a safe temporary directory,
    ensures the directory has proper permissions, and creates an empty file with
    secure permissions to reserve the filename.

    Args:
        prefix: Prefix for the temporary file
        suffix: Suffix for the temporary file (usually the extension)
        permissions: File permissions in octal format (default: 0o600 - owner read/write only)

    Returns:
        Path to the secure temporary file
    """
    # Get temporary directory with enhanced security
    temp_dir = os.path.join(os.path.expanduser("~"), ".cloudwan", "temp")

    # Ensure directory exists with secure permissions
    if not os.path.exists(temp_dir):
        # Create directory with secure permissions (0o700 - owner access only)
        os.makedirs(temp_dir, mode=0o700)
    elif os.path.isdir(temp_dir):
        # Update permissions if directory already exists
        try:
            os.chmod(temp_dir, 0o700)
        except Exception as e:
            logger.warning(secure_log(f"Failed to update temp directory permissions: {str(e)}"))

    # Generate secure random filename with additional entropy
    random_id = secrets.token_hex(32)  # Use 32 bytes (256 bits) of entropy
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{prefix}_{timestamp}_{random_id}{suffix}"

    # Create full path
    temp_path = os.path.join(temp_dir, filename)

    # Create an empty file with secure permissions to reserve the filename
    try:
        # Use tempfile's secure file creation to avoid race conditions
        with tempfile.NamedTemporaryFile(
            dir=temp_dir, prefix=f"{prefix}_{timestamp}_", suffix=suffix, delete=False
        ) as tf:
            temp_path = tf.name

        # Set secure permissions
        os.chmod(temp_path, permissions)
    except Exception as e:
        logger.warning(secure_log(f"Failed to create secure temp file: {str(e)}"))
        # Fall back to just returning the path without creating the file
        pass

    return temp_path


def compute_file_hash(file_path: str, algorithm: str = "sha256") -> str:
    """
    Compute the hash of a file.

    Args:
        file_path: Path to the file
        algorithm: Hash algorithm to use ('sha256', 'sha512', 'md5')

    Returns:
        Hexadecimal string representation of the file hash
    """
    # Validate path
    is_valid, error = validate_path(file_path)
    if not is_valid:
        raise ValueError(f"Invalid file path: {error}")

    # Choose hash algorithm
    if algorithm == "sha256":
        hash_obj = hashlib.sha256()
    elif algorithm == "sha512":
        hash_obj = hashlib.sha512()
    elif algorithm == "md5":
        hash_obj = hashlib.md5()
    else:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")

    # Compute hash in chunks to handle large files
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_obj.update(chunk)

    return hash_obj.hexdigest()


def create_integrity_signature(
    file_path: str, metadata: Dict[str, Any], hmac_key: Optional[bytes] = None
) -> Dict[str, str]:
    """
    Create integrity signature for a file and its metadata using HMAC for improved security.

    Args:
        file_path: Path to the file
        metadata: Dictionary containing metadata about the file
        hmac_key: Optional HMAC key for signature generation (generated if not provided)

    Returns:
        Dictionary with integrity information
    """
    # Validate path
    is_valid, error = validate_path(file_path)
    if not is_valid:
        raise ValueError(f"Invalid file path: {error}")

    # Generate HMAC key if not provided
    if hmac_key is None:
        hmac_key = secrets.token_bytes(32)  # 256-bit key

    # Compute file hash
    file_hash = compute_file_hash(file_path)

    # Convert metadata to string and compute hash
    metadata_str = json.dumps(metadata, sort_keys=True)
    metadata_hash = hashlib.sha256(metadata_str.encode()).hexdigest()

    # Create HMAC signature that covers both file hash and metadata hash
    combined = file_hash + metadata_hash
    hmac_signature = hmac.new(
        key=hmac_key, msg=combined.encode(), digestmod=hashlib.sha256
    ).hexdigest()

    # Create the current timestamp
    current_timestamp = datetime.now().isoformat()

    # Create unique signature ID for verification
    signature_id = secrets.token_hex(8)

    return {
        "file_hash": file_hash,
        "metadata_hash": metadata_hash,
        "integrity_signature": hmac_signature,
        "algorithm": "hmac-sha256",
        "timestamp": current_timestamp,
        "hmac_key_id": base64.b64encode(
            hashlib.sha256(hmac_key).digest()[:8]
        ).decode(),  # Key identifier
        "signature_id": signature_id,
        "version": "1.1",  # Signature version for future compatibility
    }


def verify_integrity_signature(
    file_path: str,
    metadata: Dict[str, Any],
    signature: Dict[str, str],
    hmac_key: Optional[bytes] = None,
) -> bool:
    """
    Verify the integrity signature of a file and its metadata with HMAC support.

    Args:
        file_path: Path to the file
        metadata: Dictionary containing metadata about the file
        signature: Dictionary with integrity information
        hmac_key: HMAC key for signature verification (required for HMAC signatures)

    Returns:
        True if the integrity signature is valid, False otherwise
    """
    # Validate path
    is_valid, error = validate_path(file_path)
    if not is_valid:
        raise ValueError(f"Invalid file path: {error}")

    # Check timestamp if available (prevent replay attacks)
    if "timestamp" in signature:
        try:
            sig_time = datetime.fromisoformat(signature["timestamp"])
            current_time = datetime.now()
            time_diff = (current_time - sig_time).total_seconds()

            # Warn about old signatures (over 90 days)
            if time_diff > 7776000:  # 90 days in seconds
                logger.warning(
                    f"Integrity signature is over 90 days old: {signature['timestamp']}. "
                    f"Consider refreshing the signature."
                )
        except (ValueError, TypeError):
            # Continue verification but log warning
            logger.warning(f"Invalid timestamp format in signature: {signature.get('timestamp')}.")

    # Check algorithm
    algorithm = signature.get("algorithm", "sha256")

    # Compute current file hash
    current_file_hash = compute_file_hash(file_path)

    # Check if file hash matches
    if current_file_hash != signature.get("file_hash"):
        logger.warning("File hash verification failed")
        return False

    # Convert metadata to string and compute hash
    if algorithm == "hmac-sha256":
        metadata_str = json.dumps(metadata, sort_keys=True)
    else:
        # Legacy format for backward compatibility
        metadata_str = str(sorted(metadata.items()))

    current_metadata_hash = hashlib.sha256(metadata_str.encode()).hexdigest()

    # Check if metadata hash matches
    if current_metadata_hash != signature.get("metadata_hash"):
        logger.warning("Metadata hash verification failed")
        return False

    # Combine hashes for full integrity check
    combined = current_file_hash + current_metadata_hash

    # Use appropriate verification method based on algorithm
    if algorithm == "hmac-sha256":
        # HMAC verification
        if hmac_key is None:
            logger.error("HMAC key required for HMAC signature verification")
            return False

        # Create HMAC signature
        current_hmac_signature = hmac.new(
            key=hmac_key, msg=combined.encode(), digestmod=hashlib.sha256
        ).hexdigest()

        # Constant-time comparison to prevent timing attacks
        return hmac.compare_digest(current_hmac_signature, signature.get("integrity_signature", ""))
    else:
        # Standard hash verification for backward compatibility
        current_integrity_hash = hashlib.sha256(combined.encode()).hexdigest()
        return current_integrity_hash == signature.get("integrity_signature")


def sanitize_input(input_data: Any, max_length: Optional[int] = None) -> Any:
    """
    Sanitize user input to prevent injection attacks.

    Args:
        input_data: Data to sanitize (string, list, dict, etc.)
        max_length: Optional maximum length for string inputs

    Returns:
        Sanitized data of the same type
    """
    if input_data is None:
        return None

    if isinstance(input_data, str):
        # Trim whitespace
        sanitized = input_data.strip()

        # Apply maximum length if specified
        if max_length is not None and len(sanitized) > max_length:
            sanitized = sanitized[:max_length]

        # Escape special characters for path safety
        sanitized = re.sub(r'[\\/:*?"<>|]', "_", sanitized)

        # Remove potentially harmful character sequences
        sanitized = sanitized.replace("../", "")
        sanitized = sanitized.replace("..\\", "")
        sanitized = sanitized.replace("%25", "")
        sanitized = sanitized.replace("&#", "")

        return sanitized

    elif isinstance(input_data, (int, float, bool)):
        # Numeric and boolean values don't need sanitization
        return input_data

    elif isinstance(input_data, list):
        # Recursively sanitize list elements
        return [sanitize_input(item, max_length) for item in input_data]

    elif isinstance(input_data, dict):
        # Recursively sanitize dictionary items
        return {sanitize_input(k): sanitize_input(v, max_length) for k, v in input_data.items()}

    # For other types, return as-is
    return input_data


def secure_delete_file(file_path: str) -> bool:
    """
    Securely delete a file by overwriting its contents before unlinking.

    Args:
        file_path: Path to the file to delete

    Returns:
        True if deletion was successful, False otherwise
    """
    # Validate path
    is_valid, error = validate_path(file_path)
    if not is_valid:
        logger.error(f"Invalid path for secure deletion: {error}")
        return False

    try:
        if os.path.exists(file_path) and os.path.isfile(file_path):
            # Get file size
            file_size = os.path.getsize(file_path)

            # Skip secure deletion for large files
            if file_size > MAX_IN_MEMORY_SIZE:
                logger.warning(
                    f"File too large for secure deletion, using standard deletion: {file_path}"
                )
                os.unlink(file_path)
                return True

            # Overwrite file with random data multiple times
            with open(file_path, "wb") as f:
                # First pass: zeros
                f.seek(0)
                f.write(b"\x00" * file_size)
                f.flush()
                os.fsync(f.fileno())

                # Second pass: ones
                f.seek(0)
                f.write(b"\xff" * file_size)
                f.flush()
                os.fsync(f.fileno())

                # Third pass: random data
                f.seek(0)
                f.write(os.urandom(file_size))
                f.flush()
                os.fsync(f.fileno())

            # Finally unlink the file
            os.unlink(file_path)
            return True
        elif os.path.exists(file_path):
            logger.warning(f"Not a file, cannot securely delete: {file_path}")
            return False
        else:
            logger.info(f"File does not exist, nothing to delete: {file_path}")
            return True
    except Exception as e:
        logger.error(f"Failed to securely delete file {file_path}: {str(e)}")
        # Attempt standard deletion as fallback
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                return True
        except Exception:
            pass
        return False


def secure_error_message(error: Exception, public_message: str) -> str:
    """
    Create a secure error message that doesn't reveal sensitive information.

    Args:
        error: The exception that occurred
        public_message: A generic message safe for user display

    Returns:
        A sanitized error message string
    """
    # Generate an error ID to help with debugging without revealing details
    error_id = secrets.token_hex(6)

    # Log the full error details for debugging
    logger.error(f"Error ID {error_id}: {str(error)}", exc_info=True)

    # Return a sanitized message for the user
    return f"{public_message} (Error ID: {error_id})"


def secure_log(message: str) -> str:
    """
    Filter sensitive information from log messages.

    Args:
        message: The message to log

    Returns:
        Sanitized message with sensitive data redacted
    """
    if not message or not isinstance(message, str):
        return str(message)

    # Make a copy of the message to avoid modifying the original
    sanitized_message = message

    # Replace sensitive information with redacted markers
    for pattern in SENSITIVE_PATTERNS:
        # Case-insensitive pattern with word boundaries
        regex = re.compile(f"({pattern}\\s*[=:]\\s*[^\\s,]+)", re.IGNORECASE)
        sanitized_message = regex.sub("\\1=***REDACTED***", sanitized_message)

    return sanitized_message
