"""
AI Assistant Routes - Blueprint for AI functionality with lazy loading
"""

import json
import logging
import time
from pathlib import Path

from flask import Blueprint, Response, flash, jsonify, redirect, render_template, request, url_for

from app.decorators import debug_login_optional

logger = logging.getLogger(__name__)

# Create blueprint
ai_assistant_bp = Blueprint("ai_assistant", __name__, url_prefix="/ai")

# Initialize lazy loading variables
_ai_assistant = None
_model_manager = None


def get_ai_assistant():
    """Get AI assistant instance with lazy loading"""
    global _ai_assistant
    if _ai_assistant is None:
        from app.services.ai_assistant import ai_assistant

        _ai_assistant = ai_assistant
    return _ai_assistant


def get_model_manager():
    """Get model manager instance with lazy loading"""
    global _model_manager
    if _model_manager is None:
        from app.services.model_manager import ModelManager

        _model_manager = ModelManager()
    return _model_manager


@ai_assistant_bp.route("/")
@debug_login_optional
def index():
    """Main AI Assistant interface"""
    try:
        ai = get_ai_assistant()
        if not ai.is_enabled():
            flash("Assistente de IA não está habilitado nas configurações.", "warning")
            return redirect(url_for("main.dashboard"))

        # Check if AI is initialized
        if not ai.is_initialized:
            # Show initialization page instead of auto-initializing
            return render_template(
                "ai_assistant/initialize.html",
                model_info={"status": "not_initialized"},
                show_initialize_button=True,
            )

        # AI is initialized, show normal interface
        model_info = ai.get_model_info()
        chat_history = ai.get_chat_history()

        return render_template(
            "ai_assistant/index.html", model_info=model_info, chat_history=chat_history
        )
    except Exception as e:
        flash(f"Erro ao acessar o Assistente de IA: {str(e)}", "error")
        return redirect(url_for("main.dashboard"))


@ai_assistant_bp.route("/chat", methods=["POST"])
@debug_login_optional
def chat():
    """Handle chat requests"""
    ai = get_ai_assistant()
    if not ai.is_enabled():
        return jsonify({"success": False, "error": "AI Assistant not available"}), 503

    # Try to initialize if not already initialized
    if not ai.is_initialized:
        try:
            if not ai.initialize():
                return (
                    jsonify({"success": False, "error": "Failed to initialize AI Assistant"}),
                    503,
                )
        except Exception as e:
            logger.error(f"Failed to initialize AI Assistant during chat: {e}")
            return (
                jsonify({"success": False, "error": f"Initialization error: {str(e)}"}),
                503,
            )

    try:
        data = request.get_json()
        query = data.get("query", "").strip()
        context = data.get("context", "")

        if not query:
            return jsonify({"success": False, "error": "Query is required"}), 400

        # Generate AI response
        result = ai.generate_response(query, context)

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in AI chat: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


@ai_assistant_bp.route("/status")
@debug_login_optional
def status():
    """Get AI Assistant status"""
    ai = get_ai_assistant()
    return jsonify(ai.get_model_info())


@ai_assistant_bp.route("/history")
@debug_login_optional
def history():
    """Get chat history"""
    ai = get_ai_assistant()
    return jsonify({"history": ai.get_chat_history()})


@ai_assistant_bp.route("/clear-history", methods=["POST"])
@debug_login_optional
def clear_history():
    """Clear chat history"""
    ai = get_ai_assistant()
    try:
        ai.clear_history()
        flash("Histórico limpo com sucesso!", "success")
        return jsonify({"success": True, "message": "Histórico limpo"})
    except Exception as e:
        logger.error(f"Error clearing history: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@ai_assistant_bp.route("/initialize", methods=["POST"])
@debug_login_optional
def initialize():
    """Initialize AI Assistant"""
    ai = get_ai_assistant()
    try:
        success = ai.initialize()
        if success:
            flash("AI Assistant inicializado com sucesso!", "success")
            return jsonify({"success": True, "message": "AI inicializado"})
        else:
            flash("Falha ao inicializar AI Assistant.", "error")
            return jsonify({"success": False, "error": "Falha na inicialização"}), 500
    except Exception as e:
        logger.error(f"Error initializing AI: {e}")
        flash(f"Erro ao inicializar: {str(e)}", "error")
        return jsonify({"success": False, "error": str(e)}), 500


@ai_assistant_bp.route("/config")
@debug_login_optional
def config():
    """AI Configuration page"""
    ai = get_ai_assistant()
    if not ai.is_enabled():
        flash("Assistente de IA não está disponível.", "warning")
        return redirect(url_for("main.index"))

    # Get configuration data
    config_data = ai.get_configuration_data()

    return render_template("ai_assistant/config.html", config=config_data)


@ai_assistant_bp.route("/config", methods=["POST"])
@debug_login_optional
def update_config():
    """Update AI configuration"""
    ai = get_ai_assistant()
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400

        # Validate required fields
        required_fields = ["ai_enabled", "provider", "model_name"]
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "error": f"Missing field: {field}"}), 400

        # Create configuration object
        config_data = {
            "ai_enabled": data["ai_enabled"],
            "provider": data["provider"],
            "model_name": data["model_name"],
            "model_path": data.get("model_path", ""),
            "temperature": float(data.get("temperature", 0.7)),
            "max_tokens": int(data.get("max_tokens", 1000)),
        }

        # Update configuration
        success = ai.update_configuration(config_data)

        if success:
            flash("Configuração atualizada com sucesso!", "success")
            return jsonify({"success": True, "message": "Configuração salva"})
        else:
            return jsonify({"success": False, "error": "Falha ao salvar configuração"}), 500

    except Exception as e:
        logger.error(f"Error updating AI config: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@ai_assistant_bp.route("/stop", methods=["POST"])
@debug_login_optional
def stop():
    """Stop AI Assistant"""
    ai = get_ai_assistant()
    try:
        success = ai.stop()
        if success:
            flash("AI Assistant parado com sucesso!", "success")
            return jsonify({"success": True, "message": "AI parado"})
        else:
            return jsonify({"success": False, "error": "Falha ao parar AI"}), 500
    except Exception as e:
        logger.error(f"Error stopping AI: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@ai_assistant_bp.route("/detailed-status")
@debug_login_optional
def detailed_status():
    """Get detailed AI status for debugging"""
    ai = get_ai_assistant()
    try:
        status = ai.get_detailed_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting detailed status: {e}")
        return jsonify({"error": str(e)}), 500


# Model Management Routes
@ai_assistant_bp.route("/models")
@debug_login_optional
def models():
    """Model management page"""
    ai = get_ai_assistant()
    if not ai.is_enabled():
        flash("Assistente de IA não está disponível.", "warning")
        return redirect(url_for("main.index"))

    model_manager = get_model_manager()

    try:
        # Get available and installed models
        installed_models = model_manager.get_installed_models()
        # For available models, we'll use a placeholder or load from config
        available_models = []

        return render_template(
            "ai_assistant/models.html",
            available_models=available_models,
            downloaded_models=installed_models,
        )
    except Exception as e:
        logger.error(f"Error loading models page: {e}")
        flash(f"Erro ao carregar modelos: {str(e)}", "error")
        return redirect(url_for("ai_assistant.index"))


@ai_assistant_bp.route("/models/download", methods=["POST"])
@debug_login_optional
def download_model():
    """Download a model"""
    model_manager = get_model_manager()

    try:
        data = request.get_json()
        model_name = data.get("model_name")

        if not model_name:
            return jsonify({"success": False, "error": "Model name required"}), 400

        # Start download (this should be async in real implementation)
        success = model_manager.download_model(model_name)

        if success:
            return jsonify({"success": True, "message": f"Download de {model_name} iniciado"})
        else:
            return jsonify({"success": False, "error": "Falha ao iniciar download"}), 500

    except Exception as e:
        logger.error(f"Error downloading model: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@ai_assistant_bp.route("/models/delete", methods=["POST"])
@debug_login_optional
def delete_model():
    """Delete a downloaded model"""
    model_manager = get_model_manager()

    try:
        data = request.get_json()
        model_name = data.get("model_name")

        if not model_name:
            return jsonify({"success": False, "error": "Model name required"}), 400

        result = model_manager.remove_model(model_name)

        if result.get("success"):
            return jsonify({"success": True, "message": f"Modelo {model_name} removido"})
        else:
            return (
                jsonify(
                    {"success": False, "error": result.get("error", "Falha ao remover modelo")}
                ),
                500,
            )

    except Exception as e:
        logger.error(f"Error deleting model: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@ai_assistant_bp.route("/templates")
@debug_login_optional
def templates():
    """Template management page"""
    ai = get_ai_assistant()
    if not ai.is_enabled():
        flash("Assistente de IA não está disponível.", "warning")
        return redirect(url_for("main.index"))

    try:
        # Return basic template data (placeholder implementation)
        templates_data = {
            "predefined_templates": [
                {
                    "id": "consultation",
                    "name": "Consulta Odontológica",
                    "description": "Template para consultas",
                },
                {
                    "id": "prescription",
                    "name": "Prescrição",
                    "description": "Template para prescrições",
                },
                {
                    "id": "treatment",
                    "name": "Plano de Tratamento",
                    "description": "Template para tratamentos",
                },
            ]
        }
        return render_template("ai_assistant/templates.html", templates=templates_data)
    except Exception as e:
        logger.error(f"Error loading templates: {e}")
        flash(f"Erro ao carregar templates: {str(e)}", "error")
        return redirect(url_for("ai_assistant.index"))


@ai_assistant_bp.route("/templates/use", methods=["POST"])
@debug_login_optional
def use_template():
    """Use a predefined template"""
    try:
        data = request.get_json()
        template_id = data.get("template_id")
        context = data.get("context", {})

        if not template_id:
            return jsonify({"success": False, "error": "Template ID required"}), 400

        # Simple template application (placeholder implementation)
        result = f"Template {template_id} aplicado com contexto: {context}"

        return jsonify({"success": True, "result": result})

    except Exception as e:
        logger.error(f"Error using template: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# Dental-specific AI routes
@ai_assistant_bp.route("/dental/diagnosis", methods=["POST"])
@debug_login_optional
def dental_diagnosis():
    """AI-assisted dental diagnosis"""
    ai = get_ai_assistant()

    try:
        data = request.get_json()
        symptoms = data.get("symptoms", "")
        patient_history = data.get("patient_history", "")

        if not symptoms:
            return jsonify({"success": False, "error": "Symptoms required"}), 400

        # Create dental diagnosis prompt
        context = f"""
        Sintomas relatados: {symptoms}
        Histórico do paciente: {patient_history}

        Por favor, forneça uma análise odontológica preliminar considerando:
        1. Possíveis diagnósticos diferenciais
        2. Exames complementares recomendados
        3. Tratamentos possíveis
        4. Urgência do caso

        Lembre-se: Esta é apenas uma assistência e não substitui o exame clínico.
        """

        result = ai.generate_response(
            "Analise odontologica baseada nos sintomas apresentados", context
        )

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in dental diagnosis: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@ai_assistant_bp.route("/dental/treatment-plan", methods=["POST"])
@debug_login_optional
def treatment_plan():
    """AI-assisted treatment planning"""
    ai = get_ai_assistant()

    try:
        data = request.get_json()
        diagnosis = data.get("diagnosis", "")
        patient_info = data.get("patient_info", "")

        if not diagnosis:
            return jsonify({"success": False, "error": "Diagnosis required"}), 400

        context = f"""
        Diagnóstico: {diagnosis}
        Informações do paciente: {patient_info}

        Por favor, elabore um plano de tratamento odontológico considerando:
        1. Prioridades de tratamento
        2. Sequência de procedimentos
        3. Estimativa de sessões
        4. Cuidados pós-tratamento
        5. Alternativas de tratamento
        """

        result = ai.generate_response("Plano de tratamento odontologico", context)

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in treatment planning: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@ai_assistant_bp.route("/settings")
@debug_login_optional
def settings():
    """AI Assistant settings page"""
    ai = get_ai_assistant()
    try:
        config_data = ai.get_configuration_data()
        return render_template("ai_assistant/settings.html", config=config_data)
    except Exception as e:
        logger.error(f"Error loading AI settings: {e}")
        flash(f"Erro ao carregar configurações: {str(e)}", "error")
        return redirect(url_for("ai_assistant.index"))


# API Routes for AJAX calls
@ai_assistant_bp.route("/api/config")
@debug_login_optional
def api_config():
    """API endpoint to get AI configuration"""
    try:
        ai = get_ai_assistant()
        config_data = ai.get_configuration_data()
        return jsonify({"success": True, "config": config_data})
    except Exception as e:
        logger.error(f"Error getting API config: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@ai_assistant_bp.route("/api/status")
@debug_login_optional
def api_status():
    """API endpoint to get AI status"""
    try:
        ai = get_ai_assistant()
        status = ai.get_detailed_status()
        return jsonify({"success": True, "status": status})
    except Exception as e:
        logger.error(f"Error getting API status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@ai_assistant_bp.route("/api/models/search")
@debug_login_optional
def api_models_search():
    """API endpoint to search for models"""
    try:
        query = request.args.get("query", "")
        category = request.args.get("category", "all")

        model_manager = get_model_manager()
        results = model_manager.search_huggingface_models(query, filter_type=category)

        return jsonify({"success": True, "models": results, "query": query, "total": len(results)})

    except Exception as e:
        logger.error(f"Error searching models: {e}")
        return jsonify({"success": False, "error": str(e), "models": []}), 500


@ai_assistant_bp.route("/api/models/download", methods=["POST"])
@debug_login_optional
def api_models_download():
    """API endpoint to download a model"""
    try:
        data = request.get_json()
        model_name = data.get("model_name")

        if not model_name:
            return jsonify({"success": False, "error": "Model name required"}), 400

        from app.services.download_progress import download_manager

        # Verificar se já está baixando
        if download_manager.is_downloading(model_name):
            return (
                jsonify(
                    {"success": False, "error": "Download já em andamento", "downloading": True}
                ),
                409,
            )

        # Iniciar download
        success = download_manager.start_download(model_name)

        if success:
            return jsonify(
                {
                    "success": True,
                    "message": f"Download de {model_name} iniciado",
                    "downloading": True,
                }
            )
        else:
            return jsonify({"success": False, "error": "Falha ao iniciar download"}), 500

    except Exception as e:
        logger.error(f"Error downloading model: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@ai_assistant_bp.route("/api/models/<path:model_name>/progress")
@debug_login_optional
def api_model_progress(model_name):
    """API endpoint to get model download progress"""
    try:
        from urllib.parse import unquote

        from app.services.download_progress import download_manager

        # Decodificar o nome do modelo (suporta path com :)
        decoded_model_name = unquote(model_name)

        # Obter progresso real do download
        progress = download_manager.get_progress(decoded_model_name)

        # Formatar resposta
        response = {
            "status": progress.get("status", "Não iniciado"),
            "progress": progress.get("progress", 0),
            "downloading": progress.get("downloading", False),
            "error": progress.get("error"),
        }

        # Adicionar informações detalhadas se disponíveis
        if progress.get("total_bytes", 0) > 0:
            downloaded_mb = progress.get("downloaded_bytes", 0) / (1024 * 1024)
            total_mb = progress.get("total_bytes", 0) / (1024 * 1024)

            response.update(
                {
                    "downloaded": f"{downloaded_mb:.1f} MB",
                    "total_size": f"{total_mb:.1f} MB",
                    "downloaded_bytes": progress.get("downloaded_bytes", 0),
                    "total_bytes": progress.get("total_bytes", 0),
                }
            )

        # Adicionar velocidade se disponível
        if progress.get("speed", 0) > 0:
            speed_mb = progress.get("speed", 0) / (1024 * 1024)
            response["speed"] = f"{speed_mb:.1f} MB/s"

        # Adicionar ETA se disponível
        if progress.get("eta", 0) > 0:
            eta_minutes = int(progress.get("eta", 0) // 60)
            eta_seconds = int(progress.get("eta", 0) % 60)
            if eta_minutes > 0:
                response["eta"] = f"{eta_minutes}min {eta_seconds}s"
            else:
                response["eta"] = f"{eta_seconds}s"

        return jsonify(response)
    except Exception as e:
        logger.error(f"Error getting model progress: {e}")
        return jsonify({"error": str(e)}), 500


@ai_assistant_bp.route("/api/models/<path:model_name>/cancel", methods=["POST"])
@debug_login_optional
def api_model_cancel(model_name):
    """API endpoint to cancel model download"""
    try:
        from urllib.parse import unquote

        from app.services.download_progress import download_manager

        # Decodificar o nome do modelo (suporta path com :)
        decoded_model_name = unquote(model_name)

        success = download_manager.cancel_download(decoded_model_name)

        if success:
            return jsonify({"success": True, "message": f"Download de {model_name} cancelado"})
        else:
            return (
                jsonify({"success": False, "error": "Download não encontrado ou já concluído"}),
                404,
            )
    except Exception as e:
        logger.error(f"Error canceling model download: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@ai_assistant_bp.route("/api/models/<model_name>/progress/stream")
@debug_login_optional
def api_model_progress_stream(model_name):
    """API endpoint para stream de progresso via Server-Sent Events"""
    from app.services.download_progress import download_manager

    def generate():
        last_progress = None

        while True:
            try:
                # Obter progresso atual
                progress = download_manager.get_progress(model_name)

                # Enviar apenas se houver mudança
                if progress != last_progress:
                    data = {"model": model_name, "progress": progress, "timestamp": time.time()}

                    yield f"data: {json.dumps(data)}\n\n"
                    last_progress = progress.copy()

                # Parar se download terminou
                if not progress.get("downloading", False):
                    break

                time.sleep(0.5)  # Atualizar a cada 500ms

            except Exception as e:
                # Enviar erro via SSE
                error_data = {"model": model_name, "error": str(e), "timestamp": time.time()}
                yield f"data: {json.dumps(error_data)}\n\n"
                break

    return Response(generate(), mimetype="text/event-stream")


@ai_assistant_bp.route("/api/models/remove", methods=["POST", "DELETE"])
@debug_login_optional
def api_models_remove():
    """API endpoint to remove a model"""
    try:
        data = request.get_json()
        model_name = data.get("model_name")

        if not model_name:
            return jsonify({"success": False, "error": "Model name required"}), 400

        model_manager = get_model_manager()
        result = model_manager.remove_model(model_name)

        if result.get("success"):
            return jsonify(
                {
                    "success": True,
                    "message": f"Modelo {model_name} removido",
                    "space_freed": result.get("space_freed", "N/A"),
                }
            )
        else:
            return (
                jsonify(
                    {"success": False, "error": result.get("error", "Falha ao remover modelo")}
                ),
                500,
            )

    except Exception as e:
        logger.error(f"Error removing model: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@ai_assistant_bp.route("/api/models/cleanup", methods=["POST"])
@debug_login_optional
def api_models_cleanup():
    """API endpoint to cleanup unused models and locks"""
    try:
        from pathlib import Path

        model_manager = get_model_manager()
        cache_dir = Path(model_manager.cache_dir)
        locks_dir = cache_dir / ".locks"

        cleaned_files = 0
        space_freed = 0

        # Clean .locks directory
        if locks_dir.exists():
            for item in locks_dir.rglob("*"):
                if item.is_file():
                    try:
                        file_size = item.stat().st_size
                        item.unlink()
                        cleaned_files += 1
                        space_freed += file_size
                        logger.info(f"Removed lock file: {item}")
                    except Exception as e:
                        logger.warning(f"Could not remove lock file {item}: {e}")

            # Remove empty lock directories
            for item in locks_dir.rglob("*"):
                if item.is_dir() and not any(item.iterdir()):
                    try:
                        item.rmdir()
                        logger.info(f"Removed empty lock directory: {item}")
                    except Exception as e:
                        logger.warning(f"Could not remove empty directory {item}: {e}")

        # Clean incomplete/temporary files in cache
        if cache_dir.exists():
            for item in cache_dir.rglob("*"):
                if item.is_file():
                    # Remove files with temporary extensions or incomplete downloads
                    if (
                        item.suffix in [".tmp", ".temp", ".part", ".download"]
                        or item.name.startswith("tmp")
                        or item.name.endswith(".incomplete")
                    ):
                        try:
                            file_size = item.stat().st_size
                            item.unlink()
                            cleaned_files += 1
                            space_freed += file_size
                            logger.info(f"Removed temporary file: {item}")
                        except Exception as e:
                            logger.warning(f"Could not remove temporary file {item}: {e}")

        # Format space freed
        if space_freed > 1024**3:  # GB
            space_freed_str = f"{space_freed / (1024**3):.2f} GB"
        elif space_freed > 1024**2:  # MB
            space_freed_str = f"{space_freed / (1024**2):.1f} MB"
        elif space_freed > 1024:  # KB
            space_freed_str = f"{space_freed / 1024:.1f} KB"
        else:
            space_freed_str = f"{space_freed} bytes"

        return jsonify(
            {
                "success": True,
                "cleaned_files": cleaned_files,
                "space_freed": space_freed_str,
                "message": f"Cache limpo: {cleaned_files} arquivos removidos",
            }
        )

    except Exception as e:
        logger.error(f"Error cleaning up models: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@ai_assistant_bp.route("/api/update-config", methods=["POST"])
@debug_login_optional
def api_update_config():
    """API endpoint to update AI configuration"""
    try:
        data = request.get_json()
        ai = get_ai_assistant()
        success = ai.update_configuration(data)

        if success:
            return jsonify({"success": True, "message": "Configuração atualizada"})
        else:
            return jsonify({"success": False, "error": "Falha ao atualizar configuração"}), 500

    except Exception as e:
        logger.error(f"Error updating config: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@ai_assistant_bp.route("/api/start", methods=["POST"])
@debug_login_optional
def api_start():
    """API endpoint to start AI"""
    try:
        ai = get_ai_assistant()
        result = ai.initialize()
        if result:
            status = ai.get_detailed_status()
            return jsonify(
                {"success": True, "message": "AI inicializado com sucesso", "status": status}
            )
        else:
            return jsonify({"success": False, "error": "Falha ao inicializar AI"}), 500
    except Exception as e:
        logger.error(f"Error starting AI: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@ai_assistant_bp.route("/api/stop", methods=["POST"])
@debug_login_optional
def api_stop():
    """API endpoint to stop AI"""
    try:
        ai = get_ai_assistant()
        ai.stop()
        status = ai.get_detailed_status()
        return jsonify({"success": True, "message": "AI parado", "status": status})
    except Exception as e:
        logger.error(f"Error stopping AI: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@ai_assistant_bp.route("/api/hardware-info")
@debug_login_optional
def api_hardware_info():
    """API endpoint to get hardware information"""
    try:
        # Try to get real hardware info first
        try:
            from app.services.hardware_detector import detect_system_capabilities

            hardware_info = detect_system_capabilities()
        except ImportError as e:
            logger.warning(f"Hardware detector dependencies missing: {e}")
            # Fallback to basic system info
            import os
            import platform

            hardware_info = {
                "cpu": {
                    "cores": os.cpu_count() or 4,
                    "threads": os.cpu_count() or 4,
                    "architecture": platform.processor() or platform.machine(),
                    "suitable_for_ai": True,
                    "ai_performance": "Unknown",
                },
                "gpu": {
                    "recommended_backend": "cpu",
                    "nvidia": {"available": False, "devices": []},
                    "amd": {"available": False, "devices": []},
                    "integrated": {"available": False, "devices": []},
                },
                "memory": {
                    "total_gb": "Unknown",
                    "available_gb": "Unknown",
                    "suitable_for_ai": True,
                    "ai_performance": "Unknown",
                },
                "recommendations": ["⚠️ Instale 'psutil' para detecção completa de hardware"],
            }
        except Exception as e:
            logger.error(f"Error in hardware detection: {e}")
            # Basic fallback
            hardware_info = {
                "cpu": {"cores": 4, "threads": 4, "suitable_for_ai": True},
                "gpu": {"recommended_backend": "cpu"},
                "memory": {"suitable_for_ai": True},
                "recommendations": [f"❌ Erro na detecção: {str(e)}"],
            }

        # Return in format expected by JavaScript
        return jsonify({"success": True, "hardware": hardware_info})
    except Exception as e:
        logger.error(f"Critical error getting hardware info: {e}")
        return (
            jsonify(
                {"success": False, "error": f"Falha crítica na detecção de hardware: {str(e)}"}
            ),
            500,
        )


@ai_assistant_bp.route("/test-hardware")
@debug_login_optional
def test_hardware():
    """Test page for hardware detection"""
    return """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Hardware Detection</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; }
        .info { margin: 10px 0; padding: 10px; border: 1px solid #ccc; }
        .error { color: red; }
        .success { color: green; }
    </style>
</head>
<body>
    <h1>Hardware Detection Test</h1>

    <button onclick="testHardwareDetection()">Test Hardware Detection</button>

    <div id="results"></div>

    <script>
        async function testHardwareDetection() {
            const resultsDiv = document.getElementById('results');
            resultsDiv.innerHTML = '<p>Testing hardware detection...</p>';

            try {
                const response = await fetch('/ai/api/hardware-info');

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const data = await response.json();
                console.log('Hardware data:', data);

                if (data.success) {
                    const hardware = data.hardware;

                    let html = '<div class="success">✅ Hardware detection successful!</div>';

                    // CPU info
                    html += '<div class="info"><h3>CPU</h3>';
                    if (hardware.cpu) {
                        html += `<p>Cores: ${hardware.cpu.cores || 'N/A'}</p>`;
                        html += `<p>Threads: ${hardware.cpu.threads || 'N/A'}</p>`;
                        html += `<p>AI Performance: ${hardware.cpu.ai_performance || 'Unknown'}</p>`;
                    }
                    html += '</div>';

                    // Memory info
                    html += '<div class="info"><h3>Memory</h3>';
                    if (hardware.memory) {
                        html += `<p>Total: ${hardware.memory.total_gb || 'N/A'} GB</p>`;
                        html += `<p>Available: ${hardware.memory.available_gb || 'N/A'} GB</p>`;
                        html += `<p>AI Performance: ${hardware.memory.ai_performance || 'Unknown'}</p>`;
                    }
                    html += '</div>';

                    // GPU info
                    html += '<div class="info"><h3>GPU</h3>';
                    if (hardware.gpu) {
                        if (hardware.gpu.nvidia && hardware.gpu.nvidia.available) {
                            html += '<p><strong>NVIDIA GPU:</strong> ';
                            if (hardware.gpu.nvidia.devices && Array.isArray(hardware.gpu.nvidia.devices)) {
                                html += hardware.gpu.nvidia.devices.join(', ');
                            } else {
                                html += 'No device info';
                            }
                            html += '</p>';
                        }

                        if (hardware.gpu.amd && hardware.gpu.amd.available) {
                            html += '<p><strong>AMD GPU:</strong> ';
                            if (hardware.gpu.amd.devices && Array.isArray(hardware.gpu.amd.devices)) {
                                html += hardware.gpu.amd.devices.join(', ');
                            } else {
                                html += 'No device info';
                            }
                            html += '</p>';
                        }

                        if (hardware.gpu.integrated && hardware.gpu.integrated.available) {
                            html += '<p><strong>Integrated GPU:</strong> ';
                            if (hardware.gpu.integrated.devices && Array.isArray(hardware.gpu.integrated.devices)) {
                                html += hardware.gpu.integrated.devices.join(', ');
                            } else {
                                html += 'No device info';
                            }
                            html += '</p>';
                        }

                        if (!hardware.gpu.nvidia?.available && !hardware.gpu.amd?.available && !hardware.gpu.integrated?.available) {
                            html += '<p>No GPU detected</p>';
                        }
                    }
                    html += '</div>';

                    // Recommendations
                    if (hardware.recommendations && Array.isArray(hardware.recommendations)) {
                        html += '<div class="info"><h3>Recommendations</h3>';
                        hardware.recommendations.forEach(rec => {
                            html += `<p>• ${rec}</p>`;
                        });
                        html += '</div>';
                    }

                    resultsDiv.innerHTML = html;

                } else {
                    throw new Error(data.error || 'Hardware detection failed');
                }

            } catch (error) {
                console.error('Error:', error);
                resultsDiv.innerHTML = `<div class="error">❌ Error: ${error.message}</div>`;
            }
        }
    </script>
</body>
</html>
    """


@ai_assistant_bp.route("/api/models/installed")
@debug_login_optional
def api_models_installed():
    """API endpoint to get installed models"""
    try:
        # Import ModelManager only when needed
        from app.services.model_manager import ModelManager

        model_manager = ModelManager()
        installed_models = model_manager.get_installed_models()

        return jsonify({"success": True, "models": installed_models})

    except Exception as e:
        logger.error(f"Error getting installed models: {e}")
        return jsonify({"success": False, "error": str(e), "models": []}), 500


@ai_assistant_bp.route("/api/models/available")
@debug_login_optional
def api_models_available():
    """API endpoint to get available models for download"""
    try:
        # Import ModelManager only when needed
        from app.services.model_manager import ModelManager

        model_manager = ModelManager()
        if not model_manager.is_available():
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Model manager dependencies not available",
                        "models": [],
                    }
                ),
                503,
            )

        # Try to load from config file first
        available_models = []
        try:
            config_path = Path("config/available_models.json")
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)

                # Get models from config and check if they're installed
                for model_config in config.get("recommended_models", []):
                    model_name = model_config["name"]
                    is_installed = any(
                        installed_model["name"] == model_name
                        for installed_model in model_manager.get_installed_models()
                    )

                    available_models.append(
                        {
                            "name": model_name,
                            "description": model_config.get("description", f"Model: {model_name}"),
                            "size": model_config.get("size_estimate", "Unknown"),
                            "type": model_config.get("type", "general"),
                            "recommended": model_config.get("recommended", False),
                            "tags": model_config.get("tags", []),
                            "installed": is_installed,
                        }
                    )
            else:
                logger.warning("Config file not found, using ModelManager recommended models")
                raise FileNotFoundError("Config file not available")

        except Exception as e:
            logger.warning(f"Failed to load from config file: {e}, using ModelManager")
            # Fallback to ModelManager's recommended models
            recommended_models = model_manager._get_recommended_models()
            available_models = [
                {
                    "name": model["name"],
                    "description": model.get("description", f"Model: {model['name']}"),
                    "size": model.get("size_estimate", "Unknown"),
                    "type": model.get("type", "general"),
                    "recommended": True,
                    "tags": [],
                    "installed": model.get("installed", False),
                }
                for model in recommended_models
            ]

        return jsonify(
            {"success": True, "models": available_models, "total": len(available_models)}
        )

    except Exception as e:
        logger.error(f"Error getting available models: {e}")
        return jsonify({"success": False, "error": str(e), "models": []}), 500


@ai_assistant_bp.route("/api/models")
@debug_login_optional
def api_models():
    """API endpoint to get both installed and available models"""
    try:
        # Import ModelManager only when needed
        from app.services.model_manager import ModelManager

        model_manager = ModelManager()
        installed_models = model_manager.get_installed_models()

        # Get available models dynamically
        available_models = []
        if model_manager.is_available():
            try:
                # Try to load from config file first
                config_path = Path("config/available_models.json")
                if config_path.exists():
                    with open(config_path, "r", encoding="utf-8") as f:
                        config = json.load(f)

                    # Get models from config, filtering out already installed ones
                    installed_names = {model["name"] for model in installed_models}

                    for model_config in config.get("recommended_models", []):
                        model_name = model_config["name"]

                        # Only include if not already installed
                        if model_name not in installed_names:
                            available_models.append(
                                {
                                    "name": model_name,
                                    "description": model_config.get(
                                        "description", f"Model: {model_name}"
                                    ),
                                    "size": model_config.get("size_estimate", "Unknown"),
                                    "type": model_config.get("type", "general"),
                                    "recommended": model_config.get("recommended", False),
                                    "tags": model_config.get("tags", []),
                                    "installed": False,
                                }
                            )
                else:
                    # Fallback to ModelManager's recommended models
                    recommended_models = model_manager._get_recommended_models()
                    installed_names = {model["name"] for model in installed_models}

                    for model in recommended_models:
                        if model["name"] not in installed_names:
                            available_models.append(
                                {
                                    "name": model["name"],
                                    "description": model.get(
                                        "description", f"Model: {model['name']}"
                                    ),
                                    "size": model.get("size_estimate", "Unknown"),
                                    "type": model.get("type", "general"),
                                    "recommended": True,
                                    "tags": [],
                                    "installed": False,
                                }
                            )

            except Exception as e:
                logger.warning(f"Failed to load available models: {e}")
                available_models = []

        return jsonify(
            {
                "success": True,
                "installed": installed_models,
                "available": available_models,
                "total_installed": len(installed_models),
                "total_available": len(available_models),
            }
        )

    except Exception as e:
        logger.error(f"Error getting models: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "installed": [],
                    "available": [],
                    "total_installed": 0,
                    "total_available": 0,
                }
            ),
            500,
        )


@ai_assistant_bp.route("/api/disk-usage")
@debug_login_optional
def api_disk_usage():
    """API endpoint to get disk usage information"""
    try:
        import shutil
        from pathlib import Path

        # Import ModelManager only when needed
        from app.services.model_manager import ModelManager

        model_manager = ModelManager()
        cache_dir = Path(model_manager.cache_dir)

        # Get disk usage for the cache directory
        try:
            total, used, free = shutil.disk_usage(cache_dir)
        except Exception as e:
            logger.error(f"Error getting disk usage: {e}")
            return jsonify({"success": False, "error": f"Unable to get disk usage: {str(e)}"}), 500

        # Calculate models cache usage
        models_cache_size = 0
        models_count = 0

        try:
            if cache_dir.exists():
                for item in cache_dir.iterdir():
                    if item.is_dir() and item.name.startswith("models--"):
                        models_count += 1
                        try:
                            for file_path in item.rglob("*"):
                                if file_path.is_file():
                                    try:
                                        models_cache_size += file_path.stat().st_size
                                    except (OSError, PermissionError):
                                        continue
                        except Exception:
                            continue
        except Exception as e:
            logger.warning(f"Error calculating models cache size: {e}")

        # Convert to human readable sizes
        total_gb = round(total / (1024**3), 2)
        used_gb = round(used / (1024**3), 2)
        free_gb = round(free / (1024**3), 2)

        models_cache_gb = round(models_cache_size / (1024**3), 2)
        models_cache_mb = round(models_cache_size / (1024**2), 1)

        return jsonify(
            {
                "success": True,
                "total_space_gb": total_gb,
                "used_space_gb": used_gb,
                "free_space_gb": free_gb,
                "available_space_gb": free_gb,
                "models_cache_size_gb": models_cache_gb,
                "models_cache_size_mb": models_cache_mb,
                "total_size_gb": models_cache_gb,
                "total_size_mb": models_cache_mb,
                "models_count": models_count,
                "cache_path": str(cache_dir),
            }
        )

    except Exception as e:
        logger.error(f"Error getting disk usage: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
