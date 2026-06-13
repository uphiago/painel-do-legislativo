from legislativo_backend.normalizers import (
    normalize_camara_ceap_archive_row,
    normalize_camara_deputado,
    normalize_camara_despesa,
    normalize_camara_proposicao,
    normalize_senado_autoria,
    normalize_senado_ceaps,
    normalize_senado_processo,
    normalize_senado_senador,
)


def test_normalize_camara_deputado_maps_core_profile_fields():
    result = normalize_camara_deputado(
        {
            "id": 204379,
            "nome": "Acácio Favacho",
            "siglaPartido": "MDB",
            "siglaUf": "AP",
            "urlFoto": "https://example.com/foto.jpg",
            "email": "dep@example.com",
        }
    )

    assert result.model_dump() == {
        "source": "camara",
        "external_id": "204379",
        "nome": "Acácio Favacho",
        "casa": "camara",
        "partido": "MDB",
        "uf": "AP",
        "email": "dep@example.com",
        "foto_url": "https://example.com/foto.jpg",
    }


def test_normalize_senado_senador_maps_nested_identification():
    result = normalize_senado_senador(
        {
            "IdentificacaoParlamentar": {
                "CodigoParlamentar": "5672",
                "NomeParlamentar": "Alan Rick",
                "SiglaPartidoParlamentar": "REPUBLICANOS",
                "UfParlamentar": "AC",
                "EmailParlamentar": "sen.alanrick@senado.leg.br",
                "UrlFotoParlamentar": "https://example.com/senador.jpg",
            }
        }
    )

    assert result.source == "senado"
    assert result.external_id == "5672"
    assert result.nome == "Alan Rick"
    assert result.casa == "senado"
    assert result.partido == "REPUBLICANOS"
    assert result.uf == "AC"


def test_normalize_senado_ceaps_maps_reimbursed_value():
    result = normalize_senado_ceaps(
        {
            "id": 2229299,
            "ano": 2024,
            "mes": 4,
            "codSenador": 5672,
            "nomeSenador": "ALAN RICK",
            "tipoDespesa": "Passagens aéreas",
            "fornecedor": "AEROTUR SERVIÇOS",
            "documento": "2154385247",
            "data": "2024-04-26",
            "valorReembolsado": 1030.22,
        }
    )

    assert result.source == "senado_ceaps"
    assert result.external_id == "2229299"
    assert result.parlamentar_external_id == "5672"
    assert result.valor == 1030.22


def test_normalize_camara_despesa_prefers_liquid_value():
    result = normalize_camara_despesa(
        {
            "codDocumento": 123,
            "ano": 2024,
            "mes": 2,
            "tipoDespesa": "COMBUSTÍVEIS E LUBRIFICANTES.",
            "nomeFornecedor": "POSTO TESTE",
            "numDocumento": "NF-1",
            "dataDocumento": "2024-02-03",
            "valorDocumento": 500,
            "valorLiquido": 450,
        },
        deputado_id=204379,
    )

    assert result.source == "camara_ceap"
    assert result.external_id == "123"
    assert result.parlamentar_external_id == "204379"
    assert result.valor == 450


def test_normalize_camara_ceap_archive_row_maps_annual_csv_fields():
    result = normalize_camara_ceap_archive_row(
        {
            "txNomeParlamentar": "Deputada Teste",
            "nuDeputadoId": "204379",
            "numAno": "2024",
            "numMes": "2",
            "txtDescricao": "DIVULGAÇÃO DA ATIVIDADE PARLAMENTAR.",
            "txtFornecedor": "FORNECEDOR TESTE",
            "txtNumero": "NF-1",
            "datEmissao": "2024-02-03T00:00:00",
            "vlrDocumento": "500.3",
            "vlrLiquido": "450.2",
            "ideDocumento": "7696122",
        }
    )

    assert result.source == "camara_ceap_arquivo"
    assert result.external_id == "7696122"
    assert result.parlamentar_external_id == "204379"
    assert result.parlamentar_nome == "Deputada Teste"
    assert result.valor == 450.2


def test_normalize_camara_proposicao_maps_legislative_fields():
    result = normalize_camara_proposicao(
        {
            "id": 2626629,
            "siglaTipo": "PL",
            "numero": 2546,
            "ano": 2026,
            "ementa": "Altera o Código de Processo Civil.",
            "dataApresentacao": "2026-05-20T20:10",
        }
    )

    assert result.source == "camara"
    assert result.external_id == "2626629"
    assert result.sigla == "PL"
    assert result.numero == "2546"
    assert result.ano == 2026


def test_normalize_senado_autoria_maps_nested_materia():
    result = normalize_senado_autoria(
        {
            "Materia": {
                "Codigo": "159093",
                "Sigla": "PEC",
                "Numero": "35",
                "Ano": "2023",
                "Ementa": "Altera o Sistema Tributário Nacional.",
                "Data": "2023-08-10",
            },
            "IndicadorAutorPrincipal": "Não",
        }
    )

    assert result.source == "senado"
    assert result.external_id == "159093"
    assert result.sigla == "PEC"
    assert result.numero == "35"
    assert result.ano == 2023
    assert result.autor_principal is False


def test_normalize_senado_processo_maps_new_process_endpoint():
    result = normalize_senado_processo(
        {
            "id": 8360649,
            "identificacao": "RQS 41/2023",
            "sigla": "RQS",
            "numero": "41",
            "ano": 2023,
            "conteudo": {"ementa": "Desarquivamento de matérias."},
            "documento": {"dataApresentacao": "2023-02-02"},
        }
    )

    assert result.source == "senado_processo"
    assert result.external_id == "8360649"
    assert result.sigla == "RQS"
    assert result.numero == "41"
    assert result.ano == 2023
    assert result.ementa == "Desarquivamento de matérias."
    assert result.data_apresentacao == "2023-02-02"


def test_normalize_senado_processo_extracts_parts_from_identificacao_when_list_is_flat():
    result = normalize_senado_processo(
        {
            "id": 8784312,
            "identificacao": "PDL 29/2025",
            "ementa": "Susta decreto.",
            "dataApresentacao": "2025-01-07",
        }
    )

    assert result.sigla == "PDL"
    assert result.numero == "29"
    assert result.ano == 2025
