import pytest


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/auth/login",
        "/agenda/",
        "/ai/",
        "/atestados/",
        "/catalogo/",
        "/cro/",
        "/documentos/",
        "/dashboard/",
        "/pacientes/",
        "/receitas/",
        "/reports/",
    ],
)
def test_routes_render_ok(client, path):
    resp = client.get(path)
    assert resp.status_code == 200, f"GET {path} should render 200, got {resp.status_code}"
    # basic HTML sanity
    assert b"<!doctype html" in resp.data.lower() or b"<html" in resp.data.lower()
