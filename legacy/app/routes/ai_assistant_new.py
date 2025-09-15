"""
AI Assistant Routes - Blueprint for AI functionality with lazy loading
"""

import logging

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

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


def reset_ai_assistant():
    """Reset the AI assistant instance to force reinitialization"""
    global _ai_assistant
    _ai_assistant = None


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
    ai = get_ai_assistant()
    if not ai.is_enabled():
        flash("Assistente de IA não está disponível.", "warning")
        return redirect(url_for("main.index"))

    # No auto-initialization - manual control only
    model_info = ai.get_model_info()
    chat_history = ai.get_chat_history()

    return render_template(
        "ai_assistant/index.html", model_info=model_info, chat_history=chat_history
    )


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
        # Get available models
        available_models = model_manager.get_available_models()
        downloaded_models = model_manager.get_downloaded_models()

        return render_template(
            "ai_assistant/models.html",
            available_models=available_models,
            downloaded_models=downloaded_models,
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

        success = model_manager.delete_model(model_name)

        if success:
            return jsonify({"success": True, "message": f"Modelo {model_name} removido"})
        else:
            return jsonify({"success": False, "error": "Falha ao remover modelo"}), 500

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
        # Get predefined templates
        templates_data = ai.get_template_data()
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

        ai = get_ai_assistant()

        # Apply template with context
        result = ai.apply_template(template_id, context)

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
            "Análise odontológica baseada nos sintomas apresentados", context
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

        result = ai.generate_response("Plano de tratamento odontológico", context)

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
