import json
import os
from io import BytesIO
from typing import Any, Sequence

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from .. import db
from ..auth.models import User  # type: ignore
from ..core.models import Clinica
from ..pacientes.models import Paciente  # type: ignore
from ..utils_db import get_or_404
from .models import Documento

documentos_bp = Blueprint(
    "documentos",
    __name__,
    template_folder=".",
)


@documentos_bp.route("/")
def index():
    ultimos = Documento.query.order_by(Documento.data_emissao.desc()).limit(10).all()
    return render_template(
        "documentos/index.html",
        ultimos=ultimos,
    )


# Alias leve para compatibilidade (templates antigos)


@documentos_bp.route("/index")  # pragma: no cover - redundante
def index_alias():  # retorna mesmo conteúdo
    return index()


@documentos_bp.route("/novo", methods=["GET", "POST"])
def novo():
    if request.method == "POST":
        titulo = request.form.get("titulo_documento", "").strip()
        tipo_val = request.form.get("tipo_documento", "generico").strip()
        tipo = tipo_val or "generico"
        observacoes = request.form.get("observacoes", "").strip()
        if not titulo:
            flash("Título obrigatório", "danger")
        else:
            d = Documento()
            d.titulo_documento = titulo  # type: ignore[assignment]
            d.tipo_documento = tipo  # type: ignore[assignment]
            d.conteudo_json = "{}"  # type: ignore[assignment]
            d.observacoes = observacoes  # type: ignore[assignment]
            db.session.add(d)
            db.session.commit()
            flash("Documento criado", "success")
            return redirect(url_for("documentos.historico"))
    return render_template("documentos/form.html", doc=None)


@documentos_bp.route("/<int:doc_id>/editar", methods=["POST"])
def editar(doc_id: int):
    doc = get_or_404(Documento, doc_id)
    titulo = request.form.get("titulo_documento", "").strip()
    observacoes = request.form.get("observacoes", "").strip()
    if not titulo:
        flash("Título obrigatório", "danger")
    else:
        doc.titulo_documento = titulo  # type: ignore[assignment]
        doc.observacoes = observacoes  # type: ignore[assignment]
        db.session.commit()
        flash("Documento atualizado", "success")
    return redirect(url_for("documentos.historico"))


@documentos_bp.route("/<int:doc_id>/excluir", methods=["POST"])
def excluir(doc_id: int):
    doc = get_or_404(Documento, doc_id)
    db.session.delete(doc)
    db.session.commit()
    flash("Documento excluído", "info")
    return redirect(url_for("documentos.historico"))


@documentos_bp.route("/historico")
def historico():
    documentos = Documento.query.order_by(Documento.data_emissao.desc()).limit(50).all()
    return render_template(
        "documentos/historico.html",
        documentos=documentos,
    )


@documentos_bp.route("/api/<int:doc_id>")
def api_documento(doc_id: int):
    doc = get_or_404(Documento, doc_id)
    return jsonify(
        {
            "id": doc.id,
            "tipo": doc.tipo_documento,
            "titulo": doc.titulo_documento,
            "data": doc.data_emissao.isoformat(),
        }
    )


# ------------------ Migração simplificada geração dinâmica ------------------


def _load_tipos_config() -> dict:
    """Carrega JSON de tipos de documentos (cópia simplificada).

    Procura primeiro em app/documentos/tipos_documentos.json; se não existir,
    tenta fallback no legacy para evitar bloqueio inicial.
    """
    search_paths = [
        os.path.join(
            current_app.root_path,
            "documentos",
            "tipos_documentos.json",
        ),
        os.path.join(
            current_app.root_path,
            "..",
            "legacy",
            "config",
            "tipos_documentos.json",
        ),
    ]
    for path in search_paths:
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as fh:
                    return json.load(fh)
        except Exception:  # pragma: no cover - fallback silencioso
            continue
    return {"tipos_documentos": {}}


@documentos_bp.route("/gerar/<string:tipo>", methods=["GET", "POST"])
def gerar(tipo: str):
    cfg = _load_tipos_config()
    tipos = cfg.get("tipos_documentos", {})
    if tipo not in tipos:
        flash("Tipo não encontrado", "danger")
        return redirect(url_for("documentos.index"))
    tipo_cfg: dict[str, Any] = tipos[tipo]
    campos: Sequence[dict[str, Any]] = tipo_cfg.get("campos", [])  # type: ignore[assignment]
    if request.method == "POST":
        dados: dict[str, object] = {}
        valido = True
        for campo in campos:
            nome = campo["nome"]
            valor: Any
            if campo.get("tipo") == "checkbox":
                valor = request.form.getlist(nome)  # list[str]
            else:
                valor = request.form.get(nome, "").strip()  # str
            if campo.get("obrigatorio") and (not valor):
                valido = False
                flash(f"Campo '{campo['label']}' obrigatório", "danger")
            dados[nome] = valor
        if valido:
            # Campos adicionais (paciente/dentista, local, obs, assinatura)
            paciente_id = request.form.get("paciente_id")
            dentista_id = request.form.get("dentista_id")
            local_emissao = request.form.get("local_emissao", "").strip()
            observacoes = request.form.get("observacoes", "").strip()
            assinatura_tipo = request.form.get("assinatura_tipo", "dentista")
            if paciente_id:
                try:
                    dados["paciente_id"] = int(paciente_id)
                except ValueError:
                    pass
            if dentista_id and assinatura_tipo == "dentista":
                try:
                    dados["dentista_id"] = int(dentista_id)
                except ValueError:
                    pass
            dados["assinatura_tipo"] = assinatura_tipo
            documento = Documento()
            documento.paciente_id = dados.get("paciente_id")  # type: ignore[assignment]
            documento.dentista_id = dados.get("dentista_id")  # type: ignore[assignment]
            documento.tipo_documento = tipo  # type: ignore[assignment]
            titulo_cfg = tipo_cfg.get("titulo", tipo)
            if not isinstance(titulo_cfg, str):  # segurança contra tipos inesperados
                titulo_cfg = str(titulo_cfg)
            documento.titulo_documento = titulo_cfg  # type: ignore[assignment]
            documento.conteudo_json = json.dumps(  # type: ignore[assignment]
                dados,
                ensure_ascii=False,
            )
            documento.local_emissao = local_emissao  # type: ignore[assignment]
            documento.observacoes = observacoes  # type: ignore[assignment]
            db.session.add(documento)
            db.session.commit()
            flash("Documento gerado", "success")
            return redirect(url_for("documentos.gerar_html", doc_id=documento.id))
    # GET context: fornecer pacientes e dentistas ativos
    pacientes = Paciente.query.order_by(Paciente.nome).limit(200).all()
    dentistas = User.query.filter_by(cargo="dentista").order_by(User.nome_completo).all()
    clinica = Clinica.get_instance()
    local_padrao = ""
    if clinica.cidade and clinica.estado:
        local_padrao = f"{clinica.cidade} - {clinica.estado}"
    elif clinica.cidade:
        local_padrao = clinica.cidade
    return render_template(
        "documentos/gerar.html",
        tipo=tipo,
        config=tipo_cfg,
        campos=campos,
        pacientes=pacientes,
        dentistas=dentistas,
        local_padrao=local_padrao,
    )


@documentos_bp.route("/html/<int:doc_id>")
def gerar_html(doc_id: int):
    doc = get_or_404(Documento, doc_id)
    cfg = _load_tipos_config()
    tipo_cfg: dict[str, Any] | None = cfg.get("tipos_documentos", {}).get(
        doc.tipo_documento
    )  # type: ignore
    if not tipo_cfg:
        flash("Configuração não encontrada", "danger")
        return redirect(url_for("documentos.historico"))
    # Evita uso de Query.get (SQLAlchemy 2.x legacy warning)
    paciente = db.session.get(Paciente, doc.paciente_id) if doc.paciente_id else None
    dentista = db.session.get(User, doc.dentista_id) if doc.dentista_id else None
    clinica = Clinica.get_instance()
    dados_json = json.loads(doc.conteudo_json)
    template = tipo_cfg.get("template", "")
    # Monta contexto seguro
    from flask import render_template_string
    from markupsafe import escape

    ctx: dict[str, Any] = {
        "nome_paciente": paciente.nome if paciente else "",
        "cpf_paciente": getattr(paciente, "cpf", "") or "Não informado",
    }
    assinatura_tipo = dados_json.get("assinatura_tipo", "dentista")
    if assinatura_tipo == "dentista" and dentista:
        ctx["nome_dentista"] = dentista.nome_completo
        ctx["cro_dentista"] = dentista.cro or "Não informado"
    else:
        ctx["nome_dentista"] = clinica.nome or "Clínica"
        ctx["cro_dentista"] = f"CNPJ: {clinica.cnpj}" if clinica.cnpj else ""
    for k, v in dados_json.items():
        if isinstance(v, list):
            ctx[k] = ", ".join(v)
        else:
            ctx[k] = v
    safe_ctx = {k: escape(str(v)) for k, v in ctx.items()}
    try:
        conteudo_final = render_template_string(template, **safe_ctx)
    except Exception:  # pragma: no cover
        conteudo_final = template
    return render_template(
        "documentos/documento_html.html",
        documento=doc,
        paciente=paciente,
        dentista=dentista,
        clinica=clinica,
        conteudo_final=conteudo_final,
        dados_json=dados_json,
    )


@documentos_bp.route("/pdf/<int:doc_id>")
def gerar_pdf(doc_id: int):  # pragma: no cover - I/O pesado
    doc = get_or_404(Documento, doc_id)
    cfg = _load_tipos_config()
    tipo_cfg: dict[str, Any] | None = cfg.get("tipos_documentos", {}).get(
        doc.tipo_documento
    )  # type: ignore
    if not tipo_cfg:
        flash("Configuração não encontrada", "danger")
        return redirect(url_for("documentos.historico"))
    paciente = db.session.get(Paciente, doc.paciente_id) if doc.paciente_id else None
    dentista = db.session.get(User, doc.dentista_id) if doc.dentista_id else None
    clinica = Clinica.get_instance()
    dados_json = json.loads(doc.conteudo_json)
    template = tipo_cfg.get("template", "")
    # Monta contexto texto simples (parágrafo único)
    from flask import render_template_string
    from markupsafe import escape

    ctx: dict[str, Any] = {
        "nome_paciente": paciente.nome if paciente else "",
        "cpf_paciente": getattr(paciente, "cpf", "") or "Não informado",
    }
    assinatura_tipo = dados_json.get("assinatura_tipo", "dentista")
    if assinatura_tipo == "dentista" and dentista:
        ctx["nome_dentista"] = dentista.nome_completo
        ctx["cro_dentista"] = dentista.cro or "Não informado"
    else:
        ctx["nome_dentista"] = clinica.nome or "Clínica"
        ctx["cro_dentista"] = f"CNPJ: {clinica.cnpj}" if clinica.cnpj else ""
    for k, v in dados_json.items():
        if isinstance(v, list):
            ctx[k] = ", ".join(v)
        else:
            ctx[k] = v
    safe_ctx = {k: escape(str(v)) for k, v in ctx.items()}
    try:
        conteudo_final = render_template_string(template, **safe_ctx)
    except Exception:
        conteudo_final = template
    buffer = BytesIO()
    pdf = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Title"],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=20,
    )
    normal_style = ParagraphStyle(
        "DocBody",
        parent=styles["Normal"],
        fontSize=11,
        alignment=TA_JUSTIFY,
        leading=15,
    )
    story: list[Any] = []
    # Cabeçalho clínica
    header_parts = []
    if clinica.nome:
        header_parts.append(f"<b>{clinica.nome}</b>")
    if clinica.endereco:
        header_parts.append(clinica.endereco)
    if clinica.telefone:
        header_parts.append(f"Tel: {clinica.telefone}")
    if header_parts:
        story.append(Paragraph("<br/>".join(header_parts), normal_style))
        story.append(Spacer(1, 12))
    story.append(Paragraph(tipo_cfg.get("titulo", doc.titulo_documento), title_style))
    story.append(Spacer(1, 12))
    story.append(Paragraph(conteudo_final, normal_style))
    story.append(Spacer(1, 24))
    # Local/data
    if doc.local_emissao:
        story.append(
            Paragraph(
                f"{doc.local_emissao}, {doc.data_emissao.strftime('%d/%m/%Y')}",
                normal_style,
            )
        )
        story.append(Spacer(1, 24))
    # Assinatura
    story.append(Paragraph("_" * 50, normal_style))
    if assinatura_tipo == "dentista" and dentista:
        story.append(Paragraph(dentista.nome_completo, normal_style))
        if dentista.cro:
            story.append(Paragraph(f"CRO: {dentista.cro}", normal_style))
    else:
        story.append(Paragraph(clinica.nome or "Clínica", normal_style))
        if clinica.cnpj:
            story.append(Paragraph(f"CNPJ: {clinica.cnpj}", normal_style))
    # Observações
    if doc.observacoes:
        story.append(Spacer(1, 18))
        story.append(Paragraph("<b>Observações:</b>", normal_style))
        story.append(Paragraph(doc.observacoes, normal_style))
    pdf.build(story)
    buffer.seek(0)
    from flask import send_file

    filename = (
        f"{doc.titulo_documento.replace(' ', '_')}_"
        f"{(paciente.nome if paciente else 'doc').replace(' ', '_')}.pdf"
    )
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf",
    )
