"""PushDispatcher: queries DB, formats payloads, sends via pywebpush."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from pywebpush import WebPushException, webpush
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.persistence.orm.catalog import TeamORM
from analytis.persistence.orm.inference import ModelVersionORM, PredictionORM
from analytis.persistence.orm.matches import MatchORM
from analytis.persistence.orm.push import MatchNotificationORM, PushSubscriptionORM
from analytis.push.bodies import build_post_payload, build_pre_payload
from analytis.push.vapid import VapidConfig

log = logging.getLogger(__name__)

PRE_WINDOW_LO = timedelta(minutes=9)
PRE_WINDOW_HI = timedelta(minutes=11)
POST_LOOKBACK = timedelta(hours=2)
ENSEMBLE_NAME = "ensemble-v1"


@dataclass
class DispatchResult:
    pre_matches: int = 0
    post_matches: int = 0
    subscribers: int = 0
    successes: int = 0
    deleted: int = 0


class PushDispatcher:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        vapid: VapidConfig,
    ) -> None:
        self._factory = session_factory
        self._vapid = vapid

    async def dispatch(self) -> DispatchResult:
        result = DispatchResult()
        async with self._factory() as session:
            pre_matches = await self._find_pre_matches(session)
            post_matches = await self._find_post_matches(session)
            subscriptions = (await session.scalars(select(PushSubscriptionORM))).all()
            subscriptions = list(subscriptions)

            result.pre_matches = len(pre_matches)
            result.post_matches = len(post_matches)
            result.subscribers = len(subscriptions)

            for match in pre_matches:
                pred = await self._load_ensemble_pred(session, match.id)
                if pred is None:
                    log.warning("no ensemble-v1 prediction for match %s, skipping pre", match.id)
                    continue
                home_name, away_name = await self._team_names(
                    session, match.home_team_id, match.away_team_id
                )
                payload = build_pre_payload(self._match_to_dict(match, home_name, away_name), pred)
                ok, deleted = await self._send_to_all(session, subscriptions, payload)
                result.successes += ok
                result.deleted += deleted
                await self._record_notification(session, match.id, "pre", ok)

            for match in post_matches:
                pred = await self._load_ensemble_pred(session, match.id)
                if pred is None:
                    log.warning("no ensemble-v1 prediction for match %s, skipping post", match.id)
                    continue
                home_name, away_name = await self._team_names(
                    session, match.home_team_id, match.away_team_id
                )
                payload = build_post_payload(self._match_to_dict(match, home_name, away_name), pred)
                ok, deleted = await self._send_to_all(session, subscriptions, payload)
                result.successes += ok
                result.deleted += deleted
                await self._record_notification(session, match.id, "post", ok)

            await session.commit()

        return result

    async def _find_pre_matches(self, session: AsyncSession) -> list[MatchORM]:
        now = datetime.now(UTC)
        not_notified = (
            ~select(MatchNotificationORM.id)
            .where(
                MatchNotificationORM.match_id == MatchORM.id,
                MatchNotificationORM.kind == "pre",
            )
            .exists()
        )
        stmt = select(MatchORM).where(
            MatchORM.kickoff_utc >= now + PRE_WINDOW_LO,
            MatchORM.kickoff_utc <= now + PRE_WINDOW_HI,
            not_notified,
        )
        return list((await session.scalars(stmt)).all())

    async def _find_post_matches(self, session: AsyncSession) -> list[MatchORM]:
        now = datetime.now(UTC)
        not_notified = (
            ~select(MatchNotificationORM.id)
            .where(
                MatchNotificationORM.match_id == MatchORM.id,
                MatchNotificationORM.kind == "post",
            )
            .exists()
        )
        stmt = select(MatchORM).where(
            MatchORM.status == "finished",
            MatchORM.kickoff_utc > now - POST_LOOKBACK,
            not_notified,
        )
        return list((await session.scalars(stmt)).all())

    async def _load_ensemble_pred(
        self, session: AsyncSession, match_id: UUID
    ) -> dict[str, float] | None:
        stmt = (
            select(PredictionORM.outcome, PredictionORM.prob)
            .join(ModelVersionORM, ModelVersionORM.id == PredictionORM.model_version_id)
            .where(
                PredictionORM.match_id == match_id,
                ModelVersionORM.name == ENSEMBLE_NAME,
                PredictionORM.market == "1x2",
            )
        )
        rows = (await session.execute(stmt)).all()
        if not rows:
            return None
        return {row.outcome: float(row.prob) for row in rows}

    async def _team_names(
        self, session: AsyncSession, home_id: UUID, away_id: UUID
    ) -> tuple[str, str]:
        result = (
            await session.execute(
                select(TeamORM.id, TeamORM.name).where(TeamORM.id.in_([home_id, away_id]))
            )
        ).all()
        names: dict[UUID, str] = {row[0]: row[1] for row in result}
        return names.get(home_id, "?"), names.get(away_id, "?")

    @staticmethod
    def _match_to_dict(match: MatchORM, home: str, away: str) -> dict[str, str | int | None]:
        return {
            "id": str(match.id),
            "home_team": home,
            "away_team": away,
            "home_goals": match.home_goals,
            "away_goals": match.away_goals,
        }

    async def _send_to_all(
        self,
        session: AsyncSession,
        subscriptions: list[PushSubscriptionORM],
        payload: Mapping[str, object],
    ) -> tuple[int, int]:
        ok = 0
        deleted = 0
        for sub in subscriptions:
            sub_info = {
                "endpoint": sub.endpoint,
                "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
            }
            try:
                webpush(
                    subscription_info=sub_info,
                    data=json.dumps(payload),
                    vapid_private_key=self._vapid.private_key,
                    vapid_claims={"sub": self._vapid.subject},
                )
                ok += 1
            except WebPushException as e:
                status = getattr(getattr(e, "response", None), "status_code", None)
                if status == 410:
                    await session.delete(sub)
                    deleted += 1
                else:
                    log.warning("webpush failed for %s: %s", sub.endpoint, e)
            except Exception as e:
                log.warning("unexpected push error for %s: %s", sub.endpoint, e)
        return ok, deleted

    async def _record_notification(
        self, session: AsyncSession, match_id: UUID, kind: str, n_recipients: int
    ) -> None:
        try:
            session.add(
                MatchNotificationORM(
                    match_id=match_id,
                    kind=kind,
                    n_recipients=n_recipients,
                    sent_at=datetime.now(UTC),
                )
            )
            await session.flush()
        except IntegrityError:
            await session.rollback()
            log.info(
                "match_notification already exists for %s/%s, skipping",
                match_id,
                kind,
            )
