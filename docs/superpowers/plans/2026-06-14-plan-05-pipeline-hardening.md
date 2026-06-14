# Plano 5 — Pipeline hardening + cobertura DC + ingest live

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fechar os buracos descobertos na noite do Brasil x Marrocos (2026-06-13): pipeline de value bets com 3 bugs (sem devigging, sem unique constraint, sem modelo de produção padrão), cobertura do modelo DC limitada a 51 seleções (Haiti, Escócia, Curaçao etc ficam de fora), e ingestão de resultado live que não atualiza `matches` quando o jogo termina.

**Architecture:** 4 workstreams **independentes** (podem ser executadas em paralelo por developers diferentes ou em sequência):

- **A.** Bugs da pipeline de value bets (3 tasks)
- **B.** Expansão de cobertura do DC (3 tasks)
- **C.** Ingestão live de resultados (2 tasks)
- **D.** Validação end-to-end (2 tasks)

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy async + Alembic, pytest, Typer CLI, modelos DC/XGBoost/ensemble já existentes. Sem stack nova.

**Branch:** continuar em `main` (preferência do usuário desde Plano 2).

**Branch base:** main, commit atual `a2d080f` (fim do Plano 4).

---

## Estrutura de arquivos a tocar

```
src/analytis/
├── modeling/
│   └── ev.py                                 # MODIFY: adicionar devig helpers
├── application/
│   ├── find_value_bets.py                    # MODIFY: usar devig + upsert
│   ├── ingest_international_history.py       # MODIFY: aceitar lista de torneios
│   ├── train_dixon_coles.py                  # (re-usar — sem mudança)
│   ├── train_xgboost.py                      # (re-usar)
│   ├── score_ensemble.py                     # MODIFY: skip + warn em vez de raise
│   └── update_results.py                     # NEW: backfill de resultado final
├── persistence/
│   ├── orm/
│   │   └── bets.py                           # MODIFY: UniqueConstraint
│   └── repositories/
│       ├── bets.py                           # MODIFY: upsert ON CONFLICT
│       └── model_version.py                  # MODIFY: get_promoted helper
├── cli/
│   ├── bets.py                               # MODIFY: --model opcional + warn
│   ├── score.py                              # MODIFY: --ensemble-name opcional
│   ├── ingest.py                             # MODIFY: novo subcomando results
│   └── train.py                              # MODIFY: --promote flag
└── api/routes/
    └── (sem mudança — rotas já leem do banco)

alembic/versions/
└── 2026_06_14_XXXX_value_bet_unique.py       # NEW

tests/
├── unit/modeling/test_ev.py                  # MODIFY: testes devig
├── unit/application/test_find_value_bets.py  # MODIFY: assert sem duplicata
├── integration/application/test_update_results.py  # NEW
└── integration/cli/test_bets_cli.py          # MODIFY: --model opcional

scripts/
└── promote_model.py                          # NEW (one-off)
```

---

## Workstream A — Pipeline value bets (bugs estruturais)

### Task A1: Devigging em `find_value_bets`

**Files:**
- Modify: `src/analytis/modeling/ev.py` (já tem `remove_overround` — vamos usar)
- Modify: `src/analytis/application/find_value_bets.py:55-94`
- Modify: `tests/unit/modeling/test_ev.py`

**Contexto:** Hoje `find_value_bets.py:68` calcula `market_prob = 1.0 / best_odds`. Não remove o overround (juice) da casa. Em casas com overround típico de 5%, a probabilidade implícita é superestimada em ~5%, e o `edge = our_prob - market_prob` é deflacionado (efeito ruim de Pinnacle, casa sharp) ou inflacionado dependendo do mercado. A função `remove_overround` já existe em `ev.py` — basta usar.

- [ ] **A1-S1: Teste falhante de devig**

```python
# tests/unit/modeling/test_ev.py
def test_remove_overround_pinnacle_under_over():
    # Pinnacle ~0% overround
    fair = remove_overround([1.96, 1.94])
    assert abs(fair[0] - 0.4974) < 0.001
    assert abs(fair[1] - 0.5026) < 0.001
    assert abs(sum(fair) - 1.0) < 1e-9

def test_remove_overround_high_juice():
    # 5% overround
    fair = remove_overround([2.0, 2.0])
    assert abs(fair[0] - 0.5) < 1e-9
```

Run: `pytest tests/unit/modeling/test_ev.py -v`
Expected: PASS (já passa — só garantir cobertura)

- [ ] **A1-S2: Modificar `find_value_bets.py` para devigar por mercado antes de comparar**

```python
# src/analytis/application/find_value_bets.py
# Após linha 56 (latest = await odds_repo.latest_for_match(...))

from analytis.modeling.ev import remove_overround

# ...
for market in {p.market for p in preds}:
    latest = await odds_repo.latest_for_match(params.match_id, market)
    # Best odd per outcome
    best_by_outcome: dict[str, tuple[float, str]] = {}
    for q in latest:
        cur = best_by_outcome.get(q.outcome)
        if cur is None or q.decimal_odds > cur[0]:
            best_by_outcome[q.outcome] = (q.decimal_odds, q.bookmaker)

    if not best_by_outcome:
        continue
    # Devig: usar Pinnacle como referência se disponível, senão média
    # Estratégia simples: devigar a partir das melhores odds do match
    outcomes_sorted = sorted(best_by_outcome.keys())
    odds_list = [best_by_outcome[o][0] for o in outcomes_sorted]
    fair_probs = remove_overround(odds_list)
    fair_by_outcome = dict(zip(outcomes_sorted, fair_probs, strict=True))

    for outcome, (best_odds, bm) in best_by_outcome.items():
        pred = our_by_outcome.get((market, outcome))
        if pred is None:
            continue
        our_prob = pred.prob
        market_prob = fair_by_outcome[outcome]  # devigged
        # ... resto igual
```

> **Nota:** usar best-of-market introduz viés (best-of-market overround é menor que o de qualquer casa individual). Plano realista: armazenar `market_prob` como devigged from best-of-market; edge fica mais conservador. Aceitável como v1.

- [ ] **A1-S3: Teste integração validando edge devigged**

```python
# tests/unit/application/test_find_value_bets.py (novo)
async def test_devigging_reduces_edge_against_sharp_book(test_session_factory):
    # Setup: 1 match, predições 50/30/20, odds Pinnacle 2.0/2.0/2.0 (overround 0%)
    # ... arrange fixture
    result = await use_case.execute(params)
    # Pré-fix daria edge inflacionado; pós-fix deve mostrar edges menores
    bets = await get_bets_for(match_id)
    for b in bets:
        assert abs(b.market_prob - 0.333) < 0.01  # devigged
```

- [ ] **A1-S4: Commit**

```bash
rtk git add src/analytis/modeling/ev.py src/analytis/application/find_value_bets.py tests/unit/modeling/test_ev.py tests/unit/application/test_find_value_bets.py
rtk git commit -m "fix(bets): devig market probabilities before computing edge"
```

---

### Task A2: Unique constraint + upsert em `value_bet`

**Files:**
- Modify: `src/analytis/persistence/orm/bets.py:22-25`
- Create: `alembic/versions/2026_06_14_XXXX_value_bet_unique.py`
- Modify: `src/analytis/persistence/repositories/bets.py`
- Modify: `src/analytis/application/find_value_bets.py:80-93`

**Contexto:** `value_bet` sem unique constraint → rodar `find-value` N vezes gera N duplicatas. Já visto em Brasil x Marrocos: `over_under_goals/under_2.5 @ pinnacle` repetido 2x.

- [ ] **A2-S1: Adicionar `UniqueConstraint` no ORM**

```python
# src/analytis/persistence/orm/bets.py
class ValueBetORM(Base, TimestampMixin):
    __tablename__ = "value_bet"
    __table_args__ = (
        UniqueConstraint(
            "match_id", "model_version_id", "market", "outcome", "bookmaker",
            name="uq_value_bet_natural",
        ),
        Index("ix_value_bet_match", "match_id"),
        Index("ix_value_bet_model", "model_version_id"),
    )
```

- [ ] **A2-S2: Migration**

```bash
uv run alembic revision -m "value_bet unique constraint" --autogenerate
```

Editar a migration gerada para também **deduplicar dados existentes** antes do ADD CONSTRAINT:

```python
def upgrade() -> None:
    # Deduplicar: manter o mais recente por (match, model, market, outcome, bookmaker)
    op.execute("""
        DELETE FROM value_bet vb1 USING value_bet vb2
        WHERE vb1.id < vb2.id
          AND vb1.match_id = vb2.match_id
          AND vb1.model_version_id = vb2.model_version_id
          AND vb1.market = vb2.market
          AND vb1.outcome = vb2.outcome
          AND vb1.bookmaker = vb2.bookmaker;
    """)
    op.create_unique_constraint(
        "uq_value_bet_natural",
        "value_bet",
        ["match_id", "model_version_id", "market", "outcome", "bookmaker"],
    )
```

- [ ] **A2-S3: Repository com upsert**

```python
# src/analytis/persistence/repositories/bets.py
from sqlalchemy.dialects.postgresql import insert as pg_insert

class ValueBetRepository:
    async def upsert(self, *, match_id, model_version_id, market, outcome, bookmaker,
                     our_prob, market_prob, decimal_odds, edge, kelly_fraction,
                     suggested_stake_units, found_at) -> None:
        stmt = pg_insert(ValueBetORM).values(
            match_id=match_id, model_version_id=model_version_id,
            market=market, outcome=outcome, bookmaker=bookmaker,
            our_prob=our_prob, market_prob=market_prob, decimal_odds=decimal_odds,
            edge=edge, kelly_fraction=kelly_fraction,
            suggested_stake_units=suggested_stake_units, found_at=found_at,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_value_bet_natural",
            set_={
                "our_prob": stmt.excluded.our_prob,
                "market_prob": stmt.excluded.market_prob,
                "decimal_odds": stmt.excluded.decimal_odds,
                "edge": stmt.excluded.edge,
                "kelly_fraction": stmt.excluded.kelly_fraction,
                "suggested_stake_units": stmt.excluded.suggested_stake_units,
                "found_at": stmt.excluded.found_at,
            },
        )
        await self._session.execute(stmt)
```

- [ ] **A2-S4: Mudar `find_value_bets.py` para chamar `upsert` em vez de `insert`**

- [ ] **A2-S5: Teste de duplicata**

```python
async def test_find_value_bets_idempotent(test_session_factory):
    # Run use case twice with same input
    await use_case.execute(params)
    n1 = await count_bets(match_id)
    await use_case.execute(params)
    n2 = await count_bets(match_id)
    assert n1 == n2  # No duplicates
```

- [ ] **A2-S6: Run migration + tests + commit**

```bash
uv run alembic upgrade head
uv run pytest tests/unit/application/test_find_value_bets.py tests/integration/db -v
rtk git add alembic/versions/ src/analytis/persistence/ src/analytis/application/find_value_bets.py tests/
rtk git commit -m "fix(bets): unique constraint + upsert on value_bet (no duplicates)"
```

---

### Task A3: Modelo de produção como default

**Files:**
- Modify: `src/analytis/persistence/repositories/model_version.py`
- Modify: `src/analytis/cli/bets.py:25-35`
- Modify: `src/analytis/cli/score.py` (ensemble subcommand)
- Modify: `src/analytis/cli/train.py` (adicionar flag `--promote`)
- Create: `scripts/promote_model.py`

**Contexto:** Já existe campo `is_promoted: bool` em `ModelVersionORM`. Está sempre `False`. CLI exige `--model` obrigatório, sem default — fácil rodar `find-value` com baseline errado (foi exatamente o que aconteceu com Brasil x Marrocos).

- [ ] **A3-S1: Helper `get_promoted`**

```python
# src/analytis/persistence/repositories/model_version.py
class ModelVersionRepository:
    async def get_promoted(self, family: str | None = None) -> ModelVersionORM | None:
        q = select(ModelVersionORM).where(ModelVersionORM.is_promoted.is_(True))
        if family:
            q = q.where(ModelVersionORM.family == family)
        return (await self._session.execute(q)).scalars().first()
```

- [ ] **A3-S2: Promover `ens-dc-xgb-v0.1.0`**

```python
# scripts/promote_model.py
"""One-off: mark a model version as promoted (production default)."""
import asyncio
import sys
import typer
from sqlalchemy import update
from analytis.config import get_settings
from analytis.persistence.engine import create_engine, create_session_factory
from analytis.persistence.orm.inference import ModelVersionORM

app = typer.Typer()

@app.command()
def promote(model_name: str) -> None:
    asyncio.run(_promote(model_name))

async def _promote(name: str) -> None:
    s = get_settings()
    eng = create_engine(s)
    Sf = create_session_factory(eng)
    async with Sf() as ses:
        # Demote all in same family first
        mv = (await ses.execute(
            update(ModelVersionORM).where(ModelVersionORM.name == name)
            .values(is_promoted=True).returning(ModelVersionORM.family)
        )).scalar_one_or_none()
        if mv is None:
            print(f"Model {name!r} not found"); sys.exit(2)
        await ses.execute(
            update(ModelVersionORM)
            .where(ModelVersionORM.family == mv, ModelVersionORM.name != name)
            .values(is_promoted=False)
        )
        await ses.commit()
    await eng.dispose()
    print(f"Promoted {name}")

if __name__ == "__main__":
    app()
```

Run: `uv run python scripts/promote_model.py ens-dc-xgb-v0.1.0`

- [ ] **A3-S3: CLI `bets find-value` com `--model` opcional**

```python
# src/analytis/cli/bets.py
@app.command("find-value")
def find_value(
    match_id: str = typer.Option(..., help="Match UUID."),
    model: str | None = typer.Option(
        None, "--model",
        help="ModelVersion name. Defaults to the promoted model.",
    ),
    # ...
) -> None:
    asyncio.run(_find(match_id, model, min_edge, bankroll, fraction, max_units))

async def _find(match_id_str, model_name, ...):
    settings = get_settings()
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    try:
        async with factory() as s:
            if model_name is None:
                mv = (await s.scalars(
                    select(ModelVersionORM).where(ModelVersionORM.is_promoted.is_(True))
                )).first()
                if mv is None:
                    console.print("[red]No promoted model found. Pass --model explicitly.[/red]")
                    raise typer.Exit(code=2)
                console.print(f"[yellow]Using promoted model: {mv.name}[/yellow]")
            else:
                mv = (await s.scalars(
                    select(ModelVersionORM).where(ModelVersionORM.name == model_name)
                )).one_or_none()
                if mv is None:
                    console.print(f"[red]Model {model_name!r} not found[/red]")
                    raise typer.Exit(code=2)
                if not mv.is_promoted:
                    console.print(
                        f"[yellow]⚠ Using non-promoted model {mv.name!r}. "
                        f"The promoted model is the production default.[/yellow]"
                    )
```

- [ ] **A3-S4: Test CLI default behavior**

```python
def test_find_value_uses_promoted_when_no_model(test_db_with_promoted_ens):
    result = runner.invoke(app, ["bets", "find-value", "--match-id", str(match_id)])
    assert result.exit_code == 0
    assert "Using promoted model: ens-dc-xgb-v0.1.0" in result.stdout
```

- [ ] **A3-S5: Commit**

```bash
rtk git add src/analytis/persistence/repositories/model_version.py src/analytis/cli/ scripts/promote_model.py tests/
rtk git commit -m "feat(cli): default to promoted model in bets/score commands"
```

---

## Workstream B — Cobertura DC (Haiti, Escócia, etc)

### Task B1: Expandir filtro de torneios em `ingest_international_history`

**Files:**
- Modify: `src/analytis/application/ingest_international_history.py:30-32`
- Modify: `src/analytis/cli/ingest.py` (CLI command já existe; adicionar `--tournament` repetível)

**Contexto:** Hoje `tournaments={"FIFA World Cup"}` é o default e provavelmente foi o único usado. CSV adapter já parseia muitos torneios. Time como Haiti não aparece em finais de WC, mas aparece em **Concacaf Gold Cup**, **qualificatórias da Concacaf**, **amistosos**. Escócia: **UEFA Euro**, **UEFA Euro Qualifying**, **Friendly**.

- [ ] **B1-S1: Listar torneios disponíveis no CSV**

```bash
uv run python -c "
import pandas as pd
df = pd.read_csv('data/international_results.csv')  # ajustar path se diferente
print(df['tournament'].value_counts().head(30))
"
```

Expected: dezenas de torneios. Decidir lista útil:
- FIFA World Cup, FIFA World Cup qualification
- UEFA Euro, UEFA Euro qualification, UEFA Nations League
- Copa América, Copa América qualification
- Africa Cup of Nations, AFC Asian Cup, CONCACAF Gold Cup, CONCACAF Nations League
- CONMEBOL/CONCACAF/AFC/CAF qualifications for WC
- Friendly (filtro extra: só últimos 5-10 anos pra não inflar com dados velhos)

- [ ] **B1-S2: CLI aceitando `--tournament` múltiplo**

```python
# src/analytis/cli/ingest.py — extend international-history command
@app.command("international-history")
def international_history(
    csv_path: Path = typer.Option(..., exists=True),
    tournament: list[str] = typer.Option(
        ["FIFA World Cup"],
        "--tournament", "-t",
        help="Repeatable. Default keeps WC-only behavior.",
    ),
    min_date: str | None = typer.Option(None, help="ISO date e.g. 2010-01-01"),
) -> None:
    # ... passar set(tournament) como params.tournaments
```

- [ ] **B1-S3: Run ingest com lista ampliada**

```bash
uv run analytis ingest international-history \
    --csv-path data/international_results.csv \
    --min-date 2014-01-01 \
    -t "FIFA World Cup" \
    -t "FIFA World Cup qualification" \
    -t "UEFA Euro" -t "UEFA Euro qualification" -t "UEFA Nations League" \
    -t "Copa América" -t "Copa América qualification" \
    -t "African Cup of Nations" -t "AFC Asian Cup" \
    -t "CONCACAF Gold Cup" -t "CONCACAF Nations League" \
    -t "Friendly"
```

Verificar contagem de times depois:

```sql
SELECT COUNT(DISTINCT team_id)
FROM match m
CROSS JOIN LATERAL (VALUES (m.home_team_id), (m.away_team_id)) AS x(team_id)
WHERE m.status = 'finished';
```

Expected: ≥ 150 times (vs 51 antes).

- [ ] **B1-S4: Commit**

```bash
rtk git add src/analytis/application/ingest_international_history.py src/analytis/cli/ingest.py
rtk git commit -m "feat(ingest): support multiple tournaments in international history"
```

---

### Task B2: Retreinar DC com cobertura ampla

**Files:**
- Run-only — usa `analytis train dixon-coles` existente

- [ ] **B2-S1: Train novo DC**

```bash
uv run analytis train dixon-coles \
    --since 2014-01-01 \
    --decay-per-day 0.0 \
    --name dc-intl-v0.3.0-broad
```

Verificar:
- `n_teams` ≥ 150
- `n_matches` ≥ 2000 (qualificatórias + amistosos somam muito)

- [ ] **B2-S2: Sanity check — verificar que Haiti e Scotland estão**

```bash
uv run python -c "
import pickle
with open('models/<new-model-uuid>.pkl', 'rb') as f:
    p = pickle.load(f)
assert 'Haiti' in p.attack, 'Haiti missing'
assert 'Scotland' in p.attack, 'Scotland missing'
print(f'{len(p.attack)} teams, Haiti attack={p.attack[\"Haiti\"]:.3f}, Scotland attack={p.attack[\"Scotland\"]:.3f}')
"
```

---

### Task B3: Retreinar XGBoost + registrar novo ensemble

**Files:**
- Run-only + opcional `--promote` flag

- [ ] **B3-S1: Train XGB com mesmo dataset ampliado**

```bash
uv run analytis train xgboost \
    --since 2014-01-01 \
    --name xgb-intl-1x2-v0.2.0
```

- [ ] **B3-S2: Registrar ensemble + promover**

Em vez de criar comando novo, usar `score ensemble --match-id ...` num jogo qualquer para forçar criação do `ModelVersion` ensemble (já tem essa lógica em `score_ensemble.py:184`). Depois:

```bash
uv run python scripts/promote_model.py ens-intl-v0.2.0
```

- [ ] **B3-S3: Backfill score em todos os matches scheduled** (Workstream D fará isso na D1)

- [ ] **B3-S4: Commit (sem código novo, só artifacts)**

Os `.pkl` em `models/` estão no `.gitignore` (verificar). Se sim, só commit é metadata. Senão, atualizar `.gitignore`.

---

## Workstream C — Ingestão live de resultados

### Task C1: Use case `update-results`

**Files:**
- Create: `src/analytis/application/update_results.py`
- Modify: `src/analytis/cli/ingest.py` (subcomando `results`)
- Create: `tests/integration/application/test_update_results.py`

**Contexto:** Hoje `ingest fixtures` cria matches `scheduled`, e nada atualiza pra `live` ou `finished`. Brasil x Marrocos foi visto às 23:30 UTC, kickoff 22:00 UTC — status ainda `scheduled` no banco.

Football-Data.org adapter já busca matches com status atual. Basta um use case que repete o fetch e dá UPDATE em status + home_goals/away_goals onde divergir.

- [ ] **C1-S1: Use case**

```python
# src/analytis/application/update_results.py
@dataclass
class UpdateResultsParams:
    competition_external_id: str
    season_label: str
    only_recent_hours: int = 24  # filtra matches que terminaram nas últimas N horas

class UpdateResultsUseCase:
    async def execute(self, params: UpdateResultsParams) -> int:
        # 1. Fetch matches via FootballDataAdapter (com status atualizado)
        # 2. UPDATE match SET status=, home_goals=, away_goals= WHERE id=...
        # 3. Retornar quantos foram atualizados
```

- [ ] **C1-S2: CLI**

```bash
uv run analytis ingest results \
    --competition-id WC \
    --season 2026 \
    --only-recent-hours 24
```

- [ ] **C1-S3: Teste integração com fixture HTTP**

- [ ] **C1-S4: Commit**

---

### Task C2: Cron/agendamento + idempotência

**Files:**
- Doc: `docs/operations/scheduling.md` (NEW)
- (Sem código novo se Windows Task Scheduler for usado externamente)

**Contexto:** Quem dispara `ingest results` periodicamente? Para um setup local solo, Windows Task Scheduler é mais simples que adicionar APScheduler ao backend. Documentar.

- [ ] **C2-S1: Script `.ps1` chamável**

```powershell
# scripts/update_results.ps1
$ErrorActionPreference = 'Stop'
cd "C:\Projetos\Pessoal\analytis"
uv run analytis ingest results --competition-id WC --season 2026 --only-recent-hours 6
```

- [ ] **C2-S2: Instruções para Task Scheduler em `docs/operations/scheduling.md`**

A cada 30 min durante a janela de jogos.

- [ ] **C2-S3: Commit**

---

## Workstream D — Validação end-to-end

### Task D1: Backtest com ensemble novo

**Files:**
- Run-only

- [ ] **D1-S1: Backtest walk-forward com `ens-intl-v0.2.0`**

```bash
uv run analytis backtest walk-forward \
    --model ens-intl-v0.2.0 \
    --from 2024-01-01 \
    --to 2026-06-13
```

Comparar log-loss e Brier contra `ens-dc-xgb-v0.1.0`. Sem regressão → OK.

- [ ] **D1-S2: Score all upcoming com modelo novo**

```bash
uv run analytis score all-upcoming --model ens-intl-v0.2.0
```

Validar: Haiti x Scotland agora deve ter predição (não dará mais `ValueError`).

---

### Task D2: Teste E2E de pipeline value bets

**Files:**
- Create: `tests/integration/pipeline/test_value_bet_e2e.py`

- [ ] **D2-S1: Teste E2E com fixture sintética**

```python
async def test_e2e_pipeline_no_duplicates_devigged(test_db):
    # 1. Insert match, model, predictions, odds com overround = 0%
    # 2. Run find_value_bets
    # 3. Run find_value_bets de novo (idempotência)
    # 4. Assert: edge ≈ 0 (devig zera juice), zero duplicatas
    ...
```

- [ ] **D2-S2: Commit final**

```bash
rtk git add tests/integration/pipeline/
rtk git commit -m "test: e2e value bets pipeline (devig + idempotency)"
```

---

## Acceptance criteria (end-of-plan)

- [ ] `value_bet` tem `UNIQUE(match_id, model_version_id, market, outcome, bookmaker)` e migration rodada
- [ ] `find_value_bets` é idempotente (rodar 2x não duplica)
- [ ] `market_prob` armazenado é devigged (não `1.0 / best_odds` cru)
- [ ] Pelo menos um modelo `is_promoted=True` no banco
- [ ] `analytis bets find-value` sem `--model` usa o promoted automaticamente
- [ ] DC novo tem ≥ 150 times (Haiti, Scotland verificados via script)
- [ ] `score ensemble` em Haiti x Scotland (ou outro jogo fora do top-51) retorna predição válida
- [ ] `analytis ingest results --competition-id WC --season 2026` atualiza status de matches finished sem erro
- [ ] Doc `docs/operations/scheduling.md` explica como agendar via Task Scheduler
- [ ] Backtest do ensemble novo: log-loss ≤ ensemble v0.1.0 + 5%
- [ ] `uv run pytest` clean (195 atuais + ~10 novos)
- [ ] `pnpm test --run` clean (28 atuais, sem regressão)
- [ ] `uv run analytis frontend build` clean

Se algum item falhar, criar tarefa específica antes de declarar o plano concluído.

---

## Out of scope (deliberadamente)

- Atualização live em-jogo (placar minuto-a-minuto). Só backfill pós-jogo.
- UI para escolher modelo no frontend. Modelo de produção é fixado server-side.
- APScheduler embarcado no backend. Task Scheduler externo é suficiente para single-user.
- Devigging avançado (Shin, Wisdom of the Crowd). Proportional é v1; podemos iterar depois.
- Re-tipagem de `Decimal` para odds/edge. Float continua aceitável.

## Riscos / unknowns

- **CSV de histórico internacional pode não ter todos os torneios listados.** Mitigação: B1-S1 lista o que tem antes de filtrar. Se faltar Friendly ou qualifiers, adiar B2/B3.
- **XGBoost re-train pode demorar muito com 10x mais dados.** Mitigação: monitorar tempo no train; se passar de ~10 min, restringir `--since` para 2018.
- **Devigging proportional super-corrige em mercados pesados (O/U com book muito enviesado).** Mitigação: D2 valida com fixture controlada; revisitar com Shin se necessário.
- **`ingest results` da Football-Data tem rate-limit (10 req/min free tier).** Mitigação: C1 pula matches que já são `finished` antes de chamar API.

---

## Execution

Branch: `main` (continuar prática dos planos anteriores).

Recomendação: rodar workstreams **A** e **C** em paralelo (independentes), **B** depende de nada mas é mais lenta (treino), **D** depende de A+B+C concluídos. Subagent-Driven Development funciona bem.
