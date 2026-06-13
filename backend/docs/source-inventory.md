# Inventario Inicial de Fontes

Data da descoberta: 2026-06-08.

## Camara dos Deputados

Fonte principal:
- API REST: `https://dadosabertos.camara.leg.br/api/v2`
- OpenAPI: `https://dadosabertos.camara.leg.br/api/v2/api-docs`
- Arquivos completos: `https://dadosabertos.camara.leg.br/swagger/api.html`

Cobertura confirmada:
- OpenAPI com 78 caminhos.
- Deputados atuais: `/deputados`.
- Perfil expandido: `/deputados/{id}`.
- Despesas CEAP por deputado: `/deputados/{id}/despesas`.
- Proposicoes por deputado: `/proposicoes?idDeputadoAutor={id}`.
- Proposicao expandida: `/proposicoes/{id}`.
- Autores: `/proposicoes/{id}/autores`.
- Temas: `/proposicoes/{id}/temas`.
- Tramitacoes: `/proposicoes/{id}/tramitacoes`.
- Votacoes: `/votacoes`, `/votacoes/{id}`, `/votacoes/{id}/votos`.
- Comissoes/orgaos: `/deputados/{id}/orgaos`, `/orgaos`, `/orgaos/{id}/membros`.
- Frentes: `/deputados/{id}/frentes`, `/frentes`, `/frentes/{id}/membros`.
- Referencias: temas, tipos, situacoes, UFs, tipos de despesa.

Arquivos completos relevantes:
- Despesas CEAP por ano desde 2008: `https://www.camara.leg.br/cotas/Ano-{ano}.csv.zip`.
- Testados `Ano-2024.csv.zip`, `Ano-2025.csv.zip` e `Ano-2026.csv.zip`: HTTP 200 em 2026-06-08.
- `Ano-2024.csv.zip`: 7.2 MB zip, CSV com 232.259 linhas processadas.
- `Ano-2025.csv.zip`: 6.6 MB zip, 208.333 linhas importadas.
- `Ano-2026.csv.zip`: 2.3 MB zip, 59.221 linhas importadas.
- A pagina de arquivos tambem lista bases de votacoes, deputados, orgaos, frentes, partidos, servidores, historico e outras tabelas.

Descobertas em amostra:
- Deputado `204379`: perfil com 13 campos principais.
- Deputado `204379`: 5 orgaos atuais na amostra consultada.
- Deputado `204379`: 208 frentes retornadas.
- Proposicao `2626629`: 21 campos de detalhe, 1 autor, 2 temas, 1 tramitacao.

Descobertas em carga local:
- Deputados ativos enriquecidos: 512/512.
- Proposicoes 2026 por ano: 14.255 registros lidos em 143 paginas.
- Proposicoes 2025 por ano: 48.386 registros lidos em 484 paginas.
- CEAP 2024-2026 importada para SQLite local, com categoria, fornecedor, CNPJ/CPF, documento, URL oficial, glosa, valor liquido, passageiro e trecho quando houver.

Observacoes:
- Para busca por tema, o caminho mais confiavel tende a ser `codTema` + enriquecimento por `/temas`.
- `keywords` existe na API, mas precisa validacao por formato/recorte porque a primeira consulta com termo livre nao retornou dados.

## Senado Federal - Legislativo

Fonte principal:
- OpenAPI: `https://legis.senado.leg.br/dadosabertos/v3/api-docs`
- Swagger: `https://legis.senado.leg.br/dadosabertos/api-docs/swagger-ui/index.html`

Cobertura confirmada:
- OpenAPI com 157 caminhos.
- Senadores em exercicio: `/dadosabertos/senador/lista/atual`.
- Senador expandido: `/dadosabertos/senador/{codigo}`.
- Autorias legado: `/dadosabertos/senador/{codigo}/autorias`.
- Comissoes do senador: `/dadosabertos/senador/{codigo}/comissoes`.
- Discursos, cargos, filiacoes, licencas, liderancas, mandatos e profissao por senador.
- Materias: detalhes, movimentacoes, textos, votacoes, relatorias, situacao atual.
- Processo novo: `/dadosabertos/processo` e `/dadosabertos/processo/{id}`.

Descobertas em amostra:
- Senador `5672` via lista atual normalizou como Alan Rick.
- `/senador/5672/autorias` funcionou, mas o payload informa depreciação e substituto `/processo`.
- `/processo?codigoParlamentarAutor=5672&v=1` retornou 373 processos.
- `/processo?termo=seguranca publica&dataInicioApresentacao=2025-01-01&dataFimApresentacao=2025-12-31&v=1` retornou 171 processos.
- `/processo/{id}` retorna autores estruturados, documento, conteudo, situacao, deliberacao e outros detalhes.

Descobertas em carga local:
- Senadores ativos enriquecidos: 81/81.
- Processos por senador coletados em lote para todos os senadores ativos, com limite inicial de 50 por senador.
- 50 processos detalhados via `/processo/{id}` confirmaram campos para leitura de tramitacao: `situacaoAtual`, `tramitando`, `deliberacao`, `despachos`, `ordensDoDia`, `normaGerada`, `processosRelacionados`, `documento`, `conteudo` e `autoriaIniciativa`.

Observacoes:
- Para produção, preferir `/processo` em vez de `/senador/{codigo}/autorias`.
- O campo `identificacao` precisa parsing para extrair sigla, numero e ano quando a lista nao traz campos separados.

## Senado Federal - Administrativo

Fonte principal:
- OpenAPI: `https://adm.senado.gov.br/adm-dadosabertos/v3/api-docs`
- Swagger: `https://adm.senado.gov.br/adm-dadosabertos/swagger-ui`

Cobertura confirmada:
- OpenAPI com 81 caminhos.
- CEAPS por ano: `/api/v1/senadores/despesas_ceaps/{ano}` e `/csv`.
- Escritorios: `/api/v1/senadores/escritorios`.
- Auxilio moradia: `/api/v1/senadores/auxilio-moradia`.
- Aposentados e quantitativos.
- Contratacoes, licitacoes, contratos, empresas, notas de empenho, pagamentos.

Descobertas em amostra:
- CEAPS 2024 retornou lista direta com campos: id, tipoDocumento, ano, mes, codSenador, nomeSenador, tipoDespesa, cpfCnpj, fornecedor, documento, data, detalhamento, valorReembolsado.

Descobertas em carga local:
- CEAPS 2024: 20.000 registros carregados na primeira janela.
- CEAPS 2025: 23.600 registros carregados apos elevar limite de coleta.
- CEAPS 2026: 7.197 registros carregados ate 2026-06-08.

## Cobertura SQLite local em 2026-06-08

- Parlamentares: 593.
- Proposicoes/materias normalizadas: 68.318.
- Despesas normalizadas: 512.038.
- Payloads brutos: 2.435.
- Execucoes registradas: 105.
- Tamanho do banco local apos cargas: aproximadamente 200 MB.

## Portal da Transparencia / CGU

Fonte:
- Catalogo gov.br: `https://www.gov.br/conecta/catalogo/apis/portal-da-transparencia-do-governo-federal`
- Swagger: `https://api.portaldatransparencia.gov.br/swagger-ui/index.html`

Status:
- Requer chave de API.
- Deve entrar depois das fontes legislativas basicas.
- Provavelmente mais util para emendas parlamentares, despesas federais executadas, convenios, contratos e transferencias do que para CEAP/CEAPS.

## Scraping HTML

Status:
- Mantido como fallback.
- Usar apenas quando API/CSV oficial nao entregar o dado ou quando a pagina publica tiver leitura enriquecida que nao aparece nos endpoints.
- Antes de scraping, verificar se ha JSON embutido, endpoint usado pela pagina ou arquivo de download oficial.

## Candidatos a tabelas Supabase

- `source_runs`
- `source_snapshots`
- `parlamentarians`
- `parliamentarian_terms`
- `parliamentarian_contacts`
- `parliamentarian_memberships`
- `parliamentarian_fronts`
- `propositions`
- `proposition_authors`
- `proposition_themes`
- `proposition_movements`
- `expenses`
- `expense_suppliers`
- `votes`
- `vote_items`
- `raw_payloads`

## Proxima investigacao

- Validar paginação e limites reais dos endpoints grandes.
- Baixar e ler um ZIP anual CEAP da Camara com streaming, sem carregar tudo em memoria.
- Validar CSV da CEAPS Senado versus JSON.
- Testar Portal da Transparencia com chave.
- Definir quais dados entram como colunas normalizadas e quais ficam em `raw_payloads`.
