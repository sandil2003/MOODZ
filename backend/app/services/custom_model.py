"""LangChain Custom LLM wrapper for external model endpoints (e.g. Google Colab via ngrok)."""

import logging
from typing import List, Dict, Any, Optional
import httpx
from pydantic import Field
from langchain_core.language_models.llms import LLM
from langchain_core.callbacks.manager import CallbackManagerForLLMRun

logger = logging.getLogger(__name__)


class CustomModelLLM(LLM):
    """LangChain LLM wrapper for custom self-hosted inference endpoints."""

    base_url: str = Field(description="Base URL of the inference endpoint (e.g., ngrok tunnel)")
    model_name: str = Field(default="custom-model", description="Identifier of the model")
    temperature: float = Field(default=0.7, description="Temperature for generation")
    max_tokens: int = Field(default=2048, description="Maximum tokens to generate")
    timeout: int = Field(default=60, description="Request timeout in seconds")

    @property
    def _llm_type(self) -> str:
        return "custom_model"

    def _extract_text(self, result: Any) -> str:
        """Extract output text from various response structures."""
        if isinstance(result, str):
            return result

        if isinstance(result, dict):
            # Check primary keys
            for key in ["generated_text", "text", "response", "output", "result", "answer", "completion"]:
                if key in result and result[key]:
                    return str(result[key])

            # Check nested data dictionary
            if "data" in result:
                data = result["data"]
                if isinstance(data, dict):
                    for key in ["generated_text", "text", "response"]:
                        if key in data and data[key]:
                            return str(data[key])
                elif isinstance(data, str):
                    return data

        return str(result) if result else ""

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Synchronous HTTP call to the /generate endpoint."""
        payload = {
            "prompt": prompt,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
        }
        if stop:
            payload["stop"] = stop

        try:
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
                return self._extract_text(response.json())
        except httpx.TimeoutException:
            logger.error("Custom model request timed out")
            return "Error: Request timed out. The model took too long to respond."
        except httpx.HTTPStatusError as e:
            logger.error(f"Custom model returned HTTP {e.response.status_code}")
            return f"Error: HTTP {e.response.status_code} - {e.response.text}"
        except Exception as e:
            logger.error(f"Error calling custom model: {e}")
            return f"Error calling custom model: {str(e)}"

    async def _acall(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Asynchronous HTTP call to the /generate endpoint."""
        payload = {
            "prompt": prompt,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
        }
        if stop:
            payload["stop"] = stop

        try:
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
                return self._extract_text(response.json())
        except httpx.TimeoutException:
            logger.error("Custom model async request timed out")
            return "Error: Request timed out. The model took too long to respond."
        except httpx.HTTPStatusError as e:
            logger.error(f"Custom model async returned HTTP {e.response.status_code}")
            return f"Error: HTTP {e.response.status_code} - {e.response.text}"
        except Exception as e:
            logger.error(f"Error in async call to custom model: {e}")
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
    """Factory creating CustomModelLLM instance."""
    return CustomModelLLM(
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout
    )
