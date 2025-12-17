"""
Custom Model Service for using external model via ngrok.

This service provides a LangChain-compatible interface to interact with
a custom model hosted on Google Colab and exposed via ngrok.
"""

import httpx
from typing import Any, Dict, List, Optional, Iterator
from langchain_core.language_models.llms import LLM
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.outputs import GenerationChunk
from pydantic import Field


class CustomModelLLM(LLM):
    """
    Custom LLM wrapper for external model via ngrok.
    
    This class implements the LangChain LLM interface to work with
    a custom model hosted externally and accessed via ngrok URL.
    """
    
    base_url: str = Field(description="Base URL of the ngrok endpoint")
    model_name: str = Field(default="custom-model", description="Name of the model")
    temperature: float = Field(default=0.7, description="Temperature for generation")
    max_tokens: int = Field(default=2048, description="Maximum tokens to generate")
    timeout: int = Field(default=60, description="Request timeout in seconds")
    
    @property
    def _llm_type(self) -> str:
        """Return identifier for this LLM."""
        return "custom_model"
    
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """
        Call the custom model API.
        
        Args:
            prompt: The prompt to send to the model
            stop: Optional list of stop sequences
            run_manager: Optional callback manager
            **kwargs: Additional arguments
            
        Returns:
            str: Generated text from the model
        """
        try:
            # Prepare the request payload
            payload = {
                "prompt": prompt,
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            }
            
            if stop:
                payload["stop"] = stop
            
            # Make the API request
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/generate",
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "ngrok-skip-browser-warning": "true"  # Skip ngrok browser warning
                    }
                )
                response.raise_for_status()
                
                # Parse the response
                result = response.json()
                
                # Debug: Print the raw response
                print(f"🔍 DEBUG - Raw response from server:")
                print(f"   Type: {type(result)}")
                print(f"   Content: {result}")
                
                # Extract generated text (try multiple possible keys)
                generated_text = ""
                
                if isinstance(result, dict):
                    # Try common response keys
                    generated_text = (
                        result.get("generated_text") or 
                        result.get("text") or 
                        result.get("response") or
                        result.get("output") or
                        result.get("result") or
                        result.get("answer") or
                        result.get("completion") or
                        ""
                    )
                    
                    # If still empty, check if there's a nested structure
                    if not generated_text and "data" in result:
                        data = result["data"]
                        if isinstance(data, dict):
                            generated_text = (
                                data.get("generated_text") or 
                                data.get("text") or 
                                data.get("response") or
                                ""
                            )
                        elif isinstance(data, str):
                            generated_text = data
                    
                    # If still empty, print all keys to help debug
                    if not generated_text:
                        print(f"⚠️  WARNING - Could not find text in response. Available keys: {list(result.keys())}")
                        # As a last resort, try to get any string value
                        for key, value in result.items():
                            if isinstance(value, str) and len(value) > 10:
                                generated_text = value
                                print(f"   Using value from key '{key}': {value[:100]}...")
                                break
                
                elif isinstance(result, str):
                    generated_text = result
                else:
                    generated_text = str(result)
                
                print(f"✅ Extracted text: {generated_text[:100] if generated_text else '(empty)'}...")
                
                return generated_text
                
        except httpx.TimeoutException:
            return "Error: Request timed out. The model took too long to respond."
        except httpx.HTTPStatusError as e:
            return f"Error: HTTP {e.response.status_code} - {e.response.text}"
        except Exception as e:
            return f"Error calling custom model: {str(e)}"
    
    async def _acall(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """
        Async call to the custom model API.
        
        Args:
            prompt: The prompt to send to the model
            stop: Optional list of stop sequences
            run_manager: Optional callback manager
            **kwargs: Additional arguments
            
        Returns:
            str: Generated text from the model
        """
        try:
            # Prepare the request payload
            payload = {
                "prompt": prompt,
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            }
            
            if stop:
                payload["stop"] = stop
            
            # Make the async API request
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/generate",
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "ngrok-skip-browser-warning": "true"  # Skip ngrok browser warning
                    }
                )
                response.raise_for_status()
                
                # Parse the response
                result = response.json()
                
                # Debug: Print the raw response
                print(f"🔍 DEBUG - Raw response from server (async):")
                print(f"   Type: {type(result)}")
                print(f"   Content: {result}")
                
                # Extract generated text (try multiple possible keys)
                generated_text = ""
                
                if isinstance(result, dict):
                    # Try common response keys
                    generated_text = (
                        result.get("generated_text") or 
                        result.get("text") or 
                        result.get("response") or
                        result.get("output") or
                        result.get("result") or
                        result.get("answer") or
                        result.get("completion") or
                        ""
                    )
                    
                    # If still empty, check if there's a nested structure
                    if not generated_text and "data" in result:
                        data = result["data"]
                        if isinstance(data, dict):
                            generated_text = (
                                data.get("generated_text") or 
                                data.get("text") or 
                                data.get("response") or
                                ""
                            )
                        elif isinstance(data, str):
                            generated_text = data
                    
                    # If still empty, print all keys to help debug
                    if not generated_text:
                        print(f"⚠️  WARNING - Could not find text in response. Available keys: {list(result.keys())}")
                        # As a last resort, try to get any string value
                        for key, value in result.items():
                            if isinstance(value, str) and len(value) > 10:
                                generated_text = value
                                print(f"   Using value from key '{key}': {value[:100]}...")
                                break
                
                elif isinstance(result, str):
                    generated_text = result
                else:
                    generated_text = str(result)
                
                print(f"✅ Extracted text: {generated_text[:100] if generated_text else '(empty)'}...")
                
                return generated_text
                
        except httpx.TimeoutException:
            return "Error: Request timed out. The model took too long to respond."
        except httpx.HTTPStatusError as e:
            return f"Error: HTTP {e.response.status_code} - {e.response.text}"
        except Exception as e:
            return f"Error calling custom model: {str(e)}"
    
    @property
    def _identifying_params(self) -> Dict[str, Any]:
        """Return identifying parameters for this LLM."""
        return {
            "base_url": self.base_url,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }


def get_custom_model(
    base_url: str,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    timeout: int = 60
) -> CustomModelLLM:
    """
    Factory function to create a custom model instance.
    
    Args:
        base_url: Base URL of the ngrok endpoint
        temperature: Temperature for generation (default: 0.7)
        max_tokens: Maximum tokens to generate (default: 2048)
        timeout: Request timeout in seconds (default: 60)
        
    Returns:
        CustomModelLLM: Configured custom model instance
    """
    return CustomModelLLM(
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout
    )
