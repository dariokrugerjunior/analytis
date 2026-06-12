# Plano 1 — Fundação + Ingestão

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Esqueleto de projeto Python funcional com Postgres modelado, CLI/API minimalistas operacionais, ingestão Football-Data.org + ELO funcionando, e backfill das Copas 2018/2022 carregado no banco.

**Architecture:** Monolito modular Python (Pydantic/SQLAlchemy/FastAPI/Typer) sobre Postgres 16 em Docker. Domain entities puras (Pydantic) separadas de ORM (SQLAlchemy 2.x); repositórios escondem persistência. Ingestão via padrão Adapter — cada fonte implementa interface comum; pipeline orquestra com idempotência (UPSERT) + rate limiting + retry. APScheduler embarcado dispara jobs periódicos.

**Tech Stack:** Python 3.12, uv, Ruff, Mypy strict, Pytest + hypothesis + respx + testcontainers, FastAPI, SQLAlchemy 2.x, Pydantic 2, Alembic, Typer, APScheduler, httpx, structlog, Docker Compose, Postgres 16.

**Spec:** `docs/superpowers/specs/2026-06-12-football-analytics-design.md` (§1-5, §10, §11 sem 1-2).

---

## Estrutura de arquivos criada neste plano

```
analytis/
├── .github/workflows/ci.yml
├── .gitignore
├── .pre-commit-config.yaml
├── .env.example
├── README.md
├── docker-compose.yml
├── docker-compose.test.yml
├── pyproject.toml
├── alembic.ini
├── migrations/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/0001_initial_schema.py
├── src/analytis/
│   ├── __init__.py
│   ├── config.py
│   ├── logging.py
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── ids.py
│   │   ├── competition.py
│   │   ├── team.py
│   │   ├── player.py
│   │   ├── venue.py
│   │   ├── referee.py
│   │   ├── match.py
│   │   ├── season.py
│   │   ├── ingestion.py
│   │   └── snapshots.py            # FeatureSnapshot, ModelVersion, Prediction
│   ├── persistence/
│   │   ├── __init__.py
│   │   ├── engine.py
│   │   ├── unit_of_work.py
│   │   ├── orm/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── catalog.py          # Competition, Season, Team, Player, Venue, Referee
│   │   │   ├── matches.py
│   │   │   ├── inference.py        # FeatureSnapshot, ModelVersion, Prediction
│   │   │   └── ingestion.py        # DataSource, IngestionRun
│   │   └── repositories/
│   │       ├── __init__.py
│   │       ├── base.py
│   │       ├── competition.py
│   │       ├── team.py
│   │       ├── match.py
│   │       ├── ingestion.py
│   │       └── reference.py
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── ports.py                # DataSourceAdapter Protocol + DTOs
│   │   ├── rate_limiter.py
│   │   ├── retry.py
│   │   ├── pipeline.py
│   │   ├── scheduler.py
│   │   └── adapters/
│   │       ├── __init__.py
│   │       ├── football_data.py
│   │       └── elo_ratings.py
│   ├── application/
│   │   ├── __init__.py
│   │   ├── ingest_fixtures.py
│   │   ├── ingest_backfill.py
│   │   └── ingest_elo.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── deps.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── health.py
│   └── cli/
│       ├── __init__.py
│       ├── app.py                  # Typer root
│       ├── db.py
│       ├── api.py
│       └── ingest.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── unit/
    │   ├── domain/test_match.py
    │   ├── ingestion/test_rate_limiter.py
    │   ├── ingestion/test_retry.py
    │   ├── ingestion/adapters/test_football_data.py
    │   └── ingestion/adapters/test_elo_ratings.py
    └── integration/
        ├── persistence/test_repositories.py
        ├── ingestion/test_pipeline.py
        └── api/test_health.py
```

---

## Convenções gerais (válidas para todas as tasks)

- **Linguagem Python:** 3.12+ exigida; nada de `from __future__ import annotations` (Pydantic 2 funciona bem com tipos atuais).
- **TDD obrigatório** em código de domínio, persistência, ingestão e API. Testes vão antes do código de produção.
- **Commits frequentes:** cada task termina num commit isolado. Mensagens em inglês no formato `<tipo>: <mensagem curta>` (tipos: `feat`, `fix`, `chore`, `docs`, `test`, `refactor`).
- **Co-autoria:** **NÃO** adicionar trailer `Co-Authored-By: Claude...` nos commits deste plano (o usuário só quer no commit do design — ele vai ajustar essa preferência conforme o uso).
- **Comandos de teste:** rodar sempre com `uv run pytest <path> -v`. Nada de `pytest` direto sem `uv run`.
- **Postgres:** a maioria dos testes integration usa `testcontainers`. O dev DB local usa `docker-compose.yml`. O CI usa serviço Postgres do GitHub Actions.

---

## Task 1: Bootstrap do projeto Python (pyproject.toml + estrutura)

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `src/analytis/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/unit/__init__.py`
- Create: `tests/integration/__init__.py`

- [ ] **Step 1: Criar `.gitignore`**

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
.venv/
.venv*/

# Tooling
.ruff_cache/
.mypy_cache/
.pytest_cache/
.coverage
htmlcov/
coverage.xml

# Env
.env
.env.*
!.env.example

# Project artifacts
models/
data/cache/
*.pickle
*.pkl

# OS / IDE
.DS_Store
Thumbs.db
.idea/
.vscode/

# Logs
*.log
```

- [ ] **Step 2: Criar `pyproject.toml`**

```toml
[project]
name = "analytis"
version = "0.1.0"
description = "Football analytics backend platform — pre-match probabilistic predictions"
readme = "README.md"
requires-python = ">=3.12"
license = { text = "Proprietary" }

dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "sqlalchemy[asyncio]>=2.0.36",
    "psycopg[binary,pool]>=3.2.3",
    "alembic>=1.14.0",
    "pydantic>=2.9.0",
    "pydantic-settings>=2.6.0",
    "typer>=0.13.0",
    "rich>=13.9.0",
    "apscheduler>=3.10.4",
    "httpx>=0.27.2",
    "structlog>=24.4.0",
    "tenacity>=9.0.0",
]

[dependency-groups]
dev = [
    "pytest>=8.3.3",
    "pytest-cov>=6.0.0",
    "pytest-asyncio>=0.24.0",
    "hypothesis>=6.115.0",
    "respx>=0.21.1",
    "testcontainers[postgres]>=4.8.2",
    "ruff>=0.7.4",
    "mypy>=1.13.0",
    "types-python-dateutil>=2.9.0",
    "pre-commit>=4.0.1",
]

[project.scripts]
analytis = "analytis.cli.app:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/analytis"]

[tool.ruff]
target-version = "py312"
line-length = 100
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "B", "I", "UP", "SIM", "RUF", "N", "C4", "PT", "TID"]
ignore = ["E501"]  # line length handled by formatter

[tool.ruff.lint.per-file-ignores]
"tests/**/*" = ["B011"]

[tool.ruff.format]
quote-style = "double"

[tool.mypy]
python_version = "3.12"
strict = true
warn_unused_ignores = true
warn_return_any = true
disallow_untyped_decorators = false
plugins = ["pydantic.mypy"]

[[tool.mypy.overrides]]
module = ["apscheduler.*", "testcontainers.*"]
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --strict-markers --strict-config"
markers = [
    "integration: tests that require external services (Postgres, network)",
]
asyncio_mode = "auto"
filterwarnings = ["error"]

[tool.coverage.run]
source = ["src/analytis"]
branch = true

[tool.coverage.report]
exclude_lines = ["pragma: no cover", "if TYPE_CHECKING:", "raise NotImplementedError"]
```

- [ ] **Step 3: Criar `src/analytis/__init__.py`**

```python
"""analytis — football analytics backend platform."""

__version__ = "0.1.0"
```

- [ ] **Step 4: Criar `tests/__init__.py`, `tests/unit/__init__.py`, `tests/integration/__init__.py`** (cada um vazio)

```python
```

- [ ] **Step 5: Criar `tests/conftest.py` (mínimo por enquanto)**

```python
"""Shared pytest fixtures."""

import pytest


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
```

- [ ] **Step 6: Instalar dependências e validar lint/types/tests**

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run mypy src tests
uv run pytest -v
```

Expected:
- `uv sync` cria `.venv/` e `uv.lock`
- Ruff: clean (sem arquivos para lintar)
- Mypy: clean
- Pytest: "no tests ran" (0 testes, exit 5)

Aceite exit 5 do pytest como sucesso neste momento; nas próximas tasks haverá testes.

- [ ] **Step 7: Commit**

```bash
git add .gitignore pyproject.toml uv.lock src/analytis/__init__.py tests/
git commit -m "chore: bootstrap python project with uv, ruff, mypy, pytest"
```

---

## Task 2: Docker Compose com Postgres 16

**Files:**
- Create: `docker-compose.yml`
- Create: `docker-compose.test.yml`
- Create: `.env.example`

- [ ] **Step 1: Criar `docker-compose.yml`**

```yaml
services:
  postgres:
    image: postgres:16-alpine
    container_name: analytis-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: analytis
      POSTGRES_PASSWORD: analytis_dev
      POSTGRES_DB: analytis
    ports:
      - "5432:5432"
    volumes:
      - analytis-pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U analytis -d analytis"]
      interval: 5s
      timeout: 5s
      retries: 10

volumes:
  analytis-pgdata:
```

- [ ] **Step 2: Criar `docker-compose.test.yml`** (Postgres temporário para tests locais sem testcontainers)

```yaml
services:
  postgres-test:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: analytis
      POSTGRES_PASSWORD: analytis_test
      POSTGRES_DB: analytis_test
    ports:
      - "5433:5432"
    tmpfs:
      - /var/lib/postgresql/data
```

- [ ] **Step 3: Criar `.env.example`**

```
# Database
ANALYTIS_DATABASE_URL=postgresql+psycopg://analytis:analytis_dev@localhost:5432/analytis

# API
ANALYTIS_API_KEY=change-me-local-dev

# Logging
ANALYTIS_LOG_LEVEL=INFO
ANALYTIS_LOG_FORMAT=console

# External sources
ANALYTIS_FOOTBALL_DATA_API_KEY=
ANALYTIS_ELO_RATINGS_URL=http://www.eloratings.net/World.tsv
```

- [ ] **Step 4: Subir e validar Postgres**

```bash
docker compose up -d postgres
docker compose ps
docker compose exec postgres psql -U analytis -d analytis -c "SELECT version();"
```

Expected: Postgres healthy + retorna versão "PostgreSQL 16.x".

- [ ] **Step 5: Commit**

```bash
git add docker-compose.yml docker-compose.test.yml .env.example
git commit -m "chore: add docker-compose with postgres 16"
```

---

## Task 3: Configuração centralizada (Pydantic Settings)

**Files:**
- Create: `src/analytis/config.py`
- Test: `tests/unit/test_config.py`

- [ ] **Step 1: Escrever o teste primeiro — `tests/unit/test_config.py`**

```python
"""Tests for Settings loader."""

import pytest
from pydantic import ValidationError

from analytis.config import Settings


def test_settings_loads_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "ANALYTIS_DATABASE_URL", "postgresql+psycopg://u:p@h:5432/d"
    )
    monkeypatch.setenv("ANALYTIS_API_KEY", "secret-key")

    settings = Settings()

    assert settings.database_url == "postgresql+psycopg://u:p@h:5432/d"
    assert settings.api_key.get_secret_value() == "secret-key"
    assert settings.log_level == "INFO"
    assert settings.log_format == "console"


def test_settings_requires_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANALYTIS_DATABASE_URL", raising=False)
    monkeypatch.delenv("ANALYTIS_API_KEY", raising=False)

    with pytest.raises(ValidationError):
        Settings()


def test_settings_log_level_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANALYTIS_DATABASE_URL", "postgresql+psycopg://u:p@h/d")
    monkeypatch.setenv("ANALYTIS_API_KEY", "x")
    monkeypatch.setenv("ANALYTIS_LOG_LEVEL", "TRACE")

    with pytest.raises(ValidationError):
        Settings()
```

- [ ] **Step 2: Rodar test para verificar falha**

```bash
uv run pytest tests/unit/test_config.py -v
```

Expected: ImportError ou ModuleNotFoundError em `analytis.config`.

- [ ] **Step 3: Implementar `src/analytis/config.py`**

```python
"""Centralized application configuration loaded from environment."""

from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings — single source of truth for env-driven config."""

    model_config = SettingsConfigDict(
        env_prefix="ANALYTIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    database_url: str
    api_key: SecretStr

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["console", "json"] = "console"

    football_data_api_key: SecretStr | None = None
    elo_ratings_url: str = "http://www.eloratings.net/World.tsv"


def get_settings() -> Settings:
    """Factory for DI — keeps `Settings()` call in one place."""
    return Settings()  # type: ignore[call-arg]
```

- [ ] **Step 4: Rodar testes**

```bash
uv run pytest tests/unit/test_config.py -v
uv run mypy src tests
uv run ruff check .
```

Expected: 3 tests passed, mypy clean, ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/analytis/config.py tests/unit/test_config.py
git commit -m "feat(config): add Pydantic Settings loader with validation"
```

---

## Task 4: Logging estruturado (structlog)

**Files:**
- Create: `src/analytis/logging.py`
- Test: `tests/unit/test_logging.py`

- [ ] **Step 1: Escrever o teste — `tests/unit/test_logging.py`**

```python
"""Tests for structured logging setup."""

import logging

import structlog

from analytis.logging import configure_logging, get_logger


def test_configure_logging_console_format() -> None:
    configure_logging(level="INFO", fmt="console")
    logger = get_logger("test")
    assert isinstance(logger, structlog.stdlib.BoundLogger)


def test_configure_logging_json_format() -> None:
    configure_logging(level="DEBUG", fmt="json")
    root = logging.getLogger()
    assert root.level == logging.DEBUG


def test_get_logger_returns_bound() -> None:
    configure_logging(level="INFO", fmt="console")
    logger = get_logger(__name__)
    logger = logger.bind(component="test")
    assert "component" in logger._context
```

- [ ] **Step 2: Verificar falha**

```bash
uv run pytest tests/unit/test_logging.py -v
```

Expected: ImportError em `analytis.logging`.

- [ ] **Step 3: Implementar `src/analytis/logging.py`**

```python
"""Structured logging configuration based on structlog."""

import logging
import sys
from typing import Literal

import structlog


def configure_logging(
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO",
    fmt: Literal["console", "json"] = "console",
) -> None:
    """Configure stdlib logging + structlog with a single processor chain."""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
        force=True,
    )

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    renderer: structlog.types.Processor
    if fmt == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger bound to `name`."""
    return structlog.get_logger(name)
```

- [ ] **Step 4: Rodar testes + qualidade**

```bash
uv run pytest tests/unit/test_logging.py -v
uv run mypy src tests
uv run ruff check .
```

Expected: 3 tests passed.

- [ ] **Step 5: Commit**

```bash
git add src/analytis/logging.py tests/unit/test_logging.py
git commit -m "feat(logging): structured logging via structlog"
```

---

## Task 5: Pre-commit hooks

**Files:**
- Create: `.pre-commit-config.yaml`

- [ ] **Step 1: Criar `.pre-commit-config.yaml`**

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-added-large-files
        args: ["--maxkb=512"]
      - id: check-merge-conflict
      - id: mixed-line-ending
        args: ["--fix=lf"]

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.7.4
    hooks:
      - id: ruff
        args: ["--fix"]
      - id: ruff-format

  - repo: local
    hooks:
      - id: mypy
        name: mypy
        entry: uv run mypy src tests
        language: system
        types: [python]
        pass_filenames: false
```

- [ ] **Step 2: Instalar e validar**

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

Expected: hooks rodam e arquivos passam (alguns podem ser auto-corrigidos).

- [ ] **Step 3: Commit**

```bash
git add .pre-commit-config.yaml
git commit -m "chore: configure pre-commit with ruff, mypy and basic hygiene"
```

---

## Task 6: Domain entities — catálogo (Pydantic)

**Files:**
- Create: `src/analytis/domain/__init__.py`
- Create: `src/analytis/domain/ids.py`
- Create: `src/analytis/domain/competition.py`
- Create: `src/analytis/domain/team.py`
- Create: `src/analytis/domain/player.py`
- Create: `src/analytis/domain/venue.py`
- Create: `src/analytis/domain/referee.py`
- Create: `src/analytis/domain/season.py`
- Test: `tests/unit/domain/__init__.py`
- Test: `tests/unit/domain/test_catalog.py`

- [ ] **Step 1: Escrever teste — `tests/unit/domain/test_catalog.py`**

```python
"""Tests for catalog domain entities."""

from uuid import uuid4

import pytest

from analytis.domain.competition import Competition, CompetitionType
from analytis.domain.player import Player, PreferredFoot
from analytis.domain.referee import Referee
from analytis.domain.season import Season
from analytis.domain.team import Team, TeamType
from analytis.domain.venue import Venue


def test_competition_minimal() -> None:
    c = Competition(
        name="FIFA World Cup 2026",
        slug="wc-2026",
        competition_type=CompetitionType.SELECAO,
        country="INTL",
    )
    assert c.name == "FIFA World Cup 2026"
    assert c.competition_type is CompetitionType.SELECAO


def test_competition_rejects_empty_name() -> None:
    with pytest.raises(ValueError):
        Competition(
            name="",
            slug="x",
            competition_type=CompetitionType.CLUBE,
            country="BRA",
        )


def test_team_minimal() -> None:
    t = Team(name="Brazil", short_name="BRA", team_type=TeamType.SELECAO, country="BRA")
    assert t.team_type is TeamType.SELECAO


def test_team_external_ids_roundtrip() -> None:
    t = Team(
        name="Flamengo",
        short_name="FLA",
        team_type=TeamType.CLUBE,
        country="BRA",
        external_ids={"footballdata": "127", "fbref": "639950ae"},
    )
    assert t.external_ids["footballdata"] == "127"


def test_player_with_preferred_foot() -> None:
    p = Player(name="Vinicius Jr", preferred_foot=PreferredFoot.RIGHT, position="LW")
    assert p.preferred_foot is PreferredFoot.RIGHT


def test_venue_altitude_nonnegative() -> None:
    Venue(name="Estadio Azteca", city="Mexico City", country="MEX", altitude_m=2240)
    with pytest.raises(ValueError):
        Venue(name="Submarine", city="Atlantis", country="ATL", altitude_m=-10)


def test_referee_stats_default_none() -> None:
    r = Referee(name="Joel Aguilar", country="SLV")
    assert r.cards_per_game is None


def test_season_label() -> None:
    s = Season(label="2026", competition_id=uuid4())
    assert s.label == "2026"
```

- [ ] **Step 2: Verificar falha**

```bash
uv run pytest tests/unit/domain/test_catalog.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implementar `src/analytis/domain/__init__.py`** (vazio)

```python
```

- [ ] **Step 4: Implementar `src/analytis/domain/ids.py`** (alias semântico para UUID)

```python
"""Type aliases for entity IDs across the domain."""

from uuid import UUID

CompetitionId = UUID
SeasonId = UUID
TeamId = UUID
PlayerId = UUID
VenueId = UUID
RefereeId = UUID
MatchId = UUID
FeatureSnapshotId = UUID
ModelVersionId = UUID
PredictionId = UUID
DataSourceId = UUID
IngestionRunId = UUID
```

- [ ] **Step 5: Implementar `src/analytis/domain/competition.py`**

```python
"""Competition domain entity."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from analytis.domain.ids import CompetitionId


class CompetitionType(StrEnum):
    SELECAO = "selecao"
    CLUBE = "clube"


class Competition(BaseModel):
    """Top-level competition (league, cup, international tournament)."""

    model_config = ConfigDict(frozen=False, str_strip_whitespace=True)

    id: CompetitionId = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9\-]+$")
    competition_type: CompetitionType
    country: str = Field(min_length=2, max_length=10, description="ISO-3 or 'INTL'")
    external_ids: dict[str, str] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
```

- [ ] **Step 6: Implementar `src/analytis/domain/team.py`**

```python
"""Team domain entity."""

from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from analytis.domain.ids import TeamId


class TeamType(StrEnum):
    SELECAO = "selecao"
    CLUBE = "clube"


class Team(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: TeamId = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=200)
    short_name: str = Field(min_length=1, max_length=50)
    team_type: TeamType
    country: str = Field(min_length=2, max_length=10)
    external_ids: dict[str, str] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
```

- [ ] **Step 7: Implementar `src/analytis/domain/player.py`**

```python
"""Player domain entity."""

from datetime import date, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from analytis.domain.ids import PlayerId


class PreferredFoot(StrEnum):
    LEFT = "left"
    RIGHT = "right"
    BOTH = "both"


class Player(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: PlayerId = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=200)
    date_of_birth: date | None = None
    nationality: str | None = Field(default=None, max_length=10)
    position: str | None = Field(default=None, max_length=10)
    preferred_foot: PreferredFoot | None = None
    external_ids: dict[str, str] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
```

- [ ] **Step 8: Implementar `src/analytis/domain/venue.py`**

```python
"""Venue (stadium) domain entity."""

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from analytis.domain.ids import VenueId


class Venue(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: VenueId = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=200)
    city: str = Field(min_length=1, max_length=100)
    country: str = Field(min_length=2, max_length=10)
    altitude_m: int = Field(default=0, ge=0)
    capacity: int | None = Field(default=None, ge=0)
    external_ids: dict[str, str] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
```

- [ ] **Step 9: Implementar `src/analytis/domain/referee.py`**

```python
"""Referee domain entity."""

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from analytis.domain.ids import RefereeId


class Referee(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: RefereeId = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=200)
    country: str = Field(min_length=2, max_length=10)
    cards_per_game: float | None = Field(default=None, ge=0)
    penalties_per_game: float | None = Field(default=None, ge=0)
    external_ids: dict[str, str] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
```

- [ ] **Step 10: Implementar `src/analytis/domain/season.py`**

```python
"""Season domain entity."""

from datetime import date, datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from analytis.domain.ids import CompetitionId, SeasonId


class Season(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: SeasonId = Field(default_factory=uuid4)
    competition_id: CompetitionId
    label: str = Field(min_length=1, max_length=50)
    start_date: date | None = None
    end_date: date | None = None
    external_ids: dict[str, str] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
```

- [ ] **Step 11: Criar `tests/unit/domain/__init__.py`** (vazio)

```python
```

- [ ] **Step 12: Rodar testes**

```bash
uv run pytest tests/unit/domain/test_catalog.py -v
uv run mypy src tests
uv run ruff check .
```

Expected: 8 tests passed.

- [ ] **Step 13: Commit**

```bash
git add src/analytis/domain tests/unit/domain
git commit -m "feat(domain): add catalog entities (competition, team, player, venue, referee, season)"
```

---

## Task 7: Domain entities — match e ingestão

**Files:**
- Create: `src/analytis/domain/match.py`
- Create: `src/analytis/domain/ingestion.py`
- Test: `tests/unit/domain/test_match.py`
- Test: `tests/unit/domain/test_ingestion.py`

- [ ] **Step 1: Escrever testes — `tests/unit/domain/test_match.py`**

```python
"""Tests for Match domain entity."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from analytis.domain.match import Match, MatchStatus


def test_match_minimal() -> None:
    m = Match(
        season_id=uuid4(),
        home_team_id=uuid4(),
        away_team_id=uuid4(),
        kickoff_utc=datetime(2026, 6, 15, 20, 0, tzinfo=UTC),
    )
    assert m.status is MatchStatus.SCHEDULED


def test_match_rejects_same_team() -> None:
    tid = uuid4()
    with pytest.raises(ValueError, match="cannot play itself"):
        Match(
            season_id=uuid4(),
            home_team_id=tid,
            away_team_id=tid,
            kickoff_utc=datetime(2026, 6, 15, 20, 0, tzinfo=UTC),
        )


def test_match_finished_requires_goals() -> None:
    m = Match(
        season_id=uuid4(),
        home_team_id=uuid4(),
        away_team_id=uuid4(),
        kickoff_utc=datetime(2026, 6, 15, 20, 0, tzinfo=UTC),
        status=MatchStatus.FINISHED,
        home_goals=2,
        away_goals=1,
    )
    assert m.home_goals == 2


def test_match_finished_rejects_missing_goals() -> None:
    with pytest.raises(ValueError, match="finished match requires goals"):
        Match(
            season_id=uuid4(),
            home_team_id=uuid4(),
            away_team_id=uuid4(),
            kickoff_utc=datetime(2026, 6, 15, 20, 0, tzinfo=UTC),
            status=MatchStatus.FINISHED,
        )


def test_match_naive_kickoff_rejected() -> None:
    with pytest.raises(ValueError):
        Match(
            season_id=uuid4(),
            home_team_id=uuid4(),
            away_team_id=uuid4(),
            kickoff_utc=datetime(2026, 6, 15, 20, 0),
        )
```

- [ ] **Step 2: Escrever teste — `tests/unit/domain/test_ingestion.py`**

```python
"""Tests for ingestion-tracking domain entities."""

from datetime import UTC, datetime

import pytest

from analytis.domain.ingestion import (
    DataSource,
    IngestionRun,
    IngestionStatus,
)


def test_data_source_minimal() -> None:
    ds = DataSource(source_id="footballdata", display_name="Football-Data.org")
    assert ds.source_id == "footballdata"


def test_data_source_id_format() -> None:
    with pytest.raises(ValueError):
        DataSource(source_id="Football Data", display_name="x")


def test_ingestion_run_default_status() -> None:
    r = IngestionRun(
        data_source_id="footballdata",
        job_name="ingest:fixtures",
        started_at=datetime(2026, 6, 12, tzinfo=UTC),
    )
    assert r.status is IngestionStatus.RUNNING


def test_ingestion_run_failed_requires_error() -> None:
    with pytest.raises(ValueError, match="error_message required"):
        IngestionRun(
            data_source_id="footballdata",
            job_name="ingest:fixtures",
            started_at=datetime(2026, 6, 12, tzinfo=UTC),
            status=IngestionStatus.FAILED,
        )
```

- [ ] **Step 3: Verificar falha**

```bash
uv run pytest tests/unit/domain/test_match.py tests/unit/domain/test_ingestion.py -v
```

Expected: ImportError.

- [ ] **Step 4: Implementar `src/analytis/domain/match.py`**

```python
"""Match domain entity."""

from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from analytis.domain.ids import (
    MatchId,
    RefereeId,
    SeasonId,
    TeamId,
    VenueId,
)


class MatchStatus(StrEnum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"


class Match(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: MatchId = Field(default_factory=uuid4)
    season_id: SeasonId
    home_team_id: TeamId
    away_team_id: TeamId
    kickoff_utc: datetime
    venue_id: VenueId | None = None
    referee_id: RefereeId | None = None
    is_home_neutral: bool = False
    status: MatchStatus = MatchStatus.SCHEDULED
    home_goals: int | None = Field(default=None, ge=0)
    away_goals: int | None = Field(default=None, ge=0)
    home_corners: int | None = Field(default=None, ge=0)
    away_corners: int | None = Field(default=None, ge=0)
    external_ids: dict[str, str] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @model_validator(mode="after")
    def _validate_business_rules(self) -> "Match":
        if self.home_team_id == self.away_team_id:
            raise ValueError("a team cannot play itself")
        if self.kickoff_utc.tzinfo is None:
            raise ValueError("kickoff_utc must be timezone-aware UTC")
        if self.status is MatchStatus.FINISHED and (
            self.home_goals is None or self.away_goals is None
        ):
            raise ValueError("finished match requires goals on both sides")
        return self
```

- [ ] **Step 5: Implementar `src/analytis/domain/ingestion.py`**

```python
"""Domain entities for ingestion observability."""

import re
from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from analytis.domain.ids import IngestionRunId

_SOURCE_ID_PATTERN = re.compile(r"^[a-z0-9_\-]+$")


class IngestionStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class DataSource(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    source_id: str = Field(min_length=2, max_length=50)
    display_name: str = Field(min_length=1, max_length=200)
    homepage_url: str | None = None
    created_at: datetime | None = None

    @model_validator(mode="after")
    def _validate_id(self) -> "DataSource":
        if not _SOURCE_ID_PATTERN.match(self.source_id):
            raise ValueError(
                "source_id must match [a-z0-9_-] (lowercase, no spaces)"
            )
        return self


class IngestionRun(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: IngestionRunId = Field(default_factory=uuid4)
    data_source_id: str
    job_name: str = Field(min_length=1, max_length=100)
    started_at: datetime
    finished_at: datetime | None = None
    status: IngestionStatus = IngestionStatus.RUNNING
    records_touched: int = Field(default=0, ge=0)
    error_message: str | None = None
    payload_hash: str | None = None

    @model_validator(mode="after")
    def _validate_status(self) -> "IngestionRun":
        if self.status is IngestionStatus.FAILED and not self.error_message:
            raise ValueError("error_message required when status=failed")
        if self.status is IngestionStatus.SUCCEEDED and not self.finished_at:
            raise ValueError("finished_at required when status=succeeded")
        return self
```

- [ ] **Step 6: Rodar testes**

```bash
uv run pytest tests/unit/domain -v
uv run mypy src tests
uv run ruff check .
```

Expected: 13 tests passed (5 catalog + 5 match + 4 ingestion... wait, ajustar: 8 catalog + 5 match + 4 ingestion = 17).

- [ ] **Step 7: Commit**

```bash
git add src/analytis/domain/match.py src/analytis/domain/ingestion.py tests/unit/domain/test_match.py tests/unit/domain/test_ingestion.py
git commit -m "feat(domain): add match and ingestion-tracking entities"
```

---

## Task 8: Domain entities — inferência (snapshots, model_version, prediction)

**Files:**
- Create: `src/analytis/domain/snapshots.py`
- Test: `tests/unit/domain/test_snapshots.py`

- [ ] **Step 1: Escrever teste — `tests/unit/domain/test_snapshots.py`**

```python
"""Tests for inference-side entities (snapshots, model versions, predictions)."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from analytis.domain.snapshots import (
    FeatureSnapshot,
    ModelVersion,
    Prediction,
    PredictionMarket,
)


def test_feature_snapshot_minimal() -> None:
    s = FeatureSnapshot(
        match_id=uuid4(),
        snapshot_taken_at=datetime(2026, 6, 15, 16, 0, tzinfo=UTC),
        features={"elo_diff": 184.0, "rest_days_home": 6.0},
    )
    assert s.features["elo_diff"] == 184.0


def test_feature_snapshot_taken_at_must_be_aware() -> None:
    with pytest.raises(ValueError):
        FeatureSnapshot(
            match_id=uuid4(),
            snapshot_taken_at=datetime(2026, 6, 15, 16, 0),
            features={},
        )


def test_model_version_minimal() -> None:
    mv = ModelVersion(
        name="ensemble-v0.3.1",
        family="ensemble",
        git_sha="abc1234",
        hyperparams={"learning_rate": 0.05},
        metrics={"brier_1x2": 0.21},
    )
    assert mv.is_promoted is False


def test_prediction_probability_range() -> None:
    Prediction(
        match_id=uuid4(),
        market=PredictionMarket.MATCH_RESULT,
        outcome="home",
        prob=0.527,
        ci_low=0.471,
        ci_high=0.583,
        model_version_id=uuid4(),
        feature_snapshot_id=uuid4(),
        created_at=datetime(2026, 6, 15, 16, 0, tzinfo=UTC),
    )


def test_prediction_rejects_out_of_range_prob() -> None:
    with pytest.raises(ValueError):
        Prediction(
            match_id=uuid4(),
            market=PredictionMarket.BTTS,
            outcome="yes",
            prob=1.2,
            ci_low=1.1,
            ci_high=1.3,
            model_version_id=uuid4(),
            feature_snapshot_id=uuid4(),
            created_at=datetime(2026, 6, 15, 16, 0, tzinfo=UTC),
        )


def test_prediction_rejects_ci_inverted() -> None:
    with pytest.raises(ValueError, match="ci_low must be <= ci_high"):
        Prediction(
            match_id=uuid4(),
            market=PredictionMarket.OVER_UNDER_GOALS,
            outcome="over_2.5",
            prob=0.5,
            ci_low=0.7,
            ci_high=0.3,
            model_version_id=uuid4(),
            feature_snapshot_id=uuid4(),
            created_at=datetime(2026, 6, 15, 16, 0, tzinfo=UTC),
        )
```

- [ ] **Step 2: Verificar falha**

```bash
uv run pytest tests/unit/domain/test_snapshots.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implementar `src/analytis/domain/snapshots.py`**

```python
"""Inference-side domain entities: feature snapshots, model versions, predictions."""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from analytis.domain.ids import (
    FeatureSnapshotId,
    MatchId,
    ModelVersionId,
    PredictionId,
)


class PredictionMarket(StrEnum):
    MATCH_RESULT = "1x2"
    OVER_UNDER_GOALS = "over_under_goals"
    BTTS = "btts"
    CORNERS_TOTAL = "corners_total"


class FeatureSnapshot(BaseModel):
    """Immutable snapshot of all features used in one scoring pass."""

    model_config = ConfigDict(frozen=True)

    id: FeatureSnapshotId = Field(default_factory=uuid4)
    match_id: MatchId
    snapshot_taken_at: datetime
    features: dict[str, Any]
    code_version: str | None = None

    @model_validator(mode="after")
    def _validate_aware(self) -> "FeatureSnapshot":
        if self.snapshot_taken_at.tzinfo is None:
            raise ValueError("snapshot_taken_at must be timezone-aware")
        return self


class ModelVersion(BaseModel):
    """Versioned, persisted record of a trained model."""

    model_config = ConfigDict(str_strip_whitespace=True)

    id: ModelVersionId = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=200)
    family: str = Field(min_length=1, max_length=100)
    git_sha: str = Field(min_length=4, max_length=40)
    hyperparams: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, float] = Field(default_factory=dict)
    artifact_path: str | None = None
    trained_at: datetime | None = None
    is_promoted: bool = False


class Prediction(BaseModel):
    """Immutable prediction for one (match, market, outcome) tuple."""

    model_config = ConfigDict(frozen=True)

    id: PredictionId = Field(default_factory=uuid4)
    match_id: MatchId
    market: PredictionMarket
    outcome: str = Field(min_length=1, max_length=50)
    prob: float = Field(ge=0.0, le=1.0)
    ci_low: float = Field(ge=0.0, le=1.0)
    ci_high: float = Field(ge=0.0, le=1.0)
    model_version_id: ModelVersionId
    feature_snapshot_id: FeatureSnapshotId
    created_at: datetime

    @model_validator(mode="after")
    def _validate(self) -> "Prediction":
        if self.ci_low > self.ci_high:
            raise ValueError("ci_low must be <= ci_high")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        return self
```

- [ ] **Step 4: Rodar testes**

```bash
uv run pytest tests/unit/domain -v
uv run mypy src tests
uv run ruff check .
```

Expected: total 23 tests passed (17 anteriores + 6 novos).

- [ ] **Step 5: Commit**

```bash
git add src/analytis/domain/snapshots.py tests/unit/domain/test_snapshots.py
git commit -m "feat(domain): add inference entities (snapshot, model version, prediction)"
```

---

## Task 9: SQLAlchemy ORM — base + catálogo

**Files:**
- Create: `src/analytis/persistence/__init__.py`
- Create: `src/analytis/persistence/orm/__init__.py`
- Create: `src/analytis/persistence/orm/base.py`
- Create: `src/analytis/persistence/orm/catalog.py`

- [ ] **Step 1: Criar `src/analytis/persistence/__init__.py`** (vazio)

```python
```

- [ ] **Step 2: Criar `src/analytis/persistence/orm/__init__.py`**

```python
"""SQLAlchemy ORM models — persistence layer."""

from analytis.persistence.orm.base import Base
from analytis.persistence.orm.catalog import (
    CompetitionORM,
    PlayerORM,
    RefereeORM,
    SeasonORM,
    TeamORM,
    VenueORM,
)

__all__ = [
    "Base",
    "CompetitionORM",
    "PlayerORM",
    "RefereeORM",
    "SeasonORM",
    "TeamORM",
    "VenueORM",
]
```

- [ ] **Step 3: Criar `src/analytis/persistence/orm/base.py`**

```python
"""Base ORM declarations and shared mixins."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata_obj = MetaData(naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    metadata = metadata_obj
    type_annotation_map = {
        dict[str, Any]: JSONB,
        dict[str, str]: JSONB,
        dict[str, float]: JSONB,
    }


def utcnow() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    """Provides created_at and updated_at columns managed by the DB."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


__all__ = ["Base", "TimestampMixin", "utcnow", "UUID"]
```

- [ ] **Step 4: Criar `src/analytis/persistence/orm/catalog.py`**

```python
"""ORM models for catalog entities."""

from datetime import date
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from analytis.persistence.orm.base import Base, TimestampMixin


class CompetitionORM(Base, TimestampMixin):
    __tablename__ = "competition"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    competition_type: Mapped[str] = mapped_column(String(20), nullable=False)
    country: Mapped[str] = mapped_column(String(10), nullable=False)
    external_ids: Mapped[dict[str, str]] = mapped_column(default=dict, nullable=False)

    seasons: Mapped[list["SeasonORM"]] = relationship(back_populates="competition")


class SeasonORM(Base, TimestampMixin):
    __tablename__ = "season"
    __table_args__ = (UniqueConstraint("competition_id", "label"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    competition_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("competition.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label: Mapped[str] = mapped_column(String(50), nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    external_ids: Mapped[dict[str, str]] = mapped_column(default=dict, nullable=False)

    competition: Mapped[CompetitionORM] = relationship(back_populates="seasons")


class TeamORM(Base, TimestampMixin):
    __tablename__ = "team"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    short_name: Mapped[str] = mapped_column(String(50), nullable=False)
    team_type: Mapped[str] = mapped_column(String(20), nullable=False)
    country: Mapped[str] = mapped_column(String(10), nullable=False)
    external_ids: Mapped[dict[str, str]] = mapped_column(default=dict, nullable=False)


class PlayerORM(Base, TimestampMixin):
    __tablename__ = "player"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(10), nullable=True)
    position: Mapped[str | None] = mapped_column(String(10), nullable=True)
    preferred_foot: Mapped[str | None] = mapped_column(String(10), nullable=True)
    external_ids: Mapped[dict[str, str]] = mapped_column(default=dict, nullable=False)


class VenueORM(Base, TimestampMixin):
    __tablename__ = "venue"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str] = mapped_column(String(10), nullable=False)
    altitude_m: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    external_ids: Mapped[dict[str, str]] = mapped_column(default=dict, nullable=False)


class RefereeORM(Base, TimestampMixin):
    __tablename__ = "referee"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    country: Mapped[str] = mapped_column(String(10), nullable=False)
    cards_per_game: Mapped[float | None] = mapped_column(nullable=True)
    penalties_per_game: Mapped[float | None] = mapped_column(nullable=True)
    external_ids: Mapped[dict[str, str]] = mapped_column(default=dict, nullable=False)


__all__: list[Any] = [
    "CompetitionORM",
    "SeasonORM",
    "TeamORM",
    "PlayerORM",
    "VenueORM",
    "RefereeORM",
]
```

- [ ] **Step 5: Validar import**

```bash
uv run python -c "from analytis.persistence.orm import CompetitionORM, TeamORM; print('ok')"
uv run mypy src
uv run ruff check .
```

Expected: prints "ok", mypy clean, ruff clean.

- [ ] **Step 6: Commit**

```bash
git add src/analytis/persistence/
git commit -m "feat(persistence): add ORM models for catalog entities"
```

---

## Task 10: SQLAlchemy ORM — matches, inference, ingestion

**Files:**
- Create: `src/analytis/persistence/orm/matches.py`
- Create: `src/analytis/persistence/orm/inference.py`
- Create: `src/analytis/persistence/orm/ingestion.py`
- Modify: `src/analytis/persistence/orm/__init__.py`

- [ ] **Step 1: Criar `src/analytis/persistence/orm/matches.py`**

```python
"""ORM models for matches and lineups."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from analytis.persistence.orm.base import Base, TimestampMixin


class MatchORM(Base, TimestampMixin):
    __tablename__ = "match"
    __table_args__ = (
        Index("ix_match_kickoff_utc", "kickoff_utc"),
        Index("ix_match_season_id", "season_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    season_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("season.id", ondelete="CASCADE"),
        nullable=False,
    )
    home_team_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("team.id", ondelete="RESTRICT"),
        nullable=False,
    )
    away_team_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("team.id", ondelete="RESTRICT"),
        nullable=False,
    )
    kickoff_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    venue_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("venue.id", ondelete="SET NULL"),
        nullable=True,
    )
    referee_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("referee.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_home_neutral: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="scheduled")
    home_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_corners: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_corners: Mapped[int | None] = mapped_column(Integer, nullable=True)
    external_ids: Mapped[dict[str, str]] = mapped_column(default=dict, nullable=False)

    lineups: Mapped[list["MatchLineupORM"]] = relationship(
        back_populates="match", cascade="all, delete-orphan"
    )


class MatchLineupORM(Base, TimestampMixin):
    __tablename__ = "match_lineup"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    match_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("match.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    team_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("team.id", ondelete="RESTRICT"),
        nullable=False,
    )
    formation: Mapped[str | None] = mapped_column(String(20), nullable=True)
    players: Mapped[dict[str, str]] = mapped_column(default=dict, nullable=False)
    """JSONB shape: {"starting": [player_id, ...], "bench": [...]}"""

    match: Mapped[MatchORM] = relationship(back_populates="lineups")
```

- [ ] **Step 2: Criar `src/analytis/persistence/orm/inference.py`**

```python
"""ORM models for inference-side entities (snapshots, models, predictions)."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from analytis.persistence.orm.base import Base, TimestampMixin


class FeatureSnapshotORM(Base):
    __tablename__ = "feature_snapshot"
    __table_args__ = (
        Index("ix_feature_snapshot_match", "match_id", "snapshot_taken_at"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    match_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("match.id", ondelete="CASCADE"),
        nullable=False,
    )
    snapshot_taken_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    features: Mapped[dict[str, Any]] = mapped_column(nullable=False)
    code_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class ModelVersionORM(Base, TimestampMixin):
    __tablename__ = "model_version"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    family: Mapped[str] = mapped_column(String(100), nullable=False)
    git_sha: Mapped[str] = mapped_column(String(40), nullable=False)
    hyperparams: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(default=dict, nullable=False)
    artifact_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    trained_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_promoted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class PredictionORM(Base):
    __tablename__ = "prediction"
    __table_args__ = (
        UniqueConstraint(
            "match_id",
            "market",
            "outcome",
            "model_version_id",
            "feature_snapshot_id",
        ),
        CheckConstraint("prob >= 0.0 AND prob <= 1.0", name="prob_range"),
        CheckConstraint("ci_low <= ci_high", name="ci_ordered"),
        Index("ix_prediction_match_market", "match_id", "market"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    match_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("match.id", ondelete="CASCADE"),
        nullable=False,
    )
    market: Mapped[str] = mapped_column(String(50), nullable=False)
    outcome: Mapped[str] = mapped_column(String(50), nullable=False)
    prob: Mapped[float] = mapped_column(Float, nullable=False)
    ci_low: Mapped[float] = mapped_column(Float, nullable=False)
    ci_high: Mapped[float] = mapped_column(Float, nullable=False)
    model_version_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("model_version.id", ondelete="RESTRICT"),
        nullable=False,
    )
    feature_snapshot_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("feature_snapshot.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
```

- [ ] **Step 3: Criar `src/analytis/persistence/orm/ingestion.py`**

```python
"""ORM models for ingestion observability."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from analytis.persistence.orm.base import Base, TimestampMixin


class DataSourceORM(Base, TimestampMixin):
    __tablename__ = "data_source"

    source_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    homepage_url: Mapped[str | None] = mapped_column(String(500), nullable=True)


class IngestionRunORM(Base):
    __tablename__ = "ingestion_run"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    data_source_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    job_name: Mapped[str] = mapped_column(String(100), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    records_touched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
```

- [ ] **Step 4: Atualizar `src/analytis/persistence/orm/__init__.py`**

```python
"""SQLAlchemy ORM models — persistence layer."""

from analytis.persistence.orm.base import Base
from analytis.persistence.orm.catalog import (
    CompetitionORM,
    PlayerORM,
    RefereeORM,
    SeasonORM,
    TeamORM,
    VenueORM,
)
from analytis.persistence.orm.inference import (
    FeatureSnapshotORM,
    ModelVersionORM,
    PredictionORM,
)
from analytis.persistence.orm.ingestion import DataSourceORM, IngestionRunORM
from analytis.persistence.orm.matches import MatchLineupORM, MatchORM

__all__ = [
    "Base",
    "CompetitionORM",
    "DataSourceORM",
    "FeatureSnapshotORM",
    "IngestionRunORM",
    "MatchLineupORM",
    "MatchORM",
    "ModelVersionORM",
    "PlayerORM",
    "PredictionORM",
    "RefereeORM",
    "SeasonORM",
    "TeamORM",
    "VenueORM",
]
```

- [ ] **Step 5: Validar import**

```bash
uv run python -c "from analytis.persistence.orm import MatchORM, PredictionORM, DataSourceORM; print('ok')"
uv run mypy src
uv run ruff check .
```

Expected: prints "ok".

- [ ] **Step 6: Commit**

```bash
git add src/analytis/persistence/orm/
git commit -m "feat(persistence): add ORM for matches, inference and ingestion"
```

---

## Task 11: Alembic init + primeira migration

**Files:**
- Create: `alembic.ini`
- Create: `migrations/env.py`
- Create: `migrations/script.py.mako`
- Create: `migrations/versions/0001_initial_schema.py`

- [ ] **Step 1: Inicializar Alembic**

```bash
uv run alembic init --template async migrations
```

Isso cria `alembic.ini`, `migrations/env.py`, `migrations/script.py.mako`, `migrations/versions/`.

- [ ] **Step 2: Substituir `alembic.ini`** com versão limpa

```ini
[alembic]
script_location = migrations
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url =

[post_write_hooks]
hooks = ruff
ruff.type = console_scripts
ruff.entrypoint = ruff
ruff.options = format REVISION_SCRIPT_FILENAME

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 3: Substituir `migrations/env.py`**

```python
"""Alembic environment — wires Settings + Base into the migration runtime."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from analytis.config import get_settings
from analytis.persistence.orm import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

- [ ] **Step 4: Gerar migration inicial**

```bash
docker compose up -d postgres
sleep 3
uv run alembic revision --autogenerate -m "initial schema"
```

Isso cria `migrations/versions/<hash>_initial_schema.py`. Renomeie o arquivo para `0001_initial_schema.py` e edite o atributo `revision` para `"0001"` e `down_revision` para `None`.

- [ ] **Step 5: Aplicar migration**

```bash
uv run alembic upgrade head
docker compose exec postgres psql -U analytis -d analytis -c "\dt"
```

Expected: lista de tabelas inclui `competition`, `season`, `team`, `player`, `venue`, `referee`, `match`, `match_lineup`, `feature_snapshot`, `model_version`, `prediction`, `data_source`, `ingestion_run`, `alembic_version`.

- [ ] **Step 6: Commit**

```bash
git add alembic.ini migrations/
git commit -m "feat(migrations): initialize alembic and create initial schema"
```

---

## Task 12: Unit of Work + engine

**Files:**
- Create: `src/analytis/persistence/engine.py`
- Create: `src/analytis/persistence/unit_of_work.py`
- Test: `tests/integration/persistence/__init__.py`
- Test: `tests/integration/persistence/test_unit_of_work.py`

- [ ] **Step 1: Criar `src/analytis/persistence/engine.py`**

```python
"""Async SQLAlchemy engine factory."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from analytis.config import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        settings.database_url,
        echo=False,
        future=True,
        pool_pre_ping=True,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        engine, expire_on_commit=False, autoflush=False, autocommit=False
    )


async def session_scope(
    factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Yield a session that commits on success and rolls back on error."""
    session = factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
```

- [ ] **Step 2: Criar `src/analytis/persistence/unit_of_work.py`**

```python
"""Unit of Work pattern — single session per use case."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class UnitOfWork:
    """Wraps a single AsyncSession, commits on success, rolls back on error."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    @property
    def session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("UnitOfWork must be entered before use")
        return self._session

    async def __aenter__(self) -> "UnitOfWork":
        self._session = self._session_factory()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._session is None:
            return
        try:
            if exc is None:
                await self._session.commit()
            else:
                await self._session.rollback()
        finally:
            await self._session.close()
            self._session = None


@asynccontextmanager
async def uow(
    factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[UnitOfWork]:
    """Context-manager helper around UnitOfWork."""
    async with UnitOfWork(factory) as u:
        yield u
```

- [ ] **Step 3: Criar `tests/integration/persistence/__init__.py`** (vazio)

```python
```

- [ ] **Step 4: Criar fixtures globais para Postgres em `tests/conftest.py`** (substituir conteúdo)

```python
"""Shared pytest fixtures."""

from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.postgres import PostgresContainer

from analytis.persistence.orm import Base


@pytest.fixture(scope="session")
def postgres_container() -> Iterator[PostgresContainer]:
    container = PostgresContainer("postgres:16-alpine", driver="psycopg")
    container.start()
    try:
        yield container
    finally:
        container.stop()


@pytest_asyncio.fixture(scope="session")
async def engine(postgres_container: PostgresContainer) -> AsyncIterator[AsyncEngine]:
    url = postgres_container.get_connection_url().replace(
        "postgresql+psycopg2", "postgresql+psycopg"
    )
    engine = create_async_engine(url, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


@pytest_asyncio.fixture(autouse=True)
async def _truncate_all(engine: AsyncEngine, request: pytest.FixtureRequest) -> None:
    """Wipe data between integration tests; no-op for unit tests."""
    if "integration" not in request.node.nodeid:
        return
    from sqlalchemy import text

    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(text(f'TRUNCATE TABLE "{table.name}" CASCADE'))
```

- [ ] **Step 5: Criar teste — `tests/integration/persistence/test_unit_of_work.py`**

```python
"""Integration tests for UnitOfWork."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.persistence.orm import TeamORM
from analytis.persistence.unit_of_work import UnitOfWork


@pytest.mark.integration
async def test_uow_commits_on_success(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with UnitOfWork(session_factory) as u:
        u.session.add(
            TeamORM(
                name="Brazil",
                short_name="BRA",
                team_type="selecao",
                country="BRA",
                external_ids={},
            )
        )

    async with session_factory() as s:
        result = await s.scalars(select(TeamORM).where(TeamORM.name == "Brazil"))
        team = result.one()
        assert team.short_name == "BRA"


@pytest.mark.integration
async def test_uow_rolls_back_on_error(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    with pytest.raises(RuntimeError, match="boom"):
        async with UnitOfWork(session_factory) as u:
            u.session.add(
                TeamORM(
                    name="Argentina",
                    short_name="ARG",
                    team_type="selecao",
                    country="ARG",
                    external_ids={},
                )
            )
            raise RuntimeError("boom")

    async with session_factory() as s:
        result = await s.scalars(
            select(TeamORM).where(TeamORM.name == "Argentina")
        )
        assert result.all() == []
```

- [ ] **Step 6: Rodar testes**

```bash
uv run pytest tests/integration/persistence/test_unit_of_work.py -v -m integration
uv run mypy src tests
uv run ruff check .
```

Expected: 2 tests passed (testcontainers vai baixar imagem na primeira execução, demora ~30s).

- [ ] **Step 7: Commit**

```bash
git add src/analytis/persistence/engine.py src/analytis/persistence/unit_of_work.py tests/conftest.py tests/integration/persistence/
git commit -m "feat(persistence): add engine factory and UnitOfWork with integration tests"
```

---

## Task 13: Repositórios — Competition, Team, Season

**Files:**
- Create: `src/analytis/persistence/repositories/__init__.py`
- Create: `src/analytis/persistence/repositories/base.py`
- Create: `src/analytis/persistence/repositories/competition.py`
- Create: `src/analytis/persistence/repositories/team.py`
- Create: `src/analytis/persistence/repositories/reference.py`
- Test: `tests/integration/persistence/test_repositories.py`

- [ ] **Step 1: Criar `src/analytis/persistence/repositories/__init__.py`**

```python
"""Repository pattern — hides ORM details from the rest of the system."""

from analytis.persistence.repositories.competition import CompetitionRepository
from analytis.persistence.repositories.reference import SeasonRepository
from analytis.persistence.repositories.team import TeamRepository

__all__ = ["CompetitionRepository", "SeasonRepository", "TeamRepository"]
```

- [ ] **Step 2: Criar `src/analytis/persistence/repositories/base.py`**

```python
"""Base utilities shared by repositories."""

from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from analytis.persistence.orm.base import Base


async def upsert(
    session: AsyncSession,
    model: type[Base],
    values: dict[str, Any],
    conflict_cols: list[str],
    update_cols: list[str],
) -> None:
    """Idempotent UPSERT helper using ON CONFLICT DO UPDATE."""
    stmt = pg_insert(model).values(**values)
    stmt = stmt.on_conflict_do_update(
        index_elements=conflict_cols,
        set_={c: getattr(stmt.excluded, c) for c in update_cols},
    )
    await session.execute(stmt)
```

- [ ] **Step 3: Criar `src/analytis/persistence/repositories/competition.py`**

```python
"""Competition repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from analytis.domain.competition import Competition, CompetitionType
from analytis.persistence.orm.catalog import CompetitionORM
from analytis.persistence.repositories.base import upsert


def _to_domain(orm: CompetitionORM) -> Competition:
    return Competition(
        id=orm.id,
        name=orm.name,
        slug=orm.slug,
        competition_type=CompetitionType(orm.competition_type),
        country=orm.country,
        external_ids=dict(orm.external_ids),
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


class CompetitionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_slug(self, slug: str) -> Competition | None:
        result = await self._session.scalars(
            select(CompetitionORM).where(CompetitionORM.slug == slug)
        )
        orm = result.one_or_none()
        return _to_domain(orm) if orm else None

    async def list_all(self) -> list[Competition]:
        result = await self._session.scalars(select(CompetitionORM))
        return [_to_domain(o) for o in result.all()]

    async def upsert(self, competition: Competition) -> None:
        await upsert(
            self._session,
            CompetitionORM,
            values={
                "id": competition.id,
                "name": competition.name,
                "slug": competition.slug,
                "competition_type": competition.competition_type.value,
                "country": competition.country,
                "external_ids": competition.external_ids,
            },
            conflict_cols=["slug"],
            update_cols=["name", "competition_type", "country", "external_ids"],
        )
```

- [ ] **Step 4: Criar `src/analytis/persistence/repositories/team.py`**

```python
"""Team repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from analytis.domain.team import Team, TeamType
from analytis.persistence.orm.catalog import TeamORM
from analytis.persistence.repositories.base import upsert


def _to_domain(orm: TeamORM) -> Team:
    return Team(
        id=orm.id,
        name=orm.name,
        short_name=orm.short_name,
        team_type=TeamType(orm.team_type),
        country=orm.country,
        external_ids=dict(orm.external_ids),
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


class TeamRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_name(self, name: str) -> Team | None:
        result = await self._session.scalars(
            select(TeamORM).where(TeamORM.name == name)
        )
        orm = result.one_or_none()
        return _to_domain(orm) if orm else None

    async def get_by_external_id(self, source: str, ext_id: str) -> Team | None:
        result = await self._session.scalars(
            select(TeamORM).where(TeamORM.external_ids[source].astext == ext_id)
        )
        orm = result.one_or_none()
        return _to_domain(orm) if orm else None

    async def upsert(self, team: Team) -> None:
        await upsert(
            self._session,
            TeamORM,
            values={
                "id": team.id,
                "name": team.name,
                "short_name": team.short_name,
                "team_type": team.team_type.value,
                "country": team.country,
                "external_ids": team.external_ids,
            },
            conflict_cols=["name"],
            update_cols=["short_name", "team_type", "country", "external_ids"],
        )
```

- [ ] **Step 5: Criar `src/analytis/persistence/repositories/reference.py`**

```python
"""Season repository (and other simple referential repos)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from analytis.domain.ids import CompetitionId
from analytis.domain.season import Season
from analytis.persistence.orm.catalog import SeasonORM
from analytis.persistence.repositories.base import upsert


def _to_domain(orm: SeasonORM) -> Season:
    return Season(
        id=orm.id,
        competition_id=orm.competition_id,
        label=orm.label,
        start_date=orm.start_date,
        end_date=orm.end_date,
        external_ids=dict(orm.external_ids),
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


class SeasonRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self, competition_id: CompetitionId, label: str
    ) -> Season | None:
        result = await self._session.scalars(
            select(SeasonORM).where(
                SeasonORM.competition_id == competition_id,
                SeasonORM.label == label,
            )
        )
        orm = result.one_or_none()
        return _to_domain(orm) if orm else None

    async def upsert(self, season: Season) -> None:
        await upsert(
            self._session,
            SeasonORM,
            values={
                "id": season.id,
                "competition_id": season.competition_id,
                "label": season.label,
                "start_date": season.start_date,
                "end_date": season.end_date,
                "external_ids": season.external_ids,
            },
            conflict_cols=["competition_id", "label"],
            update_cols=["start_date", "end_date", "external_ids"],
        )
```

- [ ] **Step 6: Criar teste — `tests/integration/persistence/test_repositories.py`**

```python
"""Integration tests for repositories."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.domain.competition import Competition, CompetitionType
from analytis.domain.season import Season
from analytis.domain.team import Team, TeamType
from analytis.persistence.repositories import (
    CompetitionRepository,
    SeasonRepository,
    TeamRepository,
)
from analytis.persistence.unit_of_work import UnitOfWork


@pytest.mark.integration
async def test_competition_upsert_is_idempotent(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    c = Competition(
        name="FIFA World Cup 2026",
        slug="wc-2026",
        competition_type=CompetitionType.SELECAO,
        country="INTL",
    )

    async with UnitOfWork(session_factory) as u:
        repo = CompetitionRepository(u.session)
        await repo.upsert(c)

    async with UnitOfWork(session_factory) as u:
        repo = CompetitionRepository(u.session)
        await repo.upsert(c)

    async with session_factory() as s:
        repo = CompetitionRepository(s)
        all_comps = await repo.list_all()
        assert len(all_comps) == 1
        assert all_comps[0].slug == "wc-2026"


@pytest.mark.integration
async def test_team_upsert_updates_existing(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    t1 = Team(
        name="Brazil",
        short_name="BRA",
        team_type=TeamType.SELECAO,
        country="BRA",
    )

    async with UnitOfWork(session_factory) as u:
        await TeamRepository(u.session).upsert(t1)

    t2 = Team(
        id=t1.id,
        name="Brazil",
        short_name="BRA",
        team_type=TeamType.SELECAO,
        country="BRA",
        external_ids={"footballdata": "764"},
    )
    async with UnitOfWork(session_factory) as u:
        await TeamRepository(u.session).upsert(t2)

    async with session_factory() as s:
        team = await TeamRepository(s).get_by_external_id("footballdata", "764")
        assert team is not None
        assert team.name == "Brazil"


@pytest.mark.integration
async def test_season_upsert(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    c = Competition(
        name="FIFA World Cup 2026",
        slug="wc-2026",
        competition_type=CompetitionType.SELECAO,
        country="INTL",
    )
    async with UnitOfWork(session_factory) as u:
        await CompetitionRepository(u.session).upsert(c)

    s = Season(competition_id=c.id, label="2026")
    async with UnitOfWork(session_factory) as u:
        await SeasonRepository(u.session).upsert(s)

    async with session_factory() as sess:
        got = await SeasonRepository(sess).get(c.id, "2026")
        assert got is not None
        assert got.label == "2026"
```

- [ ] **Step 7: Rodar testes**

```bash
uv run pytest tests/integration/persistence/test_repositories.py -v -m integration
uv run mypy src tests
uv run ruff check .
```

Expected: 3 tests passed.

- [ ] **Step 8: Commit**

```bash
git add src/analytis/persistence/repositories/ tests/integration/persistence/test_repositories.py
git commit -m "feat(persistence): add idempotent repositories for competition, team, season"
```

---

## Task 14: CLI base com Typer + comando `db migrate`

**Files:**
- Create: `src/analytis/cli/__init__.py`
- Create: `src/analytis/cli/app.py`
- Create: `src/analytis/cli/db.py`

- [ ] **Step 1: Criar `src/analytis/cli/__init__.py`** (vazio)

```python
```

- [ ] **Step 2: Criar `src/analytis/cli/app.py`**

```python
"""CLI entry point."""

import typer

from analytis.cli import db
from analytis.config import get_settings
from analytis.logging import configure_logging

app = typer.Typer(
    name="analytis",
    help="Football analytics backend — predictions, ingestion, modeling.",
    no_args_is_help=True,
    add_completion=False,
)

app.add_typer(db.app, name="db", help="Database operations.")


@app.callback()
def _root_callback() -> None:
    """Configure logging before any command runs."""
    settings = get_settings()
    configure_logging(level=settings.log_level, fmt=settings.log_format)


if __name__ == "__main__":
    app()
```

- [ ] **Step 3: Criar `src/analytis/cli/db.py`**

```python
"""CLI commands for database management."""

import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(help="Database operations.")
console = Console()


@app.command()
def migrate(
    revision: str = typer.Option("head", help="Alembic revision target."),
) -> None:
    """Apply Alembic migrations up to the target revision."""
    project_root = Path(__file__).resolve().parents[3]
    result = subprocess.run(  # noqa: S603
        ["uv", "run", "alembic", "upgrade", revision],
        cwd=project_root,
        check=False,
    )
    if result.returncode != 0:
        console.print("[red]Migration failed[/red]")
        sys.exit(result.returncode)
    console.print(f"[green]Migrated to {revision}[/green]")


@app.command()
def downgrade(
    revision: str = typer.Argument(..., help="Alembic revision target."),
) -> None:
    """Revert Alembic migrations down to the target revision."""
    project_root = Path(__file__).resolve().parents[3]
    result = subprocess.run(  # noqa: S603
        ["uv", "run", "alembic", "downgrade", revision],
        cwd=project_root,
        check=False,
    )
    sys.exit(result.returncode)


@app.command()
def revision(
    message: str = typer.Option(..., "-m", "--message", help="Migration message."),
    autogenerate: bool = typer.Option(True, help="Autogenerate from ORM diff."),
) -> None:
    """Create a new Alembic revision."""
    project_root = Path(__file__).resolve().parents[3]
    cmd = ["uv", "run", "alembic", "revision", "-m", message]
    if autogenerate:
        cmd.append("--autogenerate")
    result = subprocess.run(cmd, cwd=project_root, check=False)  # noqa: S603
    sys.exit(result.returncode)
```

- [ ] **Step 4: Validar CLI**

```bash
uv run analytis --help
uv run analytis db --help
```

Expected: Typer mostra help dos comandos.

- [ ] **Step 5: Commit**

```bash
git add src/analytis/cli/
git commit -m "feat(cli): add typer root and db subcommands (migrate, downgrade, revision)"
```

---

## Task 15: FastAPI mínima + autenticação por API key

**Files:**
- Create: `src/analytis/api/__init__.py`
- Create: `src/analytis/api/main.py`
- Create: `src/analytis/api/deps.py`
- Create: `src/analytis/api/routes/__init__.py`
- Create: `src/analytis/api/routes/health.py`
- Create: `src/analytis/cli/api.py`
- Modify: `src/analytis/cli/app.py` (add api typer)
- Test: `tests/integration/api/__init__.py`
- Test: `tests/integration/api/test_health.py`

- [ ] **Step 1: Criar `src/analytis/api/__init__.py`** (vazio)

```python
```

- [ ] **Step 2: Criar `src/analytis/api/deps.py`**

```python
"""FastAPI dependency providers."""

from fastapi import Depends, HTTPException, Header, status

from analytis.config import Settings, get_settings


def require_api_key(
    settings: Settings = Depends(get_settings),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    if not x_api_key or x_api_key != settings.api_key.get_secret_value():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or missing API key",
        )
```

- [ ] **Step 3: Criar `src/analytis/api/routes/__init__.py`** (vazio)

```python
```

- [ ] **Step 4: Criar `src/analytis/api/routes/health.py`**

```python
"""Health-check endpoints — no auth required."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


@router.get("", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    from analytis import __version__

    return HealthResponse(status="ok", service="analytis", version=__version__)
```

- [ ] **Step 5: Criar `src/analytis/api/main.py`**

```python
"""FastAPI application factory."""

from fastapi import FastAPI

from analytis import __version__
from analytis.api.routes import health


def create_app() -> FastAPI:
    app = FastAPI(
        title="analytis",
        version=__version__,
        description="Football analytics backend — pre-match probabilistic predictions.",
        docs_url="/docs",
        redoc_url=None,
        openapi_url="/openapi.json",
    )
    app.include_router(health.router, prefix="/v1")
    return app


app = create_app()
```

- [ ] **Step 6: Criar `src/analytis/cli/api.py`**

```python
"""CLI commands for the HTTP API server."""

import typer
import uvicorn

app = typer.Typer(help="HTTP API server.")


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Bind host."),
    port: int = typer.Option(8000, help="Bind port."),
    reload: bool = typer.Option(False, help="Enable auto-reload (dev only)."),
) -> None:
    """Start the FastAPI server."""
    uvicorn.run(
        "analytis.api.main:app",
        host=host,
        port=port,
        reload=reload,
        log_config=None,
    )
```

- [ ] **Step 7: Atualizar `src/analytis/cli/app.py` para registrar o api typer**

```python
"""CLI entry point."""

import typer

from analytis.cli import api, db
from analytis.config import get_settings
from analytis.logging import configure_logging

app = typer.Typer(
    name="analytis",
    help="Football analytics backend — predictions, ingestion, modeling.",
    no_args_is_help=True,
    add_completion=False,
)

app.add_typer(db.app, name="db", help="Database operations.")
app.add_typer(api.app, name="api", help="HTTP API server.")


@app.callback()
def _root_callback() -> None:
    """Configure logging before any command runs."""
    settings = get_settings()
    configure_logging(level=settings.log_level, fmt=settings.log_format)


if __name__ == "__main__":
    app()
```

- [ ] **Step 8: Criar `tests/integration/api/__init__.py`** (vazio)

```python
```

- [ ] **Step 9: Criar teste — `tests/integration/api/test_health.py`**

```python
"""Smoke tests for the health endpoint."""

import pytest
from fastapi.testclient import TestClient

from analytis.api.main import create_app


@pytest.mark.integration
def test_health_returns_ok() -> None:
    app = create_app()
    client = TestClient(app)
    response = client.get("/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "analytis"
```

- [ ] **Step 10: Rodar testes**

```bash
uv run pytest tests/integration/api -v -m integration
uv run mypy src tests
uv run ruff check .
```

Expected: 1 test passed.

- [ ] **Step 11: Commit**

```bash
git add src/analytis/api/ src/analytis/cli/api.py src/analytis/cli/app.py tests/integration/api/
git commit -m "feat(api): minimal FastAPI app with health endpoint and api-key dep"
```

---

## Task 16: DataSourceAdapter Protocol + DTOs

**Files:**
- Create: `src/analytis/ingestion/__init__.py`
- Create: `src/analytis/ingestion/ports.py`

- [ ] **Step 1: Criar `src/analytis/ingestion/__init__.py`** (vazio)

```python
```

- [ ] **Step 2: Criar `src/analytis/ingestion/ports.py`**

```python
"""Ports for ingestion adapters — defines the contract every source must honor."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol


@dataclass(frozen=True)
class CompetitionDTO:
    source_id: str
    external_id: str
    name: str
    slug: str
    competition_type: str  # "selecao" | "clube"
    country: str


@dataclass(frozen=True)
class SeasonDTO:
    source_id: str
    competition_external_id: str
    label: str
    start_date: date | None
    end_date: date | None


@dataclass(frozen=True)
class TeamDTO:
    source_id: str
    external_id: str
    name: str
    short_name: str
    team_type: str
    country: str


@dataclass(frozen=True)
class MatchDTO:
    source_id: str
    external_id: str
    competition_external_id: str
    season_label: str
    home_team_external_id: str
    home_team_name: str
    home_team_short_name: str
    away_team_external_id: str
    away_team_name: str
    away_team_short_name: str
    kickoff_utc: datetime
    is_home_neutral: bool
    status: str
    home_goals: int | None
    away_goals: int | None
    home_corners: int | None
    away_corners: int | None
    venue_name: str | None
    referee_name: str | None


@dataclass(frozen=True)
class EloRatingDTO:
    source_id: str
    team_name: str
    country_code: str
    rating: float
    as_of: date


class DataSourceAdapter(Protocol):
    """Common contract every external source adapter must implement."""

    source_id: str

    def fetch_competitions(self) -> Iterable[CompetitionDTO]: ...

    def fetch_seasons(self, competition_external_id: str) -> Iterable[SeasonDTO]: ...

    def fetch_teams(self, competition_external_id: str) -> Iterable[TeamDTO]: ...

    def fetch_matches(
        self, competition_external_id: str, season_label: str
    ) -> Iterable[MatchDTO]: ...
```

- [ ] **Step 3: Validar**

```bash
uv run python -c "from analytis.ingestion.ports import DataSourceAdapter, MatchDTO; print('ok')"
uv run mypy src
uv run ruff check .
```

Expected: prints "ok".

- [ ] **Step 4: Commit**

```bash
git add src/analytis/ingestion/__init__.py src/analytis/ingestion/ports.py
git commit -m "feat(ingestion): define adapter Protocol and canonical DTOs"
```

---

## Task 17: Rate limiter (token bucket)

**Files:**
- Create: `src/analytis/ingestion/rate_limiter.py`
- Test: `tests/unit/ingestion/__init__.py`
- Test: `tests/unit/ingestion/test_rate_limiter.py`

- [ ] **Step 1: Criar `tests/unit/ingestion/__init__.py`** (vazio)

```python
```

- [ ] **Step 2: Criar teste — `tests/unit/ingestion/test_rate_limiter.py`**

```python
"""Tests for the token bucket rate limiter."""

import asyncio
import time

import pytest

from analytis.ingestion.rate_limiter import TokenBucket


@pytest.mark.asyncio
async def test_bucket_allows_burst() -> None:
    bucket = TokenBucket(rate_per_second=10.0, capacity=5)
    start = time.monotonic()
    for _ in range(5):
        await bucket.acquire()
    elapsed = time.monotonic() - start
    assert elapsed < 0.05


@pytest.mark.asyncio
async def test_bucket_throttles_after_burst() -> None:
    bucket = TokenBucket(rate_per_second=10.0, capacity=2)
    await bucket.acquire()
    await bucket.acquire()
    start = time.monotonic()
    await bucket.acquire()
    elapsed = time.monotonic() - start
    assert elapsed >= 0.08, f"expected >=80ms, got {elapsed * 1000:.0f}ms"


@pytest.mark.asyncio
async def test_bucket_recovers() -> None:
    bucket = TokenBucket(rate_per_second=100.0, capacity=1)
    await bucket.acquire()
    await asyncio.sleep(0.05)
    start = time.monotonic()
    await bucket.acquire()
    elapsed = time.monotonic() - start
    assert elapsed < 0.02
```

- [ ] **Step 3: Verificar falha**

```bash
uv run pytest tests/unit/ingestion/test_rate_limiter.py -v
```

Expected: ImportError.

- [ ] **Step 4: Implementar `src/analytis/ingestion/rate_limiter.py`**

```python
"""Token bucket rate limiter for ingestion adapters."""

import asyncio
import time


class TokenBucket:
    """Asyncio-friendly token bucket.

    rate_per_second: tokens refilled per second.
    capacity: max tokens that can accumulate.
    """

    def __init__(self, rate_per_second: float, capacity: int) -> None:
        if rate_per_second <= 0:
            raise ValueError("rate_per_second must be positive")
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self._rate = rate_per_second
        self._capacity = float(capacity)
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: float = 1.0) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self._last_refill
                self._tokens = min(
                    self._capacity, self._tokens + elapsed * self._rate
                )
                self._last_refill = now
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return
                missing = tokens - self._tokens
                wait_s = missing / self._rate
                await asyncio.sleep(wait_s)
```

- [ ] **Step 5: Rodar testes**

```bash
uv run pytest tests/unit/ingestion/test_rate_limiter.py -v
uv run mypy src tests
uv run ruff check .
```

Expected: 3 tests passed.

- [ ] **Step 6: Commit**

```bash
git add src/analytis/ingestion/rate_limiter.py tests/unit/ingestion/
git commit -m "feat(ingestion): token bucket rate limiter"
```

---

## Task 18: Retry helper baseado em tenacity

**Files:**
- Create: `src/analytis/ingestion/retry.py`
- Test: `tests/unit/ingestion/test_retry.py`

- [ ] **Step 1: Criar teste — `tests/unit/ingestion/test_retry.py`**

```python
"""Tests for the retry helper."""

import httpx
import pytest

from analytis.ingestion.retry import with_retry


class _Counter:
    def __init__(self) -> None:
        self.calls = 0


@pytest.mark.asyncio
async def test_retry_succeeds_after_transient_failures() -> None:
    counter = _Counter()

    @with_retry(max_attempts=3, base_delay=0.01)
    async def flaky() -> str:
        counter.calls += 1
        if counter.calls < 3:
            raise httpx.ConnectTimeout("boom")
        return "ok"

    result = await flaky()
    assert result == "ok"
    assert counter.calls == 3


@pytest.mark.asyncio
async def test_retry_gives_up_after_max() -> None:
    counter = _Counter()

    @with_retry(max_attempts=2, base_delay=0.01)
    async def always_fails() -> str:
        counter.calls += 1
        raise httpx.ConnectTimeout("boom")

    with pytest.raises(httpx.ConnectTimeout):
        await always_fails()
    assert counter.calls == 2


@pytest.mark.asyncio
async def test_retry_does_not_retry_on_non_transient() -> None:
    counter = _Counter()

    @with_retry(max_attempts=3, base_delay=0.01)
    async def bad_input() -> str:
        counter.calls += 1
        raise ValueError("permanent")

    with pytest.raises(ValueError, match="permanent"):
        await bad_input()
    assert counter.calls == 1
```

- [ ] **Step 2: Verificar falha**

```bash
uv run pytest tests/unit/ingestion/test_retry.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implementar `src/analytis/ingestion/retry.py`**

```python
"""Retry helper for transient HTTP errors."""

from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any, TypeVar

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

T = TypeVar("T")

TRANSIENT_EXCEPTIONS = (
    httpx.ConnectTimeout,
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.RemoteProtocolError,
)


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 30.0,
) -> Callable[
    [Callable[..., Coroutine[Any, Any, T]]],
    Callable[..., Coroutine[Any, Any, T]],
]:
    """Decorate an async fn to retry on transient HTTP errors with jittered backoff."""

    def decorator(
        fn: Callable[..., Coroutine[Any, Any, T]],
    ) -> Callable[..., Coroutine[Any, Any, T]]:
        @wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            retrying = AsyncRetrying(
                stop=stop_after_attempt(max_attempts),
                wait=wait_exponential_jitter(initial=base_delay, max=max_delay),
                retry=retry_if_exception_type(TRANSIENT_EXCEPTIONS),
                reraise=True,
            )
            async for attempt in retrying:
                with attempt:
                    return await fn(*args, **kwargs)
            raise RuntimeError("unreachable")

        return wrapper

    return decorator
```

- [ ] **Step 4: Rodar testes**

```bash
uv run pytest tests/unit/ingestion/test_retry.py -v
uv run mypy src tests
uv run ruff check .
```

Expected: 3 tests passed.

- [ ] **Step 5: Commit**

```bash
git add src/analytis/ingestion/retry.py tests/unit/ingestion/test_retry.py
git commit -m "feat(ingestion): retry helper with jittered exponential backoff"
```

---

## Task 19: Pipeline base + repositório `IngestionRun`

**Files:**
- Create: `src/analytis/persistence/repositories/ingestion.py`
- Create: `src/analytis/persistence/repositories/match.py`
- Create: `src/analytis/ingestion/pipeline.py`
- Modify: `src/analytis/persistence/repositories/__init__.py`

- [ ] **Step 1: Criar `src/analytis/persistence/repositories/ingestion.py`**

```python
"""Repository for ingestion observability tables."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from analytis.domain.ingestion import (
    DataSource,
    IngestionRun,
    IngestionStatus,
)
from analytis.persistence.orm.ingestion import DataSourceORM, IngestionRunORM


class DataSourceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, ds: DataSource) -> None:
        stmt = pg_insert(DataSourceORM).values(
            source_id=ds.source_id,
            display_name=ds.display_name,
            homepage_url=ds.homepage_url,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["source_id"],
            set_={
                "display_name": stmt.excluded.display_name,
                "homepage_url": stmt.excluded.homepage_url,
            },
        )
        await self._session.execute(stmt)


class IngestionRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def start(
        self, data_source_id: str, job_name: str
    ) -> IngestionRun:
        run = IngestionRun(
            data_source_id=data_source_id,
            job_name=job_name,
            started_at=datetime.now(UTC),
        )
        self._session.add(
            IngestionRunORM(
                id=run.id,
                data_source_id=run.data_source_id,
                job_name=run.job_name,
                started_at=run.started_at,
                status=run.status.value,
                records_touched=0,
            )
        )
        return run

    async def mark_succeeded(
        self, run_id: UUID, records_touched: int, payload_hash: str | None = None
    ) -> None:
        orm = await self._session.get(IngestionRunORM, run_id)
        if orm is None:
            raise ValueError(f"IngestionRun {run_id} not found")
        orm.status = IngestionStatus.SUCCEEDED.value
        orm.finished_at = datetime.now(UTC)
        orm.records_touched = records_touched
        orm.payload_hash = payload_hash

    async def mark_failed(self, run_id: UUID, error: str) -> None:
        orm = await self._session.get(IngestionRunORM, run_id)
        if orm is None:
            raise ValueError(f"IngestionRun {run_id} not found")
        orm.status = IngestionStatus.FAILED.value
        orm.finished_at = datetime.now(UTC)
        orm.error_message = error
```

- [ ] **Step 2: Criar `src/analytis/persistence/repositories/match.py`**

```python
"""Match repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from analytis.domain.ids import SeasonId
from analytis.domain.match import Match, MatchStatus
from analytis.persistence.orm.matches import MatchORM
from analytis.persistence.repositories.base import upsert


def _to_domain(orm: MatchORM) -> Match:
    return Match(
        id=orm.id,
        season_id=orm.season_id,
        home_team_id=orm.home_team_id,
        away_team_id=orm.away_team_id,
        kickoff_utc=orm.kickoff_utc,
        venue_id=orm.venue_id,
        referee_id=orm.referee_id,
        is_home_neutral=orm.is_home_neutral,
        status=MatchStatus(orm.status),
        home_goals=orm.home_goals,
        away_goals=orm.away_goals,
        home_corners=orm.home_corners,
        away_corners=orm.away_corners,
        external_ids=dict(orm.external_ids),
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


class MatchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_external_id(self, source: str, ext_id: str) -> Match | None:
        result = await self._session.scalars(
            select(MatchORM).where(MatchORM.external_ids[source].astext == ext_id)
        )
        orm = result.one_or_none()
        return _to_domain(orm) if orm else None

    async def list_by_season(self, season_id: SeasonId) -> list[Match]:
        result = await self._session.scalars(
            select(MatchORM).where(MatchORM.season_id == season_id)
        )
        return [_to_domain(o) for o in result.all()]

    async def upsert(self, match: Match) -> None:
        external_ids = match.external_ids
        if not external_ids:
            raise ValueError("Match must have at least one external_id for upsert")
        source, ext_id = next(iter(external_ids.items()))

        existing = await self.get_by_external_id(source, ext_id)
        target_id = existing.id if existing else match.id

        await upsert(
            self._session,
            MatchORM,
            values={
                "id": target_id,
                "season_id": match.season_id,
                "home_team_id": match.home_team_id,
                "away_team_id": match.away_team_id,
                "kickoff_utc": match.kickoff_utc,
                "venue_id": match.venue_id,
                "referee_id": match.referee_id,
                "is_home_neutral": match.is_home_neutral,
                "status": match.status.value,
                "home_goals": match.home_goals,
                "away_goals": match.away_goals,
                "home_corners": match.home_corners,
                "away_corners": match.away_corners,
                "external_ids": external_ids,
            },
            conflict_cols=["id"],
            update_cols=[
                "kickoff_utc",
                "status",
                "home_goals",
                "away_goals",
                "home_corners",
                "away_corners",
                "venue_id",
                "referee_id",
                "external_ids",
            ],
        )
```

- [ ] **Step 3: Atualizar `src/analytis/persistence/repositories/__init__.py`**

```python
"""Repository pattern — hides ORM details from the rest of the system."""

from analytis.persistence.repositories.competition import CompetitionRepository
from analytis.persistence.repositories.ingestion import (
    DataSourceRepository,
    IngestionRunRepository,
)
from analytis.persistence.repositories.match import MatchRepository
from analytis.persistence.repositories.reference import SeasonRepository
from analytis.persistence.repositories.team import TeamRepository

__all__ = [
    "CompetitionRepository",
    "DataSourceRepository",
    "IngestionRunRepository",
    "MatchRepository",
    "SeasonRepository",
    "TeamRepository",
]
```

- [ ] **Step 4: Criar `src/analytis/ingestion/pipeline.py`**

```python
"""Generic ingestion pipeline — wraps a job in run tracking."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import structlog
from sqlalchemy.ext.asyncio import async_sessionmaker

from analytis.logging import get_logger
from analytis.persistence.repositories import IngestionRunRepository
from analytis.persistence.unit_of_work import UnitOfWork


@dataclass
class IngestionResult:
    records_touched: int
    payload_hash: str | None = None


JobFn = Callable[[UnitOfWork], Awaitable[IngestionResult]]


class IngestionPipeline:
    """Runs an ingestion job inside a UnitOfWork with start/succeed/fail tracking."""

    def __init__(
        self,
        session_factory: async_sessionmaker,
        data_source_id: str,
    ) -> None:
        self._factory = session_factory
        self._source = data_source_id
        self._log: structlog.stdlib.BoundLogger = get_logger(__name__).bind(
            source=data_source_id
        )

    async def run(self, job_name: str, job: JobFn) -> IngestionResult:
        async with UnitOfWork(self._factory) as run_uow:
            run = await IngestionRunRepository(run_uow.session).start(
                self._source, job_name
            )
        run_id = run.id
        self._log.info("ingestion_start", job=job_name, run_id=str(run_id))

        try:
            async with UnitOfWork(self._factory) as work_uow:
                result = await job(work_uow)

            async with UnitOfWork(self._factory) as finish_uow:
                await IngestionRunRepository(finish_uow.session).mark_succeeded(
                    run_id, result.records_touched, result.payload_hash
                )
            self._log.info(
                "ingestion_succeeded",
                job=job_name,
                records=result.records_touched,
            )
            return result
        except Exception as exc:
            async with UnitOfWork(self._factory) as finish_uow:
                await IngestionRunRepository(finish_uow.session).mark_failed(
                    run_id, str(exc)
                )
            self._log.error("ingestion_failed", job=job_name, error=str(exc))
            raise
```

- [ ] **Step 5: Validar**

```bash
uv run python -c "from analytis.ingestion.pipeline import IngestionPipeline; print('ok')"
uv run mypy src
uv run ruff check .
```

Expected: prints "ok".

- [ ] **Step 6: Commit**

```bash
git add src/analytis/persistence/repositories/ingestion.py src/analytis/persistence/repositories/match.py src/analytis/persistence/repositories/__init__.py src/analytis/ingestion/pipeline.py
git commit -m "feat(ingestion): pipeline with run tracking + match/ingestion repositories"
```

---

## Task 20: Adapter Football-Data.org

**Files:**
- Create: `src/analytis/ingestion/adapters/__init__.py`
- Create: `src/analytis/ingestion/adapters/football_data.py`
- Test: `tests/unit/ingestion/adapters/__init__.py`
- Test: `tests/unit/ingestion/adapters/test_football_data.py`

- [ ] **Step 1: Criar `src/analytis/ingestion/adapters/__init__.py`** (vazio)

```python
```

- [ ] **Step 2: Criar `tests/unit/ingestion/adapters/__init__.py`** (vazio)

```python
```

- [ ] **Step 3: Criar teste — `tests/unit/ingestion/adapters/test_football_data.py`**

```python
"""Unit tests for the Football-Data.org adapter."""

import httpx
import pytest
import respx

from analytis.ingestion.adapters.football_data import FootballDataAdapter

BASE = "https://api.football-data.org/v4"


@pytest.mark.asyncio
async def test_fetch_competitions() -> None:
    payload = {
        "competitions": [
            {
                "id": 2000,
                "name": "FIFA World Cup",
                "code": "WC",
                "type": "CUP",
                "area": {"code": "INTL", "name": "World"},
            }
        ]
    }
    with respx.mock(base_url=BASE) as mock:
        mock.get("/competitions").respond(200, json=payload)
        async with httpx.AsyncClient(base_url=BASE) as client:
            adapter = FootballDataAdapter(client=client, api_key="x")
            competitions = list(await adapter.fetch_competitions())

    assert len(competitions) == 1
    c = competitions[0]
    assert c.external_id == "2000"
    assert c.slug == "wc"
    assert c.competition_type == "selecao"
    assert c.country == "INTL"


@pytest.mark.asyncio
async def test_fetch_matches_maps_status_and_neutral() -> None:
    payload = {
        "matches": [
            {
                "id": 491189,
                "utcDate": "2026-06-15T22:00:00Z",
                "status": "FINISHED",
                "matchday": 1,
                "stage": "GROUP_STAGE",
                "homeTeam": {"id": 764, "name": "Brazil", "tla": "BRA"},
                "awayTeam": {"id": 763, "name": "Mexico", "tla": "MEX"},
                "score": {
                    "fullTime": {"home": 2, "away": 1},
                    "extraTime": {"home": None, "away": None},
                    "penalties": {"home": None, "away": None},
                },
                "season": {"id": 1, "startDate": "2026-06-11", "endDate": "2026-07-19"},
                "venue": "Estadio Azteca",
                "referees": [{"name": "Joel Aguilar", "role": "REFEREE"}],
            }
        ]
    }
    with respx.mock(base_url=BASE) as mock:
        mock.get("/competitions/2000/matches", params={"season": "2026"}).respond(
            200, json=payload
        )
        async with httpx.AsyncClient(base_url=BASE) as client:
            adapter = FootballDataAdapter(client=client, api_key="x")
            matches = list(await adapter.fetch_matches("2000", "2026"))

    assert len(matches) == 1
    m = matches[0]
    assert m.external_id == "491189"
    assert m.home_team_external_id == "764"
    assert m.home_team_name == "Brazil"
    assert m.home_team_short_name == "BRA"
    assert m.away_team_external_id == "763"
    assert m.away_team_name == "Mexico"
    assert m.away_team_short_name == "MEX"
    assert m.away_goals == 1
    assert m.status == "finished"
    assert m.is_home_neutral is True  # World Cup is always neutral
    assert m.referee_name == "Joel Aguilar"
```

- [ ] **Step 4: Verificar falha**

```bash
uv run pytest tests/unit/ingestion/adapters/test_football_data.py -v
```

Expected: ImportError.

- [ ] **Step 5: Implementar `src/analytis/ingestion/adapters/football_data.py`**

```python
"""Adapter for the Football-Data.org REST API (free tier)."""

from collections.abc import Iterable
from datetime import datetime
from typing import Any

import httpx

from analytis.ingestion.ports import CompetitionDTO, MatchDTO
from analytis.ingestion.rate_limiter import TokenBucket
from analytis.ingestion.retry import with_retry

_STATUS_MAP = {
    "SCHEDULED": "scheduled",
    "TIMED": "scheduled",
    "LIVE": "live",
    "IN_PLAY": "live",
    "PAUSED": "live",
    "FINISHED": "finished",
    "POSTPONED": "postponed",
    "SUSPENDED": "postponed",
    "CANCELLED": "cancelled",
    "AWARDED": "finished",
}

_INTERNATIONAL_CUP_CODES = {"WC", "EC", "CA", "AFCON"}


class FootballDataAdapter:
    """Adapter implementing DataSourceAdapter for Football-Data.org v4."""

    source_id = "footballdata"
    BASE_URL = "https://api.football-data.org/v4"

    def __init__(
        self,
        client: httpx.AsyncClient,
        api_key: str,
        rate_limit_per_minute: int = 10,
    ) -> None:
        self._client = client
        self._headers = {"X-Auth-Token": api_key}
        self._bucket = TokenBucket(
            rate_per_second=rate_limit_per_minute / 60.0,
            capacity=max(1, rate_limit_per_minute),
        )

    @with_retry(max_attempts=3, base_delay=1.0, max_delay=15.0)
    async def _get(self, path: str, **params: Any) -> dict[str, Any]:
        await self._bucket.acquire()
        response = await self._client.get(path, headers=self._headers, params=params)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return data

    async def fetch_competitions(self) -> Iterable[CompetitionDTO]:
        data = await self._get("/competitions")
        result = []
        for c in data.get("competitions", []):
            code = (c.get("code") or "").upper()
            ctype = (
                "selecao"
                if code in _INTERNATIONAL_CUP_CODES or c.get("type") == "CUP"
                else "clube"
            )
            result.append(
                CompetitionDTO(
                    source_id=self.source_id,
                    external_id=str(c["id"]),
                    name=c["name"],
                    slug=code.lower() or _slugify(c["name"]),
                    competition_type=ctype,
                    country=(c.get("area") or {}).get("code") or "UNK",
                )
            )
        return result

    async def fetch_matches(
        self, competition_external_id: str, season_label: str
    ) -> Iterable[MatchDTO]:
        data = await self._get(
            f"/competitions/{competition_external_id}/matches",
            season=season_label,
        )
        is_intl_cup = self._is_international_cup(competition_external_id)
        result: list[MatchDTO] = []
        for m in data.get("matches", []):
            ref = next(
                (
                    r["name"]
                    for r in m.get("referees", [])
                    if r.get("role") == "REFEREE"
                ),
                None,
            )
            full = m.get("score", {}).get("fullTime", {}) or {}
            home = m["homeTeam"]
            away = m["awayTeam"]
            result.append(
                MatchDTO(
                    source_id=self.source_id,
                    external_id=str(m["id"]),
                    competition_external_id=competition_external_id,
                    season_label=season_label,
                    home_team_external_id=str(home["id"]),
                    home_team_name=home["name"],
                    home_team_short_name=(home.get("tla") or home["name"][:5]).upper(),
                    away_team_external_id=str(away["id"]),
                    away_team_name=away["name"],
                    away_team_short_name=(away.get("tla") or away["name"][:5]).upper(),
                    kickoff_utc=_parse_iso(m["utcDate"]),
                    is_home_neutral=is_intl_cup,
                    status=_STATUS_MAP.get(m["status"], "scheduled"),
                    home_goals=full.get("home"),
                    away_goals=full.get("away"),
                    home_corners=None,
                    away_corners=None,
                    venue_name=m.get("venue"),
                    referee_name=ref,
                )
            )
        return result

    async def fetch_seasons(self, competition_external_id: str) -> Iterable[Any]:
        raise NotImplementedError("Football-Data exposes seasons via competition payload")

    async def fetch_teams(self, competition_external_id: str) -> Iterable[Any]:
        raise NotImplementedError("Use fetch_matches; teams are inferred from matches")

    def _is_international_cup(self, competition_external_id: str) -> bool:
        # Football-Data id 2000 = FIFA World Cup. Extend list if you add EC/CA/AFCON.
        return competition_external_id in {"2000"}


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _slugify(value: str) -> str:
    return "-".join(value.lower().split())
```

- [ ] **Step 6: Rodar testes**

```bash
uv run pytest tests/unit/ingestion/adapters/test_football_data.py -v
uv run mypy src tests
uv run ruff check .
```

Expected: 2 tests passed.

- [ ] **Step 7: Commit**

```bash
git add src/analytis/ingestion/adapters/__init__.py src/analytis/ingestion/adapters/football_data.py tests/unit/ingestion/adapters/
git commit -m "feat(ingestion): football-data.org adapter for competitions and matches"
```

---

## Task 21: Adapter ELO ratings

**Files:**
- Create: `src/analytis/ingestion/adapters/elo_ratings.py`
- Test: `tests/unit/ingestion/adapters/test_elo_ratings.py`

- [ ] **Step 1: Criar teste — `tests/unit/ingestion/adapters/test_elo_ratings.py`**

```python
"""Unit tests for the ELO ratings adapter."""

from datetime import date

import httpx
import pytest
import respx

from analytis.ingestion.adapters.elo_ratings import EloRatingsAdapter

URL = "http://www.eloratings.net/World.tsv"

# Minimal TSV mock — columns: rank, name, country, rating, date
TSV_FIXTURE = (
    "rank\tname\tcountry\trating\tdate\n"
    "1\tBrazil\tBRA\t2150.0\t2026-06-12\n"
    "2\tArgentina\tARG\t2120.0\t2026-06-12\n"
)


@pytest.mark.asyncio
async def test_fetch_world_ratings_parses_tsv() -> None:
    with respx.mock() as mock:
        mock.get(URL).respond(200, text=TSV_FIXTURE)
        async with httpx.AsyncClient() as client:
            adapter = EloRatingsAdapter(client=client, url=URL)
            ratings = list(await adapter.fetch_world_ratings())

    assert len(ratings) == 2
    bra = ratings[0]
    assert bra.team_name == "Brazil"
    assert bra.country_code == "BRA"
    assert bra.rating == 2150.0
    assert bra.as_of == date(2026, 6, 12)
```

- [ ] **Step 2: Verificar falha**

```bash
uv run pytest tests/unit/ingestion/adapters/test_elo_ratings.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implementar `src/analytis/ingestion/adapters/elo_ratings.py`**

```python
"""Adapter for World Football Elo ratings (CSV/TSV download)."""

import csv
from collections.abc import Iterable
from datetime import date
from io import StringIO

import httpx

from analytis.ingestion.ports import EloRatingDTO
from analytis.ingestion.retry import with_retry


class EloRatingsAdapter:
    source_id = "eloratings"

    def __init__(self, client: httpx.AsyncClient, url: str) -> None:
        self._client = client
        self._url = url

    @with_retry(max_attempts=3, base_delay=1.0)
    async def _download(self) -> str:
        response = await self._client.get(self._url)
        response.raise_for_status()
        return response.text

    async def fetch_world_ratings(self) -> Iterable[EloRatingDTO]:
        raw = await self._download()
        reader = csv.DictReader(StringIO(raw), delimiter="\t")
        result: list[EloRatingDTO] = []
        for row in reader:
            result.append(
                EloRatingDTO(
                    source_id=self.source_id,
                    team_name=row["name"].strip(),
                    country_code=row["country"].strip().upper(),
                    rating=float(row["rating"]),
                    as_of=date.fromisoformat(row["date"].strip()),
                )
            )
        return result
```

- [ ] **Step 4: Rodar testes**

```bash
uv run pytest tests/unit/ingestion/adapters/test_elo_ratings.py -v
uv run mypy src tests
uv run ruff check .
```

Expected: 1 test passed.

- [ ] **Step 5: Commit**

```bash
git add src/analytis/ingestion/adapters/elo_ratings.py tests/unit/ingestion/adapters/test_elo_ratings.py
git commit -m "feat(ingestion): elo ratings adapter (TSV download)"
```

---

## Task 22: Use cases de ingestão (application layer)

**Files:**
- Create: `src/analytis/application/__init__.py`
- Create: `src/analytis/application/ingest_fixtures.py`
- Test: `tests/integration/ingestion/__init__.py`
- Test: `tests/integration/ingestion/test_pipeline.py`

- [ ] **Step 1: Criar `src/analytis/application/__init__.py`** (vazio)

```python
```

- [ ] **Step 2: Criar `src/analytis/application/ingest_fixtures.py`**

```python
"""Use case: ingest fixtures (matches) from Football-Data.org for a competition+season."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import async_sessionmaker

from analytis.domain.competition import Competition, CompetitionType
from analytis.domain.match import Match, MatchStatus
from analytis.domain.season import Season
from analytis.domain.team import Team, TeamType
from analytis.ingestion.adapters.football_data import FootballDataAdapter
from analytis.ingestion.pipeline import IngestionPipeline, IngestionResult
from analytis.persistence.repositories import (
    CompetitionRepository,
    MatchRepository,
    SeasonRepository,
    TeamRepository,
)
from analytis.persistence.unit_of_work import UnitOfWork


@dataclass
class FixturesParams:
    competition_external_id: str
    season_label: str


class IngestFixturesUseCase:
    def __init__(
        self,
        session_factory: async_sessionmaker,
        adapter: FootballDataAdapter,
    ) -> None:
        self._factory = session_factory
        self._adapter = adapter
        self._pipeline = IngestionPipeline(session_factory, adapter.source_id)

    async def execute(self, params: FixturesParams) -> IngestionResult:
        async def job(uow: UnitOfWork) -> IngestionResult:
            comps = list(await self._adapter.fetch_competitions())
            matches = list(
                await self._adapter.fetch_matches(
                    params.competition_external_id, params.season_label
                )
            )

            comp = next(
                (c for c in comps if c.external_id == params.competition_external_id),
                None,
            )
            if comp is None:
                raise ValueError(
                    f"competition {params.competition_external_id} not found upstream"
                )

            comp_repo = CompetitionRepository(uow.session)
            season_repo = SeasonRepository(uow.session)
            team_repo = TeamRepository(uow.session)
            match_repo = MatchRepository(uow.session)

            domain_comp = Competition(
                name=comp.name,
                slug=comp.slug,
                competition_type=CompetitionType(comp.competition_type),
                country=comp.country,
                external_ids={comp.source_id: comp.external_id},
            )
            await comp_repo.upsert(domain_comp)
            stored_comp = await comp_repo.get_by_slug(domain_comp.slug)
            assert stored_comp is not None

            season = Season(
                competition_id=stored_comp.id, label=params.season_label
            )
            await season_repo.upsert(season)
            stored_season = await season_repo.get(stored_comp.id, params.season_label)
            assert stored_season is not None

            team_type = TeamType(
                "selecao"
                if domain_comp.competition_type is CompetitionType.SELECAO
                else "clube"
            )
            team_by_ext: dict[str, Team] = {}
            for m in matches:
                for ext_id, name, short in (
                    (m.home_team_external_id, m.home_team_name, m.home_team_short_name),
                    (m.away_team_external_id, m.away_team_name, m.away_team_short_name),
                ):
                    if ext_id in team_by_ext:
                        continue
                    existing = await team_repo.get_by_external_id(
                        self._adapter.source_id, ext_id
                    )
                    if existing is not None:
                        team_by_ext[ext_id] = existing
                        continue
                    new_team = Team(
                        name=name,
                        short_name=short,
                        team_type=team_type,
                        country=domain_comp.country,
                        external_ids={self._adapter.source_id: ext_id},
                    )
                    await team_repo.upsert(new_team)
                    persisted = await team_repo.get_by_external_id(
                        self._adapter.source_id, ext_id
                    )
                    assert persisted is not None
                    team_by_ext[ext_id] = persisted

            touched = 0
            for m in matches:
                home = team_by_ext[m.home_team_external_id]
                away = team_by_ext[m.away_team_external_id]
                domain_match = Match(
                    season_id=stored_season.id,
                    home_team_id=home.id,
                    away_team_id=away.id,
                    kickoff_utc=m.kickoff_utc,
                    is_home_neutral=m.is_home_neutral,
                    status=MatchStatus(m.status),
                    home_goals=m.home_goals,
                    away_goals=m.away_goals,
                    home_corners=m.home_corners,
                    away_corners=m.away_corners,
                    external_ids={self._adapter.source_id: m.external_id},
                )
                await match_repo.upsert(domain_match)
                touched += 1

            return IngestionResult(records_touched=touched)

        return await self._pipeline.run(
            job_name=f"ingest:fixtures:{params.competition_external_id}:{params.season_label}",
            job=job,
        )
```

- [ ] **Step 3: Criar `tests/integration/ingestion/__init__.py`** (vazio)

```python
```

- [ ] **Step 4: Criar teste — `tests/integration/ingestion/test_pipeline.py`**

```python
"""Integration test for the fixtures ingestion use case end-to-end."""

from collections.abc import Iterable

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from analytis.application.ingest_fixtures import (
    FixturesParams,
    IngestFixturesUseCase,
)
from analytis.ingestion.adapters.football_data import FootballDataAdapter
from analytis.ingestion.ports import CompetitionDTO, MatchDTO
from analytis.persistence.orm.ingestion import IngestionRunORM
from analytis.persistence.orm.matches import MatchORM


class _FakeAdapter:
    source_id = "footballdata"

    def __init__(
        self,
        competitions: list[CompetitionDTO],
        matches: list[MatchDTO],
    ) -> None:
        self._competitions = competitions
        self._matches = matches

    async def fetch_competitions(self) -> Iterable[CompetitionDTO]:
        return list(self._competitions)

    async def fetch_matches(
        self, _competition_external_id: str, _season_label: str
    ) -> Iterable[MatchDTO]:
        return list(self._matches)


@pytest.mark.integration
async def test_ingest_fixtures_end_to_end(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    from datetime import UTC, datetime

    comp = CompetitionDTO(
        source_id="footballdata",
        external_id="2000",
        name="FIFA World Cup",
        slug="wc",
        competition_type="selecao",
        country="INTL",
    )
    matches = [
        MatchDTO(
            source_id="footballdata",
            external_id="491189",
            competition_external_id="2000",
            season_label="2026",
            home_team_external_id="764",
            home_team_name="Brazil",
            home_team_short_name="BRA",
            away_team_external_id="763",
            away_team_name="Mexico",
            away_team_short_name="MEX",
            kickoff_utc=datetime(2026, 6, 15, 22, 0, tzinfo=UTC),
            is_home_neutral=True,
            status="finished",
            home_goals=2,
            away_goals=1,
            home_corners=None,
            away_corners=None,
            venue_name="Estadio Azteca",
            referee_name="Joel Aguilar",
        ),
    ]

    use_case = IngestFixturesUseCase(
        session_factory,
        adapter=_FakeAdapter(competitions=[comp], matches=matches),  # type: ignore[arg-type]
    )

    result = await use_case.execute(FixturesParams("2000", "2026"))
    assert result.records_touched == 1

    async with session_factory() as s:
        match_count = await s.scalar(select(func.count()).select_from(MatchORM))
        run_count = await s.scalar(
            select(func.count())
            .select_from(IngestionRunORM)
            .where(IngestionRunORM.status == "succeeded")
        )
        assert match_count == 1
        assert run_count == 1

    # Idempotency: rerun, no new rows
    result2 = await use_case.execute(FixturesParams("2000", "2026"))
    assert result2.records_touched == 1
    async with session_factory() as s:
        match_count2 = await s.scalar(select(func.count()).select_from(MatchORM))
        assert match_count2 == 1


# Touch FootballDataAdapter so mypy keeps it imported for type guards
_assert_adapter_is_protocol_compatible: type = FootballDataAdapter
```

- [ ] **Step 5: Rodar testes**

```bash
uv run pytest tests/integration/ingestion -v -m integration
uv run mypy src tests
uv run ruff check .
```

Expected: 1 test passed.

- [ ] **Step 6: Commit**

```bash
git add src/analytis/application/ tests/integration/ingestion/
git commit -m "feat(application): ingest_fixtures use case with idempotency"
```

---

## Task 23: CLI commands para ingestão

**Files:**
- Create: `src/analytis/cli/ingest.py`
- Modify: `src/analytis/cli/app.py`

- [ ] **Step 1: Criar `src/analytis/cli/ingest.py`**

```python
"""CLI commands for data ingestion."""

import asyncio

import httpx
import typer
from rich.console import Console

from analytis.application.ingest_fixtures import (
    FixturesParams,
    IngestFixturesUseCase,
)
from analytis.config import get_settings
from analytis.ingestion.adapters.football_data import FootballDataAdapter
from analytis.persistence.engine import create_engine, create_session_factory

app = typer.Typer(help="Data ingestion commands.")
console = Console()


@app.command()
def fixtures(
    competition: str = typer.Option(
        ..., "--competition", help="Football-Data competition id (e.g. 2000 for World Cup)."
    ),
    season: str = typer.Option(..., "--season", help="Season label (e.g. 2026)."),
) -> None:
    """Ingest fixtures and results for a competition/season."""
    asyncio.run(_fixtures(competition, season))


async def _fixtures(competition: str, season: str) -> None:
    settings = get_settings()
    if settings.football_data_api_key is None:
        console.print("[red]ANALYTIS_FOOTBALL_DATA_API_KEY not set[/red]")
        raise typer.Exit(code=2)

    engine = create_engine(settings)
    factory = create_session_factory(engine)
    try:
        async with httpx.AsyncClient(
            base_url=FootballDataAdapter.BASE_URL, timeout=30.0
        ) as client:
            adapter = FootballDataAdapter(
                client=client,
                api_key=settings.football_data_api_key.get_secret_value(),
            )
            use_case = IngestFixturesUseCase(factory, adapter)
            result = await use_case.execute(FixturesParams(competition, season))
        console.print(
            f"[green]Ingested {result.records_touched} matches "
            f"for competition={competition} season={season}[/green]"
        )
    finally:
        await engine.dispose()


@app.command()
def backfill(
    competition: str = typer.Option(..., "--competition"),
    seasons: list[str] = typer.Option(..., "--season", help="Repeat for each season."),
) -> None:
    """Backfill multiple seasons of a competition (sequential)."""
    asyncio.run(_backfill(competition, seasons))


async def _backfill(competition: str, seasons: list[str]) -> None:
    settings = get_settings()
    if settings.football_data_api_key is None:
        console.print("[red]ANALYTIS_FOOTBALL_DATA_API_KEY not set[/red]")
        raise typer.Exit(code=2)
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    try:
        async with httpx.AsyncClient(
            base_url=FootballDataAdapter.BASE_URL, timeout=30.0
        ) as client:
            adapter = FootballDataAdapter(
                client=client,
                api_key=settings.football_data_api_key.get_secret_value(),
            )
            use_case = IngestFixturesUseCase(factory, adapter)
            total = 0
            for season in seasons:
                console.print(f"→ season={season}")
                result = await use_case.execute(FixturesParams(competition, season))
                total += result.records_touched
                console.print(f"   {result.records_touched} matches")
        console.print(f"[green]Backfill total: {total} matches[/green]")
    finally:
        await engine.dispose()
```

- [ ] **Step 2: Atualizar `src/analytis/cli/app.py`**

```python
"""CLI entry point."""

import typer

from analytis.cli import api, db, ingest
from analytis.config import get_settings
from analytis.logging import configure_logging

app = typer.Typer(
    name="analytis",
    help="Football analytics backend — predictions, ingestion, modeling.",
    no_args_is_help=True,
    add_completion=False,
)

app.add_typer(db.app, name="db", help="Database operations.")
app.add_typer(api.app, name="api", help="HTTP API server.")
app.add_typer(ingest.app, name="ingest", help="Data ingestion.")


@app.callback()
def _root_callback() -> None:
    settings = get_settings()
    configure_logging(level=settings.log_level, fmt=settings.log_format)


if __name__ == "__main__":
    app()
```

- [ ] **Step 3: Validar CLI**

```bash
uv run analytis ingest --help
uv run analytis ingest fixtures --help
```

Expected: Typer mostra help.

- [ ] **Step 4: Commit**

```bash
git add src/analytis/cli/ingest.py src/analytis/cli/app.py
git commit -m "feat(cli): add ingest fixtures and backfill subcommands"
```

---

## Task 24: APScheduler embarcado

**Files:**
- Create: `src/analytis/ingestion/scheduler.py`

- [ ] **Step 1: Criar `src/analytis/ingestion/scheduler.py`**

```python
"""APScheduler wiring — registers ingestion jobs on a single embedded scheduler."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from analytis.logging import get_logger

logger = get_logger(__name__)


@dataclass
class JobSpec:
    name: str
    fn: Callable[[], Awaitable[None]]
    cron: str | None = None
    interval_seconds: int | None = None


def build_scheduler(jobs: list[JobSpec]) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    for job in jobs:
        if job.cron:
            trigger = CronTrigger.from_crontab(job.cron)
        elif job.interval_seconds:
            trigger = IntervalTrigger(seconds=job.interval_seconds)
        else:
            raise ValueError(f"job {job.name} must define cron or interval_seconds")
        scheduler.add_job(
            job.fn,
            trigger=trigger,
            id=job.name,
            replace_existing=True,
            misfire_grace_time=300,
        )
        logger.info("scheduler.job_registered", job=job.name)
    return scheduler
```

- [ ] **Step 2: Validar import**

```bash
uv run python -c "from analytis.ingestion.scheduler import build_scheduler, JobSpec; print('ok')"
uv run mypy src
uv run ruff check .
```

Expected: prints "ok".

- [ ] **Step 3: Commit**

```bash
git add src/analytis/ingestion/scheduler.py
git commit -m "feat(ingestion): apscheduler builder for periodic ingestion jobs"
```

---

## Task 25: README + docs operacionais

**Files:**
- Create: `README.md`

- [ ] **Step 1: Criar `README.md`**

````markdown
# analytis

Football analytics backend platform — pre-match probabilistic predictions for 1X2, Over/Under goals, BTTS and corners markets.

## Status

**Plan 1 of 4 — Foundation + Ingestion.** Pre-match probabilistic models, API key auth, full prediction pipeline still under construction. See `docs/superpowers/specs/2026-06-12-football-analytics-design.md`.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Docker Desktop (for Postgres)
- A [Football-Data.org](https://www.football-data.org/) free API token

## Setup

```bash
git clone <repo> && cd analytis
uv sync
cp .env.example .env
# edit .env: set ANALYTIS_FOOTBALL_DATA_API_KEY and ANALYTIS_API_KEY

docker compose up -d postgres
uv run analytis db migrate
```

## Common operations

```bash
# HTTP API
uv run analytis api serve --port 8000
curl -H "X-API-Key: $ANALYTIS_API_KEY" http://localhost:8000/v1/health

# Ingest the World Cup 2026 fixtures + results so far
uv run analytis ingest fixtures --competition 2000 --season 2026

# Backfill historical World Cups
uv run analytis ingest backfill --competition 2000 --season 2018 --season 2022
```

## Tests

```bash
uv run pytest                          # all tests
uv run pytest -m "not integration"     # unit only (no docker)
uv run pytest -m integration -v        # integration only (testcontainers)
```

## Quality

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src tests
uv run pre-commit run --all-files
```

## Layout

```
src/analytis/
├── config.py            # Pydantic Settings (env-driven)
├── logging.py           # structlog setup
├── domain/              # Pydantic entities (pure, no I/O)
├── persistence/         # SQLAlchemy ORM + repositories
├── ingestion/           # adapters, rate limit, retry, pipeline
├── application/         # use cases (orchestration)
├── api/                 # FastAPI routes
└── cli/                 # Typer subcommands
```

## License

Proprietary — see project owner.
````

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with setup, ops and layout"
```

---

## Task 26: CI básica via GitHub Actions

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Criar `.github/workflows/ci.yml`**

```yaml
name: ci

on:
  push:
    branches: [main]
  pull_request:

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true
      - run: uv sync --frozen
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run mypy src tests

  unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true
      - run: uv sync --frozen
      - run: uv run pytest -m "not integration" --cov=analytis --cov-report=xml -v

  integration:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: analytis
          POSTGRES_PASSWORD: analytis_test
          POSTGRES_DB: analytis_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U analytis -d analytis_test"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10
    env:
      ANALYTIS_DATABASE_URL: postgresql+psycopg://analytis:analytis_test@localhost:5432/analytis_test
      ANALYTIS_API_KEY: ci-test
      ANALYTIS_LOG_LEVEL: WARNING
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true
      - run: uv sync --frozen
      - run: uv run alembic upgrade head
      - run: uv run pytest -m integration -v
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: github actions for lint, unit and integration tests"
```

---

## Acceptance Criteria (end-of-plan checklist)

Manualmente, antes de declarar o plano completo:

- [ ] `uv run analytis --help` mostra subcomandos `db`, `api`, `ingest`
- [ ] `uv run analytis db migrate` aplica todas as migrations sem erro
- [ ] Postgres tem 13+ tabelas (`\dt` no `psql`)
- [ ] `uv run analytis api serve` sobe na porta 8000 e `GET /v1/health` retorna 200 com JSON `{"status":"ok",...}`
- [ ] `uv run analytis ingest fixtures --competition 2000 --season 2026` traz jogos da Copa 2026 (validar contagem ≥ 48 jogos)
- [ ] Re-rodar o mesmo `ingest fixtures` **não duplica** linhas (idempotência)
- [ ] `uv run analytis ingest backfill --competition 2000 --season 2018 --season 2022` carrega Copas 2018 e 2022
- [ ] `select count(*) from match where season_id in (select id from season where label='2018')` retorna ≥ 64 jogos
- [ ] `uv run pytest` passa com cobertura ≥ 75% nas pastas `domain/`, `persistence/`, `ingestion/`
- [ ] `uv run ruff check .` e `uv run mypy src tests` ambos limpos
- [ ] CI no GitHub Actions verde em todos os 3 jobs (lint, unit, integration)

Se algum item falhar, criar tarefa específica para corrigir antes de iniciar o Plano 2.
