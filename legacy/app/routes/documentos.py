import json
import os
from io import BytesIO

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask.typing import ResponseReturnValue
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.decorators import debug_login_optional
from app.extensions import db
from app.models.clinica import Clinica
from app.models.documento import Documento
from app.models.paciente import Paciente
from app.models.user import User

documentos_bp = Blueprint("documentos", __name__)


def carregar_tipos_documentos():
    """Carrega as configurações dos tipos de documentos do arquivo JSON."""
    try:
        config_path = os.path.join(current_app.root_path, "..", "config", "tipos_documentos.json")
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        current_app.logger.error(f"Erro ao carregar tipos de documentos: {e}")
        return {"tipos_documentos": {}}


@documentos_bp.route("/")
@debug_login_optional
def index() -> ResponseReturnValue:
    """Página principal mostrando tipos de documentos disponíveis."""
    tipos = carregar_tipos_documentos()
    return render_template(
        "documentos/tipos_documentos.html", tipos_documentos=tipos["tipos_documentos"]
    )


@documentos_bp.route("/gerar/<string:tipo_documento>", methods=["GET", "POST"])
@debug_login_optional
def gerar_documento(tipo_documento: str) -> ResponseReturnValue:
    """Gera um documento específico baseado no tipo."""
    tipos = carregar_tipos_documentos()

    if tipo_documento not in tipos["tipos_documentos"]:
        flash("Tipo de documento não encontrado.", "error")
        return redirect(url_for("documentos.index"))

    config_documento = tipos["tipos_documentos"][tipo_documento]

    if request.method == "GET":
        # Buscar todos os pacientes
        pacientes = Paciente.query.order_by(Paciente.nome).all()

        # Buscar todos os dentistas ativos
        from app.extensions import db as _db

        dentistas = (
            User.query.filter_by(cargo="dentista")
            .filter(User.is_active_db == _db.true())
            .order_by(User.nome_completo)
            .all()
        )

        # Verificar se o usuário logado é dentista para pré-seleção
        from flask_login import current_user

        dentista_selecionado_id = None
        if current_user.cargo == "dentista":
            dentista_selecionado_id = current_user.id

        # Buscar dados da clínica
        try:
            clinica = Clinica.get_instance()
            local_padrao = ""
            if clinica.cidade and clinica.estado:
                local_padrao = f"{clinica.cidade} - {clinica.estado}"
            elif clinica.cidade:
                local_padrao = clinica.cidade
        except Exception:
            local_padrao = ""

        return render_template(
            "documentos/formulario_documento.html",
            pacientes=pacientes,
            dentistas=dentistas,
            dentista_selecionado_id=dentista_selecionado_id,
            local_padrao=local_padrao,
            tipo_documento=tipo_documento,
            config_documento=config_documento,
        )

    elif request.method == "POST":
        try:
            # Coletar dados do formulário
            paciente_id = request.form.get("paciente_id")
            dentista_id = request.form.get("dentista_id")
            assinatura_tipo = request.form.get("assinatura_tipo", "dentista")
            local_emissao = request.form.get("local_emissao", "")
            observacoes = request.form.get("observacoes", "")

            # Validar dados obrigatórios
            if not paciente_id:
                flash("Paciente é obrigatório.", "error")
                return redirect(request.url)

            if assinatura_tipo == "dentista" and not dentista_id:
                flash(
                    "Dentista é obrigatório quando tipo de assinatura é 'dentista'.",
                    "error",
                )
                return redirect(request.url)

            # Coletar dados específicos do documento
            dados_documento = {}
            for campo in config_documento["campos"]:
                nome_campo = campo["nome"]
                valor = request.form.get(nome_campo)

                if campo["tipo"] == "checkbox":
                    # Para checkboxes, coletar múltiplos valores
                    valor = request.form.getlist(nome_campo)

                if campo["obrigatorio"] and not valor:
                    flash(f"Campo '{campo['label']}' é obrigatório.", "error")
                    return redirect(request.url)

                dados_documento[nome_campo] = valor

            # Adicionar tipo de assinatura aos dados
            dados_documento["assinatura_tipo"] = assinatura_tipo

            # Salvar no banco de dados
            documento = Documento(
                paciente_id=paciente_id,
                dentista_id=dentista_id if assinatura_tipo == "dentista" else None,
                tipo_documento=tipo_documento,
                titulo_documento=config_documento["titulo"],
                conteudo_json=json.dumps(dados_documento, ensure_ascii=False),
                local_emissao=local_emissao,
                observacoes=observacoes,
            )

            db.session.add(documento)
            db.session.commit()

            flash("Documento gerado com sucesso!", "success")

            # Redirecionar para gerar PDF
            return redirect(url_for("documentos.gerar_pdf", documento_id=documento.id))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao gerar documento: {e}")
            flash("Erro interno. Tente novamente.", "error")
        return redirect(request.url)

    # Fallback: ensure a ResponseReturnValue on all code paths
    return redirect(url_for("documentos.index"))


@documentos_bp.route("/pdf/<int:documento_id>")
@debug_login_optional
def gerar_pdf(documento_id) -> ResponseReturnValue:
    """Gera o PDF do documento."""
    documento = Documento.query.get_or_404(documento_id)

    # Carregar configuração do tipo de documento
    tipos = carregar_tipos_documentos()
    config_documento = tipos["tipos_documentos"].get(documento.tipo_documento)

    if not config_documento:
        flash("Configuração do documento não encontrada.", "error")
        return redirect(url_for("documentos.index"))

    # Buscar dados do paciente e dentista
    paciente = Paciente.query.get(documento.paciente_id)
    dentista = User.query.get(documento.dentista_id)
    clinica = Clinica.get_instance()

    if not paciente or not dentista:
        flash("Dados do paciente ou dentista não encontrados.", "error")
        return redirect(url_for("documentos.index"))

    try:
        # Criar PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)

        # Estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Title"],
            fontSize=16,
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
        )

        normal_style = ParagraphStyle(
            "CustomNormal",
            parent=styles["Normal"],
            fontSize=12,
            spaceAfter=12,
            alignment=TA_JUSTIFY,
            fontName="Helvetica",
        )

        # Construir conteúdo
        elementos = []

        # Cabeçalho da clínica
        if clinica:
            clinic_info = []
            if clinica.nome:
                clinic_info.append(f"<b>{clinica.nome}</b>")
            if clinica.endereco:
                clinic_info.append(clinica.endereco)
            if clinica.telefone:
                clinic_info.append(f"Tel: {clinica.telefone}")

            if clinic_info:
                header_text = "<br/>".join(clinic_info)
                elementos.append(Paragraph(header_text, title_style))
                elementos.append(Spacer(1, 20))

        # Título do documento
        elementos.append(Paragraph(config_documento["titulo"], title_style))
        elementos.append(Spacer(1, 20))

        # Conteúdo do documento
        dados_json = json.loads(documento.conteudo_json)
        template = config_documento["template"]

        # Preparar dados para o template
        dados_template = {
            "nome_paciente": paciente.nome,
            "cpf_paciente": paciente.cpf or "Não informado",
        }

        # Dados da assinatura baseados no tipo
        assinatura_tipo = dados_json.get("assinatura_tipo", "dentista")
        if assinatura_tipo == "dentista" and dentista:
            dados_template["nome_dentista"] = dentista.nome_completo
            dados_template["cro_dentista"] = dentista.cro or "Não informado"
        else:
            # Usar dados da clínica
            dados_template["nome_dentista"] = (
                clinica.nome if clinica and clinica.nome else "Clínica Odontológica"
            )
            dados_template["cro_dentista"] = (
                f"CNPJ: {clinica.cnpj}" if clinica and clinica.cnpj else "Dados da clínica"
            )

        # Adicionar dados específicos do documento
        for key, value in dados_json.items():
            if isinstance(value, list):
                # Para checkboxes, juntar com vírgulas
                dados_template[key] = ", ".join(value)
            else:
                dados_template[key] = value

        # Adicionar textos condicionais
        for campo in config_documento["campos"]:
            nome_campo = campo["nome"]
            if nome_campo in dados_json and dados_json[nome_campo]:
                if campo["tipo"] == "textarea":
                    dados_template[f"{nome_campo}_texto"] = f" {dados_json[nome_campo]}"
                else:
                    dados_template[f"{nome_campo}_texto"] = f" {dados_json[nome_campo]}"
            else:
                dados_template[f"{nome_campo}_texto"] = ""

        # Preencher template usando Jinja2
        from flask import render_template_string
        from markupsafe import escape

        # Sanitizar todos os dados do template
        safe_context = {k: escape(str(v)) for k, v in dados_template.items()}
        try:
            conteudo_final = render_template_string(template, **safe_context)
        except Exception as e:
            current_app.logger.warning(f"Erro ao renderizar template Jinja2: {e}")
            conteudo_final = template

        elementos.append(Paragraph(conteudo_final, normal_style))
        elementos.append(Spacer(1, 30))

        # Local e data
        if documento.local_emissao:
            local_data = (
                f"{documento.local_emissao}, {documento.data_emissao.strftime('%d de %B de %Y')}"
            )
        else:
            local_data = documento.data_emissao.strftime("%d de %B de %Y")

        elementos.append(Paragraph(local_data, normal_style))
        elementos.append(Spacer(1, 40))

        # Assinatura baseada no tipo
        assinatura_style = ParagraphStyle(
            "Signature",
            parent=styles["Normal"],
            fontSize=12,
            alignment=TA_CENTER,
            fontName="Helvetica",
        )

        elementos.append(Paragraph("_" * 50, assinatura_style))

        if assinatura_tipo == "dentista" and dentista:
            elementos.append(Paragraph(f"Dr(a). {dentista.nome_completo}", assinatura_style))
            if dentista.cro:
                elementos.append(Paragraph(f"CRO: {dentista.cro}", assinatura_style))
        else:
            # Assinatura da clínica
            if clinica and clinica.nome:
                elementos.append(Paragraph(clinica.nome, assinatura_style))
            else:
                elementos.append(Paragraph("Clínica Odontológica", assinatura_style))

            if clinica and clinica.cnpj:
                elementos.append(Paragraph(f"CNPJ: {clinica.cnpj}", assinatura_style))

        # Observações
        if documento.observacoes:
            elementos.append(Spacer(1, 30))
            elementos.append(Paragraph("<b>Observações:</b>", normal_style))
            elementos.append(Paragraph(documento.observacoes, normal_style))

        # Gerar PDF
        doc.build(elementos)
        buffer.seek(0)

        # Nome do arquivo
        nome_arquivo = (
            f"{config_documento['titulo'].replace(' ', '_')}_"
            f"{paciente.nome.replace(' ', '_')}_"
            f"{documento.data_emissao.strftime('%Y%m%d')}.pdf"
        )

        return send_file(
            buffer,
            as_attachment=True,
            download_name=nome_arquivo,
            mimetype="application/pdf",
        )

    except Exception as e:
        current_app.logger.error(f"Erro ao gerar PDF: {e}")
        flash("Erro ao gerar PDF. Tente novamente.", "error")
        return redirect(url_for("documentos.index"))


@documentos_bp.route("/historico")
@debug_login_optional
def historico() -> ResponseReturnValue:
    """Mostra o histórico de documentos gerados."""
    documentos = Documento.query.order_by(Documento.data_emissao.desc()).limit(100).all()
    return render_template("documentos/historico_documentos.html", documentos=documentos)


@documentos_bp.route("/html/<int:documento_id>")
@debug_login_optional
def gerar_html(documento_id) -> ResponseReturnValue:
    """Gera o HTML do documento para visualização/impressão."""
    documento = Documento.query.get_or_404(documento_id)

    # Carregar configuração do tipo de documento
    tipos = carregar_tipos_documentos()
    config_documento = tipos["tipos_documentos"].get(documento.tipo_documento)

    if not config_documento:
        flash("Configuração do documento não encontrada.", "error")
        return redirect(url_for("documentos.index"))

    # Buscar dados do paciente, dentista e clínica
    paciente = Paciente.query.get(documento.paciente_id)
    dentista = None
    if documento.dentista_id:
        dentista = User.query.get(documento.dentista_id)
    clinica = Clinica.get_instance()

    if not paciente:
        flash("Dados do paciente não encontrados.", "error")
        return redirect(url_for("documentos.index"))

    try:
        # Processar dados do documento
        dados_json = json.loads(documento.conteudo_json)
        template = config_documento["template"]

        # Preparar dados para o template
        dados_template = {
            "nome_paciente": paciente.nome,
            "cpf_paciente": paciente.cpf or "Não informado",
        }

        # Dados da assinatura baseados no tipo
        assinatura_tipo = dados_json.get("assinatura_tipo", "dentista")
        if assinatura_tipo == "dentista" and dentista:
            dados_template["nome_dentista"] = dentista.nome_completo
            dados_template["cro_dentista"] = dentista.cro or "Não informado"
        else:
            # Usar dados da clínica
            dados_template["nome_dentista"] = (
                clinica.nome if clinica and clinica.nome else "Clínica Odontológica"
            )
            dados_template["cro_dentista"] = (
                f"CNPJ: {clinica.cnpj}" if clinica and clinica.cnpj else "Dados da clínica"
            )

        # Adicionar dados específicos do documento
        for key, value in dados_json.items():
            if isinstance(value, list):
                # Para checkboxes, juntar com vírgulas
                dados_template[key] = ", ".join(value)
            else:
                dados_template[key] = value

        # Adicionar textos condicionais
        for campo in config_documento["campos"]:
            nome_campo = campo["nome"]
            if nome_campo in dados_json and dados_json[nome_campo]:
                if campo["tipo"] == "textarea":
                    dados_template[f"{nome_campo}_texto"] = f" {dados_json[nome_campo]}"
                else:
                    dados_template[f"{nome_campo}_texto"] = f" {dados_json[nome_campo]}"
            else:
                dados_template[f"{nome_campo}_texto"] = ""

        # Preencher template usando Jinja2
        from flask import render_template_string
        from markupsafe import escape

        # Sanitizar todos os dados do template
        safe_context = {k: escape(str(v)) for k, v in dados_template.items()}
        try:
            conteudo_final = render_template_string(template, **safe_context)
        except Exception as e:
            current_app.logger.warning(f"Erro ao renderizar template Jinja2: {e}")
            conteudo_final = template

        # Renderizar template HTML
        return render_template(
            "documentos/documento_html.html",
            documento=documento,
            paciente=paciente,
            dentista=dentista,
            clinica=clinica,
            config_documento=config_documento,
            conteudo_final=conteudo_final,
            dados_json=dados_json,
            assinatura_tipo=assinatura_tipo,
        )

    except Exception as e:
        current_app.logger.error(f"Erro ao gerar HTML: {e}")
        flash("Erro ao gerar documento HTML. Tente novamente.", "error")
        return redirect(url_for("documentos.index"))
