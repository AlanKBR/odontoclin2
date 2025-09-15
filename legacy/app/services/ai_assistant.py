"""
AI Assistant Service - Modular implementation with multiple providers
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    # Import our modular AI providers
    from .ai_providers import BaseAIProvider, ProviderFactory

    AI_PROVIDERS_AVAILABLE = True
except ImportError:
    AI_PROVIDERS_AVAILABLE = False
    ProviderFactory = None
    BaseAIProvider = None

logger = logging.getLogger(__name__)


class AIAssistantService:
    """
    Modular AI Assistant Service with multiple provider support
    Supports vLLM, OpenAI, and other providers with fallback mechanisms
    """

    def __init__(self):
        self.provider = None
        self.settings = self._load_settings()
        self.is_initialized = False
        self.chat_history = []

    def _load_settings(self) -> Dict[str, Any]:
        """Load AI settings from config file"""
        try:
            config_path = os.path.join("config", "ai_settings.json")
            logger.info(f"Loading settings from: {config_path}")

            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                logger.info(f"Settings loaded successfully: {settings}")
                return settings
            else:
                logger.warning(f"Config file not found at {config_path}, using defaults")
                return {"ai_enabled": False}
        except Exception as e:
            logger.error(f"Error loading AI settings: {e}")
            return {"ai_enabled": False}

    def is_enabled(self) -> bool:
        """Check if AI is enabled and providers are available"""
        return self.settings.get("ai_enabled", False) and AI_PROVIDERS_AVAILABLE

    def initialize(self) -> bool:
        """Initialize the AI assistant with preferred provider"""
        if self.is_initialized or not self.is_enabled():
            return self.is_initialized

        try:
            logger.info("Initializing AI Assistant...")

            # Get model from settings
            model_name = self.settings.get("selected_model") or self.settings.get("model_name")

            if model_name:
                # Auto-detect model type and adjust provider preference
                from .model_type_detector import ModelTypeDetector

                recommended_provider = ModelTypeDetector.get_recommended_provider(model_name)

                # Get provider preference from settings
                provider_config = self.settings.get("providers", {})
                preferred_providers = provider_config.get(
                    "preferred_order", ["gguf", "local", "vllm", "openai", "simple"]
                )

                # Move recommended provider to front if not already first
                if (
                    recommended_provider in preferred_providers
                    and preferred_providers[0] != recommended_provider
                ):
                    preferred_providers = [recommended_provider] + [
                        p for p in preferred_providers if p != recommended_provider
                    ]
                    logger.info(
                        f"Auto-detected model type, prioritizing {recommended_provider} provider for {model_name}"
                    )
            else:
                # Get provider preference from settings
                provider_config = self.settings.get("providers", {})
                preferred_providers = provider_config.get(
                    "preferred_order", ["gguf", "local", "vllm", "openai", "simple"]
                )

            # Create provider with fallback
            if ProviderFactory:
                self.provider = ProviderFactory.create_with_fallback(
                    preferred_providers, self.settings
                )
            else:
                logger.error("ProviderFactory not available")
                return False

            if self.provider:
                self.is_initialized = True
                logger.info(f"AI Assistant initialized with {self.provider.__class__.__name__}")
                return True
            else:
                logger.error("Failed to initialize any AI provider")
                return False

        except Exception as e:
            logger.error(f"Failed to initialize AI Assistant: {e}")
            self.is_initialized = False
            return False

    def generate_response(self, query: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate AI response using the active provider

        Args:
            query: User's question/input
            context: Optional context from the application

        Returns:
            Dictionary with response, success status, and metadata
        """
        if not self.is_enabled():
            return {
                "success": False,
                "error": "AI Assistant is disabled or providers not available",
                "response": "",
                "provider": "None",
                "model": "None",
            }

        if not self.is_initialized and not self.initialize():
            return {
                "success": False,
                "error": "Failed to initialize AI provider",
                "response": "",
                "provider": "None",
                "model": "None",
            }

        if not self.provider:
            return {
                "success": False,
                "error": "No AI provider available",
                "response": "",
                "provider": "None",
                "model": "None",
            }

        try:
            # Generate response using the active provider
            result = self.provider.generate_response(query, context)

            # Add provider information to error responses
            if not result.get("success"):
                if "provider" not in result:
                    result["provider"] = (
                        self.provider.__class__.__name__ if self.provider else "Unknown"
                    )
                if "model" not in result:
                    result["model"] = (
                        getattr(self.provider, "model_name", "Unknown")
                        if self.provider
                        else "Unknown"
                    )

            # Store in chat history if enabled and successful
            if result.get("success") and self.settings.get("ui_settings", {}).get(
                "enable_chat_history", True
            ):
                self._add_to_history(query, result.get("response", ""))

            return result

        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return {
                "success": False,
                "error": str(e),
                "response": "",
                "provider": self.provider.__class__.__name__ if self.provider else "None",
                "model": (
                    getattr(self.provider, "model_name", "Unknown") if self.provider else "None"
                ),
            }

    def _prepare_prompt(self, query: str, context: Optional[str] = None) -> str:
        """Prepare the prompt for the AI model - delegated to provider"""
        # This method is now handled by individual providers
        # Kept for backwards compatibility
        return query

    def _add_to_history(self, query: str, response: str):
        """Add interaction to chat history"""
        max_items = self.settings.get("ui_settings", {}).get("max_history_items", 50)

        self.chat_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "query": query,
                "response": response,
            }
        )

        # Keep only the most recent items
        if len(self.chat_history) > max_items:
            self.chat_history = self.chat_history[-max_items:]

    def get_chat_history(self) -> List[Dict[str, Any]]:
        """Get recent chat history"""
        return self.chat_history

    def clear_history(self):
        """Clear chat history"""
        self.chat_history = []

    def get_model_info(self) -> Dict[str, Any]:
        """Get comprehensive model information for display"""
        info = {
            "enabled": self.is_enabled(),
            "initialized": self.is_initialized,
            "dependencies_available": AI_PROVIDERS_AVAILABLE,
            "model_name": "Modelo desconhecido",
            "provider_type": None,
            "status": "not_initialized",
        }

        if not self.is_enabled():
            info["status"] = "disabled"
            return info

        if not AI_PROVIDERS_AVAILABLE:
            info["status"] = "dependencies_missing"
            return info

        # Always try to get model name from settings first, regardless of initialization
        if "selected_model" in self.settings:
            info["model_name"] = self._format_model_name(self.settings["selected_model"])
        elif "model_name" in self.settings:
            info["model_name"] = self._format_model_name(self.settings["model_name"])

        if self.is_initialized and self.provider:
            try:
                provider_info = self.provider.get_provider_info()
                info.update(
                    {
                        "status": "initialized",
                        "provider_type": provider_info.get("provider_type", "unknown"),
                    }
                )

                # Always use model name from settings (already formatted above)
                # Don't override with provider info which may not have the correct name

            except Exception as e:
                logger.error(f"Error getting model info: {e}")
                info["model_name"] = "Erro ao obter informações do modelo"
                info["status"] = "error"
        else:
            info["status"] = "not_initialized"

        return info

    def switch_provider(self, provider_type: str) -> bool:
        """Switch to a different provider"""
        if not self.is_enabled():
            return False

        try:
            if ProviderFactory:
                new_provider = ProviderFactory.create_provider(provider_type, self.settings)
            else:
                return False

            if new_provider and new_provider.initialize():
                # Cleanup old provider
                if self.provider and hasattr(self.provider, "cleanup"):
                    self.provider.cleanup()

                self.provider = new_provider
                logger.info(f"Switched to {provider_type} provider")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to switch provider: {e}")
            return False

    def cleanup(self):
        """Cleanup AI assistant resources"""
        if self.provider:
            if hasattr(self.provider, "cleanup"):
                self.provider.cleanup()
        self.provider = None
        self.is_initialized = False

    def get_configuration_data(self) -> Dict[str, Any]:
        """Get current configuration and available options"""
        return {
            "current_settings": self.settings,
            "is_initialized": self.is_initialized,
            "providers": (list(ProviderFactory.PROVIDERS.keys()) if ProviderFactory else []),
            "current_provider": (self.provider.__class__.__name__ if self.provider else None),
        }

    def scan_available_models(self) -> List[Dict[str, Any]]:
        """Scan for available local models"""
        models = []
        models_dir = (
            self.settings.get("providers", {}).get("local", {}).get("cache_dir", "./models_cache/")
        )

        try:
            import os

            if os.path.exists(models_dir):
                for item in os.listdir(models_dir):
                    model_path = os.path.join(models_dir, item)
                    if os.path.isdir(model_path):
                        # Basic model info - could be expanded with metadata
                        models.append(
                            {
                                "name": item,
                                "path": model_path,
                                "type": "local",
                                "size": self._get_dir_size(model_path),
                            }
                        )
        except Exception as e:
            logger.error(f"Error scanning models: {e}")

        return models

    def _get_dir_size(self, path: str) -> str:
        """Get directory size in human readable format"""
        try:
            import os

            total_size = 0
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    total_size += os.path.getsize(filepath)

            # Convert to human readable
            for unit in ["B", "KB", "MB", "GB"]:
                if total_size < 1024.0:
                    return f"{total_size:.1f} {unit}"
                total_size /= 1024.0
            return f"{total_size:.1f} TB"
        except Exception:
            return "Unknown"

    def update_configuration(self, config_data: Dict[str, Any]) -> bool:
        """Update AI configuration"""
        try:
            logger.info(f"Updating configuration with data: {config_data}")

            # Update settings
            old_settings = self.settings.copy()
            self.settings.update(config_data)

            logger.info(f"Settings before update: {old_settings}")
            logger.info(f"Settings after update: {self.settings}")

            # Save to file
            config_path = os.path.join("config", "ai_settings.json")
            logger.info(f"Saving configuration to: {config_path}")

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)

            logger.info("Configuration saved successfully to file")

            # If currently initialized and provider changed, reinitialize
            if self.is_initialized and config_data.get("provider_change"):
                logger.info("Provider change detected, reinitializing...")
                self.stop()
                return self.initialize()

            return True
        except Exception as e:
            logger.error(f"Error updating configuration: {e}")
            return False

    def stop(self):
        """Stop AI assistant and cleanup resources"""
        try:
            logger.info("Stopping AI Assistant...")

            # Cleanup provider if it exists
            if self.provider:
                logger.info(f"Cleaning up provider: {self.provider.__class__.__name__}")
                if hasattr(self.provider, "cleanup"):
                    self.provider.cleanup()
                    logger.info("Provider cleanup completed")
                else:
                    logger.warning("Provider has no cleanup method")

            # Clear provider reference
            self.provider = None

            # Mark as not initialized
            self.is_initialized = False

            # Force garbage collection to free memory
            import gc

            gc.collect()

            logger.info("AI Assistant stopped successfully")
            return True

        except Exception as e:
            logger.error(f"Error stopping AI Assistant: {e}")
            # Even if there's an error, ensure we're marked as stopped
            self.provider = None
            self.is_initialized = False
            return False

    def get_detailed_status(self) -> Dict[str, Any]:
        """Get detailed status information"""
        status = {
            "enabled": self.is_enabled(),
            "initialized": self.is_initialized,
            "provider_available": AI_PROVIDERS_AVAILABLE,
            "current_provider": None,
            "provider_info": None,
            "hardware_status": None,
            "model_status": None,
        }

        if self.provider:
            try:
                provider_info = self.provider.get_provider_info()
                status["current_provider"] = provider_info.get("provider_type")
                status["provider_info"] = provider_info
            except Exception as e:
                logger.error(f"Error getting provider info: {e}")

        return status

    def _format_model_name(self, model_name: str) -> str:
        """Format model name for better display"""
        if not model_name or model_name in ["Modelo desconhecido", "Nenhum modelo selecionado"]:
            return model_name

        # Extract meaningful part from model name
        if "/" in model_name:
            parts = model_name.split("/")
            if len(parts) >= 2:
                # Format: "Organization/Model-Name" -> "Model-Name (Organization)"
                org = parts[0]
                model = parts[1]

                # Clean up model name
                model_clean = model.replace("-GGUF", "").replace("-Instruct", "")

                # Special cases for better readability
                if "BioMistral" in model:
                    return f"BioMistral ({org})"
                elif "Qwen" in model:
                    return f"Qwen 2.5 Coder 1.5B ({org})"
                elif "Mistral" in model:
                    return f"Mistral 7B Instruct ({org})"
                else:
                    return f"{model_clean} ({org})"

        return model_name


# Global instance - singleton pattern for efficiency
ai_assistant = AIAssistantService()
