#!/usr/bin/env python3
"""
AMD GPU Detection and Setup Script
Configures optimal PyTorch installation for AMD RX 5700
"""

import json
import platform
import subprocess
import sys
from pathlib import Path


def detect_gpu():
    """Detect GPU information"""
    gpu_info = {
        "has_amd": False,
        "has_nvidia": False,
        "amd_devices": [],
        "nvidia_devices": [],
        "recommended_backend": "cpu",
    }

    try:
        # Try to detect AMD GPU via PowerShell (more reliable on Windows)
        if platform.system() == "Windows":
            result = subprocess.run(
                [
                    "powershell",
                    "-Command",
                    "Get-WmiObject -Class Win32_VideoController | Select-Object Name | Format-Table -HideTableHeaders",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )

            if result.returncode == 0:
                lines = [line.strip() for line in result.stdout.split("\n") if line.strip()]

                for line in lines:
                    line_lower = line.lower()
                    if any(
                        keyword in line_lower for keyword in ["amd", "radeon", "rx 5700", "rx5700"]
                    ):
                        gpu_info["has_amd"] = True
                        gpu_info["recommended_backend"] = "rocm"
                        gpu_info["amd_devices"].append(line.strip())

                    if any(
                        keyword in line_lower for keyword in ["nvidia", "geforce", "gtx", "rtx"]
                    ):
                        gpu_info["has_nvidia"] = True
                        if not gpu_info["has_amd"]:  # NVIDIA takes priority if both
                            gpu_info["recommended_backend"] = "cuda"
                            gpu_info["nvidia_devices"].append(line.strip())

    except Exception as e:
        print(f"⚠️  GPU detection error: {e}")
        # Fallback to manual detection messages
        print(
            "💡 Tip: Run 'powershell Get-WmiObject -Class Win32_VideoController | Select-Object Name' to check GPU manually"
        )

    return gpu_info


def check_rocm_compatibility():
    """Check if ROCm is supported on this system"""
    try:
        # Check if we can import torch with ROCm
        import torch

        # Try to detect ROCm - use a safer approach
        try:
            # Try to access torch.version and check for hip
            version_module = getattr(torch, "version", None)
            if version_module:
                rocm_available = hasattr(version_module, "hip") and version_module.hip is not None
                hip_version = getattr(version_module, "hip", None) if rocm_available else None
            else:
                rocm_available = False
                hip_version = None
        except (AttributeError, ImportError):
            rocm_available = False
            hip_version = None

        return {
            "rocm_available": rocm_available,
            "torch_version": torch.__version__,
            "hip_version": hip_version,
        }
    except ImportError:
        return {"rocm_available": False, "torch_version": None, "hip_version": None}


def recommend_pytorch_installation(gpu_info):
    """Recommend optimal PyTorch installation"""
    recommendations = {
        "install_command": None,
        "index_url": None,
        "packages": [],
        "notes": [],
    }

    if gpu_info["has_amd"]:
        # ROCm installation for AMD
        recommendations["install_command"] = (
            "pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm5.6"
        )
        recommendations["index_url"] = "https://download.pytorch.org/whl/rocm5.6"
        recommendations["packages"] = ["torch", "torchvision", "torchaudio"]
        recommendations["notes"] = [
            "ROCm 5.6 is compatible with RX 5700",
            "Requires AMD GPU drivers to be updated",
            "May need ROCm runtime installed separately",
            "Fallback to CPU if ROCm fails",
        ]
    elif gpu_info["has_nvidia"]:
        # CUDA installation for NVIDIA
        recommendations["install_command"] = (
            "pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118"
        )
        recommendations["index_url"] = "https://download.pytorch.org/whl/cu118"
        recommendations["packages"] = ["torch", "torchvision", "torchaudio"]
        recommendations["notes"] = [
            "CUDA 11.8 compatible",
            "Requires NVIDIA drivers",
            "Better vLLM support",
        ]
    else:
        # CPU-only fallback
        recommendations["install_command"] = "pip install torch torchvision torchaudio"
        recommendations["packages"] = ["torch", "torchvision", "torchaudio"]
        recommendations["notes"] = [
            "CPU-only installation",
            "No GPU acceleration",
            "Works on all systems",
        ]

    return recommendations


def update_ai_settings_for_gpu(gpu_info):
    """Update AI settings based on detected GPU"""
    config_path = Path("config/ai_settings.json")

    if not config_path.exists():
        print("❌ AI settings file not found")
        return False

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            settings = json.load(f)

        # Update device settings based on GPU
        if gpu_info["has_amd"]:
            settings["providers"]["local"]["device"] = "cuda"  # ROCm uses cuda API
            settings["providers"]["local"]["gpu_type"] = "amd"
            settings["providers"]["local"]["backend"] = "rocm"
        elif gpu_info["has_nvidia"]:
            settings["providers"]["local"]["device"] = "cuda"
            settings["providers"]["local"]["gpu_type"] = "nvidia"
            settings["providers"]["local"]["backend"] = "cuda"
        else:
            settings["providers"]["local"]["device"] = "cpu"
            settings["providers"]["local"]["gpu_type"] = "none"
            settings["providers"]["local"]["backend"] = "cpu"

        # Update provider order based on GPU
        if gpu_info["has_amd"] or gpu_info["has_nvidia"]:
            # GPU available - prioritize local
            settings["providers"]["preferred_order"] = ["local", "vllm", "openai"]
        else:
            # CPU only - keep vLLM first (server might be on different machine)
            settings["providers"]["preferred_order"] = ["vllm", "local", "openai"]

        # Save updated settings
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)

        print(f"✅ Updated AI settings for {gpu_info['recommended_backend']} backend")
        return True

    except Exception as e:
        print(f"❌ Error updating settings: {e}")
        return False


def main():
    print("🔍 AMD GPU Detection and Configuration")
    print("=" * 50)

    # Detect GPU
    print("🔎 Detecting GPU hardware...")
    gpu_info = detect_gpu()

    print("📊 Detection Results:")
    print(f"   AMD GPU: {'✅' if gpu_info['has_amd'] else '❌'}")
    print(f"   NVIDIA GPU: {'✅' if gpu_info['has_nvidia'] else '❌'}")
    print(f"   Recommended Backend: {gpu_info['recommended_backend']}")

    if gpu_info["amd_devices"]:
        print(f"   AMD Devices: {', '.join(gpu_info['amd_devices'])}")

    # Check current PyTorch
    print("\n🔧 Checking current PyTorch installation...")
    rocm_info = check_rocm_compatibility()
    print(f"   PyTorch Version: {rocm_info['torch_version']}")
    print(f"   ROCm Available: {'✅' if rocm_info['rocm_available'] else '❌'}")

    # Get recommendations
    print("\n💡 Installation Recommendations:")
    recommendations = recommend_pytorch_installation(gpu_info)

    if recommendations["install_command"]:
        print(f"   Command: {recommendations['install_command']}")

        for note in recommendations["notes"]:
            print(f"   📝 {note}")

    # Update settings
    print("\n⚙️  Updating AI configuration...")
    update_ai_settings_for_gpu(gpu_info)

    # Summary
    print("\n" + "=" * 50)
    if gpu_info["has_amd"]:
        print("🎯 AMD RX 5700 DETECTED!")
        print("📋 Next Steps:")
        print("   1. Run: python setup_amd_gpu.py --install")
        print("   2. Restart application")
        print("   3. GPU acceleration will be available")
    elif gpu_info["has_nvidia"]:
        print("🎯 NVIDIA GPU DETECTED!")
        print("📋 Consider using vLLM for best performance")
    else:
        print("💻 CPU-only configuration")
        print("📋 Consider cloud providers for better performance")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AMD GPU Setup")
    parser.add_argument("--install", action="store_true", help="Install recommended PyTorch")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force reinstall even if compatible version exists",
    )

    args = parser.parse_args()

    if args.install:
        gpu_info = detect_gpu()
        recommendations = recommend_pytorch_installation(gpu_info)

        if recommendations["install_command"]:
            print(f"🚀 Installing: {recommendations['install_command']}")

            if args.force:
                # Uninstall first
                subprocess.run(
                    [sys.executable, "-m", "pip", "uninstall", "-y"] + recommendations["packages"]
                )

            # Install
            cmd = recommendations["install_command"].split()
            subprocess.run([sys.executable, "-m"] + cmd[1:])

            print("✅ Installation complete!")
        else:
            print("❌ No installation command available")
    else:
        main()
