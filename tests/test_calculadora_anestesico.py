def test_calc_page(client):
    r = client.get("/calculadora-anestesico/")
    assert r.status_code == 200
    assert b"Calculadora de Anest" in r.data


def test_calc_htmx_basic(client):
    data = {
        "peso": "70",
        "anestesico": "lidocaina",
        "concentracao": "2",
        "vaso": "epinefrina",
        "conc_vaso": "0.01",
    }
    r = client.post("/calculadora-anestesico/calcular", data=data)
    assert r.status_code == 200
    # Should show a number of tubetes and explanation details
    assert (
        b"N\xc3\xbamero m\xc3\xa1ximo de tubetes" in r.data or b"Numero maximo de tubetes" in r.data
    )
