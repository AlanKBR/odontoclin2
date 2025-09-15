"""
Módulo com rotas relacionadas a receitas médicas.
"""

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user

from app.decorators import debug_login_optional
from app.models.clinica import Clinica  # Added import
from app.models.paciente import Paciente  # Added import
from app.models.receita import Medicamento, ModeloReceita
from app.models.user import User

receitas = Blueprint("receitas", __name__)


@receitas.route("/")
@debug_login_optional
def index():
    """Página principal de receitas."""
    clinica = Clinica.get_instance()
    return render_template("receitas/index.html", clinica=clinica)


@receitas.route("/nova")
@debug_login_optional
def nova_receita():
    """Página para criar nova receita."""
    pacientes = Paciente.query.order_by(Paciente.nome).all()

    # Somente dentistas ativos
    from app.extensions import db as _db

    dentistas = User.query.filter_by(cargo="dentista").filter(User.is_active_db == _db.true()).all()
    clinica = Clinica.get_instance()
    return render_template(
        "receitas/formulario_receita.html",
        pacientes=pacientes,
        dentistas=dentistas,
        clinica=clinica,
    )


@receitas.route("/medicamentos")
@debug_login_optional
def listar_medicamentos():
    """Lista todos os medicamentos cadastrados."""
    medicamentos = Medicamento.query.order_by(Medicamento.principio_ativo).all()
    return render_template("receitas/lista_medicamentos.html", medicamentos=medicamentos)


@receitas.route("/medicamentos/<int:medicamento_id>")
@debug_login_optional
def visualizar_medicamento(medicamento_id: int):
    """Visualiza detalhes de um medicamento específico."""
    medicamento = Medicamento.query.get_or_404(medicamento_id)

    # Todos os campos disponíveis do medicamento
    dados_medicamento = {
        "id": medicamento.id,
        "categoria": medicamento.categoria,
        "principio_ativo": medicamento.principio_ativo,
        "nome_referencia": medicamento.nome_referencia,
        "apresentacao": medicamento.apresentacao,
        "posologia": medicamento.posologia,
        "uso": medicamento.uso,
        "indicacoes": medicamento.indicacoes,
        "mecanismo_acao": medicamento.mecanismo_acao,
        "contraindicacoes": medicamento.contraindicacoes,
        "efeitos_colaterais": medicamento.efeitos_colaterais,
        "interacoes_medicamentosas": medicamento.interacoes_medicamentosas,
        "risco_gravidez": medicamento.risco_gravidez,
        "tipo_receita": medicamento.tipo_receita,
        "alerta_principal": medicamento.alerta_principal,
        "instrucao_compra": medicamento.instrucao_compra,
        "observacao": medicamento.observacao,
    }
    return render_template("receitas/visualizar_medicamento.html", medicamento=dados_medicamento)


@receitas.route("/medicamentos/todos", methods=["GET"])
@debug_login_optional
def obter_todos_medicamentos():
    """Obtém todos os medicamentos para busca instantânea no frontend."""
    medicamentos = Medicamento.query.order_by(Medicamento.principio_ativo).all()

    result = []
    for med in medicamentos:
        result.append(
            {
                "id": med.id,
                "principio_ativo": med.principio_ativo or "",
                "nome_referencia": med.nome_referencia or "",
                "categoria": med.categoria or "",
                "apresentacao": med.apresentacao or "",
                "posologia": med.posologia or "",
                "uso": med.uso or "",
                "indicacoes": med.indicacoes or "",
                "mecanismo_acao": med.mecanismo_acao or "",
                "contraindicacoes": med.contraindicacoes or "",
                "efeitos_colaterais": med.efeitos_colaterais or "",
                "interacoes_medicamentosas": med.interacoes_medicamentosas or "",
                "risco_gravidez": med.risco_gravidez or "",
                "tipo_receita": med.tipo_receita or "",
                "alerta_principal": med.alerta_principal or "",
                "instrucao_compra": med.instrucao_compra or "",
                "observacao": med.observacao or "",
            }
        )

    return jsonify(result)


@receitas.route("/medicamentos/buscar", methods=["GET"])
@debug_login_optional
def buscar_medicamentos():
    """Busca medicamentos por qualquer campo relevante da tabela."""
    termo = request.args.get("termo", "")
    if termo:
        filtro = (
            (Medicamento.categoria.ilike(f"%{termo}%"))
            | (Medicamento.principio_ativo.ilike(f"%{termo}%"))
            | (Medicamento.nome_referencia.ilike(f"%{termo}%"))
            | (Medicamento.apresentacao.ilike(f"%{termo}%"))
            | (Medicamento.posologia.ilike(f"%{termo}%"))
            | (Medicamento.uso.ilike(f"%{termo}%"))
            | (Medicamento.indicacoes.ilike(f"%{termo}%"))
            | (Medicamento.mecanismo_acao.ilike(f"%{termo}%"))
            | (Medicamento.contraindicacoes.ilike(f"%{termo}%"))
            | (Medicamento.efeitos_colaterais.ilike(f"%{termo}%"))
            | (Medicamento.interacoes_medicamentosas.ilike(f"%{termo}%"))
            | (Medicamento.risco_gravidez.ilike(f"%{termo}%"))
            | (Medicamento.tipo_receita.ilike(f"%{termo}%"))
            | (Medicamento.alerta_principal.ilike(f"%{termo}%"))
            | (Medicamento.instrucao_compra.ilike(f"%{termo}%"))
            | (Medicamento.observacao.ilike(f"%{termo}%"))
        )
        medicamentos = Medicamento.query.filter(filtro).order_by(Medicamento.principio_ativo).all()
    else:
        medicamentos = []

    # Se for uma solicitação AJAX, retorna JSON
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        result = []
        for med in medicamentos:
            result.append(
                {
                    "id": med.id,
                    "principio_ativo": med.principio_ativo,
                    "nome_referencia": med.nome_referencia,
                    "categoria": med.categoria,
                    "apresentacao": med.apresentacao,
                    "uso": med.uso,
                }
            )
        return jsonify(result)

    # Se não for AJAX, renderiza a página
    return render_template(
        "receitas/lista_medicamentos.html", medicamentos=medicamentos, termo_busca=termo
    )


@receitas.route("/modelos")
@debug_login_optional
def listar_modelos():
    """Lista todos os modelos de receita do usuário atual."""
    try:
        # Usar a sessão do banco de receitas através do multidb
        from app.multidb import multidb

        receitas_session = multidb.get_session("receitas")
        if receitas_session:
            modelos = (
                receitas_session.query(ModeloReceita).filter_by(usuario_id=current_user.id).all()
            )
        else:
            modelos = []
    except Exception as e:
        # Se a tabela não existe, retornar lista vazia
        print(f"Erro ao acessar modelos: {e}")
        modelos = []

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        # Retorna JSON para AJAX
        return jsonify([{"id": m.id, "titulo": m.titulo, "conteudo": m.conteudo} for m in modelos])
    return render_template("receitas/modelos_receita.html", modelos=modelos)


@receitas.route("/modelos/salvar", methods=["POST"])
@debug_login_optional
def salvar_modelo():
    """Salva um novo modelo de receita."""
    titulo = request.form.get("titulo")
    conteudo = request.form.get("conteudo")

    if not titulo or not conteudo:
        flash("Título e conteúdo são obrigatórios.", "danger")
        return redirect(url_for("receitas.listar_modelos"))

    try:
        from app.multidb import multidb

        receitas_session = multidb.get_session("receitas")
        if receitas_session:
            # Criar o modelo usando o construtor padrão do SQLAlchemy
            modelo = ModeloReceita()
            modelo.titulo = titulo  # type: ignore[assignment]
            modelo.conteudo = conteudo  # type: ignore[assignment]
            modelo.usuario_id = current_user.id

            receitas_session.add(modelo)
            receitas_session.commit()
            flash("Modelo de receita salvo com sucesso!", "success")
        else:
            flash("Erro ao acessar banco de dados de receitas.", "danger")
    except Exception as e:
        print(f"Erro ao salvar modelo: {e}")
        flash("Erro ao salvar modelo de receita.", "danger")

    return redirect(url_for("receitas.listar_modelos"))


@receitas.route("/modelos/<int:modelo_id>/visualizar")
@debug_login_optional
def visualizar_modelo(modelo_id: int):
    """Visualiza um modelo de receita."""
    try:
        from app.multidb import multidb

        receitas_session = multidb.get_session("receitas")
        if receitas_session:
            modelo = receitas_session.query(ModeloReceita).filter_by(id=modelo_id).first()
            if not modelo:
                flash("Modelo não encontrado.", "danger")
                return redirect(url_for("receitas.listar_modelos"))

            if modelo.usuario_id != current_user.id:
                flash("Você não tem permissão para acessar este modelo.", "danger")
                return redirect(url_for("receitas.listar_modelos"))

            # Criando uma cópia dos dados para evitar problemas de perda de dados
            dados_modelo = {
                "id": modelo.id,
                "titulo": modelo.titulo,
                "conteudo": modelo.conteudo,
                "usuario_id": modelo.usuario_id,
            }

            # Passa os dados do modelo como um objeto para o template
            from types import SimpleNamespace

            modelo_obj = SimpleNamespace(**dados_modelo)

            return render_template("receitas/visualizar_modelo.html", modelo=modelo_obj)
        else:
            flash("Erro ao acessar banco de dados.", "danger")
            return redirect(url_for("receitas.listar_modelos"))
    except Exception as e:
        print(f"Erro ao visualizar modelo: {e}")
        flash("Erro ao visualizar modelo.", "danger")
        return redirect(url_for("receitas.listar_modelos"))


@receitas.route("/modelos/<int:modelo_id>/excluir", methods=["POST"])
@debug_login_optional
def excluir_modelo(modelo_id: int):
    """Exclui um modelo de receita."""
    try:
        from app.multidb import multidb

        receitas_session = multidb.get_session("receitas")
        if receitas_session:
            modelo = receitas_session.query(ModeloReceita).filter_by(id=modelo_id).first()
            if not modelo:
                flash("Modelo não encontrado.", "danger")
                return redirect(url_for("receitas.listar_modelos"))

            if modelo.usuario_id != current_user.id:
                flash("Você não tem permissão para excluir este modelo.", "danger")
                return redirect(url_for("receitas.listar_modelos"))

            receitas_session.delete(modelo)
            receitas_session.commit()
            flash("Modelo de receita excluído com sucesso!", "success")
        else:
            flash("Erro ao acessar banco de dados.", "danger")
    except Exception as e:
        print(f"Erro ao excluir modelo: {e}")
        flash("Erro ao excluir modelo.", "danger")

    return redirect(url_for("receitas.listar_modelos"))


@receitas.route("/api/dentistas/<int:dentista_id>/dados-receita")
@debug_login_optional
def obter_dados_dentista_receita(dentista_id: int):
    """API para obter dados básicos do dentista para uso em receitas."""
    try:
        from app.extensions import db as _db

        dentista = (
            User.query.filter_by(id=dentista_id, cargo="dentista")
            .filter(User.is_active_db == _db.true())
            .first()
        )
        if not dentista:
            return jsonify({"error": "Dentista não encontrado"}), 404

        dados = {
            "id": dentista.id,
            "nome_completo": dentista.nome_completo,
            "nome_profissional": dentista.nome_profissional,
            "cro": dentista.cro or "",
            "username": dentista.username,
        }

        return jsonify(dados)
    except Exception:
        return jsonify({"error": "Erro ao buscar dados do dentista"}), 500
