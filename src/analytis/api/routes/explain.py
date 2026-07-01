"""LLM-backed explanation of a match's probabilistic forecast.

Reads the persisted predictions from the canonical model + best odds, hands
them to an OpenAI chat model as numbers (no fabricated facts), gets back a
short PT-BR narration. The LLM is a narrator, not a re-pricer — it never
overrides the model's probabilities.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

import openai
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from analytis.api.deps import require_api_key
from analytis.config import Settings, get_settings
from analytis.persistence.engine import create_engine, create_session_factory
from analytis.persistence.orm.catalog import TeamORM
from analytis.persistence.orm.inference import ModelVersionORM, PredictionORM
from analytis.persistence.orm.matches import MatchORM
from analytis.persistence.orm.odds import OddsSnapshotORM

CANONICAL_MODEL = "ensemble-v1"

router = APIRouter(prefix="/matches", tags=["explain"])

SYSTEM_PROMPT = """Você é um analista quantitativo de futebol que explica previsões probabilísticas em português brasileiro.

REGRAS DURAS:
- Use APENAS os números do contexto. Nunca invente lesões, escalações, histórico H2H, condições climáticas ou qualquer fato extra-modelo.
- Não dê palpite/aposta. Não diga "vai ganhar" — diga "o modelo atribui X%".
- Seja conciso: 3-5 frases, no máximo 100 palavras.
- Estrutura sugerida: (1) o que o modelo prevê em 1X2; (2) over/under e BTTS quando disponíveis; (3) se houver edge nas odds, mencione com cautela.
- Linguagem direta. Sem disclaimers genéricos longos.
- Se as odds estiverem ausentes, simplesmente não comente sobre valor/edge.
- Se algum mercado estiver ausente (indicado por "—"), simplesmente pule esse mercado — não invente valores."""


@asynccontextmanager
async def _session(settings: Settings) -> AsyncIterator[AsyncSession]:
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            yield session
    finally:
        await engine.dispose()


class ExplainResponse(BaseModel):
    match_id: UUID
    explanation: str
    model_used: str
    predictions_model: str


@router.get(
    "/{match_id}/explain",
    response_model=ExplainResponse,
    dependencies=[Depends(require_api_key)],
)
async def explain_match(
    match_id: UUID,
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> ExplainResponse:
    if settings.openai_api_key is None:
        raise HTTPException(
            status_code=503,
            detail="LLM não configurado: defina ANALYTIS_OPENAI_API_KEY no .env.",
        )

    async with _session(settings) as session:
        match = await session.get(MatchORM, match_id)
        if match is None:
            raise HTTPException(status_code=404, detail="match not found")
        home_team = await session.get(TeamORM, match.home_team_id)
        away_team = await session.get(TeamORM, match.away_team_id)
        if not home_team or not away_team:
            raise HTTPException(status_code=500, detail="team metadata missing")

        # Pull predictions from the canonical model. If ensemble-v1 hasn't
        # scored this match (edge case for very recent fixtures), fall back to
        # whatever the DB has so the LLM still has something to narrate.
        pred_stmt = (
            select(PredictionORM, ModelVersionORM)
            .join(ModelVersionORM, PredictionORM.model_version_id == ModelVersionORM.id)
            .where(PredictionORM.match_id == match_id)
        )
        rows = list((await session.execute(pred_stmt)).all())
        if not rows:
            raise HTTPException(
                status_code=422,
                detail="Sem predições para esta partida.",
            )
        by_model: dict[str, list[PredictionORM]] = {}
        for pred, mv in rows:
            by_model.setdefault(mv.name, []).append(pred)
        preds_model = CANONICAL_MODEL if CANONICAL_MODEL in by_model else next(iter(by_model))
        pred_rows = by_model[preds_model]
        preds: dict[str, dict[str, float]] = {}
        for p in pred_rows:
            preds.setdefault(p.market, {})[p.outcome] = p.prob

        odds_stmt = (
            select(OddsSnapshotORM)
            .where(OddsSnapshotORM.match_id == match_id)
            .order_by(OddsSnapshotORM.snapshot_taken_at.desc())
            .limit(50)
        )
        odds_rows = list((await session.scalars(odds_stmt)).all())
        best_odds: dict[tuple[str, str], float] = {}
        for o in odds_rows:
            key = (o.market, o.outcome)
            if key not in best_odds or o.decimal_odds > best_odds[key]:
                best_odds[key] = o.decimal_odds

    def _fmt(d: dict[str, float] | None) -> str:
        if not d:
            return "—"
        return ", ".join(f"{k}={v * 100:.1f}%" for k, v in d.items())

    odds_lines = (
        "\n".join(
            f"  - {market}/{outcome}: {odds:.2f}" for (market, outcome), odds in best_odds.items()
        )
        or "  (sem cotações coletadas)"
    )

    context = f"""PARTIDA
{home_team.name} (mandante{" — campo neutro" if match.is_home_neutral else ""}) vs {away_team.name}
Kickoff: {match.kickoff_utc.isoformat()}

PROBABILIDADES (modelo {preds_model})
1X2: {_fmt(preds.get("1x2"))}
Over/Under 2.5: {_fmt(preds.get("over_under_goals"))}
BTTS: {_fmt(preds.get("btts"))}

MELHORES ODDS DECIMAIS POR MERCADO (mercado real)
{odds_lines}

Tarefa: escreva uma explicação curta em PT-BR seguindo as regras."""

    client = openai.AsyncOpenAI(
        api_key=settings.openai_api_key.get_secret_value(),
        base_url=settings.openai_base_url,
    )
    try:
        resp = await client.chat.completions.create(
            model=settings.openai_model,
            max_tokens=600,
            temperature=0.3,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": context},
            ],
        )
    except openai.AuthenticationError as exc:
        raise HTTPException(status_code=503, detail=f"Chave OpenAI inválida: {exc}") from exc
    except openai.RateLimitError as exc:
        raise HTTPException(
            status_code=429, detail="Rate limit OpenAI; tente em alguns segundos."
        ) from exc
    except openai.APIError as exc:
        raise HTTPException(status_code=502, detail=f"Erro OpenAI: {exc}") from exc

    choice = resp.choices[0] if resp.choices else None
    explanation = (choice.message.content or "").strip() if choice else ""
    if not explanation:
        explanation = "(modelo retornou resposta vazia)"

    return ExplainResponse(
        match_id=match.id,
        explanation=explanation,
        model_used=resp.model,
        predictions_model=preds_model,
    )
