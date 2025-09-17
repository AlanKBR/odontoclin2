import json


def create_user(session, User, nome, cargo="dentista"):
    u = User()
    u.nome_completo = nome
    u.username = nome.replace(" ", "_").lower()
    u.cargo = cargo
    u.is_active_db = True
    session.add(u)
    session.commit()
    return u


def create_patient(session, Paciente, nome):
    p = Paciente()
    p.nome = nome
    session.add(p)
    session.commit()
    return p


def test_preview_and_emit(client, app):
    # Import model classes inside app context
    with app.app_context():
        from app.auth.models import User
        from app.pacientes.models import Paciente
        from app import db

        # criar dados básicos
        u = create_user(db.session, User, "Dr Teste", cargo="dentista")
        p = create_patient(db.session, Paciente, "Paciente Teste")
        u_id = u.id
        p_id = p.id

        itens = [
            {
                "medicamento_id": 1,
                "medicamento_nome": "Paracetamol",
                "posologia": "1 comp 8/8h",
            }
        ]

    # Preview
    payload = {"paciente_id": p_id, "dentista_id": u_id, "itens": itens}
    resp = client.post(
        "/receitas/preview", data=json.dumps(payload), content_type="application/json"
    )
    assert resp.status_code == 200
    assert b"Paracetamol" in resp.data

    # Emitir
    resp2 = client.post(
        "/receitas/emitir", data=json.dumps(payload), content_type="application/json"
    )
    assert resp2.status_code == 200
    data = resp2.get_json()
    assert "print_url" in data
