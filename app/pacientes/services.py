"""Serviços de domínio para o módulo pacientes.

Mantém regras de negócio fora das rotas para facilitar testes e futura
expansão (ex: logging, autorização detalhada, validações adicionais).
"""

from __future__ import annotations

import json
from typing import Iterable, Sequence

from .. import db
from .models import Financeiro, Paciente, PlanoTratamento, Procedimento


def add_procedimento(
    plano: PlanoTratamento,
    *,
    descricao: str,
    valor: float | int | None = 0,
    dente: str | None = None,
    tratamento_id: int | None = None,
    dentes: Sequence[str] | None = None,
    quadrantes: Sequence[str] | None = None,
    boca_completa: bool | None = None,
    status: str = "Pendente",
    data_prevista=None,
    data_realizado=None,
    observacoes: str | None = None,
) -> Procedimento:
    """Adiciona um procedimento e atualiza orçamento do plano.

    Valor negativo é rejeitado via ValueError.
    """
    if valor is None:
        valor = 0
    if valor < 0:  # simples regra defensiva
        raise ValueError("valor não pode ser negativo")
    proc = Procedimento()
    proc.plano_id = plano.id
    proc.descricao = descricao
    proc.valor = float(valor)
    proc.dente = dente
    proc.tratamento_id = tratamento_id
    if dentes:
        proc.dentes_selecionados = json.dumps(list(dentes))
    if quadrantes:
        proc.quadrantes = ",".join(quadrantes)
    if boca_completa is not None:
        proc.boca_completa = bool(boca_completa)
    proc.status = status
    proc.data_prevista = data_prevista
    proc.data_realizado = data_realizado
    proc.observacoes = observacoes
    # orcamento_total é recalculado por eventos (after_insert) -> evitar drift
    db.session.add(proc)
    db.session.flush()  # garante id disponível se necessário
    return proc


def remove_procedimento(proc: Procedimento) -> None:
    """Remove procedimento ajustando orçamento (sem deixar negativo)."""
    # Relação backref 'plano' (ver models) => acessar via proc.plano.
    # Pylance pode não inferir até runtime.
    # Recalculo delegado a evento after_delete
    db.session.delete(proc)


def recompute_orcamento_total(plano: PlanoTratamento) -> float:
    """Recalcula orçamento a partir dos procedimentos persistidos."""
    total = 0.0
    # relacionamento lazy='dynamic' retorna query -> usar .all()
    for p in plano.procedimentos.all():  # type: ignore[attr-defined]
        total += float(p.valor or 0)
    plano.orcamento_total = total
    return total


def calcular_totais_financeiro(
    lancamentos: Iterable[Financeiro],
) -> tuple[float, float, float]:
    """Retorna (total_credito, total_debito, saldo) com política refinada.

    Política anterior: saldo = soma de créditos pagos.
    Nova política: saldo = (créditos pagos) - (débitos não cancelados).
    Mantemos total_credito e total_debito como somas brutas
    (excluindo cancelados)
    para exibição. Saldo nunca abaixo de zero? Decisão: permitir negativo para
    indicar dívida pendente.
    """
    total_credito = 0.0
    total_debito = 0.0
    creditos_pagos = 0.0
    debitos_considerados = 0.0
    for lanc in lancamentos:
        if lanc.status == "Cancelado":
            continue
        valor = float(lanc.valor or 0)
        if lanc.tipo == "Crédito":
            total_credito += valor
            if lanc.status == "Pago":
                creditos_pagos += valor
        elif lanc.tipo == "Débito":
            total_debito += valor
            debitos_considerados += valor
    saldo = creditos_pagos - debitos_considerados
    return total_credito, total_debito, saldo


def normalizar_cpf(raw: str | None, *, validar: bool = True) -> str | None:
    """Normaliza CPF para XXX.XXX.XXX-YY e opcionalmente valida.

    Regras de validação:
    - 11 dígitos
    - Não pode ter todos dígitos iguais
    - Dígitos verificadores conforme algoritmo oficial
    Retorna None se entrada vazia. Se inválido e validar=True,
    levanta ValueError.
    """
    if not raw:
        return None
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) != 11:
        if validar:
            raise ValueError("CPF deve conter 11 dígitos")
        return digits
    if validar:
        if digits == digits[0] * 11:
            raise ValueError("CPF inválido")
        # cálculo DV1
        soma1 = sum(int(digits[i]) * (10 - i) for i in range(9))
        dv1 = (soma1 * 10) % 11
        if dv1 == 10:
            dv1 = 0
        if dv1 != int(digits[9]):
            raise ValueError("CPF inválido")
        soma2 = sum(int(digits[i]) * (11 - i) for i in range(10))
        dv2 = (soma2 * 10) % 11
        if dv2 == 10:
            dv2 = 0
        if dv2 != int(digits[10]):
            raise ValueError("CPF inválido")
    return f"{digits[0:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:11]}"


def cpf_existe(cpf_normalizado: str) -> bool:
    """Retorna True se CPF já existir (case insensitive)."""
    return Paciente.query.filter_by(cpf=cpf_normalizado).first() is not None
