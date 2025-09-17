from app.receitas.models import Atestado
from app.pacientes.models import Paciente


def test_get_gerar_mostra_select_paciente(client):
    resp = client.get("/atestados/gerar")
    assert resp.status_code == 200
    # deve conter select de paciente
    assert b"select" in resp.data.lower()


def test_post_gerar_cria_atestado(client, app):
    # cria paciente
    with app.app_context():
        from app import db

        p = Paciente()
        p.nome = "Joao da Silva"
        db.session.add(p)
        db.session.commit()

        # envia formulário vinculando paciente pelo id
        resp = client.post(
            "/atestados/gerar",
            data={
                "paciente_id": str(p.id),
                "dias": "2",
                "fins": "trabalhistas",
                "csrf_token": "",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200

        # gerar_atestado não deve gravar no DB; apenas renderizar preview
        reg = Atestado.query.order_by(Atestado.id.desc()).first()
        # se não havia registros antes, reg pode ser None
        # aqui garantimos que não houve um novo registro com os mesmos dados
        if reg is not None:
            assert not (reg.dias == 2 and reg.motivo == "trabalhistas" and reg.paciente_id == p.id)
