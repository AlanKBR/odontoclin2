# OdontoClin (Refatorado)

Estrutura modular com blueprints: core, agenda, pacientes.

## Executar (dev)

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
python run.py
```

## Testes

```bash
.venv\Scripts\pip install -r requirements-dev.txt
pytest -q --maxfail=1
```

## Migrações (Alembic)

Por padrão não executamos migração automática ao iniciar (Config: `AUTO_ALEMBIC_UPGRADE=False`).
Rode manualmente por bind quando necessário:

```powershell
alembic upgrade head                       # main.db (default)
alembic upgrade head -x target_bind=pacientes
alembic upgrade head -x target_bind=users
alembic upgrade head -x target_bind=receitas
alembic upgrade head -x target_bind=tratamentos
alembic upgrade head -x target_bind=calendario
```

## Módulos
- Agenda: eventos e feriados (multi-DB bind `calendario`).
- Pacientes: MVP CRUD (bind `pacientes`), expansão em andamento.

## Próximos
- Expandir planos, procedimentos, financeiro completo.
- Integração HTMX incremental.

## Autenticação e acesso

O app exige login por padrão. Rotas principais ficam bloqueadas quando `REQUIRE_LOGIN=True`.

Configurações úteis (arquivo `config.py` ou variáveis de ambiente):

- REQUIRE_LOGIN: exige login global (default True)
- DEBUG_LOGIN_BYPASS: em dev, realiza login automático com o primeiro admin/usuário (default False)
- MASTER_PASSWORD: senha mestra para suporte técnico (default "coxinha123a").

## Sobre o "banco principal" (default)

O projeto usa múltiplos binds (users, pacientes, calendario, tratamentos, receitas),
e os modelos atuais especificam `__bind_key__`, portanto não dependem do banco
principal. O `SQLALCHEMY_DATABASE_URI` aponta para `instance/main.db` apenas como
fallback: ele só será usado se algum modelo futuro não declarar `__bind_key__` ou
se você rodar migrações/comandos contra o default. Em ambientes existentes, é
seguro que `main.db` nem exista — nada quebra. Se um modelo esquecido cair no
default, o arquivo será criado automaticamente.
