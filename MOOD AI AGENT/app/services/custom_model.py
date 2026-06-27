from langchain_core.language_models.llms import LLM
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from pydantic import Field
from typing import List, Dict, Any, Optional
import httpx

class CustomModelLLM(LLM):
    """
    Custom LLM wrapper for external model via ngrok.
    """
    base_url: str = Field(description="Base URL of the ngrok endpoint")
    model_name: str = Field(default="custom-model", description="Name of the model")
    temperature: float = Field(default=0.7, description="Temperature for generation")
    max_tokens: int = Field(default=2048, description="Maximum tokens to generate")
    timeout: int = Field(default=60, description="Request timeout in seconds")
    
    @property
    def _llm_type(self) -> str:
        return "custom_model"
        
    def _extract_text(self, result: Any, is_async: bool = False) -> str:
        label = " (async)" if is_async else ""
        print(f"🔍 DEBUG - Raw response from server{label}:")
        print(f"   Type: {type(result)}")
        print(f"   Content: {result}")
        
        generated_text = ""
        if isinstance(result, dict):
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
                    
            if not generated_text:
                print(f"⚠️  WARNING - Model returned empty response")
                generated_text = ""
        elif isinstance(result, str):
            generated_text = result
        else:
            generated_text = str(result)
            
        print(f"✅ Extracted text: {generated_text[:100] if generated_text else '(empty)'}...")
        return generated_text
        
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        try:
            payload = {
                "prompt": prompt,
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            }
            if stop:
                payload["stop"] = stop
                
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/generate",
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "ngrok-skip-browser-warning": "true"
                    }
                )
                response.raise_for_status()
                return self._extract_text(response.json(), is_async=False)
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
        try:
            payload = {
                "prompt": prompt,
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            }
            if stop:
                payload["stop"] = stop
                
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/generate",
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "ngrok-skip-browser-warning": "true"
                    }
                )
                response.raise_for_status()
                return self._extract_text(response.json(), is_async=True)
        except httpx.TimeoutException:
            return "Error: Request timed out. The model took too long to respond."
        except httpx.HTTPStatusError as e:
            return f"Error: HTTP {e.response.status_code} - {e.response.text}"
        except Exception as e:
            return f"Error calling custom model: {str(e)}"
            
    @property
    def _identifying_params(self) -> Dict[str, Any]:
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
    return CustomModelLLM(
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout
    )
