"""
GGUF Provider - Handles GGUF model files using llama-cpp-python
"""

import contextlib
import logging
import os
import warnings
from typing import Any, Dict, Optional

from .base_provider import BaseAIProvider

logger = logging.getLogger(__name__)

# Suppress llama-cpp-python cleanup warnings
warnings.filterwarnings("ignore", category=ResourceWarning)
warnings.filterwarnings("ignore", message=".*NoneType.*not callable.*")


@contextlib.contextmanager
def suppress_stderr():
    """Context manager to suppress stderr output"""

    import io
    import sys

    old_stderr = sys.stderr
    sys.stderr = io.StringIO()
    try:
        yield
    finally:
        sys.stderr = old_stderr


# Try to import llama-cpp-python
try:
    from llama_cpp import Llama

    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    Llama = None


class GGUFProvider(BaseAIProvider):
    """
    GGUF model provider using llama-cpp-python
    Supports quantized models in GGUF format
    """

    def __init__(self, settings: Dict[str, Any]):
        super().__init__(settings)
        self.model = None
        self.model_path = None

        # Get GGUF-specific settings
        gguf_settings = settings.get("providers", {}).get("gguf", {})

        self.n_ctx = gguf_settings.get("n_ctx", settings.get("max_tokens", 2048))
        self.n_threads = gguf_settings.get("n_threads", os.cpu_count() or 4)
        self.n_gpu_layers = gguf_settings.get("n_gpu_layers", 0)
        self.verbose = gguf_settings.get("verbose", False)
        self.cache_dir = gguf_settings.get("cache_dir", "./models_cache/")

    def __del__(self):
        """Destructor to ensure cleanup"""
        with suppress_stderr():
            self.cleanup()

    def _find_gguf_model(self, model_name: str) -> Optional[str]:
        """Find GGUF model file in cache directory"""
        cache_dir = self.cache_dir

        # Convert model name to cache directory format
        cache_model_name = model_name.replace("/", "--")
        model_dir = os.path.join(cache_dir, f"models--{cache_model_name}")

        if not os.path.exists(model_dir):
            logger.error(f"Model directory not found: {model_dir}")
            return None

        # Search for .gguf files
        for root, dirs, files in os.walk(model_dir):
            for file in files:
                if file.endswith(".gguf"):
                    gguf_path = os.path.join(root, file)
                    logger.info(f"Found GGUF model: {gguf_path}")
                    return gguf_path

        logger.error(f"No GGUF files found in {model_dir}")
        return None

    def initialize(self) -> bool:
        """Initialize GGUF provider"""
        if not LLAMA_CPP_AVAILABLE:
            logger.error(
                "llama-cpp-python not available. Install with: pip install llama-cpp-python"
            )
            return False

        if self.is_initialized:
            return True

        try:
            logger.info("Initializing GGUF Provider...")

            # Get model name from GGUF-specific settings or fallback to global settings
            gguf_settings = self.settings.get("providers", {}).get("gguf", {})
            model_name = (
                gguf_settings.get("model_name")
                or self.settings.get("selected_model")
                or self.settings.get("model_name")
            )

            if not model_name:
                logger.error("No model specified")
                return False

            # Find the GGUF model file
            self.model_path = self._find_gguf_model(model_name)
            if not self.model_path:
                return False

            logger.info(f"Loading GGUF model: {self.model_path}")

            # Initialize llama.cpp model
            if not Llama:
                logger.error("Llama class not available")
                return False

            self.model = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                verbose=self.verbose,
                n_gpu_layers=self.n_gpu_layers,
            )

            self.is_initialized = True
            logger.info("GGUF Provider initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize GGUF Provider: {e}")
            return False

    def is_available(self) -> bool:
        """Check if provider is available"""
        return LLAMA_CPP_AVAILABLE and self.is_initialized

    def generate_response(self, query: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Generate response using GGUF model"""
        if not self.is_available():
            return {
                "success": False,
                "error": "GGUF Provider not available",
                "response": "",
                "provider": "GGUF",
                "model": getattr(self, "model_name", "Unknown"),
            }

        try:
            # Prepare the prompt
            system_prompt = self.settings.get("system_prompt", "Você é um assistente útil.")

            if context:
                prompt = f"{system_prompt}\n\nContexto: {context}\n\nPergunta: {query}\n\nResposta:"
            else:
                prompt = f"{system_prompt}\n\nPergunta: {query}\n\nResposta:"

            # Generate response
            if not self.model:
                return {
                    "success": False,
                    "error": "Model not loaded",
                    "response": "",
                    "provider": "GGUF",
                    "model": getattr(self, "model_name", "Unknown"),
                }

            output = self.model(
                prompt,
                max_tokens=self.settings.get("max_tokens", 256),
                temperature=self.settings.get("temperature", 0.7),
                top_p=0.9,
                echo=False,
                stop=[
                    "\n\nPergunta:",
                    "\nPergunta:",
                    "Sistema:",
                    "---",
                    "Resposta:",
                    "\n\n\n",
                    "1.",
                    "2.",
                    "3.",
                    "4.",
                    "5.",
                    "6.",
                    "7.",
                    "8.",
                    "9.",
                    "10.",
                ],
                repeat_penalty=1.1,
            )

            # Handle the response format
            if isinstance(output, dict) and "choices" in output:
                response_text = output["choices"][0]["text"].strip()
            else:
                response_text = str(output).strip()

            # Clean up the response - remove repetitive parts
            lines = response_text.split("\n")
            clean_lines = []
            seen_lines = set()

            for line in lines:
                line = line.strip()
                if line and line not in seen_lines and not line.startswith("---"):
                    clean_lines.append(line)
                    seen_lines.add(line)
                    if len(clean_lines) >= 10:  # Limitar número de linhas
                        break

            response_text = "\n".join(clean_lines)

            return {
                "success": True,
                "response": response_text,
                "model": os.path.basename(self.model_path) if self.model_path else "GGUF Model",
                "provider": "GGUF",
                "usage": {
                    "prompt_tokens": len(prompt.split()),
                    "completion_tokens": len(response_text.split()),
                },
            }

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                "success": False,
                "error": f"Error generating response: {str(e)}",
                "response": "",
                "provider": "GGUF",
                "model": getattr(self, "model_name", "Unknown"),
            }

    def cleanup(self):
        """Cleanup resources safely"""
        try:
            if hasattr(self, "model") and self.model:
                # Use context manager to suppress stderr during cleanup
                with suppress_stderr():
                    # Try to close the model properly
                    try:
                        if hasattr(self.model, "close"):
                            self.model.close()
                    except Exception:
                        pass  # Ignore cleanup errors

                    # Delete the model reference
                    try:
                        del self.model
                    except Exception:
                        pass  # Ignore deletion errors

                    self.model = None
        except Exception:
            pass  # Ignore all cleanup errors

        self.is_initialized = False

    def get_provider_info(self) -> Dict[str, Any]:
        """Get provider information"""
        info = super().get_provider_info()
        info.update(
            {
                "model_path": self.model_path,
                "model_type": "GGUF",
                "llama_cpp_available": LLAMA_CPP_AVAILABLE,
                "context_length": self.n_ctx,
            }
        )
        return info
