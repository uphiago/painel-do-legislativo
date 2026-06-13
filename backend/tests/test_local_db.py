from pathlib import Path

from legislativo_backend.db import LocalDatabase
from legislativo_backend.normalizers import DespesaResumo, ParlamentarResumo, ProposicaoResumo


def test_init_creates_empty_summary(tmp_path: Path):
    db = LocalDatabase(tmp_path / "painel.db")
    db.init()

    summary = db.summary()
    assert summary["parlamentarians"] == 0
    assert summary["propositions"] == 0
    assert summary["expenses"] == 0
    assert summary["raw_payloads"] == 0
    assert summary["sync_runs"] == 0
    assert summary["parties"] == 0
    assert summary["legislatures"] == 0
    assert summary["organs"] == 0
    assert summary["organ_memberships"] == 0
    assert summary["proposition_types"] == 0


def test_upsert_parlamentarians_is_idempotent(tmp_path: Path):
    db = LocalDatabase(tmp_path / "painel.db")
    db.init()
    parlamentar = ParlamentarResumo(
        source="camara",
        external_id="204379",
        nome="Acácio Favacho",
        casa="camara",
        partido="MDB",
        uf="AP",
        email="dep.acaciofavacho@camara.leg.br",
        foto_url="https://example.com/foto.jpg",
    )

    db.upsert_parlamentarians([parlamentar])
    db.upsert_parlamentarians([parlamentar])

    assert db.summary()["parlamentarians"] == 1


def test_list_parliamentarians_filters_by_source_with_limit_and_offset(tmp_path: Path):
    db = LocalDatabase(tmp_path / "painel.db")
    db.init()
    db.upsert_parlamentarians(
        [
            ParlamentarResumo(
                source="camara",
                external_id="1",
                nome="Deputado A",
                casa="camara",
            ),
            ParlamentarResumo(
                source="camara",
                external_id="2",
                nome="Deputado B",
                casa="camara",
            ),
            ParlamentarResumo(
                source="senado",
                external_id="3",
                nome="Senador C",
                casa="senado",
            ),
        ]
    )

    rows = db.list_parliamentarians(source="camara", limit=1, offset=1)

    assert rows == [{"external_id": "2", "name": "Deputado B"}]


def test_list_propositions_filters_by_source_with_limit_and_offset(tmp_path: Path):
    db = LocalDatabase(tmp_path / "painel.db")
    db.init()
    db.upsert_propositions(
        [
            ProposicaoResumo(source="camara", external_id="10", casa="camara", sigla="PL"),
            ProposicaoResumo(source="camara", external_id="11", casa="camara", sigla="REQ"),
            ProposicaoResumo(source="senado_processo", external_id="12", casa="senado", sigla="RQS"),
        ]
    )

    rows = db.list_propositions(source="camara", limit=1, offset=1)

    assert rows == [{"external_id": "11", "sigla": "REQ", "numero": None, "ano": None}]


def test_upsert_core_entities_and_raw_payloads(tmp_path: Path):
    db = LocalDatabase(tmp_path / "painel.db")
    db.init()

    db.upsert_propositions(
        [
            ProposicaoResumo(
                source="senado_processo",
                external_id="8784312",
                casa="senado",
                sigla="PDL",
                numero="29",
                ano=2025,
                ementa="Susta decreto.",
                data_apresentacao="2025-01-07",
            )
        ]
    )
    db.upsert_expenses(
        [
            DespesaResumo(
                source="senado_ceaps",
                external_id="2229299",
                parlamentar_external_id="5672",
                parlamentar_nome="ALAN RICK",
                ano=2024,
                mes=4,
                categoria="Passagens aéreas",
                fornecedor="AEROTUR SERVIÇOS",
                documento="2154385247",
                data="2024-04-26",
                valor=1030.22,
            )
        ]
    )
    db.upsert_raw_payload(
        source="senado",
        kind="processo",
        external_id="8784312",
        payload={"id": 8784312, "identificacao": "PDL 29/2025"},
    )

    assert db.summary()["propositions"] == 1
    assert db.summary()["expenses"] == 1
    assert db.summary()["raw_payloads"] == 1


def test_coverage_counts_enriched_profiles_by_raw_payload_kind(tmp_path: Path):
    db = LocalDatabase(tmp_path / "painel.db")
    db.init()
    db.upsert_parlamentarians(
        [
            ParlamentarResumo(source="camara", external_id="1", nome="Deputado A", casa="camara"),
            ParlamentarResumo(source="camara", external_id="2", nome="Deputado B", casa="camara"),
            ParlamentarResumo(source="senado", external_id="3", nome="Senador C", casa="senado"),
        ]
    )
    db.upsert_raw_payload(source="camara", kind="deputado-perfil", external_id="1", payload={})
    db.upsert_raw_payload(source="senado", kind="senador-processos", external_id="3", payload=[])

    coverage = db.coverage()

    assert coverage["camara_parlamentarians"] == 2
    assert coverage["senado_parliamentarians"] == 1
    assert coverage["camara_profiles"] == 1
    assert coverage["senado_profiles"] == 1
