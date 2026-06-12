# analytis — Design

**Data:** 2026-06-12
**Status:** Aprovado para implementação
**Codinome:** analytis

---

## 1. Visão geral

Plataforma backend em Python que ingere dados de futebol de múltiplas fontes, mantém estado canônico em PostgreSQL, gera previsões probabilísticas calibradas para os mercados **1X2**, **Over/Under gols**, **BTTS** (ambas marcam) e **escanteios** em jogos pré-match, expõe os resultados via API REST e oferece CLI para operação.

### 1.1 Objetivo do usuário

Apostas próprias para estudo e análise, sem pressão de retorno lucrativo. O sistema serve como ferramenta de aprendizado e análise séria, não como máquina de gerar dinheiro. Isso libera o projeto da pressão de "bater o mercado" (Pinnacle/Bet365) e permite focar em construir algo correto, didático e evolutivo.

### 1.2 Escopo

- **Plataforma multi-competição** desde o início. Copa do Mundo 2026 é o primeiro caso de uso; ligas (Brasileirão, Premier League, etc.) entram em sequência.
- **Mercados cobertos na v1:** 1X2, Over/Under gols (linha padrão 2.5, com suporte a outras), BTTS, escanteios (total + handicap derivado).
- **Pré-jogo apenas.** Modelo gera previsões até 1h antes do jogo. In-play (ao vivo) fica como projeto futuro (v2), não está coberto aqui.
- **Backend puro.** Sem frontend nesta entrega. API REST é a porta de saída para consumo futuro.
- **Roda local.** Postgres + serviço Python no Windows do usuário. Sem cloud, sem distribuição.

### 1.3 Filosofia de entrega

Construir direito desde o começo (~6-8 semanas part-time). Sem MVP correndo durante a Copa 2026. A copa que está acontecendo agora (11/06–19/07/2026) é tratada como **dataset de validação** — não como prazo. Modelos amassados em 7 dias entregariam previsões piores que copiar as odds da Bet365, o que sabotaria o aprendizado real.

---

## 2. Princípios não-funcionais

Estes princípios são vinculantes — qualquer decisão de design subsequente deve ser compatível com eles.

1. **Solidez probabilística** — toda previsão sai com (a) probabilidade pontual, (b) intervalo de credibilidade (95% por padrão), (c) versão do modelo que gerou, (d) hash do conjunto de features usado. Sem chutão. Sem `prob = 0.75` solto.
2. **Calibração antes de acerto** — uma probabilidade reportada de 70% deve acertar ~70% das vezes no longo prazo. Calibração é métrica de primeira classe (Brier, log-loss, reliability diagrams).
3. **Reprodutibilidade total** — qualquer previsão histórica pode ser regenerada exatamente, dado o snapshot de features daquele momento. Sem isso não há backtest válido.
4. **Auditável** — para cada previsão armazenada o sistema responde: quais features entraram, qual modelo gerou, com que peso de ensemble, quanto tempo antes do jogo, sob qual versão do código.
5. **Fontes pluggable** — adicionar uma API paga depois (Fase 1, 2, 3) é trocar ou adicionar adapter, não reescrever pipeline.
6. **Sem premature distribution** — monolito local modular, simples, focado. Sem microserviços, sem Kubernetes, sem Airflow nesta versão.

---

## 3. Arquitetura de alto nível

Monolito modular em sete camadas. Comunicação entre camadas por **interfaces explícitas** (Protocols / classes abstratas). Camada superior conhece apenas a interface da inferior, nunca os detalhes de implementação.

```
                      ┌────────────────────────────────────────┐
                      │ CLI (Typer)         API REST (FastAPI) │
                      └──────────────┬─────────────┬───────────┘
                                     │             │
                       ┌─────────────▼─────────────▼────────┐
                       │     Serviço de Aplicação           │
                       │  (orquestra casos de uso, sem regra)│
                       └─┬───────────────┬───────────────┬───┘
                         │               │               │
                ┌────────▼──┐   ┌────────▼─────┐  ┌──────▼──────┐
                │ Ingestão  │   │  Modelagem   │  │  Scoring &  │
                │ (adapters)│   │  (DC + XGB + │  │  Predições  │
                │           │   │  Bayes calib)│  │             │
                └────┬──────┘   └────┬─────────┘  └──────┬──────┘
                     │                │                  │
                ┌────▼────────────────▼──────────────────▼────┐
                │            Engenharia de Features            │
                │  (ELO, médias móveis, xG ajustado, descanso) │
                └───────────────────────┬──────────────────────┘
                                        │
                       ┌────────────────▼─────────────────┐
                       │   Persistência (PostgreSQL)      │
                       │   — verdade canônica imutável    │
                       └──────────────────────────────────┘
```

O **serviço de aplicação** é fino — orquestra casos de uso ("ingerir fixtures da próxima semana", "treinar modelo X", "fazer scoring do jogo Y"). Regra de negócio mora em ingestão, features, modelagem e scoring.

---

## 4. Modelo de domínio e persistência

PostgreSQL como verdade canônica. Quatro famílias de tabelas.

### 4.1 Catálogo (referencial, raramente muda)

- `competition` — Copa do Mundo 2026, Brasileirão 2026, Premier League 25/26. Coluna `competition_type` ∈ {selecao, clube} muda decisões de modelagem downstream.
- `season` — uma temporada por competição.
- `team` — atributos básicos, `team_type` ∈ {selecao, clube}.
- `player` — atributos básicos + posição preferida.
- `venue` — estádio, cidade, país, altitude, capacidade.
- `referee` — árbitro com estatísticas agregadas (cartões/jogo, pênaltis/jogo).

### 4.2 Eventos factuais (imutáveis após o jogo terminar)

- `match` — chave canônica do sistema. Campos: mandante, visitante, data/hora UTC, venue, referee, status ∈ {scheduled, live, finished, postponed}, gols finais, escanteios finais, métricas de jogo. Coluna `is_home_neutral` para jogos em sede neutra (ex.: Copa do Mundo).
- `match_lineup` — escalações por jogo (titular + reservas).
- `match_event` *(opcional Fase 0)* — gols, cartões, substituições com timestamp, quando a fonte fornecer.

### 4.3 Inferência (mutáveis, versionadas)

- `feature_snapshot` — JSONB com vetor completo de features usado num scoring específico, identificado por `(match_id, snapshot_taken_at)`. **Imutável após gravado.**
- `model_version` — registro de cada versão treinada: hash do código (git SHA + diff), hyperparams, lista de match_ids do treino, métricas de validação.
- `prediction` — uma linha por (match × mercado × modelo × snapshot). Inclui probabilidade pontual, intervalo de credibilidade, peso de ensemble. **Imutável.**

### 4.4 Ingestão (rastreabilidade)

- `data_source` — FBref, Football-Data.org, OpenLigaDB, etc.
- `ingestion_run` — quando rodou, o que pegou, sucesso/erro, hash dos dados recebidos.

### 4.5 Convenções de schema

- IDs internos são UUIDs (independentes de IDs de fontes externas).
- Cada entidade externa tem coluna `external_ids JSONB` mapeando ID por fonte: `{"fbref": "abc", "footballdata": 123}`.
- Toda tabela tem `created_at` e `updated_at` (trigger).
- `prediction` e `feature_snapshot` **nunca recebem UPDATE** — apenas INSERT. Reprodutibilidade é inegociável.
- Migrations via **Alembic**.

### 4.6 Ferramentas de acesso

- **SQLAlchemy 2.x** (ORM tipado).
- **Pydantic 2** para schemas de transporte (DTOs).
- **Pattern Repository** por agregado (`MatchRepository`, `PredictionRepository`) — esconde ORM do resto do código, facilita testes, deixa porta aberta para troca de engine se necessário.

---

## 5. Camada de ingestão

### 5.1 Padrão arquitetural

Padrão **Adapter + Repositório**. Cada fonte externa é um adapter que implementa uma interface comum (`DataSourceAdapter`). O resto do sistema nunca importa código de adapter — conhece apenas a interface.

```python
class DataSourceAdapter(Protocol):
    source_id: str  # "fbref", "footballdata", "openligadb"

    def fetch_competitions(self) -> list[CompetitionDTO]: ...
    def fetch_matches(self, competition_id: str, season: str) -> list[MatchDTO]: ...
    def fetch_match_stats(self, external_match_id: str) -> MatchStatsDTO: ...
    def fetch_lineups(self, external_match_id: str) -> LineupDTO | None: ...
```

DTOs são **canônicos do domínio**, não espelhos do JSON da fonte. O "ruído" de cada API morre na fronteira do adapter.

### 5.2 Fontes da Fase 0 (gratuitas)

| Fonte | O que entrega | Acesso | Risco |
|---|---|---|---|
| **Football-Data.org** | Fixtures, resultados, escalações básicas de ligas top + Copa | API REST oficial, free 10 req/min | Baixo |
| **FBref (StatsBomb-powered)** | Estatísticas históricas profundas (xG, passes, escanteios) | Scraping educado: cache 24h+, robots.txt, 1 req / 6s | Médio — ToS cinza, frágil |
| **OpenLigaDB** | Resultados de ligas alemãs como dataset extra | API REST aberta | Baixo |
| **Wikipedia / Wikidata** | Venues, árbitros, contexto histórico | API estável | Baixo |
| **ELO (eloratings.net)** | ELO mundial de seleções, dataset baixável | Download CSV periódico | Baixo |

**Decisão consciente sobre FBref:** ponto fraco do sistema (scraping). Mitigação: cache local de 24h+, circuit breaker se ficar instável, **fallback gracioso** — se FBref morrer, o modelo perde xG mas continua com Poisson sobre gols brutos.

### 5.3 Orquestração

**APScheduler embarcado** no processo Python — não há complexidade que justifique Airflow ou Prefect.

Jobs típicos:

- `ingest:fixtures` — diário, 06:00 local — baixa próximos 14 dias de jogos.
- `ingest:results` — a cada 30min entre 12:00–23:59 local — atualiza jogos do dia.
- `ingest:historical-backfill` — manual via CLI, paginado, retomável.
- `ingest:lineups` — disparos em T-4h, T-2h, T-1h antes de cada jogo agendado.

Cada execução grava em `ingestion_run` (start/end, registros tocados, erro). Observabilidade básica sem stack de monitoramento.

### 5.4 Idempotência

Toda ingestão é **idempotente** — rodar duas vezes não duplica. Implementação via `INSERT ... ON CONFLICT DO UPDATE` usando chave canônica + `external_ids JSONB`.

### 5.5 Rate limiting e erros

- Token bucket por fonte, encapsulado no adapter.
- Erros transitórios → retry exponencial com jitter (3 tentativas).
- Erros permanentes → log estruturado + `ingestion_run.status = 'failed'`; próxima execução tenta de novo.

### 5.6 Backfill histórico

CLI dedicada: `analytis ingest backfill --competition wc-2026 --since 2018-01-01`. Retomável via checkpoint a cada lote. Essencial para ter dataset robusto de treino/validação.

---

## 6. Engenharia de features

### 6.1 Filosofia

Features são **funções puras** sobre o estado canônico do banco num dado `as_of`. Toda função aceita `match_id + as_of` e retorna valor. **Nada lê o "agora"; tudo lê o passado relativo ao instante de scoring.** Isso garante reprodutibilidade e elimina **temporal leakage** (vazamento de informação futura no treino, que destrói modelos preditivos silenciosamente).

```python
def feature_team_elo(team_id: UUID, as_of: datetime) -> float: ...
def feature_team_form_last_5(team_id: UUID, as_of: datetime) -> dict: ...
def feature_h2h_corners_avg(home_id: UUID, away_id: UUID, as_of: datetime) -> float: ...
```

### 6.2 Catálogo de features (v1)

**Força base do time**
- `elo_world` — ELO mundial via fórmula World Football Elo (K-factor variável por tipo de jogo).
- `elo_competition` — ELO interno por competição (zera por temporada em ligas; cumulativo em copas).
- `attack_strength`, `defense_strength` — médias bayesianas de gols feitos/sofridos com prior global da competição (shrinkage para times com pouca amostra).

**Forma recente (janelas móveis)**
- Últimos 5 e 10 jogos: gols feitos, gols sofridos, xG criado, xG sofrido, escanteios feitos, escanteios sofridos.
- Pesos exponenciais (jogos mais recentes pesam mais); parâmetro de decaimento aprendido.

**Contexto do jogo**
- `home_advantage` — magnitude estimada por competição (0 em Copa do Mundo neutra; ~0.3 gol em Brasileirão).
- `rest_days` — dias desde último jogo, para cada time.
- `travel_km` — distância da cidade do último jogo até o venue atual (proxy de cansaço).
- `is_derby` — flag derivada de tabela manual + heurística.
- `competition_stage` — fase de grupos / oitavas / quartas / final (jogos eliminatórios têm padrão distinto).

**H2H (histórico direto)**
- Últimos N confrontos: vitórias mandante, gols totais, escanteios totais.
- Decaimento exponencial por tempo.

**Escalação e disponibilidade**
- `lineup_strength` — soma de "ratings" individuais dos titulares (Fase 0: heurística baseada em minutos jogados; futuro: rating SofaScore via fonte paga).
- `key_players_missing` — booleano por categoria (goleiro titular, principal artilheiro, capitão).
- `injuries_recent_text` — texto livre extraído por LLM (ver §9).

**Específicas de escanteios**
- `corners_for_per_90`, `corners_against_per_90` — médias móveis com decaimento.
- `corners_style_aggressive` — proporção de finalizações que viram escanteios (proxy de estilo ofensivo).

### 6.3 Engenharia opinionada

- **Ajuste por adversário** — médias ofensivas/defensivas são divididas pela força do adversário (xG ajustado por oponente). Padrão na literatura de modelagem esportiva.
- **Shrinkage bayesiano** — times com pouca amostra (estreantes em copa do mundo) misturam observação com prior da competição.
- **Diferenças, não absolutos** — o modelo recebe `home_attack - away_defense`, não os dois valores separados; força aprender o que importa.

### 6.4 Snapshots

A cada scoring, o vetor completo de features vai para `feature_snapshot` (JSONB) com timestamp. Isso permite:

- Auditar exatamente o que o modelo viu.
- Re-treinar com mesmo input no futuro.
- Debugar previsões esquisitas ("por que ele deu 80% para o Brasil contra a Croácia?").

### 6.5 Cache de features

Camada de cache (Redis embarcado ou DuckDB local — decisão na implementação) memoiza features históricas custosas (ELO recalculado, médias longas) por `(feature_name, params, as_of)`. **Cache é invalidado por `as_of`**, então leak temporal é impossível por construção.

---

## 7. Núcleo de modelagem

### 7.1 Visão geral

Três modelos especializados + uma camada de calibração + um agregador de ensemble.

```
                    ┌──────────────────────────────┐
                    │  Vetor de features (snapshot) │
                    └──────┬─────────┬──────────────┘
                           │         │
              ┌────────────▼┐       ┌▼─────────────┐
              │ Dixon-Coles  │       │   XGBoost    │
              │ (modelo de   │       │  classificador│
              │  gols)       │       │  + regressor │
              └────────────┬─┘       └┬─────────────┘
                           │           │
                           └──┬────────┘
                              │
                  ┌───────────▼──────────────┐
                  │ Ensemble (stacking +     │
                  │ isotonic per market)     │
                  └───────────┬──────────────┘
                              │
                  ┌───────────▼────────────────┐
                  │ Camada bayesiana (PyMC)    │
                  │ — intervalo de credibilidade│
                  └───────────┬────────────────┘
                              │
                              ▼
                   Predição final por mercado
```

### 7.2 Modelo 1: Dixon-Coles (gols)

Base do projeto. Versão moderna do Poisson bivariado para placares de futebol:

- Cada time tem `attack` e `defense` latentes por competição.
- Probabilidade de placar (i, j) é Poisson bivariada com correção Dixon-Coles para dependência em placares baixos (0-0, 1-1, 1-0, 0-1) — onde Poisson puro falha.
- Mando de campo como fator multiplicativo aprendido por competição.
- Decaimento temporal: jogos antigos pesam menos (parâmetro ξ aprendido por MLE).

A partir da matriz de placares possíveis, **derivamos os mercados**:

- 1X2 = soma das probabilidades de cada região da matriz.
- Over/Under 2.5 = soma de placares com i+j ≥ 3 vs < 3.
- BTTS = soma de placares com i ≥ 1 ∧ j ≥ 1.

Implementação: parâmetros via L-BFGS sobre log-likelihood (`scipy.optimize`). Treinos rápidos (segundos), retreino diário viável.

### 7.3 Modelo 2: XGBoost (correções e não-linearidades)

Captura o que o modelo estatístico não vê: descanso, viagem, lesão de jogador-chave, contexto de fase eliminatória, derbies.

- **Classificador** — multiclasse softmax para 1X2; binário para BTTS e Over/Under.
- **Regressor** — prediz `gols_mandante` e `gols_visitante` (alimenta mercados derivados via Poisson empírico).

Tuning com **Optuna** (busca bayesiana de hyperparams). Validação com **walk-forward cross-validation** — jamais K-fold aleatório (destrói o eixo temporal).

### 7.4 Modelo 3: Escanteios (Poisson bivariado)

Mesmo arcabouço estatístico de Dixon-Coles (Poisson bivariado com forças `corners_for` e `corners_against` latentes por time, decaimento temporal, fator de mando), **mas treinado sobre escanteios em vez de gols**, e **sem a correção de placares baixos** que caracteriza o Dixon-Coles. A correção DC ajusta os placares 0-0/1-1/1-0/0-1 (frequentes em gols, raros em escanteios). Para escanteios, Poisson puro ajusta bem porque a distribuição não tem essa anomalia em valores baixos.

### 7.5 Ensemble (stacking)

Probabilidades dos dois modelos de gols (DC e XGB) **não são médias simples**. Stacking:

1. Em walk-forward, geramos previsões out-of-fold dos dois modelos para cada jogo de treino.
2. Uma **regressão logística** aprende qual modelo confiar em cada contexto (input: probs dos dois modelos + meta-features tipo `is_eliminatorio`, `team_type`).
3. Para cada mercado, **isotonic regression** por cima da prob final calibra (probabilidade reportada bate com frequência observada).

Mercado de escanteios usa apenas o Modelo 3 (sem ensemble — fonte única).

### 7.6 Camada bayesiana de incerteza (PyMC)

O ensemble dá ponto. PyMC dá distribuição:

- Aceita probabilidade do ensemble como **prior informativo**.
- Atualiza posterior usando histórico recente de performance do modelo em jogos similares (mesma competição, mesmo tipo de mercado).
- Reporta **intervalo de credibilidade 95%** junto da prob pontual.

Implementação: MCMC roda offline 1x por semana para gerar a "calibragem bayesiana"; inferência por jogo é lookup O(1) numa tabela posterior. Não bloqueia request HTTP.

### 7.7 Versionamento de modelos

Toda execução de `analytis train` cria um `model_version`:

- Hash do código (git SHA + diff staged).
- Snapshot do dataset de treino (lista de `match_id`s).
- Hyperparams completos.
- Métricas de validação (Brier, log-loss, ECE).
- Pickle do modelo treinado em disco: `./models/{version_id}.pkl`.

Promoção a produção é **manual e explícita** via `analytis model promote <version_id>` — modelo novo só vira default depois de inspeção de métricas. Comparação A/B entre versões é trivial: as duas continuam armazenadas, dá para retroceder.

### 7.8 Métricas de avaliação (registradas a cada execução)

- **Brier score** por mercado (proper scoring rule — incentiva calibração honesta).
- **Log-loss** por mercado.
- **Reliability diagram** (calibração: prob predita vs frequência observada).
- **ROI simulado** contra odds históricas (Fase 0: odds de fechamento via The Odds API free tier ou scraping arquivado OddsPortal).
- **CLV proxy** — se temos odds de abertura e fechamento históricas, a diferença média na direção da nossa predição.

---

## 8. Scoring, API REST e CLI

### 8.1 Pipeline de scoring

Disparado em três janelas: **T-24h, T-4h, T-1h** antes da partida. Cada disparo:

1. Resolve `match_id` da janela.
2. Gera `feature_snapshot` chamando a camada de features com `as_of=now`.
3. Roda ensemble + camada bayesiana sobre o snapshot.
4. **Insere** (nunca atualiza) linhas em `prediction` — uma por (match × mercado × snapshot).
5. Registra `model_version_id` e `feature_snapshot_id` em cada linha.

Resultado: **série temporal de previsões** para o mesmo jogo. Permite observar como a probabilidade evoluiu conforme lineup confirmou e notícias chegaram.

### 8.2 API REST (FastAPI)

Stateless, documentação OpenAPI automática, **autenticação por API key** via header `X-API-Key` (gerada no `.env`, suficiente para uso local). Versionada em `/v1/`.

Endpoints essenciais:

```
GET  /v1/competitions
GET  /v1/competitions/{id}/matches?status=upcoming&from=&to=
GET  /v1/matches/{id}
GET  /v1/matches/{id}/predictions
       ?model_version=latest          (default)
       ?snapshot=latest|all|t-24|t-4|t-1
GET  /v1/matches/{id}/features/{snapshot_id}
GET  /v1/teams/{id}/elo-history?from=&to=
GET  /v1/models/{version_id}/metrics
GET  /v1/health
```

Formato de resposta padronizado:

```json
{
  "match_id": "...",
  "snapshot_taken_at": "2026-06-15T16:00:00Z",
  "model_version": "ensemble-v0.3.1",
  "markets": {
    "1x2": {
      "home": {"prob": 0.527, "ci_95": [0.471, 0.583]},
      "draw": {"prob": 0.241, "ci_95": [0.198, 0.286]},
      "away": {"prob": 0.232, "ci_95": [0.189, 0.279]}
    },
    "over_under_2_5": {"over": {"prob": 0.58, "ci_95": [0.52, 0.64]}, "under": {...}},
    "btts": {"yes": {...}, "no": {...}},
    "corners_over_9_5": {"over": {...}, "under": {...}}
  },
  "diagnostics": {
    "components": {"dixon_coles_weight": 0.62, "xgboost_weight": 0.38},
    "key_features": [
      {"name": "elo_diff", "value": 184, "shap_importance": 0.31},
      {"name": "rest_days_home", "value": 6, "shap_importance": 0.12}
    ]
  }
}
```

O bloco `diagnostics` materializa o princípio "auditável" — cada previsão se explica.

### 8.3 CLI (Typer)

CLI é bancada de operação, não consumo final:

```
analytis ingest fixtures --competition wc-2026
analytis ingest backfill --competition brasileirao --since 2018-01-01
analytis features build --match <id>
analytis train --model dixon-coles --competition wc-2026
analytis train --model xgboost --target 1x2
analytis train --model ensemble
analytis score --match <id>
analytis score --all-upcoming
analytis model list
analytis model promote <version_id>
analytis backtest --competition wc-2018 --model latest
analytis report calibration --model latest
analytis db migrate
analytis api serve --port 8000
```

Saída sempre estruturada (tabela rich + flag `--json` para pipe).

---

## 9. LLM periférico (extração de features de notícias)

### 9.1 Papel

Parsear notícias soltas que afetam o jogo: lesões, suspensões, escalações vazadas, condições climáticas. **Texto bruto não vira feature** — LLM extrai estruturado.

**O LLM nunca toca probabilidades.** É apenas extrator de features. Toda probabilidade do sistema sai de modelos estatísticos/ML rigorosos.

### 9.2 Stack

- Modelo: **Claude Haiku 4.5** (melhor custo-benefício atual para extração estruturada).
- Acesso via SDK Anthropic com **prompt caching agressivo** — prompt de sistema de extração não muda, só o texto da notícia.
- Saída forçada com **structured output / tool use** (JSON validado contra Pydantic).
- Custo esperado: < R$ 5/mês mesmo com 50 notícias/dia.

### 9.3 Fluxo

1. Job `ingest:news` varre RSS dos principais portais (Globo Esporte, ESPN, BBC Sport, Marca), filtrando por times com jogos nos próximos 14 dias.
2. Texto bruto vai ao LLM com schema:
   ```
   { team, player, status (out|doubt|suspended|key_back), confidence }
   ```
3. Resultado alimenta features `key_players_missing` e modificadores em `lineup_strength`.
4. Cada extração é **logada** (texto bruto + saída do LLM) para auditoria e calibração.
5. **Override manual** disponível via CLI:
   ```
   analytis news override --match <id> --feature key_goalkeeper_out=true
   ```
   Quando o LLM erra, o usuário corrige.

---

## 10. Estrutura do projeto

### 10.1 Layout de pastas

```
analytis/
├── pyproject.toml              # uv + Ruff + Pytest + Mypy
├── alembic.ini
├── .env.example
├── README.md
├── docs/
│   └── superpowers/specs/      # este design + futuras specs
├── migrations/                 # Alembic
├── models/                     # pickles versionados (gitignore)
├── data/cache/                 # cache de features (gitignore)
├── src/analytis/
│   ├── __init__.py
│   ├── config.py               # Pydantic Settings
│   ├── domain/                 # entidades puras (Pydantic), sem I/O
│   │   ├── competition.py
│   │   ├── match.py
│   │   ├── prediction.py
│   │   └── ...
│   ├── persistence/            # SQLAlchemy + repositórios
│   │   ├── orm/
│   │   ├── repositories/
│   │   └── unit_of_work.py
│   ├── ingestion/
│   │   ├── adapters/           # um arquivo por fonte
│   │   │   ├── football_data.py
│   │   │   ├── fbref.py
│   │   │   ├── openligadb.py
│   │   │   └── elo_ratings.py
│   │   ├── pipeline.py
│   │   └── scheduler.py
│   ├── features/
│   │   ├── catalog.py          # registry de feature funcs
│   │   ├── elo.py
│   │   ├── form.py
│   │   ├── h2h.py
│   │   ├── context.py
│   │   ├── lineup.py
│   │   ├── corners.py
│   │   └── snapshot.py
│   ├── modeling/
│   │   ├── dixon_coles.py
│   │   ├── xgboost_model.py
│   │   ├── corners_model.py
│   │   ├── ensemble.py
│   │   ├── bayesian_calibration.py
│   │   ├── training.py
│   │   ├── evaluation.py       # Brier, log-loss, reliability
│   │   └── versioning.py
│   ├── scoring/
│   │   ├── pipeline.py
│   │   └── markets.py          # derivações 1X2/OU/BTTS da matriz Poisson
│   ├── news/
│   │   ├── rss_collector.py
│   │   ├── llm_extractor.py    # cliente Anthropic
│   │   └── schemas.py
│   ├── application/            # casos de uso (orquestração fina)
│   │   ├── ingest_fixtures.py
│   │   ├── score_match.py
│   │   ├── train_models.py
│   │   └── ...
│   ├── api/
│   │   ├── main.py             # FastAPI app
│   │   ├── routes/
│   │   ├── schemas/            # Pydantic IO
│   │   └── deps.py             # DI: repos, services, auth
│   └── cli/
│       ├── __init__.py         # Typer app
│       ├── ingest.py
│       ├── train.py
│       ├── score.py
│       ├── model.py
│       ├── backtest.py
│       └── db.py
└── tests/
    ├── unit/                   # rápidos, sem I/O
    ├── integration/            # tocam Postgres em container
    └── fixtures/               # jogos reais para regressão
```

### 10.2 Tooling

| Categoria | Escolha | Por quê |
|---|---|---|
| Gerenciador de pacotes | **uv** | Rápido, lock determinístico, padrão moderno |
| Lint + format | **Ruff** (regras E, F, B, I, UP, SIM, RUF) | Substitui flake8/black/isort, instantâneo |
| Tipos | **Mypy strict** + Pydantic 2 | Pega bugs antes de rodar |
| Testes | **Pytest** + **pytest-cov** + **hypothesis** | Property-based para features matemáticas |
| Migrations | **Alembic** | Padrão SQLAlchemy |
| DB local | **Postgres 16 em Docker Compose** | Reprodutível |
| Pre-commit | **pre-commit** com Ruff + Mypy | Disciplina automática |

### 10.3 Qualidade

- **Cobertura mínima 80%** em `domain/`, `features/`, `modeling/` (lógica de negócio).
- **Property-based tests** em features matemáticas críticas:
  - "Soma das probabilidades 1X2 ≈ 1.0 ± 1e-9"
  - "ELO é monotônico ao vencer"
  - "Dixon-Coles converge"
- **Testes de regressão** sobre jogos célebres com previsão esperada documentada — sentinelas de qualidade do modelo. Se o modelo passar a dar 99% para o Brasil contra a Alemanha em 2014, algo quebrou.
- **Smoke tests da API** verificando que toda rota responde 2xx em fluxo feliz.
- **Backtest end-to-end** rodando Copa 2018 inteira em CI semanal — métricas vão para `models/{version}/backtest_history.json`.

---

## 11. Roadmap de implementação (~6-8 semanas part-time)

| Semana | Marco |
|---|---|
| 1 | Esqueleto: pyproject, Postgres + Alembic, domínio + repositórios, CLI mínima, CI |
| 2 | Ingestão Football-Data.org + ELO + scheduler + backfill da Copa 2018 e 2022 |
| 3 | Camada de features (ELO, forma, H2H, contexto) + snapshots + cache |
| 4 | Dixon-Coles treinado + derivação de mercados 1X2/OU/BTTS + métricas de calibração |
| 5 | XGBoost + ensemble + isotonic calibration + backtest Copa 2018 |
| 6 | Modelo de escanteios + ingestão FBref + camada bayesiana de incerteza |
| 7 | API REST completa + autenticação + diagnostics + LLM news extractor |
| 8 | Polimento, documentação operacional, backtest Copa 2026 (com dados já jogados) como validação final |

A partir da semana 4 há **previsões úteis fluindo**. Cada semana subsequente sobe qualidade. Quando a Copa 2026 terminar (~19/07), o sistema estará na v0.6 com material para avaliação séria.

---

## 12. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| FBref muda HTML e scraper quebra | Adapter isolado, fallback gracioso para sem-xG, cache de 24h reduz pressão |
| Dixon-Coles com poucos jogos de Copa do Mundo (seleções) | Prior bayesiano por confederação + uso de amistosos + ELO mundial como ancoragem inicial |
| Overfitting em backtest | Walk-forward CV obrigatório, nunca K-fold aleatório; backtest out-of-time é juiz final |
| LLM erra extração de notícia → feature ruim | Toda extração é logada e tem override manual via CLI |
| Sistema cresce e código vira espaguete | Mypy strict + Ruff pedante + revisão a cada PR + testes de regressão em modelos |
| Fontes gratuitas insuficientes para qualidade desejada | Arquitetura pluggable permite promover Fase 0 → 1 → 2 sem reescrever lógica |

---

## 13. Fora de escopo (decisões explícitas para evitar drift)

- **In-play (ao vivo).** Outra família de modelos, outra arquitetura. Fica para v2.
- **Frontend / UI.** API REST é a porta de saída; consumo via CLI, curl, Postman ou ferramenta de banco.
- **Outros esportes.** A arquitetura permite, mas v1 é só futebol.
- **Distribuição / cloud.** Monolito local. Cloud só se houver demanda real comprovada.
- **Mercados de jogador** (gols, finalizações, assistências individuais). Exigem dados event-level pagos. Possível Fase 2/3.
- **Cartões e mercados de árbitro.** Sinal fraco com dados gratuitos. Possível ampliação futura.
- **Bater o mercado.** Objetivo do usuário é estudo, não ROI. Métrica de sucesso = calibração + interpretabilidade, não lucro.
