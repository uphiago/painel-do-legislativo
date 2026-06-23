from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field


def ensure_list(value: Any) -> list:
    """Normaliza um campo que a API ora retorna como dict, ora como lista.

    As APIs do Senado (e algumas da Camara) retornam um unico item como dict
    e multiplos itens como lista. Esta funcao garante sempre uma lista.
    """
    if value is None:
        return []
    if isinstance(value, dict):
        return [value]
    return value if isinstance(value, list) else []


class ParlamentarResumo(BaseModel):
    source: str
    external_id: str
    nome: str
    casa: str
    partido: str | None = None
    uf: str | None = None
    email: str | None = None
    foto_url: str | None = None


class DespesaResumo(BaseModel):
    source: str
    external_id: str
    parlamentar_external_id: str | None = None
    parlamentar_nome: str | None = None
    ano: int | None = None
    mes: int | None = None
    categoria: str | None = None
    fornecedor: str | None = None
    documento: str | None = None
    data: str | None = None
    valor: float = Field(default=0)


class ProposicaoResumo(BaseModel):
    source: str
    external_id: str
    casa: str
    sigla: str | None = None
    numero: str | None = None
    ano: int | None = None
    ementa: str | None = None
    data_apresentacao: str | None = None
    autor_principal: bool | None = None


def normalize_camara_deputado(item: dict[str, Any]) -> ParlamentarResumo:
    return ParlamentarResumo(
        source="camara",
        external_id=str(item["id"]),
        nome=item["nome"],
        casa="camara",
        partido=item.get("siglaPartido"),
        uf=item.get("siglaUf"),
        email=item.get("email"),
        foto_url=item.get("urlFoto"),
    )


def normalize_senado_senador(item: dict[str, Any]) -> ParlamentarResumo:
    identificacao = item["IdentificacaoParlamentar"]
    return ParlamentarResumo(
        source="senado",
        external_id=str(identificacao["CodigoParlamentar"]),
        nome=identificacao["NomeParlamentar"],
        casa="senado",
        partido=identificacao.get("SiglaPartidoParlamentar"),
        uf=identificacao.get("UfParlamentar"),
        email=identificacao.get("EmailParlamentar"),
        foto_url=identificacao.get("UrlFotoParlamentar"),
    )


def normalize_senado_ceaps(item: dict[str, Any]) -> DespesaResumo:
    return DespesaResumo(
        source="senado",
        external_id=str(item["id"]),
        parlamentar_external_id=str(item.get("codSenador")) if item.get("codSenador") else None,
        parlamentar_nome=item.get("nomeSenador"),
        ano=item.get("ano"),
        mes=item.get("mes"),
        categoria=item.get("tipoDespesa"),
        fornecedor=item.get("fornecedor"),
        documento=item.get("documento"),
        data=item.get("data"),
        valor=float(item.get("valorReembolsado") or 0),
    )


def normalize_camara_despesa(item: dict[str, Any], deputado_id: int) -> DespesaResumo:
    doc_id = item.get("codDocumento") or item.get("numDocumento")
    return DespesaResumo(
        source="camara_ceap",
        external_id=str(doc_id) if doc_id else f"{deputado_id}-{item.get('ano','')}-{item.get('mes','')}",
        parlamentar_external_id=str(deputado_id),
        ano=item.get("ano"),
        mes=item.get("mes"),
        categoria=item.get("tipoDespesa"),
        fornecedor=item.get("nomeFornecedor"),
        documento=item.get("numDocumento"),
        data=item.get("dataDocumento"),
        valor=float(item.get("valorLiquido") or item.get("valorDocumento") or 0),
    )


def normalize_camara_ceap_archive_row(item: dict[str, Any]) -> DespesaResumo:
    doc_id = item.get("ideDocumento") or item.get("txtNumero")
    externo = str(doc_id) if doc_id else ""
    if externo:
        dep = _blank_to_none(item.get("nuDeputadoId")) or "0"
        ano = str(_int_or_none(item.get("numAno")) or 0)
        mes = str(_int_or_none(item.get("numMes")) or 0)
        doc = _blank_to_none(item.get("txtNumero")) or "0"
        externo = f"ceap-{ano}-{mes}-{dep}-{doc}"
    return DespesaResumo(
        source="camara_ceap",
        external_id=externo,
        parlamentar_external_id=_blank_to_none(item.get("nuDeputadoId")),
        parlamentar_nome=_blank_to_none(item.get("txNomeParlamentar")),
        ano=_int_or_none(item.get("numAno")),
        mes=_int_or_none(item.get("numMes")),
        categoria=_blank_to_none(item.get("txtDescricao")),
        fornecedor=_blank_to_none(item.get("txtFornecedor")),
        documento=_blank_to_none(item.get("txtNumero")),
        data=_blank_to_none(item.get("datEmissao")),
        valor=_float_or_zero(item.get("vlrLiquido") or item.get("vlrDocumento")),
    )


def normalize_camara_proposicao(item: dict[str, Any]) -> ProposicaoResumo:
    return ProposicaoResumo(
        source="camara",
        external_id=str(item["id"]),
        casa="camara",
        sigla=item.get("siglaTipo"),
        numero=str(item.get("numero")) if item.get("numero") is not None else None,
        ano=item.get("ano"),
        ementa=item.get("ementa"),
        data_apresentacao=item.get("dataApresentacao"),
    )


def normalize_senado_autoria(item: dict[str, Any]) -> ProposicaoResumo:
    materia = item["Materia"]
    return ProposicaoResumo(
        source="senado",
        external_id=str(materia["Codigo"]),
        casa="senado",
        sigla=materia.get("Sigla"),
        numero=str(materia.get("Numero")) if materia.get("Numero") is not None else None,
        ano=int(materia["Ano"]) if materia.get("Ano") else None,
        ementa=materia.get("Ementa"),
        data_apresentacao=materia.get("Data"),
        autor_principal=item.get("IndicadorAutorPrincipal") == "Sim",
    )


def normalize_senado_processo(item: dict[str, Any]) -> ProposicaoResumo:
    sigla, numero, ano = _parts_from_identificacao(item.get("identificacao"))
    return ProposicaoResumo(
        source="senado_processo",
        external_id=str(item["id"]),
        casa="senado",
        sigla=item.get("sigla") or sigla,
        numero=str(item.get("numero")) if item.get("numero") is not None else numero,
        ano=item.get("ano") or ano,
        ementa=item.get("ementa") or item.get("conteudo", {}).get("ementa"),
        data_apresentacao=item.get("dataApresentacao")
        or item.get("documento", {}).get("dataApresentacao"),
    )


def _sigla_from_identificacao(identificacao: str | None) -> str | None:
    if not identificacao:
        return None
    return identificacao.split(" ", 1)[0] or None


def _parts_from_identificacao(identificacao: str | None) -> tuple[str | None, str | None, int | None]:
    if not identificacao:
        return None, None, None
    match = re.match(r"^(?P<sigla>[A-Z]+)\s+(?P<numero>[\w.-]+)\/(?P<ano>\d{4})", identificacao)
    if not match:
        return _sigla_from_identificacao(identificacao), None, None
    return match.group("sigla"), match.group("numero"), int(match.group("ano"))


def _blank_to_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _int_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _float_or_zero(value: Any) -> float:
    if value in (None, ""):
        return 0
    try:
        return float(str(value).replace(",", "."))
    except (ValueError, TypeError):
        return 0
