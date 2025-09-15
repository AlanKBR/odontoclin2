"""
Model Type Detector - Automatically detects the type of AI model
"""

import os


class ModelTypeDetector:
    """
    Detects the type of AI model based on file structure and naming
    """

    @staticmethod
    def detect_model_type(model_name: str, cache_dir: str = "./models_cache/") -> str:
        """
        Detect model type based on model name and files

        Args:
            model_name: Name of the model (e.g., "pierreguillou/gpt2-small-portuguese")
            cache_dir: Cache directory path

        Returns:
            Model type: "gguf", "transformers", or "unknown"
        """
        # Check if model name contains GGUF indicators
        if any(
            indicator in model_name.lower()
            for indicator in ["gguf", "q4_0", "q4_1", "q5_0", "q5_1", "q6_k", "q8_0"]
        ):
            return "gguf"

        # Check cache directory for GGUF files
        cache_model_name = model_name.replace("/", "--")
        model_dir = os.path.join(cache_dir, f"models--{cache_model_name}")

        if os.path.exists(model_dir):
            # Check for GGUF files
            for root, dirs, files in os.walk(model_dir):
                for file in files:
                    if file.endswith(".gguf"):
                        return "gguf"

            # Check for transformers files
            transformers_files = ["config.json", "pytorch_model.bin", "model.safetensors"]
            for root, dirs, files in os.walk(model_dir):
                if any(tf in files for tf in transformers_files):
                    return "transformers"

        # Default assumption based on common patterns
        if any(
            pattern in model_name.lower()
            for pattern in ["gpt2", "bert", "distilbert", "roberta", "xlnet", "t5"]
        ):
            return "transformers"

        return "unknown"

    @staticmethod
    def get_recommended_provider(model_name: str, cache_dir: str = "./models_cache/") -> str:
        """
        Get recommended provider based on model type

        Args:
            model_name: Name of the model
            cache_dir: Cache directory path

        Returns:
            Recommended provider name
        """
        model_type = ModelTypeDetector.detect_model_type(model_name, cache_dir)

        if model_type == "gguf":
            return "gguf"
        elif model_type == "transformers":
            return "local"
        else:
            return "simple"
