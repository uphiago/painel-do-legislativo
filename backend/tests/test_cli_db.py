from pathlib import Path
import zipfile

from typer.testing import CliRunner

from legislativo_backend.cli import app
from legislativo_backend.db import LocalDatabase
from legislativo_backend.normalizers import ParlamentarResumo, ProposicaoResumo

runner = CliRunner()


def test_db_init_and_summary_commands(tmp_path: Path):
    db_path = tmp_path / "painel.db"

    init_result = runner.invoke(app, ["db", "init", "--path", str(db_path)])
    summary_result = runner.invoke(app, ["db", "summary", "--path", str(db_path)])

    assert init_result.exit_code == 0
    assert "banco inicializado" in init_result.stdout
    assert summary_result.exit_code == 0
    assert "parlamentarians: 0" in summary_result.stdout


def test_collect_camara_deputados_writes_to_local_db(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "painel.db"

    monkeypatch.setattr(
        "legislativo_backend.cli.list_deputados",
        lambda limit: {
            "dados": [
                {
                    "id": 204379,
                    "nome": "Acácio Favacho",
                    "siglaPartido": "MDB",
                    "siglaUf": "AP",
                    "urlFoto": "https://example.com/foto.jpg",
                    "email": "dep@example.com",
                }
            ]
        },
    )

    result = runner.invoke(
        app,
        ["collect", "camara-deputados", "--limit", "1", "--db-path", str(db_path)],
    )

    assert result.exit_code == 0
    assert "parlamentares gravados: 1" in result.stdout
    assert LocalDatabase(db_path).summary()["parlamentarians"] == 1


def test_collect_senado_processos_by_term_writes_to_local_db(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "painel.db"

    monkeypatch.setattr(
        "legislativo_backend.cli.list_processos_by_termo",
        lambda termo, data_inicio, data_fim: [
            {
                "id": 8784312,
                "identificacao": "PDL 29/2025",
                "ementa": "Susta decreto.",
                "dataApresentacao": "2025-01-07",
            }
        ],
    )

    result = runner.invoke(
        app,
        [
            "collect",
            "senado-processos",
            "--termo",
            "seguranca publica",
            "--limit",
            "1",
            "--db-path",
            str(db_path),
        ],
    )

    assert result.exit_code == 0
    assert "proposicoes gravadas: 1" in result.stdout
    assert LocalDatabase(db_path).summary()["propositions"] == 1


def test_collect_parlamentares_full_writes_both_houses(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "painel.db"

    monkeypatch.setattr(
        "legislativo_backend.cli.list_all_deputados",
        lambda page_size=100: [
            {
                "id": 204379,
                "nome": "Acácio Favacho",
                "siglaPartido": "MDB",
                "siglaUf": "AP",
                "urlFoto": "https://example.com/foto.jpg",
                "email": "dep@example.com",
            },
            {
                "id": 220593,
                "nome": "Adail Filho",
                "siglaPartido": "MDB",
                "siglaUf": "AM",
            },
        ],
    )
    monkeypatch.setattr(
        "legislativo_backend.cli.list_senadores_atual",
        lambda: {
            "ListaParlamentarEmExercicio": {
                "Parlamentares": {
                    "Parlamentar": [
                        {
                            "IdentificacaoParlamentar": {
                                "CodigoParlamentar": "5672",
                                "NomeParlamentar": "Alan Rick",
                                "SiglaPartidoParlamentar": "REPUBLICANOS",
                                "UfParlamentar": "AC",
                            }
                        }
                    ]
                }
            }
        },
    )

    result = runner.invoke(
        app,
        ["collect", "parlamentares-full", "--db-path", str(db_path)],
    )

    assert result.exit_code == 0
    assert "deputados gravados: 2" in result.stdout
    assert "senadores gravados: 1" in result.stdout
    assert LocalDatabase(db_path).summary()["parlamentarians"] == 3


def test_collect_camara_lote_enriches_existing_parliamentarians(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "painel.db"
    db = LocalDatabase(db_path)
    db.init()
    db.upsert_parlamentarians(
        [
            ParlamentarResumo(
                source="camara",
                external_id="204379",
                nome="Acácio Favacho",
                casa="camara",
            )
        ]
    )

    monkeypatch.setattr(
        "legislativo_backend.cli.get_deputado_detail",
        lambda deputado_id: {"dados": {"id": deputado_id, "nomeCivil": "Acácio Favacho"}},
    )
    monkeypatch.setattr(
        "legislativo_backend.cli.list_deputado_orgaos",
        lambda deputado_id: {"dados": [{"idOrgao": 1, "siglaOrgao": "CSSF"}]},
    )
    monkeypatch.setattr(
        "legislativo_backend.cli.list_deputado_frentes",
        lambda deputado_id: {"dados": [{"id": 10, "titulo": "Frente da Saúde"}]},
    )
    monkeypatch.setattr(
        "legislativo_backend.cli.list_deputado_proposicoes",
        lambda deputado_id, limit: {
            "dados": [
                {
                    "id": 2626629,
                    "siglaTipo": "PL",
                    "numero": 2546,
                    "ano": 2026,
                    "ementa": "Altera o Código de Processo Civil.",
                }
            ]
        },
    )
    monkeypatch.setattr(
        "legislativo_backend.cli.list_deputado_despesas",
        lambda deputado_id, ano, limit: {
            "dados": [
                {
                    "codDocumento": 123,
                    "ano": ano,
                    "mes": 1,
                    "tipoDespesa": "COMBUSTÍVEIS E LUBRIFICANTES.",
                    "nomeFornecedor": "POSTO TESTE",
                    "valorLiquido": 100,
                }
            ]
        },
    )

    result = runner.invoke(
        app,
        [
            "collect",
            "camara-lote",
            "--limit",
            "1",
            "--db-path",
            str(db_path),
        ],
    )

    assert result.exit_code == 0
    assert "perfis camara processados: 1" in result.stdout
    assert LocalDatabase(db_path).summary()["propositions"] == 1
    assert LocalDatabase(db_path).summary()["expenses"] == 1
    assert LocalDatabase(db_path).summary()["raw_payloads"] == 3


def test_collect_senado_lote_enriches_existing_senators(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "painel.db"
    db = LocalDatabase(db_path)
    db.init()
    db.upsert_parlamentarians(
        [
            ParlamentarResumo(
                source="senado",
                external_id="5672",
                nome="Alan Rick",
                casa="senado",
            )
        ]
    )

    monkeypatch.setattr(
        "legislativo_backend.cli.list_senador_comissoes",
        lambda codigo: {"comissoes": [{"sigla": "CAS"}]},
    )
    monkeypatch.setattr(
        "legislativo_backend.cli.list_processos_by_parlamentar",
        lambda codigo: [
            {
                "id": 8360649,
                "identificacao": "RQS 41/2023",
                "ementa": "Desarquivamento de matérias.",
                "dataApresentacao": "2023-02-02",
            }
        ],
    )

    result = runner.invoke(
        app,
        [
            "collect",
            "senado-lote",
            "--limit",
            "1",
            "--processos-limit",
            "1",
            "--db-path",
            str(db_path),
        ],
    )

    assert result.exit_code == 0
    assert "perfis senado processados: 1" in result.stdout
    assert LocalDatabase(db_path).summary()["propositions"] == 1
    assert LocalDatabase(db_path).summary()["raw_payloads"] == 2


def test_collect_senado_lote_records_error_and_keeps_offset_moving(
    tmp_path: Path,
    monkeypatch,
):
    db_path = tmp_path / "painel.db"
    db = LocalDatabase(db_path)
    db.init()
    db.upsert_parlamentarians(
        [
            ParlamentarResumo(source="senado", external_id="1", nome="Senador A", casa="senado"),
            ParlamentarResumo(source="senado", external_id="2", nome="Senador B", casa="senado"),
        ]
    )

    monkeypatch.setattr(
        "legislativo_backend.cli.list_senador_comissoes",
        lambda codigo: {"comissoes": []},
    )

    def fake_processos(codigo):
        if codigo == 1:
            raise TimeoutError("fonte lenta")
        return [{"id": 2, "identificacao": "PL 2/2025", "ementa": "Teste"}]

    monkeypatch.setattr("legislativo_backend.cli.list_processos_by_parlamentar", fake_processos)

    result = runner.invoke(
        app,
        ["collect", "senado-lote", "--limit", "2", "--db-path", str(db_path)],
    )

    assert result.exit_code == 0
    assert "falhas registradas: 1" in result.stdout
    assert LocalDatabase(db_path).summary()["propositions"] == 1
    assert LocalDatabase(db_path).coverage()["senado_profiles"] == 2


def test_collect_camara_proposicoes_full_lote_writes_details(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "painel.db"
    db = LocalDatabase(db_path)
    db.init()
    db.upsert_propositions(
        [
            ProposicaoResumo(
                source="camara",
                external_id="2626629",
                casa="camara",
                sigla="PL",
            )
        ]
    )

    monkeypatch.setattr(
        "legislativo_backend.cli.get_proposicao_detail",
        lambda proposicao_id: {"dados": {"id": proposicao_id, "statusProposicao": {}}},
    )
    monkeypatch.setattr(
        "legislativo_backend.cli.list_proposicao_autores",
        lambda proposicao_id: {"dados": [{"nome": "Autor"}]},
    )
    monkeypatch.setattr(
        "legislativo_backend.cli.list_proposicao_temas",
        lambda proposicao_id: {"dados": [{"tema": "Saúde"}]},
    )
    monkeypatch.setattr(
        "legislativo_backend.cli.list_proposicao_tramitacoes",
        lambda proposicao_id: {"dados": [{"despacho": "Aguardando despacho"}]},
    )

    result = runner.invoke(
        app,
        [
            "collect",
            "camara-proposicoes-full-lote",
            "--limit",
            "1",
            "--db-path",
            str(db_path),
        ],
    )

    assert result.exit_code == 0
    assert "proposicoes camara detalhadas: 1" in result.stdout
    assert LocalDatabase(db_path).summary()["raw_payloads"] == 1


def test_collect_senado_processos_full_lote_writes_details(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "painel.db"
    db = LocalDatabase(db_path)
    db.init()
    db.upsert_propositions(
        [
            ProposicaoResumo(
                source="senado_processo",
                external_id="8360649",
                casa="senado",
                sigla="RQS",
            )
        ]
    )

    monkeypatch.setattr(
        "legislativo_backend.cli.get_processo_detail",
        lambda processo_id: {"id": processo_id, "autores": [], "situacaoAtual": "APROVADA"},
    )

    result = runner.invoke(
        app,
        [
            "collect",
            "senado-processos-full-lote",
            "--limit",
            "1",
            "--db-path",
            str(db_path),
        ],
    )

    assert result.exit_code == 0
    assert "processos senado detalhados: 1" in result.stdout
    assert LocalDatabase(db_path).summary()["raw_payloads"] == 1


def test_import_camara_ceap_zip_writes_archive_expenses(tmp_path: Path):
    db_path = tmp_path / "painel.db"
    zip_path = tmp_path / "Ano-2024.csv.zip"
    csv_content = (
        "txNomeParlamentar;nuDeputadoId;numAno;numMes;txtDescricao;txtFornecedor;"
        "txtNumero;datEmissao;vlrDocumento;vlrLiquido;ideDocumento\n"
        "Deputada Teste;204379;2024;2;COMBUSTÍVEIS;POSTO TESTE;NF-1;"
        "2024-02-03T00:00:00;500;450;7696122\n"
    )
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("Ano-2024.csv", csv_content)

    result = runner.invoke(
        app,
        [
            "import",
            "camara-ceap-zip",
            "--zip-path",
            str(zip_path),
            "--db-path",
            str(db_path),
            "--batch-size",
            "1",
        ],
    )

    assert result.exit_code == 0
    assert "despesas importadas: 1" in result.stdout
    assert LocalDatabase(db_path).summary()["expenses"] == 1


def test_collect_camara_proposicoes_ano_writes_paginated_rows(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "painel.db"

    def fake_list_proposicoes_by_year(ano, limit=100, page=1):
        if page == 1:
            return {
                "dados": [
                    {
                        "id": 2630369,
                        "siglaTipo": "INC",
                        "numero": 924,
                        "ano": ano,
                        "ementa": "Sugere medidas.",
                    }
                ]
            }
        return {"dados": []}

    monkeypatch.setattr(
        "legislativo_backend.cli.list_proposicoes_by_year",
        fake_list_proposicoes_by_year,
    )

    result = runner.invoke(
        app,
        [
            "collect",
            "camara-proposicoes-ano",
            "--ano",
            "2026",
            "--max-pages",
            "2",
            "--db-path",
            str(db_path),
        ],
    )

    assert result.exit_code == 0
    assert "proposicoes camara gravadas: 1" in result.stdout
    assert LocalDatabase(db_path).summary()["propositions"] == 1
