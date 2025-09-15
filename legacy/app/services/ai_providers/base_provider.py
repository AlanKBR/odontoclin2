"""
Base AI Provider Interface
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseAIProvider(ABC):
    """
    Abstract base class for AI providers
    Defines the interface that all AI providers must implement
    """

    def __init__(self, settings: Dict[str, Any]):
        self.settings = settings
        self.is_initialized = False

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the AI provider"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available and ready to use"""
        pass

    @abstractmethod
    def generate_response(self, query: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate AI response to user query

        Args:
            query: User's question/input
            context: Optional context from the application

        Returns:
            Dictionary with response, success status, and metadata
        """
        pass

    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about the provider"""
        return {
            "provider_type": self.__class__.__name__,
            "initialized": self.is_initialized,
            "available": self.is_available(),
            "settings": self.settings,
        }

    def validate_query(self, query: str) -> Dict[str, Any]:
        """Validate user query against safety settings"""
        max_length = self.settings.get("safety_settings", {}).get("max_query_length", 2000)

        if not query or not query.strip():
            return {"valid": False, "error": "Query cannot be empty"}

        if len(query) > max_length:
            return {
                "valid": False,
                "error": f"Query too long (max {max_length} characters)",
            }

        return {"valid": True}

    def format_response(self, response: str, add_disclaimer: bool = False) -> str:
        """Format the AI response with optional medical disclaimer"""
        formatted_response = response.strip()

        # Disclaimer removido - resposta limpa conforme solicitado
        if add_disclaimer and self.settings.get("safety_settings", {}).get(
            "medical_disclaimer", False
        ):
            formatted_response += "\n\n⚠️ Aviso: Este é um assistente de IA para fins informativos. Sempre consulte um profissional de saúde qualificado para diagnósticos e tratamentos."

        return formatted_response

    def cleanup(self):
        """Cleanup provider resources - to be overridden by subclasses"""
        pass
