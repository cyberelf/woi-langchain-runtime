"""Web interaction tools for agent functionality.

This module provides secure web operations including URL fetching,
content downloading, and basic web interaction capabilities.
"""

import os
import tempfile
import logging
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse, urljoin
import aiohttp
import asyncio
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)

# Security configuration
MAX_CONTENT_SIZE = 50 * 1024 * 1024  # 50MB
REQUEST_TIMEOUT = 30  # seconds
MAX_REDIRECTS = 5
ALLOWED_SCHEMES = {'http', 'https'}
BLOCKED_DOMAINS = {
    'localhost', '127.0.0.1', '::1', '0.0.0.0',
    '169.254.169.254',  # AWS metadata service
    '10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'  # Private networks
}
ALLOWED_CONTENT_TYPES = {
    'text/plain', 'text/html', 'text/css', 'text/javascript',
    'application/json', 'application/xml', 'text/xml',
    'application/pdf', 'text/markdown', 'text/csv',
    'application/javascript', 'application/x-javascript'
}


class WebSecurityError(Exception):
    """Raised when web operation violates security constraints."""
    pass


def validate_url(url: str) -> str:
    """Validate URL for security constraints.
    
    Args:
        url: The URL to validate
        
    Returns:
        Validated URL string
        
    Raises:
        WebSecurityError: If URL violates security constraints
    """
    try:
        parsed = urlparse(url)
        
        # Check scheme
        if parsed.scheme not in ALLOWED_SCHEMES:
            raise WebSecurityError(f"Scheme {parsed.scheme} is not allowed")
        
        # Check for blocked domains
        hostname = parsed.hostname
        if hostname:
            hostname_lower = hostname.lower()
            for blocked in BLOCKED_DOMAINS:
                if hostname_lower == blocked or hostname_lower.endswith('.' + blocked):
                    raise WebSecurityError(f"Domain {hostname} is blocked")
        
        # Reconstruct URL to normalize it
        return parsed.geturl()
        
    except Exception as e:
        if isinstance(e, WebSecurityError):
            raise
        raise WebSecurityError(f"Invalid URL: {e}")


def is_content_type_allowed(content_type: str) -> bool:
    """Check if content type is allowed.
    
    Args:
        content_type: The content type to check
        
    Returns:
        True if content type is allowed
    """
    if not content_type:
        return False
    
    # Extract main content type (ignore charset, etc.)
    main_type = content_type.split(';')[0].strip().lower()
    return main_type in ALLOWED_CONTENT_TYPES


class FetchUrlInput(BaseModel):
    """Input schema for fetch_url tool."""
    url: str = Field(..., description="URL to fetch content from")
    save_to_file: Optional[bool] = Field(True, description="Whether to save content to a temporary file")
    follow_redirects: Optional[bool] = Field(True, description="Whether to follow HTTP redirects")
    headers: Optional[Dict[str, str]] = Field(default_factory=dict, description="Additional HTTP headers")


class FetchUrlTool(BaseTool):
    """Tool to fetch content from a URL and optionally save to file."""
    
    name: str = "fetch_url"
    description: str = "Fetch content from a URL and save to a temporary file or return directly."
    args_schema: type[BaseModel] = FetchUrlInput
    
    def _run(self, url: str, save_to_file: bool = True, follow_redirects: bool = True, headers: Optional[Dict[str, str]] = None) -> str:
        """Fetch URL content.
        
        Args:
            url: URL to fetch
            save_to_file: Whether to save to temporary file
            follow_redirects: Whether to follow redirects
            headers: Additional headers to send
            
        Returns:
            Content or file path information
        """
        # Run async function in sync context
        return asyncio.run(self._async_run(url, save_to_file, follow_redirects, headers or {}))
    
    async def _async_run(self, url: str, save_to_file: bool, follow_redirects: bool, headers: Dict[str, str]) -> str:
        """Async implementation of URL fetching."""
        try:
            # Validate URL
            validated_url = validate_url(url)
            
            # Set up session configuration
            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            connector = aiohttp.TCPConnector(limit_per_host=1)
            
            # Default headers
            default_headers = {
                'User-Agent': 'LangChain-Agent-Runtime/1.0',
                'Accept': ', '.join(ALLOWED_CONTENT_TYPES),
                'Accept-Encoding': 'gzip, deflate'
            }
            default_headers.update(headers)
            
            async with aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers=default_headers
            ) as session:
                
                # Configure redirect behavior
                max_redirects = MAX_REDIRECTS if follow_redirects else 0
                
                async with session.get(
                    validated_url,
                    allow_redirects=follow_redirects,
                    max_redirects=max_redirects
                ) as response:
                    
                    # Check response status
                    if response.status >= 400:
                        return f"Error: HTTP {response.status} - {response.reason}"
                    
                    # Check content type
                    content_type = response.headers.get('content-type', '')
                    if not is_content_type_allowed(content_type):
                        return f"Error: Content type '{content_type}' is not allowed"
                    
                    # Check content length
                    content_length = response.headers.get('content-length')
                    if content_length and int(content_length) > MAX_CONTENT_SIZE:
                        return f"Error: Content size {content_length} exceeds maximum {MAX_CONTENT_SIZE}"
                    
                    # Read content with size limit
                    content = b''
                    async for chunk in response.content.iter_chunked(8192):
                        content += chunk
                        if len(content) > MAX_CONTENT_SIZE:
                            return f"Error: Content size exceeds maximum {MAX_CONTENT_SIZE}"
                    
                    # Decode content
                    try:
                        text_content = content.decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            text_content = content.decode('latin-1')
                        except UnicodeDecodeError:
                            return "Error: Could not decode content as text"
                    
                    # Handle response
                    if save_to_file:
                        # Save to temporary file
                        temp_dir = Path(tempfile.gettempdir()) / "langchain_agent_downloads"
                        temp_dir.mkdir(exist_ok=True)
                        
                        # Generate safe filename
                        url_hash = hashlib.md5(validated_url.encode()).hexdigest()[:8]
                        parsed_url = urlparse(validated_url)
                        filename = f"{parsed_url.netloc}_{url_hash}.txt"
                        
                        temp_file = temp_dir / filename
                        
                        # Write content to file
                        with open(temp_file, 'w', encoding='utf-8') as f:
                            f.write(text_content)
                        
                        file_size = len(content)
                        logger.info(f"Fetched URL {url} and saved to {temp_file} ({file_size} bytes)")
                        
                        return (f"Successfully fetched URL and saved to: {temp_file}\n"
                               f"Content-Type: {content_type}\n"
                               f"Size: {file_size} bytes\n"
                               f"Status: {response.status} {response.reason}")
                    else:
                        # Return content directly (limited for large content)
                        if len(text_content) > 10000:  # 10KB limit for direct return
                            preview = text_content[:10000] + "\n\n... (content truncated, use save_to_file=true for full content)"
                            return (f"Content-Type: {content_type}\n"
                                   f"Size: {len(content)} bytes\n"
                                   f"Status: {response.status} {response.reason}\n\n"
                                   f"{preview}")
                        else:
                            return (f"Content-Type: {content_type}\n"
                                   f"Size: {len(content)} bytes\n"
                                   f"Status: {response.status} {response.reason}\n\n"
                                   f"{text_content}")
                        
        except WebSecurityError as e:
            logger.warning(f"Security violation in fetch_url: {e}")
            return f"Error: {e}"
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error fetching {url}: {e}")
            return f"Error: HTTP request failed - {e}"
        except asyncio.TimeoutError:
            return f"Error: Request timeout after {REQUEST_TIMEOUT} seconds"
        except Exception as e:
            logger.error(f"Error fetching URL {url}: {e}")
            return f"Error fetching URL: {e}"


class ParseUrlInput(BaseModel):
    """Input schema for parse_url tool."""
    url: str = Field(..., description="URL to parse and analyze")


class ParseUrlTool(BaseTool):
    """Tool to parse and analyze URL structure."""
    
    name: str = "parse_url"
    description: str = "Parse a URL and return its components (scheme, domain, path, etc.)"
    args_schema: type[BaseModel] = ParseUrlInput
    
    def _run(self, url: str) -> str:
        """Parse URL and return components.
        
        Args:
            url: URL to parse
            
        Returns:
            URL component information
        """
        try:
            parsed = urlparse(url)
            
            components = {
                'url': url,
                'scheme': parsed.scheme,
                'netloc': parsed.netloc,
                'hostname': parsed.hostname,
                'port': parsed.port,
                'path': parsed.path,
                'params': parsed.params,
                'query': parsed.query,
                'fragment': parsed.fragment
            }
            
            # Format output
            result = "URL Components:\n"
            for key, value in components.items():
                if value:
                    result += f"  {key}: {value}\n"
            
            # Security check
            try:
                validate_url(url)
                result += "\nSecurity: URL appears safe for fetching"
            except WebSecurityError as e:
                result += f"\nSecurity Warning: {e}"
            
            return result
            
        except Exception as e:
            return f"Error parsing URL: {e}"


# Tool registry for web tools
WEB_TOOLS = [
    FetchUrlTool(),
    ParseUrlTool(),
]


def get_web_tools() -> list[BaseTool]:
    """Get all web interaction tools.
    
    Returns:
        List of web interaction tools
    """
    return WEB_TOOLS.copy()
