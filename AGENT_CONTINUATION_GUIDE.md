# Este arquivo é legacy, já foi feita a continuação/migração

# OdontoClin Agent Continuation Guide

Nota rápida (2025-09-16): Para diretrizes concisas voltadas a agentes IA, consulte o novo `AGENT_BRIEF.md`. Este arquivo mantém o histórico detalhado de migração e contexto legado.

Purpose: This document is a durable, self‑contained briefing so an autonomous AI agent (or human developer) can resume work without prior chat history. Keep it updated as milestones are reached.

---
## 1. High‑Level Intent
Build a modular dental clinic management system (OdontoClin) using Flask with an application factory + blueprint architecture, multi-database binds (agenda/calendario & pacientes), and progressive enhancement (future HTMX) to manage:
- Scheduling (agenda, feriados) with external holiday API token persistence.
- Patient records (cadastro, ficha, anamnese, planos de tratamento, procedimentos, histórico clínico, financeiro).
- Robust domain validations and extensible financial tracking.

Core Non-Functional Goals:
- Clean separation of domains via blueprints and DB binds.
- Maintainable, PEP8-aligned code (spaces, <=79 char lines, no tab chars).
- Incremental test coverage expansion (pytest + factory-boy + Faker).
- Future-friendly for realtime/partial updates (HTMX) and richer validation.

---
## 2. Architecture Overview
Flask App Factory (`app/__init__.py`):
- Initializes Flask, SQLAlchemy (`db`), CSRFProtect.
- Registers blueprints: `core_bp`, `agenda_bp` (url_prefix=/agenda),
  `pacientes_bp` (url_prefix=/pacientes), plus `auth`, `catalogo`, `receitas`,
  `atestados`, `documentos`, `main`, `cro`, `ai_assistant`, `reports`, `users`.
- Migrations: optional Alembic upgrade on startup controlled by
  `AUTO_ALEMBIC_UPGRADE` (default False). Tests use `db.create_all()`.

Database Strategy:
- Separate SQLite files per bind (no merge). All DBs live under `instance/`.
- Default DB: `instance/odonto.db` (core/minimal).
- Binds:
  - `calendario` -> `instance/calendario.db`
  - `pacientes`  -> `instance/pacientes.db`
  - `users`      -> `instance/users.db`
  - `tratamentos`-> `instance/tratamentos.db`
  - `receitas`   -> `instance/receitas.db`
  Alembic is configured to run per-bind using an extra option
  `-x target_bind=<nome>` so each DB is migrated independently.

Blueprints:
- core: General/site root scaffolding (not central to current iteration).
- agenda: Calendar events, holidays, Invertexto API token persistence (token stored via `AppSetting` model in calendario bind – model not shown in this guide but functionally present earlier).
- pacientes: Full clinical & financial records and workflows.

---
## 3. Domain Model (Pacientes Bind)
File: `app/pacientes/models.py`

Entities:
1. Paciente: Demographics + relationships; helper `idade()`.
2. Ficha: Administrative/insurance data.
3. Anamnese: Medical/dental background with `ultima_atualizacao` timestamp.
4. PlanoTratamento: Treatment plan; accumulative `orcamento_total` via procedimentos.
5. Procedimento: Individual planned or completed procedure (valor, status, dates, tooth/dente, observacoes).
6. Historico: Narrative clinical history entries separate from structured plan execution.
7. Financeiro: Financial ledger entries (Crédito / Débito), optional link to plan (`plano_id`), payment metadata, status.

Design Notes:
- All models use SQLAlchemy default constructors (no custom __init__) to avoid analyzer signature warnings.
- `orcamento_total` kept consistent via SQLAlchemy events on `Procedimento` insert/update/delete and realizar; a manual recompute endpoint remains for maintenance.
- Financeiro currently not auto-synchronized with Procedimento completion; linkage considered future work.

---
## 4. Forms Layer
File: `app/pacientes/forms.py` (not reproduced here, but includes WTForms classes: PacienteForm, FichaForm, AnamneseForm, PlanoForm, ProcedimentoForm, HistoricoForm, FinanceiroForm.)
Strategy: Instantiate model objects first, then assign attributes explicitly or use `form.populate_obj()` for updates (except where manual transformations like date parsing are required).

---
## 5. Routes (Pacientes)
File: `app/pacientes/routes.py`

Implemented Endpoints:
- Listing / Search: `listar`, `/search` (AJAX-style name suggestions, min length 2).
- CRUD Paciente: `novo`, `visualizar`, `editar`, `excluir`.
- Ficha: Create-on-demand + update.
- Anamnese: Create-on-demand + timestamp update.
- Planos: List, create (`novo_plano`), view (`visualizar_plano`).
- Procedimentos: Add (`novo_procedimento`), remove (`excluir_procedimento`) with budget aggregation adjustment.
- Histórico: List + add (`novo_historico`).
- Financeiro: Ledger view + add (`novo_financeiro`) with credit/debit totals and saldo policy (créditos pagos - débitos não cancelados).
- Birthdays: `/aniversarios` per current month.
- API Data: `/api/<id>/dados` returns JSON snapshot.

Style Compliance:
- Tabs removed entirely.
- Lines wrapped to <=79 chars (post-refactor cleanup complete as of this guide creation).

---
## 6. External Integration (Agenda Context)
- Holiday API (Invertexto) token stored in database (calendario bind) via an `AppSetting` model (not in this excerpt). Token retrieved and cached in agenda routes (already implemented previously). Not currently interacted with by pacientes blueprint.

---
## 7. Current State Summary (Milestones Achieved)
Architecture & Infrastructure:
- [x] Application factory & blueprint modularization.
- [x] Multi-bind SQLAlchemy configuration (`calendario`, `pacientes`,
  `users`, `tratamentos`, `receitas`).
- [x] Alembic configured per-bind (no consolidation). Auto-upgrade disabled
  by default; use CLI with `-x target_bind=<nome>`.
- [x] CSRF protection enabled (tests disable via config).
- [x] Central auth blueprint with session-based user loading.

Agenda Module:
- [x] Migrated calendar event CRUD.
- [x] Holiday retrieval with token persistence & caching.

Pacientes Module (Clinical):
- [x] Paciente CRUD + search + birthdays.
- [x] Soft delete implemented (`deleted_at`) with removal from list & guard on all routes.
- [x] Restore endpoint (`/pacientes/<id>/restaurar`) + UI badge for deleted patients (admin-only restore button).
- [x] Ficha & Anamnese singletons per patient (create on first access) with timestamp update for Anamnese.
- [x] Treatment plans with procedures and dynamic budget accumulation; realizar endpoint marks procedure as realizado & sets date.
- [x] Recompute endpoint for plano orçamento total.
- [x] Clinical history entries (add + list) protected by roles.

Pacientes Module (Financial):
- [x] Ledger with totals (crédito, débito) and refined saldo policy: saldo = créditos pagos - débitos não cancelados.
- [x] Totals & saldo precomputed server-side (removed duplicated template calculation).
- [x] Monetary fields migrated to Decimal (Numeric(12,2)).
- [x] Financeiro ↔ Procedimento optional linkage (procedimento_id) with UI support.
- [x] Enum integrity via check constraints for tipo/status.
- [x] Automatic orçamento recompute via SQLAlchemy events (insert/update/delete/realizar). Recompute endpoint retained for maintenance.
 - [x] Plano view inclui resumo financeiro agregado (créditos, débitos, saldo, créditos pagos) e link para lançamentos do paciente.
 
Reporting:
- [x] Pacientes dashboard simples em `/pacientes/dashboard` com métricas: pacientes ativos, procedimentos pendentes/realizados e saldo global; cobertura de teste adicionada.

Authorization & Security:
- [x] Role-based decorator `require_roles` expanded with role groups (clinico, financeiro_all) and new roles (atendimento, financeiro).
- [x] Applied across catalogo & pacientes routes (create/edit/delete/finance/procedures/history) with updated tests.
- [x] Session cookie security flags (HttpOnly, SameSite=Lax; Secure configurable) added in app factory.
- [x] Password policy, account lockout after failed attempts, session inactivity timeout, optional password expiry (config via config.py). Tests disable policy by default and enable when asserting rejections.

Code Quality:
- [x] Removed custom model constructors.
- [x] Eliminated tabs in all modified files; wrapped long lines to <=79 chars.
- [x] Simplified financeiro retrieval logic in `visualizar` (removed brittle hasattr check).

Documentation:
- [x] Continuation guide updated with role auth, soft delete, saldo policy,
  tests, shared flash partial, and Alembic per-bind usage.

Testing (Current Coverage Snapshot):
- [x] Comprehensive tests added/updated for: planos/procedimentos (add/realizar/recompute auto), financeiro totals & saldo policy, CPF normalization + checksum, soft delete & restore, expanded role restrictions (catalogo, pacientes, financeiro, procedimentos). Total tests: 78 passing.
- [x] Financeiro negative role tests ensure unauthorized roles cannot create lançamentos; permitted roles include admin/gerente/financeiro.
- [x] Soft delete tests confirm list exclusion, warning redirect, and restoration.
- [x] Shared helpers reduce duplication: `tests/utils_auth.py::login_as` and `tests/utils_factory.py` with small entity factories.

---
## 8. Outstanding Work / Backlog
Priority Buckets (High → Medium → Low):

High (Post-Completion Adjusted):
1. CPF checksum validation (normalization + checksum + tests) [DONE].
2. Pagination for financeiro & histórico (scalability) [DONE].
3. Display aggregated financeiro per plano (resumo na view) [DONE].
4. Strengthen auth security (password policy, account lockout, session timeout) [DONE].
5. Add Alembic migrations for any remaining legacy tables. Consolidation is
  optional; keep per-bind separation. [ONGOING]

Medium:
6. HTMX enhancement: expand financeiro fragments (rows + live totals) — base
  fragments exist.
7. Form macros (templating DRY) — shared flash partial DONE; extract common
  field macros next.
8. Audit cascade vs. soft delete for related models (currently only Paciente soft-deleted).
9. Reporting dashboard (basic KPIs) now that data integrity improved.

Low / Future:
10. Audit trail (who changed what) for procedimentos/financeiro.
11. Advanced revenue & performance dashboards.
12. i18n / l10n abstraction (Flask-Babel) if multi-language required.
13. Document generation (receitas/atestados) modernization & PDF pipeline.

---
## 9. Proposed Next Implementation Steps (Actionable Sequence)
1. Migrations: Per-bind Alembic in place; generate revisions as schema evolves.
  Convert any remaining manual scripts into revisions (per bind).
2. Monetary Precision: Transition Financeiro.valor & Procedimento.valor to Decimal (SQLAlchemy Numeric) with migration & adapter helpers.
3. CPF Validation: Implement checksum algorithm + standardized formatting at service layer (tests for valid/invalid edge cases).
4. Financeiro Linkage: Add optional FK from Financeiro to Procedimento (nullable) + UI selection when launched from procedure context.
5. HTMX Financeiro: Add `_financeiro_row.html` & `_financeiro_totais.html`, implement htmx endpoints for create + totals refresh.
6. Template DRY: Macros for form fields; refactor existing forms. (Flash
  messages partial is shared and included in base.)
7. Authorization Expansion: Define and implement additional roles (atendimento, financeiro) & adjust `require_roles` decorator logic (list membership) + tests.
8. Recompute Automation: Hook recompute on procedure add/remove & realizar to keep orcamento_total accurate without manual endpoint (retain endpoint as maintenance tool).
9. Reporting Seed: Add simple `/pacientes/dashboard` aggregating counts (procedimentos pendentes, realizados, saldo global) with tests. [DONE]
10. Audit Hooks: Scaffold event log table for create/update/delete actions (future expansion).

---
## 10. Testing Strategy Details
Minimal Factory Plan:
- `PacienteFactory`: random nome, optional data_nascimento.
- `PlanoTratamentoFactory`: associates Paciente.
- `ProcedimentoFactory`: attaches to plan, random valor.
- `FinanceiroFactory`: attaches to Paciente, random tipo/valor.

Key Tests:
- test_plano_budget_accumulates
- test_plano_budget_decrements_on_delete
- test_financeiro_totals_exclude_cancelled
- test_api_dados_returns_expected_shape
- test_search_min_length_returns_empty

Add Pytest Fixtures:
- `app` (Flask test app via create_app + temporary sqlite memory or temp file).
- `db_session` (rollback after each test).

---
## 11. Data & Integrity Considerations
- Current manual arithmetic for `orcamento_total` can drift: implement recalculation safeguard soon.
- Financeiro lacks enum constraints; consider using Check constraints or Enum for `tipo` and `status`.
- No cascading deletes defined explicitly; deleting a Paciente currently cascades? (Default is no; related rows may orphan – validate and add `cascade="all, delete-orphan"` if desired.)

---
## 12. Validation & UX Gaps
- Dates: Only dd/mm/YYYY accepted; consider auto-normalizing `-` to `/`.
- CPF: Not validated; risk of duplicates with formatting differences (e.g., with/without punctuation).
- Monetary values: Accepting float; consider Decimal for financial precision.
- Forms: Limited user feedback messages; could centralize flash categories.

---
## 13. Performance & Scalability Notes
- Pagination only on Paciente list; others load all records (OK early, may need pagination for historico, procedimentos later).
- Queries mostly simple; add indexes (e.g., on `Financeiro.paciente_id`, `Procedimento.plano_id`) if performance degrades.

---
## 14. Security Notes
- CSRF enabled (disabled in tests via config).
- Authentication & authorization present (session user load + `require_roles`).
- Current roles enforced: admin, gerente, dentista (catalogo & pacientes domains).
- Missing yet: granular roles (financeiro, atendimento); password recovery & session timeout.
- Input validation moderate; HTML autoescaped by Jinja (default). Need stricter validation on CPF & monetary values.

---
## 15. Style & Conventions Recap
- PEP8 line length limit enforced in touched files.
- Spaces over tabs (verified in `pacientes/routes.py`).
- Explicit attribute assignment after object creation for clarity & analyzer friendliness.
- Use helper methods for repeated arithmetic once introduced.

### 15.1 Template / HTML Separation (Reinforced Principle)
Strict separation between presentation (HTML/Jinja) and business logic MUST be preserved and strengthened going forward:
- No database/session/business mutations inside templates; only read-only data rendering.
- Keep per‑blueprint templates under `templates/<blueprint>/` and use partials (`_partial_name.html`) for reusable fragments (forms, table rows, modal bodies).
- Introduce a `templates/partials/` or blueprint‑local `partials/` folder for cross‑module UI pieces (flash messages, pagination, form field macros).
- Use Jinja macros (`macros/forms.html`) for repetitive form field rendering (labels, errors) rather than duplicating markup.
- All conditional branching with side effects stays in Python routes/services; templates should only branch for display concerns (e.g., show/hide blocks) using already prepared flags/values.
- Prepare view models (dicts or lightweight dataclasses) in routes/services if raw models become too heavy to pass directly to templates.
- HTMX (when added) should call dedicated lightweight endpoints returning ONLY fragment templates (no full layout) – name them with `_fragment` suffix (e.g., `pacientes/_procedimento_row.html`).
- Keep JavaScript minimal and unobtrusive; prefer data attributes + HTMX for partial updates.
- Avoid embedding large inline scripts/styles inside business templates; centralize in static files.
- Never mix legacy monolithic template structures back into the refactored tree—migrate by extracting smallest functional partials.

Actionable Next Steps (Template Layer):
1. Create `templates/shared/_flash_messages.html` and include in base layout.
2. Extract repeated patient form fields into `templates/pacientes/_paciente_form_fields.html` + macro file.
3. Plan HTMX fragments: `_procedimento_row.html`, `_financeiro_row.html`.
4. Add naming convention note to this guide upon first fragment implementation.

---
## 16. Potential Refactors (Deferred)
- Extract service layer (e.g., `services/pacientes.py`) for business logic (budget recalculation, financial posting) to slim down routes.
- Introduce DTO or schema layer (Marshmallow / Pydantic) for API endpoints.
- Alembic migrations are configured per-bind; prefer migrations over
  `create_all()` outside tests.

---
## 17. Risks & Mitigations
| Risk | Impact | Mitigation |
|------|--------|-----------|
| Budget drift for planos | Inaccurate financial planning | Auto SQLAlchemy events + maintenance recompute route |
| Duplicate/invalid CPF | Data integrity & reporting issues | Implement normalization + checksum |
| Orphan child records on delete | Integrity issues | Add cascade rules or soft delete |
| Float precision in Financeiro | Rounding errors | Switch to Decimal with context precision |
| Open endpoints (no auth) | Unauthorized data exposure | Introduce auth layer before deployment |

---
## 18. Quick Start (For New Agent)
1. Ensure dependencies installed:
```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```
2. Run dev server:
```
python run.py
```
3. (Optional) Install dev deps & run tests:
```
.venv\Scripts\pip install -r requirements-dev.txt
pytest -q
```
4. (Optional) Run migrations per bind (examples):
```
alembic upgrade head                        # default odonto.db
alembic upgrade head -x target_bind=pacientes
alembic upgrade head -x target_bind=users
alembic upgrade head -x target_bind=receitas
alembic upgrade head -x target_bind=tratamentos
alembic upgrade head -x target_bind=calendario
```
5. Begin with High priority backlog items in Section 8.

---
## 19. Glossary
- Plano: Aggregation of proposed dental procedures.
- Procedimento: Atomic planned or executed action (e.g., obturação).
- Histórico: Narrative log independent of procedural plan.
- Financeiro Lançamento: Monetary record (credit=payment, debit=charge/liability).

---
## 20. Update Log
- 2025-09-10 (AM): Initial comprehensive guide created.
- 2025-09-10 (AM): Added multi-binds ('users', 'tratamentos', 'receitas').
- 2025-09-10 (AM): Partial legacy migration (receitas, documentos simples, atestados).
- 2025-09-10 (AM): Added tests for planos & financeiro (totals, saldo policy initial version).
- 2025-09-10 (PM): Implemented authentication blueprint & `require_roles` decorator; applied to catalogo and pacientes routes.
- 2025-09-10 (PM): Soft delete for Paciente (`deleted_at`) + restore route + UI badge & admin-only restore button.
- 2025-09-10 (PM): Refined saldo policy (créditos pagos - débitos não cancelados) + updated tests.
- 2025-09-10 (PM): Added role-based tests for pacientes (procedimentos, recompute, excluir/restaurar) & financeiro creation restrictions.
- 2025-09-10 (PM): Introduced migration script `migrations/20250910_add_paciente_deleted_at.py` (pre-Alembic stopgap).
- 2025-09-10 (PM): Simplified financeiro saldo computation to server-side only; removed duplicated template logic.
-- 2025-09-10 (PM): Added finance role negative tests (`test_financeiro_roles.py`). Total test count: 66 passed.
-- 2025-09-10 (PM): Added HTMX inline add for Financeiro (endpoint `/financeiro/novo/htmx`) and totals partial; test added. Total test count: 67 passed.
-- 2025-09-10 (PM): Migrated monetary fields to Decimal, added procedimento_id linkage, enum constraints, Alembic initial revision, automatic orçamento recompute events, expanded roles (atendimento, financeiro, groups) – all tests green (67).
-- 2025-09-10 (PM): Migrated monetary fields to Decimal, added procedimento_id linkage, enum constraints, Alembic initial revision, automatic orçamento recompute events, expanded roles (atendimento, financeiro, groups) – all tests green (67).
-- 2025-09-10 (PM): Adicionadas paginação em histórico e financeiro e resumo financeiro por plano; suíte permanece verde (67).
-- 2025-09-10 (PM): Novos testes de CPF (variações de formatação, DVs inválidos) aumentam total para 71 testes passando.

- 2025-09-11: Segurança reforçada (política de senha, lockout, timeout de inatividade, expiração opcional), eventos SQLAlchemy garantem recálculo automático de orçamento, CPF normalizado + checksum com testes, paginação e resumo financeiro por plano confirmados, helpers de teste compartilhados (`utils_auth.login_as`, `utils_factory`), script de lint estabilizado; suíte completa verde (78).
-- 2025-09-11: Alembic por bind configurado; auto-upgrade desativado por
  padrão; instruções de CLI adicionadas. Parcial HTMX para financeiro
  disponível; partial de flashes unificado em `templates/shared/_flash_messages.html`.

- 2025-09-11 (PM): Adicionado dashboard de pacientes em `/pacientes/dashboard` com métricas
  (pacientes ativos, procedimentos pendentes/realizados e saldo global) e
  teste associado; suíte total agora com 79 testes passando.

---
## 21. Maintenance Instructions
When adding new domain logic:
- Keep route functions thin; prefer helper/service extraction.
- Add/extend tests BEFORE major refactors when possible.
- Update this guide: (a) Milestones Achieved, (b) Backlog adjustments, (c) Update Log entry.
- Re-run tests & style checks after modifications.

---
## 22. Exit Criteria for Next Milestone ("Clinical & Financial Stability v1")
Must have:
- Tests: ≥80% coverage for pacientes blueprint critical paths (plan/procedimento add/remove, financeiro totals, API data endpoint).
- Recompute safeguard for plano budgets.
- CPF validation & normalization.
- Financeiro saldo policy clearly defined & tested.
- Guide updated with milestone closure date.

---
## 23. Contact / Ownership
- Original author: (inferred) AlanKBR repository owner.
- Future agents: Append your identifier & date to Update Log when making structural changes.

---
# (Addendum inserted) Legacy Origin & Migration Context

This project is a structured remake of a earlier, less modular codebase located under `legacy/`. Future contributors should REVIEW legacy to understand prior behaviors, especially features not yet re-implemented.

Legacy Key Points:
- Monolithic style with mixed concerns (models, routes, services) under `legacy/app/`.
- Broader domain coverage present in legacy models that are only partially ported:
  - `tratamento.py` (CategoriaTratamento, Tratamento catalog)  -> NOT yet reintroduced in refactor.
  - `user.py` (authentication, roles, professional metadata)   -> AUTH layer missing in new structure.
  - `documento.py` (dynamic patient documents)                 -> NOT ported.
  - Extended Procedimento fields: `dentes_selecionados`, `quadrantes`, `boca_completa`, link to optional Tratamento catalog -> Simplified in new version.
  - Financeiro fields largely similar; statuses conceptually same.
- Line length, style, and cascade configuration differ (legacy used cascades like `all, delete-orphan`; refactor currently omits them).
- Legacy agenda blueprint carried its own initialization pattern (see `legacy/agenda/README-module.md`). We adopted a unified central factory instead.

Migration/Parity Tracking Table (High-level):
| Legacy Component | Status in Refactor | Notes |
|------------------|--------------------|-------|
| Paciente CRUD    | Implemented        | Simplified relationships (no cascade yet). |
| Ficha/Anamnese   | Implemented        | Legacy stored ultima_atualizacao; refactor handles manually. |
| PlanoTratamento  | Implemented        | Missing dentista_id & cascade. |
| Procedimento Advanced Tooth Mapping | Not implemented | Re-add after core stability. |
| Tratamento Catalog | Not implemented | Requires new bind or reuse; plan for controlled import. |
| CategoriaTratamento | Not implemented | Blocked by Tratamento catalog deferment. |
| Historico        | Implemented        | Legacy had dentista_id (omitted). |
| Financeiro       | Implemented (basic) | Need saldo policy & linkage to plan/procedures. |
| Documento Model  | Parcial (DocumentoSimples) | Versões/assinatura não migradas. |
| User/Auth Layer  | Not implemented | High priority before production exposure. |
| Agenda Module    | Implemented (ported) | Token persistence retained. |
| Cascade Deletes  | Not implemented | Decide between soft delete vs cascade. |
| Tooth Selection UI Logic | Not implemented | Depends on front-end interaction design (HTMX/reactivity). |
| Receitas (modelos) | Parcial | CRUD básico persistido (sem versão/impressão PDF). |
| Atestados | Parcial | Geração em tela, sem PDF/assinatura. |

Strategic Intent of Remake:
1. Isolate bounded contexts (agenda, pacientes, future auth) into dedicated blueprints & DB binds.
2. Remove legacy complexity (dynamic document & catalog subsystems) until core patient + plan + finance flows are tested & stable.
3. Enforce consistent style (PEP8 lines <=79) to aid automated tooling & diff clarity.
4. Create a strong test harness BEFORE reintroducing advanced domain features to avoid regression risk.
5. Introduce each deferred legacy feature behind a service layer interface to avoid bloating routes.

Deferred Feature Reintroduction Guidelines:
- Tratamento Catalog: Introduce new blueprint `catalogo` or integrate into `pacientes` with clear separation. Add models with proper binds (consider new `tratamentos` bind) and service functions for price lookup, allowing Procedimento to optionally reference treatments again.
- Advanced Tooth Mapping: Represent as JSON (list of teeth identifiers) plus flags; extend forms and templates; maintain backward compatibility by leaving existing `dente` field populated with a human-readable summary.
- Documento Model: Evaluate compliance/legal requirements; if re-added, use a dedicated storage approach and possibly template-driven rendering (Jinja->PDF) with a version field.
- Auth & Users: Add `auth` blueprint. Migrate `User` model with hashed passwords; integrate Flask-Login; wrap protected routes with login_required decorators.
- Cascade vs Soft Delete: Prefer soft delete for auditing once auth exists; otherwise apply cascade to prevent orphan data in early iterations.

---
## 24. Legacy Migration Tasks
- [ ] Audit legacy `paciente.Procedimento` for advanced fields; plan migration.
- [ ] Review and test all legacy routes and models for behavioral parity.
- [ ] Reintroduce or refactor legacy features as outlined in deferred guidelines.
- [ ] Validate data integrity and application behavior post-migration.
- [ ] Update documentation and guides to reflect legacy integration status.

---
## 25. Ongoing Maintenance with Legacy
- Maintain clear separation between legacy and new code (e.g., legacy/ vs app/).
- Gradually refactor legacy code for consistency with new standards where feasible.
- Prioritize high-impact legacy gaps for immediate attention (e.g., auth, critical models).
- Leverage legacy tests and behaviors to inform new test creation and feature validation.

---
## 26. Legacy Contact / Ownership
- Legacy author: AlanKBR (assumed from repository history).
- Legacy code inquiries: Direct to current repository maintainers or original author if identifiable.

---
## Supplemental Deep-Dive Sections (Origem: Lista de Sugestões)
As seções abaixo expandem tópicos críticos solicitados. Numeração corresponde à lista adicional previamente sugerida.

### 3. Plano de Expansão de Testes
Objetivo: Evoluir cobertura de testes de ~básica para robusta antes de reintroduzir funcionalidades legadas.

Fases & Metas de Cobertura:
- Fase 1 (Core Pacientes): 60% linhas / 80% rotas principais exercitadas.
- Fase 2 (Financeiro + Planos): 70–75% linhas, 90% lógica de cálculo.
- Fase 3 (Validações + Erros): 80%+ linhas, 95% branches críticos.

Matriz de Tipos de Teste:
| Tipo | Escopo | Exemplos |
|------|--------|----------|
| Unitário | Funções/helpers isoladas | recompute_orcamento_total() |
| Modelo | Métodos de modelo/constraints | idade(), saldo derivado |
| Serviço (futuro) | Regras de negócio consolidadas | adicionar_procedimento() |
| Rota (View) | Respostas HTTP + templates | GET /pacientes/<id>/planos |
| API JSON | Estrutura e status codes | /pacientes/api/<id>/dados |
| Fragmento (HTMX futuro) | HTML parcial | Linha de procedimento adicionada |

Factories Planejadas (tests/factories.py):
- PacienteFactory
- PlanoTratamentoFactory
- ProcedimentoFactory
- FinanceiroFactory
- HistoricoFactory (opcional)

Convenções:
- Nome de arquivo: test_<dominio>_<aspecto>.py (ex: test_pacientes_planos.py)
- Usar fixtures: app, client, db_session, paciente_factory.
- Validar ambos happy path e edge (ex: remoção de último procedimento).

### 4. Linha de Base de Performance
Metas iniciais (registrar valores reais depois):
- Listagem de pacientes (pag. 1): <= 5 queries.
- Visualização de plano com 10 procedimentos: <= 3 queries adicionais.
- Cálculo de totais financeiros: O(n) onde n = lançamentos filtrados; otimizar depois se > 500 registros.

Instrumentação Recomendada:
- Decorador simples para logar tempo de rota (>150ms alerta).
- Uso de flask debugtoolbar (ambiente dev) para contar queries (futuro).

Estratégias Futuras:
- Paginação em histórico/financeiro > 50 registros.
- Índices: (procedimentos.plano_id), (financeiro.paciente_id, status), (historicos.paciente_id, data DESC).

### 5. Roteiro de Segurança & Privacidade
Princípios (mesmo antes de auth):
- Minimizar exposição de dados sensíveis via endpoints JSON.
- Sanitização de entrada (mais validações em CPF, e-mail, telefone).
- Preparar criptografia futura (colunas sensíveis? – não crítico agora).

Futuro Próximo:
- Adicionar autenticação antes de publicar externamente.
- Introduzir política de logs que evita registrar dados clínicos extensos.
- Planejar retenção / arquivamento (ex: históricos > X anos).

### 6. Modelo de Autorização (Draft)
Perfis Planejados:
| Papel | Permissões Principais |
|-------|-----------------------|
| admin | Tudo (gerência + usuários) |
| dentista | CRUD clínico + planos + procedimentos + histórico |
| atendimento | Criar/editar paciente, ver ficha, não alterar anamnese clínica detalhada |
| financeiro | Lançamentos financeiros + relatórios, não mexe em procedimentos |

Mapeamento de Rotas (Exemplo Inicial):
- /pacientes/novo -> atendimento, admin.
- /pacientes/<id>/planos -> dentista, admin.
- /pacientes/<id>/financeiro -> financeiro, admin.
- /pacientes/<id>/historico/novo -> dentista, admin.

Implementação Futura:
- Integrar Flask-Login + decorator @roles_required.
- Centralizar verificação em camada de serviço para evitar repetição.

### 7. Tratamento de Erros & Logging
Padrões Recomendados:
- JSON de erro (para endpoints API) => { "error": { "code": "<slug>", "message": "<descrição>" } }
- Slugs internos (ex): validation_error, not_found, business_rule_violation.
- Log estruturado (futuro): logging JSON (level, timestamp, rota, duração).

Boas Práticas:
- Nunca expor stack trace em produção.
- Normalizar mensagens flash: success, info, warning, danger.

### 10. Plano de Integração HTMX
Objetivo: Atualizações parciais sem recarregar páginas inteiras.
Abordagem:
- Endpoints fragment: retornam somente bloco HTML (sem layout base) – ex: /pacientes/<id>/planos/<plano_id>/procedimentos/fragmento_linha.
- Nome de templates parciais: prefixo `_` (ex: `_procedimento_row.html`).
- Atributos HTMX: hx-post/hx-get + hx-target + hx-swap="outerHTML".

Primeiros Casos:
1. Adicionar procedimento (retorna linha recém-criada).
2. Registrar lançamento financeiro (atualiza tabela e totais com fragmento separado `_financeiro_totais.html`). Endpoint HTMX inicial para add-row já presente com teste validando retorno e HX-Trigger de atualização.

Controle de Erros:
- Responder 422 com fragmento de erro de validação substituindo somente a área do formulário.

### Log de Progresso 2025-09-10 (Batch Adicional)
- Criado templates iniciais: `auth/login.html`, `catalogo/lista.html`.
- Estrutura básica de UI para login e listagem de categorias pronta para expansão CRUD.
- Próximo alvo automático: adicionar CRUD de categorias e tratamentos + formulários parciais reutilizáveis.

### 15. Fluxo de Contribuição
Branching:
- feature/<slug>
- fix/<slug>
- chore/<slug>

Commits (recomendado): Conventional style curto (ex: feat(pacientes): adiciona recalculo de orçamento).

Checklist de PR:
- [ ] Testes adicionados/atualizados.
- [ ] Cobertura não diminuiu.
- [ ] Migrations incluídas (quando schema muda).
- [ ] Guia (este arquivo) atualizado (se relevante).
- [ ] Linters/format passam (quando integrados).

### 16. Mapa de Evolução do Modelo de Dados
| Entidade | Campos Atuais Chave | Extensões Planejadas |
|----------|---------------------|----------------------|
| Paciente | nome, data_nascimento, cpf | Normalização CPF, soft delete flag, foreign key usuário responsável |
| PlanoTratamento | descricao, status, orcamento_total | dentista_id reintrodução, timestamps extra (data_conclusao) |
| Procedimento | descricao, dente, valor, status | JSON dentes, quadrantes, boca_completa, link Tratamento, auditoria (criado_por) |
| Historico | descricao, data | dentista_id, tags (lista) |
| Financeiro | valor, tipo, status | Enum real, vínculo obrigatório opcional a plano/procedimento, parcelamento futuro |
| Tratamento (catálogo) | (deferido) | Categoria, preço base, duração, ativo |
| Documento | (deferido) | Versões, assinatura digital, hash integridade |

### 18. Internacionalização / Idioma Preferencial (pt-BR)
Política Atual:
- Idioma padrão da interface e mensagens: Português (Brasil).
- Todos os textos novos devem ser redigidos diretamente em pt-BR claro e consistente.

Diretrizes:
- Evitar misturar inglês em labels (ex: usar "Salvar" ao invés de "Save").
- Centralizar strings em módulo futuro (ex: `i18n/messages.py`) para facilitar eventual exportação.
- Datas apresentadas em formato dd/mm/aaaa.
- Números monetários: usar separador de milhar opcional e vírgula para decimais ao exibir (ex: 1.234,50) – persistir sempre como número (não string) no banco.

Estratégia Futura de i18n:
- Introduzir Babel (Flask-Babel) se for necessário multi-idioma; até lá manter consistência manual.
- Criar convenção de chaves (ex: paciente.label.nome, financeiro.msg.lancamento_criado).

Revisões:
- Ao adicionar grandes blocos de texto (anamnese, documentos), garantir codificação UTF-8 e evitar hard breaks desnecessários.

---
( Fim das seções suplementares )
