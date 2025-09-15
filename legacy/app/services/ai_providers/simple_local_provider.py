"""
Simple Local AI Provider - Uses a lightweight approach for basic responses
"""

import logging
from typing import Any, Dict, Optional

from .base_provider import BaseAIProvider

logger = logging.getLogger(__name__)

# Try to import transformers
try:
    from transformers.pipelines import pipeline

    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    pipeline = None


class SimpleLocalProvider(BaseAIProvider):
    """
    Simple local AI provider using lightweight models
    Focused on basic conversational responses
    """

    def __init__(self, settings: Dict[str, Any]):
        super().__init__(settings)
        self.model_name = "gpt2"  # Use basic GPT-2 which is reliable
        self.tokenizer = None
        self.model = None
        self.pipeline = None
        self.device = "cpu"  # Keep it simple with CPU

    def initialize(self) -> bool:
        """Initialize simple provider"""
        if not TRANSFORMERS_AVAILABLE:
            logger.error("Transformers not available")
            return False

        if self.is_initialized:
            return True

        try:
            logger.info("Initializing Simple Local Provider...")

            if not pipeline:
                logger.error("Pipeline not available")
                return False

            # Create a simple text generation pipeline
            self.pipeline = pipeline(
                "text-generation",
                model=self.model_name,
                tokenizer=self.model_name,
                device=-1,  # CPU
                return_full_text=False,
            )

            self.is_initialized = True
            logger.info("Simple Local Provider initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Simple Local Provider: {e}")
            return False

    def is_available(self) -> bool:
        """Check if provider is available"""
        return TRANSFORMERS_AVAILABLE and self.is_initialized

    def generate_response(self, query: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Generate a simple response"""
        if not self.is_available():
            return {
                "success": False,
                "error": "Simple Local Provider not available",
                "response": "",
                "provider": "Simple Local",
                "model": self.model_name,
            }

        try:
            # Prepare the prompt with system prompt
            system_prompt = self.settings.get("system_prompt", "Você é um assistente útil.")

            if context:
                prompt = f"{system_prompt}\n\nContexto: {context}\n\nPergunta: {query}\n\nResposta:"
            else:
                prompt = f"{system_prompt}\n\nPergunta: {query}\n\nResposta:"

            # Generate response using the pipeline
            response = self.pipeline(
                prompt,
                max_length=min(len(prompt.split()) + 50, 200),  # Conservative max length
                do_sample=True,
                temperature=0.7,
                pad_token_id=self.pipeline.tokenizer.eos_token_id,
                num_return_sequences=1,
            )

            # Extract the generated text
            generated_text = response[0]["generated_text"]

            # Clean up the response (remove the prompt part)
            if "Resposta:" in generated_text:
                response_text = generated_text.split("Resposta:")[-1].strip()
            else:
                response_text = generated_text.strip()

            return {
                "success": True,
                "response": response_text,
                "model": self.model_name,
                "provider": "Simple Local",
            }

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                "success": False,
                "error": f"Erro ao gerar resposta: {str(e)}",
                "response": "",
                "provider": "Simple Local",
                "model": self.model_name,
            }

    def cleanup(self):
        """Cleanup resources"""
        if self.pipeline:
            del self.pipeline
        self.is_initialized = False

    def get_provider_info(self) -> Dict[str, Any]:
        """Get provider information"""
        info = super().get_provider_info()
        info.update(
            {
                "model_name": "Simple Local Assistant",
                "transformers_available": TRANSFORMERS_AVAILABLE,
                "device": "cpu",
            }
        )
        return info
