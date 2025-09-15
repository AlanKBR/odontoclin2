"""
vLLM Provider - Local high-performance inference server
"""

import logging
import subprocess
import time
from typing import Any, Dict, Optional

import requests

from .base_provider import BaseAIProvider

logger = logging.getLogger(__name__)


class VLLMProvider(BaseAIProvider):
    """
    vLLM-based AI provider using local inference server
    High performance and optimized for production use
    """

    def __init__(self, settings: Dict[str, Any]):
        super().__init__(settings)
        self.server_url = settings.get("server_url", "http://localhost:8000")
        self.model_name = settings.get("model_name", "BioMistral/BioMistral-7B-AWQ-QGS128-W4-GEMV")
        self.server_process = None

    def initialize(self) -> bool:
        """Initialize vLLM provider"""
        if self.is_initialized:
            return True

        try:
            # Check if server is already running
            if self._is_server_running():
                self.is_initialized = True
                logger.info("vLLM server already running")
                return True

            # Try to start server if auto-start is enabled
            if self.settings.get("auto_start_server", True):
                return self._start_server()

            return False

        except Exception as e:
            logger.error(f"Failed to initialize vLLM provider: {e}")
            return False

    def is_available(self) -> bool:
        """Check if vLLM server is available"""
        return self.is_initialized and self._is_server_running()

    def generate_response(self, query: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Generate response using vLLM server"""

        # Validate query
        validation = self.validate_query(query)
        if not validation["valid"]:
            return {"success": False, "error": validation["error"], "response": ""}

        if not self.is_available():
            return {
                "success": False,
                "error": "vLLM server not available",
                "response": "",
                "provider": "vLLM",
                "model": self.model_name,
            }

        try:
            # Prepare prompt
            prompt = self._prepare_prompt(query, context)

            # Make request to vLLM server
            payload = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": self.settings.get("max_tokens", 512),
                "temperature": self.settings.get("temperature", 0.7),
                "stream": False,
            }

            response = requests.post(
                f"{self.server_url}/v1/chat/completions",
                json=payload,
                timeout=self.settings.get("request_timeout", 30),
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                result = response.json()
                ai_response = result["choices"][0]["message"]["content"]

                return {
                    "success": True,
                    "response": self.format_response(ai_response),
                    "model": self.model_name,
                    "provider": "vLLM",
                    "usage": result.get("usage", {}),
                }
            else:
                return {
                    "success": False,
                    "error": f"Server error: {response.status_code}",
                    "response": "",
                    "provider": "vLLM",
                    "model": self.model_name,
                }

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            return {
                "success": False,
                "error": f"Connection error: {str(e)}",
                "response": "",
                "provider": "vLLM",
                "model": self.model_name,
            }
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {
                "success": False,
                "error": str(e),
                "response": "",
                "provider": "vLLM",
                "model": self.model_name,
            }

    def _prepare_prompt(self, query: str, context: Optional[str] = None) -> str:
        """Prepare prompt for the AI model"""
        system_prompt = self.settings.get(
            "system_prompt",
            "Você é um assistente especializado em odontologia. Responda de forma clara e precisa.",
        )

        prompt = system_prompt + "\n\n"

        if context:
            prompt += f"Contexto: {context}\n\n"

        prompt += f"Pergunta: {query}"

        return prompt

    def _is_server_running(self) -> bool:
        """Check if vLLM server is running"""
        try:
            response = requests.get(f"{self.server_url}/health", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def _start_server(self) -> bool:
        """Start vLLM server"""
        try:
            logger.info("Starting vLLM server...")

            # Build command
            cmd = [
                "vllm",
                "serve",
                self.model_name,
                "--host",
                "localhost",
                "--port",
                "8000",
            ]

            # Add optional parameters
            if self.settings.get("gpu_memory_utilization"):
                cmd.extend(
                    [
                        "--gpu-memory-utilization",
                        str(self.settings["gpu_memory_utilization"]),
                    ]
                )

            if self.settings.get("max_model_len"):
                cmd.extend(["--max-model-len", str(self.settings["max_model_len"])])

            # Start server process
            self.server_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )

            # Wait for server to be ready
            max_wait = self.settings.get("server_startup_timeout", 60)
            wait_time = 0

            while wait_time < max_wait:
                if self._is_server_running():
                    self.is_initialized = True
                    logger.info("vLLM server started successfully")
                    return True

                time.sleep(2)
                wait_time += 2

            logger.error("vLLM server failed to start within timeout")
            self._stop_server()
            return False

        except Exception as e:
            logger.error(f"Error starting vLLM server: {e}")
            return False

    def _stop_server(self):
        """Stop vLLM server"""
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
            finally:
                self.server_process = None

        self.is_initialized = False

    def cleanup(self):
        """Cleanup resources"""
        self._stop_server()

    def get_provider_info(self) -> Dict[str, Any]:
        """Get vLLM provider information"""
        info = super().get_provider_info()
        info.update(
            {
                "server_url": self.server_url,
                "server_running": self._is_server_running(),
                "model_name": self.model_name,
            }
        )
        return info
