# OdontoClin — Agent Brief (Guia Rápido para Agentes Autônomos)

Este documento é um meta‑prompt conciso para orientar agentes IA autônomos a
implementar funcionalidades futuras no projeto OdontoClin. Foque em
modularização, organização simples em uma pasta principal, HTMX‑first e código
mínimo/eficiente. Utilize rigorosamente as diretrizes abaixo.

## 1) Propósito e Escopo
- Público‑alvo: agentes autônomos (e humanos secundariamente).
- Objetivo: produzir mudanças pequenas, seguras e testadas, aderentes ao padrão
  arquitetural e de estilo do repositório.
- Escopo: back‑end Flask + SQLAlchemy, templates Jinja, interações com HTMX.
  Não priorizar CSS/estilo visual.

## 2) Arquitetura — Norte
- Flask App Factory + Blueprints por domínio.
- Organização em pasta única: todo o código de aplicação em `app/` com
  subpacotes por domínio (ex.: `app/pacientes`, `app/agenda`).
- Templates co‑localizados dentro do pacote do blueprint (ex.:
  `app/calculadora_anestesico/*.html`), seguindo o padrão de manter HTML junto
  ao módulo Python do domínio. Fragmentos reutilizáveis com prefixo `_` (ex.:
  `_procedimento_row.html`).
- Bancos/binds: `calendario`, `pacientes`, `users`, etc (SQLite sob `instance/`).
- HTMX‑first: respostas parciais (sem layout base) e progressivo; JS mínimo.

## 3) Diretrizes Obrigatórias
- Código mínimo e eficiente; evitar sobre‑engenharia e dependências pesadas.
- Segurança: manter CSRF, autenticação e verificação de papéis/roles existentes.
- Templates sem efeitos colaterais (somente renderização). Lógica de negócio no
  Python (rotas/serviços), não em Jinja.
- Estilo: PEP8 com limite de linha ≤100 colunas; sem tabs.
- Idioma de interface: pt‑BR; datas dd/mm/aaaa quando aplicável.

## 4) Protocolo Operacional para Agentes (Meta‑Prompt)
- Pesquisar antes de codar: consultar documentação oficial e referências
  reconhecidas (Flask, SQLAlchemy, HTMX, padrões de segurança). Cite as
  fontes (URLs) no PR/commit ou no topo do arquivo alterado.
- Planejar → Agir → Observar → Refletir: aplique um ciclo curto no estilo
  ReAct/Reflexion (raciocinar brevemente, executar mudanças pequenas, rodar
  testes, refletir e iterar até 3 tentativas focadas).
- Escopo pequeno e reversível: preferir patches de baixo risco que possam ser
  revertidos facilmente; não misturar múltiplos assuntos numa mesma alteração.
- Basear‑se no repositório: alinhar-se aos padrões e convenções já existentes.
- Relatar bloqueios objetivamente: se faltar contexto, descreva exatamente o que
  está faltando e proponha alternativas viáveis.

## 5) HTMX — Padrões
- Endpoints para HTMX devem retornar somente fragmentos HTML (sem `base.html`).
- Nome de parciais: prefixo `_` e nomes claros por fragmento (ex.:
  `pacientes/_financeiro_row.html`, `pacientes/_financeiro_totais.html`).
- Atributos recomendados: `hx-post/hx-get`, `hx-target`, `hx-swap="outerHTML"`.
- Erros de validação: responder 422 com um fragmento que substitua apenas a área
  do formulário/fragmento alvo.

## 6) Templates — Padrões
- Localização: dentro de `app/<módulo>/`, co‑localizado com o código do
  blueprint (como em `app/calculadora_anestesico/`).
- Somente leitura: nenhuma consulta ou mutação de banco dentro de Jinja.
- Parciais no mesmo diretório com prefixo `_` e nomes claros; usar macros quando
  reduzir repetição.

## 7) Dados e Integridade
- Integridade: usar Enums/Check constraints quando fizer sentido.

## 8) Execução Rápida
- Ambiente (Windows PowerShell):
```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```
- Rodar servidor (desenvolvimento):
```powershell
python run.py
```
- Testes:
```powershell
pytest -q --maxfail=1
```

## 9) Do / Don’t
- Faça
  - Modularizar por blueprint, rotas finas e serviços/helpers quando necessário.
  - Usar fragmentos HTMX e atualizar somente o necessário na UI.
  - Escrever testes mínimos para novo comportamento; manter suíte verde.
  - Citar fontes quando incorporar decisões/técnicas de terceiros.
- Não faça
  - Adicionar CSS/JS pesados ou frameworks de UI (sem solicitação explícita).
  - Inserir lógica de negócio ou acesso a DB em templates.
  - Expor endpoints sem autenticação/autorização adequada.
  - Grandes refatores misturados a features (divida em passos menores).

## 10) Atualização de Documentos
- Este arquivo (AGENT_BRIEF.md) é a referência ativa para agentes.
- O arquivo `AGENT_CONTINUATION_GUIDE.md` permanece como histórico e contexto de
  migração. Atualize este brief quando diretrizes mudarem.

## 11) Legacy — Recriar sem reaproveitar código
- A pasta `legacy/` contém uma versão anterior do aplicativo, com problemas de
  organização e de programação. Use‑a apenas como referência de intenção e
  comportamento.
- Quando o usuário solicitar recuperar/recriar uma funcionalidade antiga:
  - Estude o fluxo no `legacy/` (rotas, templates, modelos) para entender a
    intenção, entradas/saídas e regras de negócio.
  - Não copie/cole código do `legacy/`. Reescreva a lógica de maneira limpa,
    modular e alinhada a este brief (HTMX‑first, templates co‑localizados,
    rotas finas, sem efeitos colaterais em templates).
  - Mantenha nomes/URLs compatíveis quando fizer sentido, mas priorize coerência
    com o padrão atual do projeto.
  - Adicione testes mínimos para o comportamento recriado.
  - Documente no PR/commit quais partes do `legacy/` inspiraram a nova
    implementação (arquivos/linhas principais) — sem copiar código.

---
Repita mentalmente ao finalizar cada tarefa (recency bias):
- Código mínimo, HTMX‑first, sem CSS; PEP8 ≤100; segurança preservada;
  testes verdes; fontes citadas.
