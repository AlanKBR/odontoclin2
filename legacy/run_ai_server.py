#!/usr/bin/env python3
"""
vLLM Server Management Script
Provides easy management of the vLLM inference server
"""

import argparse
import json
import subprocess
import time
from pathlib import Path

import psutil
import requests


def load_settings():
    """Load AI settings"""
    config_path = Path("config/ai_settings.json")
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    return {}


def is_server_running(url="http://localhost:8000"):
    """Check if vLLM server is running"""
    try:
        response = requests.get(f"{url}/health", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def start_server():
    """Start vLLM server"""
    settings = load_settings()
    vllm_config = settings.get("providers", {}).get("vllm", {})

    model_name = settings.get("model_name", "BioMistral/BioMistral-7B-AWQ-QGS128-W4-GEMV")

    print(f"🚀 Starting vLLM server with model: {model_name}")

    # Build command
    cmd = ["vllm", "serve", model_name, "--host", "localhost", "--port", "8000"]

    # Add optional parameters from config
    if vllm_config.get("gpu_memory_utilization"):
        cmd.extend(["--gpu-memory-utilization", str(vllm_config["gpu_memory_utilization"])])

    if vllm_config.get("max_model_len"):
        cmd.extend(["--max-model-len", str(vllm_config["max_model_len"])])

    print(f"📋 Command: {' '.join(cmd)}")
    print("⏳ Starting server (this may take a few minutes)...")

    try:
        # Start server
        process = subprocess.Popen(cmd)

        # Wait for server to be ready
        max_wait = vllm_config.get("server_startup_timeout", 120)
        wait_time = 0

        while wait_time < max_wait:
            if is_server_running():
                print("✅ vLLM server started successfully!")
                print("🌐 Server URL: http://localhost:8000")
                print("📖 API docs: http://localhost:8000/docs")
                return process

            time.sleep(3)
            wait_time += 3
            print(f"⏳ Waiting for server... ({wait_time}/{max_wait}s)")

        print("❌ Server failed to start within timeout")
        process.terminate()
        return None

    except Exception as e:
        print(f"❌ Error starting server: {e}")
        return None


def stop_server():
    """Stop vLLM server"""
    print("🛑 Stopping vLLM server...")

    # Find and kill vLLM processes
    killed = False
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if "vllm" in proc.info["name"].lower() or any(
                "vllm" in arg for arg in proc.info["cmdline"]
            ):
                proc.kill()
                print(f"🔪 Killed process {proc.info['pid']}")
                killed = True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if killed:
        print("✅ vLLM server stopped")
    else:
        print("ℹ️  No vLLM processes found")


def server_status():
    """Check server status"""
    if is_server_running():
        print("✅ vLLM server is running")
        print("🌐 Server URL: http://localhost:8000")

        # Get model info
        try:
            response = requests.get("http://localhost:8000/v1/models")
            if response.status_code == 200:
                models = response.json()
                print(f"📦 Loaded models: {len(models.get('data', []))}")
        except Exception:
            pass
    else:
        print("❌ vLLM server is not running")


def test_inference():
    """Test model inference"""
    if not is_server_running():
        print("❌ vLLM server is not running. Start it first with: python run_ai_server.py start")
        return

    print("🧪 Testing inference...")

    settings = load_settings()
    model_name = settings.get("model_name", "BioMistral/BioMistral-7B-AWQ-QGS128-W4-GEMV")

    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": "O que é cárie dentária?"}],
        "max_tokens": 100,
        "temperature": 0.7,
    }

    try:
        response = requests.post(
            "http://localhost:8000/v1/chat/completions", json=payload, timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            answer = result["choices"][0]["message"]["content"]
            print("✅ Inference test successful!")
            print(f"📝 Response: {answer[:200]}...")
        else:
            print(f"❌ Inference test failed: {response.status_code}")
            print(response.text)

    except Exception as e:
        print(f"❌ Inference test error: {e}")


def main():
    parser = argparse.ArgumentParser(description="vLLM Server Management")
    parser.add_argument(
        "action",
        choices=["start", "stop", "status", "test", "restart"],
        help="Action to perform",
    )

    args = parser.parse_args()

    if args.action == "start":
        if is_server_running():
            print("ℹ️  vLLM server is already running")
        else:
            start_server()

    elif args.action == "stop":
        stop_server()

    elif args.action == "status":
        server_status()

    elif args.action == "test":
        test_inference()

    elif args.action == "restart":
        stop_server()
        time.sleep(2)
        start_server()


if __name__ == "__main__":
    main()
