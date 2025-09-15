"""
Hardware Detection Service
Detects available hardware for AI processing (CPU, GPU types)
"""

import logging
import platform
import subprocess
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def detect_system_capabilities() -> Dict[str, Any]:
    """
    Detect system hardware capabilities for AI processing

    Returns:
        Dictionary with hardware information and recommendations
    """
    capabilities = {
        "cpu": detect_cpu_info(),
        "gpu": detect_gpu_info(),
        "memory": detect_memory_info(),
        "recommendations": [],
    }

    # Generate recommendations based on detected hardware
    capabilities["recommendations"] = generate_recommendations(capabilities)

    return capabilities


def detect_cpu_info() -> Dict[str, Any]:
    """Detect CPU information"""
    try:
        import psutil

        cpu_info = {
            "cores": psutil.cpu_count(logical=False),
            "threads": psutil.cpu_count(logical=True),
            "frequency": psutil.cpu_freq().max if psutil.cpu_freq() else "Unknown",
            "architecture": platform.processor(),
            "suitable_for_ai": True,
        }

        # Determine if CPU is suitable for AI workloads
        if cpu_info["cores"] >= 4 and cpu_info["threads"] >= 8:
            cpu_info["ai_performance"] = "Good"
        elif cpu_info["cores"] >= 2:
            cpu_info["ai_performance"] = "Moderate"
        else:
            cpu_info["ai_performance"] = "Limited"
            cpu_info["suitable_for_ai"] = False

        return cpu_info

    except ImportError:
        # Fallback without psutil
        return {
            "cores": "Unknown",
            "threads": "Unknown",
            "frequency": "Unknown",
            "architecture": platform.processor(),
            "ai_performance": "Unknown",
            "suitable_for_ai": True,
        }
    except Exception as e:
        logger.error(f"Error detecting CPU: {e}")
        return {"error": str(e), "suitable_for_ai": False}


def detect_gpu_info() -> Dict[str, Any]:
    """Detect GPU information and capabilities"""
    gpu_info = {
        "nvidia": {"available": False, "devices": []},
        "amd": {"available": False, "devices": []},
        "integrated": {"available": False, "devices": []},
        "recommended_backend": "cpu",
    }

    try:
        if platform.system() == "Windows":
            gpu_info = detect_windows_gpu()
        elif platform.system() == "Linux":
            gpu_info = detect_linux_gpu()

    except Exception as e:
        logger.error(f"Error detecting GPU: {e}")
        gpu_info["error"] = str(e)

    return gpu_info


def detect_windows_gpu() -> Dict[str, Any]:
    """Detect GPU on Windows using PowerShell"""
    gpu_info = {
        "nvidia": {"available": False, "devices": []},
        "amd": {"available": False, "devices": []},
        "integrated": {"available": False, "devices": []},
        "recommended_backend": "cpu",
    }

    try:
        # Use PowerShell to get GPU information
        result = subprocess.run(
            [
                "powershell",
                "-Command",
                "Get-WmiObject -Class Win32_VideoController | Select-Object Name, AdapterRAM | Format-Table -HideTableHeaders",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )

        if result.returncode == 0:
            lines = [line.strip() for line in result.stdout.split("\n") if line.strip()]

            for line in lines:
                line_lower = line.lower()

                # Clean up device name by removing large numbers (RAM amounts)
                clean_name = clean_device_name(line)
                if not clean_name:
                    continue

                # NVIDIA detection
                if any(
                    keyword in line_lower for keyword in ["nvidia", "geforce", "quadro", "tesla"]
                ):
                    gpu_info["nvidia"]["available"] = True
                    gpu_info["nvidia"]["devices"].append(clean_name)
                    gpu_info["recommended_backend"] = "cuda"

                # AMD detection
                elif any(keyword in line_lower for keyword in ["amd", "radeon", "rx"]):
                    gpu_info["amd"]["available"] = True
                    gpu_info["amd"]["devices"].append(clean_name)
                    # Não forçar ROCm automaticamente - deixar CPU como padrão
                    # if gpu_info["recommended_backend"] == "cpu":  # Only if no NVIDIA found
                    #     gpu_info["recommended_backend"] = "rocm"

                # Integrated GPU detection
                elif any(
                    keyword in line_lower for keyword in ["intel", "integrated", "uhd", "iris"]
                ):
                    gpu_info["integrated"]["available"] = True
                    gpu_info["integrated"]["devices"].append(clean_name)

    except Exception as e:
        logger.error(f"Error detecting Windows GPU: {e}")

    return gpu_info


def clean_device_name(device_name: str) -> str:
    """Clean up device name by removing unnecessary information"""
    if not device_name or not isinstance(device_name, str):
        return ""

    # Remove large numbers at the end (likely RAM amounts)
    cleaned = device_name.strip()

    # Remove numbers with 8+ digits (RAM amounts like 4293918720)
    import re

    cleaned = re.sub(r"\s+\d{8,}$", "", cleaned)

    # Remove excessive whitespace
    cleaned = " ".join(cleaned.split())

    return cleaned


def detect_linux_gpu() -> Dict[str, Any]:
    """Detect GPU on Linux using various tools"""
    gpu_info = {
        "nvidia": {"available": False, "devices": []},
        "amd": {"available": False, "devices": []},
        "integrated": {"available": False, "devices": []},
        "recommended_backend": "cpu",
    }

    try:
        # Try nvidia-smi for NVIDIA
        try:
            result = subprocess.run(
                ["nvidia-smi", "-L"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                gpu_info["nvidia"]["available"] = True
                # Clean up nvidia-smi output
                devices = []
                for line in result.stdout.strip().split("\n"):
                    clean_name = clean_device_name(line)
                    if clean_name:
                        devices.append(clean_name)
                gpu_info["nvidia"]["devices"] = devices
                gpu_info["recommended_backend"] = "cuda"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Try lspci for AMD and integrated
        try:
            result = subprocess.run(["lspci", "-nn"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    line_lower = line.lower()
                    clean_name = clean_device_name(line)
                    if not clean_name:
                        continue

                    if "amd" in line_lower or "radeon" in line_lower:
                        gpu_info["amd"]["available"] = True
                        gpu_info["amd"]["devices"].append(clean_name)
                        # Não forçar ROCm automaticamente - deixar CPU como padrão
                        # if gpu_info["recommended_backend"] == "cpu":
                        #     gpu_info["recommended_backend"] = "rocm"
                    elif "intel" in line_lower and (
                        "graphics" in line_lower or "uhd" in line_lower
                    ):
                        gpu_info["integrated"]["available"] = True
                        gpu_info["integrated"]["devices"].append(clean_name)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    except Exception as e:
        logger.error(f"Error detecting Linux GPU: {e}")

    return gpu_info


def detect_memory_info() -> Dict[str, Any]:
    """Detect system memory information"""
    try:
        import psutil

        memory = psutil.virtual_memory()

        memory_info = {
            "total_gb": round(memory.total / (1024**3), 1),
            "available_gb": round(memory.available / (1024**3), 1),
            "usage_percent": memory.percent,
            "suitable_for_ai": memory.total >= 8 * (1024**3),  # 8GB minimum
        }

        # Determine AI suitability based on available memory
        if memory_info["total_gb"] >= 16:
            memory_info["ai_performance"] = "Excellent"
        elif memory_info["total_gb"] >= 8:
            memory_info["ai_performance"] = "Good"
        else:
            memory_info["ai_performance"] = "Limited"
            memory_info["suitable_for_ai"] = False

        return memory_info

    except ImportError:
        return {
            "total_gb": "Unknown",
            "available_gb": "Unknown",
            "usage_percent": "Unknown",
            "ai_performance": "Unknown",
            "suitable_for_ai": True,
        }
    except Exception as e:
        logger.error(f"Error detecting memory: {e}")
        return {"error": str(e), "suitable_for_ai": False}


def generate_recommendations(capabilities: Dict[str, Any]) -> List[str]:
    """Generate hardware-based recommendations"""
    recommendations = []

    gpu_info = capabilities.get("gpu", {})
    cpu_info = capabilities.get("cpu", {})
    memory_info = capabilities.get("memory", {})

    # GPU recommendations
    if gpu_info.get("nvidia", {}).get("available"):
        recommendations.append("✅ NVIDIA GPU detectada - Use método CUDA para melhor performance")
    elif gpu_info.get("amd", {}).get("available"):
        recommendations.append(
            "🟡 AMD GPU detectada - Opcional: método ROCm (Linux/WSL2) para aceleração GPU"
        )
    elif gpu_info.get("integrated", {}).get("available"):
        recommendations.append("🔵 GPU integrada detectada - Performance limitada, recomendado CPU")
    else:
        recommendations.append("💻 Nenhuma GPU dedicada - Use método CPU")

    # Memory recommendations
    if memory_info.get("total_gb", 0) < 8:
        recommendations.append("⚠️ Pouca RAM disponível - Use modelos menores ou cloud")
    elif memory_info.get("total_gb", 0) >= 16:
        recommendations.append("✅ RAM suficiente para modelos maiores")

    # CPU recommendations
    if cpu_info.get("ai_performance") == "Limited":
        recommendations.append("⚠️ CPU limitado - Considere cloud para melhor performance")

    return recommendations
