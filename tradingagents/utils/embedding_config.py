"""
Embedding Configuration and Utility Module

This module provides centralized configuration and utility functions for
text embedding services, specifically focusing on DashScope (Alibaba Cloud) integration.
It handles model selection, API calls, error handling, and response parsing.
"""

import os
import logging
from typing import Dict, Any, Optional, Tuple, List, Union

# Configure logger
logger = logging.getLogger("utils.embedding_config")

def get_dashscope_embedding_model() -> str:
    """
    Get the configured DashScope embedding model ID.
    
    Returns:
        str: Model ID from environment variable DASHSCOPE_EMBEDDING_MODEL,
             defaults to 'text-embedding-v3' if not set.
    """
    return os.getenv('DASHSCOPE_EMBEDDING_MODEL', 'text-embedding-v3')

def is_length_limit_error(error_or_response: Union[str, Any]) -> bool:
    """
    Check if the error or response indicates a text length limit violation.
    
    Args:
        error_or_response: Error message string or response object
        
    Returns:
        bool: True if it's a length limit error, False otherwise
    """
    error_str = str(error_or_response).lower()
    keywords = ['length', 'token', 'limit', 'exceed', 'too long', 'input too large']
    return any(keyword in error_str for keyword in keywords)

def is_dashscope_success(response: Any) -> bool:
    """
    Check if DashScope API response indicates success.
    
    Args:
        response: DashScope API response object
        
    Returns:
        bool: True if status is 200 (OK), False otherwise
    """
    # DashScope response object uses .status_code in some versions and .status in others
    # We check status_code first as it seems more reliable in current version
    try:
        if hasattr(response, 'status_code'):
            return response.status_code == 200
        elif hasattr(response, 'status'):
            return response.status == 200
    except Exception:
        # Fallback for dictionary-like access if attribute access fails
        try:
            if 'status_code' in response:
                return response['status_code'] == 200
            if 'status' in response:
                return response['status'] == 200
        except Exception:
            pass
            
    return False

def extract_embedding_from_response(response: Any) -> List[float]:
    """
    Safely extract embedding vector from DashScope response.
    
    Args:
        response: DashScope API response object
        
    Returns:
        List[float]: The embedding vector
        
    Raises:
        ValueError: If response format is invalid or missing embeddings
    """
    try:
        if hasattr(response, 'output') and 'embeddings' in response.output:
            embeddings = response.output['embeddings']
            if embeddings and len(embeddings) > 0 and 'embedding' in embeddings[0]:
                return embeddings[0]['embedding']
    except Exception as e:
        logger.error(f"Failed to extract embedding from response: {e}")
    
    raise ValueError("Invalid response format: missing embedding data")

def format_dashscope_error(response: Any) -> str:
    """
    Format error message from DashScope response.
    
    Args:
        response: DashScope API response object
        
    Returns:
        str: Formatted error message
    """
    code = getattr(response, 'code', 'Unknown')
    message = getattr(response, 'message', 'No error message provided')
    return f"{code} - {message}"

def call_dashscope_embedding(
    text: str, 
    model: Optional[str] = None, 
    api_key: Optional[str] = None
) -> Tuple[bool, Optional[List[float]], Optional[str]]:
    """
    Unified DashScope embedding API call with proper error handling.
    
    Args:
        text: Input text to embed
        model: Optional model ID override. If None, uses configured default.
        api_key: Optional API key override. If None, uses environment variable.
        
    Returns:
        Tuple containing:
        - success (bool): Whether the call was successful
        - result (List[float] or None): Embedding vector if successful, None otherwise
        - error_msg (str or None): Error message if failed, None otherwise
    """
    # Determine model
    if not model:
        model = get_dashscope_embedding_model()
        
    # Check API key
    if not api_key:
        api_key = os.getenv('DASHSCOPE_API_KEY')
        
    if not api_key:
        return False, None, "DashScope API key not configured"
        
    try:
        import dashscope
        from dashscope import TextEmbedding
        
        # Set API key
        dashscope.api_key = api_key
        
        # Call API
        response = TextEmbedding.call(
            model=model,
            input=text
        )
        
        # Check success
        if is_dashscope_success(response):
            try:
                embedding = extract_embedding_from_response(response)
                return True, embedding, None
            except ValueError as e:
                return False, None, str(e)
        else:
            error_msg = format_dashscope_error(response)
            return False, None, error_msg
            
    except ImportError:
        return False, None, "dashscope package not installed"
    except Exception as e:
        return False, None, str(e)

def test_dashscope_embedding(
    api_key: Optional[str] = None, 
    model: Optional[str] = None, 
    test_text: str = "测试文本"
) -> Tuple[bool, str]:
    """
    Test DashScope embedding API availability.
    
    Args:
        api_key: Optional API key. If None, reads from env.
        model: Optional model ID. If None, reads from env.
        test_text: Text to use for testing.
        
    Returns:
        Tuple containing:
        - success (bool): Whether the test passed
        - message (str): Status message or error details
    """
    # Use the unified call function
    success, result, error_msg = call_dashscope_embedding(test_text, model, api_key)
    
    if success:
        dim = len(result) if result else 0
        return True, f"✅ DashScope API测试成功 (模型: {model or get_dashscope_embedding_model()}, 维度: {dim})"
    else:
        return False, f"❌ DashScope API测试失败: {error_msg}"
