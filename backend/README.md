# Painel do Legislativo Backend

Backend de coleta para descobrir fontes oficiais, normalizar dados e futuramente gravar snapshots no Supabase.

## Stack

- Python 3.12
- uv
- httpx
- pydantic
- tenacity
- typer
- pytest
- ruff

## Comandos

Instalar dependencias:

```bash
uv sync
```

Rodar testes:

```bash
uv run pytest
```

Coletar amostras oficiais:

```bash
uv run legislativo discover camara-deputados --limit 5
uv run legislativo discover camara-deputado-full --deputado-id 204379
uv run legislativo discover camara-despesas --deputado-id 204379 --ano 2024 --limit 5
uv run legislativo discover camara-proposicoes --deputado-id 204379 --limit 5
uv run legislativo discover camara-proposicao-full --proposicao-id 2626629
uv run legislativo discover senado-senadores --limit 5
uv run legislativo discover senado-comissoes --senador-codigo 5672
uv run legislativo discover senado-autorias --senador-codigo 5672 --limit 5
uv run legislativo discover senado-processos --senador-codigo 5672 --limit 5
uv run legislativo discover senado-processos --termo "seguranca publica" --data-inicio 2025-01-01 --data-fim 2025-12-31 --limit 5
uv run legislativo discover senado-processo-full --processo-id 8360649
uv run legislativo discover senado-ceaps --ano 2024 --limit 5
```

Os snapshots brutos ficam em `data/raw/` e nao entram no git.

## Banco local e coleta incremental

Inicializar e ver resumo:

```bash
uv run legislativo db init
uv run legislativo db summary
uv run legislativo db coverage
```

Carregar a base atual de parlamentares ativos:

```bash
uv run legislativo collect parlamentares-full
```

Rodar enriquecimento aos poucos. Use os offsets indicados por `db coverage`:

```bash
uv run legislativo collect camara-lote --limit 5 --offset 0 --ano-despesas 2024 --proposicoes-limit 20 --despesas-limit 20
uv run legislativo collect senado-lote --limit 5 --offset 0 --processos-limit 50
uv run legislativo db coverage
```

O banco local fica em `data/local/painel.db` e nao entra no git. A ideia e usar
esse SQLite para validar schema, volume e qualidade antes de espelhar o desenho
no Supabase.

Cobertura local atual apos as primeiras rodadas:

- 593 parlamentares ativos vindos das fontes oficiais: 512 deputados e 81 senadores.
- 10 deputados enriquecidos com perfil, orgaos, frentes, proposicoes e despesas.
- 10 senadores enriquecidos com comissoes e processos legislativos.
- 595 proposicoes/materias normalizadas.
- 202 despesas normalizadas.

## Decisao atual

O Next.js deve ler snapshots persistidos no Supabase. Este backend deve rodar periodicamente, coletar dados oficiais, normalizar e fazer upsert. Scraping HTML continua como fallback quando uma fonte relevante nao tiver API/CSV confiavel.

Observacao: o endpoint legislativo do Senado `/senador/{codigo}/autorias` respondeu na descoberta, mas o payload informa depreciação e aponta `/processo` como substituto. Antes de produção, validar o endpoint novo para autorias/matérias.
