"""
OpenAI Provider - Cloud-based AI integration
"""

import logging
from typing import Any, Dict, Optional

import requests

from .base_provider import BaseAIProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseAIProvider):
    """
    OpenAI-based AI provider for cloud inference
    Useful for fallback or comparison scenarios
    """

    def __init__(self, settings: Dict[str, Any]):
        super().__init__(settings)
        self.api_key = settings.get("api_key")
        self.model_name = settings.get("model_name", "gpt-3.5-turbo")
        self.base_url = settings.get("base_url", "https://api.openai.com/v1")

    def initialize(self) -> bool:
        """Initialize OpenAI provider"""
        if not self.api_key:
            logger.warning("OpenAI API key not provided")
            return False

        self.is_initialized = True
        return True

    def is_available(self) -> bool:
        """Check if OpenAI API is available"""
        return self.is_initialized and bool(self.api_key)

    def generate_response(self, query: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Generate response using OpenAI API"""

        # Validate query
        validation = self.validate_query(query)
        if not validation["valid"]:
            return {"success": False, "error": validation["error"], "response": ""}

        if not self.is_available():
            return {
                "success": False,
                "error": "OpenAI provider not available (API key required)",
                "response": "",
                "provider": "OpenAI",
                "model": self.model_name,
            }

        try:
            # Prepare messages
            messages = [
                {
                    "role": "system",
                    "content": self.settings.get(
                        "system_prompt",
                        "Você é um assistente especializado em odontologia. Responda de forma clara e precisa.",
                    ),
                }
            ]

            if context:
                messages.append({"role": "user", "content": f"Contexto: {context}"})

            messages.append({"role": "user", "content": query})

            # Make request to OpenAI API
            payload = {
                "model": self.model_name,
                "messages": messages,
                "max_tokens": self.settings.get("max_tokens", 512),
                "temperature": self.settings.get("temperature", 0.7),
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            response = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=self.settings.get("request_timeout", 30),
            )

            if response.status_code == 200:
                result = response.json()
                ai_response = result["choices"][0]["message"]["content"]

                return {
                    "success": True,
                    "response": self.format_response(ai_response),
                    "model": self.model_name,
                    "provider": "OpenAI",
                    "usage": result.get("usage", {}),
                }
            else:
                error_data = response.json() if response.content else {}
                return {
                    "success": False,
                    "error": f"API error: {error_data.get('error', {}).get('message', 'Unknown error')}",
                    "response": "",
                    "provider": "OpenAI",
                    "model": self.model_name,
                }

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            return {
                "success": False,
                "error": f"Connection error: {str(e)}",
                "response": "",
                "provider": "OpenAI",
                "model": self.model_name,
            }
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {
                "success": False,
                "error": str(e),
                "response": "",
                "provider": "OpenAI",
                "model": self.model_name,
            }

    def get_provider_info(self) -> Dict[str, Any]:
        """Get OpenAI provider information"""
        info = super().get_provider_info()
        info.update(
            {
                "model_name": self.model_name,
                "base_url": self.base_url,
                "has_api_key": bool(self.api_key),
            }
        )
        return info
