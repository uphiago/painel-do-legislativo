from legislativo_backend.collectors import camara


def test_list_deputados_accepts_page_parameter(monkeypatch):
    seen = {}

    def fake_fetch_json(url, params=None):
        seen["url"] = url
        seen["params"] = params
        return {"dados": []}

    monkeypatch.setattr(camara, "fetch_json", fake_fetch_json)

    camara.list_deputados(limit=100, page=3)

    assert seen["params"]["pagina"] == 3
    assert seen["params"]["itens"] == 100


def test_list_all_deputados_walks_until_short_page(monkeypatch):
    pages = {
        1: [{"id": index} for index in range(100)],
        2: [{"id": index} for index in range(100, 200)],
        3: [{"id": 200}],
    }

    def fake_list_deputados(limit=100, page=1):
        return {"dados": pages[page]}

    monkeypatch.setattr(camara, "list_deputados", fake_list_deputados)

    rows = camara.list_all_deputados(page_size=100)

    assert len(rows) == 201
    assert rows[-1] == {"id": 200}


def test_list_proposicoes_by_year_accepts_page_parameter(monkeypatch):
    seen = {}

    def fake_fetch_json(url, params=None):
        seen["params"] = params
        return {"dados": []}

    monkeypatch.setattr(camara, "fetch_json", fake_fetch_json)

    camara.list_proposicoes_by_year(ano=2026, page=4, limit=100)

    assert seen["params"]["ano"] == 2026
    assert seen["params"]["pagina"] == 4
    assert seen["params"]["itens"] == 100
