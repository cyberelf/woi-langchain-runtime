"""File manipulation tools plugin.

This plugin provides secure file operations including reading, writing, 
searching, and basic file management operations.
"""

import os
import re
import logging
from pathlib import Path
from typing import Optional, List, Any
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Security configuration
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {
    '.txt', '.md', '.py', '.js', '.ts', '.json', '.yaml', '.yml', 
    '.csv', '.log', '.html', '.css', '.xml', '.sql', '.sh', '.bat'
}
BLOCKED_PATHS = {
    '/etc', '/bin', '/sbin', '/usr/bin', '/usr/sbin', '/root',
    '/sys', '/proc', '/dev', '/var/log', '/var/run'
}


class FileSecurityError(Exception):
    """Raised when file operation violates security constraints."""
    pass


def validate_file_path(file_path: str, operation: str = "access") -> Path:
    """Validate file path for security constraints.
    
    Args:
        file_path: The file path to validate
        operation: The operation being performed (access, create, delete)
        
    Returns:
        Validated Path object
        
    Raises:
        FileSecurityError: If path violates security constraints
    """
    try:
        # Convert to absolute path and resolve any symlinks/relative components
        path = Path(file_path).resolve()
        
        # Check for blocked paths
        path_str = str(path)
        for blocked in BLOCKED_PATHS:
            if path_str.startswith(blocked):
                raise FileSecurityError(f"Access to {blocked} is not allowed")
        
        # Check file extension for create operations
        if operation in ["create", "write"] and path.suffix.lower() not in ALLOWED_EXTENSIONS:
            raise FileSecurityError(f"File extension {path.suffix} is not allowed")
        
        # Check if path tries to escape working directory (additional security)
        try:
            cwd = Path.cwd().resolve()
            path.relative_to(cwd)
        except ValueError:
            # Path is outside current working directory - could be ok for read operations
            if operation in ["create", "write", "delete"]:
                raise FileSecurityError("Cannot modify files outside working directory")
        
        return path
    
    except Exception as e:
        if isinstance(e, FileSecurityError):
            raise
        raise FileSecurityError(f"Invalid file path: {e}")


def validate_file_size(file_path: Path) -> None:
    """Validate file size constraints.
    
    Args:
        file_path: Path to the file
        
    Raises:
        FileSecurityError: If file exceeds size limits
    """
    try:
        size = file_path.stat().st_size
        if size > MAX_FILE_SIZE:
            raise FileSecurityError(f"File size {size} exceeds maximum allowed size {MAX_FILE_SIZE}")
    except FileNotFoundError:
        # File doesn't exist yet - ok for create operations
        pass
    except Exception as e:
        raise FileSecurityError(f"Cannot check file size: {e}")


class ReadLinesInput(BaseModel):
    """Input schema for read_lines tool."""
    filename: str = Field(..., description="Path to the file to read")
    start: Optional[int] = Field(1, description="Starting line number (1-based, inclusive)")
    end: Optional[int] = Field(None, description="Ending line number (1-based, inclusive)")


class ReadLinesTool(BaseTool):
    """Tool to read specific lines from a file."""
    
    name: str = "read_lines"
    description: str = "Read specific lines from a file. Provide filename and optionally start/end line numbers."
    args_schema: type[BaseModel] = ReadLinesInput
    
    __version__ = "1.0.0"
    
    def _run(self, filename: str, start: Optional[int] = 1, end: Optional[int] = None) -> str:
        """Read lines from a file.
        
        Args:
            filename: Path to the file
            start: Starting line number (1-based, inclusive)
            end: Ending line number (1-based, inclusive)
            
        Returns:
            Content of the specified lines
        """
        try:
            # Validate path
            file_path = validate_file_path(filename, "access")
            
            # Check if file exists
            if not file_path.exists():
                return f"Error: File '{filename}' does not exist"
            
            # Validate file size
            validate_file_size(file_path)
            
            # Read file
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Handle line range
            total_lines = len(lines)
            start_idx = max(0, (start or 1) - 1)  # Convert to 0-based
            end_idx = min(total_lines, end) if end else total_lines
            
            if start_idx >= total_lines:
                return f"Error: Start line {start} exceeds file length ({total_lines} lines)"
            
            selected_lines = lines[start_idx:end_idx]
            result = ''.join(selected_lines)
            
            logger.info(f"Read {len(selected_lines)} lines from {filename} (lines {start_idx+1}-{end_idx})")
            return result
            
        except FileSecurityError as e:
            logger.warning(f"Security violation in read_lines: {e}")
            return f"Error: {e}"
        except UnicodeDecodeError:
            return f"Error: File '{filename}' is not a valid text file (encoding issue)"
        except Exception as e:
            logger.error(f"Error reading file {filename}: {e}")
            return f"Error reading file: {e}"


class GrepFileInput(BaseModel):
    """Input schema for grep_file tool."""
    filename: str = Field(..., description="Path to the file to search")
    pattern: str = Field(..., description="Regular expression pattern to search for")
    ignore_case: Optional[bool] = Field(False, description="Whether to ignore case in matching")
    line_numbers: Optional[bool] = Field(True, description="Whether to include line numbers in output")


class GrepFileTool(BaseTool):
    """Tool to search for patterns in a file using regular expressions."""
    
    name: str = "grep_file"
    description: str = "Search for a regular expression pattern in a file and return matching lines."
    args_schema: type[BaseModel] = GrepFileInput
    
    __version__ = "1.0.0"
    
    def _run(self, filename: str, pattern: str, ignore_case: bool = False, line_numbers: bool = True) -> str:
        """Search for pattern in file.
        
        Args:
            filename: Path to the file
            pattern: Regular expression pattern to search
            ignore_case: Whether to ignore case
            line_numbers: Whether to include line numbers
            
        Returns:
            Matching lines with optional line numbers
        """
        try:
            # Validate path
            file_path = validate_file_path(filename, "access")
            
            # Check if file exists
            if not file_path.exists():
                return f"Error: File '{filename}' does not exist"
            
            # Validate file size
            validate_file_size(file_path)
            
            # Compile regex pattern
            flags = re.IGNORECASE if ignore_case else 0
            try:
                regex = re.compile(pattern, flags)
            except re.error as e:
                return f"Error: Invalid regular expression pattern: {e}"
            
            # Search file
            matches = []
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if regex.search(line):
                        if line_numbers:
                            matches.append(f"{line_num}: {line.rstrip()}")
                        else:
                            matches.append(line.rstrip())
            
            if matches:
                result = '\n'.join(matches)
                logger.info(f"Found {len(matches)} matches for pattern '{pattern}' in {filename}")
                return result
            else:
                return f"No matches found for pattern '{pattern}' in {filename}"
                
        except FileSecurityError as e:
            logger.warning(f"Security violation in grep_file: {e}")
            return f"Error: {e}"
        except UnicodeDecodeError:
            return f"Error: File '{filename}' is not a valid text file (encoding issue)"
        except Exception as e:
            logger.error(f"Error searching file {filename}: {e}")
            return f"Error searching file: {e}"


class CreateFileInput(BaseModel):
    """Input schema for create_file tool."""
    filename: str = Field(..., description="Path to the file to create")
    content: str = Field(..., description="Content to write to the file")
    overwrite: Optional[bool] = Field(False, description="Whether to overwrite existing file")


class CreateFileTool(BaseTool):
    """Tool to create a new file with specified content."""
    
    name: str = "create_file"
    description: str = "Create a new file with specified content. Use overwrite=true to replace existing files."
    args_schema: type[BaseModel] = CreateFileInput
    
    __version__ = "1.0.0"
    
    def _run(self, filename: str, content: str, overwrite: bool = False) -> str:
        """Create file with content.
        
        Args:
            filename: Path to the file to create
            content: Content to write
            overwrite: Whether to overwrite existing file
            
        Returns:
            Success or error message
        """
        try:
            # Validate path
            file_path = validate_file_path(filename, "create")
            
            # Check if file exists and overwrite policy
            if file_path.exists() and not overwrite:
                return f"Error: File '{filename}' already exists. Use overwrite=true to replace it."
            
            # Create parent directories if they don't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            file_size = len(content.encode('utf-8'))
            logger.info(f"Created file {filename} with {file_size} bytes")
            return f"Successfully created file '{filename}' with {file_size} bytes"
            
        except FileSecurityError as e:
            logger.warning(f"Security violation in create_file: {e}")
            return f"Error: {e}"
        except Exception as e:
            logger.error(f"Error creating file {filename}: {e}")
            return f"Error creating file: {e}"


class DeleteFileInput(BaseModel):
    """Input schema for delete_file tool."""
    filename: str = Field(..., description="Path to the file to delete")
    confirm: Optional[bool] = Field(False, description="Confirmation flag to prevent accidental deletion")


class DeleteFileTool(BaseTool):
    """Tool to delete a file."""
    
    name: str = "delete_file"
    description: str = "Delete a file. Requires confirm=true to prevent accidental deletion."
    args_schema: type[BaseModel] = DeleteFileInput
    
    __version__ = "1.0.0"
    
    def _run(self, filename: str, confirm: bool = False) -> str:
        """Delete file.
        
        Args:
            filename: Path to the file to delete
            confirm: Confirmation flag
            
        Returns:
            Success or error message
        """
        try:
            # Require confirmation
            if not confirm:
                return f"Error: Deletion requires confirm=true. File '{filename}' was not deleted."
            
            # Validate path
            file_path = validate_file_path(filename, "delete")
            
            # Check if file exists
            if not file_path.exists():
                return f"Error: File '{filename}' does not exist"
            
            # Check if it's actually a file (not directory)
            if not file_path.is_file():
                return f"Error: '{filename}' is not a file"
            
            # Delete file
            file_path.unlink()
            
            logger.info(f"Deleted file {filename}")
            return f"Successfully deleted file '{filename}'"
            
        except FileSecurityError as e:
            logger.warning(f"Security violation in delete_file: {e}")
            return f"Error: {e}"
        except Exception as e:
            logger.error(f"Error deleting file {filename}: {e}")
            return f"Error deleting file: {e}"
