"""
Provider Factory - Creates and manages AI providers
"""

import logging
from typing import Any, Dict, Optional, Type

from .base_provider import BaseAIProvider
from .custom_dental_provider import CustomDentalProvider
from .gguf_provider import GGUFProvider
from .local_transformers_provider import LocalTransformersProvider
from .openai_provider import OpenAIProvider
from .simple_local_provider import SimpleLocalProvider
from .vllm_provider import VLLMProvider

logger = logging.getLogger(__name__)


class ProviderFactory:
    """
    Factory class for creating AI providers
    Supports multiple provider types with fallback mechanisms
    """

    # Registry of available providers
    PROVIDERS = {
        "vllm": VLLMProvider,
        "openai": OpenAIProvider,
        "local": LocalTransformersProvider,
        "transformers": LocalTransformersProvider,  # Alias
        "simple": SimpleLocalProvider,
        "gguf": GGUFProvider,
        "custom": CustomDentalProvider,
        "dental": CustomDentalProvider,  # Alias
    }

    @classmethod
    def create_provider(
        cls, provider_type: str, settings: Dict[str, Any]
    ) -> Optional[BaseAIProvider]:
        """
        Create an AI provider instance

        Args:
            provider_type: Type of provider ("vllm", "openai", etc.)
            settings: Provider configuration

        Returns:
            Provider instance or None if creation failed
        """
        provider_class = cls.PROVIDERS.get(provider_type.lower())

        if not provider_class:
            logger.error(f"Unknown provider type: {provider_type}")
            return None

        try:
            return provider_class(settings)
        except Exception as e:
            logger.error(f"Failed to create {provider_type} provider: {e}")
            return None

    @classmethod
    def create_with_fallback(
        cls, preferred_providers: list, settings: Dict[str, Any]
    ) -> Optional[BaseAIProvider]:
        """
        Create provider with fallback support

        Args:
            preferred_providers: List of provider types in order of preference
            settings: Provider configuration

        Returns:
            First available provider or None
        """
        for provider_type in preferred_providers:
            provider = cls.create_provider(provider_type, settings)
            if provider and provider.initialize():
                logger.info(f"Successfully initialized {provider_type} provider")
                return provider
            else:
                logger.warning(f"Failed to initialize {provider_type} provider, trying next...")

        logger.error("All providers failed to initialize")
        return None

    @classmethod
    def get_available_providers(cls) -> list:
        """Get list of available provider types"""
        return list(cls.PROVIDERS.keys())

    @classmethod
    def register_provider(cls, name: str, provider_class: Type[BaseAIProvider]):
        """
        Register a new provider type

        Args:
            name: Provider name
            provider_class: Provider class (must inherit from BaseAIProvider)
        """
        if not issubclass(provider_class, BaseAIProvider):
            raise ValueError("Provider class must inherit from BaseAIProvider")

        cls.PROVIDERS[name.lower()] = provider_class
        logger.info(f"Registered new provider: {name}")
